#!/usr/bin/env python3
"""
Quick Verification Test for Qdrant Cloud
Tests that queries work for both SaaS and DC customers
"""

import requests
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8005"

def test_customer_queries(customer_id: int, customer_name: str) -> Dict[str, Any]:
    """Test queries for a specific customer"""
    session = requests.Session()
    
    # Login
    login = session.post(f"{BASE_URL}/api/login", 
        json={'email': 'admin@syntara.com', 'password': 'syntara123'})
    
    if login.status_code != 200:
        return {'status': 'FAIL', 'message': f'Login failed: {login.status_code}'}
    
    print(f"\n{'='*70}")
    print(f"Testing {customer_name} Customer (ID: {customer_id})")
    print(f"{'='*70}")
    
    test_queries = [
        ("Which accounts have the highest revenue?", "revenue_analysis"),
        ("What are the top performing KPIs?", "kpi_analysis"),
        ("Show me account health scores", "account_analysis"),
        ("Which accounts are at risk?", "account_analysis"),
    ]
    
    results = {
        'customer_id': customer_id,
        'customer_name': customer_name,
        'queries_passed': 0,
        'queries_failed': 0,
        'details': []
    }
    
    for query, query_type in test_queries:
        start_time = time.time()
        try:
            resp = session.post(f"{BASE_URL}/api/rag-qdrant/query", 
                headers={'X-Customer-ID': str(customer_id), 'Content-Type': 'application/json'},
                json={'query': query, 'query_type': query_type},
                timeout=60
            )
            duration = time.time() - start_time
            
            if resp.status_code == 200:
                result = resp.json()
                if result and 'response' in result:
                    results_count = result.get('results_count', 0)
                    response_preview = str(result.get('response', ''))[:150]
                    results['queries_passed'] += 1
                    print(f"✅ {query[:50]}...")
                    print(f"   Results: {results_count}, Duration: {duration:.2f}s")
                    print(f"   Response: {response_preview}...")
                    results['details'].append({
                        'query': query,
                        'status': 'PASS',
                        'results_count': results_count,
                        'duration': duration
                    })
                else:
                    results['queries_failed'] += 1
                    print(f"❌ {query[:50]}... - Empty response")
                    results['details'].append({
                        'query': query,
                        'status': 'FAIL',
                        'error': 'Empty response'
                    })
            else:
                results['queries_failed'] += 1
                error_msg = resp.text[:200]
                print(f"❌ {query[:50]}... - Status {resp.status_code}: {error_msg}")
                results['details'].append({
                    'query': query,
                    'status': 'FAIL',
                    'error': f'Status {resp.status_code}'
                })
        except Exception as e:
            results['queries_failed'] += 1
            print(f"❌ {query[:50]}... - Exception: {str(e)[:100]}")
            results['details'].append({
                'query': query,
                'status': 'FAIL',
                'error': str(e)[:100]
            })
    
    return results

def main():
    print("="*70)
    print("QDRANT CLOUD VERIFICATION TEST")
    print("="*70)
    
    # Test SaaS customer
    saas_results = test_customer_queries(1, "SaaS")
    
    # Test DC customer
    dc_results = test_customer_queries(5, "DC")
    
    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    print(f"\nSaaS Customer (ID: 1):")
    print(f"  ✅ Passed: {saas_results['queries_passed']}")
    print(f"  ❌ Failed: {saas_results['queries_failed']}")
    
    print(f"\nDC Customer (ID: 5):")
    print(f"  ✅ Passed: {dc_results['queries_passed']}")
    print(f"  ❌ Failed: {dc_results['queries_failed']}")
    
    total_passed = saas_results['queries_passed'] + dc_results['queries_passed']
    total_failed = saas_results['queries_failed'] + dc_results['queries_failed']
    total = total_passed + total_failed
    
    print(f"\nOverall:")
    print(f"  ✅ Passed: {total_passed}/{total} ({total_passed/total*100:.1f}%)")
    print(f"  ❌ Failed: {total_failed}/{total}")
    
    if total_failed == 0:
        print("\n🎉 All tests passed! Qdrant Cloud is working correctly.")
    else:
        print(f"\n⚠️  {total_failed} test(s) failed.")

if __name__ == '__main__':
    main()
