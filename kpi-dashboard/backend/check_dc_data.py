#!/usr/bin/env python3
"""Check DC data in PostgreSQL database"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db
from models import Customer, User, Account, KPI

with app.app_context():
    print("="*70)
    print("DATA CENTER DATA CHECK - PostgreSQL Database")
    print("="*70)
    
    # Check customers
    customers = Customer.query.all()
    print('\n=== CUSTOMERS ===')
    for c in customers:
        print(f'Customer ID: {c.customer_id}, Name: {c.customer_name}, Email: {c.email}')
    
    # Check users
    users = User.query.all()
    print('\n=== USERS ===')
    for u in users:
        print(f'User ID: {u.user_id}, Email: {u.email}, Customer ID: {u.customer_id}, Name: {u.user_name}')
    
    # Check dc-admin user specifically
    dc_user = User.query.filter_by(email='dc-admin@example.com').first()
    if dc_user:
        print(f'\n=== DC ADMIN USER ===')
        print(f'Email: {dc_user.email}')
        print(f'Customer ID: {dc_user.customer_id}')
        print(f'User ID: {dc_user.user_id}')
        print(f'Name: {dc_user.user_name}')
        
        # Check accounts for this customer
        accounts = Account.query.filter_by(customer_id=dc_user.customer_id).all()
        print(f'\n=== ACCOUNTS for Customer ID {dc_user.customer_id} ===')
        print(f'Total accounts: {len(accounts)}')
        if accounts:
            print(f'\nFirst 5 accounts:')
            for a in accounts[:5]:
                print(f'  Account ID: {a.account_id}, Name: {a.account_name}, Revenue: ${a.revenue:,.2f}')
        
        # Check KPIs for this customer
        kpis = db.session.query(KPI).join(Account).filter(Account.customer_id == dc_user.customer_id).all()
        print(f'\n=== KPIs for Customer ID {dc_user.customer_id} ===')
        print(f'Total KPIs: {len(kpis):,}')
        if kpis:
            print(f'\nFirst 5 KPIs:')
            for k in kpis[:5]:
                print(f'  KPI ID: {k.kpi_id}, Parameter: {k.kpi_parameter}, Data: {k.data}, Account: {k.account_id}')
            
            # Group by account
            kpis_by_account = {}
            for k in kpis:
                if k.account_id not in kpis_by_account:
                    kpis_by_account[k.account_id] = []
                kpis_by_account[k.account_id].append(k)
            
            print(f'\n=== KPIs by Account ===')
            for account_id, account_kpis in list(kpis_by_account.items())[:5]:
                account = Account.query.get(account_id)
                print(f'  Account: {account.account_name if account else f"ID {account_id}"} - {len(account_kpis)} KPIs')
    else:
        print('\n❌ DC Admin user (dc-admin@example.com) not found!')
    
    print("\n" + "="*70)

