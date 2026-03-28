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


# ---------------------------------------------------------------------------
# Server-level API key (env var — super-admin / backward-compat)
# ---------------------------------------------------------------------------
MCP_SERVER_API_KEY = os.environ.get("MCP_SERVER_API_KEY", "")

# ---------------------------------------------------------------------------
# Auth toggle — set MCP_AUTH_REQUIRED=true to enforce API key auth.
# Default: false (open access, no key needed for any tool).
# ---------------------------------------------------------------------------
MCP_AUTH_REQUIRED = os.environ.get("MCP_AUTH_REQUIRED", "false").lower() in ("true", "1", "yes")


# ---------------------------------------------------------------------------
# Onboarding tools — frictionless auth (no API key required)
# ---------------------------------------------------------------------------
# These 13 tools are open for prospects. They let an AI assistant walk a
# prospect through discovery, customer creation, data upload, and
# onboarding finalization without needing a pre-existing API key.
#
# The create_customer tool auto-generates an API key that the prospect
# can later use for the intelligence tools (Groups 1-5).
# ---------------------------------------------------------------------------
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
}

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

    # In stdio mode, auth is implicit
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
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
    # Fallback: env vars
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

    return None


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
    """
    if not raw_key:
        return None
    try:
        from api_key_service import validate_api_key as db_validate
        return db_validate(raw_key)
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
        # In stdio mode, auth is implicit (local process is trusted)
        transport = os.environ.get("MCP_TRANSPORT", "stdio")
        if transport == "stdio":
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

        # In stdio mode, this decorator is a no-op
        transport = os.environ.get("MCP_TRANSPORT", "stdio")
        if transport == "stdio":
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
