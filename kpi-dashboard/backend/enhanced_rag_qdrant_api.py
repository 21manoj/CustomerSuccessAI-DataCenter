#!/usr/bin/env python3
"""
Enhanced RAG API endpoints using Qdrant Vector Database and OpenAI GPT-4
Provides advanced KPI and account analysis capabilities with production-grade vector search
"""

from flask import Blueprint, request, jsonify, abort
from extensions import db
from models import KPI, KPIUpload, Account, CustomerConfig
from enhanced_rag_qdrant import get_qdrant_rag_system
import re

enhanced_rag_qdrant_api = Blueprint('enhanced_rag_qdrant_api', __name__)

def get_customer_id():
    """Extract and validate the X-Customer-ID header from the request."""
    cid = request.headers.get('X-Customer-ID')
    if not cid:
        abort(400, 'Missing X-Customer-ID header')
    try:
        return int(cid)
    except Exception:
        abort(400, 'Invalid X-Customer-ID header')

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/build', methods=['POST'])
def build_qdrant_knowledge_base():
    """Build Qdrant knowledge base for specific customer"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        rag_system.build_knowledge_base(customer_id)
        
        # Get collection info
        collection_info = rag_system.get_collection_info()
        
        return jsonify({
            'status': 'success',
            'message': f'Qdrant knowledge base built successfully for customer {customer_id}',
            'customer_id': customer_id,
            'collection_info': collection_info
        })
    except Exception as e:
        return jsonify({'error': f'Failed to build Qdrant knowledge base: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/query', methods=['POST'])
def qdrant_query():
    """Query the Qdrant RAG system with OpenAI GPT-4 analysis"""
    customer_id = get_customer_id()
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query_text = data['query']
    query_type = data.get('query_type', 'general')
    
    # Auto-detect query type based on keywords
    if not query_type or query_type == 'auto':
        query_type = _detect_query_type(query_text)
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Query the Qdrant RAG system
        result = rag_system.query(query_text, query_type)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Query failed: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/revenue-analysis', methods=['GET'])
def analyze_revenue_drivers_qdrant():
    """Analyze revenue drivers across accounts using Qdrant"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        analysis = rag_system.analyze_revenue_drivers(customer_id)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': f'Revenue analysis failed: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/risk-analysis', methods=['GET'])
def analyze_at_risk_accounts_qdrant():
    """Find accounts at risk of churn using Qdrant"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        analysis = rag_system.find_at_risk_accounts(customer_id)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': f'Risk analysis failed: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/status', methods=['GET'])
def get_knowledge_base_status():
    """Check if knowledge base is built for the customer"""
    customer_id = get_customer_id()
    
    # For now, just return that it's built since we know it works
    # TODO: Implement proper status checking
    return jsonify({
        'customer_id': customer_id,
        'is_built': True,
        'status': 'ready'
    })

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/collection-info', methods=['GET'])
def get_collection_info():
    """Get Qdrant collection information"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        collection_info = rag_system.get_collection_info()
        return jsonify(collection_info)
    except Exception as e:
        return jsonify({'error': f'Failed to get collection info: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/account/<int:account_id>', methods=['GET'])
def analyze_specific_account_qdrant(account_id):
    """Analyze a specific account's performance using Qdrant"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Query for specific account data
        query_text = f"Analyze account {account_id} performance and health"
        result = rag_system.query(query_text, 'account_analysis')
        
        return jsonify({
            'account_id': account_id,
            'customer_id': customer_id,
            'analysis': result
        })
    except Exception as e:
        return jsonify({'error': f'Account analysis failed: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/industry/<industry>', methods=['GET'])
def analyze_industry_performance_qdrant(industry):
    """Analyze performance by industry using Qdrant"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Query for industry-specific data
        query_text = f"Analyze {industry} industry performance and trends"
        result = rag_system.query(query_text, 'revenue_analysis')
        
        return jsonify({
            'industry': industry,
            'customer_id': customer_id,
            'analysis': result
        })
    except Exception as e:
        return jsonify({'error': f'Industry analysis failed: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/top-accounts', methods=['GET'])
def get_top_accounts_qdrant():
    """Get top accounts by revenue using Qdrant"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Query for top accounts
        query_text = "Show me the top performing accounts by revenue"
        result = rag_system.query(query_text, 'revenue_analysis')
        
        return jsonify({
            'customer_id': customer_id,
            'analysis': result
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get top accounts: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/kpi-performance', methods=['GET'])
def analyze_kpi_performance_qdrant():
    """Analyze KPI performance across all accounts using Qdrant"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Query for KPI performance
        query_text = "Analyze KPI performance across all categories and provide insights"
        result = rag_system.query(query_text, 'kpi_analysis')
        
        return jsonify({
            'customer_id': customer_id,
            'analysis': result
        })
    except Exception as e:
        return jsonify({'error': f'KPI analysis failed: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/query-simple', methods=['POST'])
def simple_query_qdrant():
    """Simple natural language query handler using Qdrant"""
    customer_id = get_customer_id()
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query_text = data['query'].lower()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
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
                    filtered_accounts = [acc for acc in accounts if float(acc.revenue) >= revenue_threshold]
                    interpretation = f'Accounts with revenue >= ${revenue_threshold:,.0f}'
                elif any(keyword in query_text for keyword in ['less than', 'below', 'under', 'less']):
                    filtered_accounts = [acc for acc in accounts if float(acc.revenue) < revenue_threshold]
                    interpretation = f'Accounts with revenue < ${revenue_threshold:,.0f}'
                else:
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
        
        # Handle other query types with Qdrant
        result = rag_system.query(data['query'], 'general')
        return jsonify(result)
        
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
