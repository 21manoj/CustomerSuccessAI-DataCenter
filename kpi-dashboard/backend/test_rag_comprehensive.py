#!/usr/bin/env python3
"""
Comprehensive RAG System Testing
Tests various query types and scenarios
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_comprehensive_rag():
    """Test RAG system with comprehensive queries"""
    try:
        from enhanced_rag_openai import get_rag_system
        from models import db, KPI, Account, KPIUpload
        from app import app
        
        with app.app_context():
            print("🧪 Comprehensive RAG System Testing")
            print("=" * 70)
            
            # Test customer ID 6
            customer_id = 6
            print(f"📊 Testing with Customer ID: {customer_id}")
            
            # Get RAG system for customer
            rag_system = get_rag_system(customer_id)
            
            # Check data
            kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).all()
            accounts = Account.query.filter_by(customer_id=customer_id).all()
            
            print(f"📈 Found {len(kpis)} KPIs and {len(accounts)} accounts")
            
            # Build knowledge base
            print("\n🔍 Building knowledge base...")
            rag_system.build_knowledge_base(customer_id)
            
            # Test different types of queries
            test_scenarios = [
                {
                    "category": "Revenue Analysis",
                    "queries": [
                        "Show me accounts with highest revenue",
                        "What is the total revenue across all accounts?",
                        "Which accounts generate the most money?",
                        "Revenue analysis and trends"
                    ]
                },
                {
                    "category": "KPI Performance",
                    "queries": [
                        "What are the best performing KPIs?",
                        "Show me customer satisfaction scores",
                        "Which KPIs have the highest values?",
                        "KPI performance analysis"
                    ]
                },
                {
                    "category": "Account Health",
                    "queries": [
                        "Which accounts are performing well?",
                        "Show me account health scores",
                        "What accounts need attention?",
                        "Account performance analysis"
                    ]
                },
                {
                    "category": "Industry Analysis",
                    "queries": [
                        "What industries do our accounts belong to?",
                        "Show me technology company performance",
                        "Industry breakdown and analysis"
                    ]
                },
                {
                    "category": "Risk Assessment",
                    "queries": [
                        "Which accounts might be at risk?",
                        "Show me low performing accounts",
                        "Risk analysis and identification"
                    ]
                }
            ]
            
            for scenario in test_scenarios:
                print(f"\n🎯 {scenario['category']} Queries")
                print("=" * 50)
                
                for i, query in enumerate(scenario['queries'], 1):
                    print(f"\n🔍 Query {i}: {query}")
                    print("-" * 40)
                    
                    try:
                        result = rag_system.query(query, 'general')
                        
                        if 'error' in result:
                            print(f"❌ Error: {result['error']}")
                        else:
                            print(f"✅ Query successful!")
                            print(f"📊 Results count: {result.get('results_count', 0)}")
                            print(f"🎯 Query type: {result.get('query_type', 'unknown')}")
                            
                            if result.get('results_count', 0) > 0:
                                print(f"🔍 Similarity threshold: {result.get('similarity_threshold', 0)}")
                                print(f"📋 Top similarity score: {result['relevant_results'][0].get('similarity', 0):.3f}")
                            
                            # Show AI response (truncated)
                            response = result.get('response', 'No response')
                            if len(response) > 300:
                                response = response[:300] + "..."
                            print(f"🤖 AI Response: {response}")
                            
                            # Show relevant results metadata
                            if result.get('relevant_results'):
                                print(f"📊 Found {len(result['relevant_results'])} relevant results")
                                for j, res in enumerate(result['relevant_results'][:3], 1):
                                    metadata = res.get('metadata', {})
                                    print(f"   {j}. {metadata.get('type', 'unknown')} - {metadata.get('account_name', 'N/A')} (sim: {res.get('similarity', 0):.3f})")
                    
                    except Exception as e:
                        print(f"❌ Query failed: {str(e)}")
            
            # Test specific analysis functions
            print(f"\n🔬 Specific Analysis Functions")
            print("=" * 50)
            
            try:
                print("\n📈 Revenue Analysis...")
                revenue_analysis = rag_system.analyze_revenue_drivers(customer_id)
                if 'error' not in revenue_analysis:
                    print(f"✅ Total revenue: ${revenue_analysis.get('total_revenue', 0):,.0f}")
                    print(f"📊 Top accounts: {len(revenue_analysis.get('top_accounts', []))}")
                    print(f"🏭 Industries: {len(revenue_analysis.get('revenue_by_industry', {}))}")
                else:
                    print(f"❌ Revenue analysis error: {revenue_analysis['error']}")
            except Exception as e:
                print(f"❌ Revenue analysis failed: {str(e)}")
            
            try:
                print("\n⚠️ Risk Analysis...")
                risk_analysis = rag_system.find_at_risk_accounts(customer_id)
                if 'error' not in risk_analysis:
                    print(f"✅ At-risk accounts: {len(risk_analysis.get('at_risk_accounts', []))}")
                    print(f"📊 Risk percentage: {risk_analysis.get('risk_percentage', 0):.1f}%")
                else:
                    print(f"❌ Risk analysis error: {risk_analysis['error']}")
            except Exception as e:
                print(f"❌ Risk analysis failed: {str(e)}")
            
            print("\n🎉 Comprehensive RAG testing completed!")
            return True
            
    except Exception as e:
        print(f"❌ Comprehensive RAG test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Comprehensive RAG System Testing")
    print("=" * 70)
    
    # Test OpenAI connection
    print("1. Testing OpenAI connection...")
    try:
        import openai
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        if not openai.api_key:
            print("❌ OPENAI_API_KEY not found")
            return 1
        
        print("✅ OpenAI API key loaded")
        
        # Test API call
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello, this is a test."}],
            max_tokens=10
        )
        print("✅ OpenAI API connection successful")
        
    except Exception as e:
        print(f"❌ OpenAI connection failed: {str(e)}")
        return 1
    
    # Test comprehensive RAG system
    print("\n2. Testing comprehensive RAG system...")
    success = test_comprehensive_rag()
    
    if success:
        print("\n🎉 All comprehensive tests passed! RAG system is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
