"""
LLM Usage API
==============

Exposes LLM budget and usage data via REST endpoints.

Endpoints:
    GET  /api/llm-usage/summary?customer_id=N          — daily/monthly usage stats
    GET  /api/llm-usage/budget-status?customer_id=N     — remaining budget & circuit breaker status
    GET  /api/llm-usage/budget-config?customer_id=N     — current budget config (or defaults)
    PUT  /api/llm-usage/budget-config                   — update budget limits
    GET  /api/llm-usage/recent?customer_id=N&limit=10   — recent LLM usage log entries
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


@llm_usage_api.route('/api/llm-usage/budget-config', methods=['GET'])
def llm_budget_config_get():
    """
    Get current LLM budget configuration for a customer.

    Query params:
        customer_id (required): Customer (tenant) ID

    Returns defaults if no custom config is set.
    """
    customer_id = request.args.get('customer_id', type=int)
    if not customer_id:
        return jsonify({'error': 'customer_id is required'}), 400

    try:
        from utils.llm_budget_controller import (
            DEFAULT_DAILY_LLM_CALLS, DEFAULT_DAILY_LLM_BUDGET_USD,
            DEFAULT_MONTHLY_LLM_BUDGET_USD, DEFAULT_MAX_PROACTIVE_CALLS_PER_RUN,
        )
        from models import CustomerConfig

        defaults = {
            'daily_calls': DEFAULT_DAILY_LLM_CALLS,
            'daily_usd': DEFAULT_DAILY_LLM_BUDGET_USD,
            'monthly_usd': DEFAULT_MONTHLY_LLM_BUDGET_USD,
            'max_proactive_per_run': DEFAULT_MAX_PROACTIVE_CALLS_PER_RUN,
        }

        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if config and config.dc2s_kpi_overrides and isinstance(config.dc2s_kpi_overrides, dict):
            llm = config.dc2s_kpi_overrides.get('llm_budget', {})
            return jsonify({
                'customer_id': customer_id,
                'daily_calls': llm.get('daily_calls', defaults['daily_calls']),
                'daily_usd': llm.get('daily_usd', defaults['daily_usd']),
                'monthly_usd': llm.get('monthly_usd', defaults['monthly_usd']),
                'max_proactive_per_run': llm.get('max_proactive', defaults['max_proactive_per_run']),
                'is_custom': True,
            })

        return jsonify({
            'customer_id': customer_id,
            **defaults,
            'is_custom': False,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@llm_usage_api.route('/api/llm-usage/budget-config', methods=['PUT'])
def llm_budget_config_put():
    """
    Update LLM budget configuration for a customer.

    JSON body:
        customer_id (required): Customer (tenant) ID
        daily_calls (optional): Daily call limit
        daily_usd (optional): Daily spend limit in USD
        monthly_usd (optional): Monthly spend limit in USD
        max_proactive_per_run (optional): Max proactive calls per run
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    customer_id = data.get('customer_id')
    if not customer_id:
        return jsonify({'error': 'customer_id is required'}), 400

    try:
        from extensions import db
        from models import CustomerConfig

        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            return jsonify({'error': f'No config found for customer {customer_id}'}), 404

        # Merge into existing overrides
        overrides = config.dc2s_kpi_overrides or {}
        if not isinstance(overrides, dict):
            overrides = {}

        llm_budget = overrides.get('llm_budget', {})
        if 'daily_calls' in data:
            llm_budget['daily_calls'] = int(data['daily_calls'])
        if 'daily_usd' in data:
            llm_budget['daily_usd'] = float(data['daily_usd'])
        if 'monthly_usd' in data:
            llm_budget['monthly_usd'] = float(data['monthly_usd'])
        if 'max_proactive_per_run' in data:
            llm_budget['max_proactive'] = int(data['max_proactive_per_run'])

        overrides['llm_budget'] = llm_budget
        config.dc2s_kpi_overrides = overrides
        # Force SQLAlchemy to detect the JSON change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(config, 'dc2s_kpi_overrides')
        db.session.commit()

        return jsonify({
            'ok': True,
            'customer_id': customer_id,
            'llm_budget': llm_budget,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@llm_usage_api.route('/api/llm-usage/recent', methods=['GET'])
def llm_usage_recent():
    """
    Get recent LLM usage log entries for a customer.

    Query params:
        customer_id (required): Customer (tenant) ID
        limit (optional): Number of entries to return (default 10, max 100)
    """
    customer_id = request.args.get('customer_id', type=int)
    if not customer_id:
        return jsonify({'error': 'customer_id is required'}), 400

    limit = min(request.args.get('limit', 10, type=int), 100)

    try:
        from extensions import db

        rows = db.session.execute(db.text("""
            SELECT module, model, tokens_in, tokens_out,
                   cost_estimate_usd, success, error_message, created_at
            FROM llm_usage_log
            WHERE customer_id = :cid
            ORDER BY created_at DESC
            LIMIT :lim
        """), {'cid': customer_id, 'lim': limit}).fetchall()

        entries = []
        for row in rows:
            entries.append({
                'module': row[0],
                'model': row[1],
                'tokens_in': int(row[2]) if row[2] else 0,
                'tokens_out': int(row[3]) if row[3] else 0,
                'cost_usd': float(row[4]) if row[4] else 0.0,
                'success': bool(row[5]),
                'error_message': row[6],
                'timestamp': row[7].isoformat() if row[7] else None,
            })

        return jsonify({
            'customer_id': customer_id,
            'entries': entries,
            'count': len(entries),
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
