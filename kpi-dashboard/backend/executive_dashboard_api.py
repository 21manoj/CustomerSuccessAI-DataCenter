#!/usr/bin/env python3
"""
Executive Dashboard API — CRO & CFO Aggregated Views
=====================================================
Aggregated endpoints for executive dashboards. Each endpoint merges data
from health_scores, pillar_scores, context_nodes, context_edges,
playbook_executions, and ROI snapshots into a single response optimized
for the CRO (revenue-focused) and CFO (investment-focused) personas.

Endpoints:
  GET  /api/executive/cro-dashboard       — Revenue risk, story arcs, early warnings
  GET  /api/executive/cfo-dashboard       — Investment ROI, Power of 1, scaling projections
  GET  /api/executive/revenue-timeline    — Per-account revenue timeline with signal events
"""

import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta, date

from flask import Blueprint, request, jsonify

from auth_middleware import get_current_customer_id
from extensions import db
from models import (
    Account, HealthScore, PillarScore, KPIScore,
    ContextNode, ContextEdge, PlaybookExecution, ROISnapshot,
)
import utils.health_thresholds as ht

logger = logging.getLogger(__name__)

executive_dashboard_api = Blueprint('executive_dashboard_api', __name__)

# DC2S pillar display names
DC2S_PILLAR_DISPLAY = {
    'P1': 'Deployment Velocity',
    'P2': 'Operational Stability',
    'P3': 'AI Workload Performance',
    'P4': 'Channel & Partner Health',
    'P5': 'Expansion Readiness',
}

# Story arc pattern definitions (matched against context_node subtypes/properties)
STORY_ARC_PATTERNS = {
    'silent_churn': {
        'name': 'Silent Churn',
        'description': 'Gradual disengagement detected',
        'signal_subtypes': ['nps_decline', 'engagement_drop', 'champion_loss', 'usage_decline'],
        'impact_type': 'at_risk',
        'icon': 'alert',
    },
    'expansion_champion': {
        'name': 'Expansion Champion',
        'description': 'Internal advocate driving upsell',
        'signal_subtypes': ['expansion_signal', 'champion_identified', 'upsell_opportunity'],
        'impact_type': 'pipeline',
        'icon': 'trending_up',
    },
    'technical_debt': {
        'name': 'Technical Debt Spiral',
        'description': 'Compounding infrastructure issues',
        'signal_subtypes': ['sla_breach', 'ticket_spike', 'deployment_failure'],
        'impact_type': 'at_risk',
        'icon': 'warning',
    },
    'executive_sponsor_loss': {
        'name': 'Executive Sponsor Loss',
        'description': 'Key decision maker departed',
        'signal_subtypes': ['champion_loss', 'stakeholder_change', 'reorg_detected'],
        'impact_type': 'at_risk',
        'icon': 'person_off',
    },
    'adoption_acceleration': {
        'name': 'Adoption Acceleration',
        'description': 'Rapid feature adoption across teams',
        'signal_subtypes': ['kpi_improvement', 'adoption_spike', 'training_completed'],
        'impact_type': 'pipeline',
        'icon': 'rocket',
    },
    'renewal_momentum': {
        'name': 'Renewal Momentum',
        'description': 'Strong signals for on-time renewal',
        'signal_subtypes': ['renewal_confirmed', 'contract_discussion', 'budget_approved'],
        'impact_type': 'protected',
        'icon': 'check_circle',
    },
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_float(val, default=0.0):
    """Convert a Decimal/numeric value to float safely."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _current_quarter_label():
    """Return human-readable quarter label, e.g. 'Q1 2026'."""
    now = datetime.utcnow()
    quarter = (now.month - 1) // 3 + 1
    return f"Q{quarter} {now.year}"


def _get_customer_accounts(customer_id):
    """Get all accounts for a customer (regardless of account_status).

    Note: account_status may be 'active', 'at_risk', 'healthy', etc. —
    these are health-based labels set by the data loader, NOT business
    lifecycle states.  We must include all accounts so the CRO dashboard
    shows the complete portfolio including truly at-risk accounts.
    """
    return Account.query.filter_by(
        customer_id=customer_id,
    ).all()


def _get_latest_health_scores(customer_id, account_ids):
    """Get the most recent health score per account."""
    if not account_ids:
        return {}

    # Subquery for max measurement_month per account
    latest_month_sub = (
        db.session.query(
            HealthScore.account_id,
            db.func.max(HealthScore.measurement_month).label('max_month'),
        )
        .filter(HealthScore.account_id.in_(account_ids))
        .group_by(HealthScore.account_id)
        .subquery()
    )

    scores = (
        db.session.query(HealthScore)
        .join(
            latest_month_sub,
            db.and_(
                HealthScore.account_id == latest_month_sub.c.account_id,
                HealthScore.measurement_month == latest_month_sub.c.max_month,
            ),
        )
        .all()
    )

    return {s.account_id: s for s in scores}


def _get_previous_health_scores(customer_id, account_ids):
    """Get the second-most-recent health score per account (for trend comparison)."""
    if not account_ids:
        return {}

    # Get the two most recent months per account
    from sqlalchemy import func as sa_func

    all_scores = (
        HealthScore.query
        .filter(HealthScore.account_id.in_(account_ids))
        .order_by(HealthScore.account_id, HealthScore.measurement_month.desc())
        .all()
    )

    # Group by account, take second entry
    account_scores = defaultdict(list)
    for s in all_scores:
        account_scores[s.account_id].append(s)

    prev = {}
    for acct_id, scores_list in account_scores.items():
        if len(scores_list) >= 2:
            prev[acct_id] = scores_list[1]

    return prev


def _get_latest_pillar_scores(account_ids):
    """Get latest pillar scores per account.

    Tries PillarScore table first, then falls back to
    HealthScore.contributing_pillars JSON field.
    """
    if not account_ids:
        return {}

    # ── Try PillarScore table first ──
    latest_month_sub = (
        db.session.query(
            PillarScore.account_id,
            db.func.max(PillarScore.measurement_month).label('max_month'),
        )
        .filter(PillarScore.account_id.in_(account_ids))
        .group_by(PillarScore.account_id)
        .subquery()
    )

    scores = (
        db.session.query(PillarScore)
        .join(
            latest_month_sub,
            db.and_(
                PillarScore.account_id == latest_month_sub.c.account_id,
                PillarScore.measurement_month == latest_month_sub.c.max_month,
            ),
        )
        .all()
    )

    result = defaultdict(dict)
    for ps in scores:
        result[ps.account_id][ps.pillar_code] = _safe_float(ps.pillar_score)

    # ── Fallback: HealthScore.contributing_pillars for any missing accounts ──
    missing_ids = [aid for aid in account_ids if aid not in result]
    if missing_ids:
        hs_latest_sub = (
            db.session.query(
                HealthScore.account_id,
                db.func.max(HealthScore.measurement_month).label('max_month'),
            )
            .filter(HealthScore.account_id.in_(missing_ids))
            .group_by(HealthScore.account_id)
            .subquery()
        )
        hs_rows = (
            db.session.query(HealthScore)
            .join(
                hs_latest_sub,
                db.and_(
                    HealthScore.account_id == hs_latest_sub.c.account_id,
                    HealthScore.measurement_month == hs_latest_sub.c.max_month,
                ),
            )
            .all()
        )
        for hs in hs_rows:
            pillars = hs.contributing_pillars or {}
            if pillars:
                result[hs.account_id] = {
                    k: round(_safe_float(v), 1) for k, v in pillars.items()
                }

    return dict(result)


def _aggregate_revenue_from_context_graph(customer_id, account_ids):
    """Aggregate revenue metrics across all accounts from context graph nodes."""
    if not account_ids:
        return {
            'revenue_at_risk': 0, 'revenue_protected': 0,
            'expansion_pipeline': 0, 'node_count': 0,
        }

    outcome_nodes = (
        ContextNode.query
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.account_id.in_(account_ids),
            ContextNode.node_type == 'OUTCOME',
            ContextNode.revenue_impact.isnot(None),
        )
        .all()
    )

    at_risk = 0.0
    protected = 0.0
    expansion = 0.0

    for node in outcome_nodes:
        impact = _safe_float(node.revenue_impact)
        impact_type = (node.revenue_impact_type or '').lower()

        if impact_type == 'at_risk':
            at_risk += abs(impact)
        elif impact_type == 'protected':
            protected += abs(impact)
        elif impact_type == 'expansion':
            expansion += abs(impact)
        elif impact_type == 'lost':
            at_risk += abs(impact)

    return {
        'revenue_at_risk': round(at_risk, 2),
        'revenue_protected': round(protected, 2),
        'expansion_pipeline': round(expansion, 2),
        'node_count': len(outcome_nodes),
    }


def _build_story_arcs(customer_id, account_ids):
    """Analyze context graph nodes to identify active story arc patterns."""
    if not account_ids:
        return []

    signal_nodes = (
        ContextNode.query
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.account_id.in_(account_ids),
            ContextNode.node_type == 'SIGNAL',
        )
        .all()
    )

    # Group signals by subtype
    subtype_accounts = defaultdict(set)
    subtype_revenue = defaultdict(float)
    subtype_dates = defaultdict(list)

    for node in signal_nodes:
        subtype = (node.node_subtype or 'unknown').lower()
        subtype_accounts[subtype].add(node.account_id)
        subtype_revenue[subtype] += _safe_float(node.revenue_impact)
        if node.occurred_at:
            subtype_dates[subtype].append(node.occurred_at)

    arcs = []
    for arc_key, arc_def in STORY_ARC_PATTERNS.items():
        matching_accounts = set()
        total_revenue = 0.0
        all_dates = []

        for st in arc_def['signal_subtypes']:
            matching_accounts |= subtype_accounts.get(st, set())
            total_revenue += subtype_revenue.get(st, 0)
            all_dates.extend(subtype_dates.get(st, []))

        if not matching_accounts:
            continue

        # Calculate average runway (days from earliest signal to now)
        avg_runway_days = 0
        if all_dates:
            now = datetime.utcnow()
            deltas = [(now - d).days for d in all_dates if d < now]
            avg_runway_days = int(sum(deltas) / len(deltas)) if deltas else 0

        arc_entry = {
            'name': arc_def['name'],
            'description': arc_def['description'],
            'accounts': len(matching_accounts),
            'revenue_impact': round(abs(total_revenue), 2),
            'impact_type': arc_def['impact_type'],
            'icon': arc_def['icon'],
        }

        if arc_def['impact_type'] == 'pipeline':
            arc_entry['avg_deal_size'] = round(abs(total_revenue) / max(len(matching_accounts), 1), 2)
        else:
            arc_entry['avg_runway_days'] = avg_runway_days

        arcs.append(arc_entry)

    # Sort: at_risk arcs first, then by revenue impact descending
    arcs.sort(key=lambda a: (0 if a['impact_type'] == 'at_risk' else 1, -a['revenue_impact']))

    return arcs


def _calculate_early_warning_days(customer_id, account_ids):
    """Calculate average days of early warning from signals to outcomes."""
    if not account_ids:
        return 0

    # Find edges from SIGNAL nodes to OUTCOME nodes
    signal_node_ids = [
        r[0] for r in
        db.session.query(ContextNode.node_id)
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.account_id.in_(account_ids),
            ContextNode.node_type == 'SIGNAL',
        )
        .all()
    ]

    if not signal_node_ids:
        return 0

    edges_with_lag = (
        ContextEdge.query
        .filter(
            ContextEdge.from_node_id.in_(signal_node_ids),
            ContextEdge.lag_days.isnot(None),
            ContextEdge.lag_days > 0,
        )
        .all()
    )

    if not edges_with_lag:
        # Fallback: calculate from signal occurred_at to outcome occurred_at
        edges_to_outcomes = (
            db.session.query(ContextEdge)
            .join(ContextNode, ContextNode.node_id == ContextEdge.to_node_id)
            .filter(
                ContextEdge.from_node_id.in_(signal_node_ids),
                ContextNode.node_type == 'OUTCOME',
            )
            .all()
        )

        if not edges_to_outcomes:
            return 0

        # Compute lag from signal to outcome timestamps
        lag_days_list = []
        for edge in edges_to_outcomes:
            from_node = ContextNode.query.get(edge.from_node_id)
            to_node = ContextNode.query.get(edge.to_node_id)
            if from_node and to_node and from_node.occurred_at and to_node.occurred_at:
                delta = (to_node.occurred_at - from_node.occurred_at).days
                if delta > 0:
                    lag_days_list.append(delta)

        return int(sum(lag_days_list) / len(lag_days_list)) if lag_days_list else 0

    lag_values = [e.lag_days for e in edges_with_lag]
    return int(sum(lag_values) / len(lag_values))


def _get_playbook_investment(customer_id):
    """Estimate total CS investment from playbook executions."""
    executions = (
        PlaybookExecution.query
        .filter_by(customer_id=customer_id)
        .all()
    )

    total_cost = 0.0
    for ex in executions:
        # Extract cost from execution_data if available
        data = ex.execution_data or {}
        cost = data.get('estimated_cost') or data.get('cost') or 0
        if cost:
            total_cost += _safe_float(cost)
        else:
            # Estimate: ~$2,000 per playbook execution as baseline
            total_cost += 2000.0

    return round(total_cost, 2)


def _get_roi_snapshot(customer_id):
    """Get the latest ROI snapshot for the customer."""
    snapshot = (
        ROISnapshot.query
        .filter_by(customer_id=customer_id)
        .order_by(ROISnapshot.snapshot_date.desc())
        .first()
    )
    return snapshot


def _get_accounts_recovered(customer_id, account_ids):
    """Count accounts that improved from at-risk/critical to healthy."""
    if not account_ids:
        return 0

    latest = _get_latest_health_scores(customer_id, account_ids)
    prev = _get_previous_health_scores(customer_id, account_ids)

    recovered = 0
    healthy_min = ht.healthy_min()

    for acct_id in account_ids:
        curr_hs = latest.get(acct_id)
        prev_hs = prev.get(acct_id)
        if curr_hs and prev_hs:
            curr_score = _safe_float(curr_hs.health_score)
            prev_score = _safe_float(prev_hs.health_score)
            if curr_score >= healthy_min and prev_score < healthy_min:
                recovered += 1

    return recovered


def _get_expansion_candidates(customer_id, account_ids):
    """Count accounts with expansion signals in context graph."""
    if not account_ids:
        return 0

    expansion_nodes = (
        ContextNode.query
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.account_id.in_(account_ids),
            ContextNode.revenue_impact_type == 'expansion',
        )
        .with_entities(ContextNode.account_id)
        .distinct()
        .all()
    )

    return len(expansion_nodes)


# ─── 1. CRO Dashboard ────────────────────────────────────────────────────────

@executive_dashboard_api.route('/api/executive/cro-dashboard', methods=['GET'])
def cro_dashboard():
    """
    Aggregated CRO view: revenue at risk, story arcs, early warnings,
    highest risk accounts, and NRR projection.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 400

        accounts = _get_customer_accounts(customer_id)
        account_ids = [a.account_id for a in accounts]

        # ── Health scores ──
        latest_health = _get_latest_health_scores(customer_id, account_ids)
        prev_health = _get_previous_health_scores(customer_id, account_ids)

        # Compute revenue-weighted average health score
        total_weighted_score = 0.0
        total_revenue = 0.0
        at_risk_count = 0
        healthy_min_val = ht.healthy_min()

        account_details = []
        for acct in accounts:
            hs = latest_health.get(acct.account_id)
            score = _safe_float(hs.health_score) if hs else 0.0
            rev = _safe_float(acct.revenue)

            if score < healthy_min_val:
                at_risk_count += 1

            total_weighted_score += score * rev
            total_revenue += rev

            account_details.append({
                'account_id': acct.account_id,
                'account_name': acct.account_name,
                'health_score': round(score, 1),
                'status': ht.classify(score),
                'revenue': rev,
                'trend': (hs.trend or 'stable') if hs else 'stable',
            })

        avg_health = round(total_weighted_score / total_revenue, 1) if total_revenue > 0 else 0.0
        # Simple (unweighted) average — matches MCP list_accounts for consistency
        all_scores = [_safe_float(latest_health[aid].health_score) for aid in latest_health]
        avg_health_simple = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0

        # Health score change: compare weighted avg of latest vs previous
        prev_weighted = 0.0
        prev_total_rev = 0.0
        for acct in accounts:
            phs = prev_health.get(acct.account_id)
            if phs:
                prev_weighted += _safe_float(phs.health_score) * _safe_float(acct.revenue)
                prev_total_rev += _safe_float(acct.revenue)

        prev_avg = prev_weighted / prev_total_rev if prev_total_rev > 0 else avg_health
        health_change = round(avg_health - prev_avg, 1)

        # ── Revenue from context graph ──
        revenue_data = _aggregate_revenue_from_context_graph(customer_id, account_ids)

        # ── Story arcs ──
        story_arcs = _build_story_arcs(customer_id, account_ids)

        # ── Early warning days ──
        early_warning_days = _calculate_early_warning_days(customer_id, account_ids)

        # ── Accounts recovered & expansion candidates ──
        recovered = _get_accounts_recovered(customer_id, account_ids)
        expansion_candidates = _get_expansion_candidates(customer_id, account_ids)

        # ── ROI & NRR from snapshot ──
        roi_snap = _get_roi_snapshot(customer_id)
        playbook_roi_pct = round(roi_snap.historical_roi_pct or roi_snap.combined_roi_pct or 0) if roi_snap else 0
        nrr_projection = 100
        nrr_change = 0
        if roi_snap and roi_snap.metric_details:
            nrr_detail = roi_snap.metric_details.get('NRR', {})
            nrr_projection = round(nrr_detail.get('current', 100), 0)
            nrr_baseline = nrr_detail.get('baseline', nrr_projection)
            nrr_change = round(nrr_projection - nrr_baseline, 0)

        # ── Highest risk accounts (top 10 by lowest health) ──
        pillar_scores_map = _get_latest_pillar_scores(account_ids)
        account_details.sort(key=lambda a: a['health_score'])
        highest_risk = []
        for ad in account_details[:10]:
            pillars = pillar_scores_map.get(ad['account_id'], {})
            ad['pillar_scores'] = pillars
            highest_risk.append(ad)

        return jsonify({
            'status': 'success',
            'revenue_at_risk': revenue_data['revenue_at_risk'],
            'revenue_protected': revenue_data['revenue_protected'],
            'expansion_pipeline': revenue_data['expansion_pipeline'],
            'accounts_at_risk_count': at_risk_count,
            'accounts_recovered_count': recovered,
            'expansion_candidates_count': expansion_candidates,
            'avg_health_score': avg_health,
            'avg_health_score_simple': avg_health_simple,
            'health_score_change': health_change,
            'total_accounts': len(accounts),
            'total_arr': total_revenue,
            'early_warning_days': early_warning_days,
            'playbook_roi_pct': playbook_roi_pct,
            'nrr_projection': nrr_projection,
            'nrr_change': nrr_change,
            'story_arcs': story_arcs,
            'highest_risk_accounts': highest_risk,
            'quarter_label': _current_quarter_label(),
            'last_updated': datetime.utcnow().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error in cro_dashboard: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── 2. CFO Dashboard ────────────────────────────────────────────────────────

@executive_dashboard_api.route('/api/executive/cfo-dashboard', methods=['GET'])
def cfo_dashboard():
    """
    Aggregated CFO view: investment ROI, Power of 1 metrics,
    scaling projections, and pillar investment breakdown.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 400

        accounts = _get_customer_accounts(customer_id)
        account_ids = [a.account_id for a in accounts]

        # ── Total ARR ──
        total_arr = sum(_safe_float(a.revenue) for a in accounts)

        # ── Revenue from context graph ──
        revenue_data = _aggregate_revenue_from_context_graph(customer_id, account_ids)

        # ── CS Investment ──
        cs_investment = _get_playbook_investment(customer_id)

        # ── ROI from snapshot ──
        roi_snap = _get_roi_snapshot(customer_id)
        roi_pct = 0
        roi_impact = 0.0
        roi_investment = cs_investment
        nrr_projection = 100
        grr_projection = 85

        power_of_1_metrics = []

        if roi_snap:
            roi_pct = round(roi_snap.historical_roi_pct or roi_snap.combined_roi_pct or 0)
            roi_impact = _safe_float(roi_snap.historical_impact or roi_snap.forward_impact)
            if roi_snap.historical_investment:
                roi_investment = _safe_float(roi_snap.historical_investment)

            # Extract Power of 1 metrics from snapshot details
            # Supports two formats:
            #   A) {metric_id: {baseline, current, dollar_impact, ...}}
            #   B) {forward_metrics: [{id, impact, pct}]}
            if roi_snap.metric_details:
                details = roi_snap.metric_details

                display_names = {
                    'NRR': 'Net Revenue Retention',
                    'GRR': 'Gross Revenue Retention',
                    'TTFV': 'Time to First Value',
                    'product_adoption': 'Product Adoption',
                    'ticket_resolution_time': 'Support Resolution Time',
                    'expansion_rate': 'Expansion Rate',
                }

                # Default baselines for metrics
                default_baselines = {
                    'NRR': 105, 'GRR': 85, 'TTFV': 30,
                    'product_adoption': 65, 'ticket_resolution_time': 48,
                    'expansion_rate': 20,
                }

                # Format B: forward_metrics array
                if 'forward_metrics' in details:
                    for fm in details['forward_metrics']:
                        mid = fm.get('id', '')
                        impact = _safe_float(fm.get('impact', 0))
                        pct = _safe_float(fm.get('pct', 0))
                        baseline = default_baselines.get(mid, 0)
                        current = baseline * (1 + pct / 100.0) if baseline else 0

                        power_of_1_metrics.append({
                            'metric_id': mid,
                            'display_name': display_names.get(mid, mid),
                            'baseline': round(baseline, 2),
                            'current': round(current, 2),
                            'improvement_pct': round(pct, 1),
                            'dollar_impact': round(impact, 2),
                        })

                        if mid == 'NRR':
                            nrr_projection = round(current)
                        elif mid == 'GRR':
                            grr_projection = round(current)
                else:
                    # Format A: dict of {metric_id: {baseline, current, ...}}
                    for metric_id, detail in details.items():
                        if not isinstance(detail, dict):
                            continue
                        baseline = detail.get('baseline', 0)
                        current = detail.get('current', 0)
                        improvement_pct = 0
                        if baseline and baseline != 0:
                            improvement_pct = round(((current - baseline) / abs(baseline)) * 100, 1)
                        dollar_impact = detail.get('dollar_impact', 0)

                        power_of_1_metrics.append({
                            'metric_id': metric_id,
                            'display_name': display_names.get(metric_id, metric_id),
                            'baseline': round(baseline, 2) if baseline else 0,
                            'current': round(current, 2) if current else 0,
                            'improvement_pct': improvement_pct,
                            'dollar_impact': round(dollar_impact, 2) if dollar_impact else 0,
                        })

                    nrr_detail = details.get('NRR', {})
                    grr_detail = details.get('GRR', {})
                    if isinstance(nrr_detail, dict):
                        nrr_projection = round(nrr_detail.get('current', 100))
                    if isinstance(grr_detail, dict):
                        grr_projection = round(grr_detail.get('current', 85))

        # ── ROI scaling projections (non-linear) ──
        num_accounts = len(accounts)
        roi_scaling = {
            'current_accounts': num_accounts,
            'current_roi': roi_pct,
            'projections': [],
        }
        for target_accounts in [10, 50, 200]:
            if num_accounts > 0 and roi_pct > 0:
                # Non-linear scaling: ROI improves with log of account ratio
                scale_factor = 1 + math.log(max(target_accounts / max(num_accounts, 1), 1) + 1) * 0.8
                projected_roi = round(roi_pct * scale_factor)
            else:
                projected_roi = 0
            roi_scaling['projections'].append({
                'accounts': target_accounts,
                'roi': projected_roi,
            })

        # ── Pillar investment breakdown ──
        pillar_investments = []
        pillar_scores_map = _get_latest_pillar_scores(account_ids)

        # Aggregate pillar scores across accounts
        pillar_totals = defaultdict(lambda: {'total_score': 0, 'count': 0})
        for acct_id, pillars in pillar_scores_map.items():
            for pcode, pscore in pillars.items():
                pillar_totals[pcode]['total_score'] += pscore
                pillar_totals[pcode]['count'] += 1

        for pcode in ['P1', 'P2', 'P3', 'P4', 'P5']:
            pt = pillar_totals.get(pcode, {'total_score': 0, 'count': 0})
            avg_score = pt['total_score'] / pt['count'] if pt['count'] > 0 else 0

            # Estimate investment per pillar (proportional to playbook executions)
            pillar_exec_count = (
                PlaybookExecution.query
                .filter(
                    PlaybookExecution.customer_id == customer_id,
                    PlaybookExecution.playbook_id.ilike(f'%{pcode.lower()}%'),
                )
                .count()
            )
            pillar_investment = pillar_exec_count * 2000.0 if pillar_exec_count > 0 else cs_investment / 5.0
            pillar_impact = round(avg_score / 100.0 * total_arr * 0.02, 2) if avg_score > 0 else 0
            pillar_roi = round(pillar_impact / pillar_investment, 1) if pillar_investment > 0 else 0

            pillar_investments.append({
                'pillar': pcode,
                'name': DC2S_PILLAR_DISPLAY.get(pcode, pcode),
                'investment': round(pillar_investment, 2),
                'impact': pillar_impact,
                'roi': pillar_roi,
            })

        # ── Investment timeline (last 6 months) ──
        investment_timeline = []
        now = datetime.utcnow()
        for months_ago in range(5, -1, -1):
            month_date = now - timedelta(days=months_ago * 30)
            month_label = month_date.strftime('%Y-%m')

            # Count playbook executions in this month
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if month_date.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)

            exec_count = (
                PlaybookExecution.query
                .filter(
                    PlaybookExecution.customer_id == customer_id,
                    PlaybookExecution.started_at >= month_start,
                    PlaybookExecution.started_at < month_end,
                )
                .count()
            )

            month_investment = exec_count * 2000.0 if exec_count > 0 else 0
            # Estimate return as a multiple of investment based on ROI
            month_return = round(month_investment * (1 + roi_pct / 100.0), 2) if roi_pct > 0 else 0

            investment_timeline.append({
                'month': month_label,
                'investment': round(month_investment, 2),
                'return': month_return,
            })

        return jsonify({
            'status': 'success',
            'total_arr': round(total_arr, 2),
            'revenue_at_risk': revenue_data['revenue_at_risk'],
            'revenue_protected': revenue_data['revenue_protected'],
            'cs_investment': cs_investment,
            'roi_pct': roi_pct,
            'roi_investment': round(roi_investment, 2),
            'roi_impact': round(roi_impact, 2),
            'nrr_projection': nrr_projection,
            'grr_projection': grr_projection,
            'power_of_1_metrics': power_of_1_metrics,
            'roi_scaling': roi_scaling,
            'pillar_investments': pillar_investments,
            'investment_timeline': investment_timeline,
            'quarter_label': _current_quarter_label(),
            'last_updated': datetime.utcnow().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error in cfo_dashboard: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── 3. Revenue Timeline ─────────────────────────────────────────────────────

@executive_dashboard_api.route('/api/executive/revenue-timeline', methods=['GET'])
def revenue_timeline():
    """
    Per-account revenue timeline with signal, intervention, and outcome events
    derived from the context graph.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 400

        account_id = request.args.get('account_id', type=int)
        if not account_id:
            return jsonify({'error': 'account_id query parameter is required'}), 400

        # Verify account belongs to customer
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=customer_id,
        ).first()
        if not account:
            return jsonify({'error': 'Account not found or access denied'}), 404

        # Get all context nodes for this account, ordered by time
        nodes = (
            ContextNode.query
            .filter_by(account_id=account_id, customer_id=customer_id)
            .order_by(ContextNode.occurred_at.asc())
            .all()
        )

        events = []
        for node in nodes:
            if not node.occurred_at:
                continue

            month_label = node.occurred_at.strftime('%Y-%m')
            props = node.properties or {}

            # Map node_type to event type
            node_type = (node.node_type or '').upper()
            if node_type == 'SIGNAL':
                event_type = 'signal'
                severity = 'warning'
                if node.revenue_impact_type == 'at_risk':
                    severity = 'critical'
                elif node.revenue_impact_type == 'expansion':
                    severity = 'info'
            elif node_type == 'DECISION':
                event_type = 'intervention'
                severity = 'high'
            elif node_type == 'OUTCOME':
                event_type = 'outcome'
                severity = 'success' if node.revenue_impact_type in ('protected', 'expansion') else 'warning'
            else:
                event_type = 'info'
                severity = 'info'

            # Build event details
            details = props.get('details', '') or props.get('description', '') or ''
            action = props.get('action', '') or props.get('recommendation', '') or ''

            # Include revenue impact in action text if available
            if node.revenue_impact and not action:
                impact_val = _safe_float(node.revenue_impact)
                impact_type = node.revenue_impact_type or 'impact'
                action = f"${impact_val:,.0f} {impact_type}"

            events.append({
                'month': month_label,
                'type': event_type,
                'title': node.title or f"{node.node_type} event",
                'details': details,
                'action': action,
                'severity': severity,
            })

        return jsonify({
            'status': 'success',
            'account_id': account_id,
            'account_name': account.account_name,
            'arr': _safe_float(account.revenue),
            'events': events,
            'last_updated': datetime.utcnow().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error in revenue_timeline: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── 4. Executive Ask Anything ───────────────────────────────────────────────

PERSONA_PROMPTS = {
    'cro': {
        'role': 'Chief Revenue Officer',
        'focus': 'revenue protection, pipeline growth, churn prevention, expansion acceleration',
        'tone': 'Think like a CRO — every insight should connect to revenue impact. '
                'Lead with dollar amounts. Quantify risk in ARR terms. '
                'Recommend actions that protect or grow revenue.',
        'suggested': [
            'Which accounts have the highest churn risk and why?',
            'Where is our biggest expansion opportunity right now?',
            'What story arcs should I be worried about this quarter?',
            'How is our playbook investment translating to revenue protection?',
            'What would happen if we doubled down on our at-risk accounts?',
        ],
    },
    'cfo': {
        'role': 'Chief Financial Officer',
        'focus': 'CS investment ROI, cost efficiency, payback periods, budget allocation',
        'tone': 'Think like a CFO — every insight should connect to investment returns. '
                'Show ROI ratios, cost-per-account, payback periods. '
                'Compare actual vs projected. Flag inefficient spend.',
        'suggested': [
            'What is our CS investment returning per dollar?',
            'Which pillars have the worst ROI and should we reallocate?',
            'What is the cost per account for our CS programs?',
            'How does our ROI scale as we add more accounts?',
            'Give me the board-ready summary of our CS investment.',
        ],
    },
    'ceo': {
        'role': 'Chief Executive Officer',
        'focus': 'portfolio health, strategic risks, competitive positioning, board narrative',
        'tone': 'Think like a CEO — synthesize across the entire portfolio. '
                'Highlight the 2-3 things that matter most. '
                'Frame insights in terms of strategic risk and opportunity.',
        'suggested': [
            'Give me the 30-second board summary of customer health.',
            'What is our single biggest strategic risk right now?',
            'Are we winning or losing against competitors in our accounts?',
            'What would a 1% improvement across all metrics be worth?',
            'How should I think about our CS investment for next year?',
        ],
    },
}


@executive_dashboard_api.route('/api/executive/ask', methods=['POST'])
def executive_ask():
    """
    Executive Ask Anything — persona-aware RAG endpoint.
    Wraps the existing direct-rag query pipeline with executive context
    (CRO/CFO/CEO system prompts, context graph, revenue intelligence).
    """
    import time as _time
    start_time = _time.time()

    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        data = request.json
        if not data or 'query' not in data:
            return jsonify({'error': 'query is required'}), 400

        query_text = data['query']
        persona = data.get('persona', 'cro')  # cro | cfo | ceo
        conversation_history = data.get('conversation_history', [])

        # Validate persona
        persona_config = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS['cro'])

        # ── 1. Assemble executive context from DB ────────────────────────

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        account_ids = [a.account_id for a in accounts]
        account_lookup = {a.account_id: a for a in accounts}

        # Health scores (latest per account)
        health_rows = (
            db.session.query(HealthScore)
            .filter(HealthScore.account_id.in_(account_ids))
            .order_by(HealthScore.measurement_month.desc())
            .all()
        )
        latest_health = {}
        for h in health_rows:
            if h.account_id not in latest_health:
                latest_health[h.account_id] = h

        # Pillar scores (latest per account)
        pillar_rows = (
            db.session.query(PillarScore)
            .filter(PillarScore.account_id.in_(account_ids))
            .order_by(PillarScore.measurement_month.desc())
            .all()
        )
        pillars_by_account = {}
        for p in pillar_rows:
            if p.account_id not in pillars_by_account:
                pillars_by_account[p.account_id] = {}
            pc = p.pillar_code
            if pc not in pillars_by_account[p.account_id]:
                pillars_by_account[p.account_id][pc] = p.pillar_score

        # Context graph nodes (all types)
        ctx_nodes = (
            ContextNode.query
            .filter(ContextNode.customer_id == customer_id)
            .order_by(ContextNode.occurred_at.desc())
            .limit(200)
            .all()
        )

        # Context graph edges (for causal chains)
        node_ids = [n.node_id for n in ctx_nodes]
        ctx_edges = []
        if node_ids:
            ctx_edges = (
                ContextEdge.query
                .filter(
                    ContextEdge.from_node_id.in_(node_ids),
                    ContextEdge.to_node_id.in_(node_ids),
                )
                .limit(300)
                .all()
            )

        # ROI snapshot
        roi_snap = (
            ROISnapshot.query
            .filter_by(customer_id=customer_id)
            .order_by(ROISnapshot.created_at.desc())
            .first()
        )

        # Playbook executions (recent)
        recent_playbooks = (
            PlaybookExecution.query
            .filter(PlaybookExecution.account_id.in_(account_ids))
            .order_by(PlaybookExecution.started_at.desc())
            .limit(30)
            .all()
        )

        # ── 2. Build structured context string ───────────────────────────

        ctx_parts = []

        # Portfolio summary
        total_arr = sum(a.revenue or 0 for a in accounts)
        critical = [a for a in accounts if latest_health.get(a.account_id) and ht.classify(latest_health[a.account_id].health_score) == 'critical']
        at_risk = [a for a in accounts if latest_health.get(a.account_id) and ht.classify(latest_health[a.account_id].health_score) == 'at_risk']
        healthy = [a for a in accounts if latest_health.get(a.account_id) and ht.classify(latest_health[a.account_id].health_score) == 'healthy']

        ctx_parts.append(f"""=== PORTFOLIO SUMMARY ===
Total accounts: {len(accounts)} | Total ARR: ${total_arr:,.0f}
Critical: {len(critical)} accounts | At-Risk: {len(at_risk)} | Healthy: {len(healthy)}
Health thresholds: Critical (<{ht.at_risk_min()}), At-Risk ({ht.at_risk_min()}-{ht.healthy_min()-1}), Healthy (>={ht.healthy_min()})""")

        # Account details with pillar scores
        ctx_parts.append("\n=== ACCOUNT DETAILS ===")
        for acc in sorted(accounts, key=lambda a: latest_health.get(a.account_id, type('', (), {'health_score': 50})).health_score):
            hs = latest_health.get(acc.account_id)
            score = hs.health_score if hs else 50
            status = ht.classify(score)
            pillars = pillars_by_account.get(acc.account_id, {})
            pillar_str = ', '.join(f"{k}={v:.0f}" for k, v in pillars.items()) if pillars else 'no pillar data'
            ctx_parts.append(
                f"  {acc.account_name}: ARR=${acc.revenue or 0:,.0f}, Health={score:.0f} ({status}), "
                f"Pillars: [{pillar_str}]"
            )

        # Context graph: revenue intelligence
        revenue_at_risk = sum(n.revenue_impact or 0 for n in ctx_nodes if n.revenue_impact_type == 'at_risk')
        revenue_protected = sum(n.revenue_impact or 0 for n in ctx_nodes if n.revenue_impact_type == 'protected')
        revenue_expansion = sum(n.revenue_impact or 0 for n in ctx_nodes if n.revenue_impact_type == 'expansion')

        ctx_parts.append(f"""\n=== REVENUE INTELLIGENCE (Context Graph) ===
Revenue at Risk: ${revenue_at_risk:,.0f}
Revenue Protected: ${revenue_protected:,.0f}
Expansion Pipeline: ${revenue_expansion:,.0f}""")

        # Context graph: key signals, decisions, outcomes
        signals = [n for n in ctx_nodes if n.node_type == 'SIGNAL'][:20]
        decisions = [n for n in ctx_nodes if n.node_type == 'DECISION'][:10]
        outcomes = [n for n in ctx_nodes if n.node_type == 'OUTCOME'][:10]
        stakeholders = [n for n in ctx_nodes if n.node_type == 'STAKEHOLDER'][:10]

        if signals:
            ctx_parts.append("\n=== KEY SIGNALS ===")
            for s in signals:
                acct_name = account_lookup.get(s.account_id, type('', (), {'account_name': '?'})).account_name
                ctx_parts.append(
                    f"  [{acct_name}] {s.title or s.node_subtype}: "
                    f"confidence={s.confidence or 0:.0%}, "
                    f"revenue_impact=${s.revenue_impact or 0:,.0f} ({s.revenue_impact_type or 'n/a'})"
                )

        if decisions:
            ctx_parts.append("\n=== KEY DECISIONS ===")
            for d in decisions:
                acct_name = account_lookup.get(d.account_id, type('', (), {'account_name': '?'})).account_name
                ctx_parts.append(f"  [{acct_name}] {d.title or d.node_subtype}")

        if outcomes:
            ctx_parts.append("\n=== KEY OUTCOMES ===")
            for o in outcomes:
                acct_name = account_lookup.get(o.account_id, type('', (), {'account_name': '?'})).account_name
                ctx_parts.append(
                    f"  [{acct_name}] {o.title or o.node_subtype}: "
                    f"${o.revenue_impact or 0:,.0f} ({o.revenue_impact_type or 'n/a'})"
                )

        if stakeholders:
            ctx_parts.append("\n=== KEY STAKEHOLDERS ===")
            for sh in stakeholders:
                acct_name = account_lookup.get(sh.account_id, type('', (), {'account_name': '?'})).account_name
                props = sh.properties or {}
                ctx_parts.append(
                    f"  [{acct_name}] {sh.title or sh.node_subtype}: "
                    f"sentiment={props.get('sentiment', 'n/a')}, influence={props.get('influence', 'n/a')}"
                )

        # Causal chains (top 5 by revenue impact)
        if ctx_edges:
            node_map = {n.node_id: n for n in ctx_nodes}
            ctx_parts.append("\n=== CAUSAL CHAINS (cause → effect) ===")
            edge_with_impact = []
            for e in ctx_edges:
                to_node = node_map.get(e.to_node_id)
                impact = abs(to_node.revenue_impact or 0) if to_node else 0
                edge_with_impact.append((e, impact))
            edge_with_impact.sort(key=lambda x: x[1], reverse=True)
            for edge, impact in edge_with_impact[:10]:
                from_n = node_map.get(edge.from_node_id)
                to_n = node_map.get(edge.to_node_id)
                if from_n and to_n:
                    ctx_parts.append(
                        f"  {from_n.node_type}:{from_n.title or from_n.node_subtype} "
                        f"──{edge.edge_type}──> "
                        f"{to_n.node_type}:{to_n.title or to_n.node_subtype} "
                        f"(${impact:,.0f})"
                    )

        # ROI data
        if roi_snap:
            ctx_parts.append(f"""\n=== ROI DATA ===
Historical ROI: {roi_snap.historical_roi_pct:.0f}%
Investment: ${roi_snap.historical_investment:,.0f}
Impact: ${roi_snap.historical_impact:,.0f}
Forward ROI: {roi_snap.forward_roi_pct:.0f}%
Forward Impact: ${roi_snap.forward_impact:,.0f}""")

        # Recent playbook activity
        if recent_playbooks:
            ctx_parts.append("\n=== RECENT PLAYBOOK ACTIVITY ===")
            for pb in recent_playbooks[:15]:
                acct_name = account_lookup.get(pb.account_id, type('', (), {'account_name': '?'})).account_name
                ctx_parts.append(
                    f"  [{acct_name}] {pb.playbook_id}: status={pb.status}, "
                    f"started={pb.started_at.strftime('%Y-%m-%d') if pb.started_at else 'n/a'}"
                )

        context = '\n'.join(ctx_parts)

        # ── 3. Build conversation history ─────────────────────────────────

        conv_context = ""
        if conversation_history:
            conv_context = "\n=== CONVERSATION HISTORY ===\n"
            for i, msg in enumerate(conversation_history[-5:], 1):
                conv_context += f"Q{i}: {msg.get('query', '')}\n"
                conv_context += f"A{i}: {msg.get('response', '')[:300]}\n\n"

        # ── 4. Build persona-aware system prompt ──────────────────────────

        system_prompt = f"""You are the AI advisor to the {persona_config['role']} of a B2B technology company.
You are embedded in CS Pulse, a Revenue Intelligence platform that tracks customer health
across 5 pillars (P1-P5), 38 KPIs, and a context graph of causal signals.

YOUR ROLE: {persona_config['focus']}

STYLE: {persona_config['tone']}

CRITICAL RULES:
1. ONLY reference data provided in the context below. Never invent accounts or numbers.
2. Always quantify: use dollar amounts, percentages, account counts.
3. Connect cause to effect: use context graph chains to explain WHY things are happening.
4. Be actionable: every answer should end with a clear "do this next" recommendation.
5. Be concise: lead with the insight, support with 2-3 data points, close with action.
6. When discussing health scores: Critical (<{ht.at_risk_min()}), At-Risk ({ht.at_risk_min()}-{ht.healthy_min()-1}), Healthy (>={ht.healthy_min()}).

FORMAT:
- Use **bold** for key numbers and account names
- Use bullet points for lists
- End with a clear "**Recommended Action:**" line
- Keep total response under 200 words unless the question requires detailed analysis"""

        user_prompt = f"""{conv_context}

Current Question: {query_text}

=== AVAILABLE DATA ===
{context}

Answer as the {persona_config['role']}'s AI advisor. Be specific, quantified, and actionable."""

        # ── 5. Call OpenAI ────────────────────────────────────────────────

        import openai
        from openai_key_utils import get_openai_api_key

        api_key = get_openai_api_key(customer_id)
        if not api_key:
            return jsonify({
                'error': 'OpenAI API key not configured',
                'message': 'Please configure your OpenAI API key in Settings.',
            }), 400

        client = openai.OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model='gpt-4o',
            temperature=0.3,
            max_tokens=1200,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
        )
        response_text = completion.choices[0].message.content

        elapsed_ms = int((_time.time() - start_time) * 1000)

        return jsonify({
            'response': response_text,
            'persona': persona,
            'query': query_text,
            'elapsed_ms': elapsed_ms,
            'context_stats': {
                'accounts': len(accounts),
                'signals': len(signals),
                'decisions': len(decisions),
                'outcomes': len(outcomes),
                'stakeholders': len(stakeholders),
                'causal_edges': len(ctx_edges),
                'total_arr': total_arr,
            },
            'suggested_followups': _generate_followups(query_text, persona_config),
        })

    except Exception as e:
        logger.error(f"Error in executive_ask: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@executive_dashboard_api.route('/api/executive/ask/suggested', methods=['GET'])
def executive_suggested_questions():
    """Return persona-specific suggested questions."""
    persona = request.args.get('persona', 'cro')
    config = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS['cro'])
    return jsonify({
        'persona': persona,
        'role': config['role'],
        'suggested': config['suggested'],
    })


def _generate_followups(query: str, persona_config: dict) -> list:
    """Generate contextual follow-up suggestions based on the query."""
    q_lower = query.lower()
    followups = []

    if any(w in q_lower for w in ['risk', 'churn', 'critical']):
        followups.extend([
            'What playbooks should we activate for these accounts?',
            'How much revenue can we protect if we act this quarter?',
        ])
    elif any(w in q_lower for w in ['expand', 'growth', 'upsell']):
        followups.extend([
            'Which expansion accounts have the highest probability of closing?',
            'What is the expected NRR impact from these expansions?',
        ])
    elif any(w in q_lower for w in ['roi', 'invest', 'cost', 'budget']):
        followups.extend([
            'How does our ROI compare if we add 50 more accounts?',
            'Which pillar gives us the best return per dollar invested?',
        ])
    elif any(w in q_lower for w in ['board', 'summary', 'overview']):
        followups.extend([
            'What are the top 3 risks I should flag to the board?',
            'How should I frame our CS investment story?',
        ])
    else:
        followups.extend(persona_config['suggested'][:2])

    return followups[:3]
