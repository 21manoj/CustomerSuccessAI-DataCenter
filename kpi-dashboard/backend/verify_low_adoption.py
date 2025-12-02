#!/usr/bin/env python3
"""Verify low adoption accounts"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Account, Product, KPI

with app.app_context():
    print('='*70)
    print('LOW ADOPTION ACCOUNTS - VERIFICATION')
    print('='*70)
    
    low_adoption_accounts = [
        'TechVenture Solutions',
        'InnovateLabs Corp',
        'Digital Dynamics Inc',
        'NextGen Technologies',
        'TechMasters Group'
    ]
    
    for account_name in low_adoption_accounts:
        account = Account.query.filter_by(account_name=account_name).first()
        if account:
            print(f'\n{account_name} (ID: {account.account_id}):')
            products = Product.query.filter_by(account_id=account.account_id).order_by(Product.product_name).all()
            
            for product in products:
                # Get Product Activation Rate and Feature Adoption Rate
                activation_kpi = KPI.query.filter_by(
                    account_id=account.account_id,
                    product_id=product.product_id,
                    kpi_parameter='Product Activation Rate'
                ).first()
                
                adoption_kpi = KPI.query.filter_by(
                    account_id=account.account_id,
                    product_id=product.product_id,
                    kpi_parameter='Feature Adoption Rate'
                ).first()
                
                activation = float(activation_kpi.data.replace('%', '')) if activation_kpi else 0
                adoption = float(adoption_kpi.data.replace('%', '')) if adoption_kpi else 0
                
                status = '⚠️ LOW' if activation < 50 or adoption < 50 else '✅ OK'
                print(f'  {product.product_name}: Activation={activation:.1f}%, Adoption={adoption:.1f}% {status}')
    
    print('\n' + '='*70)
    print('SUMMARY')
    print('='*70)
    
    total_accounts = Account.query.join(Product).distinct().count()
    print(f'Total accounts with products: {total_accounts}')
    
    total_products = Product.query.count()
    print(f'Total products: {total_products}')
    
    # Count products with low adoption
    low_adoption_count = 0
    all_products = Product.query.all()
    for product in all_products:
        activation_kpi = KPI.query.filter_by(
            account_id=product.account_id,
            product_id=product.product_id,
            kpi_parameter='Product Activation Rate'
        ).first()
        if activation_kpi:
            activation = float(activation_kpi.data.replace('%', ''))
            if activation < 50:
                low_adoption_count += 1
    
    print(f'Products with low adoption (<50%): {low_adoption_count}')
    print('='*70)


