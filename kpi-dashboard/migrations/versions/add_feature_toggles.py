"""Add FeatureToggle model for MCP integration

Revision ID: add_feature_toggles
Revises: 
Create Date: 2025-10-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_feature_toggles'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create feature_toggles table
    op.create_table('feature_toggles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('feature_name', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_id', 'feature_name', name='unique_customer_feature')
    )
    
    # Create indexes
    op.create_index('ix_feature_toggles_customer_id', 'feature_toggles', ['customer_id'], unique=False)
    op.create_index('ix_feature_toggles_feature_name', 'feature_toggles', ['feature_name'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('ix_feature_toggles_feature_name', table_name='feature_toggles')
    op.drop_index('ix_feature_toggles_customer_id', table_name='feature_toggles')
    
    # Drop table
    op.drop_table('feature_toggles')

