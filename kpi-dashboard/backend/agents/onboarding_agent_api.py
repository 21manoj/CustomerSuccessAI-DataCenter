#!/usr/bin/env python3
"""
Onboarding Agent API — Flask endpoints for AI-powered onboarding
=================================================================
Provides REST endpoints for:
  - POST /api/onboarding-agent/analyze/<customer_id>   — trigger onboarding analysis
  - GET  /api/onboarding-agent/activation-plan/<cid>   — get stored activation plan
  - GET  /api/onboarding-agent/ttfv-status/<cid>       — TTFV tracking data
  - POST /api/onboarding-agent/graduate/<account_id>   — graduate account to steady-state
"""

import os
import sys
import logging
from flask import Blueprint, request, jsonify

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from .onboarding_agent import (
    OnboardingAgent,
    activation_plan_to_dict,
    ttfv_status_to_dict,
)

logger = logging.getLogger(__name__)

onboarding_agent_api = Blueprint('onboarding_agent_api', __name__)

# Import entitlement gating (graceful fallback if not available)
try:
    from entitlements import require_entitlement, check_entitlement
except ImportError:
    def require_entitlement(feature_name):
        def decorator(f):
            return f
        return decorator
    def check_entitlement(customer_id, feature_name):
        return True


# ============================================================
# POST /api/onboarding-agent/analyze/<customer_id>
# ============================================================

@onboarding_agent_api.route('/api/onboarding-agent/analyze/<customer_id>', methods=['POST'])
@require_entitlement('onboarding_agent')
def analyze_new_customer(customer_id):
    """
    Trigger the Onboarding Agent to analyse a customer and create an activation plan.

    Accepts integer customer_id or UUID in path.

    JSON body (optional overrides):
        {
            "provider": "openai" | "anthropic",
            "model": "gpt-4o" | "claude-sonnet-4-5-20250929",
        }

    Customer data (name, industry, accounts) is loaded from the database.
    """
    try:
        # Resolve customer_id (accepts integer or UUID)
        customer_id_int = _resolve_customer_id(customer_id)
        if customer_id_int is None:
            return jsonify({"error": f"Customer {customer_id} not found"}), 404

        data = request.get_json(silent=True) or {}
        provider = data.get('provider', 'openai')
        model = data.get('model')

        # Load customer data from DB
        customer_data = _load_customer_data(customer_id_int)
        if not customer_data:
            return jsonify({"error": f"Customer {customer_id} not found"}), 404

        agent = OnboardingAgent(
            customer_id=customer_id_int,
            provider=provider,
            model=model,
        )

        plan = agent.analyze_new_customer(
            customer_name=customer_data['customer_name'],
            industry=customer_data['industry'],
            onboarding_mode=customer_data.get('onboarding_mode', 'demo'),
            accounts=customer_data['accounts'],
            kpi_snapshot=customer_data.get('kpi_snapshot'),
        )

        response = {
            "status": "success",
            "customer_id": customer_id_int,
            "activation_plan": activation_plan_to_dict(plan),
        }

        # Enrich with UUID
        try:
            from id_resolve_utils import enrich_with_uuid, resolve_customer
            customer = resolve_customer(customer_id_int, allow_none=True)
            if customer:
                response = enrich_with_uuid(response, customer)
        except Exception:
            pass

        return jsonify(response)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.exception(f"Onboarding analysis failed for customer {customer_id}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


# ============================================================
# GET /api/onboarding-agent/activation-plan/<customer_id>
# ============================================================

@onboarding_agent_api.route('/api/onboarding-agent/activation-plan/<customer_id>', methods=['GET'])
@require_entitlement('onboarding_agent')
def get_activation_plan(customer_id):
    """Retrieve the stored activation plan for a customer."""
    try:
        customer_id_int = _resolve_customer_id(customer_id)
        if customer_id_int is None:
            return jsonify({"error": f"Customer {customer_id} not found"}), 404

        agent = OnboardingAgent(customer_id=customer_id_int)
        plan = agent.get_activation_plan()

        if not plan:
            return jsonify({
                "status": "not_found",
                "message": f"No activation plan found for customer {customer_id}. "
                           f"Run POST /api/onboarding-agent/analyze/{customer_id} first.",
            }), 404

        return jsonify({
            "status": "success",
            "activation_plan": plan,
        })

    except Exception as e:
        logger.exception(f"Failed to get activation plan for customer {customer_id}")
        return jsonify({"error": str(e)}), 500


# ============================================================
# GET /api/onboarding-agent/ttfv-status/<customer_id>
# ============================================================

@onboarding_agent_api.route('/api/onboarding-agent/ttfv-status/<customer_id>', methods=['GET'])
@require_entitlement('onboarding_agent')
def get_ttfv_status(customer_id):
    """
    Get TTFV tracking status for all accounts of a customer.

    Optional query params:
        ?account_id=<specific account>
    """
    try:
        customer_id_int = _resolve_customer_id(customer_id)
        if customer_id_int is None:
            return jsonify({"error": f"Customer {customer_id} not found"}), 404

        account_id = request.args.get('account_id')
        agent = OnboardingAgent(customer_id=customer_id_int)

        if account_id:
            # Single account
            status = agent.evaluate_activation_readiness(account_id)
            return jsonify({
                "status": "success",
                "ttfv_status": [ttfv_status_to_dict(status)],
            })

        # All accounts — load from plan
        plan = agent.get_activation_plan()
        if not plan:
            return jsonify({
                "status": "not_found",
                "message": "No activation plan found. Run analysis first.",
            }), 404

        statuses = []
        for entry in plan.get("plan_entries", []):
            acct_id = entry.get("account_id")
            if acct_id:
                status = agent.evaluate_activation_readiness(acct_id)
                statuses.append(ttfv_status_to_dict(status))

        return jsonify({
            "status": "success",
            "ttfv_status": statuses,
            "summary": {
                "total_accounts": len(statuses),
                "graduated": sum(1 for s in statuses if s.get("is_graduated")),
                "avg_activation_score": round(
                    sum(s.get("activation_score", 0) for s in statuses) / max(len(statuses), 1), 2
                ),
            },
        })

    except Exception as e:
        logger.exception(f"Failed to get TTFV status for customer {customer_id}")
        return jsonify({"error": str(e)}), 500


# ============================================================
# POST /api/onboarding-agent/graduate/<account_id>
# ============================================================

@onboarding_agent_api.route('/api/onboarding-agent/graduate/<account_id>', methods=['POST'])
@require_entitlement('onboarding_agent')
def graduate_account(account_id: str):
    """
    Graduate an account from onboarding to steady-state Signal Analyst monitoring.

    JSON body:
        { "customer_id": <int> }
    """
    try:
        data = request.get_json(silent=True) or {}
        customer_id = data.get('customer_id')

        if not customer_id:
            return jsonify({"error": "customer_id is required"}), 400

        agent = OnboardingAgent(customer_id=int(customer_id))
        result = agent.graduate_to_steady_state(account_id)

        return jsonify({
            "status": "success",
            **result,
        })

    except Exception as e:
        logger.exception(f"Failed to graduate account {account_id}")
        return jsonify({"error": str(e)}), 500


# ============================================================
# Health check
# ============================================================

@onboarding_agent_api.route('/api/onboarding-agent/health', methods=['GET'])
def health():
    """Health check for the Onboarding Agent API."""
    return jsonify({
        "status": "healthy",
        "service": "onboarding-agent",
        "providers": {
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        },
    })


# ============================================================
# Helper: resolve customer_id (integer or UUID)
# ============================================================

def _resolve_customer_id(identifier) -> int:
    """Resolve a customer_id path parameter (integer or UUID) to an integer PK."""
    if identifier is None:
        return None
    # Try integer first
    try:
        return int(identifier)
    except (ValueError, TypeError):
        pass
    # Try UUID resolution
    try:
        from id_resolve_utils import resolve_customer
        customer = resolve_customer(identifier, allow_none=True)
        if customer:
            return customer.customer_id
    except Exception as e:
        logger.warning(f"Failed to resolve customer identifier '{identifier}': {e}")
    return None


# ============================================================
# Helper: load customer data from DB
# ============================================================

def _load_customer_data(customer_id: int) -> dict:
    """Load customer info and accounts from the database."""
    try:
        from sqlalchemy import create_engine, text

        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.warning("DATABASE_URL not set — cannot load customer data")
            return None

        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Load customer (actual columns: customer_id, customer_name, email, phone, domain, uuid, vertical)
            result = conn.execute(text(
                "SELECT customer_id, customer_name, vertical, domain FROM customers WHERE customer_id = :cid"
            ), {"cid": customer_id})
            row = result.fetchone()
            if not row:
                return None

            customer_name = row[1] or f"Customer {customer_id}"
            industry = row[2] or "Technology"  # vertical doubles as industry

            # Load accounts (actual columns: account_id, customer_id, account_name, revenue, account_status, ...)
            result = conn.execute(text(
                "SELECT account_id, account_name, revenue, account_status FROM accounts WHERE customer_id = :cid"
            ), {"cid": customer_id})
            accounts = []
            for acct_row in result.fetchall():
                accounts.append({
                    "account_id": acct_row[0],
                    "account_name": acct_row[1] or f"Account {acct_row[0]}",
                    "arr": float(acct_row[2]) if acct_row[2] else 0,
                    "status": acct_row[3] or "unknown",
                })

            # Load KPI snapshot (dc2s_kpis: kpi_id, account_id, kpi_code, value, target, pillar, weight, status)
            kpi_snapshot = {}
            try:
                result = conn.execute(text("""
                    SELECT k.kpi_code, ROUND(AVG(k.value)::numeric, 2) as avg_val,
                           ROUND(AVG(k.target)::numeric, 2) as avg_target, k.status
                    FROM dc2s_kpis k
                    JOIN accounts a ON k.account_id = a.account_id
                    WHERE a.customer_id = :cid
                    GROUP BY k.kpi_code, k.status
                    ORDER BY k.kpi_code
                    LIMIT 30
                """), {"cid": customer_id})
                for kpi_row in result.fetchall():
                    kpi_snapshot[kpi_row[0]] = {
                        "value": float(kpi_row[1]) if kpi_row[1] else None,
                        "target": float(kpi_row[2]) if kpi_row[2] else None,
                        "status": kpi_row[3],
                    }
            except Exception:
                pass  # KPI table may not exist yet

            # Load onboarding mode from customer_configs
            onboarding_mode = "demo"
            try:
                result = conn.execute(text(
                    "SELECT kpi_upload_mode, vertical FROM customer_configs WHERE customer_id = :cid LIMIT 1"
                ), {"cid": customer_id})
                config_row = result.fetchone()
                if config_row and config_row[0]:
                    onboarding_mode = config_row[0]  # kpi_upload_mode as proxy
            except Exception:
                pass

            return {
                "customer_name": customer_name,
                "industry": industry,
                "onboarding_mode": onboarding_mode,
                "accounts": accounts,
                "kpi_snapshot": kpi_snapshot if kpi_snapshot else None,
            }

    except Exception as e:
        logger.exception(f"Failed to load customer data for {customer_id}")
        return None
