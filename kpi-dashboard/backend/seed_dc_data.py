#!/usr/bin/env python3
"""
Data Center Seed Data Script
============================
Seeds the database with DC tenant data and KPI history using the generate_seed_data.py script

This script:
1. Generates 100 DC tenant profiles
2. Creates Account records in the database
3. Creates 6 months of KPI history for all 31 DC KPIs
4. Creates KPIUpload records
5. Optionally creates time series data

Usage:
    python3 backend/seed_dc_data.py [--customer-id <id>] [--use-existing-customer]
"""

import sys
import os
import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the seed data generator
try:
    # Try to import from the Downloads directory
    sys.path.insert(0, os.path.expanduser('~/Downloads/dc_seed_data'))
    from generate_seed_data import (
        generate_tenants, generate_kpi_values, TenantProfile, KPIRecord,
        START_DATE, END_DATE
    )
except ImportError:
    print("⚠️  Could not import generate_seed_data.py")
    print("   Please ensure generate_seed_data.py is in ~/Downloads/dc_seed_data/")
    print("   Or run it first to generate CSV files, then use --from-csv option")
    sys.exit(1)

from flask import Flask
from extensions import db
from models import Customer, User, Account, KPI, KPIUpload, KPITimeSeries
from werkzeug.security import generate_password_hash
from kpi_definitions_dc import DC_KPIS

# Initialize Flask app
app = Flask(__name__)

# Load database config from .env or use defaults
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Fallback to SQLite
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# KPI ID to KPI Parameter mapping (DC KPIs)
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

# Pillar to Category mapping
PILLAR_TO_CATEGORY = {
    "Infrastructure & Performance": "Infrastructure & Performance",
    "Service Delivery": "Service Delivery",
    "Customer Sentiment": "Customer Sentiment",
    "Business Outcomes": "Business Outcomes",
    "Relationship Strength": "Relationship Strength",
}

def get_or_create_customer(customer_id=None, use_existing=False):
    """Get or create customer for DC data"""
    if customer_id:
        customer = Customer.query.filter_by(customer_id=customer_id).first()
        if customer:
            print(f"✅ Using existing customer: {customer.customer_name} (ID: {customer.customer_id})")
            return customer
        else:
            print(f"❌ Customer ID {customer_id} not found")
            return None
    
    if use_existing:
        # Try to find existing customer
        customer = Customer.query.first()
        if customer:
            print(f"✅ Using existing customer: {customer.customer_name} (ID: {customer.customer_id})")
            return customer
    
    # Create new DC customer
    customer = Customer(
        customer_name="Data Center Customer",
        email="dc@example.com",
        phone="555-DC-0000"
    )
    db.session.add(customer)
    db.session.flush()
    print(f"✅ Created new customer: {customer.customer_name} (ID: {customer.customer_id})")
    return customer

def get_or_create_user(customer_id):
    """Get or create user for DC customer"""
    user = User.query.filter_by(customer_id=customer_id, email="dc-admin@example.com").first()
    if user:
        return user
    
    user = User(
        customer_id=customer_id,
        user_name="DC Admin",
        email="dc-admin@example.com",
        password_hash=generate_password_hash("dc123", method='pbkdf2:sha256'),
        active=True
    )
    db.session.add(user)
    db.session.flush()
    return user

def create_account_from_tenant(tenant: TenantProfile, customer_id: int) -> Account:
    """Create Account record from TenantProfile"""
    # Check if account already exists
    existing = Account.query.filter_by(
        customer_id=customer_id,
        account_name=tenant.tenant_name
    ).first()
    
    if existing:
        print(f"   ⚠️  Account '{tenant.tenant_name}' already exists, updating...")
        existing.revenue = int(tenant.arr)
        existing.industry = tenant.industry
        existing.region = "Global"  # DC tenants are typically global
        existing.account_status = "active"
        return existing
    
    account = Account(
        customer_id=customer_id,
        account_name=tenant.tenant_name,
        revenue=int(tenant.arr),
        industry=tenant.industry,
        region="Global",
        account_status="active"
    )
    db.session.add(account)
    db.session.flush()
    return account

def format_kpi_value(value: float, kpi_id: str) -> str:
    """Format KPI value with appropriate unit"""
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

def create_kpi_record(account_id: int, upload_id: int, kpi_id: str, value: float, 
                     measurement_date: datetime = None) -> KPI:
    """Create KPI record for DC KPI"""
    kpi_def = DC_KPIS.get(kpi_id)
    if not kpi_def:
        print(f"   ⚠️  Unknown KPI ID: {kpi_id}")
        return None
    
    kpi_parameter = DC_KPI_MAPPING.get(kpi_id, kpi_def.get("name"))
    category = PILLAR_TO_CATEGORY.get(kpi_def.get("pillar", ""), kpi_def.get("pillar", "Unknown"))
    
    # Format the value
    formatted_value = format_kpi_value(value, kpi_id)
    
    kpi = KPI(
        account_id=account_id,
        upload_id=upload_id,
        category=category,
        kpi_parameter=kpi_parameter,
        data=formatted_value,
        impact_level="Medium",  # Default impact level
        measurement_frequency="Monthly",
        source_review="DC Seed Data",
        weight=0.1  # Default weight
    )
    
    return kpi

def seed_dc_data(customer_id=None, use_existing_customer=False, from_csv=False):
    """Main seed function"""
    print("\n" + "="*70)
    print("DATA CENTER SEED DATA - DATABASE POPULATION")
    print("="*70)
    print()
    
    with app.app_context():
        # Step 1: Get or create customer
        print("[1/5] Setting up customer...")
        customer = get_or_create_customer(customer_id, use_existing_customer)
        if not customer:
            print("❌ Failed to get/create customer")
            return
        
        customer_id = customer.customer_id
        
        # Step 2: Get or create user
        print("\n[2/5] Setting up user...")
        user = get_or_create_user(customer_id)
        print(f"   ✅ User: {user.email} (ID: {user.user_id})")
        
        # Step 3: Generate tenant profiles
        print("\n[3/5] Generating tenant profiles...")
        if from_csv:
            # Load from CSV if provided
            tenants = load_tenants_from_csv()
            if not tenants:
                print("   ❌ No tenants loaded from CSV. Trying direct generation...")
                tenants = generate_tenants()
        else:
            # Generate using the script
            try:
                tenants = generate_tenants()
            except Exception as e:
                print(f"   ⚠️  Error generating tenants: {e}")
                print("   Trying to load from CSV instead...")
                tenants = load_tenants_from_csv()
                if not tenants:
                    raise Exception("Could not generate or load tenant data")
        
        print(f"   ✅ Generated/loaded {len(tenants)} tenant profiles")
        
        # Step 4: Create accounts and KPIs
        print("\n[4/5] Creating accounts and KPI data...")
        accounts_created = 0
        kpis_created = 0
        
        # Generate monthly data points
        current_date = START_DATE
        month_counter = 0
        
        while current_date <= END_DATE:
            month_counter += 1
            print(f"\n   Processing month {month_counter} ({current_date.strftime('%Y-%m-%d')})...")
            
            for tenant in tenants:
                # Create or get account
                account = create_account_from_tenant(tenant, customer_id)
                if month_counter == 1:
                    accounts_created += 1
                
                # Create KPI upload for this month
                upload = KPIUpload(
                    customer_id=customer_id,
                    account_id=account.account_id,
                    user_id=user.user_id,
                    version=month_counter,
                    original_filename=f"{tenant.tenant_name}_DC_KPIs_Month_{month_counter}.csv"
                )
                db.session.add(upload)
                db.session.flush()
                
                # Generate KPI values for this tenant and date
                kpi_values = generate_kpi_values(tenant, current_date)
                
                # Create KPI records
                for kpi_id, value in kpi_values.items():
                    kpi = create_kpi_record(
                        account.account_id,
                        upload.upload_id,
                        kpi_id,
                        value,
                        current_date
                    )
                    if kpi:
                        db.session.add(kpi)
                        kpis_created += 1
                
                # Commit every 10 tenants to avoid memory issues
                if accounts_created % 10 == 0:
                    db.session.commit()
                    print(f"      ✅ Committed batch (accounts: {accounts_created}, KPIs: {kpis_created})")
            
            # Move to next month
            current_date += timedelta(days=30)
        
        # Final commit
        db.session.commit()
        
        print("\n" + "="*70)
        print("✅ SEED DATA COMPLETE")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   - Customer ID: {customer_id}")
        print(f"   - Accounts created: {accounts_created}")
        print(f"   - Total KPI records: {kpis_created:,}")
        print(f"   - Date range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
        print(f"   - Months of data: {month_counter}")
        print()
        print("💡 Login credentials:")
        print(f"   Email: dc-admin@example.com")
        print(f"   Password: dc123")
        print("="*70)

def load_tenants_from_csv(csv_path="tenants.csv"):
    """Load tenant profiles from CSV file"""
    tenants = []
    
    # Try multiple possible locations
    possible_paths = [
        csv_path,
        os.path.join(os.path.expanduser('~/Downloads/dc_seed_data'), csv_path),
        os.path.join(os.path.dirname(__file__), csv_path),
    ]
    
    csv_file = None
    for path in possible_paths:
        if os.path.exists(path):
            csv_file = path
            break
    
    if not csv_file:
        print(f"⚠️  CSV file not found. Tried:")
        for path in possible_paths:
            print(f"      - {path}")
        return tenants
    
    print(f"   📄 Loading from: {csv_file}")
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tenant = TenantProfile(
                tenant_id=row['tenant_id'],
                tenant_name=row['tenant_name'],
                segment=row['segment'],
                industry=row['industry'],
                arr=float(row['arr']),
                mrr=float(row['mrr']),
                contract_start=row['contract_start'],
                contract_end=row['contract_end'],
                contract_term_months=int(row['contract_term_months']),
                service_type=row['service_type'],
                total_racks=float(row['total_racks']),
                power_allocation_kw=float(row['power_allocation_kw']),
                bandwidth_allocation_gbps=float(row['bandwidth_allocation_gbps']),
                sla_tier=row['sla_tier'],
                sla_uptime_target=float(row['sla_uptime_target']),
                csm_assigned=row['csm_assigned'],
                health_category=row['health_category'],
                onboarding_date=row['onboarding_date'],
                facilities_count=int(row['facilities_count']),
                services_active_count=int(row['services_active_count']),
                is_strategic=row['is_strategic'].lower() == 'true',
                created_at=row['created_at']
            )
            tenants.append(tenant)
    
    return tenants

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Seed Data Center data into database')
    parser.add_argument('--customer-id', type=int, help='Use existing customer ID')
    parser.add_argument('--use-existing-customer', action='store_true',
                       help='Use first existing customer')
    parser.add_argument('--from-csv', action='store_true',
                       help='Load tenant data from tenants.csv file')
    
    args = parser.parse_args()
    
    seed_dc_data(
        customer_id=args.customer_id,
        use_existing_customer=args.use_existing_customer,
        from_csv=args.from_csv
    )

if __name__ == "__main__":
    main()

