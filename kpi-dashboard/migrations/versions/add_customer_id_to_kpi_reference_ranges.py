"""add customer_id to kpi_reference_ranges for SaaS isolation

Revision ID: f9a1c2d3e4b5
Revises: ef4732fc8211
Create Date: 2025-11-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f9a1c2d3e4b5'
down_revision = 'ef4732fc8211'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add customer_id to kpi_reference_ranges table for multi-tenant isolation.
    
    Strategy:
    - NULL customer_id = System default templates (global)
    - Non-NULL customer_id = Customer-specific overrides
    - API uses fallback pattern: check customer-specific first, then fall back to NULL
    """
    
    # Add customer_id column (nullable - allows NULL for system defaults)
    op.add_column('kpi_reference_ranges', 
                  sa.Column('customer_id', sa.Integer(), 
                           sa.ForeignKey('customers.customer_id', ondelete='CASCADE'), 
                           nullable=True))
    
    # Drop the existing unique constraint on kpi_name alone
    # This constraint name may vary - if this fails, check your DB schema
    try:
        op.drop_constraint('kpi_reference_ranges_kpi_name_key', 'kpi_reference_ranges', type_='unique')
    except Exception:
        # Try alternative constraint name (SQLite vs PostgreSQL)
        try:
            op.drop_constraint('uq_kpi_reference_ranges_kpi_name', 'kpi_reference_ranges', type_='unique')
        except Exception:
            print("Note: Could not drop unique constraint - it may not exist or have a different name")
    
    # Add composite unique constraint: (customer_id, kpi_name)
    # This allows same kpi_name for different customers
    op.create_unique_constraint('uq_customer_kpi_name', 'kpi_reference_ranges',
                               ['customer_id', 'kpi_name'])
    
    # Add index for fast lookups by (customer_id, kpi_name)
    op.create_index('idx_ref_range_customer_kpi', 'kpi_reference_ranges',
                   ['customer_id', 'kpi_name'])
    
    # Existing ranges automatically have customer_id = NULL (system defaults)
    # No data migration needed - they serve as templates for all customers
    print("✅ Migration complete: Existing ranges are now system defaults (customer_id = NULL)")


def downgrade():
    """
    Rollback: Remove customer_id and restore original schema.
    
    WARNING: This will delete all customer-specific overrides!
    """
    
    # Drop the index
    op.drop_index('idx_ref_range_customer_kpi', 'kpi_reference_ranges')
    
    # Drop the composite unique constraint
    op.drop_constraint('uq_customer_kpi_name', 'kpi_reference_ranges', type_='unique')
    
    # Re-create the original unique constraint on kpi_name
    op.create_unique_constraint('kpi_reference_ranges_kpi_name_key', 
                               'kpi_reference_ranges', ['kpi_name'])
    
    # Drop customer_id column (this will delete customer-specific overrides!)
    op.drop_column('kpi_reference_ranges', 'customer_id')
    
    print("⚠️ Rollback complete: Customer-specific overrides have been removed")

