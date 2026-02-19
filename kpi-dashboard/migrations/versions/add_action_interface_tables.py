"""Add action interface tables

Phase 1 migration — creates tables for the Abstract Action Interface:
  - customer_action_bindings
  - integration_credentials
  - playbook_step_log
  - crm_field_mappings
  - customer_contacts

Revision ID: c4e8f1a2b301
Revises: (depends on existing head)
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'c4e8f1a2b301'
down_revision = None  # Will be resolved by alembic
branch_labels = None
depends_on = None


def upgrade():
    # ── integration_credentials (must come first — FK target) ──
    op.create_table(
        'integration_credentials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('customer_id', sa.Integer(),
                  sa.ForeignKey('customers.customer_id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('credential_type', sa.String(50), nullable=False),
        sa.Column('encrypted_data', sa.LargeBinary(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('refresh_token_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_cred_customer_provider',
                     'integration_credentials',
                     ['customer_id', 'provider'])

    # ── customer_action_bindings ──
    op.create_table(
        'customer_action_bindings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('customer_id', sa.Integer(),
                  sa.ForeignKey('customers.customer_id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('action_name', sa.String(100), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('auth_credential_id', sa.Integer(),
                  sa.ForeignKey('integration_credentials.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('fallback', sa.String(50), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('customer_id', 'action_name', name='uq_customer_action'),
    )

    # ── playbook_step_log ──
    op.create_table(
        'playbook_step_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('execution_id', sa.String(36),
                  sa.ForeignKey('playbook_executions.execution_id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('action_name', sa.String(100), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('params_sent', sa.JSON(), nullable=True),
        sa.Column('response_received', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
    )
    op.create_index('idx_step_log_execution',
                     'playbook_step_log',
                     ['execution_id', 'step_index'])

    # ── crm_field_mappings ──
    op.create_table(
        'crm_field_mappings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('customer_id', sa.Integer(),
                  sa.ForeignKey('customers.customer_id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('cs_pulse_field', sa.String(100), nullable=False),
        sa.Column('crm_object', sa.String(50), nullable=False),
        sa.Column('crm_field', sa.String(100), nullable=False),
        sa.Column('transform', sa.String(50), nullable=True),
        sa.Column('transform_config', sa.JSON(), nullable=True),
        sa.UniqueConstraint('customer_id', 'cs_pulse_field', 'crm_object',
                            name='uq_customer_field_object'),
    )

    # ── customer_contacts ──
    op.create_table(
        'customer_contacts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('customer_id', sa.Integer(),
                  sa.ForeignKey('customers.customer_id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('account_id', sa.Integer(),
                  sa.ForeignKey('accounts.account_id', ondelete='SET NULL'),
                  nullable=True, index=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('crm_contact_id', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_contact_customer_account',
                     'customer_contacts',
                     ['customer_id', 'account_id'])
    op.create_index('idx_contact_role',
                     'customer_contacts',
                     ['role'])


def downgrade():
    op.drop_table('customer_contacts')
    op.drop_table('crm_field_mappings')
    op.drop_table('playbook_step_log')
    op.drop_table('customer_action_bindings')
    op.drop_table('integration_credentials')
