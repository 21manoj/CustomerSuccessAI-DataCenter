#!/usr/bin/env python3
"""
List all Qdrant collections
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def list_qdrant_collections():
    """List all Qdrant collections"""
    try:
        from qdrant_client import QdrantClient
        
        # Qdrant Cloud connection
        qdrant_url = os.getenv('QDRANT_URL')
        qdrant_api_key = os.getenv('QDRANT_API_KEY')
        
        if not qdrant_url or not qdrant_api_key:
            print("❌ QDRANT_URL and QDRANT_API_KEY are required")
            print("   Please set these environment variables in your .env file")
            return False
        
        # Connect to Qdrant Cloud
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            timeout=30
        )
        
        # Get collections
        collections = client.get_collections()
        
        print("=" * 60)
        print("QDRANT COLLECTIONS")
        print("=" * 60)
        print(f"Qdrant URL: {qdrant_url}")
        print(f"Total Collections: {len(collections.collections)}")
        print()
        
        if len(collections.collections) == 0:
            print("No collections found")
        else:
            print("Collection Details:")
            print("-" * 60)
            for i, collection in enumerate(collections.collections, 1):
                print(f"\n{i}. Collection Name: {collection.name}")
                
                # Get collection info
                try:
                    info = client.get_collection(collection.name)
                    print(f"   Points Count: {info.points_count}")
                    print(f"   Status: {info.status}")
                    
                    # Show vector config if available
                    if hasattr(info, 'config') and hasattr(info.config, 'params'):
                        if hasattr(info.config.params, 'vectors'):
                            vectors_config = info.config.params.vectors
                            if hasattr(vectors_config, 'size'):
                                print(f"   Vector Size: {vectors_config.size}")
                            if hasattr(vectors_config, 'distance'):
                                print(f"   Distance Metric: {vectors_config.distance}")
                except Exception as e:
                    print(f"   ⚠️  Could not get details: {str(e)[:100]}")
        
        print()
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ Error listing Qdrant collections: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = list_qdrant_collections()
    sys.exit(0 if success else 1)
