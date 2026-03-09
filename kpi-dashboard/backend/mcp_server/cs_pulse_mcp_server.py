#!/usr/bin/env python3
"""
CS Pulse MCP Server — Expose platform as tool provider for external LLMs.

Supports two transport modes:
  - stdio:  Claude Desktop, Claude Code (local subprocess)
  - http:   Copilot Studio, ChatGPT, remote agents (Streamable HTTP)

Usage:
  # stdio (default)
  python backend/mcp_server/cs_pulse_mcp_server.py

  # Streamable HTTP
  python backend/mcp_server/cs_pulse_mcp_server.py http

Feature gated: Requires FeatureToggle.MCP_SERVER to be ON.
"""

import os
import sys

# Ensure backend is on the Python path
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "CS Pulse",
    instructions=(
        "AI-native Customer Success platform — health scoring, "
        "signal detection, context graph intelligence, revenue analytics"
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _check_mcp_enabled():
    """Raise ToolError if MCP_SERVER toggle is OFF."""
    from feature_toggles import feature_toggles, FeatureToggle
    if not feature_toggles.is_enabled(FeatureToggle.MCP_SERVER):
        raise ToolError("MCP Server is disabled. Enable via FEATURE_MCP_SERVER=true")


_flask_app = None

def _get_flask_app():
    """Return a minimal Flask app for DB context.

    Creates a lightweight app with just DB access — avoids importing the full
    app_v3_minimal which requires flask_session, flask_login, etc.
    """
    global _flask_app
    if _flask_app is not None:
        return _flask_app

    from flask import Flask
    from extensions import db
    from dotenv import load_dotenv

    load_dotenv()

    app = Flask(__name__)
    database_url = os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL')
    if not database_url:
        raise ToolError("DATABASE_URL environment variable is required")

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    _flask_app = app
    return app


_registry_initialized = False

def _ensure_registry():
    """Initialize the agent tool registry (once)."""
    global _registry_initialized
    if not _registry_initialized:
        from agent_tool_registry import register_all_tools
        register_all_tools()
        _registry_initialized = True


def _get_account_arr(account) -> float:
    """Extract ARR from account (profile_metadata or revenue column)."""
    arr = 0.0
    if account.profile_metadata and isinstance(account.profile_metadata, dict):
        arr = float(account.profile_metadata.get('arr', 0) or 0)
    if not arr and account.revenue:
        arr = float(account.revenue)
    return arr


# ===================================================================
# Group 1: Account Intelligence (3 tools)
# ===================================================================

@mcp.tool
def list_accounts(customer_id: int) -> dict:
    """List all accounts with health scores for a customer.

    Args:
        customer_id: The customer (tenant) ID
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from verticals.dc2_s.api_routes import (
            calculate_kpi_health, _get_trailing_kpi_values,
            get_precalculated_scores,
        )
        import utils.health_thresholds as ht

        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
            Account.vertical == 'dc2_s',
        ).all()

        results = []
        for acct in accounts:
            # Prefer pre-calculated scores (single source of truth)
            precalc_health, precalc_status, precalc_pillars = get_precalculated_scores(acct.account_id)

            if precalc_health is not None and precalc_pillars:
                health = precalc_health
                pillars = precalc_pillars
                status = precalc_status
            else:
                # Fallback: on-the-fly calculation
                kpi_values = _get_trailing_kpi_values(acct.account_id)
                health, pillars = calculate_kpi_health(kpi_values, customer_id)
                status = ht.classify(health)

            arr = _get_account_arr(acct)

            results.append({
                "account_id": acct.account_id,
                "account_name": acct.account_name,
                "health_score": round(health, 1),
                "status": status,
                "arr": arr,
                "pillar_scores": {k: round(v, 1) for k, v in pillars.items()},
            })

        # Sort by health (worst first)
        results.sort(key=lambda x: x["health_score"])

        return {
            "customer_id": customer_id,
            "total_accounts": len(results),
            "accounts": results,
        }


@mcp.tool
def get_account_health(customer_id: int, account_id: int) -> dict:
    """Get detailed health score and pillar breakdown for a specific account.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from verticals.dc2_s.api_routes import (
            calculate_kpi_health, _get_trailing_kpi_values,
            get_precalculated_scores,
        )
        import utils.health_thresholds as ht

        account = Account.query.filter_by(account_id=account_id).first()
        if not account:
            raise ToolError(f"Account {account_id} not found")

        # Prefer pre-calculated scores (single source of truth)
        precalc_health, precalc_status, precalc_pillars = get_precalculated_scores(account_id)

        if precalc_health is not None and precalc_pillars:
            health = precalc_health
            pillars = precalc_pillars
            status = precalc_status
        else:
            # Fallback: on-the-fly calculation
            kpi_values = _get_trailing_kpi_values(account_id)
            health, pillars = calculate_kpi_health(kpi_values, customer_id)
            status = ht.classify(health)

        arr = _get_account_arr(account)

        return {
            "account_id": account_id,
            "account_name": account.account_name,
            "health_score": round(health, 1),
            "status": status,
            "status_label": ht.classify_label(health) if hasattr(ht, 'classify_label') else status,
            "arr": arr,
            "pillar_scores": {k: round(v, 1) for k, v in pillars.items()},
        }


@mcp.tool
def get_at_risk_accounts(customer_id: int, threshold: float = 70.0) -> dict:
    """List accounts with health scores below a threshold.

    Args:
        customer_id: The customer (tenant) ID
        threshold: Health score threshold (default 70 = at-risk boundary)
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from verticals.dc2_s.api_routes import (
            calculate_kpi_health, _get_trailing_kpi_values,
            get_precalculated_scores,
        )
        import utils.health_thresholds as ht

        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
            Account.vertical == 'dc2_s',
        ).all()

        at_risk = []
        total_arr_at_risk = 0.0

        for acct in accounts:
            # Prefer pre-calculated scores (single source of truth)
            precalc_health, precalc_status, precalc_pillars = get_precalculated_scores(acct.account_id)

            if precalc_health is not None and precalc_pillars:
                health = precalc_health
                pillars = precalc_pillars
            else:
                kpi_values = _get_trailing_kpi_values(acct.account_id)
                health, pillars = calculate_kpi_health(kpi_values, customer_id)

            if health < threshold:
                arr = _get_account_arr(acct)
                total_arr_at_risk += arr
                at_risk.append({
                    "account_id": acct.account_id,
                    "account_name": acct.account_name,
                    "health_score": round(health, 1),
                    "status": ht.classify(health),
                    "arr": arr,
                    "weakest_pillar": min(pillars, key=pillars.get) if pillars else None,
                })

        at_risk.sort(key=lambda x: x["health_score"])

        return {
            "customer_id": customer_id,
            "threshold": threshold,
            "at_risk_count": len(at_risk),
            "total_accounts": len(accounts),
            "total_arr_at_risk": round(total_arr_at_risk, 2),
            "accounts": at_risk,
        }


# ===================================================================
# Group 2: Context Graph / Revenue Intelligence (4 tools)
# ===================================================================

def _check_context_graph(customer_id: int):
    """Raise ToolError if context graph is not enabled for this customer."""
    from feature_toggles import is_context_graph_enabled
    if not is_context_graph_enabled(customer_id):
        raise ToolError(
            f"Context graph is not enabled for customer {customer_id}. "
            "Enable via the feature toggle API."
        )


@mcp.tool
def get_revenue_at_risk(customer_id: int, account_id: int) -> dict:
    """Get revenue breakdown from context graph: at-risk, protected, expansion, lost.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from utils.context_graph import get_revenue_at_risk as _get_rev
        from models import Account

        account = Account.query.filter_by(account_id=account_id).first()
        result = _get_rev(account_id)
        result["account_id"] = account_id
        result["account_name"] = account.account_name if account else "Unknown"
        return result


@mcp.tool
def get_causal_chain(customer_id: int, node_id: int, direction: str = "upstream") -> dict:
    """Traverse the causal chain (Signal → Decision → Outcome) from a context graph node.

    Args:
        customer_id: The customer (tenant) ID
        node_id: The starting context graph node ID
        direction: 'upstream' (what caused this) or 'downstream' (what this led to)
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from utils.context_graph import get_causal_chain as _get_chain
        from models import ContextNode, db

        start_node = db.session.get(ContextNode, node_id)
        if not start_node:
            raise ToolError(f"Node {node_id} not found")

        chain = _get_chain(node_id, direction=direction, max_depth=5)

        return {
            "start_node": start_node.to_dict(),
            "direction": direction,
            "chain_length": len(chain),
            "chain": chain,
        }


@mcp.tool
def get_graph_summary(customer_id: int, account_id: int) -> dict:
    """Get context graph summary: node/edge counts and revenue breakdown.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from utils.context_graph import get_account_graph_summary
        return get_account_graph_summary(account_id)


@mcp.tool
def search_signals(
    customer_id: int,
    account_id: int,
    node_type: str = "SIGNAL",
    node_subtype: str = None,
    limit: int = 20,
) -> dict:
    """Search for context graph nodes (signals, decisions, outcomes) for an account.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to search
        node_type: Node type filter: SIGNAL, DECISION, OUTCOME, STAKEHOLDER, EXTERNAL_CONTEXT
        node_subtype: Optional subtype filter (e.g. kpi_change, ticket, champion_loss)
        limit: Maximum number of results (default 20)
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from utils.context_graph import get_nodes

        nodes = get_nodes(
            account_id=account_id,
            node_type=node_type,
            node_subtype=node_subtype,
            limit=limit,
        )

        return {
            "account_id": account_id,
            "node_type": node_type,
            "node_subtype": node_subtype,
            "count": len(nodes),
            "nodes": [n.to_dict() for n in nodes],
        }


# ===================================================================
# Group 3: Financial / ROI (2 tools)
# ===================================================================

@mcp.tool
def calculate_power_of_1(
    customer_id: int,
    metric_id: str,
    improvement_pct: float = 1.0,
    account_arr: float = None,
) -> dict:
    """Calculate the revenue impact of a 1% improvement in a business metric (Power-of-1).

    Args:
        customer_id: The customer (tenant) ID
        metric_id: Metric to improve (e.g. NRR, GRR, product_adoption, expansion_rate, ticket_resolution_time, TTFV)
        improvement_pct: Percentage improvement (default 1.0 = 1%)
        account_arr: Optional account ARR override. If omitted, uses portfolio total.
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        _ensure_registry()
        from agent_tool_registry import get_tool_registry

        registry = get_tool_registry()
        kwargs = {"metric_id": metric_id, "improvement_pct": improvement_pct}
        if account_arr:
            kwargs["account_arr"] = account_arr
        result = registry.invoke("power_of_1_calc", **kwargs)

        if not result.success:
            raise ToolError(f"Power-of-1 calculation failed: {result.error}")

        return result.result


@mcp.tool
def get_outcome_roi_story(
    customer_id: int,
    account_id: int,
    target_improvement_pct: float = 10.0,
    projection_months: int = 12,
) -> dict:
    """Generate a full ROI narrative with proof points, projections, and context graph insights.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
        target_improvement_pct: Target improvement percentage (default 10%)
        projection_months: Projection horizon in months (default 12)
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from outcome_roi_engine import calculate_outcome_story
        from power_of_1_model import POWER_OF_1_METRICS
        from models import Account

        account = Account.query.filter_by(account_id=account_id).first()
        if not account:
            raise ToolError(f"Account {account_id} not found")

        arr = _get_account_arr(account)

        # Build metric_actuals in the format expected by calculate_outcome_story:
        # {metric_id: {"current": float, "baseline": float}}
        # Use baselines as defaults (the engine computes delta from there)
        metric_actuals = {}
        for mid, m in POWER_OF_1_METRICS.items():
            metric_actuals[mid] = {"current": m.baseline, "baseline": m.baseline}

        story = calculate_outcome_story(
            metric_actuals=metric_actuals,
            target_improvement_pct=target_improvement_pct,
            account_arr=arr,
            projection_months=projection_months,
            customer_id=customer_id,
            account_ids=[account_id],
        )

        return story


# ===================================================================
# Group 4: Actions (1 tool)
# ===================================================================

@mcp.tool
def get_playbook_recommendations(
    customer_id: int,
    account_id: int,
) -> dict:
    """Get recommended playbooks for an account based on health score and signals.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to get recommendations for
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        _ensure_registry()
        from agent_tool_registry import get_tool_registry
        from verticals.dc2_s.api_routes import (
            calculate_kpi_health, _get_trailing_kpi_values,
            get_precalculated_scores,
        )

        # Prefer pre-calculated scores (single source of truth)
        precalc_health, _, _ = get_precalculated_scores(account_id)
        if precalc_health is not None:
            health = precalc_health
        else:
            kpi_values = _get_trailing_kpi_values(account_id)
            health, _ = calculate_kpi_health(kpi_values, customer_id)

        registry = get_tool_registry()
        result = registry.invoke(
            "playbook_recommend",
            account_id=account_id,
            customer_id=customer_id,
            health_score=round(health, 1),
        )

        if not result.success:
            raise ToolError(f"Playbook recommendations failed: {result.error}")

        return result.result


# ===================================================================
# Helpers for Groups 5 & 6
# ===================================================================

def _get_account_profile(account) -> dict:
    """Safely extract profile_metadata fields with defaults."""
    meta = account.profile_metadata if isinstance(account.profile_metadata, dict) else {}
    return {
        "assigned_csm": meta.get("assigned_csm", "Unassigned"),
        "executive_sponsor": meta.get("executive_sponsor", ""),
        "contract_start_date": meta.get("contract_start_date", ""),
        "contract_end_date": meta.get("contract_end_date", ""),
        "renewal_date": meta.get("renewal_date", ""),
        "champion_name": meta.get("primary_champion_name", ""),
        "champion_title": meta.get("champion_title", ""),
        "champion_email": meta.get("champion_email", ""),
        "champion_status": meta.get("champion_status", "Unknown"),
        "champion_influence_level": meta.get("champion_influence_level", ""),
        "economic_buyer": meta.get("economic_buyer_name", ""),
        "industry": meta.get("industry", ""),
        "region": meta.get("region", ""),
        "tier": meta.get("account_tier", ""),
        "products_used": meta.get("products_used", ""),
    }


def _compute_renewal_stage(days_until_renewal: int, health_status: str) -> dict:
    """Derive CRM renewal stage and probability from days remaining and health."""
    if days_until_renewal > 180:
        stage, forecast = "Early Renewal", "Pipeline"
    elif days_until_renewal > 90:
        stage, forecast = "Renewal Discussion", "Best Case"
    elif days_until_renewal > 30:
        stage, forecast = "Negotiation", "Commit"
    elif days_until_renewal > 0:
        stage, forecast = "Final Review", "Commit"
    else:
        stage, forecast = "Overdue", "Omitted"

    prob = {"healthy": 90, "at_risk": 65, "critical": 35}.get(health_status, 70)
    return {"stage": stage, "probability": prob, "forecast_category": forecast}


def _derive_nps_from_signals(signals) -> dict:
    """Compute NPS proxy from QualitativeSignal sentiment distribution."""
    if not signals:
        return {"score": 0, "trend": "unknown", "response_count": 0}

    total = len(signals)
    positive = sum(1 for s in signals if getattr(s, 'sentiment', '') == 'positive')
    negative = sum(1 for s in signals if getattr(s, 'sentiment', '') == 'negative')

    nps = int(((positive - negative) / total) * 100) if total else 0

    # Trend: compare first half (older) vs second half (newer, sorted DESC)
    mid = total // 2
    if mid > 0:
        older_half_pos = sum(1 for s in signals[mid:] if getattr(s, 'sentiment', '') == 'positive')
        newer_half_pos = sum(1 for s in signals[:mid] if getattr(s, 'sentiment', '') == 'positive')
        trend = "improving" if newer_half_pos > older_half_pos else (
            "declining" if newer_half_pos < older_half_pos else "stable"
        )
    else:
        trend = "stable"

    return {"score": nps, "trend": trend, "response_count": total}


# ===================================================================
# Group 5: External System Integration — Simulated (3 tools)
# ===================================================================

@mcp.tool
def get_crm_account_data(customer_id: int, account_id: int) -> dict:
    """Pull CRM data for an account — contract details, renewal opportunity, champion contacts, usage metrics. Simulates Salesforce integration; reads from CS Pulse platform data.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to pull CRM data for
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from verticals.dc2_s.api_routes import (
            calculate_kpi_health, _get_trailing_kpi_values,
            get_precalculated_scores,
        )
        import utils.health_thresholds as ht
        from datetime import datetime, date

        account = Account.query.filter_by(account_id=account_id).first()
        if not account:
            raise ToolError(f"Account {account_id} not found")

        profile = _get_account_profile(account)
        arr = _get_account_arr(account)

        # Health for renewal probability — prefer pre-calculated scores
        precalc_health, precalc_status, precalc_pillars = get_precalculated_scores(account_id)
        kpi_values = _get_trailing_kpi_values(account_id)  # still needed for usage metrics

        if precalc_health is not None:
            health = precalc_health
            health_status = precalc_status
        else:
            health, pillars = calculate_kpi_health(kpi_values, customer_id)
            health_status = ht.classify(health)

        # Compute days until renewal
        days_until_renewal = 180  # default
        if profile["contract_end_date"]:
            try:
                end_date = datetime.strptime(str(profile["contract_end_date"])[:10], "%Y-%m-%d").date()
                days_until_renewal = (end_date - date.today()).days
            except (ValueError, TypeError):
                pass

        renewal = _compute_renewal_stage(days_until_renewal, health_status)

        # Usage metrics from KPIs (raw values, not health scores)
        gpu_util = kpi_values.get("P3-KPI1", 0)
        capacity_util = kpi_values.get("P5-KPI1", 0)
        uptime = kpi_values.get("P2-KPI4", 0)

        return {
            "source": "salesforce_simulated",
            "account_id": account_id,
            "account_name": account.account_name,
            "crm_id": f"SF-{account_id}",
            "industry": profile["industry"] or getattr(account, 'industry', ''),
            "region": profile["region"] or getattr(account, 'region', ''),
            "contract": {
                "start_date": profile["contract_start_date"],
                "end_date": profile["contract_end_date"],
                "renewal_date": profile["renewal_date"],
                "days_until_renewal": days_until_renewal,
                "arr": arr,
                "mrr": round(arr / 12, 2) if arr else 0,
            },
            "renewal_opportunity": {
                "stage": renewal["stage"],
                "probability": renewal["probability"],
                "amount": arr,
                "forecast_category": renewal["forecast_category"],
            },
            "champion": {
                "name": profile["champion_name"],
                "title": profile["champion_title"],
                "email": profile["champion_email"],
                "status": profile["champion_status"],
                "influence_level": profile["champion_influence_level"],
            },
            "executive_sponsor": profile["executive_sponsor"],
            "assigned_csm": profile["assigned_csm"],
            "account_tier": profile["tier"],
            "health_score": round(health, 1),
            "health_status": health_status,
            "usage_summary": {
                "gpu_utilization_pct": round(gpu_util, 1),
                "capacity_utilization_pct": round(capacity_util, 1),
                "system_uptime_pct": round(uptime, 1),
            },
        }


@mcp.tool
def get_support_tickets(customer_id: int, account_id: int) -> dict:
    """Pull support ticket summary for an account — open tickets, SLA compliance, escalations, risk indicators. Simulates ServiceNow integration; derives ticket data from operational KPIs and qualitative signals.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to pull ticket data for
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Account, QualitativeSignal
        from verticals.dc2_s.api_routes import _get_trailing_kpi_values
        import math

        account = Account.query.filter_by(account_id=account_id).first()
        if not account:
            raise ToolError(f"Account {account_id} not found")

        kpi_values = _get_trailing_kpi_values(account_id)

        # P2 pillar KPIs for ticket derivation
        critical_incidents = kpi_values.get("P2-KPI3", 0)
        mttr_hours = kpi_values.get("P2-KPI7", 4.0)
        uptime_pct = kpi_values.get("P2-KPI4", 99.9)
        mtbf_hours = kpi_values.get("P2-KPI2", 720)
        rma_rate = kpi_values.get("P2-KPI1", 2.0)
        thermal_score = kpi_values.get("P2-KPI5", 85)
        preventive_maint = kpi_values.get("P2-KPI8", 90)

        # Derive open tickets from critical incidents
        open_tickets = max(0, math.ceil(critical_incidents))
        resolved_last_30d = max(0, open_tickets + int(critical_incidents * 1.5))

        # SLA compliance from MTTR and uptime
        resolution_target_hours = 4.0
        resolution_sla_met = mttr_hours <= resolution_target_hours
        sla_breaches = max(0, math.ceil((mttr_hours - resolution_target_hours) * 2)) if not resolution_sla_met else 0

        # Query recent negative signals for escalation context
        recent_signals = QualitativeSignal.query.filter(
            QualitativeSignal.account_id == str(account_id),
            QualitativeSignal.sentiment == 'negative',
        ).order_by(QualitativeSignal.signal_date.desc()).limit(10).all()

        escalation_entries = []
        for sig in recent_signals[:3]:
            escalation_entries.append({
                "date": sig.signal_date.strftime('%Y-%m-%d') if sig.signal_date else "",
                "summary": (sig.signal_text or "")[:200],
                "stakeholder": sig.stakeholder_name or "",
            })

        return {
            "source": "servicenow_simulated",
            "account_id": account_id,
            "account_name": account.account_name,
            "ticket_summary": {
                "open_tickets": open_tickets,
                "resolved_last_30d": resolved_last_30d,
                "critical_incidents_30d": round(critical_incidents, 1),
                "avg_resolution_hours": round(mttr_hours, 1),
                "mtbf_hours": round(mtbf_hours, 1),
                "system_uptime_pct": round(uptime_pct, 2),
            },
            "sla_compliance": {
                "overall_pct": round(uptime_pct, 2),
                "response_sla_met": uptime_pct >= 99.5,
                "resolution_sla_met": resolution_sla_met,
                "resolution_target_hours": resolution_target_hours,
                "breaches_last_30d": sla_breaches,
            },
            "escalations": {
                "count": len(recent_signals),
                "recent": escalation_entries,
            },
            "risk_indicators": {
                "rma_rate_pct": round(rma_rate, 2),
                "preventive_maintenance_compliance_pct": round(preventive_maint, 1),
                "thermal_management_score": round(thermal_score, 1),
            },
        }


@mcp.tool
def get_customer_feedback(customer_id: int, account_id: int) -> dict:
    """Pull customer feedback for an account — NPS trend, CSAT indicators, VoC summaries, CSM relationship assessment. Simulates survey system integration; derives sentiment from qualitative signals and health data.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to pull feedback for
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Account, QualitativeSignal
        from verticals.dc2_s.api_routes import (
            calculate_kpi_health, _get_trailing_kpi_values,
            get_precalculated_scores,
        )
        import utils.health_thresholds as ht

        account = Account.query.filter_by(account_id=account_id).first()
        if not account:
            raise ToolError(f"Account {account_id} not found")

        kpi_values = _get_trailing_kpi_values(account_id)  # still needed for KPI values

        # Prefer pre-calculated health scores (single source of truth)
        precalc_health, precalc_status, _ = get_precalculated_scores(account_id)
        if precalc_health is not None:
            health = precalc_health
            health_status = precalc_status
        else:
            health, pillars = calculate_kpi_health(kpi_values, customer_id)
            health_status = ht.classify(health)

        # Query recent qualitative signals
        signals = QualitativeSignal.query.filter(
            QualitativeSignal.account_id == str(account_id),
        ).order_by(QualitativeSignal.signal_date.desc()).limit(20).all()

        # NPS: use KPI P4-KPI6 if available, else derive from signals
        partner_nps = kpi_values.get("P4-KPI6")
        if partner_nps is not None and partner_nps > 0:
            nps_data = {"score": int(partner_nps), "trend": "stable", "source": "kpi_data", "response_count": 1}
        else:
            nps_data = _derive_nps_from_signals(signals)
            nps_data["source"] = "signal_derived"

        # CSAT: derive from sentiment scores
        sentiment_scores = [
            s.sentiment_score for s in signals
            if hasattr(s, 'sentiment_score') and s.sentiment_score is not None
        ]
        avg_sentiment = round(sum(sentiment_scores) / len(sentiment_scores), 2) if sentiment_scores else 0.0
        # Map sentiment (-1 to 1) to CSAT (1 to 5)
        csat_score = round(max(1.0, min(5.0, (avg_sentiment + 1) * 2 + 1)), 1)

        # Sentiment distribution
        positive_count = sum(1 for s in signals if getattr(s, 'sentiment', '') == 'positive')
        negative_count = sum(1 for s in signals if getattr(s, 'sentiment', '') == 'negative')
        neutral_count = len(signals) - positive_count - negative_count

        # Voice of Customer: top 3 signals with content
        voc_entries = []
        for sig in signals[:5]:
            text = getattr(sig, 'signal_text', '') or ''
            if text and len(text) > 20:
                voc_entries.append({
                    "date": sig.signal_date.strftime('%Y-%m-%d') if sig.signal_date else "",
                    "type": getattr(sig, 'signal_type', 'general'),
                    "summary": text[:300],
                    "sentiment": getattr(sig, 'sentiment', 'neutral'),
                })
            if len(voc_entries) >= 3:
                break

        # CSM assessment from health data
        relationship_strength = min(5, max(1, int(health / 20)))
        expansion_kpi = kpi_values.get("P5-KPI7", 0)
        champion_engagement = kpi_values.get("P5-KPI8", kpi_values.get("P4-KPI1", 0))

        return {
            "source": "survey_simulated",
            "account_id": account_id,
            "account_name": account.account_name,
            "nps": nps_data,
            "csat": {
                "score": csat_score,
                "avg_sentiment_score": avg_sentiment,
            },
            "voice_of_customer": voc_entries,
            "csm_assessment": {
                "relationship_strength": relationship_strength,
                "churn_risk": health_status,
                "expansion_potential": f"{expansion_kpi:.0f}%" if expansion_kpi else "Unknown",
                "champion_engagement_score": round(champion_engagement, 1),
                "health_score": round(health, 1),
                "recommended_focus": min(pillars, key=pillars.get) if pillars else "Unknown",
            },
            "sentiment_distribution": {
                "positive": positive_count,
                "neutral": neutral_count,
                "negative": negative_count,
                "total_signals": len(signals),
            },
        }


# ===================================================================
# Group 6: Operational Intelligence (2 tools)
# ===================================================================

@mcp.tool
def get_csm_daily_actions(customer_id: int) -> dict:
    """Get top-10 prioritized CSM actions across all accounts. Each action includes the linked playbook, urgency level, estimated effort hours, and projected dollar impact via Power-of-1 ROI metric correlation.

    Priority formula: (impact × 0.6 × arr_weight) - (effort × 0.4)

    Args:
        customer_id: The customer (tenant) ID
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from datetime import datetime
        from verticals.dc2_s.api_routes import (
            _get_trailing_kpi_values, calculate_kpi_health,
            _normalize_kpi_code_for_health,
            _compute_impact_score, _compute_effort_score,
            _determine_urgency, _get_roi_context,
            get_precalculated_scores,
        )
        from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG, should_trigger_playbook
        from verticals.dc2_s.kpi_definitions import DC2S_KPIS
        import utils.health_thresholds as ht

        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
            Account.vertical == 'dc2_s',
        ).all()

        if not accounts:
            return {
                "date": datetime.utcnow().strftime('%Y-%m-%d'),
                "actions": [],
                "summary": {
                    "total_actions": 0, "critical_count": 0,
                    "high_count": 0, "opportunity_count": 0,
                    "total_estimated_hours": 0,
                    "total_roi_projected_impact": 0,
                },
            }

        all_actions = []

        for account in accounts:
            # --- Pre-calculated scores (source of truth for health) ---
            precalc_health, precalc_status, precalc_pillars = get_precalculated_scores(account.account_id)

            # Raw KPI values still needed for playbook trigger evaluation
            trailing_kpis = _get_trailing_kpi_values(account.account_id, days=30)

            if precalc_health is not None:
                overall_health = precalc_health
                pillar_averages = precalc_pillars or {}
            else:
                # Fallback to on-the-fly if no pre-calculated scores
                overall_health, pillar_averages = calculate_kpi_health(
                    trailing_kpis, customer_id=customer_id
                )

            # Normalize KPI codes for playbook trigger evaluation
            normalized_kpis = {}
            for code, val in trailing_kpis.items():
                norm = _normalize_kpi_code_for_health(code)
                if norm:
                    normalized_kpis[norm] = val
            normalized_kpis['OVERALL_HEALTH'] = overall_health

            # ARR weight (0.5-1.5)
            arr = _get_account_arr(account)
            if arr > 10_000_000:
                arr_weight = 1.5
            elif arr > 5_000_000:
                arr_weight = 1.3
            elif arr > 2_000_000:
                arr_weight = 1.1
            elif arr > 0:
                arr_weight = 1.0
            else:
                arr_weight = 0.8

            # Churn / expansion estimates
            h_cls = ht.classify(overall_health)
            churn_prob = 80 if h_cls == 'critical' else (40 if h_cls == 'at_risk' else 15)
            expansion_prob_val = 75 if h_cls == 'healthy' else (30 if h_cls == 'at_risk' else 5)

            exp_kpi = normalized_kpis.get('P5-KPI7')
            if exp_kpi is not None:
                expansion_prob_val = max(expansion_prob_val, exp_kpi)

            # Evaluate all 6 playbook triggers
            for pb_id, pb_cfg in PLAYBOOK_CONFIG.items():
                if should_trigger_playbook(pb_id, normalized_kpis):
                    impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                    effort = _compute_effort_score(pb_cfg)
                    priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)

                    total_hours = sum(s.get('estimated_hours', 0) for s in pb_cfg.get('sub_components', []))

                    trigger_details = []
                    for tk in pb_cfg.get('trigger_kpis', []):
                        if tk in normalized_kpis:
                            cond = pb_cfg.get('trigger_conditions', {}).get(tk, {})
                            threshold = cond.get('value', '?')
                            kpi_name = DC2S_KPIS.get(tk, {}).get('name', tk)
                            trigger_details.append(f"{kpi_name}: {normalized_kpis[tk]:.1f} (threshold {threshold})")

                    description = '; '.join(trigger_details) if trigger_details else pb_cfg.get('estimated_impact', '')

                    roi_ctx = _get_roi_context('playbook', pb_id, arr)
                    all_actions.append({
                        'account_id': account.account_id,
                        'account_name': account.account_name,
                        'action_title': f"Start {pb_cfg['name']} Playbook",
                        'action_description': description,
                        'action_type': 'playbook',
                        'related_playbook_id': pb_id,
                        'urgency': _determine_urgency(overall_health, churn_prob, expansion_prob_val),
                        'impact_score': impact,
                        'effort_score': effort,
                        'priority_index': priority_index,
                        'account_health': round(overall_health, 1),
                        'estimated_hours': total_hours,
                        'estimated_duration_display': pb_cfg.get('estimated_duration_display', ''),
                        **roi_ctx,
                    })

            # Non-playbook actions
            if overall_health < 80:
                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 20
                priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                roi_ctx = _get_roi_context('follow_up', None, arr)
                all_actions.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'action_title': 'Health Check Follow-up',
                    'action_description': f'Health score at {overall_health:.0f}. Schedule intervention call.',
                    'action_type': 'follow_up',
                    'related_playbook_id': None,
                    'urgency': _determine_urgency(overall_health, churn_prob, expansion_prob_val),
                    'impact_score': impact, 'effort_score': effort,
                    'priority_index': priority_index,
                    'account_health': round(overall_health, 1),
                    'estimated_hours': 2,
                    'estimated_duration_display': '1 day',
                    **roi_ctx,
                })

            # QBR scheduling (P4-KPI3 < target 3)
            qbr_val = normalized_kpis.get('P4-KPI3')
            if qbr_val is not None and qbr_val < 3:
                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 25
                priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                roi_ctx = _get_roi_context('qbr', None, arr)
                all_actions.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'action_title': 'Schedule QBR',
                    'action_description': f'QBR frequency at {qbr_val:.0f}/yr (target 3+). Schedule next review.',
                    'action_type': 'qbr',
                    'related_playbook_id': None,
                    'urgency': 'high',
                    'impact_score': impact, 'effort_score': effort,
                    'priority_index': priority_index,
                    'account_health': round(overall_health, 1),
                    'estimated_hours': 4,
                    'estimated_duration_display': '1-2 days',
                    **roi_ctx,
                })

            # Expansion call (P5-KPI7 > 70%)
            if exp_kpi is not None and exp_kpi > 70:
                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 30
                priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                roi_ctx = _get_roi_context('expansion', None, arr)
                all_actions.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'action_title': 'Expansion Opportunity Call',
                    'action_description': f'Expansion probability at {exp_kpi:.0f}%. Schedule capacity planning discussion.',
                    'action_type': 'expansion',
                    'related_playbook_id': None,
                    'urgency': 'opportunity',
                    'impact_score': impact, 'effort_score': effort,
                    'priority_index': priority_index,
                    'account_health': round(overall_health, 1),
                    'estimated_hours': 3,
                    'estimated_duration_display': '1 day',
                    **roi_ctx,
                })

        # Sort by priority_index DESC, take top 10
        all_actions.sort(key=lambda a: a['priority_index'], reverse=True)
        top_actions = all_actions[:10]

        for i, action in enumerate(top_actions, 1):
            action['rank'] = i
            action['id'] = f"act-{i:03d}"

        # Summary
        urgency_counts = {'critical': 0, 'high': 0, 'opportunity': 0, 'medium': 0}
        total_hours = 0
        for a in top_actions:
            urg = a.get('urgency', 'medium')
            urgency_counts[urg] = urgency_counts.get(urg, 0) + 1
            total_hours += a.get('estimated_hours', 0)

        total_roi_impact = sum(a.get('roi_projected_impact', 0) for a in top_actions)
        roi_metrics_involved = list({a['roi_metric_name'] for a in top_actions if a.get('roi_metric_name')})

        return {
            "date": datetime.utcnow().strftime('%Y-%m-%d'),
            "actions": top_actions,
            "summary": {
                "total_actions": len(top_actions),
                "critical_count": urgency_counts.get('critical', 0),
                "high_count": urgency_counts.get('high', 0),
                "opportunity_count": urgency_counts.get('opportunity', 0),
                "total_estimated_hours": total_hours,
                "total_roi_projected_impact": total_roi_impact,
                "roi_metrics_involved": roi_metrics_involved,
            },
        }


@mcp.tool
def get_portfolio_roi_summary(customer_id: int) -> dict:
    """Get the complete ROI story for a customer portfolio — historical proof (what we delivered) + forward projection (what we will deliver) + bridging narrative + trajectory assessment. Covers all accounts.

    Args:
        customer_id: The customer (tenant) ID
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from outcome_roi_engine import calculate_outcome_story
        from outcome_roi_api import _extract_historical_actuals, _extract_accounts_at_risk

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        if not accounts:
            raise ToolError(f"No accounts found for customer {customer_id}")

        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None
        account_ids = [a.account_id for a in accounts]

        # Extract historical metric actuals from DB
        metric_actuals, data_source = _extract_historical_actuals(accounts, 6)

        # Identify at-risk accounts per Power of 1 metric
        accounts_at_risk = _extract_accounts_at_risk(accounts, customer_id=customer_id)

        story = calculate_outcome_story(
            metric_actuals=metric_actuals,
            target_improvement_pct=4.0,
            account_arr=total_arr,
            projection_months=6,
            accounts_at_risk=accounts_at_risk,
            customer_id=customer_id,
            account_ids=account_ids,
        )

        return {
            "customer_id": customer_id,
            "total_arr": total_arr,
            "account_count": len(accounts),
            "data_source": data_source,
            "story": story,
        }


# ===================================================================
# Entrypoint
# ===================================================================
if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if transport == "http":
        os.environ["MCP_TRANSPORT"] = "http"
        mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
    else:
        os.environ["MCP_TRANSPORT"] = "stdio"
        mcp.run(transport="stdio")
