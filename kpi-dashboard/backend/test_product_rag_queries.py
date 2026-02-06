#!/usr/bin/env python3
"""
Test RAG Product Queries - Post Product Analytics Implementation
Tests product-related queries to see if they're easier to analyze and report
"""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:5059"  # Updated to correct backend port

# Product queries - LIMITED TO 5 MAX TO SAVE COSTS
PRODUCT_QUERIES = [
    # Product identification queries
    "Which products are commonly used across accounts?",
    
    # Product health queries
    "Which products have low health scores?",
    
    # Product performance queries
    "Which products have low adoption rates?",
    
    # Product analytics queries
    "Which products generate the most revenue?",
    "Which accounts use multiple products?",
]

def login():
    """Login and get session"""
    session = requests.Session()
    try:
        response = session.post(
            f"{BASE_URL}/api/login",
            json={"email": "admin@syntara.com", "password": "syntara123"},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            customer_id = data.get('user', {}).get('customer_id', 1)
            print(f"✅ Logged in as: {data.get('user', {}).get('email')}")
            print(f"   Customer ID: {customer_id}")
            return session, customer_id
        else:
            print(f"⚠️  Login failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return session, 1  # Default customer ID
    except Exception as e:
        print(f"⚠️  Login error: {str(e)}")
        return requests.Session(), 1

def test_rag_query(session, customer_id, query, query_type="product_analysis"):
    """Test a single RAG query"""
    try:
        response = session.post(
            f"{BASE_URL}/api/rag-qdrant/query",
            json={
                "query": query,
                "query_type": query_type
            },
            headers={"X-Customer-ID": str(customer_id)},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'error' in data:
                return False, None, data.get('error', 'Unknown error'), {}
            
            response_text = data.get('response', 'No response')
            results_count = data.get('results_count', 0)
            relevant_results = data.get('relevant_results', [])
            
            metadata = {
                'results_count': results_count,
                'query_type': data.get('query_type', 'unknown'),
                'has_relevant_results': len(relevant_results) > 0
            }
            
            return True, response_text, None, metadata
        else:
            error_text = response.text[:500]
            return False, None, f"HTTP {response.status_code}: {error_text}", {}
    except Exception as e:
        return False, None, str(e), {}

def analyze_response_quality(response_text, query):
    """Analyze the quality of the RAG response"""
    analysis = {
        'mentions_products': False,
        'mentions_accounts': False,
        'mentions_health_scores': False,
        'mentions_kpis': False,
        'has_specific_data': False,
        'has_recommendations': False,
        'length': len(response_text),
        'quality_score': 0
    }
    
    # Check for product mentions
    product_keywords = ['product', 'platform', 'app', 'gateway', 'core', 'mobile', 'api']
    analysis['mentions_products'] = any(kw in response_text.lower() for kw in product_keywords)
    
    # Check for account mentions
    analysis['mentions_accounts'] = 'account' in response_text.lower()
    
    # Check for health score mentions
    analysis['mentions_health_scores'] = 'health' in response_text.lower() or 'score' in response_text.lower()
    
    # Check for KPI mentions
    analysis['mentions_kpis'] = 'kpi' in response_text.lower() or 'metric' in response_text.lower()
    
    # Check for specific data (numbers, percentages)
    import re
    has_numbers = bool(re.search(r'\d+', response_text))
    has_percentages = '%' in response_text
    analysis['has_specific_data'] = has_numbers or has_percentages
    
    # Check for recommendations
    recommendation_keywords = ['recommend', 'suggest', 'should', 'consider', 'action']
    analysis['has_recommendations'] = any(kw in response_text.lower() for kw in recommendation_keywords)
    
    # Calculate quality score
    score = 0
    if analysis['mentions_products']: score += 2
    if analysis['mentions_accounts']: score += 1
    if analysis['mentions_health_scores']: score += 2
    if analysis['mentions_kpis']: score += 1
    if analysis['has_specific_data']: score += 2
    if analysis['has_recommendations']: score += 1
    if analysis['length'] > 200: score += 1  # Substantial response
    
    analysis['quality_score'] = min(score, 10)  # Max score of 10
    
    return analysis

def main():
    """Run product RAG query tests"""
    print("=" * 80)
    print("RAG PRODUCT QUERY TEST SUITE")
    print("Testing product queries after product analytics implementation")
    print("=" * 80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Login
    session, customer_id = login()
    print()
    
    # Test queries
    results = []
    total_queries = len(PRODUCT_QUERIES)
    
    print("=" * 80)
    print(f"TESTING {total_queries} PRODUCT QUERIES")
    print("=" * 80)
    print()
    
    for i, query in enumerate(PRODUCT_QUERIES, 1):
        print(f"[{i}/{total_queries}] Query: {query}")
        print("-" * 80)
        
        start_time = time.time()
        success, response_text, error, metadata = test_rag_query(session, customer_id, query)
        duration = time.time() - start_time
        
        if success:
            # Analyze response quality
            quality = analyze_response_quality(response_text, query)
            
            print(f"✅ SUCCESS ({duration:.1f}s)")
            print(f"   Results: {metadata.get('results_count', 0)}")
            print(f"   Quality Score: {quality['quality_score']}/10")
            print(f"   Response Length: {quality['length']} chars")
            print(f"   Mentions Products: {quality['mentions_products']}")
            print(f"   Mentions Health Scores: {quality['mentions_health_scores']}")
            print(f"   Has Specific Data: {quality['has_specific_data']}")
            print(f"   Has Recommendations: {quality['has_recommendations']}")
            print()
            print(f"   Response Preview:")
            print(f"   {response_text[:300]}...")
            print()
            
            results.append({
                'query': query,
                'status': 'success',
                'duration': duration,
                'response': response_text,
                'quality': quality,
                'metadata': metadata
            })
        else:
            print(f"❌ FAILED ({duration:.1f}s)")
            print(f"   Error: {error}")
            print()
            
            results.append({
                'query': query,
                'status': 'failed',
                'duration': duration,
                'error': error
            })
        
        # Rate limiting
        if i < total_queries:
            time.sleep(2)
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'failed']
    
    print(f"Total Queries: {total_queries}")
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    print(f"Success Rate: {len(successful)/total_queries*100:.1f}%")
    print()
    
    if successful:
        avg_duration = sum(r['duration'] for r in successful) / len(successful)
        avg_quality = sum(r['quality']['quality_score'] for r in successful) / len(successful)
        
        print("Performance Metrics:")
        print(f"  Average Response Time: {avg_duration:.2f}s")
        print(f"  Average Quality Score: {avg_quality:.1f}/10")
        print()
        
        # Quality breakdown
        high_quality = [r for r in successful if r['quality']['quality_score'] >= 7]
        medium_quality = [r for r in successful if 4 <= r['quality']['quality_score'] < 7]
        low_quality = [r for r in successful if r['quality']['quality_score'] < 4]
        
        print("Quality Distribution:")
        print(f"  High Quality (7-10): {len(high_quality)} ({len(high_quality)/len(successful)*100:.1f}%)")
        print(f"  Medium Quality (4-6): {len(medium_quality)} ({len(medium_quality)/len(successful)*100:.1f}%)")
        print(f"  Low Quality (0-3): {len(low_quality)} ({len(low_quality)/len(successful)*100:.1f}%)")
        print()
        
        # Feature analysis
        mentions_products = sum(1 for r in successful if r['quality']['mentions_products'])
        mentions_health = sum(1 for r in successful if r['quality']['mentions_health_scores'])
        has_data = sum(1 for r in successful if r['quality']['has_specific_data'])
        has_recommendations = sum(1 for r in successful if r['quality']['has_recommendations'])
        
        print("Response Features:")
        print(f"  Mentions Products: {mentions_products}/{len(successful)} ({mentions_products/len(successful)*100:.1f}%)")
        print(f"  Mentions Health Scores: {mentions_health}/{len(successful)} ({mentions_health/len(successful)*100:.1f}%)")
        print(f"  Has Specific Data: {has_data}/{len(successful)} ({has_data/len(successful)*100:.1f}%)")
        print(f"  Has Recommendations: {has_recommendations}/{len(successful)} ({has_recommendations/len(successful)*100:.1f}%)")
        print()
    
    # Save detailed results
    output_file = f"product_rag_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'customer_id': customer_id,
            'total_queries': total_queries,
            'successful': len(successful),
            'failed': len(failed),
            'results': results
        }, f, indent=2)
    
    print(f"📄 Detailed results saved to: {output_file}")
    print()
    
    # Overall assessment
    print("=" * 80)
    print("OVERALL ASSESSMENT")
    print("=" * 80)
    
    if len(successful) == total_queries:
        print("✅ All queries succeeded!")
    elif len(successful) / total_queries >= 0.8:
        print("✅ Most queries succeeded (>80%)")
    elif len(successful) / total_queries >= 0.5:
        print("⚠️  Some queries failed (50-80% success)")
    else:
        print("❌ Many queries failed (<50% success)")
    
    if successful and avg_quality >= 7:
        print("✅ High quality responses (avg score >= 7)")
    elif successful and avg_quality >= 5:
        print("⚠️  Moderate quality responses (avg score 5-7)")
    else:
        print("❌ Low quality responses (avg score < 5)")
    
    print()
    print("=" * 80)
    
    return 0 if len(successful) == total_queries else 1

if __name__ == "__main__":
    sys.exit(main())
