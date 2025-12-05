#!/usr/bin/env python3
"""Debug product names to see why they're not merging."""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app_v3_minimal import app
from extensions import db
from models import Account, KPI, Product

def debug_product_names():
    """Check product names in the data."""
    with app.app_context():
        customer = db.session.query(Account).filter_by(customer_id=1).first().customer_id
        accounts = Account.query.filter_by(customer_id=customer).limit(5).all()
        
        print(f"📊 Product Names Debug (Customer ID: {customer})\n")
        
        # Check profile_metadata.products_used
        print("From Customer Profile Data (profile_metadata.products_used):")
        for acc in accounts:
            profile = acc.profile_metadata or {}
            products = profile.get('products_used', '').strip()
            if products:
                print(f"  {acc.account_name}: '{products}'")
        
        print("\nFrom Product Table (products table):")
        products = Product.query.filter_by(customer_id=customer).limit(10).all()
        product_names = set()
        for p in products:
            product_names.add(p.product_name)
            print(f"  Product ID {p.product_id}: '{p.product_name}' (Account: {p.account_id})")
        
        print("\nFrom Product-Level KPIs (KPIs with product_id set):")
        product_kpis = db.session.query(KPI).join(Product, KPI.product_id == Product.product_id).filter(
            Product.customer_id == customer
        ).limit(10).all()
        kpi_product_names = set()
        for kpi in product_kpis:
            # Get product name from the KPI's product
            product = Product.query.get(kpi.product_id)
            if product:
                kpi_product_names.add(product.product_name)
                print(f"  KPI ID {kpi.kpi_id}: Product '{product.product_name}' (Product ID: {kpi.product_id})")
        
        print(f"\nSummary:")
        print(f"  Profile products: {set()}")
        print(f"  Product table names: {sorted(product_names)}")
        print(f"  KPI product names: {sorted(kpi_product_names)}")


if __name__ == '__main__':
    debug_product_names()









