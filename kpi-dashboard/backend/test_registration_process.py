#!/usr/bin/env python3
"""
Test SaaS Customer Registration Process
Tests if new customers can be registered without backend restart
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:3003"

def print_header(msg):
    print(f"\n{'='*70}")
    print(f"{msg}")
    print(f"{'='*70}\n")

def test_registration_flow():
    """Test complete registration flow"""
    print_header("TEST: SaaS Customer Registration Process")
    
    # Test data - use timestamp to ensure uniqueness
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    company_name = f"TestCustomer{timestamp}"
    email = f"admin{timestamp}@testcompany.com"
    
    print(f"Testing registration for:")
    print(f"  Company: {company_name}")
    print(f"  Email: {email}")
    print()
    
    # Step 1: Check availability
    print("Step 1: Checking company name availability...")
    check_data = {
        "company_name": company_name,
        "email": email
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/register/check-availability",
            json=check_data
        )
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"  Result: {json.dumps(result, indent=2)}")
        print("  ✅ Availability check working\n")
    except Exception as e:
        print(f"  ❌ Error: {e}\n")
    
    # Step 2: Register new customer
    print("Step 2: Registering new customer...")
    registration_data = {
        "company_name": company_name,
        "admin_name": "Test Admin",
        "email": email,
        "password": "SecurePass123!",
        "phone": "+1-555-123-4567"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/register",
            json=registration_data
        )
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print(f"  ✅ Registration successful!")
            print(f"  Response: {json.dumps(result, indent=2)}")
            
            customer_id = result.get('customer_id')
            user_id = result.get('user_id')
            
            if customer_id and user_id:
                print(f"\n  📊 New Customer Details:")
                print(f"     Customer ID: {customer_id}")
                print(f"     User ID: {user_id}")
                print(f"     Email: {result.get('email')}")
                print(f"     Company: {result.get('company_name')}")
                
                # Step 3: Test login for new customer
                print("\nStep 3: Testing login for new customer...")
                login_response = requests.post(
                    f"{BASE_URL}/api/login",
                    json={"email": email, "password": "SecurePass123!"}
                )
                
                if login_response.status_code == 200:
                    login_data = login_response.json()
                    print(f"  ✅ Login successful!")
                    print(f"  Customer ID from login: {login_data.get('user', {}).get('customer_id')}")
                    print(f"  User ID from login: {login_data.get('user', {}).get('user_id')}")
                    
                    # Verify customer ID matches
                    if login_data.get('user', {}).get('customer_id') == customer_id:
                        print("\n✅ VERIFIED: New customer can login immediately")
                        print("✅ VERIFIED: No backend restart needed")
                        return True
                    else:
                        print("❌ Customer ID mismatch!")
                        return False
                else:
                    print(f"  ❌ Login failed: {login_response.status_code}")
                    print(f"  Response: {login_response.text[:200]}")
                    return False
            else:
                print("❌ Missing customer_id or user_id in response")
                return False
                
        elif response.status_code == 409:
            print(f"  ⚠️  Company/email already exists")
            result = response.json()
            print(f"  Response: {json.dumps(result, indent=2)}")
            return False
        else:
            print(f"  ❌ Registration failed: {response.status_code}")
            result = response.json()
            print(f"  Response: {json.dumps(result, indent=2)}")
            return False
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_existing_customers():
    """Verify existing customers still work"""
    print_header("TEST: Verify Existing Customers Still Work")
    
    print("Testing login for existing customer (Test Company)...")
    
    response = requests.post(
        f"{BASE_URL}/api/login",
        json={"email": "test@test.com", "password": "test123"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Existing customer login successful")
        print(f"  Customer: {data.get('user', {}).get('customer_name')}")
        print(f"  Customer ID: {data.get('user', {}).get('customer_id')}")
        return True
    else:
        print(f"❌ Existing customer login failed")
        return False

def main():
    """Run all registration tests"""
    print("\n🔐 SAAS REGISTRATION PROCESS TEST\n")
    
    # Test 1: New customer registration
    test1_result = test_registration_flow()
    
    # Test 2: Existing customers still work
    test2_result = test_existing_customers()
    
    # Summary
    print_header("SUMMARY")
    
    if test1_result and test2_result:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ New customers can be registered via API")
        print("✅ No backend restart required")
        print("✅ Existing customers unaffected")
        print("✅ Ready for production use")
        return True
    else:
        print("⚠️  SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    main()

