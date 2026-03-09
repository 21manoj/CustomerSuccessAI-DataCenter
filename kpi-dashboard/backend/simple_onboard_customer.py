#!/usr/bin/env python3
"""
Simple Customer Onboarding Script (Config-Aware)
=================================================

Creates a new customer with config-aware data generation.
No test framework - just clean onboarding execution.

Usage:
    python3 simple_onboard_customer.py --name "Acme Corp" --industry "Technology"
    python3 simple_onboard_customer.py --name "Test Co" --accounts 5 --months 6
    
Options:
    --name: Company name (required)
    --industry: Industry (default: Technology)
    --accounts: Number of accounts to create (default: 3)
    --months: Months of historical data (default: 12)
    --enabled-kpis: Number of KPIs to enable (default: 15)
    --vertical: Vertical (default: dc2_s)
"""

import sys
import os
from pathlib import Path
import argparse
from datetime import datetime, timedelta
import pandas as pd
import random

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer, CustomerConfig, Account, DC2SKPI
from utils.config_loader import ConfigLoader
from verticals.dc2_s.vertical_loader import DC2SVertical

def log(message):
    """Simple logging"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def create_customer(company_name, industry):
    """Create customer record"""
    log(f"Creating customer: {company_name}")
    
    customer = Customer(customer_name=company_name)
    db.session.add(customer)
    db.session.flush()
    
    customer_id = customer.customer_id
    log(f"✅ Customer created with ID: {customer_id}")
    
    return customer_id

def create_customer_config(customer_id, num_enabled_kpis=15):
    """Create CustomerConfig with enabled KPIs"""
    log(f"Creating CustomerConfig with {num_enabled_kpis} enabled KPIs...")
    
    # Load vertical KPIs
    vertical = DC2SVertical()
    all_kpis = vertical.kpis
    
    # Select KPIs to enable (evenly across pillars)
    enabled_kpis = []
    kpis_per_pillar = num_enabled_kpis // 5
    extra_kpis = num_enabled_kpis % 5
    
    for i, pillar in enumerate(['P1', 'P2', 'P3', 'P4', 'P5']):
        pillar_kpis = [k['code'] for k in all_kpis if k['pillar'] == pillar]
        
        # Add extra KPI to first pillars if not evenly divisible
        num_to_add = kpis_per_pillar + (1 if i < extra_kpis else 0)
        enabled_kpis.extend(pillar_kpis[:num_to_add])
    
    # Create config
    config = CustomerConfig(
        customer_id=customer_id,
        vertical='dc2_s',
        dc2s_enabled_kpis=enabled_kpis,
        dc2s_pillar_weights={
            'P1': 0.15,
            'P2': 0.20,
            'P3': 0.25,
            'P4': 0.15,
            'P5': 0.25
        }
    )
    db.session.add(config)
    db.session.commit()
    
    log(f"✅ Config created with {len(enabled_kpis)} enabled KPIs")
    log(f"   Enabled KPIs: {', '.join(enabled_kpis[:5])}...")
    
    return enabled_kpis

def create_accounts(customer_id, company_name, industry, num_accounts=3):
    """Create account records"""
    log(f"Creating {num_accounts} accounts...")
    
    environments = ['Production', 'Staging', 'Development', 'QA', 'UAT']
    accounts = []
    
    for i in range(num_accounts):
        env = environments[i] if i < len(environments) else f'Account-{i+1}'
        
        account = Account(
            customer_id=customer_id,
            account_name=f"{company_name}-{env}",
            industry=industry,
            vertical='dc2_s',
            region=random.choice(['us-west-2', 'us-east-1', 'eu-west-1']),
            account_status='active'
        )
        db.session.add(account)
        db.session.flush()
        
        accounts.append({
            'account_id': account.account_id,
            'account_name': account.account_name
        })
    
    db.session.commit()
    
    log(f"✅ Created {len(accounts)} accounts")
    for acc in accounts:
        log(f"   • {acc['account_id']}: {acc['account_name']}")
    
    return accounts

def generate_kpi_data(customer_id, accounts, enabled_kpis, num_months=12):
    """Generate config-aware KPI measurement data"""
    log(f"Generating KPI data for {num_months} months...")
    
    loader = ConfigLoader(customer_id)
    start_date = datetime(2024, 1, 1)
    
    measurements = []
    
    for account in accounts:
        account_id = account['account_id']
        
        # Determine scenario for this account
        scenario_types = ['improving', 'stable', 'declining']
        scenario = scenario_types[account_id % 3]
        
        for month_idx in range(num_months):
            measured_at = start_date + timedelta(days=30 * month_idx)
            
            # Generate only enabled KPIs (config-aware!)
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
                
                value = max(0, min(100, base + random.uniform(-5, 5)))
                
                measurements.append({
                    'account_id': account_id,
                    'kpi_code': kpi_code,
                    'measured_at': measured_at,
                    'value': round(value, 2),
                    'target': kpi_def['target'],
                    'pillar': kpi_def['pillar']
                })
    
    log(f"✅ Generated {len(measurements)} KPI measurements (config-aware)")
    log(f"   Accounts: {len(accounts)}")
    log(f"   KPIs: {len(enabled_kpis)}")
    log(f"   Months: {num_months}")
    log(f"   Total: {len(accounts)} × {len(enabled_kpis)} × {num_months} = {len(measurements)}")
    
    return measurements

def save_to_database(measurements):
    """Save KPI measurements to database"""
    log(f"Saving {len(measurements)} records to database...")
    
    batch_size = 1000
    saved = 0
    
    for i in range(0, len(measurements), batch_size):
        batch = measurements[i:i+batch_size]
        
        for record in batch:
            kpi = DC2SKPI(
                account_id=record['account_id'],
                kpi_code=record['kpi_code'],
                measured_at=record['measured_at'],
                value=record['value'],
                target=record['target'],
                pillar=record['pillar']
            )
            db.session.add(kpi)
            saved += 1
        
        db.session.commit()
        log(f"   Saved batch {i//batch_size + 1}: {len(batch)} records")
    
    log(f"✅ Saved {saved} records to database")

def calculate_scores(customer_id):
    """Calculate health scores"""
    log("Calculating health scores...")
    
    try:
        from utils.score_calculator import ScoreCalculator
        
        calculator = ScoreCalculator(customer_id)
        
        # Get all accounts
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        # Get latest month with data
        latest_month = db.session.query(
            db.func.max(db.func.date_trunc('month', DC2SKPI.measured_at))
        ).filter(
            DC2SKPI.account_id.in_([a.account_id for a in accounts])
        ).scalar()
        
        if not latest_month:
            log("⚠️  No KPI data found, skipping score calculation")
            return
        
        measurement_date = latest_month.date()
        log(f"   Calculating for month: {measurement_date}")
        
        # Calculate for each account
        scores = []
        for account in accounts:
            result = calculator.calculate_scores_for_account(
                account.account_id,
                measurement_date
            )
            
            if result and 'health_score' in result:
                health = result['health_score']
                scores.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'health_score': health['health_score'],
                    'health_status': health['health_status']
                })
        
        log(f"✅ Calculated scores for {len(scores)} accounts")
        for score in scores:
            log(f"   • {score['account_name']}: {score['health_score']:.1f} ({score['health_status']})")
        
    except Exception as e:
        log(f"⚠️  Score calculation failed: {e}")
        log("   Continuing without scores...")

def main():
    parser = argparse.ArgumentParser(
        description='Simple customer onboarding with config-aware data generation'
    )
    parser.add_argument('--name', required=True, help='Company name')
    parser.add_argument('--industry', default='Technology', help='Industry (default: Technology)')
    parser.add_argument('--accounts', type=int, default=3, help='Number of accounts (default: 3)')
    parser.add_argument('--months', type=int, default=12, help='Months of data (default: 12)')
    parser.add_argument('--enabled-kpis', type=int, default=38, help='Number of enabled KPIs (default: 38 = all)')
    parser.add_argument('--skip-scores', action='store_true', help='Skip score calculation')
    
    args = parser.parse_args()
    
    print("="*70)
    print("SIMPLE CUSTOMER ONBOARDING (CONFIG-AWARE)")
    print("="*70)
    print(f"Company: {args.name}")
    print(f"Industry: {args.industry}")
    print(f"Accounts: {args.accounts}")
    print(f"Months: {args.months}")
    print(f"Enabled KPIs: {args.enabled_kpis}")
    print("="*70)
    print()
    
    with app.app_context():
        try:
            # Step 1: Create customer
            customer_id = create_customer(args.name, args.industry)
            
            # Step 2: Create config
            enabled_kpis = create_customer_config(customer_id, args.enabled_kpis)
            
            # Step 3: Create accounts
            accounts = create_accounts(customer_id, args.name, args.industry, args.accounts)
            
            # Step 4: Generate KPI data (config-aware)
            measurements = generate_kpi_data(customer_id, accounts, enabled_kpis, args.months)
            
            # Step 5: Save to database
            save_to_database(measurements)
            
            # Step 6: Calculate scores (optional)
            if not args.skip_scores:
                calculate_scores(customer_id)
            
            # Success summary
            print()
            print("="*70)
            print("✅ ONBOARDING COMPLETE!")
            print("="*70)
            print(f"Customer ID: {customer_id}")
            print(f"Company: {args.name}")
            print(f"Accounts: {len(accounts)}")
            print(f"Enabled KPIs: {len(enabled_kpis)}")
            print(f"KPI Records: {len(measurements)}")
            print()
            print("Next steps:")
            print(f"  • View in dashboard: http://localhost:3000/customer/{customer_id}")
            print(f"  • Test API: curl http://localhost:5059/api/journey/<account_id>")
            print(f"  • Upload more data: POST /api/upload")
            print("="*70)
            
            return 0
            
        except Exception as e:
            print()
            print("="*70)
            print("❌ ONBOARDING FAILED")
            print("="*70)
            print(f"Error: {e}")
            print()
            
            import traceback
            traceback.print_exc()
            
            db.session.rollback()
            return 1

if __name__ == '__main__':
    sys.exit(main())
