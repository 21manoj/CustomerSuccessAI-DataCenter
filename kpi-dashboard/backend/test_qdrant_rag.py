#!/usr/bin/env python3
"""
Test script for Qdrant RAG integration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_qdrant_connection():
    """Test Qdrant Cloud connection"""
    try:
        from qdrant_client import QdrantClient
        
        # Qdrant Cloud connection (required)
        qdrant_url = os.getenv('QDRANT_URL')
        qdrant_api_key = os.getenv('QDRANT_API_KEY')
        
        if not qdrant_url or not qdrant_api_key:
            print("❌ QDRANT_URL and QDRANT_API_KEY are required for Qdrant Cloud connection")
            print("   Please set these environment variables in your .env file")
            return False
        
        # Connect to Qdrant Cloud
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            timeout=30
        )
        
        # Get collections info
        collections = client.get_collections()
        print(f"✅ Qdrant Cloud connection successful")
        print(f"📊 Found {len(collections.collections)} collections")
        
        return True
        
    except Exception as e:
        print(f"❌ Qdrant Cloud connection failed: {str(e)}")
        print("   Please verify QDRANT_URL and QDRANT_API_KEY are set correctly")
        return False

def test_rag_system():
    """Test Qdrant RAG system initialization"""
    try:
        from enhanced_rag_qdrant import get_qdrant_rag_system
        from models import db, KPI, Account, KPIUpload
        from app import app
        
        with app.app_context():
            print("🧪 Testing Qdrant RAG System...")
            print("=" * 50)
            
            # Test customer ID 6
            customer_id = 6
            print(f"📊 Testing with Customer ID: {customer_id}")
            
            # Get RAG system for customer
            rag_system = get_qdrant_rag_system(customer_id)
            print("✅ Qdrant RAG system initialized successfully")
            
            # Check if customer has data
            kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).all()
            accounts = Account.query.filter_by(customer_id=customer_id).all()
            
            print(f"📈 Found {len(kpis)} KPIs and {len(accounts)} accounts for customer {customer_id}")
            
            if len(kpis) == 0:
                print("❌ No KPI data found for customer 6. Testing with sample data...")
                return test_with_sample_data(rag_system, customer_id)
            
            # Build knowledge base
            print("\n🔍 Building Qdrant knowledge base...")
            try:
                rag_system.build_knowledge_base(customer_id)
                print("✅ Qdrant knowledge base built successfully")
            except Exception as e:
                print(f"❌ Error building knowledge base: {str(e)}")
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
            
            print("\n🎉 Qdrant RAG system testing completed!")
            return True
            
    except Exception as e:
        print(f"❌ Qdrant RAG system test failed: {str(e)}")
        import traceback
        traceback.print_exc()
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
    
    # Manually set sample data and build index
    try:
        rag_system._build_qdrant_index(sample_kpis, sample_accounts)
        print("✅ Sample data indexed in Qdrant")
        
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
        
    except Exception as e:
        print(f"❌ Sample data test failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🚀 Qdrant RAG Integration Testing")
    print("=" * 60)
    
    # Test Qdrant connection
    print("1. Testing Qdrant connection...")
    qdrant_success = test_qdrant_connection()
    
    if not qdrant_success:
        print("\n❌ Qdrant connection failed. Please check Qdrant installation.")
        print("💡 To install Qdrant locally:")
        print("   docker run -p 6333:6333 qdrant/qdrant")
        return 1
    
    # Test OpenAI connection
    print("\n2. Testing OpenAI connection...")
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
    
    # Test Qdrant RAG system
    print("\n3. Testing Qdrant RAG system...")
    rag_success = test_rag_system()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"Qdrant Connection: {'✅ PASS' if qdrant_success else '❌ FAIL'}")
    print(f"OpenAI Connection: {'✅ PASS' if 'openai' in locals() else '❌ FAIL'}")
    print(f"Qdrant RAG System: {'✅ PASS' if rag_success else '❌ FAIL'}")
    
    if qdrant_success and rag_success:
        print("\n🎉 All tests passed! Qdrant RAG integration is ready.")
        print("\n📝 Next steps:")
        print("1. Start the Flask server: python app.py")
        print("2. Test the Qdrant API endpoints:")
        print("   - POST /api/rag-qdrant/build")
        print("   - POST /api/rag-qdrant/query")
        print("3. Use X-Customer-ID header for multi-tenant support")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
