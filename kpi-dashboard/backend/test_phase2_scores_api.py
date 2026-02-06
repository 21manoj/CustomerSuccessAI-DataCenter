#!/usr/bin/env python3
"""
Test Phase 2 Scores API
Tests all score endpoints with authentication
"""

import requests
import json
import sys
from datetime import date, datetime

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
        print(f"✅ Authenticated as {TEST_EMAIL}")
        return session
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return None

def test_calculate_scores(session):
    """Test POST /api/dc2s/scores/calculate"""
    print("\n" + "="*70)
    print("TEST 1: Calculate Scores")
    print("="*70)
    
    # Calculate for December 2024 (has data)
    measurement_month = date(2024, 12, 1)
    
    response = session.post(
        f"{BASE_URL}/api/dc2s/scores/calculate",
        json={'measurement_month': measurement_month.isoformat()}
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Calculate scores successful")
        print(f"   Total accounts: {data.get('total_accounts')}")
        print(f"   Successful: {data.get('successful')}")
        print(f"   Failed: {data.get('failed')}")
        return True
    else:
        print(f"❌ Calculate scores failed: {response.text[:200]}")
        return False

def test_get_latest_scores(session, account_id):
    """Test GET /api/dc2s/scores/account/:id/latest"""
    print("\n" + "="*70)
    print("TEST 2: Get Latest Scores")
    print("="*70)
    
    response = session.get(f"{BASE_URL}/api/dc2s/scores/account/{account_id}/latest")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Get latest scores successful")
        print(f"   Account ID: {data.get('account_id')}")
        print(f"   Health Score: {data.get('health_score', {}).get('health_score')}")
        print(f"   Pillar Scores: {len(data.get('pillar_scores', []))}")
        print(f"   KPI Scores: {len(data.get('kpi_scores', []))}")
        return True
    else:
        print(f"❌ Get latest scores failed: {response.text[:200]}")
        return False

def test_get_customer_summary(session):
    """Test GET /api/dc2s/scores/customer/summary"""
    print("\n" + "="*70)
    print("TEST 3: Get Customer Summary")
    print("="*70)
    
    response = session.get(f"{BASE_URL}/api/dc2s/scores/customer/summary")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Get customer summary successful")
        print(f"   Total accounts: {data.get('total_accounts')}")
        print(f"   Accounts with scores: {data.get('accounts_with_scores')}")
        print(f"   Average health score: {data.get('average_health_score')}")
        print(f"   Status distribution: {data.get('status_distribution')}")
        return True
    else:
        print(f"❌ Get customer summary failed: {response.text[:200]}")
        return False

def test_get_pillar_breakdown(session, account_id, pillar_code='AI'):
    """Test GET /api/dc2s/scores/account/:id/pillars/:pillar"""
    print("\n" + "="*70)
    print("TEST 4: Get Pillar Breakdown")
    print("="*70)
    
    response = session.get(f"{BASE_URL}/api/dc2s/scores/account/{account_id}/pillars/{pillar_code}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Get pillar breakdown successful")
        print(f"   Pillar: {data.get('pillar_code')}")
        print(f"   Pillar Score: {data.get('pillar_score')}")
        print(f"   KPI Details: {len(data.get('kpi_details', []))}")
        return True
    else:
        print(f"❌ Get pillar breakdown failed: {response.text[:200]}")
        return False

def test_get_score_history(session, account_id):
    """Test GET /api/dc2s/scores/account/:id/history"""
    print("\n" + "="*70)
    print("TEST 5: Get Score History")
    print("="*70)
    
    response = session.get(f"{BASE_URL}/api/dc2s/scores/account/{account_id}/history?months=12")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Get score history successful")
        print(f"   Months of history: {data.get('months')}")
        return True
    else:
        print(f"❌ Get score history failed: {response.text[:200]}")
        return False

def get_account_id(session):
    """Get first account ID for customer 9 that has scores"""
    # Try to get an account with scores
    response = session.get(f"{BASE_URL}/api/dc2s/scores/customer/summary")
    if response.status_code == 200:
        data = response.json()
        accounts = data.get('accounts', [])
        if accounts:
            return accounts[0].get('account_id')
    
    # Fallback to any account
    response = session.get(f"{BASE_URL}/api/accounts")
    if response.status_code == 200:
        data = response.json()
        accounts = data.get('accounts', [])
        if accounts:
            return accounts[0].get('account_id')
    return None

def main():
    """Run all tests"""
    print("="*70)
    print("PHASE 2 SCORES API TEST SUITE")
    print("="*70)
    
    # Login
    session = login()
    if not session:
        print("\n❌ Cannot proceed without authentication")
        return False
    
    # Get an account ID for testing
    account_id = get_account_id(session)
    if not account_id:
        print("\n❌ No accounts found for testing")
        return False
    
    print(f"\nUsing account ID: {account_id} for testing")
    
    results = {}
    results['calculate_scores'] = test_calculate_scores(session)
    results['get_latest_scores'] = test_get_latest_scores(session, account_id)
    results['get_customer_summary'] = test_get_customer_summary(session)
    results['get_pillar_breakdown'] = test_get_pillar_breakdown(session, account_id)
    results['get_score_history'] = test_get_score_history(session, account_id)
    
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
        print("✅ ALL SCORES API TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED - Review output above")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
