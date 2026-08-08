"""
Spec-faithful, self-contained rebuild of Module 07 (Agent / MCP Tool Layer)
from SPEC.md ALONE. No real fastmcp / Flask / DB — tiny fakes stand in for the
platform so the spec's *logic and internal consistency* can be exercised.

Everything here follows the SPEC Build Prompt (six pieces) literally. Where the
Build Prompt leaves a helper undefined (e.g. `run_server`, `load_system_prompt`)
we implement "the most natural reading a competent engineer would choose" and
mark it, because that is exactly where the spec's defects hide.

Python 3.9 compatible.
"""
from __future__ import annotations

import os
import sys
import time
import logging
import contextvars
from typing import Optional, List, Dict, Any


# ---------------------------------------------------------------------------
# Tiny fake fastmcp  (FastMCP + @mcp.tool -> FunctionTool with .fn)
# ---------------------------------------------------------------------------
class ToolError(Exception):
    """Stand-in for fastmcp.exceptions.ToolError."""


class FunctionTool:
    """A @mcp.tool-decorated function is a FunctionTool WRAPPER, not the fn.

    Per Gotcha 2, calling the wrapper is NOT calling the underlying function.
    We model that faithfully: __call__ does not run fn (raises), .fn reaches it.
    """

    def __init__(self, fn, name):
        self.fn = fn
        self.name = name
        self.__name__ = getattr(fn, "__name__", name)
        self.__doc__ = getattr(fn, "__doc__", None)

    def __call__(self, *args, **kwargs):
        raise TypeError(
            "FunctionTool is not directly callable; call the _impl or use .fn "
            "(Gotcha 2)."
        )


class _ToolManager:
    def __init__(self):
        self._tools: Dict[str, FunctionTool] = {}


class FastMCP:
    def __init__(self, name, instructions=None):
        self.name = name
        self.instructions = instructions
        self._tool_manager = _ToolManager()

    def tool(self, fn=None, **kwargs):
        def deco(f):
            ft = FunctionTool(f, f.__name__)
            self._tool_manager._tools[f.__name__] = ft
            return ft
        if fn is not None and callable(fn):
            return deco(fn)
        return deco


# ---------------------------------------------------------------------------
# Piece 1 — server instance + feature gate
# ---------------------------------------------------------------------------
def load_system_prompt() -> str:
    # SPEC references load_system_prompt() (pieces 1 & 5) but never defines it.
    # "Most natural reading": return the client system-prompt markdown.
    return "# CS Pulse\nAgent tool layer."


mcp = FastMCP("CS Pulse", instructions=load_system_prompt())


# ---- fake feature toggles (Module 01 owns storage; we only read MCP_SERVER) --
class FeatureToggle:
    MCP_SERVER = "MCP_SERVER"


class _FeatureToggles:
    def __init__(self):
        self._state = {FeatureToggle.MCP_SERVER: True}

    def is_enabled(self, name) -> bool:
        return bool(self._state.get(name, False))


feature_toggles = _FeatureToggles()


def check_mcp_enabled():
    # Executable gate, not a comment: raises when the server toggle is off.
    if not feature_toggles.is_enabled(FeatureToggle.MCP_SERVER):
        raise ToolError("MCP Server is disabled. Enable via FEATURE_MCP_SERVER=true")


# ---- minimal Flask-app stand-in for DB context (piece 1) --------------------
class _FakeAppContext:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeApp:
    def app_context(self):
        return _FakeAppContext()


_flask_app = None


def get_flask_app():
    global _flask_app
    if _flask_app is not None:
        return _flask_app
    # Spec requires DATABASE_URL; keep faithful but tolerant for the harness.
    url = os.environ.get("SQLALCHEMY_DATABASE_URI") or os.environ.get("DATABASE_URL")
    if not url:
        # Spec raises here; harness sets a dummy URL so tools can run.
        raise ToolError("DATABASE_URL environment variable is required")
    _flask_app = _FakeApp()
    return _flask_app


# ---------------------------------------------------------------------------
# Fake Module 01 data model:  Account + CustomerApiKey + validate_api_key
# (schema owned by Module 01; this module consumes it.)
# ---------------------------------------------------------------------------
class Account:
    _store: List["Account"] = []

    def __init__(self, account_id, customer_id):
        self.account_id = int(account_id)
        self.customer_id = int(customer_id)

    # crude .query.filter_by(...).first() shim keyed on BOTH ids
    class _Query:
        def filter_by(self, **kw):
            self._kw = kw
            return self

        def first(self):
            for a in Account._store:
                if all(getattr(a, k) == v for k, v in self._kw.items()):
                    return a
            return None

    query = _Query()

    @classmethod
    def add(cls, account_id, customer_id):
        acct = cls(account_id, customer_id)
        cls._store.append(acct)
        return acct

    @classmethod
    def reset(cls):
        cls._store = []


import hashlib


class CustomerApiKey:
    """Fake in-memory CustomerApiKey record (schema owned by Module 01)."""

    _store: List["CustomerApiKey"] = []

    def __init__(self, raw_key, customer_id, scopes=None,
                 allowed_account_ids=None, expires_at=None):
        self.key_prefix = raw_key[:8]
        self.key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        self.customer_id = int(customer_id)
        self.scopes = scopes  # NULL/empty -> ["read"] handled in check_scope
        self.allowed_account_ids = allowed_account_ids  # NULL => ALL
        self.expires_at = expires_at  # NULL => never expires (epoch float or None)
        self.last_used_at = None
        self.last_used_ip = None

    def has_account_access(self, account_id) -> bool:
        # NULL-safe (mirrors module-level has_account_access)
        if self.allowed_account_ids is None:
            return True
        return int(account_id) in self.allowed_account_ids

    @classmethod
    def add(cls, raw_key, customer_id, **kw):
        rec = cls(raw_key, customer_id, **kw)
        cls._store.append(rec)
        return rec

    @classmethod
    def reset(cls):
        cls._store = []


def module01_validate_api_key(raw_key) -> Optional[CustomerApiKey]:
    """Module 01's validator: prefix lookup -> hash compare -> expiry check.

    NOTE (spec finding): this expiry logic lives in Module 01, NOT in the
    Build Prompt of Module 07. Restated here only so the harness can run.
    """
    if not raw_key:
        return None
    prefix = raw_key[:8]
    h = hashlib.sha256(raw_key.encode()).hexdigest()
    for rec in CustomerApiKey._store:
        if rec.key_prefix == prefix and rec.key_hash == h:
            # expiry check: NULL => never expires
            if rec.expires_at is not None and rec.expires_at < time.time():
                return None
            return rec
    return None


# ---------------------------------------------------------------------------
# Piece 3 — the auth core
# ---------------------------------------------------------------------------
_current_api_key_var = contextvars.ContextVar("_current_api_key", default="")
_current_session_id_var = contextvars.ContextVar("_current_session_id", default="")
_session_api_keys: dict = {}  # session_id -> raw key

# NOTE (spec finding #4): these two are captured at IMPORT time, per the Build
# Prompt pseudocode. A test that sets the env var AFTER import does not change
# them. MCP_TRANSPORT (below) is read LIVE in every enforcer.
MCP_SERVER_API_KEY = os.environ.get("MCP_SERVER_API_KEY", "")
MCP_AUTH_REQUIRED = os.environ.get("MCP_AUTH_REQUIRED", "true").lower() in (
    "true", "1", "yes")
if not MCP_AUTH_REQUIRED:
    logging.getLogger(__name__).critical(
        "MCP_AUTH_REQUIRED=false — API key enforcement DISABLED for ALL tools")


def extract_api_key():
    k = _current_api_key_var.get("")
    if k:
        return k
    sid = _current_session_id_var.get("")
    if sid and sid in _session_api_keys:
        return _session_api_keys[sid]
    if _session_api_keys:  # <-- "last session key" fallback (see FINDINGS #2)
        return list(_session_api_keys.values())[-1]
    return os.environ.get("CS_PULSE_API_KEY", "") or None


def validate_server_key(raw):
    return bool(MCP_SERVER_API_KEY) and raw == MCP_SERVER_API_KEY


def validate_customer_key(raw):
    if not raw:
        return None
    return module01_validate_api_key(raw)


def check_scope(key_record, required) -> bool:
    scopes = key_record.scopes or ["read"]
    if "admin" in scopes:
        return True
    if required == "read" and "write" in scopes:
        return True
    return required in scopes


def has_account_access(key_record, account_id) -> bool:
    allowed = key_record.allowed_account_ids
    if allowed is None:  # NULL => ALL accounts (Gotcha 8)
        return True
    return int(account_id) in allowed


def resolve_key(customer_id, required_scope, api_key=None):
    if not MCP_AUTH_REQUIRED:
        return None
    if api_key is not None:
        raw = api_key
    else:
        if os.environ.get("MCP_TRANSPORT", "stdio") != "http":
            return None  # stdio trusted
        raw = extract_api_key()
    if not raw:
        raise ToolError("API key required. Pass Authorization: Bearer <key>.")
    kr = validate_customer_key(raw)
    if kr:
        if kr.customer_id != int(customer_id):
            raise ToolError(f"API key not authorized for customer {customer_id}.")
        if not check_scope(kr, required_scope):
            raise ToolError(f"API key lacks '{required_scope}' scope; has {kr.scopes}.")
        return kr
    if validate_server_key(raw):
        return None  # super-admin, cross-customer
    raise ToolError("Invalid or expired API key.")


def require_auth(customer_id, required_scope="read", api_key=None):
    resolve_key(customer_id, required_scope, api_key)


def require_account_auth(customer_id, account_id, required_scope="read", api_key=None):
    kr = resolve_key(customer_id, required_scope, api_key)
    if kr is None:
        return  # stdio or server key: unrestricted
    if not has_account_access(kr, account_id):
        raise ToolError(
            f"API key not authorized for account {account_id}; "
            f"restricted to {kr.allowed_account_ids}.")


def require_read_key(tool_name, api_key=None):
    if not MCP_AUTH_REQUIRED:
        return
    if os.environ.get("MCP_TRANSPORT", "stdio") != "http":
        return
    raw = api_key if api_key is not None else extract_api_key()
    if not raw:
        raise ToolError(f"API key required for '{tool_name}'.")
    if validate_customer_key(raw) or validate_server_key(raw):
        return
    raise ToolError("Invalid or expired API key.")


def require_cross_customer_auth(tool_name, api_key=None):
    if not MCP_AUTH_REQUIRED:
        return
    if os.environ.get("MCP_TRANSPORT", "stdio") != "http":
        return
    raw = api_key if api_key is not None else extract_api_key()
    if not raw:
        raise ToolError(f"'{tool_name}' requires a server-level key.")
    if validate_server_key(raw):
        return
    if validate_customer_key(raw):
        raise ToolError(
            f"'{tool_name}' is cross-customer; a customer-scoped key cannot "
            f"call it. Use a server-level key.")
    raise ToolError("Invalid or expired API key.")


def get_scoped_customer_id():
    raw = extract_api_key()
    if not raw:
        return None  # stdio / no key: caller decides
    if MCP_SERVER_API_KEY and raw == MCP_SERVER_API_KEY:
        return None  # super-admin
    kr = validate_customer_key(raw)
    if kr and kr.customer_id:
        return int(kr.customer_id)
    raise PermissionError("Invalid or revoked API key")  # NOT None


# ---------------------------------------------------------------------------
# Piece 4 — impl/tool separation, ownership, envelope
# ---------------------------------------------------------------------------
def validate_account_ownership(customer_id, account_id):
    acct = Account.query.filter_by(account_id=int(account_id),
                                   customer_id=int(customer_id)).first()
    if not acct:
        raise ToolError(f"Account {account_id} not found for customer {customer_id}")
    return acct


def envelope(scope, payload, arr_basis=None, arr_basis_value=None):
    assert scope in ("account", "portfolio", "platform", "node_traversal")
    out = {"scope": scope, **payload}
    if arr_basis is not None:
        out["arr_basis"] = arr_basis
        out["arr_basis_value"] = arr_basis_value
    return out


# fake Module 03 delegate
def module03_read_scores(account_id):
    return (82.0, {"P1": 80.0, "P2": 84.0}, "Healthy")


def _get_account_health_impl(customer_id, account_id, api_key=None):
    check_mcp_enabled()
    require_account_auth(customer_id, account_id, "read", api_key)
    with get_flask_app().app_context():
        validate_account_ownership(customer_id, account_id)
        health, pillars, status = module03_read_scores(account_id)
        return envelope("account", {
            "account_id": account_id, "health_score": round(health, 1),
            "status": status, "pillar_scores": pillars})


@mcp.tool
def get_account_health(customer_id: int, account_id: int) -> dict:
    """Health score + pillar breakdown for one account."""
    return _get_account_health_impl(customer_id, account_id)


# a representative portfolio (dollar-bearing) tool
def _get_portfolio_arr_impl(customer_id, api_key=None):
    check_mcp_enabled()
    require_auth(customer_id, "read", api_key)
    return envelope("portfolio", {"customer_id": customer_id, "total_arr": 10_000_000},
                    arr_basis="explicit", arr_basis_value=10_000_000)


@mcp.tool
def get_portfolio_arr(customer_id: int) -> dict:
    """Portfolio ARR rollup for a customer."""
    return _get_portfolio_arr_impl(customer_id)


# a representative write tool
def _run_wizard_impl(customer_id, api_key=None):
    check_mcp_enabled()
    require_auth(customer_id, "write", api_key)
    return envelope("portfolio", {"customer_id": customer_id, "wizard": "ran"})


@mcp.tool
def run_wizard(customer_id: int) -> dict:
    """Trigger a wizard (write scope)."""
    return _run_wizard_impl(customer_id)


# a no-tenant discovery tool
def _list_catalog_impl(api_key=None):
    check_mcp_enabled()
    require_read_key("list_catalog", api_key)
    cid = get_scoped_customer_id()
    return envelope("platform", {"scope_customer": cid, "tools": sorted(registered_tool_names())})


@mcp.tool
def list_catalog() -> dict:
    """List tools (discovery)."""
    return _list_catalog_impl()


# ---------------------------------------------------------------------------
# Piece 5 — registry as single source of truth + parity
# ---------------------------------------------------------------------------
def registered_tool_names() -> set:
    return set(mcp._tool_manager._tools.keys())


def platform_instructions() -> dict:
    require_read_key("get_platform_instructions")
    return {"instructions": load_system_prompt(),
            "tool_count": len(registered_tool_names())}


def assert_registry_parity(secondary_names: set):
    live = registered_tool_names()
    missing, extra = live - secondary_names, secondary_names - live
    if missing or extra:
        raise AssertionError(
            f"registry drift: missing={sorted(missing)} extra={sorted(extra)}")


# ---------------------------------------------------------------------------
# Piece 2 — registration + dual-instance fix
# ---------------------------------------------------------------------------
TOOL_MODULES = ["cs_pulse_intelligence", "cs_pulse_revenue",
                "cs_pulse_onboarding", "cs_pulse_admin", "cs_pulse_predictor",
                "cs_pulse_executive", "cs_pulse_integrations",
                "cs_pulse_onboarding_agent"]


def register_tool_modules():
    # In this self-contained harness the tools above are already defined in this
    # file (import side-effect equivalent). Real spec: __import__(name) each.
    for name in TOOL_MODULES:
        try:
            __import__(name)
        except ImportError:
            pass  # harness: tool modules are inline, not separate files


# ---------------------------------------------------------------------------
# Piece 6 — HTTP Bearer middleware
# ---------------------------------------------------------------------------
class BearerAuthMiddleware:
    def __init__(self, app, allow_query_param=False):
        self.app = app
        self.allow_query_param = allow_query_param

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            sid = headers.get(b"mcp-session-id", b"").decode()
            auth = headers.get(b"authorization", b"").decode()
            token = ""
            if auth.startswith("Bearer "):
                token = auth[7:].strip()
                if sid:
                    _session_api_keys[sid] = token
            elif sid and sid in _session_api_keys:
                token = _session_api_keys[sid]
            if not token and self.allow_query_param:
                from urllib.parse import parse_qs
                qs = parse_qs(scope.get("query_string", b"").decode())
                token = (qs.get("api_key", [""])[0] or qs.get("token", [""])[0]).strip()
                if token and sid:
                    _session_api_keys[sid] = token
            if token:
                t = _current_api_key_var.set(token)
                s = _current_session_id_var.set(sid) if sid else None
                try:
                    await self.app(scope, receive, send)
                finally:
                    _current_api_key_var.reset(t)
                    if s:
                        _current_session_id_var.reset(s)
                return
        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# run_server + __main__ entrypoint  (UNDEFINED in the Build Prompt; natural impl)
# ---------------------------------------------------------------------------
def run_server(transport="stdio", set_env_naively=False):
    """The Build Prompt references run_server(transport=...) but NEVER defines
    it, and its __main__ block NEVER sets os.environ['MCP_TRANSPORT'].

    This is the "most natural reading" a competent engineer writes from the
    Build Prompt alone: start the requested transport. Nothing tells them to
    also set the env var the enforcers gate on. See FINDINGS #1.
    """
    # (In real life this would call mcp.run(transport=...).) We do not serve.
    return {"served_transport": transport,
            "mcp_transport_env": os.environ.get("MCP_TRANSPORT", "stdio")}


def entrypoint(argv):
    """Faithful replication of the SPEC's `if __name__ == '__main__'` block."""
    # sys.modules aliasing fix would go here in the real file.
    register_tool_modules()
    transport = argv[1] if len(argv) > 1 else "stdio"
    return run_server(transport=transport)
