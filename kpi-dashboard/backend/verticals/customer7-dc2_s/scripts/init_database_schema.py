#!/usr/bin/env python3
"""
DC2_S Database Schema Initialization
====================================

Creates the dc2s_* tables for the DC2_S vertical (Customer 7).

Tables created:
- dc2s_journey_weeks: Weekly journey snapshots
- dc2s_journey_events: Qualitative signals (emails, tickets, meetings)
- dc2s_milestones: Training labels (outcomes)
- dc2s_predictions: Signal Analyst predictions
- dc2s_actions: CSM actions taken

SAFETY: Only creates new tables. Does NOT modify existing SaaS tables.

Usage:
    python3 init_database_schema.py
    python3 init_database_schema.py --dry-run
"""

import os
import sys
import argparse
import psycopg2
from psycopg2 import sql


# Schema definitions
SCHEMAS = {
    'dc2s_journey_weeks': """
        CREATE TABLE IF NOT EXISTS dc2s_journey_weeks (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL DEFAULT 9,
            week_number INTEGER NOT NULL,
            week_start_date DATE,
            week_end_date DATE,
            
            -- Raw KPIs with units (JSON: {"mtbf": [8500, "hours"], ...})
            raw_kpis JSONB,
            
            -- Normalized KPIs (0-100 scores)
            normalized_kpis JSONB,
            
            -- Health scores per pillar
            health_score DECIMAL(5,2),
            p1_deployment_score DECIMAL(5,2),
            p2_stability_score DECIMAL(5,2),
            p3_performance_score DECIMAL(5,2),
            p4_channel_score DECIMAL(5,2),
            p5_expansion_score DECIMAL(5,2),
            
            -- Coverage tracking
            coverage_pct DECIMAL(5,2),
            data_quality DECIMAL(5,3),
            missing_kpis JSONB,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(account_id, week_number)
        )
    """,
    
    'dc2s_journey_events': """
        CREATE TABLE IF NOT EXISTS dc2s_journey_events (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL DEFAULT 9,
            week_number INTEGER,
            
            -- Event details
            event_type VARCHAR(50) NOT NULL,
            event_date DATE,
            event_timestamp TIMESTAMP,
            
            -- Content
            subject VARCHAR(500),
            description TEXT,
            sentiment DECIMAL(3,2),
            sentiment_label VARCHAR(20),
            
            -- Participants
            participants JSONB,
            from_email VARCHAR(255),
            to_emails JSONB,
            
            -- Classification
            category VARCHAR(50),
            priority VARCHAR(20),
            is_escalation BOOLEAN DEFAULT FALSE,
            
            -- Metadata
            source VARCHAR(50),
            external_id VARCHAR(255),
            raw_data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Index for fast lookups
            CONSTRAINT dc2s_events_account_week_idx UNIQUE (account_id, week_number, event_type, event_timestamp)
        )
    """,
    
    'dc2s_milestones': """
        CREATE TABLE IF NOT EXISTS dc2s_milestones (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL DEFAULT 9,
            week_number INTEGER NOT NULL,
            
            -- Milestone/Outcome
            milestone_type VARCHAR(50) NOT NULL,
            outcome VARCHAR(50),
            outcome_label VARCHAR(100),
            
            -- Context
            description TEXT,
            trigger_event TEXT,
            
            -- For training
            is_training_label BOOLEAN DEFAULT TRUE,
            confidence DECIMAL(3,2),
            
            -- Metadata
            milestone_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(account_id, week_number, milestone_type)
        )
    """,
    
    'dc2s_predictions': """
        CREATE TABLE IF NOT EXISTS dc2s_predictions (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL DEFAULT 9,
            week_number INTEGER NOT NULL,
            
            -- Prediction
            predicted_outcome VARCHAR(50) NOT NULL,
            confidence DECIMAL(3,2),
            
            -- Model info
            model_version VARCHAR(50),
            model_type VARCHAR(50),
            
            -- Reasoning (from LLM)
            reasoning JSONB,
            signal_interpretation TEXT,
            contextual_analysis TEXT,
            pattern_recognition TEXT,
            
            -- Recommended actions
            recommended_playbook VARCHAR(100),
            recommended_actions JSONB,
            
            -- Actual outcome (for accuracy tracking)
            actual_outcome VARCHAR(50),
            was_correct BOOLEAN,
            
            -- Metadata
            prediction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            llm_cost DECIMAL(10,6),
            
            UNIQUE(account_id, week_number, model_version)
        )
    """,
    
    'dc2s_actions': """
        CREATE TABLE IF NOT EXISTS dc2s_actions (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL DEFAULT 9,
            prediction_id INTEGER REFERENCES dc2s_predictions(id),
            
            -- Action details
            action_type VARCHAR(50) NOT NULL,
            action_description TEXT,
            playbook_id VARCHAR(50),
            
            -- Status
            status VARCHAR(20) DEFAULT 'pending',
            assigned_to VARCHAR(255),
            due_date DATE,
            completed_date DATE,
            
            -- Outcome
            outcome TEXT,
            effectiveness_score DECIMAL(3,2),
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
}

# Indexes for performance
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_dc2s_weeks_account ON dc2s_journey_weeks(account_id)",
    "CREATE INDEX IF NOT EXISTS idx_dc2s_weeks_customer ON dc2s_journey_weeks(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_dc2s_events_account ON dc2s_journey_events(account_id)",
    "CREATE INDEX IF NOT EXISTS idx_dc2s_events_week ON dc2s_journey_events(week_number)",
    "CREATE INDEX IF NOT EXISTS idx_dc2s_events_type ON dc2s_journey_events(event_type)",
    "CREATE INDEX IF NOT EXISTS idx_dc2s_milestones_account ON dc2s_milestones(account_id)",
    "CREATE INDEX IF NOT EXISTS idx_dc2s_predictions_account ON dc2s_predictions(account_id)",
    "CREATE INDEX IF NOT EXISTS idx_dc2s_predictions_outcome ON dc2s_predictions(predicted_outcome)",
]


def get_db_connection():
    """Get database connection from environment"""
    db_url = os.environ.get('DATABASE_URL', 
        'postgresql://dcuser:dcpass123@localhost:5432/cs_pulse_datacenter')
    return psycopg2.connect(db_url)


def table_exists(cursor, table_name):
    """Check if table exists"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        )
    """, (table_name,))
    return cursor.fetchone()[0]


def run_schema_init(dry_run=False):
    """Initialize the dc2s_* schema"""
    print("=" * 60)
    print("DC2_S Database Schema Initialization")
    print("=" * 60)
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(f"\nConnected to database")
        
        # Create tables
        print("\n📋 Creating tables...")
        for table_name, schema in SCHEMAS.items():
            exists = table_exists(cursor, table_name)
            
            if exists:
                print(f"  ⏭️  {table_name} already exists")
            else:
                if dry_run:
                    print(f"  🔵 Would create: {table_name}")
                else:
                    cursor.execute(schema)
                    print(f"  ✅ Created: {table_name}")
        
        # Create indexes
        print("\n📋 Creating indexes...")
        for index_sql in INDEXES:
            index_name = index_sql.split("INDEX IF NOT EXISTS ")[1].split(" ON")[0]
            if dry_run:
                print(f"  🔵 Would create index: {index_name}")
            else:
                cursor.execute(index_sql)
                print(f"  ✅ Created index: {index_name}")
        
        if not dry_run:
            conn.commit()
            print("\n✅ Schema initialization complete!")
        else:
            print("\n🔵 Dry run complete - no changes made")
        
        # Verify
        print("\n📋 Verification:")
        for table_name in SCHEMAS.keys():
            exists = table_exists(cursor, table_name)
            status = "✅" if exists else "❌"
            print(f"  {status} {table_name}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Initialize DC2_S database schema')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without making changes')
    args = parser.parse_args()
    
    run_schema_init(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
