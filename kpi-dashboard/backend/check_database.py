#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import KPI, Account, KPIUpload

def check_database():
    """Directly check the database state"""
    with app.app_context():
        print("=== Direct Database Check ===\n")
        
        # 1. Check KPIs with account_id
        print("1. Checking KPIs with account_id...")
        kpis_with_account = KPI.query.filter(KPI.account_id.isnot(None)).all()
        print(f"   KPIs with account_id: {len(kpis_with_account)}")
        
        kpis_without_account = KPI.query.filter(KPI.account_id.is_(None)).all()
        print(f"   KPIs without account_id: {len(kpis_without_account)}")
        
        total_kpis = KPI.query.count()
        print(f"   Total KPIs: {total_kpis}")
        
        # 2. Check specific account
        print("\n2. Checking account 16...")
        account_16_kpis = KPI.query.filter_by(account_id=16).all()
        print(f"   KPIs for account 16: {len(account_16_kpis)}")
        
        if account_16_kpis:
            print(f"   First KPI account_id: {account_16_kpis[0].account_id}")
            print(f"   First KPI data: {account_16_kpis[0].data}")
        
        # 3. Check all accounts
        print("\n3. Checking all accounts...")
        accounts = Account.query.all()
        print(f"   Total accounts: {len(accounts)}")
        
        for account in accounts[:5]:
            kpi_count = KPI.query.filter_by(account_id=account.account_id).count()
            print(f"   - {account.account_name} (ID: {account.account_id}): {kpi_count} KPIs")
        
        # 4. Check uploads
        print("\n4. Checking uploads...")
        uploads = KPIUpload.query.all()
        print(f"   Total uploads: {len(uploads)}")
        
        for upload in uploads[:3]:
            kpi_count = KPI.query.filter_by(upload_id=upload.upload_id).count()
            print(f"   - {upload.original_filename} (ID: {upload.upload_id}): {kpi_count} KPIs")

if __name__ == "__main__":
    check_database() 