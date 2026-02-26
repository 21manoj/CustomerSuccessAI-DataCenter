#!/usr/bin/env python3
"""
Wizard A - KPI Generator Wrapper
=================================

Wraps kpi_generator_phase3.py to process multiple accounts.
Your original script stays unchanged!

Usage:
    python wizard_kpi_generator.py \
        --input-dir outputs/wizard_runs/run_001 \
        --output-dir outputs/wizard_runs/run_001
"""

import sys
import os
import json
import csv
import argparse
from glob import glob
from pathlib import Path
from datetime import datetime

# Import from your existing Phase 3 script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../scripts/phase3'))

try:
    from kpi_generator_phase3 import (
        add_kpis_to_journey,
        KPI_DEFINITIONS
    )
except ImportError as e:
    print(f"❌ Error importing kpi_generator_phase3.py")
    print(f"   Make sure the path is correct in sys.path.insert()")
    print(f"   Error: {e}")
    sys.exit(1)


def process_journey_files(input_dir, output_dir, progress_callback=None):
    """
    Process all journey JSON files and generate KPIs
    
    Args:
        input_dir: Directory containing account_*_journey.json files
        output_dir: Directory to save KPI CSVs
        progress_callback: Optional function(current, total) for progress
    
    Returns:
        Number of files processed
    """
    
    print("="*70)
    print("WIZARD A - KPI GENERATOR")
    print("="*70)
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all journey files
    journey_files = sorted(glob(os.path.join(input_dir, "account_*_journey.json")))
    
    if not journey_files:
        print(f"❌ No journey files found in {input_dir}")
        print(f"   Looking for: account_*_journey.json")
        return 0
    
    print(f"📁 Found {len(journey_files)} journey files")
    print()
    
    # Process each journey
    all_kpis = []
    
    for idx, journey_file in enumerate(journey_files):
        # Extract account ID from filename
        filename = os.path.basename(journey_file)
        account_id = filename.replace('account_', '').replace('_journey.json', '')
        
        # Load journey data
        with open(journey_file, 'r') as f:
            journey_data = json.load(f)
        
        # Add KPIs using your existing function
        journey_with_kpis = add_kpis_to_journey(journey_data)
        
        # Extract KPI data
        kpis = journey_with_kpis.get('kpis', [])
        
        # Save individual account KPI file
        output_file = os.path.join(output_dir, f"account_{account_id}_kpis.csv")
        save_kpis_to_csv(kpis, output_file)
        
        # Collect for combined file
        all_kpis.extend(kpis)
        
        # Progress update
        print(f"✅ [{idx+1:3d}/{len(journey_files)}] Account {account_id} - "
              f"Generated {len(kpis)} KPI records ({len(kpis)//52 if kpis else 0} KPIs × {52 if kpis else 0} weeks)")
        
        if progress_callback:
            progress_callback(idx + 1, len(journey_files))
    
    # Save combined KPI file
    print()
    print("💾 Saving combined KPI file...")
    combined_file = os.path.join(output_dir, "all_accounts_kpis.csv")
    save_kpis_to_csv(all_kpis, combined_file)
    print(f"   ✅ Saved {combined_file} ({len(all_kpis)} total records)")
    
    # Save metadata
    metadata_file = os.path.join(output_dir, "kpi_metadata.json")
    save_kpi_metadata(len(journey_files), len(all_kpis), metadata_file)
    print(f"   ✅ Saved {metadata_file}")
    
    print()
    print("="*70)
    print("✅ KPI GENERATION COMPLETE!")
    print("="*70)
    print(f"Accounts processed: {len(journey_files)}")
    print(f"Total KPI records: {len(all_kpis)}")
    print(f"KPIs per week: 35")
    print(f"Weeks per account: {len(all_kpis) // len(journey_files) // 35 if journey_files else 0}")
    print()
    
    return len(journey_files)


def save_kpis_to_csv(kpis, output_file):
    """Save KPI data to CSV file"""
    
    if not kpis:
        print(f"⚠️  No KPIs to save")
        return
    
    # Get all unique fieldnames from KPIs
    fieldnames = set()
    for kpi in kpis:
        fieldnames.update(kpi.keys())
    
    fieldnames = sorted(fieldnames)
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kpis)


def save_kpi_metadata(num_accounts, num_records, output_file):
    """Save KPI metadata"""
    
    metadata = {
        'generator_version': '3.0',
        'generation_date': str(datetime.now()),
        'num_accounts': num_accounts,
        'num_kpi_records': num_records,
        'kpis_per_week': 35,
        'kpi_categories': {
            'Performance & Utilization': 8,
            'Cost Efficiency': 7,
            'Scalability & Growth': 7,
            'Support & Reliability': 6,
            'Business Value': 7
        },
        'kpi_definitions': {
            kpi_id: {
                'name': defn.name,
                'category': defn.category.value,
                'unit': defn.unit,
                'good_range': defn.good_range,
                'bad_range': defn.bad_range,
                'inverse': defn.inverse
            }
            for kpi_id, defn in KPI_DEFINITIONS.items()
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Generate KPIs for multiple customer journey accounts'
    )
    parser.add_argument('--input-dir', required=True,
                       help='Directory containing account_*_journey.json files')
    parser.add_argument('--output-dir', required=True,
                       help='Directory for output KPI CSV files')
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.exists(args.input_dir):
        print(f"❌ Input directory not found: {args.input_dir}")
        sys.exit(1)
    
    # Process files
    try:
        from datetime import datetime
        num_processed = process_journey_files(
            input_dir=args.input_dir,
            output_dir=args.output_dir
        )
        
        if num_processed == 0:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error during KPI generation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
