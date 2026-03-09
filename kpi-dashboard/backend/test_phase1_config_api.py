#!/usr/bin/env python3
"""
Test Phase 1 Configuration API
Tests all endpoints with authentication
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5059"
# Customer 9 user credentials
TEST_EMAIL = "dc2s_super@gpucloud.com"  # Customer 9 user
TEST_PASSWORD = "TestPass123!"  # Reset password for testing

def login():
    """Login and return session"""
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/login",
        json={'email': TEST_EMAIL, 'password': TEST_PASSWORD},
        timeout=10
    )
    if response.status_code == 200:
        print(f"✅ Authenticated as {TEST_EMAIL}")
        return session
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return None

def test_get_config(session):
    """Test GET /api/dc2s/config"""
    print("\n" + "="*70)
    print("TEST 1: GET Configuration")
    print("="*70)
    
    # Routes require trailing slash
    response = session.get(f"{BASE_URL}/api/dc2s/config/")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ GET config successful")
        print(f"   Customer ID: {data.get('customer_id')}")
        print(f"   Is Default: {data.get('is_default')}")
        print(f"   Enabled KPIs: {len(data.get('enabled_kpis', []))}")
        print(f"   Pillar Weights: {data.get('pillar_weights')}")
        return True
    else:
        print(f"❌ GET config failed: {response.text[:200]}")
        return False

def test_add_custom_kpi(session):
    """Test POST /api/dc2s/config/custom-kpi"""
    print("\n" + "="*70)
    print("TEST 2: Add Custom KPI")
    print("="*70)
    
    custom_kpi = {
        "kpi_code": "CUSTOM-GPU-TEMP",
        "user_email": "admin@customer9.com",
        "kpi_definition": {
            "pillar": "P3",
            "name": "GPU Temperature",
            "description": "Average GPU temperature across cluster",
            "unit": "°C",
            "data_type": "numeric",
            "target": 75.0,
            "operator": "<",
            "range": [60.0, 85.0],
            "thresholds": {
                "excellent": {"min": None, "max": 70.0},
                "good": {"min": 70.0, "max": 75.0},
                "warning": {"min": 75.0, "max": 80.0},
                "critical": {"min": 80.0, "max": None}
            }
        }
    }
    
    response = session.post(
        f"{BASE_URL}/api/dc2s/config/custom-kpi",
        json=custom_kpi
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Custom KPI added successfully")
        print(f"   KPI Code: {data.get('kpi_code')}")
        return True
    else:
        print(f"❌ Add custom KPI failed: {response.text[:200]}")
        return False

def test_update_pillar_weights(session):
    """Test PUT /api/dc2s/config/pillar-weights"""
    print("\n" + "="*70)
    print("TEST 3: Update Pillar Weights")
    print("="*70)
    
    new_weights = {
        "user_email": "admin@customer9.com",
        "pillar_weights": {
            "P3": 0.30,
            "P4": 0.20,
            "P1": 0.15,
            "P5": 0.20,
            "P2": 0.15
        }
    }
    
    response = session.put(
        f"{BASE_URL}/api/dc2s/config/pillar-weights",
        json=new_weights
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Pillar weights updated successfully")
        print(f"   New weights: {data.get('pillar_weights')}")
        return True
    else:
        print(f"❌ Update pillar weights failed: {response.text[:200]}")
        return False

def test_delete_custom_kpi(session):
    """Test DELETE /api/dc2s/config/custom-kpi/CUSTOM-GPU-TEMP"""
    print("\n" + "="*70)
    print("TEST 4: Delete Custom KPI")
    print("="*70)
    
    response = session.delete(f"{BASE_URL}/api/dc2s/config/custom-kpi/CUSTOM-GPU-TEMP")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Custom KPI deleted successfully")
        return True
    else:
        print(f"❌ Delete custom KPI failed: {response.text[:200]}")
        return False

def main():
    """Run all tests"""
    print("="*70)
    print("PHASE 1 CONFIG API TEST SUITE")
    print("="*70)
    
    # Login
    session = login()
    if not session:
        print("\n❌ Cannot proceed without authentication")
        print("   Please check TEST_EMAIL and TEST_PASSWORD in script")
        return False
    
    results = {}
    results['get_config'] = test_get_config(session)
    results['add_custom_kpi'] = test_add_custom_kpi(session)
    results['update_pillar_weights'] = test_update_pillar_weights(session)
    results['delete_custom_kpi'] = test_delete_custom_kpi(session)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ ALL CONFIG API TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED - Review output above")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
