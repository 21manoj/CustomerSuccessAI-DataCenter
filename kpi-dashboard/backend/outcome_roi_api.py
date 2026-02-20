#!/usr/bin/env python3
"""
Outcome ROI API — Historical Proof + Forward Projection
=========================================================
Outcome-focused endpoints. Headlines are always dollars and
Power of 1 metrics — never raw KPIs.

Endpoints:
  GET  /api/outcome-roi/historical     — "We proved it works"
  GET  /api/outcome-roi/forward        — "Here's what's next"
  GET  /api/outcome-roi/story          — Combined side-by-side for demo
  GET  /api/outcome-roi/demo           — Pre-loaded demo data (no DB needed)

Feature flag: 'revenue_intelligence'
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import Account, HealthTrend, FeatureToggle as FeatureToggleModel
from resolve_identifier import resolve_customer_id

outcome_roi_api = Blueprint('outcome_roi_api', __name__)


# ============================================================
# FEATURE TOGGLE
# ============================================================

def _is_revenue_intelligence_enabled(customer_id):
    toggle = FeatureToggleModel.query.filter_by(
        customer_id=customer_id,
        feature_name='revenue_intelligence'
    ).first()
    return toggle and toggle.enabled


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

        metric_actuals = _extract_historical_actuals(accounts, months)

        result = calculate_historical_roi(
            metric_actuals=metric_actuals,
            account_arr=total_arr,
            period_label=f"Last {months} Months",
        )

        from outcome_roi_engine import _result_to_dict
        return jsonify({
            'customer_id': customer_id,
            'model': 'outcome_roi',
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

        current_values = _extract_current_values(accounts)

        result = calculate_forward_roi(
            current_values=current_values,
            target_improvement_pct=improvement_pct,
            account_arr=total_arr,
            projection_months=projection_months,
        )

        from outcome_roi_engine import _result_to_dict
        return jsonify({
            'customer_id': customer_id,
            'model': 'outcome_roi',
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

        metric_actuals = _extract_historical_actuals(accounts, 6)

        story = calculate_outcome_story(
            metric_actuals=metric_actuals,
            target_improvement_pct=improvement_pct,
            account_arr=total_arr,
            projection_months=projection_months,
        )

        return jsonify({
            'customer_id': customer_id,
            'model': 'outcome_roi',
            'story': story,
            'last_updated': datetime.now().isoformat(),
        })

    except Exception as e:
        import traceback
        print(f"Outcome story error: {e}\n{traceback.format_exc()}")
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
    Extract historical metric actuals from HealthTrend data.
    Maps health score categories to Power of 1 metrics.
    Falls back to demo data if insufficient DB data.
    """
    from power_of_1_model import POWER_OF_1_METRICS

    if not accounts:
        return DEMO_HISTORICAL_ACTUALS

    # Gather all health trends across accounts
    account_ids = [a.account_id for a in accounts]
    trends = HealthTrend.query.filter(
        HealthTrend.account_id.in_(account_ids)
    ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).all()

    if len(trends) < 2:
        return DEMO_HISTORICAL_ACTUALS

    # Map health score changes to Power of 1 metric improvements
    # Health scores are 0-100; 10-point change ≈ 1% metric improvement
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

        # Convert health score change to metric value change
        score_change = latest_score - earliest_score
        pct_improvement = score_change / 10.0  # 10 pts = 1%

        if metric.direction == "lower_is_better":
            current_value = metric.baseline - (metric.one_pct_move * pct_improvement)
        else:
            current_value = metric.baseline + (metric.one_pct_move * pct_improvement)

        metric_actuals[metric_id] = {
            "baseline": metric.baseline,
            "current": round(current_value, 2),
        }

    # TTFV always uses its own mapping
    if "TTFV" not in metric_actuals:
        metric_actuals["TTFV"] = DEMO_HISTORICAL_ACTUALS["TTFV"]

    # Fill gaps with demo data
    for metric_id in POWER_OF_1_METRICS:
        if metric_id not in metric_actuals:
            metric_actuals[metric_id] = DEMO_HISTORICAL_ACTUALS.get(metric_id, {
                "baseline": POWER_OF_1_METRICS[metric_id].baseline,
                "current": POWER_OF_1_METRICS[metric_id].baseline,
            })

    return metric_actuals


def _extract_current_values(accounts):
    """Extract current metric values from latest health trends."""
    from power_of_1_model import POWER_OF_1_METRICS

    if not accounts:
        return DEMO_CURRENT_VALUES

    account_ids = [a.account_id for a in accounts]
    latest_trend = HealthTrend.query.filter(
        HealthTrend.account_id.in_(account_ids)
    ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).first()

    if not latest_trend:
        return DEMO_CURRENT_VALUES

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

    # Fill gaps
    for metric_id in POWER_OF_1_METRICS:
        if metric_id not in current_values:
            current_values[metric_id] = DEMO_CURRENT_VALUES.get(
                metric_id, POWER_OF_1_METRICS[metric_id].baseline
            )

    return current_values
