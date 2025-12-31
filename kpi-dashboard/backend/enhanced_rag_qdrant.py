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
from models import db, KPI, Account, KPIUpload, CustomerConfig, KPITimeSeries

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
        
        # Initialize Qdrant client with local file storage fallback
        try:
            self.qdrant_client = QdrantClient(
                host=os.getenv('QDRANT_HOST', 'localhost'),
                port=int(os.getenv('QDRANT_PORT', 6333))
            )
            # Test connection
            self.qdrant_client.get_collections()
            print("✅ Connected to Qdrant server")
        except Exception as e:
            print(f"⚠️ Qdrant server not available, using local file storage: {e}")
            # Use fixed storage path for consistency (all instances use same storage)
            self.qdrant_client = QdrantClient(path="./qdrant_storage")
        
        # Configuration
        # Use per-customer collections for tenant isolation (SECURITY)
        # Collection name will be set based on customer_id in build_knowledge_base()
        self.collection_name_base = os.getenv('QDRANT_COLLECTION', 'kpi_dashboard_vectors')
        self.collection_name = None  # Will be set per customer
        self.top_k = int(os.getenv('RAG_TOP_K', 10))
        self.similarity_threshold = float(os.getenv('RAG_SIMILARITY_THRESHOLD', 0.01))
        self.customer_id = None
        self.openai_client = None  # Will be initialized when needed
    
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
            print(f"❌ Error ensuring collection exists: {str(e)}")
            # Fallback to local file-based storage
            self.qdrant_client = QdrantClient(path="./qdrant_storage")
            self._ensure_collection_exists()
    
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
        
        # Fetch all KPIs for the customer
        kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).all()
        
        # Fetch all accounts for the customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        # Fetch time-series data for the customer
        time_series_data = KPITimeSeries.query.filter_by(customer_id=customer_id).all()
        
        # Create account lookup
        account_lookup = {acc.account_id: acc for acc in accounts}
        
        # Prepare data for indexing
        kpi_data = []
        account_data = []
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
        
        # Process temporal data for monthly revenue analysis
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
        
        # Build Qdrant index
        self._build_qdrant_index(kpi_data, account_data, temporal_data)
        
        print(f"✅ Qdrant knowledge base built for customer {customer_id} with {len(kpi_data)} KPIs, {len(account_data)} accounts, and {len(temporal_data)} monthly records")
        
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
    
    def _build_qdrant_index(self, kpi_data: List[Dict], account_data: List[Dict], temporal_data: List[Dict] = None):
        """Build Qdrant index from embeddings"""
        if not kpi_data and not account_data and not temporal_data:
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
        """Query the enhanced RAG system using Qdrant with collection-aware prompts"""
        if not self.customer_id:
            return {'error': 'Knowledge base not built for this customer'}
        if not self.collection_name:
            return {'error': 'Collection name not set. Must build knowledge base first.'}
        
        # Generate query embedding using OpenAI
        query_embedding = self._generate_embedding(query_text, self.customer_id)
        
        # Search Qdrant - No filter needed since collection is per-customer (tenant isolated)
        # All data in this collection belongs to self.customer_id
        try:
            # Use query_points with direct vector (newer API)
            query_response = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,  # Direct vector list
                # No customer_id filter needed - collection is already tenant-isolated
                limit=self.top_k,
                with_payload=True
            )
            
            # Extract results from QueryResponse
            search_results = query_response.points if hasattr(query_response, 'points') else []
            
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
                    relevant_results.append({
                        'similarity': float(score),
                        'text': payload.get('text', ''),
                        'metadata': {
                            'type': payload.get('type', 'unknown'),
                            'kpi_id': payload.get('kpi_id'),
                            'account_id': payload.get('account_id'),
                            'account_name': payload.get('account_name'),
                            'revenue': payload.get('revenue'),
                            'industry': payload.get('industry'),
                            'region': payload.get('region'),
                            'category': payload.get('category'),
                            'kpi_parameter': payload.get('kpi_parameter'),
                            'data': payload.get('data'),
                            'impact_level': payload.get('impact_level')
                        }
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
            
        except Exception as e:
            return {'error': f'Query failed: {str(e)}'}
    
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
        QUANTITATIVE_TYPES = ['revenue_analysis', 'account_analysis', 'kpi_analysis', 'general']
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
    
    def _prepare_context(self, results: List[Dict]) -> str:
        """Prepare context from search results"""
        context_parts = []
        
        for i, result in enumerate(results[:10]):  # Limit to top 10 results
            metadata = result['metadata']
            text = result['text']
            similarity = result['similarity']
            
            if metadata['type'] == 'kpi':
                context_parts.append(f"""
                KPI {i+1} (Similarity: {similarity:.3f}):
                {text}
                """)
            else:
                context_parts.append(f"""
                Account {i+1} (Similarity: {similarity:.3f}):
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
    else:
        # Ensure customer_id is set
        qdrant_rag_systems[customer_id].customer_id = customer_id
        # Ensure collection_name is set
        if not qdrant_rag_systems[customer_id].collection_name:
            collection_name_base = os.getenv('QDRANT_COLLECTION', 'kpi_dashboard_vectors')
            qdrant_rag_systems[customer_id].collection_name = f"{collection_name_base}_customer_{customer_id}"
    
    return qdrant_rag_systems[customer_id]
