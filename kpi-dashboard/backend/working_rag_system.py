#!/usr/bin/env python3
"""
Working RAG System - Bypasses Qdrant storage issues
"""

import os
import json
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import openai
from models import db, KPI, Account, KPIUpload, DC2SKPI, User

try:
    from utils.llm_budget_controller import can_call as _budget_can_call, record_usage as _budget_record
except Exception:
    _budget_can_call = None
    _budget_record = None

class WorkingRAGSystem:
    def __init__(self):
        """Initialize working RAG system"""
        # Initialize OpenAI client
        self.openai_api_key = os.environ.get('OPENAI_API_KEY', '')
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # In-memory storage
        self.vectors = []
        self.data = []
        self.customer_id = None
        
    def build_knowledge_base(self, customer_id: int):
        """Build knowledge base for customer - supports both SaaS and DC verticals"""
        print(f"🔍 Building working knowledge base for customer {customer_id} (no VDB, pure in-memory)...")
        
        self.customer_id = customer_id
        self.vectors = []
        self.data = []
        
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
            
            # Create account lookup
            accounts = Account.query.filter(
                Account.customer_id == customer_id,
                Account.vertical == 'dc2_s'
            ).all()
            account_lookup = {acc.account_id: acc for acc in accounts}
            
            # Convert DC2SKPI to KPI-like format
            class MockKPI:
                def __init__(self, dc_kpi, account):
                    self.kpi_id = dc_kpi.kpi_id
                    self.account_id = dc_kpi.account_id
                    self.category = dc_kpi.pillar or 'Uncategorized'
                    self.kpi_parameter = dc_kpi.kpi_code or 'Unknown KPI'
                    self.data = str(dc_kpi.value) if dc_kpi.value is not None else '0'
                    self.impact_level = 'Medium'
                    self.source_review = 'DC Data Source'
                    self.measurement_frequency = 'Monthly'
                    self.upload_id = None
            
            kpis = []
            for dc_kpi in dc_kpis:
                account = account_lookup.get(dc_kpi.account_id)
                kpis.append(MockKPI(dc_kpi, account))
        else:
            # For SaaS customers, use standard KPI table
            print(f"📊 Building knowledge base for SaaS customer {customer_id}")
            kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).all()
            accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        # Create account lookup (if not already created for DC)
        if not is_dc_customer:
            account_lookup = {acc.account_id: acc for acc in accounts}
        else:
            # Account lookup already created for DC above
            pass
        
        # Process KPIs
        for kpi in kpis:
            account = account_lookup.get(kpi.account_id)
            
            # Create text representation
            kpi_text = f"""
            KPI: {kpi.kpi_parameter}
            Category: {kpi.category}
            Account: {account.account_name if account else 'Unknown'}
            Revenue: ${account.revenue:,.0f} if account else 0
            Industry: {account.industry if account else 'Unknown'}
            Region: {account.region if account else 'Unknown'}
            Value: {kpi.data}
            Impact Level: {kpi.impact_level}
            """
            
            # Generate embedding
            embedding = self.embedding_model.encode([kpi_text])[0]
            
            # Store data
            self.vectors.append(embedding)
            self.data.append({
                'type': 'kpi',
                'text': kpi_text,
                'kpi_id': kpi.kpi_id,
                'account_id': kpi.account_id,
                'account_name': account.account_name if account else 'Unknown',
                'revenue': float(account.revenue) if account else 0,
                'industry': account.industry if account else 'Unknown',
                'region': account.region if account else 'Unknown',
                'category': kpi.category,
                'kpi_parameter': kpi.kpi_parameter,
                'data': kpi.data
            })
        
        # Process accounts
        for account in accounts:
            account_text = f"""
            Account: {account.account_name}
            Revenue: ${account.revenue:,.0f}
            Industry: {account.industry}
            Region: {account.region}
            Status: {account.account_status}
            """
            
            embedding = self.embedding_model.encode([account_text])[0]
            
            self.vectors.append(embedding)
            self.data.append({
                'type': 'account',
                'text': account_text,
                'account_id': account.account_id,
                'account_name': account.account_name,
                'revenue': float(account.revenue),
                'industry': account.industry,
                'region': account.region,
                'account_status': account.account_status
            })
        
        print(f"✅ Working knowledge base built with {len(self.data)} records")
        
    def query(self, query_text: str, query_type: str = 'general') -> Dict[str, Any]:
        """Query the working RAG system"""
        if not self.customer_id or not self.vectors:
            return {'error': 'Knowledge base not built for this customer'}
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query_text])[0]
        
        # Calculate similarities
        similarities = []
        for i, vector in enumerate(self.vectors):
            similarity = np.dot(query_embedding, vector) / (np.linalg.norm(query_embedding) * np.linalg.norm(vector))
            similarities.append((i, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top results
        top_k = 10
        relevant_results = []
        for i, (idx, similarity) in enumerate(similarities[:top_k]):
            if similarity > 0.3:  # similarity threshold
                relevant_results.append({
                    'text': self.data[idx]['text'],
                    'similarity': float(similarity),
                    'metadata': {k: v for k, v in self.data[idx].items() if k != 'text'}
                })
        
        # Generate AI response
        if relevant_results:
            try:
                client = openai.OpenAI(api_key=self.openai_api_key)
                
                # Prepare context
                context = "\n\n".join([result['text'] for result in relevant_results[:5]])
                
                system_prompt = f"""
                You are an AI assistant analyzing KPI and account data for a customer success platform.
                Based on the provided data, answer the user's query with specific insights and recommendations.
                """
                
                user_prompt = f"""
                Query: {query_text}
                
                Context Data:
                {context}
                
                Please provide a comprehensive analysis and answer based on the available data.
                """
                
                _cid = getattr(self, 'customer_id', 0) or 0
                # Budget check (fail-open)
                try:
                    if _budget_can_call and not _budget_can_call(_cid, 'rag_query'):
                        ai_response = "Daily AI budget reached — please try again tomorrow."
                        return {
                            'customer_id': self.customer_id,
                            'query': query_text,
                            'query_type': query_type,
                            'results_count': len(similarities),
                            'relevant_results': relevant_results,
                            'response': ai_response,
                            'similarity_threshold': 0.3,
                            'budget_exceeded': True,
                        }
                except Exception:
                    pass

                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.3
                )

                # Record usage (fail-open)
                try:
                    if _budget_record:
                        _budget_record(_cid, 'rag_query',
                                       tokens_in=response.usage.prompt_tokens,
                                       tokens_out=response.usage.completion_tokens,
                                       model='gpt-4')
                except Exception:
                    pass

                ai_response = response.choices[0].message.content

            except Exception as e:
                try:
                    if _budget_record:
                        _budget_record(getattr(self, 'customer_id', 0) or 0, 'rag_query',
                                       0, 0, model='gpt-4', success=False, error_message=str(e)[:200])
                except Exception:
                    pass
                ai_response = f"Error generating AI response: {str(e)}"
        else:
            ai_response = "I couldn't find relevant information to answer your query."
        
        return {
            'customer_id': self.customer_id,
            'query': query_text,
            'query_type': query_type,
            'results_count': len(similarities),
            'relevant_results': relevant_results,
            'response': ai_response,
            'similarity_threshold': 0.3
        }

# Global instance
working_rag_system = WorkingRAGSystem()
