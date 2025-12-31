#!/usr/bin/env python3
"""
Upload Data Center seed data from Excel file to PostgreSQL database
"""
import sys
import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from extensions import db
from models import Customer, User, Account, KPI, KPIUpload
from werkzeug.security import generate_password_hash
from kpi_definitions_dc import DC_KPIS

# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path=env_path)

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///kpi_dashboard.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Mapping from DC_KPI_ID to KPI Parameter name for the database
DC_KPI_MAPPING = {
    "DC-INF-001": "Server Uptime %",
    "DC-INF-002": "Network Latency",
    "DC-INF-003": "Power Utilization %",
    "DC-INF-004": "Rack Utilization %",
    "DC-INF-005": "Bandwidth Utilization %",
    "DC-INF-006": "Provisioning Time",
    "DC-INF-007": "Backup Success Rate %",
    "DC-INF-008": "Environmental Alerts",
    "DC-INF-009": "Security Incidents",
    "DC-INF-010": "Cooling Efficiency (PUE)",
    "DC-INF-029": "Usage Growth Velocity %",
    "DC-SVC-011": "MTTR",
    "DC-SVC-012": "Support Satisfaction",
    "DC-SVC-013": "Ticket Volume",
    "DC-SVC-014": "Customer Effort Score",
    "DC-SVC-015": "SLA Breach Count",
    "DC-SVC-016": "Remote Hands Response Time",
    "DC-SENT-017": "NPS",
    "DC-SENT-018": "CSAT",
    "DC-SENT-019": "Complaints",
    "DC-BIZ-020": "CLV",
    "DC-BIZ-021": "ROI %",
    "DC-BIZ-022": "GRR",
    "DC-BIZ-023": "NRR",
    "DC-BIZ-030": "Payment Health Score",
    "DC-BIZ-031": "Service Breadth Score",
    "DC-REL-024": "QBR Frequency",
    "DC-REL-025": "Account Engagement",
    "DC-REL-026": "Executive Engagement",
    "DC-REL-027": "Renewal Probability",
    "DC-REL-028": "Multi-Site Deployment",
}

# Mapping from Pillar name to Category name for the database
PILLAR_TO_CATEGORY = {
    "Infrastructure & Performance": "Infrastructure KPI",
    "Service Delivery": "Service KPI",
    "Customer Sentiment": "Customer Sentiment KPI",
    "Business Outcomes": "Business Outcomes KPI",
    "Relationship Strength": "Relationship Strength KPI",
}

def get_or_create_customer(customer_id=None):
    """Get or create DC customer"""
    if customer_id:
        customer = Customer.query.filter_by(customer_id=customer_id).first()
        if customer:
            print(f"✅ Using existing customer: {customer.customer_name} (ID: {customer.customer_id})")
            return customer
    
    # Try to find existing DC customer
    customer = Customer.query.filter(
        (Customer.email == 'dc@example.com') | 
        (Customer.customer_name.ilike('%data center%'))
    ).first()
    
    if customer:
        print(f"✅ Using existing customer: {customer.customer_name} (ID: {customer.customer_id})")
        return customer
    
    # Create new customer
    customer = Customer(
        customer_name='Data Center Customer',
        email='dc@example.com',
        phone='555-DC-DATA',
        domain='datacenter.com'
    )
    db.session.add(customer)
    db.session.flush()
    print(f"✅ Created new customer: {customer.customer_name} (ID: {customer.customer_id})")
    return customer

def get_or_create_user(customer_id):
    """Get or create DC admin user"""
    user = User.query.filter_by(customer_id=customer_id, email="dc-admin@example.com").first()
    if user:
        user.password_hash = generate_password_hash('dc123', method='pbkdf2:sha256')
        user.active = True
        print(f"✅ Updated existing admin user: dc-admin@example.com / dc123")
    else:
        user = User(
            customer_id=customer_id,
            user_name='DC Admin',
            email='dc-admin@example.com',
            password_hash=generate_password_hash('dc123', method='pbkdf2:sha256'),
            active=True
        )
        db.session.add(user)
        print(f"✅ Created admin user: dc-admin@example.com / dc123")
    db.session.flush()
    return user

def format_kpi_value(value: float, kpi_id: str) -> str:
    """Format KPI value with appropriate units"""
    kpi_def = DC_KPIS.get(kpi_id)
    if not kpi_def:
        return str(value)
    
    unit = kpi_def.get("unit", "")
    
    if unit == "%":
        return f"{value:.2f}%"
    elif unit == "$":
        if value >= 1000000:
            return f"${value/1000000:.2f}M"
        elif value >= 1000:
            return f"${value/1000:.2f}K"
        else:
            return f"${value:.2f}"
    elif unit == "ms":
        return f"{value:.2f}ms"
    elif unit == "hours":
        return f"{value:.2f} hours"
    elif unit == "minutes":
        return f"{int(value)} minutes"
    elif unit == "count":
        return str(int(value))
    elif unit == "ratio":
        return f"{value:.2f}"
    elif unit == "score":
        return f"{value:.1f}"
    else:
        return str(value)

def upload_from_excel(excel_file_path):
    """Upload data from Excel file to database"""
    print("\n" + "="*70)
    print("UPLOADING DATA CENTER SEED DATA FROM EXCEL")
    print("="*70)
    
    if not os.path.exists(excel_file_path):
        print(f"❌ Excel file not found: {excel_file_path}")
        return
    
    with app.app_context():
        print("\n[1/4] Setting up customer and user...")
        customer = get_or_create_customer()
        customer_id = customer.customer_id
        user = get_or_create_user(customer_id)
        user_id = user.user_id
        
        print("\n[2/4] Reading Excel file...")
        try:
            df_tenants = pd.read_excel(excel_file_path, sheet_name='Tenants')
            df_kpis = pd.read_excel(excel_file_path, sheet_name='KPI_History')
            print(f"✅ Read {len(df_tenants)} tenants and {len(df_kpis)} KPI records")
        except Exception as e:
            print(f"❌ Error reading Excel file: {e}")
            return
        
        print("\n[3/4] Creating accounts and KPI data...")
        accounts_created = 0
        kpis_created = 0
        
        # Group KPIs by tenant and month
        kpis_by_tenant_month = {}
        for _, row in df_kpis.iterrows():
            tenant_id = str(row['tenant_id'])
            month = str(row['month'])
            key = (tenant_id, month)
            if key not in kpis_by_tenant_month:
                kpis_by_tenant_month[key] = []
            kpis_by_tenant_month[key].append({
                'kpi_id': row['kpi_id'],
                'value': float(row['value'])
            })
        
        # Process each tenant
        tenant_account_map = {}  # Map tenant_id to account_id
        
        for _, tenant_row in df_tenants.iterrows():
            tenant_id = str(tenant_row['tenant_id'])
            tenant_name = str(tenant_row['tenant_name'])
            
            # Check if account already exists
            existing_account = Account.query.filter_by(
                customer_id=customer_id,
                account_name=tenant_name
            ).first()
            
            if existing_account:
                account = existing_account
                # Update account data
                account.revenue = float(tenant_row.get('arr', 0))
                account.industry = str(tenant_row.get('industry', 'Unknown'))
                account.region = "Global"
                account.account_status = "active"
                account.profile_metadata = {
                    "segment": str(tenant_row.get('segment', '')),
                    "mrr": float(tenant_row.get('mrr', 0)),
                    "contract_start": str(tenant_row.get('contract_start', '')),
                    "contract_end": str(tenant_row.get('contract_end', '')),
                    "contract_term_months": int(tenant_row.get('contract_term_months', 0)),
                    "service_type": str(tenant_row.get('service_type', '')),
                    "total_racks": float(tenant_row.get('total_racks', 0)),
                    "power_allocation_kw": float(tenant_row.get('power_allocation_kw', 0)),
                    "bandwidth_allocation_gbps": float(tenant_row.get('bandwidth_allocation_gbps', 0)),
                    "sla_tier": str(tenant_row.get('sla_tier', '')),
                    "sla_uptime_target": float(tenant_row.get('sla_uptime_target', 0)),
                    "csm_assigned": str(tenant_row.get('csm_assigned', '')),
                    "health_category": str(tenant_row.get('health_category', '')),
                    "onboarding_date": str(tenant_row.get('onboarding_date', '')),
                    "facilities_count": int(tenant_row.get('facilities_count', 0)),
                    "services_active_count": int(tenant_row.get('services_active_count', 0)),
                    "is_strategic": bool(tenant_row.get('is_strategic', False)),
                }
            else:
                account = Account(
                    customer_id=customer_id,
                    account_name=tenant_name,
                    revenue=float(tenant_row.get('arr', 0)),
                    industry=str(tenant_row.get('industry', 'Unknown')),
                    region="Global",
                    external_account_id=tenant_id,
                    profile_metadata={
                        "segment": str(tenant_row.get('segment', '')),
                        "mrr": float(tenant_row.get('mrr', 0)),
                        "contract_start": str(tenant_row.get('contract_start', '')),
                        "contract_end": str(tenant_row.get('contract_end', '')),
                        "contract_term_months": int(tenant_row.get('contract_term_months', 0)),
                        "service_type": str(tenant_row.get('service_type', '')),
                        "total_racks": float(tenant_row.get('total_racks', 0)),
                        "power_allocation_kw": float(tenant_row.get('power_allocation_kw', 0)),
                        "bandwidth_allocation_gbps": float(tenant_row.get('bandwidth_allocation_gbps', 0)),
                        "sla_tier": str(tenant_row.get('sla_tier', '')),
                        "sla_uptime_target": float(tenant_row.get('sla_uptime_target', 0)),
                        "csm_assigned": str(tenant_row.get('csm_assigned', '')),
                        "health_category": str(tenant_row.get('health_category', '')),
                        "onboarding_date": str(tenant_row.get('onboarding_date', '')),
                        "facilities_count": int(tenant_row.get('facilities_count', 0)),
                        "services_active_count": int(tenant_row.get('services_active_count', 0)),
                        "is_strategic": bool(tenant_row.get('is_strategic', False)),
                    },
                    account_status="active"
                )
                db.session.add(account)
                accounts_created += 1
            
            db.session.flush()
            tenant_account_map[tenant_id] = account.account_id
        
        # Process KPIs by month
        month_counter = 0
        processed_months = set()
        
        for (tenant_id, month), kpi_list in kpis_by_tenant_month.items():
            if month not in processed_months:
                month_counter += 1
                processed_months.add(month)
            
            account_id = tenant_account_map.get(tenant_id)
            if not account_id:
                continue
            
            # Create upload record for this month (one per tenant per month)
            upload = KPIUpload(
                customer_id=customer_id,
                account_id=account_id,
                user_id=user_id,
                version=month_counter,
                original_filename=f"{tenant_name}_DC_KPIs_Month_{month_counter}.csv"
            )
            db.session.add(upload)
            db.session.flush()
            
            # Create KPI records
            for kpi_data in kpi_list:
                kpi_id = kpi_data['kpi_id']
                value = kpi_data['value']
                
                kpi_def = DC_KPIS.get(kpi_id)
                if not kpi_def:
                    continue
                
                kpi_parameter = DC_KPI_MAPPING.get(kpi_id, kpi_def.get("name"))
                category = PILLAR_TO_CATEGORY.get(kpi_def.get("pillar", ""), kpi_def.get("pillar", "Unknown"))
                formatted_value = format_kpi_value(value, kpi_id)
                
                kpi = KPI(
                    account_id=account_id,
                    upload_id=upload.upload_id,
                    category=category,
                    kpi_parameter=kpi_parameter,
                    data=formatted_value,
                    impact_level="Medium",
                    measurement_frequency="Monthly",
                    source_review="DC Seed Data",
                    weight=0.1
                )
                db.session.add(kpi)
                kpis_created += 1
            
            # Commit in batches
            if kpis_created % 1000 == 0:
                db.session.commit()
                print(f"      ✅ Committed batch (accounts: {accounts_created}, KPIs: {kpis_created})")
        
        # Final commit
        db.session.commit()
        
        print("\n" + "="*70)
        print("✅ UPLOAD COMPLETE")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   - Customer ID: {customer_id}")
        print(f"   - Accounts created/updated: {accounts_created}")
        print(f"   - Total KPI records: {kpis_created:,}")
        print(f"   - Months of data: {month_counter}")
        print()
        print("💡 Login credentials:")
        print(f"   Email: dc-admin@example.com")
        print(f"   Password: dc123")
        print("="*70)

if __name__ == "__main__":
    excel_file = os.path.expanduser('~/Downloads/dc_seed_data/DC_Seed_Data_Review.xlsx')
    upload_from_excel(excel_file)

