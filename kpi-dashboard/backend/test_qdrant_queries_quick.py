#!/usr/bin/env python3
"""
Quick test of Qdrant queries with OpenAI embeddings
Tests a few key queries to verify functionality
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8001"

# Test queries - focusing on the previously failing ones
TEST_QUERIES = [
    {
        'title': 'Top Revenue Accounts',
        'query': 'Which accounts have the highest revenue?',
        'query_type': 'revenue_analysis'
    },
    {
        'title': 'Account Health Overview',
        'query': 'Show me account health scores and performance',
        'query_type': 'account_analysis'
    },
    {
        'title': 'At-Risk Accounts',
        'query': 'Which accounts are at risk of churn?',
        'query_type': 'account_analysis'
    },
    {
        'title': 'Strategic Recommendations',
        'query': 'What strategic recommendations do you have for improving our business?',
        'query_type': 'general'
    }
]

def login():
    """Login and get customer_id"""
    response = requests.post(
        f"{BASE_URL}/api/login",
        json={
            'email': 'admin@syntara.com',
            'password': 'syntara123',
            'vertical': 'saas'
        }
    )
    if response.status_code == 200:
        data = response.json()
        return data.get('customer_id', 1)
    return None

def test_query(customer_id, title, query, query_type):
    """Test a single query"""
    print(f"\n{'='*70}")
    print(f"Testing: {title}")
    print(f"Query: {query}")
    print(f"{'='*70}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/rag-qdrant/query",
            json={
                'query': query,
                'query_type': query_type,
                'conversation_history': []
            },
            headers={
                'X-Customer-ID': str(customer_id),
                'Content-Type': 'application/json'
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            results_count = data.get('results_count', 0)
            response_text = data.get('response', '')
            
            print(f"✅ SUCCESS")
            print(f"   Results found: {results_count}")
            print(f"   Response length: {len(response_text)} chars")
            print(f"   Response preview: {response_text[:200]}...")
            
            # Check if response is meaningful
            if len(response_text.strip()) > 50 and results_count > 0:
                return True, "Working correctly"
            elif len(response_text.strip()) > 50:
                return True, "Working but no results found"
            else:
                return False, "Response too short or empty"
        else:
            error_text = response.text[:200]
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Error: {error_text}")
            return False, f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        print(f"❌ FAILED: Request timeout")
        return False, "Timeout"
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False, str(e)

def main():
    print("="*70)
    print("QDRANT + OPENAI EMBEDDINGS - QUICK TEST")
    print("="*70)
    
    # Login
    print("\n[1/2] Logging in...")
    customer_id = login()
    if not customer_id:
        print("❌ Login failed")
        return 1
    
    print(f"✅ Logged in (customer_id: {customer_id})")
    
    # Test queries
    print("\n[2/2] Testing queries...")
    results = {
        'passed': [],
        'failed': []
    }
    
    for test in TEST_QUERIES:
        success, message = test_query(
            customer_id,
            test['title'],
            test['query'],
            test['query_type']
        )
        
        if success:
            results['passed'].append((test['title'], message))
        else:
            results['failed'].append((test['title'], message))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"✅ Passed: {len(results['passed'])}/{len(TEST_QUERIES)}")
    print(f"❌ Failed: {len(results['failed'])}/{len(TEST_QUERIES)}")
    
    if results['failed']:
        print("\n❌ FAILED QUERIES:")
        for title, error in results['failed']:
            print(f"   - {title}: {error}")
    
    return 0 if len(results['failed']) == 0 else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())

