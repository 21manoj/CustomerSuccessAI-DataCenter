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
# Load system prompt from file (ships with the server)
# ---------------------------------------------------------------------------
_PROMPT_FILE = os.path.join(_backend_dir, 'config', 'mcp_system_prompt.md')

def _load_system_prompt() -> str:
    """Load MCP system prompt from config/mcp_system_prompt.md.

    Falls back to a compact version if the file is missing.
    """
    try:
        with open(_PROMPT_FILE, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return (
            "AI-native Customer Success platform — health scoring, "
            "signal detection, context graph intelligence, revenue analytics. "
            "SCOPE CONVENTION: Every tool response includes a 'scope' field. "
            "'account' = data for one account, 'portfolio' = aggregated across all accounts, "
            "'node_traversal' = context graph path. "
            "DOLLAR AMOUNTS: All financial figures include 'arr_basis' (explicit or baseline_10m) "
            "and 'arr_basis_value' so you know the ARR used for scaling. "
            "Never mix account-level and portfolio-level dollar figures without labeling scope."
        )

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "CS Pulse",
    instructions=_load_system_prompt(),
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


def _get_dc2s_pillar_labels() -> dict:
    """Return canonical DC2S pillar labels from kpi_definitions.py."""
    try:
        from verticals.dc2_s.kpi_definitions import DC2S_PILLARS
        return {
            code: pillar['name']
            for code, pillar in DC2S_PILLARS.items()
        }
    except ImportError:
        return {
            'P1': 'Deployment Velocity',
            'P2': 'Operational Stability',
            'P3': 'AI Workload Performance',
            'P4': 'Channel & Partner Health',
            'P5': 'Expansion Readiness',
        }


def _validate_account_ownership(customer_id: int, account_id: int):
    """Tenant isolation: verify account belongs to customer, return Account or raise."""
    from models import Account
    account = Account.query.filter_by(
        account_id=account_id,
        customer_id=int(customer_id),
    ).first()
    if not account:
        raise ToolError(
            f"Account {account_id} not found for customer {customer_id}"
        )
    return account


def _resolve_customer_vertical(customer_id: int) -> str:
    """Look up the vertical for a customer. Falls back to 'dc2_s'."""
    from models import Customer
    customer = Customer.query.get(int(customer_id))
    if not customer:
        raise ToolError(f"Customer {customer_id} not found")
    return getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'


def _get_precalculated_scores(account_id: int):
    """Vertical-agnostic: read pre-calculated scores from HealthScore/PillarScore tables.

    Returns (health_score, health_status, pillar_dict) or (None, None, None).
    This is the single source of truth — no vertical module import needed.
    """
    try:
        from models import HealthScore, PillarScore
        import utils.health_thresholds as ht

        hs = HealthScore.query.filter_by(account_id=account_id) \
            .order_by(HealthScore.measurement_month.desc()).first()
        if not hs or hs.health_score is None:
            return None, None, None

        health = float(hs.health_score)
        status = hs.health_status or ht.classify(health)

        pillars = {}
        if hs.contributing_pillars:
            pillars = {k: float(v) for k, v in hs.contributing_pillars.items()}
        else:
            ps_rows = PillarScore.query.filter_by(
                account_id=account_id,
                measurement_month=hs.measurement_month,
            ).all()
            for ps in ps_rows:
                if ps.pillar_score is not None:
                    pillars[ps.pillar_code] = float(ps.pillar_score)

        return health, status, pillars
    except Exception:
        return None, None, None


def _get_trailing_kpi_values_generic(account_id: int) -> dict:
    """Vertical-agnostic: read latest KPI values from KpiScore table.

    Returns dict of {kpi_code: score_value}.
    """
    try:
        from models import KpiScore
        rows = KpiScore.query.filter_by(account_id=account_id) \
            .order_by(KpiScore.measurement_month.desc()).all()
        # Take most recent value per KPI code
        seen = {}
        for r in rows:
            if r.kpi_code not in seen and r.kpi_score is not None:
                seen[r.kpi_code] = float(r.kpi_score)
        return seen
    except Exception:
        return {}


def _get_health_functions(vertical: str):
    """Return (calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores)
    for the given vertical.

    Tries to load the vertical-specific module first. If not installed,
    falls back to generic DB-reading functions (precalculated scores still work;
    live recalculation returns 0).
    """
    if vertical in ('saas_premium', 'saas'):
        try:
            from verticals.saas_premium.api_routes import (
                calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores,
            )
            return calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores
        except ImportError:
            # SaaS Premium module not installed — use generic DB readers.
            # Live recalculation won't work, but pre-calculated scores will.
            def _noop_calculate(kpi_values, customer_id=None):
                return 0.0, {}
            return _noop_calculate, _get_trailing_kpi_values_generic, _get_precalculated_scores

    from verticals.dc2_s.api_routes import (
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores,
    )
    return calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores


def _get_kpi_definitions(vertical: str) -> dict:
    """Return the KPI definitions dict for a vertical."""
    if vertical in ('saas_premium', 'saas'):
        try:
            from verticals.saas_premium.kpi_definitions import SAAS_KPIS
            return SAAS_KPIS
        except ImportError:
            # No SaaS module — return empty dict (KPI names come from DB)
            return {}
    from verticals.dc2_s.kpi_definitions import DC2S_KPIS
    return DC2S_KPIS


def _get_playbook_config(vertical: str):
    """Return (PLAYBOOK_CONFIG, should_trigger_playbook) for a vertical."""
    if vertical in ('saas_premium', 'saas'):
        try:
            from verticals.saas_premium.vertical_config import PLAYBOOK_CONFIG, should_trigger_playbook
            return PLAYBOOK_CONFIG, should_trigger_playbook
        except ImportError:
            return {}, lambda *a, **kw: False
    from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG, should_trigger_playbook
    return PLAYBOOK_CONFIG, should_trigger_playbook


def _require_auth(customer_id: int, required_scope: str = 'read',
                  _api_key: str = None):
    """Enforce API key auth for portfolio/customer-level intelligence tools.

    For HTTP transport: validates customer API key (DB-backed), checks
    tenant isolation (key.customer_id == customer_id), and scope.

    For stdio transport: no-op (local process is trusted) unless _api_key
    is explicitly passed (for testing).

    Args:
        customer_id: The customer_id the tool is operating on.
        required_scope: 'read' (default) or 'write'.
        _api_key: Explicit key for testing (bypasses transport check).
    """
    from mcp_server.auth import require_auth
    require_auth(customer_id, required_scope, _api_key)


def _require_account_auth(customer_id: int, account_id: int,
                          required_scope: str = 'read',
                          _api_key: str = None):
    """Enforce API key auth for account-level intelligence tools.

    Same as _require_auth plus account-level restriction:
    if the key has allowed_account_ids set, the account must be in the list.

    A partner key restricted to [354001, 354003] can only access those
    two accounts, not the full portfolio.

    Args:
        customer_id: The customer (tenant) ID.
        account_id: The specific account being accessed.
        required_scope: 'read' (default) or 'write'.
        _api_key: Explicit key for testing.
    """
    from mcp_server.auth import require_account_auth
    require_account_auth(customer_id, account_id, required_scope, _api_key)


def _load_system_prompt_content() -> str:
    """Load CS Pulse MCP system prompt for Claude. Used by cspulse://system-prompt resource.

    Search order:
      1) CSPULSE_MCP_SYSTEM_PROMPT_PATH env var (explicit override)
      2) backend/config/mcp_system_prompt.md  (works in Docker: /app/backend/config/...)
      3) Repo root CS_PULSE_MCP_SYSTEM_PROMPT.md  (works in local dev)
      4) mcp_server/cs_pulse_mcp_system_prompt.md  (co-located fallback)
    """
    # 1) Explicit path (e.g. in production)
    env_path = os.environ.get("CSPULSE_MCP_SYSTEM_PROMPT_PATH")
    if env_path and os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            return f.read()
    # 2) Search standard locations
    _dir = os.path.dirname(os.path.abspath(__file__))
    for candidate in [
        # Docker & local: backend/config/mcp_system_prompt.md
        os.path.join(_dir, "..", "config", "mcp_system_prompt.md"),
        # Local dev: repo root CS_PULSE_MCP_SYSTEM_PROMPT.md
        os.path.join(_dir, "..", "..", "..", "CS_PULSE_MCP_SYSTEM_PROMPT.md"),
        # Co-located fallback
        os.path.join(_dir, "cs_pulse_mcp_system_prompt.md"),
    ]:
        abs_path = os.path.abspath(candidate)
        if os.path.isfile(abs_path):
            with open(abs_path, "r", encoding="utf-8") as f:
                return f.read()
    return (
        "# CS Pulse MCP — System Prompt\n\n"
        "System prompt file not found. Set CSPULSE_MCP_SYSTEM_PROMPT_PATH or place "
        "mcp_system_prompt.md in backend/config/.\n\n"
        "See docs/MCP_SYSTEM_PROMPT_FOR_END_USERS.md for how to use this with Claude."
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
    return _load_system_prompt_content()


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
    content = _load_system_prompt()
    return {
        "instructions": content,
        "status": "loaded",
        "tool_count": 20,
        "note": (
            "These instructions are now in your context. Follow them for all subsequent "
            "tool calls. Key rules: (1) customer_id is the tenant, account_id is one of "
            "their accounts. (2) Never manually sum revenue from nodes — use "
            "get_revenue_at_risk() only. (3) Health thresholds: critical <50, at_risk 50-69, "
            "healthy >=70."
        ),
    }


# ===================================================================
# Tool: get_kpi_catalog — Canonical KPI definitions & weights
# ===================================================================

@mcp.tool
def get_kpi_catalog(customer_id: int = 0) -> dict:
    """Return the canonical KPI catalog with pillar names, KPI names, and default weights.

    Use this tool whenever you need to display or reference pillar names, KPI names,
    or weight values. NEVER guess or invent KPI names — always use this catalog.

    If customer_id is provided, auto-detects the customer's vertical and returns
    the correct pillar/KPI definitions plus any calibrated weights (from Wizard C).
    If customer_id=0 or omitted, returns the DC2S platform defaults.

    No authentication required.
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        # Determine vertical for this customer
        vertical = 'dc2_s'
        if customer_id and int(customer_id) > 0:
            try:
                vertical = _resolve_customer_vertical(int(customer_id))
            except Exception:
                pass

        # Load the right definitions for this vertical
        kpi_defs = _get_kpi_definitions(vertical)

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
                'L1 (KPI scores x weight_l1) → L2 (pillar scores x pillar_weight) '
                '→ L3 (account health) → L4 (customer health = revenue-weighted avg of L3)'
            ),
        }

        if customer_id and int(customer_id) > 0:
            result['customer_id'] = int(customer_id)
            result['customer_pillar_weights_l2'] = customer_l2 or 'not configured — using defaults'
            result['customer_kpi_weights_l1'] = customer_l1 or 'not configured — using defaults'

        return result


# ===================================================================
# Group 1: Account Intelligence (3 tools)
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
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account, DC2SKPI, Customer, db
        from sqlalchemy import func as sqlfunc
        import utils.health_thresholds as ht

        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)

        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
        ).all()

        # Pre-fetch last KPI data timestamp per account (single query)
        account_ids = [a.account_id for a in accounts]
        last_data_map = {}
        if account_ids:
            try:
                last_data_rows = db.session.query(
                    DC2SKPI.account_id,
                    sqlfunc.max(DC2SKPI.measured_at).label('last_data_at'),
                ).filter(
                    DC2SKPI.account_id.in_(account_ids),
                ).group_by(DC2SKPI.account_id).all()
                for row in last_data_rows:
                    last_data_map[row.account_id] = row.last_data_at
            except Exception:
                pass  # DC2SKPI table may not exist for all verticals

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

            last_data_at = last_data_map.get(acct.account_id)

            results.append({
                "account_id": acct.account_id,
                "account_name": acct.account_name,
                "health_score": round(health, 1),
                "status": status,
                "arr": arr,
                "pillar_scores": {k: round(v, 1) for k, v in pillars.items()},
                "updated_at": acct.updated_at.isoformat() if acct.updated_at else None,
                "last_data_at": last_data_at.isoformat() if last_data_at else None,
            })

        # Sort by health (worst first)
        results.sort(key=lambda x: x["health_score"])

        # Portfolio summary
        total_arr = sum(r["arr"] for r in results)
        avg_health = round(
            sum(r["health_score"] for r in results) / len(results), 1
        ) if results else 0

        # Fetch customer created_at for display
        customer_obj = Customer.query.filter_by(customer_id=int(customer_id)).first()
        customer_created = customer_obj.created_at.isoformat() if customer_obj and customer_obj.created_at else None

        return {
            "scope": "portfolio",
            "customer_id": customer_id,
            "customer_created_at": customer_created,
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
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        import utils.health_thresholds as ht

        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)

        account = _validate_account_ownership(customer_id, account_id)

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
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        import utils.health_thresholds as ht

        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)

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

        # Compute portfolio total ARR for pct_arr_at_risk
        total_portfolio_arr = sum(_get_account_arr(a) for a in accounts)
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

    IMPORTANT: This is the ONLY authoritative source for revenue figures. Never manually
    sum revenue_impact values from individual context graph nodes — that causes double-counting.
    Individual SIGNAL nodes have revenue_impact=null; only OUTCOME nodes carry revenue.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from utils.context_graph import get_revenue_at_risk as _get_rev

        account = _validate_account_ownership(customer_id, account_id)
        result = _get_rev(account_id)
        result["scope"] = "account"
        result["account_id"] = account_id
        result["account_name"] = account.account_name
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
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from utils.context_graph import get_causal_chain as _get_chain
        from models import ContextNode, db

        start_node = db.session.get(ContextNode, node_id)
        if not start_node:
            raise ToolError(f"Node {node_id} not found")

        # Tenant isolation: verify node belongs to this customer
        if start_node.customer_id != int(customer_id):
            raise ToolError(
                f"Node {node_id} not found for customer {customer_id}"
            )

        chain = _get_chain(node_id, direction=direction, max_depth=5)

        return {
            "scope": "node_traversal",
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
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from utils.context_graph import get_account_graph_summary

        _validate_account_ownership(customer_id, account_id)
        result = get_account_graph_summary(account_id)
        result["scope"] = "account"
        return result


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
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from utils.context_graph import get_nodes

        _validate_account_ownership(customer_id, account_id)
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
# Group 3: Financial / ROI (3 tools)
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
    _require_auth(customer_id)
    app = _get_flask_app()

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
            effective_arr = sum(_get_account_arr(a) for a in accounts)
            if not effective_arr:
                effective_arr = None  # fall back to $10M baseline

        # Resolve vertical from customer record
        po1_vertical = _resolve_customer_vertical(customer_id)

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
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        from outcome_roi_engine import calculate_outcome_story
        from power_of_1_model import POWER_OF_1_METRICS

        account = _validate_account_ownership(customer_id, account_id)

        arr = _get_account_arr(account)

        # Build metric_actuals in the format expected by calculate_outcome_story:
        # {metric_id: {"current": float, "baseline": float}}
        # Use baselines as defaults (the engine computes delta from there)
        metric_actuals = {}
        for mid, m in POWER_OF_1_METRICS.items():
            metric_actuals[mid] = {"current": m.baseline, "baseline": m.baseline}

        # Determine vertical from account
        acct_vertical = getattr(account, 'vertical', None)

        story = calculate_outcome_story(
            metric_actuals=metric_actuals,
            target_improvement_pct=target_improvement_pct,
            account_arr=arr,
            projection_months=projection_months,
            customer_id=customer_id,
            account_ids=[account_id],
            vertical=acct_vertical,
        )

        story["scope"] = "account"
        return story


@mcp.tool
def get_playbook_economics(
    customer_id: int,
    account_arr: float = None,
) -> dict:
    """Get playbook cost bridge economics — investment breakdown, hours, ROI per playbook.

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
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

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
            effective_arr = float(sum(_get_account_arr(a) for a in accounts)) if accounts else 10_000_000

        result = calculate_cost_bridge(account_arr=effective_arr)
        return bridge_to_dict(result)


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
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _validate_account_ownership(customer_id, account_id)
        _ensure_registry()
        from agent_tool_registry import get_tool_registry

        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)

        # Always fetch KPI values — needed for playbook evaluation
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
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)
        import utils.health_thresholds as ht
        from datetime import datetime, date

        account = _validate_account_ownership(customer_id, account_id)

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
    """Pull support ticket summary for an account — open tickets, SLA compliance, escalations, risk indicators. Simulates ServiceNow integration; derives ticket data from operational KPIs and qualitative signals.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to pull ticket data for
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        from models import QualitativeSignal
        vertical = _resolve_customer_vertical(customer_id)
        _, _get_trailing_kpi_values, _ = _get_health_functions(vertical)
        import math

        account = _validate_account_ownership(customer_id, account_id)

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
    """Pull customer feedback for an account — NPS trend, CSAT indicators, VoC summaries, CSM relationship assessment. Simulates survey system integration; derives sentiment from qualitative signals and health data.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to pull feedback for
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        from models import QualitativeSignal
        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)
        import utils.health_thresholds as ht

        account = _validate_account_ownership(customer_id, account_id)

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
# Group 6: Operational Intelligence (2 tools)
# ===================================================================

@mcp.tool
def get_csm_daily_actions(customer_id: int) -> dict:
    """Get top-10 prioritized CSM actions across all accounts (portfolio-level). Each action includes the linked playbook, urgency level, estimated effort hours, and projected dollar impact via Power-of-1 ROI metric correlation.

    Use for "What should I do today?" or "Morning briefing" questions.
    Priority formula: (impact × 0.6 × arr_weight) - (effort × 0.4)

    Args:
        customer_id: The customer (tenant) ID — actions span ALL accounts for this tenant
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from datetime import datetime
        import utils.health_thresholds as ht

        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)
        PLAYBOOK_CONFIG, should_trigger_playbook = _get_playbook_config(vertical)
        KPI_DEFS = _get_kpi_definitions(vertical)

        # CSM action helpers — currently only in DC2_S, import with fallback
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


@mcp.tool
def get_portfolio_roi_summary(customer_id: int) -> dict:
    """Get the complete ROI story for a customer portfolio — historical proof (what we delivered) + forward projection (what we will deliver) + bridging narrative + trajectory assessment. Covers all accounts.

    Args:
        customer_id: The customer (tenant) ID
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
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

        # Determine vertical from first account (portfolio is single-vertical)
        portfolio_vertical = getattr(accounts[0], 'vertical', None) if accounts else None

        story = calculate_outcome_story(
            metric_actuals=metric_actuals,
            target_improvement_pct=4.0,
            account_arr=total_arr,
            projection_months=6,
            accounts_at_risk=accounts_at_risk,
            customer_id=customer_id,
            account_ids=account_ids,
            vertical=portfolio_vertical,
        )

        return {
            "scope": "portfolio",
            "customer_id": customer_id,
            "total_arr": total_arr,
            "arr_basis": "portfolio_total",
            "arr_basis_value": total_arr,
            "account_count": len(accounts),
            "data_source": data_source,
            "story": story,
        }


# ===================================================================
# Group 7: Portfolio / CEO View (2 tools)
# ===================================================================

@mcp.tool
def list_portfolio_customers(portfolio_id: int) -> dict:
    """List all customers in a PE portfolio with health and ARR summary.

    NOTE: This tool uses portfolio_id (not customer_id). A portfolio is a PE fund or
    holding company that owns multiple customers. Each customer has its own accounts.

    Args:
        portfolio_id: The portfolio (PE fund / holding company) ID
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Portfolio, PortfolioMembership, Customer, Account
        import utils.health_thresholds as ht

        portfolio = Portfolio.query.filter_by(
            portfolio_id=portfolio_id, enabled=True,
        ).first()
        if not portfolio:
            raise ToolError(f"Portfolio {portfolio_id} not found or disabled")

        memberships = PortfolioMembership.query.filter_by(
            portfolio_id=portfolio_id,
        ).all()

        if not memberships:
            return {
                "scope": "portfolio",
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio.portfolio_name,
                "customers": [],
                "summary": {"total_customers": 0, "total_arr": 0, "avg_health": 0},
            }

        customer_summaries = []
        for mem in memberships:
            customer = Customer.query.filter_by(
                customer_id=mem.customer_id,
            ).first()
            if not customer:
                continue

            mem_vertical = getattr(customer, 'vertical', None) or mem.vertical or 'dc2_s'
            calc_health, get_trailing, get_precalc = _get_health_functions(mem_vertical)

            accounts = Account.query.filter(
                Account.customer_id == mem.customer_id,
            ).all()

            total_arr = sum(_get_account_arr(a) for a in accounts)
            health_scores = []
            at_risk_count = 0

            for acct in accounts:
                ph, ps, _ = get_precalc(acct.account_id)
                if ph is not None:
                    health_scores.append(ph)
                    if ps in ('at_risk', 'critical'):
                        at_risk_count += 1
                else:
                    kv = get_trailing(acct.account_id)
                    h, _ = calc_health(kv, mem.customer_id)
                    health_scores.append(h)
                    if ht.classify(h) in ('at_risk', 'critical'):
                        at_risk_count += 1

            avg_health = round(
                sum(health_scores) / len(health_scores), 1
            ) if health_scores else 0

            customer_summaries.append({
                "customer_id": mem.customer_id,
                "customer_name": getattr(customer, 'customer_name', None) or getattr(customer, 'company_name', 'Unknown'),
                "created_at": customer.created_at.isoformat() if customer.created_at else None,
                "vertical": mem_vertical,
                "status": mem.status,
                "total_accounts": len(accounts),
                "total_arr": round(total_arr, 2),
                "avg_health_score": avg_health,
                "at_risk_accounts": at_risk_count,
                "synergies_realized": mem.synergies_realized,
                "synergy_value": float(mem.synergy_value or 0),
            })

        customer_summaries.sort(key=lambda x: x["avg_health_score"])

        total_arr = sum(c["total_arr"] for c in customer_summaries)
        total_accounts = sum(c["total_accounts"] for c in customer_summaries)
        avg_health = round(
            sum(c["avg_health_score"] * c["total_accounts"] for c in customer_summaries)
            / total_accounts, 1
        ) if total_accounts else 0

        return {
            "scope": "portfolio",
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "total_aum": float(portfolio.total_aum) if portfolio.total_aum else None,
            "customers": customer_summaries,
            "summary": {
                "total_customers": len(customer_summaries),
                "total_accounts": total_accounts,
                "total_arr": round(total_arr, 2),
                "avg_health_score": avg_health,
                "total_at_risk": sum(c["at_risk_accounts"] for c in customer_summaries),
            },
        }


@mcp.tool
def get_portfolio_cross_customer_comparison(portfolio_id: int) -> dict:
    """Compare all customers in a portfolio side-by-side: health, ARR, risk, expansion. CEO-level view.

    NOTE: Uses portfolio_id (not customer_id). Includes context graph revenue intelligence
    when enabled. Use for board-level cross-company benchmarking.

    Args:
        portfolio_id: The portfolio (PE fund / holding company) ID
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Portfolio, PortfolioMembership, Customer, Account
        import utils.health_thresholds as ht

        portfolio = Portfolio.query.filter_by(
            portfolio_id=portfolio_id, enabled=True,
        ).first()
        if not portfolio:
            raise ToolError(f"Portfolio {portfolio_id} not found or disabled")

        memberships = PortfolioMembership.query.filter_by(
            portfolio_id=portfolio_id,
        ).all()

        comparisons = []
        for mem in memberships:
            customer = Customer.query.filter_by(
                customer_id=mem.customer_id,
            ).first()
            if not customer:
                continue

            mem_vertical = getattr(customer, 'vertical', None) or mem.vertical or 'dc2_s'
            calc_health, get_trailing, get_precalc = _get_health_functions(mem_vertical)

            accounts = Account.query.filter(
                Account.customer_id == mem.customer_id,
            ).all()

            total_arr = sum(_get_account_arr(a) for a in accounts)
            pillar_totals = {}
            health_scores = []
            statuses = {'healthy': 0, 'at_risk': 0, 'critical': 0}

            for acct in accounts:
                ph, ps, pp = get_precalc(acct.account_id)
                if ph is not None:
                    health_scores.append(ph)
                    statuses[ps] = statuses.get(ps, 0) + 1
                    if pp:
                        for k, v in pp.items():
                            pillar_totals.setdefault(k, []).append(v)
                else:
                    kv = get_trailing(acct.account_id)
                    h, pillars = calc_health(kv, mem.customer_id)
                    health_scores.append(h)
                    cls = ht.classify(h)
                    statuses[cls] = statuses.get(cls, 0) + 1
                    for k, v in pillars.items():
                        pillar_totals.setdefault(k, []).append(v)

            avg_health = round(
                sum(health_scores) / len(health_scores), 1
            ) if health_scores else 0

            avg_pillars = {
                k: round(sum(v) / len(v), 1) for k, v in pillar_totals.items()
            } if pillar_totals else {}

            weakest_pillar = min(avg_pillars, key=avg_pillars.get) if avg_pillars else None

            # Context graph revenue (if enabled)
            revenue_data = None
            try:
                from feature_toggles import is_context_graph_enabled
                if is_context_graph_enabled(mem.customer_id):
                    from utils.context_graph import get_revenue_at_risk as _gar
                    total_rev = {'at_risk': 0, 'protected': 0, 'expansion': 0, 'net_impact': 0}
                    for acct in accounts:
                        rev = _gar(acct.account_id)
                        if rev.get('node_count', 0) > 0:
                            for k in total_rev:
                                total_rev[k] += rev.get(k, 0)
                    revenue_data = {k: round(v, 2) for k, v in total_rev.items()}
            except Exception:
                pass

            comparisons.append({
                "customer_id": mem.customer_id,
                "customer_name": getattr(customer, 'customer_name', None) or getattr(customer, 'company_name', 'Unknown'),
                "total_arr": round(total_arr, 2),
                "avg_health_score": avg_health,
                "account_distribution": statuses,
                "total_accounts": len(accounts),
                "avg_pillar_scores": avg_pillars,
                "weakest_pillar": weakest_pillar,
                "revenue_intelligence": revenue_data,
            })

        comparisons.sort(key=lambda x: x["avg_health_score"])

        return {
            "scope": "portfolio",
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "comparisons": comparisons,
        }


# ===================================================================
# Group 8: Journey & Graph Visualization (3 tools)
# ===================================================================

def _mermaid_safe(text: str, max_len: int = 40) -> str:
    """Escape and truncate text for Mermaid diagram labels."""
    if not text:
        return ""
    # Remove characters that break Mermaid syntax
    safe = text.replace('"', "'").replace("[", "(").replace("]", ")")
    safe = safe.replace("{", "(").replace("}", ")").replace("`", "'")
    safe = safe.replace("<", "‹").replace(">", "›").replace("#", "")
    if len(safe) > max_len:
        safe = safe[: max_len - 1] + "…"
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

    PREFERRED over calling search_signals multiple times — one call replaces 3+ search_signals calls.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
        limit: Max events to return (default 50, max 200)
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from models import ContextNode, db
        from utils.context_graph import get_revenue_at_risk
        from datetime import datetime

        account = _validate_account_ownership(customer_id, account_id)
        arr = _get_account_arr(account)

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

            # Revenue — only on OUTCOME nodes (signals are null)
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
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from models import ContextNode, ContextEdge, db
        from datetime import datetime

        _validate_account_ownership(customer_id, account_id)

        max_nodes = min(max(max_nodes, 5), 60)
        now = datetime.utcnow()

        # Nodes — chronological
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

        # ── Build Mermaid ──
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


@mcp.tool
def get_stakeholder_map(customer_id: int, account_id: int) -> dict:
    """Get the stakeholder network for an account — who influenced which decisions and outcomes.

    Returns each stakeholder with their role, engagement details, and the
    decisions and outcomes they are connected to via INVOLVES edges or
    decision_maker_role references.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from models import ContextNode, ContextEdge, db
        from datetime import datetime

        account = _validate_account_ownership(customer_id, account_id)
        now = datetime.utcnow()

        # ── Stakeholder nodes ──
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

        # ── Decision and Outcome nodes (for linking) ──
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

        # ── All INVOLVES edges for this account's stakeholders ──
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

        # Build adjacency: stakeholder_id → set of connected node_ids
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

        # ── Build response ──
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
# Group 6: Onboarding Tools (13 tools) — FRICTIONLESS AUTH
# ===================================================================
#
# FRICTIONLESS AUTH MODEL:
# These 13 onboarding tools require NO API key. They are open for
# prospects who are evaluating the platform via an AI assistant.
# The auth.py module skips authentication for any tool whose name
# appears in the ONBOARDING_TOOLS set below.
#
# Discovery Phase tools (1-5) are read-only.
# Customer Setup (6-8), Data Ingestion (9-11), and Post-Onboarding
# (12-13) are write tools but still auth-free so that a prospect
# can complete the entire self-service onboarding via MCP without
# ever needing a pre-existing API key.
#
# The create_customer tool auto-generates an API key that the
# prospect can use for the intelligence tools (Group 1-5) later.
# ===================================================================

ONBOARDING_TOOLS = {
    'list_verticals',
    'get_reference_customer',
    'get_csv_templates',
    'get_vertical_config',
    'get_onboarding_status',
    'create_customer',
    'configure_customer_kpis',
    'enable_features',
    'validate_csv',
    'upload_csv',
    'process_data',
    'trigger_wizard',
    'complete_onboarding',
    'clone_customer',
    'export_customer_csvs',
}


def _is_onboarding_tool(name: str) -> bool:
    """Return True if the tool name is in the frictionless onboarding set."""
    return name in ONBOARDING_TOOLS


# -------------------------------------------------------------------
# Discovery Phase (read-only, no auth) — Tools 22-26
# -------------------------------------------------------------------

@mcp.tool
def list_verticals() -> dict:
    """List all available verticals with their KPI counts and config types.

    Discovery tool for prospects — no authentication required.
    Returns each vertical with its description, total KPI count,
    and the number of config type templates available.
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        # Build vertical catalog from kpi_definitions (always available)
        # VerticalTemplate model is optional — used when DB templates exist.
        verticals: dict = {}

        # Try DB-backed VerticalTemplate if available
        try:
            from models import VerticalTemplate
            from extensions import db
            from sqlalchemy import func

            rows = (
                db.session.query(
                    VerticalTemplate.vertical,
                    VerticalTemplate.config_type,
                    func.count(VerticalTemplate.template_id).label('cnt'),
                )
                .group_by(VerticalTemplate.vertical, VerticalTemplate.config_type)
                .all()
            )

            for vertical, config_type, cnt in rows:
                if vertical not in verticals:
                    verticals[vertical] = {
                        'vertical': vertical,
                        'config_types': [],
                        'config_type_count': 0,
                        'kpi_count': 0,
                        'description': None,
                    }
                verticals[vertical]['config_types'].append(config_type)
                verticals[vertical]['config_type_count'] += 1
        except (ImportError, Exception):
            pass  # VerticalTemplate not available yet — use fallback below

        # Enrich with KPI count from kpi_definitions if available
        for v_key, v_info in verticals.items():
            try:
                kpi_defs = _get_kpi_definitions(v_key)
                v_info['kpi_count'] = len(kpi_defs)
            except Exception:
                pass
            if v_key == 'dc2_s':
                v_info['description'] = 'Data Center Infrastructure vertical — AI/ML, infra reliability, cloud & DevOps, customer engagement, expansion'
            elif v_key in ('saas_premium', 'saas'):
                v_info['description'] = 'SaaS Premium vertical — product adoption, operational resilience, growth efficiency, partner ecosystem, strategic value'

        # Fallback: if no DB templates, return known verticals from kpi_definitions
        if not verticals:
            known_verticals = {
                'dc2_s': ('Data Center Infrastructure vertical', 38),
                'saas_premium': ('SaaS Premium vertical — product adoption, engagement, support quality, partner ecosystem, revenue & growth', 35),
            }
            for v_slug, (v_desc, v_default_count) in known_verticals.items():
                try:
                    kpi_defs = _get_kpi_definitions(v_slug)
                    kpi_count = len(kpi_defs)
                except Exception:
                    kpi_count = v_default_count
                verticals[v_slug] = {
                    'vertical': v_slug,
                    'config_types': [],
                    'config_type_count': 0,
                    'kpi_count': kpi_count,
                    'description': v_desc,
                }

        return {
            'scope': 'platform',
            'total_verticals': len(verticals),
            'verticals': list(verticals.values()),
        }


@mcp.tool
def get_reference_customer(vertical: str) -> dict:
    """Get the reference/demo customer for a vertical.

    Discovery tool — no authentication required.
    Returns the reference customer's ID, name, account count, and health summary.
    Reference customers are pre-seeded demo tenants that showcase the platform.

    Args:
        vertical: The vertical slug (e.g. 'dc2_s')
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, Account
        import utils.health_thresholds as ht

        customer = None

        # Try DB columns if they exist (is_reference, reference_for)
        try:
            customer = Customer.query.filter_by(
                is_reference=True,
                reference_for=vertical,
            ).first()
        except Exception:
            pass  # Columns not available yet

        if not customer:
            # Fallback: find any customer tagged with the vertical
            customer = Customer.query.filter_by(vertical=vertical).first()
            if not customer:
                raise ToolError(
                    f"No reference customer found for vertical '{vertical}'. "
                    f"Available verticals can be discovered via list_verticals()."
                )

        # Use the vertical parameter to resolve health functions
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)

        accounts = Account.query.filter_by(
            customer_id=customer.customer_id,
        ).all()

        # Health summary
        health_scores = []
        for acct in accounts:
            precalc_health, _, _ = get_precalculated_scores(acct.account_id)
            if precalc_health is not None:
                health_scores.append(precalc_health)
            else:
                try:
                    kpi_values = _get_trailing_kpi_values(acct.account_id)
                    h, _ = calculate_kpi_health(kpi_values, customer.customer_id)
                    health_scores.append(h)
                except Exception:
                    pass

        avg_health = round(sum(health_scores) / len(health_scores), 1) if health_scores else None
        healthy_count = sum(1 for h in health_scores if h >= ht.healthy_min())
        at_risk_count = sum(1 for h in health_scores if ht.at_risk_min() <= h < ht.healthy_min())
        critical_count = sum(1 for h in health_scores if h < ht.at_risk_min())

        return {
            'scope': 'portfolio',
            'customer_id': customer.customer_id,
            'customer_name': customer.customer_name,
            'created_at': customer.created_at.isoformat() if customer.created_at else None,
            'vertical': vertical,
            'is_reference': getattr(customer, 'is_reference', False),
            'account_count': len(accounts),
            'health_summary': {
                'avg_health': avg_health,
                'healthy': healthy_count,
                'at_risk': at_risk_count,
                'critical': critical_count,
            },
        }


@mcp.tool
def get_csv_templates(vertical: str, file_type: str = None) -> dict:
    """Get CSV column schemas for data uploads.

    Discovery tool — no authentication required.
    Returns the required and optional columns for each CSV file type
    that the platform accepts during onboarding data ingestion.

    Args:
        vertical: The vertical slug (e.g. 'dc2_s')
        file_type: Optional specific file type (e.g. 'accounts.csv', 'kpi_measurements.csv').
                   If omitted, returns all file types for the vertical.
    """
    _check_mcp_enabled()

    import json as _json

    schemas_path = os.path.join(_backend_dir, 'config', 'csv_schemas.json')
    if not os.path.isfile(schemas_path):
        raise ToolError("CSV schemas config file not found at config/csv_schemas.json")

    with open(schemas_path, 'r') as f:
        schemas = _json.load(f)

    # Combine regular + context_graph files
    all_files = {}
    for model_key in ('regular_model', 'context_graph_model'):
        model = schemas.get(model_key, {})
        files = model.get('files', {})
        for fname, fschema in files.items():
            all_files[fname] = {
                'file_type': fname,
                'model': model_key,
                'required_columns': fschema.get('required_columns', []),
                'optional_columns': fschema.get('optional_columns', []),
                'db_table': fschema.get('db_table', ''),
                'note': fschema.get('note', ''),
            }

    if file_type:
        if file_type not in all_files:
            raise ToolError(
                f"Unknown file_type '{file_type}'. Available: {sorted(all_files.keys())}"
            )
        return {
            'scope': 'platform',
            'vertical': vertical,
            'file_type': file_type,
            'schema': all_files[file_type],
        }

    return {
        'scope': 'platform',
        'vertical': vertical,
        'total_file_types': len(all_files),
        'schemas': all_files,
    }


@mcp.tool
def get_vertical_config(vertical: str, config_type: str = None) -> dict:
    """Get vertical configuration templates.

    Discovery tool — no authentication required.
    Returns base configuration from VerticalTemplate for the specified vertical.
    If config_type is specified, returns just that config; otherwise returns all.

    Args:
        vertical: The vertical slug (e.g. 'dc2_s')
        config_type: Optional config type (e.g. 'kpi_weights', 'pillar_weights',
                     'health_thresholds', 'scoring_rules'). If omitted, returns all.
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        results = []

        # Try DB-backed VerticalTemplate if available
        try:
            from models import VerticalTemplate

            query = VerticalTemplate.query.filter_by(vertical=vertical)
            if config_type:
                query = query.filter_by(config_type=config_type)

            templates = query.all()
            for t in templates:
                results.append({
                    'template_id': t.template_id,
                    'vertical': t.vertical,
                    'config_type': t.config_type,
                    'version': t.version,
                    'config': t.config,
                })
        except (ImportError, Exception):
            pass  # VerticalTemplate not available — use fallback

        # Fallback: build config from kpi_definitions + config files
        if not results:
            try:
                kpi_defs = _get_kpi_definitions(vertical)
                results.append({
                    'template_id': None,
                    'vertical': vertical,
                    'config_type': 'kpi_definitions',
                    'version': '1.0',
                    'config': {
                        'kpi_count': len(kpi_defs),
                        'kpis': list(kpi_defs.keys())[:10],  # First 10 for preview
                        'note': f'Full {len(kpi_defs)} KPI definitions available',
                    },
                })
            except Exception:
                pass

            # Health thresholds config
            try:
                import utils.health_thresholds as ht
                results.append({
                    'template_id': None,
                    'vertical': vertical,
                    'config_type': 'health_thresholds',
                    'version': '1.0',
                    'config': {
                        'healthy_min': ht.healthy_min(),
                        'at_risk_min': ht.at_risk_min(),
                    },
                })
            except Exception:
                pass

        if config_type and not results:
            raise ToolError(
                f"No config template found for vertical='{vertical}', "
                f"config_type='{config_type}'"
            )

        if config_type and len(results) == 1:
            return {
                'scope': 'platform',
                'vertical': vertical,
                'config_type': config_type,
                'template': results[0],
            }

        return {
            'scope': 'platform',
            'vertical': vertical,
            'total_configs': len(results),
            'templates': results,
        }


@mcp.tool
def get_onboarding_status(customer_id: int) -> dict:
    """Check onboarding progress for a customer.

    Returns a checklist of what has been completed: customer record, admin user,
    config, accounts, KPI data, scores, wizard runs, etc.

    Args:
        customer_id: The customer ID to check
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, CustomerConfig, Account, User, DC2SKPI, WizardRun, db
        from pathlib import Path

        checklist = {
            'customer_exists': False,
            'admin_user_exists': False,
            'config_exists': False,
            'accounts_uploaded': False,
            'account_count': 0,
            'kpi_data_loaded': False,
            'kpi_record_count': 0,
            'scores_calculated': False,
            'wizard_runs': 0,
            'directory_provisioned': False,
            'data_files_present': [],
        }

        # Customer
        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            return {
                'scope': 'customer',
                'customer_id': customer_id,
                'status': 'not_found',
                'checklist': checklist,
                'message': f'Customer {customer_id} does not exist yet. Use create_customer() to begin.',
            }
        checklist['customer_exists'] = True

        # Admin user
        admin = User.query.filter_by(customer_id=customer_id).first()
        checklist['admin_user_exists'] = admin is not None

        # Config
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        checklist['config_exists'] = config is not None

        # Accounts
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        checklist['accounts_uploaded'] = len(accounts) > 0
        checklist['account_count'] = len(accounts)

        # KPI data
        if accounts:
            account_ids = [a.account_id for a in accounts]
            kpi_count = DC2SKPI.query.filter(
                DC2SKPI.account_id.in_(account_ids)
            ).count()
            checklist['kpi_data_loaded'] = kpi_count > 0
            checklist['kpi_record_count'] = kpi_count

        # Pre-calculated scores
        if accounts:
            cust_vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
            _, _, get_precalculated_scores = _get_health_functions(cust_vertical)
            scored = 0
            for acct in accounts:
                h, _, _ = get_precalculated_scores(acct.account_id)
                if h is not None:
                    scored += 1
            checklist['scores_calculated'] = scored > 0

        # Wizard runs
        wizard_count = WizardRun.query.filter_by(customer_id=customer_id).count()
        checklist['wizard_runs'] = wizard_count

        # Directory — use customer's actual vertical
        backend_dir = Path(__file__).parent.parent
        cust_v = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        customer_dir = backend_dir / 'verticals' / f'customer{customer_id}-{cust_v}'
        checklist['directory_provisioned'] = customer_dir.exists()
        if customer_dir.exists():
            data_dir = customer_dir / 'data'
            if data_dir.exists():
                checklist['data_files_present'] = [
                    f.name for f in data_dir.iterdir() if f.is_file() and f.suffix == '.csv'
                ]

        # Overall status
        all_done = all([
            checklist['customer_exists'],
            checklist['admin_user_exists'],
            checklist['config_exists'],
            checklist['accounts_uploaded'],
            checklist['kpi_data_loaded'],
            checklist['scores_calculated'],
        ])
        status = 'complete' if all_done else 'in_progress'

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'created_at': customer.created_at.isoformat() if customer.created_at else None,
            'status': status,
            'checklist': checklist,
        }


# -------------------------------------------------------------------
# Customer Setup Phase (write, no auth) — Tools 27-29
# -------------------------------------------------------------------

@mcp.tool
def create_customer(
    name: str,
    domain: str,
    vertical: str,
    admin_email: str,
    admin_name: str,
) -> dict:
    """Create a new customer with admin user and auto-generated API key.

    This is the first write step in onboarding. Creates:
    1. Customer record (with UUID)
    2. Admin user (with generated password)
    3. CustomerConfig (vertical defaults)
    4. API key (returned once — save it!)

    No authentication required — this is the entry point for new prospects.

    Args:
        name: Company name
        domain: Email domain (e.g. 'acme.com')
        vertical: Vertical slug (e.g. 'dc2_s')
        admin_email: Admin user email
        admin_name: Admin user display name
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, User, CustomerConfig
        from extensions import db
        from werkzeug.security import generate_password_hash
        import secrets as _secrets

        # Check for duplicate domain
        existing = Customer.query.filter_by(domain=domain).first()
        if existing:
            raise ToolError(
                f"A customer with domain '{domain}' already exists "
                f"(customer_id={existing.customer_id}). "
                f"Use get_onboarding_status() to check its state."
            )

        # Check for duplicate email
        existing_user = User.query.filter_by(email=admin_email).first()
        if existing_user:
            raise ToolError(f"Email '{admin_email}' is already registered.")

        # Generate UUID
        try:
            from id_generator import generate_id, resolve_vertical_prefix
            uuid_vertical = 'dc' if vertical.startswith('dc') else vertical
            customer_uuid = generate_id(uuid_vertical, 'customer')
        except Exception:
            customer_uuid = None

        # Create customer
        customer = Customer(
            customer_name=name,
            email=admin_email,
            domain=domain,
            vertical=vertical,
        )
        if customer_uuid:
            customer.uuid = customer_uuid
        db.session.add(customer)
        db.session.flush()  # Get customer_id

        customer_id = customer.customer_id

        # Create admin user with generated password
        generated_password = _secrets.token_urlsafe(16)
        user = User(
            customer_id=customer_id,
            user_name=admin_name,
            email=admin_email,
            password_hash=generate_password_hash(generated_password),
            role='admin',
            vertical=vertical,
        )
        if customer_uuid:
            user.customer_uuid = customer_uuid
        try:
            from id_generator import generate_id as _gen_id
            user.uuid = _gen_id('dc' if vertical.startswith('dc') else vertical, 'user')
        except Exception:
            pass
        db.session.add(user)
        db.session.flush()  # Get user_id

        # Create default CustomerConfig
        config = CustomerConfig(
            customer_id=customer_id,
            vertical=vertical,
        )
        db.session.add(config)

        # Generate API key
        try:
            from api_key_service import generate_api_key as _gen_api_key
            full_key, _key_record = _gen_api_key(
                customer_id=customer_id,
                created_by=user.user_id,
                name='MCP Onboarding Key',
                scopes=['read', 'write'],
            )
        except Exception as e:
            full_key = None

        # Provision customer directory
        try:
            from verticals.provision_dc_customer import provision_customer
            provision_customer(
                customer_id=customer_id,
                customer_name=name,
                vertical_slug=vertical,
                force=True,
            )
            directory_provisioned = True
        except Exception:
            directory_provisioned = False

        db.session.commit()

        result = {
            'scope': 'customer',
            'customer_id': customer_id,
            'customer_name': name,
            'customer_uuid': customer_uuid,
            'domain': domain,
            'vertical': vertical,
            'created_at': customer.created_at.isoformat() if customer.created_at else None,
            'admin_user_id': user.user_id,
            'admin_email': admin_email,
            'directory_provisioned': directory_provisioned,
        }

        if full_key:
            result['api_key'] = full_key
            result['api_key_note'] = (
                'Save this API key — it is shown only once. '
                'Use it for the intelligence tools (list_accounts, get_account_health, etc.).'
            )

        return result


@mcp.tool
def configure_customer_kpis(
    customer_id: int,
    enabled_pillars: list = None,
    enabled_kpis: list = None,
    pillar_weights: dict = None,
    kpi_weights: dict = None,
) -> dict:
    """Configure KPI selection and weights for a customer.

    Sets customer-level overrides via CustomerConfig. You can:
    - Select which pillars are active (enabled_pillars)
    - Select exact KPIs (enabled_kpis overrides enabled_pillars)
    - Set L2 pillar weights (pillar_weights)
    - Set L1 KPI weights per pillar (kpi_weights)

    Args:
        customer_id: The customer ID
        enabled_pillars: Optional list of pillar codes (e.g. ['P1', 'P3', 'P5'])
        enabled_kpis: Optional list of KPI codes (e.g. ['P1-KPI1', 'P1-KPI2'])
        pillar_weights: Optional dict of pillar weights (e.g. {'P1': 0.4, 'P3': 0.35, 'P5': 0.25})
        kpi_weights: Optional dict of KPI weights per pillar (e.g. {'P1': {'P1-KPI1': 0.5}})
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, CustomerConfig
        from extensions import db

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found. Use create_customer() first.")

        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        cust_vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        if not config:
            config = CustomerConfig(customer_id=customer_id, vertical=cust_vertical)
            db.session.add(config)

        # Determine enabled KPIs
        if enabled_kpis:
            config.dc2s_enabled_kpis = enabled_kpis
        elif enabled_pillars:
            # Derive KPIs from pillar selection using the customer's vertical
            try:
                kpi_defs = _get_kpi_definitions(cust_vertical)
                derived_kpis = [
                    code for code, defn in kpi_defs.items()
                    if defn.get('pillar') in enabled_pillars
                ]
                config.dc2s_enabled_kpis = derived_kpis
            except Exception:
                raise ToolError("Could not load KPI definitions for pillar-based selection.")

        # Set pillar weights
        if pillar_weights:
            config.dc2s_pillar_weights = pillar_weights

        # Set KPI weights
        if kpi_weights:
            config.dc2s_kpi_weights = kpi_weights

        db.session.commit()

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'enabled_kpis': config.dc2s_enabled_kpis,
            'enabled_kpi_count': len(config.dc2s_enabled_kpis) if config.dc2s_enabled_kpis else 0,
            'pillar_weights': config.dc2s_pillar_weights,
            'kpi_weights': config.dc2s_kpi_weights,
            'message': 'Customer KPI configuration updated.',
        }


@mcp.tool
def enable_features(customer_id: int, features: list = None) -> dict:
    """Enable or disable feature toggles for a customer.

    Each feature is a per-customer DB toggle. Common features include:
    context_graph, story_arcs, signal_edges, stakeholder_tracking,
    decision_lifecycle, outcome_economics, industry_benchmarks.

    Args:
        customer_id: The customer ID
        features: List of feature names to enable. If None, returns current state.
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer
        from models import FeatureToggle as FTModel
        from extensions import db

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        if features is None:
            # Read-only: return current toggles
            toggles = FTModel.query.filter_by(customer_id=customer_id).all()
            return {
                'scope': 'customer',
                'customer_id': customer_id,
                'features': {
                    t.feature_name: t.enabled for t in toggles
                },
                'total_features': len(toggles),
            }

        # Enable specified features
        results = {}
        for feature_name in features:
            toggle = FTModel.query.filter_by(
                customer_id=customer_id,
                feature_name=feature_name,
            ).first()
            if toggle:
                toggle.enabled = True
            else:
                toggle = FTModel(
                    customer_id=customer_id,
                    feature_name=feature_name,
                    enabled=True,
                    description=f'Enabled via MCP onboarding',
                )
                db.session.add(toggle)
            results[feature_name] = True

        db.session.commit()

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'features_enabled': results,
            'total_enabled': len(results),
            'message': f'Enabled {len(results)} features for customer {customer_id}.',
        }


# -------------------------------------------------------------------
# Data Ingestion Phase (write, no auth) — Tools 30-32
# -------------------------------------------------------------------

@mcp.tool
def validate_csv(customer_id: int, file_type: str, csv_content: str) -> dict:
    """Validate CSV content against the platform schema before uploading.

    Checks that required columns are present and reports any issues.
    Does NOT persist data — use upload_csv() after validation passes.

    Args:
        customer_id: The customer ID (used for context only)
        file_type: The CSV file type (e.g. 'accounts.csv', 'kpi_measurements.csv')
        csv_content: The raw CSV content as a string
    """
    _check_mcp_enabled()

    import json as _json
    import csv as _csv
    import io as _io

    # Load schema
    schemas_path = os.path.join(_backend_dir, 'config', 'csv_schemas.json')
    if not os.path.isfile(schemas_path):
        raise ToolError("CSV schemas config not found.")

    with open(schemas_path, 'r') as f:
        schemas = _json.load(f)

    # Normalize file_type: accept both 'kpi_measurements' and 'kpi_measurements.csv'
    ft = file_type if file_type.endswith('.csv') else f'{file_type}.csv'

    # Find schema for file_type
    schema = None
    for model_key in ('regular_model', 'context_graph_model'):
        files = schemas.get(model_key, {}).get('files', {})
        if ft in files:
            schema = files[ft]
            break

    if not schema:
        available = []
        for model_key in ('regular_model', 'context_graph_model'):
            available.extend(schemas.get(model_key, {}).get('files', {}).keys())
        raise ToolError(
            f"Unknown file_type '{file_type}'. Available: {sorted(available)}"
        )

    required_columns = set(schema.get('required_columns', []))
    optional_columns = set(schema.get('optional_columns', []))
    all_known = required_columns | optional_columns

    # Parse CSV
    reader = _csv.DictReader(_io.StringIO(csv_content))
    headers = set(reader.fieldnames or [])
    rows = list(reader)

    # Validation
    missing_required = required_columns - headers
    unknown_columns = headers - all_known
    errors = []
    warnings = []

    if missing_required:
        errors.append(f"Missing required columns: {sorted(missing_required)}")
    if unknown_columns:
        warnings.append(f"Unknown columns (will be ignored): {sorted(unknown_columns)}")
    if len(rows) == 0:
        errors.append("CSV has no data rows.")

    valid = len(errors) == 0

    return {
        'scope': 'validation',
        'customer_id': customer_id,
        'file_type': file_type,
        'valid': valid,
        'row_count': len(rows),
        'columns_found': sorted(headers),
        'required_columns': sorted(required_columns),
        'missing_required': sorted(missing_required) if missing_required else [],
        'errors': errors,
        'warnings': warnings,
    }


@mcp.tool
def upload_csv(customer_id: int, file_type: str, csv_content: str) -> dict:
    """Upload CSV data for a customer.

    Saves the CSV content to the customer's data directory on disk.
    The file can then be processed via process_data().

    Args:
        customer_id: The customer ID
        file_type: The CSV file type (e.g. 'accounts.csv', 'kpi_measurements.csv')
        csv_content: The raw CSV content as a string
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, db
        from pathlib import Path

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        # Normalize file_type to include .csv extension
        ft = file_type if file_type.endswith('.csv') else f'{file_type}.csv'

        # Determine customer data directory
        vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        backend_dir = Path(__file__).parent.parent
        customer_dir = backend_dir / 'verticals' / f'customer{customer_id}-{vertical}'

        # Ensure directory exists
        data_dir = customer_dir / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)

        # Write file
        file_path = data_dir / ft
        file_path.write_text(csv_content, encoding='utf-8')

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'file_type': file_type,
            'file_path': str(file_path),
            'bytes_written': len(csv_content.encode('utf-8')),
            'message': f"Uploaded {file_type} ({len(csv_content.encode('utf-8'))} bytes). "
                       f"Use process_data() to ingest into the database.",
        }


@mcp.tool
def process_data(customer_id: int) -> dict:
    """Trigger the data processing pipeline for a customer.

    Processes uploaded CSV files through the full pipeline:
    1. Data loading (CSVs -> PostgreSQL)
    2. Embedding generation
    3. Data validation
    4. Journey generation (Wizard A)
    5. Pattern analysis (Wizard B)
    6. Weight calibration (Wizard C)

    Args:
        customer_id: The customer ID
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, db
        from pathlib import Path

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        # Check data directory has files
        vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        backend_dir = Path(__file__).parent.parent
        customer_dir = backend_dir / 'verticals' / f'customer{customer_id}-{vertical}'
        data_dir = customer_dir / 'data'

        if not data_dir.exists():
            raise ToolError(
                f"No data directory found for customer {customer_id}. "
                f"Upload CSV files first via upload_csv()."
            )

        csv_files = [f.name for f in data_dir.iterdir() if f.is_file() and f.suffix == '.csv']
        if not csv_files:
            raise ToolError("No CSV files found in data directory. Upload files first.")

        # Check required files
        required = ['accounts.csv', 'kpi_measurements.csv']
        missing = [f for f in required if f not in csv_files]
        if missing:
            raise ToolError(f"Missing required files: {missing}. Upload them via upload_csv().")

        # Call the onboarding process-data endpoint internally
        import json as _json
        import requests as _requests

        steps_completed = []
        errors = []

        # Call the REST API process-data endpoint (which does the real work)
        try:
            base_url = os.environ.get('CS_PULSE_BASE_URL', 'http://localhost:5001')
            resp = _requests.post(
                f'{base_url}/api/onboarding/process-data',
                json={'customer_id': customer_id},
                timeout=120,
            )
            if resp.status_code == 200:
                result_data = resp.json()
                steps_completed = result_data.get('steps_completed', ['full_pipeline'])
                return {
                    'scope': 'customer',
                    'customer_id': customer_id,
                    'status': 'success',
                    'csv_files_found': csv_files,
                    'steps_completed': steps_completed,
                    'errors': [],
                    'message': (
                        f"Data processing completed successfully. "
                        f"{len(csv_files)} CSV files processed through full pipeline."
                    ),
                }
            else:
                error_msg = resp.text[:500] if resp.text else f'HTTP {resp.status_code}'
                errors.append(f"pipeline: {error_msg}")
        except _requests.exceptions.ConnectionError:
            errors.append(
                "Cannot connect to CS Pulse backend API. "
                "Ensure the backend is running on the configured base URL."
            )
        except Exception as e:
            errors.append(f"pipeline: {str(e)}")

        # Fallback: try direct CSV loading if REST call failed
        try:
            import pandas as pd
            from extensions import db as _db
            from models import Account, DC2SKPI, QualitativeSignal

            for csv_file in csv_files:
                csv_path = data_dir / csv_file
                df = pd.read_csv(str(csv_path))
                if df.empty:
                    continue

                if csv_file == 'accounts.csv':
                    for _, row in df.iterrows():
                        existing = Account.query.filter_by(
                            customer_id=customer_id,
                            account_name=row.get('account_name', row.get('name', ''))
                        ).first()
                        if not existing:
                            acct = Account(
                                customer_id=customer_id,
                                account_name=row.get('account_name', row.get('name', '')),
                                arr=row.get('arr', row.get('annual_revenue', 0)),
                                vertical=vertical,
                            )
                            _db.session.add(acct)
                    _db.session.flush()
                    steps_completed.append('accounts_loaded')

                elif csv_file == 'kpi_measurements.csv':
                    # Get account mapping
                    accounts = {a.account_name: a.account_id
                                for a in Account.query.filter_by(customer_id=customer_id).all()}
                    for _, row in df.iterrows():
                        acct_name = row.get('account_name', row.get('account', ''))
                        acct_id = accounts.get(acct_name)
                        if acct_id:
                            kpi = DC2SKPI(
                                account_id=acct_id,
                                kpi_code=row.get('kpi_code', row.get('kpi_id', '')),
                                value=float(row.get('value', 0)),
                                target=float(row.get('target', 100)),
                                measured_at=row.get('measured_at', row.get('date')),
                            )
                            _db.session.add(kpi)
                    steps_completed.append('kpis_loaded')

                elif csv_file == 'enhanced_qualitative_signals.csv':
                    accounts = {a.account_name: a.account_id
                                for a in Account.query.filter_by(customer_id=customer_id).all()}
                    for _, row in df.iterrows():
                        acct_name = row.get('account_name', row.get('account', ''))
                        acct_id = accounts.get(acct_name)
                        if acct_id:
                            sig = QualitativeSignal(
                                account_id=acct_id,
                                signal_type=row.get('signal_type', 'nps'),
                                content=row.get('content', row.get('signal_text', '')),
                                sentiment=row.get('sentiment', 'neutral'),
                                sentiment_score=float(row.get('sentiment_score', 0.5)),
                                signal_date=row.get('signal_date', row.get('date')),
                            )
                            _db.session.add(sig)
                    steps_completed.append('signals_loaded')

            _db.session.commit()

            # Trigger health score calculation via event system
            try:
                from event_system import publish_event
                publish_event('kpi_data_uploaded', {
                    'customer_id': customer_id,
                    'source': 'mcp_process_data',
                })
                steps_completed.append('health_score_calculation_triggered')
            except Exception:
                pass

        except Exception as e:
            errors.append(f"direct_loading: {str(e)}")

        status = 'success' if steps_completed and not errors else 'partial' if steps_completed else 'failed'

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'status': status,
            'csv_files_found': csv_files,
            'steps_completed': steps_completed,
            'errors': errors,
            'message': (
                f"Data processing {'completed' if status == 'success' else 'completed with issues'}. "
                f"Steps: {', '.join(steps_completed) if steps_completed else 'none'}."
            ),
        }


# -------------------------------------------------------------------
# Post-Onboarding Phase (write, no auth) — Tools 33-34
# -------------------------------------------------------------------

@mcp.tool
def trigger_wizard(customer_id: int, wizard: str) -> dict:
    """Trigger a wizard (A, B, or C) for a customer.

    Wizards perform advanced analysis:
    - Wizard A: Journey generation — creates journey JSON for each account
    - Wizard B: Pattern analysis — extracts patterns, early warnings, phase transitions
    - Wizard C: Weight calibration — self-learning optimal KPI/pillar weights

    Args:
        customer_id: The customer ID
        wizard: Which wizard to trigger: 'a', 'b', or 'c'
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, WizardRun
        from extensions import db
        from pathlib import Path
        from datetime import datetime

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        wizard = wizard.lower().strip()
        if wizard not in ('a', 'b', 'c'):
            raise ToolError(f"Invalid wizard '{wizard}'. Must be 'a', 'b', or 'c'.")

        wizard_name = {
            'a': 'Journey Generation',
            'b': 'Pattern Analysis',
            'c': 'Weight Calibration',
        }[wizard]

        # Create a WizardRun record
        import uuid as _uuid
        run_id = f"wizard_{wizard}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{_uuid.uuid4().hex[:8]}"

        run = WizardRun(
            run_id=run_id,
            customer_id=customer_id,
            status='queued',
            config={'wizard': wizard, 'triggered_via': 'mcp_onboarding'},
        )
        db.session.add(run)
        db.session.commit()

        # Execute wizard using DB-native functions (no subprocess/filesystem)
        result_summary = {}

        try:
            db.session.rollback()  # Clear any dirty session state

            if wizard == 'a':
                from wizards.wizard_a_journey_db import run_wizard_a
                wiz_result = run_wizard_a(customer_id)
                result_summary = wiz_result
                result_summary['return_code'] = 0

            elif wizard == 'b':
                try:
                    from wizards.wizard_b_pattern_db import run_wizard_b
                    wiz_result = run_wizard_b(customer_id)
                    result_summary = wiz_result
                    result_summary['return_code'] = 0
                except Exception as wb_err:
                    result_summary['error'] = str(wb_err)
                    result_summary['return_code'] = 1

            elif wizard == 'c':
                from wizards.wizard_c_weight_calibrator_db import run_wizard_c
                wiz_result = run_wizard_c(customer_id)
                result_summary = wiz_result
                result_summary['return_code'] = 0

            # Update run status
            run.status = 'completed' if result_summary.get('return_code', 1) == 0 else 'failed'
            run.completed_at = datetime.utcnow()
            run.results = result_summary
            db.session.commit()

        except Exception as e:
            run.status = 'failed'
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            db.session.commit()
            result_summary['error'] = str(e)

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'wizard': wizard,
            'wizard_name': wizard_name,
            'run_id': run_id,
            'status': run.status,
            'result_summary': result_summary,
        }


@mcp.tool
def complete_onboarding(customer_id: int) -> dict:
    """Finalize onboarding for a customer.

    Performs final checks and marks the customer as onboarded:
    1. Verifies all required steps are done (customer, accounts, KPIs, scores)
    2. Sets the customer status to active
    3. Returns a final summary with next steps

    Args:
        customer_id: The customer ID
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, CustomerConfig, Account, User, DC2SKPI
        from extensions import db

        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        # Check all required pieces
        issues = []

        admin = User.query.filter_by(customer_id=customer_id).first()
        if not admin:
            issues.append('No admin user found. Use create_customer() to create one.')

        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            issues.append('No customer config found. Use configure_customer_kpis() to set one up.')

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        if not accounts:
            issues.append('No accounts found. Upload accounts.csv via upload_csv() and process_data().')

        kpi_count = 0
        if accounts:
            account_ids = [a.account_id for a in accounts]
            kpi_count = DC2SKPI.query.filter(
                DC2SKPI.account_id.in_(account_ids)
            ).count()
            if kpi_count == 0:
                issues.append('No KPI data loaded. Upload kpi_measurements.csv via upload_csv() and process_data().')

        if issues:
            return {
                'scope': 'customer',
                'customer_id': customer_id,
                'customer_name': customer.customer_name,
                'status': 'incomplete',
                'issues': issues,
                'message': 'Onboarding cannot be finalized. Resolve the issues above.',
            }

        # Calculate portfolio health for summary
        cust_vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(cust_vertical)
        import utils.health_thresholds as ht

        health_scores = []
        total_arr = 0.0
        for acct in accounts:
            precalc_health, _, _ = get_precalculated_scores(acct.account_id)
            if precalc_health is not None:
                health_scores.append(precalc_health)
            else:
                try:
                    kpi_values = _get_trailing_kpi_values(acct.account_id)
                    h, _ = calculate_kpi_health(kpi_values, customer_id)
                    health_scores.append(h)
                except Exception:
                    pass
            total_arr += _get_account_arr(acct)

        avg_health = round(sum(health_scores) / len(health_scores), 1) if health_scores else 0

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'customer_uuid': getattr(customer, 'uuid', None),
            'vertical': getattr(customer, 'vertical', None) or 'dc2_s',
            'status': 'onboarded',
            'summary': {
                'account_count': len(accounts),
                'kpi_records': kpi_count,
                'avg_health_score': avg_health,
                'total_arr': round(total_arr, 2),
                'enabled_kpis': config.dc2s_enabled_kpis if config else None,
            },
            'next_steps': [
                'Use list_accounts() to view all accounts and health scores.',
                'Use get_account_health() to drill into individual accounts.',
                'Use get_at_risk_accounts() to find accounts needing attention.',
                'Use get_csm_actions() for AI-recommended next-best actions.',
                'Use the Context Graph tools for revenue intelligence (if enabled).',
            ],
            'message': f'Onboarding complete. {len(accounts)} accounts, avg health {avg_health}.',
        }


# ===================================================================
# Tool: clone_customer — Deep-copy an existing customer for demos
# ===================================================================

@mcp.tool
def clone_customer(
    source_customer_id: int,
    new_name: str,
    new_domain: str,
) -> dict:
    """Deep-copy an existing customer with all data into a new customer.

    Creates a full clone including accounts, KPI measurements, health scores,
    context graph (nodes + edges with remapped IDs), qualitative signals,
    playbook executions, and ROI snapshots. Enables instant demo setup:
    "clone Gold_DC_Alpha as Acme Corp" in ~2 seconds.

    No authentication required (onboarding tool).

    Args:
        source_customer_id: Customer ID to clone from (e.g. 407 for Gold_DC_Alpha)
        new_name: Name for the new customer (e.g. 'Acme Corp')
        new_domain: Domain for the new customer (e.g. 'acme.com')
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import (
            Customer, CustomerConfig, Account, DC2SKPI,
            HealthScore, KPIScore, PillarScore,
            ContextNode, ContextEdge,
            QualitativeSignal, PlaybookExecution,
            ROISnapshot, JourneyData,
        )
        from extensions import db
        import uuid as _uuid_mod
        from datetime import datetime

        # ----------------------------------------------------------
        # Validate source customer exists
        # ----------------------------------------------------------
        source = db.session.get(Customer, int(source_customer_id))
        if not source:
            raise ToolError(f"Source customer {source_customer_id} not found.")

        # Check for duplicate domain
        existing = Customer.query.filter_by(domain=new_domain).first()
        if existing:
            raise ToolError(
                f"A customer with domain '{new_domain}' already exists "
                f"(customer_id={existing.customer_id})."
            )

        summary = {}

        # ----------------------------------------------------------
        # 1. Clone Customer record
        # ----------------------------------------------------------
        new_customer = Customer(
            customer_name=new_name,
            email=None,  # No email for cloned customer
            domain=new_domain,
            vertical=source.vertical,
        )
        # Generate UUID
        try:
            from id_generator import generate_id
            uuid_vertical = 'dc' if (source.vertical or '').startswith('dc') else (source.vertical or 'dc')
            new_customer.uuid = generate_id(uuid_vertical, 'customer')
        except Exception:
            new_customer.uuid = f"clone_{_uuid_mod.uuid4().hex[:16]}"
        db.session.add(new_customer)
        db.session.flush()  # Get new customer_id

        new_cid = new_customer.customer_id
        summary['customer_id'] = new_cid
        summary['customer_name'] = new_name
        summary['domain'] = new_domain
        summary['vertical'] = source.vertical
        summary['created_at'] = new_customer.created_at.isoformat() if new_customer.created_at else None

        # ----------------------------------------------------------
        # 2. Clone CustomerConfig
        # ----------------------------------------------------------
        source_config = CustomerConfig.query.filter_by(
            customer_id=source_customer_id,
        ).first()
        if source_config:
            new_config = CustomerConfig(
                customer_id=new_cid,
                vertical=source_config.vertical,
                kpi_upload_mode=source_config.kpi_upload_mode,
                dc2s_pillar_weights=source_config.dc2s_pillar_weights,
                dc2s_enabled_kpis=source_config.dc2s_enabled_kpis,
                dc2s_kpi_overrides=source_config.dc2s_kpi_overrides,
                dc2s_kpi_weights=source_config.dc2s_kpi_weights,
                dc2s_kpi_definitions=source_config.dc2s_kpi_definitions,
                config_version=source_config.config_version,
            )
            db.session.add(new_config)
            summary['config_cloned'] = True
        else:
            summary['config_cloned'] = False

        # ----------------------------------------------------------
        # 3. Clone Accounts (build old→new account_id map)
        # ----------------------------------------------------------
        source_accounts = Account.query.filter_by(
            customer_id=source_customer_id,
        ).all()

        acct_id_map = {}  # old_account_id → new_account_id
        for acct in source_accounts:
            new_acct = Account(
                customer_id=new_cid,
                account_name=acct.account_name,
                revenue=acct.revenue,
                account_status=acct.account_status,
                industry=acct.industry,
                vertical=acct.vertical,
                region=acct.region,
                external_account_id=acct.external_account_id,
                profile_metadata=acct.profile_metadata,
            )
            # Generate account UUID
            try:
                new_acct.uuid = generate_id(uuid_vertical, 'account')
            except Exception:
                new_acct.uuid = f"clone_acct_{_uuid_mod.uuid4().hex[:12]}"
            new_acct.customer_uuid = new_customer.uuid
            db.session.add(new_acct)
            db.session.flush()
            acct_id_map[acct.account_id] = new_acct.account_id

        summary['accounts_cloned'] = len(acct_id_map)

        # ----------------------------------------------------------
        # 4. Clone DC2S KPI measurements (joins through accounts)
        # ----------------------------------------------------------
        kpi_count = 0
        for old_aid, new_aid in acct_id_map.items():
            kpis = DC2SKPI.query.filter_by(account_id=old_aid).all()
            for kpi in kpis:
                new_kpi = DC2SKPI(
                    account_id=new_aid,
                    kpi_code=kpi.kpi_code,
                    value=kpi.value,
                    target=kpi.target,
                    pillar=kpi.pillar,
                    weight=kpi.weight,
                    status=kpi.status,
                    measured_at=kpi.measured_at,
                    created_at=kpi.created_at,
                )
                db.session.add(new_kpi)
                kpi_count += 1
        summary['dc2s_kpis_cloned'] = kpi_count

        # ----------------------------------------------------------
        # 5. Clone Health Scores (joins through accounts)
        # ----------------------------------------------------------
        hs_count = 0
        for old_aid, new_aid in acct_id_map.items():
            scores = HealthScore.query.filter_by(account_id=old_aid).all()
            for s in scores:
                new_hs = HealthScore(
                    account_id=new_aid,
                    measurement_month=s.measurement_month,
                    health_score=s.health_score,
                    health_status=s.health_status,
                    trend=s.trend,
                    change_from_last_month=s.change_from_last_month,
                    contributing_pillars=s.contributing_pillars,
                    pillar_weights=s.pillar_weights,
                    calculated_at=s.calculated_at,
                )
                db.session.add(new_hs)
                hs_count += 1
        summary['health_scores_cloned'] = hs_count

        # ----------------------------------------------------------
        # 5b. Clone KPI Scores (L1) and Pillar Scores (L2)
        # ----------------------------------------------------------
        kpi_score_count = 0
        for old_aid, new_aid in acct_id_map.items():
            rows = KPIScore.query.filter_by(account_id=old_aid).all()
            for r in rows:
                new_row = KPIScore(
                    account_id=new_aid,
                    measurement_month=r.measurement_month,
                    kpi_code=r.kpi_code,
                    kpi_value=r.kpi_value,
                    kpi_target=r.kpi_target,
                    kpi_score=r.kpi_score,
                    kpi_status=r.kpi_status,
                    calculated_at=r.calculated_at,
                )
                db.session.add(new_row)
                kpi_score_count += 1
        summary['kpi_scores_cloned'] = kpi_score_count

        pillar_score_count = 0
        for old_aid, new_aid in acct_id_map.items():
            rows = PillarScore.query.filter_by(account_id=old_aid).all()
            for r in rows:
                new_row = PillarScore(
                    account_id=new_aid,
                    measurement_month=r.measurement_month,
                    pillar_code=r.pillar_code,
                    pillar_score=r.pillar_score,
                    pillar_status=r.pillar_status,
                    contributing_kpis=r.contributing_kpis,
                    kpi_weights=r.kpi_weights,
                    calculated_at=r.calculated_at,
                )
                db.session.add(new_row)
                pillar_score_count += 1
        summary['pillar_scores_cloned'] = pillar_score_count

        # ----------------------------------------------------------
        # 6. Clone Context Graph Nodes (has customer_id)
        # ----------------------------------------------------------
        source_nodes = ContextNode.query.filter_by(
            customer_id=source_customer_id,
        ).all()

        node_id_map = {}  # old_node_id → new_node_id
        for node in source_nodes:
            new_account_id = acct_id_map.get(node.account_id)
            if new_account_id is None:
                continue  # Skip orphaned nodes
            new_node = ContextNode(
                customer_id=new_cid,
                account_id=new_account_id,
                node_type=node.node_type,
                node_subtype=node.node_subtype,
                tier=node.tier,
                title=node.title,
                properties=node.properties,
                revenue_impact=node.revenue_impact,
                revenue_impact_type=node.revenue_impact_type,
                confidence=node.confidence,
                source_platform=node.source_platform,
                source_event_id=node.source_event_id,
                source_ref=node.source_ref,
                occurred_at=node.occurred_at,
                expires_at=node.expires_at,
                weight_decay=node.weight_decay,
            )
            db.session.add(new_node)
            db.session.flush()  # Get new node_id for edge remapping
            node_id_map[node.node_id] = new_node.node_id

        summary['context_nodes_cloned'] = len(node_id_map)

        # ----------------------------------------------------------
        # 7. Clone Context Graph Edges (remap node IDs)
        # ----------------------------------------------------------
        edge_count = 0
        source_edges = ContextEdge.query.filter_by(
            customer_id=source_customer_id,
        ).all()
        for edge in source_edges:
            new_from = node_id_map.get(edge.from_node_id)
            new_to = node_id_map.get(edge.to_node_id)
            if new_from is None or new_to is None:
                continue  # Skip edges with unmapped nodes
            new_edge = ContextEdge(
                customer_id=new_cid,
                from_node_id=new_from,
                to_node_id=new_to,
                edge_type=edge.edge_type,
                lag_days=edge.lag_days,
                weight=edge.weight,
                confidence=edge.confidence,
                revenue_impact=edge.revenue_impact,
                revenue_impact_type=edge.revenue_impact_type,
                properties=edge.properties,
                source_platform=edge.source_platform,
                created_by=edge.created_by,
                occurred_at=edge.occurred_at,
                expires_at=edge.expires_at,
            )
            db.session.add(new_edge)
            edge_count += 1
        summary['context_edges_cloned'] = edge_count

        # ----------------------------------------------------------
        # 8. Clone Qualitative Signals (account_id based)
        # ----------------------------------------------------------
        signal_count = 0
        for old_aid, new_aid in acct_id_map.items():
            signals = QualitativeSignal.query.filter_by(account_id=old_aid).all()
            for sig in signals:
                new_sig = QualitativeSignal(
                    signal_id=f"clone_{_uuid_mod.uuid4().hex[:8]}_{sig.signal_id[-8:] if len(sig.signal_id) > 8 else sig.signal_id}",
                    account_id=new_aid,
                    signal_date=sig.signal_date,
                    signal_type=sig.signal_type,
                    content=sig.content,
                    sentiment=sig.sentiment,
                    stakeholder_level=sig.stakeholder_level,
                    stakeholder_title=sig.stakeholder_title,
                    sentiment_score=sig.sentiment_score,
                    keywords=sig.keywords,
                    is_narrative_signal=sig.is_narrative_signal,
                )
                db.session.add(new_sig)
                signal_count += 1
        summary['qualitative_signals_cloned'] = signal_count

        # ----------------------------------------------------------
        # 9. Clone Playbook Executions (has customer_id)
        # ----------------------------------------------------------
        pb_count = 0
        source_pbs = PlaybookExecution.query.filter_by(
            customer_id=source_customer_id,
        ).all()
        for pb in source_pbs:
            new_account_id = acct_id_map.get(pb.account_id) if pb.account_id else None
            new_exec_id = str(_uuid_mod.uuid4())
            new_pb = PlaybookExecution(
                execution_id=new_exec_id,
                customer_id=new_cid,
                account_id=new_account_id,
                playbook_id=pb.playbook_id,
                status=pb.status,
                current_step=pb.current_step,
                execution_data=pb.execution_data,
                started_at=pb.started_at,
                completed_at=pb.completed_at,
                execution_mode=pb.execution_mode,
                trigger_context=pb.trigger_context,
                outcome=pb.outcome,
                outcome_notes=pb.outcome_notes,
                llm_validation_result=pb.llm_validation_result,
            )
            db.session.add(new_pb)
            pb_count += 1
        summary['playbook_executions_cloned'] = pb_count

        # ----------------------------------------------------------
        # 10. Clone ROI Snapshots (has customer_id)
        # ----------------------------------------------------------
        roi_count = 0
        source_rois = ROISnapshot.query.filter_by(
            customer_id=source_customer_id,
        ).all()
        for roi in source_rois:
            new_roi = ROISnapshot(
                customer_id=new_cid,
                snapshot_date=roi.snapshot_date,
                improvement_pct=roi.improvement_pct,
                historical_roi_pct=roi.historical_roi_pct,
                historical_impact=roi.historical_impact,
                historical_investment=roi.historical_investment,
                forward_roi_pct=roi.forward_roi_pct,
                forward_impact=roi.forward_impact,
                forward_investment=roi.forward_investment,
                combined_roi_pct=roi.combined_roi_pct,
                total_arr=roi.total_arr,
                metric_details=roi.metric_details,
            )
            db.session.add(new_roi)
            roi_count += 1
        summary['roi_snapshots_cloned'] = roi_count

        # ----------------------------------------------------------
        # 11. Clone Journey Data (has customer_id + account_id)
        # ----------------------------------------------------------
        journey_count = 0
        for old_aid, new_aid in acct_id_map.items():
            journeys = JourneyData.query.filter_by(
                customer_id=source_customer_id,
                account_id=old_aid,
            ).all()
            for j in journeys:
                new_j = JourneyData(
                    customer_id=new_cid,
                    account_id=new_aid,
                    journey_json=j.journey_json,
                    total_weeks=j.total_weeks,
                    journey_pattern=j.journey_pattern,
                    generator_version=j.generator_version,
                    generated_at=j.generated_at,
                )
                db.session.add(new_j)
                journey_count += 1
        summary['journey_data_cloned'] = journey_count

        # ----------------------------------------------------------
        # 12. Create admin user for the new customer
        # ----------------------------------------------------------
        admin_user = None
        try:
            from models import User
            from werkzeug.security import generate_password_hash
            import secrets as _secrets
            admin_email = f"admin@{new_domain}"
            admin_password = _secrets.token_urlsafe(16)
            new_user = User(
                email=admin_email,
                user_name=f"Admin ({new_name})",
                customer_id=new_cid,
                role='admin',
                password_hash=generate_password_hash(admin_password),
                vertical=source.vertical,
            )
            new_user.customer_uuid = new_customer.uuid
            try:
                new_user.uuid = generate_id(uuid_vertical, 'user')
            except Exception:
                new_user.uuid = f"clone_user_{_uuid_mod.uuid4().hex[:12]}"
            db.session.add(new_user)
            db.session.flush()
            admin_user = {
                'user_id': new_user.user_id,
                'email': admin_email,
                'password': admin_password,
                'role': 'admin',
            }
            summary['admin_user_created'] = True
        except Exception as e:
            summary['admin_user_created'] = False
            summary['admin_user_error'] = str(e)

        # ----------------------------------------------------------
        # 13. Generate API key for the new customer
        # ----------------------------------------------------------
        api_key = None
        try:
            from api_key_service import generate_api_key as _gen_api_key
            full_key, _key_record = _gen_api_key(
                customer_id=new_cid,
                created_by=0,  # System-generated
                name='Clone Onboarding Key',
                scopes=['read', 'write'],
            )
            api_key = full_key
        except Exception:
            api_key = None

        # ----------------------------------------------------------
        # Commit the entire transaction atomically
        # ----------------------------------------------------------
        db.session.commit()

        # ----------------------------------------------------------
        # Build response
        # ----------------------------------------------------------
        total_records = (
            summary.get('accounts_cloned', 0)
            + summary.get('dc2s_kpis_cloned', 0)
            + summary.get('health_scores_cloned', 0)
            + summary.get('kpi_scores_cloned', 0)
            + summary.get('pillar_scores_cloned', 0)
            + summary.get('context_nodes_cloned', 0)
            + summary.get('context_edges_cloned', 0)
            + summary.get('qualitative_signals_cloned', 0)
            + summary.get('playbook_executions_cloned', 0)
            + summary.get('roi_snapshots_cloned', 0)
            + summary.get('journey_data_cloned', 0)
        )

        result = {
            'scope': 'customer',
            'status': 'cloned',
            'source_customer_id': source_customer_id,
            'new_customer_id': new_cid,
            'new_customer_name': new_name,
            'new_domain': new_domain,
            'vertical': source.vertical,
            'total_records_cloned': total_records,
            'details': summary,
            'message': (
                f"Successfully cloned customer {source_customer_id} "
                f"as '{new_name}' (ID={new_cid}). "
                f"{summary.get('accounts_cloned', 0)} accounts, "
                f"{summary.get('context_nodes_cloned', 0)} context nodes, "
                f"{total_records} total records."
            ),
        }

        if api_key:
            result['api_key'] = api_key
            result['api_key_note'] = (
                'Save this API key — it is shown only once. '
                'Use it for the intelligence tools.'
            )

        if admin_user:
            result['admin_user'] = admin_user
            result['admin_user_note'] = (
                'Admin user auto-created. Use these credentials to log in.'
            )

        result['next_steps'] = (
            'OPTION 1 — Use as-is: Clone is ready immediately. '
            'All data (accounts, KPIs, health scores, context graph, '
            'signals, playbooks, ROI) has been deep-copied with '
            'pre-calculated scores. No Wizards or process_data needed. '
            'OPTION 2 — Customize: Use export_customer_csvs() to download '
            'the 8 CSVs, modify them (change account names, KPI values, etc.), '
            'then upload_csv() + process_data() to recalculate scores '
            'with your changes. Wizards A/B/C only needed if you want '
            'to regenerate journeys or recalibrate weights.'
        )

        # Include canonical pillar labels so LLM clients display correct names
        result['dc2s_pillar_labels'] = _get_dc2s_pillar_labels()

        return result


# ===================================================================
# Tool: export_customer_csvs — Export all customer data as CSVs
# ===================================================================

@mcp.tool
def export_customer_csvs(
    customer_id: int,
    output_dir: str = '',
) -> dict:
    """Export all data for a customer as CSV files matching the onboarding upload format.

    Produces CSVs that can be re-uploaded via upload_csv() + process_data()
    without any transformation. Useful for cloning, backup, or data migration.

    No authentication required (onboarding tool).

    Exported files (8 customer-provided CSVs matching config/csv_schemas.json):
      Regular model: accounts.csv, kpi_measurements.csv, enhanced_qualitative_signals.csv, products.csv
      Context graph: stakeholders.csv, engagement_events.csv, account_business_profiles.csv, outcomes.csv

    Note: The 3 auto-generated files (decisions.csv, signal_edges.csv, industry_benchmarks.csv)
    are NOT exported — they get regenerated by process_data() from the uploaded data.

    Args:
        customer_id: Customer ID to export data from
        output_dir: Directory to save CSVs. Default: /tmp/cs_pulse_export_{customer_id}/
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        import csv
        import io
        from pathlib import Path
        from models import (
            Customer, Account, DC2SKPI, Product,
            QualitativeSignal, ContextNode,
        )
        from extensions import db

        # ----------------------------------------------------------
        # Validate customer
        # ----------------------------------------------------------
        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        # Resolve output directory
        if not output_dir:
            output_dir = f'/tmp/cs_pulse_export_{customer_id}'
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # ----------------------------------------------------------
        # Helper: write rows to CSV
        # ----------------------------------------------------------
        def _write_csv(filename: str, columns: list, rows: list) -> int:
            """Write rows to a CSV file. Returns row count."""
            fp = out_path / filename
            with open(fp, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            return len(rows)

        # ----------------------------------------------------------
        # Load all accounts for this customer (needed for joins)
        # ----------------------------------------------------------
        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        account_ids = [a.account_id for a in accounts]
        # Build account_id -> account_name lookup
        acct_name_map = {a.account_id: a.account_name for a in accounts}

        results = {}

        # ----------------------------------------------------------
        # 1. accounts.csv
        # ----------------------------------------------------------
        acct_cols = [
            'account_id', 'customer_id', 'account_name', 'industry', 'region',
            'vertical', 'tier', 'arr', 'revenue', 'contract_start', 'contract_end',
            'renewal_date', 'csm_name', 'csm_email', 'account_status', 'uuid',
        ]
        acct_rows = []
        for a in accounts:
            pm = a.profile_metadata or {}
            acct_rows.append({
                'account_id': a.account_id,
                'customer_id': a.customer_id,
                'account_name': a.account_name,
                'industry': a.industry,
                'region': a.region,
                'vertical': a.vertical,
                'tier': pm.get('tier', ''),
                'arr': pm.get('arr', '') or (float(a.revenue) if a.revenue else ''),
                'revenue': float(a.revenue) if a.revenue else '',
                'contract_start': pm.get('contract_start', ''),
                'contract_end': pm.get('contract_end', ''),
                'renewal_date': pm.get('renewal_date', ''),
                'csm_name': pm.get('assigned_csm', '') or pm.get('csm_name', ''),
                'csm_email': pm.get('csm_email', ''),
                'account_status': a.account_status,
                'uuid': a.uuid or '',
            })
        results['accounts.csv'] = _write_csv('accounts.csv', acct_cols, acct_rows)

        # ----------------------------------------------------------
        # 2. kpi_measurements.csv
        # ----------------------------------------------------------
        kpi_cols = [
            'account_id', 'kpi_code', 'measured_at', 'value',
            'kpi_name', 'pillar', 'target', 'weight', 'unit', 'status',
        ]
        kpi_rows = []
        if account_ids:
            kpis = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).all()
            for k in kpis:
                kpi_rows.append({
                    'account_id': k.account_id,
                    'kpi_code': k.kpi_code,
                    'measured_at': k.measured_at.isoformat() if k.measured_at else '',
                    'value': float(k.value),
                    'kpi_name': '',
                    'pillar': k.pillar or '',
                    'target': float(k.target) if k.target else '',
                    'weight': float(k.weight) if k.weight else '',
                    'unit': '',
                    'status': k.status or '',
                })
        results['kpi_measurements.csv'] = _write_csv('kpi_measurements.csv', kpi_cols, kpi_rows)

        # ----------------------------------------------------------
        # 3. enhanced_qualitative_signals.csv
        # ----------------------------------------------------------
        qs_cols = [
            'account_id', 'signal_date', 'signal_type', 'content', 'sentiment',
            'signal_ref', 'sentiment_score', 'stakeholder_name', 'stakeholder_title',
            'causal_chain_ref', 'revenue_impact', 'confidence', 'source_platform',
        ]
        qs_rows = []
        if account_ids:
            signals = QualitativeSignal.query.filter(
                QualitativeSignal.account_id.in_(account_ids)
            ).all()
            for s in signals:
                qs_rows.append({
                    'account_id': s.account_id,
                    'signal_date': s.signal_date.isoformat() if s.signal_date else '',
                    'signal_type': s.signal_type or '',
                    'content': s.content or '',
                    'sentiment': s.sentiment or '',
                    'signal_ref': s.signal_id or '',
                    'sentiment_score': float(s.sentiment_score) if s.sentiment_score else '',
                    'stakeholder_name': '',
                    'stakeholder_title': s.stakeholder_title or '',
                    'causal_chain_ref': '',
                    'revenue_impact': '',
                    'confidence': '',
                    'source_platform': '',
                })
        results['enhanced_qualitative_signals.csv'] = _write_csv(
            'enhanced_qualitative_signals.csv', qs_cols, qs_rows
        )

        # ----------------------------------------------------------
        # 4. products.csv
        # ----------------------------------------------------------
        prod_cols = [
            'account_id', 'product_name', 'product_category', 'quantity',
            'unit_price', 'deployment_date', 'status', 'customer_id',
        ]
        prod_rows = []
        if account_ids:
            products = Product.query.filter(Product.account_id.in_(account_ids)).all()
            for p in products:
                prod_rows.append({
                    'account_id': p.account_id,
                    'product_name': p.product_name,
                    'product_category': p.product_type or '',
                    'quantity': '',
                    'unit_price': float(p.revenue) if p.revenue else '',
                    'deployment_date': '',
                    'status': p.status or '',
                    'customer_id': p.customer_id,
                })
        results['products.csv'] = _write_csv('products.csv', prod_cols, prod_rows)

        # ----------------------------------------------------------
        # Context Graph CSVs — from context_nodes table
        # ----------------------------------------------------------
        ctx_nodes = []
        if account_ids:
            ctx_nodes = ContextNode.query.filter(
                ContextNode.account_id.in_(account_ids)
            ).all()

        # Group nodes by type
        nodes_by_type = {}
        for n in ctx_nodes:
            nodes_by_type.setdefault(n.node_type, []).append(n)

        # ----------------------------------------------------------
        # 5. stakeholders.csv (node_type=STAKEHOLDER)
        # ----------------------------------------------------------
        sh_cols = [
            'account_id', 'stakeholder_name', 'title', 'role', 'influence_score',
            'email', 'engagement_frequency', 'sentiment', 'department',
            'is_active', 'source_platform', 'first_observed_at',
        ]
        sh_rows = []
        for n in nodes_by_type.get('STAKEHOLDER', []):
            props = n.properties or {}
            sh_rows.append({
                'account_id': n.account_id,
                'stakeholder_name': n.title or props.get('stakeholder_name', ''),
                'title': props.get('title', ''),
                'role': props.get('role', n.node_subtype or ''),
                'influence_score': props.get('influence_score', ''),
                'email': props.get('email', ''),
                'engagement_frequency': props.get('engagement_frequency', ''),
                'sentiment': props.get('sentiment', ''),
                'department': props.get('department', ''),
                'is_active': props.get('is_active', ''),
                'source_platform': n.source_platform or '',
                'first_observed_at': n.occurred_at.isoformat() if n.occurred_at else '',
            })
        results['stakeholders.csv'] = _write_csv('stakeholders.csv', sh_cols, sh_rows)

        # ----------------------------------------------------------
        # 6. engagement_events.csv (node_type=SIGNAL, subtype=engagement)
        # ----------------------------------------------------------
        ee_cols = [
            'account_id', 'event_date', 'event_type', 'description',
            'stakeholder_name', 'sentiment_shift', 'channel',
            'duration_minutes', 'outcome', 'source_platform',
        ]
        ee_rows = []
        for n in nodes_by_type.get('SIGNAL', []):
            props = n.properties or {}
            # Include all SIGNAL nodes as engagement events
            ee_rows.append({
                'account_id': n.account_id,
                'event_date': n.occurred_at.isoformat() if n.occurred_at else '',
                'event_type': n.node_subtype or props.get('event_type', ''),
                'description': n.title or '',
                'stakeholder_name': props.get('stakeholder_name', ''),
                'sentiment_shift': props.get('sentiment_shift', ''),
                'channel': props.get('channel', ''),
                'duration_minutes': props.get('duration_minutes', ''),
                'outcome': props.get('outcome', ''),
                'source_platform': n.source_platform or '',
            })
        results['engagement_events.csv'] = _write_csv('engagement_events.csv', ee_cols, ee_rows)

        # ----------------------------------------------------------
        # 7. account_business_profiles.csv (node_type=ACCOUNT)
        # ----------------------------------------------------------
        abp_cols = [
            'account_id', 'arr', 'industry', 'employee_count',
            'fiscal_year_end', 'tech_stack', 'cloud_provider',
            'competitive_landscape', 'strategic_initiatives', 'budget_cycle',
            'profile_date', 'assigned_csm', 'csm_manager', 'executive_sponsor',
            'mrr', 'primary_champion_name', 'primary_champion_title',
            'primary_champion_email', 'primary_champion_engagement_score',
            'last_updated',
        ]
        abp_rows = []
        # If no ACCOUNT nodes, build from the accounts table profile_metadata
        account_nodes = nodes_by_type.get('ACCOUNT', [])
        if account_nodes:
            for n in account_nodes:
                props = n.properties or {}
                abp_rows.append({
                    'account_id': n.account_id,
                    'arr': props.get('arr', ''),
                    'industry': props.get('industry', ''),
                    'employee_count': props.get('employee_count', ''),
                    'fiscal_year_end': props.get('fiscal_year_end', ''),
                    'tech_stack': props.get('tech_stack', ''),
                    'cloud_provider': props.get('cloud_provider', ''),
                    'competitive_landscape': props.get('competitive_landscape', ''),
                    'strategic_initiatives': props.get('strategic_initiatives', ''),
                    'budget_cycle': props.get('budget_cycle', ''),
                    'profile_date': n.occurred_at.isoformat() if n.occurred_at else '',
                    'assigned_csm': props.get('assigned_csm', ''),
                    'csm_manager': props.get('csm_manager', ''),
                    'executive_sponsor': props.get('executive_sponsor', ''),
                    'mrr': props.get('mrr', ''),
                    'primary_champion_name': props.get('primary_champion_name', ''),
                    'primary_champion_title': props.get('primary_champion_title', ''),
                    'primary_champion_email': props.get('primary_champion_email', ''),
                    'primary_champion_engagement_score': props.get('primary_champion_engagement_score', ''),
                    'last_updated': n.updated_at.isoformat() if n.updated_at else '',
                })
        else:
            # Fallback: build from accounts table profile_metadata
            for a in accounts:
                pm = a.profile_metadata or {}
                abp_rows.append({
                    'account_id': a.account_id,
                    'arr': pm.get('arr', '') or (float(a.revenue) if a.revenue else ''),
                    'industry': a.industry or '',
                    'employee_count': pm.get('employee_count', ''),
                    'fiscal_year_end': pm.get('fiscal_year_end', ''),
                    'tech_stack': pm.get('tech_stack', ''),
                    'cloud_provider': pm.get('cloud_provider', ''),
                    'competitive_landscape': pm.get('competitive_landscape', ''),
                    'strategic_initiatives': pm.get('strategic_initiatives', ''),
                    'budget_cycle': pm.get('budget_cycle', ''),
                    'profile_date': '',
                    'assigned_csm': pm.get('assigned_csm', ''),
                    'csm_manager': pm.get('csm_manager', ''),
                    'executive_sponsor': pm.get('executive_sponsor', ''),
                    'mrr': pm.get('mrr', ''),
                    'primary_champion_name': pm.get('primary_champion_name', ''),
                    'primary_champion_title': pm.get('primary_champion_title', ''),
                    'primary_champion_email': pm.get('primary_champion_email', ''),
                    'primary_champion_engagement_score': pm.get('primary_champion_engagement_score', ''),
                    'last_updated': a.updated_at.isoformat() if a.updated_at else '',
                })
        results['account_business_profiles.csv'] = _write_csv(
            'account_business_profiles.csv', abp_cols, abp_rows
        )

        # ----------------------------------------------------------
        # 8. outcomes.csv (node_type=OUTCOME)
        # ----------------------------------------------------------
        out_cols = [
            'account_id', 'outcome_date', 'title', 'outcome_type', 'revenue_value',
            'outcome_id', 'evidence', 'confidence', 'related_decision_id',
            'source_platform',
        ]
        out_rows = []
        for n in nodes_by_type.get('OUTCOME', []):
            props = n.properties or {}
            out_rows.append({
                'account_id': n.account_id,
                'outcome_date': n.occurred_at.isoformat() if n.occurred_at else '',
                'title': n.title or '',
                'outcome_type': n.node_subtype or props.get('outcome_type', ''),
                'revenue_value': float(n.revenue_impact) if n.revenue_impact else '',
                'outcome_id': n.source_ref or n.source_event_id or '',
                'evidence': props.get('evidence', ''),
                'confidence': float(n.confidence) if n.confidence else '',
                'related_decision_id': props.get('related_decision_id', ''),
                'source_platform': n.source_platform or '',
            })
        results['outcomes.csv'] = _write_csv('outcomes.csv', out_cols, out_rows)

        # ----------------------------------------------------------
        # Build response
        # NOTE: decisions.csv, signal_edges.csv, industry_benchmarks.csv
        # are auto-generated by process_data() — not exported here.
        # ----------------------------------------------------------
        files_created = [
            {'file': name, 'rows': count, 'path': str(out_path / name)}
            for name, count in results.items()
            if count > 0
        ]
        total_rows = sum(results.values())
        all_files = [
            {'file': name, 'rows': count, 'path': str(out_path / name)}
            for name, count in results.items()
        ]

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'output_dir': str(out_path),
            'files_with_data': len(files_created),
            'total_files': len(all_files),
            'total_rows': total_rows,
            'files': all_files,
            'message': (
                f"Exported {total_rows} rows across {len(files_created)} files "
                f"(of {len(all_files)} total) to {out_path}. "
                f"Re-upload via upload_csv() + process_data(). "
                f"NOTE: If you cannot access these files (e.g. Claude.ai), "
                f"use download_customer_csv() instead — it returns CSV content inline."
            ),
        }


# ===================================================================
# Tool: download_customer_csv — Return CSV content inline for download
# ===================================================================

@mcp.tool
def download_customer_csv(
    customer_id: int,
    file_type: str = 'all',
) -> dict:
    """Download customer data as CSV content returned inline in the response.

    Unlike export_customer_csvs() which writes to the server filesystem,
    this tool returns CSV content directly in the response — making it
    accessible to Claude.ai and other MCP clients that cannot access
    the server's filesystem.

    No authentication required (onboarding tool).

    Args:
        customer_id: Customer ID to download data from
        file_type: Which CSV to download. Options:
            'all' — returns all 8 CSVs (may be large)
            'accounts' — accounts.csv
            'kpi_measurements' — kpi_measurements.csv
            'signals' — enhanced_qualitative_signals.csv
            'products' — products.csv
            'stakeholders' — stakeholders.csv
            'engagement_events' — engagement_events.csv
            'profiles' — account_business_profiles.csv
            'outcomes' — outcomes.csv
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        import csv
        import io
        from models import (
            Customer, Account, DC2SKPI, Product,
            QualitativeSignal, ContextNode,
        )
        from extensions import db

        # Validate customer
        customer = db.session.get(Customer, int(customer_id))
        if not customer:
            raise ToolError(f"Customer {customer_id} not found.")

        # Load accounts
        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        account_ids = [a.account_id for a in accounts]

        # Helper: build CSV string in memory
        def _csv_string(columns: list, rows: list) -> str:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            return buf.getvalue()

        # Map of file_type -> (generator_function)
        valid_types = [
            'accounts', 'kpi_measurements', 'signals', 'products',
            'stakeholders', 'engagement_events', 'profiles', 'outcomes',
        ]

        if file_type != 'all' and file_type not in valid_types:
            raise ToolError(
                f"Invalid file_type '{file_type}'. "
                f"Valid options: 'all', {', '.join(valid_types)}"
            )

        requested = valid_types if file_type == 'all' else [file_type]
        csvs = {}

        # ---- accounts ----
        if 'accounts' in requested:
            cols = [
                'account_id', 'customer_id', 'account_name', 'industry', 'region',
                'vertical', 'tier', 'arr', 'revenue', 'contract_start', 'contract_end',
                'renewal_date', 'csm_name', 'csm_email', 'account_status', 'uuid',
            ]
            rows = []
            for a in accounts:
                pm = a.profile_metadata or {}
                rows.append({
                    'account_id': a.account_id,
                    'customer_id': a.customer_id,
                    'account_name': a.account_name,
                    'industry': a.industry,
                    'region': a.region,
                    'vertical': a.vertical,
                    'tier': pm.get('tier', ''),
                    'arr': pm.get('arr', '') or (float(a.revenue) if a.revenue else ''),
                    'revenue': float(a.revenue) if a.revenue else '',
                    'contract_start': pm.get('contract_start', ''),
                    'contract_end': pm.get('contract_end', ''),
                    'renewal_date': pm.get('renewal_date', ''),
                    'csm_name': pm.get('assigned_csm', '') or pm.get('csm_name', ''),
                    'csm_email': pm.get('csm_email', ''),
                    'account_status': a.account_status,
                    'uuid': a.uuid or '',
                })
            csvs['accounts.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # ---- kpi_measurements ----
        if 'kpi_measurements' in requested:
            cols = [
                'account_id', 'kpi_code', 'measured_at', 'value',
                'kpi_name', 'pillar', 'target', 'weight', 'unit', 'status',
            ]
            rows = []
            if account_ids:
                kpis = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).all()
                for k in kpis:
                    rows.append({
                        'account_id': k.account_id,
                        'kpi_code': k.kpi_code,
                        'measured_at': k.measured_at.isoformat() if k.measured_at else '',
                        'value': float(k.value),
                        'kpi_name': '',
                        'pillar': k.pillar or '',
                        'target': float(k.target) if k.target else '',
                        'weight': float(k.weight) if k.weight else '',
                        'unit': '',
                        'status': k.status or '',
                    })
            csvs['kpi_measurements.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # ---- signals ----
        if 'signals' in requested:
            cols = [
                'account_id', 'signal_date', 'signal_type', 'content', 'sentiment',
                'signal_ref', 'sentiment_score', 'stakeholder_name', 'stakeholder_title',
                'causal_chain_ref', 'revenue_impact', 'confidence', 'source_platform',
            ]
            rows = []
            if account_ids:
                signals = QualitativeSignal.query.filter(
                    QualitativeSignal.account_id.in_(account_ids)
                ).all()
                for s in signals:
                    rows.append({
                        'account_id': s.account_id,
                        'signal_date': s.signal_date.isoformat() if s.signal_date else '',
                        'signal_type': s.signal_type or '',
                        'content': s.content or '',
                        'sentiment': s.sentiment or '',
                        'signal_ref': s.signal_id or '',
                        'sentiment_score': float(s.sentiment_score) if s.sentiment_score else '',
                        'stakeholder_name': '',
                        'stakeholder_title': s.stakeholder_title or '',
                        'causal_chain_ref': '',
                        'revenue_impact': '',
                        'confidence': '',
                        'source_platform': '',
                    })
            csvs['enhanced_qualitative_signals.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # ---- products ----
        if 'products' in requested:
            cols = [
                'account_id', 'product_name', 'product_category', 'quantity',
                'unit_price', 'deployment_date', 'status', 'customer_id',
            ]
            rows = []
            if account_ids:
                products = Product.query.filter(Product.account_id.in_(account_ids)).all()
                for p in products:
                    rows.append({
                        'account_id': p.account_id,
                        'product_name': p.product_name,
                        'product_category': p.product_type or '',
                        'quantity': '',
                        'unit_price': float(p.revenue) if p.revenue else '',
                        'deployment_date': '',
                        'status': p.status or '',
                        'customer_id': p.customer_id,
                    })
            csvs['products.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # ---- Context graph CSVs ----
        ctx_nodes = []
        if account_ids and any(t in requested for t in ['stakeholders', 'engagement_events', 'profiles', 'outcomes']):
            ctx_nodes = ContextNode.query.filter(
                ContextNode.account_id.in_(account_ids)
            ).all()

        nodes_by_type = {}
        for n in ctx_nodes:
            nodes_by_type.setdefault(n.node_type, []).append(n)

        # ---- stakeholders ----
        if 'stakeholders' in requested:
            cols = [
                'account_id', 'stakeholder_name', 'title', 'role', 'influence_score',
                'email', 'engagement_frequency', 'sentiment', 'department',
                'is_active', 'source_platform', 'first_observed_at',
            ]
            rows = []
            for n in nodes_by_type.get('STAKEHOLDER', []):
                props = n.properties or {}
                rows.append({
                    'account_id': n.account_id,
                    'stakeholder_name': n.title or props.get('stakeholder_name', ''),
                    'title': props.get('title', ''),
                    'role': props.get('role', n.node_subtype or ''),
                    'influence_score': props.get('influence_score', ''),
                    'email': props.get('email', ''),
                    'engagement_frequency': props.get('engagement_frequency', ''),
                    'sentiment': props.get('sentiment', ''),
                    'department': props.get('department', ''),
                    'is_active': props.get('is_active', ''),
                    'source_platform': n.source_platform or '',
                    'first_observed_at': n.occurred_at.isoformat() if n.occurred_at else '',
                })
            csvs['stakeholders.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # ---- engagement_events ----
        if 'engagement_events' in requested:
            cols = [
                'account_id', 'event_date', 'event_type', 'description',
                'stakeholder_name', 'sentiment_shift', 'channel',
                'duration_minutes', 'outcome', 'source_platform',
            ]
            rows = []
            for n in nodes_by_type.get('SIGNAL', []):
                props = n.properties or {}
                rows.append({
                    'account_id': n.account_id,
                    'event_date': n.occurred_at.isoformat() if n.occurred_at else '',
                    'event_type': n.node_subtype or props.get('event_type', ''),
                    'description': n.title or '',
                    'stakeholder_name': props.get('stakeholder_name', ''),
                    'sentiment_shift': props.get('sentiment_shift', ''),
                    'channel': props.get('channel', ''),
                    'duration_minutes': props.get('duration_minutes', ''),
                    'outcome': props.get('outcome', ''),
                    'source_platform': n.source_platform or '',
                })
            csvs['engagement_events.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # ---- profiles ----
        if 'profiles' in requested:
            cols = [
                'account_id', 'arr', 'industry', 'employee_count',
                'fiscal_year_end', 'tech_stack', 'cloud_provider',
                'competitive_landscape', 'strategic_initiatives', 'budget_cycle',
                'profile_date', 'assigned_csm', 'csm_manager', 'executive_sponsor',
                'mrr', 'primary_champion_name', 'primary_champion_title',
                'primary_champion_email', 'primary_champion_engagement_score',
                'last_updated',
            ]
            rows = []
            account_nodes = nodes_by_type.get('ACCOUNT', [])
            if account_nodes:
                for n in account_nodes:
                    props = n.properties or {}
                    rows.append({
                        'account_id': n.account_id,
                        'arr': props.get('arr', ''),
                        'industry': props.get('industry', ''),
                        'employee_count': props.get('employee_count', ''),
                        'fiscal_year_end': props.get('fiscal_year_end', ''),
                        'tech_stack': props.get('tech_stack', ''),
                        'cloud_provider': props.get('cloud_provider', ''),
                        'competitive_landscape': props.get('competitive_landscape', ''),
                        'strategic_initiatives': props.get('strategic_initiatives', ''),
                        'budget_cycle': props.get('budget_cycle', ''),
                        'profile_date': n.occurred_at.isoformat() if n.occurred_at else '',
                        'assigned_csm': props.get('assigned_csm', ''),
                        'csm_manager': props.get('csm_manager', ''),
                        'executive_sponsor': props.get('executive_sponsor', ''),
                        'mrr': props.get('mrr', ''),
                        'primary_champion_name': props.get('primary_champion_name', ''),
                        'primary_champion_title': props.get('primary_champion_title', ''),
                        'primary_champion_email': props.get('primary_champion_email', ''),
                        'primary_champion_engagement_score': props.get('primary_champion_engagement_score', ''),
                        'last_updated': n.updated_at.isoformat() if n.updated_at else '',
                    })
            else:
                for a in accounts:
                    pm = a.profile_metadata or {}
                    rows.append({
                        'account_id': a.account_id,
                        'arr': pm.get('arr', '') or (float(a.revenue) if a.revenue else ''),
                        'industry': a.industry or '',
                        'employee_count': pm.get('employee_count', ''),
                        'fiscal_year_end': pm.get('fiscal_year_end', ''),
                        'tech_stack': pm.get('tech_stack', ''),
                        'cloud_provider': pm.get('cloud_provider', ''),
                        'competitive_landscape': pm.get('competitive_landscape', ''),
                        'strategic_initiatives': pm.get('strategic_initiatives', ''),
                        'budget_cycle': pm.get('budget_cycle', ''),
                        'profile_date': '',
                        'assigned_csm': pm.get('assigned_csm', ''),
                        'csm_manager': pm.get('csm_manager', ''),
                        'executive_sponsor': pm.get('executive_sponsor', ''),
                        'mrr': pm.get('mrr', ''),
                        'primary_champion_name': pm.get('primary_champion_name', ''),
                        'primary_champion_title': pm.get('primary_champion_title', ''),
                        'primary_champion_email': pm.get('primary_champion_email', ''),
                        'primary_champion_engagement_score': pm.get('primary_champion_engagement_score', ''),
                        'last_updated': a.updated_at.isoformat() if a.updated_at else '',
                    })
            csvs['account_business_profiles.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # ---- outcomes ----
        if 'outcomes' in requested:
            cols = [
                'account_id', 'outcome_date', 'title', 'outcome_type', 'revenue_value',
                'outcome_id', 'evidence', 'confidence', 'related_decision_id',
                'source_platform',
            ]
            rows = []
            for n in nodes_by_type.get('OUTCOME', []):
                props = n.properties or {}
                rows.append({
                    'account_id': n.account_id,
                    'outcome_date': n.occurred_at.isoformat() if n.occurred_at else '',
                    'title': n.title or '',
                    'outcome_type': n.node_subtype or props.get('outcome_type', ''),
                    'revenue_value': float(n.revenue_impact) if n.revenue_impact else '',
                    'outcome_id': n.source_ref or n.source_event_id or '',
                    'evidence': props.get('evidence', ''),
                    'confidence': float(n.confidence) if n.confidence else '',
                    'related_decision_id': props.get('related_decision_id', ''),
                    'source_platform': n.source_platform or '',
                })
            csvs['outcomes.csv'] = {'content': _csv_string(cols, rows), 'rows': len(rows)}

        # Build response
        total_rows = sum(f['rows'] for f in csvs.values())
        files_summary = [
            {'file': name, 'rows': info['rows']}
            for name, info in csvs.items()
        ]

        result = {
            'scope': 'customer',
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'file_type': file_type,
            'total_files': len(csvs),
            'total_rows': total_rows,
            'files': files_summary,
            'message': (
                f"Downloaded {total_rows} rows across {len(csvs)} CSV(s) for "
                f"{customer.customer_name}. CSV content is in the 'csv_data' field. "
                f"Save each file using the filename as key."
            ),
            'csv_data': {
                name: info['content']
                for name, info in csvs.items()
            },
        }

        # For single file, also put content at top level for easy access
        if file_type != 'all' and len(csvs) == 1:
            fname = list(csvs.keys())[0]
            result['filename'] = fname
            result['csv_content'] = csvs[fname]['content']

        return result


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
