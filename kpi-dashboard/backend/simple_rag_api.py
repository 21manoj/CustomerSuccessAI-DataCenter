#!/usr/bin/env python3
"""
Simple RAG API endpoints
"""

from flask import Blueprint, request, jsonify, abort
from auth_middleware import get_current_customer_id, get_current_user_id
from simple_rag_system import simple_rag_system

simple_rag_api = Blueprint('simple_rag_api', __name__)

def get_current_customer_id():
    """Extract and validate the X-Customer-ID header from the request."""
    cid = get_current_customer_id()
    if not cid:
        abort(400, 'Authentication required (handled by middleware)')
    try:
        return int(cid)
    except Exception:
        abort(400, 'Invalid authentication (handled by middleware)')

@simple_rag_api.route('/api/simple-rag/build', methods=['POST'])
def build_simple_knowledge_base():
    """Build simple knowledge base for specific customer"""
    customer_id = get_current_customer_id()
    
    try:
        simple_rag_system.build_knowledge_base(customer_id)
        
        return jsonify({
            'status': 'success',
            'message': f'Simple knowledge base built successfully for customer {customer_id}',
            'customer_id': customer_id,
            'records_count': len(simple_rag_system.data)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to build simple knowledge base: {str(e)}'}), 500

@simple_rag_api.route('/api/simple-rag/query', methods=['POST'])
def simple_query():
    """Query the simple RAG system"""
    customer_id = get_current_customer_id()
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query_text = data['query']
    query_type = data.get('query_type', 'general')
    
    try:
        result = simple_rag_system.query(query_text, query_type)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Query failed: {str(e)}'}), 500

@simple_rag_api.route('/api/simple-rag/status', methods=['GET'])
def simple_status():
    """Get simple RAG system status"""
    customer_id = get_current_customer_id()
    
    is_built = simple_rag_system.customer_id == customer_id and len(simple_rag_system.data) > 0
    
    return jsonify({
        'customer_id': customer_id,
        'is_built': is_built,
        'status': 'ready' if is_built else 'not_built',
        'records_count': len(simple_rag_system.data) if is_built else 0
    })
