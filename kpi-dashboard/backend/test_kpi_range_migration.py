#!/usr/bin/env python3
"""
Test script to manually run the KPI Reference Range migration
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3

# Path to database
DB_PATH = '../instance/kpi_dashboard.db'

def check_current_schema():
    """Check current schema of kpi_reference_ranges table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 70)
    print("CURRENT SCHEMA:")
    print("=" * 70)
    
    # Get table info
    cursor.execute("PRAGMA table_info(kpi_reference_ranges)")
    columns = cursor.fetchall()
    
    for col in columns:
        print(f"  {col[1]}: {col[2]} {'(PK)' if col[5] else ''} {'NOT NULL' if col[3] else 'NULL'}")
    
    # Check for existing constraints
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='kpi_reference_ranges'")
    table_sql = cursor.fetchone()
    if table_sql:
        print(f"\nTable SQL:\n{table_sql[0]}")
    
    # Count existing ranges
    cursor.execute("SELECT COUNT(*) FROM kpi_reference_ranges")
    count = cursor.fetchone()[0]
    print(f"\nExisting reference ranges: {count}")
    
    conn.close()
    return count

def run_migration():
    """Run the migration manually"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "=" * 70)
    print("RUNNING MIGRATION:")
    print("=" * 70)
    
    try:
        # Step 1: Add customer_id column
        print("\n1. Adding customer_id column...")
        cursor.execute("""
            ALTER TABLE kpi_reference_ranges 
            ADD COLUMN customer_id INTEGER 
            REFERENCES customers(customer_id) ON DELETE CASCADE
        """)
        print("   ✅ customer_id column added")
        
        # Step 2: SQLite doesn't support dropping constraints directly
        # We need to recreate the table
        print("\n2. Recreating table with new constraints...")
        
        # Create new table with correct schema
        cursor.execute("""
            CREATE TABLE kpi_reference_ranges_new (
                range_id INTEGER PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(customer_id) ON DELETE CASCADE,
                kpi_name TEXT NOT NULL,
                unit TEXT NOT NULL,
                higher_is_better INTEGER NOT NULL DEFAULT 1,
                critical_min NUMERIC(10, 2) NOT NULL,
                critical_max NUMERIC(10, 2) NOT NULL,
                risk_min NUMERIC(10, 2) NOT NULL,
                risk_max NUMERIC(10, 2) NOT NULL,
                healthy_min NUMERIC(10, 2) NOT NULL,
                healthy_max NUMERIC(10, 2) NOT NULL,
                critical_range TEXT,
                risk_range TEXT,
                healthy_range TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER REFERENCES users(user_id),
                updated_by INTEGER REFERENCES users(user_id),
                UNIQUE(customer_id, kpi_name)
            )
        """)
        print("   ✅ New table created")
        
        # Copy data from old table
        print("\n3. Copying existing data...")
        cursor.execute("""
            INSERT INTO kpi_reference_ranges_new 
            SELECT range_id, NULL as customer_id, kpi_name, unit, higher_is_better,
                   critical_min, critical_max, risk_min, risk_max,
                   healthy_min, healthy_max, critical_range, risk_range, healthy_range,
                   description, created_at, updated_at, created_by, updated_by
            FROM kpi_reference_ranges
        """)
        rows_copied = cursor.rowcount
        print(f"   ✅ {rows_copied} rows copied (all with customer_id = NULL)")
        
        # Drop old table
        print("\n4. Dropping old table...")
        cursor.execute("DROP TABLE kpi_reference_ranges")
        print("   ✅ Old table dropped")
        
        # Rename new table
        print("\n5. Renaming new table...")
        cursor.execute("ALTER TABLE kpi_reference_ranges_new RENAME TO kpi_reference_ranges")
        print("   ✅ Table renamed")
        
        # Create index
        print("\n6. Creating index...")
        cursor.execute("""
            CREATE INDEX idx_ref_range_customer_kpi 
            ON kpi_reference_ranges(customer_id, kpi_name)
        """)
        print("   ✅ Index created")
        
        conn.commit()
        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 70)
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {e}")
        return False
    finally:
        conn.close()
    
    return True

def verify_migration():
    """Verify migration was successful"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "=" * 70)
    print("VERIFICATION:")
    print("=" * 70)
    
    # Check schema
    cursor.execute("PRAGMA table_info(kpi_reference_ranges)")
    columns = cursor.fetchall()
    
    has_customer_id = any(col[1] == 'customer_id' for col in columns)
    print(f"\n✓ customer_id column exists: {has_customer_id}")
    
    # Check data
    cursor.execute("SELECT COUNT(*) FROM kpi_reference_ranges WHERE customer_id IS NULL")
    null_count = cursor.fetchone()[0]
    print(f"✓ Ranges with customer_id = NULL: {null_count} (system defaults)")
    
    cursor.execute("SELECT COUNT(*) FROM kpi_reference_ranges WHERE customer_id IS NOT NULL")
    non_null_count = cursor.fetchone()[0]
    print(f"✓ Ranges with customer_id set: {non_null_count} (customer-specific)")
    
    # List some examples
    cursor.execute("SELECT kpi_name, customer_id FROM kpi_reference_ranges LIMIT 5")
    examples = cursor.fetchall()
    print(f"\nSample ranges:")
    for kpi, cust_id in examples:
        cust_str = "System Default" if cust_id is None else f"Customer {cust_id}"
        print(f"  • {kpi}: {cust_str}")
    
    conn.close()

if __name__ == '__main__':
    print("KPI Reference Range Migration Test")
    print("=" * 70)
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)
    
    # Check current schema
    count = check_current_schema()
    
    if count == 0:
        print("\n⚠️  No reference ranges found. Migration may not be needed.")
        sys.exit(0)
    
    # Ask for confirmation
    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        sys.exit(0)
    
    # Run migration
    success = run_migration()
    
    if success:
        # Verify
        verify_migration()
    else:
        print("\n❌ Migration failed. Database rolled back.")
        sys.exit(1)

