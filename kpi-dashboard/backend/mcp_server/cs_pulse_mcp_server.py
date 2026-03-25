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

Architecture:
  This file defines the `mcp` FastMCP instance and all shared helpers.
  Tools are split across modules that import `mcp` and register on it:
    - cs_pulse_intelligence.py  (7 tools: context graph / revenue intel)
    - cs_pulse_revenue.py       (7 tools: ROI / portfolio / playbooks)
    - cs_pulse_onboarding.py    (11 tools: onboarding / clone / CSV)
    - cs_pulse_admin.py         (5 tools: CRM / tickets / feedback / CSM actions / partner)
  This file keeps 7 core tools: platform_instructions, list_customers,
  get_kpi_catalog, list_accounts, get_account_health, get_at_risk_accounts,
  plus the system prompt resource.
"""

import os
import sys

# Ensure backend AND mcp_server dirs are on the Python path
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_mcp_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
if _mcp_dir not in sys.path:
    sys.path.insert(0, _mcp_dir)

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
# Helpers (exported to modules via import)
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

    Priority:
    1. Try vertical-specific Python module (legacy DC2_S / SaaS Premium)
    2. Fall back to generic scorer (works with any JSON-catalog-defined vertical)
    3. Last resort: noop scorer (returns 0)
    """
    # 1. Try vertical-specific modules (legacy DC2_S only)
    # NOTE: SaaS Premium's Python scorer is a stub that returns 50 for all KPIs.
    # Skip it and use the generic JSON-catalog scorer instead. DC2_S's Python
    # scorer is fully functional and remains the primary path for DC2_S.
    if vertical in ('dc2_s', 'dc2s', 'dc', 'datacenter'):
        try:
            from verticals.dc2_s.api_routes import (
                calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores,
            )
            return calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores
        except ImportError:
            pass  # Fall through to generic

    # 2. Generic scorer — works with any JSON-catalog-defined vertical
    try:
        from utils.generic_scorer import calculate_health_generic
        def _generic_calculate(kpi_values, customer_id=None):
            return calculate_health_generic(kpi_values, vertical)
        return _generic_calculate, _get_trailing_kpi_values_generic, _get_precalculated_scores
    except ImportError:
        pass

    # 3. Last resort: noop
    def _noop_calculate(kpi_values, customer_id=None):
        return 0.0, {}
    return _noop_calculate, _get_trailing_kpi_values_generic, _get_precalculated_scores


def _get_kpi_definitions(vertical: str) -> dict:
    """Return the KPI definitions dict for a vertical."""
    if vertical in ('saas_premium', 'saas'):
        try:
            from verticals.saas_premium.kpi_definitions import SAAS_KPIS
            return SAAS_KPIS
        except ImportError:
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
    """Enforce API key auth for portfolio/customer-level intelligence tools."""
    from mcp_server.auth import require_auth
    require_auth(customer_id, required_scope, _api_key)


def _require_account_auth(customer_id: int, account_id: int,
                          required_scope: str = 'read',
                          _api_key: str = None):
    """Enforce API key auth for account-level intelligence tools."""
    from mcp_server.auth import require_account_auth
    require_account_auth(customer_id, account_id, required_scope, _api_key)


def _load_system_prompt_content() -> str:
    """Load CS Pulse MCP system prompt for Claude. Used by cspulse://system-prompt resource."""
    env_path = os.environ.get("CSPULSE_MCP_SYSTEM_PROMPT_PATH")
    if env_path and os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            return f.read()
    _dir = os.path.dirname(os.path.abspath(__file__))
    for candidate in [
        os.path.join(_dir, "..", "config", "mcp_system_prompt.md"),
        os.path.join(_dir, "..", "..", "..", "CS_PULSE_MCP_SYSTEM_PROMPT.md"),
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
        "tool_count": 45,
        "note": (
            "These instructions are now in your context. Follow them for all subsequent "
            "tool calls. Key rules: (1) customer_id is the tenant, account_id is one of "
            "their accounts. (2) Never manually sum revenue from nodes — use "
            "get_revenue_at_risk() only. (3) Health thresholds: critical <50, at_risk 50-69, "
            "healthy >=70."
        ),
    }


# ===================================================================
# Tool: list_customers — Debug tool: recent customers by vertical
# ===================================================================

@mcp.tool
def list_customers() -> dict:
    """List recent customers grouped by vertical (last 5 per vertical).

    Debug/internal tool — returns customer_id, name, vertical, account count,
    total ARR, and created_at for the most recent customers in each vertical.
    Use this to find the correct customer_id before calling other tools.

    No parameters required.
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Customer, Account, CustomerConfig
        from extensions import db
        from sqlalchemy import func, text

        acct_stats = dict(
            db.session.query(
                Account.customer_id,
                func.count(Account.account_id),
            ).group_by(Account.customer_id).all()
        )
        arr_stats = dict(
            db.session.query(
                Account.customer_id,
                func.sum(Account.revenue),
            ).group_by(Account.customer_id).all()
        )

        cc_map = {}
        for cc in CustomerConfig.query.all():
            if cc.vertical:
                cc_map[cc.customer_id] = cc.vertical

        import os, glob
        vert_base = os.path.join(os.path.dirname(__file__), '..', 'verticals')
        for d in glob.glob(os.path.join(vert_base, 'customer*-*')):
            dirname = os.path.basename(d)
            try:
                cid_str, vsuffix = dirname.split('-', 1)
                cid = int(cid_str.replace('customer', ''))
                if cid not in cc_map:
                    cc_map[cid] = vsuffix
            except (ValueError, IndexError):
                pass

        customers = Customer.query.order_by(Customer.customer_id.desc()).all()

        by_vertical = {}
        for c in customers:
            num_accts = acct_stats.get(c.customer_id, 0)
            if num_accts == 0:
                continue
            vertical = cc_map.get(c.customer_id, 'dc2_s')
            if vertical in ('saas', 'saas_premium'):
                vertical = 'saas_premium'
            if vertical not in by_vertical:
                by_vertical[vertical] = []
            arr = arr_stats.get(c.customer_id) or 0
            by_vertical[vertical].append({
                'customer_id': c.customer_id,
                'name': c.customer_name,
                'accounts': num_accts,
                'total_arr': round(float(arr), 0),
                'created_at': getattr(c, 'created_at', None).strftime('%Y-%m-%d %H:%M:%S') if getattr(c, 'created_at', None) else 'unknown',
            })

        result = {}
        for vertical, custs in by_vertical.items():
            result[vertical] = custs[:5]

        return {
            'scope': 'platform',
            'verticals': result,
            'total_customers': sum(len(v) for v in result.values()),
            'note': 'Debug tool — shows last 5 customers per vertical. Use customer_id with other tools.',
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
        vertical = 'dc2_s'
        if customer_id and int(customer_id) > 0:
            try:
                vertical = _resolve_customer_vertical(int(customer_id))
            except Exception:
                pass

        kpi_defs = _get_kpi_definitions(vertical)

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
# Tool: list_accounts
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
                pass

        results = []
        for acct in accounts:
            precalc_health, precalc_status, precalc_pillars = get_precalculated_scores(acct.account_id)

            if precalc_health is not None and precalc_pillars:
                health = precalc_health
                pillars = precalc_pillars
                status = precalc_status
            else:
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

        results.sort(key=lambda x: x["health_score"])

        total_arr = sum(r["arr"] for r in results)
        avg_health = round(
            sum(r["health_score"] for r in results) / len(results), 1
        ) if results else 0

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


# ===================================================================
# Tool: get_account_health
# ===================================================================

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

        precalc_health, precalc_status, precalc_pillars = get_precalculated_scores(account_id)

        if precalc_health is not None and precalc_pillars:
            health = precalc_health
            pillars = precalc_pillars
            status = precalc_status
        else:
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


# ===================================================================
# Tool: get_at_risk_accounts
# ===================================================================

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
# Register tools from modules (import triggers @mcp.tool registration)
# Only runs when imported as a module (not when run as __main__).
# When run as __main__, tool imports happen in the entrypoint block below
# AFTER sys.modules aliasing fixes the dual-instance bug.
# ===================================================================
if __name__ != "__main__":
    _module_tools = {'intelligence': 7, 'revenue': 7, 'onboarding': 11, 'admin': 5}
    for _mod_name, _expected in _module_tools.items():
        try:
            __import__(f'cs_pulse_{_mod_name}')
        except Exception as _e:
            print(f"  ❌ FAILED to load cs_pulse_{_mod_name}: {_e}")


# ===================================================================
# Entrypoint
# ===================================================================
if __name__ == "__main__":
    # CRITICAL: When run as `python3 mcp_server/cs_pulse_mcp_server.py`,
    # this file is loaded as __main__, not as cs_pulse_mcp_server.
    # Submodules do `from cs_pulse_mcp_server import mcp` which would
    # create a SECOND module instance with its own `mcp` object.
    # Fix: register __main__ as cs_pulse_mcp_server in sys.modules
    # so submodule imports find THIS instance, not a fresh copy.
    import types
    sys.modules['cs_pulse_mcp_server'] = sys.modules['__main__']

    # Now import submodules — they'll get our mcp instance
    _module_tools_main = {'intelligence': 7, 'revenue': 7, 'onboarding': 11, 'admin': 5}
    for _mod, _exp in _module_tools_main.items():
        try:
            __import__(f'cs_pulse_{_mod}')
            print(f"  ✅ Loaded cs_pulse_{_mod} ({_exp} tools)")
        except Exception as _e:
            print(f"  ❌ FAILED to load cs_pulse_{_mod}: {_e}")

    print(f"  Total tools registered: {len(mcp._tool_manager._tools)}")

    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if transport == "http":
        os.environ["MCP_TRANSPORT"] = "http"
        mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
    else:
        os.environ["MCP_TRANSPORT"] = "stdio"
        mcp.run(transport="stdio")
