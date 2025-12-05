#!/usr/bin/env python3
"""
Test script to verify multi-product accounts display KPIs correctly
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app_v3_minimal import app, db
from models import Account, KPI, Product, KPIUpload
import json

def test_multi_product_accounts():
    """Test that accounts with multiple products have correct KPIs"""
    with app.app_context():
        customer_id = 1
        
        # Test accounts with multiple products
        test_accounts = [
            'TechVision',
            'NetCore', 
            'NextGen Technologies'
        ]
        
        print("="*70)
        print("TESTING MULTI-PRODUCT ACCOUNTS KPI DISPLAY")
        print("="*70)
        
        all_passed = True
        
        for account_name in test_accounts:
            print(f"\n📊 Testing: {account_name}")
            print("-" * 70)
            
            account = Account.query.filter_by(
                account_name=account_name,
                customer_id=customer_id
            ).first()
            
            if not account:
                print(f"❌ Account {account_name} not found")
                all_passed = False
                continue
            
            # Get products from metadata
            products = []
            if hasattr(account, 'profile_metadata') and account.profile_metadata:
                try:
                    metadata = json.loads(account.profile_metadata) if isinstance(account.profile_metadata, str) else account.profile_metadata
                    products_str = metadata.get('products_used', '')
                    if products_str and products_str.strip():
                        products = [p.strip() for p in products_str.split(',') if p.strip()]
                except:
                    pass
            
            print(f"   Products: {len(products)} - {', '.join(products)}")
            
            # Get all KPIs
            kpis = db.session.query(KPI, Product).join(
                KPIUpload, KPI.upload_id == KPIUpload.upload_id
            ).outerjoin(
                Product, KPI.product_id == Product.product_id
            ).filter(
                KPIUpload.customer_id == customer_id,
                KPI.account_id == account.account_id
            ).all()
            
            product_kpis = [(k, p) for k, p in kpis if k.product_id is not None]
            account_kpis = [(k, p) for k, p in kpis if k.product_id is None]
            
            print(f"   Total KPIs: {len(kpis)}")
            print(f"   Product-level KPIs: {len(product_kpis)}")
            print(f"   Account-level KPIs: {len(account_kpis)}")
            
            # Verify product-level KPIs exist for each product
            product_kpi_counts = {}
            for kpi, product in product_kpis:
                if product:
                    product_name = product.product_name
                    if product_name not in product_kpi_counts:
                        product_kpi_counts[product_name] = 0
                    product_kpi_counts[product_name] += 1
            
            print(f"   Product-level KPIs by product:")
            for product_name, count in sorted(product_kpi_counts.items()):
                print(f"     - {product_name}: {count} KPIs")
            
            # Verify all products have KPIs
            missing_kpis = [p for p in products if p not in product_kpi_counts]
            if missing_kpis:
                print(f"   ⚠️  Products without KPIs: {missing_kpis}")
                all_passed = False
            else:
                print(f"   ✅ All products have KPIs")
            
            # Verify expected counts
            if len(products) == 3:
                expected_product_kpis = 15  # 5 KPIs per product
                if len(product_kpis) == expected_product_kpis:
                    print(f"   ✅ Product-level KPI count correct ({expected_product_kpis})")
                else:
                    print(f"   ⚠️  Expected {expected_product_kpis} product-level KPIs, got {len(product_kpis)}")
                    all_passed = False
        
        print("\n" + "="*70)
        if all_passed:
            print("✅ ALL TESTS PASSED")
        else:
            print("⚠️  SOME TESTS FAILED - Check output above")
        print("="*70)
        
        return all_passed

if __name__ == "__main__":
    test_multi_product_accounts()



