#!/usr/bin/env python3
"""
E2E RAG Tests for Customer 130
==============================

Tests RAG queries on collection: kpi_dashboard_vectors_customer_130
Runs 10 test queries to validate the knowledge base.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from enhanced_rag_qdrant import EnhancedRAGSystemQdrant
from models import Customer, Account, DC2SKPI

CUSTOMER_ID = 130
COLLECTION_NAME = f"kpi_dashboard_vectors_customer_{CUSTOMER_ID}"

# 10 test queries covering different aspects
TEST_QUERIES = [
    "What are the health scores for all accounts?",
    "Which KPIs are performing best?",
    "Show me accounts with high AI workload performance",
    "What are the deployment velocity metrics?",
    "Which accounts need attention?",
    "What is the overall customer health?",
    "Show me expansion readiness indicators",
    "What are the operational stability metrics?",
    "Which accounts have the highest scores?",
    "Analyze the channel and partner health"
]

def log(message: str):
    """Log with timestamp"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")

def test_rag_queries():
    """Run 10 E2E RAG tests on customer 130"""
    log("="*70)
    log(f"E2E RAG TESTS - Customer {CUSTOMER_ID}")
    log(f"Collection: {COLLECTION_NAME}")
    log("="*70)
    log("")
    
    with app.app_context():
        # Verify customer exists
        customer = Customer.query.get(CUSTOMER_ID)
        if not customer:
            log(f"❌ Customer {CUSTOMER_ID} not found!")
            return 1
        
        log(f"✅ Customer found: {customer.customer_name}")
        
        # Check accounts
        accounts = Account.query.filter_by(customer_id=CUSTOMER_ID).all()
        log(f"✅ Found {len(accounts)} accounts")
        
        # Check KPI data
        account_ids = [a.account_id for a in accounts]
        kpi_count = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).count()
        log(f"✅ Found {kpi_count} KPI measurements")
        log("")
        
        # Initialize RAG system
        try:
            rag = EnhancedRAGSystemQdrant()
            
            if rag.qdrant_bypassed:
                log("❌ Qdrant is bypassed - cannot run RAG tests")
                log("   Set QDRANT_URL and QDRANT_API_KEY to enable")
                return 1
            
            # Set customer ID and collection
            rag.customer_id = CUSTOMER_ID
            rag.collection_name = COLLECTION_NAME
            
            # Verify collection exists
            try:
                collection_info = rag.qdrant_client.get_collection(COLLECTION_NAME)
                vectors = collection_info.points_count
                log(f"✅ Collection found: {COLLECTION_NAME}")
                log(f"   Vectors: {vectors}")
                log("")
            except Exception as e:
                log(f"❌ Collection not found: {e}")
                log("   Run the E2E onboarding test first to build the knowledge base")
                return 1
            
            # Run 10 test queries
            log("="*70)
            log("RUNNING 10 RAG QUERIES")
            log("="*70)
            log("")
            
            results = []
            for i, query in enumerate(TEST_QUERIES, 1):
                log(f"Query {i}/10: {query}")
                log("-" * 70)
                
                try:
                    result = rag.query(query, query_type='general')
                    
                    if 'error' in result:
                        log(f"❌ Error: {result['error']}")
                        results.append({
                            'query': query,
                            'success': False,
                            'error': result['error']
                        })
                    else:
                        response = result.get('response', 'No response')
                        results_count = result.get('results_count', 0)
                        relevant_results = result.get('relevant_results', [])
                        
                        log(f"✅ Results: {results_count} relevant matches")
                        log(f"✅ Response: {response[:200]}..." if len(response) > 200 else f"✅ Response: {response}")
                        
                        if relevant_results:
                            log(f"   Top match similarity: {relevant_results[0].get('similarity', 0):.3f}")
                        
                        results.append({
                            'query': query,
                            'success': True,
                            'results_count': results_count,
                            'response_length': len(response),
                            'top_similarity': relevant_results[0].get('similarity', 0) if relevant_results else 0
                        })
                    
                    log("")
                    
                except Exception as e:
                    log(f"❌ Query failed: {e}")
                    import traceback
                    log(traceback.format_exc())
                    results.append({
                        'query': query,
                        'success': False,
                        'error': str(e)
                    })
                    log("")
            
            # Summary
            log("="*70)
            log("TEST SUMMARY")
            log("="*70)
            
            successful = sum(1 for r in results if r.get('success', False))
            failed = len(results) - successful
            
            log(f"Total Queries: {len(results)}")
            log(f"✅ Successful: {successful}")
            log(f"❌ Failed: {failed}")
            log("")
            
            if successful > 0:
                avg_results = sum(r.get('results_count', 0) for r in results if r.get('success')) / successful
                avg_similarity = sum(r.get('top_similarity', 0) for r in results if r.get('success')) / successful
                log(f"Average results per query: {avg_results:.1f}")
                log(f"Average top similarity: {avg_similarity:.3f}")
            
            log("")
            log("Query Details:")
            for i, result in enumerate(results, 1):
                status = "✅" if result.get('success') else "❌"
                log(f"  {status} Query {i}: {result['query'][:50]}...")
                if result.get('success'):
                    log(f"     Results: {result.get('results_count', 0)}, Similarity: {result.get('top_similarity', 0):.3f}")
                else:
                    log(f"     Error: {result.get('error', 'Unknown')}")
            
            log("")
            log("="*70)
            if successful == len(results):
                log("✅ ALL TESTS PASSED!")
            else:
                log(f"⚠️  {failed} TEST(S) FAILED")
            log("="*70)
            
            return 0 if successful == len(results) else 1
            
        except Exception as e:
            log(f"❌ Failed to initialize RAG system: {e}")
            import traceback
            log(traceback.format_exc())
            return 1

if __name__ == "__main__":
    sys.exit(test_rag_queries())
