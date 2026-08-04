#!/usr/bin/env python3
"""
Test that all components are installed and working
"""

import os
from dotenv import load_dotenv
from sqlalchemy import text  # ← ADD THIS

# Load environment
load_dotenv()

print("=" * 60)
print("SIGNAL ANALYST MVP - SETUP TEST")
print("=" * 60)

# Test 1: Anthropic API
print("\n1. Testing Anthropic API...")
try:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Simple test call with CORRECT model name
    response = client.messages.create(
        model="claude-sonnet-4-6",  # ← UPDATED
        max_tokens=50,
        messages=[{"role": "user", "content": "Say 'API working!'"}]
    )
    
    print(f"   ✅ API Response: {response.content[0].text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: PostgreSQL Connection
print("\n2. Testing PostgreSQL connection...")
try:
    from sqlalchemy import create_engine
    
    engine = create_engine(os.getenv("DATABASE_URL"))
    with engine.connect()as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM accounts")).fetchone()  # ← FIXED
        print(f"   ✅ Connected! Found {result[0]} accounts in database")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: ChromaDB
print("\n3. Testing ChromaDB...")
try:
    import chromadb
    
    # Create in-memory client for testing
    client = chromadb.Client()
    collection = client.create_collection("test")
    
    print("   ⏳ Downloading embedding model (first time only)...")
    collection.add(
        documents=["This is a test document"],
        ids=["test1"]
    )
    
    results = collection.query(query_texts=["test"], n_results=1)
    print(f"   ✅ ChromaDB working! Retrieved: {results['documents'][0]}")
    
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Sentence Transformers
print("\n4. Testing Sentence Transformers...")
try:
    from sentence_transformers import SentenceTransformer
    
    print("   ⏳ Loading model...")
    model = SentenceTransformer('all-MiniLM-L6-v2') 
    embeddings = model.encode(["Test sentence"])
    
    print(f"   ✅ Model loaded! Embedding dimension: {len(embeddings[0])}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("SETUP TEST COMPLETE!")
print("=" * 60)
