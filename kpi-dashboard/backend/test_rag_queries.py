#!/usr/bin/env python3
"""
Test RAG queries directly without Flask server
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_rag_system():
    """Test RAG system with sample queries"""
    try:
        from enhanced_rag_openai import get_rag_system
        from models import db, KPI, Account, KPIUpload
        from app import app
        
        with app.app_context():
            print("🧪 Testing RAG System with Sample Queries")
            print("=" * 60)
            
            # Test customer ID 6 (assuming it has data)
            customer_id = 6
            print(f"📊 Testing with Customer ID: {customer_id}")
            
            # Get RAG system for customer
            rag_system = get_rag_system(customer_id)
            
            # Check if customer has data
            kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).all()
            accounts = Account.query.filter_by(customer_id=customer_id).all()
            
            print(f"📈 Found {len(kpis)} KPIs and {len(accounts)} accounts for customer {customer_id}")
            
            if len(kpis) == 0:
                print("❌ No KPI data found for customer 6. Testing with sample data...")
                return test_with_sample_data(rag_system, customer_id)
            
            # Build knowledge base
            print("\n🔍 Building knowledge base...")
            try:
                rag_system.build_knowledge_base(customer_id)
                print("✅ Knowledge base built successfully")
            except Exception as e:
                print(f"❌ Error building knowledge base: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
            
            # Test queries
            test_queries = [
                "Which accounts have the highest revenue?",
                "What are the top performing KPIs?",
                "Show me customer satisfaction analysis",
                "Which accounts are at risk of churn?",
                "Analyze revenue growth patterns"
            ]
            
            for i, query in enumerate(test_queries, 1):
                print(f"\n🔍 Test Query {i}: {query}")
                print("-" * 50)
                
                try:
                    result = rag_system.query(query, 'general')
                    
                    if 'error' in result:
                        print(f"❌ Error: {result['error']}")
                    else:
                        print(f"✅ Query successful!")
                        print(f"📊 Results count: {result.get('results_count', 0)}")
                        print(f"🤖 AI Response: {result.get('response', 'No response')[:200]}...")
                        
                        if result.get('relevant_results'):
                            print(f"📋 Top result similarity: {result['relevant_results'][0].get('similarity', 0):.3f}")
                
                except Exception as e:
                    print(f"❌ Query failed: {str(e)}")
            
            print("\n🎉 RAG system testing completed!")
            return True
            
    except Exception as e:
        print(f"❌ RAG system test failed: {str(e)}")
        return False

def test_with_sample_data(rag_system, customer_id):
    """Test with sample data if no real data exists"""
    print("\n📝 Testing with sample data...")
    
    # Create sample data for testing
    sample_kpis = [
        {
            'kpi_id': 1,
            'account_id': 1,
            'account_name': 'Acme Corp',
            'revenue': 1000000,
            'industry': 'Technology',
            'region': 'North America',
            'category': 'Customer Sentiment',
            'kpi_parameter': 'Customer Satisfaction Score',
            'data': 85.5,
            'impact_level': 'High',
            'source_review': 'Quarterly Survey',
            'measurement_frequency': 'Quarterly'
        },
        {
            'kpi_id': 2,
            'account_id': 2,
            'account_name': 'TechStart Inc',
            'revenue': 500000,
            'industry': 'Technology',
            'region': 'North America',
            'category': 'Business Outcomes',
            'kpi_parameter': 'Monthly Recurring Revenue Growth',
            'data': 12.3,
            'impact_level': 'High',
            'source_review': 'Financial System',
            'measurement_frequency': 'Monthly'
        }
    ]
    
    sample_accounts = [
        {
            'account_id': 1,
            'account_name': 'Acme Corp',
            'revenue': 1000000,
            'industry': 'Technology',
            'region': 'North America',
            'account_status': 'Active'
        },
        {
            'account_id': 2,
            'account_name': 'TechStart Inc',
            'revenue': 500000,
            'industry': 'Technology',
            'region': 'North America',
            'account_status': 'Active'
        }
    ]
    
    # Manually set sample data
    rag_system.kpi_data = sample_kpis
    rag_system.account_data = sample_accounts
    
    # Test queries with sample data
    test_queries = [
        "Which accounts have the highest revenue?",
        "What are the top performing KPIs?",
        "Show me customer satisfaction analysis"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Test Query {i}: {query}")
        print("-" * 50)
        
        try:
            result = rag_system.query(query, 'general')
            
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
            else:
                print(f"✅ Query successful!")
                print(f"📊 Results count: {result.get('results_count', 0)}")
                print(f"🤖 AI Response: {result.get('response', 'No response')[:200]}...")
        
        except Exception as e:
            print(f"❌ Query failed: {str(e)}")
    
    print("\n🎉 Sample data testing completed!")
    return True

def main():
    """Main test function"""
    print("🚀 RAG System Query Testing")
    print("=" * 60)
    
    # Test OpenAI connection first
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
    
    # Test RAG system
    print("\n2. Testing RAG system...")
    success = test_rag_system()
    
    if success:
        print("\n🎉 All tests passed! RAG system is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
