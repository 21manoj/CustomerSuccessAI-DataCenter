#!/usr/bin/env python3
"""
Cleanup script to remove old category-based collections from Qdrant Cloud
Keeps only per-customer collections following the pattern: kpi_dashboard_vectors_customer_{customer_id}
"""

import os
import sys
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

def main(confirm=True):
    qdrant_url = os.getenv('QDRANT_URL')
    qdrant_api_key = os.getenv('QDRANT_API_KEY')

    if not qdrant_url or not qdrant_api_key:
        print("❌ QDRANT_URL or QDRANT_API_KEY not set")
        sys.exit(1)

    print("=" * 70)
    print("CLEANUP OLD CATEGORY-BASED COLLECTIONS")
    print("=" * 70)
    print()

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=30)

    # Get all collections
    collections = client.get_collections().collections
    print(f"Found {len(collections)} collections\n")

    old_model_collections = []
    per_customer_collections = []
    unknown_collections = []

    for coll in collections:
        info = client.get_collection(coll.name)
        points = info.points_count

        # Identify old model collections (category-based)
        if any(pattern in coll.name for pattern in ['_signals_', '_temporal', '_historical']):
            old_model_collections.append((coll.name, points))
        elif '_customer_' in coll.name and coll.name.startswith('kpi_dashboard_vectors_customer_'):
            per_customer_collections.append((coll.name, points))
        else:
            unknown_collections.append((coll.name, points))

    print("Collections to DELETE (old category-based model):")
    if old_model_collections:
        for name, points in old_model_collections:
            print(f"  ❌ {name} ({points} points)")
    else:
        print("  (none found)")

    print()
    print("Collections to KEEP (per-customer model):")
    for name, points in per_customer_collections:
        print(f"  ✅ {name} ({points} points)")

    if unknown_collections:
        print()
        print("⚠️  Unknown collections (not matching either pattern):")
        for name, points in unknown_collections:
            print(f"  ? {name} ({points} points)")
        if confirm:
            print()
            response = input("Delete unknown collections as well? (yes/no): ").strip().lower()
            if response == 'yes':
                old_model_collections.extend(unknown_collections)
        else:
            # In non-interactive mode, don't delete unknown collections
            print("  (Skipping unknown collections in non-interactive mode)")

    print()
    if not old_model_collections:
        print("✅ No old collections to delete!")
        return

    print(f"⚠️  WARNING: About to delete {len(old_model_collections)} collections:")
    for name, points in old_model_collections:
        print(f"   - {name} ({points} points)")
    print()
    
    if confirm:
        response = input("Are you sure you want to proceed? (yes/no): ").strip().lower()
        if response != 'yes':
            print("❌ Cancelled. No collections deleted.")
            return
    else:
        print("Auto-confirmed (non-interactive mode)")

    print()
    print("Deleting collections...")
    deleted = []
    errors = []

    for name, points in old_model_collections:
        try:
            client.delete_collection(name)
            deleted.append((name, points))
            print(f"  ✅ Deleted: {name} ({points} points)")
        except Exception as e:
            errors.append((name, str(e)))
            print(f"  ❌ Failed to delete {name}: {e}")

    print()
    print("=" * 70)
    print("CLEANUP SUMMARY")
    print("=" * 70)
    print(f"✅ Successfully deleted: {len(deleted)} collections")
    for name, points in deleted:
        print(f"   - {name} ({points} points)")

    if errors:
        print()
        print(f"❌ Failed to delete: {len(errors)} collections")
        for name, error in errors:
            print(f"   - {name}: {error}")

    print()
    print("Remaining collections (per-customer):")
    remaining = client.get_collections().collections
    for coll in remaining:
        info = client.get_collection(coll.name)
        print(f"  ✅ {coll.name} ({info.points_count} points)")

    print()
    print("✅ Cleanup complete!")

if __name__ == "__main__":
    # Check for --yes flag for non-interactive mode
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv
    main(confirm=not auto_confirm)

