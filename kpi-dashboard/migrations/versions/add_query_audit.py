"""Add query audit table for RAG query logging

Revision ID: add_query_audit
Revises: add_feature_toggles
Create Date: 2025-10-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_query_audit'
down_revision = 'add_feature_toggles'
branch_labels = None
depends_on = None

def upgrade():
    # Create query_audits table
    op.create_table(
        'query_audits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('query_type', sa.String(50), server_default='general'),
        
        # Response metadata
        sa.Column('response_text', sa.Text()),
        sa.Column('response_time_ms', sa.Integer()),
        sa.Column('results_count', sa.Integer()),
        
        # Classification
        sa.Column('is_deterministic', sa.Boolean(), default=False),
        sa.Column('cache_hit', sa.Boolean(), default=False),
        
        # Enhancements
        sa.Column('mcp_enhanced', sa.Boolean(), default=False),
        sa.Column('playbook_enhanced', sa.Boolean(), default=False),
        
        # Conversation context
        sa.Column('has_conversation_history', sa.Boolean(), default=False),
        sa.Column('conversation_turn', sa.Integer(), default=1),
        
        # Cost tracking
        sa.Column('estimated_cost', sa.Float(), default=0.0),
        
        # Audit fields
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
    )
    
    # Create indexes for common queries
    op.create_index('idx_query_audits_customer', 'query_audits', ['customer_id'])
    op.create_index('idx_query_audits_created', 'query_audits', ['created_at'])
    op.create_index('idx_query_audits_customer_date', 'query_audits', ['customer_id', 'created_at'])

def downgrade():
    op.drop_index('idx_query_audits_customer_date', table_name='query_audits')
    op.drop_index('idx_query_audits_created', table_name='query_audits')
    op.drop_index('idx_query_audits_customer', table_name='query_audits')
    op.drop_table('query_audits')

