#!/usr/bin/env python3
"""
CS Pulse MCP — Onboarding Agent (read-only).

Mirrors GET /api/onboarding-agent/* without invoking LLM analysis.
Use onboarding MCP tools (process_data, complete_onboarding) for data load;
use these to read activation plans and TTFV status after analysis has run.
"""

from cs_pulse_mcp_server import (
    mcp,
    _check_mcp_enabled,
    _require_auth,
    _get_flask_app,
    ToolError,
)


def _require_onboarding_agent_entitlement(customer_id: int) -> None:
    try:
        from entitlements import check_entitlement
        if not check_entitlement(int(customer_id), 'onboarding_agent'):
            raise ToolError(
                f"onboarding_agent entitlement not enabled for customer {customer_id}. "
                "Enable via enable_features() or Admin UI."
            )
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"Could not verify onboarding_agent entitlement: {exc}") from exc


@mcp.tool
def get_onboarding_activation_plan(customer_id: int) -> dict:
    """Retrieve the stored onboarding activation plan for a customer.

    Read-only — does not call LLM. Same data as
    GET /api/onboarding-agent/activation-plan/<customer_id>.

    process_data() generates a plan automatically; POST /api/onboarding-agent/analyze
    can also be used to regenerate (LLM, requires onboarding_agent entitlement).

    Args:
        customer_id: Tenant ID
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        _require_onboarding_agent_entitlement(customer_id)
        from agents.onboarding_agent import OnboardingAgent

        agent = OnboardingAgent(customer_id=int(customer_id))
        plan = agent.get_activation_plan()
        if not plan:
            return {
                'scope': 'customer',
                'customer_id': customer_id,
                'status': 'not_found',
                'message': (
                    f'No activation plan for customer {customer_id}. '
                    'Run onboarding analysis via the UI or REST analyze endpoint first.'
                ),
            }
        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'status': 'success',
            'activation_plan': plan,
        }


@mcp.tool
def get_onboarding_ttfv_status(customer_id: int, account_id: int = None) -> dict:
    """TTFV / activation readiness for onboarding accounts.

    Read-only. Same data as GET /api/onboarding-agent/ttfv-status/<customer_id>.
    Optional account_id filters to a single account.

    Args:
        customer_id: Tenant ID
        account_id: Optional account to scope (omit for all accounts in the plan)
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        _require_onboarding_agent_entitlement(customer_id)
        from agents.onboarding_agent import OnboardingAgent, ttfv_status_to_dict

        agent = OnboardingAgent(customer_id=int(customer_id))

        if account_id is not None:
            status = agent.evaluate_activation_readiness(int(account_id))
            return {
                'scope': 'account' if account_id else 'customer',
                'customer_id': customer_id,
                'account_id': account_id,
                'status': 'success',
                'ttfv_status': [ttfv_status_to_dict(status)],
            }

        plan = agent.get_activation_plan()
        if not plan:
            return {
                'scope': 'customer',
                'customer_id': customer_id,
                'status': 'not_found',
                'message': 'No activation plan found. Run onboarding analysis first.',
            }

        statuses = []
        for entry in plan.get('plan_entries', []):
            acct_id = entry.get('account_id')
            if acct_id:
                status = agent.evaluate_activation_readiness(acct_id)
                statuses.append(ttfv_status_to_dict(status))

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'status': 'success',
            'ttfv_status': statuses,
            'summary': {
                'total_accounts': len(statuses),
                'graduated': sum(1 for s in statuses if s.get('is_graduated')),
                'avg_activation_score': round(
                    sum(s.get('activation_score', 0) for s in statuses) / max(len(statuses), 1),
                    2,
                ),
            },
        }
