#!/usr/bin/env python3
"""Test Qdrant Cloud Connection and Show Collections"""

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

print("=" * 70)
print("QDRANT CLOUD CONNECTION TEST")
print("=" * 70)

# Get credentials from .env
qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")

if not qdrant_url or not qdrant_api_key:
    print("\nERROR: Missing Qdrant credentials in .env file")
    exit(1)

print("\nConnecting to Qdrant Cloud...")
print("URL: " + qdrant_url)

try:
    client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key,
    )
    
    print("\n✅ Connected successfully!")
    
    # Get all collections
    collections = client.get_collections()
    
    print("\n" + "=" * 70)
    print("EXISTING COLLECTIONS")
    print("=" * 70)
    
    print("\nTotal collections: " + str(len(collections.collections)))
    
    if collections.collections:
        for collection in collections.collections:
            print("\n📦 Collection: " + collection.name)
            info = client.get_collection(collection.name)
            print("   Points: " + str(info.points_count))
            print("   Vector size: " + str(info.config.params.vectors.size))
            print("   Distance: " + str(info.config.params.vectors.distance))
            
            # Sample a point if exists
            if info.points_count > 0:
                sample = client.scroll(
                    collection_name=collection.name,
                    limit=1
                )[0]
                if sample:
                    print("   Sample payload keys: " + str(list(sample[0].payload.keys())[:5]))
    
    print("\n" + "=" * 70)
    print("READY FOR SIGNAL EMBEDDING!")
    print("=" * 70)
    
except Exception as e:
    print("\n❌ Connection failed!")
    print("Error: " + str(e))
    exit(1)
