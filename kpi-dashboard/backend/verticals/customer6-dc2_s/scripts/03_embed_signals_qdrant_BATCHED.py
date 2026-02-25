#!/usr/bin/env python3
"""
Generate embeddings for qualitative signals and KPI definitions
Upload to Qdrant in batches to avoid timeouts
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import time

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/cs_pulse_datacenter')
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
COLLECTION_NAME = 'customer_signals'
EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
BATCH_SIZE = 50  # Upload 50 points at a time

print("=" * 80)
print("CUSTOMER 6 EMBEDDINGS GENERATOR - Batched Upload")
print("=" * 80)
print()

# Initialize
print("🔧 Initializing...")
print(f"   Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")
print(f"   Qdrant: {QDRANT_URL}")
print(f"   Batch size: {BATCH_SIZE} points")
print()

# Load embedding model
print("📦 Loading embedding model...")
model = SentenceTransformer(EMBEDDING_MODEL)
embedding_dim = model.get_sentence_embedding_dimension()
print(f"   Model: {EMBEDDING_MODEL}")
print(f"   Dimension: {embedding_dim}")
print()

# Connect to database
print("🔌 Connecting to PostgreSQL...")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)
print("   ✅ Connected")
print()

# Connect to Qdrant
print("🔌 Connecting to Qdrant...")
qdrant = QdrantClient(url=QDRANT_URL)
print("   ✅ Connected")
print()

# Create or recreate collection
print("📁 Setting up Qdrant collection...")
try:
    qdrant.delete_collection(collection_name=COLLECTION_NAME)
    print(f"   Deleted existing collection: {COLLECTION_NAME}")
except Exception as e:
    print(f"   No existing collection to delete")

qdrant.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE)
)
print(f"   ✅ Created collection: {COLLECTION_NAME}")
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
        signal_text,
        sentiment,
        confidence_score,
        source,
        metadata
    FROM qualitative_signals
    WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 6)
    ORDER BY signal_id
""")

signals = cursor.fetchall()
print(f"📊 Found {len(signals)} qualitative signals")
print()

if signals:
    print("🔄 Generating embeddings...")
    
    # Generate all embeddings first
    signal_texts = [s['signal_text'] for s in signals]
    embeddings = model.encode(signal_texts, show_progress_bar=True)
    
    print(f"   ✅ Generated {len(embeddings)} embeddings")
    print()
    
    # Prepare points
    points = []
    for i, signal in enumerate(signals):
        point = PointStruct(
            id=f"signal-{signal['signal_id']}",
            vector=embeddings[i].tolist(),
            payload={
                "type": "signal",
                "signal_id": signal['signal_id'],
                "account_id": signal['account_id'],
                "signal_type": signal['signal_type'],
                "signal_date": signal['signal_date'].isoformat() if signal['signal_date'] else None,
                "signal_text": signal['signal_text'],
                "sentiment": signal['sentiment'],
                "confidence_score": float(signal['confidence_score']) if signal['confidence_score'] else None,
                "source": signal['source'],
                "metadata": signal['metadata']
            }
        )
        points.append(point)
    
    # Upload in batches
    print(f"⬆️  Uploading to Qdrant in batches of {BATCH_SIZE}...")
    total_uploaded = 0
    
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(points) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"   Batch {batch_num}/{total_batches}: Uploading {len(batch)} points...", end=" ")
        
        try:
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=batch
            )
            total_uploaded += len(batch)
            print("✅")
            time.sleep(0.1)  # Small delay between batches
        except Exception as e:
            print(f"❌ Error: {e}")
            print(f"   Failed to upload batch {batch_num}")
            break
    
    print()
    print(f"✅ Uploaded {total_uploaded}/{len(signals)} qualitative signals")
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
    print("🔄 Generating embeddings...")
    
    # Create text representations
    kpi_texts = []
    for kpi in kpis:
        text_parts = [
            f"KPI: {kpi['kpi_name']}",
            f"Type: {kpi['indicator_type']}",
            f"Direction: {kpi['direction']}",
        ]
        
        if kpi['business_impact']:
            text_parts.append(f"Impact: {kpi['business_impact']}")
        
        if kpi['notes']:
            text_parts.append(f"Notes: {kpi['notes']}")
        
        kpi_texts.append(" | ".join(text_parts))
    
    # Generate embeddings
    embeddings = model.encode(kpi_texts, show_progress_bar=True)
    
    print(f"   ✅ Generated {len(embeddings)} embeddings")
    print()
    
    # Prepare points
    points = []
    for i, kpi in enumerate(kpis):
        point = PointStruct(
            id=f"kpi-{kpi['kpi_code']}",
            vector=embeddings[i].tolist(),
            payload={
                "type": "kpi",
                "kpi_code": kpi['kpi_code'],
                "kpi_name": kpi['kpi_name'],
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
        points.append(point)
    
    # Upload in batches
    print(f"⬆️  Uploading to Qdrant in batches of {BATCH_SIZE}...")
    total_uploaded = 0
    
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(points) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"   Batch {batch_num}/{total_batches}: Uploading {len(batch)} points...", end=" ")
        
        try:
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=batch
            )
            total_uploaded += len(batch)
            print("✅")
            time.sleep(0.1)  # Small delay between batches
        except Exception as e:
            print(f"❌ Error: {e}")
            print(f"   Failed to upload batch {batch_num}")
            break
    
    print()
    print(f"✅ Uploaded {total_uploaded}/{len(kpis)} KPI definitions")
    print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()

# Get final collection info
collection_info = qdrant.get_collection(collection_name=COLLECTION_NAME)
print(f"📊 Collection: {COLLECTION_NAME}")
print(f"   Vectors: {collection_info.points_count}")
print(f"   Dimension: {embedding_dim}")
print(f"   Distance: COSINE")
print()

total_expected = len(signals) + len(kpis)
if collection_info.points_count == total_expected:
    print("✅ SUCCESS: All embeddings uploaded!")
    print()
    print("Next steps:")
    print("  1. Validate: python3 scripts/04_validate_data_integrity.py")
    print("  2. Test semantic search in your application")
else:
    print(f"⚠️  WARNING: Expected {total_expected} vectors, got {collection_info.points_count}")
    print()

cursor.close()
conn.close()
print("✅ Done!")
print()
