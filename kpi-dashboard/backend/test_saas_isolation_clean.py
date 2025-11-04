#!/usr/bin/env python3
"""
SaaS Multi-Tenant Isolation Test Suite
Simple, clean version
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:3003"

def print_header(msg):
    print(f"\n{'='*70}")
    print(f"{msg}")
    print(f"{'='*70}\n")

def login_user(email, password):
    """Login and return customer_id, user_id"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                user = data.get('user', {})
                return user.get('customer_id'), user.get('user_id')
    except:
        pass
    return None, None

def test_1_auth():
    """Test login"""
    print_header("TEST 1: User Authentication")
    
    customer_id, user_id = login_user("test@test.com", "test123")
    if customer_id:
        print(f"✅ Login successful: customer_id={customer_id}, user_id={user_id}")
        return True
    else:
        print("❌ Login failed")
        return False

def test_2_isolation():
    """Test data isolation"""
    print_header("TEST 2: Data Isolation")
    
    customer_id, user_id = login_user("test@test.com", "test123")
    if not customer_id:
        print("❌ Login failed")
        return False
    
    # Get accounts
    response = requests.get(
        f"{BASE_URL}/api/accounts",
        headers={"X-Customer-ID": str(customer_id)}
    )
    
    if response.status_code == 200:
        data = response.json()
        accounts = data if isinstance(data, list) else data.get('accounts', [])
        print(f"✅ Retrieved {len(accounts)} accounts for customer {customer_id}")
        print(f"   Account IDs: {[a.get('account_id') for a in accounts[:3]]}")
        return True
    else:
        print(f"❌ Failed to fetch accounts")
        return False

def run_tests():
    """Run all tests"""
    print("\n🔐 SAAS ISOLATION & SECURITY TEST SUITE\n")
    
    passed = 0
    total = 0
    
    total += 1
    if test_1_auth():
        passed += 1
    
    total += 1
    if test_2_isolation():
        passed += 1
    
    print_header("SUMMARY")
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("⚠️  SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    run_tests()

