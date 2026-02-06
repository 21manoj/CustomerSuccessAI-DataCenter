#!/usr/bin/env python3
"""
Fix Customer 33 CSV files to match ACTUAL production schema
Smart date handling - only converts if needed
"""

import pandas as pd
import os
import shutil
from datetime import datetime

DATA_DIR = './data'
BACKUP_DIR = './data/backup_' + datetime.now().strftime('%Y%m%d_%H%M%S')

print("=" * 80)
print("CUSTOMER 33 CSV FIXER - FINAL (Smart Date Handling)")
print("=" * 80)
print()

# Create backup directory
os.makedirs(BACKUP_DIR, exist_ok=True)
print(f"📁 Backup directory: {BACKUP_DIR}")
print()

def backup_and_fix_file(filename, fix_function):
    """Backup original file and apply fix"""
    filepath = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f"⚠️  {filename} not found - skipping")
        return False
    
    # Backup
    backup_path = os.path.join(BACKUP_DIR, filename)
    shutil.copy2(filepath, backup_path)
    print(f"💾 Backed up: {filename}")
    
    # Fix
    try:
        fix_function(filepath)
        print(f"✅ Fixed: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")
        # Restore from backup
        shutil.copy2(backup_path, filepath)
        print(f"🔄 Restored from backup")
        return False

# ============================================================================
# FIX 1: kpi_definitions - Match the MIXED schema naming
# ============================================================================
def fix_kpi_definitions(filepath):
    """Fix column naming to match production's MIXED schema AND handle non-numeric values"""
    print(f"   Fixing column names to match MIXED schema...")
    
    df = pd.read_csv(filepath)
    
    # Production schema uses:
    # - range_optimal_min/max
    # - range_healthy_min/max
    # - state_at_risk_min/max  (ONLY this one uses "state_")
    # - range_critical_min/max
    
    renames = {
        # From current CSV → To production schema
        'range_critical_min': 'range_critical_min',      # Already correct
        'range_critical_max': 'range_critical_max',      # Already correct
        'range_atrisk_min': 'state_at_risk_min',         # Fix: add underscore + state prefix
        'range_atrisk_max': 'state_at_risk_max',         # Fix: add underscore + state prefix
        'range_healthy_min': 'range_healthy_min',        # Already correct
        'range_healthy_max': 'range_healthy_max',        # Already correct
        'range_optimal_min': 'range_optimal_min',        # Already correct
        'range_optimal_max': 'range_optimal_max',        # Already correct
        
        # Handle if CSV already has state_* (from previous fix attempts)
        'state_critical_min': 'range_critical_min',
        'state_critical_max': 'range_critical_max',
        'state_at_risk_min': 'state_at_risk_min',        # Keep as-is
        'state_at_risk_max': 'state_at_risk_max',        # Keep as-is
        'state_healthy_min': 'range_healthy_min',
        'state_healthy_max': 'range_healthy_max',
        'state_optimal_min': 'range_optimal_min',
        'state_optimal_max': 'range_optimal_max',
    }
    
    # Only rename columns that exist
    renames = {k: v for k, v in renames.items() if k in df.columns}
    
    if renames:
        df.rename(columns=renames, inplace=True)
        print(f"   Renamed {len(renames)} columns")
        print(f"   Schema expects: range_optimal, range_healthy, STATE_at_risk, range_critical")
    
    # Clean ALL numeric columns - they all expect NUMERIC type in schema
    numeric_columns = [
        'target_value', 'range_min', 'range_max',
        'range_optimal_min', 'range_optimal_max',
        'range_healthy_min', 'range_healthy_max',
        'state_at_risk_min', 'state_at_risk_max',
        'range_critical_min', 'range_critical_max',
        'pillar_weight', 'kpi_weight_in_pillar',
        'predictive_horizon_days', 'confidence_level',
        'priority_normal', 'priority_at_risk', 'priority_expansion', 'priority_churn_prevention'
    ]
    
    print(f"   Cleaning numeric columns (converting text to NULL)...")
    cleaned_count = 0
    for col in numeric_columns:
        if col in df.columns:
            # Convert to string first
            df[col] = df[col].astype(str)
            # Replace text values with empty string (becomes NULL in DB)
            df[col] = df[col].replace(['Baseline', 'N/A', 'n/a', 'NA', 'na', 'nan', 'None'], '')
            # Also handle "Baseline + X%" patterns
            df[col] = df[col].str.replace(r'Baseline.*', '', regex=True)
            # Convert to numeric, errors become NaN (which writes as NULL)
            df[col] = pd.to_numeric(df[col], errors='coerce')
            cleaned_count += 1
    
    print(f"   Cleaned {cleaned_count} numeric columns (text values → NULL)")
    
    # Also need to remove columns that don't exist in schema
    schema_columns = [
        'kpi_code', 'kpi_name', 'pillar', 'pillar_weight', 'kpi_weight_in_pillar',
        'indicator_type', 'predictive_horizon_days', 'confidence_level', 'direction',
        'source_review', 'data_source_system', 'data_collection_method', 'impact_level',
        'measurement_frequency', 'range_type', 'range_min', 'range_max', 'target_value',
        'target_operator', 'unit', 'range_optimal_min', 'range_optimal_max',
        'range_healthy_min', 'range_healthy_max', 'state_at_risk_min', 'state_at_risk_max',
        'range_critical_min', 'range_critical_max', 'priority_normal', 'priority_at_risk',
        'priority_expansion', 'priority_churn_prevention', 'causal_kpis', 'correlated_kpis',
        'triggered_playbooks', 'business_impact', 'notes', 'active'
    ]
    
    # Find columns to drop
    extra_columns = [col for col in df.columns if col not in schema_columns]
    if extra_columns:
        print(f"   Dropping {len(extra_columns)} columns not in schema: {extra_columns[:3]}...")
        df = df[[col for col in df.columns if col in schema_columns]]
    
    df.to_csv(filepath, index=False)

# ============================================================================
# FIX 2: kpi_measurements - Fix date format AND clean target_value
# ============================================================================
def fix_kpi_measurements(filepath):
    """Fix measurement_month date format if needed AND clean target_value"""
    print(f"   Checking measurement_month date format...")
    
    df = pd.read_csv(filepath)
    
    if 'measurement_month' in df.columns:
        # Check a sample value to see what format it's in
        sample = str(df['measurement_month'].iloc[0])
        
        if len(sample) == 7:  # Format: YYYY-MM
            print(f"   Converting YYYY-MM → YYYY-MM-01...")
            df['measurement_month'] = pd.to_datetime(df['measurement_month'], format='%Y-%m').dt.strftime('%Y-%m-%d')
            print(f"   Fixed {len(df)} date values")
        elif len(sample) == 10:  # Format: YYYY-MM-DD
            print(f"   ✓ Already in YYYY-MM-DD format (no change needed)")
        else:
            print(f"   ⚠️  Unexpected date format: {sample}")
    
    # Clean target_value - schema expects NUMERIC but CSV may have "Baseline"
    if 'target_value' in df.columns:
        print(f"   Cleaning target_value column (converting text to NULL)...")
        # Convert to string first
        df['target_value'] = df['target_value'].astype(str)
        # Replace text values with empty string (becomes NULL in DB)
        df['target_value'] = df['target_value'].replace(['Baseline', 'N/A', 'n/a', 'NA', 'na', 'nan', 'None'], '')
        # Also handle "Baseline + X%" patterns
        df['target_value'] = df['target_value'].str.replace(r'Baseline.*', '', regex=True)
        # Convert to numeric, errors become NaN (which writes as NULL)
        df['target_value'] = pd.to_numeric(df['target_value'], errors='coerce')
        print(f"   Cleaned target_value (text values → NULL)")
    
    df.to_csv(filepath, index=False)
    print(f"   Kept {len(df)} rows, {len(df.columns)} columns")

# ============================================================================
# FIX 3: account_health_history - Fix date format (smart - only if needed)
# ============================================================================
def fix_account_health_history(filepath):
    """Fix month date format if needed"""
    print(f"   Checking month date format...")
    
    df = pd.read_csv(filepath)
    
    if 'month' in df.columns:
        # Check a sample value to see what format it's in
        sample = str(df['month'].iloc[0])
        
        if len(sample) == 7:  # Format: YYYY-MM
            print(f"   Converting YYYY-MM → YYYY-MM-01...")
            df['month'] = pd.to_datetime(df['month'], format='%Y-%m').dt.strftime('%Y-%m-%d')
            print(f"   Fixed {len(df)} date values")
        elif len(sample) == 10:  # Format: YYYY-MM-DD
            print(f"   ✓ Already in YYYY-MM-DD format (no change needed)")
        else:
            print(f"   ⚠️  Unexpected date format: {sample}")
    
    df.to_csv(filepath, index=False)

# ============================================================================
# FIX 4: expansion_readiness_scores - Fix date format (smart - only if needed)
# ============================================================================
def fix_expansion_readiness_scores(filepath):
    """Fix month date format if needed"""
    print(f"   Checking month date format...")
    
    df = pd.read_csv(filepath)
    
    if 'month' in df.columns:
        # Check a sample value to see what format it's in
        sample = str(df['month'].iloc[0])
        
        if len(sample) == 7:  # Format: YYYY-MM
            print(f"   Converting YYYY-MM → YYYY-MM-01...")
            df['month'] = pd.to_datetime(df['month'], format='%Y-%m').dt.strftime('%Y-%m-%d')
            print(f"   Fixed {len(df)} date values")
        elif len(sample) == 10:  # Format: YYYY-MM-DD
            print(f"   ✓ Already in YYYY-MM-DD format (no change needed)")
        else:
            print(f"   ⚠️  Unexpected date format: {sample}")
    
    df.to_csv(filepath, index=False)

# ============================================================================
# FIX 5: playbook_executions - Clean trigger_value (remove % signs, $ signs, etc)
# ============================================================================
def fix_playbook_executions(filepath):
    """Clean trigger_value - schema expects NUMERIC but CSV has text like '2.8%'"""
    print(f"   Cleaning trigger_value column...")
    
    df = pd.read_csv(filepath)
    
    if 'trigger_value' in df.columns:
        # Remove % signs, $ signs, commas, and other non-numeric characters
        # Keep only numbers and decimal points
        df['trigger_value'] = df['trigger_value'].astype(str).str.replace(r'[^\d.]', '', regex=True)
        
        # Convert to numeric, set errors to NaN
        df['trigger_value'] = pd.to_numeric(df['trigger_value'], errors='coerce')
        
        print(f"   Cleaned {len(df)} trigger_value entries")
    
    df.to_csv(filepath, index=False)

# ============================================================================
# MAIN EXECUTION
# ============================================================================
print("🔧 Fixing CSV files...")
print()

fixes = [
    ('kpi_definitions_complete_33_corrected.csv', fix_kpi_definitions),
    ('kpi_measurements.csv', fix_kpi_measurements),
    ('account_health_history.csv', fix_account_health_history),
    ('expansion_readiness_scores.csv', fix_expansion_readiness_scores),
    ('playbook_executions.csv', fix_playbook_executions),
]

success_count = 0
for filename, fix_func in fixes:
    if backup_and_fix_file(filename, fix_func):
        success_count += 1
    print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"✅ Fixed: {success_count}/{len(fixes)} files")
print(f"💾 Backups: {BACKUP_DIR}")
print()

if success_count == len(fixes):
    print("🎉 All CSV files fixed successfully!")
    print()
    print("Key fixes applied:")
    print("  ✅ kpi_definitions: Matched MIXED schema + cleaned ALL numeric columns")
    print("     - range_optimal_min/max")
    print("     - range_healthy_min/max") 
    print("     - state_at_risk_min/max  ← ONLY these use 'state_'")
    print("     - range_critical_min/max")
    print("     - 'Baseline', 'Baseline + 30%' → NULL in all numeric columns")
    print("  ✅ kpi_measurements: Dates checked/fixed + cleaned target_value")
    print("  ✅ account_health_history: Dates checked/fixed")
    print("  ✅ expansion_readiness_scores: Dates checked/fixed")
    print("  ✅ playbook_executions: Cleaned trigger_value (2.8% → 2.8)")
    print()
    print("Next steps:")
    print("  1. Run: python3 scripts/02_load_customer33_data.py")
    print("  2. Should now load all 12 tables successfully!")
    print()
else:
    print("⚠️  Some files failed to fix - check errors above")
    print(f"   Original files backed up to: {BACKUP_DIR}")

print()
