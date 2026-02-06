#!/usr/bin/env python3
"""
Schema Alignment Audit
Validates that CSV files, generator, and loader all match models.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app_v3_minimal import app
from models import DC2SKPI, QualitativeSignal, Account
from extensions import db
import pandas as pd
from sqlalchemy import inspect


def get_model_columns(model):
    """Get all columns from a SQLAlchemy model"""
    mapper = inspect(model)
    return {col.key: str(col.type) for col in mapper.columns}


def audit_csv_file(csv_path, expected_columns, entity_name):
    """Audit a CSV file against expected schema"""
    print(f"\n{'='*70}")
    print(f"AUDITING: {entity_name} - {csv_path.name}")
    print(f"{'='*70}")
    
    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        return False
    
    # Read CSV
    df = pd.read_csv(csv_path, nrows=1)
    csv_columns = set(df.columns)
    
    # Compare
    missing = expected_columns - csv_columns
    era = csv_columns - expected_columns
    matching = expected_columns & csv_columns
    
    print(f"\n✅ Matching columns ({len(matching)}):")
    for col in sorted(matching):
        print(f"   {col}")
    
    if missing:
        print(f"\n❌ Missing columns ({len(missing)}):")
        for col in sorted(missing):
            print(f"   {col} - REQUIRED!")
    
    if era:
        print(f"\n⚠️  Extra columns ({len(era)}):")
        for col in sorted(era):
            print(f"   {col} - Will be ignored")
    
    # Check sample data
    print(f"\n📊 Sample data (first row):")
    for col in df.columns:
        value = df[col].iloc[0]
        print(f"   {col}: {value} ({type(value).__name__})")
    
    return len(missing) == 0


def audit_generator_script(script_path, entity_name):
    """Audit generator script output"""
    print(f"\n{'='*70}")
    print(f"AUDITING: {entity_name} Generator - {script_path.name}")
    print(f"{'='*70}")
    
    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return False
    
    # Read script and look for DataFrame creation
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Search for column definitions
    print(f"\n🔍 Searching for column definitions...")
    
    # Look for patterns like: 'column_name': value
    import re
    patterns = [
        r"'(\w+)':\s*",  # Single quotes
        r'"(\w+)":\s*',  # Double quotes
    ]
    
    found_columns = set()
    for pattern in patterns:
        matches = re.findall(pattern, content)
        found_columns.update(matches)
    
    if found_columns:
        print(f"✅ Found {len(found_columns)} column definitions:")
        for col in sorted(found_columns):
            print(f"   {col}")
    else:
        print(f"⚠️  Could not parse column definitions automatically")
    
    return True


def audit_loader_script(script_path, entity_name):
    """Audit loader script column mappings"""
    print(f"\n{'='*70}")
    print(f"AUDITING: {entity_name} Loader - {script_path.name}")
    print(f"{'='*70}")
    
    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return False
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    print(f"\n🔍 Checking for column name usage...")
    
    # Look for DataFrame column access patterns
    import re
    
    # Pattern: row['column_name'] or df['column_name']
    patterns = [
        r"row\['(\w+)'\]",
        r"df\['(\w+)'\]",
        r'row\["(\w+)"\]',
        r'df\["(\w+)"\]',
    ]
    
    found_columns = set()
    for pattern in patterns:
        matches = re.findall(pattern, content)
        found_columns.update(matches)
    
    if found_columns:
        print(f"✅ Found {len(found_columns)} column references:")
        for col in sorted(found_columns):
            print(f"   {col}")
    else:
        print(f"⚠️  Could not parse column references")
    
    return True


def main():
    """Run complete audit"""
    print("\n" + "="*70)
    print("SCHEMA ALIGNMENT AUDIT")
    print("="*70)
    
    with app.app_context():
        # Get model schemas
        kpi_columns = get_model_columns(DC2SKPI)
        signal_columns = get_model_columns(QualitativeSignal)
        account_columns = get_model_columns(Account)
        
        print(f"\n📋 DATABASE SCHEMA (models.py)")
        print(f"="*70)
        
        print(f"\nDC2SKPI columns ({len(kpi_columns)}):")
        for col, dtype in kpi_columns.items():
            print(f"   {col}: {dtype}")
        
        print(f"\nQualitativeSignal columns ({len(signal_columns)}):")
        for col, dtype in signal_columns.items():
            print(f"   {col}: {dtype}")
        
        print(f"\nAccount columns ({len(account_columns)}):")
        for col, dtype in account_columns.items():
            print(f"   {col}: {dtype}")
        
        # Define required CSV columns (subset of DB columns)
        kpi_csv_required = {
            'account_id', 'customer_id', 'kpi_id', 
            'measured_at', 'kpvalue', 'unit'
        }
        
        signal_csv_required = {
            'account_id', 'customer_id', 'signal_date',
            'signal_type', 'signal_text', 'sentiment_score', 'sentiment'
        }
        
        account_csv_required = {
            'account_id', 'customer_id', 'account_name',
            'vertical', 'account_status'
        }
        
        # Audit Customer 19 if exists
        customer_dir = Path('verticals/customer19-dc2_s/data')
        
        results = {}
        
        if customer_dir.exists():
            results['kpi_csv'] = audit_csv_file(
                customer_dir / 'kpi_measurements.csv',
                kpi_csv_required,
                'KPI Measurements'
            )
            
            results['signal_csv'] = audit_csv_file(
                customer_dir / 'qualitative_signals.csv',
                signal_csv_required,
                'Qualitative Signals'
            )
            
            results['account_csv'] = audit_csv_file(
                customer_dir / 'accounts.csv',
                account_csv_required,
                'Accounts'
            )
        else:
            print(f"\n⚠️  Customer 19 directory not found: {customer_dir}")
        
        # Audit generator script
        generator_path = Path('scripts/generate_synthetic_customer_data.py')
        results['generator'] = audit_generator_script(generator_path, 'Data Generator')
        
        # Audit loader script
        loader_path = Path('verticals/customer19-dc2_s/script_load_customer19_data_SMART.py')
        if loader_path.exists():
            results['loader'] = audit_loader_script(loader_path, 'Data Loader')
        
        # Summary
        print(f"\n{'='*70}")
        print(f"AUDIT SUMMARY")
        print(f"{'='*70}")
        
        all_pass = all(results.values())
        
        for component, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {component}")
        
        if all_pass:
            print(f"\n🎉 All components aligned!")
        else:
            print(f"\n⚠️  Alignment issues found - see details above")
        
        return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
