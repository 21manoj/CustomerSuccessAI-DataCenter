#!/usr/bin/env python3
"""
Upload Company B clients data to MANANK LLC account
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from models import Customer, User, Account, KPI, KPIUpload
from extensions import db
from werkzeug.security import generate_password_hash
import pandas as pd
from datetime import datetime
import flask
from flask import Flask

def upload_company_b_data():
    """Upload Company B clients data to MANANK LLC"""
    # Create minimal Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/kpi_dashboard.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        # Step 1: Find or create MANANK LLC customer
        print("🔍 Finding MANANK LLC customer...")
        customer = Customer.query.filter_by(customer_name='MANANK LLC').first()
        
        if not customer:
            print("⚠️  MANANK LLC not found. Please register it first via the UI at /register")
            print("   Or create it manually in the database.")
            return
        
        customer_id = customer.customer_id
        print(f"✅ Found MANANK LLC (Customer ID: {customer_id})")
        
        # Step 2: Find or create admin user
        print("\n🔍 Checking admin user...")
        user = User.query.filter_by(customer_id=customer_id).first()
        if not user:
            print("⚠️  No user found for MANANK LLC. Creating admin user...")
            user = User(
                customer_id=customer_id,
                email='admin@manank.com',
                password_hash=generate_password_hash('admin123'),
                user_name='admin',
                role='admin'
            )
            db.session.add(user)
            db.session.commit()
        user_id = user.user_id
        print(f"✅ Using user ID: {user_id}")
        
        # Step 3: Read CSV file
        print("\n📖 Reading CSV file...")
        csv_path = os.path.expanduser('~/Downloads/company_b_clients_dataset.csv')
        
        if not os.path.exists(csv_path):
            print(f"❌ File not found: {csv_path}")
            return
        
        df = pd.read_csv(csv_path)
        print(f"✅ Read {len(df)} accounts from CSV")
        
        # Step 4: Check existing accounts
        existing_accounts = Account.query.filter_by(customer_id=customer_id).all()
        print(f"📊 {len(existing_accounts)} accounts already exist for MANANK LLC")
        
        # Step 5: Create accounts and KPIs
        accounts_created = 0
        for idx, row in df.iterrows():
            account_name = row['Account_Name']
            
            # Check if account already exists
            existing = Account.query.filter_by(
                customer_id=customer_id,
                account_name=account_name
            ).first()
            
            if existing:
                print(f"   ⏭️  Skipping existing account: {account_name}")
                continue
            
            # Create account
            account = Account(
                customer_id=customer_id,
                account_name=account_name,
                revenue=float(row.get('Annual_ARR', 0)),
                industry=row.get('Industry', 'Unknown'),
                region=row.get('Location', 'Unknown'),
                account_status='active'
            )
            db.session.add(account)
            db.session.flush()
            
            # Create KPI Upload
            upload = KPIUpload(
                customer_id=customer_id,
                user_id=user_id,
                account_id=account.account_id,
                version=1,
                original_filename=f'{account_name}_data.csv'
            )
            db.session.add(upload)
            db.session.flush()
            upload_id = upload.upload_id
            
            # Create KPIs from CSV columns (treat numeric columns as KPIs)
            kpi_count = 0
            for col_name in df.columns:
                if col_name in ['Account_ID', 'Account_Name', 'Notes']:
                    continue
                    
                value = row[col_name]
                if pd.isna(value):
                    continue
                
                # Determine category based on column name
                category = 'General'
                if any(x in col_name.lower() for x in ['health', 'dau', 'wau', 'mau', 'adoption', 'usage']):
                    category = 'Product Usage'
                elif any(x in col_name.lower() for x in ['ticket', 'support', 'response', 'sla', 'csat']):
                    category = 'Support'
                elif any(x in col_name.lower() for x in ['nps', 'sentiment', 'engagement']):
                    category = 'Customer Sentiment'
                elif any(x in col_name.lower() for x in ['revenue', 'arr', 'expansion', 'ltv', 'cac', 'roi', 'margin']):
                    category = 'Business Outcomes'
                elif any(x in col_name.lower() for x in ['champion', 'executive', 'threat', 'risk', 'churn']):
                    category = 'Relationship Strength'
                
                kpi = KPI(
                    upload_id=upload_id,
                    account_id=account.account_id,
                    category=category,
                    kpi_parameter=col_name.replace('_', ' ').title(),
                    data=str(value),
                    impact_level='Medium',
                    health_score_component=col_name.replace('_', ' ').title(),
                    weight='10',
                    row_index=str(idx)
                )
                db.session.add(kpi)
                kpi_count += 1
            
            accounts_created += 1
            print(f"   ✅ Created account: {account_name} with {kpi_count} KPIs")
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n🎉 Successfully uploaded data for MANANK LLC!")
        print(f"   ✅ Created {accounts_created} new accounts")
        print(f"   ✅ Total accounts for MANANK LLC: {accounts_created + len(existing_accounts)}")

if __name__ == '__main__':
    upload_company_b_data()
