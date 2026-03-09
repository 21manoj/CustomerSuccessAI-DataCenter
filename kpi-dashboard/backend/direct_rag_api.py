#!/usr/bin/env python3
"""
Direct RAG API - Bypasses vector search issues
"""

from flask import Blueprint, request, jsonify, abort
from auth_middleware import get_current_customer_id, get_current_user_id
from models import db, KPI, Account, KPIUpload, PlaybookReport, QueryAudit, PlaybookTrigger, AccountSnapshot, AccountNote, DC2SKPI, PillarScore, QualitativeSignal
from sqlalchemy import text
import openai
import os
import time
from dotenv import load_dotenv
from query_cache import get_cached_query_result, cache_query_result, get_cache_stats

# Load environment variables
load_dotenv()

direct_rag_api = Blueprint('direct_rag_api', __name__)

# Use get_current_customer_id from auth_middleware (imported above)
# No need to redefine it here


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
            
            # DC Playbook: hours tracking
            hours = data.get('hours_tracking', {})
            if hours:
                context += f"Hours: {hours.get('total_actual_hours', 'N/A')}h actual vs {hours.get('total_estimated_hours', 'N/A')}h estimated ({hours.get('efficiency_rating', 'N/A')})\n"

            # DC Playbook: KPI impact with financial
            kpi_impact = data.get('kpi_impact', {})
            if kpi_impact:
                fin = kpi_impact.get('financial_impact')
                if fin:
                    context += f"Financial Impact: {fin}\n"
                for ti in kpi_impact.get('trigger_kpis', [])[:3]:
                    if isinstance(ti, dict) and ti.get('before') is not None:
                        context += f"  • {ti.get('kpi_name', '')}: {ti['before']} → {ti.get('after', 'N/A')} ({ti.get('improvement', '')})\n"

            # DC Playbook: learnings
            learnings = data.get('learnings', [])
            if learnings:
                context += "Learnings:\n"
                for lr in learnings[:2]:
                    context += f"  • {lr}\n"

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
        # NOTE: Only count KPIs (they are not used in context, only for results_count)
        kpi_count = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).count()
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        # Create account lookup
        account_lookup = {acc.account_id: acc for acc in accounts}
        
        # Prepare context data
        context_data = []
        
        # Import models needed for health score calculation
        from models import HealthTrend
        from playbook_recommendations_api import calculate_health_score_proxy
        
        # Add top 20 accounts by revenue with health scores (limit context size)
        top_accounts = sorted(accounts, key=lambda x: x.revenue, reverse=True)[:20]
        for account in top_accounts:
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
            
            # Add account snapshot context if available (read-only, no auto-creation)
            try:
                latest_snapshot = AccountSnapshot.query.filter_by(
                    account_id=account.account_id,
                    customer_id=customer_id
                ).order_by(AccountSnapshot.snapshot_timestamp.desc()).first()

                if latest_snapshot:
                    revenue_change_str = ""
                    if latest_snapshot.revenue_change_percent is not None:
                        change_pct = float(latest_snapshot.revenue_change_percent)
                        arrow = '↑' if change_pct > 0 else '↓'
                        revenue_change_str = f" ({arrow} {abs(change_pct):.1f}% change)"
                    
                    snapshot_context = (
                        f"\nAccount Snapshot ({latest_snapshot.snapshot_timestamp.strftime('%Y-%m-%d')}):\n"
                        f"  Revenue: ${latest_snapshot.revenue:,.0f}{revenue_change_str}\n"
                        f"  Health Score: {latest_snapshot.overall_health_score:.1f}/100 "
                        f"({latest_snapshot.health_score_trend})\n"
                        f"  CSM: {latest_snapshot.assigned_csm or 'Unassigned'}\n"
                        f"  Products: {', '.join(latest_snapshot.products_used or [])}\n"
                        f"  Playbooks Running: {latest_snapshot.playbooks_running_count}, "
                        f"Completed: {latest_snapshot.playbooks_completed_count}\n"
                        f"  Critical KPIs: {latest_snapshot.critical_kpis_count}/{latest_snapshot.total_kpis}\n"
                    )
                    
                    # Add CSM notes summaries
                    if latest_snapshot.recent_csm_note_ids:
                        notes = AccountNote.query.filter(
                            AccountNote.note_id.in_(latest_snapshot.recent_csm_note_ids),
                            AccountNote.customer_id == customer_id
                        ).order_by(AccountNote.created_at.desc()).limit(3).all()
                        
                        if notes:
                            snapshot_context += "  Recent CSM Notes:\n"
                            for note in notes:
                                note_preview = note.note_content[:150] + "..." if len(note.note_content) > 150 else note.note_content
                                snapshot_context += f"    - {note.note_type.title()} ({note.created_at.strftime('%Y-%m-%d')}): {note_preview}\n"
                    
                    # NOTE: Playbook report summaries omitted here to reduce memory
                    # (full reports loaded via get_playbook_context with limit=3)

                    context_data.append(snapshot_context)
                    print(f"✓ Added account snapshot context for {account.account_name}")
            except Exception as e:
                print(f"Note: Could not fetch account snapshot: {e}")
        
        # Add revenue time series data (last 3 months only to limit memory)
        # SECURITY: Only use data from the current customer to prevent cross-tenant data leakage
        try:
            from models import KPITimeSeries
            from datetime import datetime as _dt
            cutoff_year = _dt.now().year
            cutoff_month = _dt.now().month - 3
            if cutoff_month <= 0:
                cutoff_month += 12
                cutoff_year -= 1
            time_series_records = KPITimeSeries.query.filter_by(
                customer_id=customer_id
            ).filter(
                db.or_(
                    KPITimeSeries.year > cutoff_year,
                    db.and_(KPITimeSeries.year == cutoff_year, KPITimeSeries.month >= cutoff_month)
                )
            ).all()
            
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

        # ── DC2S Infrastructure KPI Data ──
        try:
            import json as _json
            # Load KPI catalog for human-readable names
            kpi_catalog = {}
            catalog_path = os.path.join(os.path.dirname(__file__), 'config', 'dc2s_kpi_catalog.json')
            if os.path.exists(catalog_path):
                with open(catalog_path) as f:
                    cat = _json.load(f)
                    for p_code, kpi_def in cat.get('kpis', {}).items():
                        kpi_catalog[p_code] = kpi_def.get('name', p_code)

            account_ids = [a.account_id for a in accounts]
            if account_ids:
                # Get latest DC2S KPIs per account (most recent measured_at)
                from sqlalchemy import func
                latest_dates = db.session.query(
                    DC2SKPI.account_id,
                    func.max(DC2SKPI.measured_at).label('max_date')
                ).filter(DC2SKPI.account_id.in_(account_ids)).group_by(DC2SKPI.account_id).subquery()

                dc2s_kpis = DC2SKPI.query.join(
                    latest_dates,
                    db.and_(DC2SKPI.account_id == latest_dates.c.account_id,
                            DC2SKPI.measured_at == latest_dates.c.max_date)
                ).all()

                if dc2s_kpis:
                    context_data.append("\n=== DATA CENTER INFRASTRUCTURE KPIs (Latest) ===")
                    # Group by account
                    acct_kpis = {}
                    for kpi in dc2s_kpis:
                        acct_kpis.setdefault(kpi.account_id, []).append(kpi)

                    for aid, kpi_list in acct_kpis.items():
                        acct_name = account_lookup.get(aid).account_name if aid in account_lookup else f"Account {aid}"
                        kpi_strs = []
                        for k in sorted(kpi_list, key=lambda x: x.kpi_code):
                            name = kpi_catalog.get(k.kpi_code, k.kpi_code)
                            target_str = f" (target: {k.target})" if k.target else ""
                            status_str = f" [{k.status}]" if k.status else ""
                            kpi_strs.append(f"  {name}: {k.value}{target_str}{status_str}")
                        context_data.append(f"{acct_name} DC KPIs:\n" + "\n".join(kpi_strs))
                    context_data.append("=== END DC INFRASTRUCTURE KPIs ===")
                    print(f"✓ Added {len(dc2s_kpis)} DC2S KPI records for {len(acct_kpis)} accounts")

                # Add pillar scores (latest month only per account)
                from sqlalchemy import func as _func
                latest_pillar_months = db.session.query(
                    PillarScore.account_id,
                    _func.max(PillarScore.measurement_month).label('max_month')
                ).filter(
                    PillarScore.account_id.in_(account_ids)
                ).group_by(PillarScore.account_id).subquery()

                pillar_scores = PillarScore.query.join(
                    latest_pillar_months,
                    db.and_(
                        PillarScore.account_id == latest_pillar_months.c.account_id,
                        PillarScore.measurement_month == latest_pillar_months.c.max_month
                    )
                ).all()

                if pillar_scores:
                    # Group by account (already filtered to latest month via SQL)
                    acct_pillars = {}
                    pillar_names = {'P1': 'Deployment Velocity', 'P2': 'Operational Stability', 'P3': 'AI Workload Performance', 'P4': 'Channel & Partner Health', 'P5': 'Expansion Readiness'}
                    for ps in pillar_scores:
                        key = ps.account_id
                        if key not in acct_pillars:
                            acct_pillars[key] = {'month': ps.measurement_month, 'scores': {}}
                        acct_pillars[key]['scores'][pillar_names.get(ps.pillar_code, ps.pillar_code)] = round(float(ps.pillar_score), 1)

                    if acct_pillars:
                        context_data.append("\n=== PILLAR HEALTH SCORES (Latest Month) ===")
                        for aid, data in acct_pillars.items():
                            acct_name = account_lookup.get(aid).account_name if aid in account_lookup else f"Account {aid}"
                            scores_str = ", ".join(f"{p}: {s}" for p, s in data['scores'].items())
                            context_data.append(f"{acct_name}: {scores_str}")
                        context_data.append("=== END PILLAR SCORES ===")
                        print(f"✓ Added pillar scores for {len(acct_pillars)} accounts")

                # Add qualitative signals (recent, limited to reduce memory)
                signals = QualitativeSignal.query.filter(
                    QualitativeSignal.account_id.in_(account_ids)
                ).order_by(QualitativeSignal.signal_date.desc()).limit(15).all()

                if signals:
                    context_data.append("\n=== QUALITATIVE SIGNALS (Recent) ===")
                    for sig in signals:
                        acct_name = account_lookup.get(sig.account_id).account_name if sig.account_id in account_lookup else f"Account {sig.account_id}"
                        content_preview = (sig.content or '')[:100]
                        context_data.append(f"{acct_name} [{sig.signal_date}] {sig.signal_type} ({sig.sentiment}): {content_preview}")
                    context_data.append("=== END QUALITATIVE SIGNALS ===")
                    print(f"✓ Added {len(signals)} qualitative signals")

                # Add context graph data if enabled
                try:
                    from feature_toggles import is_context_graph_enabled
                    if is_context_graph_enabled(customer_id):
                        from models import ContextNode
                        ctx_nodes = ContextNode.query.filter(
                            ContextNode.account_id.in_(account_ids)
                        ).order_by(ContextNode.occurred_at.desc()).limit(20).all()

                        if ctx_nodes:
                            context_data.append("\n=== CONTEXT GRAPH (Revenue Intelligence) ===")
                            for node in ctx_nodes:
                                acct_name = account_lookup.get(node.account_id).account_name if node.account_id in account_lookup else f"Account {node.account_id}"
                                rev_str = f" Revenue Impact: ${node.revenue_impact:,.0f}" if node.revenue_impact else ""
                                conf_str = f" Confidence: {node.confidence}" if node.confidence else ""
                                context_data.append(f"{acct_name} [{node.node_type}/{node.node_subtype}]: {node.title}{rev_str}{conf_str}")
                            context_data.append("=== END CONTEXT GRAPH ===")
                            print(f"✓ Added {len(ctx_nodes)} context graph nodes")
                except ImportError:
                    pass
        except Exception as e:
            print(f"Note: DC2S data enrichment failed (non-critical): {e}")

        # Add system playbook knowledge
        from playbook_knowledge import format_playbook_knowledge_for_rag

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
            # Get API key from customer-specific encrypted storage or environment fallback
            from openai_key_utils import get_openai_api_key
            api_key = get_openai_api_key(customer_id)
            if not api_key:
                return jsonify({
                    'error': 'OpenAI API key not configured',
                    'message': 'Please configure your OpenAI API key in Settings > OpenAI Key Settings.'
                }), 400
                
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
            You are an AI assistant for a Data Center Infrastructure customer success platform (CS Pulse DC2S).
            You analyze infrastructure KPIs, AI workload performance, account health, and revenue intelligence.

            CRITICAL RULES - YOU MUST FOLLOW THESE STRICTLY:
            1. ONLY use account names, KPI values, and metrics that are explicitly provided in the "Available Data" section below
            2. NEVER invent, guess, or hallucinate account names, company names, or data that is not in the provided context
            3. If asked to list accounts, ONLY list the exact account names from the "Available Data" section
            4. If you don't have specific data to answer a question, say "I don't have that specific information in the current data"
            5. Do NOT use generic industry terms unless they appear in the actual data provided

            You have access to:
            1. Account data with revenue, health scores, and industry/region
            2. Data Center KPIs: GPU utilization, PUE (power efficiency), training completion rates, inference latency, rack capacity, uptime, SLA compliance, workload diversity, and more
            3. Pillar health scores: Deployment Value (DV/P1), Operational Scale (OS/P2), AI Innovation (AI/P3), Channel Health (CH/P4), Expansion (EX/P5)
            4. Qualitative signals (positive/negative/neutral sentiment indicators)
            5. Context graph data: stakeholders, decisions, outcomes, and revenue intelligence signals
            6. Playbook execution insights and system-defined playbooks
            7. Revenue time series and account snapshots
            8. Conversation history for context awareness

            Health score thresholds: Critical (<50), At-Risk (50-69), Healthy (70+)

            When answering:
            - ALWAYS analyze the Available Data first before saying "I don't have that information"
            - Reference specific KPI names and values (e.g., "GPU Utilization Rate: 78.5%", "PUE: 1.42")
            - Identify accounts that are critical or at-risk and explain why
            - Connect infrastructure metrics to business outcomes (revenue impact, expansion signals)
            - When playbook insights are available, cite specific names, dates, and outcomes
            - Include actionable next steps
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
                model="gpt-4o",
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
            'results_count': kpi_count + len(accounts),
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
                results_count=kpi_count + len(accounts),
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
