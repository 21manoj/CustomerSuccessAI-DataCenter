#!/usr/bin/env python3
"""
Create database with proper schema
"""

from app import app, db
from models import Customer, CustomerConfig, Account, User, KPIUpload, KPI

def create_database():
    with app.app_context():
        # Drop all tables first
        db.drop_all()
        # Create all tables
        db.create_all()
        print("Database created successfully")
        
        # Check the schema
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Tables created: {tables}")
        
        # Check customer_configs schema
        if 'customer_configs' in tables:
            columns = inspector.get_columns('customer_configs')
            print(f"customer_configs columns: {[col['name'] for col in columns]}")

if __name__ == "__main__":
    create_database()

