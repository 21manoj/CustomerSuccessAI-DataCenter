#!/usr/bin/env python3
"""
Comprehensive Test: Run Analysis + RAG Templates
================================================

Tests:
1. Run Analysis functionality on Executive Dashboard
2. RAG templates with 5 different query types
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
        return None

def test_run_analysis(session):
    """Test Run Analysis functionality"""
    print("\n" + "="*70)
    print("TEST: Run Analysis Functionality")
    print("="*70)
    
    # Get accounts
    accounts_resp = session.get(f"{BASE_URL}/api/accounts", 
        headers={'X-Customer-ID': '119'})
    if accounts_resp.status_code != 200:
        print(f"❌ Failed to get accounts: {accounts_resp.status_code}")
        return False
    
    accounts_data = accounts_resp.json()
    accounts = accounts_data.get('accounts', []) if isinstance(accounts_data, dict) else accounts_data
    
    if not isinstance(accounts, list) or len(accounts) == 0:
        print("❌ No accounts found")
        return False
    
    account_id = accounts[0].get('account_id')
    account_name = accounts[0].get('account_name', f'Account {account_id}')
    print(f"Testing with account: {account_name} (ID: {account_id})")
    
    # Test Run Analysis
    print(f"\nCalling /api/signal-analyst/analyze...")
    analyze_resp = session.post(
        f"{BASE_URL}/api/signal-analyst/analyze",
        json={
            'account_id': str(account_id),  # Frontend sends as string
            'analysis_type': 'comprehensive'
        },
        timeout=60
    )
    
    print(f"Response status: {analyze_resp.status_code}")
    
    if analyze_resp.status_code == 200:
        result = analyze_resp.json()
        print(f"✅ Analysis successful!")
        print(f"\nResponse fields:")
        print(f"  ✅ health_score: {result.get('health_score')}")
        print(f"  ✅ churn_probability: {result.get('churn_probability')}%")
        print(f"  ✅ expansion_probability: {result.get('expansion_probability')}%")
        print(f"  ✅ reasoning: {len(result.get('reasoning', ''))} chars")
        print(f"  ✅ key_insights: {len(result.get('key_insights', []))} insights")
        print(f"  ✅ recommended_actions: {len(result.get('recommended_actions', []))} actions")
        
        # Verify required fields exist
        required_fields = ['health_score', 'churn_probability', 'expansion_probability', 'reasoning']
        missing = [f for f in required_fields if f not in result]
        if missing:
            print(f"  ⚠️  Missing fields: {missing}")
            return False
        
        return True
    else:
        error = analyze_resp.json() if 'application/json' in analyze_resp.headers.get('Content-Type', '') else {}
        print(f"❌ Analysis failed: {error.get('error', analyze_resp.text[:300])}")
        return False

def test_rag_query(session, query, endpoint, description):
    """Test a RAG query"""
    print(f"\n{'─'*70}")
    print(f"TEST: {description}")
    print(f"{'─'*70}")
    print(f"Query: {query}")
    
    try:
        response = session.post(
            endpoint,
            json={'query': query},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get('response') or data.get('answer') or data.get('analysis', '')
            if isinstance(response_text, dict):
                response_text = str(response_text)
            
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Response received ({len(response_text)} chars)")
            print(f"   Preview: {response_text[:150]}...")
            
            # Check for template issues
            if 'DCMarketPlace' in response_text or 'GPU compute marketplace' in response_text:
                print("   ⚠️  Response contains DCMarketPlace template (may need updating)")
            else:
                print("   ✅ Response uses appropriate template")
            
            return True
        else:
            print(f"❌ Status: {response.status_code}")
            error_data = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else {}
            print(f"   Error: {error_data.get('error', response.text[:200])}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    """Run all tests"""
    print("="*70)
    print("COMPREHENSIVE TEST: Run Analysis + RAG Templates")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Login
    session = login()
    if not session:
        print("❌ Cannot proceed without authentication")
        return False
    
    results = {}
    
    # Test 1: Run Analysis
    results['run_analysis'] = test_run_analysis(session)
    time.sleep(2)
    
    # Tests 2-6: RAG Templates (5 queries)
    rag_tests = [
        {
            'query': 'What is the total revenue across all accounts?',
            'endpoint': f'{BASE_URL}/api/direct-rag/query',
            'description': 'RAG Template Test 1: Revenue Query'
        },
        {
            'query': 'Which accounts have the highest health scores?',
            'endpoint': f'{BASE_URL}/api/direct-rag/query',
            'description': 'RAG Template Test 2: Health Score Query'
        },
        {
            'query': 'What are the main risk factors for accounts with declining health?',
            'endpoint': f'{BASE_URL}/api/direct-rag/query',
            'description': 'RAG Template Test 3: Risk Analysis Query'
        },
        {
            'query': 'Show me account growth trends over the last 6 months',
            'endpoint': f'{BASE_URL}/api/direct-rag/query',
            'description': 'RAG Template Test 4: Trend Analysis Query'
        },
        {
            'query': 'Which accounts need immediate attention based on their KPIs?',
            'endpoint': f'{BASE_URL}/api/direct-rag/query',
            'description': 'RAG Template Test 5: Actionable Insights Query'
        }
    ]
    
    for i, test in enumerate(rag_tests, 1):
        results[f'rag_test_{i}'] = test_rag_query(
            session,
            test['query'],
            test['endpoint'],
            test['description']
        )
        time.sleep(1)
    
    # Summary
    print("\n" + "="*70)
    print("FINAL TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\nRun Analysis: {'✅ PASS' if results.get('run_analysis') else '❌ FAIL'}")
    for i in range(1, 6):
        test_name = f'rag_test_{i}'
        status = '✅ PASS' if results.get(test_name) else '❌ FAIL'
        print(f"RAG Template Test {i}: {status}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED - Review output above")
    
    return passed == total

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
