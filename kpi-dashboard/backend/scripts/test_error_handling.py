#!/usr/bin/env python3
"""
Error Handling Test - Test Invalid Inputs
Tests all DC2_S endpoints with invalid inputs to ensure proper error handling
"""

import requests
import sys

BASE_URL = "http://localhost:5059"
TEST_EMAIL = "dc2s_super@gpucloud.com"
TEST_PASSWORD = "TestPass123!"

def login():
    """Login and return session"""
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/login",
        json={'email': TEST_EMAIL, 'password': TEST_PASSWORD},
        timeout=10
    )
    if response.status_code == 200:
        return session
    return None

def test_error_handling():
    """Test error handling on all endpoints"""
    print("="*70)
    print("ERROR HANDLING TEST - INVALID INPUTS")
    print("="*70)
    print()
    
    session = login()
    if not session:
        print("❌ Cannot login - skipping error handling tests")
        return False
    
    print("✅ Authenticated successfully")
    print()
    
    tests = []
    
    # Test 1: Invalid KPI code format
    print("Test 1: Invalid KPI code format")
    response = session.post(
        f"{BASE_URL}/api/dc2s/config/custom-kpi",
        json={
            "kpi_code": "INVALID-KPI-CODE",  # Should start with CUSTOM-
            "kpi_definition": {
                "pillar": "AI",
                "name": "Test KPI",
                "target": 85.0,
                "operator": ">",
                "range": [0, 100],
                "unit": "%"
            }
        }
    )
    if response.status_code == 400:
        tests.append(("Invalid KPI code", True, "Returns 400"))
    else:
        tests.append(("Invalid KPI code", False, f"Returns {response.status_code}"))
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")
    print()
    
    # Test 2: Missing required fields
    print("Test 2: Missing required fields")
    response = session.post(
        f"{BASE_URL}/api/dc2s/config/custom-kpi",
        json={
            "kpi_code": "CUSTOM-TEST-1",
            # Missing kpi_definition
        }
    )
    if response.status_code == 400:
        tests.append(("Missing required fields", True, "Returns 400"))
    else:
        tests.append(("Missing required fields", False, f"Returns {response.status_code}"))
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")
    print()
    
    # Test 3: Invalid pillar weights (don't sum to 100%)
    print("Test 3: Invalid pillar weights (don't sum to 100%)")
    response = session.put(
        f"{BASE_URL}/api/dc2s/config/pillar-weights",
        json={
            "pillar_weights": {
                "AI": 0.50,
                "CH": 0.30,
                "DV": 0.20,
                "EX": 0.10,
                "OS": 0.10
            }
        }
    )
    if response.status_code == 400:
        tests.append(("Invalid pillar weights", True, "Returns 400"))
    else:
        tests.append(("Invalid pillar weights", False, f"Returns {response.status_code}"))
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")
    print()
    
    # Test 4: Invalid account ID
    print("Test 4: Invalid account ID")
    response = session.get(
        f"{BASE_URL}/api/dc2s/scores/account/999999/latest"
    )
    if response.status_code == 404:
        tests.append(("Invalid account ID", True, "Returns 404"))
    else:
        tests.append(("Invalid account ID", False, f"Returns {response.status_code}"))
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")
    print()
    
    # Test 5: Invalid date format
    print("Test 5: Invalid date format")
    response = session.post(
        f"{BASE_URL}/api/dc2s/scores/calculate",
        json={
            "measurement_month": "invalid-date"
        }
    )
    if response.status_code in [400, 500]:
        tests.append(("Invalid date format", True, f"Returns {response.status_code}"))
    else:
        tests.append(("Invalid date format", False, f"Returns {response.status_code}"))
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}")
    print()
    
    # Summary
    print("="*70)
    print("ERROR HANDLING TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, p, _ in tests if p)
    total = len(tests)
    
    for test_name, passed_test, message in tests:
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status} - {test_name}: {message}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All error handling tests passed!")
        return True
    else:
        print("⚠️  Some error handling tests failed")
        return False

if __name__ == '__main__':
    success = test_error_handling()
    sys.exit(0 if success else 1)
