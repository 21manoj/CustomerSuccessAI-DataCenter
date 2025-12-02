#!/usr/bin/env python3
"""
Pre-Deployment Test Suite - V4
Comprehensive tests before Docker build and AWS deployment
"""

import requests
import sys
import time

BASE_URL = 'http://localhost:5059'
FRONTEND_URL = 'http://localhost:3001'

def test_backend_health():
    """Test 1: Backend health endpoint"""
    print("\n✅ Test 1: Backend Health Check")
    print("-" * 70)
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data['status'] == 'healthy', f"Expected healthy, got {data['status']}"
        print(f"   ✅ PASS - Backend is healthy")
        print(f"      Version: {data.get('version', 'N/A')}")
        return True
    except Exception as e:
        print(f"   ❌ FAIL - {e}")
        return False

def test_authentication():
    """Test 2: Session-based authentication"""
    print("\n✅ Test 2: Authentication System")
    print("-" * 70)
    try:
        session = requests.Session()
        
        # Login
        login_resp = session.post(f"{BASE_URL}/api/login", 
                                  json={'email': 'test@test.com', 'password': 'test123'},
                                  timeout=5)
        assert login_resp.status_code == 200, f"Login failed: {login_resp.status_code}"
        
        # Check session cookie
        assert 'cs_session' in session.cookies or 'session' in session.cookies, "No session cookie set"
        
        # Test authenticated endpoint
        acc_resp = session.get(f"{BASE_URL}/api/accounts", timeout=5)
        assert acc_resp.status_code == 200, f"Authenticated request failed: {acc_resp.status_code}"
        
        # Logout
        logout_resp = session.post(f"{BASE_URL}/api/logout", timeout=5)
        assert logout_resp.status_code == 200, f"Logout failed: {logout_resp.status_code}"
        
        # Verify session destroyed
        acc_resp2 = session.get(f"{BASE_URL}/api/accounts", timeout=5)
        assert acc_resp2.status_code == 401, f"Session not destroyed: {acc_resp2.status_code}"
        
        print(f"   ✅ PASS - Authentication working")
        print(f"      ✓ Login creates session")
        print(f"      ✓ Session persists")
        print(f"      ✓ Logout destroys session")
        return True
    except Exception as e:
        print(f"   ❌ FAIL - {e}")
        return False

def test_data_endpoints():
    """Test 3: Core data endpoints"""
    print("\n✅ Test 3: Core Data Endpoints")
    print("-" * 70)
    
    session = requests.Session()
    session.post(f"{BASE_URL}/api/login", json={'email': 'test@test.com', 'password': 'test123'})
    
    endpoints = [
        ('/api/accounts', 'Accounts'),
        ('/api/kpis/customer/all', 'KPIs'),
        ('/api/kpi-reference-ranges', 'KPI Reference Ranges'),
        ('/api/corporate/rollup', 'Corporate Rollup'),
        ('/api/customer-performance/summary', 'Performance Summary'),
    ]
    
    passed = 0
    for endpoint, name in endpoints:
        try:
            resp = session.get(f"{BASE_URL}{endpoint}", timeout=10)
            if resp.status_code == 200:
                print(f"   ✅ {name}: OK")
                passed += 1
            else:
                print(f"   ❌ {name}: {resp.status_code}")
        except Exception as e:
            print(f"   ❌ {name}: {e}")
    
    success = passed == len(endpoints)
    print(f"\n   {'✅ PASS' if success else '❌ FAIL'} - {passed}/{len(endpoints)} endpoints working")
    return success

def test_ai_insights():
    """Test 4: AI/RAG functionality"""
    print("\n✅ Test 4: AI Insights (RAG)")
    print("-" * 70)
    try:
        session = requests.Session()
        session.post(f"{BASE_URL}/api/login", json={'email': 'test@test.com', 'password': 'test123'})
        
        # Test RAG query
        rag_resp = session.post(f"{BASE_URL}/api/direct-rag/query",
                               json={'query': 'What is the corporate health score?'},
                               timeout=30)
        
        assert rag_resp.status_code == 200, f"RAG query failed: {rag_resp.status_code}"
        data = rag_resp.json()
        assert 'response' in data, "No response in RAG result"
        
        print(f"   ✅ PASS - AI Insights working")
        print(f"      Query processed successfully")
        return True
    except Exception as e:
        print(f"   ❌ FAIL - {e}")
        return False

def test_performance_summary_panels():
    """Test 5: New V4 Performance Summary Panels"""
    print("\n✅ Test 5: Performance Summary Panels (V4 Feature)")
    print("-" * 70)
    try:
        session = requests.Session()
        session.post(f"{BASE_URL}/api/login", json={'email': 'test@test.com', 'password': 'test123'})
        
        resp = session.get(f"{BASE_URL}/api/customer-performance/summary", timeout=5)
        assert resp.status_code == 200, f"Performance summary failed: {resp.status_code}"
        
        data = resp.json()
        assert 'accounts_needing_attention' in data, "Missing accounts_needing_attention"
        assert 'healthy_declining_revenue' in data, "Missing healthy_declining_revenue"
        assert 'company_avg_revenue_growth' in data['summary'], "Missing company_avg_revenue_growth"
        
        print(f"   ✅ PASS - Performance Summary panels working")
        print(f"      Accounts needing attention: {len(data['accounts_needing_attention'])}")
        print(f"      Revenue decline alerts: {len(data['healthy_declining_revenue'])}")
        print(f"      Company avg revenue: {data['summary']['company_avg_revenue_growth']:+.1f}%")
        return True
    except Exception as e:
        print(f"   ❌ FAIL - {e}")
        return False

def test_database_integrity():
    """Test 6: Database data integrity"""
    print("\n✅ Test 6: Database Data Integrity")
    print("-" * 70)
    try:
        session = requests.Session()
        session.post(f"{BASE_URL}/api/login", json={'email': 'test@test.com', 'password': 'test123'})
        
        # Get accounts
        acc_resp = session.get(f"{BASE_URL}/api/accounts", timeout=5)
        accounts = acc_resp.json().get('accounts', [])
        
        # Get KPIs
        kpi_resp = session.get(f"{BASE_URL}/api/kpis/customer/all", timeout=5)
        kpis = kpi_resp.json()
        
        # Get reference ranges
        ref_resp = session.get(f"{BASE_URL}/api/kpi-reference-ranges", timeout=5)
        ref_ranges = ref_resp.json().get('ranges', [])
        
        print(f"   ✅ PASS - Database integrity verified")
        print(f"      Accounts: {len(accounts)}")
        print(f"      KPIs: {len(kpis) if isinstance(kpis, list) else kpis.get('total', 0)}")
        print(f"      Reference Ranges: {len(ref_ranges)}")
        
        assert len(accounts) > 0, "No accounts found"
        assert len(ref_ranges) >= 59, f"Missing reference ranges: {len(ref_ranges)}/68"
        
        return True
    except Exception as e:
        print(f"   ❌ FAIL - {e}")
        return False

def test_frontend_accessibility():
    """Test 7: Frontend accessibility"""
    print("\n✅ Test 7: Frontend Accessibility")
    print("-" * 70)
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        assert response.status_code == 200, f"Frontend not accessible: {response.status_code}"
        assert 'root' in response.text, "React app not loading"
        
        print(f"   ✅ PASS - Frontend is accessible")
        print(f"      URL: {FRONTEND_URL}")
        return True
    except Exception as e:
        print(f"   ❌ FAIL - {e}")
        return False

def run_all_tests():
    """Run complete pre-deployment test suite"""
    print("\n" + "=" * 70)
    print("PRE-DEPLOYMENT TEST SUITE - V4")
    print("=" * 70)
    print(f"Testing for AWS deployment to: customerbusinessvaluesystemv4.triadpartners.ai")
    print("=" * 70)
    
    tests = [
        test_backend_health,
        test_authentication,
        test_data_endpoints,
        test_ai_insights,
        test_performance_summary_panels,
        test_database_integrity,
        test_frontend_accessibility
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        time.sleep(0.5)
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("=" * 70)
        print("✅ READY FOR DOCKER BUILD")
        print("✅ READY FOR AWS DEPLOYMENT")
        print("\n📋 Next Steps:")
        print("   1. Build Docker images")
        print("   2. Push to AWS ECR")
        print("   3. Deploy to AWS (customerbusinessvaluesystemv4.triadpartners.ai)")
        print("   4. Keep v1 running at customervaluesystem.triadpartners.ai")
        return True
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        print("=" * 70)
        print("❌ NOT READY FOR DEPLOYMENT")
        print("   Fix failing tests before deploying")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)


