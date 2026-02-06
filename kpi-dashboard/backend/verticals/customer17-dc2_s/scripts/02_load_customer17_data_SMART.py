#!/usr/bin/env python3
"""
Customer 17 Data Loader - Smart Version
Automatically deletes existing Customer 17 data before loading
"""

import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import datetime
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
# Data directory is one level up from scripts/
DATA_DIR = '../data' if os.path.exists('../data') else './data'
CUSTOMER_ID = 17

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
    print("CUSTOMER 17 DATA LOADER - Smart Version with Auto-Cleanup")
    print("=" * 80)
    print()

def check_database():
    """Check database connection and display config"""
    print(f"✅ Database: {'configured' if DATABASE_URL else 'NOT SET'}")
    print(f"✅ Data Directory: {DATA_DIR}")
    print(f"✅ Customer ID: 17")
    
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
    """Check if Customer 17 data already exists"""
    print()
    print("=" * 80)
    print("CHECKING FOR EXISTING CUSTOMER 17 DATA")
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
                print(f"⚠️  Found existing Customer 17 data:")
                print(f"   Customers: {customer_count}")
                print(f"   Accounts: {account_count}")
                return True
            else:
                print("✅ No existing Customer 17 data found")
                return False
                
    except Exception as e:
        print(f"⚠️  Could not check existing data: {e}")
        return False

def delete_customer17_data(engine):
    """Delete all Customer 17 data in correct order (respecting foreign keys)"""
    print()
    print("🗑️  Deleting existing Customer 17 data...")
    print()
    
    delete_statements = [
        # Delete in reverse dependency order (child tables first)
        ("playbook_executions", "DELETE FROM playbook_executions WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("expansion_readiness_scores", "DELETE FROM expansion_readiness_scores WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("account_health_history", "DELETE FROM account_health_history WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("kpi_measurements", "DELETE FROM kpi_measurements WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("qualitative_signals", "DELETE FROM qualitative_signals WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("account_products", "DELETE FROM account_products WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("account_profiles", "DELETE FROM account_profiles WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("accounts", "DELETE FROM accounts WHERE customer_id = :cid"),
        # Note: kpi_definitions, products, partner_definitions are typically shared across customers
        # Only delete if they are customer-specific
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
                print("✅ Successfully deleted all Customer 17 data")
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
        
        # Handle customers table - only load customer_id and customer_name
        if table_name == 'customers':
            # Only keep columns that exist in the database
            required_cols = ['customer_id', 'customer_name']
            df = df[required_cols]
        
        # Handle accounts table - add missing required columns
        if table_name == 'accounts':
            # Set defaults for missing columns
            if 'account_status' not in df.columns:
                df['account_status'] = 'active'
            if 'external_account_id' not in df.columns:
                df['external_account_id'] = df['account_id'].astype(str)
            if 'revenue' not in df.columns:
                # Use final_arr if available, otherwise initial_arr
                if 'final_arr' in df.columns:
                    df['revenue'] = df['final_arr']
                elif 'initial_arr' in df.columns:
                    df['revenue'] = df['initial_arr']
                else:
                    df['revenue'] = 0
            if 'region' not in df.columns:
                # Extract region from datacenter_location if available
                if 'datacenter_location' in df.columns:
                    df['region'] = df['datacenter_location'].apply(
                        lambda x: x.split('(')[0].strip() if pd.notna(x) and '(' in str(x) else 'Global'
                    )
                else:
                    df['region'] = 'Global'
            if 'vertical' not in df.columns:
                df['vertical'] = 'DC2_S'
            if 'created_at' not in df.columns:
                df['created_at'] = datetime.now()
            if 'updated_at' not in df.columns:
                df['updated_at'] = datetime.now()
        
        # Handle data type conversions for account_profiles
        if table_name == 'account_profiles':
            # Convert boolean columns - most are boolean, but co_marketing_opportunities is integer
            bool_columns = ['strategic_account', 'reference_customer', 'case_study_approved', 
                          'logo_usage_approved', 'innovation_partner', 'advisory_board_member',
                          'narrative_available', 'budget_approved_next_year']
            for col in bool_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: True if (x == True or str(x).lower() == 'true' or x == 1 or str(x) == '1') else False)
            
            # Integer column (co_marketing_opportunities)
            if 'co_marketing_opportunities' in df.columns:
                df['co_marketing_opportunities'] = df['co_marketing_opportunities'].apply(lambda x: 1 if (x == True or str(x).lower() == 'true' or x == 1 or str(x) == '1') else 0)
        
        # Handle kpi_measurements date column
        if table_name == 'kpi_measurements' and 'date' in df.columns and 'measurement_month' not in df.columns:
            df = df.rename(columns={'date': 'measurement_month'})
        
        # Handle boolean columns in other tables
        if table_name == 'account_products' and 'primary_product' in df.columns:
            df['primary_product'] = df['primary_product'].apply(lambda x: True if (x == True or str(x).lower() == 'true' or x == 1 or str(x) == '1') else False)
        
        if table_name == 'kpi_measurements' and 'threshold_breached' in df.columns:
            df['threshold_breached'] = df['threshold_breached'].apply(lambda x: True if (x == True or str(x).lower() == 'true' or x == 1 or str(x) == '1') else False)
        
        if table_name == 'qualitative_signals' and 'is_narrative_signal' in df.columns:
            df['is_narrative_signal'] = df['is_narrative_signal'].apply(lambda x: True if (x == True or str(x).lower() == 'true' or x == 1 or str(x) == '1') else False)
        
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
            
            # Customer 17 specific checks
            print()
            print("🎯 Customer 17 Specific Checks:")
            print("─" * 80)
            
            result = conn.execute(text("SELECT customer_name FROM customers WHERE customer_id = :cid"), {"cid": CUSTOMER_ID})
            customer_name = result.scalar()
            print(f"  ✅ Customer 17: {customer_name}")
            
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
        if not delete_customer17_data(engine):
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
