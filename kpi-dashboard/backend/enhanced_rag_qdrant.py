#!/usr/bin/env python3
"""
Enhanced RAG System with Qdrant Vector Database and OpenAI GPT-4
Provides advanced KPI and account analysis capabilities with production-grade vector search
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import openai
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from models import db, KPI, Account, KPIUpload, CustomerConfig, KPITimeSeries, DC2SKPI, User, Product

# Import product analytics models (with fallback if not available)
try:
    from product_analytics_models import ProductCatalog, ProductTrend, ProductAggregateTrend
    PRODUCT_ANALYTICS_AVAILABLE = True
except ImportError:
    PRODUCT_ANALYTICS_AVAILABLE = False
    print("⚠️  Product analytics models not available - product analytics features will be disabled")

# Load environment variables
load_dotenv()

class EnhancedRAGSystemQdrant:
    def __init__(self):
        """Initialize the enhanced RAG system with Qdrant and OpenAI"""
        # Initialize OpenAI client - will be set at query time
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Use OpenAI's text-embedding-3-large model
        self.embedding_model = 'text-embedding-3-large'
        self.embedding_dimension = 3072  # text-embedding-3-large dimension
        
        # Initialize Qdrant client - ONLY support Qdrant Cloud (via URL)
        self.using_local_storage = False
        self.qdrant_bypassed = False
        
        # Qdrant Cloud connection (REQUIRED - no local server support)
        qdrant_url = os.getenv('QDRANT_URL')
        qdrant_api_key = os.getenv('QDRANT_API_KEY')  # Required for Qdrant Cloud
        
        # Qdrant Cloud connection (REQUIRED - no fallback if credentials are provided)
        if not qdrant_url:
            print("⚠️  QDRANT_URL not set - Qdrant features will be disabled")
            print("   Set QDRANT_URL and QDRANT_API_KEY to use Qdrant Cloud")
            self.qdrant_bypassed = True
            self.qdrant_client = None
            print("⚠️  Qdrant bypassed - Qdrant Cloud credentials not provided")
        elif not qdrant_api_key:
            print("❌ QDRANT_API_KEY is required when using QDRANT_URL (Qdrant Cloud)")
            print("   Please set QDRANT_API_KEY environment variable")
            self.qdrant_bypassed = True
            self.qdrant_client = None
            print("⚠️  Qdrant bypassed - Qdrant Cloud API key missing")
        else:
            # Qdrant Cloud credentials are available - MUST use Qdrant (no fallback)
            try:
                from qdrant_client import QdrantClient
                self.qdrant_client = QdrantClient(
                    url=qdrant_url,
                    api_key=qdrant_api_key,
                    timeout=30
                )
                # Test connection
                self.qdrant_client.get_collections()
                print(f"✅ Connected to Qdrant Cloud: {qdrant_url}")
                # Qdrant is available - do NOT bypass
                self.qdrant_bypassed = False
            except Exception as e:
                # If credentials are provided but connection fails, raise error (no fallback)
                error_msg = str(e)[:200]
                print(f"❌ Qdrant Cloud connection failed: {error_msg}")
                print("   QDRANT_URL and QDRANT_API_KEY are set, but connection failed")
                print("   Please verify Qdrant Cloud credentials and network connectivity")
                # Do NOT bypass - fail explicitly if credentials are provided
                self.qdrant_bypassed = False  # Keep as False to force Qdrant usage
                self.qdrant_client = None
                # Store error for later reference
                self._connection_error = error_msg
        
        # Configuration
        # Use per-customer collections for tenant isolation (SECURITY)
        # Collection name will be set based on customer_id in build_knowledge_base()
        self.collection_name_base = os.getenv('QDRANT_COLLECTION', 'kpi_dashboard_vectors')
        self.collection_name = None  # Will be set per customer
        self.top_k = int(os.getenv('RAG_TOP_K', 10))
        self.similarity_threshold = float(os.getenv('RAG_SIMILARITY_THRESHOLD', 0.01))
        self.customer_id = None
        self.openai_client = None  # Will be initialized when needed
        self._build_in_progress = {}  # Track builds in progress to prevent loops
    
    def _get_openai_client(self, customer_id: int = None):
        """Get OpenAI client with API key"""
        if self.openai_client is None:
            # Try to get customer-specific API key first
            try:
                from openai_key_utils import get_openai_api_key
                if customer_id:
                    api_key = get_openai_api_key(customer_id)
                    if api_key:
                        self.openai_api_key = api_key
            except Exception as e:
                print(f"⚠️ Could not get customer-specific OpenAI key: {e}")
            
            # Fallback to environment variable
            if not self.openai_api_key:
                self.openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable or configure customer-specific key.")
            
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
        
        return self.openai_client
    
    def _generate_embedding(self, text: str, customer_id: int = None) -> List[float]:
        """Generate embedding using OpenAI's text-embedding-3-large model"""
        client = self._get_openai_client(customer_id)
        
        try:
            response = client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            raise
        
    def _ensure_collection_exists(self):
        """Ensure Qdrant collection exists with proper configuration"""
        # If Qdrant is bypassed, skip collection creation
        if hasattr(self, 'qdrant_bypassed') and self.qdrant_bypassed:
            raise Exception("Qdrant is bypassed")
        
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                print(f"🔧 Creating Qdrant collection: {self.collection_name} with dimension {self.embedding_dimension}")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,  # 3072 for text-embedding-3-large
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ Collection {self.collection_name} created successfully with {self.embedding_dimension} dimensions")
            else:
                # Check if collection has correct dimension
                try:
                    collection_info = self.qdrant_client.get_collection(self.collection_name)
                    current_dim = collection_info.config.params.vectors.size
                    if current_dim != self.embedding_dimension:
                        print(f"⚠️ Collection {self.collection_name} has dimension {current_dim}, but we need {self.embedding_dimension}")
                        print(f"⚠️ Please delete the collection and recreate it, or use a different collection name")
                        raise ValueError(f"Collection dimension mismatch: {current_dim} vs {self.embedding_dimension}")
                    
                    if collection_info.points_count > 0:
                        print(f"✅ Collection {self.collection_name} already exists with {collection_info.points_count} points (dimension: {current_dim})")
                    else:
                        print(f"✅ Collection {self.collection_name} exists but is empty (dimension: {current_dim})")
                except Exception as e:
                    if "dimension mismatch" in str(e):
                        raise
                    print(f"✅ Collection {self.collection_name} already exists")
                
        except Exception as e:
            error_msg = str(e)
            # If Qdrant connection failed, bypass Qdrant (no local file storage fallback)
            if "Connection refused" in error_msg or "not available" in error_msg.lower():
                print(f"⚠️  Qdrant server connection failed, bypassing Qdrant (local file storage disabled)...")
                self.qdrant_bypassed = True
                self.qdrant_client = None
                raise Exception("Qdrant is bypassed - will use FAISS fallback")
            else:
                # Other error, re-raise
                print(f"❌ Error ensuring collection exists: {error_msg}")
                raise
    
    def build_knowledge_base(self, customer_id: int):
        """Build Qdrant vector database from KPI and account data for specific customer"""
        print(f"🔍 Building Qdrant knowledge base for customer {customer_id} using OpenAI text-embedding-3-large...")
        
        # Store customer ID for this instance
        self.customer_id = customer_id
        
        # Set per-customer collection name for tenant isolation (SECURITY)
        self.collection_name = f"{self.collection_name_base}_customer_{customer_id}"
        print(f"🔒 Using per-customer collection: {self.collection_name} (tenant isolation enabled)")
        
        # Ensure collection exists (will create if needed)
        self._ensure_collection_exists()
        
        # Initialize OpenAI client with customer-specific key if available
        self._get_openai_client(customer_id)
        
        # Check if customer uses DC vertical by checking accounts
        dc_accounts = Account.query.filter(
            Account.customer_id == customer_id,
            Account.vertical == 'dc2_s'
        ).first()
        is_dc_customer = dc_accounts is not None
        
        # Fetch KPIs based on vertical
        if is_dc_customer:
            print(f"📊 Building knowledge base for DC vertical customer {customer_id}")
            # For DC customers, use DC2SKPI table
            # Get latest KPIs per account (deduplicate by account_id + kpi_code)
            dc_kpis_raw = DC2SKPI.query.join(Account).filter(
                Account.customer_id == customer_id,
                Account.vertical == 'dc2_s'
            ).order_by(DC2SKPI.measured_at.desc()).all()
            
            # Deduplicate: keep only latest measurement per (account_id, kpi_code)
            seen = {}
            dc_kpis = []
            for dc_kpi in dc_kpis_raw:
                key = (dc_kpi.account_id, dc_kpi.kpi_code)
                if key not in seen:
                    seen[key] = dc_kpi
                    dc_kpis.append(dc_kpi)
            
            # Create account lookup first
            accounts = Account.query.filter(
                Account.customer_id == customer_id,
                Account.vertical == 'dc2_s'
            ).all()
            account_lookup = {acc.account_id: acc for acc in accounts}
            
            # Convert DC2SKPI to KPI-like format for processing
            class MockKPI:
                def __init__(self, dc_kpi, account):
                    self.kpi_id = dc_kpi.kpi_id
                    self.account_id = dc_kpi.account_id
                    self.category = dc_kpi.pillar or 'Uncategorized'
                    self.kpi_parameter = dc_kpi.kpi_code or 'Unknown KPI'
                    self.data = str(dc_kpi.value) if dc_kpi.value is not None else '0'
                    self.impact_level = 'Medium'  # Default for DC
                    self.source_review = 'DC Data Source'
                    self.measurement_frequency = 'Monthly'  # Default
                    self.upload_id = None  # DC KPIs don't have upload_id
            
            # Convert DC KPIs
            kpis = []
            for dc_kpi in dc_kpis:
                account = account_lookup.get(dc_kpi.account_id)
                kpis.append(MockKPI(dc_kpi, account))
        else:
            # For SaaS customers, use standard KPI table
            print(f"📊 Building knowledge base for SaaS customer {customer_id}")
            kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).all()
            accounts = Account.query.filter_by(customer_id=customer_id).all()
            account_lookup = {acc.account_id: acc for acc in accounts}
        
        # Fetch time-series data for the customer (SaaS only, DC doesn't use this)
        time_series_data = []
        if not is_dc_customer:
            time_series_data = KPITimeSeries.query.filter_by(customer_id=customer_id).all()
        
        # Fetch products for the customer from multiple sources:
        # 1. Product table (if populated)
        # 2. Account profile_metadata.products_used (comma-separated string) - PRIMARY SOURCE
        # 3. Product-level KPIs (KPIs with product_id set)
        
        products_from_table = Product.query.filter_by(customer_id=customer_id).all()
        
        # Extract products from account profile_metadata.products_used (PRIMARY SOURCE)
        # This matches how Product Health Dashboard gets products
        product_data_from_accounts = []
        for account in accounts:
            profile_metadata = account.profile_metadata or {}
            products_used_str = profile_metadata.get('products_used', '')
            
            if products_used_str and isinstance(products_used_str, str) and products_used_str.strip():
                # Parse comma-separated product names
                product_names = [p.strip() for p in products_used_str.split(',') if p.strip()]
                for product_name in product_names:
                    # Create a product-like dict from account metadata
                    product_data_from_accounts.append({
                        'product_name': product_name,
                        'account_id': account.account_id,
                        'account_name': account.account_name,
                        'customer_id': customer_id,
                        'product_type': None,  # Not available from metadata
                        'product_sku': None,   # Not available from metadata
                        'revenue': float(account.revenue) if account.revenue else 0,
                        'status': 'active',
                        'source': 'profile_metadata'
                    })
        
        # Also add products from Product table if they exist
        for product in products_from_table:
            product_data_from_accounts.append({
                'product_name': product.product_name,
                'account_id': product.account_id,
                'account_name': account_lookup.get(product.account_id, Account()).account_name if account_lookup.get(product.account_id) else 'Unknown',
                'customer_id': customer_id,
                'product_type': product.product_type,
                'product_sku': product.product_sku,
                'revenue': float(product.revenue) if product.revenue else 0,
                'status': product.status,
                'source': 'product_table'
            })
        
        # Deduplicate products (same product name + account_id)
        seen_products = set()
        unique_products = []
        for prod in product_data_from_accounts:
            key = (prod['product_name'].lower(), prod['account_id'])
            if key not in seen_products:
                seen_products.add(key)
                unique_products.append(prod)
        
        print(f"📦 Found {len(unique_products)} unique products from accounts (profile_metadata) and Product table")
        
        # Prepare data for indexing
        kpi_data = []
        account_data = []
        product_data = []
        temporal_data = []
        
        for kpi in kpis:
            account = account_lookup.get(kpi.account_id)
            
            # Create rich text representation
            kpi_text = self._create_kpi_text(kpi, account)
            
            # Generate embedding using OpenAI
            embedding = self._generate_embedding(kpi_text, customer_id)
            
            # Store data
            kpi_record = {
                'kpi_id': kpi.kpi_id,
                'account_id': kpi.account_id,
                'account_name': account.account_name if account else 'Unknown',
                'revenue': float(account.revenue) if account else 0,
                'industry': account.industry if account else 'Unknown',
                'region': account.region if account else 'Unknown',
                'category': kpi.category,
                'kpi_parameter': kpi.kpi_parameter,
                'data': kpi.data,
                'impact_level': kpi.impact_level,
                'source_review': kpi.source_review,
                'measurement_frequency': kpi.measurement_frequency,
                'text': kpi_text,
                'embedding': embedding
            }
            
            kpi_data.append(kpi_record)
            
            # Store account data separately
            if account and account.account_id not in [a['account_id'] for a in account_data]:
                account_text = self._create_account_text(account)
                account_embedding = self._generate_embedding(account_text, customer_id)
                
                account_record = {
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'revenue': float(account.revenue),
                    'industry': account.industry,
                    'region': account.region,
                    'account_status': account.account_status,
                    'text': account_text,
                    'embedding': account_embedding
                }
                account_data.append(account_record)
        
        # Process accounts even if there are no KPIs (to ensure accounts are in knowledge base)
        if len(kpis) == 0 and len(accounts) > 0:
            print(f"📊 No KPIs found, but {len(accounts)} accounts exist. Adding accounts to knowledge base...")
            for account in accounts:
                if account.account_id not in [a['account_id'] for a in account_data]:
                    account_text = self._create_account_text(account)
                    account_embedding = self._generate_embedding(account_text, customer_id)
                    
                    account_record = {
                        'account_id': account.account_id,
                        'account_name': account.account_name,
                        'revenue': float(account.revenue) if account.revenue else 0,
                        'industry': account.industry if account.industry else 'Unknown',
                        'region': account.region if account.region else 'Unknown',
                        'account_status': account.account_status if account.account_status else 'active',
                        'text': account_text,
                        'embedding': account_embedding
                    }
                    account_data.append(account_record)
        
        # Process products from account metadata and Product table
        for prod_dict in unique_products:
            account = account_lookup.get(prod_dict['account_id'])
            
            # Create a mock Product-like object for _create_product_text
            class MockProduct:
                def __init__(self, prod_dict, account):
                    self.product_name = prod_dict['product_name']
                    self.product_sku = prod_dict.get('product_sku')
                    self.product_type = prod_dict.get('product_type')
                    self.revenue = prod_dict.get('revenue', 0)
                    self.status = prod_dict.get('status', 'active')
            
            mock_product = MockProduct(prod_dict, account)
            product_text = self._create_product_text(mock_product, account)
            product_embedding = self._generate_embedding(product_text, customer_id)
            
            product_record = {
                'product_id': None,  # Not available from metadata
                'account_id': prod_dict['account_id'],
                'account_name': prod_dict['account_name'],
                'product_name': prod_dict['product_name'],
                'product_sku': prod_dict.get('product_sku'),
                'product_type': prod_dict.get('product_type'),
                'revenue': prod_dict.get('revenue', 0),
                'status': prod_dict.get('status', 'active'),
                'industry': account.industry if account else 'Unknown',
                'region': account.region if account else 'Unknown',
                'text': product_text,
                'embedding': product_embedding
            }
            product_data.append(product_record)
        
        # Process temporal data for monthly revenue analysis (SaaS only, DC doesn't use this)
        monthly_revenue_data = {}
        if not is_dc_customer and time_series_data:
            monthly_revenue_data = self._aggregate_monthly_revenue(time_series_data, kpis, account_lookup)
        
        for month_year, data in monthly_revenue_data.items():
            month, year = month_year
            temporal_text = self._create_temporal_text(month, year, data)
            embedding = self._generate_embedding(temporal_text, customer_id)
            
            temporal_data.append({
                'text': temporal_text,
                'embedding': embedding,
                'metadata': {
                    'type': 'temporal_revenue',
                    'month': month,
                    'year': year,
                    'month_year': f"{year}-{month:02d}",
                    'total_revenue': data['total_revenue'],
                    'account_count': data['account_count'],
                    'top_accounts': data['top_accounts'],
                    'customer_id': customer_id
                }
            })
        
        # ✅ RECOMMENDATION 1: Add Product Analytics Data to Knowledge Base
        product_analytics_data = []
        if PRODUCT_ANALYTICS_AVAILABLE:
            try:
                # Add Product Catalog entries
                products_catalog = ProductCatalog.query.filter_by(customer_id=customer_id, status='active').all()
                for product_catalog in products_catalog:
                    catalog_text = self._create_product_catalog_text(product_catalog)
                    catalog_embedding = self._generate_embedding(catalog_text, customer_id)
                    
                    product_analytics_data.append({
                        'type': 'product_catalog',
                        'product_id': product_catalog.product_id,
                        'product_name': product_catalog.product_name,
                        'product_sku': product_catalog.product_sku,
                        'product_type': product_catalog.product_type,
                        'status': product_catalog.status,
                        'text': catalog_text,
                        'embedding': catalog_embedding
                    })
                
                # Add Product Health Trends (per-account)
                from datetime import datetime
                now = datetime.now()
                current_month = now.month
                current_year = now.year
                
                product_trends = ProductTrend.query.filter_by(
                    customer_id=customer_id,
                    month=current_month,
                    year=current_year
                ).all()
                
                for trend in product_trends:
                    trend_text = self._create_product_trend_text(trend, account_lookup)
                    trend_embedding = self._generate_embedding(trend_text, customer_id)
                    
                    product_analytics_data.append({
                        'type': 'product_trend',
                        'product_id': trend.product_id,
                        'account_id': trend.account_id,
                        'product_name': product_catalog_lookup.get(trend.product_id, ProductCatalog()).product_name if trend.product_id in product_catalog_lookup else 'Unknown',
                        'account_name': account_lookup.get(trend.account_id, Account()).account_name if trend.account_id in account_lookup else 'Unknown',
                        'overall_health_score': float(trend.overall_health_score) if trend.overall_health_score else None,
                        'product_usage_score': float(trend.product_usage_score) if trend.product_usage_score else None,
                        'support_score': float(trend.support_score) if trend.support_score else None,
                        'month': trend.month,
                        'year': trend.year,
                        'text': trend_text,
                        'embedding': trend_embedding
                    })
                
                # Add Product Aggregate Trends
                product_agg_trends = ProductAggregateTrend.query.filter_by(
                    customer_id=customer_id,
                    month=current_month,
                    year=current_year
                ).all()
                
                for agg_trend in product_agg_trends:
                    agg_text = self._create_product_aggregate_trend_text(agg_trend, product_catalog_lookup)
                    agg_embedding = self._generate_embedding(agg_text, customer_id)
                    
                    product_analytics_data.append({
                        'type': 'product_aggregate_trend',
                        'product_id': agg_trend.product_id,
                        'product_name': product_catalog_lookup.get(agg_trend.product_id, ProductCatalog()).product_name if agg_trend.product_id in product_catalog_lookup else 'Unknown',
                        'overall_health_score': float(agg_trend.overall_health_score) if agg_trend.overall_health_score else None,
                        'total_accounts': agg_trend.total_accounts,
                        'total_revenue': float(agg_trend.total_revenue) if agg_trend.total_revenue else 0,
                        'average_revenue_per_account': float(agg_trend.average_revenue_per_account) if agg_trend.average_revenue_per_account else 0,
                        'month': agg_trend.month,
                        'year': agg_trend.year,
                        'text': agg_text,
                        'embedding': agg_embedding
                    })
                
                print(f"📊 Added {len(product_analytics_data)} product analytics entries to knowledge base")
                print(f"   - {len([d for d in product_analytics_data if d['type'] == 'product_catalog'])} product catalog entries")
                print(f"   - {len([d for d in product_analytics_data if d['type'] == 'product_trend'])} product health trends")
                print(f"   - {len([d for d in product_analytics_data if d['type'] == 'product_aggregate_trend'])} aggregate product trends")
                
            except Exception as e:
                print(f"⚠️  Error loading product analytics data: {e}")
                import traceback
                traceback.print_exc()
        
        # Build Qdrant index (including product analytics data)
        self._build_qdrant_index(kpi_data, account_data, product_data, temporal_data, product_analytics_data)
        
        total_analytics = len(product_analytics_data) if PRODUCT_ANALYTICS_AVAILABLE else 0
        print(f"✅ Qdrant knowledge base built for customer {customer_id} with {len(kpi_data)} KPIs, {len(account_data)} accounts, {len(product_data)} products, {len(temporal_data)} monthly records, and {total_analytics} product analytics entries")
        
    def _create_kpi_text(self, kpi: KPI, account: Optional[Account]) -> str:
        """Create rich text representation of KPI"""
        account_info = f"Account: {account.account_name} (${account.revenue:,.0f})" if account else "Account: Unknown"
        
        return f"""
        KPI: {kpi.kpi_parameter}
        Category: {kpi.category}
        {account_info}
        Industry: {account.industry if account else 'Unknown'}
        Region: {account.region if account else 'Unknown'}
        Value: {kpi.data}
        Impact Level: {kpi.impact_level}
        Source: {kpi.source_review}
        Frequency: {kpi.measurement_frequency}
        """
    
    def _create_account_text(self, account: Account) -> str:
        """Create rich text representation of account"""
        return f"""
        Account: {account.account_name}
        Revenue: ${account.revenue:,.0f}
        Industry: {account.industry}
        Region: {account.region}
        Status: {account.account_status}
        """
    
    def _create_product_text(self, product: Product, account: Optional[Account]) -> str:
        """Create rich text representation of product with enhanced semantic context"""
        account_info = f"Account: {account.account_name}" if account else "Account: Unknown"
        revenue_info = f"Product Revenue: ${product.revenue:,.0f}" if product.revenue else "Product Revenue: Not specified"
        
        # Enhanced text with semantic phrases for better searchability
        # Include phrases that match common product queries like "widely used", "product adoption", etc.
        product_name = product.product_name or "Unknown Product"
        product_type = product.product_type or "Not specified"
        product_sku = product.product_sku or "Not specified"
        
        # Build rich semantic text
        text_parts = [
            f"Product Name: {product_name}",
            f"Product: {product_name}",
            f"Product used by account: {account.account_name if account else 'Unknown'}",
            f"Product deployed at: {account.account_name if account else 'Unknown'}",
            f"Product adopted by: {account.account_name if account else 'Unknown'}",
            f"Product utilized by: {account.account_name if account else 'Unknown'}",
            f"Account using product: {account.account_name if account else 'Unknown'}",
            f"Account with product: {account.account_name if account else 'Unknown'}",
            f"Product SKU: {product_sku}",
            f"Product Type: {product_type}",
            f"Product Category: {product_type}",
            revenue_info,
            f"Product Status: {product.status}",
            f"Product Active: {product.status}",
        ]
        
        if account:
            text_parts.extend([
                f"Industry: {account.industry or 'Unknown'}",
                f"Region: {account.region or 'Unknown'}",
                f"Product in industry: {account.industry or 'Unknown'}",
                f"Product in region: {account.region or 'Unknown'}",
            ])
        
        # Add phrases for "widely used" queries
        text_parts.extend([
            f"This product {product_name} is used by the account",
            f"The product {product_name} is deployed",
            f"Product {product_name} adoption",
            f"Product {product_name} usage",
            f"Product {product_name} utilization",
        ])
        
        return "\n".join(text_parts)
    
    def _create_product_catalog_text(self, product_catalog: ProductCatalog) -> str:
        """Create rich text representation of product catalog entry with semantic variations"""
        product_name = product_catalog.product_name
        product_type = product_catalog.product_type or 'Not specified'
        product_sku = product_catalog.product_sku or 'Not specified'
        
        # Build text with multiple semantic variations for better query matching
        text_parts = [
            f"Product Catalog Entry:",
            f"Product Name: {product_name}",
            f"Product: {product_name}",
            f"Product ID: {product_catalog.product_id}",
            f"Product SKU: {product_sku}",
            f"Product Type: {product_type}",
            f"Status: {product_catalog.status}",
            # Semantic variations for query matching
            f"Product {product_name} is in the catalog",
            f"{product_name} is a product",
            f"{product_name} product information",
            f"Normalized product name: {product_name}",
            f"Product catalog entry for {product_name}",
            f"{product_name} product details",
            f"Product {product_name} metadata",
        ]
        
        return "\n".join(text_parts)
    
    def _create_product_trend_text(self, trend: ProductTrend, account_lookup: Dict) -> str:
        """Create rich text representation of product health trend (per-account) with semantic variations"""
        account = account_lookup.get(trend.account_id)
        account_name = account.account_name if account else 'Unknown'
        
        # Format scores with proper handling of None values
        overall_score = f"{trend.overall_health_score:.1f}" if trend.overall_health_score else "Not available"
        overall_score_num = trend.overall_health_score if trend.overall_health_score else None
        usage_score = f"{trend.product_usage_score:.1f}" if trend.product_usage_score else "Not available"
        support_score = f"{trend.support_score:.1f}" if trend.support_score else "Not available"
        sentiment_score = f"{trend.customer_sentiment_score:.1f}" if trend.customer_sentiment_score else "Not available"
        outcomes_score = f"{trend.business_outcomes_score:.1f}" if trend.business_outcomes_score else "Not available"
        relationship_score = f"{trend.relationship_strength_score:.1f}" if trend.relationship_strength_score else "Not available"
        revenue = f"${trend.revenue:,.0f}" if trend.revenue else "$0"
        
        # Build text with multiple semantic variations for better query matching
        text_parts = [
            f"Product Health Trend:",
            f"Product ID: {trend.product_id}",
            f"Account: {account_name}",
            f"Account ID: {trend.account_id}",
            f"Overall Health Score: {overall_score} out of 100",
            f"Product Health Score: {overall_score}",
            f"Product Usage Score: {usage_score} out of 100",
            f"Support Score: {support_score} out of 100",
            f"Customer Sentiment Score: {sentiment_score} out of 100",
            f"Business Outcomes Score: {outcomes_score} out of 100",
            f"Relationship Strength Score: {relationship_score} out of 100",
            f"Total KPIs: {trend.total_kpis}",
            f"Valid KPIs: {trend.valid_kpis}",
            f"Revenue: {revenue}",
            f"Month: {trend.month}/{trend.year}",
            # Semantic variations for query matching
            f"Product health for {account_name}: {overall_score}",
            f"Product health score for {account_name}: {overall_score}",
            f"Health score for product at {account_name}: {overall_score}",
            f"Product performance for {account_name}: {overall_score}/100",
            f"Product performance score for {account_name}: {overall_score}",
            f"{account_name} product health is {overall_score}",
            f"{account_name} product health score is {overall_score}",
            f"The product health score is {overall_score} for {account_name}",
        ]
        
        # Add low/medium/high health indicators
        if overall_score_num is not None:
            if overall_score_num < 50:
                text_parts.extend([
                    f"Product has low health score: {overall_score}",
                    f"Product health is low: {overall_score}",
                    f"Product needs attention with health score {overall_score}",
                ])
            elif overall_score_num < 75:
                text_parts.extend([
                    f"Product has medium health score: {overall_score}",
                    f"Product health is moderate: {overall_score}",
                ])
            else:
                text_parts.extend([
                    f"Product has high health score: {overall_score}",
                    f"Product health is good: {overall_score}",
                ])
        
        return "\n".join(text_parts)
    
    def _create_product_aggregate_trend_text(self, agg_trend: ProductAggregateTrend, product_catalog_lookup: Dict) -> str:
        """Create rich text representation of aggregate product health trend with semantic variations"""
        product = product_catalog_lookup.get(agg_trend.product_id)
        product_name = product.product_name if product else 'Unknown Product'
        
        # Format scores with proper handling of None values
        overall_score = f"{agg_trend.overall_health_score:.1f}" if agg_trend.overall_health_score else "Not available"
        overall_score_num = agg_trend.overall_health_score if agg_trend.overall_health_score else None
        usage_score = f"{agg_trend.product_usage_score:.1f}" if agg_trend.product_usage_score else "Not available"
        support_score = f"{agg_trend.support_score:.1f}" if agg_trend.support_score else "Not available"
        sentiment_score = f"{agg_trend.customer_sentiment_score:.1f}" if agg_trend.customer_sentiment_score else "Not available"
        outcomes_score = f"{agg_trend.business_outcomes_score:.1f}" if agg_trend.business_outcomes_score else "Not available"
        relationship_score = f"{agg_trend.relationship_strength_score:.1f}" if agg_trend.relationship_strength_score else "Not available"
        total_revenue = f"${agg_trend.total_revenue:,.0f}" if agg_trend.total_revenue else "$0"
        avg_revenue = f"${agg_trend.average_revenue_per_account:,.0f}" if agg_trend.average_revenue_per_account else "$0"
        
        # Build text with multiple semantic variations for better query matching
        text_parts = [
            f"Product Aggregate Health Trend:",
            f"Product: {product_name}",
            f"Product ID: {agg_trend.product_id}",
            f"Overall Health Score: {overall_score} out of 100",
            f"Product Health Score: {overall_score}",
            f"Product Usage Score: {usage_score} out of 100",
            f"Support Score: {support_score} out of 100",
            f"Customer Sentiment Score: {sentiment_score} out of 100",
            f"Business Outcomes Score: {outcomes_score} out of 100",
            f"Relationship Strength Score: {relationship_score} out of 100",
            f"Total Accounts: {agg_trend.total_accounts}",
            f"Total Revenue: {total_revenue}",
            f"Average Revenue per Account: {avg_revenue}",
            f"Total KPIs: {agg_trend.total_kpis}",
            f"Valid KPIs: {agg_trend.valid_kpis}",
            f"Month: {agg_trend.month}/{agg_trend.year}",
            # Semantic variations for query matching
            f"Aggregate product health for {product_name}: {overall_score}",
            f"Product health score for {product_name}: {overall_score}",
            f"Health score for {product_name}: {overall_score}",
            f"The health score for {product_name} is {overall_score}",
            f"{product_name} health score is {overall_score}",
            f"{product_name} has a health score of {overall_score}",
            f"Product performance across all accounts: {overall_score}/100",
            f"Average product health for {product_name}: {overall_score}",
            f"Average health score per product: {overall_score} for {product_name}",
            f"Overall health score per product: {overall_score} for {product_name}",
            f"Product {product_name} average health: {overall_score}",
        ]
        
        # Add low/medium/high health indicators
        if overall_score_num is not None:
            if overall_score_num < 50:
                text_parts.extend([
                    f"{product_name} has low health score: {overall_score}",
                    f"{product_name} health is low: {overall_score}",
                    f"{product_name} needs attention with health score {overall_score}",
                    f"Products with low health scores: {product_name} ({overall_score})",
                ])
            elif overall_score_num < 75:
                text_parts.extend([
                    f"{product_name} has medium health score: {overall_score}",
                    f"{product_name} health is moderate: {overall_score}",
                ])
            else:
                text_parts.extend([
                    f"{product_name} has high health score: {overall_score}",
                    f"{product_name} health is good: {overall_score}",
                ])
        
        return "\n".join(text_parts)
    
    def _build_qdrant_index(self, kpi_data: List[Dict], account_data: List[Dict], product_data: List[Dict] = None, temporal_data: List[Dict] = None, product_analytics_data: List[Dict] = None):
        """Build Qdrant index from embeddings"""
        if not kpi_data and not account_data and not product_data and not temporal_data:
            return
            
        points = []
        point_id = 0
        
        # Add KPI points
        for kpi in kpi_data:
            point = PointStruct(
                id=point_id,
                vector=kpi['embedding'],
                payload={
                    'type': 'kpi',
                    'customer_id': self.customer_id,
                    'kpi_id': kpi['kpi_id'],
                    'account_id': kpi['account_id'],
                    'account_name': kpi['account_name'],
                    'revenue': kpi['revenue'],
                    'industry': kpi['industry'],
                    'region': kpi['region'],
                    'category': kpi['category'],
                    'kpi_parameter': kpi['kpi_parameter'],
                    'data': kpi['data'],
                    'impact_level': kpi['impact_level'],
                    'text': kpi['text']
                }
            )
            points.append(point)
            point_id += 1
        
        # Add product points
        for product in product_data:
            point = PointStruct(
                id=point_id,
                vector=product['embedding'],
                payload={
                    'type': 'product',
                    'customer_id': self.customer_id,
                    'product_id': product['product_id'],
                    'account_id': product['account_id'],
                    'account_name': product['account_name'],
                    'product_name': product['product_name'],
                    'product_sku': product['product_sku'],
                    'product_type': product['product_type'],
                    'revenue': product['revenue'],
                    'status': product['status'],
                    'industry': product['industry'],
                    'region': product['region'],
                    'text': product['text']
                }
            )
            points.append(point)
            point_id += 1
        
        # Add account points
        for account in account_data:
            point = PointStruct(
                id=point_id,
                vector=account['embedding'],
                payload={
                    'type': 'account',
                    'customer_id': self.customer_id,
                    'account_id': account['account_id'],
                    'account_name': account['account_name'],
                    'revenue': account['revenue'],
                    'industry': account['industry'],
                    'region': account['region'],
                    'account_status': account['account_status'],
                    'text': account['text']
                }
            )
            points.append(point)
            point_id += 1
        
        # Add temporal data points
        if temporal_data:
            for temporal in temporal_data:
                point = PointStruct(
                    id=point_id,
                    vector=temporal['embedding'],
                    payload={
                        **temporal['metadata'],
                        'text': temporal['text']
                    }
                )
                points.append(point)
                point_id += 1
        
        # Add product analytics data points
        if product_analytics_data:
            for analytics in product_analytics_data:
                payload = {
                    'type': analytics['type'],
                    'customer_id': self.customer_id,
                    'text': analytics['text']
                }
                
                # Add type-specific fields
                if analytics['type'] == 'product_catalog':
                    payload.update({
                        'product_id': analytics['product_id'],
                        'product_name': analytics['product_name'],
                        'product_sku': analytics.get('product_sku'),
                        'product_type': analytics.get('product_type'),
                        'status': analytics.get('status')
                    })
                elif analytics['type'] == 'product_trend':
                    payload.update({
                        'product_id': analytics['product_id'],
                        'account_id': analytics['account_id'],
                        'product_name': analytics.get('product_name'),
                        'account_name': analytics.get('account_name'),
                        'overall_health_score': analytics.get('overall_health_score'),
                        'product_usage_score': analytics.get('product_usage_score'),
                        'support_score': analytics.get('support_score'),
                        'month': analytics.get('month'),
                        'year': analytics.get('year')
                    })
                elif analytics['type'] == 'product_aggregate_trend':
                    payload.update({
                        'product_id': analytics['product_id'],
                        'product_name': analytics.get('product_name'),
                        'overall_health_score': analytics.get('overall_health_score'),
                        'total_accounts': analytics.get('total_accounts'),
                        'total_revenue': analytics.get('total_revenue'),
                        'average_revenue_per_account': analytics.get('average_revenue_per_account'),
                        'month': analytics.get('month'),
                        'year': analytics.get('year')
                    })
                
                point = PointStruct(
                    id=point_id,
                    vector=analytics['embedding'],
                    payload=payload
                )
                points.append(point)
                point_id += 1
        
        # Upload points to Qdrant
        try:
            print(f"🔧 Uploading {len(points)} vectors to Qdrant collection '{self.collection_name}'...")
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            print(f"✅ Uploaded {len(points)} vectors to Qdrant collection")
            
            # Verify upload
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            print(f"📊 Collection info after upload: {collection_info}")
            
        except Exception as e:
            print(f"❌ Error uploading to Qdrant: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def query(self, query_text: str, query_type: str = 'general', collection: Optional[str] = None) -> Dict[str, Any]:
        """Query the enhanced RAG system using Qdrant with collection-aware prompts
        
        REQUIRES: QDRANT_URL and QDRANT_API_KEY environment variables
        NO FALLBACK: If Qdrant credentials are provided, system MUST use Qdrant
        """
        # Check if Qdrant credentials were provided but connection failed
        if hasattr(self, '_connection_error'):
            error_msg = f"Qdrant Cloud connection failed: {self._connection_error}"
            return {'error': error_msg, 'requires_qdrant': True}
        
        # If Qdrant is bypassed (no credentials), return error (no fallback)
        if hasattr(self, 'qdrant_bypassed') and self.qdrant_bypassed:
            return {'error': 'Qdrant Cloud credentials not provided. Set QDRANT_URL and QDRANT_API_KEY to use Qdrant.', 'requires_qdrant': True}
        
        # Ensure customer_id is set (should be set by get_qdrant_rag_system, but double-check)
        if not self.customer_id:
            # Try to get it from collection_name if it's in the format
            if self.collection_name and '_customer_' in self.collection_name:
                try:
                    customer_id_str = self.collection_name.split('_customer_')[-1]
                    self.customer_id = int(customer_id_str)
                    print(f"🔧 Extracted customer_id {self.customer_id} from collection name")
                except:
                    return {'error': 'Knowledge base not built for this customer - customer_id not set'}
            else:
                return {'error': 'Knowledge base not built for this customer - customer_id not set'}
        
        # Ensure collection_name is set (will be set in build_knowledge_base if not set)
        if not self.collection_name:
            collection_name_base = os.getenv('QDRANT_COLLECTION', 'kpi_dashboard_vectors')
            self.collection_name = f"{collection_name_base}_customer_{self.customer_id}"
            print(f"🔧 Collection name set to: {self.collection_name}")
        
        # Check if Qdrant is bypassed (no credentials provided)
        if hasattr(self, 'qdrant_bypassed') and self.qdrant_bypassed:
            return {'error': 'Qdrant Cloud credentials not provided. Set QDRANT_URL and QDRANT_API_KEY to use Qdrant.', 'requires_qdrant': True}
        
        # Check if qdrant_client exists (credentials provided but connection failed)
        if not hasattr(self, 'qdrant_client') or self.qdrant_client is None:
            if hasattr(self, '_connection_error'):
                return {'error': f'Qdrant Cloud connection failed: {self._connection_error}. Please verify credentials and network connectivity.', 'requires_qdrant': True}
            else:
                return {'error': 'Qdrant client not initialized. Please set QDRANT_URL and QDRANT_API_KEY.', 'requires_qdrant': True}
        
        # Check if collection exists, if not, try to build it
        collection_exists = False
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            collection_exists = True
            if collection_info.points_count == 0:
                # Collection exists but is empty, build knowledge base (only if not already building)
                if self.customer_id not in self._build_in_progress:
                    print(f"⚠️ Collection {self.collection_name} exists but is empty. Building knowledge base...")
                    self._build_in_progress[self.customer_id] = True
                    try:
                        self.build_knowledge_base(self.customer_id)
                    finally:
                        self._build_in_progress.pop(self.customer_id, None)
                else:
                    print(f"⚠️ Build already in progress for customer {self.customer_id}, skipping...")
        except Exception as e:
            error_msg = str(e).lower()
            error_full = str(e)
            # Check for various "not found" error patterns - be more permissive
            # Qdrant local storage might use different error messages
            is_not_found = any(phrase in error_msg for phrase in [
                'not found', 'does not exist', 'doesn\'t exist', 'not exist', 
                '404', 'collection', 'doesn\'t exist', 'missing', 'unknown collection'
            ])
            
            if is_not_found:
                # Collection doesn't exist, build it (only if not already building)
                if self.customer_id not in self._build_in_progress:
                    print(f"⚠️ Collection {self.collection_name} not found (error: {error_full[:100]}). Building knowledge base for customer {self.customer_id}...")
                    self._build_in_progress[self.customer_id] = True
                    try:
                        self.build_knowledge_base(self.customer_id)
                        # Verify it was created
                        try:
                            self.qdrant_client.get_collection(self.collection_name)
                            collection_exists = True
                            print(f"✅ Collection {self.collection_name} created successfully")
                        except Exception as verify_error:
                            print(f"⚠️ Verification failed but continuing: {str(verify_error)[:100]}")
                            # Still mark as exists since build completed
                            collection_exists = True
                    except Exception as build_error:
                        error_details = str(build_error)
                        print(f"❌ Failed to build knowledge base: {error_details}")
                        import traceback
                        traceback.print_exc()
                        return {'error': f'Collection not found and failed to build knowledge base: {error_details}'}
                    finally:
                        self._build_in_progress.pop(self.customer_id, None)
                else:
                    print(f"⚠️ Build already in progress for customer {self.customer_id}, returning error to prevent loop")
                    return {'error': f'Collection not found and build already in progress for customer {self.customer_id}'}
            else:
                # Other error accessing collection - but still try to build if it's a connection issue
                print(f"⚠️ Error accessing collection: {error_full[:200]}")
                # If it's a connection error, we might still want to try building
                if 'connection' in error_msg or 'refused' in error_msg:
                    if self.customer_id not in self._build_in_progress:
                        print(f"   This might be a connection issue, but collection might not exist. Trying to build anyway...")
                        self._build_in_progress[self.customer_id] = True
                        try:
                            self.build_knowledge_base(self.customer_id)
                            collection_exists = True
                        except:
                            pass
                        finally:
                            self._build_in_progress.pop(self.customer_id, None)
                    else:
                        print(f"   Build already in progress, skipping...")
                if not collection_exists:
                    return {'error': f'Failed to access collection: {error_full[:200]}'}
        
        # If we still don't have a collection, something went wrong
        if not collection_exists:
            return {'error': 'Collection does not exist and could not be created'}
        
        # Generate query embedding using OpenAI
        query_embedding = self._generate_embedding(query_text, self.customer_id)
        
        # Search Qdrant - No filter needed since collection is per-customer (tenant isolated)
        # All data in this collection belongs to self.customer_id
        try:
            # For product queries, increase limit (we'll filter manually to avoid 400 errors)
            # Note: We don't use Qdrant filter for 'type' field because it requires indexing
            # Instead, we query more results and filter manually (already implemented below)
            search_limit = self.top_k * 2 if query_type == 'product_analysis' else self.top_k
            
            # Query without filter - we'll filter results manually for product queries
            # This avoids 400 Bad Request errors from Qdrant when 'type' field isn't indexed
            query_response = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,  # Direct vector list
                # No customer_id filter needed - collection is already tenant-isolated
                # No type filter - we filter manually to avoid index requirement
                limit=search_limit,
                with_payload=True
            )
        except Exception as query_error:
            # Catch collection not found errors during query
            error_msg = str(query_error).lower()
            if any(phrase in error_msg for phrase in ['not found', 'does not exist', 'doesn\'t exist', 'not exist', '404', 'collection']):
                if self.customer_id not in self._build_in_progress:
                    print(f"⚠️ Collection {self.collection_name} not found during query. Building knowledge base...")
                    self._build_in_progress[self.customer_id] = True
                    try:
                        self.build_knowledge_base(self.customer_id)
                        # Retry query after building
                        # Use same approach as main query: no filter, manual filtering for products
                        search_limit_retry = self.top_k * 2 if query_type == 'product_analysis' else self.top_k
                        query_response = self.qdrant_client.query_points(
                            collection_name=self.collection_name,
                            query=query_embedding,
                            limit=search_limit_retry,
                            with_payload=True
                        )
                        print(f"✅ Query successful after building collection")
                    except Exception as build_error:
                        print(f"❌ Failed to build knowledge base: {str(build_error)}")
                        return {'error': f'Collection not found and failed to build: {str(build_error)}'}
                    finally:
                        self._build_in_progress.pop(self.customer_id, None)
                else:
                    print(f"⚠️ Build already in progress for customer {self.customer_id}, returning error to prevent loop")
                    return {'error': f'Collection not found and build already in progress for customer {self.customer_id}'}
            else:
                # Other query error, re-raise
                print(f"❌ Query error: {str(query_error)}")
                raise
        
        # Extract results from QueryResponse
        search_results = query_response.points if hasattr(query_response, 'points') else []
        
        # ✅ RECOMMENDATION 2: For product queries, include product AND product analytics types
        if query_type == 'product_analysis':
            # Include product, product_catalog, product_trend, and product_aggregate_trend types
            product_results = []
            for result in search_results:
                payload = {}
                if hasattr(result, 'payload'):
                    payload = result.payload if result.payload else {}
                elif hasattr(result, 'payloads'):
                    payload = result.payloads[0] if result.payloads else {}
                
                result_type = payload.get('type', '')
                # Include product types and product analytics types
                if result_type in ['product', 'product_catalog', 'product_trend', 'product_aggregate_trend']:
                    product_results.append(result)
            
            # Use product and product analytics results
            search_results = product_results
            
            if len(product_results) == 0:
                print("⚠️ No product results found in knowledge base for product query")
            else:
                # Count by type for debugging
                type_counts = {}
                for result in product_results:
                    payload = {}
                    if hasattr(result, 'payload'):
                        payload = result.payload if result.payload else {}
                    elif hasattr(result, 'payloads'):
                        payload = result.payloads[0] if result.payloads else {}
                    result_type = payload.get('type', 'unknown')
                    type_counts[result_type] = type_counts.get(result_type, 0) + 1
                print(f"📊 Product query found {len(product_results)} results: {type_counts}")
        
        # Filter by similarity threshold (very permissive)
        relevant_results = []
        for result in search_results:
            # Extract score and payload from ScoredPoint
            # Try different attribute names for score
            score = None
            if hasattr(result, 'score'):
                score = result.score
            elif hasattr(result, 'similarity'):
                score = result.similarity
            
            # Extract payload
            payload = {}
            if hasattr(result, 'payload'):
                payload = result.payload if result.payload else {}
            elif hasattr(result, 'payloads'):
                payload = result.payloads[0] if result.payloads else {}
            
            # Accept all results with any positive score
            if score is not None and score > 0:
                result_type = payload.get('type', 'unknown')
                metadata = {
                    'type': result_type,
                    'account_id': payload.get('account_id'),
                    'account_name': payload.get('account_name'),
                    'revenue': payload.get('revenue'),
                    'industry': payload.get('industry'),
                    'region': payload.get('region'),
                }
                
                # Add type-specific metadata
                if result_type == 'kpi':
                    metadata.update({
                        'kpi_id': payload.get('kpi_id'),
                        'category': payload.get('category'),
                        'kpi_parameter': payload.get('kpi_parameter'),
                        'data': payload.get('data'),
                        'impact_level': payload.get('impact_level')
                    })
                elif result_type == 'product':
                    metadata.update({
                        'product_id': payload.get('product_id'),
                        'product_name': payload.get('product_name'),
                        'product_sku': payload.get('product_sku'),
                        'product_type': payload.get('product_type'),
                        'status': payload.get('status')
                    })
                elif result_type == 'account':
                    metadata.update({
                        'account_status': payload.get('account_status')
                    })
                
                relevant_results.append({
                    'similarity': float(score),
                    'text': payload.get('text', ''),
                    'metadata': metadata
                })
        
        # Infer collection if not provided
        if not collection:
            collection = self._infer_collection_from_query_type(query_type)
        
        # Generate response using OpenAI with collection-aware prompts
        response = self._generate_openai_response(query_text, relevant_results, query_type, collection)
        
        return {
            'query': query_text,
            'query_type': query_type,
            'collection': collection,  # Include collection in response
            'customer_id': self.customer_id,
            'results_count': len(relevant_results),
            'similarity_threshold': self.similarity_threshold,
            'response': response,
            'relevant_results': relevant_results[:5]  # Limit for response
        }
    
    def _generate_openai_response(self, query: str, results: List[Dict], query_type: str, collection: Optional[str] = None) -> str:
        """Generate response using OpenAI GPT-4 with hierarchical collection + query_type prompts"""
        if not results:
            return "I couldn't find relevant information to answer your query."
        
        # Prepare context from results
        context = self._prepare_context(results)
        
        # Get collection-level base prompt and query_type-specific prompt
        system_prompt = self._get_combined_system_prompt(collection, query_type)
        
        user_prompt = f"""
        Query: {query}
        
        Context from knowledge base (Customer ID: {self.customer_id}):
        {context}
        
        Please provide a comprehensive analysis and answer to the query based on the available data.
        Include specific insights, recommendations, and relevant metrics where applicable.
        Format your response in a clear, actionable manner.
        """
        
        try:
            # Get API key from environment at query time
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                # Try the specific key that was provided
                api_key = "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"
            
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def _infer_collection_from_query_type(self, query_type: str) -> str:
        """Infer collection from query_type if not explicitly provided"""
        QUANTITATIVE_TYPES = ['revenue_analysis', 'account_analysis', 'kpi_analysis', 'product_analysis', 'general']
        HISTORICAL_TYPES = ['trend_analysis', 'temporal_analysis']
        
        if query_type in QUANTITATIVE_TYPES:
            return 'quantitative'
        elif query_type in HISTORICAL_TYPES:
            return 'historical'
        else:
            return 'quantitative'  # Default fallback
    
    def _get_collection_base_prompt(self, collection: str) -> str:
        """Get collection-level base prompt"""
        COLLECTION_PROMPTS = {
            'quantitative': """You are analyzing QUANTITATIVE data from structured databases:
- KPI metrics, health scores, revenue figures, account statistics
- Numerical values, rankings, comparisons
- Precise, measurable, factual data

CRITICAL GUIDELINES:
1. Base answers STRICTLY on numeric values from the data
2. Provide specific metrics, scores, percentages, rankings
3. Use quantitative comparisons (e.g., "Account A has 45% higher revenue than Account B")
4. Avoid speculation - only use data explicitly provided
5. Cite specific numbers from the data

Data Sources: PostgreSQL (KPIs, Accounts, Health Scores, Revenue)
Response Style: Metrics-focused, precise, data-driven""",
            
            'qualitative': """You are analyzing QUALITATIVE data from unstructured text sources:
- Emails, meeting transcripts, support tickets, notes
- Sentiment, tone, themes, context, communication patterns
- Subjective interpretation, textual analysis

CRITICAL GUIDELINES:
1. Analyze sentiment, tone, and underlying themes
2. Extract contextual insights from communications
3. Identify patterns and trends in qualitative feedback
4. Synthesize information from multiple text sources
5. Provide evidence-based interpretations

Data Sources: PostgreSQL (qualitative_signals, account_notes, playbook_reports)
Response Style: Theme-focused, context-aware, sentiment-driven""",
            
            'historical': """You are analyzing HISTORICAL and TEMPORAL data:
- Time-series data, trends over time, evolution patterns
- Seasonal patterns, predictive insights, historical comparisons
- Temporal relationships, growth trajectories

CRITICAL GUIDELINES:
1. Focus on trends, patterns, and evolution over time
2. Identify temporal relationships and seasonality
3. Compare current vs. historical performance
4. Provide predictive insights based on historical patterns
5. Highlight significant changes and trend directions

Data Sources: PostgreSQL (kpi_time_series, health_trends, historical snapshots)
Response Style: Trend-focused, temporal, predictive"""
        }
        
        return COLLECTION_PROMPTS.get(collection, COLLECTION_PROMPTS['quantitative'])
    
    def _get_query_type_specific_prompt(self, query_type: str) -> str:
        """Get query_type-specific prompt focus"""
        QUERY_TYPE_PROMPTS = {
            'product_analysis': """SPECIFIC FOCUS: Product Analysis
- CRITICAL: Always return actual PRODUCT NAMES from the data - never return KPI names or account names as products
- Focus on PRODUCT NAMES, product types, product SKUs, and product usage
- Identify which PRODUCTS are used by which accounts/customers
- Provide specific PRODUCT NAMES when answering product-related questions - list them explicitly
- Count how many accounts use each PRODUCT and list the product names
- When asked "which products are widely used", return a list of actual product names (e.g., "Product A", "Product B", "Product C")
- When asked "what products", "which products", or "list products", return product names from the product data
- Do NOT confuse products with KPIs - products have names like "Enterprise Suite", "Cloud Platform", etc.
- Do NOT confuse products with accounts - products are things accounts use, not the accounts themselves
- If product data is available, prioritize product information over KPI metrics
- Format your answer with clear product names in a list or bullet points""",
            
            'revenue_analysis': """SPECIFIC FOCUS: Revenue Analysis
- Focus on revenue drivers, account performance, and business insights
- Provide specific metrics and actionable recommendations
- Analyze revenue patterns, growth, and financial performance""",
            
            'account_analysis': """SPECIFIC FOCUS: Account Analysis
- Focus on account health, engagement patterns, and retention strategies
- Analyze customer relationships and risk assessment
- Provide insights about account performance and engagement""",
            
            'kpi_analysis': """SPECIFIC FOCUS: KPI Analysis
- Focus on performance optimization and strategic insights
- Analyze KPI performance, trends, and impact levels
- Provide insights about business metrics and recommendations""",
            
            'trend_analysis': """SPECIFIC FOCUS: Trend Analysis
- Focus on identifying patterns and trends over time
- Analyze historical evolution and changes
- Provide insights about directional changes and patterns""",
            
            'temporal_analysis': """SPECIFIC FOCUS: Temporal Analysis
- Focus on time-based patterns, seasonality, and cyclical trends
- Analyze temporal relationships and time-series data
- Provide insights about time-dependent patterns""",
            
            'qualitative_analysis': """SPECIFIC FOCUS: Qualitative Analysis
- Focus on sentiment, tone, and communication themes
- Analyze text data, context, and qualitative signals
- Provide insights based on textual and contextual information"""
        }
        
        return QUERY_TYPE_PROMPTS.get(query_type, """SPECIFIC FOCUS: General Business Intelligence
- Provide comprehensive analysis with specific recommendations
- Analyze the provided data to answer questions about business performance, KPIs, and customer insights
- Use available data to provide actionable insights""")
    
    def _get_combined_system_prompt(self, collection: Optional[str], query_type: str) -> str:
        """Get combined collection + query_type system prompt using hierarchical approach"""
        # Infer collection if not provided
        if not collection:
            collection = self._infer_collection_from_query_type(query_type)
        
        # Get collection-level base prompt
        base_prompt = self._get_collection_base_prompt(collection)
        
        # Get query_type-specific prompt
        specific_prompt = self._get_query_type_specific_prompt(query_type)
        
        # Combine prompts hierarchically
        combined_prompt = f"{base_prompt}\n\n{specific_prompt}"
        
        return combined_prompt
    
    def _prepare_context(self, results: List[Dict], query_type: str = 'general') -> str:
        """Prepare context from search results"""
        context_parts = []
        
        # ✅ RECOMMENDATION 2: For product queries, include product AND product analytics types
        filtered_results = results
        if query_type == 'product_analysis':
            product_types = ['product', 'product_catalog', 'product_trend', 'product_aggregate_trend']
            filtered_results = [r for r in results if r.get('metadata', {}).get('type') in product_types]
            if len(filtered_results) == 0:
                return "No product data found in the knowledge base. Only account and KPI information is available."
        
        for i, result in enumerate(filtered_results[:10]):  # Limit to top 10 results
            metadata = result['metadata']
            text = result['text']
            similarity = result['similarity']
            
            if metadata['type'] == 'kpi':
                context_parts.append(f"""
                KPI {i+1} (Similarity: {similarity:.3f}):
                {text}
                """)
            elif metadata['type'] == 'product':
                # Enhance product context with metadata - emphasize product name
                product_name = metadata.get('product_name', 'Unknown')
                product_info = f"PRODUCT NAME: {product_name}"
                if metadata.get('product_sku'):
                    product_info += f" (SKU: {metadata['product_sku']})"
                if metadata.get('product_type'):
                    product_info += f" (Type: {metadata['product_type']})"
                if metadata.get('account_name'):
                    product_info += f" - Used by Account: {metadata['account_name']}"
                if metadata.get('revenue'):
                    product_info += f" - Revenue: ${metadata['revenue']:,.0f}"
                context_parts.append(f"""
                {product_info} (Similarity: {similarity:.3f}):
                {text}
                """)
            elif metadata['type'] == 'product_catalog':
                # ✅ RECOMMENDATION 2: Product catalog context
                product_name = metadata.get('product_name', 'Unknown')
                product_info = f"PRODUCT CATALOG: {product_name}"
                if metadata.get('product_sku'):
                    product_info += f" (SKU: {metadata['product_sku']})"
                if metadata.get('product_type'):
                    product_info += f" (Type: {metadata['product_type']})"
                if metadata.get('status'):
                    product_info += f" (Status: {metadata['status']})"
                context_parts.append(f"""
                Product Catalog Entry {i+1} (Similarity: {similarity:.3f}):
                {product_info}
                {text}
                """)
            elif metadata['type'] == 'product_trend':
                # ✅ RECOMMENDATION 2: Product health trend context
                product_name = metadata.get('product_name', 'Unknown')
                account_name = metadata.get('account_name', 'Unknown')
                health_score = metadata.get('overall_health_score')
                product_info = f"PRODUCT HEALTH TREND: {product_name} @ {account_name}"
                if health_score is not None:
                    product_info += f" - Health Score: {health_score:.1f}/100"
                if metadata.get('product_usage_score') is not None:
                    product_info += f" - Usage Score: {metadata['product_usage_score']:.1f}/100"
                if metadata.get('support_score') is not None:
                    product_info += f" - Support Score: {metadata['support_score']:.1f}/100"
                context_parts.append(f"""
                Product Health Trend {i+1} (Similarity: {similarity:.3f}):
                {product_info}
                {text}
                """)
            elif metadata['type'] == 'product_aggregate_trend':
                # ✅ RECOMMENDATION 2: Aggregate product trend context
                product_name = metadata.get('product_name', 'Unknown')
                health_score = metadata.get('overall_health_score')
                product_info = f"AGGREGATE PRODUCT HEALTH: {product_name}"
                if health_score is not None:
                    product_info += f" - Overall Health Score: {health_score:.1f}/100"
                if metadata.get('total_accounts') is not None:
                    product_info += f" - Total Accounts: {metadata['total_accounts']}"
                if metadata.get('total_revenue') is not None:
                    product_info += f" - Total Revenue: ${metadata['total_revenue']:,.0f}"
                context_parts.append(f"""
                Aggregate Product Trend {i+1} (Similarity: {similarity:.3f}):
                {product_info}
                {text}
                """)
            elif metadata['type'] == 'account':
                context_parts.append(f"""
                Account {i+1} (Similarity: {similarity:.3f}):
                {text}
                """)
            else:
                context_parts.append(f"""
                Result {i+1} (Similarity: {similarity:.3f}):
                {text}
                """)
        
        return "\n".join(context_parts)
    
    def analyze_revenue_drivers(self, customer_id: int) -> Dict[str, Any]:
        """Analyze revenue drivers across accounts using Qdrant"""
        try:
            # Query for revenue-related data
            revenue_embedding = self._generate_embedding("revenue business outcomes financial performance", self.customer_id)
            query_response = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=revenue_embedding,  # Direct vector list
                # No customer_id filter needed - collection is per-customer (tenant isolated)
                limit=50,
                with_payload=True
            )
            search_results = query_response.points if hasattr(query_response, 'points') else []
            
            # Process results
            accounts = {}
            total_revenue = 0
            
            for result in search_results:
                payload = getattr(result, 'payload', {}) if hasattr(result, 'payload') else {}
                if payload.get('type') == 'account':
                    account_id = payload.get('account_id')
                    if account_id not in accounts:
                        accounts[account_id] = {
                            'account_name': payload.get('account_name'),
                            'revenue': payload.get('revenue', 0),
                            'industry': payload.get('industry'),
                            'region': payload.get('region')
                        }
                        total_revenue += payload.get('revenue', 0)
            
            # Sort accounts by revenue
            sorted_accounts = sorted(accounts.values(), key=lambda x: x['revenue'], reverse=True)
            
            return {
                'total_revenue': total_revenue,
                'top_accounts': sorted_accounts[:5],
                'total_accounts': len(accounts)
            }
            
        except Exception as e:
            return {'error': f'Revenue analysis failed: {str(e)}'}
    
    def find_at_risk_accounts(self, customer_id: int) -> Dict[str, Any]:
        """Find accounts at risk of churn using Qdrant"""
        try:
            # Query for risk-related data
            risk_embedding = self._generate_embedding("churn risk satisfaction engagement health score", self.customer_id)
            query_response = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=risk_embedding,  # Direct vector list
                # No customer_id filter needed - collection is per-customer (tenant isolated)
                limit=50,
                with_payload=True
            )
            search_results = query_response.points if hasattr(query_response, 'points') else []
            
            # Process results
            risk_indicators = []
            
            for result in search_results:
                payload = getattr(result, 'payload', {}) if hasattr(result, 'payload') else {}
                if payload.get('type') == 'kpi':
                    kpi_param = payload.get('kpi_parameter', '').lower()
                    if any(keyword in kpi_param for keyword in ['churn', 'risk', 'flag', 'satisfaction']):
                        try:
                            value = float(str(payload.get('data', '0')).replace('%', '').replace(',', ''))
                            if value < 50:  # Low scores indicate risk
                                risk_indicators.append({
                                    'account_name': payload.get('account_name', 'Unknown'),
                                    'kpi_parameter': payload.get('kpi_parameter'),
                                    'value': payload.get('data'),
                                    'risk_level': 'High' if value < 30 else 'Medium'
                                })
                        except:
                            pass
            
            return {
                'at_risk_accounts': risk_indicators,
                'total_indicators': len(risk_indicators)
            }
            
        except Exception as e:
            return {'error': f'Risk analysis failed: {str(e)}'}
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the Qdrant collection"""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return {
                'collection_name': self.collection_name,
                'dimension': self.embedding_dimension,
                'embedding_model': self.embedding_model,
                'vectors_count': collection_info.points_count,
                'indexed_vectors_count': collection_info.indexed_vectors_count if hasattr(collection_info, 'indexed_vectors_count') else collection_info.points_count,
                'status': str(collection_info.status) if hasattr(collection_info, 'status') else 'unknown'
            }
        except Exception as e:
            return {
                'collection_name': self.collection_name,
                'dimension': self.embedding_dimension,
                'embedding_model': self.embedding_model,
                'error': f'Failed to get collection info: {str(e)}'
            }
    
    def _aggregate_monthly_revenue(self, time_series_data, kpis, account_lookup):
        """Aggregate monthly revenue data from time-series records and account data"""
        monthly_data = {}
        
        # First, get all unique months from time-series data
        months_years = set()
        for ts in time_series_data:
            months_years.add((ts.month, ts.year))
        
        # For each month, aggregate revenue data
        for month, year in months_years:
            month_year = (month, year)
            monthly_data[month_year] = {
                'total_revenue': 0,
                'account_revenues': {},
                'account_count': 0
            }
            
            # Get all accounts for this customer
            for account_id, account in account_lookup.items():
                if account.customer_id == self.customer_id:
                    # Use account revenue as base (this represents the account's total revenue)
                    account_revenue = float(account.revenue) if account.revenue else 0
                    
                    # Look for revenue growth or changes in time-series data for this account
                    revenue_growth = 0
                    for ts in time_series_data:
                        if (ts.account_id == account_id and 
                            ts.month == month and 
                            ts.year == year):
                            
                            # Get the KPI parameter from the related KPI record
                            kpi = next((k for k in kpis if k.kpi_id == ts.kpi_id), None)
                            if kpi and ('revenue' in kpi.kpi_parameter.lower() or 'growth' in kpi.kpi_parameter.lower()):
                                
                                # Apply growth percentage to base revenue
                                growth_value = float(ts.value) if ts.value else 0
                                if '%' in str(ts.value):
                                    # It's a percentage, apply it to base revenue
                                    revenue_growth = account_revenue * (growth_value / 100)
                                else:
                                    # It's an absolute value
                                    revenue_growth = growth_value
                                break
                    
                    # Calculate final revenue for this month
                    final_revenue = account_revenue + revenue_growth
                    
                    if final_revenue > 0:
                        monthly_data[month_year]['total_revenue'] += final_revenue
                        monthly_data[month_year]['account_revenues'][account_id] = {
                            'account_name': account.account_name,
                            'revenue': final_revenue,
                            'base_revenue': account_revenue,
                            'growth': revenue_growth
                        }
                        monthly_data[month_year]['account_count'] += 1
        
        # Calculate top accounts for each month
        for month_year, data in monthly_data.items():
            # Sort accounts by revenue and get top 5
            sorted_accounts = sorted(
                data['account_revenues'].items(),
                key=lambda x: x[1]['revenue'],
                reverse=True
            )[:5]
            
            data['top_accounts'] = [
                {
                    'account_id': acc_id,
                    'account_name': acc_data['account_name'],
                    'revenue': acc_data['revenue'],
                    'base_revenue': acc_data['base_revenue'],
                    'growth': acc_data['growth']
                }
                for acc_id, acc_data in sorted_accounts
            ]
        
        return monthly_data
    
    def _create_temporal_text(self, month: int, year: int, data: Dict):
        """Create text representation for temporal revenue data"""
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }
        
        month_name = month_names.get(month, f"Month {month}")
        total_revenue = data['total_revenue']
        account_count = data['account_count']
        top_accounts = data['top_accounts']
        
        text = f"""Monthly Revenue Report: {month_name} {year}
Total Revenue: ${total_revenue:,.2f}
Active Accounts: {account_count}
Top Revenue Accounts:"""
        
        for i, acc in enumerate(top_accounts, 1):
            text += f"\n{i}. {acc['account_name']}: ${acc['revenue']:,.2f}"
        
        if top_accounts:
            text += f"""

This month showed revenue performance across {account_count} active accounts.
The top performing account was {top_accounts[0]['account_name']} with ${top_accounts[0]['revenue']:,.2f}."""
        else:
            text += f"""

This month showed revenue performance across {account_count} active accounts."""
        
        return text.strip()

# Global instances for each customer (multi-tenant support)
qdrant_rag_systems = {}

def get_qdrant_rag_system(customer_id: int) -> EnhancedRAGSystemQdrant:
    """Get or create Qdrant RAG system instance for specific customer"""
    # Only create new instance if it doesn't exist
    if customer_id not in qdrant_rag_systems:
        qdrant_rag_systems[customer_id] = EnhancedRAGSystemQdrant()
        qdrant_rag_systems[customer_id].customer_id = customer_id
        # Set per-customer collection name for tenant isolation
        collection_name_base = os.getenv('QDRANT_COLLECTION', 'kpi_dashboard_vectors')
        qdrant_rag_systems[customer_id].collection_name = f"{collection_name_base}_customer_{customer_id}"
        print(f"🔧 Initialized RAG system for customer {customer_id}, collection: {qdrant_rag_systems[customer_id].collection_name}")
    else:
        # Ensure customer_id is set
        qdrant_rag_systems[customer_id].customer_id = customer_id
        # Ensure collection_name is set
        if not qdrant_rag_systems[customer_id].collection_name:
            collection_name_base = os.getenv('QDRANT_COLLECTION', 'kpi_dashboard_vectors')
            qdrant_rag_systems[customer_id].collection_name = f"{collection_name_base}_customer_{customer_id}"
            print(f"🔧 Set collection name for customer {customer_id}: {qdrant_rag_systems[customer_id].collection_name}")
    
    return qdrant_rag_systems[customer_id]
