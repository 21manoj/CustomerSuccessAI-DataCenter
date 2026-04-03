"""
Playbook Execution API

Manages playbook execution, step tracking, and progress monitoring
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from models import db, PlaybookExecution, PlaybookReport

try:
    from activity_logging import activity_logger
except ImportError:
    activity_logger = None
from datetime import datetime
from dateutil import parser as date_parser
import json
import uuid

playbook_execution_api = Blueprint('playbook_execution_api', __name__)

# In-memory cache for executions (automatically loaded from DB on startup)
_executions = {}
_db_loaded = False




def load_executions_from_db():
    """Load all executions from database into memory cache on startup"""
    global _db_loaded
    if _db_loaded:
        return
    
    try:
        all_executions = PlaybookExecution.query.all()
        for exec_record in all_executions:
            customer_id = exec_record.customer_id
            if customer_id not in _executions:
                _executions[customer_id] = {}
            _executions[customer_id][exec_record.execution_id] = exec_record.execution_data
        _db_loaded = True
        print(f"✓ Loaded {len(all_executions)} playbook executions from database")
    except Exception as e:
        print(f"Warning: Could not load executions from database: {e}")
        _db_loaded = True  # Set to True to prevent repeated attempts


def save_execution_to_db(execution_id, execution_data, customer_id):
    """Save or update a playbook execution in the database"""
    try:
        # Parse timestamps
        started_at = execution_data.get('startedAt')
        if isinstance(started_at, str):
            started_at = date_parser.parse(started_at)
        
        completed_at = execution_data.get('completedAt')
        if completed_at and isinstance(completed_at, str):
            completed_at = date_parser.parse(completed_at)
        
        # Get account info
        account_id = execution_data.get('accountId') or execution_data.get('context', {}).get('accountId')
        
        # Check if execution already exists
        existing_exec = PlaybookExecution.query.filter_by(execution_id=execution_id).first()
        
        if existing_exec:
            # Update existing execution
            was_completed = existing_exec.status == 'completed'
            existing_exec.execution_data = execution_data
            existing_exec.status = execution_data.get('status', 'in-progress')
            existing_exec.current_step = execution_data.get('currentStep')
            existing_exec.completed_at = completed_at
            existing_exec.updated_at = datetime.utcnow()
            
            # Publish event if playbook just completed
            if not was_completed and existing_exec.status == 'completed' and account_id:
                try:
                    from event_system import event_manager, EventType
                    event_manager.publish(
                        EventType.ACCOUNT_DATA_CHANGED,
                        customer_id,
                        {
                            'account_id': account_id,
                            'playbook_id': existing_exec.playbook_id,
                            'execution_id': execution_id,
                            'action': 'playbook_execution_completed'
                        },
                        priority=2
                    )
                except Exception as e:
                    print(f"Note: Could not publish playbook completion event: {e}")
        else:
            # Create new execution
            new_exec = PlaybookExecution(
                execution_id=execution_id,
                customer_id=customer_id,
                account_id=account_id,
                playbook_id=execution_data.get('playbookId'),
                status=execution_data.get('status', 'in-progress'),
                current_step=execution_data.get('currentStep'),
                execution_data=execution_data,
                started_at=started_at or datetime.utcnow(),
                completed_at=completed_at
            )
            db.session.add(new_exec)
        
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error saving execution to database: {e}")
        db.session.rollback()
        return False


@playbook_execution_api.route('/api/playbooks/executions', methods=['POST'])
def create_execution():
    """Create a new playbook execution"""
    try:
        # Load executions from DB on first access
        load_executions_from_db()
        
        customer_id = get_current_customer_id()
        data = request.json
        
        # Check if this is a full execution object (from PlaybookManager) or just create params
        if 'id' in data and 'playbookId' in data:
            # Full execution object from PlaybookManager
            execution = data
            execution_id = execution['id']
            
            # Store execution in memory
            if customer_id not in _executions:
                _executions[customer_id] = {}
            _executions[customer_id][execution_id] = execution
            
            # Save to database
            save_execution_to_db(execution_id, execution, customer_id)
            
            return jsonify({
                'status': 'success',
                'execution': execution,
                'persisted': True
            })
        else:
            # Legacy format - create params only
            playbook_id = data.get('playbookId')
            context = data.get('context', {})
            
            if not playbook_id:
                return jsonify({
                    'status': 'error',
                    'message': 'playbookId is required'
                }), 400
            
            # Create execution record
            execution_id = str(uuid.uuid4())
            execution = {
                'id': execution_id,
                'playbookId': playbook_id,
                'customerId': customer_id,
                'accountId': context.get('accountId'),
                'status': 'in-progress',
                'startedAt': datetime.utcnow().isoformat(),
                'completedAt': None,
                'results': [],
                'context': context,
                'metadata': {
                    'userId': context.get('userId'),
                    'userName': context.get('userName'),
                    'priority': context.get('metadata', {}).get('priority', 'normal')
                }
            }
            
            # Store execution in memory
            if customer_id not in _executions:
                _executions[customer_id] = {}
            _executions[customer_id][execution_id] = execution
            
            # Save to database
            save_execution_to_db(execution_id, execution, customer_id)
            
            return jsonify({
                'status': 'success',
                'execution': execution,
                'persisted': True
            })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@playbook_execution_api.route('/api/playbooks/executions', methods=['GET'])
def get_executions():
    """Get all executions for a customer"""
    try:
        # Load executions from DB on first access
        load_executions_from_db()
        
        customer_id = get_current_customer_id()
        playbook_id = request.args.get('playbookId')
        status = request.args.get('status')
        
        # Get customer executions
        customer_executions = _executions.get(customer_id, {})
        executions = list(customer_executions.values())
        
        # Filter by playbookId if provided
        if playbook_id:
            executions = [e for e in executions if e['playbookId'] == playbook_id]
        
        # Filter by status if provided
        if status:
            executions = [e for e in executions if e['status'] == status]
        
        return jsonify({
            'status': 'success',
            'executions': executions,
            'total': len(executions)
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@playbook_execution_api.route('/api/playbooks/executions/<execution_id>', methods=['GET'])
def get_execution(execution_id):
    """Get a specific execution"""
    try:
        customer_id = get_current_customer_id()
        
        customer_executions = _executions.get(customer_id, {})
        execution = customer_executions.get(execution_id)
        
        if not execution:
            return jsonify({
                'status': 'error',
                'message': 'Execution not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'execution': execution
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@playbook_execution_api.route('/api/playbooks/executions/<execution_id>/steps', methods=['POST'])
def execute_step(execution_id):
    """Execute/complete a step in a playbook"""
    try:
        customer_id = get_current_customer_id()
        data = request.json
        
        step_id = data.get('stepId')
        result = data.get('result', {})
        
        if not step_id:
            return jsonify({
                'status': 'error',
                'message': 'stepId is required'
            }), 400
        
        # Get execution
        customer_executions = _executions.get(customer_id, {})
        execution = customer_executions.get(execution_id)
        
        if not execution:
            return jsonify({
                'status': 'error',
                'message': 'Execution not found'
            }), 404
        
        # Add step result
        step_result = {
            'stepId': step_id,
            'completedAt': datetime.utcnow().isoformat(),
            'result': result,
            'status': 'completed'
        }
        
        execution['results'].append(step_result)
        
        # Update current step
        execution['currentStep'] = step_id
        
        # Save to database
        save_execution_to_db(execution_id, execution, customer_id)
        
        # Activity log when playbook completes (e.g. last step sets status to completed)
        if execution.get('status') == 'completed' and activity_logger:
            try:
                user_id = get_current_user_id()
                playbook_id = execution.get('playbookId') or execution.get('playbook_id') or 'unknown'
                account_id = execution.get('accountId') or execution.get('context', {}).get('accountId')
                activity_logger.log_playbook_execution(
                    customer_id=customer_id,
                    user_id=user_id,
                    playbook_id=str(playbook_id),
                    execution_id=execution_id,
                    account_id=account_id,
                    status='success',
                )
            except Exception:
                pass
        
        return jsonify({
            'status': 'success',
            'execution': execution,
            'stepResult': step_result,
            'persisted': True
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@playbook_execution_api.route('/api/playbooks/executions/<execution_id>', methods=['PUT'])
def update_execution(execution_id):
    """Update execution status"""
    try:
        customer_id = get_current_customer_id()
        data = request.json
        
        # Get execution
        customer_executions = _executions.get(customer_id, {})
        execution = customer_executions.get(execution_id)
        
        if not execution:
            return jsonify({
                'status': 'error',
                'message': 'Execution not found'
            }), 404
        
        # Update status
        if 'status' in data:
            execution['status'] = data['status']
            if data['status'] == 'completed':
                execution['completedAt'] = datetime.utcnow().isoformat()
                # Persist completion to DB
                save_execution_to_db(execution_id, execution, customer_id)
                # Activity log: high-value playbook completion (low volume)
                if activity_logger:
                    try:
                        user_id = get_current_user_id()
                        playbook_id = execution.get('playbookId') or execution.get('playbook_id') or 'unknown'
                        account_id = execution.get('accountId') or execution.get('context', {}).get('accountId')
                        activity_logger.log_playbook_execution(
                            customer_id=customer_id,
                            user_id=user_id,
                            playbook_id=str(playbook_id),
                            execution_id=execution_id,
                            account_id=account_id,
                            status='success',
                        )
                    except Exception:
                        pass
        
        # Update other fields
        if 'metadata' in data:
            execution['metadata'].update(data['metadata'])
        
        return jsonify({
            'status': 'success',
            'execution': execution
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@playbook_execution_api.route('/api/playbooks/executions/<execution_id>', methods=['DELETE'])
def delete_execution(execution_id):
    """Delete an execution and its associated report"""
    try:
        customer_id = get_current_customer_id()
        
        customer_executions = _executions.get(customer_id, {})
        
        if execution_id not in customer_executions:
            return jsonify({
                'status': 'error',
                'message': 'Execution not found'
            }), 404
        
        # Delete from memory
        del customer_executions[execution_id]
        
        # Delete from database (this will cascade to reports due to foreign key)
        db_execution = PlaybookExecution.query.filter_by(execution_id=execution_id).first()
        if db_execution:
            db.session.delete(db_execution)
            db.session.commit()
            print(f"✓ Deleted execution {execution_id} and associated report from database")
        
        return jsonify({
            'status': 'success',
            'message': 'Execution and associated report deleted',
            'cascade_delete': True
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@playbook_execution_api.route('/api/playbooks/executions/stats', methods=['GET'])
def get_execution_stats():
    """Get execution statistics for a customer"""
    try:
        customer_id = get_current_customer_id()
        
        customer_executions = _executions.get(customer_id, {})
        executions = list(customer_executions.values())
        
        # Calculate stats
        total = len(executions)
        in_progress = len([e for e in executions if e['status'] == 'in-progress'])
        completed = len([e for e in executions if e['status'] == 'completed'])
        cancelled = len([e for e in executions if e['status'] == 'cancelled'])
        
        # Group by playbook
        by_playbook = {}
        for execution in executions:
            playbook_id = execution['playbookId']
            if playbook_id not in by_playbook:
                by_playbook[playbook_id] = {
                    'total': 0,
                    'in_progress': 0,
                    'completed': 0,
                    'cancelled': 0
                }
            by_playbook[playbook_id]['total'] += 1
            by_playbook[playbook_id][execution['status']] += 1
        
        return jsonify({
            'status': 'success',
            'stats': {
                'total': total,
                'in_progress': in_progress,
                'completed': completed,
                'cancelled': cancelled,
                'by_playbook': by_playbook
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@playbook_execution_api.route('/api/playbooks/active', methods=['GET'])
def get_active_playbooks():
    """Get in-progress playbook executions (V2) for the CSM dashboard."""
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        from models import PlaybookExecutionV2, Account, HealthScore

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

        from models import PlaybookExecutionV2, Account

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

