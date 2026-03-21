"""
Integration Registry Models
============================

DB models for external data source connectors (SFDC, HubSpot, Zendesk, n8n).
Tracks connector configuration, sync status, field mappings, and audit trail.
"""

from extensions import db
from datetime import datetime


class IntegrationConnector(db.Model):
    """
    Registry of configured external data connectors per customer.
    Each connector represents one external system (e.g. Salesforce, HubSpot).
    """
    __tablename__ = 'integration_connectors'

    connector_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)

    # Connector identity
    connector_type = db.Column(db.String(50), nullable=False)
    # sfdc, hubspot, zendesk, n8n, csv_upload, api_push, custom_webhook
    connector_name = db.Column(db.String(255), nullable=False)
    # Human-readable label, e.g. "Production Salesforce"
    description = db.Column(db.Text)

    # Connection config (encrypted at rest in production)
    auth_type = db.Column(db.String(30), default='oauth2')
    # oauth2, api_key, webhook_secret, basic_auth
    auth_config_encrypted = db.Column(db.Text)
    # Encrypted JSON: {"client_id": "...", "refresh_token": "...", ...}
    webhook_url = db.Column(db.String(500))
    # Inbound webhook URL (for n8n push)
    webhook_secret_hash = db.Column(db.String(64))
    # HMAC secret hash for webhook validation

    # Sync configuration
    sync_direction = db.Column(db.String(20), default='inbound')
    # inbound (external→CS Pulse), outbound (CS Pulse→external), bidirectional
    sync_frequency_minutes = db.Column(db.Integer, default=60)
    # 0 = webhook/real-time only
    sync_enabled = db.Column(db.Boolean, default=True)

    # Field mapping: maps external fields to CS Pulse schema
    field_mapping = db.Column(db.JSON, default=dict)
    # Example: {"sfdc_AccountName": "account_name", "sfdc_AnnualRevenue": "revenue", ...}

    # Entity mapping: which external objects map to which CS Pulse entities
    entity_mapping = db.Column(db.JSON, default=dict)
    # Example: {"Account": "accounts", "Opportunity": "context_nodes", "Case": "enhanced_signals"}

    # Status tracking
    status = db.Column(db.String(30), default='pending_setup')
    # pending_setup, active, paused, error, disabled, expired
    status_message = db.Column(db.Text)
    last_sync_at = db.Column(db.DateTime)
    last_sync_status = db.Column(db.String(20))
    # success, partial, error
    last_sync_records = db.Column(db.Integer, default=0)
    last_sync_errors = db.Column(db.Integer, default=0)
    last_error_at = db.Column(db.DateTime)
    last_error_message = db.Column(db.Text)
    consecutive_errors = db.Column(db.Integer, default=0)

    # Metadata
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    created_by = db.Column(db.String(255))

    __table_args__ = (
        db.Index('idx_connector_customer_type', 'customer_id', 'connector_type'),
        db.Index('idx_connector_status', 'status'),
    )

    def to_dict(self):
        return {
            'connector_id': self.connector_id,
            'customer_id': self.customer_id,
            'connector_type': self.connector_type,
            'connector_name': self.connector_name,
            'description': self.description,
            'auth_type': self.auth_type,
            'sync_direction': self.sync_direction,
            'sync_frequency_minutes': self.sync_frequency_minutes,
            'sync_enabled': self.sync_enabled,
            'field_mapping': self.field_mapping,
            'entity_mapping': self.entity_mapping,
            'status': self.status,
            'status_message': self.status_message,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'last_sync_status': self.last_sync_status,
            'last_sync_records': self.last_sync_records,
            'last_sync_errors': self.last_sync_errors,
            'last_error_at': self.last_error_at.isoformat() if self.last_error_at else None,
            'last_error_message': self.last_error_message,
            'consecutive_errors': self.consecutive_errors,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class IntegrationSyncLog(db.Model):
    """
    Audit trail of every sync operation.
    One row per sync attempt per connector.
    """
    __tablename__ = 'integration_sync_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    connector_id = db.Column(db.Integer, db.ForeignKey('integration_connectors.connector_id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)

    # Sync details
    sync_type = db.Column(db.String(30), nullable=False)
    # full, incremental, webhook_push, manual
    sync_status = db.Column(db.String(20), nullable=False)
    # started, success, partial, error
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Float)

    # Record counts
    records_fetched = db.Column(db.Integer, default=0)
    records_created = db.Column(db.Integer, default=0)
    records_updated = db.Column(db.Integer, default=0)
    records_skipped = db.Column(db.Integer, default=0)
    records_errored = db.Column(db.Integer, default=0)

    # Error details
    error_message = db.Column(db.Text)
    error_details = db.Column(db.JSON)
    # [{field: "revenue", error: "null value", row: 42}, ...]

    # Source metadata
    source_query = db.Column(db.Text)
    # e.g. "SELECT * FROM Account WHERE LastModifiedDate > ..."
    watermark_value = db.Column(db.String(255))
    # High-water mark for incremental sync (e.g. last modified timestamp)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (
        db.Index('idx_synclog_connector_time', 'connector_id', 'started_at'),
        db.Index('idx_synclog_customer_status', 'customer_id', 'sync_status'),
    )

    def to_dict(self):
        return {
            'log_id': self.log_id,
            'connector_id': self.connector_id,
            'customer_id': self.customer_id,
            'sync_type': self.sync_type,
            'sync_status': self.sync_status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'records_fetched': self.records_fetched,
            'records_created': self.records_created,
            'records_updated': self.records_updated,
            'records_skipped': self.records_skipped,
            'records_errored': self.records_errored,
            'error_message': self.error_message,
            'watermark_value': self.watermark_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class WebhookEvent(db.Model):
    """
    Raw inbound webhook events (before processing).
    Stores the raw payload for replay/debugging.
    """
    __tablename__ = 'webhook_events'

    event_id = db.Column(db.Integer, primary_key=True)
    connector_id = db.Column(db.Integer, db.ForeignKey('integration_connectors.connector_id'), index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)

    # Event details
    event_type = db.Column(db.String(100))
    # e.g. "account.updated", "ticket.created", "deal.won"
    source_system = db.Column(db.String(50), nullable=False)
    # sfdc, hubspot, zendesk, n8n
    source_event_id = db.Column(db.String(255))
    # Dedup key from source system

    # Raw payload
    payload = db.Column(db.JSON, nullable=False)
    headers = db.Column(db.JSON)
    # Stored for signature verification replay

    # Processing status
    processing_status = db.Column(db.String(20), default='pending')
    # pending, processing, processed, failed, skipped
    processed_at = db.Column(db.DateTime)
    processing_error = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)

    # What was created/updated
    target_entity = db.Column(db.String(50))
    # accounts, context_nodes, enhanced_signals, health_scores
    target_id = db.Column(db.Integer)

    received_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (
        db.Index('idx_webhook_customer_status', 'customer_id', 'processing_status'),
        db.Index('idx_webhook_source_dedup', 'source_system', 'source_event_id'),
    )

    def to_dict(self):
        return {
            'event_id': self.event_id,
            'connector_id': self.connector_id,
            'customer_id': self.customer_id,
            'event_type': self.event_type,
            'source_system': self.source_system,
            'source_event_id': self.source_event_id,
            'processing_status': self.processing_status,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'processing_error': self.processing_error,
            'retry_count': self.retry_count,
            'target_entity': self.target_entity,
            'target_id': self.target_id,
            'received_at': self.received_at.isoformat() if self.received_at else None,
        }


class PlaybookWebhookTrigger(db.Model):
    """
    Configuration for outbound webhooks fired when playbook conditions are met.
    CS Pulse → n8n (or any external orchestrator).
    """
    __tablename__ = 'playbook_webhook_triggers'

    trigger_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)

    # Trigger definition
    trigger_name = db.Column(db.String(255), nullable=False)
    trigger_type = db.Column(db.String(50), nullable=False)
    # health_drop, health_critical, signal_detected, renewal_approaching, expansion_ready, custom
    trigger_condition = db.Column(db.JSON, nullable=False)
    # Example: {"metric": "health_score", "operator": "drops_below", "threshold": 50, "window_days": 7}

    # Target webhook
    webhook_url = db.Column(db.String(500), nullable=False)
    webhook_method = db.Column(db.String(10), default='POST')
    webhook_headers = db.Column(db.JSON, default=dict)
    webhook_secret_hash = db.Column(db.String(64))
    # For HMAC signing outbound payloads

    # Payload template
    payload_template = db.Column(db.JSON)
    # Jinja-like template: {"account": "{{account_name}}", "health": "{{health_score}}", ...}

    # Execution config
    enabled = db.Column(db.Boolean, default=True)
    cooldown_minutes = db.Column(db.Integer, default=60)
    # Don't re-fire for same account within cooldown
    max_fires_per_day = db.Column(db.Integer, default=10)
    fire_count_today = db.Column(db.Integer, default=0)
    last_fired_at = db.Column(db.DateTime)
    last_fire_status = db.Column(db.String(20))
    # success, error, cooldown_skipped

    # Scope
    account_filter = db.Column(db.JSON)
    # null = all accounts, or {"account_ids": [1,2,3]} or {"min_arr": 500000}

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        db.Index('idx_playbook_wh_customer', 'customer_id', 'enabled'),
    )

    def to_dict(self):
        return {
            'trigger_id': self.trigger_id,
            'customer_id': self.customer_id,
            'trigger_name': self.trigger_name,
            'trigger_type': self.trigger_type,
            'trigger_condition': self.trigger_condition,
            'webhook_url': self.webhook_url,
            'webhook_method': self.webhook_method,
            'enabled': self.enabled,
            'cooldown_minutes': self.cooldown_minutes,
            'max_fires_per_day': self.max_fires_per_day,
            'last_fired_at': self.last_fired_at.isoformat() if self.last_fired_at else None,
            'last_fire_status': self.last_fire_status,
            'account_filter': self.account_filter,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PlaybookWebhookLog(db.Model):
    """
    Audit trail of outbound webhook fires.
    """
    __tablename__ = 'playbook_webhook_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    trigger_id = db.Column(db.Integer, db.ForeignKey('playbook_webhook_triggers.trigger_id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), index=True)

    # What happened
    fire_reason = db.Column(db.Text)
    # "Health score dropped from 62 to 44 for K2 Hyperscale"
    payload_sent = db.Column(db.JSON)
    response_status = db.Column(db.Integer)
    response_body = db.Column(db.Text)
    duration_ms = db.Column(db.Integer)

    # Status
    status = db.Column(db.String(20), nullable=False)
    # success, error, timeout, skipped_cooldown
    error_message = db.Column(db.Text)

    fired_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (
        db.Index('idx_pbwh_log_trigger_time', 'trigger_id', 'fired_at'),
    )

    def to_dict(self):
        return {
            'log_id': self.log_id,
            'trigger_id': self.trigger_id,
            'customer_id': self.customer_id,
            'account_id': self.account_id,
            'fire_reason': self.fire_reason,
            'response_status': self.response_status,
            'duration_ms': self.duration_ms,
            'status': self.status,
            'error_message': self.error_message,
            'fired_at': self.fired_at.isoformat() if self.fired_at else None,
        }


# ============================================================
# Default field mappings for common connectors
# ============================================================

DEFAULT_FIELD_MAPPINGS = {
    'sfdc': {
        'Account': {
            'Name': 'account_name',
            'AnnualRevenue': 'revenue',
            'Industry': 'industry',
            'BillingCountry': 'region',
            'Id': 'external_account_id',
            'AccountStatus__c': 'account_status',
            'Type': 'profile_metadata.account_type',
        },
        'Opportunity': {
            'Name': 'title',
            'Amount': 'revenue_impact',
            'StageName': 'node_subtype',
            'CloseDate': 'event_date',
            'Type': 'properties.opp_type',
        },
        'Case': {
            'Subject': 'title',
            'Priority': 'properties.priority',
            'Status': 'properties.status',
            'CreatedDate': 'event_date',
            'Description': 'properties.description',
        },
    },
    'hubspot': {
        'companies': {
            'name': 'account_name',
            'annualrevenue': 'revenue',
            'industry': 'industry',
            'country': 'region',
            'hs_object_id': 'external_account_id',
        },
        'deals': {
            'dealname': 'title',
            'amount': 'revenue_impact',
            'dealstage': 'node_subtype',
            'closedate': 'event_date',
        },
        'tickets': {
            'subject': 'title',
            'hs_ticket_priority': 'properties.priority',
            'hs_pipeline_stage': 'properties.status',
            'createdate': 'event_date',
            'content': 'properties.description',
        },
    },
    'zendesk': {
        'tickets': {
            'subject': 'title',
            'priority': 'properties.priority',
            'status': 'properties.status',
            'created_at': 'event_date',
            'description': 'properties.description',
            'satisfaction_rating.score': 'properties.csat_score',
            'tags': 'properties.tags',
        },
        'users': {
            'name': 'properties.contact_name',
            'email': 'properties.contact_email',
            'role': 'properties.role',
            'organization_id': 'external_account_id',
        },
    },
}

# Connector type metadata for UI
CONNECTOR_TYPES = {
    'sfdc': {
        'label': 'Salesforce',
        'icon': 'cloud',
        'color': '#00A1E0',
        'auth_types': ['oauth2'],
        'entities': ['Account', 'Opportunity', 'Case', 'Contact'],
        'docs_url': 'https://developer.salesforce.com/docs',
    },
    'hubspot': {
        'label': 'HubSpot',
        'icon': 'hub',
        'color': '#FF7A59',
        'auth_types': ['oauth2', 'api_key'],
        'entities': ['companies', 'deals', 'tickets', 'contacts'],
        'docs_url': 'https://developers.hubspot.com',
    },
    'zendesk': {
        'label': 'Zendesk',
        'icon': 'headset',
        'color': '#03363D',
        'auth_types': ['oauth2', 'api_key'],
        'entities': ['tickets', 'users', 'organizations'],
        'docs_url': 'https://developer.zendesk.com',
    },
    'n8n': {
        'label': 'n8n Workflow',
        'icon': 'workflow',
        'color': '#EA4B71',
        'auth_types': ['webhook_secret'],
        'entities': ['custom'],
        'docs_url': 'https://docs.n8n.io',
    },
    'csv_upload': {
        'label': 'CSV Upload',
        'icon': 'upload',
        'color': '#6B7280',
        'auth_types': ['none'],
        'entities': ['accounts', 'kpi_measurements', 'signals'],
        'docs_url': None,
    },
    'custom_webhook': {
        'label': 'Custom Webhook',
        'icon': 'webhook',
        'color': '#8B5CF6',
        'auth_types': ['webhook_secret', 'api_key'],
        'entities': ['custom'],
        'docs_url': None,
    },
}
