#!/usr/bin/env python3
"""Check data availability for RAG queries"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import HealthTrend, Product, Account

with app.app_context():
    # Check HealthTrend data
    trends = HealthTrend.query.filter_by(customer_id=1).count()
    print(f'HealthTrend records for customer_id=1: {trends}')
    
    if trends > 0:
        sample = HealthTrend.query.filter_by(customer_id=1).first()
        print(f'  Sample: Account {sample.account_id}, Month {sample.month}/{sample.year}, Score {sample.overall_health_score}')
    
    # Check Product data
    products = Product.query.filter_by(customer_id=1).count()
    print(f'\nProduct records for customer_id=1: {products}')
    
    # Check accounts with multiple products
    accounts = Account.query.filter_by(customer_id=1).all()
    multi_product_count = 0
    for acc in accounts:
        count = Product.query.filter_by(account_id=acc.account_id, customer_id=1).count()
        if count > 1:
            multi_product_count += 1
            products = Product.query.filter_by(account_id=acc.account_id, customer_id=1).all()
            names = [p.product_name for p in products]
            print(f'  {acc.account_name}: {count} products - {", ".join(names)}')
    
    print(f'\nAccounts with >1 product: {multi_product_count}/{len(accounts)}')


