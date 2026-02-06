#!/usr/bin/env python3
"""
Config-Aware CSV Generator
Generates CSV files based on CustomerConfig instead of hardcoded KPIs
For use in testing CSV upload flows
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from utils.config_loader import ConfigLoader
import pandas as pd
from datetime import datetime, timedelta
import random

def generate_accounts(customer_id, num_accounts=10):
    """Generate accounts DataFrame"""
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

def generate_kpi_measurements(accounts, customer_id=None, num_months=12):
    """
    Generate KPI measurements DataFrame - CONFIG AWARE!
    Only generates KPIs that are enabled in CustomerConfig
    """
    
    if customer_id is None:
        # Fallback to default KPIs if no customer_id
        raise ValueError("customer_id is required for config-aware generation")
    
    with app.app_context():
        loader = ConfigLoader(customer_id)
        enabled_kpis = loader.get_enabled_kpis()
        
        print(f"Config-aware generation for customer {customer_id}:")
        print(f"  Enabled KPIs: {len(enabled_kpis)}")
        print(f"  KPIs: {', '.join(sorted(enabled_kpis)[:5])}...")
        
        measurements = []
        start_date = datetime(2024, 1, 1)
        
        # For each account
        for _, account in accounts.iterrows():
            account_id = account['account_id']
            
            # Determine scenario
            scenario_idx = account_id % 3
            scenarios = ['improving', 'stable', 'declining']
            scenario = scenarios[scenario_idx]
            
            # For each month
            for month_idx in range(num_months):
                measured_at = start_date + timedelta(days=30 * month_idx)
                
                # For each ENABLED KPI only (config-aware!)
                for kpi_code in enabled_kpis:
                    kpi_def = loader.get_kpi_definition(kpi_code)
                    
                    if not kpi_def:
                        continue
                    
                    # Generate value based on scenario
                    if scenario == 'improving':
                        base = 50 + (month_idx * 3)
                    elif scenario == 'declining':
                        base = 80 - (month_idx * 2)
                    else:
                        base = 75
                    
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
        
        print(f"  Generated {len(measurements)} measurements")
        return pd.DataFrame(measurements)

def generate_qualitative_signals(accounts):
    """Generate qualitative signals DataFrame"""
    signals = []
    
    for _, account in accounts.iterrows():
        signals.append({
            'account_id': account['account_id'],
            'signal_date': datetime.now().strftime('%Y-%m-%d'),
            'signal_type': 'health_check',
            'signal_text': f'Regular health check for {account["account_name"]}',
            'sentiment': 'positive'
        })
    
    return pd.DataFrame(signals)

def generate_products(customer_id):
    """Generate products DataFrame"""
    return pd.DataFrame([
        {
            'customer_id': customer_id,
            'product_id': 1,
            'product_name': 'DC2_S Platform',
            'category': 'Infrastructure'
        }
    ])

def generate_customers_csv(customer_id, company_name):
    """Generate customers DataFrame"""
    return pd.DataFrame([{
        'customer_id': customer_id,
        'customer_name': company_name,
        'vertical': 'dc2_s',
        'created_at': datetime.now().strftime('%Y-%m-%d')
    }])
