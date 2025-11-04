#!/usr/bin/env python3
"""
Direct RAG API - Bypasses vector search issues
"""

from flask import Blueprint, request, jsonify, abort
from auth_middleware import get_current_customer_id, get_current_user_id
from models import db, KPI, Account, KPIUpload, PlaybookReport, QueryAudit, PlaybookTrigger
from sqlalchemy import text
import openai
import os
import time
from dotenv import load_dotenv
from query_cache import get_cached_query_result, cache_query_result, get_cache_stats

# Load environment variables
load_dotenv()

direct_rag_api = Blueprint('direct_rag_api', __name__)

def get_current_customer_id():
    """Extract and validate the X-Customer-ID header from the request."""
    cid = get_current_customer_id()
    if not cid:
        abort(400, 'Authentication required (handled by middleware)')
    try:
        return int(cid)
    except Exception:
        abort(400, 'Invalid authentication (handled by middleware)')


def get_playbook_context(customer_id, query_text):
    """Get recent playbook insights for context enrichment"""
    try:
        # Try to extract account from query
        query_lower = query_text.lower()
        account_id = None
        
        # Find account by name in query
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        for account in accounts:
            # Exact match
            if account.account_name.lower() in query_lower:
                account_id = account.account_id
                break
        
        # Partial match (word-based)
        if not account_id:
            for account in accounts:
                account_words = account.account_name.lower().split()
                for word in account_words:
                    if len(word) > 3 and word in query_lower:
                        account_id = account.account_id
                        print(f"✓ Matched '{word}' from '{account.account_name}' in query")
                        break
                if account_id:
                    break
        
        # Query playbook reports
        query = PlaybookReport.query.filter_by(customer_id=customer_id)
        if account_id:
            query = query.filter_by(account_id=account_id)
            print(f"🔍 Fetching playbook reports for customer {customer_id}, account {account_id}")
        else:
            print(f"🔍 Fetching playbook reports for customer {customer_id} (all accounts)")
        
        reports = query.order_by(PlaybookReport.report_generated_at.desc()).limit(3).all()
        
        if not reports:
            print(f"⚠️  No playbook reports found")
            return None
        
        print(f"✓ Found {len(reports)} playbook report(s)")
        
        # Build context
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
                context += f"Summary: {exec_summary[:250]}...\n"
            
            # Add key outcomes
            outcomes = data.get('outcomes_achieved', {})
            if outcomes:
                context += "Key Outcomes:\n"
                count = 0
                for outcome_key, outcome_data in outcomes.items():
                    if count >= 3:  # Show top 3 outcomes
                        break
                    if isinstance(outcome_data, dict):
                        baseline = outcome_data.get('baseline', 'N/A')
                        current = outcome_data.get('current', 'N/A')
                        improvement = outcome_data.get('improvement', 'N/A')
                        status = outcome_data.get('status', 'Unknown')
                        context += f"  • {outcome_key}: {baseline} → {current} ({improvement}) - {status}\n"
                        count += 1
            
            # Add top 2 next steps
            next_steps = data.get('next_steps', [])
            if next_steps:
                context += "Priority Actions:\n"
                for i, step in enumerate(next_steps[:2]):
                    context += f"  {i+1}. {step}\n"
        
        context += "\n(Use these playbook insights to provide evidence-based, action-oriented recommendations)\n"
        return context
        
    except Exception as e:
        print(f"Warning: Could not fetch playbook context: {e}")
        return None

@direct_rag_api.route('/api/direct-rag/query', methods=['POST'])
def direct_query():
    """Direct RAG query that bypasses vector search"""
    start_time = time.time()
    customer_id = get_current_customer_id()
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query_text = data['query']
    query_type = data.get('query_type', 'general')
    conversation_history = data.get('conversation_history', [])
    
    # Security: Validate conversation history belongs to this customer
    # Prevent conversation history from one customer being used by another
    if conversation_history:
        # Check if any previous query in history contains data from a different customer
        # We'll validate by checking if the customer_id in history matches current customer_id
        for i, msg in enumerate(conversation_history):
            hist_customer_id = msg.get('customer_id')
            if hist_customer_id and hist_customer_id != customer_id:
                return jsonify({
                    'error': 'Invalid conversation history',
                    'message': 'Conversation history does not belong to this customer'
                }), 403
    
    # Determine conversation turn
    conversation_turn = len(conversation_history) + 1
    has_conversation_history = len(conversation_history) > 0
    
    # Check cache first (skip if conversation history exists - dynamic context)
    cache_hit = False
    if not conversation_history:
        cached_result = get_cached_query_result(customer_id, query_text, query_type)
        if cached_result:
            cached_result['cache_hit'] = True
            cached_result['cost'] = '$0.00'
            cache_hit = True
            
            # Log cached query to audit
            try:
                audit = QueryAudit(
                    customer_id=customer_id,
                    query_text=query_text,
                    query_type=query_type,
                    response_text=cached_result.get('response', ''),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    results_count=cached_result.get('results_count', 0),
                    cache_hit=True,
                    playbook_enhanced=cached_result.get('playbook_enhanced', False),
                    has_conversation_history=has_conversation_history,
                    conversation_turn=conversation_turn,
                    estimated_cost=0.0,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')[:500]
                )
                db.session.add(audit)
                db.session.commit()
            except Exception as e:
                print(f"Audit log failed (non-critical): {e}")
                db.session.rollback()
            
            return jsonify(cached_result)
    
    try:
        # Fetch data directly from database
        kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).all()
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        # Create account lookup
        account_lookup = {acc.account_id: acc for acc in accounts}
        
        # Prepare context data
        context_data = []
        
        # Import models needed for health score calculation
        from models import HealthTrend
        from playbook_recommendations_api import calculate_health_score_proxy
        
        # Add ALL accounts by revenue (not just top 5) with health scores
        all_accounts = sorted(accounts, key=lambda x: x.revenue, reverse=True)
        for account in all_accounts:
            # Get latest health score
            latest_trend = HealthTrend.query.filter_by(
                account_id=account.account_id,
                customer_id=customer_id
            ).order_by(
                HealthTrend.year.desc(),
                HealthTrend.month.desc()
            ).first()
            
            health_score = None
            if latest_trend and latest_trend.overall_health_score:
                health_score = float(latest_trend.overall_health_score)
            else:
                # Calculate on-the-fly
                health_score = calculate_health_score_proxy(account.account_id)
            
            context_data.append(f"Account: {account.account_name}, Revenue: ${account.revenue:,.0f}, Health Score: {health_score:.1f}/100, Industry: {account.industry}, Region: {account.region}")
        
        # Add revenue time series data from actual KPITimeSeries records (customer-specific)
        # SECURITY: Only use data from the current customer to prevent cross-tenant data leakage
        try:
            from models import KPITimeSeries
            time_series_records = KPITimeSeries.query.filter_by(customer_id=customer_id).all()
            
            if time_series_records:
                context_data.append("=== REVENUE TIME SERIES DATA ===")
                
                # Group by account
                account_series = {}
                for ts in time_series_records:
                    if ts.account_id not in account_series:
                        account_series[ts.account_id] = []
                    account_series[ts.account_id].append({
                        'year': ts.year,
                        'month': ts.month,
                        'revenue_growth': ts.revenue_growth,
                        'nrr': ts.net_revenue_retention,
                        'grr': ts.gross_revenue_retention,
                        'expansion_revenue_rate': ts.expansion_revenue_rate
                    })
                
                # Add time series data for top accounts
                for account_id, series in account_series.items():
                    account_name = account_lookup.get(account_id, {}).account_name if account_id in account_lookup else f"Account {account_id}"
                    
                    # Revenue Growth
                    growth_data = [f"{ts['year']}-{ts['month']:02d}: {ts['revenue_growth']:.2f}%" 
                                   for ts in sorted(series, key=lambda x: (x['year'], x['month'])) 
                                   if ts.get('revenue_growth')]
                    if growth_data:
                        context_data.append(f"{account_name} Revenue Growth: {', '.join(growth_data)}")
                    
                    # NRR
                    nrr_data = [f"{ts['year']}-{ts['month']:02d}: {ts['nrr']:.2f}%" 
                                for ts in sorted(series, key=lambda x: (x['year'], x['month'])) 
                                if ts.get('nrr')]
                    if nrr_data:
                        context_data.append(f"{account_name} NRR: {', '.join(nrr_data)}")
                
                context_data.append("=== END TIME SERIES DATA ===")
            else:
                print(f"No time series data available for customer {customer_id}")
        except Exception as e:
            print(f"Note: No time series data available for customer {customer_id}: {e}")
        
        # Add playbook insights context
        playbook_context = get_playbook_context(customer_id, query_text)
        if playbook_context:
            context_data.append(playbook_context)
            print(f"✓ Added playbook insights context")
        
        # Add system playbook knowledge
        from playbook_knowledge import format_playbook_knowledge_for_rag
        import os
        
        playbook_knowledge = ""
        # Check if query is about playbooks or improvement
        if any(keyword in query_text.lower() for keyword in ['playbook', 'improve', 'increase', 'reduce', 'better', 'leverage', 'help', 'address']):
            playbook_knowledge = format_playbook_knowledge_for_rag()
        
        # Add playbook trigger context (alert thresholds)
        trigger_context = ""
        try:
            triggers = PlaybookTrigger.query.filter_by(customer_id=customer_id).all()
            if triggers:
                trigger_context = "\n\n=== ACTIVE PLAYBOOK ALERTS ===\n"
                trigger_context += "(Current trigger thresholds for automated alerts):\n"
                for trigger in triggers:
                    import json
                    try:
                        config = json.loads(trigger.trigger_config) if trigger.trigger_config else {}
                        playbook_type = trigger.playbook_type
                        trigger_context += f"\n{playbook_type.upper()} Playbook Triggers:\n"
                        if config:
                            for key, value in config.items():
                                trigger_context += f"  • {key}: {value}\n"
                    except:
                        pass
        except Exception as e:
            print(f"Error getting playbook triggers: {e}")
        
        # Generate AI response
        try:
            # Use environment variable for API key
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return jsonify({'error': 'OpenAI API key not configured'}), 500
                
            # Initialize OpenAI client with explicit httpx configuration
            import httpx
            http_client = httpx.Client(timeout=30.0)
            client = openai.OpenAI(api_key=api_key, http_client=http_client)
            
            context = "\n".join(context_data)
            
            playbook_instruction = ""
            if playbook_knowledge:
                playbook_instruction = "\nIMPORTANT: When recommending playbooks, ONLY suggest the 5 system-defined playbooks listed below. Do NOT make up generic playbook names."
            
            # Build conversation context
            conversation_context = ""
            if conversation_history:
                conversation_context = "\n=== CONVERSATION HISTORY ===\n"
                for i, msg in enumerate(conversation_history, 1):
                    conversation_context += f"\nPrevious Q{i}: {msg.get('query', '')}\n"
                    conversation_context += f"Previous A{i}: {msg.get('response', '')[:200]}...\n"
                conversation_context += "\n(Use this context to understand follow-up questions and maintain conversation flow)\n"
            
            system_prompt = f"""
            You are an AI assistant analyzing KPI and account data for a customer success platform.
            
            CRITICAL RULES - YOU MUST FOLLOW THESE STRICTLY:
            1. ONLY use account names, KPI values, and metrics that are explicitly provided in the "Available Data" section below
            2. NEVER invent, guess, or hallucinate account names, company names, or data that is not in the provided context
            3. If asked to list accounts, ONLY list the exact account names from the "Available Data" section
            4. If you don't have specific data to answer a question, say "I don't have that specific information in the current data"
            5. Do NOT use generic industry terms like "pharmaceutical", "aerospace", "technology" unless they appear in the actual account names provided
            
            You have access to:
            1. Real-time KPI data for ALL accounts in the "Available Data" section
            2. Historical playbook execution insights (see "Available Data" section)
            3. System-defined playbooks (VoC Sprint, Activation Blitz, SLA Stabilizer, Renewal Safeguard, Expansion Timing)
            4. Active playbook trigger thresholds
            5. Conversation history for context awareness
            
            CRITICAL: The "Available Data" section contains ALL the information you need. ALWAYS analyze it to answer questions about accounts, KPIs, risks, revenue, etc.
            
            When answering:
            - ALWAYS analyze the Available Data first before saying "I don't have that information"
            - Extract specific metrics from the data (revenue, KPIs, playbook results, etc.)
            - Use conversation history to understand follow-up questions (e.g., "What about TechCorp?" refers to previous context)
            - When playbook insights are available, cite specific names, dates, and outcomes
            - Reference concrete metrics with before/after comparisons
            - Include actionable next steps from playbook reports
            - Connect playbook results to current KPI trends
            {playbook_instruction}
            
            REMEMBER: Only use data explicitly provided to you. Never make up account names or data points.
            """
            
            user_prompt = f"""
            {conversation_context}
            
            Current Query: {query_text}
            
            Available Data:
            {context}
            
            {playbook_knowledge}
            
            {trigger_context}
            
            Provide a CONCISE, DIRECT answer in 2-3 sentences maximum. Be specific and actionable. No fluff, no general statements. Use bullet points if needed.
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
            return jsonify({'error': f'Query failed: {str(e)}'}), 500
        
        # Create properly formatted relevant_results with metadata
        relevant_results = []
        for i, data in enumerate(context_data[:10]):  # Show more results for better demo
            if "Account:" in data:
                # Parse account data
                parts = data.split(", ")
                account_name = parts[0].replace("Account: ", "")
                revenue = int(parts[1].replace("Revenue: $", "").replace(",", ""))
                industry = parts[2].replace("Industry: ", "")
                region = parts[3].replace("Region: ", "")
                
                relevant_results.append({
                    'text': data,
                    'similarity': 1.0,
                    'metadata': {
                        'type': 'account',
                        'account_id': i + 1,
                        'account_name': account_name,
                        'revenue': revenue,
                        'industry': industry,
                        'region': region
                    }
                })
            else:
                # KPI data
                relevant_results.append({
                    'text': data,
                    'similarity': 1.0,
                    'metadata': {
                        'type': 'kpi',
                        'category': 'performance'
                    }
                })
        
        result = {
            'customer_id': customer_id,
            'query': query_text,
            'query_type': query_type,
            'results_count': len(kpis) + len(accounts),
            'relevant_results': relevant_results,
            'response': ai_response,
            'similarity_threshold': 0.0,
            'playbook_enhanced': bool(playbook_context),
            'enhancement_source': 'playbook_reports' if playbook_context else None,
            'cache_hit': False,
            'cost': '$0.02'  # Estimated OpenAI cost per query
        }
        
        # Cache the result (only if no conversation history - those are dynamic)
        if not conversation_history:
            cache_query_result(customer_id, query_text, result, query_type)
        
        # Audit logging (for compliance and analytics)
        try:
            response_time_ms = int((time.time() - start_time) * 1000)
            audit = QueryAudit(
                customer_id=customer_id,
                query_text=query_text,
                query_type=query_type,
                response_text=ai_response,
                response_time_ms=response_time_ms,
                results_count=len(kpis) + len(accounts),
                cache_hit=False,
                playbook_enhanced=bool(playbook_context),
                has_conversation_history=has_conversation_history,
                conversation_turn=conversation_turn,
                estimated_cost=0.02,  # $0.02 per OpenAI query
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:500]
            )
            db.session.add(audit)
            db.session.commit()
        except Exception as e:
            print(f"Audit log failed (non-critical): {e}")
            db.session.rollback()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Query failed: {str(e)}'}), 500

@direct_rag_api.route('/api/direct-rag/status', methods=['GET'])
def direct_status():
    """Get direct RAG system status"""
    customer_id = get_current_customer_id()
    
    try:
        kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).count()
        accounts = Account.query.filter_by(customer_id=customer_id).count()
        
        return jsonify({
            'customer_id': customer_id,
            'is_built': True,
            'status': 'ready',
            'records_count': kpis + accounts,
            'kpis_count': kpis,
            'accounts_count': accounts
        })
    except Exception as e:
        return jsonify({'error': f'Status check failed: {str(e)}'}), 500
