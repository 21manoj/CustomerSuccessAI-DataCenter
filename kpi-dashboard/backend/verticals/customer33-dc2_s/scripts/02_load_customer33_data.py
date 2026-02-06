#!/usr/bin/env python3
"""
Customer 33 Data Loader - Smart Version
Automatically deletes existing Customer 33 data before loading
"""

import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import datetime
import sys

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
DATA_DIR = './data'
CUSTOMER_ID = 33

# File mapping
FILES = {
    'customers.csv': {'table': 'customers', 'desc': 'Customer profile'},
    'partner_definitions.csv': {'table': 'partner_definitions', 'desc': 'Partner profiles'},
    'accounts.csv': {'table': 'accounts', 'desc': 'Basic accounts'},
    'account_profiles.csv': {'table': 'account_profiles', 'desc': 'Detailed account profiles (100+ attributes)'},
    'kpi_definitions_complete_33_corrected.csv': {'table': 'kpi_definitions', 'desc': 'KPI metadata (38 attributes)'},
    'kpi_measurements.csv': {'table': 'kpi_measurements', 'desc': 'KPI measurements (time series)'},
    'qualitative_signals.csv': {'table': 'qualitative_signals', 'desc': 'Qualitative signals (engagement, sentiment)'},
    'account_health_history.csv': {'table': 'account_health_history', 'desc': 'Account health over time'},
    'expansion_readiness_scores.csv': {'table': 'expansion_readiness_scores', 'desc': 'Expansion readiness tracking'},
    'playbook_executions.csv': {'table': 'playbook_executions', 'desc': 'Playbook execution history'},
    'products.csv': {'table': 'products', 'desc': 'Product catalog'},
    'account_products.csv': {'table': 'account_products', 'desc': 'Account-product usage (24 rows)'},
}

def print_header():
    print("=" * 80)
    print("CUSTOMER 33 DATA LOADER - Smart Version with Auto-Cleanup")
    print("=" * 80)
    print()

def check_database():
    """Check database connection and display config"""
    print(f"✅ Database: {'configured' if DATABASE_URL else 'NOT SET'}")
    print(f"✅ Data Directory: {DATA_DIR}")
    print(f"✅ Customer ID: 33")
    
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            print("✅ Database connection successful")
            return engine
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

def check_existing_data(engine):
    """Check if Customer 33 data already exists"""
    print()
    print("=" * 80)
    print("CHECKING FOR EXISTING CUSTOMER 33 DATA")
    print("=" * 80)
    print()
    
    try:
        with engine.connect() as conn:
            # Check customer
            result = conn.execute(text("SELECT COUNT(*) FROM customers WHERE customer_id = :cid"), {"cid": CUSTOMER_ID})
            customer_count = result.scalar()
            
            # Check accounts
            result = conn.execute(text("SELECT COUNT(*) FROM accounts WHERE customer_id = :cid"), {"cid": CUSTOMER_ID})
            account_count = result.scalar()
            
            if customer_count > 0 or account_count > 0:
                print(f"⚠️  Found existing Customer 33 data:")
                print(f"   Customers: {customer_count}")
                print(f"   Accounts: {account_count}")
                return True
            else:
                print("✅ No existing Customer 33 data found")
                return False
                
    except Exception as e:
        print(f"⚠️  Could not check existing data: {e}")
        return False

def delete_customer33_data(engine):
    """Delete all Customer 33 data in correct order (respecting foreign keys)"""
    print()
    print("🗑️  Deleting existing Customer 33 data...")
    print()
    
    delete_statements = [
        # Delete in reverse dependency order
        ("playbook_executions", "DELETE FROM playbook_executions WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("expansion_readiness_scores", "DELETE FROM expansion_readiness_scores WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("account_health_history", "DELETE FROM account_health_history WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("kpi_measurements", "DELETE FROM kpi_measurements WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("qualitative_signals", "DELETE FROM qualitative_signals WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("account_products", "DELETE FROM account_products WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("account_profiles", "DELETE FROM account_profiles WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("accounts", "DELETE FROM accounts WHERE customer_id = :cid"),
        ("kpi_definitions", "DELETE FROM kpi_definitions"),  # Assuming Customer 33 specific
        ("products", "DELETE FROM products WHERE product_id IN ('PRD-001', 'PRD-002', 'PRD-003', 'PRD-004', 'PRD-005', 'PRD-006', 'PRD-007')"),
        ("partner_definitions", "DELETE FROM partner_definitions WHERE partner_id IN ('P001', 'P002', 'P003', 'P004')"),
        ("customers", "DELETE FROM customers WHERE customer_id = :cid"),
    ]
    
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                for table_name, sql in delete_statements:
                    result = conn.execute(text(sql), {"cid": CUSTOMER_ID})
                    deleted = result.rowcount
                    if deleted > 0:
                        print(f"   ✅ Deleted {deleted} rows from {table_name}")
                
                trans.commit()
                print()
                print("✅ Successfully deleted all Customer 33 data")
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Error during deletion: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Failed to delete data: {e}")
        return False

def load_table(engine, filename, table_name, description):
    """Load a single CSV file into database"""
    print("─" * 80)
    print(f"📊 Loading: {description}")
    print(f"   File: {filename}")
    print(f"   Table: {table_name}")
    
    filepath = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f"   ❌ File not found: {filepath}")
        return False
    
    try:
        # Read CSV
        df = pd.read_csv(filepath)
        print(f"   📈 Rows: {len(df)} | Columns: {len(df.columns)}")
        
        # Load to PostgreSQL
        print(f"   ⏳ Loading to PostgreSQL... ", end='', flush=True)
        df.to_sql(
            table_name,
            engine,
            if_exists='append',  # Safe to append now since we deleted first
            index=False,
            method='multi',
            chunksize=1000
        )
        print("✅")
        
        # Verify
        with engine.connect() as conn:
            if table_name in ['accounts', 'account_profiles', 'kpi_measurements', 
                             'qualitative_signals', 'account_health_history', 
                             'expansion_readiness_scores', 'playbook_executions', 'account_products']:
                # Tables with customer_id or account_id
                if table_name == 'accounts':
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name} WHERE customer_id = :cid"), {"cid": CUSTOMER_ID})
                else:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name} WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"), {"cid": CUSTOMER_ID})
            elif table_name == 'customers':
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name} WHERE customer_id = :cid"), {"cid": CUSTOMER_ID})
            else:
                # Partner_definitions, products, kpi_definitions - count all
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            
            count = result.scalar()
            print(f"   ✅ Verified: {count} rows in database")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def verify_integrity(engine):
    """Verify data integrity and foreign keys"""
    print()
    print("=" * 80)
    print("DATA INTEGRITY VERIFICATION")
    print("=" * 80)
    print()
    
    try:
        with engine.connect() as conn:
            # Record counts
            print("📊 Record Counts:")
            print(f"{'Table':<40} {'Count':>10}     Status")
            print("─" * 60)
            
            expected_counts = {
                'customers': 1,
                'partner_definitions': 4,
                'accounts': 10,
                'account_profiles': 10,
                'kpi_definitions': 34,
                'kpi_measurements': 3696,
                'qualitative_signals': 320,
                'account_health_history': 113,
                'expansion_readiness_scores': 113,
                'playbook_executions': 28,
                'products': 7,
                'account_products': 24,
            }
            
            total = 0
            all_match = True
            
            for table, expected in expected_counts.items():
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                total += count
                
                status = "✅" if count == expected else f"⚠️ (exp: {expected})"
                print(f"{table:<40} {count:>10} {status:>10}")
                
                if count != expected:
                    all_match = False
            
            print("─" * 60)
            print(f"{'TOTAL':<40} {total:>10}")
            print()
            
            # Foreign key checks
            print("🔗 Foreign Key Integrity:")
            print("─" * 80)
            
            checks = [
                ("Accounts → Customers", "SELECT COUNT(*) FROM accounts a LEFT JOIN customers c ON a.customer_id = c.customer_id WHERE c.customer_id IS NULL"),
                ("Account Profiles → Accounts", "SELECT COUNT(*) FROM account_profiles ap LEFT JOIN accounts a ON ap.account_id = a.account_id WHERE a.account_id IS NULL"),
                ("KPI Measurements → Accounts", "SELECT COUNT(*) FROM kpi_measurements km LEFT JOIN accounts a ON km.account_id = a.account_id WHERE a.account_id IS NULL"),
                ("KPI Measurements → KPI Definitions", "SELECT COUNT(*) FROM kpi_measurements km LEFT JOIN kpi_definitions kd ON km.kpi_code = kd.kpi_code WHERE kd.kpi_code IS NULL"),
                ("Account Products → Accounts", "SELECT COUNT(*) FROM account_products ap LEFT JOIN accounts a ON ap.account_id = a.account_id WHERE a.account_id IS NULL"),
                ("Account Products → Products", "SELECT COUNT(*) FROM account_products ap LEFT JOIN products p ON ap.product_id = p.product_id WHERE p.product_id IS NULL"),
            ]
            
            fk_ok = True
            for check_name, sql in checks:
                result = conn.execute(text(sql))
                orphans = result.scalar()
                status = "✅ PASS" if orphans == 0 else f"❌ FAIL ({orphans} orphans)"
                print(f"  {check_name:<50} {status}")
                if orphans > 0:
                    fk_ok = False
            
            # Customer 33 specific checks
            print()
            print("🎯 Customer 33 Specific Checks:")
            print("─" * 80)
            
            result = conn.execute(text("SELECT customer_name FROM customers WHERE customer_id = :cid"), {"cid": CUSTOMER_ID})
            customer_name = result.scalar()
            print(f"  ✅ Customer 33: {customer_name}")
            
            result = conn.execute(text("SELECT COUNT(*) FROM accounts WHERE customer_id = :cid"), {"cid": CUSTOMER_ID})
            account_count = result.scalar()
            print(f"  ✅ Accounts: {account_count} (expected: 10)")
            
            return all_match and fk_ok
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

def main():
    print_header()
    
    # Check database
    engine = check_database()
    print()
    
    # Check for existing data
    has_existing = check_existing_data(engine)
    
    # Delete existing data if found
    if has_existing:
        if not delete_customer33_data(engine):
            print("❌ Failed to delete existing data. Aborting.")
            sys.exit(1)
    
    # Start data load
    print()
    print("=" * 80)
    print("STARTING DATA LOAD")
    print("=" * 80)
    print()
    
    # Find CSV files
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    print(f"📁 Found {len(csv_files)} CSV files in {DATA_DIR}")
    print()
    
    # Load tables
    success_count = 0
    failed_count = 0
    
    for filename, info in FILES.items():
        if load_table(engine, filename, info['table'], info['desc']):
            success_count += 1
        else:
            failed_count += 1
        print()
    
    # Summary
    print("=" * 80)
    print("LOAD SUMMARY")
    print("=" * 80)
    print(f"  ✅ Successful: {success_count}")
    print(f"  ❌ Failed: {failed_count}")
    print(f"  ⏭️  Skipped: 0")
    print(f"  📊 Total: {len(FILES)}")
    
    if failed_count > 0:
        print()
        print("⚠️  WARNING: Some tables failed to load")
        print("Review errors above")
    
    # Verify integrity
    print()
    integrity_ok = verify_integrity(engine)
    
    # Final status
    print()
    print("=" * 80)
    if success_count == len(FILES) and integrity_ok:
        print("✅ SUCCESS: All data loaded and verified!")
    elif success_count == len(FILES):
        print("⚠️  WARNING: All data loaded but integrity checks failed")
    else:
        print("❌ FAILURE: Some tables failed to load")
    print("=" * 80)
    print()
    
    if success_count == len(FILES) and integrity_ok:
        print("Next steps:")
        print("  1. Generate embeddings: python3 scripts/03_embed_signals_qdrant.py")
        print("  2. Validate: python3 scripts/04_validate_data_integrity.py")
        print()

if __name__ == "__main__":
    main()
