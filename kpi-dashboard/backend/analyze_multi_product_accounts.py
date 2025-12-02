#!/usr/bin/env python3
"""
Analyze Multi-Product Accounts

Shows which accounts have products and their product details.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Account, Product, KPI
from kpi_queries import get_product_kpis

def analyze_multi_product_accounts():
    """Analyze accounts with multi-product data"""
    
    with app.app_context():
        print('='*70)
        print('MULTI-PRODUCT ACCOUNTS ANALYSIS')
        print('='*70)
        
        # Get all accounts that have products
        accounts_with_products = db.session.query(Account).join(Product).distinct().all()
        
        print(f'\nTotal accounts with products: {len(accounts_with_products)}')
        print('\n' + '-'*70)
        
        if accounts_with_products:
            for account in accounts_with_products:
                print(f'\nAccount: {account.account_name} (ID: {account.account_id})')
                print(f'  Customer ID: {account.customer_id}')
                print(f'  Revenue: ${account.revenue:,.0f}' if account.revenue else '  Revenue: N/A')
                print(f'  Industry: {account.industry or "N/A"}')
                print(f'  Region: {account.region or "N/A"}')
                
                # Get products for this account
                products = Product.query.filter_by(account_id=account.account_id).order_by(Product.product_id).all()
                print(f'  Products: {len(products)}')
                
                for product in products:
                    # Count product-level KPIs
                    product_kpi_count = KPI.query.filter_by(
                        account_id=account.account_id,
                        product_id=product.product_id
                    ).count()
                    
                    print(f'    - Product ID: {product.product_id}')
                    print(f'      Name: {product.product_name}')
                    print(f'      SKU: {product.product_sku or "N/A"}')
                    print(f'      Type: {product.product_type or "N/A"}')
                    print(f'      Revenue: ${product.revenue:,.0f}' if product.revenue else '      Revenue: N/A')
                    print(f'      Status: {product.status}')
                    print(f'      Product-level KPIs: {product_kpi_count}')
                
                # Show aggregate KPIs
                aggregate_kpis = KPI.query.filter_by(
                    account_id=account.account_id,
                    product_id=None,
                    aggregation_type='weighted_avg'
                ).all()
                
                if aggregate_kpis:
                    print(f'  Account Aggregates: {len(aggregate_kpis)}')
                    for agg in aggregate_kpis[:5]:  # Show first 5
                        print(f'    - {agg.kpi_parameter}: {agg.data}')
                    if len(aggregate_kpis) > 5:
                        print(f'    ... and {len(aggregate_kpis) - 5} more')
                
                print('-'*70)
        else:
            print('\nNo accounts with products found.')
        
        # Summary statistics
        print('\n' + '='*70)
        print('SUMMARY STATISTICS')
        print('='*70)
        
        total_products = Product.query.count()
        total_product_kpis = KPI.query.filter(KPI.product_id.isnot(None)).count()
        total_aggregates = KPI.query.filter(
            KPI.product_id.is_(None),
            KPI.aggregation_type == 'weighted_avg'
        ).count()
        
        print(f'Total products across all accounts: {total_products}')
        print(f'Total product-level KPIs: {total_product_kpis}')
        print(f'Total account aggregates: {total_aggregates}')
        
        # Product names summary
        print('\nAll Product Names:')
        all_products = Product.query.order_by(Product.product_name, Product.product_id).all()
        product_names = {}
        for product in all_products:
            account = Account.query.get(product.account_id)
            account_name = account.account_name if account else 'N/A'
            
            if product.product_name not in product_names:
                product_names[product.product_name] = []
            product_names[product.product_name].append({
                'id': product.product_id,
                'account_id': product.account_id,
                'account_name': account_name
            })
        
        for name, details in sorted(product_names.items()):
            print(f'  - {name}: {len(details)} instance(s)')
            for detail in details:
                print(f'      ID: {detail["id"]}, Account: {detail["account_name"]} (ID: {detail["account_id"]})')
        
        print('='*70)

if __name__ == "__main__":
    analyze_multi_product_accounts()


