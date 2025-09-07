#!/usr/bin/env python3
"""
Enhanced RAG System using FAISS and Claude
Provides advanced KPI and account analysis capabilities
"""

import os
import json
import numpy as np
import faiss
from typing import List, Dict, Any, Optional
from datetime import datetime
import anthropic
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from models import db, KPI, Account, KPIUpload, CustomerConfig

# Load environment variables
load_dotenv()

class EnhancedRAGSystem:
    def __init__(self):
        """Initialize the enhanced RAG system with FAISS and Claude"""
        self.anthropic_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.faiss_index = None
        self.kpi_data = []
        self.account_data = []
        self.index_path = os.getenv('FAISS_INDEX_PATH', './faiss_index')
        self.dimension = int(os.getenv('FAISS_DIMENSION', 768))
        self.top_k = int(os.getenv('RAG_TOP_K', 10))
        self.similarity_threshold = float(os.getenv('RAG_SIMILARITY_THRESHOLD', 0.7))
        
    def build_knowledge_base(self, customer_id: int):
        """Build FAISS index from KPI and account data"""
        print("🔍 Building enhanced knowledge base...")
        
        # Fetch all KPIs for the customer
        kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).all()
        
        # Fetch all accounts for the customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        # Create account lookup
        account_lookup = {acc.account_id: acc for acc in accounts}
        
        # Prepare data for indexing
        self.kpi_data = []
        self.account_data = []
        
        for kpi in kpis:
            account = account_lookup.get(kpi.account_id)
            
            # Create rich text representation
            kpi_text = self._create_kpi_text(kpi, account)
            
            # Generate embedding
            embedding = self.embedding_model.encode([kpi_text])[0]
            
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
            
            self.kpi_data.append(kpi_record)
            
            # Store account data separately
            if account and account.account_id not in [a['account_id'] for a in self.account_data]:
                account_text = self._create_account_text(account)
                account_embedding = self.embedding_model.encode([account_text])[0]
                
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
                self.account_data.append(account_record)
        
        # Build FAISS index
        self._build_faiss_index()
        
        print(f"✅ Knowledge base built with {len(self.kpi_data)} KPIs and {len(self.account_data)} accounts")
        
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
    
    def _build_faiss_index(self):
        """Build FAISS index from embeddings"""
        if not self.kpi_data:
            return
            
        # Combine KPI and account embeddings
        all_embeddings = []
        all_texts = []
        all_metadata = []
        
        # Add KPI embeddings
        for kpi in self.kpi_data:
            all_embeddings.append(kpi['embedding'])
            all_texts.append(kpi['text'])
            all_metadata.append({
                'type': 'kpi',
                'kpi_id': kpi['kpi_id'],
                'account_id': kpi['account_id'],
                'account_name': kpi['account_name'],
                'revenue': kpi['revenue'],
                'industry': kpi['industry'],
                'region': kpi['region'],
                'category': kpi['category'],
                'kpi_parameter': kpi['kpi_parameter'],
                'data': kpi['data'],
                'impact_level': kpi['impact_level']
            })
        
        # Add account embeddings
        for account in self.account_data:
            all_embeddings.append(account['embedding'])
            all_texts.append(account['text'])
            all_metadata.append({
                'type': 'account',
                'account_id': account['account_id'],
                'account_name': account['account_name'],
                'revenue': account['revenue'],
                'industry': account['industry'],
                'region': account['region'],
                'account_status': account['account_status']
            })
        
        # Convert to numpy arrays
        embeddings_array = np.array(all_embeddings).astype('float32')
        
        # Create FAISS index
        self.faiss_index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
        self.faiss_index.add(embeddings_array)
        
        # Store metadata
        self.index_texts = all_texts
        self.index_metadata = all_metadata
        
        print(f"✅ FAISS index built with {len(all_embeddings)} vectors")
    
    def query(self, query_text: str, query_type: str = 'general') -> Dict[str, Any]:
        """Query the enhanced RAG system"""
        if not self.faiss_index:
            return {'error': 'Knowledge base not built'}
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query_text])[0].reshape(1, -1).astype('float32')
        
        # Search FAISS index
        similarities, indices = self.faiss_index.search(query_embedding, self.top_k)
        
        # Filter by similarity threshold
        relevant_results = []
        for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
            if similarity >= self.similarity_threshold:
                relevant_results.append({
                    'similarity': float(similarity),
                    'text': self.index_texts[idx],
                    'metadata': self.index_metadata[idx]
                })
        
        # Generate response using Claude
        response = self._generate_claude_response(query_text, relevant_results, query_type)
        
        return {
            'query': query_text,
            'query_type': query_type,
            'results_count': len(relevant_results),
            'similarity_threshold': self.similarity_threshold,
            'response': response,
            'relevant_results': relevant_results[:5]  # Limit for response
        }
    
    def _generate_claude_response(self, query: str, results: List[Dict], query_type: str) -> str:
        """Generate response using Claude"""
        if not results:
            return "I couldn't find relevant information to answer your query."
        
        # Prepare context from results
        context = self._prepare_context(results)
        
        # Create prompt based on query type
        if query_type == 'revenue_analysis':
            system_prompt = """You are a business analyst specializing in KPI and revenue analysis. 
            Analyze the provided KPI and account data to answer questions about revenue, growth, and business performance.
            Focus on revenue drivers, account performance, and business insights."""
        elif query_type == 'account_analysis':
            system_prompt = """You are a customer success analyst. 
            Analyze account performance, engagement, and health scores to provide insights about customer relationships and risk assessment."""
        elif query_type == 'kpi_analysis':
            system_prompt = """You are a KPI specialist. 
            Analyze KPI performance, trends, and impact levels to provide insights about business metrics and recommendations."""
        else:
            system_prompt = """You are a business intelligence analyst. 
            Analyze the provided data to answer questions about business performance, KPIs, and customer insights."""
        
        user_prompt = f"""
        Query: {query}
        
        Context from knowledge base:
        {context}
        
        Please provide a comprehensive analysis and answer to the query based on the available data.
        Include specific insights, recommendations, and relevant metrics where applicable.
        """
        
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return response.content[0].text
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
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
        """Analyze revenue drivers across accounts"""
        if not self.kpi_data:
            return {'error': 'No data available'}
        
        # Filter business outcomes KPIs
        business_kpis = [kpi for kpi in self.kpi_data if 'Business Outcomes' in kpi['category']]
        
        # Analyze revenue-related metrics
        revenue_analysis = {
            'total_revenue': sum(kpi['revenue'] for kpi in self.kpi_data if kpi['revenue'] > 0),
            'top_accounts': sorted(self.account_data, key=lambda x: x['revenue'], reverse=True)[:5],
            'revenue_by_industry': {},
            'revenue_by_region': {},
            'business_kpis': business_kpis
        }
        
        # Group by industry and region
        for account in self.account_data:
            industry = account['industry']
            region = account['region']
            revenue = account['revenue']
            
            if industry not in revenue_analysis['revenue_by_industry']:
                revenue_analysis['revenue_by_industry'][industry] = 0
            if region not in revenue_analysis['revenue_by_region']:
                revenue_analysis['revenue_by_region'][region] = 0
            
            revenue_analysis['revenue_by_industry'][industry] += revenue
            revenue_analysis['revenue_by_region'][region] += revenue
        
        return revenue_analysis
    
    def find_at_risk_accounts(self, customer_id: int) -> Dict[str, Any]:
        """Find accounts at risk of churn"""
        if not self.kpi_data:
            return {'error': 'No data available'}
        
        # Look for risk indicators
        risk_indicators = []
        
        for kpi in self.kpi_data:
            if any(keyword in kpi['kpi_parameter'].lower() for keyword in ['churn', 'risk', 'flag', 'satisfaction']):
                try:
                    value = float(str(kpi['data']).replace('%', '').replace(',', ''))
                    if value < 50:  # Low scores indicate risk
                        risk_indicators.append({
                            'account_name': kpi['account_name'],
                            'kpi_parameter': kpi['kpi_parameter'],
                            'value': kpi['data'],
                            'risk_level': 'High' if value < 30 else 'Medium'
                        })
                except:
                    pass
        
        return {
            'at_risk_accounts': risk_indicators,
            'total_accounts': len(self.account_data),
            'risk_percentage': len(risk_indicators) / len(self.account_data) * 100 if self.account_data else 0
        }

# Global instance
enhanced_rag_system = EnhancedRAGSystem() 