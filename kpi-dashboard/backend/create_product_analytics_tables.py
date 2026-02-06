#!/usr/bin/env python3
"""
Create Product Analytics Tables Migration Script
Creates product_catalog, product_trends, and product_aggregate_trends tables
"""

from extensions import db
from app_v3_minimal import app
from product_analytics_models import ProductCatalog, ProductTrend, ProductAggregateTrend

def create_product_analytics_tables():
    """Create all product analytics tables"""
    with app.app_context():
        try:
            print("Creating product analytics tables...")
            
            # Create tables
            db.create_all()
            
            print("✅ Product analytics tables created successfully!")
            print("   - product_catalog")
            print("   - product_trends")
            print("   - product_aggregate_trends")
            
            # Verify tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'product_catalog' in tables:
                print("✅ Verified: product_catalog table exists")
            if 'product_trends' in tables:
                print("✅ Verified: product_trends table exists")
            if 'product_aggregate_trends' in tables:
                print("✅ Verified: product_aggregate_trends table exists")
                
        except Exception as e:
            print(f"❌ Error creating tables: {str(e)}")
            raise

if __name__ == '__main__':
    create_product_analytics_tables()
