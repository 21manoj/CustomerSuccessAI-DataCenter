#!/usr/bin/env python3
"""Find customer with 36 accounts and their login credentials"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import User, Account, Customer
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
    print("\n" + "="*70)
    print("SEARCHING FOR CUSTOMER WITH 36 ACCOUNTS")
    print("="*70)
    
    # Get all customers with their account counts
    customers = Customer.query.all()
    
    found_36 = False
    for customer in customers:
        account_count = Account.query.filter_by(customer_id=customer.customer_id).count()
        
        if account_count == 36:
            found_36 = True
            print(f"\n✅ FOUND CUSTOMER WITH 36 ACCOUNTS:")
            print(f"   Customer Name: {customer.customer_name}")
            print(f"   Customer ID: {customer.customer_id}")
            print(f"   Email: {customer.email}")
            print(f"   Account Count: {account_count}")
            
            # Find users for this customer
            users = User.query.filter_by(customer_id=customer.customer_id).all()
            
            if users:
                print(f"\n👤 USERS FOR THIS CUSTOMER:")
                for user in users:
                    print(f"   Email: {user.email}")
                    print(f"   User Name: {user.user_name}")
                    print(f"   User ID: {user.user_id}")
                    print(f"   Active: {user.active}")
                    print(f"   Has Password: {bool(user.password_hash)}")
                    print("")
            else:
                print(f"\n⚠️  No users found for this customer!")
                print(f"   Creating a user with default password...")
                
                # Create a user for this customer
                from werkzeug.security import generate_password_hash
                user = User(
                    customer_id=customer.customer_id,
                    user_name=customer.customer_name + ' Admin',
                    email=customer.email or f'admin@{customer.customer_name.lower().replace(" ", "")}.com',
                    password_hash=generate_password_hash('admin123', method='pbkdf2:sha256'),
                    active=True
                )
                db.session.add(user)
                db.session.commit()
                
                print(f"   ✅ Created user:")
                print(f"      Email: {user.email}")
                print(f"      Password: admin123")
            
            # List all 36 accounts
            accounts = Account.query.filter_by(customer_id=customer.customer_id).order_by(Account.account_name).all()
            print(f"\n📋 ALL {len(accounts)} ACCOUNTS:")
            for i, acc in enumerate(accounts, 1):
                print(f"   {i:2d}. {acc.account_name} (ID: {acc.account_id})")
            
            break
    
    if not found_36:
        print("\n❌ No customer found with exactly 36 accounts")
        print("\n📊 ALL CUSTOMERS AND THEIR ACCOUNT COUNTS:")
        print("="*70)
        for customer in customers:
            account_count = Account.query.filter_by(customer_id=customer.customer_id).count()
            print(f"   {customer.customer_name} (ID: {customer.customer_id}): {account_count} accounts")
            
            # Show users for each
            users = User.query.filter_by(customer_id=customer.customer_id).all()
            if users:
                for user in users:
                    print(f"      User: {user.email}")


