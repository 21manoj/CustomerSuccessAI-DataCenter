#!/usr/bin/env python3
"""
Ultra-Simple Customer Onboarding
=================================

Creates customer with defaults - no arguments needed.
Just run and go!

Usage:
    python3 quick_onboard.py
    python3 quick_onboard.py "Acme Corp"
    python3 quick_onboard.py "Test Company" --kpis 20
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer, CustomerConfig, Account, DC2SKPI
from utils.config_loader import ConfigLoader
from verticals.dc2_s.vertical_loader import DC2SVertical

# Defaults
DEFAULT_COMPANY = f"Demo Company {int(datetime.now().timestamp())}"
DEFAULT_NUM_ACCOUNTS = 3
DEFAULT_NUM_MONTHS = 12
DEFAULT_NUM_KPIS = 38  # All KPIs (customer can narrow via enabled_kpis later)

def onboard(company_name=None, num_kpis=DEFAULT_NUM_KPIS):
    """Simple onboarding - returns customer_id"""
    
    company_name = company_name or DEFAULT_COMPANY
    
    print(f"\n🚀 Onboarding: {company_name}")
    print(f"   KPIs: {num_kpis}, Accounts: {DEFAULT_NUM_ACCOUNTS}, Months: {DEFAULT_NUM_MONTHS}")
    
    with app.app_context():
        # 1. Create customer
        customer = Customer(customer_name=company_name)
        db.session.add(customer)
        db.session.flush()
        customer_id = customer.customer_id
        print(f"   ✅ Customer ID: {customer_id}")
        
        # 2. Create config with enabled KPIs
        vertical = DC2SVertical()
        all_kpis = [k['code'] for k in vertical.kpis]
        enabled_kpis = all_kpis[:num_kpis]  # Take first N KPIs
        
        config = CustomerConfig(
            customer_id=customer_id,
            vertical='dc2_s',
            dc2s_enabled_kpis=enabled_kpis,
            dc2s_pillar_weights={'P3': 0.25, 'P4': 0.20, 'P1': 0.15, 'P5': 0.20, 'P2': 0.20}
        )
        db.session.add(config)
        print(f"   ✅ Config: {len(enabled_kpis)} KPIs enabled")
        
        # 3. Create accounts
        accounts = []
        for i, env in enumerate(['Production', 'Staging', 'Development']):
            account = Account(
                customer_id=customer_id,
                account_name=f"{company_name}-{env}",
                industry='Technology',
                vertical='dc2_s',
                region='us-west-2',
                account_status='active'
            )
            db.session.add(account)
            db.session.flush()
            accounts.append(account.account_id)
        
        print(f"   ✅ Accounts: {len(accounts)} created")
        
        # 4. Generate KPI data (config-aware!)
        loader = ConfigLoader(customer_id)
        start_date = datetime(2024, 1, 1)
        
        total_records = 0
        for account_id in accounts:
            for month in range(DEFAULT_NUM_MONTHS):
                measured_at = start_date + timedelta(days=30 * month)
                
                for kpi_code in enabled_kpis:
                    kpi_def = loader.get_kpi_definition(kpi_code)
                    value = random.uniform(60, 90)
                    
                    kpi = DC2SKPI(
                        account_id=account_id,
                        kpi_code=kpi_code,
                        measured_at=measured_at,
                        value=round(value, 2),
                        target=kpi_def['target'],
                        pillar=kpi_def['pillar']
                    )
                    db.session.add(kpi)
                    total_records += 1
        
        db.session.commit()
        print(f"   ✅ KPI Data: {total_records} records")
        
        # 5. Calculate scores
        try:
            from utils.score_calculator import ScoreCalculator
            calculator = ScoreCalculator(customer_id)
            
            latest_month = db.session.query(
                db.func.max(db.func.date_trunc('month', DC2SKPI.measured_at))
            ).filter(DC2SKPI.account_id.in_(accounts)).scalar()
            
            if latest_month:
                for account_id in accounts:
                    calculator.calculate_scores_for_account(account_id, latest_month.date())
                print(f"   ✅ Scores: Calculated for {len(accounts)} accounts")
        except:
            print(f"   ⚠️  Scores: Skipped (optional)")
        
        print(f"\n✅ DONE! Customer {customer_id} ready to use\n")
        
        return customer_id

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Quick customer onboarding')
    parser.add_argument('company', nargs='?', help='Company name (optional)')
    parser.add_argument('--kpis', type=int, default=DEFAULT_NUM_KPIS, help=f'Number of KPIs (default: {DEFAULT_NUM_KPIS})')
    
    args = parser.parse_args()
    
    customer_id = onboard(args.company, args.kpis)
    
    print(f"Customer ID: {customer_id}")
    print(f"Dashboard: http://localhost:3000/customer/{customer_id}")
    print(f"API: curl http://localhost:5059/api/journey/<account_id>")
