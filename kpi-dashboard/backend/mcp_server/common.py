#!/usr/bin/env python3
"""
CS Pulse MCP — Shared helpers used across all tiered MCP servers.

Extracted from the monolithic cs_pulse_mcp_server.py so that
cs_pulse_intelligence, cs_pulse_revenue, cs_pulse_onboarding,
and cs_pulse_admin can each import a common foundation.
"""

import os
import sys

# Ensure backend is on the Python path
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastmcp.exceptions import ToolError

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_PROMPT_FILE = os.path.join(_backend_dir, 'config', 'mcp_system_prompt.md')


def load_system_prompt() -> str:
    """Load MCP system prompt from config/mcp_system_prompt.md."""
    try:
        with open(_PROMPT_FILE, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return (
            "AI-native Customer Success platform — health scoring, "
            "signal detection, context graph intelligence, revenue analytics."
        )


def load_system_prompt_content() -> str:
    """Load CS Pulse MCP system prompt for the resource endpoint.

    Search order:
      1) CSPULSE_MCP_SYSTEM_PROMPT_PATH env var
      2) backend/config/mcp_system_prompt.md
      3) Repo root CS_PULSE_MCP_SYSTEM_PROMPT.md
      4) mcp_server/cs_pulse_mcp_system_prompt.md
    """
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
    return "# CS Pulse MCP — System prompt file not found."


# ---------------------------------------------------------------------------
# Feature gate
# ---------------------------------------------------------------------------
def check_mcp_enabled():
    """Raise ToolError if MCP_SERVER toggle is OFF."""
    from feature_toggles import feature_toggles, FeatureToggle
    if not feature_toggles.is_enabled(FeatureToggle.MCP_SERVER):
        raise ToolError("MCP Server is disabled. Enable via FEATURE_MCP_SERVER=true")


# ---------------------------------------------------------------------------
# Flask app singleton (lightweight DB context)
# ---------------------------------------------------------------------------
_flask_app = None


def get_flask_app():
    """Return a minimal Flask app for DB context."""
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


# ---------------------------------------------------------------------------
# Agent tool registry
# ---------------------------------------------------------------------------
_registry_initialized = False


def ensure_registry():
    """Initialize the agent tool registry (once)."""
    global _registry_initialized
    if not _registry_initialized:
        from agent_tool_registry import register_all_tools
        register_all_tools()
        _registry_initialized = True


# ---------------------------------------------------------------------------
# Account / customer helpers
# ---------------------------------------------------------------------------
def get_account_arr(account) -> float:
    """Extract ARR from account (profile_metadata or revenue column)."""
    arr = 0.0
    if account.profile_metadata and isinstance(account.profile_metadata, dict):
        arr = float(account.profile_metadata.get('arr', 0) or 0)
    if not arr and account.revenue:
        arr = float(account.revenue)
    return arr


def validate_account_ownership(customer_id: int, account_id: int):
    """Tenant isolation: verify account belongs to customer, return Account or raise."""
    from models import Account
    account = Account.query.filter_by(
        account_id=account_id,
        customer_id=int(customer_id),
    ).first()
    if not account:
        raise ToolError(f"Account {account_id} not found for customer {customer_id}")
    return account


def resolve_customer_vertical(customer_id: int) -> str:
    """Look up the vertical for a customer. Falls back to 'dc2_s'."""
    from models import Customer
    customer = Customer.query.get(int(customer_id))
    if not customer:
        raise ToolError(f"Customer {customer_id} not found")
    return getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'


# ---------------------------------------------------------------------------
# Pillar labels (vertical-aware)
# ---------------------------------------------------------------------------
def get_pillar_labels(vertical: str = 'dc2_s') -> dict:
    """Return canonical pillar labels for a vertical."""
    if vertical in ('saas_premium', 'saas'):
        try:
            from verticals.saas_premium.kpi_definitions import SAAS_PILLARS
            return {code: p['name'] for code, p in SAAS_PILLARS.items()}
        except ImportError:
            pass
    try:
        from verticals.dc2_s.kpi_definitions import DC2S_PILLARS
        return {code: p['name'] for code, p in DC2S_PILLARS.items()}
    except ImportError:
        return {
            'P1': 'Deployment Velocity', 'P2': 'Operational Stability',
            'P3': 'AI Workload Performance', 'P4': 'Channel & Partner Health',
            'P5': 'Expansion Readiness',
        }


# ---------------------------------------------------------------------------
# Health / score helpers (vertical-agnostic)
# ---------------------------------------------------------------------------
def get_precalculated_scores(account_id: int):
    """Read pre-calculated scores from HealthScore/PillarScore tables.

    Returns (health_score, health_status, pillar_dict) or (None, None, None).
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


def get_trailing_kpi_values_generic(account_id: int) -> dict:
    """Read latest KPI values from KpiScore table. Returns {kpi_code: score}."""
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


def get_health_functions(vertical: str):
    """Return (calculate_kpi_health, get_trailing_kpi_values, get_precalculated_scores)
    for the given vertical. All verticals use the generic JSON-catalog scorer.
    """
    from utils.vertical_health import get_health_calculator, get_trailing_kpi_values_func
    from utils.vertical_health import get_precalculated_scores as vpc

    try:
        calc = get_health_calculator(None)  # Vertical resolved from catalog
        trailing = get_trailing_kpi_values_func(None)
        return calc, trailing, vpc
    except Exception:
        def _noop_calculate(kpi_values, customer_id=None):
            return 0.0, {}
        return _noop_calculate, get_trailing_kpi_values_generic, get_precalculated_scores


def get_kpi_definitions(vertical: str) -> dict:
    """Return the KPI definitions dict for a vertical."""
    if vertical in ('saas_premium', 'saas'):
        try:
            from verticals.saas_premium.kpi_definitions import SAAS_KPIS
            return SAAS_KPIS
        except ImportError:
            return {}
    from verticals.dc2_s.kpi_definitions import DC2S_KPIS
    return DC2S_KPIS


def get_playbook_config(vertical: str):
    """Return (PLAYBOOK_CONFIG, should_trigger_playbook) for a vertical."""
    if vertical in ('saas_premium', 'saas'):
        try:
            from verticals.saas_premium.vertical_config import PLAYBOOK_CONFIG, should_trigger_playbook
            return PLAYBOOK_CONFIG, should_trigger_playbook
        except ImportError:
            return {}, lambda *a, **kw: False
    from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG, should_trigger_playbook
    return PLAYBOOK_CONFIG, should_trigger_playbook


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def require_auth(customer_id: int, required_scope: str = 'read', _api_key: str = None):
    """Enforce API key auth for customer-level tools."""
    from mcp_server.auth import require_auth as _auth
    _auth(customer_id, required_scope, _api_key)


def require_account_auth(customer_id: int, account_id: int,
                         required_scope: str = 'read', _api_key: str = None):
    """Enforce API key auth + account-level restriction."""
    from mcp_server.auth import require_account_auth as _auth
    _auth(customer_id, account_id, required_scope, _api_key)


# ---------------------------------------------------------------------------
# Context graph gate
# ---------------------------------------------------------------------------
def check_context_graph(customer_id: int):
    """Raise ToolError if context graph is not enabled for this customer.

    Checks:
      1. Global platform toggle (FeatureToggleManager)
      2. Per-customer DB toggle (models.FeatureToggle) — if the row exists
         and is explicitly disabled, blocks access.
    """
    from feature_toggles import feature_toggles, FeatureToggle as FTEnum

    # Check global toggle
    if not feature_toggles.is_enabled(FTEnum.CONTEXT_GRAPH):
        raise ToolError(
            f"Context graph is not enabled for customer {customer_id}. "
            "Enable via feature toggles or onboarding."
        )

    # Check per-customer DB toggle (already inside app context from caller)
    try:
        from models import FeatureToggle as FTModel
        toggle = FTModel.query.filter_by(
            customer_id=int(customer_id),
            feature_name='context_graph',
        ).first()
        # Only block if the toggle explicitly exists and is disabled
        if toggle is not None and not toggle.enabled:
            raise ToolError(
                f"Context graph is not enabled for customer {customer_id}. "
                "Enable via enable_features() or onboarding."
            )
    except ToolError:
        raise
    except Exception:
        pass  # DB toggle check unavailable — rely on global toggle


# ---------------------------------------------------------------------------
# Visualization helpers
# ---------------------------------------------------------------------------
def mermaid_safe(text: str) -> str:
    """Escape text for safe use inside Mermaid node labels."""
    if not text:
        return ''
    return (text.replace('"', "'")
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('&', '&amp;')
                .replace('\n', ' ')
                .replace('[', '(')
                .replace(']', ')'))


def format_revenue_short(value: float) -> str:
    """Format a revenue value as a short string like $1.2M or $450K."""
    if not value:
        return '$0'
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    else:
        return f"${value:.0f}"


# ---------------------------------------------------------------------------
# CSV helper
# ---------------------------------------------------------------------------
def csv_string(headers: list, rows: list) -> str:
    """Build a CSV string from headers and list-of-dict rows."""
    import csv
    import io
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# MCP server runner helper
# ---------------------------------------------------------------------------
def run_server(mcp_instance, default_port: int = 8001):
    """Run an MCP server in stdio or HTTP mode based on sys.argv."""
    transport = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "http":
        os.environ["MCP_TRANSPORT"] = "http"
        mcp_instance.run(transport="streamable-http", host="0.0.0.0", port=default_port)
    else:
        mcp_instance.run(transport="stdio")
