"""add performance indexes for query optimization

Revision ID: h1c2d3e4f5g6
Revises: g0b1c2d3e4f5
Create Date: 2025-11-04 22:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h1c2d3e4f5g6'
down_revision = 'g0b1c2d3e4f5'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing indexes for performance optimization (Issue #4)"""
    
    print("Creating performance indexes...")
    
    # Accounts table
    try:
        op.create_index('idx_accounts_customer_id', 'accounts', ['customer_id'])
        print("  ✅ idx_accounts_customer_id")
    except:
        print("  ⏭  idx_accounts_customer_id already exists")
    
    # KPIs table  
    try:
        op.create_index('idx_kpis_upload_id', 'kpis', ['upload_id'])
        print("  ✅ idx_kpis_upload_id")
    except:
        print("  ⏭  idx_kpis_upload_id already exists")
    
    try:
        op.create_index('idx_kpis_account_id', 'kpis', ['account_id'])
        print("  ✅ idx_kpis_account_id")
    except:
        print("  ⏭  idx_kpis_account_id already exists")
    
    # KPI Uploads table
    try:
        op.create_index('idx_kpi_uploads_customer_id', 'kpi_uploads', ['customer_id'])
        print("  ✅ idx_kpi_uploads_customer_id")
    except:
        print("  ⏭  idx_kpi_uploads_customer_id already exists")
    
    try:
        op.create_index('idx_kpi_uploads_account_id', 'kpi_uploads', ['account_id'])
        print("  ✅ idx_kpi_uploads_account_id")
    except:
        print("  ⏭  idx_kpi_uploads_account_id already exists")
    
    # KPI Time Series table - Composite index for common queries
    try:
        op.create_index('idx_kpi_time_series_composite', 'kpi_time_series',
                        ['customer_id', 'account_id', 'year', 'month'])
        print("  ✅ idx_kpi_time_series_composite")
    except:
        print("  ⏭  idx_kpi_time_series_composite already exists")
    
    try:
        op.create_index('idx_kpi_time_series_kpi_id', 'kpi_time_series', ['kpi_id'])
        print("  ✅ idx_kpi_time_series_kpi_id")
    except:
        print("  ⏭  idx_kpi_time_series_kpi_id already exists")
    
    # Health Trends table
    try:
        op.create_index('idx_health_trends_customer_id', 'health_trends', ['customer_id'])
        print("  ✅ idx_health_trends_customer_id")
    except:
        print("  ⏭  idx_health_trends_customer_id already exists")
    
    try:
        op.create_index('idx_health_trends_account_id', 'health_trends', ['account_id'])
        print("  ✅ idx_health_trends_account_id")
    except:
        print("  ⏭  idx_health_trends_account_id already exists")
    
    # Playbook Executions table
    try:
        op.create_index('idx_playbook_exec_customer_id', 'playbook_executions', ['customer_id'])
        print("  ✅ idx_playbook_exec_customer_id")
    except:
        print("  ⏭  idx_playbook_exec_customer_id already exists")
    
    try:
        op.create_index('idx_playbook_exec_account_id', 'playbook_executions', ['account_id'])
        print("  ✅ idx_playbook_exec_account_id")
    except:
        print("  ⏭  idx_playbook_exec_account_id already exists")
    
    try:
        op.create_index('idx_playbook_exec_execution_id', 'playbook_executions', ['execution_id'])
        print("  ✅ idx_playbook_exec_execution_id")
    except:
        print("  ⏭  idx_playbook_exec_execution_id already exists")
    
    # Users table
    try:
        op.create_index('idx_users_customer_id', 'users', ['customer_id'])
        print("  ✅ idx_users_customer_id")
    except:
        print("  ⏭  idx_users_customer_id already exists")
    
    try:
        op.create_index('idx_users_email', 'users', ['email'])
        print("  ✅ idx_users_email")
    except:
        print("  ⏭  idx_users_email already exists")
    
    print("✅ Performance indexes migration complete")


def downgrade():
    """Remove performance indexes"""
    op.drop_index('idx_accounts_customer_id', 'accounts')
    op.drop_index('idx_kpis_upload_id', 'kpis')
    op.drop_index('idx_kpis_account_id', 'kpis')
    op.drop_index('idx_kpi_uploads_customer_id', 'kpi_uploads')
    op.drop_index('idx_kpi_uploads_account_id', 'kpi_uploads')
    op.drop_index('idx_kpi_time_series_composite', 'kpi_time_series')
    op.drop_index('idx_kpi_time_series_kpi_id', 'kpi_time_series')
    op.drop_index('idx_health_trends_customer_id', 'health_trends')
    op.drop_index('idx_health_trends_account_id', 'health_trends')
    op.drop_index('idx_playbook_exec_customer_id', 'playbook_executions')
    op.drop_index('idx_playbook_exec_account_id', 'playbook_executions')
    op.drop_index('idx_playbook_exec_execution_id', 'playbook_executions')
    op.drop_index('idx_users_customer_id', 'users')
    op.drop_index('idx_users_email', 'users')
    
    print("⚠️  Performance indexes removed")

