"""
Playbook Triggers API

Manages playbook trigger configurations and evaluates trigger conditions
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from models import db, PlaybookTrigger, Account, KPI
from datetime import datetime, timedelta
from sqlalchemy import func
import json

playbook_triggers_api = Blueprint('playbook_triggers_api', __name__)





@playbook_triggers_api.route('/api/playbook-triggers', methods=['GET'])
def get_trigger_settings():
    """Get all playbook trigger configurations for a customer"""
    try:
        customer_id = get_current_customer_id()
        
        # Fetch all trigger configurations for this customer
        triggers = PlaybookTrigger.query.filter_by(customer_id=customer_id).all()
        
        # Organize by playbook type
        trigger_settings = {}
        for trigger in triggers:
            trigger_settings[trigger.playbook_type] = {
                'trigger_id': trigger.trigger_id,
                'playbook_type': trigger.playbook_type,
                'trigger_config': json.loads(trigger.trigger_config) if trigger.trigger_config else {},
                'auto_trigger_enabled': trigger.auto_trigger_enabled,
                'last_evaluated': trigger.last_evaluated.isoformat() if trigger.last_evaluated else None,
                'last_triggered': trigger.last_triggered.isoformat() if trigger.last_triggered else None,
                'trigger_count': trigger.trigger_count,
                'created_at': trigger.created_at.isoformat() if trigger.created_at else None,
                'updated_at': trigger.updated_at.isoformat() if trigger.updated_at else None
            }
        
        # If no triggers exist, return defaults
        if not trigger_settings:
            trigger_settings = {
                'voc': {
                    'nps_threshold': 10,
                    'csat_threshold': 3.6,
                    'churn_risk_threshold': 0.30,
                    'health_score_drop_threshold': 10,
                    'churn_mentions_threshold': 2,
                    'auto_trigger_enabled': False
                },
                'activation': {
                    'adoption_index_threshold': 60,
                    'active_users_threshold': 50,
                    'dau_mau_threshold': 0.25,
                    'unused_feature_check': True,
                    'auto_trigger_enabled': False
                }
            }
        
        return jsonify({
            'status': 'success',
            'customer_id': customer_id,
            'triggers': trigger_settings
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@playbook_triggers_api.route('/api/playbook-triggers', methods=['POST'])
def save_trigger_settings():
    """Save or update playbook trigger configuration"""
    try:
        customer_id = get_current_customer_id()
        data = request.json
        
        playbook_type = data.get('playbook_type')
        triggers = data.get('trigger_config', data.get('triggers', {}))
        
        if not playbook_type:
            return jsonify({
                'status': 'error',
                'message': 'playbook_type is required'
            }), 400
        
        # Check if trigger configuration already exists
        existing_trigger = PlaybookTrigger.query.filter_by(
            customer_id=customer_id,
            playbook_type=playbook_type
        ).first()
        
        if existing_trigger:
            # Update existing configuration
            existing_trigger.trigger_config = json.dumps(triggers)
            existing_trigger.auto_trigger_enabled = triggers.get('auto_trigger_enabled', False)
            existing_trigger.updated_at = datetime.utcnow()
        else:
            # Create new configuration
            new_trigger = PlaybookTrigger(
                customer_id=customer_id,
                playbook_type=playbook_type,
                trigger_config=json.dumps(triggers),
                auto_trigger_enabled=triggers.get('auto_trigger_enabled', False),
                trigger_count=0
            )
            db.session.add(new_trigger)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'{playbook_type} trigger settings saved successfully',
            'playbook_type': playbook_type,
            'triggers': triggers
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@playbook_triggers_api.route('/api/playbook-triggers/test', methods=['POST'])
def test_trigger_conditions():
    """Test trigger conditions against current account data"""
    try:
        customer_id = get_current_customer_id()
        data = request.json
        
        playbook_type = data.get('playbook_type')
        triggers = data.get('trigger_config', data.get('triggers', {}))
        
        if not playbook_type:
            return jsonify({
                'status': 'error',
                'message': 'playbook_type is required'
            }), 400
        
        # Evaluate triggers based on playbook type
        if playbook_type == 'voc':
            result = evaluate_voc_triggers(customer_id, triggers)
        elif playbook_type == 'activation':
            result = evaluate_activation_triggers(customer_id, triggers)
        else:
            return jsonify({
                'status': 'error',
                'message': f'Unknown playbook type: {playbook_type}'
            }), 400
        
        # Update last_evaluated timestamp
        trigger_config = PlaybookTrigger.query.filter_by(
            customer_id=customer_id,
            playbook_type=playbook_type
        ).first()
        
        if trigger_config:
            trigger_config.last_evaluated = datetime.utcnow()
            db.session.commit()
        
        return jsonify({
            'status': 'success',
            'playbook_type': playbook_type,
            'message': result['message'],
            'triggered': result['triggered'],
            'trigger_details': result['details'],
            'affected_accounts': result['affected_accounts']
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def evaluate_voc_triggers(customer_id, triggers):
    """Evaluate VoC Sprint trigger conditions"""
    nps_threshold = triggers.get('nps_threshold', 10)
    csat_threshold = triggers.get('csat_threshold', 3.6)
    churn_risk_threshold = triggers.get('churn_risk_threshold', 0.30)
    health_score_drop_threshold = triggers.get('health_score_drop_threshold', 10)
    
    # Get all accounts for this customer
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    
    triggered_accounts = []
    trigger_reasons = []
    
    for account in accounts:
        account_triggers = []
        
        # Check NPS (simulated - you would get this from actual NPS data)
        # For now, we'll use health_score as a proxy
        if account.health_score < nps_threshold * 10:  # Scale to 0-100
            account_triggers.append(f"Low health score ({account.health_score:.1f}) as NPS proxy")
        
        # Check CSAT (simulated - you would get this from actual CSAT data)
        # Using health_score / 20 as CSAT proxy (0-5 scale)
        csat_proxy = account.health_score / 20
        if csat_proxy < csat_threshold:
            account_triggers.append(f"Low CSAT proxy ({csat_proxy:.2f})")
        
        # Check churn risk (simulated)
        if account.account_status == 'At Risk':
            account_triggers.append("Account marked as 'At Risk'")
        
        # Check health score drop (would need historical data)
        if account.health_score < 50:  # Simplified check
            account_triggers.append(f"Low health score ({account.health_score:.1f})")
        
        if account_triggers:
            triggered_accounts.append({
                'account_id': account.account_id,
                'account_name': account.account_name,
                'health_score': account.health_score,
                'triggers': account_triggers
            })
    
    triggered = len(triggered_accounts) > 0
    
    return {
        'triggered': triggered,
        'message': f'VoC Sprint triggered for {len(triggered_accounts)} account(s)' if triggered else 'No accounts meet VoC Sprint trigger conditions',
        'details': {
            'nps_threshold': nps_threshold,
            'csat_threshold': csat_threshold,
            'churn_risk_threshold': churn_risk_threshold,
            'health_score_drop_threshold': health_score_drop_threshold
        },
        'affected_accounts': triggered_accounts
    }


def evaluate_activation_triggers(customer_id, triggers):
    """Evaluate Activation Blitz trigger conditions"""
    adoption_index_threshold = triggers.get('adoption_index_threshold', 60)
    active_users_threshold = triggers.get('active_users_threshold', 50)
    dau_mau_threshold = triggers.get('dau_mau_threshold', 0.25)
    unused_feature_check = triggers.get('unused_feature_check', True)
    
    # Get all accounts for this customer
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    
    triggered_accounts = []
    
    for account in accounts:
        account_triggers = []
        
        # Check adoption index (using health_score as proxy)
        adoption_proxy = account.health_score
        if adoption_proxy < adoption_index_threshold:
            account_triggers.append(f"Low adoption index ({adoption_proxy:.1f})")
        
        # Check active users (simulated - would come from usage data)
        # For now, we'll simulate based on account size
        active_users_proxy = int(account.revenue / 1000) if account.revenue else 0
        if active_users_proxy < active_users_threshold:
            account_triggers.append(f"Low active users (~{active_users_proxy})")
        
        # Check DAU/MAU (simulated)
        dau_mau_proxy = 0.15 if account.health_score < 60 else 0.30
        if dau_mau_proxy < dau_mau_threshold:
            account_triggers.append(f"Low DAU/MAU ratio (~{dau_mau_proxy:.2f})")
        
        # Check for unused features (simulated)
        if unused_feature_check:
            # Get KPI count as proxy for feature usage
            kpi_count = KPI.query.filter_by(account_id=account.account_id).count()
            if kpi_count < 10:  # Arbitrary threshold
                account_triggers.append(f"Limited feature usage ({kpi_count} KPIs tracked)")
        
        if account_triggers:
            triggered_accounts.append({
                'account_id': account.account_id,
                'account_name': account.account_name,
                'adoption_index': adoption_proxy,
                'active_users': active_users_proxy,
                'triggers': account_triggers
            })
    
    triggered = len(triggered_accounts) > 0
    
    return {
        'triggered': triggered,
        'message': f'Activation Blitz triggered for {len(triggered_accounts)} account(s)' if triggered else 'No accounts meet Activation Blitz trigger conditions',
        'details': {
            'adoption_index_threshold': adoption_index_threshold,
            'active_users_threshold': active_users_threshold,
            'dau_mau_threshold': dau_mau_threshold,
            'unused_feature_check': unused_feature_check
        },
        'affected_accounts': triggered_accounts
    }


@playbook_triggers_api.route('/api/playbook-triggers/evaluate-all', methods=['POST'])
def evaluate_all_triggers():
    """Evaluate all enabled playbook triggers for a customer"""
    try:
        customer_id = get_current_customer_id()
        
        # Get all enabled trigger configurations
        triggers = PlaybookTrigger.query.filter_by(
            customer_id=customer_id,
            auto_trigger_enabled=True
        ).all()
        
        results = []
        
        for trigger in triggers:
            trigger_config = json.loads(trigger.trigger_config) if trigger.trigger_config else {}
            
            # Evaluate based on playbook type
            if trigger.playbook_type == 'voc':
                result = evaluate_voc_triggers(customer_id, trigger_config)
            elif trigger.playbook_type == 'activation':
                result = evaluate_activation_triggers(customer_id, trigger_config)
            else:
                continue
            
            # Update last_evaluated
            trigger.last_evaluated = datetime.utcnow()
            
            # If triggered, update last_triggered and trigger_count
            if result['triggered']:
                trigger.last_triggered = datetime.utcnow()
                trigger.trigger_count += 1
            
            results.append({
                'playbook_type': trigger.playbook_type,
                'triggered': result['triggered'],
                'message': result['message'],
                'affected_accounts': result['affected_accounts']
            })
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'customer_id': customer_id,
            'evaluation_time': datetime.utcnow().isoformat(),
            'results': results,
            'total_triggers_evaluated': len(results),
            'total_triggered': sum(1 for r in results if r['triggered'])
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@playbook_triggers_api.route('/api/playbook-triggers/history', methods=['GET'])
def get_trigger_history():
    """Get trigger evaluation history for a customer"""
    try:
        customer_id = get_current_customer_id()
        playbook_type = request.args.get('playbook_type')
        
        query = PlaybookTrigger.query.filter_by(customer_id=customer_id)
        
        if playbook_type:
            query = query.filter_by(playbook_type=playbook_type)
        
        triggers = query.all()
        
        history = []
        for trigger in triggers:
            history.append({
                'playbook_type': trigger.playbook_type,
                'auto_trigger_enabled': trigger.auto_trigger_enabled,
                'last_evaluated': trigger.last_evaluated.isoformat() if trigger.last_evaluated else None,
                'last_triggered': trigger.last_triggered.isoformat() if trigger.last_triggered else None,
                'trigger_count': trigger.trigger_count,
                'created_at': trigger.created_at.isoformat() if trigger.created_at else None,
                'updated_at': trigger.updated_at.isoformat() if trigger.updated_at else None
            })
        
        return jsonify({
            'status': 'success',
            'customer_id': customer_id,
            'history': history
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

