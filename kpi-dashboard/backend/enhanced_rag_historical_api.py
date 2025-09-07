#!/usr/bin/env python3
"""
Enhanced Historical RAG API endpoints
Provides temporal analysis, trend analysis, and historical insights
"""

from flask import Blueprint, request, jsonify, abort
from extensions import db
from models import KPI, KPIUpload, Account, HealthTrend
from enhanced_rag_historical import get_historical_rag_system
import re

enhanced_rag_historical_api = Blueprint('enhanced_rag_historical_api', __name__)

def get_customer_id():
    """Extract and validate the X-Customer-ID header from the request."""
    cid = request.headers.get('X-Customer-ID')
    if not cid:
        abort(400, 'Missing X-Customer-ID header')
    try:
        return int(cid)
    except Exception:
        abort(400, 'Invalid X-Customer-ID header')

@enhanced_rag_historical_api.route('/api/rag-historical/build', methods=['POST'])
def build_historical_knowledge_base():
    """Build historical knowledge base with temporal data"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_historical_rag_system(customer_id)
        rag_system.build_historical_knowledge_base(customer_id)
        
        # Get collection info
        collection_info = rag_system.qdrant_client.get_collection(rag_system.collection_name)
        
        return jsonify({
            'status': 'success',
            'message': f'Historical knowledge base built successfully for customer {customer_id}',
            'customer_id': customer_id,
            'collection_info': {
                'collection_name': rag_system.collection_name,
                'vectors_count': collection_info.vectors_count,
                'indexed_vectors_count': collection_info.indexed_vectors_count,
                'status': str(collection_info.status)
            }
        })
    except Exception as e:
        return jsonify({'error': f'Failed to build historical knowledge base: {str(e)}'}), 500

@enhanced_rag_historical_api.route('/api/rag-historical/query', methods=['POST'])
def historical_query():
    """Query the historical RAG system with temporal analysis"""
    customer_id = get_customer_id()
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query_text = data['query']
    query_type = data.get('query_type', 'general')
    
    # Auto-detect query type based on keywords
    if not query_type or query_type == 'auto':
        query_type = _detect_historical_query_type(query_text)
    
    try:
        rag_system = get_historical_rag_system(customer_id)
        result = rag_system.query_historical(query_text, query_type)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Historical query failed: {str(e)}'}), 500

@enhanced_rag_historical_api.route('/api/rag-historical/trend-analysis', methods=['GET'])
def analyze_trends():
    """Analyze trends across all KPIs and accounts"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_historical_rag_system(customer_id)
        
        # Query for trend analysis
        result = rag_system.query_historical(
            "Analyze trends across all KPIs and accounts. Show me which metrics are improving, declining, or stable over time.",
            'trend_analysis'
        )
        
        return jsonify({
            'customer_id': customer_id,
            'analysis_type': 'trend_analysis',
            'result': result
        })
    except Exception as e:
        return jsonify({'error': f'Trend analysis failed: {str(e)}'}), 500

@enhanced_rag_historical_api.route('/api/rag-historical/temporal-analysis', methods=['GET'])
def analyze_temporal_patterns():
    """Analyze temporal patterns and seasonality"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_historical_rag_system(customer_id)
        
        # Query for temporal analysis
        result = rag_system.query_historical(
            "Analyze temporal patterns and seasonality in the data. Identify any cyclical trends, anomalies, or time-based correlations.",
            'temporal_analysis'
        )
        
        return jsonify({
            'customer_id': customer_id,
            'analysis_type': 'temporal_analysis',
            'result': result
        })
    except Exception as e:
        return jsonify({'error': f'Temporal analysis failed: {str(e)}'}), 500

@enhanced_rag_historical_api.route('/api/rag-historical/kpi-trends/<kpi_name>', methods=['GET'])
def analyze_kpi_trends(kpi_name):
    """Analyze trends for a specific KPI"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_historical_rag_system(customer_id)
        
        # Query for specific KPI trends
        result = rag_system.query_historical(
            f"Analyze the historical trends and patterns for {kpi_name}. Show me the trend direction, volatility, and any insights about this KPI over time.",
            'trend_analysis'
        )
        
        return jsonify({
            'customer_id': customer_id,
            'kpi_name': kpi_name,
            'analysis_type': 'kpi_trends',
            'result': result
        })
    except Exception as e:
        return jsonify({'error': f'KPI trend analysis failed: {str(e)}'}), 500

@enhanced_rag_historical_api.route('/api/rag-historical/account-trends/<int:account_id>', methods=['GET'])
def analyze_account_trends(account_id):
    """Analyze trends for a specific account"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_historical_rag_system(customer_id)
        
        # Query for specific account trends
        result = rag_system.query_historical(
            f"Analyze the historical trends and performance for account {account_id}. Show me how this account's KPIs have changed over time and identify any patterns or insights.",
            'trend_analysis'
        )
        
        return jsonify({
            'customer_id': customer_id,
            'account_id': account_id,
            'analysis_type': 'account_trends',
            'result': result
        })
    except Exception as e:
        return jsonify({'error': f'Account trend analysis failed: {str(e)}'}), 500

@enhanced_rag_historical_api.route('/api/rag-historical/health-evolution', methods=['GET'])
def analyze_health_evolution():
    """Analyze health score evolution over time"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_historical_rag_system(customer_id)
        
        # Query for health evolution
        result = rag_system.query_historical(
            "Analyze the evolution of health scores over time. Show me how overall health, business outcomes, customer sentiment, and other health metrics have changed.",
            'trend_analysis'
        )
        
        return jsonify({
            'customer_id': customer_id,
            'analysis_type': 'health_evolution',
            'result': result
        })
    except Exception as e:
        return jsonify({'error': f'Health evolution analysis failed: {str(e)}'}), 500

@enhanced_rag_historical_api.route('/api/rag-historical/predictive-insights', methods=['GET'])
def get_predictive_insights():
    """Get predictive insights based on historical data"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_historical_rag_system(customer_id)
        
        # Query for predictive insights
        result = rag_system.query_historical(
            "Based on the historical data, provide predictive insights about future performance. Identify which KPIs are likely to improve or decline, and what actions should be taken.",
            'general'
        )
        
        return jsonify({
            'customer_id': customer_id,
            'analysis_type': 'predictive_insights',
            'result': result
        })
    except Exception as e:
        return jsonify({'error': f'Predictive insights failed: {str(e)}'}), 500

@enhanced_rag_historical_api.route('/api/rag-historical/collection-info', methods=['GET'])
def get_historical_collection_info():
    """Get historical collection information"""
    customer_id = get_customer_id()
    
    try:
        rag_system = get_historical_rag_system(customer_id)
        collection_info = rag_system.qdrant_client.get_collection(rag_system.collection_name)
        
        return jsonify({
            'collection_name': rag_system.collection_name,
            'vectors_count': collection_info.vectors_count,
            'indexed_vectors_count': collection_info.indexed_vectors_count,
            'status': str(collection_info.status)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get collection info: {str(e)}'}), 500

def _detect_historical_query_type(query_text: str) -> str:
    """Auto-detect query type based on keywords"""
    query_lower = query_text.lower()
    
    # Trend-related keywords
    trend_keywords = ['trend', 'trending', 'change', 'improve', 'decline', 'increase', 'decrease', 'over time', 'evolution']
    if any(keyword in query_lower for keyword in trend_keywords):
        return 'trend_analysis'
    
    # Temporal-related keywords
    temporal_keywords = ['temporal', 'time', 'seasonal', 'cyclical', 'pattern', 'anomaly', 'correlation', 'historical']
    if any(keyword in query_lower for keyword in temporal_keywords):
        return 'temporal_analysis'
    
    # Predictive keywords
    predictive_keywords = ['predict', 'forecast', 'future', 'will', 'likely', 'should', 'recommendation']
    if any(keyword in query_lower for keyword in predictive_keywords):
        return 'general'  # Will use general with predictive context
    
    return 'general'
