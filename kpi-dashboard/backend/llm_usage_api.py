"""
LLM Usage API
==============

Exposes LLM budget and usage data via REST endpoints.

Endpoints:
    GET /api/llm-usage/summary?customer_id=N          — daily/monthly usage stats
    GET /api/llm-usage/budget-status?customer_id=N     — remaining budget & circuit breaker status
"""

from flask import Blueprint, request, jsonify

llm_usage_api = Blueprint('llm_usage_api', __name__)


@llm_usage_api.route('/api/llm-usage/summary', methods=['GET'])
def llm_usage_summary():
    """
    Get LLM usage summary for a customer.

    Query params:
        customer_id (required): Customer (tenant) ID
        period (optional): 'daily' (default) or 'monthly'
    """
    customer_id = request.args.get('customer_id', type=int)
    if not customer_id:
        return jsonify({'error': 'customer_id is required'}), 400

    period = request.args.get('period', 'daily')
    if period not in ('daily', 'monthly'):
        return jsonify({'error': "period must be 'daily' or 'monthly'"}), 400

    try:
        from utils.llm_budget_controller import get_usage_summary, get_budget_status
        summary = get_usage_summary(customer_id, period=period)
        budget = get_budget_status(customer_id)
        return jsonify({
            'usage': summary,
            'budget': budget,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@llm_usage_api.route('/api/llm-usage/budget-status', methods=['GET'])
def llm_budget_status():
    """
    Get LLM budget status for a customer.

    Query params:
        customer_id (required): Customer (tenant) ID
    """
    customer_id = request.args.get('customer_id', type=int)
    if not customer_id:
        return jsonify({'error': 'customer_id is required'}), 400

    try:
        from utils.llm_budget_controller import get_budget_status
        status = get_budget_status(customer_id)
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
