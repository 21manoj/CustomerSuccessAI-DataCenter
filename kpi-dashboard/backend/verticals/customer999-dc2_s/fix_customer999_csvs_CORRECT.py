#!/usr/bin/env python3
"""
Fix Customer 99999 CSV files to match production schema
Handles TEXT IDs and DATE formats correctly
"""

import pandas as pd
import os
import shutil
from datetime import datetime

DATA_DIR = './data'
BACKUP_DIR = './data/backup_' + datetime.now().strftime('%Y%m%d_%H%M%S')

print("=" * 80)
print("CUSTOMER 999 CSV FIXER - Production Safe (TEXT IDs + Dates)")
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
# FIX 1: kpi_definitions - Fix column names
# ============================================================================
def fix_kpi_definitions(filepath):
    """Fix column naming to match production schema"""
    print(f"   Fixing column names...")
    
    df = pd.read_csv(filepath)
    
    # Column renames to match production
    renames = {
        'range_critical_min': 'state_critical_min',
        'range_critical_max': 'state_critical_max',
        'range_atrisk_min': 'state_at_risk_min',      # Note: at_risk with underscore
        'range_atrisk_max': 'state_at_risk_max',
        'range_healthy_min': 'state_healthy_min',
        'range_healthy_max': 'state_healthy_max',
        'range_optimal_min': 'state_optimal_min',
        'range_optimal_max': 'state_optimal_max',
    }
    
    # Only rename columns that exist
    renames = {k: v for k, v in renames.items() if k in df.columns}
    
    if renames:
        df.rename(columns=renames, inplace=True)
        print(f"   Renamed {len(renames)} columns")
    
    df.to_csv(filepath, index=False)

# ============================================================================
# FIX 2: kpi_measurements - Fix date format AND keep TEXT IDs
# ============================================================================
def fix_kpi_measurements(filepath):
    """Fix measurement_month from 'YYYY-MM' to 'YYYY-MM-01' DATE format"""
    print(f"   Fixing measurement_month date format...")
    
    df = pd.read_csv(filepath)
    
    # Keep measurement_id as TEXT (production expects it)
    # Just fix the date format
    if 'measurement_month' in df.columns:
        # Convert 'YYYY-MM' to 'YYYY-MM-01'
        df['measurement_month'] = pd.to_datetime(df['measurement_month'], format='%Y-%m').dt.strftime('%Y-%m-%d')
        print(f"   Fixed {len(df)} date values")
    
    df.to_csv(filepath, index=False)
    print(f"   Kept {len(df)} rows, {len(df.columns)} columns")

# ============================================================================
# FIX 3: account_health_history - Fix date format
# ============================================================================
def fix_account_health_history(filepath):
    """Fix month from 'YYYY-MM' to 'YYYY-MM-01' DATE format"""
    print(f"   Fixing month date format...")
    
    df = pd.read_csv(filepath)
    
    if 'month' in df.columns:
        # Convert 'YYYY-MM' to 'YYYY-MM-01'
        df['month'] = pd.to_datetime(df['month'], format='%Y-%m').dt.strftime('%Y-%m-%d')
        print(f"   Fixed {len(df)} date values")
    
    df.to_csv(filepath, index=False)

# ============================================================================
# FIX 4: expansion_readiness_scores - Fix date format
# ============================================================================
def fix_expansion_readiness_scores(filepath):
    """Fix month from 'YYYY-MM' to 'YYYY-MM-01' DATE format"""
    print(f"   Fixing month date format...")
    
    df = pd.read_csv(filepath)
    
    if 'month' in df.columns:
        # Convert 'YYYY-MM' to 'YYYY-MM-01'
        df['month'] = pd.to_datetime(df['month'], format='%Y-%m').dt.strftime('%Y-%m-%d')
        print(f"   Fixed {len(df)} date values")
    
    df.to_csv(filepath, index=False)

# ============================================================================
# FIX 5: playbook_executions - Keep TEXT IDs (no changes needed)
# ============================================================================
def fix_playbook_executions(filepath):
    """Verify playbook_executions format (should be fine as-is)"""
    print(f"   Checking playbook_executions...")
    
    df = pd.read_csv(filepath)
    
    # execution_id should be TEXT - keep it as-is
    # execution_date should already be proper date format
    
    print(f"   File looks good: {len(df)} rows, {len(df.columns)} columns")
    # Don't need to save, just verify

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
    print("Next steps:")
    print("  1. Run: python3 scripts/02_load_customer99999_data.py")
    print("  2. Should now load all 12 tables successfully")
    print()
    print("Key fixes applied:")
    print("  ✅ kpi_definitions: Fixed column names (range_* → state_*)")
    print("  ✅ kpi_measurements: Fixed dates (YYYY-MM → YYYY-MM-01)")
    print("  ✅ account_health_history: Fixed dates")
    print("  ✅ expansion_readiness_scores: Fixed dates")
    print("  ✅ TEXT IDs preserved (production expects them)")
else:
    print("⚠️  Some files failed to fix - check errors above")
    print(f"   Original files backed up to: {BACKUP_DIR}")

print()
