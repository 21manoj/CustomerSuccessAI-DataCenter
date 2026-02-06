#!/usr/bin/env python3
"""
Migration Script: Update Customer Loaders to Config-Aware
==========================================================

This script updates all existing customer loader scripts to use
the new config-aware version that respects CustomerConfig.

What it does:
1. Finds all existing 02_load_customer*_data_SMART.py files
2. Backs up original files
3. Creates new config-aware versions
4. Updates customer-specific settings

Usage:
    python3 migrate_loaders_to_config_aware.py [--dry-run] [--customer-id ID]
    
Options:
    --dry-run: Show what would be updated without making changes
    --customer-id ID: Only update specific customer (default: all)
"""

import sys
import os
from pathlib import Path
import shutil
from datetime import datetime
import argparse

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def find_customer_loaders():
    """Find all existing customer loader scripts"""
    
    verticals_dir = backend_dir / 'verticals'
    
    if not verticals_dir.exists():
        print(f"❌ Verticals directory not found: {verticals_dir}")
        return []
    
    loaders = []
    
    # Find all customer directories
    for customer_dir in verticals_dir.glob('customer*-dc2_s'):
        scripts_dir = customer_dir / 'scripts'
        
        if not scripts_dir.exists():
            continue
        
        # Find loader script
        loader_files = list(scripts_dir.glob('02_load_customer*_data_SMART.py'))
        
        for loader_file in loader_files:
            # Extract customer ID from filename
            import re
            match = re.search(r'customer(\d+)', loader_file.name)
            if match:
                customer_id = int(match.group(1))
                loaders.append({
                    'customer_id': customer_id,
                    'file': loader_file,
                    'customer_dir': customer_dir
                })
    
    return loaders

def backup_file(file_path):
    """Create backup of original file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = file_path.parent / f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    print(f"  📦 Backed up: {backup_path.name}")
    return backup_path

def create_config_aware_loader(customer_id, output_file, template_file):
    """Create config-aware loader from template"""
    
    # Read template
    with open(template_file, 'r') as f:
        content = f.read()
    
    # Update customer ID
    content = content.replace('CUSTOMER_ID = 9', f'CUSTOMER_ID = {customer_id}')
    content = content.replace('CUSTOMER_NAME = "Customer 9"', f'CUSTOMER_NAME = "Customer {customer_id}"')
    
    # Write new file
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"  ✅ Created config-aware version: {output_file.name}")

def migrate_loader(loader_info, template_file, dry_run=False):
    """Migrate a single loader to config-aware version"""
    
    customer_id = loader_info['customer_id']
    current_file = loader_info['file']
    
    print(f"\n{'='*70}")
    print(f"Customer {customer_id}: {current_file.name}")
    print(f"{'='*70}")
    
    if dry_run:
        print(f"  [DRY RUN] Would backup: {current_file}")
        print(f"  [DRY RUN] Would create config-aware version")
        return
    
    # Backup original
    backup_path = backup_file(current_file)
    
    # Create new config-aware version
    create_config_aware_loader(customer_id, current_file, template_file)
    
    print(f"  ✅ Migration complete for customer {customer_id}")

def main():
    parser = argparse.ArgumentParser(
        description='Migrate customer loaders to config-aware version'
    )
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')
    parser.add_argument('--customer-id', type=int, help='Only migrate specific customer')
    parser.add_argument('--template', help='Path to template file', 
                       default='02_load_customer_data_SMART_V2_CONFIG_AWARE.py')
    
    args = parser.parse_args()
    
    print("="*70)
    print("MIGRATE CUSTOMER LOADERS TO CONFIG-AWARE")
    print("="*70)
    print()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()
    
    # Find template
    template_file = Path(args.template)
    if not template_file.exists():
        # Try in backend/scripts
        template_file = backend_dir / 'scripts' / args.template
    
    if not template_file.exists():
        print(f"❌ Template file not found: {args.template}")
        print(f"   Looked in:")
        print(f"   - {Path(args.template).absolute()}")
        print(f"   - {backend_dir / 'scripts' / args.template}")
        return 1
    
    print(f"✅ Using template: {template_file}")
    print()
    
    # Find all loaders
    loaders = find_customer_loaders()
    
    if not loaders:
        print("❌ No customer loaders found")
        return 1
    
    print(f"Found {len(loaders)} customer loaders:")
    for loader in loaders:
        print(f"  • Customer {loader['customer_id']}: {loader['file']}")
    print()
    
    # Filter if specific customer requested
    if args.customer_id:
        loaders = [l for l in loaders if l['customer_id'] == args.customer_id]
        if not loaders:
            print(f"❌ No loader found for customer {args.customer_id}")
            return 1
        print(f"Filtering to customer {args.customer_id} only")
        print()
    
    # Confirm
    if not args.dry_run:
        response = input(f"Proceed with migrating {len(loaders)} loaders? [y/N]: ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return 0
        print()
    
    # Migrate each loader
    migrated = 0
    failed = 0
    
    for loader in loaders:
        try:
            migrate_loader(loader, template_file, args.dry_run)
            migrated += 1
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            failed += 1
    
    # Summary
    print()
    print("="*70)
    print("MIGRATION SUMMARY")
    print("="*70)
    print(f"Total loaders: {len(loaders)}")
    print(f"Migrated: {migrated} ✅")
    print(f"Failed: {failed} ❌")
    print()
    
    if not args.dry_run and migrated > 0:
        print("Next steps:")
        print("  1. Test each migrated loader:")
        print("     python3 verticals/customer{ID}-dc2_s/scripts/02_load_customer{ID}_data_SMART.py")
        print()
        print("  2. Verify config-aware filtering works:")
        print("     - Check logs for 'CONFIG-AWARE' messages")
        print("     - Verify disabled KPIs are filtered")
        print()
        print("  3. Original files backed up with _backup_{timestamp} suffix")
        print("     - Can restore if needed")
    
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
