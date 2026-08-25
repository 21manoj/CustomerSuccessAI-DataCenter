#!/usr/bin/env python3
"""
Financial Projections API (Step 5 — Full Power of 1 Refactor)
==============================================================
When revenue_intelligence is enabled, projections use the Power of 1 model
with non-linear scaling curves and compounding cascades.  When disabled,
falls back to the legacy linear coefficient model.

Endpoints:
  GET /api/financial-projections/account/<account_id>  — Account-level
  GET /api/financial-projections/corporate             — Corporate rollup
  GET /api/financial-projections/kpi-impact/<kpi_name> — KPI-level analysis
  GET /api/financial-projections/scaling-curves         — Non-linear ROI curves (NEW)
  GET /api/financial-projections/quarterly-status       — Quarterly checkpoint status (NEW)
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from datetime import datetime, timedelta
from decimal import Decimal
import json

from extensions import db
from models import Account, KPI, KPITimeSeries, HealthTrend, FeatureToggle as FeatureToggleModel
from resolve_identifier import resolve_customer_id

financial_projections_api = Blueprint('financial_projections_api', __name__)


# ============================================================
# FEATURE TOGGLE HELPER
# ============================================================

def _is_revenue_intelligence_enabled(customer_id):
    """Check if the revenue_intelligence feature toggle is on for this customer."""
    toggle = FeatureToggleModel.query.filter_by(
        customer_id=customer_id,
        feature_name='revenue_intelligence'
    ).first()
    return toggle and toggle.enabled


# ============================================================
# LEGACY COEFFICIENT MODEL (fallback when feature disabled)
# ============================================================

FINANCIAL_IMPACT_COEFFICIENTS = {
    'Product Usage KPI': {
        'revenue_impact': 0.15,
        'cost_impact': -0.05,
        'retention_impact': 0.08
    },
    'Support KPI': {
        'revenue_impact': 0.08,
        'cost_impact': -0.12,
        'retention_impact': 0.12
    },
    'Customer Sentiment KPI': {
        'revenue_impact': 0.20,
        'cost_impact': -0.03,
        'retention_impact': 0.15
    },
    'Business Outcomes KPI': {
        'revenue_impact': 0.25,
        'cost_impact': -0.08,
        'retention_impact': 0.10
    },
    'Relationship Strength KPI': {
        'revenue_impact': 0.18,
        'cost_impact': -0.04,
        'retention_impact': 0.20
    }
}

# Map health score categories to Power of 1 metrics
_CATEGORY_TO_PO1 = {
    'product_usage': 'product_adoption',
    'support': 'ticket_resolution_time',
    'customer_sentiment': 'GRR',
    'business_outcomes': 'NRR',
    'relationship_strength': 'expansion_rate',
}


def calculate_financial_impact(kpi_category, current_score, projected_score, account_revenue):
    """Legacy linear financial impact calculation."""
    if kpi_category not in FINANCIAL_IMPACT_COEFFICIENTS:
        return {
            'revenue_impact': 0, 'cost_savings': 0,
            'retention_improvement': 0, 'total_impact': 0
        }

    score_change = projected_score - current_score
    improvement_factor = score_change / 10

    coefficients = FINANCIAL_IMPACT_COEFFICIENTS[kpi_category]

    revenue_impact = account_revenue * coefficients['revenue_impact'] * improvement_factor
    cost_savings = account_revenue * abs(coefficients['cost_impact']) * improvement_factor
    retention_improvement = coefficients['retention_impact'] * improvement_factor * 100

    total_impact = revenue_impact + cost_savings

    return {
        'revenue_impact': float(revenue_impact),
        'cost_savings': float(cost_savings),
        'retention_improvement': float(retention_improvement),
        'total_impact': float(total_impact),
        'score_change': float(score_change),
        'improvement_factor': float(improvement_factor)
    }


# ============================================================
# POWER OF 1 FINANCIAL IMPACT (non-linear, compounding)
# ============================================================

def _power_of_1_financial_impact(score_key, current_score, projected_score, account_arr):
    """
    Convert a health-score improvement into Power of 1 dollar impact.

    Uses non-linear scaling: impact grows compoundingly with improvement_pct.
    Investment is NOT held constant across improvement levels (owner decision,
    item 20, state-of-play.md 2026-08-24) — it scales per tier via
    calculate_portfolio_impact's cost_scale; this function only returns dollar
    impact, no investment figure, so it was never itself wrong, but its old
    docstring repeated the retired "same investment" framing.
    """
    try:
        from power_of_1_model import calculate_power_of_1_impact, POWER_OF_1_METRICS
    except ImportError:
        return None

    metric_id = _CATEGORY_TO_PO1.get(score_key)
    if not metric_id:
        return None

    metric = POWER_OF_1_METRICS.get(metric_id)
    if not metric:
        return None

    # Convert 0-100 health score change to % improvement units
    score_change = projected_score - current_score
    # A 10-point health score improvement ≈ 1% metric improvement
    improvement_pct = score_change / 10.0

    if improvement_pct <= 0:
        return {
            'metric_id': metric_id,
            'display_name': metric.display_name,
            'improvement_pct': round(improvement_pct, 2),
            'direct_impact': 0, 'compounding_impact': 0, 'total_impact': 0,
            'roi': 0, 'payback_months': None,
            'category': metric.category.value,
            'revenue_increase': 0, 'cost_savings': 0,
        }

    result = calculate_power_of_1_impact(metric_id, improvement_pct, account_arr)
    return result


# ============================================================
# ACCOUNT-LEVEL PROJECTIONS
# ============================================================

@financial_projections_api.route('/api/financial-projections/account/<int:account_id>', methods=['GET'])
def get_account_financial_projections(account_id):
    """Get financial projections for a specific account based on KPI trends."""
    customer_id = get_current_customer_id()

    if not customer_id:
        return jsonify({'error': 'Authentication required (handled by middleware)'}), 400

    customer_id = resolve_customer_id(db, customer_id)
    use_po1 = _is_revenue_intelligence_enabled(customer_id)

    try:
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).first()

        if not account:
            return jsonify({'error': 'Account not found'}), 404

        recent_trends = HealthTrend.query.filter_by(
            account_id=account_id
        ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).limit(12).all()

        if len(recent_trends) < 2:
            return jsonify({
                'account_id': account_id,
                'account_name': account.account_name,
                'revenue': float(account.revenue) if account.revenue else 0,
                'projections': [],
                'message': 'Insufficient trend data for projections'
            })

        latest_trend = recent_trends[0]
        account_arr = float(account.revenue) if account.revenue else 1_000_000

        baseline_scores = {
            'product_usage': float(latest_trend.product_usage_score) if latest_trend.product_usage_score else 0,
            'support': float(latest_trend.support_score) if latest_trend.support_score else 0,
            'customer_sentiment': float(latest_trend.customer_sentiment_score) if latest_trend.customer_sentiment_score else 0,
            'business_outcomes': float(latest_trend.business_outcomes_score) if latest_trend.business_outcomes_score else 0,
            'relationship_strength': float(latest_trend.relationship_strength_score) if latest_trend.relationship_strength_score else 0,
            'overall': float(latest_trend.overall_health_score) if latest_trend.overall_health_score else 0
        }

        projections = []
        categories = [
            ('Product Usage KPI', 'product_usage'),
            ('Support KPI', 'support'),
            ('Customer Sentiment KPI', 'customer_sentiment'),
            ('Business Outcomes KPI', 'business_outcomes'),
            ('Relationship Strength KPI', 'relationship_strength')
        ]

        for months_ahead in [3, 6, 12]:
            projected_month = datetime.now() + timedelta(days=months_ahead * 30)
            projected_scores = {}
            total_impact = 0
            total_revenue_impact = 0
            total_cost_savings = 0
            po1_details = {}

            for category_name, score_key in categories:
                current_score = baseline_scores[score_key]

                try:
                    trend_data = [getattr(trend, f"{score_key}_score") for trend in recent_trends[:3]]
                except AttributeError:
                    trend_data = [0, 0, 0]

                if len(trend_data) >= 2:
                    trend_slope = (trend_data[0] - trend_data[-1]) / len(trend_data)
                    projected_score = max(0, min(100, current_score + (trend_slope * months_ahead)))
                else:
                    projected_score = current_score

                projected_scores[score_key] = projected_score

                # --- Power of 1 path (non-linear) ---
                if use_po1:
                    po1 = _power_of_1_financial_impact(
                        score_key, current_score, projected_score, account_arr
                    )
                    if po1 and 'total_impact' in po1:
                        total_impact += po1['total_impact']
                        total_revenue_impact += po1.get('impact_breakdown', {}).get('revenue_increase', 0)
                        total_cost_savings += po1.get('impact_breakdown', {}).get('cost_savings', 0)
                        po1_details[score_key] = po1
                        continue

                # --- Legacy path (linear) ---
                impact = calculate_financial_impact(
                    category_name, current_score, projected_score, account_arr
                )
                total_impact += impact['total_impact']
                total_revenue_impact += impact['revenue_impact']
                total_cost_savings += impact['cost_savings']

            # Weighted overall score
            weights = {
                'product_usage': 0.3, 'support': 0.2,
                'customer_sentiment': 0.2, 'business_outcomes': 0.15,
                'relationship_strength': 0.15
            }
            overall_projected = sum(
                projected_scores[k] * w for k, w in weights.items()
            )

            projection = {
                'months_ahead': months_ahead,
                'projection_date': projected_month.strftime('%Y-%m'),
                'projected_scores': projected_scores,
                'overall_projected_score': float(overall_projected),
                'financial_impact': {
                    'total_impact': round(float(total_impact), 2),
                    'revenue_impact': round(float(total_revenue_impact), 2),
                    'cost_savings': round(float(total_cost_savings), 2),
                    'roi_percentage': round(
                        float((total_impact / account_arr) * 100), 2
                    ) if account_arr else 0,
                },
                'confidence_level': 'medium' if months_ahead <= 6 else 'low',
                'model': 'power_of_1' if use_po1 else 'legacy_linear',
            }

            if use_po1 and po1_details:
                projection['power_of_1_detail'] = po1_details

            projections.append(projection)

        return jsonify({
            'account_id': account_id,
            'account_name': account.account_name,
            'revenue': float(account.revenue) if account.revenue else 0,
            'baseline_scores': baseline_scores,
            'projections': projections,
            'model': 'power_of_1' if use_po1 else 'legacy_linear',
            'last_updated': datetime.now().isoformat()
        })

    except Exception as e:
        import traceback
        print(f"Error generating financial projections: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ============================================================
# CORPORATE ROLLUP
# ============================================================

@financial_projections_api.route('/api/financial-projections/corporate', methods=['GET'])
def get_corporate_financial_projections():
    """Get corporate-level financial projections with Power of 1 scaling."""
    customer_id = get_current_customer_id()

    if not customer_id:
        return jsonify({'error': 'Authentication required (handled by middleware)'}), 400

    customer_id = resolve_customer_id(db, customer_id)
    use_po1 = _is_revenue_intelligence_enabled(customer_id)

    try:
        accounts = Account.query.filter_by(customer_id=customer_id).all()

        if not accounts:
            return jsonify({'error': 'No accounts found'}), 404

        total_revenue = sum(float(a.revenue) for a in accounts if a.revenue)

        # --- Power of 1 corporate projection ---
        if use_po1:
            try:
                from power_of_1_model import (
                    calculate_portfolio_impact, SCALING_SCENARIOS, INVESTMENT_SUMMARY
                )
                from quarterly_checkpoints import (
                    assess_quarter, get_current_quarter_from_date, assessment_to_dict
                )

                improvement_pct = request.args.get('improvement_pct', 1.0, type=float)
                result = calculate_portfolio_impact(improvement_pct, total_revenue or None)

                # Build scaling curves for 1%, 2%, 3%, 4%, 5%, 6%
                scaling_curves = []
                for pct in [1, 2, 3, 4, 5, 6]:
                    r = calculate_portfolio_impact(float(pct), total_revenue or None)
                    scaling_curves.append({
                        'improvement_pct': pct,
                        'total_impact': r['totals']['total_impact'],
                        'roi': r['totals']['roi'],
                        'payback_months': r['totals']['payback_months'],
                        'investment': r['totals']['investment'],
                    })

                return jsonify({
                    'customer_id': customer_id,
                    'total_revenue': float(total_revenue),
                    'total_accounts': len(accounts),
                    'model': 'power_of_1',
                    'improvement_pct': improvement_pct,
                    'totals': result['totals'],
                    'metrics': result['metrics'],
                    'scaling_curves': scaling_curves,
                    'scaling_scenarios': SCALING_SCENARIOS,
                    'investment_summary': INVESTMENT_SUMMARY,
                    'time_economics': result.get('time_economics'),
                    'last_updated': datetime.now().isoformat(),
                })
            except Exception as po1_err:
                print(f"Power of 1 corporate projection failed, falling back: {po1_err}")

        # --- Legacy corporate projection ---
        corporate_projections = []

        for months_ahead in [3, 6, 12]:
            total_financial_impact = 0
            account_projections = []

            for account in accounts:
                account_data = get_account_financial_projections(account.account_id).get_json()
                if 'projections' in account_data:
                    account_proj = next(
                        (p for p in account_data['projections'] if p['months_ahead'] == months_ahead),
                        None
                    )
                    if account_proj:
                        total_financial_impact += account_proj['financial_impact']['total_impact']
                        account_projections.append({
                            'account_id': account.account_id,
                            'account_name': account.account_name,
                            'financial_impact': account_proj['financial_impact']
                        })

            projected_month = datetime.now() + timedelta(days=months_ahead * 30)

            corporate_projections.append({
                'months_ahead': months_ahead,
                'projection_date': projected_month.strftime('%Y-%m'),
                'total_financial_impact': float(total_financial_impact),
                'revenue_impact': float(total_financial_impact * 0.6),
                'cost_savings': float(total_financial_impact * 0.4),
                'roi_percentage': float((total_financial_impact / total_revenue) * 100) if total_revenue > 0 else 0,
                'accounts_count': len(account_projections),
                'account_projections': account_projections,
                'confidence_level': 'medium' if months_ahead <= 6 else 'low'
            })

        return jsonify({
            'customer_id': customer_id,
            'total_revenue': float(total_revenue),
            'total_accounts': len(accounts),
            'model': 'legacy_linear',
            'corporate_projections': corporate_projections,
            'last_updated': datetime.now().isoformat()
        })

    except Exception as e:
        print(f"Error generating corporate financial projections: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================
# NON-LINEAR SCALING CURVES (NEW — Step 5)
# ============================================================

@financial_projections_api.route('/api/financial-projections/scaling-curves', methods=['GET'])
def get_scaling_curves():
    """
    Return non-linear ROI scaling curves for the Power of 1 model.

    Investment scales WITH improvement_pct here (calculate_portfolio_impact's
    cost_scale, ~+50% of the base per 1% improvement) — not a fixed $247K.
    Owner decision, item 20 (state-of-play.md, 2026-08-24): a flat investment
    across every improvement tier was the retired thesis; $247K is the
    baseline-tier reference figure (10M-ARR, 4% improvement), not a constant.
    No frontend caller found for this route as of 2026-08-24 (dead server-side
    endpoint) — safe to remove/wire up, but out of scope of this doc fix.
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 400

    customer_id = resolve_customer_id(db, customer_id)

    if not _is_revenue_intelligence_enabled(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    try:
        from power_of_1_model import (
            calculate_portfolio_impact, SCALING_SCENARIOS,
            INVESTMENT_SUMMARY, POWER_OF_1_METRICS,
        )

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None

        curves = []
        for pct_x10 in range(5, 65, 5):  # 0.5% to 6.0% in 0.5% steps
            pct = pct_x10 / 10.0
            r = calculate_portfolio_impact(pct, total_arr)
            curves.append({
                'improvement_pct': pct,
                'direct_impact': r['totals']['direct_impact'],
                'compounding_effect': r['totals']['compounding_effect'],
                'total_impact': r['totals']['total_impact'],
                'investment': r['totals']['investment'],
                'roi': r['totals']['roi'],
                'payback_months': r['totals']['payback_months'],
                'revenue_increase': r['totals']['revenue_increase'],
                'cost_savings': r['totals']['cost_savings'],
            })

        # Per-metric scaling curves
        metric_curves = {}
        for metric_id in POWER_OF_1_METRICS:
            from power_of_1_model import calculate_power_of_1_impact
            metric_points = []
            for pct_x10 in [10, 20, 40, 60]:
                pct = pct_x10 / 10.0
                impact = calculate_power_of_1_impact(metric_id, pct, total_arr)
                metric_points.append({
                    'improvement_pct': pct,
                    'total_impact': impact['total_impact'],
                    'roi': impact['roi'],
                })
            metric_curves[metric_id] = metric_points

        return jsonify({
            'customer_id': customer_id,
            'total_arr': total_arr,
            'portfolio_curves': curves,
            'metric_curves': metric_curves,
            'scenarios': SCALING_SCENARIOS,
            'investment_summary': INVESTMENT_SUMMARY,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# QUARTERLY STATUS (NEW — Step 5, bridges to Step 4)
# ============================================================

@financial_projections_api.route('/api/financial-projections/quarterly-status', methods=['GET'])
def get_quarterly_status():
    """
    Return current quarter checkpoint assessment using Step 4 validation logic.
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 400

    customer_id = resolve_customer_id(db, customer_id)

    if not _is_revenue_intelligence_enabled(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    try:
        from quarterly_checkpoints import (
            assess_quarter, assess_full_year, get_current_quarter_from_date,
            assessment_to_dict, QUARTER_TARGETS,
        )

        quarter = request.args.get('quarter', get_current_quarter_from_date())
        actual_values = {}

        # Try to extract actual values from query params
        for param_key, param_val in request.args.items():
            if param_key.startswith('metric_'):
                metric_id = param_key[7:]  # strip 'metric_'
                try:
                    actual_values[metric_id] = float(param_val)
                except ValueError:
                    pass

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None

        assessment = assess_quarter(quarter, actual_values, total_arr)

        return jsonify({
            'customer_id': customer_id,
            'assessment': assessment_to_dict(assessment),
            'all_quarters': {
                q: {'label': qt.label, 'month_range': qt.month_range}
                for q, qt in QUARTER_TARGETS.items()
            },
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# KPI IMPACT ANALYSIS (kept from legacy, enhanced)
# ============================================================

@financial_projections_api.route('/api/financial-projections/kpi-impact/<kpi_name>', methods=['GET'])
def get_kpi_financial_impact(kpi_name):
    """Get financial impact analysis for a specific KPI across all accounts."""
    customer_id = get_current_customer_id()

    if not customer_id:
        return jsonify({'error': 'Authentication required (handled by middleware)'}), 400

    customer_id = resolve_customer_id(db, customer_id)
    use_po1 = _is_revenue_intelligence_enabled(customer_id)

    try:
        kpis = db.session.query(KPI).join(Account).filter(
            KPI.kpi_parameter == kpi_name,
            Account.customer_id == customer_id
        ).all()

        if not kpis:
            return jsonify({'error': f'KPI "{kpi_name}" not found'}), 404

        impact_analysis = []
        total_potential_impact = 0

        # Check if this KPI maps to a Power of 1 metric
        po1_metric_id = None
        if use_po1:
            try:
                from power_of_1_model import get_metric_for_kpi_code
                po1_metric_id = get_metric_for_kpi_code(kpi_name)
            except ImportError:
                pass

        for kpi in kpis:
            account = db.session.get(Account, kpi.account_id)
            if not account:
                continue

            current_score = 50
            target_score = 80
            account_arr = float(account.revenue) if account.revenue else 1_000_000

            if po1_metric_id:
                from power_of_1_model import calculate_power_of_1_impact
                po1_impact = calculate_power_of_1_impact(
                    po1_metric_id, 3.0, account_arr  # Target 3% improvement
                )
                total_potential_impact += po1_impact['total_impact']
                impact_analysis.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'model': 'power_of_1',
                    'power_of_1_metric': po1_metric_id,
                    'financial_impact': po1_impact,
                    'kpi_category': kpi.category,
                })
            else:
                impact = calculate_financial_impact(
                    kpi.category, current_score, target_score, account_arr
                )
                total_potential_impact += impact['total_impact']
                impact_analysis.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'model': 'legacy_linear',
                    'current_score': current_score,
                    'target_score': target_score,
                    'financial_impact': impact,
                    'kpi_category': kpi.category,
                })

        return jsonify({
            'kpi_name': kpi_name,
            'customer_id': customer_id,
            'total_accounts': len(impact_analysis),
            'total_potential_impact': float(total_potential_impact),
            'impact_analysis': impact_analysis,
            'model': 'power_of_1' if po1_metric_id else 'legacy_linear',
            'last_updated': datetime.now().isoformat()
        })

    except Exception as e:
        print(f"Error analyzing KPI financial impact: {e}")
        return jsonify({'error': str(e)}), 500
