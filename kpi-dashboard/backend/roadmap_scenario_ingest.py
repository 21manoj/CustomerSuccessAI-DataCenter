#!/usr/bin/env python3
"""
Step 6 — REST Ingest + Scenario Scripts (Roadmap-Driven Simulation)
====================================================================
Provides endpoints and helper functions to:
  1. Ingest quarterly actual values (roadmap-driven)
  2. Run "what-if" scenario simulations against the Power of 1 model
  3. Generate scenario comparison reports
  4. Seed the system with baseline or demo data for quarterly checkpoints

Feature flag: 'revenue_intelligence'
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id
from extensions import db
from models import (
    Account, ActionEconomics, FeatureToggle as FeatureToggleModel,
    WeightCalibrationHistory,
)
from resolve_identifier import resolve_customer_id
from datetime import datetime
import json

from power_of_1_model import (
    POWER_OF_1_METRICS, calculate_power_of_1_impact,
    calculate_portfolio_impact, SCALING_SCENARIOS,
)
from quarterly_checkpoints import (
    assess_quarter, assess_full_year, get_current_quarter_from_date,
    assessment_to_dict, QUARTER_TARGETS, TrackStatus,
)
from resource_capacity_model import (
    check_capacity, calculate_action_cost, get_resource_pool_summary, CSRole,
)

roadmap_scenario_api = Blueprint('roadmap_scenario_api', __name__)


# ============================================================
# FEATURE GATE
# ============================================================

def _require_ri(customer_id):
    toggle = FeatureToggleModel.query.filter_by(
        customer_id=customer_id, feature_name='revenue_intelligence'
    ).first()
    return toggle and toggle.enabled


# ============================================================
# 6A. QUARTERLY ACTUAL VALUE INGEST
# ============================================================

@roadmap_scenario_api.route('/api/roadmap/ingest-actuals', methods=['POST'])
def ingest_quarterly_actuals():
    """
    Ingest quarterly actual metric values that the roadmap tracks.
    Stores them in WeightCalibrationHistory as a versioned snapshot.

    Body:
    {
        "quarter": "Q2",
        "actuals": {
            "TTFV": 29.3,
            "NRR": 105.8,
            "ticket_resolution_time": 46.0
        },
        "notes": "End-of-Q2 review data"
    }
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Auth required'}), 401
    customer_id = resolve_customer_id(db, customer_id)

    if not _require_ri(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    data = request.get_json()
    if not data or 'actuals' not in data:
        return jsonify({'error': 'Body must include "actuals" dict'}), 400

    quarter = data.get('quarter', get_current_quarter_from_date())
    actuals = data['actuals']
    notes = data.get('notes', '')

    # Get targets for this quarter
    qt = QUARTER_TARGETS.get(quarter)
    targets = {}
    if qt:
        targets = {mid: mc.target_value for mid, mc in qt.metric_targets.items()}

    # Compute assessment
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None
    assessment = assess_quarter(quarter, actuals, total_arr)

    # Persist as a calibration history record
    record = WeightCalibrationHistory(
        customer_id=customer_id,
        calibration_type='quarterly_actuals',
        previous_weights=json.dumps(targets),
        new_weights=json.dumps(actuals),
        error_reduction_pct=0,
        notes=f"{quarter} actuals — {notes}. Status: {assessment.overall_status.value}",
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        'quarter': quarter,
        'assessment': assessment_to_dict(assessment),
        'calibration_id': record.id,
        'message': f'Ingested {len(actuals)} metric values for {quarter}',
    }), 201


# ============================================================
# 6B. WHAT-IF SCENARIO SIMULATION
# ============================================================

@roadmap_scenario_api.route('/api/roadmap/scenario', methods=['POST'])
def run_scenario():
    """
    Run a what-if scenario: given a set of metric improvements,
    return the financial impact, resource requirements, and ROI.

    Body:
    {
        "name": "Aggressive Growth",
        "improvements": {
            "TTFV": 3.0,
            "NRR": 4.0,
            "GRR": 2.0,
            "ticket_resolution_time": 5.0,
            "product_adoption": 3.0,
            "expansion_rate": 2.0
        },
        "account_arr": 10000000
    }
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Auth required'}), 401
    customer_id = resolve_customer_id(db, customer_id)

    if not _require_ri(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    data = request.get_json()
    if not data or 'improvements' not in data:
        return jsonify({'error': 'Body must include "improvements" dict'}), 400

    scenario_name = data.get('name', 'Custom Scenario')
    improvements = data['improvements']
    account_arr = data.get('account_arr')

    if not account_arr:
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        account_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None

    # Calculate per-metric impact
    metric_results = {}
    total_direct = 0
    total_compound = 0
    total_investment = 0
    total_hours = 0

    for metric_id, pct_improvement in improvements.items():
        if metric_id not in POWER_OF_1_METRICS:
            continue
        impact = calculate_power_of_1_impact(metric_id, pct_improvement, account_arr)
        metric_results[metric_id] = impact
        total_direct += impact['direct_impact']
        total_compound += impact['compounding_impact']
        total_investment += impact['investment']
        total_hours += impact.get('total_hours', 0)

    total_impact = total_direct + total_compound

    # Check resource capacity
    planned = {}
    for metric_id in improvements:
        from resource_capacity_model import METRIC_RESOURCE_ALLOCATION
        alloc = METRIC_RESOURCE_ALLOCATION.get(metric_id, {})
        for role, hours in alloc.get('roles', {}).items():
            planned[role] = planned.get(role, 0) + hours

    capacity = check_capacity(planned)

    return jsonify({
        'scenario_name': scenario_name,
        'improvements': improvements,
        'account_arr': account_arr,
        'metrics': metric_results,
        'totals': {
            'direct_impact': round(total_direct, 2),
            'compounding_effect': round(total_compound, 2),
            'total_impact': round(total_impact, 2),
            'total_investment': round(total_investment, 2),
            'total_hours': round(total_hours, 1),
            'roi': round((total_impact - total_investment) / total_investment, 2) if total_investment > 0 else 0,
            'payback_months': round(
                total_investment / (total_impact / 12), 1
            ) if total_impact > 0 else None,
        },
        'capacity_check': {
            'is_feasible': capacity.is_feasible,
            'utilization_by_role': capacity.utilization_by_role,
            'bottleneck_role': capacity.bottleneck_role,
            'recommendation': capacity.recommendation,
        },
    })


# ============================================================
# 6C. SCENARIO COMPARISON
# ============================================================

@roadmap_scenario_api.route('/api/roadmap/compare-scenarios', methods=['POST'])
def compare_scenarios():
    """
    Compare multiple scenarios side-by-side.

    Body:
    {
        "scenarios": [
            {
                "name": "Conservative",
                "improvements": {"TTFV": 1, "NRR": 1, ...}
            },
            {
                "name": "Aggressive",
                "improvements": {"TTFV": 3, "NRR": 4, ...}
            }
        ],
        "account_arr": 10000000
    }
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Auth required'}), 401
    customer_id = resolve_customer_id(db, customer_id)

    if not _require_ri(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    data = request.get_json()
    scenarios = data.get('scenarios', [])
    account_arr = data.get('account_arr')

    if not account_arr:
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        account_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None

    results = []
    for scenario in scenarios:
        improvements = scenario.get('improvements', {})
        name = scenario.get('name', 'Unnamed')

        total_impact = 0
        total_investment = 0
        for metric_id, pct in improvements.items():
            if metric_id not in POWER_OF_1_METRICS:
                continue
            impact = calculate_power_of_1_impact(metric_id, pct, account_arr)
            total_impact += impact['total_impact']
            total_investment += impact['investment']

        results.append({
            'name': name,
            'total_impact': round(total_impact, 2),
            'total_investment': round(total_investment, 2),
            'roi': round((total_impact - total_investment) / total_investment, 2) if total_investment > 0 else 0,
            'payback_months': round(
                total_investment / (total_impact / 12), 1
            ) if total_impact > 0 else None,
            'improvements': improvements,
        })

    # Sort by ROI descending
    results.sort(key=lambda r: r['roi'], reverse=True)

    return jsonify({
        'customer_id': customer_id,
        'account_arr': account_arr,
        'comparison': results,
        'best_roi': results[0]['name'] if results else None,
    })


# ============================================================
# 6D. SEED / DEMO DATA
# ============================================================

@roadmap_scenario_api.route('/api/roadmap/seed-baseline', methods=['POST'])
def seed_baseline():
    """
    Seed the system with the Power of 1 baseline values for demo purposes.
    Creates ActionEconomics records that represent the initial state.
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Auth required'}), 401
    customer_id = resolve_customer_id(db, customer_id)

    if not _require_ri(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    created = 0
    for metric_id, metric in POWER_OF_1_METRICS.items():
        record = ActionEconomics(
            customer_id=customer_id,
            action_type='baseline',
            action_id=f'baseline_{metric_id}',
            action_name=f'Baseline: {metric.display_name}',
            power_of_1_metric=metric_id,
            dollar_impact_annual=metric.annual_impact_per_pct,
            journey_phase='foundation',
            notes=json.dumps({
                'baseline': metric.baseline,
                'unit': metric.unit,
                'direction': metric.direction,
                'category': metric.category.value,
            }),
        )
        db.session.add(record)
        created += 1

    db.session.commit()

    return jsonify({
        'message': f'Seeded {created} baseline records',
        'metrics': list(POWER_OF_1_METRICS.keys()),
    }), 201


# ============================================================
# 6E. ROADMAP TIMELINE OVERVIEW
# ============================================================

@roadmap_scenario_api.route('/api/roadmap/timeline', methods=['GET'])
def get_roadmap_timeline():
    """
    Return the full quarterly roadmap with targets, resource allocations,
    and current status for each quarter.
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Auth required'}), 401
    customer_id = resolve_customer_id(db, customer_id)

    if not _require_ri(customer_id):
        return jsonify({'error': 'Revenue Intelligence not enabled'}), 403

    current_q = get_current_quarter_from_date()

    timeline = []
    for q in ['Q1', 'Q2', 'Q3', 'Q4']:
        qt = QUARTER_TARGETS.get(q)
        if not qt:
            continue

        metrics = {}
        for mid, mc in qt.metric_targets.items():
            m = POWER_OF_1_METRICS.get(mid)
            metrics[mid] = {
                'display_name': m.display_name if m else mid,
                'target_value': mc.target_value,
                'milestone': mc.milestone,
                'unit': m.unit if m else '',
            }

        timeline.append({
            'quarter': q,
            'label': qt.label,
            'month_range': qt.month_range,
            'is_current': q == current_q,
            'platform_milestone': qt.platform_milestone,
            'review_label': qt.review_label,
            'metrics': metrics,
        })

    return jsonify({
        'customer_id': customer_id,
        'current_quarter': current_q,
        'timeline': timeline,
        'resource_pool': get_resource_pool_summary(),
        'scaling_scenarios': SCALING_SCENARIOS,
    })
