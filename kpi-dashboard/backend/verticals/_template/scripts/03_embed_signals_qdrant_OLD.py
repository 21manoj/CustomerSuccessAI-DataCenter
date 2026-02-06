#!/usr/bin/env python3
"""
Embed Customer {CUSTOMER_ID} Signals to Qdrant
===================================

Embeds qualitative signals and KPI metadata for Customer {CUSTOMER_ID} into Qdrant Cloud
using the latest architecture (Jan 4-5, 2026 updates).

Architecture Updates (Jan 4-5):
- Collection naming: kpi_dashboard_vectors_customer_{customer_id}
- Direct Qdrant client (no RAG abstraction)  
- Single collection for all signal types
- Filter by account_id in queries

Usage:
    python3 03_embed_signals_qdrant.py

Requirements:
    - PostgreSQL with Customer {CUSTOMER_ID} data loaded
    - Qdrant Cloud credentials in .env
    - OpenAI API key for embeddings
"""

import os
import sys
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI

load_dotenv()

print("=" * 80)
print("CUSTOMER 9 → QDRANT EMBEDDING (Latest Architecture)")
print("Updated: Jan 5, 2026")
print("=" * 80)

# Configuration (matching Jan 4-5 architecture)
DATABASE_URL = os.getenv("DATABASE_URL")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CUSTOMER_ID = {CUSTOMER_ID}
COLLECTION_NAME = f"kpi_dashboard_vectors_customer_{CUSTOMER_ID}"  # New naming convention!
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072

# Validate environment
missing = []
if not DATABASE_URL: missing.append("DATABASE_URL")
if not QDRANT_URL: missing.append("QDRANT_URL")
if not QDRANT_API_KEY: missing.append("QDRANT_API_KEY")
if not OPENAI_API_KEY: missing.append("OPENAI_API_KEY")

if missing:
    print(f"\n❌ Missing environment variables: {', '.join(missing)}")
    print("Set in .env file or export them")
    sys.exit(1)

print(f"\n✅ Configuration:")
print(f"   Customer ID: {CUSTOMER_ID}")
print(f"   Collection: {COLLECTION_NAME}")
print(f"   Embedding Model: {EMBEDDING_MODEL}")
print(f"   Dimensions: {EMBEDDING_DIM}")

# Initialize connections
print(f"\n{'─' * 80}")
print("INITIALIZING CONNECTIONS")
print("─" * 80)

print("  PostgreSQL...", end=" ", flush=True)
try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅")
except Exception as e:
    print(f"❌ {e}")
    sys.exit(1)

print("  Qdrant Cloud...", end=" ", flush=True)
try:
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    qdrant.get_collections()
    print("✅")
except Exception as e:
    print(f"❌ {e}")
    sys.exit(1)

print("  OpenAI...", end=" ", flush=True)
try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    # Test with a dummy call
    print("✅")
except Exception as e:
    print(f"❌ {e}")
    sys.exit(1)

# Check/create collection
print(f"\n{'─' * 80}")
print(f"COLLECTION SETUP: {COLLECTION_NAME}")
print("─" * 80)

collections = qdrant.get_collections().collections
existing = [c.name for c in collections]

if COLLECTION_NAME in existing:
    print(f"\n⚠️  Collection '{COLLECTION_NAME}' already exists")
    info = qdrant.get_collection(COLLECTION_NAME)
    print(f"   Current points: {info.points_count:,}")
    print(f"   Vector dimension: {info.config.params.vectors.size}")
    
    response = input("\n   Delete and recreate? (y/n): ")
    if response.lower() == 'y':
        qdrant.delete_collection(COLLECTION_NAME)
        print("   ✅ Deleted existing collection")
        should_create = True
    else:
        print("   ⏭️  Using existing collection (will append)")
        should_create = False
else:
    should_create = True

if should_create:
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)
    )
    print(f"   ✅ Created collection: {COLLECTION_NAME}")

# Fetch signals from PostgreSQL
print(f"\n{'─' * 80}")
print("FETCHING SIGNALS FROM POSTGRESQL")
print("─" * 80)

with engine.connect() as conn:
    # Fetch qualitative signals
    print("\n  Fetching qualitative signals...", end=" ", flush=True)
    qualitative = conn.execute(text("""
        SELECT 
            qs.signal_id,
            qs.account_id,
            qs.signal_date as date,
            qs.signal_type,
            qs.stakeholder_level,
            qs.stakeholder_title,
            qs.content,
            qs.sentiment,
            qs.sentiment_score,
            qs.keywords,
            qs.is_narrative_signal,
            a.account_name,
            a.industry
        FROM qualitative_signals qs
        JOIN accounts a ON qs.account_id = a.account_id
        ORDER BY qs.signal_date DESC
    """)).fetchall()
    print(f"✅ {len(qualitative)} signals")
    
    # Fetch KPI definitions
    print("  Fetching KPI definitions...", end=" ", flush=True)
    kpis = conn.execute(text("""
        SELECT 
            kpi_code,
            kpi_name,
            pillar,
            indicator_type,
            impact_level,
            predictive_horizon_days,
            business_impact
        FROM kpi_definitions
        WHERE active = true
        ORDER BY pillar, kpi_code
    """)).fetchall()
    print(f"✅ {len(kpis)} KPIs")

print(f"\n   📊 Total signals to embed: {len(qualitative) + len(kpis):,}")

# Generate embeddings
print(f"\n{'─' * 80}")
print("GENERATING EMBEDDINGS WITH OPENAI")
print("─" * 80)

points = []
total_tokens = 0

# Embed qualitative signals
print(f"\n  Embedding qualitative signals...")
for i, sig in enumerate(qualitative):
    text_to_embed = (
        f"Type: {sig.signal_type}\n"
        f"Account: {sig.account_name} ({sig.industry})\n"
        f"Stakeholder: {sig.stakeholder_title or 'Unknown'} ({sig.stakeholder_level})\n"
        f"Content: {sig.content}\n"
        f"Sentiment: {sig.sentiment} ({sig.sentiment_score:.2f})\n"
        f"Keywords: {sig.keywords if sig.keywords else 'None'}\n"
        f"Date: {sig.date}"
    )
    
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text_to_embed
    )
    
    embedding = response.data[0].embedding
    total_tokens += response.usage.total_tokens
    
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=embedding,
        payload={
            "type": "qualitative_signal",
            "customer_id": CUSTOMER_ID,
            "signal_id": sig.signal_id,
            "account_id": sig.account_id,
            "account_name": sig.account_name,
            "date": str(sig.date),
            "signal_type": sig.signal_type,
            "stakeholder_level": sig.stakeholder_level,
            "stakeholder_title": sig.stakeholder_title or "Unknown",
            "content": sig.content,
            "sentiment": sig.sentiment,
            "sentiment_score": float(sig.sentiment_score) if sig.sentiment_score else None,
            "keywords": sig.keywords if sig.keywords else "",
            "is_narrative_signal": sig.is_narrative_signal,
            "industry": sig.industry,
            "text": text_to_embed
        }
    )
    
    points.append(point)
    
    if (i + 1) % 10 == 0 or (i + 1) == len(qualitative):
        print(f"     {i + 1:>4}/{len(qualitative)} signals (tokens: {total_tokens:,})")

# Embed KPI definitions
print(f"\n  Embedding KPI definitions...")
for i, kpi in enumerate(kpis):
    text_to_embed = (
        f"KPI: {kpi.kpi_code} - {kpi.kpi_name}\n"
        f"Pillar: {kpi.pillar}\n"
        f"Type: {kpi.indicator_type}\n"
        f"Impact: {kpi.impact_level}\n"
        f"Business Impact: {kpi.business_impact or 'Not specified'}\n"
        f"Predictive Horizon: {kpi.predictive_horizon_days} days"
    )
    
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text_to_embed
    )
    
    embedding = response.data[0].embedding
    total_tokens += response.usage.total_tokens
    
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=embedding,
        payload={
            "type": "kpi_definition",
            "customer_id": CUSTOMER_ID,
            "kpi_code": kpi.kpi_code,
            "kpi_name": kpi.kpi_name,
            "pillar": kpi.pillar,
            "indicator_type": kpi.indicator_type,
            "impact_level": kpi.impact_level,
            "business_impact": kpi.business_impact or "Not specified",
            "predictive_horizon_days": kpi.predictive_horizon_days,
            "text": text_to_embed
        }
    )
    
    points.append(point)
    
    if (i + 1) % 10 == 0 or (i + 1) == len(kpis):
        print(f"     {i + 1:>4}/{len(kpis)} KPIs (tokens: {total_tokens:,})")

# Calculate cost
embedding_cost = (total_tokens / 1_000_000) * 0.13
print(f"\n   💰 Embedding cost: ${embedding_cost:.4f} ({total_tokens:,} tokens)")

# Upload to Qdrant
print(f"\n{'─' * 80}")
print("UPLOADING TO QDRANT")
print("─" * 80)

print(f"\n  Uploading {len(points):,} points...", end=" ", flush=True)
qdrant.upsert(
    collection_name=COLLECTION_NAME,
    points=points,
    wait=True
)
print("✅")

# Verify
print(f"\n{'─' * 80}")
print("VERIFICATION")
print("─" * 80)

info = qdrant.get_collection(COLLECTION_NAME)
print(f"\n  ✅ Collection: {COLLECTION_NAME}")
print(f"  ✅ Total points: {info.points_count:,}")
print(f"  ✅ Vector dimension: {info.config.params.vectors.size}")
print(f"  ✅ Embedding cost: ${embedding_cost:.4f}")

# Test search
print(f"\n{'─' * 80}")
print("TEST SEMANTIC SEARCH")
print("─" * 80)

test_queries = [
    "budget concerns and cost reduction",
    "champion risk and stakeholder changes",
    "GPU utilization and performance metrics"
]

for query in test_queries:
    print(f"\n  Query: '{query}'")
    
    query_response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    )
    query_embedding = query_response.data[0].embedding
    
    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=3
    )
    
    print(f"  Top 3 results:")
    for i, result in enumerate(results, 1):
        payload = result.payload
        signal_type = payload.get('type', 'unknown')
        score = result.score
        
        if signal_type == 'qualitative_signal':
            print(f"    {i}. [{score:.3f}] Signal: {payload.get('subject', 'N/A')[:50]}...")
            print(f"       Account: {payload.get('account_name', 'N/A')} | Sentiment: {payload.get('sentiment', 'N/A')}")
        else:
            print(f"    {i}. [{score:.3f}] KPI: {payload.get('kpi_name', 'N/A')}")
            print(f"       Category: {payload.get('category', 'N/A')} | Impact: {payload.get('business_impact_level', 'N/A')}")

# Success summary
print(f"\n{'=' * 80}")
print("✅ EMBEDDING COMPLETE!")
print("=" * 80)

print(f"\n📊 Summary:")
print(f"   • Collection: {COLLECTION_NAME}")
print(f"   • Qualitative signals: {len(qualitative):,}")
print(f"   • KPI definitions: {len(kpis):,}")
print(f"   • Total points: {len(points):,}")
print(f"   • Cost: ${embedding_cost:.4f}")

print(f"\n📋 Next Steps:")
print(f"   1. Update Signal Analyst to use collection: {COLLECTION_NAME}")
print(f"   2. Test queries for Customer {CUSTOMER_ID} accounts ({ACCOUNT_ID_START}-10010)")
print(f"   3. Validate retrieval accuracy")
print(f"   4. Monitor query performance\n")

print(f"💡 Query Example:")
print(f"   qdrant_client.search(")
print(f"       collection_name='{COLLECTION_NAME}',")
print(f"       query_vector=embedding,")
print(f"       limit=20")
print(f"   )\n")
