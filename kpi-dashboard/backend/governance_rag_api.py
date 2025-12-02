#!/usr/bin/env python3
"""
Governance RAG API
Separate RAG endpoint for governance and compliance queries
Optimized for activity log queries and governance-related questions
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import ActivityLog, QueryAudit, User, Account, KPI
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

governance_rag_api = Blueprint('governance_rag_api', __name__)

def get_governance_context(customer_id: int, query_text: str, days: int = 90) -> str:
    """
    Build governance-focused context for RAG queries
    Includes activity logs, query audits, and system changes
    """
    context_parts = []
    
    try:
        # Get date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get activity logs
        activity_logs = ActivityLog.query.filter(
            ActivityLog.customer_id == customer_id,
            ActivityLog.created_at >= start_date
        ).order_by(ActivityLog.created_at.desc()).limit(500).all()
        
        if activity_logs:
            context_parts.append(f"=== USER ACTIVITY LOGS (Last {days} days) ===")
            context_parts.append(f"Total activities: {len(activity_logs)}")
            
            # Summary by category
            category_counts = {}
            action_type_counts = {}
            user_counts = {}
            status_counts = {}
            
            for log in activity_logs:
                category_counts[log.action_category] = category_counts.get(log.action_category, 0) + 1
                action_type_counts[log.action_type] = action_type_counts.get(log.action_type, 0) + 1
                if log.user_id:
                    user_name = log.user.user_name if log.user else f"User {log.user_id}"
                    user_counts[user_name] = user_counts.get(user_name, 0) + 1
                status_counts[log.status] = status_counts.get(log.status, 0) + 1
            
            context_parts.append(f"\nActivity Summary:")
            context_parts.append(f"- By Category: {', '.join([f'{k}: {v}' for k, v in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)])}")
            context_parts.append(f"- By Action Type: {', '.join([f'{k}: {v}' for k, v in sorted(action_type_counts.items(), key=lambda x: x[1], reverse=True)[:15]])}")
            context_parts.append(f"- By Status: {', '.join([f'{k}: {v}' for k, v in status_counts.items()])}")
            if user_counts:
                context_parts.append(f"- Top Users: {', '.join([f'{k}: {v}' for k, v in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]])}")
            
            # Recent activities (detailed) - with resource validation
            context_parts.append(f"\nRecent Activities (Most Recent First):")
            invalid_refs_count = 0
            for log in activity_logs[:100]:  # Top 100 most recent
                # Validate resource reference if present
                resource_info = ""
                resource_valid = True
                
                if log.resource_type and log.resource_id:
                    try:
                        resource_id = int(log.resource_id)
                        if log.resource_type == 'kpi':
                            resource = db.session.get(KPI, resource_id)
                            if not resource:
                                resource_valid = False
                                invalid_refs_count += 1
                        elif log.resource_type == 'account':
                            resource = db.session.get(Account, resource_id)
                            if not resource:
                                resource_valid = False
                                invalid_refs_count += 1
                        # For other resource types, we don't validate (e.g., settings, playbook, etc.)
                        
                        if resource_valid:
                            resource_info = f" ({log.resource_type} #{log.resource_id})"
                        else:
                            # Skip invalid references - they likely indicate deleted resources or test data
                            continue
                    except (ValueError, TypeError):
                        # Invalid resource_id format - skip this log entry
                        invalid_refs_count += 1
                        continue
                
                user_name = log.user.user_name if log.user else "System"
                timestamp = log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else "Unknown"
                changed_fields_str = f" [Changed: {', '.join(log.changed_fields)}]" if log.changed_fields else ""
                
                context_parts.append(
                    f"- {timestamp}: {user_name} - {log.action_description}{resource_info}{changed_fields_str} "
                    f"(Type: {log.action_type}, Category: {log.action_category}, Status: {log.status})"
                )
            
            if invalid_refs_count > 0:
                context_parts.append(f"\n⚠️ Note: {invalid_refs_count} activity log(s) with invalid resource references were excluded (likely deleted resources or test data).")
            
            # Activities by resource type
            resource_activities = {}
            for log in activity_logs:
                if log.resource_type:
                    if log.resource_type not in resource_activities:
                        resource_activities[log.resource_type] = []
                    resource_activities[log.resource_type].append(log)
            
            if resource_activities:
                context_parts.append(f"\nActivities by Resource Type:")
                for resource_type, logs in sorted(resource_activities.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
                    # Filter valid resource references
                    valid_logs = []
                    for log in logs:
                        if log.resource_type and log.resource_id:
                            try:
                                resource_id = int(log.resource_id)
                                if log.resource_type == 'kpi':
                                    if db.session.get(KPI, resource_id):
                                        valid_logs.append(log)
                                elif log.resource_type == 'account':
                                    if db.session.get(Account, resource_id):
                                        valid_logs.append(log)
                                else:
                                    # For other types (settings, playbook, etc.), include them
                                    valid_logs.append(log)
                            except (ValueError, TypeError):
                                # Invalid resource_id, skip
                                continue
                        else:
                            # No resource reference, include it
                            valid_logs.append(log)
                    
                    if valid_logs:
                        context_parts.append(f"- {resource_type}: {len(valid_logs)} activities (valid references only)")
                        # Show recent activities for each resource type
                        for log in valid_logs[:5]:
                            user_name = log.user.user_name if log.user else "System"
                            timestamp = log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else "Unknown"
                            resource_info = f" ({log.resource_type} #{log.resource_id})" if log.resource_type and log.resource_id else ""
                            context_parts.append(f"  * {timestamp}: {user_name} - {log.action_description}{resource_info}")
            
            context_parts.append("=== END ACTIVITY LOGS ===")
        
        # Get query audit logs
        query_audits = QueryAudit.query.filter(
            QueryAudit.customer_id == customer_id,
            QueryAudit.created_at >= start_date
        ).order_by(QueryAudit.created_at.desc()).limit(200).all()
        
        if query_audits:
            context_parts.append(f"\n=== RAG QUERY AUDIT LOGS (Last {days} days) ===")
            context_parts.append(f"Total queries: {len(query_audits)}")
            
            # Summary statistics
            cache_hits = sum(1 for qa in query_audits if qa.cache_hit)
            total_cost = sum(qa.estimated_cost for qa in query_audits)
            avg_response_time = sum(qa.response_time_ms or 0 for qa in query_audits) / len(query_audits) if query_audits else 0
            
            context_parts.append(f"- Cache hit rate: {cache_hits}/{len(query_audits)} ({100*cache_hits/len(query_audits):.1f}%)")
            context_parts.append(f"- Total estimated cost: ${total_cost:.4f}")
            context_parts.append(f"- Average response time: {avg_response_time:.0f}ms")
            
            # Recent queries
            context_parts.append(f"\nRecent Queries (Last 50):")
            for qa in query_audits[:50]:
                user_name = qa.user.user_name if qa.user else "Anonymous"
                timestamp = qa.created_at.strftime('%Y-%m-%d %H:%M:%S') if qa.created_at else "Unknown"
                cache_indicator = " [CACHED]" if qa.cache_hit else ""
                context_parts.append(
                    f"- {timestamp}: {user_name} - Query: \"{qa.query_text[:100]}\"{cache_indicator} "
                    f"(Response time: {qa.response_time_ms}ms, Cost: ${qa.estimated_cost:.4f})"
                )
            
            context_parts.append("=== END QUERY AUDIT LOGS ===")
        
        # Get configuration changes
        config_changes = ActivityLog.query.filter(
            ActivityLog.customer_id == customer_id,
            ActivityLog.action_category == 'configuration',
            ActivityLog.created_at >= start_date
        ).order_by(ActivityLog.created_at.desc()).limit(50).all()
        
        if config_changes:
            context_parts.append(f"\n=== CONFIGURATION CHANGES (Last {days} days) ===")
            for log in config_changes:
                user_name = log.user.user_name if log.user else "System"
                timestamp = log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else "Unknown"
                context_parts.append(
                    f"- {timestamp}: {user_name} - {log.action_description} "
                    f"(Changed fields: {', '.join(log.changed_fields) if log.changed_fields else 'N/A'})"
                )
            context_parts.append("=== END CONFIGURATION CHANGES ===")
        
    except Exception as e:
        context_parts.append(f"\n⚠️  Error building governance context: {e}")
    
    return "\n".join(context_parts)

@governance_rag_api.route('/api/governance-rag/query', methods=['POST'])
def governance_query():
    """Governance-focused RAG query endpoint"""
    start_time = time.time()
    customer_id = get_current_customer_id()
    user_id = get_current_user_id()
    
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query_text = data['query']
    days = data.get('days', 90)  # Default to 90 days of history
    
    try:
        # Build governance context
        governance_context = get_governance_context(customer_id, query_text, days)
        
        if not governance_context.strip():
            return jsonify({
                'response': 'No governance data available for the specified period.',
                'context': '',
                'cost': '$0.00',
                'response_time_ms': int((time.time() - start_time) * 1000)
            })
        
        # Use OpenAI to answer governance queries
        from openai_key_utils import get_openai_api_key
        import openai
        import httpx
        
        api_key = get_openai_api_key(customer_id)
        if not api_key:
            return jsonify({
                'error': 'OpenAI API key not configured',
                'message': 'Please configure your OpenAI API key in Settings → OpenAI API Key.'
            }), 400
        
        # Initialize OpenAI client with explicit httpx configuration
        http_client = httpx.Client(timeout=60.0, follow_redirects=True)
        client = openai.OpenAI(api_key=api_key, http_client=http_client)
        
        system_prompt = """You are a governance and compliance assistant for a KPI dashboard system.
Your role is to help answer questions about user activities, system changes, audit logs, and compliance.

You have access to:
1. User Activity Logs - All user actions (edits, uploads, exports, settings changes, etc.)
   - Only activity logs with VALID resource references are included
   - If a KPI or Account is referenced, it exists in the system
   - Invalid references (e.g., deleted resources) are excluded
2. RAG Query Audit Logs - All AI queries made to the system
3. Configuration Changes - Settings and configuration updates

IMPORTANT: 
- If you see a resource reference (e.g., "KPI #999"), it means that resource EXISTS in the system
- If you cannot verify a resource exists, DO NOT make claims about it
- If asked about a resource that doesn't appear in the logs, state that you have no evidence of that resource in the system
- When in doubt, acknowledge uncertainty rather than making assumptions

When answering questions:
- Be specific about who did what and when
- Only reference resources that are confirmed to exist in the activity logs
- Include relevant details like resource IDs, changed fields, IP addresses when relevant
- Highlight any anomalies or compliance concerns
- Provide timelines and summaries when asked
- Use the activity logs to trace changes and user actions
- If asked about a resource that doesn't exist in the logs, clearly state that

Format your responses clearly with dates, user names, and action details."""

        user_prompt = f"""Based on the following governance data, answer this question: {query_text}

{governance_context}

Please provide a comprehensive answer based on the governance data above."""

        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        response_text = response.choices[0].message.content
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Estimate cost (GPT-4 pricing: $0.03/1K input tokens, $0.06/1K output tokens)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        estimated_cost = (input_tokens / 1000 * 0.03) + (output_tokens / 1000 * 0.06)
        
        return jsonify({
            'response': response_text,
            'context': governance_context[:1000] + '...' if len(governance_context) > 1000 else governance_context,
            'cost': f'${estimated_cost:.4f}',
            'response_time_ms': response_time_ms,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'response_time_ms': int((time.time() - start_time) * 1000)
        }), 500

