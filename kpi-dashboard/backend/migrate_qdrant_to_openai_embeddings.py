#!/usr/bin/env python3
"""
Migration script to update Qdrant collection from SentenceTransformer to OpenAI embeddings
This will delete the old collection (if it exists with wrong dimensions) and rebuild it
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import Customer
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from enhanced_rag_qdrant import EnhancedRAGSystemQdrant
import argparse

# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
# Use PostgreSQL database (required)
database_url = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
if not database_url:
    print("❌ ERROR: DATABASE_URL or SQLALCHEMY_DATABASE_URI environment variable not set!")
    print("   Please set DATABASE_URL to your PostgreSQL connection string")
    print("   Example: postgresql://user:password@localhost:5432/dbname")
    sys.exit(1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
print(f"✅ Using PostgreSQL database: {database_url[:50]}..." if len(database_url) > 50 else f"✅ Using PostgreSQL database")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def delete_collection_if_needed(collection_name: str, required_dimension: int = 3072):
    """Delete collection if it exists with wrong dimensions"""
    try:
        # Initialize Qdrant client
        try:
            qdrant_client = QdrantClient(
                host=os.getenv('QDRANT_HOST', 'localhost'),
                port=int(os.getenv('QDRANT_PORT', 6333))
            )
            qdrant_client.get_collections()
            print("✅ Connected to Qdrant server")
        except Exception as e:
            print(f"⚠️ Qdrant server not available, using local file storage: {e}")
            qdrant_client = QdrantClient(path="./qdrant_storage")
        
        # Check if collection exists
        collections = qdrant_client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if collection_name in collection_names:
            # Get collection info
            collection_info = qdrant_client.get_collection(collection_name)
            current_dim = collection_info.config.params.vectors.size
            points_count = collection_info.points_count
            
            print(f"\n📊 Collection '{collection_name}' found:")
            print(f"   Current dimension: {current_dim}")
            print(f"   Required dimension: {required_dimension}")
            print(f"   Points count: {points_count}")
            
            if current_dim != required_dimension:
                print(f"\n⚠️  Dimension mismatch detected!")
                print(f"   Deleting old collection (will be recreated with correct dimensions)...")
                qdrant_client.delete_collection(collection_name)
                print(f"✅ Collection '{collection_name}' deleted successfully")
                return True
            else:
                print(f"\n✅ Collection already has correct dimension ({current_dim})")
                print(f"   No deletion needed")
                return False
        else:
            print(f"\n✅ Collection '{collection_name}' does not exist yet (will be created)")
            return False
            
    except Exception as e:
        print(f"❌ Error checking/deleting collection: {e}")
        import traceback
        traceback.print_exc()
        return False

def rebuild_knowledge_base(customer_id: int):
    """Rebuild knowledge base for a customer"""
    print(f"\n{'='*70}")
    print(f"Rebuilding Qdrant Knowledge Base for Customer {customer_id}")
    print(f"{'='*70}")
    
    try:
        # Initialize RAG system
        rag_system = EnhancedRAGSystemQdrant()
        
        # Build knowledge base
        print(f"\n🔨 Building knowledge base...")
        rag_system.build_knowledge_base(customer_id)
        
        # Get collection info
        collection_info = rag_system.get_collection_info()
        
        print(f"\n✅ Knowledge base rebuilt successfully!")
        print(f"   Collection: {collection_info.get('collection_name', 'N/A')}")
        print(f"   Dimension: {collection_info.get('dimension', 'N/A')}")
        print(f"   Vectors: {collection_info.get('vectors_count', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error rebuilding knowledge base: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description='Migrate Qdrant collection to OpenAI embeddings')
    parser.add_argument('--customer-id', type=int, help='Customer ID to rebuild for (default: all customers with data)')
    parser.add_argument('--collection', type=str, default='kpi_dashboard_vectors', help='Collection name')
    parser.add_argument('--skip-delete', action='store_true', help='Skip collection deletion (use if dimensions already match)')
    
    args = parser.parse_args()
    
    collection_name = os.getenv('QDRANT_COLLECTION', args.collection)
    
    print("="*70)
    print("QDRANT TO OPENAI EMBEDDINGS MIGRATION")
    print("="*70)
    print(f"Collection: {collection_name}")
    print(f"Target dimension: 3072 (text-embedding-3-large)")
    print(f"Embedding model: text-embedding-3-large")
    
    with app.app_context():
        # Step 1: Delete collection if needed
        if not args.skip_delete:
            print(f"\n[Step 1/3] Checking existing collection...")
            deleted = delete_collection_if_needed(collection_name, required_dimension=3072)
        else:
            print(f"\n[Step 1/3] Skipping collection deletion (--skip-delete flag)")
            deleted = False
        
        # Step 2: Get customer IDs to rebuild
        if args.customer_id:
            customer_ids = [args.customer_id]
            customer = Customer.query.get(args.customer_id)
            if not customer:
                print(f"\n❌ Customer {args.customer_id} not found!")
                return 1
            print(f"\n[Step 2/3] Rebuilding for customer {args.customer_id}: {customer.customer_name}")
        else:
            # Get all customers
            customers = Customer.query.all()
            customer_ids = [c.customer_id for c in customers]
            print(f"\n[Step 2/3] Found {len(customer_ids)} customer(s) to rebuild")
        
        # Step 3: Rebuild knowledge bases
        print(f"\n[Step 3/3] Rebuilding knowledge bases...")
        success_count = 0
        failed_count = 0
        
        for customer_id in customer_ids:
            customer = Customer.query.get(customer_id)
            customer_name = customer.customer_name if customer else f"ID {customer_id}"
            
            print(f"\n{'─'*70}")
            print(f"Customer {customer_id}: {customer_name}")
            print(f"{'─'*70}")
            
            if rebuild_knowledge_base(customer_id):
                success_count += 1
            else:
                failed_count += 1
        
        # Summary
        print(f"\n{'='*70}")
        print("MIGRATION SUMMARY")
        print(f"{'='*70}")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"📊 Total: {len(customer_ids)}")
        
        if failed_count > 0:
            return 1
        else:
            return 0

if __name__ == '__main__':
    sys.exit(main())

