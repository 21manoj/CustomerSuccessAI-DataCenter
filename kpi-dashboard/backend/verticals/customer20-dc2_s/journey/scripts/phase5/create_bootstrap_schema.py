#!/usr/bin/env python3
"""
Bootstrap Weights Database Schema
==================================

Creates tables for:
1. bootstrap_weights - Stores 32 KPI weights from Supermicro simulation
2. kpi_mapping - Maps 32 bootstrap KPIs → 35 journey KPIs
3. signal_baseline_results - Stores baseline test results

Usage:
    python3 create_bootstrap_schema.py
"""

import os
import sys
from sqlalchemy import create_engine, text

def create_bootstrap_tables(db_url):
    """Create bootstrap-related tables"""
    
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        print("="*70)
        print("CREATING BOOTSTRAP WEIGHTS SCHEMA")
        print("="*70)
        print()
        
        # Table 1: Bootstrap Weights
        print("📊 Creating bootstrap_weights table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bootstrap_weights (
                weight_id SERIAL PRIMARY KEY,
                pillar_code VARCHAR(50) NOT NULL,
                pillar_name VARCHAR(255) NOT NULL,
                kpi_code VARCHAR(100) NOT NULL,
                kpi_name VARCHAR(255) NOT NULL,
                l2_weight NUMERIC(6,4) NOT NULL,
                l1_weight NUMERIC(6,4) NOT NULL,
                effective_weight NUMERIC(6,4) NOT NULL,
                rank_by_importance INTEGER,
                source VARCHAR(100) DEFAULT 'Supermicro_simulation',
                confidence_level VARCHAR(20) DEFAULT 'high',
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(pillar_code, kpi_code)
            );
            
            CREATE INDEX IF NOT EXISTS idx_bootstrap_pillar ON bootstrap_weights(pillar_code);
            CREATE INDEX IF NOT EXISTS idx_bootstrap_kpi ON bootstrap_weights(kpi_code);
            CREATE INDEX IF NOT EXISTS idx_bootstrap_effective ON bootstrap_weights(effective_weight DESC);
        """))
        print("   ✅ bootstrap_weights table created")
        print()
        
        # Table 2: KPI Mapping
        print("🔗 Creating kpi_mapping table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS kpi_mapping (
                mapping_id SERIAL PRIMARY KEY,
                bootstrap_kpi_code VARCHAR(100) NOT NULL,
                bootstrap_kpi_name VARCHAR(255) NOT NULL,
                journey_kpi_code VARCHAR(10) NOT NULL,
                journey_kpi_name VARCHAR(255) NOT NULL,
                mapping_weight NUMERIC(4,2) DEFAULT 1.0,
                mapping_type VARCHAR(50) NOT NULL,
                confidence NUMERIC(3,2) NOT NULL,
                transformation_rule TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(bootstrap_kpi_code, journey_kpi_code)
            );
            
            CREATE INDEX IF NOT EXISTS idx_mapping_bootstrap ON kpi_mapping(bootstrap_kpi_code);
            CREATE INDEX IF NOT EXISTS idx_mapping_journey ON kpi_mapping(journey_kpi_code);
        """))
        print("   ✅ kpi_mapping table created")
        print()
        
        # Table 3: Signal Baseline Results
        print("📈 Creating signal_baseline_results table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS signal_baseline_results (
                result_id SERIAL PRIMARY KEY,
                journey_account_id INTEGER REFERENCES journey_accounts(journey_account_id),
                test_date TIMESTAMP DEFAULT NOW(),
                prediction_week INTEGER NOT NULL,
                predicted_outcome VARCHAR(50),
                predicted_health_score NUMERIC(5,2),
                predicted_churn_risk NUMERIC(3,2),
                predicted_expansion_prob NUMERIC(3,2),
                actual_outcome VARCHAR(50),
                actual_milestone_type VARCHAR(100),
                actual_milestone_date DATE,
                prediction_correct BOOLEAN,
                health_score_error NUMERIC(5,2),
                outcome_match BOOLEAN,
                confidence_score NUMERIC(3,2),
                pillar_scores JSONB,
                top_signals JSONB,
                test_run_id VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_baseline_account ON signal_baseline_results(journey_account_id);
            CREATE INDEX IF NOT EXISTS idx_baseline_run ON signal_baseline_results(test_run_id);
            CREATE INDEX IF NOT EXISTS idx_baseline_correct ON signal_baseline_results(prediction_correct);
        """))
        print("   ✅ signal_baseline_results table created")
        print()
        
        # Commit changes
        conn.commit()
        
        # Verify tables
        print("🔍 Verifying tables...")
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('bootstrap_weights', 'kpi_mapping', 'signal_baseline_results')
            ORDER BY table_name;
        """))
        
        tables = [row[0] for row in result]
        print(f"   Tables created: {len(tables)}/3")
        for table in tables:
            print(f"      ✅ {table}")
        print()
        
        print("="*70)
        print("✅ BOOTSTRAP SCHEMA CREATED SUCCESSFULLY!")
        print("="*70)
        print()
        print("Next steps:")
        print("  1. Load bootstrap weights: python3 load_bootstrap_weights.py")
        print("  2. Load KPI mapping: python3 load_kpi_mapping.py")
        print("  3. Test Signal Analyst: python3 test_signal_analyst.py")
        print()


if __name__ == "__main__":
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        print()
        print("Usage:")
        print("  export DATABASE_URL='postgresql://user:pass@host:5432/database'")
        print("  python3 create_bootstrap_schema.py")
        sys.exit(1)
    
    try:
        create_bootstrap_tables(db_url)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
