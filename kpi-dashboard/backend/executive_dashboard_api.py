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

try:
    from utils.llm_budget_controller import can_call as _budget_can_call, record_usage as _budget_record
except Exception:
    _budget_can_call = None
    _budget_record = None

from models import (
    Account, HealthScore, PillarScore, KPIScore,
    ContextNode, ContextEdge, PlaybookExecutionV2, ROISnapshot,
)
import utils.health_thresholds as ht
from utils.context_graph import aggregate_revenue_across_accounts, aggregate_revenue_with_provenance
from utils.vertical_registry import get_vertical_for_customer, get_pillars
from utils import value_provenance as _vp
from power_of_1_model import dedupe_portfolio_dollar_impact

logger = logging.getLogger(__name__)

executive_dashboard_api = Blueprint('executive_dashboard_api', __name__)

# Per-vertical CFO pillar-investment breakdown config (Aug 21 2026
# vertical-coupling audit, bug #2). Was hardcoded to dc2_s's 5 pillars —
# every other vertical (datacenter_v1 included, which has 6 real pillars)
# silently got dc2_s's names, and datacenter_v1's 6th pillar's real-dollar
# data was dropped from the CFO report entirely, not even mislabeled.
#
# 'metric_groups': pillar_code -> list of Power-of-1 metric_ids whose
#   dollar_impact rolls up into that pillar's investment-breakdown tile.
#   An empty list means "no direct Po1 metric for this pillar" — falls
#   through to weight-based allocation (existing behavior, unchanged).
# 'weights': pillar_code -> investment-allocation weight, must sum to 1.0.
#
# dc2_s's values are UNCHANGED from the original hardcode — this is a
# regression-safety requirement, not a design choice.
CFO_PILLAR_INVESTMENT_CONFIG = {
    'dc2_s': {
        'metric_groups': {
            'P1': ['TTFV', 'product_adoption'],
            'P2': ['ticket_resolution_time'],
            'P3': ['NRR', 'GRR'],
            'P4': [],  # partner — no direct Po1 metric
            'P5': ['expansion_rate'],
        },
        'weights': {'P1': 0.25, 'P2': 0.15, 'P3': 0.30, 'P4': 0.10, 'P5': 0.20},
    },
    'saas_premium': {
        'metric_groups': {
            'P1': ['product_adoption'],       # Product Adoption & Usage
            'P2': ['TTFV'],                    # Customer Engagement
            'P3': ['ticket_resolution_time'],  # Customer Sentiment & Support
            'P4': ['GRR'],                     # Partner & Ecosystem Health
            'P5': ['NRR', 'expansion_rate'],   # Revenue & Growth
        },
        'weights': {'P1': 0.25, 'P2': 0.15, 'P3': 0.30, 'P4': 0.10, 'P5': 0.20},
    },
    'datacenter_v1': {
        'metric_groups': {
            'P1': ['NRR'],                     # Revenue & Unit Economics
            'P2': ['product_adoption'],        # Fleet Utilization & Goodput
            'P3': ['ticket_resolution_time'],  # Reliability & SLA Delivery
            'P4': ['GRR'],                     # Power & Facility
            'P5': ['expansion_rate'],          # Commercial & Expansion
            'P6': ['TTFV'],                    # Provisioning Velocity
        },
        'weights': {'P1': 0.25, 'P2': 0.15, 'P3': 0.20, 'P4': 0.10, 'P5': 0.15, 'P6': 0.15},
    },
}


def _cfo_pillar_investment_config(vertical, pillar_codes):
    """Return (metric_groups, weights) for a vertical's CFO pillar breakdown.

    Falls back to an even weight split across the vertical's own real
    pillar codes (from vertical_registry, not a guess) with no metric
    groups, for any vertical without a curated entry above — never
    borrows another vertical's config.
    """
    cfg = CFO_PILLAR_INVESTMENT_CONFIG.get(vertical)
    if cfg:
        return cfg['metric_groups'], cfg['weights']
    n = max(len(pillar_codes), 1)
    even_weight = round(1.0 / n, 4)
    return {}, {pcode: even_weight for pcode in pillar_codes}

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
    """Aggregate revenue metrics across all accounts from context graph nodes.

    Delegates to the shared utils.context_graph.aggregate_revenue_across_accounts().
    """
    return aggregate_revenue_across_accounts(customer_id, account_ids)


def _revenue_bundle_from_context_graph(customer_id, account_ids):
    """Totals + trace samples for dashboard tiles (MVP audit trail)."""
    return aggregate_revenue_with_provenance(customer_id, account_ids)


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

    # Build account ARR lookup for revenue attribution
    account_arr = {}
    for acct in Account.query.filter(Account.account_id.in_(account_ids)).all():
        account_arr[acct.account_id] = _safe_float(acct.revenue)

    # Group signals by subtype
    subtype_accounts = defaultdict(set)
    subtype_dates = defaultdict(list)

    for node in signal_nodes:
        subtype = (node.node_subtype or 'unknown').lower()
        subtype_accounts[subtype].add(node.account_id)
        if node.occurred_at:
            subtype_dates[subtype].append(node.occurred_at)

    arcs = []
    for arc_key, arc_def in STORY_ARC_PATTERNS.items():
        matching_accounts = set()
        all_dates = []

        for st in arc_def['signal_subtypes']:
            matching_accounts |= subtype_accounts.get(st, set())
            all_dates.extend(subtype_dates.get(st, []))

        # Revenue = ARR of affected accounts (not signal.revenue_impact which is null)
        total_revenue = sum(account_arr.get(aid, 0) for aid in matching_accounts)

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
    """Total CS investment from PlaybookExecutionV2 (actual playbook costs)."""
    executions = PlaybookExecutionV2.query.filter_by(customer_id=customer_id).all()
    return round(sum(_safe_float(ex.total_cost) for ex in executions), 2)


def _get_po1_benchmark_investment(total_arr):
    """Return Power-of-1 benchmark investment scaled to actual ARR.

    Loads from config/power_of_1_economics.json.  At the $10M ARR baseline
    the total investment across all 6 metrics is ~$247K.  We scale linearly
    by actual_arr / 10M so a $57M portfolio sees ~$1.4M.
    """
    import json, os
    config_path = os.path.join(
        os.path.dirname(__file__), 'config', 'power_of_1_economics.json'
    )
    try:
        with open(config_path) as f:
            data = json.load(f)
        arr_base = data.get('_arr_base', 10_000_000)
        arr_scale = total_arr / arr_base if arr_base > 0 else 1
        total_inv = sum(
            m.get('total_investment', 0) for m in data.get('metrics', {}).values()
        )
        return round(total_inv * arr_scale, 2)
    except Exception:
        # Fallback: 0.5% of ARR as rough CS investment estimate
        return round(total_arr * 0.005, 2)


def _get_po1_benchmark_metrics(total_arr):
    """Return Power-of-1 metrics as estimated baseline (no DB needed).

    Used when no ROISnapshot exists to populate the CFO Power-of-1 table
    with benchmark values and estimated dollar impacts.
    """
    import json, os
    config_path = os.path.join(
        os.path.dirname(__file__), 'config', 'power_of_1_economics.json'
    )
    try:
        with open(config_path) as f:
            data = json.load(f)
        arr_base = data.get('_arr_base', 10_000_000)
        arr_scale = total_arr / arr_base if arr_base > 0 else 1
        metrics = []
        for mid, m in data.get('metrics', {}).items():
            impact = round(m.get('annual_impact_per_pct', 0) * arr_scale, 2)
            baseline = m.get('baseline', 0)
            direction = m.get('direction', 'higher_is_better')
            # Show projected 1% improvement as the "current" value
            if direction == 'lower_is_better':
                current = round(baseline * 0.99, 1)  # 1% lower is better
            else:
                current = round(baseline * 1.01, 1)  # 1% higher is better
            metrics.append({
                'metric_id': mid,
                'display_name': m.get('display_name', mid),
                'baseline': baseline,
                'current': current,
                'improvement_pct': 1.0,
                'dollar_impact': impact,
                'estimated': True,
                # Deck benchmarks ARR-scaled — no customer measurement behind
                # any of these values. Explicit tier alongside the legacy
                # boolean so the frontend badge doesn't have to infer it.
                'data_source': _vp.BENCHMARK,
            })
        return metrics
    except Exception:
        return []


def _get_roi_snapshot(customer_id):
    """Get the latest ROI snapshot for the customer."""
    snapshot = (
        ROISnapshot.query
        .filter_by(customer_id=customer_id)
        .order_by(ROISnapshot.snapshot_date.desc(), ROISnapshot.created_at.desc())
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


def _compute_historical_actuals(customer_id: int, total_arr: float):
    """Row A NRR lens — raw OUTCOME aggregates (backward TTM)."""
    try:
        from sqlalchemy import text as _sql_text
        from extensions import db as _db

        ha_rows = _db.session.execute(_sql_text(
            """
            SELECT
                SUM(CASE WHEN node_subtype = 'churn_lost'      THEN COALESCE(revenue_impact, 0) ELSE 0 END) AS arr_churned,
                SUM(CASE WHEN node_subtype = 'expansion_closed' THEN COALESCE(revenue_impact, 0) ELSE 0 END) AS arr_expanded,
                SUM(CASE WHEN node_subtype = 'contraction'      THEN COALESCE(revenue_impact, 0) ELSE 0 END) AS arr_contracted,
                COUNT(*) FILTER (WHERE node_subtype = 'churn_lost')       AS n_churned,
                COUNT(*) FILTER (WHERE node_subtype = 'expansion_closed') AS n_expanded,
                COUNT(*) FILTER (WHERE node_subtype = 'contraction')      AS n_contracted
            FROM context_nodes
            WHERE customer_id = :cust
              AND node_type = 'OUTCOME'
              AND node_subtype IN ('churn_lost', 'expansion_closed', 'contraction')
            """
        ), {'cust': customer_id}).fetchone()

        if not ha_rows:
            return None

        arr_churned = float(ha_rows[0] or 0)
        arr_expanded = float(ha_rows[1] or 0)
        arr_contracted = float(ha_rows[2] or 0)
        starting_arr_ttm = total_arr + abs(arr_churned)
        if starting_arr_ttm <= 0:
            return None

        historical_nrr_ttm = (
            (starting_arr_ttm + arr_expanded + arr_churned + arr_contracted)
            / starting_arr_ttm
        ) * 100

        return {
            'historical_nrr_pct_ttm': round(historical_nrr_ttm, 2),
            'arr_churned': round(arr_churned, 0),
            'arr_expanded': round(arr_expanded, 0),
            'arr_contracted': round(arr_contracted, 0),
            'starting_arr_ttm': round(starting_arr_ttm, 0),
            'n_churned_accounts': int(ha_rows[3] or 0),
            'n_expansion_events': int(ha_rows[4] or 0),
            'n_contraction_events': int(ha_rows[5] or 0),
            'lens': 'historical_actuals',
            'engine': 'raw_outcomes',
            'time_direction': 'backward',
            'source': 'context graph OUTCOME nodes (uploaded outcomes · not GL-reconciled)',
        }
    except Exception as e:
        logger.warning(f"historical_actuals computation failed: {e}")
        return None


def _compute_predictor_v3_portfolio_nrr(accounts) -> dict | None:
    """Forward 12mo NRR lens — ARR-weighted Predictor v3 (matches CFO tile)."""
    try:
        from predictor.inference import predict_for_account_id
        from models import PredictorCalibration

        v3_rows = []
        v3_failed = 0
        for a in accounts:
            try:
                pred = predict_for_account_id(account_id=a.account_id, horizon='12mo')
                v3_rows.append({
                    'account_id': a.account_id,
                    'account_name': a.account_name,
                    'arr': float(a.revenue or 0),
                    'nrr_point': pred['expected_nrr']['point'],
                    'method': pred.get('prediction_method', '?'),
                })
            except Exception:
                v3_failed += 1

        if not v3_rows:
            return None

        v3_total_arr = sum(r['arr'] for r in v3_rows)
        arr_weighted = (
            sum(r['arr'] * r['nrr_point'] for r in v3_rows) / v3_total_arr
            if v3_total_arr > 0 else 0
        )
        simple_avg = sum(r['nrr_point'] for r in v3_rows) / len(v3_rows)
        method_counts: dict[str, int] = {}
        for r in v3_rows:
            method_counts[r['method']] = method_counts.get(r['method'], 0) + 1

        latest_cal = (
            PredictorCalibration.query
            .filter(PredictorCalibration.is_active == True)  # noqa: E712
            .order_by(PredictorCalibration.created_at.desc())
            .first()
        )

        return {
            'arr_weighted_nrr_pct': round(arr_weighted * 100, 2),
            'simple_avg_nrr_pct': round(simple_avg * 100, 2),
            'horizon': '12mo',
            'account_count': len(v3_rows),
            'active_account_count': sum(1 for r in v3_rows if r['arr'] > 0),
            'failed_count': v3_failed,
            'prediction_method_counts': method_counts,
            'last_calibration_id': latest_cal.calibration_id if latest_cal else None,
            'last_calibration_at': (
                latest_cal.created_at.isoformat() if latest_cal else None
            ),
            'lens': 'point_forecast_ntm',
            'engine': 'predictor_v3',
            'time_direction': 'forward',
            'method_note': (
                'ARR-weighted average of per-account expected_nrr. '
                'Excludes $0-ARR accounts from weight (typically '
                'already-churned). simple_avg counts all equally. '
                'Differs from wizard_b_nrr by design — forward vs '
                'backward, point vs counterfactual.'
            ),
        }
    except Exception as e:
        logger.warning(f"predictor_v3_portfolio_nrr computation failed: {e}")
        return None


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

        # Get signal counts per account from context graph
        signal_counts = {}
        try:
            from sqlalchemy import func as sa_func
            signal_rows = (
                ContextNode.query
                .filter(
                    ContextNode.customer_id == customer_id,
                    ContextNode.account_id.in_(account_ids),
                    ContextNode.node_type == 'SIGNAL',
                )
                .with_entities(ContextNode.account_id, sa_func.count(ContextNode.node_id))
                .group_by(ContextNode.account_id)
                .all()
            )
            signal_counts = {row[0]: row[1] for row in signal_rows}
        except Exception:
            pass

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
                'signal_count': signal_counts.get(acct.account_id, 0),
                # CRO-5: surface CSM owner on at-risk table so CRO can route escalations
                # without drilling into get_crm_account_data per account.
                # `assigned_csm` lives in Account.profile_metadata (JSON), NOT as a top-level
                # column — same convention as account_snapshot_api.py:381, cs_pulse_admin.py:101,
                # and scripts/verify_profile_data.py:65. PR #23 mis-attributed it as a column,
                # crashing /api/executive/cro-dashboard with AttributeError. Fix-forward #28.
                'assigned_csm': (acct.profile_metadata or {}).get('assigned_csm'),
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

        # ── Revenue from context graph (with trace samples for UI drill-down) ──
        revenue_bundle = _revenue_bundle_from_context_graph(customer_id, account_ids)
        revenue_data = revenue_bundle
        context_graph_provenance = revenue_bundle.get('provenance')

        # ── Story arcs ──
        story_arcs = _build_story_arcs(customer_id, account_ids)

        # ── Early warning days ──
        early_warning_days = _calculate_early_warning_days(customer_id, account_ids)

        # ── Accounts recovered & expansion candidates ──
        recovered = _get_accounts_recovered(customer_id, account_ids)
        expansion_candidates = _get_expansion_candidates(customer_id, account_ids)

        # ── PROOF DATA: actual playbook economics (same as CFO) ──
        from utils.playbook_lifecycle import (
            health_to_annual_churn_prob,
            health_to_annual_expansion_prob,
            INTERVENTION_ATTRIBUTION,
            EXPANSION_ATTRIBUTION,
        )
        cro_proof = {'total_cost': 0, 'revenue_protected': 0, 'revenue_expanded': 0,
                     'realized_roi': 0, 'executions_total': 0, 'executions_resolved': 0}
        try:
            pb_execs = PlaybookExecutionV2.query.filter_by(customer_id=customer_id).all()
            cro_proof['executions_total'] = len(pb_execs)
            for ex in pb_execs:
                cro_proof['total_cost'] += float(ex.total_cost or 0)
                cro_proof['revenue_protected'] += float(ex.revenue_protected or 0)
                cro_proof['revenue_expanded'] += float(ex.revenue_expanded or 0)
                if ex.outcome == 'resolved':
                    cro_proof['executions_resolved'] += 1
            total_value = cro_proof['revenue_protected'] + cro_proof['revenue_expanded']
            cro_proof['realized_roi'] = round(total_value / cro_proof['total_cost'], 1) if cro_proof['total_cost'] > 0 else 0
            for k in ['total_cost', 'revenue_protected', 'revenue_expanded']:
                cro_proof[k] = round(cro_proof[k], 0)
        except Exception:
            pass
        has_proof = cro_proof['total_cost'] > 0 or cro_proof['revenue_protected'] > 0

        # ── WIZARD B NRR (backward counterfactual — Realized NRR TTM) ──
        cro_wizard_b_nrr = None
        try:
            from wizards.wizard_b_pattern_db import run_wizard_b
            wb_result = run_wizard_b(customer_id)
            forecast = (wb_result.get('nrr_intelligence') or {}).get('forecast') or {}
            if forecast.get('current_nrr_pct'):
                cro_wizard_b_nrr = {
                    'without_cs_pulse_nrr_pct': forecast.get('without_cs_pulse_nrr_pct', 100),
                    'with_cs_pulse_nrr_pct': forecast.get('current_nrr_pct', 100),
                    'delta_pct': forecast.get('cs_pulse_delta_pct', 0),
                    'arr_protected': forecast.get('cs_pulse_arr_protected', 0),
                    'accounts_saved': forecast.get('cs_pulse_accounts_saved', 0),
                    'with_interventions_nrr_pct': forecast.get('with_interventions_nrr_pct', 100),
                    'lens': 'counterfactual_ttm',
                    'engine': 'wizard_b',
                    'time_direction': 'backward',
                }
        except Exception:
            pass

        historical_actuals = _compute_historical_actuals(customer_id, total_revenue)
        predictor_v3_portfolio_nrr = _compute_predictor_v3_portfolio_nrr(accounts)

        # ── ROI from actual playbook data (no Power-of-1 fallback for CRO) ──
        playbook_roi_pct = cro_proof['realized_roi'] if has_proof else 0
        is_estimated_roi = not has_proof

        # ── NRR headline: Predictor v3 forward forecast (matches CFO tile) ──
        if (
            predictor_v3_portfolio_nrr
            and predictor_v3_portfolio_nrr.get('arr_weighted_nrr_pct') is not None
        ):
            nrr_projection = round(predictor_v3_portfolio_nrr['arr_weighted_nrr_pct'], 1)
            nrr_projection_lens = 'predictor_v3'
        elif cro_wizard_b_nrr:
            nrr_projection = round(cro_wizard_b_nrr['with_cs_pulse_nrr_pct'], 1)
            nrr_projection_lens = 'wizard_b'
        elif avg_health >= 70:
            nrr_projection = round(100 + (avg_health - 70) * 0.33)
            nrr_projection_lens = 'health_heuristic'
        elif avg_health >= 40:
            nrr_projection = round(90 + (avg_health - 40) * 0.33)
            nrr_projection_lens = 'health_heuristic'
        else:
            nrr_projection = round(85 + avg_health * 0.125)
            nrr_projection_lens = 'health_heuristic'
        nrr_change = round(nrr_projection - 100, 1)

        # ── Highest risk accounts (only at-risk/critical, sorted by lowest health) ──
        pillar_scores_map = _get_latest_pillar_scores(account_ids)
        account_details.sort(key=lambda a: a['health_score'])
        highest_risk = []
        for ad in account_details:
            if ad['health_score'] >= healthy_min_val:
                continue  # Skip healthy accounts — only show truly at-risk
            pillars = pillar_scores_map.get(ad['account_id'], {})
            ad['pillar_scores'] = pillars
            highest_risk.append(ad)

        # ARR Exposure = total ARR sitting in at-risk/critical accounts
        arr_exposure = sum(
            ad['revenue'] for ad in account_details
            if ad['health_score'] < healthy_min_val
        )

        # ── NRR Forecast: dual NRR + trajectory + waterfall ──
        # "Current NRR" = health-weighted baseline (no intervention)
        # "Projected NRR" = if playbooks execute on at-risk accounts
        nrr_current = nrr_projection  # already computed above from health correlation
        nrr_with_intervention = nrr_current
        nrr_arr_protected = 0
        nrr_trajectory = {}
        nrr_waterfall_summary = {}
        renewals_at_risk = []

        try:
            ATTRIBUTION_FACTOR = 0.5
            waterfall_accounts = []
            total_exposure_wf = 0
            total_expected_loss = 0
            total_gross_saved = 0
            total_attributed = 0
            total_cost = 0

            for acct in accounts:
                arr = float(acct.revenue or 0)
                if arr <= 0:
                    continue
                acct_scores = HealthScore.query.filter_by(
                    account_id=acct.account_id
                ).order_by(HealthScore.measurement_month.asc()).all()
                if not acct_scores:
                    continue
                health_now = float(acct_scores[-1].health_score)
                if health_now >= healthy_min_val:
                    continue  # skip healthy — only model at-risk/critical

                # Project health at T+90 assuming partial trend continuation
                if len(acct_scores) >= 2:
                    delta = float(acct_scores[-1].health_score) - float(acct_scores[0].health_score)
                    projected = health_now + delta * 0.5
                else:
                    projected = health_now - 3

                churn_now = health_to_annual_churn_prob(health_now) * 100
                churn_proj = health_to_annual_churn_prob(max(projected, 0)) * 100
                expected_loss = arr * churn_now / 100
                gross_saved = max(0, expected_loss - arr * churn_proj / 100)
                attributed = gross_saved * ATTRIBUTION_FACTOR
                pb_cost = 4560  # avg playbook cost from cost bridge

                total_exposure_wf += arr
                total_expected_loss += expected_loss
                total_gross_saved += gross_saved
                total_attributed += attributed
                total_cost += pb_cost

                waterfall_accounts.append({
                    'account_name': acct.account_name,
                    'arr': arr,
                    'health_now': round(health_now, 1),
                    'churn_prob_pct': round(churn_now, 1),
                    'expected_loss': round(expected_loss, 0),
                    'attributed_save': round(attributed, 0),
                })

            waterfall_accounts.sort(key=lambda x: x['expected_loss'], reverse=True)

            if total_revenue > 0 and total_attributed > 0:
                nrr_lift_pct = (total_attributed / total_revenue) * 100
                nrr_with_intervention = round(nrr_current + nrr_lift_pct, 1)
            nrr_arr_protected = round(total_attributed, 0)

            nrr_waterfall_summary = {
                'total_exposure': round(total_exposure_wf, 0),
                'expected_loss': round(total_expected_loss, 0),
                'gross_saved': round(total_gross_saved, 0),
                'attributed_save': round(total_attributed, 0),
                'intervention_cost': round(total_cost, 0),
                'roi_x': round(total_attributed / total_cost, 1) if total_cost > 0 else 0,
                'accounts': waterfall_accounts[:5],  # top 5
            }

            # T+30/60/90 trajectory
            for horizon_days, label in [(30, 't30'), (60, 't60'), (90, 't90')]:
                crossings = []
                for acct in accounts:
                    acct_scores = HealthScore.query.filter_by(
                        account_id=acct.account_id
                    ).order_by(HealthScore.measurement_month.asc()).all()
                    if len(acct_scores) < 2:
                        continue
                    delta_pm = (float(acct_scores[-1].health_score) - float(acct_scores[0].health_score))
                    months_span = max(1, len(acct_scores) - 1)
                    proj = float(acct_scores[-1].health_score) + (delta_pm / months_span) * (horizon_days / 30)
                    curr_st = ht.classify(float(acct_scores[-1].health_score))
                    proj_st = ht.classify(proj)
                    if curr_st != proj_st:
                        crossings.append({
                            'account_name': acct.account_name,
                            'crossing': f"{curr_st}_to_{proj_st}",
                        })
                nrr_at_horizon = nrr_current - (horizon_days / 30) * 0.6
                nrr_trajectory[label] = {
                    'nrr_pct': round(nrr_at_horizon, 1),
                    'crossings': crossings,
                }

            # Renewals at risk (within 90 days)
            for acct in accounts:
                meta = acct.profile_metadata if isinstance(acct.profile_metadata, dict) else {}
                rd = meta.get('renewal_date') or meta.get('contract_end')
                if rd:
                    try:
                        rdate = datetime.strptime(str(rd)[:10], '%Y-%m-%d').date()
                        days_until = (rdate - datetime.utcnow().date()).days
                        if 0 <= days_until <= 90:
                            hs_obj = latest_health.get(acct.account_id)
                            h = float(hs_obj.health_score) if hs_obj and hs_obj.health_score else 0
                            renewals_at_risk.append({
                                'account_name': acct.account_name,
                                'arr': float(acct.revenue or 0),
                                'days_until': days_until,
                                'health_score': round(h, 1),
                            })
                    except (ValueError, TypeError):
                        pass
            renewals_at_risk.sort(key=lambda x: x['days_until'])

        except Exception as nrr_err:
            logger.warning(f"NRR forecast enrichment failed (non-fatal): {nrr_err}")

        period_param = (request.args.get('period') or '').strip().upper() or None
        period_meta = {
            'requested_period': period_param,
            'anchor_quarter_label': _current_quarter_label(),
            'filter_mode': 'client_side',
            'note': (
                'CRO period tabs (Q3/Q4/TTM) filter at-risk $ and accounts in the UI; '
                'pass ?period=Q3|Q4|TTM to echo the tab. Protected/expansion $ stay point-in-time.'
            ),
        }

        return jsonify({
            'status': 'success',
            'period': period_param,
            'period_meta': period_meta,
            # Revenue Intelligence — Confirmed Risk (causal, from Context Graph)
            'revenue_at_risk': revenue_data['revenue_at_risk'],
            'revenue_protected': revenue_data['revenue_protected'],
            'expansion_pipeline': revenue_data['expansion_pipeline'],
            'revenue_risk_type': 'confirmed',
            'revenue_risk_label': 'Confirmed Risk (Context Graph)',
            'context_graph_provenance': context_graph_provenance,
            # ARR Exposure — surface-level risk (health-score based)
            'arr_exposure': round(arr_exposure, 2),
            'arr_exposure_label': 'Exposure (ARR in at-risk accounts)',
            # Accounts
            'accounts_at_risk_count': at_risk_count,
            'accounts_recovered_count': recovered,
            'expansion_candidates_count': expansion_candidates,
            # Health scores
            'avg_health_score': avg_health,
            'avg_health_score_simple': avg_health_simple,
            'health_avg_method': 'revenue_weighted',
            'health_avg_method_label': 'Revenue-weighted average',
            'health_score_change': health_change,
            'total_accounts': len(accounts),
            'total_arr': total_revenue,
            'early_warning_days': early_warning_days,
            'playbook_roi_pct': playbook_roi_pct,
            'playbook_roi_estimated': is_estimated_roi,
            'playbook_roi_label': 'Actual (playbook executions)' if has_proof else 'Estimated',
            'cs_investment': cro_proof['total_cost'],
            'proof_data': cro_proof,
            'wizard_b_nrr': cro_wizard_b_nrr,
            'historical_actuals': historical_actuals,
            'predictor_v3_portfolio_nrr': predictor_v3_portfolio_nrr,
            'nrr_projection': nrr_projection,
            'nrr_projection_lens': nrr_projection_lens,
            'nrr_change': nrr_change,
            # Health-model baseline for waterfall / trajectory (not the headline forecast)
            'nrr_current': nrr_current,
            'nrr_with_intervention': nrr_with_intervention,
            'nrr_arr_protected': nrr_arr_protected,
            'nrr_trajectory': nrr_trajectory,
            'nrr_waterfall_summary': nrr_waterfall_summary,
            'renewals_at_risk': renewals_at_risk,
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
        vertical = get_vertical_for_customer(customer_id)

        # ── Total ARR ──
        total_arr = sum(_safe_float(a.revenue) for a in accounts)

        # ── Revenue from context graph (with trace samples for UI drill-down) ──
        revenue_bundle = _revenue_bundle_from_context_graph(customer_id, account_ids)
        revenue_data = revenue_bundle
        context_graph_provenance = revenue_bundle.get('provenance')

        # ── CS Investment ──
        cs_investment = _get_playbook_investment(customer_id)

        # ── Power-of-1 benchmark fallback when no playbook data ──
        estimated_investment = 0
        if cs_investment == 0 and total_arr > 0:
            estimated_investment = _get_po1_benchmark_investment(total_arr)

        # ── ROI from snapshot ──
        roi_snap = _get_roi_snapshot(customer_id)
        roi_pct = 0
        roi_impact = 0.0
        roi_investment = cs_investment or estimated_investment
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
                            # dollar_impact is from a real ROI snapshot
                            # (derived), but baseline/current here are
                            # SYNTHESIZED from the default_baselines
                            # constants above — the card's headline
                            # "baseline → current" is default-tier, and
                            # the blend carries the weaker input.
                            'data_source': _vp.most_conservative([_vp.DERIVED, _vp.DEFAULT]),
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
                            # All values from a persisted ROI snapshot of
                            # computed-from-real-data results.
                            'data_source': _vp.DERIVED,
                        })

                    nrr_detail = details.get('NRR', {})
                    grr_detail = details.get('GRR', {})
                    if isinstance(nrr_detail, dict):
                        nrr_projection = round(nrr_detail.get('current', 100))
                    if isinstance(grr_detail, dict):
                        grr_projection = round(grr_detail.get('current', 85))

        # ── Power-of-1 benchmark fallback when no ROI snapshot ──
        if not power_of_1_metrics and total_arr > 0:
            power_of_1_metrics = _get_po1_benchmark_metrics(total_arr)
            if estimated_investment > 0:
                roi_impact = dedupe_portfolio_dollar_impact(power_of_1_metrics)
            for m in power_of_1_metrics:
                if m['metric_id'] == 'NRR':
                    nrr_projection = round(m['current'])
                elif m['metric_id'] == 'GRR':
                    grr_projection = round(m['current'])

        # ── Pre-compute effective investment (needed by pillar breakdown + efficiency) ──
        is_estimated = cs_investment == 0 and estimated_investment > 0
        effective_investment = cs_investment or estimated_investment

        # ── Phase 3: modeled ROI % + scaling (recompute when snapshot ROI is 0) ──
        from utils.cfo_dashboard_helpers import (
            build_cfo_efficiency_metrics,
            build_roi_scaling,
            resolve_cfo_roi_pct,
        )

        roi_pct, roi_multiple, roi_is_modeled = resolve_cfo_roi_pct(
            roi_snap,
            power_of_1_metrics,
            effective_investment,
            roi_impact=roi_impact,
        )
        if roi_impact <= 0 and power_of_1_metrics:
            roi_impact = dedupe_portfolio_dollar_impact(power_of_1_metrics)

        num_accounts = len(accounts)
        roi_scaling = build_roi_scaling(
            roi_pct, num_accounts, is_modeled=roi_is_modeled or is_estimated,
        )
        roi_scaling['roi_multiple'] = roi_multiple

        # ── Pillar investment breakdown (from Power-of-1 metrics) ──
        # Vertical-aware: was hardcoded to dc2_s's 5 pillars (bug #2, Aug 21
        # 2026 vertical-coupling audit) — every other vertical got dc2_s's
        # pillar names, and any vertical with more than 5 pillars (e.g.
        # datacenter_v1's 6) silently lost its extra pillar's $ entirely.
        vertical_pillars = get_pillars(vertical)
        pillar_codes = sorted(vertical_pillars.keys())
        _pillar_metric_map, pillar_weights = _cfo_pillar_investment_config(vertical, pillar_codes)

        # Item 22: allocate the single canonical value/spend by pillar weight —
        # no rival second value source (see _build_pillar_investments).
        pillar_investments = _build_pillar_investments(
            pillar_codes, pillar_weights, vertical_pillars,
            roi_impact, effective_investment,
        )

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

            month_execs = (
                PlaybookExecutionV2.query
                .filter(
                    PlaybookExecutionV2.customer_id == customer_id,
                    PlaybookExecutionV2.triggered_at >= month_start,
                    PlaybookExecutionV2.triggered_at < month_end,
                )
                .all()
            )

            month_investment = sum(_safe_float(ex.total_cost) for ex in month_execs)
            month_return = sum(_safe_float(ex.revenue_protected) + _safe_float(ex.revenue_expanded) for ex in month_execs)

            investment_timeline.append({
                'month': month_label,
                'investment': round(month_investment, 2),
                'return': month_return,
            })

        payback_months = round((effective_investment / roi_impact) * 12) if roi_impact > 0 else 0

        # ── Cost of Inaction + Revenue Waterfall ──
        # Uses the same churn + expansion probability models as playbook close
        from utils.playbook_lifecycle import (
            health_to_annual_churn_prob,
            health_to_annual_expansion_prob,
            INTERVENTION_ATTRIBUTION,
            EXPANSION_ATTRIBUTION,
        )
        account_ids = [a.account_id for a in accounts]
        latest_scores = _get_latest_health_scores(customer_id, account_ids)
        at_risk_accounts_list = []
        total_arr_at_risk = 0
        total_churn_exposure = 0
        total_expansion_missed = 0
        for acct in accounts:
            # Wave 1 Workstream A (Aug 4 2026): exclude churned accounts —
            # this tile previously double-counted already-churned ARR as
            # "at risk," violating the invariant MCP's get_at_risk_accounts
            # already enforces (tests/test_context_graph_invariants.py:631).
            if (acct.account_status or '').lower() == 'churned':
                continue
            hs_obj = latest_scores.get(acct.account_id)
            h = _safe_float(hs_obj.health_score if hs_obj else 0)
            arr = _safe_float(acct.revenue)
            if h < ht.healthy_min() and arr > 0:
                churn_prob = health_to_annual_churn_prob(h)
                # What expansion this account is missing by being unhealthy
                exp_current = health_to_annual_expansion_prob(h)
                exp_if_healthy = health_to_annual_expansion_prob(75)  # target: healthy threshold
                expansion_gap = max(0, exp_if_healthy - exp_current)
                annual_loss = arr * churn_prob
                annual_expansion_missed = arr * expansion_gap
                total_arr_at_risk += arr
                total_churn_exposure += annual_loss
                total_expansion_missed += annual_expansion_missed
                at_risk_accounts_list.append({
                    'account_name': acct.account_name,
                    'arr': round(arr, 0),
                    'health': round(h, 1),
                    'churn_pct': round(churn_prob * 100, 1),
                    'expansion_gap_pct': round(expansion_gap * 100, 1),
                    'annual_loss': round(annual_loss, 0),
                    'expansion_missed': round(annual_expansion_missed, 0),
                })
        at_risk_accounts_list.sort(key=lambda x: x['annual_loss'], reverse=True)

        # ── NRR waterfall — consistent with playbook ROI model ──
        wf_expected_loss = 0
        wf_protectable = 0
        wf_expandable = 0
        wf_cost = 0
        for entry in at_risk_accounts_list:
            h = entry['health']
            arr = entry['arr']
            # If playbook moves health from current → healthy (75), what's the delta?
            churn_before = health_to_annual_churn_prob(h)
            churn_after = health_to_annual_churn_prob(75)
            churn_reduction = max(0, churn_before - churn_after)
            exp_before = health_to_annual_expansion_prob(h)
            exp_after = health_to_annual_expansion_prob(75)
            exp_increase = max(0, exp_after - exp_before)

            wf_expected_loss += entry['annual_loss']
            wf_protectable += arr * churn_reduction * INTERVENTION_ATTRIBUTION
            wf_expandable += arr * exp_increase * EXPANSION_ATTRIBUTION
            wf_cost += 4560  # avg playbook cost from cost bridge

        wf_attributed = wf_protectable + wf_expandable
        nrr_with_intervention = nrr_projection
        if total_arr > 0 and wf_attributed > 0:
            nrr_with_intervention = round(nrr_projection + (wf_attributed / total_arr) * 100, 1)

        # ── PROOF DATA: actual playbook execution economics (bottom-up) ──
        proof_data = {'total_cost': 0, 'revenue_protected': 0, 'revenue_expanded': 0,
                      'csm_hours': 0, 'executions_total': 0, 'executions_resolved': 0,
                      'realized_roi': 0, 'executions': []}
        try:
            pb_execs = PlaybookExecutionV2.query.filter_by(customer_id=customer_id).all()
            proof_data['executions_total'] = len(pb_execs)
            for ex in pb_execs:
                cost = float(ex.total_cost or 0)
                prot = float(ex.revenue_protected or 0)
                exp = float(ex.revenue_expanded or 0)
                proof_data['total_cost'] += cost
                proof_data['revenue_protected'] += prot
                proof_data['revenue_expanded'] += exp
                proof_data['csm_hours'] += float(ex.csm_hours_actual or ex.csm_hours_planned or 0)
                if ex.outcome == 'resolved':
                    proof_data['executions_resolved'] += 1
                if prot > 0 or exp > 0 or cost > 0:
                    acct = next((a for a in accounts if a.account_id == ex.account_id), None)
                    acct_arr = float(acct.revenue or 0) if acct else 0
                    # NRR delta: this playbook's total value as % of portfolio ARR
                    nrr_delta = ((prot + exp) / total_arr * 100) if total_arr > 0 else 0
                    # Cost breakdown using cost bridge ratios (CSM 45%, Platform 30%, Overhead 25%)
                    csm_hours = float(ex.csm_hours_actual or ex.csm_hours_planned or 0)
                    csm_cost = round(cost * 0.45, 0)
                    platform_cost = round(cost * 0.30, 0)
                    overhead_cost = round(cost * 0.25, 0)
                    proof_data['executions'].append({
                        'playbook_id': ex.playbook_id,
                        'account_name': acct.account_name if acct else f'Account {ex.account_id}',
                        'arr': round(acct_arr, 0),
                        'health_at_trigger': round(ex.health_at_trigger, 1) if ex.health_at_trigger else None,
                        'health_at_close': round(ex.health_at_close, 1) if ex.health_at_close else None,
                        'health_delta': round(ex.health_delta, 1) if ex.health_delta else None,
                        'cost': round(cost, 0),
                        'cost_csm': csm_cost,
                        'cost_platform': platform_cost,
                        'cost_overhead': overhead_cost,
                        'csm_hours': csm_hours,
                        'revenue_protected': round(prot, 0),
                        'revenue_expanded': round(exp, 0),
                        'nrr_delta_pp': round(nrr_delta, 2),
                        'roi_x': round(ex.realized_roi_pct, 1) if ex.realized_roi_pct else 0,
                        'outcome': ex.outcome,
                    })
            total_value = proof_data['revenue_protected'] + proof_data['revenue_expanded']
            proof_data['realized_roi'] = round(total_value / proof_data['total_cost'], 1) if proof_data['total_cost'] > 0 else 0
            proof_data['total_cost'] = round(proof_data['total_cost'], 0)
            proof_data['revenue_protected'] = round(proof_data['revenue_protected'], 0)
            proof_data['revenue_expanded'] = round(proof_data['revenue_expanded'], 0)
            proof_data['csm_hours'] = round(proof_data['csm_hours'], 0)
            # Sort by revenue_protected desc
            proof_data['executions'].sort(key=lambda e: e['revenue_protected'], reverse=True)
        except Exception as e:
            logger.warning(f"CFO proof_data computation failed: {e}")

        # ── Phase 3: efficiency from playbook economics or proof (after proof_data) ──
        efficiency_block = build_cfo_efficiency_metrics(
            customer_id,
            total_arr,
            proof_data,
            effective_investment,
            roi_impact,
        )
        efficiency_score = efficiency_block.get('efficiency_score', 0)
        automation_rate = efficiency_block.get('automation_rate', 0)
        time_saved_hours = efficiency_block.get('time_saved_hours', 0)

        # ── HISTORICAL ACTUALS (Row A of "Past — Three Lenses") ──
        historical_actuals = _compute_historical_actuals(customer_id, total_arr)

        # ── WIZARD B NRR: backward counterfactual (with/without CS Pulse) ──
        wizard_b_nrr = None
        try:
            from wizards.wizard_b_pattern_db import run_wizard_b
            wb_result = run_wizard_b(customer_id)
            forecast = (wb_result.get('nrr_intelligence') or {}).get('forecast') or {}
            if forecast.get('current_nrr_pct'):
                grr_data = wb_result.get('grr_intelligence') or {}
                wizard_b_nrr = {
                    'without_cs_pulse_nrr_pct': forecast.get('without_cs_pulse_nrr_pct', 100),
                    'with_cs_pulse_nrr_pct': forecast.get('current_nrr_pct', 100),
                    'delta_pct': forecast.get('cs_pulse_delta_pct', 0),
                    'arr_protected': forecast.get('cs_pulse_arr_protected', 0),
                    'accounts_saved': forecast.get('cs_pulse_accounts_saved', 0),
                    'with_interventions_nrr_pct': forecast.get('with_interventions_nrr_pct', 100),
                    'intervention_delta_arr': forecast.get('delta_arr', 0),
                    'grr_before_pct': grr_data.get('grr_before_pct'),
                    'grr_after_pct': grr_data.get('grr_after_pct'),
                    # Lens metadata — helps the frontend label this card
                    # correctly vs. predictor_v3_portfolio_nrr below.
                    'lens': 'counterfactual_ttm',
                    'engine': 'wizard_b',
                    'time_direction': 'backward',
                }
        except Exception as e:
            logger.warning(f"CFO wizard_b_nrr computation failed: {e}")

        # ── PREDICTOR v3 PORTFOLIO NRR: forward point forecast ──
        predictor_v3_portfolio_nrr = _compute_predictor_v3_portfolio_nrr(accounts)

        return jsonify({
            'status': 'success',
            'total_arr': round(total_arr, 2),
            'account_count': len(accounts),
            # ── PROOF: actual playbook economics ──
            'proof_data': proof_data,
            # ── ROW A: historical actuals from customer's uploaded data ──
            'historical_actuals': historical_actuals,
            # ── WIZARD B (ROW B): backward counterfactual (with vs without CS Pulse) ──
            'wizard_b_nrr': wizard_b_nrr,
            # ── PREDICTOR v3: forward point forecast (per-account aggregated) ──
            'predictor_v3_portfolio_nrr': predictor_v3_portfolio_nrr,
            # Revenue Intelligence — Confirmed Risk (causal, from Context Graph)
            # graph_* totals match CRO dashboard (aggregate_revenue_across_accounts).
            # Distinct from proof_data.revenue_protected (playbook executions).
            'revenue_at_risk': revenue_data['revenue_at_risk'],
            'revenue_protected': revenue_data['revenue_protected'],
            'expansion_pipeline': revenue_data['expansion_pipeline'],
            'revenue_risk_type': 'confirmed',
            'revenue_risk_label': 'Confirmed Risk (Context Graph)',
            'context_graph_provenance': context_graph_provenance,
            # Cost of Inaction
            'cost_of_inaction': {
                'arr_at_risk': round(total_arr_at_risk, 0),
                'annual_churn_exposure': round(total_churn_exposure, 0),
                'annual_expansion_missed': round(total_expansion_missed, 0),
                'total_cost_of_inaction': round(total_churn_exposure + total_expansion_missed, 0),
                'accounts': at_risk_accounts_list[:5],
                'account_count': len(at_risk_accounts_list),
            },
            # NRR/GRR dual
            'nrr_current': nrr_projection,
            'nrr_with_intervention': nrr_with_intervention,
            'nrr_arr_protectable': round(wf_attributed, 0),
            'nrr_waterfall': {
                'expected_loss': round(wf_expected_loss, 0),
                'protectable': round(wf_protectable, 0),
                'expandable': round(wf_expandable, 0),
                'attributed_save': round(wf_attributed, 0),
                'intervention_cost': round(wf_cost, 0),
                'roi_x': round(wf_attributed / wf_cost, 1) if wf_cost > 0 else 0,
                # attributed_save is real health/ARR through the churn model
                # (derived); intervention_cost is the fixed 4560-per-account
                # constant (benchmark). roi_x divides one by the other, so it
                # carries the weaker tier of its two inputs.
                'data_source': _vp.most_conservative([_vp.DERIVED, _vp.BENCHMARK]),
            },
            'expansion_missed': round(total_expansion_missed, 0),
            'cs_investment': cs_investment,
            'estimated_investment': estimated_investment,
            'is_estimated': is_estimated,
            'roi_pct': roi_pct,
            'roi_investment': round(roi_investment, 2),
            'roi_impact': round(roi_impact, 2),
            'nrr_projection': nrr_projection,
            'grr_projection': grr_projection,
            'power_of_1_metrics': power_of_1_metrics,
            # ── Layered investment story ──
            'layered_story': _build_layered_story(
                proof_data, total_arr, wf_protectable, wf_expandable, wf_cost,
                power_of_1_metrics,
            ),
            'roi_scaling': roi_scaling,
            'roi_multiple': roi_multiple,
            'roi_is_modeled': roi_is_modeled or is_estimated,
            'pillar_investments': pillar_investments,
            'investment_timeline': investment_timeline,
            'efficiency': efficiency_block,
            'efficiency_score': efficiency_score,
            'automation_rate': automation_rate,
            'time_saved_hours': time_saved_hours,
            'payback_months': payback_months,
            # Pre-computed ratios so frontend doesn't need the fallback logic
            'rev_per_cs_dollar': round(roi_impact / effective_investment, 1) if effective_investment > 0 else 0,
            'quarter_label': _current_quarter_label(),
            'last_updated': datetime.utcnow().isoformat(),
            # Account-level details for drill-down
            'accounts': _build_cfo_account_details(customer_id, accounts, effective_investment, roi_impact),
        })

    except Exception as e:
        logger.error(f"Error in cfo_dashboard: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


def _build_layered_story(proof_data, total_arr, wf_protectable, wf_expandable, wf_cost,
                         power_of_1_metrics):
    """Build the 3-layer investment allocation story for the CFO dashboard.

    Layer 1: Already delivered (from playbook executions)
    Layer 2: Still protectable (from waterfall — at-risk accounts)
    Layer 3: Growth upside (from Power-of-1 — 1% improvement across all metrics)

    Every layer (and the blended totals) carries a value-provenance
    `data_source` tier. Each layer's tier is most_conservative(value, cost)
    — a ROI number is only as grounded as the weaker of its numerator and
    denominator — and the blended totals take most_conservative across all
    six inputs. This is why layer 2 is 'benchmark', not 'derived': its
    value is real health/ARR run through the churn model (derived), but
    its cost is a fixed per-account constant (benchmark), so the ROI
    blends the two.
    """
    from utils import value_provenance as vp

    # Layer 1: Proof — real PlaybookExecutionV2 rows, value and cost both.
    prot = proof_data.get('revenue_protected', 0)
    exp = proof_data.get('revenue_expanded', 0)
    cost1 = proof_data.get('total_cost', 0)
    value1 = prot + exp
    roi1 = round(value1 / cost1, 1) if cost1 > 0 else 0
    value1_tier, cost1_tier = vp.MEASURED, vp.MEASURED

    # Layer 2: Protectable — value is real health/ARR through the
    # health_to_annual_churn_prob model (derived); cost is the fixed
    # 4560-per-account cost-bridge constant (benchmark).
    value2 = wf_protectable + wf_expandable
    cost2 = wf_cost
    roi2 = round(value2 / cost2, 1) if cost2 > 0 else 0
    value2_tier, cost2_tier = vp.DERIVED, vp.BENCHMARK

    # Layer 3: Power-of-1 growth
    # Impact scales linearly with ARR, cost scales sub-linearly (sqrt).
    # Deduped, not summed: 3 of the 6 metrics share a playbook with another
    # metric (PB-01 → TTFV + product_adoption, PB-02 → GRR + ticket_resolution_time,
    # PB-04 → NRR + expansion_rate) — a naive sum counted each shared
    # playbook's benefit twice (vertical-coupling audit Finding 6, 2026-08-21).
    po1_impact = dedupe_portfolio_dollar_impact(power_of_1_metrics)
    # Compute Po1 cost from POWER_OF_1_METRICS benchmarks
    po1_cost = 0
    try:
        from outcome_roi_engine import POWER_OF_1_METRICS as _PO1
        inv_scale = (total_arr / 10_000_000) ** 0.5 if total_arr > 0 else 1.0
        po1_cost = sum(m.total_investment * inv_scale for m in _PO1.values())
    except Exception:
        po1_cost = total_arr * 0.01  # fallback: 1% of ARR
    roi3 = round(po1_impact / po1_cost, 1) if po1_cost > 0 else 0
    value3_tier, cost3_tier = vp.BENCHMARK, vp.BENCHMARK

    total_value = value1 + value2 + po1_impact
    total_cost = cost1 + cost2 + po1_cost
    blended_roi = round(total_value / total_cost, 1) if total_cost > 0 else 0

    all_tiers = [value1_tier, cost1_tier, value2_tier, cost2_tier, value3_tier, cost3_tier]

    return {
        'layers': [
            {
                'name': 'Already Delivered',
                'value': round(value1, 0),
                'cost': round(cost1, 0),
                'roi': roi1,
                'status': 'done',
                'color': 'green',
                'data_source': vp.most_conservative([value1_tier, cost1_tier]),
            },
            {
                'name': 'Still Protectable',
                'value': round(value2, 0),
                'cost': round(cost2, 0),
                'roi': roi2,
                'status': 'intervene_now',
                'color': 'cyan',
                'data_source': vp.most_conservative([value2_tier, cost2_tier]),
            },
            {
                'name': 'Growth (Po1 1%)',
                'value': round(po1_impact, 0),
                'cost': round(po1_cost, 0),
                'roi': roi3,
                'status': 'invest_to_grow',
                'color': 'purple',
                'data_source': vp.most_conservative([value3_tier, cost3_tier]),
            },
        ],
        'total_value': round(total_value, 0),
        'total_cost': round(total_cost, 0),
        'blended_roi': blended_roi,
        # The blended figures mix all three layers — honest label is the
        # weakest input across all six numerators/denominators.
        'data_source': vp.most_conservative(all_tiers),
    }


def _build_pillar_investments(pillar_codes, pillar_weights, vertical_pillars,
                              roi_impact, effective_investment):
    """Allocate the SINGLE canonical program value + spend across pillars.

    Item 22 (state-of-play.md, owner decision 2026-08-24): pillar impacts used
    to sum the raw per-metric ``dollar_impact`` values, which double-counts any
    metric mapped to more than one pillar and produced a *second, larger*
    program-value figure than the canonical deduped total — 1,746,250 vs
    1,331,250 on customer 393, an implied 5.3× ROI competing with the 4.0×
    headline (``roi_impact`` / ``effective_investment``). Decision: there is
    exactly one modeled value per program; the pillar table is an ALLOCATION of
    it, never an independent second source. So both value and spend are split by
    pillar weight from the canonical ``roi_impact`` / ``effective_investment``,
    and ``sum(impact) == roi_impact`` by construction. Per-pillar ROI is
    therefore the headline ROI — this is an allocation view, not a claim of
    differentiated per-pillar returns (the metric→pillar map still drives the
    Power-of-1 cards, just not a rival headline value here).
    """
    total_weight = sum(pillar_weights.get(p, 0) for p in pillar_codes) or 1.0
    rows = []
    for pcode in pillar_codes:
        wshare = pillar_weights.get(pcode, 0) / total_weight
        pillar_impact = round(roi_impact * wshare, 2)
        pillar_investment = round(effective_investment * wshare, 2)
        pillar_roi = round(pillar_impact / pillar_investment, 1) if pillar_investment > 0 else 0
        rows.append({
            'pillar': pcode,
            'name': vertical_pillars.get(pcode, {}).get('name', pcode),
            'investment': pillar_investment,
            'impact': pillar_impact,
            'roi': pillar_roi,
        })
    return rows


def _build_cfo_account_details(customer_id, accounts, total_investment, total_impact):
    """Build per-account investment/impact breakdown for CFO drill-down."""
    if not accounts:
        return []

    total_arr = sum(_safe_float(a.revenue) for a in accounts)
    if total_arr <= 0:
        return []

    latest_scores = _get_latest_health_scores(customer_id, [a.account_id for a in accounts])
    healthy_min_val = ht.healthy_min()

    # ── benchmark impact allocation weights (health-adjusted) ────────────────
    # Item 6 fix: the old benchmark branch scaled BOTH investment and impact by
    # the same arr_share, so it cancelled in the ROI ratio and every account
    # reported the identical portfolio ROI (302% on 390) regardless of health —
    # a constant column that read as measured. Investment tracks account size
    # (ARR ≈ CS servicing effort); impact tracks *recoverable* revenue, which
    # the platform already models as ARR × churn_pct(health) (the sanctioned
    # 40/20/5 band, single source in context_graph.churn_pct_for_health). So
    # allocate impact by that weight and renormalize to preserve the portfolio
    # total — ROI now varies by health (worse accounts protect more revenue per
    # servicing dollar) while per-account impact still sums to total_impact.
    from utils.context_graph import churn_pct_for_health
    impact_weights = {}
    for acct in accounts:
        arr = _safe_float(acct.revenue)
        hs = latest_scores.get(acct.account_id)
        score = float(hs.health_score) if hs else 0
        impact_weights[acct.account_id] = arr * churn_pct_for_health(score)
    total_impact_weight = sum(impact_weights.values())

    result = []
    for acct in accounts:
        arr = _safe_float(acct.revenue)
        arr_share = arr / total_arr if total_arr > 0 else 0
        hs = latest_scores.get(acct.account_id)
        score = float(hs.health_score) if hs else 0

        # Check for actual ActionEconomics data
        try:
            from models import ActionEconomics
            ae_records = ActionEconomics.query.filter_by(
                customer_id=customer_id, account_id=acct.account_id
            ).all()
            if ae_records:
                acct_investment = sum(float(a.total_action_cost or 0) for a in ae_records)
                acct_impact = sum(float(a.dollar_impact_annual or 0) for a in ae_records)
                source = 'actual'
                playbook_runs = len(ae_records)
            else:
                # cost ∝ account size; impact ∝ recoverable revenue (health-band).
                impact_share = (
                    impact_weights[acct.account_id] / total_impact_weight
                    if total_impact_weight > 0 else arr_share
                )
                acct_investment = round(total_investment * arr_share, 2)
                acct_impact = round(total_impact * impact_share, 2)
                source = 'benchmark'
                playbook_runs = 0
        except Exception:
            impact_share = (
                impact_weights.get(acct.account_id, 0) / total_impact_weight
                if total_impact_weight > 0 else arr_share
            )
            acct_investment = round(total_investment * arr_share, 2)
            acct_impact = round(total_impact * impact_share, 2)
            source = 'benchmark'
            playbook_runs = 0

        acct_roi = round((acct_impact / acct_investment - 1) * 100) if acct_investment > 0 else 0

        result.append({
            'account_id': acct.account_id,
            'account_name': acct.account_name,
            'arr': arr,
            'health_score': round(score, 1),
            'classification': ht.classify(score),
            'investment': round(acct_investment, 2),
            'impact': round(acct_impact, 2),
            'roi_pct': acct_roi,
            'source': source,
            'playbook_runs': playbook_runs,
        })

    # Sort by health score ascending (worst first)
    result.sort(key=lambda a: a['health_score'])
    return result


# ─── 2b. CEO Dashboard (single-customer fallback) ────────────────────────────

@executive_dashboard_api.route('/api/executive/ceo-dashboard', methods=['GET'])
def ceo_dashboard():
    """
    CEO-level portfolio view.  When the authenticated customer belongs to a
    portfolio, delegates to the portfolio API.  Otherwise falls back to a
    single-customer "portfolio of one" view — same data as CRO/CFO but
    formatted for the CEO persona (cross-account summary, NRR, churn risk).
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        from models import Customer, PortfolioMembership
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404

        # Check if customer belongs to a portfolio
        try:
            membership = PortfolioMembership.query.filter_by(customer_id=customer_id).first()
            if membership:
                # Has portfolio — return portfolio_id so frontend can call portfolio API
                return jsonify({
                    'status': 'success',
                    'mode': 'portfolio',
                    'portfolio_id': membership.portfolio_id,
                })
        except Exception:
            # Table may not exist yet — fall through to single-customer mode
            pass

        # ── Single-customer fallback: "portfolio of one" ──
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        account_ids = [a.account_id for a in accounts]
        num_accounts = len(accounts)
        total_arr = sum(a.revenue or 0 for a in accounts)

        # Health scores
        healthy_min_val = ht.healthy_min()
        at_risk_min_val = ht.at_risk_min()
        latest_scores = _get_latest_health_scores(customer_id, account_ids)
        healthy_count = 0
        at_risk_count = 0
        critical_count = 0
        total_weighted = 0.0
        total_rev = 0.0

        account_details = []
        for acct in accounts:
            hs = latest_scores.get(acct.account_id)
            score = float(hs.health_score) if hs else 0
            rev = float(acct.revenue or 0)
            total_weighted += score * rev
            total_rev += rev
            if score >= healthy_min_val:
                healthy_count += 1
            elif score >= at_risk_min_val:
                at_risk_count += 1
            else:
                critical_count += 1
            account_details.append({
                'account_id': acct.account_id,
                'account_name': acct.account_name,
                'health_score': round(score, 1),
                'revenue': rev,
                'classification': ht.classify(score),
            })

        avg_health = round(total_weighted / total_rev, 1) if total_rev > 0 else 0

        revenue_bundle = _revenue_bundle_from_context_graph(customer_id, account_ids)
        revenue_data = revenue_bundle
        context_graph_provenance = revenue_bundle.get('provenance')

        # NRR derived from health
        if avg_health >= 70:
            nrr = round(100 + (avg_health - 70) * 0.33)
        elif avg_health >= 40:
            nrr = round(90 + (avg_health - 40) * 0.33)
        else:
            nrr = round(85 + avg_health * 0.125)

        # ROI from snapshot or Power-of-1 fallback
        roi_snap = _get_roi_snapshot(customer_id)
        roi_pct = 0
        if roi_snap:
            roi_pct = round(roi_snap.historical_roi_pct or roi_snap.combined_roi_pct or 0)
        if roi_pct == 0 and total_arr > 0:
            po1_metrics = _get_po1_benchmark_metrics(total_arr)
            po1_inv = _get_po1_benchmark_investment(total_arr)
            if po1_inv > 0:
                po1_impact = dedupe_portfolio_dollar_impact(po1_metrics)
                roi_pct = round((po1_impact / po1_inv - 1) * 100)

        # Sort by health ascending (worst first)
        account_details.sort(key=lambda a: a['health_score'])

        # Build single company entry (portfolio of one)
        companies = [{
            'customer_id': customer_id,
            'name': customer.customer_name,
            'arr': round(total_arr, 2),
            'health_score': avg_health,
            'account_count': num_accounts,
            'at_risk_count': at_risk_count + critical_count,
            'nrr': nrr,
            'trend': 'down' if avg_health < 60 else ('up' if avg_health >= 70 else 'flat'),
            'trend_change': round(avg_health - 60, 1),
            'vertical': customer.vertical or 'dc2_s',
        }]

        return jsonify({
            'status': 'success',
            'mode': 'single_customer',
            'companies': companies,
            'portfolio_summary': {
                'total_arr': round(total_arr, 2),
                'avg_health': avg_health,
                'total_accounts': num_accounts,
                'healthy': healthy_count,
                'at_risk': at_risk_count,
                'critical': critical_count,
                'nrr': nrr,
                'roi_pct': roi_pct,
                'revenue_at_risk': revenue_data['revenue_at_risk'],
                'revenue_protected': revenue_data['revenue_protected'],
                'expansion_pipeline': revenue_data['expansion_pipeline'],
            },
            'context_graph_provenance': context_graph_provenance,
            'highest_risk_accounts': account_details[:5],
            'quarter_label': _current_quarter_label(),
            'last_updated': datetime.utcnow().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error in ceo_dashboard: {e}", exc_info=True)
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
            'How much confirmed revenue is at risk (context graph) over the next 90 days?',
            'Which 3 accounts are most likely to churn next quarter, and why?',
            'Where is our biggest expansion upside in the portfolio?',
            'Show the causal chain for our worst-trending account this quarter.',
            'Which playbooks are moving revenue vs wasting CSM time?',
        ],
    },
    'cfo': {
        'role': 'Chief Financial Officer',
        'focus': 'CS investment ROI, cost efficiency, payback periods, budget allocation',
        'tone': 'Think like a CFO — every insight should connect to investment returns. '
                'Show ROI ratios, cost-per-account, payback periods. '
                'Compare actual vs projected. Flag inefficient spend. '
                'Distinguish context-graph confirmed $ at risk vs playbook-attributed $ '
                'vs modeled churn exposure. Name the NRR lens (historical / Wizard B / forward).',
        'suggested': [
            'What is our CS investment returning per dollar?',
            'How much confirmed revenue is at risk (context graph)?',
            'Compare actual vs projected revenue protection — is a target set?',
            'What is our payback period on CS Pulse adoption?',
            'How does modeled ROI scale as we add more accounts?',
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

        # ── 1–2. Load context graph + portfolio (same engine as dashboards) ──
        from utils.context_graph_ask_context import build_ask_context_graph_block

        context, ctx_stats = build_ask_context_graph_block(customer_id)

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
2. Revenue at risk / protected / expansion MUST match REVENUE INTELLIGENCE (context graph OUTCOME aggregation).
3. When citing a specific signal or outcome, include its node_id from the context block.
4. Always quantify: use dollar amounts, percentages, account counts.
5. Connect cause to effect: use context graph chains to explain WHY things are happening.
6. Be actionable: every answer should end with a clear "do this next" recommendation.
7. Be concise: lead with the insight, support with 2-3 data points, close with action.
8. When discussing health scores: Critical (<{ht.at_risk_min()}), At-Risk ({ht.at_risk_min()}-{ht.healthy_min()-1}), Healthy (>={ht.healthy_min()}).

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

        # ── 5. Call Claude (Anthropic) ────────────────────────────────────

        from anthropic_chat_utils import generate_text, AnthropicKeyNotConfigured, DEFAULT_MODEL

        # Budget check (fail-open)
        try:
            if _budget_can_call and not _budget_can_call(customer_id, 'exec_dashboard'):
                return jsonify({'error': 'Daily AI budget reached', 'budget_exceeded': True}), 429
        except Exception:
            pass

        try:
            response_text, _tok_in, _tok_out = generate_text(
                customer_id, system_prompt, user_prompt,
                max_tokens=1200, temperature=0.3,
            )
        except AnthropicKeyNotConfigured:
            return jsonify({
                'error': 'Anthropic API key not configured',
                'message': 'Set ANTHROPIC_API_KEY or configure a per-customer key in Settings.',
            }), 400

        # Record usage (fail-open)
        try:
            if _budget_record:
                _budget_record(customer_id, 'exec_dashboard',
                               tokens_in=_tok_in,
                               tokens_out=_tok_out,
                               model=DEFAULT_MODEL)
        except Exception:
            pass

        elapsed_ms = int((_time.time() - start_time) * 1000)

        return jsonify({
            'response': response_text,
            'persona': persona,
            'query': query_text,
            'elapsed_ms': elapsed_ms,
            'context_stats': ctx_stats,
            'context_graph_loaded': True,
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


# ─────────────────────────────────────────────────────────────────────────────
# Pending Decisions Queue (CRO / CFO right-sidebar panel)
# ─────────────────────────────────────────────────────────────────────────────
# Read-only v1. Surfaces items awaiting an executive decision, drawn from
# existing data sources:
#   • PlaybookExecutionV2 (status='in_progress')      → playbook reviews / spend approvals
#   • ContextNode (node_type='DECISION', subset)      → flagged decisions (escalations etc.)
#   • At-risk accounts without an active playbook     → launch-a-playbook decision
#
# Persona filter:
#   • cro: sort by revenue_at_stake desc; default headline is account-centric.
#   • cfo: sort by dollar_amount desc; default headline is investment-centric.
# Both personas receive the SAME data; ordering + framing differ.

_DECISION_KIND_HEADLINES = {
    'playbook_in_flight': {
        'cro': 'Review {account}: playbook in flight',
        'cfo': 'Approve continued spend on {account}',
    },
    'at_risk_no_playbook': {
        'cro': 'Decide intervention for {account}',
        'cfo': 'Authorise budget to protect {account}',
    },
    'expansion_open': {
        'cro': 'Staff expansion on {account}',
        'cfo': 'Approve expansion investment in {account}',
    },
    'flagged_decision': {
        'cro': 'Decide: {title}',
        'cfo': 'Decide: {title}',
    },
}


def _classify_urgency(revenue_at_stake: float, days_open: int) -> str:
    """Simple urgency heuristic — not a model, just a deterministic bucket.
    High = revenue ≥ $1M OR open > 30d. Low = revenue < $250k AND open ≤ 7d.
    """
    if revenue_at_stake >= 1_000_000 or days_open > 30:
        return 'high'
    if revenue_at_stake < 250_000 and days_open <= 7:
        return 'low'
    return 'medium'


def _build_pending_decisions(customer_id: int, limit: int = 5):
    """Pull pending-decision rows from existing sources. Returns unsorted list."""
    accounts = _get_customer_accounts(customer_id)
    if not accounts:
        return []

    account_ids = [a.account_id for a in accounts]
    account_by_id = {a.account_id: a for a in accounts}
    now = datetime.utcnow()
    items = []

    # Health scores — guarded against schema drift (rare, but pre-existing pattern).
    latest_health = {}
    try:
        latest_health = _get_latest_health_scores(customer_id, account_ids)
    except Exception:
        logger.warning('pending_decisions: health-score fetch failed; skipping at-risk path', exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass

    # 1) In-flight playbooks — spend/continuation decisions
    in_flight = []
    try:
        in_flight = (
            PlaybookExecutionV2.query
            .filter_by(customer_id=customer_id, status='in_progress')
            .order_by(PlaybookExecutionV2.triggered_at.desc())
            .limit(20)
            .all()
        )
    except Exception:
        logger.warning('pending_decisions: PlaybookExecutionV2 query failed; skipping', exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
    for ex in in_flight:
        acct = account_by_id.get(ex.account_id)
        if not acct:
            continue
        rev_at_stake = _safe_float(ex.arr_at_trigger) or _safe_float(acct.revenue)
        cost = _safe_float(ex.total_cost)
        triggered_at = ex.triggered_at or now
        days_open = max(0, (now - triggered_at).days)
        progress = ''
        if ex.actions_planned:
            progress = f"{ex.actions_completed or 0}/{ex.actions_planned} actions complete"
        rationale_bits = [
            f"{ex.playbook_name or ex.playbook_id}",
            f"phase: {ex.phase or 'stabilize'}",
            f"open {days_open}d",
        ]
        if progress:
            rationale_bits.append(progress)
        items.append({
            'decision_id': f"pbexec_{ex.id}",
            'kind': 'playbook_in_flight',
            'account_id': acct.account_id,
            'account_name': acct.account_name,
            'dollar_amount': round(cost, 0),
            'revenue_at_stake': round(rev_at_stake, 0),
            'rationale': ' · '.join(rationale_bits),
            'urgency': _classify_urgency(rev_at_stake, days_open),
            'occurred_at': triggered_at.isoformat(),
            'source': {'type': 'playbook_execution', 'id': ex.execution_id},
        })

    # 2) At-risk accounts WITHOUT an active playbook — launch-decision needed
    accounts_with_active_pb = {ex.account_id for ex in in_flight}
    healthy_floor = ht.healthy_min()
    for acct in accounts:
        if acct.account_id in accounts_with_active_pb:
            continue
        hs = latest_health.get(acct.account_id)
        if not hs:
            continue
        score = _safe_float(hs.health_score)
        if score >= healthy_floor:
            continue
        rev = _safe_float(acct.revenue)
        # only surface accounts with material exposure
        if rev < 100_000:
            continue
        # days since latest health snapshot (best-effort signal of how stale this risk is)
        days_open = 0
        snapshot_dt = getattr(hs, 'created_at', None) or getattr(hs, 'measurement_month', None)
        if snapshot_dt:
            try:
                snapshot_dt = snapshot_dt if isinstance(snapshot_dt, datetime) else datetime.combine(snapshot_dt, datetime.min.time())
                days_open = max(0, (now - snapshot_dt).days)
            except Exception:
                days_open = 0
        items.append({
            'decision_id': f"atrisk_{acct.account_id}",
            'kind': 'at_risk_no_playbook',
            'account_id': acct.account_id,
            'account_name': acct.account_name,
            'dollar_amount': 0,  # no spend yet — that's the point
            'revenue_at_stake': round(rev, 0),
            'rationale': f"health {round(score, 1)} · {ht.classify(score)} · no active playbook",
            'urgency': _classify_urgency(rev, days_open),
            'occurred_at': snapshot_dt.isoformat() if snapshot_dt else now.isoformat(),
            'source': {'type': 'account', 'id': acct.account_id},
        })

    # 3) Open expansion opportunities from ContextNode
    # Defensive: matches the cro_dashboard pattern (~line 568) — ContextNode schema
    # drift between image versions has burned us before, so don't let a single
    # missing column collapse the whole queue.
    expansion_nodes = []
    try:
        expansion_nodes = (
            ContextNode.query
            .filter(
                ContextNode.customer_id == customer_id,
                ContextNode.revenue_impact_type == 'expansion',
                ContextNode.revenue_impact.isnot(None),
            )
            .order_by(ContextNode.revenue_impact.desc())
            .limit(10)
            .all()
        )
    except Exception:
        logger.warning('pending_decisions: ContextNode expansion query failed; skipping', exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
    for n in expansion_nodes:
        acct = account_by_id.get(n.account_id)
        if not acct:
            continue
        rev = _safe_float(n.revenue_impact)
        if rev <= 0:
            continue
        occurred = n.occurred_at or now
        days_open = max(0, (now - occurred).days)
        items.append({
            'decision_id': f"ctx_{n.node_id}",
            'kind': 'expansion_open',
            'account_id': acct.account_id,
            'account_name': acct.account_name,
            'dollar_amount': 0,
            'revenue_at_stake': round(rev, 0),
            'rationale': (n.title or n.node_subtype or 'expansion signal') + f" · open {days_open}d",
            'urgency': _classify_urgency(rev, days_open),
            'occurred_at': occurred.isoformat(),
            'source': {'type': 'context_node', 'id': n.node_id},
        })

    return items


@executive_dashboard_api.route('/api/executive/pending-decisions', methods=['GET'])
def pending_decisions():
    """
    Read-only pending-decisions queue for CRO + CFO dashboards.

    Query params:
      persona  — 'cro' (default) | 'cfo'   controls sort order + headline framing
      limit    — int, default 5

    Returns: { persona, items: [...], generated_at }
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 400

        persona = (request.args.get('persona') or 'cro').lower()
        if persona not in ('cro', 'cfo'):
            persona = 'cro'
        try:
            limit = max(1, min(int(request.args.get('limit') or 5), 20))
        except (TypeError, ValueError):
            limit = 5

        items = _build_pending_decisions(customer_id, limit=limit)

        # persona-driven sort
        if persona == 'cfo':
            items.sort(key=lambda x: (x['dollar_amount'], x['revenue_at_stake']), reverse=True)
        else:  # cro
            items.sort(key=lambda x: x['revenue_at_stake'], reverse=True)

        items = items[:limit]

        # attach persona-framed headline
        for it in items:
            template = (_DECISION_KIND_HEADLINES.get(it['kind']) or {}).get(persona, '{title}')
            it['headline'] = template.format(
                account=it.get('account_name', 'account'),
                title=it.get('rationale', 'decision'),
            )

        return jsonify({
            'persona': persona,
            'customer_id': customer_id,
            'items': items,
            'generated_at': datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.exception('pending_decisions failed')
        return jsonify({'error': str(e)}), 500
