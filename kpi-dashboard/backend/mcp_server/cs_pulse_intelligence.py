#!/usr/bin/env python3
"""
CS Pulse Intelligence MCP Server — Account health, signals, playbooks, and
context-graph intelligence tools.

Extracted from the monolithic cs_pulse_mcp_server.py.  Runs on port 8001.

Usage:
  # stdio (default)
  python backend/mcp_server/cs_pulse_intelligence.py

  # Streamable HTTP
  python backend/mcp_server/cs_pulse_intelligence.py http
"""

import os
import sys

# Ensure backend is on the Python path
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from mcp_server import common

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "CS Pulse Intelligence",
    instructions=common.load_system_prompt(),
)


# ---------------------------------------------------------------------------
# Resource: system prompt for Claude (end users fetch this via MCP)
# ---------------------------------------------------------------------------
@mcp.resource(
    "cspulse://system-prompt",
    name="CS Pulse MCP system prompt",
    description="System prompt for Claude (and other LLMs) when using the CS Pulse MCP server. Copy or use as project instructions.",
    mime_type="text/markdown",
)
def get_system_prompt() -> str:
    """Returns the full system prompt text for CS Pulse MCP. Use as Claude project/custom instructions."""
    return common.load_system_prompt_content()


# ---------------------------------------------------------------------------
# Local helpers (used only within this file)
# ---------------------------------------------------------------------------

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


def _mermaid_safe(text: str, max_len: int = 40) -> str:
    """Escape and truncate text for Mermaid diagram labels."""
    if not text:
        return ""
    # Remove characters that break Mermaid syntax
    safe = text.replace('"', "'").replace("[", "(").replace("]", ")")
    safe = safe.replace("{", "(").replace("}", ")").replace("`", "'")
    safe = safe.replace("<", "\u2039").replace(">", "\u203a").replace("#", "")
    if len(safe) > max_len:
        safe = safe[: max_len - 1] + "\u2026"
    return safe


def _format_revenue_short(amount: float) -> str:
    """Format revenue as short string, e.g. '$5.2M' or '$424K'."""
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    elif amount > 0:
        return f"${amount:,.0f}"
    return ""


# ===================================================================
# Tool 0: Platform Instructions (call FIRST before any other tool)
# ===================================================================

@mcp.tool
def get_platform_instructions() -> dict:
    """IMPORTANT: Call this tool FIRST before using any other CS Pulse tools.

    Returns the complete platform context including tenant model (customer_id vs account_id),
    health score thresholds, tool orchestration patterns, revenue double-counting rules,
    and response guidelines. Without these instructions you may misinterpret tool responses
    or produce inaccurate analysis.

    This tool requires no parameters. Call it once at the start of each conversation.
    """
    content = common.load_system_prompt()
    return {
        "instructions": content,
        "status": "loaded",
        "tool_count": 20,
        "note": (
            "These instructions are now in your context. Follow them for all subsequent "
            "tool calls. Key rules: (1) customer_id is the tenant, account_id is one of "
            "their accounts. (2) Never manually sum revenue from nodes \u2014 use "
            "get_revenue_at_risk() only. (3) Health thresholds: critical <50, at_risk 50-69, "
            "healthy >=70."
        ),
    }


# ===================================================================
# Tool: get_kpi_catalog
# ===================================================================

@mcp.tool
def get_kpi_catalog(customer_id: int = 0) -> dict:
    """Return the canonical KPI catalog with pillar names, KPI names, and default weights.

    Use this tool whenever you need to display or reference pillar names, KPI names,
    or weight values. NEVER guess or invent KPI names \u2014 always use this catalog.

    If customer_id is provided, auto-detects the customer's vertical and returns
    the correct pillar/KPI definitions plus any calibrated weights (from Wizard C).
    If customer_id=0 or omitted, returns the DC2S platform defaults.

    No authentication required.
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        # Determine vertical for this customer
        vertical = 'dc2_s'
        if customer_id and int(customer_id) > 0:
            try:
                vertical = common.resolve_customer_vertical(int(customer_id))
            except Exception:
                pass

        # Load the right definitions for this vertical
        kpi_defs = common.get_kpi_definitions(vertical)

        # Load pillar definitions
        if vertical in ('saas_premium', 'saas'):
            try:
                from verticals.saas_premium.kpi_definitions import SAAS_PILLARS, SAAS_PILLAR_WEIGHTS
                PILLARS = SAAS_PILLARS
                default_l2 = SAAS_PILLAR_WEIGHTS
            except ImportError:
                from verticals.dc2_s.kpi_definitions import DC2S_PILLARS
                PILLARS = DC2S_PILLARS
                default_l2 = {'P1': 0.15, 'P2': 0.20, 'P3': 0.25, 'P4': 0.15, 'P5': 0.25}
        else:
            from verticals.dc2_s.kpi_definitions import DC2S_PILLARS
            PILLARS = DC2S_PILLARS
            default_l2 = {'P1': 0.15, 'P2': 0.20, 'P3': 0.25, 'P4': 0.15, 'P5': 0.25}

        # Build pillar catalog
        pillar_catalog = {}
        for pcode, pdata in PILLARS.items():
            pillar_kpis = {
                kcode: {
                    'name': kdata['name'],
                    'weight_l1': kdata.get('weight_l1', kdata.get('weight', 0)),
                    'unit': kdata.get('unit', ''),
                    'direction': kdata.get('direction', ''),
                    'range_min': kdata.get('range_min'),
                    'range_max': kdata.get('range_max'),
                    'target': kdata.get('target'),
                }
                for kcode, kdata in sorted(kpi_defs.items())
                if kdata.get('pillar') == pcode
            }
            pillar_catalog[pcode] = {
                'name': pdata['name'],
                'kpi_count': len(pillar_kpis),
                'kpis': pillar_kpis,
            }

        # Customer-specific weights if requested
        customer_l2 = None
        customer_l1 = None
        if customer_id and int(customer_id) > 0:
            try:
                from models import CustomerConfig
                cc = CustomerConfig.query.filter_by(
                    customer_id=int(customer_id)
                ).first()
                if cc:
                    if cc.dc2s_pillar_weights:
                        customer_l2 = cc.dc2s_pillar_weights
                    if cc.dc2s_kpi_weights:
                        customer_l1 = cc.dc2s_kpi_weights
            except Exception:
                pass

        result = {
            'scope': 'platform',
            'vertical': vertical,
            'total_pillars': len(pillar_catalog),
            'total_kpis': sum(p['kpi_count'] for p in pillar_catalog.values()),
            'default_pillar_weights_l2': default_l2,
            'pillars': pillar_catalog,
            'weight_rollup': (
                'L1 (KPI scores x weight_l1) \u2192 L2 (pillar scores x pillar_weight) '
                '\u2192 L3 (account health) \u2192 L4 (customer health = revenue-weighted avg of L3)'
            ),
        }

        if customer_id and int(customer_id) > 0:
            result['customer_id'] = int(customer_id)
            result['customer_pillar_weights_l2'] = customer_l2 or 'not configured \u2014 using defaults'
            result['customer_kpi_weights_l1'] = customer_l1 or 'not configured \u2014 using defaults'

        return result


# ===================================================================
# Account Intelligence
# ===================================================================

@mcp.tool
def list_accounts(customer_id: int) -> dict:
    """List all accounts with health scores for a customer.

    TENANT MODEL: customer_id is the CS Pulse tenant (the company using the platform),
    NOT the end-user. Each tenant has multiple accounts (their end-customers).
    Health thresholds: critical <50, at_risk 50-69, healthy >=70.

    Args:
        customer_id: The customer (tenant) ID
    """
    common.check_mcp_enabled()
    common.require_auth(customer_id)
    app = common.get_flask_app()

    with app.app_context():
        from models import Account
        import utils.health_thresholds as ht

        vertical = common.resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = common.get_health_functions(vertical)

        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
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

            arr = common.get_account_arr(acct)

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

        # Portfolio summary
        total_arr = sum(r["arr"] for r in results)
        avg_health = round(
            sum(r["health_score"] for r in results) / len(results), 1
        ) if results else 0

        return {
            "scope": "portfolio",
            "customer_id": customer_id,
            "total_accounts": len(results),
            "portfolio_summary": {
                "total_arr": round(total_arr, 2),
                "avg_health_score": avg_health,
            },
            "accounts": results,
        }


@mcp.tool
def get_account_health(customer_id: int, account_id: int) -> dict:
    """Get detailed health score and pillar breakdown for a specific account.

    Health is computed from 5 pillars (P1-P5): AI/ML Performance, Infrastructure Reliability,
    Cloud & DevOps, Customer Engagement, Commercial & Expansion.
    Thresholds: critical <50, at_risk 50-69, healthy >=70.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
    """
    common.check_mcp_enabled()
    common.require_account_auth(customer_id, account_id)
    app = common.get_flask_app()

    with app.app_context():
        from models import Account
        import utils.health_thresholds as ht

        vertical = common.resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = common.get_health_functions(vertical)

        account = common.validate_account_ownership(customer_id, account_id)

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

        arr = common.get_account_arr(account)

        return {
            "scope": "account",
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
    common.check_mcp_enabled()
    common.require_auth(customer_id)
    app = common.get_flask_app()

    with app.app_context():
        from models import Account
        import utils.health_thresholds as ht

        vertical = common.resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = common.get_health_functions(vertical)

        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
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
                arr = common.get_account_arr(acct)
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

        # Compute portfolio total ARR for pct_arr_at_risk
        total_portfolio_arr = sum(common.get_account_arr(a) for a in accounts)
        pct_arr_at_risk = round(
            (total_arr_at_risk / total_portfolio_arr * 100) if total_portfolio_arr else 0, 1
        )

        return {
            "scope": "portfolio",
            "customer_id": customer_id,
            "threshold": threshold,
            "at_risk_count": len(at_risk),
            "total_accounts": len(accounts),
            "total_arr_at_risk": round(total_arr_at_risk, 2),
            "pct_arr_at_risk": pct_arr_at_risk,
            "total_portfolio_arr": round(total_portfolio_arr, 2),
            "accounts": at_risk,
        }


# ===================================================================
# Journey & Graph Visualization
# ===================================================================

@mcp.tool
def get_account_journey_timeline(
    customer_id: int,
    account_id: int,
    limit: int = 50,
) -> dict:
    """Get a chronological timeline of ALL context graph events for an account.

    Returns signals, decisions, outcomes, and stakeholder events in date order
    with a pre-computed revenue summary. Replaces multiple search_signals calls.
    The revenue_summary field uses get_revenue_at_risk internally (deduplicated).

    PREFERRED over calling search_signals multiple times \u2014 one call replaces 3+ search_signals calls.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
        limit: Max events to return (default 50, max 200)
    """
    common.check_mcp_enabled()
    common.require_account_auth(customer_id, account_id)
    app = common.get_flask_app()

    with app.app_context():
        common.check_context_graph(customer_id)
        from models import ContextNode, db
        from utils.context_graph import get_revenue_at_risk
        from datetime import datetime

        account = common.validate_account_ownership(customer_id, account_id)
        arr = common.get_account_arr(account)

        limit = min(max(limit, 1), 200)
        now = datetime.utcnow()

        # All non-expired nodes, chronological
        nodes = (
            ContextNode.query
            .filter(
                ContextNode.account_id == account_id,
                db.or_(
                    ContextNode.expires_at.is_(None),
                    ContextNode.expires_at > now,
                ),
            )
            .order_by(ContextNode.occurred_at.asc())
            .limit(limit)
            .all()
        )

        if not nodes:
            return {
                "scope": "account",
                "account_id": account_id,
                "account_name": account.account_name,
                "event_count": 0,
                "timeline": [],
                "revenue_summary": get_revenue_at_risk(account_id),
            }

        # Counts by type
        counts: dict = {}
        for n in nodes:
            counts[n.node_type] = counts.get(n.node_type, 0) + 1

        # Build compact timeline entries
        timeline = []
        for n in nodes:
            props = n.properties or {}
            entry = {
                "node_id": n.node_id,
                "node_type": n.node_type,
                "node_subtype": n.node_subtype,
                "title": n.title,
                "occurred_at": n.occurred_at.isoformat() if n.occurred_at else None,
            }
            # Sentiment from properties (varies by node type)
            sentiment = props.get("sentiment") or props.get("sentiment_score")
            if sentiment is not None:
                entry["sentiment"] = sentiment

            # Stakeholder context
            sname = props.get("stakeholder_name") or props.get("stakeholder_title")
            if sname:
                entry["stakeholder"] = sname

            # Revenue \u2014 only on OUTCOME nodes (signals are null)
            if n.revenue_impact is not None:
                entry["revenue_impact"] = float(n.revenue_impact)
                entry["revenue_impact_type"] = n.revenue_impact_type

            timeline.append(entry)

        rev = get_revenue_at_risk(account_id)

        return {
            "scope": "account",
            "account_id": account_id,
            "account_name": account.account_name,
            "arr": arr,
            "date_range": {
                "start": nodes[0].occurred_at.isoformat() if nodes[0].occurred_at else None,
                "end": nodes[-1].occurred_at.isoformat() if nodes[-1].occurred_at else None,
            },
            "event_count": len(nodes),
            "counts_by_type": counts,
            "revenue_summary": rev,
            "timeline": timeline,
        }


# ===================================================================
# External System Integration \u2014 Simulated
# ===================================================================

@mcp.tool
def get_crm_account_data(customer_id: int, account_id: int) -> dict:
    """Pull CRM data for an account \u2014 contract details, renewal opportunity, champion contacts, usage metrics. Simulates Salesforce integration; reads from CS Pulse platform data.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to pull CRM data for
    """
    common.check_mcp_enabled()
    common.require_account_auth(customer_id, account_id)
    app = common.get_flask_app()

    with app.app_context():
        vertical = common.resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = common.get_health_functions(vertical)
        import utils.health_thresholds as ht
        from datetime import datetime, date

        account = common.validate_account_ownership(customer_id, account_id)

        profile = _get_account_profile(account)
        arr = common.get_account_arr(account)

        # Health for renewal probability \u2014 prefer pre-calculated scores
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
            "scope": "account",
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
    """Pull support ticket summary for an account \u2014 open tickets, SLA compliance, escalations, risk indicators. Simulates ServiceNow integration; derives ticket data from operational KPIs and qualitative signals.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to pull ticket data for
    """
    common.check_mcp_enabled()
    common.require_account_auth(customer_id, account_id)
    app = common.get_flask_app()

    with app.app_context():
        from models import QualitativeSignal
        vertical = common.resolve_customer_vertical(customer_id)
        _, _get_trailing_kpi_values, _ = common.get_health_functions(vertical)
        import math

        account = common.validate_account_ownership(customer_id, account_id)

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
                "summary": (getattr(sig, 'content', '') or "")[:200],
                "stakeholder": getattr(sig, 'stakeholder_level', '') or "",
            })

        return {
            "scope": "account",
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
    """Pull customer feedback for an account \u2014 NPS trend, CSAT indicators, VoC summaries, CSM relationship assessment. Simulates survey system integration; derives sentiment from qualitative signals and health data.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to pull feedback for
    """
    common.check_mcp_enabled()
    common.require_account_auth(customer_id, account_id)
    app = common.get_flask_app()

    with app.app_context():
        from models import QualitativeSignal
        vertical = common.resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = common.get_health_functions(vertical)
        import utils.health_thresholds as ht

        account = common.validate_account_ownership(customer_id, account_id)

        kpi_values = _get_trailing_kpi_values(account_id)  # still needed for KPI values

        # Prefer pre-calculated health scores (single source of truth)
        precalc_health, precalc_status, precalc_pillars = get_precalculated_scores(account_id)
        if precalc_health is not None:
            health = precalc_health
            health_status = precalc_status
            pillars = precalc_pillars or {}
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
            text = getattr(sig, 'content', '') or ''
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
            "scope": "account",
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
# Operational Intelligence
# ===================================================================

@mcp.tool
def get_csm_daily_actions(customer_id: int) -> dict:
    """Get top-10 prioritized CSM actions across all accounts (portfolio-level). Each action includes the linked playbook, urgency level, estimated effort hours, and projected dollar impact via Power-of-1 ROI metric correlation.

    Use for "What should I do today?" or "Morning briefing" questions.
    Priority formula: (impact x 0.6 x arr_weight) - (effort x 0.4)

    Args:
        customer_id: The customer (tenant) ID \u2014 actions span ALL accounts for this tenant
    """
    common.check_mcp_enabled()
    common.require_auth(customer_id)
    app = common.get_flask_app()

    with app.app_context():
        from models import Account
        from datetime import datetime
        import utils.health_thresholds as ht

        vertical = common.resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = common.get_health_functions(vertical)
        PLAYBOOK_CONFIG, should_trigger_playbook = common.get_playbook_config(vertical)
        KPI_DEFS = common.get_kpi_definitions(vertical)

        # CSM action helpers \u2014 currently only in DC2_S, import with fallback
        try:
            if vertical in ('saas_premium', 'saas'):
                from verticals.saas_premium.api_routes import (
                    _normalize_kpi_code_for_health,
                    _compute_impact_score, _compute_effort_score,
                    _determine_urgency, _get_roi_context,
                )
            else:
                raise ImportError("use dc2_s")
        except (ImportError, AttributeError):
            from verticals.dc2_s.api_routes import (
                _normalize_kpi_code_for_health,
                _compute_impact_score, _compute_effort_score,
                _determine_urgency, _get_roi_context,
            )

        # Alias for backward compat in the rest of this function
        DC2S_KPIS = KPI_DEFS

        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
        ).all()

        if not accounts:
            return {
                "scope": "portfolio",
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
            arr = common.get_account_arr(account)
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
            "scope": "portfolio",
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


# ===================================================================
# Context Graph Search
# ===================================================================

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
    common.check_mcp_enabled()
    common.require_account_auth(customer_id, account_id)
    app = common.get_flask_app()

    with app.app_context():
        common.check_context_graph(customer_id)
        from utils.context_graph import get_nodes

        common.validate_account_ownership(customer_id, account_id)
        nodes = get_nodes(
            account_id=account_id,
            node_type=node_type,
            node_subtype=node_subtype,
            limit=limit,
        )

        return {
            "scope": "account",
            "account_id": account_id,
            "node_type": node_type,
            "node_subtype": node_subtype,
            "count": len(nodes),
            "nodes": [n.to_dict() for n in nodes],
        }


# ===================================================================
# Playbook & Economics
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
    common.check_mcp_enabled()
    common.require_account_auth(customer_id, account_id)
    app = common.get_flask_app()

    with app.app_context():
        common.validate_account_ownership(customer_id, account_id)
        common.ensure_registry()
        from agent_tool_registry import get_tool_registry

        vertical = common.resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = common.get_health_functions(vertical)

        # Always fetch KPI values \u2014 needed for playbook evaluation
        kpi_values = _get_trailing_kpi_values(account_id)

        # Prefer pre-calculated scores (single source of truth)
        precalc_health, _, _ = get_precalculated_scores(account_id)
        if precalc_health is not None:
            health = precalc_health
        else:
            health, _ = calculate_kpi_health(kpi_values, customer_id)

        registry = get_tool_registry()
        result = registry.invoke(
            "playbook_recommend",
            account_id=account_id,
            customer_id=customer_id,
            health_score=round(health, 1),
            kpi_values=kpi_values,
        )

        if not result.success:
            raise ToolError(f"Playbook recommendations failed: {result.error}")

        data = result.result
        data["scope"] = "account"
        return data


@mcp.tool
def get_playbook_economics(
    customer_id: int,
    account_arr: float = None,
) -> dict:
    """Get playbook cost bridge economics \u2014 investment breakdown, hours, ROI per playbook.

    Returns per-metric and per-playbook economics derived from:
      - Power of 1 JSON benchmarks (source of truth for budgets)
      - PLAYBOOK_CONFIG hours (manual vs automated breakdown)
      - CSM hourly rate from resource_rates.json

    Use this to answer: "How much do playbooks cost?", "What's the CSM investment?",
    "Show me the investment breakdown", "What's the ROI per playbook run?"

    Args:
        customer_id: The customer (tenant) ID
        account_arr: Customer ARR for scaling (optional, defaults to sum of account revenues)
    """
    common.check_mcp_enabled()
    common.require_auth(customer_id)
    app = common.get_flask_app()

    with app.app_context():
        from models import Account
        from playbook_cost_bridge import calculate_cost_bridge, bridge_to_dict

        # Get account ARR
        if account_arr:
            effective_arr = float(account_arr)
        else:
            accounts = Account.query.filter(
                Account.customer_id == int(customer_id),
            ).all()
            effective_arr = float(sum(common.get_account_arr(a) for a in accounts)) if accounts else 10_000_000

        result = calculate_cost_bridge(account_arr=effective_arr)
        return bridge_to_dict(result)


# ===================================================================
# Stakeholder Map
# ===================================================================

@mcp.tool
def get_stakeholder_map(customer_id: int, account_id: int) -> dict:
    """Get the stakeholder network for an account \u2014 who influenced which decisions and outcomes.

    Returns each stakeholder with their role, engagement details, and the
    decisions and outcomes they are connected to via INVOLVES edges or
    decision_maker_role references.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
    """
    common.check_mcp_enabled()
    common.require_account_auth(customer_id, account_id)
    app = common.get_flask_app()

    with app.app_context():
        common.check_context_graph(customer_id)
        from models import ContextNode, ContextEdge, db
        from datetime import datetime

        account = common.validate_account_ownership(customer_id, account_id)
        now = datetime.utcnow()

        # -- Stakeholder nodes --
        stakeholder_nodes = (
            ContextNode.query
            .filter(
                ContextNode.account_id == account_id,
                ContextNode.node_type == "STAKEHOLDER",
                db.or_(
                    ContextNode.expires_at.is_(None),
                    ContextNode.expires_at > now,
                ),
            )
            .order_by(ContextNode.occurred_at.asc())
            .all()
        )

        # -- Decision and Outcome nodes (for linking) --
        decision_nodes = {
            n.node_id: n
            for n in ContextNode.query.filter(
                ContextNode.account_id == account_id,
                ContextNode.node_type == "DECISION",
            ).all()
        }
        outcome_nodes = {
            n.node_id: n
            for n in ContextNode.query.filter(
                ContextNode.account_id == account_id,
                ContextNode.node_type == "OUTCOME",
            ).all()
        }

        # -- All INVOLVES edges for this account's stakeholders --
        stakeholder_ids = [s.node_id for s in stakeholder_nodes]
        involves_edges = []
        if stakeholder_ids:
            involves_edges = (
                ContextEdge.query
                .filter(
                    ContextEdge.edge_type == "INVOLVES",
                    db.or_(
                        ContextEdge.from_node_id.in_(stakeholder_ids),
                        ContextEdge.to_node_id.in_(stakeholder_ids),
                    ),
                )
                .all()
            )

        # Build adjacency: stakeholder_id -> set of connected node_ids
        stakeholder_connections: dict = {s.node_id: set() for s in stakeholder_nodes}
        for e in involves_edges:
            if e.from_node_id in stakeholder_connections:
                stakeholder_connections[e.from_node_id].add(e.to_node_id)
            if e.to_node_id in stakeholder_connections:
                stakeholder_connections[e.to_node_id].add(e.from_node_id)

        # Also match decision_maker_role against stakeholder titles/subtypes
        for dec in decision_nodes.values():
            dec_props = dec.properties or {}
            maker_role = dec_props.get("decision_maker_role", "")
            if maker_role:
                for s in stakeholder_nodes:
                    if (
                        maker_role.lower() in (s.node_subtype or "").lower()
                        or maker_role.lower() in (s.title or "").lower()
                    ):
                        stakeholder_connections[s.node_id].add(dec.node_id)

        # -- Build response --
        total_decisions = 0
        total_outcomes = 0
        total_revenue = 0.0
        stakeholders = []

        for s in stakeholder_nodes:
            props = s.properties or {}
            connected = stakeholder_connections.get(s.node_id, set())

            connected_decs = []
            connected_outs = []
            for cid in connected:
                if cid in decision_nodes:
                    d = decision_nodes[cid]
                    connected_decs.append({
                        "node_id": d.node_id,
                        "title": d.title,
                        "occurred_at": d.occurred_at.isoformat() if d.occurred_at else None,
                    })
                if cid in outcome_nodes:
                    o = outcome_nodes[cid]
                    rev = float(o.revenue_impact) if o.revenue_impact else 0
                    connected_outs.append({
                        "node_id": o.node_id,
                        "title": o.title,
                        "revenue_impact": rev,
                        "revenue_impact_type": o.revenue_impact_type,
                    })
                    total_revenue += abs(rev)

            total_decisions += len(connected_decs)
            total_outcomes += len(connected_outs)

            stakeholders.append({
                "node_id": s.node_id,
                "name": s.title,
                "role": s.node_subtype,
                "engagement_frequency": props.get("engagement_frequency"),
                "department": props.get("department"),
                "is_active": props.get("is_active", True),
                "sentiment": props.get("sentiment"),
                "connected_decisions": connected_decs,
                "connected_outcomes": connected_outs,
                "edge_count": len(connected),
            })

        # Sort by edge_count descending (most connected first)
        stakeholders.sort(key=lambda x: x["edge_count"], reverse=True)

        return {
            "scope": "account",
            "account_id": account_id,
            "account_name": account.account_name,
            "stakeholder_count": len(stakeholders),
            "stakeholders": stakeholders,
            "influence_summary": (
                f"{len(stakeholders)} stakeholders, "
                f"{total_decisions} decision links, "
                f"{total_outcomes} outcome links, "
                f"{_format_revenue_short(total_revenue)} total revenue influenced"
            ),
        }


# ===================================================================
# Context Graph Mermaid Visualization
# ===================================================================

@mcp.tool
def get_context_graph_mermaid(
    customer_id: int,
    account_id: int,
    max_nodes: int = 30,
) -> dict:
    """Generate a Mermaid flowchart of the context graph for an account.

    Returns a renderable Mermaid diagram string with nodes color-coded by type
    (signal=orange, decision=blue, outcome=green, stakeholder=purple) and
    causal edges labeled. Revenue annotations appear only on OUTCOME nodes.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to visualize
        max_nodes: Maximum nodes in diagram (default 30, max 60)
    """
    common.check_mcp_enabled()
    common.require_account_auth(customer_id, account_id)
    app = common.get_flask_app()

    with app.app_context():
        common.check_context_graph(customer_id)
        from models import ContextNode, ContextEdge, db
        from datetime import datetime

        common.validate_account_ownership(customer_id, account_id)

        max_nodes = min(max(max_nodes, 5), 60)
        now = datetime.utcnow()

        # Nodes -- chronological
        nodes = (
            ContextNode.query
            .filter(
                ContextNode.account_id == account_id,
                db.or_(
                    ContextNode.expires_at.is_(None),
                    ContextNode.expires_at > now,
                ),
            )
            .order_by(ContextNode.occurred_at.asc())
            .limit(max_nodes)
            .all()
        )

        if not nodes:
            return {
                "scope": "account",
                "account_id": account_id,
                "mermaid": "flowchart TD\n    empty[No context graph data]",
                "node_count": 0,
                "edge_count": 0,
            }

        node_ids = {n.node_id for n in nodes}

        # Edges between visible nodes
        node_id_list = list(node_ids)
        edges = (
            ContextEdge.query
            .filter(
                ContextEdge.from_node_id.in_(node_id_list),
                ContextEdge.to_node_id.in_(node_id_list),
            )
            .all()
        )

        # -- Build Mermaid --
        lines = [
            "flowchart TD",
            '    classDef signal fill:#FFA500,stroke:#333,color:#000',
            '    classDef decision fill:#4169E1,stroke:#333,color:#fff',
            '    classDef outcome fill:#2E8B57,stroke:#333,color:#fff,stroke-width:3px',
            '    classDef stakeholder fill:#8B5CF6,stroke:#333,color:#fff',
            '    classDef external fill:#6B7280,stroke:#333,color:#fff',
            "",
        ]

        # Node shapes by type
        SHAPE_MAP = {
            "SIGNAL":           ('["', '"]'),           # rounded rect
            "DECISION":         ('{{"', '"}}'),         # hexagon
            "OUTCOME":          ('["', '"]'),           # rect (bold via classDef)
            "STAKEHOLDER":      ('(("', '"))'),         # circle
            "EXTERNAL_CONTEXT": ('["', '"]'),           # rect
        }

        CLASS_MAP = {
            "SIGNAL": "signal",
            "DECISION": "decision",
            "OUTCOME": "outcome",
            "STAKEHOLDER": "stakeholder",
            "EXTERNAL_CONTEXT": "external",
        }

        for n in nodes:
            nid = f"n{n.node_id}"
            date_prefix = ""
            if n.occurred_at:
                date_prefix = n.occurred_at.strftime("%b %d") + ": "

            label = _mermaid_safe(n.title, max_len=35)

            # Revenue annotation on OUTCOME nodes only
            rev_note = ""
            if n.node_type == "OUTCOME" and n.revenue_impact:
                amt = _format_revenue_short(abs(float(n.revenue_impact)))
                rtype = n.revenue_impact_type or "impact"
                rev_note = f"\\n{amt} {rtype}"

            open_br, close_br = SHAPE_MAP.get(n.node_type, ('["', '"]'))
            css_class = CLASS_MAP.get(n.node_type, "signal")

            lines.append(
                f'    {nid}{open_br}{date_prefix}{label}{rev_note}{close_br}:::{css_class}'
            )

        lines.append("")

        # Edges
        for e in edges:
            if e.from_node_id in node_ids and e.to_node_id in node_ids:
                label = e.edge_type or ""
                lines.append(
                    f"    n{e.from_node_id} -->|{label}| n{e.to_node_id}"
                )

        mermaid_str = "\n".join(lines)

        return {
            "scope": "account",
            "account_id": account_id,
            "mermaid": mermaid_str,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "legend": {
                "signal": "orange (#FFA500)",
                "decision": "blue (#4169E1)",
                "outcome": "green (#2E8B57)",
                "stakeholder": "purple (#8B5CF6)",
                "external": "gray (#6B7280)",
            },
        }


# ===================================================================
# Financial / ROI: Power of 1
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
    common.check_mcp_enabled()
    common.require_auth(customer_id)
    app = common.get_flask_app()

    with app.app_context():
        from models import Account
        from power_of_1_model import calculate_power_of_1_impact

        # Determine scope and ARR
        if account_arr:
            scope = "account"
            arr_source = "explicit_account_arr"
            effective_arr = account_arr
        else:
            # Auto-compute portfolio total ARR
            scope = "portfolio"
            arr_source = "portfolio_total"
            accounts = Account.query.filter(
                Account.customer_id == int(customer_id),
            ).all()
            effective_arr = sum(common.get_account_arr(a) for a in accounts)
            if not effective_arr:
                effective_arr = None  # fall back to $10M baseline

        # Resolve vertical from customer record
        po1_vertical = common.resolve_customer_vertical(customer_id)

        result = calculate_power_of_1_impact(
            metric_id=metric_id,
            improvement_pct=improvement_pct,
            account_arr=effective_arr,
            vertical=po1_vertical,
        )

        if "error" in result:
            raise ToolError(f"Power-of-1 calculation failed: {result['error']}")

        result["scope"] = scope
        result["arr_source"] = arr_source
        return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    common.run_server(mcp, default_port=8001)
