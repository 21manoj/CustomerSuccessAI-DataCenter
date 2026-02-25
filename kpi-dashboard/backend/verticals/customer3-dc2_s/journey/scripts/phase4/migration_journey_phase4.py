"""
Alembic Migration: Add Journey Training Tables

Revision ID: journey_phase4_001
Revises: (your_latest_revision)
Create Date: 2026-01-07

Description:
Adds journey training tables for Signal Analyst testing.
Safe to run - creates new tables only, doesn't modify production.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'journey_phase4_001'
down_revision = None  # Set this to your latest migration revision
branch_labels = None
depends_on = None


def upgrade():
    """Create journey training tables"""
    
    # 1. journey_accounts table
    op.create_table(
        'journey_accounts',
        sa.Column('journey_account_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('account_name', sa.String(length=200), nullable=False),
        sa.Column('external_account_id', sa.String(length=50), nullable=False),
        sa.Column('pattern_type', sa.String(length=50), nullable=False),
        sa.Column('pattern_description', sa.Text(), nullable=True),
        sa.Column('arr', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('journey_start_date', sa.DateTime(), nullable=False),
        sa.Column('journey_end_date', sa.DateTime(), nullable=True),
        sa.Column('total_weeks', sa.Integer(), nullable=True),
        sa.Column('total_events', sa.Integer(), nullable=True),
        sa.Column('starting_health', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('ending_health', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('health_change', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('final_outcome', sa.String(length=50), nullable=True),
        sa.Column('outcome_arr_impact', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_csm_investment', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('journey_account_id'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.account_id'], ondelete='SET NULL'),
        sa.UniqueConstraint('external_account_id', name='uq_journey_external_account')
    )
    
    # Indexes for journey_accounts
    op.create_index('idx_journey_account_pattern', 'journey_accounts', ['pattern_type'])
    op.create_index('idx_journey_account_external', 'journey_accounts', ['external_account_id'])
    op.create_index('idx_journey_account_prod_ref', 'journey_accounts', ['account_id'])
    
    # 2. journey_events table
    op.create_table(
        'journey_events',
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('journey_account_id', sa.Integer(), nullable=False),
        sa.Column('week_number', sa.Integer(), nullable=False),
        sa.Column('event_date', sa.DateTime(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('phase', sa.String(length=50), nullable=False),
        sa.Column('sentiment_level', sa.String(length=20), nullable=True),
        sa.Column('sentiment_value', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('health_score_before', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('health_score_after', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('health_impact', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('csm_action_type', sa.String(length=50), nullable=True),
        sa.Column('csm_response_time_hours', sa.Integer(), nullable=True),
        sa.Column('csm_action_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('csm_action_description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('event_id'),
        sa.ForeignKeyConstraint(['journey_account_id'], ['journey_accounts.journey_account_id'], ondelete='CASCADE')
    )
    
    # Indexes for journey_events
    op.create_index('idx_journey_event_account', 'journey_events', ['journey_account_id'])
    op.create_index('idx_journey_event_account_week', 'journey_events', ['journey_account_id', 'week_number'])
    op.create_index('idx_journey_event_account_date', 'journey_events', ['journey_account_id', 'event_date'])
    op.create_index('idx_journey_event_phase', 'journey_events', ['phase'])
    op.create_index('idx_journey_event_type', 'journey_events', ['event_type'])
    op.create_index('idx_journey_event_sentiment', 'journey_events', ['sentiment_level'])
    
    # 3. journey_kpis table
    op.create_table(
        'journey_kpis',
        sa.Column('journey_kpi_id', sa.Integer(), nullable=False),
        sa.Column('journey_account_id', sa.Integer(), nullable=False),
        sa.Column('week_number', sa.Integer(), nullable=False),
        sa.Column('measurement_date', sa.DateTime(), nullable=False),
        sa.Column('kpi_code', sa.String(length=10), nullable=False),
        sa.Column('kpi_name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('good_range_min', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('good_range_max', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('bad_range_min', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('bad_range_max', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('health_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('phase', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('journey_kpi_id'),
        sa.ForeignKeyConstraint(['journey_account_id'], ['journey_accounts.journey_account_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('journey_account_id', 'week_number', 'kpi_code', name='uq_journey_kpi')
    )
    
    # Indexes for journey_kpis
    op.create_index('idx_journey_kpi_account', 'journey_kpis', ['journey_account_id'])
    op.create_index('idx_journey_kpi_account_week', 'journey_kpis', ['journey_account_id', 'week_number'])
    op.create_index('idx_journey_kpi_account_code', 'journey_kpis', ['journey_account_id', 'kpi_code'])
    op.create_index('idx_journey_kpi_category', 'journey_kpis', ['category'])
    op.create_index('idx_journey_kpi_code', 'journey_kpis', ['kpi_code'])
    
    # 4. journey_health table
    op.create_table(
        'journey_health',
        sa.Column('health_id', sa.Integer(), nullable=False),
        sa.Column('journey_account_id', sa.Integer(), nullable=False),
        sa.Column('week_number', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.DateTime(), nullable=False),
        sa.Column('overall_health_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('health_status', sa.String(length=20), nullable=True),
        sa.Column('phase', sa.String(length=50), nullable=False),
        sa.Column('p1_deployment_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('p2_operational_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('p3_performance_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('p4_channel_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('p5_expansion_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('events_this_week', sa.Integer(), server_default='0'),
        sa.Column('csm_actions_this_week', sa.Integer(), server_default='0'),
        sa.Column('total_csm_cost_this_week', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('health_id'),
        sa.ForeignKeyConstraint(['journey_account_id'], ['journey_accounts.journey_account_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('journey_account_id', 'week_number', name='uq_journey_health')
    )
    
    # Indexes for journey_health
    op.create_index('idx_journey_health_account', 'journey_health', ['journey_account_id'])
    op.create_index('idx_journey_health_account_week', 'journey_health', ['journey_account_id', 'week_number'])
    op.create_index('idx_journey_health_account_date', 'journey_health', ['journey_account_id', 'snapshot_date'])
    op.create_index('idx_journey_health_phase', 'journey_health', ['phase'])
    
    # 5. journey_milestones table (Training labels)
    op.create_table(
        'journey_milestones',
        sa.Column('milestone_id', sa.Integer(), nullable=False),
        sa.Column('journey_account_id', sa.Integer(), nullable=False),
        sa.Column('week_number', sa.Integer(), nullable=False),
        sa.Column('milestone_date', sa.DateTime(), nullable=False),
        sa.Column('milestone_type', sa.String(length=50), nullable=False),
        sa.Column('milestone_outcome', sa.String(length=50), nullable=True),
        sa.Column('leading_indicators', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('arr_impact', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('confidence_at_time', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('primary_drivers', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('signal_breakdown', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('milestone_id'),
        sa.ForeignKeyConstraint(['journey_account_id'], ['journey_accounts.journey_account_id'], ondelete='CASCADE')
    )
    
    # Indexes for journey_milestones
    op.create_index('idx_journey_milestone_account', 'journey_milestones', ['journey_account_id'])
    op.create_index('idx_journey_milestone_type', 'journey_milestones', ['milestone_type'])
    op.create_index('idx_journey_milestone_account_week', 'journey_milestones', ['journey_account_id', 'week_number'])
    op.create_index('idx_journey_milestone_date', 'journey_milestones', ['milestone_date'])
    
    # 6. signal_predictions table (Feedback loop)
    op.create_table(
        'signal_predictions',
        sa.Column('prediction_id', sa.Integer(), nullable=False),
        sa.Column('journey_account_id', sa.Integer(), nullable=False),
        sa.Column('prediction_week', sa.Integer(), nullable=False),
        sa.Column('prediction_date', sa.DateTime(), nullable=False),
        sa.Column('predicted_outcome', sa.String(length=50), nullable=False),
        sa.Column('churn_probability', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('expansion_probability', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('predicted_health_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('time_to_event_prediction', sa.String(length=50), nullable=True),
        sa.Column('actual_outcome', sa.String(length=50), nullable=True),
        sa.Column('actual_event_week', sa.Integer(), nullable=True),
        sa.Column('actual_arr_impact', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('prediction_correct', sa.Boolean(), nullable=True),
        sa.Column('probability_error', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('timing_error_days', sa.Integer(), nullable=True),
        sa.Column('confidence_level', sa.String(length=20), nullable=True),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('model_used', sa.String(length=50), nullable=True),
        sa.Column('model_version', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('outcome_confirmed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('prediction_id'),
        sa.ForeignKeyConstraint(['journey_account_id'], ['journey_accounts.journey_account_id'], ondelete='CASCADE')
    )
    
    # Indexes for signal_predictions
    op.create_index('idx_signal_pred_account', 'signal_predictions', ['journey_account_id'])
    op.create_index('idx_signal_pred_week', 'signal_predictions', ['prediction_week'])
    op.create_index('idx_signal_pred_outcome', 'signal_predictions', ['predicted_outcome'])
    op.create_index('idx_signal_pred_correct', 'signal_predictions', ['prediction_correct'])
    
    # 7. prediction_explanations table (Explainability)
    op.create_table(
        'prediction_explanations',
        sa.Column('explanation_id', sa.Integer(), nullable=False),
        sa.Column('prediction_id', sa.Integer(), nullable=False),
        sa.Column('reasoning_text', sa.Text(), nullable=False),
        sa.Column('key_insights', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('quantitative_signals_used', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('qualitative_signals_used', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('historical_patterns_used', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('top_risk_drivers', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('top_growth_drivers', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('signal_weights', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('decision_tree', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_breakdown', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('what_if_scenarios', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('explanation_id'),
        sa.ForeignKeyConstraint(['prediction_id'], ['signal_predictions.prediction_id'], ondelete='CASCADE')
    )
    
    # Indexes for prediction_explanations
    op.create_index('idx_pred_explain_prediction', 'prediction_explanations', ['prediction_id'])
    
    # 8. journey_metadata table
    op.create_table(
        'journey_metadata',
        sa.Column('metadata_id', sa.Integer(), nullable=False),
        sa.Column('generation_phase', sa.String(length=20), nullable=False),
        sa.Column('generation_date', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('generator_version', sa.String(length=20), nullable=True),
        sa.Column('accounts_generated', sa.Integer(), nullable=True),
        sa.Column('events_generated', sa.Integer(), nullable=True),
        sa.Column('kpis_generated', sa.Integer(), nullable=True),
        sa.Column('parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('patterns', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('source_files', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('metadata_id')
    )
    
    print("✅ Journey training tables created successfully!")


def downgrade():
    """Drop journey training tables (in reverse order due to foreign keys)"""
    op.drop_table('journey_metadata')
    op.drop_table('prediction_explanations')
    op.drop_table('signal_predictions')
    op.drop_table('journey_milestones')
    op.drop_table('journey_health')
    op.drop_table('journey_kpis')
    op.drop_table('journey_events')
    op.drop_table('journey_accounts')
    
    print("✅ Journey training tables dropped!")


if __name__ == "__main__":
    """Run migration directly (not through Alembic)"""
    from sqlalchemy import create_engine
    import os
    
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        print("Usage: export DATABASE_URL='postgresql://...' && python3 migration_journey_phase4.py")
        exit(1)
    
    print("="*70)
    print("CREATING JOURNEY TRAINING TABLES")
    print("="*70)
    print(f"Database: {db_url.split('@')[1] if '@' in db_url else 'hidden'}")
    print()
    
    # Create engine and connection
    engine = create_engine(db_url)
    
    # Create mock Alembic operation context
    from alembic.operations import Operations
    from alembic.migration import MigrationConte
    
    conn = engine.connect()
    ctx = MigrationContext.configure(conn)
    op = Operations(ctx)
    
    # Store op in global namespace so upgrade() can use it
    import builtins
    builtins.op = op
    
    try:
        # Run upgrade
        upgrade()
        conn.commit()
        print()
        print("="*70)
        print("✅ ALL TABLES CREATED SUCCESSFULLY!")
        print("="*70)
    except Exception as e:
        conn.rollck()
        print(f"❌ ERROR: {e}")
        exit(1)
    finally:
        conn.close()
