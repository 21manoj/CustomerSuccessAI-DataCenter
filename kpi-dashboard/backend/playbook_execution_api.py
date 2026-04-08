"""
Playbook Execution API

Manages playbook execution, step tracking, and progress monitoring.
All execution state uses PlaybookExecutionV2 (DB-first, no in-memory cache).
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from models import db, PlaybookExecutionV2, PlaybookReport, Account

try:
    from activity_logging import activity_logger
except ImportError:
    activity_logger = None
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

playbook_execution_api = Blueprint('playbook_execution_api', __name__)


def _v2_to_camelcase(v2):
    """Map PlaybookExecutionV2 record to camelCase dict for legacy frontend compat."""
    action_log = v2.action_log or []
    return {
        'id': v2.execution_id,
        'execution_id': v2.execution_id,
        'playbookId': v2.playbook_id,
        'playbook_id': v2.playbook_id,
        'playbook_name': v2.playbook_name,
        'customerId': v2.customer_id,
        'accountId': v2.account_id,
        'account_id': v2.account_id,
        'status': (v2.status or 'in_progress').replace('_', '-'),
        'currentStep': None,
        'startedAt': v2.triggered_at.isoformat() if v2.triggered_at else None,
        'completedAt': v2.closed_at.isoformat() if v2.closed_at else None,
        'results': [],
        'steps': action_log,
        'actions_planned': v2.actions_planned or 0,
        'actions_completed': v2.actions_completed or 0,
        'health_at_trigger': v2.health_at_trigger,
        'outcome': v2.outcome,
        'context': {},
        'metadata': {
            'triggered_by': v2.triggered_by,
            'arc_type': v2.arc_type,
        },
    }


@playbook_execution_api.route('/api/playbooks/executions', methods=['POST'])
def create_execution():
    """Create a new playbook execution (V2)."""
    try:
        customer_id = get_current_customer_id()
        data = request.json

        # Extract playbook_id and account_id from either format
        playbook_id = data.get('playbookId') or data.get('playbook_id')
        account_id = (
            data.get('accountId')
            or data.get('account_id')
            or (data.get('context', {}).get('accountId'))
        )

        if not playbook_id:
            return jsonify({'status': 'error', 'message': 'playbookId is required'}), 400

        if account_id:
            # Use lifecycle module for full V2 creation with health snapshot
            from utils.playbook_lifecycle import start_execution
            try:
                v2 = start_execution(
                    customer_id=int(customer_id),
                    account_id=int(account_id),
                    playbook_id=playbook_id,
                    triggered_by='csm_manual',
                )
            except ValueError as e:
                return jsonify({'status': 'error', 'message': str(e)}), 404

            return jsonify({
                'status': 'success',
                'execution': _v2_to_camelcase(v2),
                'persisted': True,
            })
        else:
            # No account_id — create a minimal V2 record
            execution_id = str(uuid.uuid4())
            v2 = PlaybookExecutionV2(
                execution_id=execution_id,
                customer_id=int(customer_id),
                account_id=0,  # unknown
                playbook_id=playbook_id,
                playbook_name=playbook_id,
                triggered_by='csm_manual',
                status='in_progress',
                phase='stabilize',
            )
            db.session.add(v2)
            db.session.commit()

            return jsonify({
                'status': 'success',
                'execution': _v2_to_camelcase(v2),
                'persisted': True,
            })

    except Exception as e:
        logger.error(f"Error creating execution: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@playbook_execution_api.route('/api/playbooks/executions', methods=['GET'])
def get_executions():
    """Get all executions for a customer (V2)."""
    try:
        customer_id = get_current_customer_id()
        playbook_id = request.args.get('playbookId') or request.args.get('playbook_id')
        status = request.args.get('status')

        query = PlaybookExecutionV2.query.filter_by(customer_id=int(customer_id))

        if playbook_id:
            query = query.filter_by(playbook_id=playbook_id)
        if status:
            db_status = status.replace('-', '_')
            query = query.filter_by(status=db_status)

        v2_records = query.order_by(PlaybookExecutionV2.triggered_at.desc()).all()

        return jsonify({
            'status': 'success',
            'executions': [_v2_to_camelcase(v2) for v2 in v2_records],
            'total': len(v2_records),
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@playbook_execution_api.route('/api/playbooks/executions/<execution_id>', methods=['GET'])
def get_execution(execution_id):
    """Get a specific execution (V2)."""
    try:
        v2 = PlaybookExecutionV2.query.filter_by(execution_id=execution_id).first()
        if not v2:
            return jsonify({'status': 'error', 'message': 'Execution not found'}), 404

        return jsonify({'status': 'success', 'execution': _v2_to_camelcase(v2)})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@playbook_execution_api.route('/api/playbooks/executions/<execution_id>/steps', methods=['POST'])
def execute_step(execution_id):
    """Execute/complete a step in a playbook (V2 — updates action_log)."""
    try:
        customer_id = get_current_customer_id()
        data = request.json

        step_id = data.get('stepId') or data.get('step_id')
        result = data.get('result', {})

        if not step_id:
            return jsonify({'status': 'error', 'message': 'stepId is required'}), 400

        v2 = PlaybookExecutionV2.query.filter_by(execution_id=execution_id).first()
        if not v2:
            return jsonify({'status': 'error', 'message': 'Execution not found'}), 404

        # Update action_log entry
        action_log = list(v2.action_log or [])
        step_found = False
        for step in action_log:
            if step.get('step_id') == step_id:
                step_found = True
                step['status'] = 'completed'
                step['completed_at'] = datetime.utcnow().isoformat()
                step['result'] = result
                break

        if not step_found:
            # Append as new step result
            action_log.append({
                'step_id': step_id,
                'status': 'completed',
                'completed_at': datetime.utcnow().isoformat(),
                'result': result,
            })

        v2.action_log = action_log
        v2.actions_completed = sum(1 for s in action_log if s.get('status') == 'completed')
        db.session.commit()

        # Activity log when all steps complete
        if v2.actions_planned and v2.actions_completed >= v2.actions_planned and activity_logger:
            try:
                user_id = get_current_user_id()
                activity_logger.log_playbook_execution(
                    customer_id=customer_id,
                    user_id=user_id,
                    playbook_id=str(v2.playbook_id),
                    execution_id=execution_id,
                    account_id=v2.account_id,
                    status='success',
                )
            except Exception:
                pass

        return jsonify({
            'status': 'success',
            'execution': _v2_to_camelcase(v2),
            'stepResult': {'stepId': step_id, 'status': 'completed'},
            'persisted': True,
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@playbook_execution_api.route('/api/playbooks/executions/<execution_id>', methods=['PUT'])
def update_execution(execution_id):
    """Update execution status (V2)."""
    try:
        customer_id = get_current_customer_id()
        data = request.json

        v2 = PlaybookExecutionV2.query.filter_by(execution_id=execution_id).first()
        if not v2:
            return jsonify({'status': 'error', 'message': 'Execution not found'}), 404

        if 'status' in data:
            new_status = data['status'].replace('-', '_')
            was_completed = v2.status == 'completed'
            v2.status = new_status

            if new_status == 'completed' and not was_completed:
                v2.closed_at = datetime.utcnow()
                v2.outcome = 'resolved'

                if activity_logger:
                    try:
                        user_id = get_current_user_id()
                        activity_logger.log_playbook_execution(
                            customer_id=customer_id,
                            user_id=user_id,
                            playbook_id=str(v2.playbook_id),
                            execution_id=execution_id,
                            account_id=v2.account_id,
                            status='success',
                        )
                    except Exception:
                        pass

        if 'outcome' in data:
            v2.outcome = data['outcome']
        if 'outcome_notes' in data:
            v2.outcome_notes = data['outcome_notes']

        db.session.commit()

        return jsonify({'status': 'success', 'execution': _v2_to_camelcase(v2)})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@playbook_execution_api.route('/api/playbooks/executions/<execution_id>', methods=['DELETE'])
def delete_execution(execution_id):
    """Delete an execution."""
    try:
        v2 = PlaybookExecutionV2.query.filter_by(execution_id=execution_id).first()
        if not v2:
            return jsonify({'status': 'error', 'message': 'Execution not found'}), 404

        db.session.delete(v2)
        db.session.commit()
        logger.info(f"Deleted V2 execution {execution_id}")

        return jsonify({
            'status': 'success',
            'message': 'Execution deleted',
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@playbook_execution_api.route('/api/playbooks/executions/stats', methods=['GET'])
def get_execution_stats():
    """Get execution statistics for a customer (V2)."""
    try:
        customer_id = get_current_customer_id()

        v2_records = PlaybookExecutionV2.query.filter_by(customer_id=int(customer_id)).all()

        total = len(v2_records)
        in_progress = sum(1 for e in v2_records if e.status == 'in_progress')
        completed = sum(1 for e in v2_records if e.status == 'completed')
        cancelled = sum(1 for e in v2_records if e.status == 'cancelled')

        by_playbook = {}
        for v2 in v2_records:
            pid = v2.playbook_id
            if pid not in by_playbook:
                by_playbook[pid] = {'total': 0, 'in_progress': 0, 'completed': 0, 'cancelled': 0}
            by_playbook[pid]['total'] += 1
            status_key = v2.status if v2.status in by_playbook[pid] else 'in_progress'
            by_playbook[pid][status_key] = by_playbook[pid].get(status_key, 0) + 1

        return jsonify({
            'status': 'success',
            'stats': {
                'total': total,
                'in_progress': in_progress,
                'completed': completed,
                'cancelled': cancelled,
                'by_playbook': by_playbook,
            },
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@playbook_execution_api.route('/api/playbooks/active', methods=['GET'])
def get_active_playbooks():
    """Get in-progress playbook executions (V2) for the CSM dashboard."""
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        from models import HealthScore

        executions = (
            PlaybookExecutionV2.query
            .filter_by(customer_id=int(customer_id), status='in_progress')
            .order_by(PlaybookExecutionV2.triggered_at.desc())
            .limit(20)
            .all()
        )

        results = []
        for ex in executions:
            account = db.session.get(Account, ex.account_id)
            account_name = account.account_name if account else f'Account {ex.account_id}'
            latest_hs = (
                HealthScore.query.filter_by(account_id=ex.account_id)
                .order_by(HealthScore.measurement_month.desc()).first()
            )
            health_now = float(latest_hs.health_score) if latest_hs and latest_hs.health_score else None
            health_delta = round(health_now - ex.health_at_trigger, 1) if health_now and ex.health_at_trigger else None
            days_active = (datetime.utcnow() - ex.triggered_at).days if ex.triggered_at else 0

            results.append({
                'execution_id': ex.execution_id,
                'account_id': ex.account_id,
                'account_name': account_name,
                'playbook_id': ex.playbook_id,
                'playbook_name': ex.playbook_name,
                'triggered_by': ex.triggered_by,
                'arc_type': ex.arc_type,
                'status': ex.status,
                'phase': ex.phase,
                'days_active': days_active,
                'health_at_trigger': float(ex.health_at_trigger) if ex.health_at_trigger else None,
                'health_now': health_now,
                'health_delta': health_delta,
                'arr_at_trigger': float(ex.arr_at_trigger) if ex.arr_at_trigger else None,
                'actions_planned': ex.actions_planned or 0,
                'actions_completed': ex.actions_completed or 0,
                'triggered_at': ex.triggered_at.isoformat() if ex.triggered_at else None,
            })

        return jsonify({'status': 'success', 'active_playbooks': results, 'total': len(results)})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@playbook_execution_api.route('/api/playbooks/completed', methods=['GET'])
def get_completed_playbooks():
    """Get recently completed playbook executions with ROI data."""
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        executions = (
            PlaybookExecutionV2.query
            .filter_by(customer_id=int(customer_id), status='completed')
            .order_by(PlaybookExecutionV2.closed_at.desc())
            .limit(20)
            .all()
        )

        results = []
        for ex in executions:
            account = db.session.get(Account, ex.account_id)
            results.append({
                'execution_id': ex.execution_id,
                'account_id': ex.account_id,
                'account_name': account.account_name if account else f'Account {ex.account_id}',
                'playbook_id': ex.playbook_id,
                'playbook_name': ex.playbook_name,
                'outcome': ex.outcome,
                'health_delta': float(ex.health_delta) if ex.health_delta else None,
                'revenue_protected': float(ex.revenue_protected) if ex.revenue_protected else 0,
                'total_cost': float(ex.total_cost) if ex.total_cost else 0,
                'realized_roi_pct': float(ex.realized_roi_pct) if ex.realized_roi_pct else None,
                'nrr_impact_pct': float(ex.nrr_impact_pct) if ex.nrr_impact_pct else None,
                'closed_at': ex.closed_at.isoformat() if ex.closed_at else None,
            })

        return jsonify({'status': 'success', 'completed_playbooks': results, 'total': len(results)})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ── Vertical-agnostic health scores endpoint ──────────────────────────

@playbook_execution_api.route('/api/health-scores', methods=['GET'])
def get_health_scores():
    """Get health score history for a customer's accounts (all verticals).

    Works for both DC2_S and SaaS Premium — queries HealthScore table directly.
    Query params: customer_id (optional, defaults to session), months (default 6).
    """
    try:
        customer_id = request.args.get('customer_id') or get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401
        customer_id = int(customer_id)
        months = int(request.args.get('months', 6))

        from models import HealthScore
        from datetime import timedelta

        account_ids = [
            a.account_id for a in
            Account.query.filter_by(customer_id=customer_id).all()
        ]
        if not account_ids:
            return jsonify({'health_scores': [], 'total': 0})

        cutoff = datetime.utcnow() - timedelta(days=months * 30)
        scores = (
            HealthScore.query
            .filter(
                HealthScore.account_id.in_(account_ids),
                HealthScore.measurement_month >= cutoff.date(),
            )
            .order_by(HealthScore.account_id, HealthScore.measurement_month)
            .all()
        )

        return jsonify({
            'health_scores': [s.to_dict() for s in scores],
            'total': len(scores),
            'accounts': len(account_ids),
            'months': months,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
