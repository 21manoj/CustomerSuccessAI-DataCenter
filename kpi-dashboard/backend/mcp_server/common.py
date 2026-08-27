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


# ---------------------------------------------------------------------------
# Pillar labels (vertical-aware)
# ---------------------------------------------------------------------------
def get_pillar_labels(vertical: str = 'dc2_s') -> dict:
    """Return canonical pillar labels for a vertical.

    Resolves through the vertical registry so ANY vertical (JSON-catalog or
    Python-module) gets its own pillar display names. The registry already
    covers dc2_s and saas_premium via their JSON catalogs (see
    utils/vertical_registry.py), so the two vertical-specific import
    fallbacks that used to live here (one for saas_premium, one for dc2_s)
    were dead in practice — cross-vertical import cleanup, Phase 5 of the
    vertical-registry fail-closed refactor, Aug 21 2026. Only the final
    vertical-agnostic literal dict remains, as a last resort for the case
    where the registry itself can't resolve ANY vertical (e.g. import
    failure) — it is intentionally not vertical-specific data, just an
    inert default.
    """
    try:
        from utils.vertical_registry import get_pillars
        pillars = get_pillars(vertical)
        if pillars:
            return {code: (p.get('name') or code) for code, p in pillars.items()}
    except Exception:
        pass
    return {
        'P1': 'Deployment Velocity', 'P2': 'Operational Stability',
        'P3': 'AI Workload Performance', 'P4': 'Channel & Partner Health',
        'P5': 'Expansion Readiness',
    }


# ---------------------------------------------------------------------------
# Health / score helpers (vertical-agnostic)
# ---------------------------------------------------------------------------
def get_precalculated_scores(account_id: int):
    """Read pre-calculated scores from the canonical account-health service.

    Returns (health_score, health_status, pillar_dict) or (None, None, None).
    Wave 1 Workstream A (Aug 4 2026): delegates to utils/account_health.py —
    was one of four independent copies of this read.
    """
    try:
        from utils.account_health import get_precalculated_scores_tuple
        return get_precalculated_scores_tuple(account_id)
    except Exception:
        return None, None, None


def get_trailing_kpi_values_generic(account_id: int) -> dict:
    """Read latest KPI values from KPIScore table. Returns {kpi_code: score}."""
    try:
        from models import KPIScore
        rows = KPIScore.query.filter_by(account_id=account_id) \
            .order_by(KPIScore.measurement_month.desc()).all()
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
    """Return the KPI definitions dict for a vertical.

    Routes through utils.vertical_registry.get_kpis so ANY vertical (JSON
    catalog or legacy Python module) gets its own KPI catalog, instead of
    the hardcoded saas_premium/dc2_s two-branch that used to silently
    serve DC2S_KPIS to every other vertical (e.g. datacenter_v1) — the
    same bug class already fixed the same day in
    cs_pulse_mcp_server.py::_get_kpi_definitions (Aug 21 2026
    vertical-coupling audit, commit b1232d97a; see also
    tests/test_ask_ai_helpers_kpi_definitions.py for the sibling fix's
    coverage). This is a real, live call site — wizards/wizard_c_weight_
    calibrator_db.py imports it directly for weight calibration.

    Raises ValueError for a vertical the registry can't resolve at all
    (no JSON catalog, no Python module) — matches the sibling function's
    fail-closed behavior rather than silently returning {} and letting
    callers iterate over nothing.
    """
    from utils.vertical_registry import get_kpis
    return get_kpis(vertical)


def get_playbook_config(vertical: str):
    """Return (PLAYBOOK_CONFIG, should_trigger_playbook) for a vertical.

    Genuinely vertical-specific: dc2_s and saas_premium each define their
    own playbook trigger logic in Python
    (verticals/{vertical}/vertical_config.py) and there is no generic /
    JSON-catalog equivalent yet (playbook_recommendations_api has the same
    gap — see backlog_vertical_registry_fail_closed_refactor). Explicitly
    gated per known vertical rather than falling through to dc2_s's config
    for every other vertical, which is what this function did before: any
    non-dc2_s/saas_premium customer (e.g. datacenter_v1) was silently
    served dc2_s's playbook definitions under its own vertical's name.
    """
    if vertical in ('saas_premium', 'saas'):
        try:
            from verticals.saas_premium.vertical_config import PLAYBOOK_CONFIG, should_trigger_playbook
            return PLAYBOOK_CONFIG, should_trigger_playbook
        except ImportError:
            return {}, lambda *a, **kw: False
    if vertical == 'dc2_s':
        from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG, should_trigger_playbook
        return PLAYBOOK_CONFIG, should_trigger_playbook
    if vertical == 'datacenter_v1':
        # datacenter_v1/vertical_config.py defines PLAYBOOK_CONFIG (PB-01
        # etc.) but has no should_trigger_playbook of its own yet — fall
        # back to a no-op trigger rather than fail the whole lookup (Aug 27
        # 2026, found live on customer 408: playbook-close was resolving
        # this correctly-named vertical, then silently getting {} back and
        # reporting 0 CSM hours for every execution).
        try:
            from verticals.datacenter_v1.vertical_config import PLAYBOOK_CONFIG
        except ImportError:
            return {}, lambda *a, **kw: False
        try:
            from verticals.datacenter_v1.vertical_config import should_trigger_playbook
        except ImportError:
            should_trigger_playbook = lambda *a, **kw: False
        return PLAYBOOK_CONFIG, should_trigger_playbook
    # No generic playbook-config equivalent exists yet for other
    # verticals (e.g. healthcare_provider, manufacturing_iot — no
    # vertical_config.py at all yet) — return a safe no-op rather than
    # crashing onboarding or silently borrowing dc2_s's playbooks.
    return {}, lambda *a, **kw: False


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
