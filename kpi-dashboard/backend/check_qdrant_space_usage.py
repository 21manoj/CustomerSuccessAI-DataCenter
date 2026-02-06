#!/usr/bin/env python3
"""
Check total space usage of Qdrant collections
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_qdrant_space_usage():
    """Check space usage of all Qdrant collections"""
    try:
        from qdrant_client import QdrantClient
        
        # Qdrant Cloud connection
        qdrant_url = os.getenv('QDRANT_URL')
        qdrant_api_key = os.getenv('QDRANT_API_KEY')
        
        if not qdrant_url or not qdrant_api_key:
            print("❌ QDRANT_URL and QDRANT_API_KEY are required")
            return False
        
        # Connect to Qdrant Cloud
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            timeout=30
        )
        
        print("=" * 60)
        print("QDRANT SPACE USAGE ANALYSIS")
        print("=" * 60)
        print(f"Qdrant URL: {qdrant_url}")
        print()
        
        # Get all collections
        collections = client.get_collections()
        
        total_points = 0
        total_vectors_size = 0
        collection_details = []
        
        print("Analyzing collections...")
        for collection in collections.collections:
            try:
                info = client.get_collection(collection.name)
                points = info.points_count
                total_points += points
                
                # Calculate approximate size
                # Each point has a vector (3072 dimensions * 4 bytes = 12,288 bytes for float32)
                # Plus payload data (varies, estimate ~1KB per point)
                vector_size = 0
                if hasattr(info.config, 'params') and hasattr(info.config.params, 'vectors'):
                    vectors_config = info.config.params.vectors
                    if hasattr(vectors_config, 'size'):
                        vector_dim = vectors_config.size
                        # float32 = 4 bytes per dimension
                        vector_bytes_per_point = vector_dim * 4
                        # Estimate payload as 1KB per point
                        estimated_payload = 1024
                        vector_size = points * (vector_bytes_per_point + estimated_payload)
                        total_vectors_size += vector_size
                
                collection_details.append({
                    'name': collection.name,
                    'points': points,
                    'estimated_size_mb': vector_size / (1024 * 1024)
                })
            except Exception as e:
                print(f"   ⚠️  Error analyzing {collection.name}: {str(e)[:100]}")
        
        # Sort by size
        collection_details.sort(key=lambda x: x['estimated_size_mb'], reverse=True)
        
        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total Collections: {len(collections.collections)}")
        print(f"Total Points: {total_points:,}")
        print(f"Estimated Total Size: {total_vectors_size / (1024 * 1024):.2f} MB")
        print(f"Estimated Total Size: {total_vectors_size / (1024 * 1024 * 1024):.2f} GB")
        print()
        
        print("Top 10 Largest Collections:")
        print("-" * 60)
        for i, detail in enumerate(collection_details[:10], 1):
            print(f"{i:2d}. {detail['name']:50s} {detail['points']:6,} points  {detail['estimated_size_mb']:8.2f} MB")
        
        print()
        print("=" * 60)
        
        # Try to get cluster info if available
        try:
            cluster_info = client.get_cluster_info()
            if hasattr(cluster_info, 'status'):
                print(f"Cluster Status: {cluster_info.status}")
        except:
            pass  # Cluster info might not be available
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = check_qdrant_space_usage()
    sys.exit(0 if success else 1)
