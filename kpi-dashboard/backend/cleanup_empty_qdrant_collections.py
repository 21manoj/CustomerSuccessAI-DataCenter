#!/usr/bin/env python3
"""
Cleanup all empty Qdrant collections (0 points)
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def cleanup_empty_qdrant_collections():
    """Delete all Qdrant collections with 0 points"""
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
        
        print("=" * 60)
        print("QDRANT EMPTY COLLECTION CLEANUP")
        print("=" * 60)
        print(f"Qdrant URL: {qdrant_url}")
        print()
        
        # Get all collections
        collections = client.get_collections()
        print(f"📊 Total collections: {len(collections.collections)}")
        print()
        
        empty_collections = []
        
        # Find all empty collections
        print("Scanning collections for empty ones...")
        for collection in collections.collections:
            try:
                info = client.get_collection(collection.name)
                if info.points_count == 0:
                    empty_collections.append(collection.name)
                    print(f"   Found empty: {collection.name}")
            except Exception as e:
                print(f"   ⚠️  Error checking {collection.name}: {str(e)[:100]}")
        
        if not empty_collections:
            print("\n✅ No empty collections found!")
            return True
        
        print(f"\n⚠️  WARNING: Found {len(empty_collections)} empty collections to delete:")
        for name in empty_collections:
            print(f"   - {name}")
        print()
        
        # Confirm deletion
        response = input("Do you want to proceed with deletion? (yes/no): ").strip().lower()
        if response != 'yes':
            print("❌ Cleanup cancelled")
            return False
        
        print()
        print("Deleting empty collections...")
        print("-" * 60)
        
        deleted = []
        errors = []
        
        for collection_name in empty_collections:
            try:
                client.delete_collection(collection_name)
                deleted.append(collection_name)
                print(f"✅ Deleted: {collection_name}")
            except Exception as e:
                errors.append((collection_name, str(e)))
                print(f"❌ Error deleting {collection_name}: {str(e)[:100]}")
        
        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully deleted: {len(deleted)}")
        if deleted:
            for name in deleted:
                print(f"   - {name}")
        
        if errors:
            print(f"\n❌ Errors: {len(errors)}")
            for name, error in errors:
                print(f"   - {name}: {error[:100]}")
        
        print("=" * 60)
        return len(errors) == 0
        
    except Exception as e:
        print(f"❌ Error connecting to Qdrant: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = cleanup_empty_qdrant_collections()
    sys.exit(0 if success else 1)
