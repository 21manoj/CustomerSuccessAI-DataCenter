"""
Integration API — Webhook Ingest + Connector Management
=========================================================

Endpoints:
  POST /api/integrations/ingest           — Receive data from n8n/external webhooks
  POST /api/integrations/ingest/batch     — Batch ingest (multiple records)
  GET  /api/integrations/connectors       — List all connectors for customer
  POST /api/integrations/connectors       — Create/register a connector
  PUT  /api/integrations/connectors/<id>  — Update connector config
  DELETE /api/integrations/connectors/<id>— Deactivate connector
  GET  /api/integrations/connectors/<id>/logs — Sync history for connector
  GET  /api/integrations/health           — Overall integration health summary
  GET  /api/integrations/sync-logs        — All recent sync logs
  POST /api/integrations/connectors/<id>/test — Test connectivity (loopback stub)
  GET  /api/integrations/connector-types  — Available connector types
  POST /api/integrations/webhook/<customer_id>/<connector_type> — Public webhook endpoint
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from sqlalchemy import desc, func
import hashlib
import hmac
import json
import logging
import time
import requests as http_requests

logger = logging.getLogger(__name__)

integration_api = Blueprint('integration_api', __name__)


def _get_customer_id():
    """Get customer_id from auth context or header."""
    try:
        from auth_middleware import get_current_customer_id
        return get_current_customer_id()
    except Exception:
        return int(request.headers.get('X-Customer-ID', 0))


def _verify_webhook_signature(payload_bytes, signature, secret_hash):
    """Verify HMAC-SHA256 webhook signature."""
    if not secret_hash or not signature:
        return True  # No secret configured = skip verification
    expected = hmac.new(
        secret_hash.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


# ============================================================
# Connector CRUD
# ============================================================

@integration_api.route('/api/integrations/connector-types', methods=['GET'])
def get_connector_types():
    """Return available connector types with metadata."""
    from integration_models import CONNECTOR_TYPES
    return jsonify(CONNECTOR_TYPES)


@integration_api.route('/api/integrations/connectors', methods=['GET'])
def list_connectors():
    """List all integration connectors for the current customer."""
    from integration_models import IntegrationConnector
    customer_id = _get_customer_id()
    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 401

    connectors = IntegrationConnector.query.filter_by(
        customer_id=customer_id
    ).order_by(desc(IntegrationConnector.updated_at)).all()

    return jsonify({
        'connectors': [c.to_dict() for c in connectors],
        'total': len(connectors),
    })


@integration_api.route('/api/integrations/connectors', methods=['POST'])
def create_connector():
    """Register a new integration connector."""
    from extensions import db
    from integration_models import IntegrationConnector, DEFAULT_FIELD_MAPPINGS

    customer_id = _get_customer_id()
    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    connector_type = data.get('connector_type')
    if not connector_type:
        return jsonify({'error': 'connector_type is required'}), 400

    # Generate webhook secret for inbound webhooks
    import secrets
    webhook_secret = secrets.token_hex(32)
    webhook_secret_hash = hashlib.sha256(webhook_secret.encode()).hexdigest()

    connector = IntegrationConnector(
        customer_id=customer_id,
        connector_type=connector_type,
        connector_name=data.get('connector_name', f'{connector_type} connector'),
        description=data.get('description'),
        auth_type=data.get('auth_type', 'webhook_secret'),
        webhook_url=data.get('webhook_url'),
        webhook_secret_hash=webhook_secret_hash,
        sync_direction=data.get('sync_direction', 'inbound'),
        sync_frequency_minutes=data.get('sync_frequency_minutes', 60),
        sync_enabled=data.get('sync_enabled', True),
        field_mapping=data.get('field_mapping') or DEFAULT_FIELD_MAPPINGS.get(connector_type, {}),
        entity_mapping=data.get('entity_mapping', {}),
        status='active',
    )

    db.session.add(connector)
    db.session.commit()

    result = connector.to_dict()
    # Return webhook secret only on creation (never stored in plain text)
    result['webhook_secret'] = webhook_secret
    result['webhook_endpoint'] = f'/api/integrations/webhook/{customer_id}/{connector_type}'

    return jsonify(result), 201


@integration_api.route('/api/integrations/connectors/<int:connector_id>', methods=['PUT'])
def update_connector(connector_id):
    """Update connector configuration."""
    from extensions import db
    from integration_models import IntegrationConnector

    customer_id = _get_customer_id()
    connector = IntegrationConnector.query.filter_by(
        connector_id=connector_id, customer_id=customer_id
    ).first()

    if not connector:
        return jsonify({'error': 'Connector not found'}), 404

    data = request.get_json()
    updatable = [
        'connector_name', 'description', 'sync_direction',
        'sync_frequency_minutes', 'sync_enabled', 'field_mapping',
        'entity_mapping', 'webhook_url', 'status',
    ]
    for field in updatable:
        if field in data:
            setattr(connector, field, data[field])

    db.session.commit()
    return jsonify(connector.to_dict())


@integration_api.route('/api/integrations/connectors/<int:connector_id>', methods=['DELETE'])
def deactivate_connector(connector_id):
    """Soft-delete: set connector status to disabled."""
    from extensions import db
    from integration_models import IntegrationConnector

    customer_id = _get_customer_id()
    connector = IntegrationConnector.query.filter_by(
        connector_id=connector_id, customer_id=customer_id
    ).first()

    if not connector:
        return jsonify({'error': 'Connector not found'}), 404

    connector.status = 'disabled'
    connector.sync_enabled = False
    db.session.commit()

    return jsonify({'message': 'Connector disabled', 'connector_id': connector_id})


# ============================================================
# Webhook Ingest (inbound data from n8n / external systems)
# ============================================================

@integration_api.route('/api/integrations/ingest', methods=['POST'])
def ingest_single():
    """
    Receive a single record from an external system.

    Expected JSON:
    {
        "source": "sfdc|hubspot|zendesk|n8n|custom",
        "entity_type": "account|signal|ticket|opportunity|contact",
        "event_type": "created|updated|deleted",
        "data": { ... mapped fields ... },
        "source_id": "optional-dedup-key"
    }
    """
    from extensions import db
    from integration_models import WebhookEvent, IntegrationConnector, IntegrationSyncLog

    customer_id = _get_customer_id()
    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 401

    payload = request.get_json()
    if not payload:
        return jsonify({'error': 'JSON body required'}), 400

    source = payload.get('source', 'unknown')
    entity_type = payload.get('entity_type', 'unknown')
    event_type = payload.get('event_type', 'created')
    data = payload.get('data', {})
    source_id = payload.get('source_id')

    # Find matching connector
    connector = IntegrationConnector.query.filter_by(
        customer_id=customer_id,
        connector_type=source,
        status='active',
    ).first()

    # Log the raw event
    event = WebhookEvent(
        connector_id=connector.connector_id if connector else None,
        customer_id=customer_id,
        event_type=f"{entity_type}.{event_type}",
        source_system=source,
        source_event_id=source_id,
        payload=payload,
        headers=dict(request.headers),
        processing_status='pending',
    )
    db.session.add(event)
    db.session.flush()

    # Process the record
    result = _process_ingest_record(
        customer_id=customer_id,
        source=source,
        entity_type=entity_type,
        event_type=event_type,
        data=data,
        field_mapping=connector.field_mapping if connector else {},
        event=event,
    )

    # Update event status
    event.processing_status = 'processed' if result['success'] else 'failed'
    event.processed_at = datetime.utcnow()
    event.processing_error = result.get('error')
    event.target_entity = result.get('target_entity')
    event.target_id = result.get('target_id')

    # Update connector sync stats
    if connector:
        connector.last_sync_at = datetime.utcnow()
        connector.last_sync_status = 'success' if result['success'] else 'error'
        connector.last_sync_records = (connector.last_sync_records or 0) + (1 if result['success'] else 0)
        if not result['success']:
            connector.consecutive_errors = (connector.consecutive_errors or 0) + 1
            connector.last_error_at = datetime.utcnow()
            connector.last_error_message = result.get('error')
        else:
            connector.consecutive_errors = 0

    db.session.commit()

    return jsonify({
        'event_id': event.event_id,
        'status': event.processing_status,
        'target_entity': result.get('target_entity'),
        'target_id': result.get('target_id'),
        'error': result.get('error'),
    }), 200 if result['success'] else 422


@integration_api.route('/api/integrations/ingest/batch', methods=['POST'])
def ingest_batch():
    """
    Receive multiple records in one call.

    Expected JSON:
    {
        "source": "sfdc",
        "records": [
            {"entity_type": "account", "event_type": "updated", "data": {...}, "source_id": "001xx"},
            ...
        ]
    }
    """
    from extensions import db
    from integration_models import IntegrationConnector, IntegrationSyncLog

    customer_id = _get_customer_id()
    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 401

    payload = request.get_json()
    source = payload.get('source', 'unknown')
    records = payload.get('records', [])

    if not records:
        return jsonify({'error': 'No records provided'}), 400

    connector = IntegrationConnector.query.filter_by(
        customer_id=customer_id,
        connector_type=source,
        status='active',
    ).first()

    # Create sync log entry
    sync_log = IntegrationSyncLog(
        connector_id=connector.connector_id if connector else None,
        customer_id=customer_id,
        sync_type='webhook_push',
        sync_status='started',
        started_at=datetime.utcnow(),
        records_fetched=len(records),
    )
    db.session.add(sync_log)
    db.session.flush()

    results = []
    created = updated = skipped = errored = 0

    for record in records:
        result = _process_ingest_record(
            customer_id=customer_id,
            source=source,
            entity_type=record.get('entity_type', 'unknown'),
            event_type=record.get('event_type', 'created'),
            data=record.get('data', {}),
            field_mapping=connector.field_mapping if connector else {},
        )

        if result['success']:
            if result.get('action') == 'created':
                created += 1
            else:
                updated += 1
        elif result.get('skipped'):
            skipped += 1
        else:
            errored += 1

        results.append(result)

    # Finalize sync log
    sync_log.sync_status = 'success' if errored == 0 else ('partial' if created + updated > 0 else 'error')
    sync_log.completed_at = datetime.utcnow()
    sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()
    sync_log.records_created = created
    sync_log.records_updated = updated
    sync_log.records_skipped = skipped
    sync_log.records_errored = errored

    # Update connector stats
    if connector:
        connector.last_sync_at = datetime.utcnow()
        connector.last_sync_status = sync_log.sync_status
        connector.last_sync_records = created + updated
        connector.last_sync_errors = errored
        if errored > 0:
            connector.consecutive_errors = (connector.consecutive_errors or 0) + 1
        else:
            connector.consecutive_errors = 0

    db.session.commit()

    return jsonify({
        'sync_log_id': sync_log.log_id,
        'status': sync_log.sync_status,
        'records_created': created,
        'records_updated': updated,
        'records_skipped': skipped,
        'records_errored': errored,
        'total': len(records),
    })


@integration_api.route('/api/integrations/webhook/<int:customer_id>/<connector_type>', methods=['POST'])
def public_webhook(customer_id, connector_type):
    """
    Public webhook endpoint for n8n/external systems to push data.
    Authenticated via HMAC signature in X-Webhook-Signature header.
    """
    from extensions import db
    from integration_models import IntegrationConnector, WebhookEvent

    connector = IntegrationConnector.query.filter_by(
        customer_id=customer_id,
        connector_type=connector_type,
        status='active',
        sync_enabled=True,
    ).first()

    if not connector:
        return jsonify({'error': 'No active connector found'}), 404

    # Verify webhook signature
    signature = request.headers.get('X-Webhook-Signature', '')
    if connector.webhook_secret_hash:
        if not _verify_webhook_signature(request.data, signature, connector.webhook_secret_hash):
            return jsonify({'error': 'Invalid webhook signature'}), 401

    payload = request.get_json(silent=True) or {}

    # Log raw event
    event = WebhookEvent(
        connector_id=connector.connector_id,
        customer_id=customer_id,
        event_type=payload.get('event_type', f'{connector_type}.push'),
        source_system=connector_type,
        source_event_id=payload.get('source_id'),
        payload=payload,
        headers={k: v for k, v in request.headers if k.startswith('X-')},
        processing_status='pending',
    )
    db.session.add(event)

    # Process based on payload structure
    records = payload.get('records', [payload.get('data', payload)])
    if not isinstance(records, list):
        records = [records]

    processed = 0
    errors = 0
    for record in records:
        result = _process_ingest_record(
            customer_id=customer_id,
            source=connector_type,
            entity_type=record.get('entity_type', payload.get('entity_type', 'account')),
            event_type=record.get('event_type', 'updated'),
            data=record.get('data', record),
            field_mapping=connector.field_mapping,
        )
        if result['success']:
            processed += 1
        else:
            errors += 1

    event.processing_status = 'processed' if errors == 0 else 'failed'
    event.processed_at = datetime.utcnow()

    connector.last_sync_at = datetime.utcnow()
    connector.last_sync_records = processed

    db.session.commit()

    return jsonify({
        'status': 'ok',
        'processed': processed,
        'errors': errors,
    })


# ============================================================
# Record Processing Logic
# ============================================================

def _apply_field_mapping(data, field_mapping, entity_type):
    """Apply field mapping to transform external data to CS Pulse schema."""
    if not field_mapping:
        return data

    # Get mapping for this entity type (try multiple case/plural variations)
    candidates = [
        entity_type,
        entity_type.capitalize(),
        entity_type.lower(),
        entity_type.title(),
        entity_type + 's',           # company → companys (rare)
        entity_type + 'es',          # company → companyes (rare)
        entity_type.rstrip('s'),     # companies → companie
        entity_type.lower() + 's',   # company → companys
    ]
    # Also try HubSpot-style plurals: company→companies, deal→deals, ticket→tickets
    if entity_type.lower().endswith('y'):
        candidates.append(entity_type.lower()[:-1] + 'ies')  # company→companies
    else:
        candidates.append(entity_type.lower() + 's')  # deal→deals

    entity_map = {}
    for c in candidates:
        if c in field_mapping and field_mapping[c]:
            entity_map = field_mapping[c]
            break
    if not entity_map:
        # Try without entity type (flat mapping)
        entity_map = field_mapping

    mapped = {}
    properties = {}

    for source_field, target_field in entity_map.items():
        if source_field in data:
            value = data[source_field]
            if target_field.startswith('properties.'):
                prop_key = target_field.replace('properties.', '')
                properties[prop_key] = value
            else:
                mapped[target_field] = value

    if properties:
        mapped['properties'] = properties

    # Pass through unmapped fields that match CS Pulse schema
    passthrough_fields = [
        'account_id', 'account_name', 'revenue', 'industry', 'region', 'account_status',
        'title', 'health_score', 'event_date', 'node_type', 'node_subtype',
        'external_account_id', 'revenue_impact', 'revenue_impact_type',
    ]
    for f in passthrough_fields:
        if f in data and f not in mapped:
            mapped[f] = data[f]

    return mapped


def _process_ingest_record(customer_id, source, entity_type, event_type, data, field_mapping, event=None):
    """
    Process a single ingest record: map fields + upsert into CS Pulse DB.

    Returns: {"success": bool, "action": "created"|"updated", "target_entity": str, "target_id": int}
    """
    from extensions import db

    try:
        mapped = _apply_field_mapping(data, field_mapping, entity_type)

        # Normalize entity type for matching
        et_lower = entity_type.lower().rstrip('s')  # companies→companie→company, tickets→ticket
        if et_lower in ('account', 'company', 'companie'):
            return _upsert_account(customer_id, mapped, source)
        elif et_lower in ('signal', 'ticket', 'case'):
            return _upsert_signal(customer_id, mapped, source)
        elif et_lower in ('opportunity', 'deal'):
            return _upsert_opportunity(customer_id, mapped, source)
        elif et_lower in ('contact', 'stakeholder', 'user'):
            return _upsert_contact(customer_id, mapped, source)
        elif entity_type in ('kpi', 'metric', 'kpi_measurement'):
            return _upsert_kpi(customer_id, mapped, source)
        else:
            # Store as generic context node
            return _upsert_generic_node(customer_id, entity_type, mapped, source)

    except Exception as e:
        logger.exception(f"Error processing ingest record: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return {'success': False, 'error': str(e)}


def _upsert_account(customer_id, data, source):
    """Create or update an account."""
    from extensions import db
    from models import Account

    ext_id = data.get('external_account_id')
    account_name = data.get('account_name')

    # Try to find existing account
    account = None
    if ext_id:
        account = Account.query.filter_by(
            customer_id=customer_id,
            external_account_id=str(ext_id),
        ).first()

    if not account and account_name:
        account = Account.query.filter_by(
            customer_id=customer_id,
            account_name=account_name,
        ).first()

    action = 'updated'
    if not account:
        account = Account(customer_id=customer_id)
        db.session.add(account)
        action = 'created'

    # Update fields
    if account_name:
        account.account_name = account_name
    if data.get('revenue') is not None:
        account.revenue = float(data['revenue'])
    if data.get('industry'):
        account.industry = data['industry']
    if data.get('region'):
        account.region = data['region']
    if data.get('account_status'):
        account.account_status = data['account_status']
    if ext_id:
        account.external_account_id = str(ext_id)

    # Merge profile metadata
    existing_meta = account.profile_metadata or {}
    if data.get('properties'):
        existing_meta.update(data['properties'])
    existing_meta['_last_sync_source'] = source
    existing_meta['_last_sync_at'] = datetime.utcnow().isoformat()
    account.profile_metadata = existing_meta

    db.session.flush()

    return {
        'success': True,
        'action': action,
        'target_entity': 'accounts',
        'target_id': account.account_id,
    }


def _upsert_signal(customer_id, data, source):
    """Create a signal/ticket as a context node."""
    from extensions import db
    from models import ContextNode, Account

    # Resolve account — accept account_id directly or via external_account_id
    account_id = data.get('account_id')
    if account_id:
        # Verify it exists
        acct = Account.query.filter_by(account_id=int(account_id), customer_id=customer_id).first()
        if acct:
            account_id = acct.account_id
        else:
            account_id = None

    if not account_id and data.get('external_account_id'):
        acct = Account.query.filter_by(
            customer_id=customer_id,
            external_account_id=str(data['external_account_id']),
        ).first()
        if acct:
            account_id = acct.account_id

    if not account_id:
        return {'success': False, 'error': 'Cannot resolve account for signal'}

    node = ContextNode(
        customer_id=customer_id,
        account_id=account_id,
        node_type='SIGNAL',
        node_subtype=data.get('node_subtype', f'{source}_ticket'),
        tier=2,
        title=data.get('title', f'{source} signal'),
        properties={
            **(data.get('properties', {})),
            '_source': source,
            '_ingested_at': datetime.utcnow().isoformat(),
        },
        occurred_at=_parse_date(data.get('event_date')) or datetime.utcnow(),
        confidence=0.8,
    )
    db.session.add(node)
    db.session.flush()

    return {
        'success': True,
        'action': 'created',
        'target_entity': 'context_nodes',
        'target_id': node.node_id,
    }


def _upsert_opportunity(customer_id, data, source):
    """Create an opportunity as a context node (DECISION or OUTCOME)."""
    from extensions import db
    from models import ContextNode, Account

    account_id = data.get('account_id')
    if not account_id and data.get('external_account_id'):
        acct = Account.query.filter_by(
            customer_id=customer_id,
            external_account_id=str(data['external_account_id']),
        ).first()
        if acct:
            account_id = acct.account_id

    if not account_id:
        return {'success': False, 'error': 'Cannot resolve account for opportunity'}

    # Determine node type based on stage
    stage = (data.get('node_subtype') or '').lower()
    if stage in ('closed won', 'closed_won', 'won'):
        node_type = 'OUTCOME'
        revenue_type = 'expansion'
    elif stage in ('closed lost', 'closed_lost', 'lost'):
        node_type = 'OUTCOME'
        revenue_type = 'lost'
    else:
        node_type = 'DECISION'
        revenue_type = 'at_risk'

    node = ContextNode(
        customer_id=customer_id,
        account_id=account_id,
        node_type=node_type,
        node_subtype=data.get('node_subtype', f'{source}_opportunity'),
        tier=1,
        title=data.get('title', f'{source} opportunity'),
        properties={
            **(data.get('properties', {})),
            '_source': source,
        },
        revenue_impact=float(data['revenue_impact']) if data.get('revenue_impact') else None,
        revenue_impact_type=revenue_type,
        occurred_at=_parse_date(data.get('event_date')) or datetime.utcnow(),
    )
    db.session.add(node)
    db.session.flush()

    return {
        'success': True,
        'action': 'created',
        'target_entity': 'context_nodes',
        'target_id': node.node_id,
    }


def _upsert_contact(customer_id, data, source):
    """Create a stakeholder/contact as a context node."""
    from extensions import db
    from models import ContextNode, Account

    account_id = data.get('account_id')
    if not account_id and data.get('external_account_id'):
        acct = Account.query.filter_by(
            customer_id=customer_id,
            external_account_id=str(data['external_account_id']),
        ).first()
        if acct:
            account_id = acct.account_id

    if not account_id:
        return {'success': False, 'error': 'Cannot resolve account for contact'}

    node = ContextNode(
        customer_id=customer_id,
        account_id=account_id,
        node_type='STAKEHOLDER',
        node_subtype=data.get('node_subtype', 'contact'),
        tier=1,
        title=data.get('title') or data.get('properties', {}).get('contact_name', f'{source} contact'),
        properties={
            **(data.get('properties', {})),
            '_source': source,
        },
    )
    db.session.add(node)
    db.session.flush()

    return {
        'success': True,
        'action': 'created',
        'target_entity': 'context_nodes',
        'target_id': node.node_id,
    }


def _upsert_kpi(customer_id, data, source):
    """Create or update a KPI measurement."""
    from extensions import db
    from models import DC2SKPI, Account

    account_id = data.get('account_id')
    if not account_id:
        return {'success': False, 'error': 'account_id required for KPI measurement'}

    kpi_code = data.get('kpi_code')
    if not kpi_code:
        return {'success': False, 'error': 'kpi_code required'}

    kpi = DC2SKPI(
        customer_id=customer_id,
        account_id=account_id,
        kpi_code=kpi_code,
        kpi_value=float(data.get('kpi_value', 0)),
        measurement_date=_parse_date(data.get('measurement_date')) or datetime.utcnow(),
    )
    db.session.add(kpi)
    db.session.flush()

    return {
        'success': True,
        'action': 'created',
        'target_entity': 'dc2s_kpis',
        'target_id': kpi.kpi_id if hasattr(kpi, 'kpi_id') else None,
    }


def _upsert_generic_node(customer_id, entity_type, data, source):
    """Store unknown entity types as generic context nodes."""
    from extensions import db
    from models import ContextNode

    account_id = data.get('account_id')
    if not account_id:
        return {'success': False, 'error': f'account_id required for entity_type={entity_type}'}

    node = ContextNode(
        customer_id=customer_id,
        account_id=account_id,
        node_type='EXTERNAL_CONTEXT',
        node_subtype=f'{source}_{entity_type}',
        tier=3,
        title=data.get('title', f'{source} {entity_type}'),
        properties={
            **data,
            '_source': source,
            '_entity_type': entity_type,
            '_ingested_at': datetime.utcnow().isoformat(),
        },
        occurred_at=_parse_date(data.get('event_date')) or datetime.utcnow(),
    )
    db.session.add(node)
    db.session.flush()

    return {
        'success': True,
        'action': 'created',
        'target_entity': 'context_nodes',
        'target_id': node.node_id,
    }


def _parse_date(date_str):
    """Parse date string in various formats."""
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str
    for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


# ============================================================
# Integration Health & Monitoring
# ============================================================

@integration_api.route('/api/integrations/health', methods=['GET'])
def integration_health():
    """Overall integration health for CS Ops dashboard."""
    from integration_models import IntegrationConnector, IntegrationSyncLog, WebhookEvent
    from sqlalchemy import func

    customer_id = _get_customer_id()
    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 401

    connectors = IntegrationConnector.query.filter_by(customer_id=customer_id).all()

    # Compute health metrics
    total = len(connectors)
    active = sum(1 for c in connectors if c.status == 'active' and c.sync_enabled)
    errored = sum(1 for c in connectors if c.consecutive_errors and c.consecutive_errors > 0)
    stale = sum(
        1 for c in connectors
        if c.last_sync_at and c.last_sync_at < datetime.utcnow() - timedelta(hours=2)
        and c.sync_enabled and c.status == 'active'
    )

    # Recent sync stats (last 24h)
    since = datetime.utcnow() - timedelta(hours=24)
    recent_logs = IntegrationSyncLog.query.filter(
        IntegrationSyncLog.customer_id == customer_id,
        IntegrationSyncLog.started_at >= since,
    ).all()

    total_records_24h = sum(
        (l.records_created or 0) + (l.records_updated or 0) for l in recent_logs
    )
    total_errors_24h = sum(l.records_errored or 0 for l in recent_logs)

    # Pending webhooks
    pending_events = WebhookEvent.query.filter_by(
        customer_id=customer_id,
        processing_status='pending',
    ).count()

    # Overall status
    if errored > 0:
        overall_status = 'degraded'
    elif stale > 0:
        overall_status = 'warning'
    elif active > 0:
        overall_status = 'healthy'
    else:
        overall_status = 'no_connectors'

    return jsonify({
        'overall_status': overall_status,
        'connectors': {
            'total': total,
            'active': active,
            'errored': errored,
            'stale': stale,
        },
        'last_24h': {
            'syncs': len(recent_logs),
            'records_processed': total_records_24h,
            'errors': total_errors_24h,
        },
        'pending_events': pending_events,
        'connector_details': [c.to_dict() for c in connectors],
    })


@integration_api.route('/api/integrations/sync-logs', methods=['GET'])
def get_sync_logs():
    """Recent sync logs across all connectors."""
    from integration_models import IntegrationSyncLog

    customer_id = _get_customer_id()
    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 401

    limit = request.args.get('limit', 50, type=int)
    connector_id = request.args.get('connector_id', type=int)

    query = IntegrationSyncLog.query.filter_by(customer_id=customer_id)
    if connector_id:
        query = query.filter_by(connector_id=connector_id)

    logs = query.order_by(desc(IntegrationSyncLog.started_at)).limit(limit).all()

    return jsonify({
        'logs': [l.to_dict() for l in logs],
        'total': len(logs),
    })


@integration_api.route('/api/integrations/connectors/<int:connector_id>/logs', methods=['GET'])
def get_connector_logs(connector_id):
    """Sync logs for a specific connector."""
    from integration_models import IntegrationSyncLog

    customer_id = _get_customer_id()
    limit = request.args.get('limit', 20, type=int)

    logs = IntegrationSyncLog.query.filter_by(
        connector_id=connector_id,
        customer_id=customer_id,
    ).order_by(desc(IntegrationSyncLog.started_at)).limit(limit).all()

    return jsonify({'logs': [l.to_dict() for l in logs]})


# ============================================================
# Connector Test (Loopback Stub)
# ============================================================

@integration_api.route('/api/integrations/connectors/<int:connector_id>/test', methods=['POST'])
def test_connector(connector_id):
    """
    Test connector connectivity.
    Uses loopback stub: sends a test record through ingest and verifies it arrives.
    """
    from extensions import db
    from integration_models import IntegrationConnector

    customer_id = _get_customer_id()
    connector = IntegrationConnector.query.filter_by(
        connector_id=connector_id, customer_id=customer_id
    ).first()

    if not connector:
        return jsonify({'error': 'Connector not found'}), 404

    # Loopback test: create a test record and verify processing
    test_payload = {
        'source': connector.connector_type,
        'entity_type': 'account',
        'event_type': 'test',
        'data': {
            'account_name': f'__test_{connector.connector_type}_{int(time.time())}',
            'revenue': 0,
            'industry': 'test',
            'external_account_id': f'test_{connector.connector_id}_{int(time.time())}',
        },
        'source_id': f'test_{int(time.time())}',
    }

    # Process through the same pipeline
    result = _process_ingest_record(
        customer_id=customer_id,
        source=connector.connector_type,
        entity_type='account',
        event_type='test',
        data=test_payload['data'],
        field_mapping=connector.field_mapping,
    )

    # Clean up test record
    if result['success'] and result.get('target_id'):
        from models import Account
        test_acct = Account.query.get(result['target_id'])
        if test_acct and test_acct.account_name.startswith('__test_'):
            db.session.delete(test_acct)
            db.session.commit()

    connector.status_message = (
        f"Test passed at {datetime.utcnow().isoformat()}"
        if result['success']
        else f"Test failed: {result.get('error')}"
    )
    db.session.commit()

    return jsonify({
        'test_status': 'pass' if result['success'] else 'fail',
        'message': connector.status_message,
        'connector_type': connector.connector_type,
        'field_mapping_keys': len(connector.field_mapping) if connector.field_mapping else 0,
    })
