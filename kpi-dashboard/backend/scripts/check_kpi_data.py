#!/usr/bin/env python3
"""Check what KPI data exists for Test Company accounts."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app_v3_minimal import app
from extensions import db
from models import Account, KPI, Customer

def check_kpi_data():
    """Check KPI data for Test Company."""
    with app.app_context():
        customer = Customer.query.filter_by(customer_name='Test Company').first()
        if not customer:
            print("❌ Customer not found")
            return
        
        customer_id = customer.customer_id
        print(f"📊 KPI Data Check for Test Company (Customer ID: {customer_id})\n")
        
        # Get all accounts
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        print(f"Total accounts: {len(accounts)}\n")
        
        # Check KPIs per account
        accounts_with_kpis = 0
        total_kpis = 0
        
        print("Account-level KPI counts:")
        print("-" * 60)
        for acc in accounts:
            kpis = KPI.query.filter_by(account_id=acc.account_id).all()
            kpi_count = len(kpis)
            if kpi_count > 0:
                accounts_with_kpis += 1
                total_kpis += kpi_count
                print(f"  {acc.account_name}: {kpi_count} KPIs")
        
        print("-" * 60)
        print(f"\n✅ Accounts with KPIs: {accounts_with_kpis}/{len(accounts)}")
        print(f"📊 Total KPIs: {total_kpis}")
        
        if total_kpis == 0:
            print("\n⚠️  NO KPI DATA FOUND!")
            print("   The customer profile file only contains profile metadata,")
            print("   not KPI values. KPI data should be uploaded separately via")
            print("   the KPI upload functionality.")
        else:
            # Show sample KPIs
            sample_kpis = KPI.query.filter_by(customer_id=customer_id).limit(10).all()
            print(f"\n📝 Sample KPIs (first 10):")
            for kpi in sample_kpis:
                acc_name = Account.query.get(kpi.account_id).account_name if kpi.account_id else "N/A"
                print(f"   {acc_name} | {kpi.kpi_parameter}: {kpi.data}")


if __name__ == '__main__':
    check_kpi_data()









