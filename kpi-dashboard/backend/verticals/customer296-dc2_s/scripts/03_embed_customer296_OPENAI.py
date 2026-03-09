#!/usr/bin/env python3
"""
Generate OpenAI Embeddings for Customer 296 (Production Architecture)
===================================================================

Matches the architecture of Customers 1 and 5:
- Collection: kpi_dashboard_vectors_customer_296
- Model: text-embedding-3-large (3072 dimensions)
- Batched upload to avoid timeouts

Usage:
    export OPENAI_API_KEY="your-key-here"
    python3 03_embed_customer296_OPENAI.py
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI
import time
import uuid

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/cs_pulse_datacenter')
QDRANT_URL = os.getenv('QDRANT_URL', 'https://7528cec3-24f4-4584-bee2-ca371726134a.us-east-1-1.aws.cloud.qdrant.io:6333')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8t-hHzNql_9C-BEBs2Pye0l942C6HbBvz7Ro_DDKEH4')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

CUSTOMER_ID = 296
COLLECTION_NAME = f'kpi_dashboard_vectors_customer_296'
EMBEDDING_MODEL = 'text-embedding-3-large'
EMBEDDING_DIMENSIONS = 3072
BATCH_SIZE = 50

print("=" * 80)
print("CUSTOMER 296 OPENAI EMBEDDINGS - Production Architecture")
print("=" * 80)
print()

# Validate
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY environment variable not set!")
    print("   Set it with: export OPENAI_API_KEY='your-key-here'")
    exit(1)

print("🔧 Configuration:")
print(f"   Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")
print(f"   Qdrant: {QDRANT_URL}")
print(f"   Collection: {COLLECTION_NAME}")
print(f"   Model: {EMBEDDING_MODEL}")
print(f"   Dimensions: {EMBEDDING_DIMENSIONS}")
print(f"   Batch size: {BATCH_SIZE}")
print()

# Initialize clients
print("🔌 Connecting...")
openai_client = OpenAI(api_key=OPENAI_API_KEY)
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)
print("   ✅ All connections established")
print()

# Create or recreate collection
print(f"📁 Setting up collection '{COLLECTION_NAME}'...")
try:
    qdrant.delete_collection(collection_name=COLLECTION_NAME)
    print(f"   Deleted existing collection")
except Exception:
    print(f"   No existing collection to delete")

qdrant.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=EMBEDDING_DIMENSIONS, distance=Distance.COSINE)
)
print(f"   ✅ Created collection")
print()

# Create payload indexes
print("📊 Creating payload indexes...")
indexes = [
    ("type", "keyword"),
    ("account_id", "integer"),
    ("signal_type", "keyword"),
    ("category", "keyword"),
    ("sentiment", "keyword")
]

for field, field_type in indexes:
    try:
        from qdrant_client.models import PayloadSchemaType
        schema_type = PayloadSchemaType.KEYWORD if field_type == "keyword" else PayloadSchemaType.INTEGER
        qdrant.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema=schema_type
        )
        print(f"   ✅ Created index: {field}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"   ℹ️  Index exists: {field}")
        else:
            print(f"   ⚠️  Failed: {field} - {e}")
print()

# ============================================================================
# EMBED QUALITATIVE SIGNALS
# ============================================================================
print("=" * 80)
print("EMBEDDING QUALITATIVE SIGNALS")
print("=" * 80)
print()

cursor.execute("""
    SELECT 
        signal_id,
        account_id,
        signal_type,
        signal_date,
        content,
        sentiment,
        sentiment_score,
        stakeholder_level,
        stakeholder_title,
        keywords,
        is_narrative_signal
    FROM qualitative_signals
    WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = %s)
    ORDER BY signal_id
""", (CUSTOMER_ID,))

signals = cursor.fetchall()
print(f"📊 Found {len(signals)} qualitative signals")
print()

if signals:
    # Get account names for better context
    cursor.execute("""
        SELECT account_id, account_name 
        FROM accounts 
        WHERE customer_id = %s
    """, (CUSTOMER_ID,))
    account_names = {row['account_id']: row['account_name'] for row in cursor.fetchall()}
    
    print("🔄 Generating embeddings with OpenAI...")
    all_points = []
    
    # Process in batches for OpenAI API
    for i in range(0, len(signals), BATCH_SIZE):
        batch = signals[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(signals) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"   Batch {batch_num}/{total_batches}: Generating embeddings for {len(batch)} signals...", end=" ", flush=True)
        
        # Prepare texts for embedding
        texts = [s['content'] for s in batch]
        
        try:
            # Call OpenAI API
            response = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts
            )
            
            # Create points
            for j, signal in enumerate(batch):
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"signal-{signal['signal_id']}"))
                embedding = response.data[j].embedding
                
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "type": "qualitative_signal",
                        "signal_id": signal['signal_id'],
                        "account_id": signal['account_id'],
                        "account_name": account_names.get(signal['account_id'], 'Unknown'),
                        "signal_type": signal['signal_type'],
                        "signal_date": signal['signal_date'].isoformat() if signal['signal_date'] else None,
                        "content": signal['content'],
                        "subject": signal['content'][:100],  # First 100 chars as subject
                        "sentiment": signal['sentiment'],
                        "sentiment_score": float(signal['sentiment_score']) if signal['sentiment_score'] else None,
                        "stakeholder_level": signal['stakeholder_level'],
                        "stakeholder_title": signal['stakeholder_title'],
                        "keywords": signal['keywords'],
                        "is_narrative_signal": signal['is_narrative_signal']
                    }
                )
                all_points.append(point)
            
            print("✅")
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"❌ Error: {e}")
            break
    
    print(f"   ✅ Generated {len(all_points)} embeddings")
    print()
    
    # Upload to Qdrant in batches
    print(f"⬆️  Uploading to Qdrant in batches of {BATCH_SIZE}...")
    uploaded = 0
    
    for i in range(0, len(all_points), BATCH_SIZE):
        batch = all_points[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(all_points) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"   Batch {batch_num}/{total_batches}: Uploading {len(batch)} points...", end=" ", flush=True)
        
        try:
            qdrant.upsert(collection_name=COLLECTION_NAME, points=batch)
            uploaded += len(batch)
            print("✅")
            time.sleep(0.1)
        except Exception as e:
            print(f"❌ Error: {e}")
            break
    
    print()
    print(f"✅ Uploaded {uploaded}/{len(signals)} qualitative signals")
    print()

# ============================================================================
# EMBED KPI DEFINITIONS
# ============================================================================
print("=" * 80)
print("EMBEDDING KPI DEFINITIONS")
print("=" * 80)
print()

cursor.execute("""
    SELECT 
        kpi_code,
        kpi_name,
        pillar,
        indicator_type,
        direction,
        business_impact,
        causal_kpis,
        correlated_kpis,
        triggered_playbooks,
        notes
    FROM kpi_definitions
    ORDER BY kpi_code
""")

kpis = cursor.fetchall()
print(f"📊 Found {len(kpis)} KPI definitions")
print()

if kpis:
    print("🔄 Generating embeddings with OpenAI...")
    all_points = []
    
    # Create text representations
    texts = []
    for kpi in kpis:
        parts = [
            f"KPI: {kpi['kpi_name']}",
            f"Type: {kpi['indicator_type']}",
            f"Direction: {kpi['direction']}",
        ]
        if kpi['business_impact']:
            parts.append(f"Impact: {kpi['business_impact']}")
        if kpi['notes']:
            parts.append(f"Notes: {kpi['notes']}")
        texts.append(" | ".join(parts))
    
    # Get embeddings from OpenAI
    print(f"   Calling OpenAI API for {len(kpis)} KPIs...", end=" ", flush=True)
    try:
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts
        )
        print("✅")
        
        # Create points
        for i, kpi in enumerate(kpis):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"kpi-{kpi['kpi_code']}"))
            embedding = response.data[i].embedding
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "type": "kpi_definition",
                    "kpi_code": kpi['kpi_code'],
                    "kpi_name": kpi['kpi_name'],
                    "category": kpi['pillar'],  # Map pillar to category
                    "pillar": kpi['pillar'],
                    "indicator_type": kpi['indicator_type'],
                    "direction": kpi['direction'],
                    "business_impact": kpi['business_impact'],
                    "causal_kpis": kpi['causal_kpis'],
                    "correlated_kpis": kpi['correlated_kpis'],
                    "triggered_playbooks": kpi['triggered_playbooks'],
                    "notes": kpi['notes']
                }
            )
            all_points.append(point)
        
        print(f"   ✅ Generated {len(all_points)} embeddings")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        all_points = []
    
    # Upload to Qdrant
    if all_points:
        print(f"⬆️  Uploading {len(all_points)} KPIs to Qdrant...", end=" ", flush=True)
        try:
            qdrant.upsert(collection_name=COLLECTION_NAME, points=all_points)
            print("✅")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print()
    print(f"✅ Uploaded {len(all_points)}/{len(kpis)} KPI definitions")
    print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()

collection_info = qdrant.get_collection(collection_name=COLLECTION_NAME)
print(f"📊 Collection: {COLLECTION_NAME}")
print(f"   Vectors: {collection_info.points_count}")
print(f"   Dimension: {EMBEDDING_DIMENSIONS}")
print(f"   Distance: COSINE")
print(f"   Model: {EMBEDDING_MODEL}")
print()

expected = len(signals) + len(kpis)
if collection_info.points_count == expected:
    print("✅ SUCCESS: All embeddings uploaded!")
    print()
    print("🎯 Customer 296 now matches production architecture:")
    print("   - Collection name: kpi_dashboard_vectors_customer_296 ✅")
    print("   - Embedding model: OpenAI text-embedding-3-large ✅")
    print("   - Dimensions: 3072 ✅")
    print("   - Consistent with Customers 1 and 5 ✅")
    print()
else:
    print(f"⚠️  WARNING: Expected {expected} vectors, got {collection_info.points_count}")
    print()

cursor.close()
conn.close()
print("✅ Done!")
print()
