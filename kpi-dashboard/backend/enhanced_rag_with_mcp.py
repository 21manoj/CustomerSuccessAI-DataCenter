"""
Enhanced RAG System with MCP Integration
Extends existing RAG to include real-time data from external systems
Feature-toggled for safe rollback
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from enhanced_rag_openai import EnhancedRAGSystemOpenAI
from mcp_integration import MCPIntegration, get_mcp_config
from models import Account

logger = logging.getLogger(__name__)


class EnhancedRAGWithMCP(EnhancedRAGSystemOpenAI):
    """
    MCP-Enhanced RAG System
    Extends existing RAG with real-time external system data
    Falls back gracefully if MCP unavailable
    """
    
    def __init__(self, customer_id: int):
        # Initialize parent RAG system (existing functionality)
        super().__init__()  # Parent takes no args
        
        # Store customer_id for MCP
        self.customer_id = customer_id
        
        # MCP integration
        self.mcp = MCPIntegration(customer_id)
        self.mcp_enabled = False
        self.mcp_systems = get_mcp_config(customer_id)
        
        logger.info(f"MCP-Enhanced RAG initialized for customer {customer_id}. MCP systems: {self.mcp_systems}")
    
    async def init_mcp(self):
        """Initialize MCP connections (async)"""
        enabled_systems = [
            system for system, enabled in self.mcp_systems.items()
            if enabled
        ]
        
        if enabled_systems:
            success = await self.mcp.connect_all(enabled_systems)
            self.mcp_enabled = success
            logger.info(f"MCP initialized: {success}, systems: {enabled_systems}")
        else:
            logger.info("No MCP systems enabled")
    
    def query_sync(self, query_text: str, query_type: str = 'general', conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Synchronous wrapper for async query
        Maintains compatibility with existing code
        """
        if conversation_history is None:
            conversation_history = []
        try:
            # Run async query in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.query_async(query_text, query_type))
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Error in async query: {e}")
            # Fallback to original RAG
            return super().query(query_text, query_type)
    
    async def query_async(self, query_text: str, query_type: str = 'general') -> Dict[str, Any]:
        """
        Async query with optional MCP enhancement
        """
        # ============================================
        # STEP 1: Original RAG Query (Always)
        # ============================================
        local_result = super().query(query_text, query_type)
        
        # ============================================
        # STEP 2: MCP Enhancement (Conditional)
        # ============================================
        mcp_context = {}
        
        # Check if any MCP systems are enabled
        if any(self.mcp_systems.values()):
            try:
                # Initialize MCP if not already done
                if not self.mcp.connected:
                    await self.init_mcp()
                
                # Extract account from query
                account_id = self._extract_account_id_from_query(query_text)
                
                if account_id:
                    # Fetch data from enabled systems
                    enabled_systems = [
                        system for system, enabled in self.mcp_systems.items()
                        if enabled
                    ]
                    
                    if enabled_systems:
                        mcp_context = await self.mcp.fetch_account_data(
                            account_id,
                            enabled_systems
                        )
                        logger.info(f"Fetched MCP data from {len(mcp_context)} systems")
                
            except Exception as e:
                logger.error(f"MCP fetch failed, using local data only: {e}")
                mcp_context = {}
        
        # ============================================
        # STEP 3: Combine Contexts
        # ============================================
        if mcp_context:
            # Enhance the response with MCP data
            enhanced_response = self._generate_enhanced_response(
                query_text,
                local_result,
                mcp_context,
                query_type
            )
            
            return {
                **local_result,
                'response': enhanced_response,
                'mcp_enhanced': True,
                'mcp_sources': list(mcp_context.keys()),
                'external_data': mcp_context
            }
        else:
            # No MCP data, return original result
            return {
                **local_result,
                'mcp_enhanced': False
            }
    
    def _generate_enhanced_response(
        self,
        query: str,
        local_result: Dict,
        mcp_context: Dict,
        query_type: str
    ) -> str:
        """
        Generate enhanced response using both local and MCP data
        """
        import openai
        
        # Build comprehensive context
        context_parts = []
        
        # Local database context
        context_parts.append("=== LOCAL KPI DATABASE ===")
        if local_result.get('relevant_results'):
            for result in local_result['relevant_results'][:5]:
                context_parts.append(f"- {result.get('text', '')}")
        
        # Playbook context
        account_id = self._extract_account_id_from_query(query)
        playbook_context = self._get_playbook_context(account_id)
        if playbook_context:
            context_parts.append(playbook_context)
        
        # MCP external system context
        if 'salesforce' in mcp_context:
            context_parts.append("\n=== SALESFORCE CRM (Real-Time) ===")
            sf_data = mcp_context['salesforce']
            if 'account' in sf_data:
                acc = sf_data['account']
                context_parts.append(f"Account: {acc.get('Name')}")
                context_parts.append(f"ARR: ${acc.get('ARR__c', 0):,.0f}")
                context_parts.append(f"Industry: {acc.get('Industry')}")
            if 'opportunity' in sf_data:
                opp = sf_data['opportunity']
                context_parts.append(f"Renewal Stage: {opp.get('StageName')}")
                context_parts.append(f"Close Date: {opp.get('CloseDate')}")
        
        if 'servicenow' in mcp_context:
            context_parts.append("\n=== SERVICENOW SUPPORT (Real-Time) ===")
            sn_data = mcp_context['servicenow']
            if 'tickets' in sn_data:
                tickets = sn_data['tickets']
                context_parts.append(f"Open Tickets: {len(tickets)}")
                critical = [t for t in tickets if '1-Critical' in t.get('Priority', '')]
                if critical:
                    context_parts.append(f"Critical Tickets: {len(critical)}")
        
        if 'surveys' in mcp_context:
            context_parts.append("\n=== SURVEY DATA (Real-Time) ===")
            survey_data = mcp_context['surveys']
            if 'nps' in survey_data:
                nps = survey_data['nps']
                context_parts.append(f"NPS Score: {nps.get('score')}")
                context_parts.append(f"Survey Date: {nps.get('survey_date')}")
            if 'csat' in survey_data:
                csat = survey_data['csat']
                context_parts.append(f"CSAT Score: {csat.get('score')}")
        
        combined_context = "\n".join(context_parts)
        
        # Add system playbook knowledge
        from playbook_knowledge import format_playbook_knowledge_for_rag
        
        playbook_knowledge = ""
        # Check if query is about playbooks or improvement
        if any(keyword in query.lower() for keyword in ['playbook', 'improve', 'increase', 'reduce', 'better', 'leverage']):
            playbook_knowledge = format_playbook_knowledge_for_rag()
        
        # Generate response with enhanced context
        system_prompt = f"""You are a Customer Success AI assistant with access to:
1. Historical KPI data from the customer's database
2. Real-time CRM data from Salesforce  
3. Live support ticket data from ServiceNow
4. Recent survey results and customer feedback
5. System-defined playbooks (VoC Sprint, Activation Blitz, SLA Stabilizer, Renewal Safeguard, Expansion Timing)

Provide comprehensive analysis using ALL available data sources.
Always cite which system the data came from (e.g., "According to Salesforce...", "Recent support tickets show...").
When recommending playbooks, ONLY suggest the 5 system-defined playbooks. Do NOT invent generic playbook names.
Prioritize real-time data when available."""
        
        playbook_instruction = ""
        if playbook_knowledge:
            playbook_instruction = "5. When recommending playbooks, ONLY use the 5 system playbooks listed above (VoC Sprint, Activation Blitz, SLA Stabilizer, Renewal Safeguard, Expansion Timing)"
        
        user_prompt = f"""
Query: {query}

Available Context:
{combined_context}

{playbook_knowledge}

Provide a comprehensive answer that:
1. Synthesizes data from all sources
2. Highlights real-time insights from external systems
3. Provides specific, actionable recommendations
4. Cites data sources (Local DB, Salesforce, ServiceNow, Surveys)
{playbook_instruction}
"""
        
        try:
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1200,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating enhanced response: {e}")
            # Fall back to original response
            return local_result.get('response', 'Error generating response')

