#!/usr/bin/env python3
"""
Wizard A - Milestone Generator (Enhanced)
=========================================

Enhanced version of generate_milestones_phase4.py with auto-discovery.
Discovers accounts automatically instead of hardcoded list.

Usage:
    python wizard_milestone_generator.py \
        --data-dir outputs/wizard_runs/run_001 \
        --output-dir outputs/wizard_runs/run_001/processed
"""

import sys
import os
import json
import csv
import argparse
from glob import glob
from pathlib import Path

# Import from your existing Phase 4 script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../scripts/phase4'))

try:
    from generate_milestones_phase4 import (
        extract_milestones_from_journey,
        MILESTONE_TYPES
    )
except ImportError as e:
    print(f"❌ Error importing generate_milestones_phase4.py")
    print(f"   Make sure the path is correct in sys.path.insert()")
    print(f"   Error: {e}")
    sys.exit(1)


def auto_discover_accounts(data_dir):
    """
    Auto-discover account IDs from journey files
    
    Args:
        data_dir: Directory containing journey files
    
    Returns:
        List of (account_id, journey_file_path) tuples
    """
    
    # Search for journey files
    journey_files = glob(os.path.join(data_dir, "account_*_journey.json"))
    
    # Also check subdirectories (phase1, phase2, etc.)
    for subdir in ['phase1', 'phase2', 'phase3']:
        subdir_path = os.path.join(data_dir, subdir)
        if os.path.exists(subdir_path):
            journey_files.extend(glob(os.path.join(subdir_path, "account_*_journey.json")))
    
    # Extract account IDs
    accounts = []
    for journey_file in journey_files:
        filename = os.path.basename(journey_file)
        account_id = filename.replace('account_', '').replace('_journey.json', '')
        accounts.append((account_id, journey_file))
    
    # Remove duplicates and sort
    accounts = sorted(set(accounts), key=lambda x: x[0])
    
    return accounts


def find_kpis_file(data_dir):
    """
    Find the KPI CSV file (all_accounts_kpis.csv)
    
    Args:
        data_dir: Base directory to search
    
    Returns:
        Path to KPI file or None
    """
    
    # Check current directory
    kpis_file = os.path.join(data_dir, 'all_accounts_kpis.csv')
    if os.path.exists(kpis_file):
        return kpis_file
    
    # Check phase3 subdirectory
    kpis_file = os.path.join(data_dir, 'phase3', 'all_accounts_kpis.csv')
    if os.path.exists(kpis_file):
        return kpis_file
    
    # Check parent directory
    parent_dir = os.path.dirname(data_dir)
    kpis_file = os.path.join(parent_dir, 'all_accounts_kpis.csv')
    if os.path.exists(kpis_file):
        return kpis_file
    
    return None


def generate_milestones_for_accounts(data_dir, output_dir, progress_callback=None):
    """
    Generate milestones for all discovered accounts
    
    Args:
        data_dir: Directory containing journey and KPI files
        output_dir: Output directory for milestone CSVs
        progress_callback: Optional function(current, total) for progress
    
    Returns:
        Number of accounts processed
    """
    
    print("="*70)
    print("WIZARD A - MILESTONE GENERATOR")
    print("="*70)
    print(f"Data: {data_dir}")
    print(f"Output: {output_dir}")
    print()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Auto-discover accounts
    print("🔍 Discovering accounts...")
    accounts = auto_discover_accounts(data_dir)
    
    if not accounts:
        print(f"❌ No journey files found in {data_dir}")
        print(f"   Looking for: account_*_journey.json")
        return 0
    
    print(f"✅ Found {len(accounts)} accounts")
    print()
    
    # Find KPI file
    print("🔍 Looking for KPI file...")
    kpis_file = find_kpis_file(data_dir)
    
    if not kpis_file:
        print(f"⚠️  Warning: KPI file not found!")
        print(f"   Looked in:")
        print(f"   - {data_dir}/all_accounts_kpis.csv")
        print(f"   - {data_dir}/phase3/all_accounts_kpis.csv")
        print(f"   Milestones will be generated without KPI context")
    else:
        print(f"✅ Found KPI file: {kpis_file}")
    print()
    
    # Generate milestones for each account
    all_milestones = []
    
    for idx, (account_id, journey_file) in enumerate(accounts):
        print(f"📍 [{idx+1:3d}/{len(accounts)}] Generating milestones for Account {account_id}...")
        
        # Load journey data
        with open(journey_file, 'r') as f:
            journey_data = json.load(f)
        
        # Extract milestones
        try:
            milestones = extract_milestones_from_journey(journey_data, kpis_file or '')
            print(f"   ✅ Generated {len(milestones)} milestones")
        except Exception as e:
            print(f"   ⚠️  Error extracting milestones: {e}")
            milestones = []
        
        # Save individual file
        if milestones:
            output_file = os.path.join(output_dir, f'account_{account_id}_milestones.csv')
            save_milestones_to_csv(milestones, output_file)
            print(f"   💾 Saved to {output_file}")
        
        # Add to combined list
        all_milestones.extend([{**m, 'account_id': account_id} for m in milestones])
        
        if progress_callback:
            progress_callback(idx + 1, len(accounts))
    
    # Save combined file
    print()
    print("💾 Saving combined milestones file...")
    
    combined_file = os.path.join(output_dir, 'all_accounts_milestones.csv')
    save_combined_milestones(all_milestones, combined_file)
    print(f"   ✅ Saved {combined_file} ({len(all_milestones)} total milestones)")
    
    # Statistics
    print()
    print("="*70)
    print("✅ MILESTONE GENERATION COMPLETE!")
    print("="*70)
    print(f"Accounts processed: {len(accounts)}")
    print(f"Total milestones: {len(all_milestones)}")
    print(f"Output directory: {output_dir}")
    print()
    
    if all_milestones:
        print("Milestone breakdown by type:")
        milestone_counts = {}
        for m in all_milestones:
            mtype = m.get('milestone_type', 'unknown')
            milestone_counts[mtype] = milestone_counts.get(mtype, 0) + 1
        
        for mtype, count in sorted(milestone_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {mtype:40s}: {count:3d}")
    
    print()
    
    return len(accounts)


def save_milestones_to_csv(milestones, output_file):
    """Save milestones to individual CSV file"""
    
    if not milestones:
        return
    
    fieldnames = [
        'week_number', 'milestone_date', 'milestone_type',
        'milestone_outcome', 'leading_indicators', 'arr_impact',
        'confidence_at_time', 'primary_drivers', 'signal_breakdown'
    ]
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(milestones)


def save_combined_milestones(milestones, output_file):
    """Save combined milestones to CSV"""
    
    if not milestones:
        print("   ⚠️  No milestones to save")
        return
    
    fieldnames = [
        'account_id', 'week_number', 'milestone_date', 'milestone_type',
        'milestone_outcome', 'leading_indicators', 'arr_impact',
        'confidence_at_time', 'primary_drivers', 'signal_breakdown'
    ]
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for milestone in milestones:
            # Ensure JSON fields are strings
            row = milestone.copy()
            for field in ['leading_indicators', 'primary_drivers', 'signal_breakdown']:
                if field in row and not isinstance(row[field], str):
                    row[field] = json.dumps(row[field])
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(
        description='Generate milestones for customer journeys (auto-discovery)'
    )
    parser.add_argument('--data-dir', required=True,
                       help='Directory containing journey and KPI files')
    parser.add_argument('--output-dir', required=True,
                       help='Directory for output milestone CSVs')
    
    args = parser.parse_args()
    
    # Validate data directory
    if not os.path.exists(args.data_dir):
        print(f"❌ Data directory not found: {args.data_dir}")
        sys.exit(1)
    
    # Generate milestones
    try:
        num_processed = generate_milestones_for_accounts(
            data_dir=args.data_dir,
            output_dir=args.output_dir
        )
        
        if num_processed == 0:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error during milestone generation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
