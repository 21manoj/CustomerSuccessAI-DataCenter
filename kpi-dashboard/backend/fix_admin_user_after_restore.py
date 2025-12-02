#!/usr/bin/env python3
"""
Fix Admin User After Database Restore

This script ensures admin@example.com exists and is linked to customer_id=1
(Test Company) which has the 25 accounts with 6 months of KPI data.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import Customer, User
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def fix_admin_user():
    """Ensure admin@example.com exists and is linked to customer_id=1"""
    print("\n" + "="*70)
    print("FIXING ADMIN USER AFTER RESTORE")
    print("="*70)
    
    with app.app_context():
        # Get customer_id=1 (Test Company - has 25 accounts)
        customer = Customer.query.get(1)
        if not customer:
            print("\n❌ Customer ID 1 not found!")
            return False
        
        print(f"\n✅ Found customer: {customer.customer_name} (ID: {customer.customer_id})")
        
        # Check if admin user exists
        admin = User.query.filter_by(email='admin@example.com').first()
        
        if admin:
            # Update existing admin user
            old_customer_id = admin.customer_id
            admin.customer_id = customer.customer_id
            admin.password_hash = generate_password_hash('admin123', method='pbkdf2:sha256')
            admin.active = True
            admin.user_name = admin.user_name or 'Demo Admin'
            print(f"\n✅ Updated existing admin user:")
            print(f"   Email: admin@example.com")
            print(f"   Password: admin123")
            print(f"   Customer ID: {old_customer_id} → {customer.customer_id}")
        else:
            # Create new admin user
            admin = User(
                customer_id=customer.customer_id,
                user_name='Demo Admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123', method='pbkdf2:sha256'),
                active=True
            )
            db.session.add(admin)
            print(f"\n✅ Created new admin user:")
            print(f"   Email: admin@example.com")
            print(f"   Password: admin123")
            print(f"   Customer ID: {customer.customer_id}")
        
        db.session.commit()
        db.session.refresh(admin)
        
        # Verify
        print(f"\n📊 Verification:")
        print(f"   User ID: {admin.user_id}")
        print(f"   Email: {admin.email}")
        print(f"   Customer ID: {admin.customer_id}")
        print(f"   Customer Name: {customer.customer_name}")
        print(f"   Active: {admin.active}")
        
        # Check accounts for this customer
        from models import Account
        account_count = Account.query.filter_by(customer_id=customer.customer_id).count()
        print(f"\n📋 Customer {customer.customer_id} has {account_count} accounts")
        
        if account_count == 25:
            print(f"   ✅ Perfect! 25 accounts found (6 months of data)")
        else:
            print(f"   ⚠️  Expected 25 accounts, found {account_count}")
        
        print(f"\n✅ Admin user fixed successfully!")
        return True

if __name__ == '__main__':
    success = fix_admin_user()
    sys.exit(0 if success else 1)

