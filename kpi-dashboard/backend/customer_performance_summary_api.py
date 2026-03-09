#!/usr/bin/env python3
"""
Customer Performance Summary API
Provides summary of accounts needing attention with focus areas.

DC2_S-aware: Uses PillarScore + DC2SKPI models for DC2_S vertical,
falls back to generic KPI model for SaaS.
"""

from flask import Blueprint, jsonify, request
from auth_middleware import get_current_customer_id
from models import db, Account, HealthTrend, PlaybookExecution, KPI, PillarScore, DC2SKPI
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from collections import defaultdict
import utils.health_thresholds as ht
import statistics
import traceback

customer_perf_summary_api = Blueprint('customer_perf_summary_api', __name__)

# Pillar code → display name mapping for DC2_S
PILLAR_NAMES = {
    'P1': 'Delivery & Velocity',
    'P2': 'Operational Stability',
    'P3': 'AI & Innovation',
    'P4': 'Customer Health',
    'P5': 'Experience',
}


@customer_perf_summary_api.route('/api/customer-performance/summary', methods=['GET'])
def get_performance_summary():
    """
    Get summary of accounts needing attention.
    DC2_S-aware: uses PillarScore for category scores and DC2SKPI for health.
    """
    try:
        customer_id = get_current_customer_id()

        if not customer_id:
            return jsonify({
                'status': 'error',
                'error': 'Authentication required',
                'message': 'Please log in to access this resource',
                'login_url': '/api/login'
            }), 401

        accounts = Account.query.filter_by(customer_id=customer_id).all()

        if not accounts:
            return jsonify({
                'status': 'success',
                'summary': {
                    'total_accounts': 0,
                    'critical_accounts': 0,
                    'at_risk_accounts': 0,
                    'healthy_accounts': 0,
                    'average_health_score': 0,
                    'company_avg_revenue_growth': 0
                },
                'accounts_needing_attention': [],
                'healthy_declining_revenue': [],
                'timeframe': 'Last 3 months'
            })

        # Detect vertical: if any account has DC2_S pillar scores, use DC2_S path
        sample_pillar = PillarScore.query.filter(
            PillarScore.account_id.in_([a.account_id for a in accounts])
        ).first()

        if sample_pillar:
            return _dc2s_performance_summary(customer_id, accounts)
        else:
            return _saas_performance_summary(customer_id, accounts)

    except Exception as e:
        traceback.print_exc()
        print(f"Error in get_performance_summary: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Failed to fetch performance summary'
        }), 500


def _dc2s_performance_summary(customer_id, accounts):
    """
    DC2_S-aware performance summary using PillarScore and DC2SKPI.
    L3 account health uses CustomerConfig pillar weights (not equal-weight).
    """
    from models import CustomerConfig

    account_ids = [a.account_id for a in accounts]
    account_map = {a.account_id: a for a in accounts}

    # Load pillar weights from CustomerConfig
    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    pillar_weights = {}
    if config and config.dc2s_pillar_weights:
        pillar_weights = config.dc2s_pillar_weights  # e.g., {'P1': 0.15, 'P2': 0.20, ...}

    # Get latest measurement month with pillar scores
    latest_month = db.session.query(
        func.max(PillarScore.measurement_month)
    ).filter(
        PillarScore.account_id.in_(account_ids)
    ).scalar()

    if not latest_month:
        # No pillar scores at all — return empty with account count
        return jsonify({
            'status': 'success',
            'summary': {
                'total_accounts': len(accounts),
                'critical_accounts': 0,
                'at_risk_accounts': 0,
                'healthy_accounts': 0,
                'average_health_score': 0,
                'company_avg_revenue_growth': 0
            },
            'accounts_needing_attention': [],
            'healthy_declining_revenue': [],
            'timeframe': f'No scored data yet'
        })

    # Get all pillar scores for the latest month
    pillar_scores = PillarScore.query.filter(
        PillarScore.account_id.in_(account_ids),
        PillarScore.measurement_month == latest_month
    ).all()

    # Group by account_id
    account_pillars = defaultdict(list)
    for ps in pillar_scores:
        account_pillars[ps.account_id].append(ps)

    account_summaries = []
    three_months_ago = datetime.utcnow() - timedelta(days=90)

    for acct_id, pillars in account_pillars.items():
        account = account_map.get(acct_id)
        if not account:
            continue

        # Build category scores from pillars
        category_scores = {}
        for ps in pillars:
            name = PILLAR_NAMES.get(ps.pillar_code, ps.pillar_code)
            score = float(ps.pillar_score) if ps.pillar_score else 0
            category_scores[name] = round(score, 1)

        if not category_scores:
            continue

        # L3: Weighted average of pillar scores using CustomerConfig weights
        if pillar_weights:
            weighted_sum = 0.0
            total_weight = 0.0
            for ps in pillars:
                w = pillar_weights.get(ps.pillar_code, 0.2)
                s = float(ps.pillar_score) if ps.pillar_score else 0
                weighted_sum += s * w
                total_weight += w
            overall_health = weighted_sum / total_weight if total_weight > 0 else 0
        else:
            overall_health = sum(category_scores.values()) / len(category_scores)

        # Focus areas (worst 2 pillars)
        focus_areas = sorted(
            [(cat, score) for cat, score in category_scores.items()],
            key=lambda x: x[1]
        )[:2]

        # Active playbooks count
        try:
            active_playbooks = PlaybookExecution.query.filter_by(
                account_id=acct_id,
                customer_id=customer_id
            ).filter(
                PlaybookExecution.started_at >= three_months_ago
            ).count()
        except Exception:
            active_playbooks = 0

        # Revenue growth from DC2SKPI (look for revenue-related KPIs)
        revenue_growth_pct = _dc2s_revenue_growth(acct_id, latest_month)

        account_summaries.append({
            'account_id': acct_id,
            'account_name': account.account_name,
            'revenue': float(account.revenue) if account.revenue else 0,
            'industry': account.industry or 'Data Center',
            'region': account.region or 'N/A',
            'overall_health_score': round(overall_health, 1),
            'category_scores': category_scores,
            'focus_areas': [{'category': cat, 'score': round(score, 1)} for cat, score in focus_areas],
            'active_playbooks_count': active_playbooks,
            'revenue_growth_pct': revenue_growth_pct
        })

    # Also include accounts that have NO pillar scores (show as critical)
    scored_ids = set(account_pillars.keys())
    for account in accounts:
        if account.account_id not in scored_ids:
            account_summaries.append({
                'account_id': account.account_id,
                'account_name': account.account_name,
                'revenue': float(account.revenue) if account.revenue else 0,
                'industry': account.industry or 'Data Center',
                'region': account.region or 'N/A',
                'overall_health_score': 0,
                'category_scores': {},
                'focus_areas': [{'category': 'No data', 'score': 0}],
                'active_playbooks_count': 0,
                'revenue_growth_pct': 0
            })

    return _build_summary_response(accounts, account_summaries, latest_month)


def _saas_performance_summary(customer_id, accounts):
    """
    Original SaaS performance summary using generic KPI model.
    """
    three_months_ago = datetime.utcnow() - timedelta(days=90)
    account_summaries = []

    for account in accounts:
        category_scores = _saas_category_scores(account.account_id, customer_id)
        if not category_scores:
            continue

        overall_health_score = sum(category_scores.values()) / len(category_scores)
        revenue_growth_pct = _saas_revenue_growth(account.account_id, customer_id)

        focus_areas = sorted(
            [(cat, score) for cat, score in category_scores.items()],
            key=lambda x: x[1]
        )[:2]

        try:
            active_playbooks = PlaybookExecution.query.filter_by(
                account_id=account.account_id,
                customer_id=customer_id
            ).filter(
                PlaybookExecution.started_at >= three_months_ago
            ).count()
        except Exception:
            active_playbooks = 0

        account_summaries.append({
            'account_id': account.account_id,
            'account_name': account.account_name,
            'revenue': float(account.revenue) if account.revenue else 0,
            'industry': account.industry,
            'region': account.region,
            'overall_health_score': overall_health_score,
            'category_scores': category_scores,
            'focus_areas': [{'category': cat, 'score': score} for cat, score in focus_areas],
            'active_playbooks_count': active_playbooks,
            'revenue_growth_pct': revenue_growth_pct
        })

    return _build_summary_response(accounts, account_summaries)


def _build_summary_response(accounts, account_summaries, latest_month=None):
    """Build the final JSON response from account summaries."""
    total_accounts = len(accounts)

    # Thresholds from centralized config
    _h = ht.healthy_min()
    _a = ht.at_risk_min()
    critical_accounts = len([a for a in account_summaries if a['overall_health_score'] < _a])
    at_risk_accounts = len([a for a in account_summaries if _a <= a['overall_health_score'] < _h])
    healthy_accounts = len([a for a in account_summaries if a['overall_health_score'] >= _h])

    # Sort ascending by health
    account_summaries.sort(key=lambda x: x['overall_health_score'])

    # Accounts needing attention: score < healthy threshold, or bottom 3 if all healthy
    accounts_needing_attention = [a for a in account_summaries if a['overall_health_score'] < _h]
    if len(accounts_needing_attention) < 3:
        accounts_needing_attention = account_summaries[:min(3, len(account_summaries))]
    else:
        accounts_needing_attention = accounts_needing_attention[:6]

    # Healthy accounts with declining revenue
    healthy_declining_revenue = [
        a for a in account_summaries
        if a['overall_health_score'] >= 80 and a.get('revenue_growth_pct', 0) < 0
    ]
    healthy_declining_revenue.sort(key=lambda x: x.get('revenue_growth_pct', 0))
    healthy_declining_revenue = healthy_declining_revenue[:5]

    # Company average
    all_growth = [a['revenue_growth_pct'] for a in account_summaries if a.get('revenue_growth_pct') is not None]
    avg_growth = sum(all_growth) / len(all_growth) if all_growth else 0

    # L4: Revenue-weighted average of L3 account health scores
    total_revenue = sum(a.get('revenue', 0) for a in account_summaries)
    if total_revenue > 0:
        avg_health = sum(a['overall_health_score'] * a.get('revenue', 0) for a in account_summaries) / total_revenue
    else:
        avg_health = sum(a['overall_health_score'] for a in account_summaries) / max(len(account_summaries), 1)

    timeframe = f'Month: {latest_month.strftime("%Y-%m")}' if latest_month else 'Last 6 months'

    return jsonify({
        'status': 'success',
        'summary': {
            'total_accounts': total_accounts,
            'critical_accounts': critical_accounts,
            'at_risk_accounts': at_risk_accounts,
            'healthy_accounts': healthy_accounts,
            'average_health_score': round(avg_health, 1),
            'company_avg_revenue_growth': round(avg_growth, 1)
        },
        'accounts_needing_attention': accounts_needing_attention,
        'healthy_declining_revenue': healthy_declining_revenue,
        'timeframe': timeframe
    })


# ──────────────────────────────────────────────────────────────
# DC2_S helpers
# ──────────────────────────────────────────────────────────────

def _dc2s_revenue_growth(account_id, latest_month):
    """Estimate revenue growth from DC2SKPI trend (last 3 months vs prior 3 months)."""
    try:
        kpis = DC2SKPI.query.filter_by(account_id=account_id).order_by(
            DC2SKPI.measured_at.desc()
        ).limit(200).all()

        if not kpis:
            return 0.0

        # Use overall health trend as proxy for revenue trajectory
        # Group by month, average the scores
        month_scores = defaultdict(list)
        for k in kpis:
            if k.measured_at:
                key = k.measured_at.strftime('%Y-%m')
                try:
                    month_scores[key].append(float(k.score) if k.score is not None else 0)
                except (ValueError, TypeError):
                    pass

        sorted_months = sorted(month_scores.keys())
        if len(sorted_months) < 2:
            return 0.0

        # Recent half vs earlier half
        mid = len(sorted_months) // 2
        recent_avgs = [statistics.mean(month_scores[m]) for m in sorted_months[mid:]]
        earlier_avgs = [statistics.mean(month_scores[m]) for m in sorted_months[:mid]]

        recent_overall = statistics.mean(recent_avgs) if recent_avgs else 0
        earlier_overall = statistics.mean(earlier_avgs) if earlier_avgs else 0

        if earlier_overall == 0:
            return 0.0

        return round(((recent_overall - earlier_overall) / earlier_overall) * 100, 1)
    except Exception:
        return 0.0


# ──────────────────────────────────────────────────────────────
# SaaS helpers (original logic, preserved for non-DC2_S customers)
# ──────────────────────────────────────────────────────────────

def _saas_revenue_growth(account_id, customer_id):
    """Calculate revenue growth % for a SaaS account."""
    try:
        from kpi_queries import get_account_level_kpis
        account_kpis = get_account_level_kpis(account_id, customer_id)
        revenue_kpis = [kpi for kpi in account_kpis if kpi.kpi_parameter == 'Revenue Growth']

        if not revenue_kpis or len(revenue_kpis) < 2:
            return 0.0

        revenue_data = []
        for kpi in revenue_kpis:
            try:
                val_str = str(kpi.data).replace('%', '').strip()
                revenue_data.append(float(val_str))
            except Exception:
                continue

        if len(revenue_data) < 2:
            return 0.0

        mid = len(revenue_data) // 2
        recent_avg = statistics.mean(revenue_data[mid:])
        earlier_avg = statistics.mean(revenue_data[:mid])

        if earlier_avg == 0:
            return 0.0

        return round(((recent_avg - earlier_avg) / earlier_avg) * 100, 1)
    except Exception:
        return 0.0


def _saas_category_scores(account_id, customer_id):
    """Calculate category-level health scores for a SaaS account."""
    try:
        from kpi_queries import get_account_level_kpis
        kpis = get_account_level_kpis(account_id, customer_id)

        if not kpis:
            return {}

        category_groups = defaultdict(list)
        for kpi in kpis:
            category_groups[kpi.category].append(kpi)

        category_scores = {}
        for category, kpi_list in category_groups.items():
            scores = []
            for kpi in kpi_list:
                try:
                    val_str = str(kpi.data).replace('%', '').replace('$', '').replace(',', '').strip()
                    parts = val_str.split()
                    if parts:
                        val = float(parts[0])
                        normalized = val if 0 <= val <= 100 else min(100, max(0, val / 10))
                        scores.append(normalized)
                    else:
                        scores.append(65)
                except Exception:
                    scores.append(65)

            category_scores[category] = sum(scores) / len(scores) if scores else 65

        return category_scores
    except Exception:
        return {}
