#!/usr/bin/env python3
"""Verify admin user login credentials"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import User, Customer
from werkzeug.security import check_password_hash
from dotenv import load_dotenv

# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
# Use PostgreSQL if DATABASE_URL is set, otherwise use SQLite
database_url = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print(f"✅ Using PostgreSQL database")
else:
    instance_path = os.path.join(os.path.dirname(basedir), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'kpi_dashboard.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    print(f"⚠️  Using SQLite database: {db_path}")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    # Check admin user
    admin = User.query.filter_by(email='admin@example.com').first()
    
    if not admin:
        print("❌ Admin user not found!")
        print("   Run: python3 seed_all_data.py")
        sys.exit(1)
    
    print(f"\n✅ Admin user found:")
    print(f"   Email: {admin.email}")
    print(f"   User ID: {admin.user_id}")
    print(f"   Customer ID: {admin.customer_id}")
    print(f"   Active: {admin.active}")
    print(f"   Password hash exists: {bool(admin.password_hash)}")
    
    if admin.password_hash:
        print(f"   Password hash: {admin.password_hash[:50]}...")
    
    # Test password
    test_password = 'admin123'
    if admin.password_hash:
        password_valid = check_password_hash(admin.password_hash, test_password)
        print(f"\n🔐 Password test:")
        print(f"   Testing password: {test_password}")
        print(f"   Result: {'✅ VALID' if password_valid else '❌ INVALID'}")
        
        if not password_valid:
            print(f"\n⚠️  Password hash mismatch!")
            print(f"   The password hash may have been created with a different method.")
            print(f"   Run: python3 seed_all_data.py to reset the password")
    else:
        print(f"\n❌ No password hash set!")
        print(f"   Run: python3 seed_all_data.py to set the password")
    
    # Check customer
    if admin.customer_id:
        customer = Customer.query.get(admin.customer_id)
        if customer:
            print(f"\n👤 Customer:")
            print(f"   Name: {customer.customer_name}")
            print(f"   ID: {customer.customer_id}")
        else:
            print(f"\n⚠️  Customer ID {admin.customer_id} not found!")


