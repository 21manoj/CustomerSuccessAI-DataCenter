#!/usr/bin/env python3
"""Move accounts from Seed Customer to Test Company (customer_id=1)"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Account, Product, KPI, KPITimeSeries, KPIUpload

with app.app_context():
    print('='*70)
    print('MOVING ACCOUNTS TO ADMIN CUSTOMER (customer_id=1)')
    print('='*70)
    
    # Get accounts from Seed Customer (customer_id=5)
    seed_customer_accounts = Account.query.filter_by(customer_id=5).all()
    
    print(f'\nFound {len(seed_customer_accounts)} accounts in Seed Customer (ID: 5)')
    
    if len(seed_customer_accounts) == 0:
        print('No accounts to move.')
        exit(0)
    
    moved_count = 0
    for account in seed_customer_accounts:
        print(f'\nMoving: {account.account_name} (ID: {account.account_id})')
        
        # Update account
        account.customer_id = 1
        db.session.add(account)
        
        # Update products
        products = Product.query.filter_by(account_id=account.account_id, customer_id=5).all()
        for product in products:
            product.customer_id = 1
            db.session.add(product)
            print(f'  - Updated product: {product.product_name} (ID: {product.product_id})')
        
        # Update KPIs (via KPIUpload)
        uploads = KPIUpload.query.filter_by(account_id=account.account_id, customer_id=5).all()
        for upload in uploads:
            upload.customer_id = 1
            db.session.add(upload)
        
        # Update KPIs directly (if they have customer_id)
        # Note: KPIs don't have customer_id column, they're linked via account_id
        
        # Update KPITimeSeries
        time_series = KPITimeSeries.query.filter_by(account_id=account.account_id, customer_id=5).all()
        for ts in time_series:
            ts.customer_id = 1
            db.session.add(ts)
        
        moved_count += 1
        print(f'  ✅ Moved account and all related data')
    
    # Commit all changes
    db.session.commit()
    
    print('\n' + '='*70)
    print(f'✅ Successfully moved {moved_count} accounts to Test Company (customer_id=1)')
    print('='*70)
    
    # Verify
    test_company_accounts = Account.query.filter_by(customer_id=1).count()
    print(f'\nTotal accounts for Test Company (customer_id=1): {test_company_accounts}')
    
    # Show account names
    accounts = Account.query.filter_by(customer_id=1).order_by(Account.account_id).all()
    print(f'\nAccount names:')
    for acc in accounts:
        product_count = Product.query.filter_by(account_id=acc.account_id).count()
        if product_count > 0:
            print(f'  - {acc.account_name} (ID: {acc.account_id}) - {product_count} products')
        else:
            print(f'  - {acc.account_name} (ID: {acc.account_id})')


