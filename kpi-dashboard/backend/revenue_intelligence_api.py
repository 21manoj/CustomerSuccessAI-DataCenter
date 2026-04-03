#!/usr/bin/env python3
"""
Revenue Intelligence API — Power of 1 Endpoints
==================================================
Exposes the Power of 1 economic framework via REST API.
All endpoints are gated by the 'revenue_intelligence' feature toggle.

Feature flag: 'revenue_intelligence' (per-customer toggle in FeatureToggle table)

Routes:
  GET  /api/revenue-intelligence/power-of-1                 — Full Power of 1 table
  GET  /api/revenue-intelligence/power-of-1/<metric_id>     — Single metric detail
  GET  /api/revenue-intelligence/impact                     — Portfolio-level impact calc
  GET  /api/revenue-intelligence/account/<account_id>       — Account-level projections
  GET  /api/revenue-intelligence/resources                  — Resource pool summary
  GET  /api/revenue-intelligence/capacity-check             — Capacity feasibility check
  GET  /api/revenue-intelligence/action-economics           — Action economics history
  POST /api/revenue-intelligence/action-economics           — Record action economics
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id
from extensions import db
from models import Account, ActionEconomics, FeatureToggle as FeatureToggleModel
from resolve_identifier import resolve_customer_id
from datetime import datetime
from functools import wraps

from power_of_1_model import (
    POWER_OF_1_METRICS,
    METRIC_CASCADES,
    SCALING_SCENARIOS,
    INVESTMENT_SUMMARY,
    TIME_ECONOMICS,
    IMPLEMENTATION_PHASES,
    AUTOMATION_TIMELINE,
    QUARTERLY_CHECKPOINTS,
    CS_PILLAR_WEIGHTS,
    calculate_power_of_1_impact,
    calculate_portfolio_impact,
    get_metric_for_kpi_code,
    get_metrics_for_playbook,
)
from resource_capacity_model import (
    DEFAULT_RESOURCE_POOL,
    METRIC_RESOURCE_ALLOCATION,
    CSRole,
    check_capacity,
    calculate_action_cost,
    get_resource_pool_summary,
)

revenue_intelligence_api = Blueprint('revenue_intelligence_api', __name__)


# ============================================================
# FEATURE GATE DECORATOR
# ============================================================

def require_revenue_intelligence(f):
    """Decorator that checks the revenue_intelligence feature toggle."""
    @wraps(f)
    def decorated(*args, **kwargs):
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        customer_id = resolve_customer_id(db, customer_id)

        toggle = FeatureToggleModel.query.filter_by(
            customer_id=customer_id,
            feature_name='revenue_intelligence'
        ).first()

        # Check per-customer toggle first, then fall back to global toggle
        if toggle:
            enabled = toggle.enabled
        else:
            try:
                from feature_toggles import feature_toggles, FeatureToggle
                enabled = feature_toggles.is_enabled(FeatureToggle.REVENUE_INTELLIGENCE)
            except Exception:
                enabled = False

        if not enabled:
            return jsonify({
                'error': 'Revenue Intelligence is not enabled for this customer',
                'feature': 'revenue_intelligence',
                'enabled': False,
            }), 403

        # Inject resolved customer_id into kwargs
        kwargs['customer_id'] = customer_id
        return f(*args, **kwargs)
    return decorated


# ============================================================
# POWER OF 1 TABLE ENDPOINTS
# ============================================================

@revenue_intelligence_api.route('/api/revenue-intelligence/power-of-1', methods=['GET'])
@require_revenue_intelligence
def get_power_of_1_table(customer_id):
    """Return the full Power of 1 metric table with economic models."""
    try:
        metrics = {}
        for metric_id, metric in POWER_OF_1_METRICS.items():
            metrics[metric_id] = {
                'metric_id': metric.metric_id,
                'display_name': metric.display_name,
                'baseline': metric.baseline,
                'unit': metric.unit,
                'direction': metric.direction,
                'one_pct_move': metric.one_pct_move,
                'annual_impact_per_pct': metric.annual_impact_per_pct,
                'total_investment': metric.total_investment,
                'roi_at_1pct': metric.roi_at_1pct,
                'payback_months': metric.payback_months,
                'category': metric.category.value,
                'primary_pillar': metric.primary_pillar.value,
                'total_hours': metric.total_hours,
                'quarters': metric.quarters,
                'linked_playbooks': metric.linked_playbooks,
                'work_packages': [
                    {
                        'name': wp.name,
                        'description': wp.description,
                        'hours': wp.hours,
                        'deliverables': wp.deliverables,
                    }
                    for wp in metric.work_packages
                ],
            }

        return jsonify({
            'metrics': metrics,
            'investment_summary': INVESTMENT_SUMMARY,
            'scaling_scenarios': SCALING_SCENARIOS,
            'cascades': {
                mid: {
                    'amplifies': cascade.get('amplifies', [])
                }
                for mid, cascade in METRIC_CASCADES.items()
            },
            'pillar_weights': {k.value: v for k, v in CS_PILLAR_WEIGHTS.items()},
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@revenue_intelligence_api.route('/api/revenue-intelligence/power-of-1/<metric_id>', methods=['GET'])
@require_revenue_intelligence
def get_power_of_1_metric(customer_id, metric_id):
    """Return detailed economic model for a single Power of 1 metric."""
    try:
        improvement_pct = request.args.get('improvement_pct', 1.0, type=float)
        account_arr = request.args.get('account_arr', None, type=float)

        impact = calculate_power_of_1_impact(metric_id, improvement_pct, account_arr)

        if 'error' in impact:
            return jsonify(impact), 404

        # Add work package details
        metric = POWER_OF_1_METRICS.get(metric_id)
        if metric:
            impact['work_packages'] = [
                {
                    'name': wp.name,
                    'description': wp.description,
                    'hours': wp.hours,
                    'deliverables': wp.deliverables,
                    'roles': {
                        'csm': wp.roles.csm,
                        'cs_ops': wp.roles.cs_ops,
                        'product': wp.roles.product,
                        'platform': wp.roles.platform,
                        'leadership': wp.roles.leadership,
                    },
                }
                for wp in metric.work_packages
            ]
            impact['linked_playbooks'] = metric.linked_playbooks
            impact['linked_kpi_codes'] = metric.linked_kpi_codes

        return jsonify(impact)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# PORTFOLIO IMPACT ENDPOINT
# ============================================================

@revenue_intelligence_api.route('/api/revenue-intelligence/impact', methods=['GET'])
@require_revenue_intelligence
def get_portfolio_impact(customer_id):
    """Calculate total Power of 1 impact across all 6 metrics."""
    try:
        improvement_pct = request.args.get('improvement_pct', 1.0, type=float)

        # Sum ARR across all accounts for this customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None

        result = calculate_portfolio_impact(improvement_pct, total_arr)
        result['customer_id'] = customer_id
        result['total_accounts'] = len(accounts)
        result['total_arr'] = total_arr

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# ACCOUNT-LEVEL PROJECTIONS
# ============================================================

@revenue_intelligence_api.route('/api/revenue-intelligence/account/<int:account_id>', methods=['GET'])
@require_revenue_intelligence
def get_account_revenue_intelligence(customer_id, account_id):
    """Get Power of 1 projections for a specific account."""
    try:
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).first()

        if not account:
            return jsonify({'error': 'Account not found'}), 404

        improvement_pct = request.args.get('improvement_pct', 1.0, type=float)
        account_arr = float(account.revenue) if account.revenue else None

        # Calculate per-metric impact for this account
        metrics = {}
        for metric_id in POWER_OF_1_METRICS:
            metrics[metric_id] = calculate_power_of_1_impact(
                metric_id, improvement_pct, account_arr
            )

        # Aggregate
        total_direct = sum(m['direct_impact'] for m in metrics.values())
        total_compound = sum(m['compounding_impact'] for m in metrics.values())
        total_impact = total_direct + total_compound

        return jsonify({
            'account_id': account_id,
            'account_name': account.account_name,
            'revenue': float(account.revenue) if account.revenue else 0,
            'improvement_pct': improvement_pct,
            'metrics': metrics,
            'totals': {
                'direct_impact': round(total_direct, 2),
                'compounding_impact': round(total_compound, 2),
                'total_impact': round(total_impact, 2),
            },
            'scaling_scenarios': SCALING_SCENARIOS,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# RESOURCE CAPACITY ENDPOINTS
# ============================================================

@revenue_intelligence_api.route('/api/revenue-intelligence/resources', methods=['GET'])
@require_revenue_intelligence
def get_resources(customer_id):
    """Return the resource pool summary and per-metric allocation."""
    try:
        pool_summary = get_resource_pool_summary()
        return jsonify({
            'resource_pool': pool_summary,
            'metric_allocation': {
                mid: {
                    'total_hours': alloc['total_hours'],
                    'cost': alloc['cost'],
                    'quarters': alloc['quarters'],
                    'primary_pillar': alloc['primary_pillar'],
                    'roles': {role.value: hours for role, hours in alloc['roles'].items()},
                }
                for mid, alloc in METRIC_RESOURCE_ALLOCATION.items()
            },
            'time_economics': TIME_ECONOMICS,
            'implementation_phases': IMPLEMENTATION_PHASES,
            'automation_timeline': AUTOMATION_TIMELINE,
            'quarterly_checkpoints': QUARTERLY_CHECKPOINTS,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@revenue_intelligence_api.route('/api/revenue-intelligence/capacity-check', methods=['GET'])
@require_revenue_intelligence
def capacity_check(customer_id):
    """Check if planned initiatives fit within resource capacity."""
    try:
        quarter = request.args.get('quarter', None)

        # Build planned hours from query params or default to full-year allocation
        planned = {}
        for role in CSRole:
            hours = request.args.get(f'{role.value}_hours', None, type=float)
            if hours is not None:
                planned[role] = hours

        # If no specific hours provided, check against full annual allocation
        if not planned:
            for alloc in METRIC_RESOURCE_ALLOCATION.values():
                for role, hours in alloc['roles'].items():
                    planned[role] = planned.get(role, 0) + hours

        result = check_capacity(planned, quarter=quarter)

        return jsonify({
            'is_feasible': result.is_feasible,
            'utilization_by_role': result.utilization_by_role,
            'bottleneck_role': result.bottleneck_role,
            'overflow_hours': result.overflow_hours,
            'recommendation': result.recommendation,
            'quarter': quarter,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# ACTION ECONOMICS ENDPOINTS
# ============================================================

@revenue_intelligence_api.route('/api/revenue-intelligence/action-economics', methods=['GET'])
@require_revenue_intelligence
def get_action_economics(customer_id):
    """Query action economics history for the customer."""
    try:
        account_id = request.args.get('account_id', None, type=int)
        action_type = request.args.get('action_type', None)
        limit = request.args.get('limit', 50, type=int)

        query = ActionEconomics.query.filter_by(customer_id=customer_id)

        if account_id:
            query = query.filter_by(account_id=account_id)
        if action_type:
            query = query.filter_by(action_type=action_type)

        records = query.order_by(ActionEconomics.measured_at.desc()).limit(limit).all()

        return jsonify({
            'customer_id': customer_id,
            'count': len(records),
            'records': [r.to_dict() for r in records],
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@revenue_intelligence_api.route('/api/revenue-intelligence/action-economics', methods=['POST'])
@require_revenue_intelligence
def record_action_economics(customer_id):
    """Record an action economics entry (used by MCP agents)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        record = ActionEconomics(
            customer_id=customer_id,
            account_id=data.get('account_id'),
            execution_id=data.get('execution_id'),
            action_type=data.get('action_type', 'manual'),
            action_id=data.get('action_id', ''),
            action_name=data.get('action_name'),
            csm_hours=data.get('csm_hours', 0),
            cs_ops_hours=data.get('cs_ops_hours', 0),
            product_hours=data.get('product_hours', 0),
            platform_hours=data.get('platform_hours', 0),
            leadership_hours=data.get('leadership_hours', 0),
            kpi_before=data.get('kpi_before'),
            kpi_after=data.get('kpi_after'),
            kpi_deltas=data.get('kpi_deltas'),
            power_of_1_metric=data.get('power_of_1_metric'),
            dollar_impact_annual=data.get('dollar_impact_annual'),
            dollar_impact_monthly=data.get('dollar_impact_monthly'),
            revenue_increase=data.get('revenue_increase', 0),
            cost_savings=data.get('cost_savings', 0),
            journey_phase=data.get('journey_phase'),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
        )

        # Auto-calculate cost using resource capacity model
        hours_by_role = {}
        for role in CSRole:
            h = getattr(record, f'{role.value}_hours', None)
            if h and float(h) > 0:
                hours_by_role[role] = float(h)

        if hours_by_role:
            cost = calculate_action_cost(hours_by_role)
            record.cs_initiative_cost = cost['cs_initiative_cost']
            record.platform_cost = cost['platform_cost']
            record.total_action_cost = cost['total_cost']

        # Auto-calculate ROI if we have cost and impact
        if record.total_action_cost and record.dollar_impact_annual:
            cost_val = float(record.total_action_cost)
            impact_val = float(record.dollar_impact_annual)
            if cost_val > 0:
                record.roi = (impact_val - cost_val) / cost_val
                record.payback_days = int((cost_val / (impact_val / 365))) if impact_val > 0 else None

        db.session.add(record)
        db.session.commit()

        return jsonify({
            'id': record.id,
            'message': 'Action economics recorded',
            'record': record.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================
# UTILITY ENDPOINTS
# ============================================================

@revenue_intelligence_api.route('/api/revenue-intelligence/kpi-mapping/<kpi_code>', methods=['GET'])
@require_revenue_intelligence
def get_kpi_mapping(customer_id, kpi_code):
    """Map a KPI code to its Power of 1 metric."""
    metric_id = get_metric_for_kpi_code(kpi_code)
    if not metric_id:
        return jsonify({'error': f'No Power of 1 metric found for KPI code: {kpi_code}'}), 404

    return jsonify({
        'kpi_code': kpi_code,
        'power_of_1_metric': metric_id,
        'impact': calculate_power_of_1_impact(metric_id, 1.0),
    })


@revenue_intelligence_api.route('/api/revenue-intelligence/playbook-mapping/<playbook_id>', methods=['GET'])
@require_revenue_intelligence
def get_playbook_mapping(customer_id, playbook_id):
    """Map a playbook to the Power of 1 metrics it improves."""
    metric_ids = get_metrics_for_playbook(playbook_id)
    if not metric_ids:
        return jsonify({'error': f'No Power of 1 metrics found for playbook: {playbook_id}'}), 404

    metrics = {}
    for mid in metric_ids:
        metrics[mid] = calculate_power_of_1_impact(mid, 1.0)

    return jsonify({
        'playbook_id': playbook_id,
        'metrics': metrics,
        'metric_count': len(metrics),
    })


@revenue_intelligence_api.route('/api/revenue-intelligence/nrr-forecast', methods=['GET'])
@require_revenue_intelligence
def get_nrr_forecast_endpoint(customer_id):
    """NRR trajectory forecast with intervention simulation.

    Query params:
        months: forecast horizon in months (default 3, max 12)

    Returns portfolio NRR trajectory at T+30/60/90, renewal risk overlay,
    and ranked interventions with playbook cost and ROI.
    """
    import sys
    from pathlib import Path

    months = min(int(request.args.get('months', 3)), 12)

    # Try cached forecast from Wizard B
    from models import WizardLearning
    learning = (
        WizardLearning.query
        .filter_by(customer_id=customer_id, is_active=True)
        .order_by(WizardLearning.created_at.desc())
        .first()
    )
    if learning and learning.learnings:
        cached = learning.learnings.get('portfolio_nrr_forecast')
        if cached and cached.get('trajectory'):
            cached['source'] = 'wizard_b_cached'
            return jsonify(cached)

    # Live calculation
    _wb_dir = str(Path(__file__).parent / 'verticals' / '_template' / 'journey' / 'wizard_b')
    if _wb_dir not in sys.path:
        sys.path.insert(0, _wb_dir)

    try:
        from wizard_b_pattern_analyzer import PatternAnalyzer
        analyzer = PatternAnalyzer.from_database(customer_id)
        analyzer.analyze_patterns()
    except (ValueError, ImportError) as e:
        return jsonify({'error': str(e)}), 404

    if analyzer.portfolio_nrr_forecast:
        result = analyzer.portfolio_nrr_forecast
        result['source'] = 'live_calculation'
        return jsonify(result)

    return jsonify({'error': 'NRR forecast unavailable — ensure accounts have ARR and context graph outcomes.'}), 404
