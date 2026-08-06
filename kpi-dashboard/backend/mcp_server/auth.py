"""
MCP Server Authentication — API key validation for HTTP transport.

For stdio transport (Claude Desktop, Claude Code), auth is implicit (local process).
For Streamable HTTP transport (Copilot Studio, ChatGPT), Bearer token auth is required.

TWO-TIER AUTH MODEL:
  1. Server-level key (MCP_SERVER_API_KEY env var) — super-admin access to all customers
  2. Customer-scoped keys (DB-backed, csp_* format) — per-customer access with scopes

FRICTIONLESS AUTH MODEL:
  Onboarding tools (ONBOARDING_TOOLS) require NO API key. They are open for
  prospects evaluating the platform via an AI assistant. All other intelligence
  tools (Groups 1-5, tools 1-21) require a valid API key over HTTP.

SCOPE HIERARCHY:
  'read'  — intelligence/read tools (list_accounts, get_account_health, etc.)
  'write' — read + data ingestion (upload_csv, process_data, configure_customer_kpis)
  'admin' — write + customer management (all tools)
"""

import os
import logging
import contextvars
from functools import wraps
from typing import Optional

logger = logging.getLogger(__name__)

# Request-scoped API key storage (set by ASGI middleware, read by tool functions)
_current_api_key_var: contextvars.ContextVar[str] = contextvars.ContextVar('_current_api_key', default='')

# Session-scoped API key cache — survives across async tasks within the same MCP session.
# FastMCP may spawn tool execution in a new asyncio.Task where contextvars don't propagate.
# Key: mcp-session-id (str), Value: Bearer token (str)
_session_api_keys: dict = {}
_current_session_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('_current_session_id', default='')


# ---------------------------------------------------------------------------
# Server-level API key (env var — super-admin / backward-compat)
# ---------------------------------------------------------------------------
MCP_SERVER_API_KEY = os.environ.get("MCP_SERVER_API_KEY", "")

# ---------------------------------------------------------------------------
# Auth toggle — set MCP_AUTH_REQUIRED=false to disable API key enforcement.
# Default: true (production-safe). Onboarding tools are exempt (ONBOARDING_TOOLS set).
# ---------------------------------------------------------------------------
MCP_AUTH_REQUIRED = os.environ.get("MCP_AUTH_REQUIRED", "true").lower() in ("true", "1", "yes")

if not MCP_AUTH_REQUIRED:
    import logging as _auth_log
    _auth_log.getLogger(__name__).critical(
        "⚠️  MCP_AUTH_REQUIRED=false — API key enforcement DISABLED. "
        "All tools accessible without authentication. "
        "Set MCP_AUTH_REQUIRED=true for production."
    )


# ---------------------------------------------------------------------------
# Onboarding tools — frictionless auth (no API key required)
# ---------------------------------------------------------------------------
# Canonical set: onboarding_tool_registry.py (15 frictionless tools).
from onboarding_tool_registry import ONBOARDING_TOOLS

# Write-scope tools — require 'write' scope on the API key
WRITE_TOOLS = {
    'upload_csv',
    'process_data',
    'configure_customer_kpis',
    'enable_features',
    'trigger_wizard',
    'complete_onboarding',
    'validate_csv',
}


def is_onboarding_tool(name: str) -> bool:
    """Return True if the tool name is in the frictionless onboarding set."""
    return name in ONBOARDING_TOOLS


def is_write_tool(name: str) -> bool:
    """Return True if the tool requires write scope."""
    return name in WRITE_TOOLS


def require_auth_if_key_present(tool_name: str, customer_id: int = None):
    """Enforce scope validation on onboarding tools IF an API key is present.

    Frictionless model: onboarding tools require NO key for prospects.
    BUT if a key IS present (e.g. a partner calling upload_csv), we still
    validate it — ensuring scope and customer isolation.

    This closes the security gap where a partner could call onboarding tools
    with an invalid or mismatched key and bypass scope checks.

    Args:
        tool_name: The MCP tool being called.
        customer_id: The customer_id in the request (may be None for
                     discovery tools like list_verticals).

    Returns:
        The key_record if a key was present and validated, None otherwise.

    Raises:
        ToolError if a key IS present but fails validation.
    """
    from fastmcp.exceptions import ToolError

    # Non-HTTP transports (stdio, SSE, etc.) are trusted — local process.
    # Only enforce auth when MCP_TRANSPORT is explicitly "http" (set by __main__).
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport != "http":
        return None

    # Check if a key was provided
    raw_key = extract_api_key()
    if not raw_key:
        # No key → prospect flow, allow (existing frictionless behavior)
        return None

    # Key IS present → validate it even for onboarding tools
    key_record = validate_customer_key(raw_key)

    # Also check server-level key
    if not key_record and validate_server_key(raw_key):
        return None  # Server key = super-admin, allow everything

    if not key_record:
        raise ToolError(
            "Invalid or expired API key provided. "
            "Onboarding tools don't require a key — remove the Authorization "
            "header to use the frictionless flow, or provide a valid key."
        )

    # Key is valid — enforce customer isolation if customer_id specified
    if customer_id is not None and key_record.customer_id != int(customer_id):
        raise ToolError(
            f"API key does not have access to customer {customer_id}. "
            f"This key is scoped to a different customer."
        )

    # Enforce scope: onboarding write tools need 'write' scope
    if is_write_tool(tool_name):
        if not check_scope(key_record, 'write'):
            raise ToolError(
                f"API key lacks required 'write' scope for tool '{tool_name}'. "
                f"Current scopes: {key_record.scopes}."
            )

    return key_record


# ---------------------------------------------------------------------------
# Key extraction
# ---------------------------------------------------------------------------
def extract_api_key() -> Optional[str]:
    """Extract API key from the current transport context.

    Priority:
      1. contextvars _current_api_key_var (set by ASGI middleware per-request)
      2. _MCP_CURRENT_API_KEY env var (legacy fallback)
      3. CS_PULSE_API_KEY env var (stdio transport / testing)
    """
    # Primary: request-scoped context var (set by BearerAuthMiddleware)
    key = _current_api_key_var.get('')
    if key:
        return key
    # Fallback 1: session-scoped cache (for async task propagation)
    session_id = _current_session_id_var.get('')
    if session_id and session_id in _session_api_keys:
        logger.debug("extract_api_key: found key via session cache (session_id=%s)", session_id[:8])
        return _session_api_keys[session_id]
    # Fallback 2: check ALL session keys (last resort — only 1 session typically active)
    if _session_api_keys:
        logger.debug("extract_api_key: using last session key (sessions=%d)", len(_session_api_keys))
        return list(_session_api_keys.values())[-1]
    logger.debug("extract_api_key: no key found (contextvar=%r, sessions=%d)", key, len(_session_api_keys))
    # Fallback 3: env vars
    key = os.environ.get("_MCP_CURRENT_API_KEY", "")
    if not key:
        key = os.environ.get("CS_PULSE_API_KEY", "")
    return key or None


# ---------------------------------------------------------------------------
# Scoped customer_id extraction (for tenant isolation on unscoped tools)
# ---------------------------------------------------------------------------
def get_scoped_customer_id() -> Optional[int]:
    """Return the customer_id this key is scoped to, or None for server/stdio keys.

    Used by tools like list_customers and get_platform_instructions to
    restrict results to only the customer this API key belongs to.
    If no key or server key → returns None (show all customers).
    If customer-scoped key → returns that customer_id.
    """
    raw_key = extract_api_key()
    if not raw_key:
        return None  # stdio or no key

    # Check if it's the server-level key (super-admin sees all)
    if MCP_SERVER_API_KEY and raw_key == MCP_SERVER_API_KEY:
        return None

    # Try customer-scoped key
    key_record = validate_customer_key(raw_key)
    if key_record and key_record.customer_id:
        return int(key_record.customer_id)

    # Key was present but invalid (revoked, expired, or not found)
    # Raise error instead of returning None (which would mean "show all")
    logger.warning("API key present but invalid/revoked — blocking request")
    raise PermissionError("Invalid or revoked API key")


# ---------------------------------------------------------------------------
# Server-level key validation (backward-compat, super-admin)
# ---------------------------------------------------------------------------
def validate_server_key(api_key: str) -> bool:
    """Validate an API key against the configured server-level key."""
    if not MCP_SERVER_API_KEY:
        return False
    return api_key == MCP_SERVER_API_KEY


# Legacy alias
validate_api_key = validate_server_key


# ---------------------------------------------------------------------------
# Customer-scoped key validation (DB-backed)
# ---------------------------------------------------------------------------
def validate_customer_key(raw_key: str):
    """Validate a customer API key against the customer_api_keys DB table.

    Returns the CustomerApiKey record if valid, None otherwise.
    Uses api_key_service.validate_api_key() which does:
      - Prefix-based DB lookup (indexed)
      - SHA-256 hash verification
      - Expiry check
      - Usage tracking (last_used_at, last_used_ip)

    NOTE: Ensures Flask app context for DB access — MCP tools call this
    BEFORE their own `with app.app_context():` block.
    """
    if not raw_key:
        return None
    try:
        from api_key_service import validate_api_key as db_validate

        # Try direct call first (works if already in app context)
        try:
            return db_validate(raw_key)
        except RuntimeError:
            pass  # "Working outside application context" — create one

        # MCP tools call _require_auth before entering app context.
        # Create a minimal Flask app context for the DB lookup.
        try:
            from mcp_server.cs_pulse_mcp_server import _get_flask_app
            app = _get_flask_app()
            with app.app_context():
                return db_validate(raw_key)
        except Exception as ctx_err:
            logger.warning("Customer key validation (app context fallback): %s", ctx_err)
            return None

    except Exception as e:
        logger.warning("Customer key validation failed: %s", e)
        return None


def check_scope(key_record, required_scope: str) -> bool:
    """Check if a key record has the required scope.

    Scope hierarchy:
      admin ⊃ write ⊃ read
    """
    scopes = key_record.scopes if key_record.scopes else ['read']

    # Admin scope includes everything
    if 'admin' in scopes:
        return True

    # Write scope includes read
    if required_scope == 'read' and 'write' in scopes:
        return True

    return required_scope in scopes


# ---------------------------------------------------------------------------
# Unified auth enforcement (called by MCP tools)
# ---------------------------------------------------------------------------
def _resolve_key(customer_id: int, required_scope: str, _api_key=None):
    """Internal: validate key + customer + scope. Returns key_record or None (server key).

    Raises ToolError on any auth failure.
    """
    from fastmcp.exceptions import ToolError

    # Auth toggle: if disabled, skip all auth
    if not MCP_AUTH_REQUIRED:
        return None

    # Determine the raw key
    if _api_key is not None:
        raw_key = _api_key
    else:
        # Non-HTTP transports (stdio, SSE, etc.) are trusted ��� local process.
        # Only enforce auth when MCP_TRANSPORT is explicitly "http" (set by
        # the __main__ HTTP startup path in cs_pulse_mcp_server.py).
        transport = os.environ.get("MCP_TRANSPORT", "stdio")
        if transport != "http":
            return None  # Trusted — no key_record to return

        raw_key = extract_api_key()

    if not raw_key:
        raise ToolError(
            "API key required. Pass via Authorization: Bearer <key> header. "
            "You received a key when your customer was created via create_customer(). "
            "If you lost it, generate a new one from the Admin UI."
        )

    # Try customer-scoped key first (DB lookup)
    key_record = validate_customer_key(raw_key)
    if key_record:
        # Tenant isolation: key must belong to the requested customer
        if key_record.customer_id != int(customer_id):
            raise ToolError(
                f"API key does not have access to customer {customer_id}. "
                f"This key is scoped to a different customer."
            )

        # Scope enforcement
        if not check_scope(key_record, required_scope):
            raise ToolError(
                f"API key lacks required '{required_scope}' scope. "
                f"Current scopes: {key_record.scopes}. "
                f"Contact your admin to get a key with '{required_scope}' access."
            )

        logger.debug(
            "Auth OK: key_id=%s customer=%s scope=%s",
            key_record.id, key_record.customer_id, required_scope,
        )
        return key_record

    # Fall back to server-level key (super-admin — cross-customer access)
    if validate_server_key(raw_key):
        logger.debug("Auth OK: server key (super-admin) for customer=%s", customer_id)
        return None  # Server key — no account restrictions

    raise ToolError(
        "Invalid or expired API key. Check your key and try again. "
        "If you lost your key, generate a new one from the Admin UI."
    )


def require_auth(customer_id: int, required_scope: str = 'read',
                 _api_key: str = None):
    """Enforce customer API key auth for a tool call (customer-level).

    Checks: valid key → customer_id match → scope.
    For stdio transport: no-op (local process trusted).
    """
    _resolve_key(customer_id, required_scope, _api_key)


def require_read_key(tool_name: str, _api_key: str = None):
    """Enforce that *some* valid API key (customer-scoped or server-level) is
    present for a non-onboarding tool that has no customer_id parameter
    (discovery/list tools: get_platform_instructions, list_customers,
    get_kpi_catalog).

    These tools apply their own tenant filtering via get_scoped_customer_id();
    this check only closes the gap where an HTTP caller with NO key at all
    could enumerate cross-tenant metadata. stdio transport: no-op.

    Added Aug 4 2026 (audit C-10 remediation).
    """
    from fastmcp.exceptions import ToolError

    if not MCP_AUTH_REQUIRED:
        return
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport != "http":
        return

    raw_key = _api_key if _api_key is not None else extract_api_key()
    if not raw_key:
        raise ToolError(
            f"API key required for '{tool_name}'. Pass via "
            "Authorization: Bearer <key> header."
        )
    if validate_customer_key(raw_key) or validate_server_key(raw_key):
        return
    raise ToolError(
        "Invalid or expired API key. Check your key and try again."
    )


def require_cross_customer_auth(tool_name: str, _api_key: str = None):
    """Enforce SERVER-LEVEL key auth for tools that read across customers
    (portfolio tools: list_portfolio_customers,
    get_portfolio_cross_customer_comparison).

    Customer-scoped keys are explicitly rejected — a tenant key must never
    enumerate other tenants, regardless of scope. stdio transport: no-op.

    Added Aug 4 2026 (audit C-10 remediation).
    """
    from fastmcp.exceptions import ToolError

    if not MCP_AUTH_REQUIRED:
        return
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport != "http":
        return

    raw_key = _api_key if _api_key is not None else extract_api_key()
    if not raw_key:
        raise ToolError(
            f"'{tool_name}' is a cross-customer tool and requires a "
            "server-level API key over HTTP."
        )
    if validate_server_key(raw_key):
        return
    if validate_customer_key(raw_key):
        raise ToolError(
            f"'{tool_name}' reads across customers and cannot be called "
            "with a customer-scoped key. A server-level key is required."
        )
    raise ToolError(
        "Invalid or expired API key. Check your key and try again."
    )


def require_account_auth(customer_id: int, account_id: int,
                         required_scope: str = 'read',
                         _api_key: str = None):
    """Enforce customer + account-level API key auth for a tool call.

    Same as require_auth, plus checks allowed_account_ids restriction.

    If a key has allowed_account_ids set (e.g. [354001, 354003]),
    the tool is ONLY allowed to access those accounts. NULL = all accounts.

    This is the partner isolation layer: a partner managing P4 for 3 accounts
    can only read/write those 3 accounts, not the full portfolio.

    Args:
        customer_id: The customer (tenant) ID.
        account_id: The specific account being accessed.
        required_scope: 'read' or 'write'.
        _api_key: Explicit key for testing.

    Raises:
        ToolError if auth fails or account not in allowed list.
    """
    from fastmcp.exceptions import ToolError

    key_record = _resolve_key(customer_id, required_scope, _api_key)

    if key_record is None:
        return  # stdio or server key — no account restrictions

    # Account-level restriction
    if not key_record.has_account_access(int(account_id)):
        raise ToolError(
            f"API key does not have access to account {account_id}. "
            f"This key is restricted to accounts: {key_record.allowed_account_ids}."
        )


# ---------------------------------------------------------------------------
# Legacy decorator (kept for backward-compat, but prefer require_auth())
# ---------------------------------------------------------------------------
def require_api_key(func):
    """Decorator to require API key for HTTP-transported tool calls.

    Only enforced when MCP_SERVER_API_KEY is set. If not set, all
    HTTP requests are rejected (stdio is always allowed).

    ONBOARDING TOOLS: Still frictionless (no key required), BUT if a key
    IS present, it is validated for scope and customer isolation via
    require_auth_if_key_present(). This closes the gap where a partner
    could bypass scope checks on onboarding tools.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Auth toggle: if disabled, skip all auth
        if not MCP_AUTH_REQUIRED:
            return func(*args, **kwargs)

        # Non-HTTP transports are trusted — decorator is a no-op
        transport = os.environ.get("MCP_TRANSPORT", "stdio")
        if transport != "http":
            return func(*args, **kwargs)

        # Onboarding tools: frictionless, but validate if key IS present
        if is_onboarding_tool(func.__name__):
            # Extract customer_id from kwargs if available
            cid = kwargs.get('customer_id')
            require_auth_if_key_present(func.__name__, cid)
            return func(*args, **kwargs)

        # For HTTP non-onboarding tools, check the API key
        api_key = os.environ.get("_MCP_CURRENT_API_KEY", "")
        if not validate_api_key(api_key):
            raise PermissionError("Invalid or missing MCP API key")
        return func(*args, **kwargs)

    return wrapper
