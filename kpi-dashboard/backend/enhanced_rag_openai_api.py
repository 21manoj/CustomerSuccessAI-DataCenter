#!/usr/bin/env python3
"""
Enhanced RAG API endpoints using OpenAI GPT-4 and FAISS
Provides advanced KPI and account analysis capabilities with multi-tenant support
"""

from flask import Blueprint, request, jsonify, abort
from extensions import db
from models import KPI, KPIUpload, Account, CustomerConfig
from enhanced_rag_openai import get_rag_system
import re

enhanced_rag_openai_api = Blueprint('enhanced_rag_openai_api', __name__)

def get_customer_id():
    """Extract and validate the X-Customer-ID header from the request."""
    cid = request.headers.get('X-Customer-ID')
    if not cid:
        abort(400, 'Missing X-Customer-ID header')
    try:
        return int(cid)
    except Exception:
        abort(400, 'Invalid X-Customer-ID header')

@enhanced_rag_openai_api.route('/api/rag-openai/build', methods=['POST'])
def build_enhanced_knowledge_base():
    """Build enhanced knowledge base with FAISS index for specific customer"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_rag_system(customer_id)
        rag_system.build_knowledge_base(customer_id)
        return jsonify({
            'status': 'success',
            'message': f'Enhanced knowledge base built successfully for customer {customer_id}',
            'customer_id': customer_id,
            'kpi_count': len(rag_system.kpi_data),
            'account_count': len(rag_system.account_data)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to build knowledge base: {str(e)}'}), 500

@enhanced_rag_openai_api.route('/api/rag-openai/query', methods=['POST'])
def enhanced_query():
    """Query the enhanced RAG system with OpenAI GPT-4 analysis (MCP-enhanced when enabled)"""
    customer_id = get_customer_id()
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query_text = data['query']
    query_type = data.get('query_type', 'general')
    conversation_history = data.get('conversation_history', [])
    
    # Auto-detect query type based on keywords
    if not query_type or query_type == 'auto':
        query_type = _detect_query_type(query_text)
    
    try:
        # ============================================
        # Check if MCP integration is enabled
        # ============================================
        from mcp_integration import is_mcp_enabled
        mcp_enabled = is_mcp_enabled(customer_id)
        
        if mcp_enabled:
            # Use MCP-enhanced RAG
            try:
                from enhanced_rag_with_mcp import EnhancedRAGWithMCP
                rag_system = EnhancedRAGWithMCP(customer_id)
                
                # Ensure knowledge base is built
                if not rag_system.faiss_index:
                    rag_system.build_knowledge_base(customer_id)
                
                # Query with MCP enhancement (async)
                result = rag_system.query_sync(query_text, query_type, conversation_history)
                
            except Exception as e:
                # Automatic fallback to standard RAG on any MCP error
                import logging
                logging.error(f"MCP-enhanced RAG failed, falling back: {e}")
                
                rag_system = get_rag_system(customer_id)
                if not rag_system.faiss_index:
                    rag_system.build_knowledge_base(customer_id)
                result = rag_system.query(query_text, query_type, conversation_history)
                result['mcp_enhanced'] = False
                result['mcp_fallback'] = True
                result['mcp_error'] = str(e)
        else:
            # Use standard RAG (existing functionality)
            rag_system = get_rag_system(customer_id)
            
            # Ensure knowledge base is built
            if not rag_system.faiss_index:
                rag_system.build_knowledge_base(customer_id)
            
            # Query the enhanced RAG system
            result = rag_system.query(query_text, query_type, conversation_history)
            result['mcp_enhanced'] = False
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Query failed: {str(e)}'}), 500

@enhanced_rag_openai_api.route('/api/rag-openai/revenue-analysis', methods=['GET'])
def analyze_revenue_drivers():
    """Analyze revenue drivers across accounts"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_rag_system(customer_id)
        
        # Ensure knowledge base is built
        if not rag_system.faiss_index:
            rag_system.build_knowledge_base(customer_id)
        
        analysis = rag_system.analyze_revenue_drivers(customer_id)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': f'Revenue analysis failed: {str(e)}'}), 500

@enhanced_rag_openai_api.route('/api/rag-openai/risk-analysis', methods=['GET'])
def analyze_at_risk_accounts():
    """Find accounts at risk of churn"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_rag_system(customer_id)
        
        # Ensure knowledge base is built
        if not rag_system.faiss_index:
            rag_system.build_knowledge_base(customer_id)
        
        analysis = rag_system.find_at_risk_accounts(customer_id)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': f'Risk analysis failed: {str(e)}'}), 500

@enhanced_rag_openai_api.route('/api/rag-openai/account/<int:account_id>', methods=['GET'])
def analyze_specific_account(account_id):
    """Analyze a specific account's performance"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_rag_system(customer_id)
        
        # Ensure knowledge base is built
        if not rag_system.faiss_index:
            rag_system.build_knowledge_base(customer_id)
        
        # Find account data
        account_data = None
        for account in rag_system.account_data:
            if account['account_id'] == account_id:
                account_data = account
                break
        
        if not account_data:
            return jsonify({'error': 'Account not found'}), 404
        
        # Get KPIs for this account
        account_kpis = [kpi for kpi in rag_system.kpi_data if kpi['account_id'] == account_id]
        
        # Create analysis query
        query_text = f"Analyze the performance of account {account_data['account_name']} with revenue ${account_data['revenue']:,.0f} in {account_data['industry']} industry"
        
        result = rag_system.query(query_text, 'account_analysis')
        
        return jsonify({
            'account': account_data,
            'kpi_count': len(account_kpis),
            'analysis': result
        })
    except Exception as e:
        return jsonify({'error': f'Account analysis failed: {str(e)}'}), 500

@enhanced_rag_openai_api.route('/api/rag-openai/industry/<industry>', methods=['GET'])
def analyze_industry_performance(industry):
    """Analyze performance by industry"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_rag_system(customer_id)
        
        # Ensure knowledge base is built
        if not rag_system.faiss_index:
            rag_system.build_knowledge_base(customer_id)
        
        # Filter data by industry
        industry_accounts = [acc for acc in rag_system.account_data if acc['industry'].lower() == industry.lower()]
        industry_kpis = [kpi for kpi in rag_system.kpi_data if kpi['industry'].lower() == industry.lower()]
        
        if not industry_accounts:
            return jsonify({'error': f'No data found for industry: {industry}'}), 404
        
        # Create analysis query
        total_revenue = sum(acc['revenue'] for acc in industry_accounts)
        query_text = f"Analyze the performance of {industry} industry with {len(industry_accounts)} accounts and total revenue ${total_revenue:,.0f}"
        
        result = rag_system.query(query_text, 'revenue_analysis')
        
        return jsonify({
            'industry': industry,
            'account_count': len(industry_accounts),
            'kpi_count': len(industry_kpis),
            'total_revenue': total_revenue,
            'accounts': industry_accounts,
            'analysis': result
        })
    except Exception as e:
        return jsonify({'error': f'Industry analysis failed: {str(e)}'}), 500

@enhanced_rag_openai_api.route('/api/rag-openai/top-accounts', methods=['GET'])
def get_top_accounts():
    """Get top accounts by revenue"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_rag_system(customer_id)
        
        # Ensure knowledge base is built
        if not rag_system.faiss_index:
            rag_system.build_knowledge_base(customer_id)
        
        # Sort accounts by revenue
        top_accounts = sorted(rag_system.account_data, key=lambda x: x['revenue'], reverse=True)
        
        return jsonify({
            'top_accounts': top_accounts[:10],  # Top 10
            'total_accounts': len(top_accounts),
            'total_revenue': sum(acc['revenue'] for acc in top_accounts)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get top accounts: {str(e)}'}), 500

@enhanced_rag_openai_api.route('/api/rag-openai/kpi-performance', methods=['GET'])
def analyze_kpi_performance():
    """Analyze KPI performance across all accounts"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_rag_system(customer_id)
        
        # Ensure knowledge base is built
        if not rag_system.faiss_index:
            rag_system.build_knowledge_base(customer_id)
        
        # Group KPIs by category
        kpi_by_category = {}
        for kpi in rag_system.kpi_data:
            category = kpi['category']
            if category not in kpi_by_category:
                kpi_by_category[category] = []
            kpi_by_category[category].append(kpi)
        
        # Create analysis query
        query_text = "Analyze KPI performance across all categories and provide insights on strengths and areas for improvement"
        
        result = rag_system.query(query_text, 'kpi_analysis')
        
        return jsonify({
            'kpi_by_category': kpi_by_category,
            'total_kpis': len(rag_system.kpi_data),
            'categories': list(kpi_by_category.keys()),
            'analysis': result
        })
    except Exception as e:
        return jsonify({'error': f'KPI analysis failed: {str(e)}'}), 500

@enhanced_rag_openai_api.route('/api/rag-openai/accounts/revenue', methods=['GET'])
def get_accounts_by_revenue():
    """Get accounts filtered by revenue criteria"""
    customer_id = get_customer_id()
    min_revenue = request.args.get('min_revenue', type=float)
    max_revenue = request.args.get('max_revenue', type=float)
    
    try:
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        if min_revenue:
            accounts = [acc for acc in accounts if float(acc.revenue) >= min_revenue]
        if max_revenue:
            accounts = [acc for acc in accounts if float(acc.revenue) <= max_revenue]
        
        # Sort by revenue descending
        accounts.sort(key=lambda x: float(x.revenue), reverse=True)
        
        result = {
            'accounts': [{
                'account_id': acc.account_id,
                'account_name': acc.account_name,
                'revenue': float(acc.revenue),
                'industry': acc.industry,
                'region': acc.region,
                'account_status': acc.account_status
            } for acc in accounts],
            'total_accounts': len(accounts),
            'total_revenue': sum(float(acc.revenue) for acc in accounts),
            'average_revenue': sum(float(acc.revenue) for acc in accounts) / len(accounts) if accounts else 0
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Failed to get accounts: {str(e)}'}), 500

@enhanced_rag_openai_api.route('/api/rag-openai/query-simple', methods=['POST'])
def simple_query():
    """Simple natural language query handler for revenue questions"""
    customer_id = get_customer_id()
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query_text = data['query'].lower()
    
    try:
        # Parse revenue questions
        if 'revenue' in query_text:
            import re
            amount_match = re.search(r'(\$?)(\d+(?:,\d+)*(?:\.\d+)?)([km]?)', query_text)
            
            if amount_match:
                amount_str = amount_match.group(2).replace(',', '')
                multiplier = 1000 if amount_match.group(3) == 'k' else 1000000 if amount_match.group(3) == 'm' else 1
                revenue_threshold = float(amount_str) * multiplier
                
                # Get all accounts
                accounts = Account.query.filter_by(customer_id=customer_id).all()
                
                # Determine filter type based on keywords
                if any(keyword in query_text for keyword in ['more than', 'greater than', 'above', 'over']):
                    # Filter for accounts with revenue >= threshold
                    filtered_accounts = [acc for acc in accounts if float(acc.revenue) >= revenue_threshold]
                    interpretation = f'Accounts with revenue >= ${revenue_threshold:,.0f}'
                elif any(keyword in query_text for keyword in ['less than', 'below', 'under', 'less']):
                    # Filter for accounts with revenue < threshold
                    filtered_accounts = [acc for acc in accounts if float(acc.revenue) < revenue_threshold]
                    interpretation = f'Accounts with revenue < ${revenue_threshold:,.0f}'
                else:
                    # Default to "above" if no clear direction specified
                    filtered_accounts = [acc for acc in accounts if float(acc.revenue) >= revenue_threshold]
                    interpretation = f'Accounts with revenue >= ${revenue_threshold:,.0f}'
                
                # Sort by revenue descending
                filtered_accounts.sort(key=lambda x: float(x.revenue), reverse=True)
                
                result = {
                    'query': data['query'],
                    'interpretation': interpretation,
                    'accounts': [{
                        'account_id': acc.account_id,
                        'account_name': acc.account_name,
                        'revenue': float(acc.revenue),
                        'industry': acc.industry,
                        'region': acc.region
                    } for acc in filtered_accounts],
                    'total_accounts': len(filtered_accounts),
                    'total_revenue': sum(float(acc.revenue) for acc in filtered_accounts),
                    'average_revenue': sum(float(acc.revenue) for acc in filtered_accounts) / len(filtered_accounts) if filtered_accounts else 0
                }
                
                return jsonify(result)
        
        # Handle other query types
        elif 'accounts' in query_text and 'revenue' in query_text:
            # Get all accounts sorted by revenue
            accounts = Account.query.filter_by(customer_id=customer_id).all()
            accounts.sort(key=lambda x: float(x.revenue), reverse=True)
            
            result = {
                'query': data['query'],
                'interpretation': 'All accounts sorted by revenue',
                'accounts': [{
                    'account_id': acc.account_id,
                    'account_name': acc.account_name,
                    'revenue': float(acc.revenue),
                    'industry': acc.industry,
                    'region': acc.region
                } for acc in accounts],
                'total_accounts': len(accounts),
                'total_revenue': sum(float(acc.revenue) for acc in accounts),
                'average_revenue': sum(float(acc.revenue) for acc in accounts) / len(accounts) if accounts else 0
            }
            
            return jsonify(result)
        
        else:
            return jsonify({
                'error': 'Query not understood. Try asking about accounts and revenue.',
                'supported_queries': [
                    'Which accounts have more than $1M revenue?',
                    'Which accounts have revenue below $900K?',
                    'Show me all accounts by revenue',
                    'Accounts with revenue above $500K',
                    'Accounts with revenue less than $200K'
                ]
            }), 400
            
    except Exception as e:
        return jsonify({'error': f'Query failed: {str(e)}'}), 500

def _detect_query_type(query_text: str) -> str:
    """Auto-detect query type based on keywords"""
    query_lower = query_text.lower()
    
    # Revenue-related keywords
    revenue_keywords = ['revenue', 'growth', 'money', 'dollar', 'profit', 'income', 'sales', 'earnings']
    if any(keyword in query_lower for keyword in revenue_keywords):
        return 'revenue_analysis'
    
    # Account-related keywords
    account_keywords = ['account', 'customer', 'client', 'relationship', 'engagement', 'satisfaction', 'churn']
    if any(keyword in query_lower for keyword in account_keywords):
        return 'account_analysis'
    
    # KPI-related keywords
    kpi_keywords = ['kpi', 'metric', 'performance', 'score', 'measurement', 'indicator']
    if any(keyword in query_lower for keyword in kpi_keywords):
        return 'kpi_analysis'
    
    return 'general'
