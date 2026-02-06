#!/usr/bin/env python3
"""
Journey Data → Qdrant Training Collection Loader
===============================================

Loads Phase 1-4 journey data into separate Qdrant collection for Signal Analyst testing.

Collection: journey_training_vectors_customer_102
- Isolated from production (kpi_dashboard_vectors_customer_102)
- Contains: 3 accounts (112000, {ACCOUNT_ID_START+2}, 10007)
- Data: Synthetic journey patterns with known outcomes

Usage:
    python load_journey_to_qdrant_phase4.py \
        --qdrant-url https://your-cluster.qdrant.io \
        --qdrant-api-key YOUR_API_KEY \
        --openai-api-key YOUR_OPENAI_KEY \
        --data-dir /path/to/journey/files
"""

import json
import csv
import argparse
from datetime import datetime
from typing import List, Dict, Any
import sys

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from openai import OpenAI
except ImportError:
    print("ERROR: Missing dependencies. Install with:")
    print("  pip install qdrant-client openai")
    sys.exit(1)


# ============================================================================
# CONFIGURATION
# ============================================================================

TRAINING_COLLECTION = "journey_training_vectors_customer_102"
CUSTOMER_ID = 102
VECTOR_SIZE = 1536  # OpenAI text-embedding-3-small
JOURNEY_ACCOUNTS = [10007, {ACCOUNT_ID_START+2}, 112000]


# ============================================================================
# QDRANT COLLECTION SETUP
# ============================================================================

def create_training_collection(client: QdrantClient, force_recreate: bool = False):
    """
    Create separate training collection for journey data
    
    Args:
        client: Qdrant client
        force_recreate: If True, delete existing collection first
    """
    
    print("="*70)
    print("QDRANT TRAINING COLLECTION SETUP")
    print("="*70)
    print()
    
    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if TRAINING_COLLECTION in collection_names:
        if force_recreate:
            print(f"⚠️  Deleting existing collection: {TRAINING_COLLECTION}")
            client.delete_collection(TRAINING_COLLECTION)
            print(f"   ✅ Deleted")
        else:
            print(f"✅ Collection already exists: {TRAINING_COLLECTION}")
            return
    
    # Create collection
    print(f"📦 Creating collection: {TRAINING_COLLECTION}")
    print(f"   Vector size: {VECTOR_SIZE}")
    print(f"   Distance: Cosine")
    
    client.create_collection(
        collection_name=TRAINING_COLLECTION,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )
    
    print(f"   ✅ Collection created!")
    print()


# ============================================================================
# EMBEDDING GENERATION
# ============================================================================

def get_embedding(text: str, openai_client: OpenAI) -> List[float]:
    """
    Generate embedding for text using OpenAI
    
    Args:
        text: Text to embed
        openai_client: OpenAI client
        
    Returns:
        Embedding vector (1536 dimensions)
    """
    
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    
    return response.data[0].embedding


# ============================================================================
# LOAD JOURNEY EVENTS
# ============================================================================

def load_journey_events(
    client: QdrantClient,
    openai_client: OpenAI,
    data_dir: str
):
    """
    Load journey events into Qdrant training collection
    
    Args:
        client: Qdrant client
        openai_client: OpenAI client
        data_dir: Directory containing journey JSON files
    """
    
    print("="*70)
    print("LOADING JOURNEY EVENTS TO QDRANT")
    print("="*70)
    print()
    
    total_events = 0
    
    for account_id in JOURNEY_ACCOUNTS:
        print(f"📍 Processing Account {account_id}...")
        
        # Load journey data
        journey_file = f"{data_dir}/account_{account_id}_journey.json"
        try:
            with open(journey_file, 'r') as f:
                journey_data = json.load(f)
        except FileNotFoundError:
            print(f"   ❌ File not found: {journey_file}")
            continue
        
        events = journey_data['events']
        pattern_type = journey_data['pattern_type']
        
        print(f"   Pattern: {pattern_type}")
        print(f"   Events: {len(events)}")
        
        # Process each event
        points = []
        for idx, event in enumerate(events):
            # Create text for embedding
            event_text = f"""
            Account {account_id} - {pattern_type}
            Week {event['week_number']} - Phase: {event['phase']}
            Event: {event['event_type']}
            Description: {event['description']}
            Sentiment: {event['sentiment_value']}
            Health Impact: {event.get('health_impact', 0)}
            CSM Action: {event.get('csm_action_type', 'none')}
            """.strip()
            
            # Generate embedding
            embedding = get_embedding(event_text, openai_client)
            
            # Create point
            point = PointStruct(
                id=f"evt_{account_id}_{event['week_number']}_{idx}",
                vector=embedding,
                payload={
                    # Metadata
                    "customer_id": CUSTOMER_ID,
                    "account_id": account_id,
                    "is_training_data": True,
                    "data_source": "journey_pattern_generator",
                    "pattern_type": pattern_type,
                    
                    # Event details
                    "week_number": event['week_number'],
                    "event_date": event['date'],
                    "event_type": event['event_type'],
                    "description": event['description'],
                    "phase": event['phase'],
                    
                    # Signal attributes
                    "sentiment_level": event['sentiment_level'],
                    "sentiment_value": event['sentiment_value'],
                    "health_score_before": event.get('health_score_before', 0),
                    "health_score_after": event.get('health_score_after', 0),
                    "health_impact": event.get('health_impact', 0),
                    
                    # CSM actions
                    "csm_action_type": event.get('csm_action_type'),
                    "csm_response_time_hours": event.get('csm_response_time_hours'),
                    "csm_action_cost": event.get('csm_action_cost', 0),
                    "csm_action_description": event.get('csm_action_description', '')
                }
            )
            
            points.append(point)
        
        # Upload to Qdrant
        client.upsert(
            collection_name=TRAINING_COLLECTION,
            points=points
        )
        
        total_events += len(events)
        print(f"   ✅ Uploaded {len(events)} events")
        print()
    
    print(f"✅ Total events loaded: {total_events}")
    print()


# ============================================================================
# LOAD JOURNEY KPIs
# ============================================================================

def load_journey_kpis(
    client: QdrantClient,
    openai_client: OpenAI,
    data_dir: str
):
    """
    Load journey KPIs into Qdrant training collection
    
    Args:
        client: Qdrant client
        openai_client: OpenAI client
        data_dir: Directory containing KPI CSV files
    """
    
    print("="*70)
    print("LOADING JOURNEY KPIs TO QDRANT")
    print("="*70)
    print()
    
    total_kpis = 0
    
    for account_id in JOURNEY_ACCOUNTS:
        print(f"📍 Processing Account {account_id} KPIs...")
        
        # Load KPI data
        kpi_file = f"{data_dir}/account_{account_id}_kpis.csv"
        try:
            with open(kpi_file, 'r') as f:
                reader = csv.DictReader(f)
                kpis = list(reader)
        except FileNotFoundError:
            print(f"   ❌ File not found: {kpi_file}")
            continue
        
        print(f"   KPI measurements: {len(kpis)}")
        
        # Process each KPI
        points = []
        for idx, kpi in enumerate(kpis):
            # Create text for embedding
            kpi_text = f"""
            Account {account_id}
            Week {kpi['week_number']} - Phase: {kpi['phase']}
            KPI: {kpi['kpi_name']} ({kpi['kpi_code']})
            Category: {kpi['category']}
            Value: {kpi['value']} {kpi['unit']}
            Status: {kpi['status']}
            Health Score: {kpi['health_score']}
            """.strip()
            
            # Generate embedding
            embedding = get_embedding(kpi_text, openai_client)
            
            # Create point
            point = PointStruct(
                id=f"kpi_{account_id}_{kpi['week_number']}_{kpi['kpi_code']}",
                vector=embedding,
                payload={
                    # Metadata
                    "customer_id": CUSTOMER_ID,
                    "account_id": account_id,
                    "is_training_data": True,
                    "data_source": "journey_pattern_generator",
                    "data_type": "kpi",
                    
                    # KPI details
                    "week_number": int(kpi['week_number']),
                    "measurement_date": kpi['date'],
                    "kpi_code": kpi['kpi_code'],
                    "kpi_name": kpi['kpi_name'],
                    "category": kpi['category'],
                    "phase": kpi['phase'],
                    
                    # Values
                    "value": float(kpi['value']),
                    "unit": kpi['unit'],
                    "status": kpi['status'],
                    "health_score": float(kpi['health_score']),
                    
                    # Ranges
                    "good_range_min": float(kpi['good_range_min']) if kpi['good_range_min'] else None,
                    "good_range_max": float(kpi['good_range_max']) if kpi['good_range_max'] else None,
                    "bad_range_min": float(kpi['bad_range_min']) if kpi['bad_range_min'] else None,
                    "bad_range_max": float(kpi['bad_range_max']) if kpi['bad_range_max'] else None
                }
            )
            
            points.append(point)
            
            # Upload in batches of 100
            if len(points) >= 100:
                client.upsert(
                    collection_name=TRAINING_COLLECTION,
                    points=points
                )
                total_kpis += len(points)
                points = []
        
        # Upload remaining points
        if points:
            client.upsert(
                collection_name=TRAINING_COLLECTION,
                points=points
            )
            total_kpis += len(points)
        
        print(f"   ✅ Uploaded {len(kpis)} KPI measurements")
        print()
    
    print(f"✅ Total KPIs loaded: {total_kpis}")
    print()


# ============================================================================
# VERIFY COLLECTION
# ============================================================================

def verify_collection(client: QdrantClient):
    """
    Verify training collection was loaded correctly
    
    Args:
        client: Qdrant client
    """
    
    print("="*70)
    print("VERIFYING TRAINING COLLECTION")
    print("="*70)
    print()
    
    # Get collection info
    info = client.get_collection(TRAINING_COLLECTION)
    
    print(f"Collection: {TRAINING_COLLECTION}")
    print(f"Total points: {info.points_count}")
    print(f"Vector size: {info.config.params.vectors.size}")
    print()
    
    # Sample search for each account
    for account_id in JOURNEY_ACCOUNTS:
        results = client.scroll(
            collection_name=TRAINING_COLLECTION,
            scroll_filter={
                "must": [
                    {"key": "account_id", "match": {"value": account_id}}
                ]
            },
            limit=10
        )
        
        print(f"Account {account_id}: {len(results[0])} points (showing 10)")
        
        for point in results[0][:3]:
            payload = point.payload
            if payload.get('data_type') == 'kpi':
                print(f"  - KPI: {payload['kpi_code']} = {payload['value']} (Week {payload['week_number']})")
            else:
                print(f"  - Event: {payload['event_type']} (Week {payload['week_number']})")
        print()
    
    print("✅ Collection verified!")
    print()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main execution"""
    
    parser = argparse.ArgumentParser(description='Load journey data to Qdrant training collection')
    parser.add_argument('--qdrant-url', required=True, help='Qdrant cluster URL')
    parser.add_argument('--qdrant-api-key', required=True, help='Qdrant API key')
    parser.add_argument('--openai-api-key', required=True, help='OpenAI API key')
    parser.add_argument('--data-dir', required=True, help='Directory with journey files')
    parser.add_argument('--force-recreate', action='store_true', help='Recreate collection if exists')
    
    args = parser.parse_args()
    
    print()
    print("="*70)
    print("JOURNEY DATA → QDRANT TRAINING COLLECTION")
    print("="*70)
    print()
    print(f"Qdrant URL: {args.qdrant_url}")
    print(f"Collection: {TRAINING_COLLECTION}")
    print(f"Accounts: {JOURNEY_ACCOUNTS}")
    print(f"Data dir: {args.data_dir}")
    print()
    
    # Initialize clients
    print("🔌 Connecting to Qdrant...")
    qdrant_client = QdrantClient(
        url=args.qdrant_url,
        api_key=args.qdrant_api_key
    )
    print("   ✅ Connected")
    
    print("🔌 Connecting to OpenAI...")
    openai_client = OpenAI(api_key=args.openai_api_key)
    print("   ✅ Connected")
    print()
    
    try:
        # Step 1: Create collection
        create_training_collection(qdrant_client, args.force_recreate)
        
        # Step 2: Load events
        load_journey_events(qdrant_client, openai_client, args.data_dir)
        
        # Step 3: Load KPIs
        load_journey_kpis(qdrant_client, openai_client, args.data_dir)
        
        # Step 4: Verify
        verify_collection(qdrant_client)
        
        print("="*70)
        print("✅ JOURNEY DATA LOADED TO QDRANT SUCCESSFULLY!")
        print("="*70)
        print()
        print(f"Collection: {TRAINING_COLLECTION}")
        print(f"Ready for Signal Analyst testing!")
        print()
        
    except Exception as e:
        print()
        print("="*70)
        print("❌ ERROR")
        print("="*70)
        print(f"{str(e)}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
