"""
Playbook Webhook Engine
========================

Evaluates playbook trigger conditions and fires outbound webhooks to n8n
or any external orchestrator when conditions are met.

Usage:
    from playbook_webhook_engine import evaluate_triggers
    evaluate_triggers(customer_id, account_id, event_type='health_update', context={...})

Trigger types:
    health_drop       — Health score dropped below threshold
    health_critical   — Health score entered critical zone (<50)
    signal_detected   — Specific signal type created
    renewal_approaching — Renewal within N days
    expansion_ready   — Account meets expansion criteria
    custom            — Custom JSON condition
"""

import json
import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Loopback stub registry: in-memory log of webhook fires for testing
# In production, this is replaced by actual HTTP calls
_LOOPBACK_STUB_LOG: List[Dict] = []
_USE_LOOPBACK_STUB = True  # Set False in production


def evaluate_triggers(customer_id: int, account_id: int, event_type: str, context: Dict) -> List[Dict]:
    """
    Evaluate all active webhook triggers for a customer/account.

    Args:
        customer_id: CS Pulse customer (tenant) ID
        account_id: Account that changed
        event_type: What happened (health_update, signal_created, renewal_check, etc.)
        context: Event data (health_score, previous_score, signal_type, etc.)

    Returns:
        List of fire results: [{"trigger_id": int, "fired": bool, "status": str}, ...]
    """
    from integration_models import PlaybookWebhookTrigger
    from extensions import db

    triggers = PlaybookWebhookTrigger.query.filter_by(
        customer_id=customer_id,
        enabled=True,
    ).all()

    results = []
    for trigger in triggers:
        # Check if trigger applies to this account
        if not _account_matches_filter(account_id, trigger.account_filter, customer_id):
            continue

        # Check if trigger type matches event
        if not _event_matches_trigger(event_type, trigger.trigger_type):
            continue

        # Evaluate condition
        if _evaluate_condition(trigger.trigger_condition, context):
            # Check cooldown
            if _is_in_cooldown(trigger, account_id):
                results.append({
                    'trigger_id': trigger.trigger_id,
                    'trigger_name': trigger.trigger_name,
                    'fired': False,
                    'status': 'cooldown_skipped',
                })
                continue

            # Check daily limit
            if trigger.fire_count_today and trigger.fire_count_today >= trigger.max_fires_per_day:
                results.append({
                    'trigger_id': trigger.trigger_id,
                    'trigger_name': trigger.trigger_name,
                    'fired': False,
                    'status': 'daily_limit_reached',
                })
                continue

            # Fire the webhook
            fire_result = _fire_webhook(trigger, customer_id, account_id, context)
            results.append(fire_result)

            # Update trigger stats
            trigger.last_fired_at = datetime.utcnow()
            trigger.last_fire_status = fire_result['status']
            trigger.fire_count_today = (trigger.fire_count_today or 0) + 1

    if results:
        db.session.commit()

    return results


def _event_matches_trigger(event_type: str, trigger_type: str) -> bool:
    """Check if the event type should evaluate this trigger type."""
    mapping = {
        'health_update': ['health_drop', 'health_critical', 'custom'],
        'signal_created': ['signal_detected', 'custom'],
        'renewal_check': ['renewal_approaching', 'custom'],
        'expansion_check': ['expansion_ready', 'custom'],
        'manual': ['health_drop', 'health_critical', 'signal_detected',
                   'renewal_approaching', 'expansion_ready', 'custom'],
    }
    return trigger_type in mapping.get(event_type, [trigger_type])


def _account_matches_filter(account_id: int, account_filter: Optional[Dict], customer_id: int) -> bool:
    """Check if account matches the trigger's scope filter."""
    if not account_filter:
        return True  # No filter = all accounts

    # Filter by specific account IDs
    if 'account_ids' in account_filter:
        return account_id in account_filter['account_ids']

    # Filter by minimum ARR
    if 'min_arr' in account_filter:
        from models import Account
        acct = Account.query.filter_by(
            account_id=account_id, customer_id=customer_id
        ).first()
        if acct and acct.revenue:
            return float(acct.revenue) >= account_filter['min_arr']
        return False

    return True


def _evaluate_condition(condition: Dict, context: Dict) -> bool:
    """
    Evaluate a trigger condition against the current context.

    Condition format:
    {
        "metric": "health_score",
        "operator": "drops_below",  // drops_below, rises_above, equals, less_than, greater_than, changed_by
        "threshold": 50,
        "window_days": 7  // optional: only trigger if change happened within N days
    }
    """
    if not condition:
        return False

    metric = condition.get('metric', 'health_score')
    operator = condition.get('operator', 'less_than')
    threshold = condition.get('threshold', 50)

    current_value = context.get(metric)
    previous_value = context.get(f'previous_{metric}')

    if current_value is None:
        return False

    try:
        current_value = float(current_value)
        threshold = float(threshold)
    except (ValueError, TypeError):
        return False

    if operator == 'drops_below':
        if previous_value is None:
            return current_value < threshold
        return float(previous_value) >= threshold and current_value < threshold

    elif operator == 'rises_above':
        if previous_value is None:
            return current_value > threshold
        return float(previous_value) <= threshold and current_value > threshold

    elif operator == 'less_than':
        return current_value < threshold

    elif operator == 'greater_than':
        return current_value > threshold

    elif operator == 'equals':
        return abs(current_value - threshold) < 0.01

    elif operator == 'changed_by':
        if previous_value is None:
            return False
        delta = abs(current_value - float(previous_value))
        return delta >= threshold

    return False


def _is_in_cooldown(trigger, account_id: int) -> bool:
    """Check if we're in cooldown for this trigger + account combo."""
    from integration_models import PlaybookWebhookLog

    if not trigger.cooldown_minutes:
        return False

    cooldown_since = datetime.utcnow() - timedelta(minutes=trigger.cooldown_minutes)

    recent_fire = PlaybookWebhookLog.query.filter(
        PlaybookWebhookLog.trigger_id == trigger.trigger_id,
        PlaybookWebhookLog.account_id == account_id,
        PlaybookWebhookLog.status == 'success',
        PlaybookWebhookLog.fired_at >= cooldown_since,
    ).first()

    return recent_fire is not None


def _build_payload(trigger, customer_id: int, account_id: int, context: Dict) -> Dict:
    """Build the webhook payload from template + context."""
    from models import Account

    account = Account.query.filter_by(
        account_id=account_id, customer_id=customer_id
    ).first()

    # Base payload
    payload = {
        'event': 'playbook_trigger',
        'trigger_id': trigger.trigger_id,
        'trigger_name': trigger.trigger_name,
        'trigger_type': trigger.trigger_type,
        'customer_id': customer_id,
        'account_id': account_id,
        'account_name': account.account_name if account else 'Unknown',
        'account_arr': float(account.revenue) if account and account.revenue else 0,
        'timestamp': datetime.utcnow().isoformat(),
        'context': context,
    }

    # Apply template if defined
    if trigger.payload_template:
        template = trigger.payload_template.copy()
        # Simple variable substitution
        for key, val in template.items():
            if isinstance(val, str) and '{{' in val:
                for ctx_key, ctx_val in {**payload, **context}.items():
                    val = val.replace(f'{{{{{ctx_key}}}}}', str(ctx_val))
                template[key] = val
        payload.update(template)

    return payload


def _fire_webhook(trigger, customer_id: int, account_id: int, context: Dict) -> Dict:
    """
    Fire an outbound webhook. Uses loopback stub in dev, real HTTP in production.
    """
    from extensions import db
    from integration_models import PlaybookWebhookLog

    payload = _build_payload(trigger, customer_id, account_id, context)

    # Sign payload with HMAC if secret is configured
    payload_bytes = json.dumps(payload).encode()
    signature = None
    if trigger.webhook_secret_hash:
        signature = 'sha256=' + hmac.new(
            trigger.webhook_secret_hash.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

    start_time = time.time()
    response_status = None
    response_body = None
    error_message = None
    status = 'success'

    if _USE_LOOPBACK_STUB:
        # Loopback stub: log locally instead of making HTTP call
        _LOOPBACK_STUB_LOG.append({
            'trigger_id': trigger.trigger_id,
            'trigger_name': trigger.trigger_name,
            'customer_id': customer_id,
            'account_id': account_id,
            'payload': payload,
            'webhook_url': trigger.webhook_url,
            'signature': signature,
            'timestamp': datetime.utcnow().isoformat(),
        })
        response_status = 200
        response_body = json.dumps({'status': 'loopback_ok', 'stub': True})
        logger.info(f"[LOOPBACK] Webhook fired: trigger={trigger.trigger_name}, account={account_id}")
    else:
        # Real HTTP call to n8n or external system
        try:
            import requests as http_requests
            headers = {
                'Content-Type': 'application/json',
                'X-CS-Pulse-Trigger': trigger.trigger_name,
                'X-CS-Pulse-Customer': str(customer_id),
                **(trigger.webhook_headers or {}),
            }
            if signature:
                headers['X-Webhook-Signature'] = signature

            resp = http_requests.post(
                trigger.webhook_url,
                json=payload,
                headers=headers,
                timeout=30,
            )
            response_status = resp.status_code
            response_body = resp.text[:2000]  # Truncate large responses

            if resp.status_code >= 400:
                status = 'error'
                error_message = f"HTTP {resp.status_code}: {resp.text[:500]}"
        except Exception as e:
            status = 'error'
            error_message = str(e)
            response_status = 0

    duration_ms = int((time.time() - start_time) * 1000)

    # Resolve account for fire_reason
    from models import Account
    account = Account.query.filter_by(
        account_id=account_id, customer_id=customer_id
    ).first()
    account_name = account.account_name if account else f'Account #{account_id}'

    fire_reason = _build_fire_reason(trigger, account_name, context)

    # Log the fire
    log = PlaybookWebhookLog(
        trigger_id=trigger.trigger_id,
        customer_id=customer_id,
        account_id=account_id,
        fire_reason=fire_reason,
        payload_sent=payload,
        response_status=response_status,
        response_body=response_body,
        duration_ms=duration_ms,
        status=status,
        error_message=error_message,
    )
    db.session.add(log)

    return {
        'trigger_id': trigger.trigger_id,
        'trigger_name': trigger.trigger_name,
        'fired': True,
        'status': status,
        'response_status': response_status,
        'duration_ms': duration_ms,
        'fire_reason': fire_reason,
    }


def _build_fire_reason(trigger, account_name: str, context: Dict) -> str:
    """Build human-readable fire reason."""
    cond = trigger.trigger_condition or {}
    metric = cond.get('metric', 'health_score')
    threshold = cond.get('threshold', '?')
    current = context.get(metric, '?')
    previous = context.get(f'previous_{metric}')

    if previous is not None:
        return f"{metric} changed from {previous} to {current} (threshold: {threshold}) for {account_name}"
    return f"{metric} = {current} (threshold: {threshold}) for {account_name}"


# ============================================================
# API endpoints for managing playbook webhook triggers
# ============================================================

from flask import Blueprint, request, jsonify
playbook_webhook_api = Blueprint('playbook_webhook_api', __name__)


@playbook_webhook_api.route('/api/integrations/playbook-triggers', methods=['GET'])
def list_playbook_triggers():
    """List all playbook webhook triggers for the customer."""
    from integration_models import PlaybookWebhookTrigger
    customer_id = int(request.headers.get('X-Customer-ID', 0))
    try:
        from auth_middleware import get_current_customer_id
        customer_id = get_current_customer_id()
    except Exception:
        pass

    triggers = PlaybookWebhookTrigger.query.filter_by(
        customer_id=customer_id
    ).all()

    return jsonify({
        'triggers': [t.to_dict() for t in triggers],
        'total': len(triggers),
    })


@playbook_webhook_api.route('/api/integrations/playbook-triggers', methods=['POST'])
def create_playbook_trigger():
    """Create a new playbook webhook trigger."""
    from extensions import db
    from integration_models import PlaybookWebhookTrigger

    customer_id = int(request.headers.get('X-Customer-ID', 0))
    try:
        from auth_middleware import get_current_customer_id
        customer_id = get_current_customer_id()
    except Exception:
        pass

    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    # Generate webhook secret for HMAC signing
    import secrets
    webhook_secret = secrets.token_hex(32)

    trigger = PlaybookWebhookTrigger(
        customer_id=customer_id,
        trigger_name=data['trigger_name'],
        trigger_type=data['trigger_type'],
        trigger_condition=data['trigger_condition'],
        webhook_url=data['webhook_url'],
        webhook_method=data.get('webhook_method', 'POST'),
        webhook_headers=data.get('webhook_headers', {}),
        webhook_secret_hash=hashlib.sha256(webhook_secret.encode()).hexdigest(),
        payload_template=data.get('payload_template'),
        enabled=data.get('enabled', True),
        cooldown_minutes=data.get('cooldown_minutes', 60),
        max_fires_per_day=data.get('max_fires_per_day', 10),
        account_filter=data.get('account_filter'),
    )
    db.session.add(trigger)
    db.session.commit()

    result = trigger.to_dict()
    result['webhook_secret'] = webhook_secret  # Return only on creation

    return jsonify(result), 201


@playbook_webhook_api.route('/api/integrations/playbook-triggers/<int:trigger_id>', methods=['PUT'])
def update_playbook_trigger(trigger_id):
    """Update a playbook webhook trigger."""
    from extensions import db
    from integration_models import PlaybookWebhookTrigger

    customer_id = int(request.headers.get('X-Customer-ID', 0))
    try:
        from auth_middleware import get_current_customer_id
        customer_id = get_current_customer_id()
    except Exception:
        pass

    trigger = PlaybookWebhookTrigger.query.filter_by(
        trigger_id=trigger_id, customer_id=customer_id
    ).first()

    if not trigger:
        return jsonify({'error': 'Trigger not found'}), 404

    data = request.get_json()
    updatable = [
        'trigger_name', 'trigger_type', 'trigger_condition',
        'webhook_url', 'webhook_headers', 'payload_template',
        'enabled', 'cooldown_minutes', 'max_fires_per_day', 'account_filter',
    ]
    for field in updatable:
        if field in data:
            setattr(trigger, field, data[field])

    db.session.commit()
    return jsonify(trigger.to_dict())


@playbook_webhook_api.route('/api/integrations/playbook-triggers/<int:trigger_id>', methods=['DELETE'])
def delete_playbook_trigger(trigger_id):
    """Delete a playbook webhook trigger."""
    from extensions import db
    from integration_models import PlaybookWebhookTrigger

    customer_id = int(request.headers.get('X-Customer-ID', 0))
    try:
        from auth_middleware import get_current_customer_id
        customer_id = get_current_customer_id()
    except Exception:
        pass

    trigger = PlaybookWebhookTrigger.query.filter_by(
        trigger_id=trigger_id, customer_id=customer_id
    ).first()

    if not trigger:
        return jsonify({'error': 'Trigger not found'}), 404

    trigger.enabled = False
    db.session.commit()

    return jsonify({'message': 'Trigger disabled', 'trigger_id': trigger_id})


@playbook_webhook_api.route('/api/integrations/playbook-triggers/<int:trigger_id>/test', methods=['POST'])
def test_playbook_trigger(trigger_id):
    """Test-fire a playbook webhook trigger with mock context."""
    from integration_models import PlaybookWebhookTrigger

    customer_id = int(request.headers.get('X-Customer-ID', 0))
    try:
        from auth_middleware import get_current_customer_id
        customer_id = get_current_customer_id()
    except Exception:
        pass

    trigger = PlaybookWebhookTrigger.query.filter_by(
        trigger_id=trigger_id, customer_id=customer_id
    ).first()

    if not trigger:
        return jsonify({'error': 'Trigger not found'}), 404

    # Build test context
    test_context = request.get_json() or {
        'health_score': 42,
        'previous_health_score': 65,
        'account_name': 'Test Account',
    }

    # Get first account for test
    from models import Account
    account = Account.query.filter_by(customer_id=customer_id).first()
    account_id = account.account_id if account else 0

    result = _fire_webhook(trigger, customer_id, account_id, test_context)

    from extensions import db
    db.session.commit()

    return jsonify({
        'test_status': 'pass' if result['status'] == 'success' else 'fail',
        'result': result,
        'loopback_mode': _USE_LOOPBACK_STUB,
    })


@playbook_webhook_api.route('/api/integrations/playbook-triggers/fire-log', methods=['GET'])
def get_fire_log():
    """Get recent webhook fire log."""
    from integration_models import PlaybookWebhookLog

    customer_id = int(request.headers.get('X-Customer-ID', 0))
    try:
        from auth_middleware import get_current_customer_id
        customer_id = get_current_customer_id()
    except Exception:
        pass

    limit = request.args.get('limit', 50, type=int)

    logs = PlaybookWebhookLog.query.filter_by(
        customer_id=customer_id
    ).order_by(PlaybookWebhookLog.fired_at.desc()).limit(limit).all()

    return jsonify({
        'logs': [l.to_dict() for l in logs],
        'total': len(logs),
        'loopback_stub_count': len(_LOOPBACK_STUB_LOG),
    })


# ============================================================
# Utility: Get loopback stub log (for testing only)
# ============================================================

def get_loopback_log() -> List[Dict]:
    """Return the in-memory loopback stub log (test use only)."""
    return _LOOPBACK_STUB_LOG.copy()


def clear_loopback_log():
    """Clear the loopback stub log."""
    _LOOPBACK_STUB_LOG.clear()


# request, jsonify imported with Blueprint above
