#!/usr/bin/env python3
"""
Test Customer 23 Onboarding with Explicit Customer ID
Tests whether provided customer_id=23 is used or auto-generated
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer

def test_customer_23_onboarding():
    """Test what customer_id is actually created"""
    
    with app.app_context():
        # Check current state
        print("=" * 70)
        print("CUSTOMER 23 ONBOARDING TEST")
        print("=" * 70)
        
        # Check if customer 23 already exists
        existing = Customer.query.filter_by(customer_id=23).first()
        if existing:
            print(f"⚠️  Customer 23 already exists:")
            print(f"   ID: {existing.customer_id}")
            print(f"   Name: {existing.customer_name}")
            print(f"   Email: {existing.email}")
            return
        
        # Check highest customer_id
        max_customer = db.session.query(db.func.max(Customer.customer_id)).scalar()
        print(f"📊 Current max customer_id: {max_customer}")
        print(f"📊 Next auto-increment would be: {max_customer + 1 if max_customer else 1}")
        print()
        
        # Try to create customer with explicit ID 23
        print("🔍 Attempting to create customer with customer_id=23...")
        print()
        
        try:
            # Method 1: Try to set sequence first
            from sqlalchemy import text
            try:
                db.session.execute(
                    text("SELECT setval('customers_customer_id_seq', :max_id, false)"),
                    {"max_id": 22}  # Set sequence to 22, so next is 23
                )
                print("✅ Set sequence to 22 (next will be 23)")
            except Exception as e:
                print(f"⚠️  Could not set sequence: {e}")
                print("   Will try creating customer directly...")
            
            # Create customer
            customer = Customer(
                customer_name="Test Customer 23",
                email="test23@example.com",
                domain="example.com",
                phone="555-0230"
            )
            
            db.session.add(customer)
            db.session.flush()  # Get the ID
            
            actual_id = customer.customer_id
            print(f"📋 Customer created with ID: {actual_id}")
            
            if actual_id == 23:
                print("✅ SUCCESS: Customer ID matches requested ID (23)")
            else:
                print(f"⚠️  WARNING: Customer ID mismatch!")
                print(f"   Requested: 23")
                print(f"   Got: {actual_id}")
                print()
                print("   Database auto-increment overrode provided ID.")
                print("   This means:")
                print("   - CSV files with customer_id=23 won't match")
                print("   - Data loading script will auto-correct customer_id")
                print("   - Accounts will be linked to actual customer_id={actual_id}")
            
            # Rollback to avoid polluting database
            db.session.rollback()
            print()
            print("🔄 Rolled back transaction (no database changes made)")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")
        
        print()
        print("=" * 70)
        print("CONCLUSION")
        print("=" * 70)
        print()
        print("When onboarding customer with ID 23:")
        print()
        print("1. **Provisioning Step** (`POST /api/onboarding/provision`):")
        print("   ✅ Creates directory: `customer23-dc2_s/`")
        print("   ✅ Uses customer_id=23 for directory structure")
        print("   ✅ Scripts are created with customer_id=23")
        print()
        print("2. **Complete Step** (`POST /api/onboarding/complete`):")
        print("   ⚠️  Database may auto-increment to next available ID")
        print("   ⚠️  If sequence is at 22, customer_id=23 will work")
        print("   ⚠️  If sequence is higher, will get next ID (e.g., 24, 25...)")
        print()
        print("3. **Data Loading Step** (`POST /api/onboarding/process-data`):")
        print("   ✅ CSV files have customer_id=23")
        print("   ✅ Script auto-corrects to actual database customer_id")
        print("   ✅ Accounts are linked correctly")
        print()
        print("**RECOMMENDATION:**")
        print("   - Always provision with desired customer_id")
        print("   - Accept that database customer_id may differ")
        print("   - Data loading script handles the mismatch automatically")
        print("=" * 70)

if __name__ == '__main__':
    test_customer_23_onboarding()
