"""Add context graph tables

Creates context_nodes and context_edges tables for the
Context Graph / Revenue Intelligence feature.

Guarded at runtime by FeatureToggle.CONTEXT_GRAPH.

Revision ID: d5f2a3c4e601
Revises: c4e8f1a2b301
Create Date: 2026-03-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'd5f2a3c4e601'
down_revision = 'c4e8f1a2b301'
branch_labels = None
depends_on = None


def upgrade():
    # ── context_nodes (must come first — FK target for edges) ──
    op.create_table(
        'context_nodes',
        sa.Column('node_id', sa.Integer(), primary_key=True),
        sa.Column('customer_id', sa.Integer(),
                  sa.ForeignKey('customers.customer_id'),
                  nullable=False, index=True),
        sa.Column('account_id', sa.Integer(),
                  sa.ForeignKey('accounts.account_id'),
                  nullable=False, index=True),

        # Node classification
        sa.Column('node_type', sa.String(30), nullable=False, index=True),
        sa.Column('node_subtype', sa.String(50), index=True),

        # Storage tier: 1=permanent, 2=decaying, 3=ephemeral
        sa.Column('tier', sa.SmallInteger(), nullable=False, server_default='2'),

        # Core content
        sa.Column('title', sa.String(500)),
        sa.Column('properties', sa.JSON(), nullable=False, server_default='{}'),

        # Revenue impact (CRO/CFO lens)
        sa.Column('revenue_impact', sa.Numeric(15, 2)),
        sa.Column('revenue_impact_type', sa.String(30)),
        sa.Column('confidence', sa.Numeric(3, 2), server_default='1.00'),

        # Source tracking
        sa.Column('source_platform', sa.String(50)),
        sa.Column('source_event_id', sa.String(200)),
        sa.Column('source_ref', sa.String(200)),

        # Temporal
        sa.Column('occurred_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('weight_decay', sa.Numeric(3, 2), server_default='1.00'),

        # Lifecycle
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Composite indexes for graph traversal
    op.create_index('idx_ctx_node_account_type',
                     'context_nodes', ['account_id', 'node_type'])
    op.create_index('idx_ctx_node_customer',
                     'context_nodes', ['customer_id', 'node_type'])
    op.create_index('idx_ctx_node_occurred',
                     'context_nodes', ['account_id', 'occurred_at'])
    op.create_index('idx_ctx_node_tier_expires',
                     'context_nodes', ['tier', 'expires_at'])
    op.create_index('idx_ctx_node_source',
                     'context_nodes', ['source_platform', 'source_event_id'])

    # ── context_edges ──
    op.create_table(
        'context_edges',
        sa.Column('edge_id', sa.Integer(), primary_key=True),
        sa.Column('from_node_id', sa.Integer(),
                  sa.ForeignKey('context_nodes.node_id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('to_node_id', sa.Integer(),
                  sa.ForeignKey('context_nodes.node_id', ondelete='CASCADE'),
                  nullable=False, index=True),

        # Edge classification
        sa.Column('edge_type', sa.String(30), nullable=False, index=True),

        # Weight and confidence
        sa.Column('weight', sa.Numeric(3, 2), nullable=False, server_default='1.00'),
        sa.Column('confidence', sa.Numeric(3, 2), server_default='1.00'),

        # Revenue context on the causal link
        sa.Column('revenue_impact', sa.Numeric(15, 2)),
        sa.Column('revenue_impact_type', sa.String(30)),

        # Edge payload
        sa.Column('properties', sa.JSON(), server_default='{}'),

        # Source tracking
        sa.Column('source_platform', sa.String(50)),
        sa.Column('created_by', sa.String(50)),

        # Temporal
        sa.Column('occurred_at', sa.DateTime()),
        sa.Column('expires_at', sa.DateTime()),

        # Lifecycle
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Composite indexes for graph traversal
    op.create_index('idx_ctx_edge_from',
                     'context_edges', ['from_node_id', 'edge_type'])
    op.create_index('idx_ctx_edge_to',
                     'context_edges', ['to_node_id', 'edge_type'])
    op.create_index('idx_ctx_edge_type',
                     'context_edges', ['edge_type'])
    op.create_index('idx_ctx_edge_pair',
                     'context_edges', ['from_node_id', 'to_node_id', 'edge_type'])


def downgrade():
    op.drop_table('context_edges')
    op.drop_table('context_nodes')
