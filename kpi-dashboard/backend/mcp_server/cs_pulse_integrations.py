"""
CS Pulse MCP — Integration & n8n Tools
========================================

MCP tools for managing integrations, triggering n8n workflows,
and monitoring connector health from Claude conversations.

Tools:
  - list_integration_connectors: Show all configured connectors
  - create_integration_connector: Register a new external source
  - get_integration_health: Overall health of all integrations
  - trigger_n8n_workflow: Fire an n8n workflow via webhook
  - get_sync_logs: Recent sync activity
  - test_connector: Verify connectivity (loopback)
  - fire_playbook_webhook: Manually trigger a playbook webhook
  - list_playbook_webhook_triggers: Show all playbook webhook configs
  - create_playbook_webhook_trigger: Set up a new outbound trigger
"""

import json
import logging
import time
import hashlib
from datetime import datetime
from typing import Optional, Dict, List

from cs_pulse_mcp_server import (
    mcp,
    _check_mcp_enabled,
    _require_auth,
    ToolError,
)

logger = logging.getLogger(__name__)


def _get_app_context():
    """Get Flask app context for DB operations."""
    from cs_pulse_mcp_server import _get_flask_app
    return _get_flask_app().app_context()


# ============================================================
# Connector Management Tools (MCP-registered)
# ============================================================

@mcp.tool
def list_integration_connectors(customer_id: int) -> Dict:
    """
    List all integration connectors for a customer.
    Shows connector type, status, last sync time, and record counts.

    Args:
        customer_id: The customer (tenant) ID
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    with _get_app_context():
        from integration_models import IntegrationConnector

        connectors = IntegrationConnector.query.filter_by(
            customer_id=customer_id
        ).all()

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'connectors': [c.to_dict() for c in connectors],
            'total': len(connectors),
            'summary': {
                'active': sum(1 for c in connectors if c.status == 'active'),
                'errored': sum(1 for c in connectors if c.consecutive_errors and c.consecutive_errors > 0),
                'types': list(set(c.connector_type for c in connectors)),
            }
        }


def create_integration_connector(
    customer_id: int,
    connector_type: str,
    connector_name: str,
    description: str = '',
    sync_frequency_minutes: int = 60,
    webhook_url: str = '',
) -> Dict:
    """
    Register a new integration connector for a customer.
    Supports: sfdc, hubspot, zendesk, n8n, csv_upload, custom_webhook.

    Returns the connector config including the webhook endpoint URL and secret
    (secret is shown only once — save it!).

    Args:
        customer_id: The customer (tenant) ID
        connector_type: Type of connector (sfdc, hubspot, zendesk, n8n, csv_upload, custom_webhook)
        connector_name: Human-readable name (e.g. "Production Salesforce")
        description: Optional description
        sync_frequency_minutes: How often to sync (0 = webhook only)
        webhook_url: For n8n: the n8n webhook URL to call
    """
    with _get_app_context():
        from extensions import db
        from integration_models import IntegrationConnector, DEFAULT_FIELD_MAPPINGS
        import secrets

        webhook_secret = secrets.token_hex(32)
        webhook_secret_hash = hashlib.sha256(webhook_secret.encode()).hexdigest()

        connector = IntegrationConnector(
            customer_id=customer_id,
            connector_type=connector_type,
            connector_name=connector_name,
            description=description,
            auth_type='webhook_secret',
            webhook_url=webhook_url or None,
            webhook_secret_hash=webhook_secret_hash,
            sync_direction='inbound',
            sync_frequency_minutes=sync_frequency_minutes,
            sync_enabled=True,
            field_mapping=DEFAULT_FIELD_MAPPINGS.get(connector_type, {}),
            entity_mapping={},
            status='active',
        )
        db.session.add(connector)
        db.session.commit()

        result = connector.to_dict()
        result['webhook_secret'] = webhook_secret
        result['inbound_webhook_endpoint'] = f'/api/integrations/webhook/{customer_id}/{connector_type}'
        result['note'] = 'Save the webhook_secret — it will not be shown again.'

        return result


@mcp.tool
def get_integration_health(customer_id: int) -> Dict:
    """
    Get overall integration health summary for CS Ops monitoring.
    Shows connector status, recent sync stats, and pending events.

    Args:
        customer_id: The customer (tenant) ID
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    with _get_app_context():
        from integration_models import IntegrationConnector, IntegrationSyncLog, WebhookEvent
        from datetime import timedelta

        connectors = IntegrationConnector.query.filter_by(
            customer_id=customer_id
        ).all()

        total = len(connectors)
        active = sum(1 for c in connectors if c.status == 'active' and c.sync_enabled)
        errored = sum(1 for c in connectors if c.consecutive_errors and c.consecutive_errors > 0)
        stale = sum(
            1 for c in connectors
            if c.last_sync_at and c.last_sync_at < datetime.utcnow() - timedelta(hours=2)
            and c.sync_enabled and c.status == 'active'
        )

        since = datetime.utcnow() - timedelta(hours=24)
        recent_logs = IntegrationSyncLog.query.filter(
            IntegrationSyncLog.customer_id == customer_id,
            IntegrationSyncLog.started_at >= since,
        ).all()

        total_records = sum(
            (l.records_created or 0) + (l.records_updated or 0) for l in recent_logs
        )

        pending = WebhookEvent.query.filter_by(
            customer_id=customer_id,
            processing_status='pending',
        ).count()

        if errored > 0:
            status = 'degraded'
        elif stale > 0:
            status = 'warning'
        elif active > 0:
            status = 'healthy'
        else:
            status = 'no_connectors'

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'overall_status': status,
            'connectors': {'total': total, 'active': active, 'errored': errored, 'stale': stale},
            'last_24h': {'syncs': len(recent_logs), 'records_processed': total_records},
            'pending_events': pending,
            'connector_summary': [
                {
                    'name': c.connector_name,
                    'type': c.connector_type,
                    'status': c.status,
                    'last_sync': c.last_sync_at.isoformat() if c.last_sync_at else 'never',
                    'errors': c.consecutive_errors or 0,
                }
                for c in connectors
            ],
        }


@mcp.tool
def get_sync_logs(customer_id: int, connector_id: int = None, limit: int = 20) -> Dict:
    """
    Get recent sync activity logs.

    Args:
        customer_id: The customer (tenant) ID
        connector_id: Optional connector ID to filter by
        limit: Max logs to return (default 20)
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    with _get_app_context():
        from integration_models import IntegrationSyncLog
        from sqlalchemy import desc

        query = IntegrationSyncLog.query.filter_by(customer_id=customer_id)
        if connector_id:
            query = query.filter_by(connector_id=connector_id)

        logs = query.order_by(desc(IntegrationSyncLog.started_at)).limit(limit).all()

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'logs': [l.to_dict() for l in logs],
            'total': len(logs),
        }


def test_connector(customer_id: int, connector_id: int) -> Dict:
    """
    Test a connector's connectivity using a loopback stub.
    Creates a test record, verifies processing, and cleans up.

    Args:
        customer_id: The customer (tenant) ID
        connector_id: The connector to test
    """
    with _get_app_context():
        from extensions import db
        from integration_models import IntegrationConnector
        from integration_api import _process_ingest_record
        from models import Account

        connector = IntegrationConnector.query.filter_by(
            connector_id=connector_id, customer_id=customer_id
        ).first()

        if not connector:
            return {'error': 'Connector not found'}

        test_data = {
            'account_name': f'__mcp_test_{int(time.time())}',
            'revenue': 0,
            'industry': 'test',
            'external_account_id': f'mcp_test_{connector_id}_{int(time.time())}',
        }

        result = _process_ingest_record(
            customer_id=customer_id,
            source=connector.connector_type,
            entity_type='account',
            event_type='test',
            data=test_data,
            field_mapping=connector.field_mapping,
        )

        # Cleanup
        if result['success'] and result.get('target_id'):
            test_acct = Account.query.get(result['target_id'])
            if test_acct and test_acct.account_name.startswith('__mcp_test_'):
                db.session.delete(test_acct)

        connector.status_message = (
            f"MCP test passed at {datetime.utcnow().isoformat()}"
            if result['success']
            else f"MCP test failed: {result.get('error')}"
        )
        db.session.commit()

        return {
            'test_status': 'pass' if result['success'] else 'fail',
            'connector_name': connector.connector_name,
            'connector_type': connector.connector_type,
            'message': connector.status_message,
        }


# ============================================================
# n8n Workflow Trigger Tool
# ============================================================

def trigger_n8n_workflow(
    customer_id: int,
    workflow_name: str,
    account_id: int = None,
    payload: Dict = None,
) -> Dict:
    """
    Trigger an n8n workflow via webhook.
    Finds the n8n connector for this customer and fires its webhook URL
    with the specified payload. Use for playbook execution.

    Example: "Run the re-engagement playbook for K2 Hyperscale"

    Args:
        customer_id: The customer (tenant) ID
        workflow_name: Human label for the workflow (e.g. "re-engagement", "escalation")
        account_id: Optional account this workflow applies to
        payload: Optional extra data to send to n8n
    """
    with _get_app_context():
        from extensions import db
        from integration_models import IntegrationConnector
        from models import Account

        # Find n8n connector
        connector = IntegrationConnector.query.filter_by(
            customer_id=customer_id,
            connector_type='n8n',
            status='active',
        ).first()

        if not connector:
            return {
                'error': 'No active n8n connector found. Create one first with create_integration_connector().',
                'hint': 'connector_type="n8n", webhook_url="https://your-n8n.com/webhook/..."',
            }

        if not connector.webhook_url:
            return {'error': 'n8n connector has no webhook_url configured'}

        # Build payload
        account = None
        if account_id:
            account = Account.query.filter_by(
                account_id=account_id, customer_id=customer_id
            ).first()

        webhook_payload = {
            'workflow': workflow_name,
            'customer_id': customer_id,
            'account_id': account_id,
            'account_name': account.account_name if account else None,
            'account_arr': float(account.revenue) if account and account.revenue else None,
            'triggered_by': 'mcp_agent',
            'triggered_at': datetime.utcnow().isoformat(),
            **(payload or {}),
        }

        # Use loopback stub in dev
        from playbook_webhook_engine import _USE_LOOPBACK_STUB, _LOOPBACK_STUB_LOG

        if _USE_LOOPBACK_STUB:
            _LOOPBACK_STUB_LOG.append({
                'type': 'n8n_workflow',
                'workflow_name': workflow_name,
                'payload': webhook_payload,
                'webhook_url': connector.webhook_url,
                'timestamp': datetime.utcnow().isoformat(),
            })

            connector.last_sync_at = datetime.utcnow()
            connector.last_sync_status = 'success'
            db.session.commit()

            return {
                'status': 'triggered (loopback stub)',
                'workflow': workflow_name,
                'account': account.account_name if account else None,
                'webhook_url': connector.webhook_url,
                'note': 'Running in loopback mode — set _USE_LOOPBACK_STUB=False for real HTTP',
            }
        else:
            import requests as http_requests
            try:
                resp = http_requests.post(
                    connector.webhook_url,
                    json=webhook_payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30,
                )
                connector.last_sync_at = datetime.utcnow()
                connector.last_sync_status = 'success' if resp.status_code < 400 else 'error'
                db.session.commit()

                return {
                    'status': 'triggered',
                    'workflow': workflow_name,
                    'http_status': resp.status_code,
                    'response': resp.text[:500],
                }
            except Exception as e:
                connector.last_sync_at = datetime.utcnow()
                connector.last_sync_status = 'error'
                connector.last_error_message = str(e)
                db.session.commit()
                return {'error': f'n8n webhook failed: {str(e)}'}


# ============================================================
# Playbook Webhook Management Tools
# ============================================================

@mcp.tool
def list_playbook_webhook_triggers(customer_id: int) -> Dict:
    """
    List all playbook webhook triggers (outbound: CS Pulse → n8n).
    Shows what conditions fire webhooks and their recent activity.

    Args:
        customer_id: The customer (tenant) ID
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    with _get_app_context():
        from integration_models import PlaybookWebhookTrigger, PlaybookWebhookLog
        from sqlalchemy import desc

        triggers = PlaybookWebhookTrigger.query.filter_by(
            customer_id=customer_id
        ).all()

        result = []
        for t in triggers:
            recent = PlaybookWebhookLog.query.filter_by(
                trigger_id=t.trigger_id
            ).order_by(desc(PlaybookWebhookLog.fired_at)).limit(3).all()

            entry = t.to_dict()
            entry['recent_fires'] = [l.to_dict() for l in recent]
            result.append(entry)

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'triggers': result,
            'total': len(result),
        }


def create_playbook_webhook_trigger(
    customer_id: int,
    trigger_name: str,
    trigger_type: str,
    webhook_url: str,
    threshold: float = 50,
    operator: str = 'drops_below',
    metric: str = 'health_score',
    cooldown_minutes: int = 60,
    account_filter: Dict = None,
) -> Dict:
    """
    Create a playbook webhook trigger (CS Pulse → n8n/external).

    Example: "When any account's health drops below 50, fire webhook to n8n"

    Args:
        customer_id: The customer (tenant) ID
        trigger_name: Human label (e.g. "Critical Health Alert")
        trigger_type: health_drop, health_critical, signal_detected, renewal_approaching, expansion_ready
        webhook_url: URL to POST to when trigger fires
        threshold: Numeric threshold (default 50)
        operator: drops_below, rises_above, less_than, greater_than, changed_by
        metric: Which metric to watch (health_score, nrr, expansion_rate, etc.)
        cooldown_minutes: Don't re-fire for same account within this window
        account_filter: Optional scope filter (e.g. {"min_arr": 500000})
    """
    with _get_app_context():
        from extensions import db
        from integration_models import PlaybookWebhookTrigger
        import secrets

        webhook_secret = secrets.token_hex(32)

        trigger = PlaybookWebhookTrigger(
            customer_id=customer_id,
            trigger_name=trigger_name,
            trigger_type=trigger_type,
            trigger_condition={
                'metric': metric,
                'operator': operator,
                'threshold': threshold,
            },
            webhook_url=webhook_url,
            webhook_secret_hash=hashlib.sha256(webhook_secret.encode()).hexdigest(),
            enabled=True,
            cooldown_minutes=cooldown_minutes,
            max_fires_per_day=20,
            account_filter=account_filter,
        )
        db.session.add(trigger)
        db.session.commit()

        result = trigger.to_dict()
        result['webhook_secret'] = webhook_secret
        result['note'] = 'Trigger is now active. It will fire when conditions are met during health score updates.'

        return result


def fire_playbook_webhook(
    customer_id: int,
    trigger_id: int,
    account_id: int,
    context: Dict = None,
) -> Dict:
    """
    Manually fire a playbook webhook trigger for testing or one-off actions.

    Args:
        customer_id: The customer (tenant) ID
        trigger_id: Which trigger to fire
        account_id: Which account to fire for
        context: Optional override context (default uses current health score)
    """
    with _get_app_context():
        from extensions import db
        from integration_models import PlaybookWebhookTrigger
        from models import HealthScore
        from playbook_webhook_engine import _fire_webhook

        trigger = PlaybookWebhookTrigger.query.filter_by(
            trigger_id=trigger_id, customer_id=customer_id
        ).first()

        if not trigger:
            return {'error': 'Trigger not found'}

        if not context:
            # Build context from current health score
            health = HealthScore.query.filter_by(
                customer_id=customer_id, account_id=account_id
            ).order_by(HealthScore.calculated_at.desc()).first()

            context = {
                'health_score': float(health.health_score) if health else 0,
                'previous_health_score': None,
                'manual_fire': True,
            }

        result = _fire_webhook(trigger, customer_id, account_id, context)
        db.session.commit()

        return result
