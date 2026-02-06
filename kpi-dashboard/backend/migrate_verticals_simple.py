#!/usr/bin/env python3
"""
SIMPLIFIED MULTI-VERTICAL MIGRATION
Focus: DC2_S and SaaS verticals only
No PE portfolio layer - that's future work

This migration:
1. Adds vertical columns to users/accounts
2. Creates dc2s_kpis table (separate from existing kpis)
3. Sets up vertical registry
4. Preserves existing kpis table for SaaS

Time: 30-60 minutes
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from sqlalchemy import text

def step1_add_vertical_columns():
    """Add minimal vertical support columns"""
    
    print("=" * 60)
    print("STEP 1: Adding Vertical Columns")
    print("=" * 60)
    print()
    
    try:
        # Users table
        print("Adding columns to 'users' table...")
        db.session.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS vertical VARCHAR(50)'))
        db.session.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50)'))
        db.session.commit()
        print("✅ Added: users.vertical, users.role")
        
        # Accounts table
        print()
        print("Adding columns to 'accounts' table...")
        db.session.execute(text('ALTER TABLE accounts ADD COLUMN IF NOT EXISTS vertical VARCHAR(50)'))
        db.session.commit()
        print("✅ Added: accounts.vertical")
        
        # Indexes
        print()
        print("Creating indexes...")
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_user_vertical ON users(vertical)'))
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_user_role ON users(role)'))
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_account_vertical ON accounts(vertical)'))
        db.session.commit()
        print("✅ Created indexes")
        
        print()
        print("✅ Step 1 Complete")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.session.rollback()
        return False

def step2_create_dc2s_kpi_table():
    """Create DC2_S-specific KPI table"""
    
    print()
    print("=" * 60)
    print("STEP 2: Creating DC2_S KPI Table")
    print("=" * 60)
    print()
    
    try:
        print("Creating 'dc2s_kpis' table...")
        
        create_sql = """
        CREATE TABLE IF NOT EXISTS dc2s_kpis (
            kpi_id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
            kpi_code VARCHAR(50) NOT NULL,
            value NUMERIC(10, 2) NOT NULL,
            target NUMERIC(10, 2),
            pillar VARCHAR(10),
            weight NUMERIC(5, 4),
            status VARCHAR(20),
            measured_at TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW(),
            
            CONSTRAINT unique_dc2s_kpi UNIQUE(account_id, kpi_code, measured_at)
        )
        """
        
        db.session.execute(text(create_sql))
        db.session.commit()
        print("✅ Created 'dc2s_kpis' table")
        
        # Indexes
        print()
        print("Creating indexes...")
        index_sqls = [
            'CREATE INDEX IF NOT EXISTS idx_dc2s_account ON dc2s_kpis(account_id)',
            'CREATE INDEX IF NOT EXISTS idx_dc2s_code ON dc2s_kpis(kpi_code)',
            'CREATE INDEX IF NOT EXISTS idx_dc2s_pillar ON dc2s_kpis(pillar)',
            'CREATE INDEX IF NOT EXISTS idx_dc2s_account_code ON dc2s_kpis(account_id, kpi_code)'
        ]
        
        for sql in index_sqls:
            db.session.execute(text(sql))
        
        db.session.commit()
        print("✅ Created indexes")
        
        print()
        print("✅ Step 2 Complete")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.session.rollback()
        return False

def step3_tag_existing_kpis_as_saas():
    """Mark existing KPIs as SaaS vertical (optional)"""
    
    print()
    print("=" * 60)
    print("STEP 3: Handle Existing KPIs")
    print("=" * 60)
    print()
    print("Your existing 'kpis' table contains data.")
    print("Options:")
    print("  1. Keep as-is (we'll use dc2s_kpis separately)")
    print("  2. Add vertical column to kpis table (tag as 'saas')")
    print("  3. Skip (decide later)")
    print()
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice == '1':
        print("✅ Keeping 'kpis' table unchanged")
        print("   DC2_S will use separate 'dc2s_kpis' table")
        print("   SaaS will continue using 'kpis' table")
        return True
        
    elif choice == '2':
        try:
            print()
            print("Adding 'vertical' column to kpis table...")
            db.session.execute(text('ALTER TABLE kpis ADD COLUMN IF NOT EXISTS vertical VARCHAR(50) DEFAULT \'saas\''))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_kpi_vertical ON kpis(vertical)'))
            db.session.commit()
            print("✅ Added vertical column, defaulted existing rows to 'saas'")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()
            return False
    
    else:  # choice == '3' or anything else
        print("⏭️  Skipped - you can decide later")
        return True

def step4_verify():
    """Verify migration completed successfully"""
    
    print()
    print("=" * 60)
    print("STEP 4: Verification")
    print("=" * 60)
    print()
    
    try:
        # Check users columns
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('vertical', 'role')
        """))
        user_cols = [row[0] for row in result]
        
        print("✓ Users table:")
        print(f"  vertical: {'✅' if 'vertical' in user_cols else '❌'}")
        print(f"  role: {'✅' if 'role' in user_cols else '❌'}")
        
        # Check accounts columns
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'accounts' 
            AND column_name = 'vertical'
        """))
        account_cols = [row[0] for row in result]
        
        print()
        print("✓ Accounts table:")
        print(f"  vertical: {'✅' if 'vertical' in account_cols else '❌'}")
        
        # Check dc2s_kpis exists
        result = db.session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'dc2s_kpis'
        """))
        dc2s_exists = result.fetchone() is not None
        
        print()
        print("✓ DC2_S table:")
        print(f"  dc2s_kpis: {'✅' if dc2s_exists else '❌'}")
        
        # Summary
        print()
        if all([user_cols, account_cols, dc2s_exists]):
            print("✅ MIGRATION SUCCESSFUL")
            print()
            print("Next steps:")
            print("  1. Update models.py (add DC2SKPI model)")
            print("  2. Create DC2_S user and accounts")
            print("  3. Test vertical routing")
            return True
        else:
            print("❌ MIGRATION INCOMPLETE")
            print("Some steps failed - review errors above")
            return False
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

def main():
    """Run simplified multi-vertical migration"""
    
    print()
    print("🚀 MULTI-VERTICAL MIGRATION (SIMPLIFIED)")
    print("=" * 60)
    print()
    print("Focus: DC2_S and SaaS verticals")
    print("Time: 30-60 minutes")
    print()
    print("This will:")
    print("  • Add vertical/role columns")
    print("  • Create dc2s_kpis table")
    print("  • Keep existing kpis table for SaaS")
    print("  • NO portfolio layer (that's future)")
    print()
    print("⚠️  BACKUP YOUR DATABASE FIRST")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ Cancelled")
        return
    
    with app.app_context():
        success = True
        
        if success:
            success = step1_add_vertical_columns()
        
        if success:
            success = step2_create_dc2s_kpi_table()
        
        if success:
            success = step3_tag_existing_kpis_as_saas()
        
        if success:
            success = step4_verify()
        
        if success:
            print()
            print("=" * 60)
            print("✅ MIGRATION COMPLETE!")
            print("=" * 60)
            print()
            print("Your database is now ready for multi-vertical:")
            print("  • DC2_S vertical → dc2s_kpis table")
            print("  • SaaS vertical → kpis table (existing)")
            print()
            print("Next: Run setup_dc2s_vertical.py to create DC2_S data")
            print()
        else:
            print()
            print("=" * 60)
            print("❌ MIGRATION FAILED")
            print("=" * 60)
            print("Database rolled back. Fix errors and retry.")
            print()

if __name__ == "__main__":
    main()
