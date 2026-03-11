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
  GET  /api/outcome-roi/demo                — Pre-loaded demo data (no DB needed)
  GET  /api/outcome-roi/historical-details  — Per-account evidence drill-down

Feature flag: 'revenue_intelligence'
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import (
    Account, HealthTrend, FeatureToggle as FeatureToggleModel, ROISnapshot,
    QualitativeSignal, PlaybookExecution, KPIScore, PillarScore,
)
from resolve_identifier import resolve_customer_id
import utils.health_thresholds as ht

outcome_roi_api = Blueprint('outcome_roi_api', __name__)

# PillarScore → Power-of-1 metric mapping (DC2S vertical)
# Used by _extract_historical_actuals, _extract_current_values, _extract_accounts_at_risk
DC2S_PILLAR_METRIC_MAP = {
    'P1': 'TTFV',                    # Deployment Velocity → Time-to-First-Value
    'P2': 'ticket_resolution_time',  # Operational Stability → Support metric
    'P3': 'product_adoption',        # AI Workload Perf → Adoption
    'P4': 'GRR',                     # Channel & Partner → Gross Revenue Retention
    'P5': 'expansion_rate',          # Expansion Readiness → Expansion Rate
}
# NRR synthesized from P4 (retention) + P5 (expansion) weighted average


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
# DEMO DATA — Pre-loaded realistic scenario
# ============================================================

# Realistic historical actuals: what a customer achieved after 6 months
DEMO_HISTORICAL_ACTUALS = {
    "TTFV": {"baseline": 30.0, "current": 27.5},           # 30→27.5 days
    "NRR": {"baseline": 105.0, "current": 108.2},          # 105→108.2%
    "GRR": {"baseline": 85.0, "current": 87.1},            # 85→87.1%
    "ticket_resolution_time": {"baseline": 48.0, "current": 43.0},  # 48→43 hrs
    "product_adoption": {"baseline": 65.0, "current": 68.5},        # 65→68.5%
    "expansion_rate": {"baseline": 20.0, "current": 22.8},          # 20→22.8%
}

# After 6 months, where they currently stand (for forward projection baseline)
DEMO_CURRENT_VALUES = {
    "TTFV": 27.5,
    "NRR": 108.2,
    "GRR": 87.1,
    "ticket_resolution_time": 43.0,
    "product_adoption": 68.5,
    "expansion_rate": 22.8,
}

DEMO_ARR = 10_000_000  # $10M ARR


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
        from outcome_roi_engine import calculate_historical_roi

        period = request.args.get('period', '6m')
        months = {'3m': 3, '6m': 6, '12m': 12}.get(period, 6)

        # Get actual metric values from health trends
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None

        metric_actuals, data_source = _extract_historical_actuals(accounts, months)

        # Determine vertical from first account
        acct_vertical = getattr(accounts[0], 'vertical', None) if accounts else None

        result = calculate_historical_roi(
            metric_actuals=metric_actuals,
            account_arr=total_arr,
            period_label=f"Last {months} Months",
            vertical=acct_vertical,
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
    Forward outcome ROI: what the CS investment will deliver.

    Query params:
        improvement_pct: Target improvement % (default: 4.0)
        months: Projection months (default: 6)
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 400

    customer_id = resolve_customer_id(db, customer_id)

    if not _is_revenue_intelligence_enabled(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    try:
        from outcome_roi_engine import calculate_forward_roi

        improvement_pct = request.args.get('improvement_pct', 4.0, type=float)
        projection_months = request.args.get('months', 6, type=int)

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None

        current_values, data_source = _extract_current_values(accounts)

        # Determine vertical from first account
        fwd_vertical = getattr(accounts[0], 'vertical', None) if accounts else None

        result = calculate_forward_roi(
            current_values=current_values,
            target_improvement_pct=improvement_pct,
            account_arr=total_arr,
            projection_months=projection_months,
            vertical=fwd_vertical,
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
        print(f"Forward ROI error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ============================================================
# STORY ENDPOINT — Combined for demo
# ============================================================

@outcome_roi_api.route('/api/outcome-roi/story', methods=['GET'])
def get_outcome_story():
    """
    Combined outcome story: historical proof + forward projection.
    The demo endpoint — shows both sides with bridging narrative.

    Query params:
        improvement_pct: Forward target (default: 4.0)
        months: Forward projection months (default: 6)
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 400

    customer_id = resolve_customer_id(db, customer_id)

    if not _is_revenue_intelligence_enabled(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    try:
        from outcome_roi_engine import calculate_outcome_story

        improvement_pct = request.args.get('improvement_pct', 4.0, type=float)
        projection_months = request.args.get('months', 6, type=int)

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None

        metric_actuals, data_source = _extract_historical_actuals(accounts, 6)

        # Identify at-risk accounts per Power of 1 metric
        accounts_at_risk = _extract_accounts_at_risk(accounts, customer_id=customer_id)

        # Determine vertical from first account (single-vertical portfolio)
        acct_vertical = getattr(accounts[0], 'vertical', None) if accounts else None

        story = calculate_outcome_story(
            metric_actuals=metric_actuals,
            target_improvement_pct=improvement_pct,
            account_arr=total_arr,
            projection_months=projection_months,
            accounts_at_risk=accounts_at_risk,
            customer_id=customer_id,
            account_ids=[a.account_id for a in accounts],
            vertical=acct_vertical,
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

        return jsonify({
            'customer_id': customer_id,
            'model': 'outcome_roi',
            'data_source': data_source,
            'story': story,
            'last_updated': datetime.now().isoformat(),
        })

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
        metric_actuals, _data_source = _extract_historical_actuals(accounts, months)

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
        improvement_pct: Forward target (default: 4.0)
        months: Forward projection months (default: 6)
        arr: ARR in dollars (default: 10000000)
    """
    try:
        from outcome_roi_engine import calculate_outcome_story

        improvement_pct = request.args.get('improvement_pct', 4.0, type=float)
        projection_months = request.args.get('months', 6, type=int)
        arr = request.args.get('arr', DEMO_ARR, type=float)

        story = calculate_outcome_story(
            metric_actuals=DEMO_HISTORICAL_ACTUALS,
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

def _extract_historical_actuals(accounts, months):
    """
    Extract historical metric actuals from DB.

    Tries HealthTrend (SaaS) first, then PillarScore (DC2S).
    Falls back to demo data only if neither has sufficient data.

    Returns:
        tuple: (metric_actuals dict, data_source string)
    """
    from power_of_1_model import POWER_OF_1_METRICS

    if not accounts:
        return DEMO_HISTORICAL_ACTUALS, 'demo_fallback'

    account_ids = [a.account_id for a in accounts]

    # ── Path 1: HealthTrend (SaaS customers) ──
    trends = HealthTrend.query.filter(
        HealthTrend.account_id.in_(account_ids)
    ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).all()

    if len(trends) >= 2:
        latest = trends[0]
        earliest_idx = min(len(trends) - 1, months)
        earliest = trends[earliest_idx]

        score_map = {
            'product_usage': 'product_adoption',
            'support': 'ticket_resolution_time',
            'customer_sentiment': 'GRR',
            'business_outcomes': 'NRR',
            'relationship_strength': 'expansion_rate',
        }

        metric_actuals = {}
        for score_key, metric_id in score_map.items():
            metric = POWER_OF_1_METRICS.get(metric_id)
            if not metric:
                continue
            try:
                latest_score = float(getattr(latest, f'{score_key}_score') or 0)
                earliest_score = float(getattr(earliest, f'{score_key}_score') or 0)
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

        return metric_actuals, 'health_trends'

    # ── Path 2: PillarScore (DC2S customers) ──
    cutoff = datetime.now() - timedelta(days=months * 30)

    # Get earliest and latest months with pillar data in the period
    earliest_month = db.session.query(
        db.func.min(PillarScore.measurement_month)
    ).filter(
        PillarScore.account_id.in_(account_ids),
        PillarScore.measurement_month >= cutoff,
    ).scalar()

    # Fallback: use all available data if none in period
    if not earliest_month:
        earliest_month = db.session.query(
            db.func.min(PillarScore.measurement_month)
        ).filter(PillarScore.account_id.in_(account_ids)).scalar()

    latest_month = db.session.query(
        db.func.max(PillarScore.measurement_month)
    ).filter(PillarScore.account_id.in_(account_ids)).scalar()

    if not earliest_month or not latest_month:
        return DEMO_HISTORICAL_ACTUALS, 'demo_fallback'

    # Average pillar scores across all accounts for earliest and latest months
    earliest_scores = PillarScore.query.filter(
        PillarScore.account_id.in_(account_ids),
        PillarScore.measurement_month == earliest_month,
    ).all()

    latest_scores = PillarScore.query.filter(
        PillarScore.account_id.in_(account_ids),
        PillarScore.measurement_month == latest_month,
    ).all()

    if not earliest_scores or not latest_scores:
        return DEMO_HISTORICAL_ACTUALS, 'demo_fallback'

    def _avg_by_pillar(scores):
        """Average pillar scores across accounts."""
        totals = {}
        counts = {}
        for ps in scores:
            code = ps.pillar_code
            val = float(ps.pillar_score) if ps.pillar_score else 0
            totals[code] = totals.get(code, 0) + val
            counts[code] = counts.get(code, 0) + 1
        return {code: totals[code] / counts[code] for code in totals}

    early_avg = _avg_by_pillar(earliest_scores)
    late_avg = _avg_by_pillar(latest_scores)

    metric_actuals = {}

    for pillar_code, metric_id in DC2S_PILLAR_METRIC_MAP.items():
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

    # Synthesize NRR from P4 (GRR/retention) + P5 (expansion) weighted average
    nrr_metric = POWER_OF_1_METRICS.get('NRR')
    if nrr_metric:
        p4_early = early_avg.get('P4', 50.0)
        p4_late = late_avg.get('P4', 50.0)
        p5_early = early_avg.get('P5', 50.0)
        p5_late = late_avg.get('P5', 50.0)

        # NRR = retention + expansion; weight P5 slightly higher
        combined_early = p4_early * 0.4 + p5_early * 0.6
        combined_late = p4_late * 0.4 + p5_late * 0.6

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

    return metric_actuals, 'pillar_scores'


def _extract_current_values(accounts):
    """
    Extract current metric values from latest health data.

    Tries HealthTrend (SaaS) first, then PillarScore (DC2S).

    Returns:
        tuple: (current_values dict, data_source string)
    """
    from power_of_1_model import POWER_OF_1_METRICS

    if not accounts:
        return DEMO_CURRENT_VALUES, 'demo_fallback'

    account_ids = [a.account_id for a in accounts]

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

        return current_values, 'health_trends'

    # ── Path 2: PillarScore (DC2S) ──
    latest_month = db.session.query(
        db.func.max(PillarScore.measurement_month)
    ).filter(PillarScore.account_id.in_(account_ids)).scalar()

    if not latest_month:
        return DEMO_CURRENT_VALUES, 'demo_fallback'

    latest_scores = PillarScore.query.filter(
        PillarScore.account_id.in_(account_ids),
        PillarScore.measurement_month == latest_month,
    ).all()

    if not latest_scores:
        return DEMO_CURRENT_VALUES, 'demo_fallback'

    # Average pillar scores across accounts
    totals = {}
    counts = {}
    for ps in latest_scores:
        code = ps.pillar_code
        val = float(ps.pillar_score) if ps.pillar_score else 0
        totals[code] = totals.get(code, 0) + val
        counts[code] = counts.get(code, 0) + 1
    pillar_avgs = {code: totals[code] / counts[code] for code in totals}

    current_values = {}
    for pillar_code, metric_id in DC2S_PILLAR_METRIC_MAP.items():
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

    # Synthesize NRR from P4 + P5
    nrr_metric = POWER_OF_1_METRICS.get('NRR')
    if nrr_metric:
        combined = pillar_avgs.get('P4', 50.0) * 0.4 + pillar_avgs.get('P5', 50.0) * 0.6
        pct = (combined - 50) / 10.0
        current_values['NRR'] = round(
            nrr_metric.baseline + (nrr_metric.one_pct_move * pct), 2
        )

    for metric_id in POWER_OF_1_METRICS:
        if metric_id not in current_values:
            current_values[metric_id] = POWER_OF_1_METRICS[metric_id].baseline

    return current_values, 'pillar_scores'


def _extract_accounts_at_risk(accounts, customer_id=None):
    """
    Identify which specific accounts need attention for each Power of 1 metric.

    Uses HealthTrend (SaaS) first, then falls back to PillarScore (DC2S).
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

    # PillarScore code → Power of 1 metric mapping (DC2S fallback)
    # Uses shared constant; P1→TTFV, NRR synthesized from P4+P5
    pillar_metric_map = DC2S_PILLAR_METRIC_MAP

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

        # Fallback: PillarScore (DC2S customers)
        latest_pillars = PillarScore.query.filter_by(
            account_id=aid
        ).order_by(PillarScore.measurement_month.desc()).all()

        if latest_pillars:
            # Get the latest month's pillar scores
            latest_month = latest_pillars[0].measurement_month
            scores = {}
            for p in latest_pillars:
                if p.measurement_month != latest_month:
                    break
                metric_id = pillar_metric_map.get(p.pillar_code)
                if metric_id:
                    scores[metric_id] = float(p.pillar_score) if p.pillar_score else 0
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
    """
    earliest_month = db.session.query(
        db.func.min(PillarScore.measurement_month)
    ).filter(
        PillarScore.account_id == account_id,
        PillarScore.measurement_month >= cutoff_date,
    ).scalar()

    # Fallback: no data after cutoff → use all available data
    if not earliest_month:
        earliest_month = db.session.query(
            db.func.min(PillarScore.measurement_month)
        ).filter(PillarScore.account_id == account_id).scalar()

    latest_month = db.session.query(
        db.func.max(PillarScore.measurement_month)
    ).filter(
        PillarScore.account_id == account_id,
    ).scalar()

    if not earliest_month or not latest_month:
        return [], None, None

    # Single month: show current pillar scores as snapshot
    if earliest_month == latest_month:
        latest_pillars = PillarScore.query.filter_by(
            account_id=account_id,
            measurement_month=latest_month,
        ).all()

        l_map = {p.pillar_code: float(p.pillar_score) if p.pillar_score else 0 for p in latest_pillars}
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
    earliest_pillars = PillarScore.query.filter_by(
        account_id=account_id,
        measurement_month=earliest_month,
    ).all()

    latest_pillars = PillarScore.query.filter_by(
        account_id=account_id,
        measurement_month=latest_month,
    ).all()

    e_map = {p.pillar_code: float(p.pillar_score) if p.pillar_score else 0 for p in earliest_pillars}
    l_map = {p.pillar_code: float(p.pillar_score) if p.pillar_score else 0 for p in latest_pillars}

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
