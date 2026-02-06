#!/usr/bin/env python3
"""
Test RAG Templates with 5 Test Queries
======================================

Tests RAG templates to ensure they're working correctly with different query types.
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5059"
TEST_EMAIL = "test_1769120059@e2ecompletetest.com"
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
        print(f"✅ Authenticated")
        return session
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return None

def test_rag_query(session, query, endpoint, description):
    """Test a RAG query"""
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    print(f"Query: {query}")
    print(f"Endpoint: {endpoint}")
    
    try:
        response = session.post(
            endpoint,
            json={'query': query},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            
            # Check response structure
            if 'response' in data or 'answer' in data or 'analysis' in data:
                response_text = data.get('response') or data.get('answer') or data.get('analysis', '')
                if isinstance(response_text, dict):
                    response_text = str(response_text)
                print(f"✅ Response received ({len(response_text)} chars)")
                print(f"   Preview: {response_text[:200]}...")
                
                # Check for template indicators
                if 'DCMarketPlace' in response_text or 'GPU compute marketplace' in response_text:
                    print("   ⚠️  Response contains DCMarketPlace template (may need updating)")
                else:
                    print("   ✅ Response appears to use appropriate template")
                
                return True
            else:
                print(f"⚠️  Unexpected response structure: {list(data.keys())}")
                return False
        else:
            print(f"❌ Status: {response.status_code}")
            error_data = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else {}
            print(f"   Error: {error_data.get('error', response.text[:200])}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    """Run 5 RAG template tests"""
    print("="*70)
    print("RAG TEMPLATES TEST SUITE")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print()
    
    # Login
    session = login()
    if not session:
        print("❌ Cannot proceed without authentication")
        return False
    
    # Test queries covering different RAG endpoints
    test_queries = [
        {
            'query': 'What is the total revenue across all accounts?',
            'endpoint': '/api/direct-rag/query',
            'description': 'Direct RAG - Revenue Query'
        },
        {
            'query': 'Which accounts have the highest health scores?',
            'endpoint': '/api/direct-rag/query',
            'description': 'Direct RAG - Health Score Query'
        },
        {
            'query': 'What are the main risk factors for accounts with declining health?',
            'endpoint': '/api/direct-rag/query',
            'description': 'Direct RAG - Risk Analysis Query'
        },
        {
            'query': 'Show me account growth trends over the last 6 months',
            'endpoint': '/api/direct-rag/query',
            'description': 'Direct RAG - Trend Analysis Query'
        },
        {
            'query': 'Which accounts need immediate attention based on their KPIs?',
            'endpoint': '/api/direct-rag/query',
            'description': 'Direct RAG - Actionable Insights Query'
        }
    ]
    
    results = {}
    for i, test in enumerate(test_queries, 1):
        success = test_rag_query(
            session,
            test['query'],
            f"{BASE_URL}{test['endpoint']}",
            f"{i}. {test['description']}"
        )
        results[test['description']] = success
        time.sleep(1)  # Small delay between requests
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for desc, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {desc}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ ALL RAG TEMPLATE TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED - Review output above")
    
    return passed == total

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
