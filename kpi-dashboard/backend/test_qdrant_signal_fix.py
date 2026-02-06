#!/usr/bin/env python3
"""
Test Qdrant Integration Fix for Signal Analyst

Tests that the fixed qdrant_integration.py correctly retrieves signals
from Qdrant Cloud for account 372.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app_v3_minimal import app
from enhanced_rag_qdrant import get_qdrant_rag_system
from agents.qdrant_integration import (
    get_quantitative_signals_from_qdrant,
    get_qualitative_signals_from_qdrant,
    get_historical_patterns_from_qdrant,
    query_qdrant_for_signals
)

def test_qdrant_signal_retrieval():
    """Test Qdrant signal retrieval for account 372"""
    
    print("=" * 70)
    print("TESTING QDRANT INTEGRATION FIX")
    print("=" * 70)
    print()
    
    customer_id = 5  # Supermicro customer
    account_id = "372"
    
    with app.app_context():
        try:
            # Initialize RAG system
            print("1. Initializing RAG system...")
            rag_system = get_qdrant_rag_system(customer_id)
            
            if rag_system.qdrant_bypassed:
                print("   ❌ Qdrant is bypassed - cannot test")
                return False
            
            if not rag_system.qdrant_client:
                print("   ❌ Qdrant client not available - cannot test")
                return False
            
            collection_name = f"kpi_dashboard_vectors_customer_{customer_id}"
            print(f"   ✅ RAG system initialized")
            print(f"   ✅ Collection: {collection_name}")
            print()
            
            # Test quantitative signals
            print("2. Testing Quantitative Signals Retrieval...")
            print("-" * 70)
            try:
                quant_signals = get_quantitative_signals_from_qdrant(
                    rag_system, account_id, customer_id, top_k=20
                )
                print(f"   ✅ Retrieved: {len(quant_signals)} quantitative signals")
                
                if len(quant_signals) > 0:
                    print(f"   Sample signals:")
                    for i, sig in enumerate(quant_signals[:3], 1):
                        payload = sig.payload
                        text = payload.get('text', 'N/A')[:60]
                        similarity = sig.similarity
                        print(f"   {i}. Similarity: {similarity:.3f}")
                        print(f"      Text: {text}...")
                        print(f"      Account ID in payload: {payload.get('account_id')}")
                else:
                    print("   ⚠️  No quantitative signals found (this is OK if Qdrant doesn't have quantitative data)")
                
            except Exception as e:
                print(f"   ❌ Error retrieving quantitative signals: {e}")
                import traceback
                traceback.print_exc()
            
            print()
            
            # Test qualitative signals (THE KEY TEST)
            print("3. Testing Qualitative Signals Retrieval (KEY TEST)...")
            print("-" * 70)
            try:
                qual_signals = get_qualitative_signals_from_qdrant(
                    rag_system, account_id, customer_id, top_k=20
                )
                print(f"   ✅ Retrieved: {len(qual_signals)} qualitative signals")
                
                # Check if we got 4+ signals (the expected result)
                if len(qual_signals) >= 4:
                    print(f"   ✅ SUCCESS: Got {len(qual_signals)} signals (expected 4+)")
                    test_passed = True
                elif len(qual_signals) > 0:
                    print(f"   ⚠️  Got {len(qual_signals)} signals (expected 4+)")
                    test_passed = False
                else:
                    print(f"   ❌ FAILED: Got 0 signals (expected 4+)")
                    test_passed = False
                
                if len(qual_signals) > 0:
                    print(f"\n   Sample qualitative signals:")
                    for i, sig in enumerate(qual_signals, 1):
                        payload = sig.payload
                        text = payload.get('text', payload.get('kpi_parameter', 'N/A'))[:80]
                        similarity = sig.similarity
                        account_id_in_payload = payload.get('account_id')
                        kpi_code = payload.get('kpi_code', 'N/A')
                        pillar = payload.get('pillar', 'N/A')
                        
                        print(f"   {i}. Similarity: {similarity:.3f}")
                        print(f"      Account ID: {account_id_in_payload} (expected: {account_id})")
                        print(f"      KPI Code: {kpi_code}")
                        print(f"      Pillar: {pillar}")
                        print(f"      Text: {text}...")
                        
                        # Verify account_id matches
                        if str(account_id_in_payload) != str(account_id):
                            print(f"      ⚠️  WARNING: Account ID mismatch!")
                        else:
                            print(f"      ✅ Account ID matches")
                        print()
                else:
                    print("   ⚠️  No qualitative signals found")
                    test_passed = False
                    
            except Exception as e:
                print(f"   ❌ Error retrieving qualitative signals: {e}")
                import traceback
                traceback.print_exc()
                test_passed = False
            
            print()
            
            # Test historical patterns
            print("4. Testing Historical Patterns Retrieval...")
            print("-" * 70)
            try:
                hist_signals = get_historical_patterns_from_qdrant(
                    rag_system, account_id, customer_id, top_k=10
                )
                print(f"   ✅ Retrieved: {len(hist_signals)} historical patterns")
                
                if len(hist_signals) > 0:
                    print(f"   Sample patterns:")
                    for i, sig in enumerate(hist_signals[:3], 1):
                        payload = sig.payload
                        text = payload.get('text', 'N/A')[:60]
                        print(f"   {i}. {text}...")
                else:
                    print("   ⚠️  No historical patterns found (this is OK if Qdrant doesn't have historical data)")
                
            except Exception as e:
                print(f"   ❌ Error retrieving historical patterns: {e}")
                import traceback
                traceback.print_exc()
            
            print()
            print("=" * 70)
            print("TEST SUMMARY")
            print("=" * 70)
            
            total_signals = len(quant_signals) + len(qual_signals) + len(hist_signals)
            print(f"Quantitative signals: {len(quant_signals)}")
            print(f"Qualitative signals: {len(qual_signals)} (expected: 4+)")
            print(f"Historical patterns: {len(hist_signals)}")
            print(f"Total signals: {total_signals}")
            print()
            
            if len(qual_signals) >= 4:
                print("✅ TEST PASSED: Qualitative signals retrieval is working!")
                print("   The fix successfully retrieves 4+ signals from Qdrant Cloud")
                return True
            else:
                print("❌ TEST FAILED: Expected 4+ qualitative signals, got {}".format(len(qual_signals)))
                print("   Possible issues:")
                print("   - Qdrant collection may not have data for account 372")
                print("   - Account ID filtering may be too strict")
                print("   - Collection name may be incorrect")
                return False
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_direct_collection_query():
    """Test direct collection query to verify data exists"""
    
    print("\n" + "=" * 70)
    print("VERIFYING QDRANT COLLECTION DATA")
    print("=" * 70)
    print()
    
    customer_id = 5
    account_id = "372"
    
    with app.app_context():
        try:
            rag_system = get_qdrant_rag_system(customer_id)
            
            if not rag_system.qdrant_client:
                print("❌ Qdrant client not available")
                return
            
            collection_name = f"kpi_dashboard_vectors_customer_{customer_id}"
            
            # Get collection info
            collection_info = rag_system.qdrant_client.get_collection(collection_name)
            print(f"Collection: {collection_name}")
            print(f"Total points: {collection_info.points_count}")
            print()
            
            # Try to query with a simple query to see what we get
            query_text = f"account {account_id}"
            query_embedding = rag_system.embedding_model.embed_query(query_text)
            
            # Search without filtering first to see all results
            search_results = rag_system.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=20
            )
            
            print(f"Found {len(search_results)} total results (before filtering)")
            print()
            
            # Count results with account_id = 372
            account_372_results = []
            for result in search_results:
                payload = result.payload
                result_account_id = payload.get('account_id')
                if result_account_id and str(result_account_id) == str(account_id):
                    account_372_results.append(result)
            
            print(f"Results for account {account_id}: {len(account_372_results)}")
            
            if len(account_372_results) >= 4:
                print(f"✅ Found {len(account_372_results)} points for account {account_id} in collection")
                print()
                print("Sample points:")
                for i, result in enumerate(account_372_results[:5], 1):
                    payload = result.payload
                    kpi_code = payload.get('kpi_code', 'N/A')
                    pillar = payload.get('pillar', 'N/A')
                    text = str(payload.get('text', payload.get('kpi_parameter', 'N/A')))[:60]
                    print(f"  {i}. KPI: {kpi_code}, Pillar: {pillar}")
                    print(f"     Text: {text}...")
            else:
                print(f"⚠️  Only found {len(account_372_results)} points for account {account_id}")
                print("   Expected at least 4 points")
                
        except Exception as e:
            print(f"❌ Error verifying collection: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print()
    print("🧪 Testing Qdrant Integration Fix for Signal Analyst")
    print()
    
    # Run verification first
    test_direct_collection_query()
    
    # Run main test
    print()
    success = test_qdrant_signal_retrieval()
    
    print()
    if success:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed - check the output above")
        sys.exit(1)


