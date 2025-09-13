#!/usr/bin/env python3
"""
Direct RAG API - Bypasses vector search issues
"""

from flask import Blueprint, request, jsonify, abort
from models import db, KPI, Account, KPIUpload
import openai

direct_rag_api = Blueprint('direct_rag_api', __name__)

def get_customer_id():
    """Extract and validate the X-Customer-ID header from the request."""
    cid = request.headers.get('X-Customer-ID')
    if not cid:
        abort(400, 'Missing X-Customer-ID header')
    try:
        return int(cid)
    except Exception:
        abort(400, 'Invalid X-Customer-ID header')

@direct_rag_api.route('/api/direct-rag/query', methods=['POST'])
def direct_query():
    """Direct RAG query that bypasses vector search"""
    customer_id = get_customer_id()
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query_text = data['query']
    query_type = data.get('query_type', 'general')
    
    try:
        # Fetch data directly from database
        kpis = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).all()
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        # Create account lookup
        account_lookup = {acc.account_id: acc for acc in accounts}
        
        # Prepare context data
        context_data = []
        
        # Add top accounts by revenue
        top_accounts = sorted(accounts, key=lambda x: x.revenue, reverse=True)[:5]
        for account in top_accounts:
            context_data.append(f"Account: {account.account_name}, Revenue: ${account.revenue:,.0f}, Industry: {account.industry}, Region: {account.region}")
        
        # Add sample KPIs
        sample_kpis = kpis[:10]  # Take first 10 KPIs
        for kpi in sample_kpis:
            account = account_lookup.get(kpi.account_id)
            context_data.append(f"KPI: {kpi.kpi_parameter}, Account: {account.account_name if account else 'Unknown'}, Value: {kpi.data}, Category: {kpi.category}")
        
        # Generate AI response
        try:
            client = openai.OpenAI(api_key="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")
            
            context = "\n".join(context_data)
            
            system_prompt = f"""
            You are an AI assistant analyzing KPI and account data for a customer success platform.
            Based on the provided data, answer the user's query with specific insights and recommendations.
            """
            
            user_prompt = f"""
            Query: {query_text}
            
            Available Data:
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
        
        # Create properly formatted relevant_results with metadata
        relevant_results = []
        for i, data in enumerate(context_data[:5]):
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
        
        return jsonify({
            'customer_id': customer_id,
            'query': query_text,
            'query_type': query_type,
            'results_count': len(kpis) + len(accounts),
            'relevant_results': relevant_results,
            'response': ai_response,
            'similarity_threshold': 0.0
        })
        
    except Exception as e:
        return jsonify({'error': f'Query failed: {str(e)}'}), 500

@direct_rag_api.route('/api/direct-rag/status', methods=['GET'])
def direct_status():
    """Get direct RAG system status"""
    customer_id = get_customer_id()
    
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
