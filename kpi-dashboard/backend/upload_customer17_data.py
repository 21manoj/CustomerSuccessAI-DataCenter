#!/usr/bin/env python3
"""
Customer 17 Data Upload Script
Uploads CSV files directly to database (same approach as customer 9)
"""

import pandas as pd
import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
DATA_DIR = './verticals/customer17-dc2_s/data'
CUSTOMER_ID = 17

# File mapping - map our CSV names to database table names
FILES = {
    'accounts.csv': {'table': 'accounts', 'desc': 'Basic accounts'},
    'profiles.csv': {'table': 'account_profiles', 'desc': 'Detailed account profiles'},
    'kpis.csv': {'table': 'kpi_measurements', 'desc': 'KPI measurements (time series)'},
    'signals.csv': {'table': 'qualitative_signals', 'desc': 'Qualitative signals'},
    'products.csv': {'table': 'account_products', 'desc': 'Account-product usage'},
}

def check_database():
    """Check database connection"""
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

def delete_customer17_data(engine):
    """Delete all Customer 17 data in correct order"""
    print("\n🗑️  Deleting existing Customer 17 data...")
    
    delete_statements = [
        ("kpi_measurements", "DELETE FROM kpi_measurements WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("qualitative_signals", "DELETE FROM qualitative_signals WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("account_products", "DELETE FROM account_products WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("account_profiles", "DELETE FROM account_profiles WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
        ("accounts", "DELETE FROM accounts WHERE customer_id = :cid"),
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
                print("✅ Successfully deleted all Customer 17 data\n")
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
    print(f"\n📊 Loading: {description}")
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
        
        # Handle column name mapping if needed
        # kpis.csv has 'date' column, but kpi_measurements table expects 'measurement_month'
        if filename == 'kpis.csv' and 'date' in df.columns:
            df = df.rename(columns={'date': 'measurement_month'})
        
        # Convert boolean columns - check what type the database expects
        # account_profiles: most are boolean, but co_marketing_opportunities is integer
        if filename == 'profiles.csv':
            # Boolean columns
            bool_columns = ['strategic_account', 'reference_customer', 'case_study_approved', 
                          'logo_usage_approved', 'innovation_partner', 'advisory_board_member',
                          'narrative_available', 'budget_approved_next_year']
            for col in bool_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: True if (x == True or str(x).lower() == 'true' or x == 1 or str(x) == '1') else False)
            
            # Integer column (co_marketing_opportunities)
            if 'co_marketing_opportunities' in df.columns:
                df['co_marketing_opportunities'] = df['co_marketing_opportunities'].apply(lambda x: 1 if (x == True or str(x).lower() == 'true' or x == 1 or str(x) == '1') else 0)
        
        # account_products: primary_product is boolean
        if filename == 'products.csv':
            bool_columns = ['primary_product']
            for col in bool_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: True if (x == True or str(x).lower() == 'true' or x == 1 or str(x) == '1') else False)
        
        # kpi_measurements: threshold_breached is boolean
        if filename == 'kpis.csv':
            bool_columns = ['threshold_breached']
            for col in bool_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: True if (x == True or str(x).lower() == 'true' or x == 1 or str(x) == '1') else False)
        
        # qualitative_signals: is_narrative_signal is boolean
        if filename == 'signals.csv':
            bool_columns = ['is_narrative_signal']
            for col in bool_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: True if (x == True or str(x).lower() == 'true' or x == 1 or str(x) == '1') else False)
        
        # Load to PostgreSQL
        print(f"   ⏳ Loading to PostgreSQL... ", end='', flush=True)
        
        # For accounts table, set missing fields before upload
        if filename == 'accounts.csv':
            # Set defaults for missing columns
            if 'account_status' not in df.columns:
                df['account_status'] = 'active'
            if 'external_account_id' not in df.columns:
                df['external_account_id'] = df['account_id'].astype(str)
            if 'revenue' not in df.columns:
                df['revenue'] = df['final_arr']
            if 'region' not in df.columns:
                # Extract region from datacenter_location if available
                if 'datacenter_location' in df.columns:
                    df['region'] = df['datacenter_location'].apply(
                        lambda x: x.split('(')[0].strip() if '(' in str(x) else 'Global'
                    )
                else:
                    df['region'] = 'Global'
            if 'vertical' not in df.columns:
                df['vertical'] = 'DC2_S'  # Data center vertical
            if 'created_at' not in df.columns:
                df['created_at'] = datetime.now()
            if 'updated_at' not in df.columns:
                df['updated_at'] = datetime.now()
        
        df.to_sql(
            table_name,
            engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )
        print("✅")
        
        # Verify
        with engine.connect() as conn:
            if table_name == 'accounts':
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name} WHERE customer_id = :cid"), {"cid": CUSTOMER_ID})
            elif table_name in ['account_profiles', 'kpi_measurements', 'qualitative_signals', 'account_products']:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name} WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"), {"cid": CUSTOMER_ID})
            else:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            
            count = result.scalar()
            print(f"   ✅ Verified: {count} rows in database")
        
        return True
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_integrity(engine):
    """Verify data integrity"""
    print("\n" + "=" * 80)
    print("DATA INTEGRITY VERIFICATION")
    print("=" * 80)
    
    try:
        with engine.connect() as conn:
            print("\n📊 Record Counts:")
            print(f"{'Table':<40} {'Count':>10}")
            print("─" * 60)
            
            checks = [
                ('accounts', "SELECT COUNT(*) FROM accounts WHERE customer_id = :cid"),
                ('account_profiles', "SELECT COUNT(*) FROM account_profiles WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
                ('kpi_measurements', "SELECT COUNT(*) FROM kpi_measurements WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
                ('qualitative_signals', "SELECT COUNT(*) FROM qualitative_signals WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
                ('account_products', "SELECT COUNT(*) FROM account_products WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
            ]
            
            total = 0
            for table, sql in checks:
                result = conn.execute(text(sql), {"cid": CUSTOMER_ID})
                count = result.scalar()
                total += count
                print(f"{table:<40} {count:>10}")
            
            print("─" * 60)
            print(f"{'TOTAL':<40} {total:>10}")
            
            # Foreign key checks
            print("\n🔗 Foreign Key Integrity:")
            print("─" * 80)
            
            fk_checks = [
                ("Accounts → Customers", "SELECT COUNT(*) FROM accounts a LEFT JOIN customers c ON a.customer_id = c.customer_id WHERE c.customer_id IS NULL AND a.customer_id = :cid"),
                ("Account Profiles → Accounts", "SELECT COUNT(*) FROM account_profiles ap LEFT JOIN accounts a ON ap.account_id = a.account_id WHERE a.account_id IS NULL AND ap.account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
                ("KPI Measurements → Accounts", "SELECT COUNT(*) FROM kpi_measurements km LEFT JOIN accounts a ON km.account_id = a.account_id WHERE a.account_id IS NULL AND km.account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
                ("Account Products → Accounts", "SELECT COUNT(*) FROM account_products ap LEFT JOIN accounts a ON ap.account_id = a.account_id WHERE a.account_id IS NULL AND ap.account_id IN (SELECT account_id FROM accounts WHERE customer_id = :cid)"),
            ]
            
            fk_ok = True
            for check_name, sql in fk_checks:
                result = conn.execute(text(sql), {"cid": CUSTOMER_ID})
                orphans = result.scalar()
                status = "✅ PASS" if orphans == 0 else f"❌ FAIL ({orphans} orphans)"
                print(f"  {check_name:<50} {status}")
                if orphans > 0:
                    fk_ok = False
            
            return fk_ok
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 80)
    print("CUSTOMER 17 DATA UPLOAD")
    print("=" * 80)
    print()
    
    # Check database
    engine = check_database()
    print(f"✅ Data Directory: {DATA_DIR}")
    print(f"✅ Customer ID: {CUSTOMER_ID}")
    
    # Delete existing data first
    delete_customer17_data(engine)
    
    # Start data load
    print("\n" + "=" * 80)
    print("STARTING DATA LOAD")
    print("=" * 80)
    
    success_count = 0
    failed_count = 0
    
    for filename, info in FILES.items():
        if load_table(engine, filename, info['table'], info['desc']):
            success_count += 1
        else:
            failed_count += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("LOAD SUMMARY")
    print("=" * 80)
    print(f"  ✅ Successful: {success_count}")
    print(f"  ❌ Failed: {failed_count}")
    print(f"  📊 Total: {len(FILES)}")
    
    # Verify integrity
    if success_count == len(FILES):
        integrity_ok = verify_integrity(engine)
        
        print("\n" + "=" * 80)
        if integrity_ok:
            print("✅ SUCCESS: All data loaded and verified!")
        else:
            print("⚠️  WARNING: All data loaded but integrity checks failed")
        print("=" * 80)
    else:
        print("\n❌ FAILURE: Some tables failed to load")
        print("=" * 80)

if __name__ == "__main__":
    main()
