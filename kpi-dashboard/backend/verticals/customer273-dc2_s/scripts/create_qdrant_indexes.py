#!/usr/bin/env python3
"""
Create Qdrant Payload Indexes for Customer 273
=============================================

Creates indexes on frequently filtered fields:
- type (signal vs kpi)
- account_id (filter by account)
- signal_type (filter by signal type)
- pillar (filter by KPI pillar)

Usage:
    python3 create_qdrant_indexes.py
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "https://7528cec3-24f4-4584-bee2-ca371726134a.us-east-1-1.aws.cloud.qdrant.io:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8t-hHzNql_9C-BEBs2Pye0l942C6HbBvz7Ro_DDKEH4")
COLLECTION_NAME = "customer_signals"

print("=" * 80)
print("CREATING QDRANT PAYLOAD INDEXES")
print("=" * 80)
print()

# Connect to Qdrant
print(f"🔌 Connecting to Qdrant Cloud...")
print(f"   URL: {QDRANT_URL}")
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
print(f"   ✅ Connected")
print()

# Check collection exists
collections = [c.name for c in qdrant.get_collections().collections]
if COLLECTION_NAME not in collections:
    print(f"❌ Collection '{COLLECTION_NAME}' not found!")
    print(f"   Run: python3 scripts/03_embed_signals_qdrant.py first")
    exit(1)

print(f"✅ Collection '{COLLECTION_NAME}' found")
print()

# Define indexes to create
indexes = [
    {
        "field_name": "type",
        "field_schema": PayloadSchemaType.KEYWORD,
        "description": "Filter by signal vs kpi"
    },
    {
        "field_name": "account_id",
        "field_schema": PayloadSchemaType.INTEGER,
        "description": "Filter by account"
    },
    {
        "field_name": "signal_type",
        "field_schema": PayloadSchemaType.KEYWORD,
        "description": "Filter by signal type (email, meeting, etc)"
    },
    {
        "field_name": "pillar",
        "field_schema": PayloadSchemaType.KEYWORD,
        "description": "Filter by KPI pillar"
    },
    {
        "field_name": "sentiment",
        "field_schema": PayloadSchemaType.KEYWORD,
        "description": "Filter by sentiment"
    }
]

print("📊 Creating payload indexes...")
print("─" * 80)

success_count = 0
for idx in indexes:
    field = idx["field_name"]
    schema = idx["field_schema"]
    desc = idx["description"]
    
    print(f"\n  Creating index: {field}")
    print(f"    Type: {schema}")
    print(f"    Purpose: {desc}")
    
    try:
        qdrant.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema=schema
        )
        print(f"    ✅ Created successfully")
        success_count += 1
    except Exception as e:
        error_msg = str(e)
        if "already exists" in error_msg.lower():
            print(f"    ℹ️  Already exists (skipped)")
            success_count += 1
        else:
            print(f"    ❌ Error: {e}")

print()
print("─" * 80)
print(f"✅ Created/verified {success_count}/{len(indexes)} indexes")
print()

# Verify indexes
print("🔍 Verifying indexes...")
collection_info = qdrant.get_collection(COLLECTION_NAME)
print(f"   Collection: {COLLECTION_NAME}")
print(f"   Points: {collection_info.points_count:,}")

if hasattr(collection_info.config, 'payload_schema'):
    print(f"   Payload indexes: {len(collection_info.config.payload_schema)} field(s)")
else:
    print(f"   Payload indexes: Verification not available (but created)")

print()
print("=" * 80)
print("✅ DONE! Indexes are ready")
print("=" * 80)
print()
print("Next step:")
print("  Run validation: python3 scripts/04_validate_data_integrity.py")
print()
