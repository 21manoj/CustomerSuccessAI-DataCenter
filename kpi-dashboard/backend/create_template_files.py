#!/usr/bin/env python3
"""
Create Template CSV Files for Onboarding
=========================================

Creates downloadable template CSV files for all 6 file types:
1. accounts.csv
2. kpi_measurements.csv (kpis.csv)
3. qualitative_signals.csv (signals.csv)
4. products.csv
5. account_profiles.csv (profiles.csv)
6. customers.csv

These templates are used by users to understand the expected structure
and format of data files for onboarding.
"""

import csv
import json
from pathlib import Path
from datetime import datetime, timedelta

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "verticals" / "_template" / "templates"
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

def create_accounts_template():
    """Create accounts.csv template"""
    filepath = TEMPLATE_DIR / "accounts.csv"
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        # Header
        writer.writerow([
            'account_id', 'customer_id', 'account_name', 'revenue',
            'industry', 'region', 'account_status', 'external_account_id',
            'profile_metadata'
        ])
        # Sample rows (2 examples)
        writer.writerow([
            '10001', '1', 'Acme Corporation - Datacenter East', '2500000.00',
            'Technology', 'North America', 'active', 'EXT-1-10001',
            '{"assigned_csm": "John Smith", "csm_manager": "Jane Doe", "onboarding_status": "completed"}'
        ])
        writer.writerow([
            '10002', '1', 'Acme Corporation - Cloud Ops', '1800000.00',
            'Technology', 'North America', 'active', 'EXT-1-10002',
            '{"assigned_csm": "John Smith", "csm_manager": "Jane Doe", "onboarding_status": "completed"}'
        ])
    
    print(f"✅ Created: {filepath}")
    return filepath

def create_kpi_measurements_template():
    """Create kpi_measurements.csv template"""
    filepath = TEMPLATE_DIR / "kpi_measurements.csv"
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'account_id', 'kpi_code', 'measurement_date', 'value',
            'unit', 'source', 'notes'
        ])
        writer.writeheader()
        
        # Sample rows (3 examples showing different KPIs)
        base_date = datetime.now() - timedelta(days=30)
        writer.writerow({
            'account_id': '10001',
            'kpi_code': 'AI-KPI1',
            'measurement_date': base_date.strftime('%Y-%m-%d'),
            'value': '85.5',
            'unit': '%',
            'source': 'System Monitoring',
            'notes': 'GPU Utilization'
        })
        writer.writerow({
            'account_id': '10001',
            'kpi_code': 'CH-KPI1',
            'measurement_date': base_date.strftime('%Y-%m-%d'),
            'value': '82.0',
            'unit': 'score',
            'source': 'Health Calculator',
            'notes': 'Overall Health Score'
        })
        writer.writerow({
            'account_id': '10001',
            'kpi_code': 'DV-KPI1',
            'measurement_date': base_date.strftime('%Y-%m-%d'),
            'value': '12',
            'unit': 'days',
            'source': 'Deployment System',
            'notes': 'Time to First Workload'
        })
    
    print(f"✅ Created: {filepath}")
    return filepath

def create_qualitative_signals_template():
    """Create qualitative_signals.csv template"""
    filepath = TEMPLATE_DIR / "qualitative_signals.csv"
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'signal_id', 'account_id', 'signal_date', 'signal_type',
            'sentiment', 'content'
        ])
        writer.writeheader()
        
        # Sample rows (3 examples)
        base_date = datetime.now() - timedelta(days=7)
        writer.writerow({
            'signal_id': '1',
            'account_id': '10001',
            'signal_date': base_date.strftime('%Y-%m-%d'),
            'signal_type': 'email',
            'sentiment': 'positive',
            'content': 'Customer expressed satisfaction with recent deployment'
        })
        writer.writerow({
            'signal_id': '2',
            'account_id': '10001',
            'signal_date': (base_date - timedelta(days=3)).strftime('%Y-%m-%d'),
            'signal_type': 'meeting',
            'sentiment': 'neutral',
            'content': 'QBR meeting scheduled for next month'
        })
        writer.writerow({
            'signal_id': '3',
            'account_id': '10001',
            'signal_date': (base_date - timedelta(days=1)).strftime('%Y-%m-%d'),
            'signal_type': 'escalation',
            'sentiment': 'negative',
            'content': 'Performance issue reported, resolved within 2 hours'
        })
    
    print(f"✅ Created: {filepath}")
    return filepath

def create_products_template():
    """Create products.csv template"""
    filepath = TEMPLATE_DIR / "products.csv"
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['product_id', 'product_name', 'category', 'description'])
        writer.writeheader()
        
        # Sample rows (3 examples)
        writer.writerow({
            'product_id': '1',
            'product_name': 'AI Compute Platform',
            'category': 'Infrastructure',
            'description': 'High-performance GPU compute platform for AI workloads'
        })
        writer.writerow({
            'product_id': '2',
            'product_name': 'Data Analytics Suite',
            'category': 'Software',
            'description': 'Comprehensive analytics and reporting tools'
        })
        writer.writerow({
            'product_id': '3',
            'product_name': 'Managed Services',
            'category': 'Services',
            'description': '24/7 managed infrastructure services'
        })
    
    print(f"✅ Created: {filepath}")
    return filepath

def create_account_profiles_template():
    """Create account_profiles.csv template (profiles.csv)"""
    filepath = TEMPLATE_DIR / "account_profiles.csv"
    
    # Note: account_profiles has 100+ columns, we'll include key ones
    key_columns = [
        'account_id', 'customer_id', 'account_name', 'account_nickname',
        'industry', 'account_tier', 'initial_arr', 'final_arr',
        'contract_start_date', 'contract_end_date', 'partner_id',
        'csm_assigned', 'executive_sponsor', 'journey_type', 'outcome'
    ]
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=key_columns)
        writer.writeheader()
        
        # Sample row
        writer.writerow({
            'account_id': '10001',
            'customer_id': '1',
            'account_name': 'Acme Corporation - Datacenter East',
            'account_nickname': 'Acme DC East',
            'industry': 'Technology',
            'account_tier': 'Enterprise',
            'initial_arr': '2000000',
            'final_arr': '2500000',
            'contract_start_date': '2024-01-01',
            'contract_end_date': '2025-12-31',
            'partner_id': 'PARTNER-001',
            'csm_assigned': 'John Smith',
            'executive_sponsor': 'Jane Executive',
            'journey_type': 'expansion',
            'outcome': 'success'
        })
    
    print(f"✅ Created: {filepath}")
    return filepath

def create_customers_template():
    """Create customers.csv template"""
    filepath = TEMPLATE_DIR / "customers.csv"
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'customer_id', 'customer_name', 'domain', 'industry_vertical', 'created_at'
        ])
        writer.writeheader()
        
        # Sample row
        writer.writerow({
            'customer_id': '1',
            'customer_name': 'Acme Corporation',
            'domain': 'acme-corporation.com',
            'industry_vertical': 'Technology - dc2_s',
            'created_at': datetime.now().strftime('%Y-%m-%d')
        })
    
    print(f"✅ Created: {filepath}")
    return filepath

def main():
    """Create all template files"""
    print("=" * 70)
    print("Creating Template CSV Files for Onboarding")
    print("=" * 70)
    print()
    
    templates = {
        'accounts': create_accounts_template,
        'kpi_measurements': create_kpi_measurements_template,
        'qualitative_signals': create_qualitative_signals_template,
        'products': create_products_template,
        'account_profiles': create_account_profiles_template,
        'customers': create_customers_template
    }
    
    created = []
    for name, func in templates.items():
        try:
            filepath = func()
            created.append((name, filepath))
        except Exception as e:
            print(f"❌ Failed to create {name} template: {e}")
    
    print()
    print("=" * 70)
    print(f"✅ Created {len(created)} template files")
    print("=" * 70)
    print()
    print("Template files location:")
    print(f"  {TEMPLATE_DIR}")
    print()
    print("Files created:")
    for name, filepath in created:
        print(f"  - {name}: {filepath.name}")
    
    return created

if __name__ == '__main__':
    main()
