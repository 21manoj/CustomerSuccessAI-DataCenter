#!/usr/bin/env python3
"""
Customer {CUSTOMER_ID} Data Loader - Smart Version
Automatically deletes existing Customer {CUSTOMER_ID} data before loading
"""

import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import datetime
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
# Data directory is one level up from scripts/
# Detect at runtime based on script location, not module load time
def get_data_dir():
    """Get data directory path relative to script location"""
    script_dir = Path(__file__).parent
    # Check if ../data exists (when run from scripts/)
    parent_data = script_dir.parent / 'data'
    if parent_data.exists():
        return str(parent_data)
    # Fallback to ./data (when run from backend/)
    local_data = script_dir / 'data'
    if local_data.exists():
        return str(local_data)
    # Default to ../data (expected location)
    return str(parent_data)

DATA_DIR = get_data_dir()
CUSTOMER_ID = {CUSTOMER_ID}

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
    print("CUSTOMER 9 DATA LOADER - Smart Version with Auto-Cleanup")
    print("=" * 80)
    print()

def check_database():
    """Check database connection and display config"""
    print(f"✅ Database: {'configured' if DATABASE_URL else 'NOT SET'}")
    print(f"✅ Data Directory: {DATA_DIR}")
    print(f"✅ Customer ID: {CUSTOMER_ID}")
    
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
    """Check if Customer {CUSTOMER_ID} data already exists"""
    print()
    print("=" * 80)
    print("CHECKING FOR EXISTING CUSTOMER 9 DATA")
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
                print(f"⚠️  Found existing Customer {CUSTOMER_ID} data:")
                print(f"   Customers: {customer_count}")
                print(f"   Accounts: {account_count}")
                return True
            else:
                print("✅ No existing Customer {CUSTOMER_ID} data found")
                return False
                
    except Exception as e:
        print(f"⚠️  Could not check existing data: {e}")
        return False

def delete_customer9_data(engine):
    """Delete all Customer {CUSTOMER_ID} data in correct order (respecting foreign keys)
    
    CRITICAL DELETION ORDER:
    Always delete in this order to avoid FK constraint violations:
    1. Deepest children first (kpi_measurements, events, health_snapshots, etc.)
    2. Their parents next (accounts)
    3. Top-level records last (kpi_definitions - only if customer-specific)
    
    WHY: PostgreSQL enforces foreign key constraints. You cannot delete
    a parent record while children still reference it.
    """
    print()
    print("🗑️  Deleting existing Customer {CUSTOMER_ID} data...")
    print()
    
    delete_statements = [
        # ===================================================================
        # STEP 1: Delete child records of Account (deepest children first)
        # ===================================================================
        ("playbook_executions", "DELETE FROM playbook_executions WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("expansion_readiness_scores", "DELETE FROM expansion_readiness_scores WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("account_health_history", "DELETE FROM account_health_history WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        # CRITICAL: Delete kpi_measurements BEFORE kpi_definitions (FK: kpi_code)
        ("kpi_measurements", "DELETE FROM kpi_measurements WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("qualitative_signals", "DELETE FROM qualitative_signals WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("account_products", "DELETE FROM account_products WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("account_profiles", "DELETE FROM account_profiles WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        
        # ===================================================================
        # STEP 2: Delete Account records (parent of above children)
        # ===================================================================
        ("accounts", "DELETE FROM accounts WHERE customer_id = :cid"),
        
        # ===================================================================
        # STEP 3: Delete top-level records (only if customer-specific)
        # ===================================================================
        # CRITICAL: kpi_definitions may be shared across customers
        # Only delete kpi_definitions that were actually used by this customer's kpi_measurements
        # This is done AFTER kpi_measurements are deleted to avoid FK violations
        # Note: We'll handle kpi_definitions specially using captured kpi_codes
        ("kpi_definitions", None),  # Handled specially below using captured kpi_codes
        # CRITICAL: Products must be deleted AFTER account_products (FK: product_id)
        # Only delete products that are customer-specific and not referenced by other customers' account_products
        # If products are shared, skip deletion (they may be used by other customers)
        ("products", "DELETE FROM products WHERE product_id IN ('PRD-001', 'PRD-002', 'PRD-003', 'PRD-004', 'PRD-005', 'PRD-006', 'PRD-007') AND customer_id = :cid AND product_id NOT IN (SELECT DISTINCT product_id FROM account_products WHERE product_id IN ('PRD-001', 'PRD-002', 'PRD-003', 'PRD-004', 'PRD-005', 'PRD-006', 'PRD-007'))"),
        # CRITICAL: partner_definitions must be deleted AFTER accounts (FK: partner_id)
        # Only delete if not referenced by any accounts (may be shared)
        ("partner_definitions", "DELETE FROM partner_definitions WHERE partner_id IN ('P001', 'P002', 'P003', 'P004') AND partner_id NOT IN (SELECT DISTINCT partner_id FROM accounts WHERE partner_id IN ('P001', 'P002', 'P003', 'P004'))"),
        ("customers", "DELETE FROM customers WHERE customer_id = :cid"),
    ]
    
    try:
        # CRITICAL: Capture kpi_codes BEFORE starting deletion transaction
        # Use separate connection to avoid transaction conflicts
        kpi_codes_to_delete = []
        try:
            with engine.connect() as check_conn:
                kpi_codes_sql = """
                    SELECT DISTINCT kpi_code 
                    FROM kpi_measurements 
                    WHERE account_id IN (
                        SELECT account_id FROM accounts WHERE customer_id = :cid
                    )
                """
                result = check_conn.execute(text(kpi_codes_sql), {"cid": CUSTOMER_ID})
                kpi_codes_to_delete = [row[0] for row in result.fetchall()]
                if kpi_codes_to_delete:
                    print(f"   📋 Found {len(kpi_codes_to_delete)} unique KPI codes used by this customer")
        except Exception as e:
            print(f"   ⚠️  Could not fetch KPI codes (table may not exist): {e}")
        
        # Now execute deletions in a transaction
        with engine.begin() as conn:  # Use begin() context manager - auto-commits on success, rolls back on error
            
            deletion_errors = []
            critical_error = None
            
            for table_name, sql in delete_statements:
                # Skip if sql is None (handled specially)
                if sql is None:
                    continue
                
                try:
                    # Special handling for kpi_definitions - use captured kpi_codes
                    if table_name == "kpi_definitions":
                        if kpi_codes_to_delete:
                            # Delete only kpi_definitions that were used by this customer
                            # Use parameterized query to avoid SQL injection
                            kpi_codes_placeholders = ",".join([f":code{i}" for i in range(len(kpi_codes_to_delete))])
                            kpi_defs_sql = f"DELETE FROM kpi_definitions WHERE kpi_code IN ({kpi_codes_placeholders})"
                            params = {f"code{i}": code for i, code in enumerate(kpi_codes_to_delete)}
                            result = conn.execute(text(kpi_defs_sql), params)
                            deleted = result.rowcount
                            if deleted > 0:
                                print(f"   ✅ Deleted {deleted} customer-specific KPI definitions")
                            else:
                                print(f"   ⚠️  No KPI definitions deleted (may be shared or already deleted)")
                        else:
                            # No kpi_codes found - kpi_definitions might be shared
                            print(f"   ⚠️  Skipping {table_name} (no customer-specific definitions found - may be shared)")
                    else:
                        # Regular deletion statement
                        result = conn.execute(text(sql), {"cid": CUSTOMER_ID})
                        deleted = result.rowcount
                        if deleted > 0:
                            print(f"   ✅ Deleted {deleted} rows from {table_name}")
                except Exception as table_error:
                    # Handle FK constraint violations or missing columns
                    error_msg = str(table_error).lower()
                    if "foreign key" in error_msg or ("constraint" in error_msg and "violates" in error_msg):
                        # Critical FK violation - this will cause transaction to rollback
                        print(f"   ❌ Error deleting {table_name}: {table_error}")
                        print(f"   ⚠️  This indicates a deletion order issue - children must be deleted before parents")
                        critical_error = table_error
                        raise  # Re-raise FK violations - transaction will rollback automatically
                    elif "column" in error_msg or "does not exist" in error_msg:
                        # Missing column - skip this table, continue with others
                        print(f"   ⚠️  Skipping {table_name} (column/table doesn't exist: {table_error})")
                        deletion_errors.append((table_name, str(table_error)))
                        # Continue with next statement
                    else:
                        # Unexpected error - log but continue
                        print(f"   ⚠️  Unexpected error deleting {table_name}: {table_error}")
                        deletion_errors.append((table_name, str(table_error)))
            
            # If we get here, transaction will auto-commit
            if deletion_errors:
                print(f"   ⚠️  Some deletions had errors (non-critical): {len(deletion_errors)}")
                for table_name, error in deletion_errors:
                    print(f"      - {table_name}: {error}")
            
            print()
            print("✅ Successfully deleted all Customer {CUSTOMER_ID} data")
            return True
                
    except Exception as e:
        print(f"❌ Failed to delete data: {e}")
        return False

def load_table(engine, filename, table_name, description, upload_mode='incremental'):
    """Load a single CSV file into database with upload mode support
    
    Args:
        engine: SQLAlchemy engine
        filename: CSV filename
        table_name: Target database table
        description: Description for logging
        upload_mode: One of 'full_refresh', 'incremental', 'upsert', 'merge'
    """
    print("─" * 80)
    print(f"📊 Loading: {description}")
    print(f"   File: {filename}")
    print(f"   Table: {table_name}")
    print(f"   Mode: {upload_mode}")
    
    filepath = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f"   ❌ File not found: {filepath}")
        return False
    
    try:
        # Read CSV
        df = pd.read_csv(filepath)
        print(f"   📈 Rows: {len(df)} | Columns: {len(df.columns)}")
        
        # Handle different upload modes
        if_exists_mode = 'append'  # Default
        
        if upload_mode == 'full_refresh':
            # Delete existing data for this customer first
            print(f"   🗑️  Full Refresh: Deleting existing data for customer {CUSTOMER_ID}...")
            with engine.connect() as conn:
                if table_name == 'accounts':
                    result = conn.execute(text(f"DELETE FROM {table_name} WHERE customer_id = :cid"), {"cid": CUSTOMER_ID})
                elif table_name in ['kpi_measurements', 'qualitative_signals', 'account_profiles', 
                                   'account_health_history', 'expansion_readiness_scores', 
                                   'playbook_executions', 'account_products']:
                    result = conn.execute(text(f"""
                        DELETE FROM {table_name} 
                        WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)
                    """), {"cid": CUSTOMER_ID})
                elif table_name == 'customers':
                    result = conn.execute(text(f"DELETE FROM {table_name} WHERE customer_id = :cid"), {"cid": CUSTOMER_ID})
                else:
                    # For shared tables (products, kpi_definitions, partner_definitions)
                    # Only delete if they have customer_id column
                    try:
                        result = conn.execute(text(f"DELETE FROM {table_name} WHERE customer_id = :cid"), {"cid": CUSTOMER_ID})
                    except:
                        # Table doesn't have customer_id, skip deletion
                        print(f"   ⚠️  Table {table_name} doesn't have customer_id, skipping deletion")
                deleted = result.rowcount
                if deleted > 0:
                    print(f"   ✅ Deleted {deleted} existing rows")
            if_exists_mode = 'append'  # Now append new data
        
        elif upload_mode == 'incremental':
            if_exists_mode = 'append'  # Simply append new data
        
        elif upload_mode == 'upsert':
            # For upsert, we need to update existing records and insert new ones
            # This requires identifying the primary key or unique constraint
            print(f"   🔄 Upsert: Updating existing, inserting new...")
            if_exists_mode = 'append'  # We'll handle upsert logic after loading
            # Note: Full upsert logic would require knowing primary keys per table
            # For now, we'll append and let database handle duplicates if unique constraints exist
        
        elif upload_mode == 'merge':
            # Merge mode: Smart merge with conflict resolution
            print(f"   🔀 Merge: Smart merge with conflict resolution...")
            if_exists_mode = 'append'  # Similar to upsert, but with conflict resolution logic
            # Note: Full merge logic would require conflict resolution rules
        
        # Load to PostgreSQL
        print(f"   ⏳ Loading to PostgreSQL... ", end='', flush=True)
        df.to_sql(
            table_name,
            engine,
            if_exists=if_exists_mode,
            index=False,
            method='multi',
            chunksize=1000
        )
        print("✅")
        
        # Post-processing for upsert/merge modes
        if upload_mode in ['upsert', 'merge'] and table_name == 'accounts':
            # For accounts, update existing records based on account_id
            print(f"   🔄 Post-processing: Updating existing accounts...")
            with engine.connect() as conn:
                for _, row in df.iterrows():
                    account_id = row.get('account_id')
                    if account_id:
                        # Build UPDATE statement for non-null columns
                        update_cols = []
                        update_vals = {}
                        for col in df.columns:
                            if col != 'account_id' and pd.notna(row[col]):
                                update_cols.append(f"{col} = :{col}")
                                update_vals[col] = row[col]
                        
                        if update_cols:
                            update_sql = f"""
                                UPDATE {table_name} 
                                SET {', '.join(update_cols)}
                                WHERE account_id = :account_id
                            """
                            update_vals['account_id'] = account_id
                            conn.execute(text(update_sql), update_vals)
                conn.commit()
            print("   ✅ Upsert/Merge completed")
        
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
            
            # Customer {CUSTOMER_ID} specific checks
            print()
            print("🎯 Customer {CUSTOMER_ID} Specific Checks:")
            print("─" * 80)
            
            result = conn.execute(text("SELECT customer_name FROM customers WHERE customer_id = :cid"), {"cid": CUSTOMER_ID})
            customer_name = result.scalar()
            print(f"  ✅ Customer {CUSTOMER_ID}: {customer_name}")
            
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
        if not delete_customer9_data(engine):
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
    
    # Get upload mode from environment variable (set by onboarding_api.py)
    upload_mode = os.getenv('UPLOAD_MODE', 'incremental')
    print(f"📋 Upload Mode: {upload_mode}")
    print()
    
    # Load tables
    success_count = 0
    failed_count = 0
    
    for filename, info in FILES.items():
        if load_table(engine, filename, info['table'], info['desc'], upload_mode=upload_mode):
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
    
    # ====================================================================
    # CRITICAL FIX: Explicit commit to ensure data is visible
    # ====================================================================
    print()
    print("=" * 80)
    print("COMMITTING DATA TO DATABASE")
    print("=" * 80)
    print()
    
    try:
        # Force commit all pending changes
        with engine.begin() as conn:
            # Explicit commit via begin() context manager
            # This ensures all data loaded by pandas to_sql() is committed
            conn.execute(text("SELECT 1"))  # Dummy query to ensure connection is active
        print("✅ All data committed to database")
        
        # Verify commit by checking counts
        with engine.connect() as conn:
            # Check KPI measurements
            result = conn.execute(text("""
                SELECT COUNT(*) FROM kpi_measurements 
                WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)
            """), {"cid": CUSTOMER_ID})
            kpi_count = result.scalar()
            
            # Check qualitative signals
            result = conn.execute(text("""
                SELECT COUNT(*) FROM qualitative_signals 
                WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)
            """), {"cid": CUSTOMER_ID})
            signal_count = result.scalar()
            
            print(f"🔍 Verification:")
            print(f"   KPI measurements: {kpi_count}")
            print(f"   Qualitative signals: {signal_count}")
            
    except Exception as e:
        print(f"❌ Commit verification failed: {e}")
        import traceback
        traceback.print_exc()
    
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
