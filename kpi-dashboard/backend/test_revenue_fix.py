#!/usr/bin/env python3
"""
Test script to verify revenue fix in historical trend analysis
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from enhanced_rag_qdrant import get_qdrant_rag_system

def test_revenue_fix():
    """Test the revenue fix in historical trend analysis"""
    print("🧪 Testing Revenue Fix in Historical Trend Analysis")
    print("=" * 60)
    
    with app.app_context():
        customer_id = 6
        
        # Get RAG system
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Test queries
        test_queries = [
            "Which accounts have the highest revenue across last 4 months? please provide month details as well?",
            "Show me revenue trends for the last 4 months",
            "What is the total revenue for each month?",
            "Which accounts generated the most revenue in September 2025?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔍 Test Query {i}: {query}")
            print("-" * 50)
            
            try:
                result = rag_system.query(query, 'temporal_analysis')
                
                if 'error' in result:
                    print(f"❌ Error: {result['error']}")
                else:
                    print(f"✅ Query successful!")
                    print(f"📊 Results count: {result.get('results_count', 0)}")
                    
                    if result.get('relevant_results'):
                        print(f"🔍 Found {len(result['relevant_results'])} relevant results")
                        
                        # Show first few results
                        for j, res in enumerate(result['relevant_results'][:3], 1):
                            metadata = res.get('metadata', {})
                            print(f"   {j}. Type: {metadata.get('type', 'unknown')}")
                            print(f"      Similarity: {res.get('similarity', 0):.3f}")
                            
                            if metadata.get('type') == 'temporal_revenue':
                                print(f"      Month: {metadata.get('month_year', 'N/A')}")
                                print(f"      Revenue: ${metadata.get('total_revenue', 0):,.2f}")
                            
                            # Show text snippet
                            text = res.get('text', '')
                            if text:
                                text_preview = text[:200] + "..." if len(text) > 200 else text
                                print(f"      Text: {text_preview}")
                    
                    # Show AI response
                    response = result.get('response', 'No response')
                    if response:
                        response_preview = response[:300] + "..." if len(response) > 300 else response
                        print(f"🤖 AI Response: {response_preview}")
                
            except Exception as e:
                print(f"❌ Query failed: {str(e)}")
        
        print("\n" + "=" * 60)
        print("🎉 Revenue fix testing completed!")

if __name__ == "__main__":
    test_revenue_fix()
