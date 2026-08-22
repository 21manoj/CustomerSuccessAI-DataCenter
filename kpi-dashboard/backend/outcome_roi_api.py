#!/usr/bin/env python3
"""
Outcome ROI API — Historical Proof + Forward Projection
=========================================================
Outcome-focused endpoints. Headlines are always dollars and
Power of 1 metrics — never raw KPIs.

Endpoints:
  GET  /api/outcome-roi/historical          — "We proved it works"
  GET  /api/outcome-roi/forward             — "Here's what's next"
  GET  /api/outcome-roi/story               — Combined side-by-side for demo
  GET  /api/outcome-roi/demo                — Baseline projection (no DB needed, uses Power-of-1 defaults)
  GET  /api/outcome-roi/historical-details  — Per-account evidence drill-down

Feature flag: 'revenue_intelligence'
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import (
    Account, HealthTrend, FeatureToggle as FeatureToggleModel, ROISnapshot,
    QualitativeSignal, PlaybookExecution, KPIScore, HealthScore,
    DC2SKPI, CustomerConfig,
)
from resolve_identifier import resolve_customer_id
import utils.health_thresholds as ht
import utils.value_provenance as vp

outcome_roi_api = Blueprint('outcome_roi_api', __name__)

# Pillar code → Power-of-1 metric mapping, per vertical.
# Used by _extract_historical_actuals, _extract_current_values, _extract_accounts_at_risk,
# _compute_pillar_changes — the HealthScore.contributing_pillars data path (DC2SKPI's
# Path 0 is dc2_s-only; every other vertical resolves its pillar scores through here).
# Each entry pairs a pillar_metric_map (pillar_code → Power-of-1 metric_id) with an
# optional nrr_synthesis (which two pillars combine into a synthetic NRR reading,
# when NRR isn't already covered directly).
POWER_OF_1_PILLAR_MAPS = {
    'dc2_s': {
        'pillar_metric_map': {
            'P1': 'TTFV',                    # Deployment Velocity → Time-to-First-Value
            'P2': 'ticket_resolution_time',  # Operational Stability → Support metric
            'P3': 'product_adoption',        # AI Workload Perf → Adoption
            'P4': 'GRR',                     # Channel & Partner → Gross Revenue Retention
            'P5': 'expansion_rate',          # Expansion Readiness → Expansion Rate
        },
        'nrr_synthesis': {'retention_pillar': 'P4', 'retention_weight': 0.4,
                           'expansion_pillar': 'P5', 'expansion_weight': 0.6},
    },
    'saas_premium': {
        'pillar_metric_map': {
            'P1': 'product_adoption',        # Product Adoption & Usage → Adoption
            'P2': 'TTFV',                    # Customer Engagement → Time-to-First-Value
            'P3': 'ticket_resolution_time',  # Customer Sentiment & Support → Support metric
            'P4': 'GRR',                     # Partner & Ecosystem Health → Gross Revenue Retention
            'P5': 'expansion_rate',          # Revenue & Growth → Expansion Rate
        },
        'nrr_synthesis': {'retention_pillar': 'P4', 'retention_weight': 0.4,
                           'expansion_pillar': 'P5', 'expansion_weight': 0.6},
    },
    'datacenter_v1': {
        'pillar_metric_map': {
            'P1': 'NRR',                     # Revenue & Unit Economics → Net Revenue Retention
            'P2': 'product_adoption',        # Fleet Utilization & Goodput → Adoption
            'P3': 'ticket_resolution_time',  # Reliability & SLA Delivery → Support metric
            'P4': 'GRR',                     # Power & Facility → Gross Revenue Retention
            'P5': 'expansion_rate',          # Commercial & Expansion → Expansion Rate
            'P6': 'TTFV',                    # Provisioning Velocity → Time-to-First-Value
        },
        'nrr_synthesis': None,  # NRR already covered directly by P1 above
    },
}

# Fallback for verticals with no entry above: assign each of the vertical's own
# pillar codes a distinct real Power-of-1 metric_id, cycling through this fixed
# order. Never re-uses dc2_s's pillar semantics (e.g. "Deployment Velocity")
# mislabeled onto an unrelated pillar — see historical bug where every non-dc2_s
# vertical inherited DC2S_PILLAR_METRIC_MAP unconditionally.
_GENERIC_METRIC_FALLBACK_ORDER = [
    'product_adoption', 'ticket_resolution_time', 'GRR', 'expansion_rate', 'TTFV', 'NRR',
]


def _get_pillar_metric_map(vertical):
    """Return (pillar_metric_map, nrr_synthesis) for a vertical.

    pillar_metric_map: dict of pillar_code -> Power-of-1 metric_id.
    nrr_synthesis: {'retention_pillar', 'retention_weight', 'expansion_pillar',
        'expansion_weight'} or None if the vertical's map already covers NRR directly.
    """
    entry = POWER_OF_1_PILLAR_MAPS.get(vertical)
    if entry:
        return entry['pillar_metric_map'], entry['nrr_synthesis']

    from utils.vertical_registry import get_pillars
    try:
        pillar_codes = sorted(get_pillars(vertical).keys())
    except Exception:
        pillar_codes = []
    generic_map = {
        code: _GENERIC_METRIC_FALLBACK_ORDER[i % len(_GENERIC_METRIC_FALLBACK_ORDER)]
        for i, code in enumerate(pillar_codes)
    }
    return generic_map, None


def _resolve_vertical(customer_id):
    """Resolve a customer's vertical, defaulting to dc2_s when customer_id is unknown."""
    if customer_id is None:
        return 'dc2_s'
    from utils.vertical_registry import get_vertical_for_customer
    return get_vertical_for_customer(customer_id)


def _pillar_metric_map_for_customer(customer_id):
    """Resolve a customer's vertical and return its pillar→metric map."""
    return _get_pillar_metric_map(_resolve_vertical(customer_id))


# ============================================================
# FEATURE TOGGLE
# ============================================================

def _is_revenue_intelligence_enabled(customer_id):
    # Check per-customer DB toggle first
    toggle = FeatureToggleModel.query.filter_by(
        customer_id=customer_id,
        feature_name='revenue_intelligence'
    ).first()
    if toggle:
        return toggle.enabled

    # Fallback: if no per-customer toggle, check global feature toggle
    try:
        from feature_toggles import feature_toggles, FeatureToggle
        return feature_toggles.is_enabled(FeatureToggle.REVENUE_INTELLIGENCE)
    except Exception:
        return False


# ============================================================
# BASELINE DEFAULTS — "no change" state from Power-of-1 model
# Used when DB has no historical data yet. Shows baseline=current
# (zero improvement), never fabricated numbers.
# ============================================================

def _get_baseline_actuals():
    """Return baseline-only actuals (no improvement) from Power-of-1 model."""
    try:
        from power_of_1_model import POWER_OF_1_METRICS
        return {
            mid: {"baseline": m.baseline, "current": m.baseline}
            for mid, m in POWER_OF_1_METRICS.items()
        }
    except Exception:
        return {}

def _get_baseline_current_values():
    """Return baseline current values from Power-of-1 model."""
    try:
        from power_of_1_model import POWER_OF_1_METRICS
        return {mid: m.baseline for mid, m in POWER_OF_1_METRICS.items()}
    except Exception:
        return {}


# ============================================================
# HISTORICAL ENDPOINT — "We proved it works"
# ============================================================

@outcome_roi_api.route('/api/outcome-roi/historical', methods=['GET'])
def get_historical_roi():
    """
    Historical outcome ROI: what the CS investment has already delivered.

    Query params:
        period: '3m', '6m', '12m' (default: '6m')
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 400

    customer_id = resolve_customer_id(db, customer_id)

    if not _is_revenue_intelligence_enabled(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    try:
        import os
        from outcome_roi_engine import calculate_historical_roi, learn_investment_from_actuals

        period = request.args.get('period', '6m')
        months = {'3m': 3, '6m': 6, '12m': 12}.get(period, 6)

        # Option A (stable-window baseline) — opt-in via env var or ?stable=N
        # Default 0 keeps legacy trailing-window behaviour; Option C's auditor
        # disclosure already covers the freshly-onboarded case automatically.
        try:
            skip_unstable_months = int(
                request.args.get('stable')
                or os.environ.get('ROI_HISTORICAL_SKIP_UNSTABLE_MONTHS', '0')
                or '0'
            )
        except (TypeError, ValueError):
            skip_unstable_months = 0

        # Get actual metric values from health trends
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None
        account_ids = [a.account_id for a in accounts]

        metric_actuals, data_source = _extract_historical_actuals(
            accounts, months, customer_id=customer_id,
            skip_unstable_months=skip_unstable_months,
        )

        # Learn investment model from execution history
        learned_investment = learn_investment_from_actuals(customer_id, account_ids, months)

        # Determine vertical from first account
        acct_vertical = getattr(accounts[0], 'vertical', None) if accounts else None

        historical_period_basis = (
            "stable_window" if skip_unstable_months > 0 else "trailing_window"
        )

        result = calculate_historical_roi(
            metric_actuals=metric_actuals,
            account_arr=total_arr,
            period_label=f"Last {months} Months",
            vertical=acct_vertical,
            learned_investment=learned_investment,
            data_source=data_source,
            period_basis=historical_period_basis,
        )

        from outcome_roi_engine import _result_to_dict
        return jsonify({
            'customer_id': customer_id,
            'model': 'outcome_roi',
            'data_source': data_source,
            'result': _result_to_dict(result),
            'last_updated': datetime.now().isoformat(),
        })

    except Exception as e:
        import traceback
        print(f"Historical ROI error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ============================================================
# FORWARD ENDPOINT — "Here's what's next"
# ============================================================

@outcome_roi_api.route('/api/outcome-roi/forward', methods=['GET'])
def get_forward_roi():
    """
    Forward outcome ROI: velocity-based projection with optional pillar boost.

    Uses per-pillar historical velocity (pts/month) with diminishing returns,
    instead of a flat improvement assumption. CEOs can boost specific pillars
    to model increased investment scenarios.

    Query params:
        months: Projection months (default: 6)
        mode: 'velocity' (default, data-driven) or 'flat' (legacy flat %)
        improvement_pct: Flat improvement % when mode=flat (default: 1.0)

    JSON body (POST) or query params for pillar_boost:
        pillar_boost: {"P2": 1.5, "P3": 2.0}  — multipliers on velocity
            1.0 = maintain current trajectory
            1.5 = 50% more investment → 50% faster improvement
            2.0 = double investment → double the velocity
            0.5 = reduce investment → half the velocity
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 400

    customer_id = resolve_customer_id(db, customer_id)

    if not _is_revenue_intelligence_enabled(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    try:
        from outcome_roi_engine import calculate_forward_roi, learn_investment_from_actuals

        projection_months = request.args.get('months', 6, type=int)
        mode = request.args.get('mode', 'velocity')

        # Parse pillar_boost from POST body or query param
        pillar_boost = {}
        fwd_body = request.get_json(silent=True) or {}
        if fwd_body.get('pillar_boost'):
            pillar_boost = fwd_body['pillar_boost']
        elif request.args.get('pillar_boost'):
            import json
            try:
                pillar_boost = json.loads(request.args.get('pillar_boost', '{}'))
            except (json.JSONDecodeError, TypeError):
                pass

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None
        account_ids = [a.account_id for a in accounts]
        current_values, data_source = _extract_current_values(accounts, customer_id=customer_id)
        fwd_vertical = getattr(accounts[0], 'vertical', None) if accounts else None

        # Learn investment model from execution history
        learned_investment = learn_investment_from_actuals(customer_id, account_ids, projection_months)

        if mode == 'velocity':
            # Velocity-based: per-pillar rates from historical data
            velocities, vel_source = _extract_pillar_velocities(accounts, months=projection_months)

            if velocities:
                # Build per-metric improvement rates from velocity
                per_metric_pcts = {}
                velocity_detail = {}
                for metric_id, vel in velocities.items():
                    pillar_code = vel['pillar_code']
                    boost = float(pillar_boost.get(pillar_code, 1.0))
                    boosted_pct = vel['projected_pct'] * boost

                    per_metric_pcts[metric_id] = boosted_pct

                    # Industry benchmark gap
                    industry_target = 4.0
                    base_pct = vel['projected_pct']
                    gap = max(0, industry_target - boosted_pct)
                    boost_needed = round(industry_target / base_pct, 1) if base_pct > 0 else 99.0

                    velocity_detail[pillar_code] = {
                        'pillar_name': vel['pillar_name'],
                        'metric_id': metric_id,
                        'velocity_per_month': vel['velocity_per_month'],
                        'headroom': vel['headroom'],
                        'decel_factor': vel['decel_factor'],
                        'base_projected_pct': vel['projected_pct'],
                        'boost_multiplier': boost,
                        'boosted_projected_pct': round(boosted_pct, 2),
                        'earliest_score': vel['earliest_score'],
                        'latest_score': vel['latest_score'],
                        'industry_target_pct': industry_target,
                        'gap_to_target_pct': round(gap, 2),
                        'boost_needed_for_target': min(boost_needed, 10.0),
                        'at_or_above_target': boosted_pct >= industry_target,
                    }

                result = calculate_forward_roi(
                    current_values=current_values,
                    target_improvement_pct=None,  # ignored when per_metric_pcts provided
                    per_metric_pcts=per_metric_pcts,
                    account_arr=total_arr,
                    projection_months=projection_months,
                    vertical=fwd_vertical,
                    learned_investment=learned_investment,
                )
                data_source = vel_source
            else:
                # Fallback to flat if no velocity data
                improvement_pct = request.args.get('improvement_pct', 1.0, type=float)
                result = calculate_forward_roi(
                    current_values=current_values,
                    target_improvement_pct=improvement_pct,
                    account_arr=total_arr,
                    projection_months=projection_months,
                    vertical=fwd_vertical,
                    learned_investment=learned_investment,
                )
                velocity_detail = {}
        else:
            # Legacy flat mode
            improvement_pct = request.args.get('improvement_pct', 1.0, type=float)
            result = calculate_forward_roi(
                current_values=current_values,
                target_improvement_pct=improvement_pct,
                account_arr=total_arr,
                projection_months=projection_months,
                vertical=fwd_vertical,
                learned_investment=learned_investment,
            )
            velocity_detail = {}

        from outcome_roi_engine import _result_to_dict
        response = {
            'customer_id': customer_id,
            'model': 'outcome_roi',
            'mode': mode,
            'data_source': data_source,
            'result': _result_to_dict(result),
            'last_updated': datetime.now().isoformat(),
        }
        if velocity_detail:
            response['velocity_detail'] = velocity_detail
        if pillar_boost:
            response['pillar_boost_applied'] = pillar_boost

        return jsonify(response)

    except Exception as e:
        import traceback
        print(f"Forward ROI error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ============================================================
# STORY ENDPOINT — Combined for demo
# ============================================================

@outcome_roi_api.route('/api/outcome-roi/story', methods=['GET', 'POST'])
def get_outcome_story():
    """
    Combined outcome story: historical proof + forward projection.

    Query params:
        improvement_pct: Forward target (default: 1.0, used when mode=flat)
        months: Forward projection months (default: 6)
        mode: 'velocity' (default, data-driven) or 'flat' (legacy)

    POST body (optional, for velocity mode):
        pillar_boost: {"P2": 1.5, "P3": 2.0} — multipliers on velocity
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 400

    customer_id = resolve_customer_id(db, customer_id)

    if not _is_revenue_intelligence_enabled(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    try:
        from outcome_roi_engine import calculate_outcome_story

        improvement_pct = request.args.get('improvement_pct', 1.0, type=float)
        projection_months = request.args.get('months', 6, type=int)
        mode = request.args.get('mode', 'velocity')

        # Parse pillar_boost from POST body or query param
        pillar_boost = {}
        body = request.get_json(silent=True) or {}
        if body.get('pillar_boost'):
            pillar_boost = body['pillar_boost']
        elif request.args.get('pillar_boost'):
            import json as _json
            try:
                pillar_boost = _json.loads(request.args.get('pillar_boost', '{}'))
            except (ValueError, TypeError):
                pass

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None
        account_ids = [a.account_id for a in accounts]

        metric_actuals, data_source = _extract_historical_actuals(accounts, 6, customer_id=customer_id)

        # ── Learn investment model from actual execution history ──
        from outcome_roi_engine import learn_investment_from_actuals
        learned_investment = learn_investment_from_actuals(
            customer_id=customer_id,
            account_ids=account_ids,
            months=projection_months,
        )

        # Identify at-risk accounts per Power of 1 metric
        accounts_at_risk = _extract_accounts_at_risk(accounts, customer_id=customer_id)

        # Determine vertical from first account (single-vertical portfolio)
        acct_vertical = getattr(accounts[0], 'vertical', None) if accounts else None

        # Velocity mode: extract per-pillar rates from historical data
        per_metric_pcts = None
        velocity_detail = {}
        if mode == 'velocity':
            velocities, vel_source = _extract_pillar_velocities(accounts, months=projection_months)
            if velocities:
                per_metric_pcts = {}
                for metric_id, vel in velocities.items():
                    pillar_code = vel['pillar_code']
                    boost = float(pillar_boost.get(pillar_code, 1.0))
                    boosted_pct = vel['projected_pct'] * boost
                    per_metric_pcts[metric_id] = boosted_pct

                    # Industry benchmark: 4% = "Target (Industry Leading)" scenario
                    industry_target = 4.0
                    base_pct = vel['projected_pct']
                    gap = max(0, industry_target - boosted_pct)
                    boost_needed = round(industry_target / base_pct, 1) if base_pct > 0 else 99.0

                    velocity_detail[pillar_code] = {
                        'pillar_name': vel['pillar_name'],
                        'metric_id': metric_id,
                        'velocity_per_month': vel['velocity_per_month'],
                        'headroom': vel['headroom'],
                        'decel_factor': vel['decel_factor'],
                        'base_projected_pct': vel['projected_pct'],
                        'boost_multiplier': boost,
                        'boosted_projected_pct': round(boosted_pct, 2),
                        'earliest_score': vel['earliest_score'],
                        'latest_score': vel['latest_score'],
                        # Gap to industry benchmark
                        'industry_target_pct': industry_target,
                        'gap_to_target_pct': round(gap, 2),
                        'boost_needed_for_target': min(boost_needed, 10.0),
                        'at_or_above_target': boosted_pct >= industry_target,
                    }
                data_source = vel_source

        story = calculate_outcome_story(
            metric_actuals=metric_actuals,
            target_improvement_pct=improvement_pct,
            account_arr=total_arr,
            projection_months=projection_months,
            accounts_at_risk=accounts_at_risk,
            customer_id=customer_id,
            account_ids=account_ids,
            vertical=acct_vertical,
            per_metric_pcts=per_metric_pcts,
            learned_investment=learned_investment,
            data_source=data_source,
        )

        # Persist ROI snapshot for audit trail and trending
        try:
            hist_summary = story.get('historical', {}).get('summary', {})
            fwd_summary = story.get('forward', {}).get('summary', {})
            combined = story.get('combined', {})
            snapshot = ROISnapshot(
                customer_id=customer_id,
                improvement_pct=improvement_pct,
                historical_roi_pct=hist_summary.get('roi_pct'),
                historical_impact=hist_summary.get('total_impact'),
                historical_investment=hist_summary.get('total_investment'),
                forward_roi_pct=fwd_summary.get('roi_pct'),
                forward_impact=fwd_summary.get('total_impact'),
                forward_investment=fwd_summary.get('total_investment'),
                combined_roi_pct=combined.get('combined_roi_pct'),
                total_arr=total_arr,
                metric_details={
                    'forward_metrics': [
                        {'id': m.get('metric_id'), 'impact': m.get('dollar_impact'), 'pct': m.get('improvement_pct')}
                        for m in story.get('forward', {}).get('metric_outcomes', [])
                    ]
                },
            )
            db.session.add(snapshot)
            db.session.commit()
        except Exception as snap_err:
            db.session.rollback()
            print(f"ROI snapshot save failed (non-fatal): {snap_err}")

        response = {
            'customer_id': customer_id,
            'model': 'outcome_roi',
            'mode': mode,
            'data_source': data_source,
            'story': story,
            'investment_model': {
                'source': learned_investment.source,
                'playbook_runs_observed': learned_investment.playbook_runs,
                'observation_months': learned_investment.observation_months,
                'learned_total': learned_investment.total_investment,
            },
            'last_updated': datetime.now().isoformat(),
        }
        if velocity_detail:
            response['velocity_detail'] = velocity_detail
        if pillar_boost:
            response['pillar_boost_applied'] = pillar_boost

        return jsonify(response)

    except Exception as e:
        import traceback
        print(f"Outcome story error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ============================================================
# TIMELINE ENDPOINT — Historical ROI + Context Graph Narrative
# ============================================================

@outcome_roi_api.route('/api/outcome-roi/timeline', methods=['GET'])
def get_outcome_timeline():
    """
    Month-by-month timeline correlating historical ROI metric movements
    with context graph signals, decisions, and outcomes.

    Shows how the system navigated different signals, saved money, and improved ROI.

    Requires: revenue_intelligence + context_graph feature toggles.

    Query params:
        period: '3m', '6m', '12m' (default: '6m')
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 400

    customer_id = resolve_customer_id(db, customer_id)

    if not _is_revenue_intelligence_enabled(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    try:
        from feature_toggles import is_context_graph_enabled
        if not is_context_graph_enabled(customer_id):
            return jsonify({'error': 'Context graph not enabled for this customer'}), 403
    except ImportError:
        return jsonify({'error': 'Context graph module not available'}), 500

    try:
        from outcome_roi_engine import build_historical_timeline

        period = request.args.get('period', '6m')
        months = {'3m': 3, '6m': 6, '12m': 12}.get(period, 6)

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        account_ids = [a.account_id for a in accounts]
        metric_actuals, _data_source = _extract_historical_actuals(accounts, months, customer_id=customer_id)

        timeline = build_historical_timeline(
            customer_id=customer_id,
            account_ids=account_ids,
            metric_actuals=metric_actuals,
            months=months,
        )

        if not timeline:
            return jsonify({'error': 'No context graph data available for this period'}), 404

        return jsonify({
            'status': 'success',
            'customer_id': customer_id,
            **timeline,
        })

    except Exception as e:
        import traceback
        print(f"Timeline error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ============================================================
# DEMO ENDPOINT — No DB needed, pre-loaded data
# ============================================================

@outcome_roi_api.route('/api/outcome-roi/demo', methods=['GET'])
def get_demo_outcome_story():
    """
    Demo mode: pre-loaded realistic data, no authentication or DB required.
    Perfect for presentations and demos.

    Query params:
        improvement_pct: Forward target (default: 1.0)
        months: Forward projection months (default: 6)
        arr: ARR in dollars (default: 10000000)
    """
    try:
        from outcome_roi_engine import calculate_outcome_story

        improvement_pct = request.args.get('improvement_pct', 1.0, type=float)
        projection_months = request.args.get('months', 6, type=int)
        arr = request.args.get('arr', 10_000_000, type=float)

        story = calculate_outcome_story(
            metric_actuals=_get_baseline_actuals(),
            target_improvement_pct=improvement_pct,
            account_arr=arr,
            projection_months=projection_months,
            historical_period_label="Last 6 Months (Realized)",
        )

        return jsonify({
            'customer_id': 'demo',
            'model': 'outcome_roi',
            'demo_mode': True,
            'arr': arr,
            'story': story,
            'last_updated': datetime.now().isoformat(),
        })

    except Exception as e:
        import traceback
        print(f"Demo outcome story error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ============================================================
# HELPERS — Extract metric values from DB
# ============================================================

def _is_calibrated(customer_id):
    """Check if Wizard C has calibrated weights for this customer."""
    if not customer_id:
        return False
    from models import CustomerConfig as _CC
    cfg = _CC.query.filter_by(customer_id=int(customer_id)).first()
    return bool(cfg and cfg.dc2s_kpi_weights)


def _tag_real_data_source(detail_prefix, *, calibrated, stable_tag=''):
    """Build the `data_source` value for a real-data extraction path
    (kpi_actuals / health_trends / health_score_pillars).

    Tier follows Wizard-C calibration state (see
    utils.value_provenance.calibration_tier): calibrated customers get
    DERIVED (their own learned weights applied to real data), everyone
    else gets BENCHMARK (real data read through default/benchmark
    weights because Wizard C hasn't run yet). `detail_prefix` and
    `stable_tag` are preserved verbatim in `.detail` as the granular
    breadcrumb — this is what the pre-retrofit ad-hoc strings
    (`kpi_actuals_benchmark`, `health_trends_calibrated`, etc.) used to
    be, still available via `.detail` for logging/audit trail.
    """
    tier = vp.calibration_tier(calibrated=calibrated)
    cal_suffix = '_calibrated' if calibrated else '_benchmark'
    return vp.tag(tier, f'{detail_prefix}{cal_suffix}{stable_tag}')


def _extract_historical_actuals(accounts, months, customer_id=None, skip_unstable_months=0):
    """
    Extract historical metric actuals from DB.

    Priority: DC2SKPI (actual measurements, dc2_s only) → HealthTrend (SaaS)
    → HealthScore.contributing_pillars (generic scorer, every vertical) → baseline.
    Falls back to demo data only if no path has sufficient data.

    Args:
        accounts: List of Account rows for the customer.
        months: Trailing-window size for the historical view (e.g. 6 means
            "last 6 months of measurements").
        customer_id: Optional customer id used to detect Wizard-C calibration.
        skip_unstable_months: Option-A stable-window control. When > 0 we drop
            the earliest N distinct months of measurements per KPI before
            computing the baseline anchor. Default 0 preserves legacy
            behaviour. Set to 3 to skip the typical onboarding-ramp phase
            on freshly-loaded synthetic tenants (decline → recovery arcs).

    Returns:
        tuple: (metric_actuals dict, data_source ValueProvenance) — see
            utils.value_provenance; behaves as a plain str equal to its
            tier (measured/derived/benchmark/default/unavailable).
    """
    from power_of_1_model import POWER_OF_1_METRICS

    if not accounts:
        return _get_baseline_actuals(), vp.tag(vp.DEFAULT, 'baseline_defaults')

    account_ids = [a.account_id for a in accounts]
    calibrated = _is_calibrated(customer_id)
    skip_n = max(0, int(skip_unstable_months or 0))
    vertical = _resolve_vertical(customer_id)

    # ── Path 0: DC2SKPI (actual KPI measurements) ──
    # linked_kpi_codes in power_of_1_economics.json are dc2_s-specific KPI
    # codes with no per-vertical equivalent yet, so this path only applies
    # to dc2_s — other verticals fall through to Path 1/Path 2 below, which
    # resolve metrics through the vertical-aware pillar_metric_map instead.
    kpi_rows = []
    if vertical == 'dc2_s':
        from models import DC2SKPI as _DC2SKPI
        cutoff_dt = datetime.now() - timedelta(days=months * 30)
        kpi_rows = _DC2SKPI.query.filter(
            _DC2SKPI.account_id.in_(account_ids),
            _DC2SKPI.measured_at >= cutoff_dt,
        ).all()

    if len(kpi_rows) >= 2:
        # Build {kpi_code: [(measured_at, value), ...]} and collect targets
        from collections import defaultdict
        kpi_by_code = defaultdict(list)
        kpi_targets = {}  # kpi_code → target value
        for row in kpi_rows:
            kpi_by_code[row.kpi_code].append((row.measured_at, float(row.value)))
            if row.target and row.kpi_code not in kpi_targets:
                kpi_targets[row.kpi_code] = float(row.target)

        # For each kpi_code, compute earliest-avg and latest-avg
        kpi_earliest = {}  # kpi_code → avg value at earliest month
        kpi_latest = {}    # kpi_code → avg value at latest month
        for kpi_code, measurements in kpi_by_code.items():
            measurements.sort(key=lambda x: x[0])
            distinct_months = sorted({m[0].strftime('%Y-%m') for m in measurements})
            # Option A: skip the first N distinct months to anchor the baseline
            # past the onboarding-ramp / synthetic-decline phase. Guard against
            # eating all available data — leave at least 2 distinct months.
            if skip_n > 0 and len(distinct_months) > skip_n + 1:
                stable_months = set(distinct_months[skip_n:])
                measurements = [m for m in measurements if m[0].strftime('%Y-%m') in stable_months]
                if not measurements:
                    continue
            earliest_month = measurements[0][0].strftime('%Y-%m')
            latest_month = measurements[-1][0].strftime('%Y-%m')
            if earliest_month == latest_month and len(measurements) > 1:
                mid = len(measurements) // 2
                early_vals = [v for _, v in measurements[:mid]]
                late_vals = [v for _, v in measurements[mid:]]
            else:
                early_vals = [v for dt, v in measurements if dt.strftime('%Y-%m') == earliest_month]
                late_vals = [v for dt, v in measurements if dt.strftime('%Y-%m') == latest_month]

            kpi_earliest[kpi_code] = sum(early_vals) / len(early_vals) if early_vals else None
            kpi_latest[kpi_code] = sum(late_vals) / len(late_vals) if late_vals else None

        # Map linked_kpi_codes → Power-of-1 metrics using IMPROVEMENT-BASED mapping.
        # Each KPI's improvement is normalized as a fraction of its own scale,
        # then the average improvement fraction is applied to the Po1 metric baseline.
        # This prevents mixing units (e.g., RMA rate % with MTBF hours).
        metric_actuals = {}
        metrics_with_data = 0
        for metric_id, metric in POWER_OF_1_METRICS.items():
            linked = metric.linked_kpi_codes
            if not linked:
                continue

            improvement_fractions = []
            for kpi_code in linked:
                early = kpi_earliest.get(kpi_code)
                late = kpi_latest.get(kpi_code)
                if early is None or late is None:
                    continue
                target = kpi_targets.get(kpi_code, early)
                # Determine KPI direction from whether target > early baseline
                kpi_higher_is_better = target > early if target != early else True
                if kpi_higher_is_better:
                    # Higher is better: fraction of target achieved
                    denom = max(abs(target), abs(early), 1)
                    frac = (late - early) / denom
                else:
                    # Lower is better: fraction of reduction achieved
                    denom = max(abs(early), 1)
                    frac = (early - late) / denom
                improvement_fractions.append(frac)

            if improvement_fractions:
                avg_improvement = sum(improvement_fractions) / len(improvement_fractions)
                # Convert fraction to Power-of-1 percentage points
                po1_pct = avg_improvement * 100
                if metric.direction == "lower_is_better":
                    baseline_val = metric.baseline + (metric.one_pct_move * max(-po1_pct, 0))
                    current_val = metric.baseline - (metric.one_pct_move * max(po1_pct, 0))
                else:
                    baseline_val = metric.baseline - (metric.one_pct_move * max(po1_pct, 0))
                    current_val = metric.baseline + (metric.one_pct_move * max(po1_pct, 0))
                metric_actuals[metric_id] = {
                    "baseline": round(baseline_val, 2),
                    "current": round(current_val, 2),
                }
                metrics_with_data += 1

        # Need at least 2 metrics with actual data to use this path
        if metrics_with_data >= 2:
            # Fill gaps with static baselines
            for metric_id in POWER_OF_1_METRICS:
                if metric_id not in metric_actuals:
                    metric_actuals[metric_id] = {
                        "baseline": POWER_OF_1_METRICS[metric_id].baseline,
                        "current": POWER_OF_1_METRICS[metric_id].baseline,
                    }
            stable_tag = f"_stable_skip{skip_n}" if skip_n > 0 else ""
            return metric_actuals, _tag_real_data_source(
                'kpi_actuals', calibrated=calibrated, stable_tag=stable_tag,
            )

    # ── Path 1: HealthTrend (SaaS customers) ──
    trends = HealthTrend.query.filter(
        HealthTrend.account_id.in_(account_ids)
    ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).all()

    if len(trends) >= 2:
        # Aggregate by (year, month) across all accounts to get portfolio averages
        from collections import defaultdict
        month_buckets = defaultdict(list)
        for t in trends:
            month_buckets[(t.year, t.month)].append(t)

        sorted_months = sorted(month_buckets.keys())
        # Option A: skip first N months to anchor baseline on stable region
        if skip_n > 0 and len(sorted_months) > skip_n + 1:
            sorted_months = sorted_months[skip_n:]
        if len(sorted_months) >= 2:
            earliest_key = sorted_months[0]
            latest_key = sorted_months[-1]
            earliest_trends = month_buckets[earliest_key]
            latest_trends = month_buckets[latest_key]

            score_map = {
                'product_usage': 'product_adoption',
                'support': 'ticket_resolution_time',
                'customer_sentiment': 'GRR',
                'business_outcomes': 'NRR',
                'relationship_strength': 'expansion_rate',
            }

            def _avg_score(trend_list, attr):
                vals = [float(getattr(t, attr) or 0) for t in trend_list if getattr(t, attr, None) is not None]
                return sum(vals) / len(vals) if vals else 0

            metric_actuals = {}
            for score_key, metric_id in score_map.items():
                metric = POWER_OF_1_METRICS.get(metric_id)
                if not metric:
                    continue
                try:
                    latest_score = _avg_score(latest_trends, f'{score_key}_score')
                    earliest_score = _avg_score(earliest_trends, f'{score_key}_score')
                except (AttributeError, TypeError):
                    continue

                score_change = latest_score - earliest_score
                pct_improvement = score_change / 10.0

                if metric.direction == "lower_is_better":
                    current_value = metric.baseline - (metric.one_pct_move * pct_improvement)
                else:
                    current_value = metric.baseline + (metric.one_pct_move * pct_improvement)

                metric_actuals[metric_id] = {
                    "baseline": metric.baseline,
                    "current": round(current_value, 2),
                }

            # Fill gaps
            for metric_id in POWER_OF_1_METRICS:
                if metric_id not in metric_actuals:
                    metric_actuals[metric_id] = {
                        "baseline": POWER_OF_1_METRICS[metric_id].baseline,
                        "current": POWER_OF_1_METRICS[metric_id].baseline,
                    }

            stable_tag = f"_stable_skip{skip_n}" if skip_n > 0 else ""
            return metric_actuals, _tag_real_data_source(
                'health_trends', calibrated=calibrated, stable_tag=stable_tag,
            )

    # ── Path 2: HealthScore.contributing_pillars (generic scorer, every vertical) ──
    # PillarScore (the table this path used to read) is dead — confirmed zero
    # rows platform-wide, for every customer and every vertical, as of the
    # generic-scorer migration. contributing_pillars is the live equivalent:
    # a per-account, per-month JSON {"P1": score, ...} written by every
    # process_data run regardless of vertical.
    cutoff = datetime.now() - timedelta(days=months * 30)

    # Build the set of distinct months in the window so we can apply
    # Option-A stable-window skip without losing the trailing-window cutoff.
    distinct_months_rows = db.session.query(
        HealthScore.measurement_month
    ).filter(
        HealthScore.account_id.in_(account_ids),
        HealthScore.measurement_month >= cutoff,
    ).distinct().order_by(HealthScore.measurement_month.asc()).all()
    distinct_months = [r[0] for r in distinct_months_rows]

    # Fallback: use all available data if none in window
    if not distinct_months:
        distinct_months_rows = db.session.query(
            HealthScore.measurement_month
        ).filter(
            HealthScore.account_id.in_(account_ids),
        ).distinct().order_by(HealthScore.measurement_month.asc()).all()
        distinct_months = [r[0] for r in distinct_months_rows]

    if skip_n > 0 and len(distinct_months) > skip_n + 1:
        distinct_months = distinct_months[skip_n:]

    earliest_month = distinct_months[0] if distinct_months else None
    latest_month = distinct_months[-1] if distinct_months else None

    if not earliest_month or not latest_month:
        return _get_baseline_actuals(), vp.tag(vp.DEFAULT, 'baseline_defaults')

    # Average contributing_pillars across all accounts for earliest and latest months
    earliest_scores = HealthScore.query.filter(
        HealthScore.account_id.in_(account_ids),
        HealthScore.measurement_month == earliest_month,
    ).all()

    latest_scores = HealthScore.query.filter(
        HealthScore.account_id.in_(account_ids),
        HealthScore.measurement_month == latest_month,
    ).all()

    if not earliest_scores or not latest_scores:
        return _get_baseline_actuals(), vp.tag(vp.DEFAULT, 'baseline_defaults')

    def _avg_by_pillar(scores):
        """Average contributing_pillars scores across accounts."""
        totals = {}
        counts = {}
        for hs in scores:
            for code, val in (hs.contributing_pillars or {}).items():
                totals[code] = totals.get(code, 0) + float(val)
                counts[code] = counts.get(code, 0) + 1
        return {code: totals[code] / counts[code] for code in totals}

    early_avg = _avg_by_pillar(earliest_scores)
    late_avg = _avg_by_pillar(latest_scores)

    metric_actuals = {}
    pillar_metric_map, nrr_synthesis = _get_pillar_metric_map(vertical)

    for pillar_code, metric_id in pillar_metric_map.items():
        metric = POWER_OF_1_METRICS.get(metric_id)
        if not metric:
            continue

        early_val = early_avg.get(pillar_code, 50.0)
        late_val = late_avg.get(pillar_code, 50.0)
        score_change = late_val - early_val

        # 10 pillar points ≈ 1% Power-of-1 improvement
        pct_improvement = score_change / 10.0

        if metric.direction == "lower_is_better":
            # For lower-is-better: higher pillar score = lower metric value = better
            baseline_derived = metric.baseline - (metric.one_pct_move * (early_val - 50) / 10.0)
            current_derived = metric.baseline - (metric.one_pct_move * (late_val - 50) / 10.0)
        else:
            # For higher-is-better: higher pillar score = higher metric value = better
            baseline_derived = metric.baseline + (metric.one_pct_move * (early_val - 50) / 10.0)
            current_derived = metric.baseline + (metric.one_pct_move * (late_val - 50) / 10.0)

        metric_actuals[metric_id] = {
            "baseline": round(baseline_derived, 2),
            "current": round(current_derived, 2),
        }

    # Synthesize NRR from the vertical's retention + expansion pillars (weighted average)
    nrr_metric = POWER_OF_1_METRICS.get('NRR')
    if nrr_metric and nrr_synthesis:
        r_code, r_w = nrr_synthesis['retention_pillar'], nrr_synthesis['retention_weight']
        e_code, e_w = nrr_synthesis['expansion_pillar'], nrr_synthesis['expansion_weight']
        r_early = early_avg.get(r_code, 50.0)
        r_late = late_avg.get(r_code, 50.0)
        e_early = early_avg.get(e_code, 50.0)
        e_late = late_avg.get(e_code, 50.0)

        combined_early = r_early * r_w + e_early * e_w
        combined_late = r_late * r_w + e_late * e_w

        nrr_baseline = nrr_metric.baseline + (nrr_metric.one_pct_move * (combined_early - 50) / 10.0)
        nrr_current = nrr_metric.baseline + (nrr_metric.one_pct_move * (combined_late - 50) / 10.0)

        metric_actuals['NRR'] = {
            "baseline": round(nrr_baseline, 2),
            "current": round(nrr_current, 2),
        }

    # Fill any remaining gaps with static baselines (no improvement)
    for metric_id in POWER_OF_1_METRICS:
        if metric_id not in metric_actuals:
            metric_actuals[metric_id] = {
                "baseline": POWER_OF_1_METRICS[metric_id].baseline,
                "current": POWER_OF_1_METRICS[metric_id].baseline,
            }

    stable_tag = f"_stable_skip{skip_n}" if skip_n > 0 else ""
    return metric_actuals, _tag_real_data_source(
        'health_score_pillars', calibrated=calibrated, stable_tag=stable_tag,
    )


# ── Pillar velocity map: pillar_code → ROI metric_id ──
PILLAR_TO_METRIC = {
    'P1': 'product_adoption',
    'P2': 'ticket_resolution_time',
    'P3': 'GRR',
    'P4': 'NRR',
    'P5': 'expansion_rate',
}

# Also map human-readable pillar names for CEO-friendly API
PILLAR_NAMES = {
    'P1': 'Product Usage & Adoption',
    'P2': 'Support & Reliability',
    'P3': 'Customer Sentiment',
    'P4': 'Business Outcomes',
    'P5': 'Relationship & Expansion',
}


def _extract_pillar_velocities(accounts, months=6):
    """Extract per-pillar improvement velocity from health_trends.

    Computes monthly velocity (pts/month), current level, headroom to 100,
    and a deceleration-adjusted projected improvement for the next N months.

    Args:
        accounts: list of Account objects
        months: historical lookback period

    Returns:
        tuple: (velocities dict, data_source ValueProvenance) — see
            utils.value_provenance.
            velocities: {metric_id: {velocity, current, headroom, projected_pct, pillar_code}}
    """
    import math
    from power_of_1_model import POWER_OF_1_METRICS

    if not accounts:
        return {}, vp.tag(vp.UNAVAILABLE, 'no_data')

    account_ids = [a.account_id for a in accounts]

    # Aggregate health_trends by (year, month) across all accounts
    trends = HealthTrend.query.filter(
        HealthTrend.account_id.in_(account_ids)
    ).order_by(HealthTrend.year, HealthTrend.month).all()

    if len(trends) < 2:
        return {}, vp.tag(vp.UNAVAILABLE, 'insufficient_data')

    from collections import defaultdict
    month_buckets = defaultdict(list)
    for t in trends:
        month_buckets[(t.year, t.month)].append(t)

    sorted_months = sorted(month_buckets.keys())
    if len(sorted_months) < 2:
        return {}, vp.tag(vp.UNAVAILABLE, 'insufficient_data')

    earliest_key = sorted_months[0]
    latest_key = sorted_months[-1]
    earliest_trends = month_buckets[earliest_key]
    latest_trends = month_buckets[latest_key]

    # Number of months between earliest and latest
    num_months = (latest_key[0] - earliest_key[0]) * 12 + (latest_key[1] - earliest_key[1])
    if num_months < 1:
        num_months = 1

    score_keys = {
        'product_usage': ('P1', 'product_adoption'),
        'support': ('P2', 'ticket_resolution_time'),
        'customer_sentiment': ('P3', 'GRR'),
        'business_outcomes': ('P4', 'NRR'),
        'relationship_strength': ('P5', 'expansion_rate'),
    }

    def _avg_score(trend_list, attr):
        vals = [float(getattr(t, attr) or 0) for t in trend_list if getattr(t, attr, None) is not None]
        return sum(vals) / len(vals) if vals else 0

    velocities = {}
    for score_key, (pillar_code, metric_id) in score_keys.items():
        attr = f'{score_key}_score'
        earliest_score = _avg_score(earliest_trends, attr)
        latest_score = _avg_score(latest_trends, attr)

        velocity_per_month = (latest_score - earliest_score) / num_months
        headroom = max(0, 100.0 - latest_score)

        # Deceleration: as score approaches 100, gains diminish
        # decel_factor ranges 0→1: more headroom = more growth potential
        decel_factor = min(1.0, headroom / 50.0)

        # Projected additional score improvement over forward months
        # Uses diminishing returns: velocity * months * decel_factor * log_decay
        forward_months = months
        if velocity_per_month > 0:
            raw_gain = velocity_per_month * forward_months * decel_factor
            # Log decay: fast early, slower later
            log_decay = math.log1p(forward_months) / math.log1p(12)
            projected_gain = raw_gain * log_decay
        else:
            projected_gain = velocity_per_month * forward_months * 0.5  # declining pillar

        # Convert pillar score gain to ROI % improvement (10 pts = 1%)
        projected_pct = projected_gain / 10.0

        velocities[metric_id] = {
            'pillar_code': pillar_code,
            'pillar_name': PILLAR_NAMES.get(pillar_code, pillar_code),
            'earliest_score': round(earliest_score, 1),
            'latest_score': round(latest_score, 1),
            'velocity_per_month': round(velocity_per_month, 2),
            'headroom': round(headroom, 1),
            'decel_factor': round(decel_factor, 2),
            'projected_pct': round(projected_pct, 2),
        }

    # DERIVED (not calibration-gated like _tag_real_data_source): velocity
    # is computed purely from real HealthTrend rows via a fixed pillar->
    # metric map, with no dc2s_kpi_weights/benchmark blending involved.
    return velocities, vp.tag(vp.DERIVED, 'health_trends_velocity')


def _extract_current_values(accounts, customer_id=None):
    """
    Extract current metric values from latest health data.

    Tries DC2SKPI (actual measurements, dc2_s only) first, then HealthTrend (SaaS),
    then HealthScore.contributing_pillars (generic scorer, every vertical).

    Returns:
        tuple: (current_values dict, data_source ValueProvenance) — see
            utils.value_provenance.
    """
    from power_of_1_model import POWER_OF_1_METRICS

    if not accounts:
        return _get_baseline_current_values(), vp.tag(vp.DEFAULT, 'baseline_defaults')

    account_ids = [a.account_id for a in accounts]
    calibrated = _is_calibrated(customer_id)
    vertical = _resolve_vertical(customer_id)

    # ── Path 0: DC2SKPI (actual KPI measurements — latest values) ──
    # dc2_s only — see the matching comment in _extract_historical_actuals.
    from collections import defaultdict
    latest_kpis = []
    if vertical == 'dc2_s':
        from models import DC2SKPI as _DC2SKPI
        # Get most recent measurement per kpi_code per account
        latest_kpis = _DC2SKPI.query.filter(
            _DC2SKPI.account_id.in_(account_ids),
        ).order_by(_DC2SKPI.measured_at.desc()).all()

    if latest_kpis:
        # Keep only the latest measurement per (account_id, kpi_code) + targets
        seen = set()
        kpi_latest_vals = defaultdict(list)
        kpi_targets = {}
        for row in latest_kpis:
            key = (row.account_id, row.kpi_code)
            if key not in seen:
                seen.add(key)
                kpi_latest_vals[row.kpi_code].append(float(row.value))
                if row.target and row.kpi_code not in kpi_targets:
                    kpi_targets[row.kpi_code] = float(row.target)

        # Map to Power-of-1 metrics using improvement-based approach
        # Current state = Po1 baseline adjusted by how far current KPIs are from target
        current_values = {}
        metrics_with_data = 0
        for metric_id, metric in POWER_OF_1_METRICS.items():
            linked = metric.linked_kpi_codes
            if not linked:
                continue
            achievement_fracs = []
            for kpi_code in linked:
                kpi_vals = kpi_latest_vals.get(kpi_code, [])
                if not kpi_vals:
                    continue
                avg_val = sum(kpi_vals) / len(kpi_vals)
                target = kpi_targets.get(kpi_code)
                if not target:
                    continue
                # How close to target? 1.0 = at target, >1 = exceeding
                achievement = avg_val / target if target != 0 else 1.0
                achievement_fracs.append(achievement)
            if achievement_fracs:
                avg_achievement = sum(achievement_fracs) / len(achievement_fracs)
                # Map achievement to Po1 scale: 1.0 = at baseline, deviation maps via one_pct_move
                deviation_pct = (avg_achievement - 1.0) * 100
                if metric.direction == "lower_is_better":
                    current_values[metric_id] = round(metric.baseline - (metric.one_pct_move * deviation_pct), 2)
                else:
                    current_values[metric_id] = round(metric.baseline + (metric.one_pct_move * deviation_pct), 2)
                metrics_with_data += 1

        if metrics_with_data >= 2:
            for metric_id in POWER_OF_1_METRICS:
                if metric_id not in current_values:
                    current_values[metric_id] = POWER_OF_1_METRICS[metric_id].baseline
            return current_values, _tag_real_data_source('kpi_actuals', calibrated=calibrated)

    # ── Path 1: HealthTrend (SaaS) ──
    latest_trend = HealthTrend.query.filter(
        HealthTrend.account_id.in_(account_ids)
    ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).first()

    if latest_trend:
        score_map = {
            'product_usage': 'product_adoption',
            'support': 'ticket_resolution_time',
            'customer_sentiment': 'GRR',
            'business_outcomes': 'NRR',
            'relationship_strength': 'expansion_rate',
        }

        current_values = {}
        for score_key, metric_id in score_map.items():
            metric = POWER_OF_1_METRICS.get(metric_id)
            if not metric:
                continue
            try:
                score = float(getattr(latest_trend, f'{score_key}_score') or 0)
            except (AttributeError, TypeError):
                continue

            pct_from_baseline = score / 10.0
            if metric.direction == "lower_is_better":
                current_values[metric_id] = round(
                    metric.baseline - (metric.one_pct_move * pct_from_baseline), 2
                )
            else:
                current_values[metric_id] = round(
                    metric.baseline + (metric.one_pct_move * pct_from_baseline), 2
                )

        for metric_id in POWER_OF_1_METRICS:
            if metric_id not in current_values:
                current_values[metric_id] = POWER_OF_1_METRICS[metric_id].baseline

        return current_values, _tag_real_data_source('health_trends', calibrated=calibrated)

    # ── Path 2: HealthScore.contributing_pillars (generic scorer, every vertical) ──
    # PillarScore (the table this path used to read) is dead — see the matching
    # comment in _extract_historical_actuals.
    latest_month = db.session.query(
        db.func.max(HealthScore.measurement_month)
    ).filter(HealthScore.account_id.in_(account_ids)).scalar()

    if not latest_month:
        return _get_baseline_current_values(), vp.tag(vp.DEFAULT, 'baseline_defaults')

    latest_scores = HealthScore.query.filter(
        HealthScore.account_id.in_(account_ids),
        HealthScore.measurement_month == latest_month,
    ).all()

    if not latest_scores:
        return _get_baseline_current_values(), vp.tag(vp.DEFAULT, 'baseline_defaults')

    # Average contributing_pillars across accounts
    totals = {}
    counts = {}
    for hs in latest_scores:
        for code, val in (hs.contributing_pillars or {}).items():
            totals[code] = totals.get(code, 0) + float(val)
            counts[code] = counts.get(code, 0) + 1
    pillar_avgs = {code: totals[code] / counts[code] for code in totals}

    pillar_metric_map, nrr_synthesis = _get_pillar_metric_map(vertical)

    current_values = {}
    for pillar_code, metric_id in pillar_metric_map.items():
        metric = POWER_OF_1_METRICS.get(metric_id)
        if not metric:
            continue

        score = pillar_avgs.get(pillar_code, 50.0)
        pct_from_center = (score - 50) / 10.0

        if metric.direction == "lower_is_better":
            current_values[metric_id] = round(
                metric.baseline - (metric.one_pct_move * pct_from_center), 2
            )
        else:
            current_values[metric_id] = round(
                metric.baseline + (metric.one_pct_move * pct_from_center), 2
            )

    # Synthesize NRR from the vertical's retention + expansion pillars
    nrr_metric = POWER_OF_1_METRICS.get('NRR')
    if nrr_metric and nrr_synthesis:
        r_code, r_w = nrr_synthesis['retention_pillar'], nrr_synthesis['retention_weight']
        e_code, e_w = nrr_synthesis['expansion_pillar'], nrr_synthesis['expansion_weight']
        combined = pillar_avgs.get(r_code, 50.0) * r_w + pillar_avgs.get(e_code, 50.0) * e_w
        pct = (combined - 50) / 10.0
        current_values['NRR'] = round(
            nrr_metric.baseline + (nrr_metric.one_pct_move * pct), 2
        )

    for metric_id in POWER_OF_1_METRICS:
        if metric_id not in current_values:
            current_values[metric_id] = POWER_OF_1_METRICS[metric_id].baseline

    return current_values, _tag_real_data_source('health_score_pillars', calibrated=calibrated)


def _extract_accounts_at_risk(accounts, customer_id=None):
    """
    Identify which specific accounts need attention for each Power of 1 metric.

    Uses HealthTrend (SaaS) first, then falls back to HealthScore.contributing_pillars
    (generic scorer, every vertical).
    Accounts with NO health data at all are skipped (not assumed at-risk).
    When context graph is enabled, enriches each at-risk entry with graph revenue data.

    Returns Dict[metric_id → List[{account_id, account_name, score, status, revenue, graph_revenue?}]]
    sorted by score ascending (worst first).
    """
    from power_of_1_model import POWER_OF_1_METRICS

    if not accounts:
        return {}

    # HealthTrend field → Power of 1 metric mapping (SaaS path)
    ht_score_map = {
        'product_usage_score': 'product_adoption',
        'support_score': 'ticket_resolution_time',
        'customer_sentiment_score': 'GRR',
        'business_outcomes_score': 'NRR',
        'relationship_strength_score': 'expansion_rate',
    }

    # PillarScore code → Power of 1 metric mapping, resolved per the account's
    # own vertical (falls back to dc2_s only when customer_id is unavailable).
    pillar_metric_map, _nrr_synthesis = _pillar_metric_map_for_customer(customer_id)

    # Real-data tier for every account below that gets a score at all —
    # DERIVED/BENCHMARK per Wizard-C calibration state, same convention as
    # _tag_real_data_source. Accounts with no data are simply absent from
    # `at_risk` output (never a fabricated UNAVAILABLE entry).
    account_data_tier = vp.calibration_tier(calibrated=_is_calibrated(customer_id))

    # Get latest health scores per account
    account_scores = {}  # account_id → {metric_id → score}
    account_map = {a.account_id: a for a in accounts}

    for account in accounts:
        aid = account.account_id

        # Try HealthTrend first (SaaS customers)
        latest_trend = HealthTrend.query.filter_by(
            account_id=aid
        ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).first()

        if latest_trend:
            scores = {}
            for score_key, metric_id in ht_score_map.items():
                try:
                    val = float(getattr(latest_trend, score_key) or 0)
                    scores[metric_id] = val
                except (AttributeError, TypeError):
                    scores[metric_id] = 0
            account_scores[aid] = scores
            continue

        # Fallback: HealthScore.contributing_pillars (generic scorer, every
        # vertical). PillarScore, the table this used to read, is dead — see
        # the matching comment in _extract_historical_actuals.
        latest_health_score = HealthScore.query.filter_by(
            account_id=aid
        ).order_by(HealthScore.measurement_month.desc()).first()

        if latest_health_score and latest_health_score.contributing_pillars:
            scores = {}
            for pillar_code, val in latest_health_score.contributing_pillars.items():
                metric_id = pillar_metric_map.get(pillar_code)
                if metric_id:
                    scores[metric_id] = float(val) if val else 0
            if scores:
                account_scores[aid] = scores
                continue

        # No data at all — skip this account (don't assume at-risk)

    # Build per-metric at-risk account lists using centralized thresholds
    at_risk = {}
    for metric_id in POWER_OF_1_METRICS:
        metric_accounts = []
        for acct_id, scores in account_scores.items():
            score = scores.get(metric_id)
            if score is None:
                continue  # No data for this metric → skip

            acct = account_map.get(acct_id)
            if not acct:
                continue

            if score < ht.healthy_min():  # Show at-risk and critical accounts
                status = ht.classify(score)
                metric_accounts.append({
                    'account_id': acct_id,
                    'account_name': acct.account_name or f'Account {acct_id}',
                    'score': round(score, 1),
                    'status': status,
                    'revenue': float(acct.revenue) if acct.revenue else 0,
                    'value_provenance': account_data_tier,
                })

        # Sort by score ascending (worst first), then by revenue descending (highest value at risk)
        metric_accounts.sort(key=lambda x: (x['score'], -x['revenue']))
        at_risk[metric_id] = metric_accounts

    # TTFV doesn't map to a single health score — use overall health
    # Identify accounts that are critical/at-risk overall as TTFV candidates
    ttfv_accounts = []
    for acct_id, scores in account_scores.items():
        avg_score = sum(scores.values()) / max(len(scores), 1)
        acct = account_map.get(acct_id)
        if acct and avg_score < ht.healthy_min():
            status = ht.classify(avg_score)
            ttfv_accounts.append({
                'account_id': acct_id,
                'account_name': acct.account_name or f'Account {acct_id}',
                'score': round(avg_score, 1),
                'status': status,
                'revenue': float(acct.revenue) if acct.revenue else 0,
                'value_provenance': account_data_tier,
            })
    ttfv_accounts.sort(key=lambda x: (x['score'], -x['revenue']))
    at_risk['TTFV'] = ttfv_accounts

    # Enrich with context graph revenue data (feature-toggle gated)
    if customer_id:
        try:
            from feature_toggles import is_context_graph_enabled
            if is_context_graph_enabled(customer_id):
                from utils.context_graph import get_revenue_at_risk
                for metric_id in at_risk:
                    for entry in at_risk[metric_id]:
                        try:
                            graph_rev = get_revenue_at_risk(entry['account_id'])
                            if graph_rev.get('node_count', 0) > 0:
                                entry['graph_revenue'] = graph_rev
                        except Exception:
                            pass
        except ImportError:
            pass

    return at_risk


# ============================================================
# HISTORICAL DETAILS — Account-Level Evidence Drill-Down
# ============================================================

def _serialize_signal(sig):
    """Serialize a QualitativeSignal for API response."""
    return {
        'signal_id': sig.signal_id,
        'date': sig.signal_date.isoformat() if sig.signal_date else None,
        'type': sig.signal_type,
        'content': (sig.content or '')[:200],  # Truncate long text
        'sentiment': sig.sentiment,
        'sentiment_score': float(sig.sentiment_score) if sig.sentiment_score else None,
        'stakeholder_level': sig.stakeholder_level,
        'stakeholder_title': sig.stakeholder_title,
    }


def _serialize_playbook(pb):
    """Serialize a PlaybookExecution for API response."""
    exec_data = pb.execution_data or {}
    return {
        'execution_id': pb.execution_id,
        'playbook_id': pb.playbook_id,
        'playbook_name': getattr(pb, 'playbook_name', None) or exec_data.get('playbook_name', pb.playbook_id),
        'status': pb.status,
        'outcome': getattr(pb, 'outcome', None),
        'outcome_notes': getattr(pb, 'outcome_notes', None),
        'started_at': pb.started_at.isoformat() if pb.started_at else None,
        'completed_at': pb.completed_at.isoformat() if pb.completed_at else None,
        'current_step': pb.current_step,
    }


def _compute_kpi_improvements(account_id, cutoff_date):
    """
    Compute top KPI improvements for an account within the period.
    Falls back to all available data if no data exists after cutoff.
    Returns list of {kpi_code, start_value, end_value, start_score, end_score, delta_score}.
    """
    # Get earliest scores in period (fallback to all data if none after cutoff)
    earliest_month = db.session.query(
        db.func.min(KPIScore.measurement_month)
    ).filter(
        KPIScore.account_id == account_id,
        KPIScore.measurement_month >= cutoff_date,
    ).scalar()

    # Fallback: no data after cutoff → use all available data
    if not earliest_month:
        earliest_month = db.session.query(
            db.func.min(KPIScore.measurement_month)
        ).filter(KPIScore.account_id == account_id).scalar()

    if not earliest_month:
        return []

    # Get latest month
    latest_month = db.session.query(
        db.func.max(KPIScore.measurement_month)
    ).filter(
        KPIScore.account_id == account_id,
    ).scalar()

    if not latest_month:
        return []

    # Single month: show current scores as snapshot (no delta)
    if earliest_month == latest_month:
        latest_scores = KPIScore.query.filter_by(
            account_id=account_id,
            measurement_month=latest_month,
        ).all()

        snapshot = []
        for s in latest_scores:
            score = float(s.kpi_score) if s.kpi_score else 0
            snapshot.append({
                'kpi_code': s.kpi_code,
                'start_value': None,
                'end_value': float(s.kpi_value) if s.kpi_value else None,
                'start_score': 0,
                'end_score': round(score, 1),
                'delta_score': round(score, 1),  # Treat current score as delta from 0
                'status': s.kpi_status,
            })
        snapshot.sort(key=lambda x: x['end_score'], reverse=True)
        return snapshot[:8]

    # Multiple months: compute delta between earliest and latest
    earliest_scores = KPIScore.query.filter_by(
        account_id=account_id,
        measurement_month=earliest_month,
    ).all()

    latest_scores = KPIScore.query.filter_by(
        account_id=account_id,
        measurement_month=latest_month,
    ).all()

    earliest_map = {s.kpi_code: s for s in earliest_scores}
    latest_map = {s.kpi_code: s for s in latest_scores}

    improvements = []
    for kpi_code in latest_map:
        if kpi_code not in earliest_map:
            continue
        e = earliest_map[kpi_code]
        l = latest_map[kpi_code]
        e_score = float(e.kpi_score) if e.kpi_score else 0
        l_score = float(l.kpi_score) if l.kpi_score else 0
        delta = l_score - e_score

        improvements.append({
            'kpi_code': kpi_code,
            'start_value': float(e.kpi_value) if e.kpi_value else None,
            'end_value': float(l.kpi_value) if l.kpi_value else None,
            'start_score': round(e_score, 1),
            'end_score': round(l_score, 1),
            'delta_score': round(delta, 1),
            'status': l.kpi_status,
        })

    # Sort by delta descending — most improved first
    improvements.sort(key=lambda x: x['delta_score'], reverse=True)
    return improvements[:8]  # Top 8


def _compute_pillar_changes(account_id, cutoff_date):
    """
    Compute pillar score changes for an account within the period.
    Falls back to all available data if no data exists after cutoff.
    Returns list of {pillar_code, start_score, end_score, delta}.

    Reads HealthScore.contributing_pillars (generic scorer, every vertical).
    PillarScore, the table this used to read, is dead — see the matching
    comment in _extract_historical_actuals.
    """
    earliest_month = db.session.query(
        db.func.min(HealthScore.measurement_month)
    ).filter(
        HealthScore.account_id == account_id,
        HealthScore.measurement_month >= cutoff_date,
    ).scalar()

    # Fallback: no data after cutoff → use all available data
    if not earliest_month:
        earliest_month = db.session.query(
            db.func.min(HealthScore.measurement_month)
        ).filter(HealthScore.account_id == account_id).scalar()

    latest_month = db.session.query(
        db.func.max(HealthScore.measurement_month)
    ).filter(
        HealthScore.account_id == account_id,
    ).scalar()

    if not earliest_month or not latest_month:
        return [], None, None

    # Single month: show current pillar scores as snapshot
    if earliest_month == latest_month:
        latest_score = HealthScore.query.filter_by(
            account_id=account_id,
            measurement_month=latest_month,
        ).first()

        l_map = {code: float(val) if val else 0 for code, val in (latest_score.contributing_pillars or {}).items()} if latest_score else {}
        changes = []
        for code in sorted(l_map.keys()):
            changes.append({
                'pillar_code': code,
                'start_score': 0,
                'end_score': round(l_map[code], 1),
                'delta': 0,  # No delta for single month
            })
        health_end = round(sum(l_map.values()) / max(len(l_map), 1), 1) if l_map else None
        return changes, health_end, health_end  # start=end for single month

    # Multiple months: compute delta
    earliest_score = HealthScore.query.filter_by(
        account_id=account_id,
        measurement_month=earliest_month,
    ).first()

    latest_score = HealthScore.query.filter_by(
        account_id=account_id,
        measurement_month=latest_month,
    ).first()

    e_map = {code: float(val) if val else 0 for code, val in (earliest_score.contributing_pillars or {}).items()} if earliest_score else {}
    l_map = {code: float(val) if val else 0 for code, val in (latest_score.contributing_pillars or {}).items()} if latest_score else {}

    changes = []
    for code in sorted(set(list(e_map.keys()) + list(l_map.keys()))):
        e_val = e_map.get(code, 0)
        l_val = l_map.get(code, 0)
        changes.append({
            'pillar_code': code,
            'start_score': round(e_val, 1),
            'end_score': round(l_val, 1),
            'delta': round(l_val - e_val, 1),
        })

    # Overall health: average of pillar scores (simple avg for now)
    health_start = round(sum(e_map.values()) / max(len(e_map), 1), 1) if e_map else None
    health_end = round(sum(l_map.values()) / max(len(l_map), 1), 1) if l_map else None

    return changes, health_start, health_end


@outcome_roi_api.route('/api/outcome-roi/historical-details', methods=['GET'])
def get_historical_details():
    """
    Per-account evidence for historical ROI period.

    Returns expansion/churn signals, playbook actions, KPI improvements,
    and pillar changes for each account — sorted by revenue descending.

    Query params:
        period: '3m', '6m', '12m' (default: '6m')
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 400

    customer_id = resolve_customer_id(db, customer_id)

    if not _is_revenue_intelligence_enabled(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    try:
        period = request.args.get('period', '6m')
        months = {'3m': 3, '6m': 6, '12m': 12}.get(period, 6)
        cutoff = datetime.now() - timedelta(days=months * 30)
        cutoff_date = cutoff.date()

        accounts = Account.query.filter_by(customer_id=customer_id).all()

        result = []
        for account in accounts:
            aid = account.account_id
            revenue = float(account.revenue) if account.revenue else 0

            # 1. Qualitative signals — expansion vs churn
            signals = QualitativeSignal.query.filter(
                QualitativeSignal.account_id == aid,
                QualitativeSignal.signal_date >= cutoff_date,
            ).order_by(QualitativeSignal.signal_date.desc()).all()

            # Fallback: if no signals in period, show most recent 20
            if not signals:
                signals = QualitativeSignal.query.filter(
                    QualitativeSignal.account_id == aid,
                ).order_by(QualitativeSignal.signal_date.desc()).limit(20).all()

            expansion_signals = [s for s in signals if s.sentiment == 'positive']
            churn_signals = [s for s in signals if s.sentiment == 'negative']
            neutral_signals = [s for s in signals if s.sentiment not in ('positive', 'negative')]

            # 2. Playbook executions
            playbooks = PlaybookExecution.query.filter(
                PlaybookExecution.account_id == aid,
                PlaybookExecution.customer_id == customer_id,
                PlaybookExecution.started_at >= cutoff,
            ).order_by(PlaybookExecution.started_at.desc()).all()

            # Fallback: show all playbooks for this account
            if not playbooks:
                playbooks = PlaybookExecution.query.filter(
                    PlaybookExecution.account_id == aid,
                    PlaybookExecution.customer_id == customer_id,
                ).order_by(PlaybookExecution.started_at.desc()).all()

            # 3. KPI improvements (top 8 by score delta)
            kpi_improvements = _compute_kpi_improvements(aid, cutoff_date)

            # 4. Pillar score changes + health delta
            pillar_changes, health_start, health_end = _compute_pillar_changes(aid, cutoff_date)
            health_delta = round(health_end - health_start, 1) if (health_start is not None and health_end is not None) else None

            # 5. Classify account risk status
            risk_status = 'healthy'
            if health_end is not None:
                risk_status = ht.classify(health_end)

            result.append({
                'account_id': aid,
                'account_name': account.account_name or f'Account {aid}',
                'revenue': revenue,
                'industry': account.industry,
                'risk_status': risk_status,
                'health_score_start': health_start,
                'health_score_end': health_end,
                'health_delta': health_delta,
                # No data path produced a pillar-score snapshot for this
                # account/window: literal UNAVAILABLE, never a silent
                # default masquerading as a real health score.
                'health_score_provenance': vp.DERIVED if health_end is not None else vp.UNAVAILABLE,
                'expansion_signals': [_serialize_signal(s) for s in expansion_signals[:5]],
                'churn_signals': [_serialize_signal(s) for s in churn_signals[:5]],
                'signal_summary': {
                    'total': len(signals),
                    'positive': len(expansion_signals),
                    'negative': len(churn_signals),
                    'neutral': len(neutral_signals),
                },
                'playbooks': [_serialize_playbook(p) for p in playbooks],
                'kpi_improvements': kpi_improvements,
                'pillar_changes': pillar_changes,
            })

        # Sort by revenue descending — highest-value accounts first
        result.sort(key=lambda a: a['revenue'], reverse=True)

        return jsonify({
            'accounts': result,
            'period': period,
            'months': months,
            'cutoff': cutoff.isoformat(),
            'total_accounts': len(result),
            'total_revenue': sum(a['revenue'] for a in result),
        })

    except Exception as e:
        import traceback
        print(f"Historical details error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ─── Portfolio Summary (CEO Dashboard) ───────────────────────────────────────

@outcome_roi_api.route('/api/outcome-roi/portfolio-summary', methods=['GET'])
def get_portfolio_summary():
    """
    Portfolio-level ROI summary for the CEO dashboard.

    Aggregates ROI snapshots across all customers in the portfolio,
    plus context-graph revenue metrics and NRR.  Falls back to the
    single-customer view when portfolio_id is not provided.

    Returns:
        roi_pct, portfolio_roi, nrr, net_revenue_retention,
        revenue_at_risk, revenue_protected, expansion_pipeline,
        total_arr, customer_count
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        customer_id = resolve_customer_id(db, customer_id)

        # Gather accounts for this customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        account_ids = [a.account_id for a in accounts]
        total_arr = sum(float(a.revenue) if a.revenue else 0 for a in accounts)

        # ROI from latest snapshot
        roi_snap = (
            ROISnapshot.query
            .filter_by(customer_id=customer_id)
            .order_by(ROISnapshot.snapshot_date.desc(), ROISnapshot.created_at.desc())
            .first()
        )
        roi_pct = 0
        if roi_snap:
            roi_pct = round(roi_snap.historical_roi_pct or roi_snap.combined_roi_pct or 0)

        # NRR from the authoritative source (Wizard B PatternAnalyzer) — the
        # same logic that powers /api/revenue-intelligence/nrr-forecast, so
        # both endpoints agree instead of drifting. Prior code used a
        # hand-rolled health→churn heuristic that defaulted to 100 on any
        # failure (stale placeholder); fall back to 100 only if the analyzer
        # genuinely can't produce a forecast.
        nrr = 100
        try:
            import sys as _sys
            from pathlib import Path as _Path
            _wb_dir = str(_Path(__file__).parent / 'verticals' / '_template' / 'journey' / 'wizard_b')
            if _wb_dir not in _sys.path:
                _sys.path.insert(0, _wb_dir)
            from wizard_b_pattern_analyzer import PatternAnalyzer as _PA
            _analyzer = _PA.from_database(customer_id)
            _analyzer.analyze_patterns()
            if _analyzer.portfolio_nrr_forecast:
                nrr = round(_analyzer.portfolio_nrr_forecast.get('current_nrr_pct') or 100, 1)
        except Exception:
            pass  # keep nrr=100 default

        # Revenue from context graph (shared util)
        from utils.context_graph import aggregate_revenue_across_accounts
        revenue_data = aggregate_revenue_across_accounts(customer_id, account_ids)

        return jsonify({
            'status': 'success',
            'roi_pct': roi_pct,
            'portfolio_roi': roi_pct,
            'nrr': nrr,
            'net_revenue_retention': nrr,
            'revenue_at_risk': revenue_data['revenue_at_risk'],
            'revenue_protected': revenue_data['revenue_protected'],
            'expansion_pipeline': revenue_data['expansion_pipeline'],
            'total_arr': round(total_arr, 2),
            'customer_count': 1,  # single-customer scope
            'account_count': len(accounts),
            'source': 'roi_snapshot + context_graph',
        })

    except Exception as e:
        import traceback
        print(f"Portfolio summary error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ─── Playbook Economics ──────────────────────────────────────────────────────

@outcome_roi_api.route('/api/outcome-roi/playbook-economics', methods=['GET'])
def playbook_economics():
    """
    Playbook cost bridge economics — investment breakdown, hours, ROI per playbook.

    Query params:
        account_arr  (optional, defaults to portfolio ARR sum)

    Returns per-metric and per-playbook economics from Power-of-1 benchmarks,
    PLAYBOOK_CONFIG hours, and CSM hourly rate.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        from playbook_cost_bridge import calculate_cost_bridge, bridge_to_dict

        account_arr = request.args.get('account_arr', type=float)
        if not account_arr:
            accounts = Account.query.filter(
                Account.customer_id == customer_id,
            ).all()
            account_arr = float(sum(
                float(a.revenue) if a.revenue else 0 for a in accounts
            )) if accounts else 10_000_000

        # Resolve tenant vertical so SaaS tenants get SaaS playbook catalog (bug B-5).
        try:
            from models import Customer, CustomerConfig
            from utils.vertical_registry import normalize_vertical
            cfg = CustomerConfig.query.filter_by(customer_id=int(customer_id)).first()
            if cfg and cfg.vertical:
                vertical = normalize_vertical(cfg.vertical)
            else:
                cust = Customer.query.get(int(customer_id))
                vertical = normalize_vertical(getattr(cust, 'vertical', None) or 'dc2_s')
        except Exception:
            vertical = 'dc2_s'

        result = calculate_cost_bridge(account_arr=account_arr, vertical=vertical)
        return jsonify({
            'status': 'success',
            'customer_id': customer_id,
            'effective_arr': account_arr,
            **bridge_to_dict(result),
        })

    except Exception as e:
        import traceback
        print(f"Playbook economics error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ─── Playbook Success Metrics (actual execution outcomes) ─────────────────────

@outcome_roi_api.route('/api/outcome-roi/playbook-success-metrics', methods=['GET'])
@outcome_roi_api.route('/api/v1/playbook-success-metrics', methods=['GET'])
def playbook_success_metrics():
    """Actual playbook execution success rates and revenue impact from V2 records.

    Unlike /playbook-economics (model-based projections), this returns ACTUAL
    outcomes from PlaybookExecutionV2: resolved/escalated counts, health deltas,
    revenue protected/expanded, ROI multiples.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        from models import PlaybookExecutionV2
        from collections import defaultdict

        execs = PlaybookExecutionV2.query.filter_by(customer_id=customer_id).all()

        if not execs:
            return jsonify({
                'scope': 'portfolio',
                'customer_id': customer_id,
                'total_executions': 0,
                'playbooks': {},
                'portfolio_summary': {'total_runs': 0, 'overall_success_rate_pct': 0},
            })

        by_pb = defaultdict(list)
        for e in execs:
            by_pb[e.playbook_id].append(e)

        playbooks = {}
        total_resolved = 0
        total_runs = 0
        total_revenue = 0
        total_cost = 0

        for pb_id, pb_execs in by_pb.items():
            n = len(pb_execs)
            resolved = sum(1 for e in pb_execs if e.outcome == 'resolved')
            escalated = sum(1 for e in pb_execs if e.outcome == 'escalated')
            timeout = sum(1 for e in pb_execs if e.outcome == 'timeout')

            health_deltas = [float(e.health_delta or 0) for e in pb_execs if e.health_delta]
            rev_protected = sum(float(e.revenue_protected or 0) for e in pb_execs)
            rev_expanded = sum(float(e.revenue_expanded or 0) for e in pb_execs)
            cost = sum(float(e.total_cost or 0) for e in pb_execs)

            playbooks[pb_id] = {
                'playbook_id': pb_id,
                'total_executions': n,
                'resolved': resolved,
                'escalated': escalated,
                'timeout': timeout,
                'success_rate_pct': round(resolved / max(n, 1) * 100, 0),
                'avg_health_delta': round(sum(health_deltas) / max(len(health_deltas), 1), 1),
                'revenue_protected': rev_protected,
                'revenue_expanded': rev_expanded,
                'total_cost': cost,
                'roi_x': round((rev_protected + rev_expanded) / max(cost, 1), 1),
            }

            total_resolved += resolved
            total_runs += n
            total_revenue += rev_protected + rev_expanded
            total_cost += cost

        return jsonify({
            'scope': 'portfolio',
            'customer_id': customer_id,
            'total_executions': total_runs,
            'playbooks': playbooks,
            'portfolio_summary': {
                'total_runs': total_runs,
                'overall_success_rate_pct': round(total_resolved / max(total_runs, 1) * 100, 0),
                'total_revenue_protected': total_revenue,
                'total_cost': total_cost,
                'portfolio_roi_x': round(total_revenue / max(total_cost, 1), 1),
            },
        })

    except Exception as e:
        import traceback
        print(f"Playbook success metrics error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ─── Per-Account ROI ──────────────────────────────────────────────────────────

@outcome_roi_api.route('/api/outcome-roi/account/<int:account_id>', methods=['GET'])
def get_account_roi(account_id):
    """
    Per-account ROI story — drill from portfolio ROI into individual account.
    Shows: playbook investment, revenue impact, causal chain summary, ROI.

    Uses ActionEconomics for actual costs when available, falls back to
    Power-of-1 benchmark allocation by account ARR share.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        from models import Account, ActionEconomics, PlaybookExecution, ContextNode
        from utils.context_graph import get_revenue_at_risk

        account = Account.query.get(account_id)
        if not account or account.customer_id != customer_id:
            return jsonify({'error': 'Account not found'}), 404

        arr = float(account.revenue or 0)

        # ── Actual playbook costs from ActionEconomics ──
        action_records = ActionEconomics.query.filter_by(
            customer_id=customer_id,
            account_id=account_id,
        ).order_by(ActionEconomics.completed_at.desc()).all()

        actual_investment = sum(float(a.total_action_cost or 0) for a in action_records)
        actual_impact = sum(float(a.dollar_impact_annual or 0) for a in action_records)
        playbook_runs = len(action_records)
        total_hours = sum(
            float(a.csm_hours or 0) + float(a.cs_ops_hours or 0)
            + float(a.product_hours or 0) + float(a.platform_hours or 0)
            + float(a.leadership_hours or 0)
            for a in action_records
        )

        # ── Revenue from context graph ──
        revenue = get_revenue_at_risk(account_id)

        # ── Benchmark allocation (if no actuals) ──
        source = 'actual' if action_records else 'benchmark'
        if not action_records and arr > 0:
            # Allocate portfolio benchmark by ARR share
            all_accounts = Account.query.filter_by(customer_id=customer_id).all()
            total_portfolio_arr = sum(float(a.revenue or 0) for a in all_accounts)
            arr_share = arr / total_portfolio_arr if total_portfolio_arr > 0 else 0

            from executive_dashboard_api import _get_po1_benchmark_investment, _get_po1_benchmark_metrics
            portfolio_investment = _get_po1_benchmark_investment(total_portfolio_arr)
            portfolio_impact = sum(m.get('dollar_impact', 0) for m in _get_po1_benchmark_metrics(total_portfolio_arr))

            actual_investment = round(portfolio_investment * arr_share, 2)
            actual_impact = round(portfolio_impact * arr_share, 2)

        roi_pct = round((actual_impact / actual_investment - 1) * 100) if actual_investment > 0 else 0

        # ── Causal chain summary ──
        signal_count = ContextNode.query.filter_by(
            customer_id=customer_id, account_id=account_id, node_type='SIGNAL'
        ).count()
        decision_count = ContextNode.query.filter_by(
            customer_id=customer_id, account_id=account_id, node_type='DECISION'
        ).count()
        outcome_count = ContextNode.query.filter_by(
            customer_id=customer_id, account_id=account_id, node_type='OUTCOME'
        ).count()

        # ── Playbook execution details ──
        playbook_details = []
        for ae in action_records:
            playbook_details.append({
                'playbook_id': ae.action_id,
                'playbook_name': ae.action_name,
                'hours': round(float(ae.csm_hours or 0) + float(ae.cs_ops_hours or 0), 1),
                'cost': float(ae.total_action_cost or 0),
                'impact': float(ae.dollar_impact_annual or 0),
                'roi': float(ae.roi or 0),
                'health_improvement': float(ae.improvement_pct or 0),
                'completed_at': ae.completed_at.isoformat() if ae.completed_at else None,
            })

        return jsonify({
            'status': 'success',
            'account_id': account_id,
            'account_name': account.account_name,
            'arr': arr,
            'source': source,  # 'actual' or 'benchmark'
            'investment': round(actual_investment, 2),
            'impact': round(actual_impact, 2),
            'roi_pct': roi_pct,
            'playbook_runs': playbook_runs,
            'total_hours': round(total_hours, 1),
            'revenue': {
                'at_risk': revenue.get('at_risk', 0),
                'protected': revenue.get('protected', 0),
                'expansion': revenue.get('expansion', 0),
            },
            'causal_chain': {
                'signals': signal_count,
                'decisions': decision_count,
                'outcomes': outcome_count,
            },
            'playbook_details': playbook_details,
        })

    except Exception as e:
        import traceback
        print(f"Account ROI error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500
