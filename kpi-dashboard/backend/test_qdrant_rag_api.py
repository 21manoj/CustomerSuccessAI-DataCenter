#!/usr/bin/env python3
"""
Test Qdrant RAG API endpoints
Tests the /api/rag-qdrant/query endpoint using Qdrant vector database
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5059"

# Test queries
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
        'title': 'KPI Performance',
        'query': 'What are the top performing KPIs?',
        'query_type': 'kpi_analysis'
    }
]

def login(session):
    """Login and establish session"""
    print("\n[1/3] Logging in...")
    try:
        response = session.post(
            f"{BASE_URL}/api/login",
            json={
                'email': 'admin@syntara.com',
                'password': 'syntara123',
                'remember': False
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            customer_id = data.get('user', {}).get('customer_id') or data.get('customer_id')
            print(f"✅ Logged in successfully")
            print(f"   Customer ID: {customer_id}")
            return customer_id
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def build_knowledge_base(session):
    """Build Qdrant knowledge base"""
    print("\n[2/3] Building Qdrant knowledge base...")
    try:
        response = session.post(
            f"{BASE_URL}/api/rag-qdrant/build",
            headers={'Content-Type': 'application/json'},
            timeout=120  # Building can take time
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Knowledge base built successfully")
            if 'collection_info' in data:
                info = data['collection_info']
                print(f"   Collection: {info.get('collection_name', 'N/A')}")
                print(f"   Points: {info.get('points_count', 0)}")
            return True
        else:
            print(f"⚠️  Build returned {response.status_code}: {response.text[:200]}")
            # Continue anyway - knowledge base might already exist
            return True
    except requests.exceptions.Timeout:
        print("⚠️  Build timeout (this is OK if knowledge base already exists)")
        return True
    except Exception as e:
        print(f"⚠️  Build error: {e} (continuing anyway)")
        return True

def test_query(session, title, query, query_type):
    """Test a single RAG query"""
    print(f"\n{'='*70}")
    print(f"Query: {title}")
    print(f"Text: {query}")
    print(f"Type: {query_type}")
    print(f"{'='*70}")
    
    try:
        response = session.post(
            f"{BASE_URL}/api/rag-qdrant/query",
            json={
                'query': query,
                'query_type': query_type,
                'conversation_history': []
            },
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            results_count = data.get('results_count', 0)
            response_text = data.get('response', '')
            
            print(f"✅ SUCCESS")
            print(f"   Results found: {results_count}")
            print(f"   Response length: {len(response_text)} characters")
            print(f"\n   Response preview:")
            print(f"   {response_text[:300]}...")
            
            # Check for relevant results
            if 'relevant_results' in data and len(data['relevant_results']) > 0:
                print(f"\n   Top result similarity: {data['relevant_results'][0].get('similarity', 0):.3f}")
            
            return True, "Working correctly"
        else:
            error_text = response.text[:300]
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Error: {error_text}")
            return False, f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        print(f"❌ FAILED: Request timeout (>60s)")
        return False, "Timeout"
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False, str(e)

def main():
    print("="*70)
    print("QDRANT RAG API TEST")
    print("="*70)
    print(f"Backend URL: {BASE_URL}")
    
    # Create session for cookie-based authentication
    session = requests.Session()
    
    # Login
    customer_id = login(session)
    if not customer_id:
        print("\n❌ Cannot proceed without authentication")
        return 1
    
    # Build knowledge base (optional - might already exist)
    build_knowledge_base(session)
    
    # Test queries
    print("\n[3/3] Testing RAG queries...")
    results = {
        'passed': [],
        'failed': []
    }
    
    for test in TEST_QUERIES:
        success, message = test_query(
            session,
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
    
    if results['passed']:
        print("\n✅ PASSED QUERIES:")
        for title, message in results['passed']:
            print(f"   - {title}: {message}")
    
    if results['failed']:
        print("\n❌ FAILED QUERIES:")
        for title, error in results['failed']:
            print(f"   - {title}: {error}")
    
    return 0 if len(results['failed']) == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
