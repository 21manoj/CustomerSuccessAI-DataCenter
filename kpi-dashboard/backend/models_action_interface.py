"""
Action Interface Models — Phase 1

New tables that support the Abstract Action Interface and LLM Validation Gate:
  - CustomerActionBinding   — per-customer action→provider routing
  - IntegrationCredential   — encrypted credentials vault
  - PlaybookStepLog         — per-step audit trail within a playbook execution
  - CRMFieldMapping         — per-customer CRM field mapping for variable interpolation
  - CustomerContact         — contact role mapping for playbook variables

These *complement* (not replace) CustomerWorkflowConfig, PlaybookExecution, and
PlaybookTrigger defined in models.py.
"""

from extensions import db
from datetime import datetime


# ============================================================
# CustomerActionBinding
# ============================================================

class CustomerActionBinding(db.Model):
    """Maps an abstract action name to a concrete provider for a customer."""
    __tablename__ = 'customer_action_bindings'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey('customers.customer_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    action_name = db.Column(db.String(100), nullable=False)  # 'create_task', 'send_alert', …
    provider = db.Column(db.String(50), nullable=False)       # 'jira', 'slack', 'salesforce', 'cs_pulse_internal'
    config = db.Column(db.JSON, nullable=False, default=dict)  # Provider-specific config (project key, channel, etc.)
    auth_credential_id = db.Column(
        db.Integer,
        db.ForeignKey('integration_credentials.id', ondelete='SET NULL'),
        nullable=True,
    )
    fallback = db.Column(db.String(50), nullable=True)  # 'log_only', 'email', null
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        db.UniqueConstraint('customer_id', 'action_name', name='uq_customer_action'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'action_name': self.action_name,
            'provider': self.provider,
            'config': self.config,
            'auth_credential_id': self.auth_credential_id,
            'fallback': self.fallback,
            'enabled': self.enabled,
        }


# ============================================================
# IntegrationCredential
# ============================================================

class IntegrationCredential(db.Model):
    """Encrypted credential vault — one row per provider per customer."""
    __tablename__ = 'integration_credentials'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey('customers.customer_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    provider = db.Column(db.String(50), nullable=False)           # 'jira', 'slack', …
    credential_type = db.Column(db.String(50), nullable=False)    # 'oauth2', 'api_key', 'bot_token', 'smtp_credentials'
    encrypted_data = db.Column(db.LargeBinary, nullable=False)    # Fernet-encrypted JSON blob
    expires_at = db.Column(db.DateTime, nullable=True)
    refresh_token_encrypted = db.Column(db.LargeBinary, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        db.Index('idx_cred_customer_provider', 'customer_id', 'provider'),
    )


# ============================================================
# PlaybookStepLog
# ============================================================

class PlaybookStepLog(db.Model):
    """Audit trail for individual steps within a playbook execution."""
    __tablename__ = 'playbook_step_log'

    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(
        db.String(36),
        db.ForeignKey('playbook_executions.execution_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    step_index = db.Column(db.Integer, nullable=False)
    action_name = db.Column(db.String(100), nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    params_sent = db.Column(db.JSON, nullable=True)
    response_received = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), nullable=False)  # 'success', 'failed', 'skipped', 'pending'
    error_message = db.Column(db.Text, nullable=True)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
    duration_ms = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.Index('idx_step_log_execution', 'execution_id', 'step_index'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'step_index': self.step_index,
            'action_name': self.action_name,
            'provider': self.provider,
            'status': self.status,
            'error_message': self.error_message,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'duration_ms': self.duration_ms,
        }


# ============================================================
# CRMFieldMapping
# ============================================================

class CRMFieldMapping(db.Model):
    """Per-customer mapping of CS Pulse fields to CRM object/field pairs."""
    __tablename__ = 'crm_field_mappings'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey('customers.customer_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    cs_pulse_field = db.Column(db.String(100), nullable=False)   # 'health_score', 'churn_probability', …
    crm_object = db.Column(db.String(50), nullable=False)        # 'Account', 'Opportunity', 'Contact'
    crm_field = db.Column(db.String(100), nullable=False)        # 'Health_Score__c', 'Churn_Risk__c'
    transform = db.Column(db.String(50), nullable=True)          # 'scale_100_to_10', 'boolean_threshold', …
    transform_config = db.Column(db.JSON, nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            'customer_id', 'cs_pulse_field', 'crm_object',
            name='uq_customer_field_object',
        ),
    )


# ============================================================
# CustomerContact
# ============================================================

class CustomerContact(db.Model):
    """Contact role mapping for playbook variable interpolation."""
    __tablename__ = 'customer_contacts'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey('customers.customer_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    account_id = db.Column(
        db.Integer,
        db.ForeignKey('accounts.account_id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    role = db.Column(db.String(50), nullable=False)           # 'champion', 'executive_sponsor', 'technical_lead'
    name = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    crm_contact_id = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (
        db.Index('idx_contact_customer_account', 'customer_id', 'account_id'),
        db.Index('idx_contact_role', 'role'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'account_id': self.account_id,
            'role': self.role,
            'name': self.name,
            'email': self.email,
            'title': self.title,
            'crm_contact_id': self.crm_contact_id,
            'is_active': self.is_active,
        }
