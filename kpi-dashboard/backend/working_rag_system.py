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
from models import db, KPI, Account, KPIUpload

class WorkingRAGSystem:
    def __init__(self):
        """Initialize working RAG system"""
        # Initialize OpenAI client
        self.openai_api_key = "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"
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # In-memory storage
        self.vectors = []
        self.data = []
        self.customer_id = None
        
    def build_knowledge_base(self, customer_id: int):
        """Build knowledge base for customer"""
        print(f"🔍 Building working knowledge base for customer {customer_id}...")
        
        self.customer_id = customer_id
        self.vectors = []
        self.data = []
        
        # Fetch KPIs for the customer
        kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).all()
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        # Create account lookup
        account_lookup = {acc.account_id: acc for acc in accounts}
        
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
                
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.3
                )
                
                ai_response = response.choices[0].message.content
                
            except Exception as e:
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
