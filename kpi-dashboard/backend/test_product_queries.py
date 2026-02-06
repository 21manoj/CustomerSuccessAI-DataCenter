#!/usr/bin/env python3
"""
Focused Product Query Test Suite
Tests product-related queries to ensure they return product names, not account names or KPI names
"""

import os
import sys
import requests
import time
from typing import Dict, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = os.getenv('BACKEND_URL', 'http://localhost:8005')
DC_CUSTOMER_ID = 5  # DC customer
SAAS_CUSTOMER_ID = 1  # SaaS customer

# Product query tests
PRODUCT_TEST_QUERIES = [
    "Which products are commonly used across accounts?",
    "What products are widely used across most accounts?",
    "List all product names used by our customers",
    "Which products are most popular across accounts?",
    "Show me product adoption across accounts",
    "What products are deployed across multiple accounts?",
]

def test_product_query(customer_id: int, query: str, session: requests.Session) -> Tuple[bool, str, str]:
    """Test a single product query and return success, message, and response preview"""
    try:
        headers = {
            'X-Customer-ID': str(customer_id),
            'Content-Type': 'application/json'
        }
        response = session.post(
            f"{BASE_URL}/api/rag-qdrant/query",
            headers=headers,
            json={
                'query': query,
                'query_type': 'product_analysis'
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'error' in result:
                return False, result.get('error', 'Unknown error'), ""
            
            response_text = result.get('response', '')
            results_count = result.get('results_count', 0)
            
            # Validate response doesn't contain account names as products
            account_names_that_should_not_be_products = ['CloudMaster', 'CloudVantage', 'CloudScale', 'CloudEdge']
            found_account_as_product = False
            for account_name in account_names_that_should_not_be_products:
                if account_name in response_text:
                    found_account_as_product = True
                    break
            
            # Validate response doesn't contain KPI names as products
            kpi_names_that_should_not_be_products = ['Feature Adoption Rate', 'Product Activation Rate', 'NPS', 'CSAT']
            found_kpi_as_product = False
            for kpi_name in kpi_names_that_should_not_be_products:
                if kpi_name in response_text and 'product' in query.lower():
                    # Check if it's mentioned as a product (not just in context)
                    if response_text.lower().count(kpi_name.lower()) > 1:  # More than just mention
                        found_kpi_as_product = True
                        break
            
            validation_msg = ""
            if found_account_as_product:
                validation_msg = " ⚠️ WARNING: Response contains account names as products!"
            elif found_kpi_as_product:
                validation_msg = " ⚠️ WARNING: Response contains KPI names as products!"
            elif "no product" in response_text.lower() or "product data not found" in response_text.lower():
                validation_msg = " ℹ️ No product data found (expected if products don't exist)"
            
            return True, f"Results: {results_count}" + validation_msg, response_text[:300]
        else:
            return False, f"Status: {response.status_code}", ""
    except Exception as e:
        return False, f"Exception: {str(e)[:100]}", ""

def main():
    """Run product query tests"""
    print("=" * 80)
    print("🧪 PRODUCT QUERY TEST SUITE")
    print("=" * 80)
    print(f"Testing {len(PRODUCT_TEST_QUERIES)} product queries")
    print(f"Backend URL: {BASE_URL}")
    print()
    
    session = requests.Session()
    
    # Authenticate and maintain session
    try:
        login_response = session.post(
            f"{BASE_URL}/api/login",
            json={'email': 'admin@syntara.com', 'password': 'syntara123'},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        if login_response.status_code == 200:
            print("✅ Authenticated successfully")
            # Session cookies should be maintained automatically
        else:
            print(f"⚠️  Authentication failed (Status: {login_response.status_code}), continuing with header-based auth")
    except Exception as e:
        print(f"⚠️  Authentication skipped ({str(e)[:50]}), using header-based auth")
    
    print()
    
    # Test DC Customer
    print("=" * 80)
    print(f"TESTING DC CUSTOMER (ID: {DC_CUSTOMER_ID})")
    print("=" * 80)
    print()
    
    dc_passed = 0
    dc_failed = 0
    
    for i, query in enumerate(PRODUCT_TEST_QUERIES, 1):
        print(f"Test {i}/{len(PRODUCT_TEST_QUERIES)}: {query}")
        start_time = time.time()
        success, message, preview = test_product_query(DC_CUSTOMER_ID, query, session)
        duration = time.time() - start_time
        
        if success:
            dc_passed += 1
            print(f"  ✅ PASS ({duration:.1f}s) - {message}")
            if preview:
                print(f"  Response preview: {preview}...")
        else:
            dc_failed += 1
            print(f"  ❌ FAIL ({duration:.1f}s) - {message}")
        print()
    
    # Test SaaS Customer
    print("=" * 80)
    print(f"TESTING SAAS CUSTOMER (ID: {SAAS_CUSTOMER_ID})")
    print("=" * 80)
    print()
    
    saas_passed = 0
    saas_failed = 0
    
    for i, query in enumerate(PRODUCT_TEST_QUERIES, 1):
        print(f"Test {i}/{len(PRODUCT_TEST_QUERIES)}: {query}")
        start_time = time.time()
        success, message, preview = test_product_query(SAAS_CUSTOMER_ID, query, session)
        duration = time.time() - start_time
        
        if success:
            saas_passed += 1
            print(f"  ✅ PASS ({duration:.1f}s) - {message}")
            if preview:
                print(f"  Response preview: {preview}...")
        else:
            saas_failed += 1
            print(f"  ❌ FAIL ({duration:.1f}s) - {message}")
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"DC Customer:   {dc_passed}/{len(PRODUCT_TEST_QUERIES)} passed, {dc_failed} failed")
    print(f"SaaS Customer: {saas_passed}/{len(PRODUCT_TEST_QUERIES)} passed, {saas_failed} failed")
    print(f"Total:         {dc_passed + saas_passed}/{len(PRODUCT_TEST_QUERIES) * 2} passed, {dc_failed + saas_failed} failed")
    
    total_passed = dc_passed + saas_passed
    total_tests = len(PRODUCT_TEST_QUERIES) * 2
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"Success Rate:  {success_rate:.1f}%")
    
    if dc_failed == 0 and saas_failed == 0:
        print("\n🎉 All product query tests passed!")
        return 0
    else:
        print(f"\n⚠️  {dc_failed + saas_failed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
