"""
Vertical-Agnostic API v1 Routes

Proxy layer that dispatches to the correct vertical handler based on the
customer's configuration, while injecting vertical context (pillar labels,
KPI labels) into responses.

Dispatch order:
  1. Check if a vertical-specific handler exists (e.g., saas_premium.api_routes.get_accounts)
  2. Fall back to DC2S handler (works for all verticals since it queries by customer_id)

All persona dashboards call /api/v1/* instead of /api/dc2s/*.
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


# ─── Vertical dispatch ───────────────────────────────────────────────────────

# Registry of vertical-specific handler overrides.
# Key: (vertical_slug, endpoint_name) → callable
# When a SaaS-specific handler is created, register it here.
# Example: _VERTICAL_HANDLERS[('saas_premium', 'accounts')] = saas_get_accounts
_VERTICAL_HANDLERS = {}


def _dispatch(endpoint_name, default_handler, inject_context=True, **kwargs):
    """Dispatch to vertical-specific handler if one exists, else use default.

    1. Resolve customer's vertical
    2. Check _VERTICAL_HANDLERS for a vertical-specific override
    3. Fall back to default_handler (DC2S — works for all verticals)
    4. Inject vertical context into successful responses
    """
    customer_id = get_current_customer_id()
    vertical = _resolve_vertical(customer_id) if customer_id else 'dc2_s'

    # Check for vertical-specific override
    handler = _VERTICAL_HANDLERS.get((vertical, endpoint_name))
    if handler is None:
        handler = default_handler

    # Call the handler
    response = handler(**kwargs) if kwargs else handler()

    # Inject vertical context
    if inject_context and hasattr(response, 'status_code') and response.status_code == 200:
        try:
            data = response.get_json()
            if isinstance(data, dict) and customer_id:
                _inject_vertical_context(data, customer_id)
                return jsonify(data)
        except Exception as e:
            logger.debug("v1 dispatch context injection failed (non-fatal): %s", e)

    return response


# ─── Proxy Routes ────────────────────────────────────────────────────────────

@api_v1.route('/accounts')
def v1_accounts():
    """List all accounts with health scores — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_dc2s_accounts
    return _dispatch('accounts', get_dc2s_accounts)


@api_v1.route('/accounts/<int:account_id>')
def v1_account_detail(account_id):
    """Account detail — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_dc2s_account_detail
    return _dispatch('account_detail', get_dc2s_account_detail, account_id=account_id)


@api_v1.route('/health-scores/<int:account_id>')
def v1_health_score(account_id):
    """Health score for a single account — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_dc2s_health_score
    return _dispatch('health_score', get_dc2s_health_score, account_id=account_id)


@api_v1.route('/health-summary')
def v1_health_summary():
    """Portfolio health summary — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_dc2s_health_summary
    return _dispatch('health_summary', get_dc2s_health_summary)


@api_v1.route('/health-score-history')
def v1_health_score_history():
    """Health score history — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_health_score_history_api
    return _dispatch('health_score_history', get_health_score_history_api)


@api_v1.route('/daily-actions')
def v1_daily_actions():
    """CSM daily actions — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_csm_daily_actions
    return _dispatch('daily_actions', get_csm_daily_actions)


@api_v1.route('/recommendations/<int:account_id>')
def v1_recommendations(account_id):
    """Playbook recommendations for an account — vertical-aware.

    Routes through ``playbook_recommendations_api.get_recommendations_for_account``
    so SaaS Premium tenants (and any non-DC2S vertical) get the SaaS playbook
    catalog (``activation-blitz``, ``voc-sprint``, ``renewal-safeguard``, ...)
    instead of falling through to the DC2S-only ``get_dc2s_recommendations``
    handler, which only knows about ``PB-01``..``PB-06``.

    Response shape (normalized for CSMCockpit drill drawer):
      {
        "account_id": int,
        "account_name": str,
        "vertical": "saas_premium" | "dc2_s" | ...,
        "overall_health": float | null,
        "recommendations": [
          {
            "playbook_id": "activation-blitz" | "PB-01" | ...,
            "playbook_name": "Activation Blitz",
            "priority": "critical" | "high" | "medium",
            "reasons": [...],
            "rationale": "<one-line summary>",
            ...
          },
          ...
        ],
        "total": int
      }
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        from models import Account
        from playbook_recommendations_api import get_recommendations_for_account
        from utils.vertical_health import (
            get_health_calculator,
            get_trailing_kpi_values_func,
            get_precalculated_scores,
        )

        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=int(customer_id),
        ).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404

        # Build kpi_values + health for the DC2S evaluator branch.
        # SaaS-path evaluators in get_recommendations_for_account ignore
        # kpi_values (they read the DB themselves), so it's safe to pass.
        _get_trailing_kpi_values = get_trailing_kpi_values_func(int(customer_id))
        calculate_kpi_health = get_health_calculator(int(customer_id))
        kpi_values = _get_trailing_kpi_values(account_id) or {}
        precalc_health, _, _ = get_precalculated_scores(account_id)
        if precalc_health is not None:
            health = float(precalc_health)
        else:
            try:
                health, _ = calculate_kpi_health(kpi_values, int(customer_id))
            except Exception:
                health = None

        raw = get_recommendations_for_account(
            account_id=account_id,
            customer_id=int(customer_id),
            health_score=health,
            kpi_values=kpi_values,
        )

        # Normalize the response so CSMCockpit's drill drawer renders the
        # same fields whether the tenant is DC2S or SaaS-flavored. The
        # vertical-aware engine emits ``urgency_level`` ("Critical"/"High"/
        # "Medium"); DC2S API previously emitted lowercase ``priority``.
        recs_in = raw.get('recommendations', []) if isinstance(raw, dict) else []
        recs_out = []
        for r in recs_in:
            priority = (
                r.get('priority')
                or (r.get('urgency_level') or 'medium')
            )
            priority_lc = str(priority).strip().lower()
            reasons = r.get('reasons') or r.get('action_items') or []
            rationale = r.get('rationale')
            if not rationale:
                rationale = reasons[0] if reasons else r.get('estimated_impact', '')
            recs_out.append({
                **r,
                'priority': priority_lc,
                'urgency_level': priority,
                'reasons': reasons,
                'rationale': rationale,
            })

        return jsonify({
            'account_id': account_id,
            'account_name': account.account_name,
            'vertical': raw.get('vertical') if isinstance(raw, dict) else None,
            'overall_health': raw.get('health_score') if isinstance(raw, dict) else health,
            'playbook_source': raw.get('playbook_source') if isinstance(raw, dict) else None,
            'recommendations': recs_out,
            'total': len(recs_out),
        })

    except Exception as e:
        logger.error(
            "v1_recommendations failed for account=%s customer=%s: %s",
            account_id, customer_id, e, exc_info=True,
        )
        return jsonify({
            'error': 'Failed to fetch recommendations',
            'account_id': account_id,
            'recommendations': [],
            'total': 0,
        }), 500


@api_v1.route('/alerts/<int:account_id>')
def v1_alerts(account_id):
    """Alerts for an account — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_dc2s_alerts
    return _dispatch('alerts', get_dc2s_alerts, account_id=account_id)


@api_v1.route('/team-capacity')
def v1_team_capacity():
    """Team capacity — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_team_capacity_api
    return _dispatch('team_capacity', get_team_capacity_api)


@api_v1.route('/csm-scorecard')
def v1_csm_scorecard():
    """CSM scorecard — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_csm_scorecard_api
    return _dispatch('csm_scorecard', get_csm_scorecard_api)


@api_v1.route('/playbook-success-metrics')
def v1_playbook_success_metrics():
    """Playbook success metrics — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_playbook_success_metrics_api
    return _dispatch('playbook_success_metrics', get_playbook_success_metrics_api)


@api_v1.route('/renewals')
def v1_renewals():
    """Renewal pipeline — vertical-agnostic."""
    from verticals.dc2_s.api_routes import get_renewals_api
    return _dispatch('renewals', get_renewals_api)


# ─── Vertical handler registration API ──────────────────────────────────────

def register_vertical_handler(vertical: str, endpoint: str, handler):
    """Register a vertical-specific handler override.

    Example:
        from api_v1_routes import register_vertical_handler
        register_vertical_handler('saas_premium', 'accounts', saas_get_accounts)

    When a SaaS customer calls /api/v1/accounts, saas_get_accounts will be
    used instead of the DC2S default.
    """
    _VERTICAL_HANDLERS[(vertical, endpoint)] = handler
    logger.info("v1: registered %s handler for endpoint '%s'", vertical, endpoint)
