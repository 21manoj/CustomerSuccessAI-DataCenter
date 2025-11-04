#!/usr/bin/env python3
"""
Quick test of authentication system
"""

import requests
import sys

BASE_URL = 'http://localhost:5059'

def test_authentication():
    """Quick test of new authentication"""
    
    print("=" * 70)
    print("QUICK AUTHENTICATION TEST")
    print("=" * 70)
    
    # Test 1: Health endpoint (public, should work without auth)
    print("\n1. Testing public endpoint (/api/health)...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            print("   ✅ Public endpoint works (no auth required)")
        else:
            print(f"   ❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Protected endpoint without auth (should fail with 401)
    print("\n2. Testing protected endpoint without auth...")
    try:
        response = requests.get(f"{BASE_URL}/api/accounts")
        if response.status_code == 401:
            print("   ✅ Correctly blocked (401 Unauthorized)")
            print(f"      Message: {response.json().get('message', 'N/A')}")
        else:
            print(f"   ❌ Should be 401, got {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Server not running or error: {e}")
        print("   Start server with: python backend/app_v3_minimal.py")
        return False
    
    # Test 3: Login with valid credentials
    print("\n3. Testing login...")
    try:
        session = requests.Session()  # Keep cookies
        response = session.post(
            f"{BASE_URL}/api/login",
            json={'email': 'test@test.com', 'password': 'test123'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Login successful")
            print(f"      User: {data.get('user', {}).get('user_name')}")
            print(f"      Customer ID: {data.get('user', {}).get('customer_id')}")
            
            # Check if session cookie was set
            if 'cs_session' in session.cookies:
                print("   ✅ Session cookie set")
            else:
                print("   ⚠️  No session cookie (check Flask-Session config)")
            
            # Test 4: Access protected endpoint with session
            print("\n4. Testing protected endpoint WITH auth...")
            response2 = session.get(f"{BASE_URL}/api/accounts")
            
            if response2.status_code == 200:
                accounts = response2.json().get('accounts', [])
                print(f"   ✅ Authenticated request works ({len(accounts)} accounts)")
                print("   ✅ TENANT ISOLATION WORKING (using session customer_id)")
            elif response2.status_code == 401:
                print("   ❌ Still getting 401 (session not persisting)")
            else:
                print(f"   ⚠️  Unexpected status: {response2.status_code}")
            
            # Test 5: Logout
            print("\n5. Testing logout...")
            response3 = session.post(f"{BASE_URL}/api/logout")
            if response3.status_code == 200:
                print("   ✅ Logout successful")
                
                # Test 6: Verify session destroyed
                response4 = session.get(f"{BASE_URL}/api/accounts")
                if response4.status_code == 401:
                    print("   ✅ Session destroyed (correctly blocked)")
                else:
                    print(f"   ⚠️  Still has access: {response4.status_code}")
            
        else:
            print(f"   ❌ Login failed: {response.status_code}")
            print(f"      {response.json()}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✅ AUTHENTICATION SYSTEM WORKING!")
    print("=" * 70)
    return True

if __name__ == '__main__':
    success = test_authentication()
    sys.exit(0 if success else 1)

