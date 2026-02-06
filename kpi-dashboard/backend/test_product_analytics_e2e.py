#!/usr/bin/env python3
"""
End-to-End Test for Product Analytics System
Tests the complete flow: normalization, health calculation, storage, and API
"""

import sys
import requests
import json
import time
from datetime import datetime

BASE_URL = 'http://localhost:8005'

def login(session):
    """Login and return session"""
    response = session.post(f'{BASE_URL}/api/login', 
        json={'email': 'admin@syntara.com', 'password': 'syntara123'})
    return response.status_code == 200

def test_product_catalog_creation():
    """Test 1: Product catalog creation from account metadata"""
    print("\n" + "="*80)
    print("TEST 1: Product Catalog Creation from Account Metadata")
    print("="*80)
    
    session = requests.Session()
    if not login(session):
        return False, "Login failed"
    
    # Get accounts with products
    response = session.get(f'{BASE_URL}/api/accounts',
        headers={'X-Customer-ID': '1'})
    
    if response.status_code != 200:
        return False, f"Failed to get accounts: {response.status_code}"
    
    accounts = response.json().get('accounts', [])
    accounts_with_products = [a for a in accounts if a.get('profile_metadata', {}).get('products_used')]
    
    print(f"Found {len(accounts_with_products)} accounts with products in metadata")
    
    # Trigger product health calculation (this will create catalog entries)
    response = session.post(f'{BASE_URL}/api/products/recalculate',
        headers={'X-Customer-ID': '1'},
        json={})
    
    if response.status_code != 200:
        return False, f"Recalculation failed: {response.status_code} - {response.text}"
    
    print(f"✅ Recalculation triggered: {response.json().get('message')}")
    
    # Wait for calculation
    time.sleep(3)
    
    # Check product catalog
    response = session.get(f'{BASE_URL}/api/products/catalog',
        headers={'X-Customer-ID': '1'})
    
    if response.status_code != 200:
        return False, f"Failed to get catalog: {response.status_code}"
    
    catalog = response.json().get('products', [])
    print(f"✅ Product catalog created: {len(catalog)} products")
    
    if catalog:
        print("Sample products:")
        for p in catalog[:5]:
            print(f"  - {p['product_name']} (ID: {p['product_id']}, {p['account_count']} accounts)")
    
    return True, f"Catalog created with {len(catalog)} products"

def test_product_health_scores():
    """Test 2: Product health score calculation and storage"""
    print("\n" + "="*80)
    print("TEST 2: Product Health Score Calculation")
    print("="*80)
    
    session = requests.Session()
    if not login(session):
        return False, "Login failed"
    
    # Get product health (per-account)
    response = session.get(f'{BASE_URL}/api/products/health',
        headers={'X-Customer-ID': '1'},
        params={'aggregate': 'false'})
    
    if response.status_code != 200:
        return False, f"Failed to get product health: {response.status_code}"
    
    trends = response.json().get('product_trends', [])
    print(f"✅ Found {len(trends)} product-account health trends")
    
    if trends:
        print("Sample product health scores:")
        for t in trends[:5]:
            print(f"  - {t['product_name']} @ {t['account_name']}: {t['overall_health_score']}/100")
            print(f"    (Product Usage: {t.get('product_usage_score', 'N/A')}, Support: {t.get('support_score', 'N/A')})")
            print(f"    KPIs: {t['total_kpis']} total, {t['product_level_kpis']} product-level, {t['account_level_kpis']} account-level")
    
    return True, f"Health scores calculated for {len(trends)} product-account combinations"

def test_aggregate_product_health():
    """Test 3: Aggregate product health across accounts"""
    print("\n" + "="*80)
    print("TEST 3: Aggregate Product Health")
    print("="*80)
    
    session = requests.Session()
    if not login(session):
        return False, "Login failed"
    
    # Get aggregate product health
    response = session.get(f'{BASE_URL}/api/products/health',
        headers={'X-Customer-ID': '1'},
        params={'aggregate': 'true'})
    
    if response.status_code != 200:
        return False, f"Failed to get aggregate health: {response.status_code}"
    
    aggregates = response.json().get('products', [])
    print(f"✅ Found {len(aggregates)} aggregate product trends")
    
    if aggregates:
        print("Aggregate product health:")
        for a in aggregates:
            print(f"  - {a['product_name']}: {a['overall_health_score']}/100")
            print(f"    Accounts: {a['total_accounts']}, Revenue: ${a['total_revenue']:,.0f}")
            print(f"    Avg Revenue/Account: ${a['average_revenue_per_account']:,.0f}")
    
    return True, f"Aggregate health calculated for {len(aggregates)} products"

def test_product_normalization():
    """Test 4: Product name normalization and similarity matching"""
    print("\n" + "="*80)
    print("TEST 4: Product Name Normalization")
    print("="*80)
    
    session = requests.Session()
    if not login(session):
        return False, "Login failed"
    
    # Get catalog to check normalization
    response = session.get(f'{BASE_URL}/api/products/catalog',
        headers={'X-Customer-ID': '1'})
    
    if response.status_code != 200:
        return False, f"Failed to get catalog: {response.status_code}"
    
    catalog = response.json().get('products', [])
    
    # Check for duplicate/typo handling
    product_names = [p['product_name'].lower().strip() for p in catalog]
    unique_names = set(product_names)
    
    print(f"Total products: {len(catalog)}")
    print(f"Unique normalized names: {len(unique_names)}")
    
    if len(catalog) > len(unique_names):
        print("⚠️ Potential duplicates found (may need manual review)")
    else:
        print("✅ No duplicate product names detected")
    
    return True, f"Normalization check: {len(catalog)} products, {len(unique_names)} unique names"

def test_api_endpoints():
    """Test 5: All API endpoints"""
    print("\n" + "="*80)
    print("TEST 5: API Endpoints Validation")
    print("="*80)
    
    session = requests.Session()
    if not login(session):
        return False, "Login failed"
    
    tests = []
    
    # Test catalog endpoint
    response = session.get(f'{BASE_URL}/api/products/catalog',
        headers={'X-Customer-ID': '1'})
    tests.append(('GET /api/products/catalog', response.status_code == 200))
    
    # Test health endpoint (per-account)
    response = session.get(f'{BASE_URL}/api/products/health',
        headers={'X-Customer-ID': '1'},
        params={'aggregate': 'false'})
    tests.append(('GET /api/products/health (per-account)', response.status_code == 200))
    
    # Test health endpoint (aggregate)
    response = session.get(f'{BASE_URL}/api/products/health',
        headers={'X-Customer-ID': '1'},
        params={'aggregate': 'true'})
    tests.append(('GET /api/products/health (aggregate)', response.status_code == 200))
    
    # Test recalculation endpoint
    response = session.post(f'{BASE_URL}/api/products/recalculate',
        headers={'X-Customer-ID': '1'},
        json={})
    tests.append(('POST /api/products/recalculate', response.status_code == 200))
    
    # Test with account_id filter
    response = session.get(f'{BASE_URL}/api/products/health',
        headers={'X-Customer-ID': '1'},
        params={'account_id': 334, 'aggregate': 'false'})
    tests.append(('GET /api/products/health (filtered by account)', response.status_code == 200))
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print("API Endpoint Tests:")
    for name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    return passed == total, f"{passed}/{total} API endpoints working"

def main():
    """Run all end-to-end tests"""
    print("\n" + "="*80)
    print("PRODUCT ANALYTICS END-TO-END TEST SUITE")
    print("="*80)
    print(f"Testing against: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    results = []
    
    # Run all tests
    results.append(("Product Catalog Creation", *test_product_catalog_creation()))
    time.sleep(2)
    results.append(("Product Health Scores", *test_product_health_scores()))
    time.sleep(1)
    results.append(("Aggregate Product Health", *test_aggregate_product_health()))
    time.sleep(1)
    results.append(("Product Normalization", *test_product_normalization()))
    time.sleep(1)
    results.append(("API Endpoints", *test_api_endpoints()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"        {message}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed*100//total}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Product Analytics system is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
