"""
Vertical-Agnostic API v1 Routes

Proxy layer that delegates to vertical-specific handlers (currently DC2S)
while injecting vertical context (pillar labels, KPI labels) into responses.
All persona dashboards should call /api/v1/* instead of /api/dc2s/*.

The /api/dc2s/* routes remain as aliases for backward compatibility.
"""

import logging
from flask import Blueprint, jsonify, request
from auth_middleware import get_current_customer_id

logger = logging.getLogger(__name__)

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')


# ─── Vertical resolution helpers ────────────────────────────────────────────

def _resolve_vertical(customer_id):
    """Return vertical slug for a customer."""
    try:
        from utils.vertical_registry import get_vertical_for_customer
        return get_vertical_for_customer(int(customer_id))
    except Exception:
        return 'dc2_s'


def _get_pillar_labels(customer_id):
    """Return {P1: 'Deployment Velocity', ...} for the customer's vertical."""
    try:
        from utils.vertical_registry import get_catalog_for_customer
        pillars, _ = get_catalog_for_customer(int(customer_id))
        return {code: p.get('name', code) for code, p in pillars.items()}
    except Exception:
        return {}


def _get_kpi_labels(customer_id):
    """Return {P1-KPI1: 'Time-to-First-Workload', ...} for the customer's vertical."""
    try:
        from utils.vertical_registry import get_catalog_for_customer
        _, kpis = get_catalog_for_customer(int(customer_id))
        return {code: k.get('name', code) for code, k in kpis.items()}
    except Exception:
        return {}


def _inject_vertical_context(data, customer_id):
    """Add vertical, pillar_labels, kpi_labels to a response dict."""
    data['vertical'] = _resolve_vertical(customer_id)
    data['pillar_labels'] = _get_pillar_labels(customer_id)
    data['kpi_labels'] = _get_kpi_labels(customer_id)
    return data


def _proxy(handler_fn, inject_context=True, **kwargs):
    """Call a DC2S handler and optionally inject vertical context.

    Returns the Flask response directly. If the handler returns 200 and
    inject_context is True, vertical/pillar/kpi labels are added to the JSON.
    """
    response = handler_fn(**kwargs) if kwargs else handler_fn()

    if inject_context and hasattr(response, 'status_code') and response.status_code == 200:
        try:
            data = response.get_json()
            if isinstance(data, dict):
                customer_id = get_current_customer_id()
                if customer_id:
                    _inject_vertical_context(data, customer_id)
                return jsonify(data)
        except Exception as e:
            logger.debug("v1 proxy context injection failed (non-fatal): %s", e)

    return response


# ─── Proxy Routes ────────────────────────────────────────────────────────────

@api_v1.route('/accounts')
def v1_accounts():
    """List all accounts with health scores — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_dc2s_accounts
    return _proxy(get_dc2s_accounts)


@api_v1.route('/accounts/<int:account_id>')
def v1_account_detail(account_id):
    """Account detail — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_dc2s_account_detail
    return _proxy(get_dc2s_account_detail, account_id=account_id)


@api_v1.route('/health-scores/<int:account_id>')
def v1_health_score(account_id):
    """Health score for a single account — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_dc2s_health_score
    return _proxy(get_dc2s_health_score, account_id=account_id)


@api_v1.route('/health-summary')
def v1_health_summary():
    """Portfolio health summary — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_dc2s_health_summary
    return _proxy(get_dc2s_health_summary)


@api_v1.route('/health-score-history')
def v1_health_score_history():
    """Health score history — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_health_score_history_api
    return _proxy(get_health_score_history_api)


@api_v1.route('/daily-actions')
def v1_daily_actions():
    """CSM daily actions — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_csm_daily_actions
    return _proxy(get_csm_daily_actions)


@api_v1.route('/recommendations/<int:account_id>')
def v1_recommendations(account_id):
    """Playbook recommendations for an account — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_dc2s_recommendations
    return _proxy(get_dc2s_recommendations, account_id=account_id)


@api_v1.route('/alerts/<int:account_id>')
def v1_alerts(account_id):
    """Alerts for an account — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_dc2s_alerts
    return _proxy(get_dc2s_alerts, account_id=account_id)


@api_v1.route('/team-capacity')
def v1_team_capacity():
    """Team capacity — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_team_capacity_api
    return _proxy(get_team_capacity_api)


@api_v1.route('/csm-scorecard')
def v1_csm_scorecard():
    """CSM scorecard — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_csm_scorecard_api
    return _proxy(get_csm_scorecard_api)


@api_v1.route('/playbook-success-metrics')
def v1_playbook_success_metrics():
    """Playbook success metrics — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_playbook_success_metrics_api
    return _proxy(get_playbook_success_metrics_api)
