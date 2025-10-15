#!/usr/bin/env python3
"""
Simple Working RAG API endpoints
"""

from flask import Blueprint, request, jsonify, abort
from simple_working_rag import simple_working_rag

simple_working_rag_api = Blueprint('simple_working_rag_api', __name__)

def get_customer_id():
    """Extract and validate the X-Customer-ID header from the request."""
    cid = request.headers.get('X-Customer-ID')
    if not cid:
        abort(400, 'Missing X-Customer-ID header')
    try:
        return int(cid)
    except Exception:
        abort(400, 'Invalid X-Customer-ID header')

@simple_working_rag_api.route('/api/simple-working-rag/build', methods=['POST'])
def build_simple_working_knowledge_base():
    """Build simple working knowledge base for specific customer"""
    customer_id = get_customer_id()
    
    try:
        simple_working_rag.build_knowledge_base(customer_id)
        
        return jsonify({
            'status': 'success',
            'message': f'Simple working knowledge base built successfully for customer {customer_id}',
            'customer_id': customer_id,
            'records_count': len(simple_working_rag.data)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to build simple working knowledge base: {str(e)}'}), 500

@simple_working_rag_api.route('/api/simple-working-rag/query', methods=['POST'])
def simple_working_query():
    """Query the simple working RAG system"""
    customer_id = get_customer_id()
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query_text = data['query']
    query_type = data.get('query_type', 'general')
    
    try:
        result = simple_working_rag.query(query_text, query_type)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Query failed: {str(e)}'}), 500

@simple_working_rag_api.route('/api/simple-working-rag/status', methods=['GET'])
def simple_working_status():
    """Get simple working RAG system status"""
    customer_id = get_customer_id()
    
    is_built = simple_working_rag.customer_id == customer_id and len(simple_working_rag.data) > 0
    
    return jsonify({
        'customer_id': customer_id,
        'is_built': is_built,
        'status': 'ready' if is_built else 'not_built',
        'records_count': len(simple_working_rag.data) if is_built else 0
    })
