#!/usr/bin/env python3
"""
Comprehensive Seed Script for KPI Dashboard

This script seeds:
1. Admin user (admin@example.com / admin123)
2. KPI Reference Ranges (from health_score_config.py)
3. Demo customer with accounts and KPIs (if needed)

Run this after create_db_minimal.py to get a fully populated database.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import Customer, User, KPIReferenceRange
from health_score_config import KPI_REFERENCE_RANGES
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')

# Load environment variables
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
# Use PostgreSQL if DATABASE_URL is set, otherwise use SQLite
database_url = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print(f"✅ Using PostgreSQL database")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
    print(f"⚠️  Using SQLite database: {DB_PATH}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def seed_admin_user():
    """Create admin user for login"""
    print("\n" + "="*70)
    print("SEEDING ADMIN USER")
    print("="*70)
    
    # Note: We'll update existing user below if it exists
    
    # Create or get demo customer
    customer = Customer.query.filter_by(customer_name='Demo Company').first()
    if not customer:
        customer = Customer(
            customer_name='Demo Company',
            email='demo@company.com',
            phone='555-DEMO-00'
        )
        db.session.add(customer)
        db.session.flush()
        print(f"   ✅ Created Demo Company (ID: {customer.customer_id})")
    else:
        print(f"   ✅ Using existing Demo Company (ID: {customer.customer_id})")
    
    # Create or update admin user
    admin = User.query.filter_by(email='admin@example.com').first()
    if admin:
        # Update existing user
        admin.customer_id = customer.customer_id
        admin.password_hash = generate_password_hash('admin123', method='pbkdf2:sha256')
        admin.active = True
        print(f"   ✅ Updated existing admin user: admin@example.com / admin123")
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
        print(f"   ✅ Created admin user: admin@example.com / admin123")
    
    db.session.commit()
    print(f"   ✅ User ID: {admin.user_id}, Customer ID: {admin.customer_id}")
    
    return customer.customer_id

def seed_reference_ranges():
    """Populate KPI reference ranges from health_score_config.py"""
    print("\n" + "="*70)
    print("SEEDING KPI REFERENCE RANGES")
    print("="*70)
    
    # Clear existing ranges (non-interactive - always populate)
    existing_count = KPIReferenceRange.query.count()
    if existing_count > 0:
        print(f"   ⚠️  Found {existing_count} existing reference ranges, clearing...")
        KPIReferenceRange.query.delete()
        print("   ✅ Cleared existing reference ranges")
    
    # Populate with current ranges
    ranges_created = 0
    for kpi_name, config in KPI_REFERENCE_RANGES.items():
        ranges = config['ranges']
        
        # Create new reference range record
        ref_range = KPIReferenceRange(
            kpi_name=kpi_name,
            unit=config['unit'],
            higher_is_better=config['higher_is_better'],
            
            # Critical range (low performance)
            critical_min=ranges['low']['min'],
            critical_max=ranges['low']['max'],
            
            # Risk range (medium performance)
            risk_min=ranges['medium']['min'],
            risk_max=ranges['medium']['max'],
            
            # Healthy range (high performance)
            healthy_min=ranges['high']['min'],
            healthy_max=ranges['high']['max']
        )
        
        db.session.add(ref_range)
        ranges_created += 1
    
    db.session.commit()
    print(f"   ✅ Created {ranges_created} KPI reference ranges")
    
    # Verify
    count = KPIReferenceRange.query.count()
    print(f"   ✅ Database now contains {count} reference ranges")

def main():
    """Main seed function"""
    print("\n" + "="*70)
    print("COMPREHENSIVE SEED SCRIPT FOR KPI DASHBOARD")
    print("="*70)
    database_url = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
    if database_url:
        print(f"\nDatabase: PostgreSQL")
    else:
        print(f"\nDatabase: {DB_PATH}")
    
    with app.app_context():
        # For PostgreSQL, database should already exist
        # For SQLite, check if database exists
        if not database_url and not os.path.exists(DB_PATH):
            print(f"\n❌ ERROR: Database not found at {DB_PATH}")
            print("   Please run 'python3 create_db_minimal.py' first to create the database.")
            sys.exit(1)
        
        # Step 1: Seed admin user
        customer_id = seed_admin_user()
        
        # Step 2: Seed reference ranges
        seed_reference_ranges()
        
        print("\n" + "="*70)
        print("✅ SEED COMPLETE")
        print("="*70)
        print("\nYou can now:")
        print("  1. Log in with: admin@example.com / admin123")
        print("  2. Upload KPI data via the UI or Excel upload")
        print("  3. Configure playbook automation in Settings")
        print("\nTo add accounts and KPIs, use the upload wizard in the UI")
        print("or run your existing seed data scripts.\n")

if __name__ == "__main__":
    main()

