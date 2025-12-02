#!/usr/bin/env python3
"""
Check OpenAI API key in database directly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import CustomerConfig, Customer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    print("\n" + "="*70)
    print("DATABASE CHECK: OpenAI API Keys")
    print("="*70)
    
    # Get all customers
    customers = Customer.query.all()
    print(f"\n📊 Found {len(customers)} customers:")
    
    for customer in customers:
        print(f"\n   Customer ID: {customer.customer_id}")
        print(f"   Name: {customer.customer_name}")
        
        config = CustomerConfig.query.filter_by(customer_id=customer.customer_id).first()
        if config:
            print(f"   ✅ CustomerConfig exists")
            print(f"   Has encrypted key: {bool(config.openai_api_key_encrypted)}")
            if config.openai_api_key_encrypted:
                print(f"   Encrypted key length: {len(config.openai_api_key_encrypted)}")
                print(f"   Key preview: {config.openai_api_key_encrypted[:50]}...")
            if config.openai_api_key_updated_at:
                print(f"   Updated at: {config.openai_api_key_updated_at}")
        else:
            print(f"   ❌ No CustomerConfig found")
    
    print("\n" + "="*70)

