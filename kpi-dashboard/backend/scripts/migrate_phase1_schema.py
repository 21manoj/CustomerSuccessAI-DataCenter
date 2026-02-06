#!/usr/bin/env python3
"""
Phase 1 Migration Script
Adds DC2_S configuration fields and score tables
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from models import db, CustomerConfig, KPIScore, PillarScore, HealthScore
from sqlalchemy import inspect, text

def migrate_phase1():
    """Run Phase 1 database migration"""
    with app.app_context():
        print("="*70)
        print("PHASE 1 DATABASE MIGRATION")
        print("="*70)
        print()
        
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        # Step 1: Add columns to customer_configs
        print("Step 1: Extending customer_configs table...")
        if 'customer_configs' in existing_tables:
            existing_columns = {col['name'] for col in inspector.get_columns('customer_configs')}
            
            new_columns = {
                'vertical': "VARCHAR(50) DEFAULT 'saas'",
                'dc2s_pillar_weights': "JSON",
                'dc2s_enabled_kpis': "JSON",
                'dc2s_kpi_overrides': "JSON",
                'dc2s_kpi_weights': "JSON",
                'dc2s_kpi_definitions': "JSON",
                'config_version': "VARCHAR(20) DEFAULT '1.0'",
                'customized_by': "VARCHAR(255)"
            }
            
            for col_name, col_def in new_columns.items():
                if col_name not in existing_columns:
                    try:
                        # PostgreSQL syntax
                        if 'postgresql' in str(db.engine.url):
                            db.session.execute(text(f"ALTER TABLE customer_configs ADD COLUMN {col_name} {col_def}"))
                            print(f"  ✅ Added column: {col_name}")
                        else:
                            # SQLite syntax (simpler)
                            db.session.execute(text(f"ALTER TABLE customer_configs ADD COLUMN {col_name} {col_def.split(' DEFAULT')[0]}"))
                            print(f"  ✅ Added column: {col_name}")
                    except Exception as e:
                        if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                            print(f"  ⚠️  Column {col_name} already exists (skipping)")
                        else:
                            print(f"  ❌ Error adding {col_name}: {e}")
                            raise
                else:
                    print(f"  ✅ Column {col_name} already exists")
            
            db.session.commit()
            print("  ✅ customer_configs table extended")
        else:
            print("  ❌ customer_configs table not found!")
            return False
        
        print()
        
        # Step 2: Create score tables
        print("Step 2: Creating score tables...")
        
        # Create tables using SQLAlchemy
        try:
            KPIScore.__table__.create(db.engine, checkfirst=True)
            print("  ✅ kpi_scores table created/verified")
        except Exception as e:
            if 'already exists' in str(e).lower():
                print("  ⚠️  kpi_scores table already exists")
            else:
                print(f"  ❌ Error creating kpi_scores: {e}")
                raise
        
        try:
            PillarScore.__table__.create(db.engine, checkfirst=True)
            print("  ✅ pillar_scores table created/verified")
        except Exception as e:
            if 'already exists' in str(e).lower():
                print("  ⚠️  pillar_scores table already exists")
            else:
                print(f"  ❌ Error creating pillar_scores: {e}")
                raise
        
        try:
            HealthScore.__table__.create(db.engine, checkfirst=True)
            print("  ✅ health_scores table created/verified")
        except Exception as e:
            if 'already exists' in str(e).lower():
                print("  ⚠️  health_scores table already exists")
            else:
                print(f"  ❌ Error creating health_scores: {e}")
                raise
        
        db.session.commit()
        
        print()
        print("="*70)
        print("✅ PHASE 1 MIGRATION COMPLETE!")
        print("="*70)
        print()
        
        # Verify
        print("Verification:")
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        score_tables = ['kpi_scores', 'pillar_scores', 'health_scores']
        for table in score_tables:
            if table in tables:
                print(f"  ✅ {table} exists")
            else:
                print(f"  ❌ {table} missing!")
        
        if 'customer_configs' in tables:
            columns = {col['name'] for col in inspector.get_columns('customer_configs')}
            dc2s_fields = ['vertical', 'dc2s_pillar_weights', 'dc2s_enabled_kpis', 'dc2s_kpi_overrides', 
                          'dc2s_kpi_weights', 'dc2s_kpi_definitions', 'config_version', 'customized_by']
            print()
            print("CustomerConfig DC2_S fields:")
            for field in dc2s_fields:
                if field in columns:
                    print(f"  ✅ {field}")
                else:
                    print(f"  ❌ {field} missing!")
        
        return True

if __name__ == '__main__':
    try:
        success = migrate_phase1()
        if success:
            print()
            print("✅ Migration successful! Ready for Phase 1 testing.")
        else:
            print()
            print("❌ Migration failed. Check errors above.")
            sys.exit(1)
    except Exception as e:
        print()
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
