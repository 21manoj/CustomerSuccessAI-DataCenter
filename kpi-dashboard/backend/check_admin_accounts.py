#!/usr/bin/env python3
"""Check admin user and account associations"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import User, Account, Customer

with app.app_context():
    # Check admin user
    admin = User.query.filter_by(email='admin@example.com').first()
    if admin:
        print(f'Admin user: {admin.email}')
        print(f'Customer ID: {admin.customer_id}')
        
        # Check customer
        customer = Customer.query.get(admin.customer_id) if admin.customer_id else None
        if customer:
            print(f'Customer: {customer.customer_name} (ID: {customer.customer_id})')
        
        # Count accounts for this customer
        account_count = Account.query.filter_by(customer_id=admin.customer_id).count() if admin.customer_id else 0
        print(f'Accounts for this customer: {account_count}')
        
        # List account names
        accounts = Account.query.filter_by(customer_id=admin.customer_id).limit(30).all() if admin.customer_id else []
        print(f'\nFirst 30 accounts:')
        for acc in accounts:
            print(f'  - {acc.account_name} (ID: {acc.account_id})')
    else:
        print('Admin user not found')
    
    # Check all customers and their account counts
    print('\n' + '='*60)
    print('All Customers and Account Counts:')
    print('='*60)
    customers = Customer.query.all()
    for cust in customers:
        count = Account.query.filter_by(customer_id=cust.customer_id).count()
        print(f'{cust.customer_name} (ID: {cust.customer_id}): {count} accounts')


