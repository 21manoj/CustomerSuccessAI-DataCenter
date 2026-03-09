"""
Step 8 — Observability: Metrics, Analytics, and Execution Dashboards
=====================================================================
Provides:
  - Execution metrics (success/fail rates, duration, provider usage)
  - Cost analytics (investment vs. realized value from ActionEconomics)
  - Recalibration metrics (weight drift, accuracy trends)
  - API endpoints for dashboards

Complements existing ActivityLog and QueryAudit models.
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id
from extensions import db
from resolve_identifier import resolve_customer_id
from datetime import datetime, timedelta
from sqlalchemy import func
import json

observability_api = Blueprint('observability_api', __name__)


def _customer_id():
    cid = get_current_customer_id()
    if not cid:
        return None
    return resolve_customer_id(db, cid)


# ============================================================
# EXECUTION METRICS
# ============================================================

@observability_api.route('/api/observability/executions', methods=['GET'])
def execution_metrics():
    """
    Aggregate playbook execution metrics: success rate, avg duration,
    provider usage, outcome distribution.
    """
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    days = request.args.get('days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)

    from models import PlaybookExecution

    executions = PlaybookExecution.query.filter(
        PlaybookExecution.customer_id == cid,
        PlaybookExecution.started_at >= cutoff,
    ).all()

    total = len(executions)
    completed = sum(1 for e in executions if e.status == 'COMPLETED')
    failed = sum(1 for e in executions if e.status == 'FAILED')
    in_progress = sum(1 for e in executions if e.status in ('in-progress', 'HANDED_OFF_TO_N8N'))

    # Duration stats for completed executions
    durations = []
    for e in executions:
        if e.completed_at and e.started_at:
            dt = (e.completed_at - e.started_at).total_seconds() / 3600
            durations.append(dt)

    avg_duration_hours = round(sum(durations) / len(durations), 2) if durations else 0

    # Playbook type breakdown
    type_counts = {}
    for e in executions:
        pb = e.playbook_id or 'unknown'
        type_counts[pb] = type_counts.get(pb, 0) + 1

    # Outcome distribution
    outcome_counts = {}
    for e in executions:
        o = e.outcome or 'pending'
        outcome_counts[o] = outcome_counts.get(o, 0) + 1

    return jsonify({
        'period_days': days,
        'total_executions': total,
        'completed': completed,
        'failed': failed,
        'in_progress': in_progress,
        'success_rate': round(completed / total, 4) if total > 0 else 0,
        'avg_duration_hours': avg_duration_hours,
        'by_playbook_type': type_counts,
        'by_outcome': outcome_counts,
    })


# ============================================================
# STEP-LEVEL METRICS
# ============================================================

@observability_api.route('/api/observability/steps', methods=['GET'])
def step_metrics():
    """
    Provider-level step metrics: success/fail by provider,
    average duration, error patterns.
    """
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    days = request.args.get('days', 30, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days)

    from models_action_interface import PlaybookStepLog
    from models import PlaybookExecution

    # Join step logs with executions to filter by customer
    steps = db.session.query(PlaybookStepLog).join(
        PlaybookExecution,
        PlaybookStepLog.execution_id == PlaybookExecution.execution_id,
    ).filter(
        PlaybookExecution.customer_id == cid,
        PlaybookStepLog.executed_at >= cutoff,
    ).all()

    total = len(steps)
    success = sum(1 for s in steps if s.status == 'success')
    failed = sum(1 for s in steps if s.status == 'failed')

    # By provider
    by_provider = {}
    for s in steps:
        p = s.provider
        if p not in by_provider:
            by_provider[p] = {'total': 0, 'success': 0, 'failed': 0, 'avg_duration_ms': 0, 'durations': []}
        by_provider[p]['total'] += 1
        if s.status == 'success':
            by_provider[p]['success'] += 1
        elif s.status == 'failed':
            by_provider[p]['failed'] += 1
        if s.duration_ms:
            by_provider[p]['durations'].append(s.duration_ms)

    for p, stats in by_provider.items():
        durations = stats.pop('durations')
        stats['avg_duration_ms'] = round(sum(durations) / len(durations)) if durations else 0
        stats['success_rate'] = round(stats['success'] / stats['total'], 4) if stats['total'] > 0 else 0

    # Top errors
    errors = [s.error_message for s in steps if s.error_message]
    error_counts = {}
    for e in errors:
        short = e[:100]
        error_counts[short] = error_counts.get(short, 0) + 1
    top_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return jsonify({
        'period_days': days,
        'total_steps': total,
        'success': success,
        'failed': failed,
        'success_rate': round(success / total, 4) if total > 0 else 0,
        'by_provider': by_provider,
        'top_errors': [{'error': e, 'count': c} for e, c in top_errors],
    })


# ============================================================
# COST ANALYTICS
# ============================================================

@observability_api.route('/api/observability/cost-analytics', methods=['GET'])
def cost_analytics():
    """
    Investment vs. realized value from ActionEconomics records.
    """
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    from models import ActionEconomics

    records = ActionEconomics.query.filter_by(customer_id=cid).all()

    total_investment = 0
    total_value = 0
    by_phase = {}
    by_metric = {}

    for r in records:
        cost = r.estimated_cost or 0
        value = r.dollar_impact_annual or 0
        total_investment += cost
        total_value += value

        phase = r.journey_phase or 'unknown'
        if phase not in by_phase:
            by_phase[phase] = {'investment': 0, 'value': 0}
        by_phase[phase]['investment'] += cost
        by_phase[phase]['value'] += value

        metric = r.power_of_1_metric or 'unknown'
        if metric not in by_metric:
            by_metric[metric] = {'investment': 0, 'value': 0}
        by_metric[metric]['investment'] += cost
        by_metric[metric]['value'] += value

    return jsonify({
        'total_investment': round(total_investment, 2),
        'total_value': round(total_value, 2),
        'roi': round((total_value - total_investment) / total_investment, 2) if total_investment > 0 else 0,
        'by_journey_phase': {
            k: {'investment': round(v['investment'], 2), 'value': round(v['value'], 2)}
            for k, v in by_phase.items()
        },
        'by_power_of_1_metric': {
            k: {'investment': round(v['investment'], 2), 'value': round(v['value'], 2)}
            for k, v in by_metric.items()
        },
    })


# ============================================================
# RECALIBRATION METRICS
# ============================================================

@observability_api.route('/api/observability/calibration', methods=['GET'])
def calibration_metrics():
    """Weight drift and accuracy trends from recalibration history."""
    cid = _customer_id()
    if not cid:
        return jsonify({'error': 'Auth required'}), 401

    from qdrant_feedback_loop import get_calibration_history, get_current_weights

    history = get_calibration_history(cid, limit=50)
    current_weights = get_current_weights(cid)

    # Separate recalibrations from feedback entries
    recalibrations = [h for h in history if h['calibration_type'] == 'weight_recalibration']
    feedbacks = [h for h in history if h['calibration_type'] == 'execution_feedback']

    # Error reduction trend
    error_trend = [
        {
            'date': r['calibrated_at'],
            'error_reduction_pct': r['error_reduction_pct'],
        }
        for r in recalibrations
    ]

    return jsonify({
        'current_weights': current_weights,
        'total_recalibrations': len(recalibrations),
        'total_feedbacks': len(feedbacks),
        'error_reduction_trend': error_trend,
        'recent_history': history[:10],
    })


# ============================================================
# SYSTEM HEALTH
# ============================================================

@observability_api.route('/api/observability/health', methods=['GET'])
def system_health():
    """Quick system health check for monitoring."""
    checks = {
        'database': False,
        'providers': {},
    }

    # DB check
    try:
        db.session.execute(db.text('SELECT 1'))
        checks['database'] = True
    except Exception:
        pass

    # Provider availability
    try:
        from providers.registry import PROVIDER_REGISTRY
        registry = PROVIDER_REGISTRY()
        checks['providers'] = {name: True for name in registry}
    except Exception:
        pass

    all_healthy = checks['database'] and all(checks['providers'].values())

    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat(),
    }), 200 if all_healthy else 503


# ============================================================
# CONTEXT GRAPH REGENERATION STATUS
# ============================================================

@observability_api.route('/api/observability/context-graph-regen', methods=['GET'])
def context_graph_regen_status():
    """
    GET /api/observability/context-graph-regen
    Returns context graph regeneration subscriber status:
    cached health classifications, pending regenerations, last regen times.
    """
    try:
        from event_system import event_manager
        sub = getattr(event_manager, 'context_graph_subscriber', None)
        if sub is None:
            return jsonify({
                'status': 'disabled',
                'message': 'ContextGraphRegenerationSubscriber not registered',
            }), 200

        return jsonify({
            'status': 'active',
            **sub.get_status(),
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@observability_api.route('/api/observability/context-graph-regen/trigger', methods=['POST'])
def context_graph_regen_trigger():
    """
    POST /api/observability/context-graph-regen/trigger
    Manually trigger context graph regeneration for a customer.
    Body: {"customer_id": 291}
    """
    try:
        from event_system import event_manager
        sub = getattr(event_manager, 'context_graph_subscriber', None)
        if sub is None:
            return jsonify({
                'status': 'error',
                'message': 'ContextGraphRegenerationSubscriber not registered',
            }), 400

        data = request.get_json() or {}
        customer_id = data.get('customer_id')
        if not customer_id:
            return jsonify({'error': 'customer_id required'}), 400

        import threading
        regen_thread = threading.Thread(
            target=sub._regenerate_customer,
            args=(int(customer_id),),
            name=f"context-graph-regen-manual-{customer_id}",
            daemon=True,
        )
        regen_thread.start()

        return jsonify({
            'status': 'triggered',
            'customer_id': customer_id,
            'message': f'Context graph regeneration started for customer {customer_id}',
        }), 202
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500
