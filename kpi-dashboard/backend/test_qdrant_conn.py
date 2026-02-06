#!/usr/bin/env python3
"""Test Qdrant Cloud Connection"""

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
    print("\nPlease add:")
    print("QDRANT_URL=https://your-cluster.cloud.qdrant.io")
    print("QDRANT_API_KEY=your-api-key-here")
    exit(1)

print("\nConnecting to Qdrant Cloud...")
print("URL: " + qdrant_url)

try:
    # Connect to Qdrant
    client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key,
    )
    
    print("\n✅ Connected successfully!")
    
    # Get cluster info
    collections = client.get_collections()
    
    print("\n" + "=" * 70)
    print("CLUSTER INFO")
    print("=" * 70)
    
    print("\nExisting collections: " + r(len(collections.collections)))
    
    if collections.collections:
        print("\nCollections:")
        for collection in collections.collections:
            print("  - " + collection.name)
            info = client.get_collection(collection.name)
            print("    Vectors: " + str(info.points_count))
            print("    Vector size: " + str(info.config.params.vectors.size))
    else:
        print("\nNo collections found (fresh cluster)")
    
    print("\n" + "=" * 70)
    print("READY TO PROCEED!")
    print("=" * 70)
    
except Exception as e:
    print("\n❌ Connection failed!")
    print("Error: " + str(e))
    print("\nPlease verify:")
    print("1. QDRANT_URL is correct")
    print("2. QDRANT_API_KEY is valid")
    print("3. Cluster is running")
    exit(1)
