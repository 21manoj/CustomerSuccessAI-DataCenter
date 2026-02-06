#!/usr/bin/env python3
"""
Test 5 RAG queries for Customer 9 to verify AI Insights is working
This script tests the RAG system with minimal cost (only 5 queries)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app_v3_minimal import app
from enhanced_rag_qdrant import get_qdrant_rag_system

# Test queries (diverse to test different query types)
TEST_QUERIES = [
    {
        'query': 'What are the top 3 accounts by revenue?',
        'query_type': 'revenue_analysis',
        'description': 'Revenue analysis query'
    },
    {
        'query': 'Which accounts have the highest health scores?',
        'query_type': 'account_analysis',
        'description': 'Account health query'
    },
    {
        'query': 'Show me KPI performance across all categories',
        'query_type': 'kpi_analysis',
        'description': 'KPI analysis query'
    },
    {
        'query': 'What are the main trends in customer data?',
        'query_type': 'trend_analysis',
        'description': 'Trend analysis query'
    },
    {
        'query': 'Which accounts need attention?',
        'query_type': 'general',
        'description': 'General query'
    }
]

def test_rag_queries():
    """Run 5 test RAG queries for Customer 9"""
    customer_id = 9
    
    print("=" * 70)
    print("RAG QUERY TEST - Customer 9")
    print("=" * 70)
    print(f"Customer ID: {customer_id}")
    print(f"Total Queries: {len(TEST_QUERIES)}")
    print("=" * 70)
    print()
    
    with app.app_context():
        # Initialize RAG system
        print("🔧 Initializing RAG system...")
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Check collection status
        if not hasattr(rag_system, 'qdrant_client') or not rag_system.qdrant_client:
            print("❌ Qdrant client not available!")
            return
        
        try:
            collection_info = rag_system.qdrant_client.get_collection(rag_system.collection_name)
            print(f"✅ Collection: {rag_system.collection_name}")
            print(f"✅ Points: {collection_info.points_count}")
            print()
        except Exception as e:
            print(f"❌ Error accessing collection: {str(e)[:100]}")
            return
        
        # Run test queries
        results = []
        for i, test_query in enumerate(TEST_QUERIES, 1):
            print(f"Query {i}/{len(TEST_QUERIES)}: {test_query['description']}")
            print(f"  Query: {test_query['query']}")
            print(f"  Type: {test_query['query_type']}")
            
            try:
                result = rag_system.query(
                    test_query['query'],
                    test_query['query_type']
                )
                
                if 'error' in result:
                    print(f"  ❌ Error: {result['error']}")
                    results.append({
                        'query': test_query['query'],
                        'status': 'error',
                        'error': result['error']
                    })
                else:
                    results_count = result.get('results_count', 0)
                    response_length = len(result.get('response', ''))
                    relevant_results = len(result.get('relevant_results', []))
                    
                    print(f"  ✅ Success!")
                    print(f"     Results: {results_count}")
                    print(f"     Response: {response_length} chars")
                    print(f"     Relevant: {relevant_results}")
                    print(f"     Response preview: {result.get('response', '')[:150]}...")
                    
                    results.append({
                        'query': test_query['query'],
                        'status': 'success',
                        'results_count': results_count,
                        'response_length': response_length,
                        'relevant_results': relevant_results
                    })
            except Exception as e:
                print(f"  ❌ Exception: {str(e)[:100]}")
                results.append({
                    'query': test_query['query'],
                    'status': 'exception',
                    'error': str(e)[:200]
                })
            
            print()
        
        # Summary
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = len(results) - successful
        
        print(f"Total Queries: {len(results)}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print()
        
        if successful > 0:
            avg_results = sum(r.get('results_count', 0) for r in results if r['status'] == 'success') / successful
            avg_response = sum(r.get('response_length', 0) for r in results if r['status'] == 'success') / successful
            print(f"Average Results per Query: {avg_results:.1f}")
            print(f"Average Response Length: {avg_response:.0f} chars")
        
        print()
        print("=" * 70)
        print("✅ RAG QUERY TEST COMPLETE")
        print("=" * 70)
        
        return results

if __name__ == '__main__':
    test_rag_queries()
