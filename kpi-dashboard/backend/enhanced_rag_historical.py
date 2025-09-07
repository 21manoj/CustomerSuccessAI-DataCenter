#!/usr/bin/env python3
"""
Enhanced RAG System with Historical Data and Temporal Analysis
Includes time-series data, trends, and historical context for comprehensive analysis
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import openai
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from models import db, KPI, Account, KPIUpload, HealthTrend

# Load environment variables
load_dotenv()

class EnhancedRAGHistoricalSystem:
    def __init__(self):
        """Initialize the enhanced RAG system with historical data capabilities"""
        # Initialize OpenAI client
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dimension = 384
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            host=os.getenv('QDRANT_HOST', 'localhost'),
            port=int(os.getenv('QDRANT_PORT', 6333))
        )
        
        # Configuration
        self.collection_name = os.getenv('QDRANT_COLLECTION', 'kpi_dashboard_historical')
        self.top_k = int(os.getenv('RAG_TOP_K', 15))  # Increased for historical data
        self.similarity_threshold = float(os.getenv('RAG_SIMILARITY_THRESHOLD', 0.3))
        self.customer_id = None
        
        # Ensure collection exists
        self._ensure_collection_exists()
        
    def _ensure_collection_exists(self):
        """Ensure Qdrant collection exists with proper configuration"""
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                print(f"🔧 Creating historical Qdrant collection: {self.collection_name}")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ Historical collection {self.collection_name} created successfully")
            else:
                print(f"✅ Historical collection {self.collection_name} already exists")
                
        except Exception as e:
            print(f"❌ Error ensuring collection exists: {str(e)}")
            # Fallback to local file-based storage
            self.qdrant_client = QdrantClient(path="./qdrant_historical_storage")
            self._ensure_collection_exists()
    
    def build_historical_knowledge_base(self, customer_id: int):
        """Build comprehensive knowledge base with historical data"""
        print(f"🔍 Building historical knowledge base for customer {customer_id}...")
        
        self.customer_id = customer_id
        
        # Get all KPIs with temporal data
        kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).all()
        
        # Get all accounts
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        account_lookup = {acc.account_id: acc for acc in accounts}
        
        # Get health trends
        health_trends = HealthTrend.query.filter_by(customer_id=customer_id).all()
        
        # Prepare historical data
        historical_data = []
        trend_data = []
        
        # Process KPI historical data
        kpi_temporal = self._process_kpi_temporal_data(kpis, account_lookup)
        historical_data.extend(kpi_temporal)
        
        # Process health trends
        trend_records = self._process_health_trends(health_trends)
        trend_data.extend(trend_records)
        
        # Process account data
        account_data = self._process_account_data(accounts)
        historical_data.extend(account_data)
        
        # Build Qdrant index
        self._build_historical_index(historical_data, trend_data)
        
        print(f"✅ Historical knowledge base built with {len(historical_data)} records and {len(trend_data)} trends")
        
    def _process_kpi_temporal_data(self, kpis: List[KPI], account_lookup: Dict) -> List[Dict]:
        """Process KPI data with temporal information"""
        temporal_data = []
        
        # Group KPIs by parameter to analyze trends
        kpi_groups = {}
        for kpi in kpis:
            account = account_lookup.get(kpi.account_id)
            if kpi.kpi_parameter not in kpi_groups:
                kpi_groups[kpi.kpi_parameter] = []
            kpi_groups[kpi.kpi_parameter].append((kpi, account))
        
        # Process each KPI group for temporal analysis
        for kpi_param, kpi_list in kpi_groups.items():
            # Get upload dates for sorting
            kpi_with_dates = []
            for kpi, account in kpi_list:
                upload = KPIUpload.query.get(kpi.upload_id)
                if upload:
                    kpi_with_dates.append((kpi, account, upload.uploaded_at))
            
            # Sort by upload date
            kpi_with_dates.sort(key=lambda x: x[2])
            
            # Calculate trends
            values = []
            dates = []
            for kpi, account, upload_date in kpi_with_dates:
                try:
                    # Parse numeric values
                    value = self._parse_kpi_value(kpi.data)
                    if value is not None:
                        values.append(value)
                        dates.append(upload_date)
                except:
                    continue
            
            if len(values) > 1:
                # Calculate trend metrics
                trend_direction = self._calculate_trend_direction(values)
                trend_strength = self._calculate_trend_strength(values)
                volatility = self._calculate_volatility(values)
                
                # Create temporal text representation
                temporal_text = self._create_temporal_kpi_text(
                    kpi_param, values, dates, trend_direction, trend_strength, volatility, kpi_list[0][1]
                )
                
                # Generate embedding
                embedding = self.embedding_model.encode([temporal_text])[0].tolist()
                
                temporal_data.append({
                    'type': 'kpi_temporal',
                    'kpi_parameter': kpi_param,
                    'account_id': kpi_list[0][0].account_id,
                    'account_name': kpi_list[0][1].account_name if kpi_list[0][1] else 'Unknown',
                    'revenue': float(kpi_list[0][1].revenue) if kpi_list[0][1] else 0,
                    'industry': kpi_list[0][1].industry if kpi_list[0][1] else 'Unknown',
                    'region': kpi_list[0][1].region if kpi_list[0][1] else 'Unknown',
                    'category': kpi_list[0][0].category,
                    'current_value': values[-1] if values else 0,
                    'previous_value': values[-2] if len(values) > 1 else values[-1] if values else 0,
                    'trend_direction': trend_direction,
                    'trend_strength': trend_strength,
                    'volatility': volatility,
                    'data_points': len(values),
                    'date_range': f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}" if dates else "N/A",
                    'text': temporal_text,
                    'embedding': embedding
                })
        
        return temporal_data
    
    def _process_health_trends(self, health_trends: List[HealthTrend]) -> List[Dict]:
        """Process health trend data"""
        trend_data = []
        
        for trend in health_trends:
            trend_text = f"""
            Health Trend Analysis - {trend.year}-{trend.month:02d}
            Overall Health Score: {trend.overall_health_score}
            Business Outcomes Score: {trend.business_outcomes_score}
            Customer Sentiment Score: {trend.customer_sentiment_score}
            Product Usage Score: {trend.product_usage_score}
            Relationship Strength Score: {trend.relationship_strength_score}
            Support Score: {trend.support_score}
            Total KPIs: {trend.total_kpis}
            Valid KPIs: {trend.valid_kpis}
            """
            
            embedding = self.embedding_model.encode([trend_text])[0].tolist()
            
            trend_data.append({
                'type': 'health_trend',
                'trend_id': trend.trend_id,
                'year': trend.year,
                'month': trend.month,
                'overall_health_score': trend.overall_health_score,
                'business_outcomes_score': trend.business_outcomes_score,
                'customer_sentiment_score': trend.customer_sentiment_score,
                'product_usage_score': trend.product_usage_score,
                'relationship_strength_score': trend.relationship_strength_score,
                'support_score': trend.support_score,
                'total_kpis': trend.total_kpis,
                'valid_kpis': trend.valid_kpis,
                'text': trend_text,
                'embedding': embedding
            })
        
        return trend_data
    
    def _process_account_data(self, accounts: List[Account]) -> List[Dict]:
        """Process account data with historical context"""
        account_data = []
        
        for account in accounts:
            account_text = f"""
            Account: {account.account_name}
            Revenue: ${account.revenue:,.0f}
            Industry: {account.industry}
            Region: {account.region}
            Status: {account.account_status}
            Historical Performance: This account has been tracked over time with multiple KPI measurements
            """
            
            embedding = self.embedding_model.encode([account_text])[0].tolist()
            
            account_data.append({
                'type': 'account',
                'account_id': account.account_id,
                'account_name': account.account_name,
                'revenue': float(account.revenue),
                'industry': account.industry,
                'region': account.region,
                'account_status': account.account_status,
                'text': account_text,
                'embedding': embedding
            })
        
        return account_data
    
    def _parse_kpi_value(self, data: str) -> Optional[float]:
        """Parse KPI value to numeric format"""
        if not data:
            return None
        
        # Remove common suffixes and convert to float
        data_clean = str(data).replace('%', '').replace(',', '').strip()
        
        # Handle time values (hours, days, etc.)
        if 'hour' in data_clean.lower():
            try:
                return float(data_clean.split()[0])
            except:
                return None
        elif 'day' in data_clean.lower():
            try:
                return float(data_clean.split()[0]) * 24  # Convert days to hours
            except:
                return None
        
        try:
            return float(data_clean)
        except:
            return None
    
    def _calculate_trend_direction(self, values: List[float]) -> str:
        """Calculate trend direction (up, down, stable)"""
        if len(values) < 2:
            return "stable"
        
        # Simple linear trend
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        change = (second_avg - first_avg) / first_avg if first_avg != 0 else 0
        
        if change > 0.05:
            return "increasing"
        elif change < -0.05:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_trend_strength(self, values: List[float]) -> float:
        """Calculate trend strength (0-1)"""
        if len(values) < 2:
            return 0.0
        
        # Calculate correlation with time
        x = list(range(len(values)))
        y = values
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        sum_y2 = sum(y[i] ** 2 for i in range(n))
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        correlation = numerator / denominator
        return abs(correlation)
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (coefficient of variation)"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0
        
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        return std_dev / mean
    
    def _create_temporal_kpi_text(self, kpi_param: str, values: List[float], dates: List[datetime], 
                                 trend_direction: str, trend_strength: float, volatility: float, 
                                 account: Optional[Account]) -> str:
        """Create rich text representation with temporal context"""
        account_info = f"Account: {account.account_name} (${account.revenue:,.0f})" if account else "Account: Unknown"
        
        return f"""
        KPI: {kpi_param}
        {account_info}
        Industry: {account.industry if account else 'Unknown'}
        Region: {account.region if account else 'Unknown'}
        Current Value: {values[-1] if values else 'N/A'}
        Previous Value: {values[-2] if len(values) > 1 else 'N/A'}
        Trend Direction: {trend_direction}
        Trend Strength: {trend_strength:.2f}
        Volatility: {volatility:.2f}
        Data Points: {len(values)}
        Date Range: {dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')} if dates else 'N/A'
        Historical Analysis: This KPI shows {trend_direction} trend with {trend_strength:.1%} strength and {volatility:.1%} volatility over {len(values)} measurements
        """
    
    def _build_historical_index(self, historical_data: List[Dict], trend_data: List[Dict]):
        """Build Qdrant index with historical data"""
        if not historical_data and not trend_data:
            return
            
        points = []
        point_id = 0
        
        # Add historical data points
        for record in historical_data:
            point = PointStruct(
                id=point_id,
                vector=record['embedding'],
                payload={
                    'type': record['type'],
                    'customer_id': self.customer_id,
                    'kpi_parameter': record.get('kpi_parameter'),
                    'account_id': record.get('account_id'),
                    'account_name': record.get('account_name'),
                    'revenue': record.get('revenue'),
                    'industry': record.get('industry'),
                    'region': record.get('region'),
                    'category': record.get('category'),
                    'current_value': record.get('current_value'),
                    'previous_value': record.get('previous_value'),
                    'trend_direction': record.get('trend_direction'),
                    'trend_strength': record.get('trend_strength'),
                    'volatility': record.get('volatility'),
                    'data_points': record.get('data_points'),
                    'date_range': record.get('date_range'),
                    'text': record['text']
                }
            )
            points.append(point)
            point_id += 1
        
        # Add trend data points
        for record in trend_data:
            point = PointStruct(
                id=point_id,
                vector=record['embedding'],
                payload={
                    'type': record['type'],
                    'customer_id': self.customer_id,
                    'trend_id': record['trend_id'],
                    'year': record['year'],
                    'month': record['month'],
                    'overall_health_score': record['overall_health_score'],
                    'business_outcomes_score': record['business_outcomes_score'],
                    'customer_sentiment_score': record['customer_sentiment_score'],
                    'product_usage_score': record['product_usage_score'],
                    'relationship_strength_score': record['relationship_strength_score'],
                    'support_score': record['support_score'],
                    'total_kpis': record['total_kpis'],
                    'valid_kpis': record['valid_kpis'],
                    'text': record['text']
                }
            )
            points.append(point)
            point_id += 1
        
        # Upload points to Qdrant
        try:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            print(f"✅ Uploaded {len(points)} historical vectors to Qdrant collection")
        except Exception as e:
            print(f"❌ Error uploading to Qdrant: {str(e)}")
            raise
    
    def query_historical(self, query_text: str, query_type: str = 'general') -> Dict[str, Any]:
        """Query the historical RAG system"""
        if not self.customer_id:
            return {'error': 'Historical knowledge base not built for this customer'}
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query_text])[0].tolist()
        
        # Search Qdrant with customer filter
        try:
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="customer_id",
                            match=MatchValue(value=self.customer_id)
                        )
                    ]
                ),
                limit=self.top_k,
                with_payload=True
            )
            
            # Filter by similarity threshold
            relevant_results = []
            for result in search_results:
                if result.score >= self.similarity_threshold:
                    relevant_results.append({
                        'similarity': float(result.score),
                        'text': result.payload.get('text', ''),
                        'metadata': result.payload
                    })
            
            # Generate response using OpenAI
            response = self._generate_historical_response(query_text, relevant_results, query_type)
            
            return {
                'query': query_text,
                'query_type': query_type,
                'customer_id': self.customer_id,
                'results_count': len(relevant_results),
                'similarity_threshold': self.similarity_threshold,
                'response': response,
                'relevant_results': relevant_results[:5]
            }
            
        except Exception as e:
            return {'error': f'Historical query failed: {str(e)}'}
    
    def _generate_historical_response(self, query: str, results: List[Dict], query_type: str) -> str:
        """Generate response with historical context using OpenAI"""
        if not results:
            return "I couldn't find relevant historical information to answer your query."
        
        # Prepare context from results
        context = self._prepare_historical_context(results)
        
        # Create system prompt for historical analysis
        if query_type == 'trend_analysis':
            system_prompt = """You are a business analyst specializing in historical trend analysis. 
            Analyze the provided historical KPI and trend data to identify patterns, trends, and insights over time.
            Focus on trend directions, volatility, seasonal patterns, and predictive insights."""
        elif query_type == 'temporal_analysis':
            system_prompt = """You are a data scientist specializing in temporal analysis. 
            Analyze time-series data to identify patterns, anomalies, and trends.
            Focus on temporal correlations, seasonality, and time-based insights."""
        else:
            system_prompt = """You are a business intelligence analyst with expertise in historical data analysis. 
            Analyze the provided historical data to answer questions about trends, patterns, and temporal insights.
            Provide comprehensive analysis with historical context and future predictions where appropriate."""
        
        user_prompt = f"""
        Query: {query}
        
        Historical Context (Customer ID: {self.customer_id}):
        {context}
        
        Please provide a comprehensive historical analysis based on the available data.
        Include trend analysis, temporal patterns, and historical context where relevant.
        Format your response with clear insights and actionable recommendations.
        """
        
        try:
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2500,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating historical response: {str(e)}"
    
    def _prepare_historical_context(self, results: List[Dict]) -> str:
        """Prepare context from historical search results"""
        context_parts = []
        
        for i, result in enumerate(results[:10]):
            metadata = result['metadata']
            text = result['text']
            similarity = result['similarity']
            
            if metadata['type'] == 'kpi_temporal':
                context_parts.append(f"""
                Historical KPI {i+1} (Similarity: {similarity:.3f}):
                {text}
                """)
            elif metadata['type'] == 'health_trend':
                context_parts.append(f"""
                Health Trend {i+1} (Similarity: {similarity:.3f}):
                {text}
                """)
            else:
                context_parts.append(f"""
                Data Point {i+1} (Similarity: {similarity:.3f}):
                {text}
                """)
        
        return "\n".join(context_parts)

# Global instances for each customer (multi-tenant support)
historical_rag_systems = {}

def get_historical_rag_system(customer_id: int) -> EnhancedRAGHistoricalSystem:
    """Get or create historical RAG system instance for specific customer"""
    if customer_id not in historical_rag_systems:
        historical_rag_systems[customer_id] = EnhancedRAGHistoricalSystem()
    return historical_rag_systems[customer_id]
