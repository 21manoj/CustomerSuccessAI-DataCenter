#!/usr/bin/env python3
"""
Generate CSV files from CustomerConfig
Config-aware synthetic data generator for CS Pulse onboarding

CORRECTED VERSION - Matches actual database schema from models.py
"""

import sys
import os
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from utils.config_loader import ConfigLoader
import pandas as pd
from datetime import datetime, timedelta
import random


def generate_accounts_csv(customer_id, num_accounts=10):
    """Generate accounts.csv with proper account IDs"""
    
    accounts = []
    # Account IDs are auto-incremented by DB; use sequential placeholders for CSV
    base_account_id = customer_id * 1000

    account_names = [
        'Production', 'Staging', 'Development', 'QA', 'UAT',
        'DR', 'Sandbox', 'Integration', 'Performance', 'Lab'
    ]

    for i in range(num_accounts):
        account_id = base_account_id + i + 1  # Placeholder; DB auto-assigns real IDs
        account_name = f"Customer {customer_id} - {account_names[i] if i < len(account_names) else f'Account-{i+1}'}"

        accounts.append({
            'account_id': account_id,
            'customer_id': customer_id,
            'uuid': f"dc2s_acct_{uuid.uuid4()}",
            'account_name': account_name,
            'industry': 'Data Center Infrastructure',
            'vertical': 'dc2_s',
            'region': random.choice(['us-west-2', 'us-east-1', 'eu-west-1']),
            'account_status': 'active',
            'created_at': datetime.now().strftime('%Y-%m-%d')
        })
    
    return pd.DataFrame(accounts)


def generate_kpi_measurements_csv(customer_id, accounts_df, num_months=12):
    """Generate KPI measurements from config (ENABLED KPIs only)"""
    
    with app.app_context():
        loader = ConfigLoader(customer_id)
        enabled_kpis = loader.get_enabled_kpis()
        
        print(f"   Config-aware: Using {len(enabled_kpis)} enabled KPIs")
        print(f"   KPIs: {', '.join(sorted(enabled_kpis)[:5])}..." if enabled_kpis else "   No enabled KPIs!")
        
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
                    
                    # Get target
                    target_value = kpi_def.get('target', {})
                    if isinstance(target_value, dict):
                        target_value = target_value.get('value', 85.0)
                    elif target_value is None:
                        target_value = 85.0
                    
                    # Generate value based on scenario
                    if scenario == 'improving':
                        base = 50 + (month_idx * 3)  # Improving trend
                    elif scenario == 'declining':
                        base = 80 - (month_idx * 2)  # Declining trend
                    else:
                        base = 75  # Stable
                    
                    # Add randomness
                    value = max(0, min(100, base + random.uniform(-5, 5)))
                    
                    # ✅ CORRECTED: Match DC2SKPI model from models.py
                    # Database columns: measured_at, target, status (NOT measurement_month, target_value, health_state)
                    measurements.append({
                        'account_id': account_id,
                        'kpi_code': kpi_code,
                        'measured_at': measured_at.strftime('%Y-%m-%d'),  # ✅ DB column name
                        'value': round(value, 2),
                        'target': target_value,  # ✅ DB column name (not target_value)
                        'pillar': kpi_def.get('pillar', 'Unknown'),
                        'weight': kpi_def.get('weight', 0.25),
                        'status': 'healthy' if value >= 70 else ('risk' if value >= 50 else 'critical')  # ✅ DB column name
                        # ✅ Removed: unit, threshold_breached (not in DC2SKPI model)
                    })
        
        print(f"   Generated {len(measurements)} KPI measurements")
        print(f"     Accounts: {len(accounts_df)}")
        print(f"     Enabled KPIs: {len(enabled_kpis)}")
        print(f"     Months: {num_months}")
        
        return pd.DataFrame(measurements)


def generate_customers_csv(customer_id, company_name):
    """Generate customers.csv"""
    
    return pd.DataFrame([{
        'customer_id': customer_id,  # ✅ KEEP - Primary key in Customer model
        'customer_name': company_name,
        'vertical': 'dc2_s',
        'created_at': datetime.now().strftime('%Y-%m-%d')
    }])


def generate_qualitative_signals_csv(customer_id, accounts_df, num_months=12):
    """Generate qualitative_signals.csv"""
    
    signals = []
    start_date = datetime(2024, 1, 1)
    signal_types = ['health_check', 'customer_feedback', 'incident', 'milestone', 'meeting']
    sentiments = ['positive', 'neutral', 'negative']
    
    signal_counter = 1
    
    for _, account in accounts_df.iterrows():
        account_id = account['account_id']
        
        for month in range(num_months):
            signal_date = start_date + timedelta(days=30 * month + random.randint(0, 28))
            
            # 2-3 signals per account per month
            for _ in range(random.randint(2, 3)):
                # ✅ Generate unique signal_id (required PK in QualitativeSignal model)
                signal_id = f'sig_{account_id}_{signal_counter:04d}'
                signal_counter += 1
                
                signals.append({
                    'signal_id': signal_id,  # ✅ Required PK
                    'account_id': account_id,
                    # ✅ NO customer_id - QualitativeSignal model doesn't have it
                    'signal_date': signal_date.strftime('%Y-%m-%d'),
                    'signal_type': random.choice(signal_types),
                    'content': f'Signal for {account["account_name"]} on {signal_date.strftime("%Y-%m-%d")}',  # ✅ DB column name (not signal_text)
                    'sentiment': random.choice(sentiments),
                    'sentiment_score': round(random.uniform(-1, 1), 2)
                })
    
    return pd.DataFrame(signals)


def generate_products_csv(customer_id):
    """Generate products.csv"""
    
    return pd.DataFrame([
        {
            'customer_id': customer_id,  # ✅ KEEP - Product model has customer_id FK
            'product_id': 1,
            'product_name': 'DC2_S Platform',
            'category': 'Infrastructure',
            'license_type': 'Enterprise'
        },
        {
            'customer_id': customer_id,  # ✅ KEEP - Product model has customer_id FK
            'product_id': 2,
            'product_name': 'Monitoring Suite',
            'category': 'Operations',
            'license_type': 'Professional'
        }
    ])


def save_csvs(customer_id, customer_dir, company_name, num_accounts=10, num_months=12, journey_patterns=None):
    """Generate and save all CSV files"""
    
    customer_dir = Path(customer_dir)
    customer_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📊 Generating config-aware CSV files for customer {customer_id}...")
    print(f"   Company: {company_name}")
    print(f"   Output: {customer_dir}")
    print(f"   Accounts: {num_accounts}")
    print(f"   Months: {num_months}")
    
    files_created = []
    
    # Generate accounts
    accounts_df = generate_accounts_csv(customer_id, num_accounts)
    accounts_file = customer_dir / 'accounts.csv'
    accounts_df.to_csv(accounts_file, index=False)
    files_created.append(f"accounts.csv ({accounts_file.stat().st_size} bytes)")
    print(f"   ✅ {accounts_file.name} ({len(accounts_df)} accounts)")
    
    # Generate KPI measurements (config-aware!)
    kpi_df = generate_kpi_measurements_csv(customer_id, accounts_df, num_months)
    kpi_file = customer_dir / 'kpi_measurements.csv'
    kpi_df.to_csv(kpi_file, index=False)
    files_created.append(f"kpi_measurements.csv ({kpi_file.stat().st_size} bytes)")
    print(f"   ✅ {kpi_file.name} ({len(kpi_df)} measurements)")
    
    # Generate customers
    customers_df = generate_customers_csv(customer_id, company_name)
    customers_file = customer_dir / 'customers.csv'
    customers_df.to_csv(customers_file, index=False)
    files_created.append(f"customers.csv ({customers_file.stat().st_size} bytes)")
    print(f"   ✅ {customers_file.name}")
    
    # Generate qualitative signals
    signals_df = generate_qualitative_signals_csv(customer_id, accounts_df, num_months)
    signals_file = customer_dir / 'qualitative_signals.csv'
    signals_df.to_csv(signals_file, index=False)
    files_created.append(f"qualitative_signals.csv ({signals_file.stat().st_size} bytes)")
    print(f"   ✅ {signals_file.name} ({len(signals_df)} signals)")
    
    # Generate products
    products_df = generate_products_csv(customer_id)
    products_file = customer_dir / 'products.csv'
    products_df.to_csv(products_file, index=False)
    files_created.append(f"products.csv ({products_file.stat().st_size} bytes)")
    print(f"   ✅ {products_file.name}")
    
    # Generate DEMO_MANIFEST if requested
    if journey_patterns == 'DEMO_MANIFEST':
        manifest_file = customer_dir.parent / 'DEMO_MANIFEST.md'
        
        manifest_content = f"""# Demo Manifest - Customer {customer_id}

## Overview
- **Customer ID:** {customer_id}
- **Company:** {company_name}
- **Accounts:** {num_accounts}
- **Time Period:** {num_months} months
- **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Data Files
{chr(10).join(f'- {f}' for f in files_created)}

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
{chr(10).join(f'- **{row["account_id"]}**: {row["account_name"]}' for _, row in accounts_df.iterrows())}

## KPIs (Config-Aware)
- Total measurements: {len(kpi_df)}
- Enabled KPIs: {len(kpi_df['kpi_code'].unique()) if not kpi_df.empty else 0}
- Months of data: {num_months}

## Next Steps
1. Run data loading: `02_load_customer{customer_id}_data_SMART.py`
2. Generate embeddings: `03_embed_customer{customer_id}_OPENAI.py`
3. Generate journeys: Wizard A
"""
        
        with open(manifest_file, 'w') as f:
            f.write(manifest_content)
        
        print(f"   ✅ DEMO_MANIFEST.md ({manifest_file.stat().st_size} bytes)")
    
    print(f"\n🎉 Data generation complete!")
    return {
        'accounts': accounts_file,
        'kpi_measurements': kpi_file,
        'customers': customers_file,
        'qualitative_signals': signals_file,
        'products': products_file
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate config-aware synthetic customer data'
    )
    parser.add_argument('--customer-id', type=int, required=True,
                       help='Customer ID')
    parser.add_argument('--company-name', type=str, default=None,
                       help='Company name (default: Customer {id})')
    parser.add_argument('--output-dir', type=str, required=True,
                       help='Output directory for CSV files')
    parser.add_argument('--num-accounts', type=int, default=10,
                       help='Number of accounts (default: 10)')
    parser.add_argument('--num-months', type=int, default=12,
                       help='Number of months of data (default: 12)')
    parser.add_argument('--journey-patterns', type=str, default=None,
                       help='Journey pattern type (e.g., DEMO_MANIFEST)')
    
    args = parser.parse_args()
    
    company_name = args.company_name or f"Customer {args.customer_id}"
    
    try:
        save_csvs(
            args.customer_id,
            args.output_dir,
            company_name,
            args.num_accounts,
            args.num_months,
            args.journey_patterns
        )
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
