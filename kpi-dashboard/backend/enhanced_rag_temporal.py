#!/usr/bin/env python3
"""
Enhanced RAG System with Qdrant Vector Database and OpenAI GPT-4
Includes time-series data for temporal analysis and monthly revenue tracking
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import openai
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from models import db, KPI, Account, KPIUpload, CustomerConfig, KPITimeSeries

# Load environment variables
load_dotenv()

class EnhancedRAGTemporalSystem:
    def __init__(self):
        """Initialize the enhanced RAG system with Qdrant and OpenAI for temporal analysis"""
        # Initialize OpenAI client
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Lazy load embedding model
        self.embedding_model = None
        self.embedding_dimension = 384  # all-MiniLM-L6-v2 dimension
        
        # Lazy load Qdrant client
        self.qdrant_client = None
        
        # Configuration
        self.collection_name = os.getenv('QDRANT_COLLECTION', 'kpi_dashboard_temporal')
        self.top_k = int(os.getenv('RAG_TOP_K', 10))
        self.similarity_threshold = float(os.getenv('RAG_SIMILARITY_THRESHOLD', 0.3))
        self.customer_id = None
        
        # Ensure collection exists
        self._ensure_collection_exists()
    
    def _get_qdrant_client(self):
        """Lazy load the Qdrant client"""
        if self.qdrant_client is None:
            try:
                self.qdrant_client = QdrantClient(
                    host=os.getenv('QDRANT_HOST', 'localhost'),
                    port=int(os.getenv('QDRANT_PORT', 6333))
                )
            except Exception as e:
                print(f"❌ Error with Qdrant collection: {e}")
                # Fallback to local file-based storage with unique path
                self.qdrant_client = QdrantClient(path=f"./qdrant_temporal_storage_{self.customer_id or 'default'}")
                print("🔄 Using local file-based Qdrant storage")
        return self.qdrant_client
    
    def _get_embedding_model(self):
        """Lazy load the embedding model"""
        if self.embedding_model is None:
            print("Loading SentenceTransformer model...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ SentenceTransformer model loaded")
        return self.embedding_model
        
    def _ensure_collection_exists(self):
        """Ensure Qdrant collection exists with proper configuration"""
        try:
            client = self._get_qdrant_client()
            
            # Try to get collections, if it fails, create the collection
            try:
                collections = client.get_collections()
                collection_names = [col.name for col in collections.collections]
                
                if self.collection_name not in collection_names:
                    print(f"Creating collection: {self.collection_name}")
                    client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=self.embedding_dimension,
                            distance=Distance.COSINE
                        )
                    )
                    print(f"✅ Created Qdrant collection: {self.collection_name}")
                else:
                    print(f"✅ Using existing Qdrant collection: {self.collection_name}")
            except Exception as e:
                # If we can't get collections, try to create the collection directly
                print(f"Could not get collections, creating directly: {e}")
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ Created Qdrant collection: {self.collection_name}")
                
        except Exception as e:
            print(f"❌ Error with Qdrant collection: {e}")
            raise e
    
    def build_knowledge_base(self, customer_id: int):
        """Build Qdrant vector database from KPI, account, and time-series data for specific customer"""
        print(f"🔍 Building temporal Qdrant knowledge base for customer {customer_id}...")
        
        # Store customer ID for this instance
        self.customer_id = customer_id
        
        # Fetch all KPIs for the customer
        kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).all()
        
        # Fetch all accounts for the customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        # Fetch time-series data for the customer
        time_series_data = KPITimeSeries.query.filter_by(customer_id=customer_id).all()
        
        # Create account lookup
        account_lookup = {acc.account_id: acc for acc in accounts}
        
        # Create KPI lookup
        kpi_lookup = {kpi.kpi_id: kpi for kpi in kpis}
        
        # Prepare data for indexing
        records = []
        
        # Process static KPI data
        for kpi in kpis:
            account = account_lookup.get(kpi.account_id)
            kpi_text = self._create_kpi_text(kpi, account)
            embedding = self._get_embedding_model().encode([kpi_text])[0].tolist()
            
            records.append({
                'text': kpi_text,
                'embedding': embedding,
                'metadata': {
                    'type': 'kpi',
                    'kpi_id': kpi.kpi_id,
                    'account_id': kpi.account_id,
                    'account_name': account.account_name if account else 'Unknown',
                    'kpi_parameter': kpi.kpi_parameter,
                    'data': kpi.data,
                    'category': kpi.category,
                    'industry': account.industry if account else None,
                    'region': account.region if account else None,
                    'revenue': float(account.revenue) if account and account.revenue else None,
                    'customer_id': customer_id
                }
            })
        
        # Process account data
        for account in accounts:
            account_text = self._create_account_text(account)
            embedding = self._get_embedding_model().encode([account_text])[0].tolist()
            
            records.append({
                'text': account_text,
                'embedding': embedding,
                'metadata': {
                    'type': 'account',
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'industry': account.industry,
                    'region': account.region,
                    'revenue': float(account.revenue) if account.revenue else None,
                    'customer_id': customer_id
                }
            })
        
        # Process time-series data with monthly revenue aggregation
        monthly_revenue_data = self._aggregate_monthly_revenue(time_series_data, kpi_lookup, account_lookup)
        
        for month_year, data in monthly_revenue_data.items():
            month, year = month_year
            temporal_text = self._create_temporal_text(month, year, data)
            embedding = self._get_embedding_model().encode([temporal_text])[0].tolist()
            
            records.append({
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
        
        # Ensure collection exists before uploading
        self._ensure_collection_exists()
        
        # Upload to Qdrant
        try:
            points = []
            for i, record in enumerate(records):
                points.append(PointStruct(
                    id=i,
                    vector=record['embedding'],
                    payload=record['metadata']
                ))
            
            # Upload in batches
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self._get_qdrant_client().upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
            
            print(f"✅ Uploaded {len(records)} vectors to Qdrant collection")
            print(f"✅ Temporal knowledge base built for customer {customer_id} with {len(kpis)} KPIs, {len(accounts)} accounts, and {len(monthly_revenue_data)} monthly records")
            
        except Exception as e:
            print(f"❌ Error uploading to Qdrant: {e}")
            raise e
    
    def _aggregate_monthly_revenue(self, time_series_data, kpi_lookup, account_lookup):
        """Aggregate monthly revenue data from time-series records"""
        monthly_data = {}
        
        # Group by month and year
        for ts in time_series_data:
            kpi = kpi_lookup.get(ts.kpi_id)
            account = account_lookup.get(ts.account_id)
            
            if not kpi or not account:
                continue
                
            # Look for revenue-related KPIs
            if 'revenue' in kpi.kpi_parameter.lower() or 'revenue' in kpi.category.lower():
                month_year = (ts.month, ts.year)
                
                if month_year not in monthly_data:
                    monthly_data[month_year] = {
                        'total_revenue': 0,
                        'account_revenues': {},
                        'account_count': 0
                    }
                
                # Add revenue (assuming value is in thousands or actual amount)
                revenue_value = float(ts.value) if ts.value else 0
                monthly_data[month_year]['total_revenue'] += revenue_value
                
                if ts.account_id not in monthly_data[month_year]['account_revenues']:
                    monthly_data[month_year]['account_revenues'][ts.account_id] = {
                        'account_name': account.account_name,
                        'revenue': 0
                    }
                    monthly_data[month_year]['account_count'] += 1
                
                monthly_data[month_year]['account_revenues'][ts.account_id]['revenue'] += revenue_value
        
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
                    'revenue': acc_data['revenue']
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
        
        text = f"""
        Monthly Revenue Report: {month_name} {year}
        Total Revenue: ${total_revenue:,.2f}
        Active Accounts: {account_count}
        Top Revenue Accounts:
        """
        
        for i, acc in enumerate(top_accounts, 1):
            text += f"        {i}. {acc['account_name']}: ${acc['revenue']:,.2f}\n"
        
        text += f"""
        This month showed revenue performance across {account_count} active accounts.
        The top performing account was {top_accounts[0]['account_name'] if top_accounts else 'N/A'} with ${top_accounts[0]['revenue']:,.2f} if top_accounts else 0.
        """
        
        return text.strip()
    
    def _create_kpi_text(self, kpi: KPI, account: Account = None):
        """Create rich text representation for KPI data"""
        text = f"""
        KPI: {kpi.kpi_parameter}
        Value: {kpi.data}
        Category: {kpi.category}
        """
        
        if account:
            text += f"""
        Account: {account.account_name} (${account.revenue:,.2f} revenue)
        Industry: {account.industry}
        Region: {account.region}
        """
        
        return text.strip()
    
    def _create_account_text(self, account: Account):
        """Create rich text representation for account data"""
        return f"""
        Account: {account.account_name}
        Revenue: ${account.revenue:,.2f}
        Industry: {account.industry}
        Region: {account.region}
        Status: active
        """.strip()
    
    def query(self, query: str, query_type: str = "general", top_k: int = None) -> Dict[str, Any]:
        """Query the knowledge base with temporal awareness"""
        if not self.customer_id:
            return {"error": "Knowledge base not built for this customer"}
        
        if top_k is None:
            top_k = self.top_k
        
        # Generate query embedding
        query_embedding = self._get_embedding_model().encode([query])[0].tolist()
        
        # Search in Qdrant
        try:
            search_results = self._get_qdrant_client().search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="customer_id",
                            match=MatchValue(value=self.customer_id)
                        )
                    ]
                )
            )
            
            # Filter by similarity threshold
            relevant_results = [
                {
                    "text": result.payload.get('type', 'unknown'),
                    "similarity": result.score,
                    "metadata": result.payload
                }
                for result in search_results
                if result.score >= self.similarity_threshold
            ]
            
            # Generate AI response
            ai_response = self._generate_ai_response(query, relevant_results, query_type)
            
            return {
                "query": query,
                "query_type": query_type,
                "customer_id": self.customer_id,
                "results_count": len(relevant_results),
                "similarity_threshold": self.similarity_threshold,
                "response": ai_response,
                "relevant_results": relevant_results
            }
            
        except Exception as e:
            return {"error": f"Query failed: {str(e)}"}
    
    def _generate_ai_response(self, query: str, results: List[Dict], query_type: str) -> str:
        """Generate AI response using OpenAI GPT-4 with temporal awareness"""
        try:
            # Prepare context from results
            context = self._prepare_context(results)
            
            # Create temporal-aware prompt
            prompt = f"""
            You are an expert business analyst specializing in KPI analysis and revenue tracking.
            
            Query: {query}
            
            Available Data Context:
            {context}
            
            Instructions:
            1. If the query asks for monthly or temporal data, focus on the temporal_revenue results
            2. Provide specific monthly breakdowns when available
            3. Include revenue trends and patterns across months
            4. Highlight top-performing accounts for each time period
            5. Give actionable insights based on the temporal data
            
            Please provide a comprehensive analysis that directly addresses the user's query.
            """
            
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert business analyst with access to detailed KPI and revenue data."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"I apologize, but I encountered an error generating the response: {str(e)}"
    
    def _prepare_context(self, results: List[Dict]) -> str:
        """Prepare context from search results with temporal focus"""
        context_parts = []
        
        # Group results by type
        temporal_results = [r for r in results if r['metadata'].get('type') == 'temporal_revenue']
        kpi_results = [r for r in results if r['metadata'].get('type') == 'kpi']
        account_results = [r for r in results if r['metadata'].get('type') == 'account']
        
        # Add temporal data first (most relevant for monthly queries)
        if temporal_results:
            context_parts.append("TEMPORAL REVENUE DATA:")
            for result in temporal_results:
                metadata = result['metadata']
                context_parts.append(f"Month: {metadata.get('month_year', 'Unknown')}")
                context_parts.append(f"Total Revenue: ${metadata.get('total_revenue', 0):,.2f}")
                context_parts.append(f"Active Accounts: {metadata.get('account_count', 0)}")
                
                top_accounts = metadata.get('top_accounts', [])
                if top_accounts:
                    context_parts.append("Top Revenue Accounts:")
                    for acc in top_accounts:
                        context_parts.append(f"  - {acc['account_name']}: ${acc['revenue']:,.2f}")
                context_parts.append("")
        
        # Add KPI data
        if kpi_results:
            context_parts.append("KPI DATA:")
            for result in kpi_results[:5]:  # Limit to top 5
                metadata = result['metadata']
                context_parts.append(f"KPI: {metadata.get('kpi_parameter', 'Unknown')}")
                context_parts.append(f"Value: {metadata.get('data', 'Unknown')}")
                context_parts.append(f"Account: {metadata.get('account_name', 'Unknown')}")
                context_parts.append("")
        
        # Add account data
        if account_results:
            context_parts.append("ACCOUNT DATA:")
            for result in account_results[:5]:  # Limit to top 5
                metadata = result['metadata']
                context_parts.append(f"Account: {metadata.get('account_name', 'Unknown')}")
                context_parts.append(f"Revenue: ${metadata.get('revenue', 0):,.2f}")
                context_parts.append(f"Industry: {metadata.get('industry', 'Unknown')}")
                context_parts.append("")
        
        return "\n".join(context_parts)

# Global instance
temporal_rag_system = EnhancedRAGTemporalSystem()
