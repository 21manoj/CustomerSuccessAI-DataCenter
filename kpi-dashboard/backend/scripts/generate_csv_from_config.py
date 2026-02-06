#!/usr/bin/env python3
"""
Generate CSV files from CustomerConfig
For testing CSV upload flow with config-aware data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from utils.config_loader import ConfigLoader
import pandas as pd
from datetime import datetime, timedelta
import random
from pathlib import Path

def generate_accounts_csv(customer_id, num_accounts=10):
    """Generate accounts.csv with config-aware data"""
    
    accounts = []
    
    for i in range(num_accounts):
        account_id = 10000 + i
        accounts.append({
            'account_id': account_id,
            'customer_id': customer_id,
            'account_name': f'Account-{account_id}',
            'industry': 'Technology',
            'vertical': 'dc2_s',
            'region': random.choice(['us-west-2', 'us-east-1', 'eu-west-1']),
            'account_status': 'active'
        })
    
    return pd.DataFrame(accounts)

def generate_kpi_measurements_csv(customer_id, accounts_df, num_months=12):
    """Gener    """Gener    """Gener    """Gener    """Gener rom config"""
    
    with app.app_context():
        loader = ConfigLoader(customer_id)
        enabled_kpis = loader.get_enabled_kpis()
        
        measurements = []
        start_date = datetime(2024, 1, 1)
        
        # For each account
        for _, account in accounts_df.iterrows():
            account_id = account['account_id']
            
            # Determine scenario based on account
            scenario_idx = account_id % 3
            scenarios = ['improving', 'stable_healthy', 'declining']
            scenario = scenarios[scenario_idx]
            
            # For each month
            for month_idx in range(num_months):
                measured_at = start_date + timedelta(days=30 * month_idx)
                
                # For each ENABLED KPI (config-aware!)
                for kpi_code in enabled_kpis:
                    kpi_def = loader.get_kpi_definition(kpi_code)
                    
                    if not kpi_def:
                        continue
                    
                    # Generate value based on scenario
                    if scenario == 'improving':
                        base = 50 + (month_idx * 3)  # Improving trend
                    elif scenario == 'declining':
                        base = 80 - (month_idx * 2)  # Declining trend
                    else:
                        base = 75  # Stable
                    
                    # Add randomness
                    value = max(0, min(100, base + random.uniform(-5, 5)))
                    
                    measurements.append({
                        'account_id': account_id,
                        'kpi_code': kpi_code,
                        'measured_at': measured_at.strftime('%Y-%m-%d'),
                        'value': round(value, 2),
                        'target': kpi_def['target'],
                        'pillar': kpi_def['pillar']
                    })
        
        print(f"Generated {len(measurements)} KPI measurements")
        print(f"  Accounts: {len(accounts_df)}")
        print(f"  Enabled KPIs: {len(enabled_kpis)}")
        print(f"  Months: {num_months}")
        print(f"  KPIs: {', '.join(sorted(enabled_kpis)[:5])}...")
        
        return pd.DataFrame(measurements)

def generate_customers_csv(customer_id, company_name):
    """Generate customers.csv"""
    
    return pd.DataFrame([{
        'customer_id': customer_id,
        'customer_name': company_name,
        'vertical': 'dc2_s',
        'created_at': datetime.now().strftime('%Y-%m-%d')
    }])

def generate_qualitative_signals_csv(accounts_df):
    """Generate qualitative_signals.csv"""
    
    signals = []
    
    for _, account in accounts_df.iterrows():
        signals.append({
            'account_id': account['account_id'],
            'signal_date': datetime.now().strftime('%Y-%m-%d'),
            'signal_type': 'health_check',
            'signal_text': f'Regular health check for {account["account_name"]}',
            'sentiment': 'positive'
        })
    
    return pd.DataFrame(signals)

def generate_products_csv(customer_id):
    """Generate products.csv"""
    
    return pd.DataFrame([
        {
            'customer_id': customer_id,
            'product_id': 1,
            'product_name': 'DC2_S Platform',
            'category': 'Infrastructure'
        }
    ])

def save_csvs(customer_id, customer_dir, company_name, num_accounts=10, num_months=12):
    """Generate and save all CSV files"""
    
    customer_dir = Path(customer_dir)
    customer_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nGenerating config-aware CSV files for customer {customer_id}...")
    print(f"Output directory: {customer_dir}")
    
    # Generate accounts
    accounts_df = generate_accounts_csv(customer_id, num_accounts)
    accounts_file = customer_dir / 'accounts.csv'
    accounts_df.to_csv(accounts_file, index=False)
    print(f"✅ {accounts_file} ({len(accounts_df)} accounts)")
    
    # Generate KPI measurements (config-aware!)
    kpi_df = generate_kpi_measurements_csv(customer_id, accounts_df, num_months)
    kpi_file = customer_dir / 'kpi_mearements.csv'
    kpi_df.to_csv(kpi_file, index=False)
    print(f"✅ {kpi_file} ({len(kpi_df)} measurements)")
    
    # Generate other files
    customers_df = generate_customers_csv(customer_id, company_name)
    customers_file = customer_dir / 'customers.csv'
    customers_df.to_csv(customers_file, index=False)
    print(f"✅ {customers_file}")
    
    signals_df = generate_qualitative_signals_csv(accounts_df)
    signals_file = customer_dir / 'qualitative_signals.csv'
    signals_df.to_csv(signals_file, index=False)
    print(f"✅ {signals_file}")
    
    products_df = generate_products_csv(customer_idproducts_file = customer_dir / 'products.csv'
    products_df.to_csv(products_file, index=False)
    print(f"✅ {products_file}")
    
    return {
        'accounts': accounts_file,
        'kpi_measurements': kpi_file,
        'customers': customers_file,
        'qualitative_signals': signals_file,
        'products': products_file
    }

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--customer-id', type=int, required=True)
    parser.add_argument('--company-name', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--num-accounts', type=int, default=10)
    parser.add_argument('--num-months', type=int, default=12)
    
  args = parser.parse_args()
    
    save_csvs(
        args.customer_id,
        args.output_dir,
        args.company_name,
        args.num_accounts,
        args.num_months
    )
