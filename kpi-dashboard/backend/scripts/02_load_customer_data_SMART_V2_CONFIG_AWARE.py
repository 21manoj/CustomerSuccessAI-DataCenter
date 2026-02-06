#!/usr/bin/env python3
"""
Config-Aware Customer Data Loader - V2
======================================

UPDATED: Now respects CustomerConfig
- Only loads KPIs that are enabled in customer_configs
- Filters out disabled KPIs from CSV uploads
- Backward compatible with existing CSV structure

This is a TEMPLATE script. When creating customer-specific loaders:
1. Copy this file to: verticals/customer{ID}-dc2_s/scripts/02_load_customer{ID}_data_SMART.py
2. Update CUSTOMER_ID constant
3. Run the script

Usage:
    python3 02_load_customer{ID}_data_SMART.py
"""

import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
import json

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app_v3_minimal import app, db
from models import (
    Customer, Account, DC2SKPI, 
    QualitativeSignal, Product, CustomerConfig
)
from utils.config_loader import ConfigLoader  # NEW: Config-aware!
from sqlalchemy import text

# ============================================================================
# CONFIGURATION - UPDATE THIS FOR EACH CUSTOMER
# ============================================================================
CUSTOMER_ID = 9  # CHANGE THIS for each customer
CUSTOMER_NAME = "Customer 9"  # CHANGE THIS

# Data directory
DATA_DIR = Path(__file__).parent.parent / 'data'

# ============================================================================
# Helper Functions
# ============================================================================

def log(message, level="INFO"):
    """Log with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

def validate_csv(file_path, required_columns):
    """Validate CSV has required columns"""
    if not file_path.exists():
        log(f"❌ File not found: {file_path}", "ERROR")
        return False
    
    df = pd.read_csv(file_path, nrows=1)
    missing = [col for col in required_columns if col not in df.columns]
    
    if missing:
        log(f"❌ Missing columns in {file_path.name}: {missing}", "ERROR")
        return False
    
    return True

# ============================================================================
# Data Loading Functions (CONFIG-AWARE!)
# ============================================================================

def load_customers(csv_file):
    """Load customers from CSV"""
    log(f"Loading customers from {csv_file.name}...")
    
    if not csv_file.exists():
        log(f"⚠️  File not found: {csv_file}", "WARNING")
        return
    
    df = pd.read_csv(csv_file)
    
    for _, row in df.iterrows():
        customer = Customer.query.get(row['customer_id'])
        
        if not customer:
            customer = Customer(
                customer_id=row['customer_id'],
                customer_name=row['customer_name']
            )
            db.session.add(customer)
    
    db.session.commit()
    log(f"✅ Loaded {len(df)} customers")

def load_accounts(csv_file):
    """Load accounts from CSV"""
    log(f"Loading accounts from {csv_file.name}...")
    
    if not csv_file.exists():
        log(f"⚠️  File not found: {csv_file}", "WARNING")
        return
    
    df = pd.read_csv(csv_file)
    
    # Remove internal columns if present
    columns_to_drop = ['_scenario', '_scenario_key']
    for col in columns_to_drop:
        if col in df.columns:
            df = df.drop(columns=[col])
            log(f"   Removed column: {col}")
    
    for _, row in df.iterrows():
        account = Account.query.get(row['account_id'])
        
        if not account:
            account = Account(
                account_id=row['account_id'],
                customer_id=row['customer_id'],
                account_name=row['account_name'],
                industry=row.get('industry'),
                vertical=row.get('vertical', 'dc2_s'),
                region=row.get('region'),
                account_status=row.get('account_status', 'active')
            )
            
            # Handle profile_metadata if present
            if 'profile_metadata' in row and pd.notna(row['profile_metadata']):
                if isinstance(row['profile_metadata'], str):
                    try:
                        account.profile_metadata = json.loads(row['profile_metadata'])
                    except:
                        account.profile_metadata = {}
            
            db.session.add(account)
    
    db.session.commit()
    log(f"✅ Loaded {len(df)} accounts")

def load_kpi_measurements_config_aware(csv_file, customer_id):
    """
    V2 UPDATE: CONFIG-AWARE KPI LOADING
    
    Only loads KPIs that are enabled in CustomerConfig.
    Filters out disabled KPIs from CSV.
    
    This ensures:
    - Customers can't accidentally upload disabled KPIs
    - Database stays in sync with configuration
    - Consistent behavior across all upload paths
    """
    log(f"Loading KPI measurements (CONFIG-AWARE) from {csv_file.name}...")
    
    if not csv_file.exists():
        log(f"⚠️  File not found: {csv_file}", "WARNING")
        return {
            "total_in_csv": 0,
            "enabled_kpis": 0,
            "loaded": 0,
            "rejected": 0
        }
    
    # Read CSV
    df = pd.read_csv(csv_file)
    log(f"   Total records in CSV: {len(df)}")
    
    # Get enabled KPIs from CustomerConfig
    loader = ConfigLoader(customer_id)
    enabled_kpis = set(loader.get_enabled_kpis())
    
    log(f"   Enabled KPIs in config: {len(enabled_kpis)}")
    log(f"   Sample enabled: {list(enabled_kpis)[:5]}...")
    
    # Get KPIs in CSV
    csv_kpis = set(df['kpi_code'].unique())
    log(f"   Unique KPIs in CSV: {len(csv_kpis)}")
    
    # Filter to only enabled KPIs
    df_filtered = df[df['kpi_code'].isin(enabled_kpis)]
    
    rejected = len(df) - len(df_filtered)
    
    if rejected > 0:
        rejected_kpis = csv_kpis - enabled_kpis
        log(f"   ⚠️  FILTERED OUT {rejected} records with disabled KPIs", "WARNING")
        log(f"   Disabled KPIs in CSV: {rejected_kpis}", "WARNING")
        log(f"   These KPIs are not enabled in CustomerConfig", "WARNING")
    
    log(f"   Records to load: {len(df_filtered)}")
    
    # Load filtered records
    records_loaded = 0
    for _, row in df_filtered.iterrows():
        kpi = DC2SKPI(
            account_id=row['account_id'],
            kpi_code=row['kpi_code'],
            measured_at=pd.to_datetime(row['measured_at']),
            value=float(row['value']),
            target=float(row['target']),
            pillar=row['pillar']
        )
        db.session.add(kpi)
        records_loaded += 1
    
    db.session.commit()
    
    log(f"✅ Loaded {records_loaded} KPI measurements (config-aware)")
    
    return {
        "total_in_csv": len(df),
        "enabled_kpis": len(enabled_kpis),
        "csv_kpis": len(csv_kpis),
        "loaded": records_loaded,
        "rejected": rejected,
        "rejected_kpis": list(csv_kpis - enabled_kpis) if rejected > 0 else []
    }

def load_qualitative_signals(csv_file):
    """Load qualitative signals from CSV"""
    log(f"Loading qualitative signals from {csv_file.name}...")
    
    if not csv_file.exists():
        log(f"⚠️  File not found: {csv_file}", "WARNING")
        return
    
    df = pd.read_csv(csv_file)
    
    for _, row in df.iterrows():
        signal = QualitativeSignal(
            account_id=row['account_id'],
            signal_date=pd.to_datetime(row['signal_date']),
            signal_type=row.get('signal_type', 'health_check'),
            signal_text=row.get('signal_text', ''),
            sentiment=row.get('sentiment', 'neutral')
        )
        db.session.add(signal)
    
    db.session.commit()
    log(f"✅ Loaded {len(df)} qualitative signals")

def load_products(csv_file):
    """Load products from CSV"""
    log(f"Loading products from {csv_file.name}...")
    
    if not csv_file.exists():
        log(f"⚠️  File not found: {csv_file}", "WARNING")
        return
    
    df = pd.read_csv(csv_file)
    
    for _, row in df.iterrows():
        product = Product(
            customer_id=row['customer_id'],
            product_id=row.get('product_id'),
            product_name=row['product_name'],
            category=row.get('category', 'Infrastructure')
        )
        db.session.add(product)
    
    db.session.commit()
    log(f"✅ Loaded {len(df)} products")

# ============================================================================
# Delete Functions
# ============================================================================

def delete_existing_data(customer_id):
    """
    Delete all existing data for this customer
    Called before loading to ensure clean state
    """
    log(f"🗑️  Deleting existing data for customer {customer_id}...")
    
    # Get account IDs
    account_ids = [a.account_id for a in Account.query.filter_by(customer_id=customer_id).all()]
    
    if not account_ids:
        log("   No accounts found, nothing to delete")
        return
    
    # Delete in correct order (respect foreign keys)
    deleted = {}
    
    # 1. KPI measurements
    count = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).delete(synchronize_session=False)
    deleted['kpi_measurements'] = count
    log(f"   Deleted {count} KPI measurements")
    
    # 2. Qualitative signals
    count = QualitativeSignal.query.filter(QualitativeSignal.account_id.in_(account_ids)).delete(synchronize_session=False)
    deleted['signals'] = count
    log(f"   Deleted {count} qualitative signals")
    
    # 3. Products
    count = Product.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
    deleted['products'] = count
    log(f"   Deleted {count} products")
    
    # 4. Accounts
    count = Account.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
    deleted['accounts'] = count
    log(f"   Deleted {count} accounts")
    
    # Note: Don't delete Customer or CustomerConfig - preserve those
    
    db.session.commit()
    
    log(f"✅ Deletion complete: {deleted}")
    return deleted

# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main execution"""
    log("="*70)
    log(f"CONFIG-AWARE DATA LOADER V2 - Customer {CUSTOMER_ID}")
    log("="*70)
    log(f"Customer: {CUSTOMER_NAME}")
    log(f"Data directory: {DATA_DIR}")
    log("")
    
    # Verify data directory exists
    if not DATA_DIR.exists():
        log(f"❌ Data directory not found: {DATA_DIR}", "ERROR")
        return 1
    
    # List CSV files
    csv_files = list(DATA_DIR.glob('*.csv'))
    log(f"Found {len(csv_files)} CSV files:")
    for f in csv_files:
        log(f"  • {f.name}")
    log("")
    
    with app.app_context():
        try:
            # Start transaction
            log("Starting database transaction...")
            
            # Step 1: Delete existing data
            delete_existing_data(CUSTOMER_ID)
            log("")
            
            # Step 2: Load CSV files in correct order
            log("Loading CSV files...")
            log("")
            
            # Load customers
            customers_file = DATA_DIR / 'customers.csv'
            if customers_file.exists():
                load_customers(customers_file)
            
            # Load accounts
            accounts_file = DATA_DIR / 'accounts.csv'
            if accounts_file.exists():
                load_accounts(accounts_file)
            
            # Load KPI measurements (CONFIG-AWARE!)
            kpi_file = DATA_DIR / 'kpi_measurements.csv'
            if kpi_file.exists():
                kpi_result = load_kpi_measurements_config_aware(kpi_file, CUSTOMER_ID)
                
                # Show summary
                log("")
                log("📊 KPI Loading Summary:")
                log(f"   Total records in CSV: {kpi_result['total_in_csv']}")
                log(f"   Enabled KPIs: {kpi_result['enabled_kpis']}")
                log(f"   Records loaded: {kpi_result['loaded']}")
                log(f"   Records rejected: {kpi_result['rejected']}")
                
                if kpi_result['rejected'] > 0:
                    log(f"   ⚠️  Rejected KPIs: {kpi_result['rejected_kpis']}", "WARNING")
            
            # Load qualitative signals
            signals_file = DATA_DIR / 'qualitative_signals.csv'
            if signals_file.exists():
                load_qualitative_signals(signals_file)
            
            # Load products
            products_file = DATA_DIR / 'products.csv'
            if products_file.exists():
                load_products(products_file)
            
            # Commit transaction
            db.session.commit()
            
            log("")
            log("="*70)
            log("✅ DATA LOADING COMPLETE!")
            log("="*70)
            log("")
            log("Next steps:")
            log("  1. Verify data in database")
            log("  2. Calculate health scores")
            log("  3. Test dashboard")
            
            return 0
            
        except Exception as e:
            log(f"❌ Error during data loading: {e}", "ERROR")
            db.session.rollback()
            
            import traceback
            log(traceback.format_exc(), "ERROR")
            
            return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
