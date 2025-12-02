#!/usr/bin/env python3
"""
Enhanced RAG System with OpenAI GPT-4 and FAISS
Provides advanced KPI and account analysis capabilities with multi-tenant support
Includes query caching to reduce API costs
"""

import os
import json
import numpy as np
import faiss
from typing import List, Dict, Any, Optional
from datetime import datetime
import openai
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from models import db, KPI, Account, KPIUpload, CustomerConfig, PlaybookReport
from query_cache import get_query_cache, cache_query_result, get_cached_query_result

# Load environment variables
load_dotenv()

class EnhancedRAGSystemOpenAI:
    def __init__(self):
        """Initialize the enhanced RAG system with OpenAI and FAISS"""
        # Initialize OpenAI client
        # API key will be retrieved per-request from customer-specific storage
        # Don't set global openai.api_key here - use get_openai_api_key(customer_id) instead
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.faiss_index = None
        self.kpi_data = []
        self.account_data = []
        self.customer_id = None
        
        # Configuration
        self.index_path = os.getenv('FAISS_INDEX_PATH', './faiss_index')
        self.dimension = int(os.getenv('FAISS_DIMENSION', 384))  # all-MiniLM-L6-v2 generates 384-dimensional embeddings
        self.top_k = int(os.getenv('RAG_TOP_K', 10))
        self.similarity_threshold = float(os.getenv('RAG_SIMILARITY_THRESHOLD', 0.3))  # Lower threshold for better recall
        
    def build_knowledge_base(self, customer_id: int):
        """Build FAISS index from KPI and account data for specific customer"""
        print(f"🔍 Building enhanced knowledge base for customer {customer_id}...")
        
        # Store customer ID for this instance
        self.customer_id = customer_id
        
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
        
        print(f"✅ Knowledge base built for customer {customer_id} with {len(self.kpi_data)} KPIs and {len(self.account_data)} accounts")
        
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
        
        print(f"✅ FAISS index built with {len(all_embeddings)} vectors for customer {self.customer_id}")
    
    def query(self, query_text: str, query_type: str = 'general', conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Query the enhanced RAG system using OpenAI with caching"""
        if not self.faiss_index:
            return {'error': 'Knowledge base not built'}
        
        if conversation_history is None:
            conversation_history = []
        
        # Check cache first
        cached_result = get_cached_query_result(self.customer_id, query_text, query_type)
        if cached_result:
            cached_result['cache_hit'] = True
            cached_result['cost'] = '$0.00'
            return cached_result
        
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
        
        # Generate response using OpenAI (expensive operation)
        response = self._generate_openai_response(query_text, relevant_results, query_type, conversation_history)
        
        # Check if playbook context was used
        account_id = self._extract_account_id_from_query(query_text)
        playbook_context = self._get_playbook_context(account_id)
        
        result = {
            'query': query_text,
            'query_type': query_type,
            'customer_id': self.customer_id,
            'results_count': len(relevant_results),
            'similarity_threshold': self.similarity_threshold,
            'response': response,
            'relevant_results': relevant_results[:5],  # Limit for response
            'cache_hit': False,
            'cost': '$0.02',
            'playbook_enhanced': bool(playbook_context),  # Track if playbook data was used
            'enhancement_source': 'playbook_reports' if playbook_context else None
        }
        
        # Cache the result for future queries
        cache_query_result(self.customer_id, query_text, result, query_type)
        
        return result
    
    def _generate_openai_response(self, query: str, results: List[Dict], query_type: str, conversation_history: List[Dict] = None) -> str:
        """Generate response using OpenAI GPT-4"""
        if not results:
            return "I couldn't find relevant information to answer your query."
        
        if conversation_history is None:
            conversation_history = []
        
        # Prepare context from results
        context = self._prepare_context(results)
        
        # Add playbook insights context
        account_id = self._extract_account_id_from_query(query)
        playbook_context = self._get_playbook_context(account_id)
        
        if playbook_context:
            context += playbook_context
        
        # Build conversation context
        conversation_context_str = ""
        if conversation_history:
            conversation_context_str = "\n\n=== CONVERSATION HISTORY ===\n"
            for i, msg in enumerate(conversation_history, 1):
                conversation_context_str += f"\nPrevious Q{i}: {msg.get('query', '')}\n"
                conversation_context_str += f"Previous A{i}: {msg.get('response', '')[:200]}...\n"
            conversation_context_str += "\n(Use this context to understand follow-up questions and maintain conversation flow)\n"
        
        # Anti-hallucination rules (applied to all prompt types)
        anti_hallucination_rules = """
        CRITICAL RULES - YOU MUST FOLLOW THESE STRICTLY:
        1. ONLY use account names, KPI values, and metrics explicitly provided in the context below
        2. NEVER invent, guess, or hallucinate account names, company names, or data not in the provided context
        3. If asked to list accounts, ONLY list exact account names from the context
        4. If you don't have specific data to answer a question, say "I don't have that specific information in the current data"
        5. Do NOT use generic industry terms like "pharmaceutical", "aerospace", "technology" unless they appear in actual account names provided
        
        REMEMBER: Only use data explicitly provided to you. Never make up account names or data points.
        """
        
        # Create system prompt based on query type
        if query_type == 'revenue_analysis':
            system_prompt = anti_hallucination_rules + """
            You are a business analyst specializing in KPI and revenue analysis. 
            Analyze the provided KPI and account data to answer questions about revenue, growth, and business performance.
            Focus on revenue drivers, account performance, and business insights. Provide specific metrics and actionable recommendations."""
        elif query_type == 'account_analysis':
            system_prompt = anti_hallucination_rules + """
            You are a customer success analyst. 
            Analyze account performance, engagement, and health scores to provide insights about customer relationships and risk assessment.
            Focus on account health, engagement patterns, and retention strategies."""
        elif query_type == 'kpi_analysis':
            system_prompt = anti_hallucination_rules + """
            You are a KPI specialist. 
            Analyze KPI performance, trends, and impact levels to provide insights about business metrics and recommendations.
            Focus on performance optimization and strategic insights."""
        else:
            system_prompt = anti_hallucination_rules + """
            You are a business intelligence analyst with access to both real-time KPI data and historical playbook execution insights. 
            Analyze the provided data to answer questions about business performance, KPIs, and customer insights.
            When playbook insights are available, use them to provide evidence-based recommendations with specific outcomes, metrics, and action plans.
            Cite specific playbook results when relevant (e.g., 'According to the VoC Sprint completed on [date]...').
            Provide comprehensive analysis with specific recommendations."""
        
        # Add system playbook knowledge
        from playbook_knowledge import format_playbook_knowledge_for_rag, get_playbook_for_goal
        
        playbook_knowledge = ""
        # Check if query is about playbooks or improvement
        if any(keyword in query.lower() for keyword in ['playbook', 'improve', 'increase', 'reduce', 'better']):
            playbook_knowledge = format_playbook_knowledge_for_rag()
        
        playbook_instruction = ""
        if playbook_knowledge:
            playbook_instruction = "\nIMPORTANT: When recommending playbooks, ONLY suggest the 5 system-defined playbooks listed above. Do NOT make up generic playbook names."
        
        playbook_context_instruction = ""
        if playbook_context:
            playbook_context_instruction = "When referencing playbook insights, cite specific outcomes with metrics and dates."
        
        user_prompt = f"""
        {conversation_context_str}
        
        Current Query: {query}
        
        Context from knowledge base (Customer ID: {self.customer_id}):
        {context}
        
        {playbook_knowledge}
        
        Please provide a comprehensive analysis and answer to the query based on the available data and conversation context.
        {playbook_context_instruction}
        {playbook_instruction}
        Include specific insights, recommendations, and relevant metrics where applicable.
        Format your response in a clear, actionable manner with concrete examples where available.
        """
        
        try:
            # Get customer-specific API key (encrypted from database or env fallback)
            from openai_key_utils import get_openai_api_key
            api_key = get_openai_api_key(self.customer_id)
            if not api_key:
                return "OpenAI API key is not configured. Please configure your OpenAI API key in Settings > OpenAI Key Settings."
            
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
        except openai.AuthenticationError as e:
            return "OpenAI API key is invalid or expired. Please update your API key in Settings > OpenAI Key Settings."
        except openai.APIError as e:
            return f"OpenAI API error: {str(e)}. Please check your API key and account status."
        except Exception as e:
            error_msg = str(e)
            if 'API key' in error_msg or '401' in error_msg or 'authentication' in error_msg.lower():
                return "OpenAI API key is missing or invalid. Please configure your API key in Settings > OpenAI Key Settings."
            return f"Error generating response: {error_msg}"
    
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
    
    def _get_playbook_context(self, account_id: Optional[int] = None) -> str:
        """Get recent playbook insights for query context enrichment"""
        try:
            query = PlaybookReport.query.filter_by(customer_id=self.customer_id)
            
            if account_id:
                query = query.filter_by(account_id=account_id)
                print(f"🔍 Fetching playbook reports for customer {self.customer_id}, account {account_id}")
            else:
                print(f"🔍 Fetching playbook reports for customer {self.customer_id} (all accounts)")
            
            # Get last 3 reports
            reports = query.order_by(PlaybookReport.report_generated_at.desc()).limit(3).all()
            
            if not reports:
                print(f"⚠️  No playbook reports found")
                return ""
            
            print(f"✓ Found {len(reports)} playbook report(s)")
            
            context = "\n\n=== RECENT PLAYBOOK INSIGHTS ===\n"
            context += f"(Based on {len(reports)} recent playbook executions)\n"
            
            for report in reports:
                data = report.report_data
                playbook_name = data.get('playbook_name', 'Unknown Playbook')
                account_name = report.account_name or 'All Accounts'
                report_date = report.report_generated_at.strftime('%Y-%m-%d') if report.report_generated_at else 'Unknown'
                
                context += f"\n📊 {playbook_name} - {account_name} ({report_date}):\n"
                
                # Add executive summary (truncated)
                exec_summary = data.get('executive_summary', '')
                if exec_summary:
                    context += f"Summary: {exec_summary[:200]}...\n"
                
                # Add key outcomes
                outcomes = data.get('outcomes_achieved', {})
                if outcomes:
                    context += "Key Outcomes:\n"
                    count = 0
                    for outcome_key, outcome_data in outcomes.items():
                        if count >= 2:  # Limit to 2 outcomes per report
                            break
                        if isinstance(outcome_data, dict):
                            improvement = outcome_data.get('improvement', 'N/A')
                            status = outcome_data.get('status', 'Unknown')
                            context += f"  • {outcome_key}: {improvement} ({status})\n"
                            count += 1
                
                # Add top next step
                next_steps = data.get('next_steps', [])
                if next_steps:
                    context += f"Next Step: {next_steps[0]}\n"
            
            context += "\n(Use these insights to provide evidence-based recommendations)\n"
            return context
            
        except Exception as e:
            print(f"Warning: Could not fetch playbook context: {e}")
            return ""
    
    def _extract_account_id_from_query(self, query: str) -> Optional[int]:
        """Try to extract account ID or name from query for account-specific context"""
        try:
            query_lower = query.lower()
            
            # Try to find account by name in query
            accounts = Account.query.filter_by(customer_id=self.customer_id).all()
            
            # First pass: exact match
            for account in accounts:
                if account.account_name.lower() in query_lower:
                    return account.account_id
            
            # Second pass: partial match (e.g., "TechCorp" matches "TechCorp Solutions")
            # Split account names into words and check if any significant word matches
            for account in accounts:
                account_words = account.account_name.lower().split()
                for word in account_words:
                    # Only match significant words (length > 3 to avoid common words)
                    if len(word) > 3 and word in query_lower:
                        print(f"✓ Matched '{word}' from '{account.account_name}' in query")
                        return account.account_id
            
            return None
        except Exception as e:
            print(f"Warning: Could not extract account ID: {e}")
            return None
    
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

# Global instances for each customer (multi-tenant support)
rag_systems = {}

def get_rag_system(customer_id: int) -> EnhancedRAGSystemOpenAI:
    """Get or create RAG system instance for specific customer"""
    if customer_id not in rag_systems:
        rag_systems[customer_id] = EnhancedRAGSystemOpenAI()
    return rag_systems[customer_id]
