#!/usr/bin/env python3
"""
Embed Qualitative Signals Using OpenAI and Upload to Qdrant
Integrated version matching codebase patterns

Usage:
    python embed_signals_qdrant.py --customer-id 1
    python embed_signals_qdrant.py --customer-id 1 --recreate
    python embed_signals_qdrant.py --customer-id 1 --batch-size 50
"""

import os
import sys
import argparse
import uuid
from typing import List, Optional
from dotenv import load_dotenv
from flask import Flask
from extensions import db
from models import Customer, Account
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI
from sqlalchemy import text

# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path=env_path)

# Configuration
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072  # text-embedding-3-large dimension
COLLECTION_NAME_BASE = "kpi_dashboard_signals"  # Collection base name (matches KPI collection pattern)


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client - ONLY supports Qdrant Cloud (via URL)"""
    qdrant_url = os.getenv('QDRANT_URL')
    qdrant_api_key = os.getenv('QDRANT_API_KEY')
    
    if not qdrant_url:
        raise ValueError("QDRANT_URL environment variable is required. Please configure Qdrant Cloud URL.")
    
    if not qdrant_api_key:
        raise ValueError("QDRANT_API_KEY is required when using QDRANT_URL (Qdrant Cloud)")
    
    return QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=30)


def get_openai_client(customer_id: Optional[int] = None) -> OpenAI:
    """Get OpenAI client with customer-specific or global API key"""
    # Try customer-specific key first
    if customer_id:
        try:
            from openai_key_utils import get_openai_api_key
            api_key = get_openai_api_key(customer_id)
            if api_key:
                return OpenAI(api_key=api_key)
        except Exception as e:
            print(f"⚠️  Could not get customer-specific OpenAI key: {e}")
    
    # Fallback to environment variable
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable or configure customer-specific key.")
    
    return OpenAI(api_key=api_key)


def ensure_collection_exists(qdrant_client: QdrantClient, collection_name: str, recreate: bool = False):
    """Ensure Qdrant collection exists, optionally recreate it"""
    collections = qdrant_client.get_collections().collections
    existing_names = [c.name for c in collections]
    
    if collection_name in existing_names:
        if recreate:
            print(f"🗑️  Deleting existing collection: {collection_name}")
            qdrant_client.delete_collection(collection_name)
            print(f"✅ Deleted collection")
            # Wait a moment for deletion to complete
            import time
            time.sleep(0.5)
            # Create new collection after deletion
            print(f"🔧 Creating collection: {collection_name}")
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )
            print(f"✅ Created collection: {collection_name}")
        else:
            print(f"✅ Using existing collection: {collection_name}")
    else:
        # Collection doesn't exist, create it
        print(f"🔧 Creating collection: {collection_name}")
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"✅ Created collection: {collection_name}")


def fetch_signals_from_db(customer_id: int, since_date: Optional[str] = None) -> List:
    """Fetch qualitative signals from PostgreSQL database"""
    query = """
        SELECT 
            signal_id,
            account_id,
            date,
            signal_type,
            from_contact,
            to_contact,
            subject,
            summary,
            sentiment,
            priority,
            keywords,
            source_system,
            created_at
        FROM qualitative_signals
        WHERE account_id IN (
            SELECT account_id 
            FROM accounts 
            WHERE customer_id = :customer_id
        )
    """
    
    params = {"customer_id": customer_id}
    
    if since_date:
        query += " AND created_at >= :since_date"
        params["since_date"] = since_date
    
    query += " ORDER BY account_id, date DESC"
    
    result = db.session.execute(text(query), params)
    signals = result.fetchall()
    return signals


def get_active_customers() -> List[int]:
    """Get list of active customer IDs (customers with active accounts)"""
    # Get customers that have at least one active account
    # Account model uses 'account_status' not 'is_active'
    query = text("""
        SELECT DISTINCT customer_id 
        FROM accounts 
        WHERE account_status = 'active' OR account_status IS NULL
        ORDER BY customer_id
    """)
    result = db.session.execute(query)
    return [row.customer_id for row in result.fetchall()]


def get_last_embed_timestamp(qdrant_client: QdrantClient, collection_name: str) -> Optional[str]:
    """Get the timestamp of the last embedded signal from collection metadata"""
    # For now, return None (will embed all signals)
    # In future, can store last_embed_timestamp in collection metadata or separate tracking table
    return None


def create_signal_text(signal) -> str:
    """Create text representation of signal for embedding"""
    parts = [
        f"Type: {signal.signal_type or 'N/A'}",
        f"Subject: {signal.subject or 'N/A'}",
        f"Summary: {signal.summary or 'N/A'}",
        f"Sentiment: {signal.sentiment or 'N/A'}",
        f"Priority: {signal.priority or 'N/A'}",
    ]
    
    if signal.from_contact:
        parts.append(f"From: {signal.from_contact}")
    if signal.to_contact:
        parts.append(f"To: {signal.to_contact}")
    
    return "\n".join(parts)


def embed_and_upload_signals(
    customer_id: int,
    mode: str = "incremental",
    since_date: Optional[str] = None,
    dry_run: bool = False,
    batch_size: int = 50
):
    """Main function to embed signals and upload to Qdrant"""
    
    # Initialize Flask app context
    app = Flask(__name__)
    database_url = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        # Verify customer exists
        customer = Customer.query.get(customer_id)
        if not customer:
            raise ValueError(f"Customer ID {customer_id} not found!")
        
        print("=" * 70)
        print("EMBED & UPLOAD SIGNALS TO QDRANT")
        print("=" * 70)
        print(f"Customer: {customer.customer_name} (ID: {customer_id})")
        print(f"Model: {EMBEDDING_MODEL}")
        print(f"Dimensions: {EMBEDDING_DIM}")
        print("=" * 70)
        
        # Initialize clients
        print("\n1. Connecting to Qdrant...")
        qdrant_client = get_qdrant_client()
        print("✅ Connected to Qdrant")
        
        print("\n2. Initializing OpenAI client...")
        openai_client = get_openai_client(customer_id)
        print("✅ OpenAI client initialized")
        
        # Collection name
        collection_name = f"{COLLECTION_NAME_BASE}_customer_{customer_id}"
        
        # Handle mode: full vs incremental
        if mode == "full":
            print(f"\n3. Full rebuild mode - recreating collection: {collection_name}")
            ensure_collection_exists(qdrant_client, collection_name, recreate=True)
            
            # Fetch all signals
            print("\n4. Fetching all signals from database...")
            signals = fetch_signals_from_db(customer_id)
            print(f"✅ Found {len(signals)} signals to embed")
            
        else:  # incremental
            print(f"\n3. Incremental mode - updating collection: {collection_name}")
            
            # Ensure collection exists (don't recreate)
            ensure_collection_exists(qdrant_client, collection_name, recreate=False)
            
            # Get since_date (from argument or last embed timestamp)
            if not since_date:
                since_date = get_last_embed_timestamp(qdrant_client, collection_name)
                if since_date:
                    print(f"   Using last embed timestamp: {since_date}")
                else:
                    print(f"   No last embed timestamp found - will embed all signals")
            
            # Fetch signals since date
            print("\n4. Fetching new/modified signals from database...")
            if since_date:
                print(f"   Filtering signals since: {since_date}")
            signals = fetch_signals_from_db(customer_id, since_date=since_date)
            print(f"✅ Found {len(signals)} signals to embed")
        
        if dry_run:
            print("\n[DRY RUN] Would embed these signals:")
            for i, sig in enumerate(signals[:10], 1):
                print(f"   {i}. Signal ID: {sig.signal_id}, Subject: {sig.subject or 'N/A'}, Date: {sig.date}")
            if len(signals) > 10:
                print(f"   ... and {len(signals) - 10} more signals")
            print("\n✅ Dry run complete - no data was embedded")
            return
        
        if not signals:
            print("⚠️  No signals found. Exiting.")
            return
        
        # Generate embeddings and create points
        print("\n5. Generating embeddings...")
        points = []
        total_tokens = 0
        
        for i, signal in enumerate(signals):
            try:
                # Create text for embedding
                text_to_embed = create_signal_text(signal)
                
                # Generate embedding
                response = openai_client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=text_to_embed
                )
                
                embedding = response.data[0].embedding
                total_tokens += response.usage.total_tokens
                
                # Create point
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "type": "qualitative_signal",
                        "customer_id": customer_id,
                        "signal_id": signal.signal_id,
                        "account_id": signal.account_id,
                        "date": str(signal.date) if signal.date else None,
                        "signal_type": signal.signal_type,
                        "from_contact": signal.from_contact,
                        "to_contact": signal.to_contact,
                        "subject": signal.subject,
                        "summary": signal.summary,
                        "sentiment": signal.sentiment,
                        "priority": signal.priority,
                        "keywords": signal.keywords if signal.keywords else [],
                        "source_system": signal.source_system if signal.source_system else "unknown",
                        "text": text_to_embed
                    }
                )
                
                points.append(point)
                
                # Progress update
                if (i + 1) % batch_size == 0 or (i + 1) == len(signals):
                    print(f"   Embedded {i + 1}/{len(signals)} signals... (tokens: {total_tokens:,})")
            
            except Exception as e:
                print(f"⚠️  Error embedding signal {signal.signal_id}: {e}")
                continue
        
        # Calculate cost
        embedding_cost = (total_tokens / 1_000_000) * 0.13  # $0.13 per 1M tokens
        print(f"\n   Total tokens: {total_tokens:,}")
        print(f"   Estimated cost: ${embedding_cost:.4f}")
        
        # Upload to Qdrant
        print(f"\n6. Uploading {len(points)} points to Qdrant...")
        if points:
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )
            print(f"✅ Uploaded {len(points)} points")
        else:
            print("⚠️  No points to upload")
        
        # Verification
        print("\n7. Verification...")
        collection_info = qdrant_client.get_collection(collection_name)
        print(f"   Collection: {collection_name}")
        print(f"   Total points: {collection_info.points_count:,}")
        if hasattr(collection_info.config.params, 'vectors'):
            vec_config = collection_info.config.params.vectors
            print(f"   Vector dimension: {vec_config.size if hasattr(vec_config, 'size') else 'N/A'}")
            print(f"   Distance metric: {vec_config.distance if hasattr(vec_config, 'distance') else 'N/A'}")
        print(f"   Estimated cost: ${embedding_cost:.4f}")
        
        # Test search
        print("\n8. Testing semantic search...")
        test_query = "budget concerns and cost reduction"
        print(f"   Query: '{test_query}'")
        
        try:
            query_response = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=test_query
            )
            query_embedding = query_response.data[0].embedding
            
            results = qdrant_client.query_points(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=3
            ).points
            
            print(f"   Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                payload = result.payload
                score = result.score if hasattr(result, 'score') else getattr(result, 'distance', 0)
                print(f"   {i}. Score: {score:.3f}")
                print(f"      Account ID: {payload.get('account_id')}")
                print(f"      Subject: {payload.get('subject', 'N/A')}")
                print(f"      Sentiment: {payload.get('sentiment', 'N/A')}")
        except Exception as e:
            print(f"   ⚠️  Test search failed: {e}")
        
        print("\n" + "=" * 70)
        print("✅ UPLOAD COMPLETE!")
        print("=" * 70)
        print(f"\nCollection: {collection_name}")
        print(f"Model: {EMBEDDING_MODEL}")
        print(f"Dimensions: {EMBEDDING_DIM}")
        print(f"Points: {collection_info.points_count:,}")
        print("\n✅ Signals are now searchable with semantic understanding!")


def process_customers(
    customer_ids: Optional[List[int]],
    mode: str = "incremental",
    since_date: Optional[str] = None,
    dry_run: bool = False,
    batch_size: int = 50
):
    """Process signals for one or more customers"""
    # Initialize Flask app context
    app = Flask(__name__)
    database_url = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        # Get customer list
        if customer_ids:
            customers = customer_ids
        else:
            customers = get_active_customers()
            print(f"\n📋 Found {len(customers)} active customer(s) to process")
        
        if not customers:
            print("⚠️  No customers found to process")
            return
        
        # Process each customer
        for customer_id in customers:
            try:
                embed_and_upload_signals(
                    customer_id=customer_id,
                    mode=mode,
                    since_date=since_date,
                    dry_run=dry_run,
                    batch_size=batch_size
                )
            except Exception as e:
                print(f"\n❌ Error processing customer {customer_id}: {e}")
                import traceback
                traceback.print_exc()
                if len(customers) > 1:
                    print(f"\nContinuing with next customer...")
                    continue
                else:
                    raise


def main():
    """Main entry point with command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Embed qualitative signals into Qdrant using OpenAI embeddings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initial load for customer 1 (full rebuild)
  python embed_signals_qdrant.py --customer-id 1 --mode full
  
  # Incremental update for customer 1 (default)
  python embed_signals_qdrant.py --customer-id 1
  
  # Incremental update for all customers
  python embed_signals_qdrant.py
  
  # Embed signals since specific date
  python embed_signals_qdrant.py --customer-id 1 --since "2025-01-01"
  
  # Dry run (test what would be embedded)
  python embed_signals_qdrant.py --customer-id 1 --dry-run
  
  # Custom batch size for progress updates
  python embed_signals_qdrant.py --customer-id 1 --batch-size 25
        """
    )
    
    parser.add_argument(
        '--customer-id',
        type=int,
        default=None,
        help='Customer ID to process (default: all active customers)'
    )
    
    parser.add_argument(
        '--mode',
        choices=['full', 'incremental'],
        default='incremental',
        help='Full rebuild (delete & recreate) or incremental update (default: incremental)'
    )
    
    parser.add_argument(
        '--since',
        type=str,
        default=None,
        help='Embed signals since date (YYYY-MM-DD). Used only in incremental mode.'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be embedded without actually doing it'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Batch size for progress updates (default: 50)'
    )
    
    args = parser.parse_args()
    
    try:
        customer_ids = [args.customer_id] if args.customer_id else None
        
        process_customers(
            customer_ids=customer_ids,
            mode=args.mode,
            since_date=args.since,
            dry_run=args.dry_run,
            batch_size=args.batch_size
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


