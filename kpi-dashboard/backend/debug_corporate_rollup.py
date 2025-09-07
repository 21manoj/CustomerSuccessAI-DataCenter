#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import KPI, Account, KPIUpload

def debug_corporate_rollup():
    """Debug the corporate rollup logic"""
    with app.app_context():
        customer_id = 6
        
        print("=== Debugging Corporate Rollup ===\n")
        
        # 1. Check accounts for customer
        print("1. Checking accounts for customer 6...")
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        print(f"   Found {len(accounts)} accounts")
        
        for account in accounts[:5]:
            kpi_count = KPI.query.filter_by(account_id=account.account_id).count()
            print(f"   - {account.account_name} (ID: {account.account_id}): {kpi_count} KPIs")
        
        # 2. Test the JOIN query
        print("\n2. Testing JOIN query...")
        kpis_with_accounts = db.session.query(KPI, Account).join(
            Account, KPI.account_id == Account.account_id
        ).filter(
            Account.customer_id == customer_id
        ).all()
        
        print(f"   Found {len(kpis_with_accounts)} KPI-Account pairs")
        
        if kpis_with_accounts:
            first_kpi, first_account = kpis_with_accounts[0]
            print(f"   First KPI: {first_kpi.kpi_parameter} (account_id: {first_kpi.account_id})")
            print(f"   First Account: {first_account.account_name} (account_id: {first_account.account_id})")
        
        # 3. Test simpler query
        print("\n3. Testing simpler query...")
        kpis_with_account_id = KPI.query.filter(KPI.account_id.isnot(None)).all()
        print(f"   KPIs with account_id: {len(kpis_with_account_id)}")
        
        if kpis_with_account_id:
            print(f"   First KPI account_id: {kpis_with_account_id[0].account_id}")
        
        # 4. Test account-specific query
        print("\n4. Testing account-specific query...")
        account_16_kpis = KPI.query.filter_by(account_id=16).all()
        print(f"   KPIs for account 16: {len(account_16_kpis)}")
        
        if account_16_kpis:
            print(f"   First KPI: {account_16_kpis[0].kpi_parameter}")

if __name__ == "__main__":
    debug_corporate_rollup() 