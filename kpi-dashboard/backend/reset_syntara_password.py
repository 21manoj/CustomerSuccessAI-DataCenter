#!/usr/bin/env python3
"""Reset password for Syntara user with 36 accounts"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import User, Account, Customer
from werkzeug.security import generate_password_hash, check_password_hash
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
else:
    instance_path = os.path.join(os.path.dirname(basedir), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'kpi_dashboard.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    # Find Syntara customer (ID: 1)
    customer = Customer.query.get(1)
    if not customer:
        print("❌ Syntara customer (ID: 1) not found!")
        sys.exit(1)
    
    print(f"\n✅ Found customer: {customer.customer_name} (ID: {customer.customer_id})")
    
    # Find user
    user = User.query.filter_by(email='admin@syntara.com').first()
    if not user:
        print("❌ User admin@syntara.com not found!")
        sys.exit(1)
    
    print(f"✅ Found user: {user.email}")
    
    # Reset password to 'syntara123'
    new_password = 'syntara123'
    user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
    user.active = True
    db.session.commit()
    
    # Verify password
    password_valid = check_password_hash(user.password_hash, new_password)
    
    print(f"\n✅ Password reset complete!")
    print(f"   Email: {user.email}")
    print(f"   Password: {new_password}")
    print(f"   Password verified: {'✅ VALID' if password_valid else '❌ INVALID'}")
    
    # Count accounts
    account_count = Account.query.filter_by(customer_id=customer.customer_id).count()
    print(f"\n📊 Account count: {account_count}")
    
    print(f"\n🎉 Login credentials:")
    print(f"   Email: {user.email}")
    print(f"   Password: {new_password}")


