#!/usr/bin/env python3
"""
Test RAG Queries for Single and Multi-Product Accounts

Tests RAG system with:
- Single product accounts (legacy accounts)
- Multi-product accounts (new accounts with products)
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:5059"

# Test queries for single vs multi-product scenarios
SINGLE_PRODUCT_QUERIES = [
    "What is the total revenue for this account?",
    "Which accounts have the highest health scores?",
    "Show me accounts that need attention",
    "What are the top performing accounts?",
    "Which accounts have low customer satisfaction scores?",
]

MULTI_PRODUCT_QUERIES = [
    "Which products have low adoption rates?",
    "Compare product performance across accounts",
    "Which accounts have products with low activation?",
    "What is the product activation rate for Core Platform?",
    "Show me accounts where Mobile App has low adoption",
    "Compare API Gateway performance across different accounts",
    "Which products are underperforming?",
    "What are the product-level KPIs for accounts with low adoption?",
]

def login():
    """Login and get session cookie"""
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/login",
        json={"email": "admin@example.com", "password": "admin123"},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None, None
    
    data = response.json()
    customer_id = data.get('user', {}).get('customer_id')
    print(f"✅ Logged in as: {data.get('user', {}).get('email')}")
    print(f"   Customer ID: {customer_id}")
    
    return session, customer_id

def build_rag_knowledge_base(session, customer_id):
    """Build RAG knowledge base"""
    print("\n" + "="*70)
    print("BUILDING RAG KNOWLEDGE BASE")
    print("="*70)
    
    response = session.post(
        f"{BASE_URL}/api/direct-rag/build",
        headers={"X-Customer-ID": str(customer_id)}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Knowledge base built successfully")
        print(f"   Status: {data.get('status', 'unknown')}")
        print(f"   KPIs: {data.get('kpis_count', 0)}")
        print(f"   Accounts: {data.get('accounts_count', 0)}")
        return True
    else:
        print(f"❌ Build failed: {response.status_code}")
        print(response.text[:500])
        return False

def test_rag_query(session, customer_id, query, query_type="general"):
    """Test a single RAG query"""
    try:
        response = session.post(
            f"{BASE_URL}/api/direct-rag/query",
            json={
                "query": query,
                "query_type": query_type,
                "conversation_history": []
            },
            headers={
                "X-Customer-ID": str(customer_id),
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('answer', 'No answer')
            return True, answer, None
        else:
            error_text = response.text[:500]
            return False, None, f"HTTP {response.status_code}: {error_text}"
    except Exception as e:
        return False, None, str(e)

def test_single_product_queries(session, customer_id):
    """Test queries for single-product accounts"""
    print("\n" + "="*70)
    print("TESTING SINGLE-PRODUCT ACCOUNT QUERIES")
    print("="*70)
    
    results = []
    for i, query in enumerate(SINGLE_PRODUCT_QUERIES, 1):
        print(f"\n[{i}/{len(SINGLE_PRODUCT_QUERIES)}] Query: {query}")
        success, answer, error = test_rag_query(session, customer_id, query)
        
        if success:
            print(f"✅ Success")
            print(f"   Answer: {answer[:200]}...")
            results.append({"query": query, "status": "success", "answer": answer[:200]})
        else:
            print(f"❌ Failed: {error}")
            results.append({"query": query, "status": "failed", "error": error})
        
        time.sleep(1)  # Rate limiting
    
    return results

def test_multi_product_queries(session, customer_id):
    """Test queries for multi-product accounts"""
    print("\n" + "="*70)
    print("TESTING MULTI-PRODUCT ACCOUNT QUERIES")
    print("="*70)
    
    results = []
    for i, query in enumerate(MULTI_PRODUCT_QUERIES, 1):
        print(f"\n[{i}/{len(MULTI_PRODUCT_QUERIES)}] Query: {query}")
        success, answer, error = test_rag_query(session, customer_id, query, "general")
        
        if success:
            print(f"✅ Success")
            print(f"   Answer: {answer[:200]}...")
            results.append({"query": query, "status": "success", "answer": answer[:200]})
        else:
            print(f"❌ Failed: {error}")
            results.append({"query": query, "status": "failed", "error": error})
        
        time.sleep(1)  # Rate limiting
    
    return results

def main():
    """Main test function"""
    print("="*70)
    print("RAG MULTI-PRODUCT TEST SUITE")
    print("="*70)
    
    # Login
    session, customer_id = login()
    if not session:
        print("❌ Cannot proceed without login")
        return 1
    
    # Build knowledge base
    if not build_rag_knowledge_base(session, customer_id):
        print("⚠️  Knowledge base build failed, but continuing with tests...")
    
    # Test single-product queries
    single_results = test_single_product_queries(session, customer_id)
    
    # Test multi-product queries
    multi_results = test_multi_product_queries(session, customer_id)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    single_success = sum(1 for r in single_results if r["status"] == "success")
    multi_success = sum(1 for r in multi_results if r["status"] == "success")
    
    print(f"\nSingle-Product Queries:")
    print(f"  ✅ Passed: {single_success}/{len(single_results)}")
    print(f"  ❌ Failed: {len(single_results) - single_success}/{len(single_results)}")
    
    print(f"\nMulti-Product Queries:")
    print(f"  ✅ Passed: {multi_success}/{len(multi_results)}")
    print(f"  ❌ Failed: {len(multi_results) - multi_success}/{len(multi_results)}")
    
    print("\n" + "="*70)
    
    if single_success == len(single_results) and multi_success == len(multi_results):
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())


