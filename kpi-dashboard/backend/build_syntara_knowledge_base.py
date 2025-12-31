#!/usr/bin/env python3
"""
Build Qdrant knowledge base for Syntara (customer_id=1)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import Customer
from enhanced_rag_qdrant import get_qdrant_rag_system
from dotenv import load_dotenv

# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
# Use PostgreSQL if DATABASE_URL is set, otherwise use SQLite
database_url = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    instance_path = os.path.join(os.path.dirname(basedir), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'kpi_dashboard.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    customer_id = 1  # Syntara
    
    # Verify customer exists
    customer = Customer.query.get(customer_id)
    if not customer:
        print(f"❌ Customer ID {customer_id} not found!")
        sys.exit(1)
    
    print(f"\n✅ Found customer: {customer.customer_name} (ID: {customer.customer_id})")
    print(f"\n🔨 Building Qdrant knowledge base for customer {customer_id}...")
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        rag_system.build_knowledge_base(customer_id)
        
        # Get collection info
        collection_info = rag_system.get_collection_info()
        
        print(f"\n✅ Knowledge base built successfully!")
        print(f"   Customer: {customer.customer_name}")
        print(f"   Collection: {collection_info.get('collection_name', 'N/A')}")
        print(f"   Vectors count: {collection_info.get('vectors_count', 0)}")
        print(f"   Dimension: {collection_info.get('vectors_config', {}).get('params', {}).get('vectors', {}).get('size', 'N/A')}")
        
    except Exception as e:
        print(f"\n❌ Error building knowledge base: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

