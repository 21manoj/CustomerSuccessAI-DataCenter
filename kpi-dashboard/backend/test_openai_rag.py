#!/usr/bin/env python3
"""
Test script for OpenAI RAG integration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openai_connection():
    """Test OpenAI API connection"""
    try:
        import openai
        
        # Set API key
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        if not openai.api_key:
            print("❌ OPENAI_API_KEY not found in environment")
            return False
        
        print(f"✅ OpenAI API key loaded: {openai.api_key[:20]}...")
        
        # Test API call
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": "Hello, this is a test. Please respond with 'OpenAI connection successful!'"}
            ],
            max_tokens=50
        )
        
        print(f"✅ OpenAI API response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI connection failed: {str(e)}")
        return False

def test_rag_system():
    """Test RAG system initialization"""
    try:
        from enhanced_rag_openai import EnhancedRAGSystemOpenAI
        
        rag_system = EnhancedRAGSystemOpenAI()
        print("✅ RAG system initialized successfully")
        
        # Test embedding model
        test_text = "This is a test KPI for customer success"
        embedding = rag_system.embedding_model.encode([test_text])[0]
        print(f"✅ Embedding generated: {len(embedding)} dimensions")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG system test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing OpenAI RAG Integration...")
    print("=" * 50)
    
    # Test OpenAI connection
    print("\n1. Testing OpenAI API connection...")
    openai_success = test_openai_connection()
    
    # Test RAG system
    print("\n2. Testing RAG system initialization...")
    rag_success = test_rag_system()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"OpenAI Connection: {'✅ PASS' if openai_success else '❌ FAIL'}")
    print(f"RAG System: {'✅ PASS' if rag_success else '❌ FAIL'}")
    
    if openai_success and rag_success:
        print("\n🎉 All tests passed! OpenAI RAG integration is ready.")
        print("\n📝 Next steps:")
        print("1. Start the Flask server: python app.py")
        print("2. Test the API endpoints:")
        print("   - POST /api/rag-openai/build")
        print("   - POST /api/rag-openai/query")
        print("3. Use X-Customer-ID header for multi-tenant support")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
