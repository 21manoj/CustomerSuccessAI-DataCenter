#!/usr/bin/env python3
"""
Create ACME Customer with 10 Accounts

This script creates a complete second customer for SaaS MVP demo:
- Customer: ACME Corporation
- User: acme@acme.com / acme123
- Accounts: 10 accounts across different industries
- KPIs: 25 KPIs per account (250 total)
- Time Series: 6 months of data
- Playbook Triggers: Default configurations
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models import Customer, User, Account, KPI, KPIUpload, CustomerConfig, PlaybookTrigger, KPITimeSeries
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random
import json

def create_acme_customer():
    """Create ACME customer with complete data"""
    
    with app.app_context():
        print("=" * 70)
        print("CREATING ACME CUSTOMER FOR SAAS MVP DEMO")
        print("=" * 70)
        
        # Step 1: Check if ACME customer already exists
        print("\n1. Checking for existing ACME customer...")
        existing_customer = Customer.query.filter_by(customer_name='ACME Corporation').first()
        existing_user = User.query.filter_by(email='acme@acme.com').first()
        
        if existing_customer:
            print(f"   ⚠️  ACME Corporation already exists (ID: {existing_customer.customer_id})")
            customer = existing_customer
            customer_id = customer.customer_id
        else:
            # Create ACME customer
            customer = Customer(
                customer_name='ACME Corporation',
                email='contact@acme.com',
                phone='555-ACME-00'
            )
            db.session.add(customer)
            db.session.flush()
            customer_id = customer.customer_id
            print(f"   ✅ Created ACME Corporation (ID: {customer_id})")
        
        # Step 2: Create ACME user
        print("\n2. Creating ACME user...")
        if existing_user:
            print(f"   ⚠️  User acme@acme.com already exists")
            user = existing_user
        else:
            user = User(
                customer_id=customer_id,
                user_name='ACME Admin',
                email='acme@acme.com',
                password_hash=generate_password_hash('acme123')
            )
            db.session.add(user)
            db.session.flush()
            print(f"   ✅ Created user: acme@acme.com / acme123")
        
        user_id = user.user_id
        
        # Step 3: Create customer config
        print("\n3. Creating customer configuration...")
        existing_config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not existing_config:
            config = CustomerConfig(
                customer_id=customer_id,
                kpi_upload_mode='account_rollup',
                category_weights=json.dumps({
                    'Relationship Strength': 20,
                    'Adoption & Engagement': 25,
                    'Support & Experience': 20,
                    'Product Value': 20,
                    'Business Outcomes': 15
                }),
                master_file_name='Maturity-Framework-KPI-loveable.xlsx'
            )
            db.session.add(config)
            print("   ✅ Created customer configuration")
        else:
            print("   ✓ Customer configuration already exists")
        
        # Step 4: Create 10 accounts
        print("\n4. Creating 10 accounts for ACME...")
        
        account_data = [
            {'name': 'ACME Retail Division', 'revenue': 2500000, 'industry': 'Retail', 'region': 'North America'},
            {'name': 'ACME Healthcare Services', 'revenue': 3200000, 'industry': 'Healthcare', 'region': 'North America'},
            {'name': 'ACME Financial Group', 'revenue': 5800000, 'industry': 'Financial Services', 'region': 'North America'},
            {'name': 'ACME Tech Solutions', 'revenue': 1800000, 'industry': 'Technology', 'region': 'North America'},
            {'name': 'ACME Manufacturing', 'revenue': 4200000, 'industry': 'Manufacturing', 'region': 'North America'},
            {'name': 'ACME Europe Operations', 'revenue': 3600000, 'industry': 'Retail', 'region': 'Europe'},
            {'name': 'ACME Asia Pacific', 'revenue': 2900000, 'industry': 'Technology', 'region': 'Asia Pacific'},
            {'name': 'ACME Pharmaceuticals', 'revenue': 6500000, 'industry': 'Pharmaceutical', 'region': 'North America'},
            {'name': 'ACME Energy Services', 'revenue': 4800000, 'industry': 'Energy', 'region': 'North America'},
            {'name': 'ACME Logistics Ltd', 'revenue': 2200000, 'industry': 'Transportation', 'region': 'Europe'}
        ]
        
        accounts = []
        existing_accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        if existing_accounts:
            print(f"   ⚠️  {len(existing_accounts)} accounts already exist for ACME")
            accounts = existing_accounts
        else:
            for acc_data in account_data:
                account = Account(
                    customer_id=customer_id,
                    account_name=acc_data['name'],
                    revenue=acc_data['revenue'],
                    industry=acc_data['industry'],
                    region=acc_data['region'],
                    account_status='active'
                )
                db.session.add(account)
                accounts.append(account)
            
            db.session.flush()
            print(f"   ✅ Created {len(accounts)} accounts")
        
        # Step 5: Create KPI Upload records FIRST (KPIs need upload_id)
        print("\n5. Creating KPI upload records...")
        
        upload_map = {}  # Map account_id to upload_id
        existing_uploads = KPIUpload.query.filter_by(customer_id=customer_id).all()
        
        if existing_uploads:
            print(f"   ⚠️  {len(existing_uploads)} KPI uploads already exist")
            for upload in existing_uploads:
                upload_map[upload.account_id] = upload.upload_id
        else:
            for account in accounts:
                upload = KPIUpload(
                    customer_id=customer_id,
                    account_id=account.account_id,
                    user_id=user_id,
                    version=1,
                    original_filename=f'{account.account_name}_KPIs.xlsx'
                )
                db.session.add(upload)
            
            db.session.flush()
            
            # Get the upload IDs
            uploads = KPIUpload.query.filter_by(customer_id=customer_id).all()
            for upload in uploads:
                upload_map[upload.account_id] = upload.upload_id
            
            print(f"   ✅ Created {len(accounts)} KPI upload records")
        
        # Step 6: Create KPIs for each account
        print("\n6. Creating KPIs for all accounts...")
        
        kpi_templates = [
            # Relationship Strength (5 KPIs) - Use 0-100 scale
            {'parameter': 'NPS', 'category': 'Relationship Strength', 'impact': 'Critical', 'frequency': 'Quarterly', 'range': (40, 85)},
            {'parameter': 'CSAT', 'category': 'Relationship Strength', 'impact': 'High', 'frequency': 'Monthly', 'range': (65, 95)},
            {'parameter': 'Executive Sponsor Engagement', 'category': 'Relationship Strength', 'impact': 'High', 'frequency': 'Monthly', 'range': (60, 90)},
            {'parameter': 'Champion Strength', 'category': 'Relationship Strength', 'impact': 'Medium', 'frequency': 'Monthly', 'range': (55, 85)},
            {'parameter': 'Relationship Depth', 'category': 'Relationship Strength', 'impact': 'Medium', 'frequency': 'Quarterly', 'range': (50, 80)},
            
            # Adoption & Engagement (5 KPIs) - Use 0-100 scale
            {'parameter': 'Adoption Index', 'category': 'Adoption & Engagement', 'impact': 'Critical', 'frequency': 'Weekly', 'range': (50, 95)},
            {'parameter': 'Active Users', 'category': 'Adoption & Engagement', 'impact': 'High', 'frequency': 'Weekly', 'range': (55, 90)},
            {'parameter': 'DAU/MAU Ratio', 'category': 'Adoption & Engagement', 'impact': 'High', 'frequency': 'Daily', 'range': (45, 85)},
            {'parameter': 'Feature Usage Rate', 'category': 'Adoption & Engagement', 'impact': 'Medium', 'frequency': 'Weekly', 'range': (50, 90)},
            {'parameter': 'Login Frequency', 'category': 'Adoption & Engagement', 'impact': 'Low', 'frequency': 'Daily', 'range': (60, 95)},
            
            # Support & Experience (5 KPIs) - Use 0-100 scale  
            {'parameter': 'Support Ticket Volume', 'category': 'Support & Experience', 'impact': 'Medium', 'frequency': 'Weekly', 'range': (70, 95)},
            {'parameter': 'SLA Compliance', 'category': 'Support & Experience', 'impact': 'Critical', 'frequency': 'Daily', 'range': (85, 98)},
            {'parameter': 'First Response Time', 'category': 'Support & Experience', 'impact': 'High', 'frequency': 'Daily', 'range': (75, 95)},
            {'parameter': 'Resolution Time', 'category': 'Support & Experience', 'impact': 'High', 'frequency': 'Weekly', 'range': (70, 92)},
            {'parameter': 'Support Satisfaction', 'category': 'Support & Experience', 'impact': 'High', 'frequency': 'Monthly', 'range': (65, 90)},
            
            # Product Value (5 KPIs) - Use 0-100 scale
            {'parameter': 'Product Satisfaction', 'category': 'Product Value', 'impact': 'Critical', 'frequency': 'Quarterly', 'range': (60, 92)},
            {'parameter': 'Feature Request Rate', 'category': 'Product Value', 'impact': 'Medium', 'frequency': 'Monthly', 'range': (50, 85)},
            {'parameter': 'Time to Value', 'category': 'Product Value', 'impact': 'High', 'frequency': 'Monthly', 'range': (55, 88)},
            {'parameter': 'Product Stickiness', 'category': 'Product Value', 'impact': 'High', 'frequency': 'Monthly', 'range': (60, 90)},
            {'parameter': 'Perceived ROI', 'category': 'Product Value', 'impact': 'Critical', 'frequency': 'Quarterly', 'range': (65, 95)},
            
            # Business Outcomes (5 KPIs) - Use 0-100 scale
            {'parameter': 'Revenue Growth', 'category': 'Business Outcomes', 'impact': 'Critical', 'frequency': 'Monthly', 'range': (55, 92)},
            {'parameter': 'Net Revenue Retention', 'category': 'Business Outcomes', 'impact': 'Critical', 'frequency': 'Quarterly', 'range': (85, 98)},
            {'parameter': 'Gross Revenue Retention', 'category': 'Business Outcomes', 'impact': 'High', 'frequency': 'Quarterly', 'range': (80, 95)},
            {'parameter': 'Expansion Revenue Rate', 'category': 'Business Outcomes', 'impact': 'High', 'frequency': 'Quarterly', 'range': (60, 95)},
            {'parameter': 'Churn Risk Score', 'category': 'Business Outcomes', 'impact': 'Critical', 'frequency': 'Monthly', 'range': (10, 40)},  # Lower is better for risk
        ]
        
        total_kpis_created = 0
        existing_kpis = KPI.query.join(Account).filter(Account.customer_id == customer_id).count()
        
        if existing_kpis > 0:
            print(f"   ⚠️  {existing_kpis} KPIs already exist for ACME accounts")
        else:
            for account in accounts:
                upload_id = upload_map.get(account.account_id)
                if not upload_id:
                    print(f"   ⚠️  No upload found for account {account.account_id}, skipping KPIs")
                    continue
                
                for kpi_template in kpi_templates:
                    # Generate realistic value based on range
                    min_val, max_val = kpi_template['range']
                    value = random.randint(min_val, max_val)
                    
                    kpi = KPI(
                        account_id=account.account_id,
                        upload_id=upload_id,  # Link to upload
                        category=kpi_template['category'],
                        kpi_parameter=kpi_template['parameter'],
                        data=str(value),
                        impact_level=kpi_template['impact'],
                        measurement_frequency=kpi_template['frequency'],
                        source_review='System Generated'
                    )
                    db.session.add(kpi)
                    total_kpis_created += 1
            
            db.session.flush()
            print(f"   ✅ Created {total_kpis_created} KPIs ({len(kpi_templates)} per account × {len(accounts)} accounts)")
        
        # Step 7: Create time series data (6 months)
        print("\n7. Creating time series data (6 months)...")
        
        existing_timeseries = KPITimeSeries.query.filter_by(customer_id=customer_id).count()
        if existing_timeseries > 0:
            print(f"   ⚠️  {existing_timeseries} time series records already exist")
        else:
            # Get all KPIs for ACME
            acme_kpis = KPI.query.join(Account).filter(Account.customer_id == customer_id).all()
            
            # Create 6 months of data (May - October 2025)
            months_data = []
            for month_offset in range(6):
                month = 5 + month_offset  # May = 5
                year = 2025
                if month > 12:
                    month -= 12
                    year += 1
                months_data.append((month, year))
            
            timeseries_count = 0
            for kpi in acme_kpis:
                base_value = float(kpi.data) if kpi.data else 50.0
                
                for month, year in months_data:
                    # Add some variation (+/- 15%)
                    variation = random.uniform(-0.15, 0.15)
                    value = base_value * (1 + variation)
                    
                    # Calculate health status
                    if value >= 70:
                        health_status = 'Healthy'
                        health_score = random.uniform(80, 100)
                    elif value >= 50:
                        health_status = 'Risk'
                        health_score = random.uniform(60, 79)
                    else:
                        health_status = 'Critical'
                        health_score = random.uniform(30, 59)
                    
                    ts = KPITimeSeries(
                        kpi_id=kpi.kpi_id,
                        account_id=kpi.account_id,  # Get account_id from the KPI
                        customer_id=customer_id,
                        month=month,
                        year=year,
                        value=round(value, 2),
                        health_status=health_status,
                        health_score=round(health_score, 2)
                    )
                    db.session.add(ts)
                    timeseries_count += 1
            
            db.session.flush()
            print(f"   ✅ Created {timeseries_count} time series records (6 months × {len(acme_kpis)} KPIs)")
        
        # Step 8: Create playbook trigger settings
        print("\n8. Creating playbook trigger settings...")
        
        playbook_types = ['voc', 'activation', 'sla', 'renewal', 'expansion']
        trigger_configs = {
            'voc': {
                'nps_threshold': 10,
                'csat_threshold': 3.6,
                'churn_risk_threshold': 0.30,
                'health_score_drop_threshold': 10,
                'churn_mentions_threshold': 2
            },
            'activation': {
                'adoption_index_threshold': 60,
                'active_users_threshold': 50,
                'dau_mau_threshold': 0.25,
                'feature_usage_threshold': 0.40
            },
            'sla': {
                'sla_breach_threshold': 5,
                'response_time_multiplier': 2.0,
                'escalation_trend': 'increasing',
                'reopen_rate_threshold': 0.20
            },
            'renewal': {
                'renewal_window_days': 90,
                'health_score_threshold': 70,
                'engagement_trend': 'declining',
                'champion_status': 'departed'
            },
            'expansion': {
                'health_score_threshold': 80,
                'adoption_threshold': 0.85,
                'usage_limit_percentage': 0.80,
                'budget_window': 'open'
            }
        }
        
        triggers_created = 0
        for playbook_type in playbook_types:
            existing_trigger = PlaybookTrigger.query.filter_by(
                customer_id=customer_id,
                playbook_type=playbook_type
            ).first()
            
            if not existing_trigger:
                trigger = PlaybookTrigger(
                    customer_id=customer_id,
                    playbook_type=playbook_type,
                    trigger_config=json.dumps(trigger_configs[playbook_type]),
                    auto_trigger_enabled=True
                )
                db.session.add(trigger)
                triggers_created += 1
        
        if triggers_created > 0:
            print(f"   ✅ Created {triggers_created} playbook trigger configurations")
        else:
            print(f"   ✓ Playbook triggers already configured")
        
        # Commit all changes
        db.session.commit()
        
        print("\n" + "=" * 70)
        print("ACME CUSTOMER CREATION COMPLETE!")
        print("=" * 70)
        
        # Summary
        print("\n📊 SUMMARY:")
        print(f"   Customer: ACME Corporation (ID: {customer_id})")
        print(f"   Login: acme@acme.com / acme123")
        print(f"   Accounts: {len(accounts)}")
        
        final_kpi_count = KPI.query.join(Account).filter(Account.customer_id == customer_id).count()
        print(f"   KPIs: {final_kpi_count}")
        
        final_ts_count = KPITimeSeries.query.filter_by(customer_id=customer_id).count()
        print(f"   Time Series Records: {final_ts_count}")
        
        print("\n✅ All functionality available:")
        print("   ✓ Data Integration (KPI uploads)")
        print("   ✓ Analytics & Dashboards")
        print("   ✓ Account Health Monitoring")
        print("   ✓ AI Insights (RAG queries)")
        print("   ✓ Playbooks (all 5 playbooks)")
        print("   ✓ Reports")
        print("   ✓ Settings (trigger configurations)")
        
        print("\n🎉 Ready to login as ACME!")
        print("   Email: acme@acme.com")
        print("   Password: acme123")
        print()
        
        return customer_id

if __name__ == '__main__':
    try:
        customer_id = create_acme_customer()
        print(f"✅ SUCCESS - ACME Corporation created (ID: {customer_id})")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        sys.exit(1)

