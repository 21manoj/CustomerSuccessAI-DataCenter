#!/usr/bin/env python3
"""Placeholder synthetic data generator - Generates ALL KPIs"""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app_v3_minimal import app
from verticals.dc2_s.vertical_loader import DC2SVertical
from id_generator import generate_customer_id, generate_account_id
import pandas as pd
from datetime import datetime, timedelta
import random

parser = argparse.ArgumentParser()
parser.add_argument('--customer-id', type=int, required=True)
parser.add_argument('--months', type=int, default=12)
parser.add_argument('--accounts', type=str, help='Account IDs (comma-separated) - will use these if provided')
args = parser.parse_args()

customer_id = args.customer_id
customer_dir = Path(f'verticals/customer{customer_id}-dc2_s')
data_dir = customer_dir / 'data'
data_dir.mkdir(parents=True, exist_ok=True)

print(f"Generating synthetic data for customer {customer_id}...")
print("NOTE: Generating ALL KPIs (not just enabled) to test filtering")

with app.app_context():
    # Get ALL KPIs from vertical (not just enabled)
    vertical = DC2SVertical()
    all_kpis = vertical.kpis  # ALL 38 KPIs
    
    print(f"Total KPIs available: {len(all_kpis)}")
    print(f"Generating CSV with ALL {len(all_kpis)} KPIs...")
    
    # Generate data
    accounts = []
    if args.accounts:
        # Use provided account IDs
        account_ids = [int(a.strip()) for a in args.accounts.split(',')]
        for i, account_id in enumerate(account_ids):
            accounts.append({
                'account_id': account_id,
                'customer_id': customer_id,
                'account_name': f'Account-{i+1}',
                'industry': 'Technology',
                'vertical': 'dc2_s',
                'region': 'us-west-2',
                'account_status': 'active'
            })
    else:
        # Default: create 3 accounts with prefixed UUID v7
        for i in range(3):
            accounts.append({
                'account_id': i + 1,  # Auto-increment placeholder; DB assigns actual ID
                'customer_id': customer_id,
                'account_name': f'Account-{i+1}',
                'industry': 'Technology',
                'vertical': 'dc2_s',
                'region': 'us-west-2',
                'account_status': 'active',
                'uuid': generate_account_id('dc')  # Prefixed UUID v7 (e.g. dc_acct_019...)
            })
    
    # Map P1-P5 codes to AI/CH/DV/EX/OS format for config compatibility
    pillar_code_map = {'P1': 'DV', 'P2': 'OS', 'P3': 'AI', 'P4': 'CH', 'P5': 'EX'}
    
    kpis = []
    start_date = datetime(2024, 1, 1)
    for account in accounts:
        for month in range(args.months):
            measured_at = start_date + timedelta(days=30 * month)
            # Generate ALL KPIs (not just enabled)
            for kpi in all_kpis:
                original_code = kpi['code']  # e.g., P1-KPI1
                
                # Convert to config format: P1-KPI1 -> DV-KPI1, P3-KPI1 -> AI-KPI1
                if '-' in original_code:
                    pillar_prefix, kpi_suffix = original_code.split('-', 1)
                    if pillar_prefix in pillar_code_map:
                        kpi_code = f"{pillar_code_map[pillar_prefix]}-{kpi_suffix}"
                    else:
                        kpi_code = original_code
                else:
                    kpi_code = original_code
                
                # Handle target - could be dict or value
                target_value = kpi.get('target', {})
                if isinstance(target_value, dict):
                    target_value = target_value.get('value', 85.0)
                elif target_value is None:
                    target_value = 85.0
                
                # Get pillar (already mapped by vertical_loader: DV, OS, AI, CH, EX)
                pillar = kpi.get('pillar', 'Unknown')
                
                kpis.append({
                    'account_id': account['account_id'],
                    'kpi_code': kpi_code,  # Use converted code
                    'measured_at': measured_at.strftime('%Y-%m-%d'),
                    'value': round(random.uniform(60, 90), 2),
                    'target': target_value,
                    'pillar': pillar
                })
    
    pd.DataFrame(accounts).to_csv(data_dir / 'accounts.csv', index=False)
    pd.DataFrame(kpis).to_csv(data_dir / 'kpi_measurements.csv', index=False)
    pd.DataFrame([{'customer_id': customer_id, 'uuid': generate_customer_id('dc'),
                   'customer_name': f'Customer {customer_id}',
                   'vertical': 'dc2_s', 'created_at': datetime.now().strftime('%Y-%m-%d')}]
                ).to_csv(data_dir / 'customers.csv', index=False)
    
    signals = [{'account_id': a['account_id'], 'signal_date': datetime.now().strftime('%Y-%m-%d'),
               'signal_type': 'health_check', 'signal_text': f'Signal for {a["account_name"]}',
               'sentiment': 'positive'} for a in accounts]
    pd.DataFrame(signals).to_csv(data_dir / 'qualitative_signals.csv', index=False)
    
    pd.DataFrame([{'customer_id': customer_id, 'product_id': 1,
                  'product_name': 'Platform', 'category': 'Infrastructure'}]
                ).to_csv(data_dir / 'products.csv', index=False)
    
    print(f"Generated {len(kpis)} KPI measurements ({len(all_kpis)} KPIs × {len(accounts)} accounts × {args.months} months)")
    print(f"Saved to: {data_dir}")
    print(f"NOTE: Loader script will filter to enabled KPIs only")
