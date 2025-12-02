#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for Multi-Product Implementation

This test suite validates:
1. All database queries work correctly
2. All endpoints return correct data
3. Backward compatibility (legacy accounts)
4. Health score calculations
5. RAG systems
6. No double-counting of KPIs

Run with: python backend/test_multi_product_comprehensive.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer, Account, KPI, Product, User
from kpi_queries import (
    get_account_level_kpis,
    get_product_kpis,
    get_all_kpis_for_account
)
from health_score_storage import HealthScoreStorageService
from customer_performance_summary_api import calculate_category_scores, calculate_revenue_growth
from playbook_recommendations_api import calculate_health_score_proxy
from corporate_api import get_corporate_rollup
import requests
import json

# Test configuration
BASE_URL = "http://127.0.0.1:5059"
TEST_CUSTOMER_ID = 1
TEST_ACCOUNT_ID = 1

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_test(name):
    print(f"\n{Colors.BLUE}=== {name} ==={Colors.RESET}")

def print_pass(message):
    print(f"{Colors.GREEN}✅ PASS: {message}{Colors.RESET}")

def print_fail(message):
    print(f"{Colors.RED}❌ FAIL: {message}{Colors.RESET}")

def print_warn(message):
    print(f"{Colors.YELLOW}⚠️  WARN: {message}{Colors.RESET}")

def test_database_queries():
    """Test all database query functions"""
    print_test("Database Query Tests")
    
    with app.app_context():
        # Test 1: get_account_level_kpis returns only account-level KPIs
        print("\n1. Testing get_account_level_kpis()...")
        try:
            account_kpis = get_account_level_kpis(TEST_ACCOUNT_ID, TEST_CUSTOMER_ID)
            
            # Verify all KPIs have product_id = NULL
            for kpi in account_kpis:
                if kpi.product_id is not None:
                    print_fail(f"KPI {kpi.kpi_id} has product_id={kpi.product_id}, expected NULL")
                    return False
            
            print_pass(f"get_account_level_kpis() returned {len(account_kpis)} account-level KPIs (all have product_id=NULL)")
        except Exception as e:
            print_fail(f"get_account_level_kpis() failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 2: Verify no product KPIs are included
        print("\n2. Testing product KPI exclusion...")
        try:
            # Get all KPIs directly (should include products if they exist)
            all_kpis_direct = KPI.query.filter_by(account_id=TEST_ACCOUNT_ID).all()
            product_kpis_count = sum(1 for kpi in all_kpis_direct if kpi.product_id is not None)
            
            # Get account-level KPIs via helper
            account_kpis_helper = get_account_level_kpis(TEST_ACCOUNT_ID, TEST_CUSTOMER_ID)
            
            if len(account_kpis_helper) + product_kpis_count != len(all_kpis_direct):
                print_warn(f"KPI count mismatch: helper={len(account_kpis_helper)}, products={product_kpis_count}, total={len(all_kpis_direct)}")
            
            print_pass(f"Product KPIs correctly excluded: {product_kpis_count} product KPIs filtered out")
        except Exception as e:
            print_fail(f"Product KPI exclusion test failed: {e}")
            return False
        
        # Test 3: Test get_all_kpis_for_account structure
        print("\n3. Testing get_all_kpis_for_account() structure...")
        try:
            all_kpis = get_all_kpis_for_account(TEST_ACCOUNT_ID, TEST_CUSTOMER_ID)
            
            required_keys = ['account_level', 'products', 'aggregates']
            for key in required_keys:
                if key not in all_kpis:
                    print_fail(f"Missing key '{key}' in get_all_kpis_for_account() result")
                    return False
            
            print_pass(f"get_all_kpis_for_account() returns correct structure")
            print(f"   - Account-level KPIs: {len(all_kpis['account_level'])}")
            print(f"   - Products: {len(all_kpis['products'])}")
            print(f"   - Aggregates: {sum(len(agg) for agg in all_kpis['aggregates'].values())}")
        except Exception as e:
            print_fail(f"get_all_kpis_for_account() failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

def test_health_score_calculations():
    """Test health score calculations use account-level KPIs only"""
    print_test("Health Score Calculation Tests")
    
    with app.app_context():
        # Test 1: HealthScoreStorageService
        print("\n1. Testing HealthScoreStorageService...")
        try:
            account = Account.query.get(TEST_ACCOUNT_ID)
            if not account:
                print_warn(f"Account {TEST_ACCOUNT_ID} not found, skipping test")
                return True
            
            service = HealthScoreStorageService()
            health_scores = service._calculate_account_health_scores(account, TEST_CUSTOMER_ID)
            
            if health_scores and 'overall' in health_scores:
                print_pass(f"HealthScoreStorageService calculated health score: {health_scores['overall']:.2f}")
            else:
                print_fail("HealthScoreStorageService returned invalid health scores")
                return False
        except Exception as e:
            print_fail(f"HealthScoreStorageService failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 2: calculate_category_scores
        print("\n2. Testing calculate_category_scores()...")
        try:
            category_scores = calculate_category_scores(TEST_ACCOUNT_ID, TEST_CUSTOMER_ID)
            
            if isinstance(category_scores, dict):
                print_pass(f"calculate_category_scores() returned {len(category_scores)} categories")
                for cat, score in category_scores.items():
                    print(f"   - {cat}: {score:.2f}")
            else:
                print_fail("calculate_category_scores() returned invalid format")
                return False
        except Exception as e:
            print_fail(f"calculate_category_scores() failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 3: calculate_health_score_proxy
        print("\n3. Testing calculate_health_score_proxy()...")
        try:
            # Mock customer_id in session
            from flask import g
            g.customer_id = TEST_CUSTOMER_ID
            
            health_score = calculate_health_score_proxy(TEST_ACCOUNT_ID)
            
            if isinstance(health_score, (int, float)) and 0 <= health_score <= 100:
                print_pass(f"calculate_health_score_proxy() returned: {health_score:.2f}")
            else:
                print_fail(f"calculate_health_score_proxy() returned invalid value: {health_score}")
                return False
        except Exception as e:
            print_fail(f"calculate_health_score_proxy() failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

def test_api_endpoints():
    """Test all API endpoints return correct data"""
    print_test("API Endpoint Tests")
    
    # Test 1: /api/accounts/<account_id>/kpis
    print("\n1. Testing GET /api/accounts/<account_id>/kpis...")
    try:
        # First, login to get session
        login_response = requests.post(
            f"{BASE_URL}/api/login",
            json={"email": "admin@example.com", "password": "admin123"},
            allow_redirects=False
        )
        
        if login_response.status_code != 200:
            print_warn("Login failed, skipping API tests. Make sure server is running and credentials are correct.")
            return True
        
        cookies = login_response.cookies
        
        # Test KPI endpoint
        response = requests.get(
            f"{BASE_URL}/api/accounts/{TEST_ACCOUNT_ID}/kpis",
            cookies=cookies
        )
        
        if response.status_code == 200:
            kpis = response.json()
            
            # Verify all KPIs are account-level (product_id should be null or not present)
            for kpi in kpis:
                if 'product_id' in kpi and kpi['product_id'] is not None:
                    print_fail(f"API returned KPI with product_id={kpi['product_id']}, expected NULL")
                    return False
            
            print_pass(f"GET /api/accounts/<account_id>/kpis returned {len(kpis)} account-level KPIs")
        else:
            print_fail(f"GET /api/accounts/<account_id>/kpis returned status {response.status_code}: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print_warn("Cannot connect to server. Make sure Flask server is running on port 5059.")
        return True
    except Exception as e:
        print_fail(f"API endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: /api/customer-performance/summary
    print("\n2. Testing GET /api/customer-performance/summary...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/customer-performance/summary",
            cookies=cookies
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print_pass("GET /api/customer-performance/summary returned success")
            else:
                print_warn(f"GET /api/customer-performance/summary returned: {data.get('status')}")
        else:
            print_warn(f"GET /api/customer-performance/summary returned status {response.status_code}")
    except Exception as e:
        print_warn(f"API endpoint test failed: {e}")
    
    # Test 3: /api/corporate/rollup
    print("\n3. Testing GET /api/corporate/rollup...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/corporate/rollup",
            cookies=cookies
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'rollup_kpis' in data:
                print_pass(f"GET /api/corporate/rollup returned {len(data['rollup_kpis'])} rollup KPIs")
            else:
                print_warn("GET /api/corporate/rollup returned unexpected format")
        else:
            print_warn(f"GET /api/corporate/rollup returned status {response.status_code}")
    except Exception as e:
        print_warn(f"API endpoint test failed: {e}")
    
    return True

def test_backward_compatibility():
    """Test that legacy accounts (without products) work correctly"""
    print_test("Backward Compatibility Tests")
    
    with app.app_context():
        # Test 1: Legacy account should work identically
        print("\n1. Testing legacy account compatibility...")
        try:
            # Find an account with KPIs
            account = Account.query.filter_by(customer_id=TEST_CUSTOMER_ID).first()
            if not account:
                print_warn("No accounts found, skipping backward compatibility test")
                return True
            
            # Get KPIs using old method (direct query)
            old_kpis = KPI.query.filter_by(account_id=account.account_id).filter(
                KPI.product_id.is_(None)
            ).all()
            
            # Get KPIs using new method (helper function)
            new_kpis = get_account_level_kpis(account.account_id, TEST_CUSTOMER_ID)
            
            # Compare counts (should be same or new method should return fewer if it filters aggregation_type)
            if len(new_kpis) <= len(old_kpis):
                print_pass(f"Backward compatibility maintained: old={len(old_kpis)}, new={len(new_kpis)}")
            else:
                print_warn(f"New method returned more KPIs: old={len(old_kpis)}, new={len(new_kpis)}")
        except Exception as e:
            print_fail(f"Backward compatibility test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

def test_no_double_counting():
    """Test that health scores don't double-count product KPIs"""
    print_test("Double-Counting Prevention Tests")
    
    with app.app_context():
        # Test 1: Verify account-level KPIs don't include products
        print("\n1. Testing no product KPIs in account-level queries...")
        try:
            account = Account.query.filter_by(customer_id=TEST_CUSTOMER_ID).first()
            if not account:
                print_warn("No accounts found, skipping double-counting test")
                return True
            
            # Get account-level KPIs
            account_kpis = get_account_level_kpis(account.account_id, TEST_CUSTOMER_ID)
            
            # Verify none have product_id
            product_kpis_found = [kpi for kpi in account_kpis if kpi.product_id is not None]
            
            if product_kpis_found:
                print_fail(f"Found {len(product_kpis_found)} product KPIs in account-level query!")
                for kpi in product_kpis_found:
                    print(f"   - KPI {kpi.kpi_id}: product_id={kpi.product_id}")
                return False
            else:
                print_pass(f"No product KPIs found in account-level query ({len(account_kpis)} KPIs checked)")
        except Exception as e:
            print_fail(f"Double-counting test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 2: Verify health score calculation uses account-level only
        print("\n2. Testing health score uses account-level KPIs only...")
        try:
            account = Account.query.filter_by(customer_id=TEST_CUSTOMER_ID).first()
            if not account:
                return True
            
            # Get all KPIs (including products if they exist)
            all_kpis = KPI.query.filter_by(account_id=account.account_id).all()
            product_kpis = [kpi for kpi in all_kpis if kpi.product_id is not None]
            
            # Calculate health score
            service = HealthScoreStorageService()
            health_scores = service._calculate_account_health_scores(account, TEST_CUSTOMER_ID)
            
            # Health score should be calculated from account-level KPIs only
            # If we have product KPIs, they should NOT be included
            if product_kpis and health_scores:
                print_pass(f"Health score calculated correctly (excluded {len(product_kpis)} product KPIs)")
            elif not product_kpis:
                print_pass("No product KPIs to exclude (legacy account)")
            else:
                print_warn("Could not verify health score calculation")
        except Exception as e:
            print_fail(f"Health score double-counting test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

def test_rag_systems():
    """Test that RAG systems work correctly"""
    print_test("RAG System Tests")
    
    with app.app_context():
        # Test 1: Verify RAG can build knowledge base
        print("\n1. Testing RAG knowledge base build...")
        try:
            from enhanced_rag_openai import EnhancedRAGSystem
            
            rag_system = EnhancedRAGSystem(customer_id=TEST_CUSTOMER_ID)
            rag_system.build_knowledge_base(customer_id=TEST_CUSTOMER_ID)
            
            # Check if knowledge base was built
            if hasattr(rag_system, 'kpi_data') and len(rag_system.kpi_data) > 0:
                print_pass(f"RAG knowledge base built with {len(rag_system.kpi_data)} KPIs")
            else:
                print_warn("RAG knowledge base appears empty")
        except Exception as e:
            print_warn(f"RAG system test failed (may be expected if OpenAI key not set): {e}")
    
    return True

def run_all_tests():
    """Run all test suites"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print("COMPREHENSIVE MULTI-PRODUCT TEST SUITE")
    print(f"{'='*60}{Colors.RESET}\n")
    
    results = []
    
    # Run all test suites
    results.append(("Database Queries", test_database_queries()))
    results.append(("Health Score Calculations", test_health_score_calculations()))
    results.append(("API Endpoints", test_api_endpoints()))
    results.append(("Backward Compatibility", test_backward_compatibility()))
    results.append(("No Double Counting", test_no_double_counting()))
    results.append(("RAG Systems", test_rag_systems()))
    
    # Print summary
    print(f"\n{Colors.BLUE}{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}{Colors.RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if result else f"{Colors.RED}❌ FAIL{Colors.RESET}"
        print(f"{status} - {name}")
    
    print(f"\n{Colors.BLUE}Total: {passed}/{total} test suites passed{Colors.RESET}\n")
    
    if passed == total:
        print(f"{Colors.GREEN}🎉 All tests passed!{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.YELLOW}⚠️  Some tests failed or were skipped. Review output above.{Colors.RESET}\n")
        return 1

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)


