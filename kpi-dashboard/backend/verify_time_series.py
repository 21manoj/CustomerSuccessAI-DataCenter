#!/usr/bin/env python3
"""Verify time series data for all accounts"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Account, KPITimeSeries, Product

with app.app_context():
    print('='*70)
    print('TIME SERIES DATA VERIFICATION')
    print('='*70)
    
    # Check all accounts with products
    accounts_with_products = db.session.query(Account).join(Product).distinct().all()
    
    print(f'\nTotal accounts with products: {len(accounts_with_products)}')
    print('\nTime Series Records per Account:')
    print('-'*70)
    
    total_records = 0
    for account in accounts_with_products:
        time_series_count = KPITimeSeries.query.filter_by(account_id=account.account_id).count()
        total_records += time_series_count
        status = '✅' if time_series_count >= 60 else '⚠️'
        print(f'{status} {account.account_name} (ID: {account.account_id}): {time_series_count} records')
    
    print(f'\nTotal time series records: {total_records}')
    expected = len(accounts_with_products) * 60
    if total_records >= expected:
        print(f'✅ Expected: {expected}, Got: {total_records}')
    else:
        print(f'⚠️  Expected: {expected}, Got: {total_records}')
    print('='*70)


