#!/usr/bin/env python3
"""
Verify Data Center data in PostgreSQL database
"""
import sys
import os
from dotenv import load_dotenv

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from extensions import db
from models import Customer, User, Account, KPI, KPIUpload

# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path=env_path)

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///kpi_dashboard.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def verify_dc_data():
    """Verify DC data in database"""
    print("\n" + "="*70)
    print("VERIFYING DATA CENTER DATA IN POSTGRESQL")
    print("="*70)
    
    with app.app_context():
        # Find DC customer
        dc_customer = Customer.query.filter(
            (Customer.email == 'dc@example.com') | 
            (Customer.customer_name.ilike('%data center%'))
        ).first()
        
        if not dc_customer:
            print("\n❌ No Data Center customer found!")
            return
        
        customer_id = dc_customer.customer_id
        print(f"\n✅ Found DC Customer: {dc_customer.customer_name} (ID: {customer_id})")
        
        # Check User
        dc_user = User.query.filter_by(customer_id=customer_id, email="dc-admin@example.com").first()
        if dc_user:
            print(f"✅ Found DC Admin User: {dc_user.email} (ID: {dc_user.user_id})")
        else:
            print("❌ DC Admin User not found!")
        
        # Check Accounts
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        print(f"\n📊 Accounts: {len(accounts)}")
        
        if len(accounts) == 0:
            print("❌ NO ACCOUNTS FOUND!")
            return
        
        # Show sample accounts
        print("\n📋 Sample Accounts (first 10):")
        for i, acc in enumerate(accounts[:10], 1):
            print(f"   {i}. {acc.account_name} (ID: {acc.account_id}) - Revenue: ${acc.revenue:,.2f}")
        
        # Check KPI Uploads
        uploads = KPIUpload.query.filter_by(customer_id=customer_id).all()
        print(f"\n📤 KPI Uploads: {len(uploads)}")
        
        if len(uploads) == 0:
            print("❌ NO KPI UPLOADS FOUND!")
            return
        
        # Check KPIs
        upload_ids = [u.upload_id for u in uploads]
        kpis = KPI.query.filter(KPI.upload_id.in_(upload_ids)).all() if upload_ids else []
        print(f"\n📈 Total KPIs: {len(kpis)}")
        
        if len(kpis) == 0:
            print("❌ NO KPIs FOUND!")
            return
        
        # Group KPIs by account
        kpis_by_account = {}
        for kpi in kpis:
            account_id = kpi.account_id
            if account_id not in kpis_by_account:
                kpis_by_account[account_id] = []
            kpis_by_account[account_id].append(kpi)
        
        print(f"\n📊 KPIs by Account:")
        print(f"   Accounts with KPIs: {len(kpis_by_account)}")
        
        # Show KPIs per account (first 10)
        print("\n📋 KPIs per Account (first 10):")
        for i, (account_id, account_kpis) in enumerate(list(kpis_by_account.items())[:10], 1):
            account = Account.query.get(account_id)
            account_name = account.account_name if account else f"Account {account_id}"
            print(f"   {i}. {account_name}: {len(account_kpis)} KPIs")
        
        # Check for unique KPI parameters
        unique_kpis = set()
        for kpi in kpis:
            unique_kpis.add(kpi.kpi_parameter)
        
        print(f"\n📊 Unique KPI Parameters: {len(unique_kpis)}")
        print("\n📋 KPI Parameters (first 20):")
        for i, kpi_param in enumerate(list(unique_kpis)[:20], 1):
            print(f"   {i}. {kpi_param}")
        
        # Check for categories
        categories = set()
        for kpi in kpis:
            if kpi.category:
                categories.add(kpi.category)
        
        print(f"\n📊 Categories: {len(categories)}")
        print("\n📋 Categories:")
        for cat in sorted(categories):
            cat_kpis = [k for k in kpis if k.category == cat]
            print(f"   - {cat}: {len(cat_kpis)} KPIs")
        
        # Check data quality
        print(f"\n🔍 Data Quality Check:")
        kpis_with_data = [k for k in kpis if k.data and k.data != '0' and k.data != '']
        kpis_without_data = [k for k in kpis if not k.data or k.data == '0' or k.data == '']
        print(f"   KPIs with data: {len(kpis_with_data)} ({len(kpis_with_data)/len(kpis)*100:.1f}%)")
        print(f"   KPIs without data: {len(kpis_without_data)} ({len(kpis_without_data)/len(kpis)*100:.1f}%)")
        
        # Check for expected count (100 tenants × 31 KPIs × 7 months = 21,700)
        expected_kpis = 100 * 31 * 7  # 21,700
        print(f"\n📊 Expected vs Actual:")
        print(f"   Expected KPIs: {expected_kpis:,}")
        print(f"   Actual KPIs: {len(kpis):,}")
        if len(kpis) == expected_kpis:
            print("   ✅ Count matches!")
        else:
            print(f"   ⚠️  Count mismatch: {abs(len(kpis) - expected_kpis):,} difference")
        
        # Check upload distribution
        uploads_by_account = {}
        for upload in uploads:
            account_id = upload.account_id
            if account_id not in uploads_by_account:
                uploads_by_account[account_id] = []
            uploads_by_account[account_id].append(upload)
        
        print(f"\n📊 Upload Distribution:")
        print(f"   Accounts with uploads: {len(uploads_by_account)}")
        if len(uploads_by_account) > 0:
            uploads_per_account = len(uploads) / len(uploads_by_account)
            print(f"   Average uploads per account: {uploads_per_account:.1f}")
        
        # Sample KPI data
        print(f"\n📋 Sample KPI Data (first 10):")
        for i, kpi in enumerate(kpis[:10], 1):
            account = Account.query.get(kpi.account_id)
            account_name = account.account_name if account else f"Account {kpi.account_id}"
            print(f"   {i}. {account_name} | {kpi.category} | {kpi.kpi_parameter} | {kpi.data}")
        
        print("\n" + "="*70)
        print("✅ VERIFICATION COMPLETE")
        print("="*70)

if __name__ == "__main__":
    verify_dc_data()



