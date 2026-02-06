#!/usr/bin/env python3
"""
Cleanup specific Qdrant collections
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def cleanup_qdrant_collections(collection_names):
    """Delete specified Qdrant collections"""
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
        print("QDRANT COLLECTION CLEANUP")
        print("=" * 60)
        print(f"Qdrant URL: {qdrant_url}")
        print(f"Collections to delete: {len(collection_names)}")
        print()
        
        deleted = []
        not_found = []
        errors = []
        
        for collection_name in collection_names:
            try:
                # Check if collection exists
                try:
                    info = client.get_collection(collection_name)
                    points_count = info.points_count
                    
                    # Delete the collection
                    client.delete_collection(collection_name)
                    deleted.append((collection_name, points_count))
                    print(f"✅ Deleted: {collection_name} ({points_count} points)")
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'not found' in error_msg or 'does not exist' in error_msg:
                        not_found.append(collection_name)
                        print(f"⚠️  Not found: {collection_name}")
                    else:
                        raise
            except Exception as e:
                errors.append((collection_name, str(e)))
                print(f"❌ Error deleting {collection_name}: {str(e)[:100]}")
        
        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully deleted: {len(deleted)}")
        for name, points in deleted:
            print(f"   - {name} ({points} points)")
        
        if not_found:
            print(f"\n⚠️  Not found: {len(not_found)}")
            for name in not_found:
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
    # Collections to delete
    collections_to_delete = [
        'kpi_dashboard_vectors_customer_130',
        'kpi_dashboard_vectors_customer_129',
        'kpi_dashboard_vectors_customer_128',
        'kpi_dashboard_vectors_customer_149',
        'kpi_dashboard_vectors_customer_150',
        'kpi_dashboard_vectors_customer_127',
        'kpi_dashboard_vectors_customer_126',
        'kpi_dashboard_vectors_customer_147',
        'kpi_dashboard_vectors_customer_143',
        'kpi_dashboard_vectors_customer_146',
        'kpi_dashboard_vectors_customer_148',
        'kpi_dashboard_vectors_customer_145',
    ]
    
    print("⚠️  WARNING: This will permanently delete the following collections:")
    for name in collections_to_delete:
        print(f"   - {name}")
    print()
    
    # Confirm deletion
    response = input("Do you want to proceed? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ Cleanup cancelled")
        sys.exit(0)
    
    success = cleanup_qdrant_collections(collections_to_delete)
    sys.exit(0 if success else 1)
