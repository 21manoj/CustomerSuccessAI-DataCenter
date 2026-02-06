#!/usr/bin/env python3
"""
Qdrant Collection Initialization
=================================

Creates all required Qdrant collections for CS Pulse system.

Collections:
- journey_weeks: Week-level customer data (main collection)
- events: Customer events and CSM actions
- accounts: Account-level metadata

Usage:
    python init_qdrant_collections.py --url http://localhost:6333
"""

import argparse
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, FieldCondition, PayloadSchemaType
from qdrant_client.http import models


def create_journey_weeks_collection(client: QdrantClient, collection_name: str = 'journey_weeks'):
    """
    Create journey_weeks collection
    
    This is the main collection storing week-by-week customer journey data.
    No vectors initially - can add later for similarity search.
    """
    
    print(f"\n📊 Creating collection: {collection_name}")
    
    try:
        # Check if exists
        collections = client.get_collections().collections
        if any(c.name == collection_name for c in collections):
            print(f"   ⚠️  Collection '{collection_name}' already exists")
            response = input("   Delete and recreate? (yes/no): ")
            if response.lower() == 'yes':
                client.delete_collection(collection_name)
                print(f"   🗑️  Deleted existing collection")
            else:
                print(f"   ⏭️  Skipping {collection_name}")
                return
        
        # Create collection (no vectors initially)
        client.create_collection(
            collection_name=collection_name,
            vectors_config={}  # No vectors for now
        )
        
        print(f"   ✅ Collection '{collection_name}' created")
        
        # Create payload indexes for efficient filtering
        print(f"   📇 Creating payload indexes...")
        
        # Index commonly filtered fields
        indexed_fields = [
            ('account_id', PayloadSchemaType.KEYWORD),
            ('week_number', PayloadSchemaType.INTEGER),
            ('date', PayloadSchemaType.KEYWORD),
            ('phase', PayloadSchemaType.KEYWORD),
            ('health_score', PayloadSchemaType.FLOAT),
            ('data_quality', PayloadSchemaType.FLOAT),
            ('data_quality_level', PayloadSchemaType.KEYWORD),
            ('has_escalation', PayloadSchemaType.BOOL),
            ('has_outage', PayloadSchemaType.BOOL),
            ('has_negative_sentiment', PayloadSchemaType.BOOL),
            ('is_crisis_start', PayloadSchemaType.BOOL),
            ('is_recovery_start', PayloadSchemaType.BOOL),
        ]
        
        for field_name, field_type in indexed_fields:
            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type
                )
                print(f"      ✓ Indexed: {field_name} ({field_type})")
            except Exception as e:
                print(f"      ⚠️  Failed to index {field_name}: {e}")
        
        print(f"   ✅ Payload indexes created")
        
    except Exception as e:
        print(f"   ❌ Failed to create collection: {e}")
        raise


def create_events_collection(client: QdrantClient, collection_name: str = 'events'):
    """
    Create events collection
    
    Stores customer events (outages, escalations, QBRs, etc.)
    """
    
    print(f"\n📅 Creating collection: {collection_name}")
    
    try:
        # Check if exists
        collections = client.get_collections().collections
        if any(c.name == collection_name for c in collections):
            print(f"   ⚠️  Collection '{collection_name}' already exists - skipping")
            return
        
        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config={}
        )
        
        print(f"   ✅ Collection '{collection_name}' created")
        
        # Create indexes
        indexed_fields = [
            ('account_id', PayloadSchemaType.KEYWORD),
            ('event_type', PayloadSchemaType.KEYWORD),
            ('event_date', PayloadSchemaType.KEYWORD),
            ('sentiment', PayloadSchemaType.KEYWORD),
            ('csm_action_type', PayloadSchemaType.KEYWORD),
        ]
        
        for field_name, field_type in indexed_fields:
            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type
                )
                print(f"      ✓ Indexed: {field_name}")
            except Exception as e:
                print(f"      ⚠️  Failed to index {field_name}: {e}")
        
    except Exception as e:
        print(f"   ❌ Failed to create collection: {e}")
        raise


def create_accounts_collection(client: QdrantClient, collection_name: str = 'accounts'):
    """
    Create accounts collection
    
    Stores account-level metadata and current state
    """
    
    print(f"\n🏢 Creating collection: {collection_name}")
    
    try:
        # Check if exists
        collections = client.get_collections().collections
        if any(c.name == collection_name for c in collections):
            print(f"   ⚠️  Collection '{collection_name}' already exists - skipping")
            return
        
        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config={}
        )
        
        print(f"   ✅ Collection '{collection_name}' created")
        
        # Create indexes
        indexed_fields = [
            ('account_id', PayloadSchemaType.KEYWORD),
            ('account_name', PayloadSchemaType.TEXT),
            ('industry', PayloadSchemaType.KEYWORD),
            ('tier', PayloadSchemaType.KEYWORD),
            ('current_health', PayloadSchemaType.FLOAT),
            ('current_phase', PayloadSchemaType.KEYWORD),
        ]
        
        for field_name, field_type in indexed_fields:
            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type
                )
                print(f"      ✓ Indexed: {field_name}")
            except Exception as e:
                print(f"      ⚠️  Failed to index {field_name}: {e}")
        
    except Exception as e:
        print(f"   ❌ Failed to create collection: {e}")
        raise


def verify_collections(client: QdrantClient):
    """Verify all collections were created successfully"""
    
    print(f"\n🔍 Verifying collections...")
    
    collections = client.get_collections().collections
    expected = ['journey_weeks', 'events', 'accounts']
    
    for name in expected:
        if any(c.name == name for c in collections):
            # Get collection info
            info = client.get_collection(name)
            print(f"   ✅ {name}")
            print(f"      Points: {info.points_count}")
            print(f"      Vectors: {len(info.config.params.vectors) if hasattr(info.config.params, 'vectors') else 0}")
        else:
            print(f"   ❌ {name} - NOT FOUND")
    
    print()


def main():
    """Main initialization"""
    
    parser = argparse.ArgumentParser(description='Initialize Qdrant collections for CS Pulse')
    parser.add_argument('--url', default='http://localhost:6333', help='Qdrant server URL')
    parser.add_argument('--recreate', action='store_true', help='Recreate existing collections')
    
    args = parser.parse_args()
    
    print("="*70)
    print("QDRANT COLLECTION INITIALIZATION")
    print("="*70)
    print(f"Server: {args.url}")
    print()
    
    try:
        # Connect to Qdrant
        print("🔌 Connecting to Qdrant...")
        client = QdrantClient(url=args.url)
        
        # Test connection
        client.get_collections()
        print("   ✅ Connected successfully")
        
        # Create collections
        create_journey_weeks_collection(client)
        create_events_collection(client)
        create_accounts_collection(client)
        
        # Verify
        verify_collections(client)
        
        print("="*70)
        print("✅ INITIALIZATION COMPLETE!")
        print("="*70)
        print()
        print("Next steps:")
        print("1. Start importing customer data")
        print("2. Run: python import_integration_adapter.py customers.xlsx")
        print("3. Verify data: python verify_qdrant_data.py")
        print()
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check Qdrant is running: docker ps | grep qdrant")
        print("2. Check URL is correct")
        print("3. Check network connectivity")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
