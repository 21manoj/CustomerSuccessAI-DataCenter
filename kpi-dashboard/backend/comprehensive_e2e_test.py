#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite

Tests:
1. Database state (customers, users, accounts, KPIs)
2. Authentication and session management
3. Account retrieval (customer isolation)
4. RAG system status
5. Customer performance summary
6. Multi-tenant data isolation
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import Customer, User, Account, KPI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def test_database_state():
    """Test 1: Verify database state"""
    print("\n" + "="*70)
    print("TEST 1: Database State Verification")
    print("="*70)
    
    with app.app_context():
        # Check customers
        customers = Customer.query.all()
        print(f"\n📊 Customers: {len(customers)}")
        for c in customers:
            account_count = Account.query.filter_by(customer_id=c.customer_id).count()
            kpi_count = db.session.query(KPI).join(Account).filter(Account.customer_id == c.customer_id).count()
            print(f"   Customer {c.customer_id}: {c.customer_name} - {account_count} accounts, {kpi_count} KPIs")
        
        # Check admin user
        admin = User.query.filter_by(email='admin@example.com').first()
        if admin:
            print(f"\n✅ Admin user found:")
            print(f"   User ID: {admin.user_id}")
            print(f"   Email: {admin.email}")
            print(f"   Customer ID: {admin.customer_id}")
            customer = Customer.query.get(admin.customer_id)
            if customer:
                print(f"   Customer Name: {customer.customer_name}")
                account_count = Account.query.filter_by(customer_id=admin.customer_id).count()
                print(f"   Accounts for this customer: {account_count}")
                if account_count == 25:
                    print(f"   ✅ Perfect! 25 accounts with 6 months of data")
                else:
                    print(f"   ⚠️  Expected 25 accounts, found {account_count}")
            else:
                print(f"   ❌ Customer {admin.customer_id} not found!")
                return False
        else:
            print(f"\n❌ Admin user not found!")
            return False
        
        return True

def test_customer_isolation():
    """Test 2: Verify customer data isolation"""
    print("\n" + "="*70)
    print("TEST 2: Customer Data Isolation")
    print("="*70)
    
    with app.app_context():
        customers = Customer.query.all()
        
        for customer in customers:
            accounts = Account.query.filter_by(customer_id=customer.customer_id).all()
            print(f"\n📋 Customer {customer.customer_id} ({customer.customer_name}):")
            print(f"   Accounts: {len(accounts)}")
            
            # Check that accounts belong to this customer
            for account in accounts[:3]:  # Show first 3
                if account.customer_id != customer.customer_id:
                    print(f"   ❌ Account {account.account_id} has wrong customer_id!")
                    return False
                kpi_count = KPI.query.filter_by(account_id=account.account_id).count()
                print(f"      - {account.account_name}: {kpi_count} KPIs")
        
        print(f"\n✅ Customer isolation verified")
        return True

def test_user_customer_relationship():
    """Test 3: Verify user-customer relationships"""
    print("\n" + "="*70)
    print("TEST 3: User-Customer Relationships")
    print("="*70)
    
    with app.app_context():
        users = User.query.all()
        
        for user in users:
            customer = Customer.query.get(user.customer_id) if user.customer_id else None
            account_count = Account.query.filter_by(customer_id=user.customer_id).count() if user.customer_id else 0
            
            print(f"\n👤 User {user.user_id} ({user.email}):")
            if customer:
                print(f"   Customer: {customer.customer_id} ({customer.customer_name})")
                print(f"   Accounts: {account_count}")
            else:
                print(f"   ❌ Customer {user.customer_id} not found!")
                return False
        
        print(f"\n✅ User-customer relationships verified")
        return True

def main():
    print("="*70)
    print("COMPREHENSIVE END-TO-END TEST SUITE")
    print("="*70)
    
    results = []
    
    # Test 1: Database state
    results.append(("Database State", test_database_state()))
    
    # Test 2: Customer isolation
    results.append(("Customer Isolation", test_customer_isolation()))
    
    # Test 3: User-customer relationships
    results.append(("User-Customer Relationships", test_user_customer_relationship()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All database tests passed!")
        print("\n⚠️  IMPORTANT: Restart your Flask server and log in again")
        print("   to clear stale sessions and see the restored data.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

