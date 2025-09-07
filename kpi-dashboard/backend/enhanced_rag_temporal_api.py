#!/usr/bin/env python3
"""
API endpoints for Enhanced RAG System with Temporal Analysis
Provides monthly revenue tracking and time-series analysis capabilities
"""

from flask import Blueprint, request, jsonify
from enhanced_rag_temporal import temporal_rag_system

# Create blueprint
enhanced_rag_temporal_api = Blueprint('enhanced_rag_temporal_api', __name__)

@enhanced_rag_temporal_api.route('/api/rag-temporal/build', methods=['POST'])
def build_temporal_knowledge_base():
    """Build temporal knowledge base with time-series data"""
    try:
        customer_id = request.headers.get('X-Customer-ID')
        if not customer_id:
            return jsonify({"error": "Missing X-Customer-ID header"}), 400
        
        customer_id = int(customer_id)
        
        # Build knowledge base
        temporal_rag_system.build_knowledge_base(customer_id)
        
        return jsonify({
            "status": "success",
            "message": f"Temporal knowledge base built successfully for customer {customer_id}",
            "customer_id": customer_id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enhanced_rag_temporal_api.route('/api/rag-temporal/query', methods=['POST'])
def query_temporal_rag():
    """Query temporal RAG system with monthly revenue analysis"""
    try:
        customer_id = request.headers.get('X-Customer-ID')
        if not customer_id:
            return jsonify({"error": "Missing X-Customer-ID header"}), 400
        
        customer_id = int(customer_id)
        
        data = request.get_json()
        query = data.get('query', '')
        query_type = data.get('query_type', 'general')
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # Execute query
        result = temporal_rag_system.query(query, query_type)
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enhanced_rag_temporal_api.route('/api/rag-temporal/monthly-revenue', methods=['GET'])
def get_monthly_revenue():
    """Get monthly revenue breakdown for the customer"""
    try:
        customer_id = request.headers.get('X-Customer-ID')
        if not customer_id:
            return jsonify({"error": "Missing X-Customer-ID header"}), 400
        
        customer_id = int(customer_id)
        
        # Query for monthly revenue data
        result = temporal_rag_system.query(
            "Show me monthly revenue breakdown for the last 6 months with account details",
            "revenue_analysis"
        )
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enhanced_rag_temporal_api.route('/api/rag-temporal/revenue-trends', methods=['GET'])
def get_revenue_trends():
    """Get revenue trends and patterns analysis"""
    try:
        customer_id = request.headers.get('X-Customer-ID')
        if not customer_id:
            return jsonify({"error": "Missing X-Customer-ID header"}), 400
        
        customer_id = int(customer_id)
        
        # Query for revenue trends
        result = temporal_rag_system.query(
            "Analyze revenue trends and patterns over time, identify growth or decline patterns",
            "trend_analysis"
        )
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enhanced_rag_temporal_api.route('/api/rag-temporal/top-accounts-monthly', methods=['GET'])
def get_top_accounts_monthly():
    """Get top performing accounts by month"""
    try:
        customer_id = request.headers.get('X-Customer-ID')
        if not customer_id:
            return jsonify({"error": "Missing X-Customer-ID header"}), 400
        
        customer_id = int(customer_id)
        
        # Query for top accounts by month
        result = temporal_rag_system.query(
            "Which accounts performed best each month? Show monthly rankings and revenue changes",
            "account_analysis"
        )
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enhanced_rag_temporal_api.route('/api/rag-temporal/status', methods=['GET'])
def get_temporal_status():
    """Get status of temporal knowledge base"""
    try:
        customer_id = request.headers.get('X-Customer-ID')
        if not customer_id:
            return jsonify({"error": "Missing X-Customer-ID header"}), 400
        
        customer_id = int(customer_id)
        
        # Check if knowledge base is built
        if temporal_rag_system.customer_id != customer_id:
            return jsonify({
                "status": "not_built",
                "message": "Temporal knowledge base not built for this customer",
                "customer_id": customer_id
            })
        
        return jsonify({
            "status": "ready",
            "message": "Temporal knowledge base is ready",
            "customer_id": customer_id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
