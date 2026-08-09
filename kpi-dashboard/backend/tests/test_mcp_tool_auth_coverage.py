"""
MCP tool auth coverage — guard tests (Aug 4 2026, audit C-10 remediation).

The Aug 3 2026 E2E audit found 21 @mcp.tool functions with no auth call.
Remediation wired every tool to exactly one of:

  - require_auth / require_account_auth (via the _require_auth wrappers) —
    standard tenant-scoped tools
  - require_auth_if_key_present — the 15 frictionless ONBOARDING_TOOLS
    (intentionally keyless for prospect flows, but validate a key when one
    IS supplied)
  - require_read_key — non-onboarding discovery tools with no customer_id
    param (get_platform_instructions, list_customers, get_kpi_catalog)
  - require_cross_customer_auth — portfolio tools that read across tenants
    (server-level key only)

Test 1 is an AST sweep that enforces the invariant repo-wide, so a future
tool CANNOT ship without an auth call — the failure message names it.
Tests 2-3 unit-test the two helpers added in the remediation.

These tests import no Flask app and need no DB.
"""

import ast
import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
MCP_DIR = BACKEND / "mcp_server"

AUTH_CALL_NAMES = {
    "require_auth", "require_account_auth",
    "_require_auth", "_require_account_auth",
    "require_auth_if_key_present", "_require_auth_if_key_present",
    "require_read_key", "require_cross_customer_auth",
}


def _is_mcp_tool_decorator(d: ast.expr) -> bool:
    if isinstance(d, ast.Call):
        d = d.func
    return (
        isinstance(d, ast.Attribute)
        and isinstance(d.value, ast.Name)
        and d.value.id == "mcp"
        and d.attr == "tool"
    )


def _iter_mcp_tools():
    for path in sorted(MCP_DIR.glob("*.py")):
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if any(_is_mcp_tool_decorator(d) for d in node.decorator_list):
                yield path, node


def _called_names(node: ast.AST) -> set:
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            f = sub.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


def test_every_mcp_tool_calls_an_auth_function():
    """No @mcp.tool may ship without one of the four auth mechanisms."""
    missing = []
    tool_count = 0
    for path, node in _iter_mcp_tools():
        tool_count += 1
        if not (_called_names(node) & AUTH_CALL_NAMES):
            missing.append(f"{path.name}:{node.lineno} {node.name}")
    assert tool_count > 50, f"AST sweep looks broken — only {tool_count} tools found"
    assert not missing, (
        "MCP tools with NO auth call (add require_auth / "
        "require_auth_if_key_present / require_read_key / "
        "require_cross_customer_auth):\n  " + "\n  ".join(missing)
    )


def test_frictionless_tools_use_if_key_present_not_hard_auth():
    """Every ONBOARDING_TOOLS member defined in cs_pulse_onboarding.py must
    call require_auth_if_key_present (frictionless model) — EXCEPT
    clone_customer and download_customer_csv, which pre-date this pass with
    a deliberate hard _require_auth (they expose full tenant data)."""
    for p in (str(BACKEND), str(MCP_DIR)):
        if p not in sys.path:
            sys.path.insert(0, p)
    from onboarding_tool_registry import ONBOARDING_TOOLS

    hard_auth_ok = {"clone_customer", "download_customer_csv"}
    problems = []
    for path, node in _iter_mcp_tools():
        if node.name not in ONBOARDING_TOOLS or node.name in hard_auth_ok:
            continue
        calls = _called_names(node)
        if not calls & {"require_auth_if_key_present", "_require_auth_if_key_present"}:
            problems.append(f"{path.name}:{node.lineno} {node.name}")
    assert not problems, (
        "Frictionless onboarding tools missing require_auth_if_key_present:\n  "
        + "\n  ".join(problems)
    )


class _FakeKeyRecord:
    def __init__(self, customer_id=42, scopes=None):
        self.id = 1
        self.customer_id = customer_id
        self.scopes = scopes or ["read"]


@pytest.fixture
def http_transport(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.setenv("MCP_AUTH_REQUIRED", "true")
    for p in (str(BACKEND), str(MCP_DIR)):
        if p not in sys.path:
            sys.path.insert(0, p)
    import mcp_server.auth as auth
    monkeypatch.setattr(auth, "MCP_AUTH_REQUIRED", True)
    return auth


def test_require_read_key_rejects_missing_and_accepts_valid(http_transport, monkeypatch):
    auth = http_transport
    from fastmcp.exceptions import ToolError

    monkeypatch.setattr(auth, "extract_api_key", lambda: None)
    with pytest.raises(ToolError):
        auth.require_read_key("list_customers")

    # Valid customer key passes
    monkeypatch.setattr(auth, "extract_api_key", lambda: "csp_valid")
    monkeypatch.setattr(auth, "validate_customer_key", lambda k: _FakeKeyRecord())
    monkeypatch.setattr(auth, "validate_server_key", lambda k: False)
    auth.require_read_key("list_customers")  # no raise

    # Invalid key rejected
    monkeypatch.setattr(auth, "validate_customer_key", lambda k: None)
    with pytest.raises(ToolError):
        auth.require_read_key("list_customers")

    # stdio transport: no-op even with no key
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    monkeypatch.setattr(auth, "extract_api_key", lambda: None)
    auth.require_read_key("list_customers")  # no raise


def test_require_cross_customer_auth_rejects_customer_keys(http_transport, monkeypatch):
    auth = http_transport
    from fastmcp.exceptions import ToolError

    # No key -> rejected
    monkeypatch.setattr(auth, "extract_api_key", lambda: None)
    with pytest.raises(ToolError):
        auth.require_cross_customer_auth("list_portfolio_customers")

    # Customer-scoped key -> rejected (must not enumerate other tenants)
    monkeypatch.setattr(auth, "extract_api_key", lambda: "csp_tenant")
    monkeypatch.setattr(auth, "validate_server_key", lambda k: False)
    monkeypatch.setattr(auth, "validate_customer_key", lambda k: _FakeKeyRecord(scopes=["admin"]))
    with pytest.raises(ToolError, match="cross|server-level"):
        auth.require_cross_customer_auth("list_portfolio_customers")

    # Server key -> allowed
    monkeypatch.setattr(auth, "validate_server_key", lambda k: True)
    auth.require_cross_customer_auth("list_portfolio_customers")  # no raise


def test_extract_api_key_no_cross_session_inheritance(http_transport, monkeypatch):
    """A session-less HTTP caller must NEVER inherit another session's key.

    Regression for the cross-tenant leak found while validating Module 07:
    extract_api_key() had an identity-blind "last resort" fallback that
    returned `list(_session_api_keys.values())[-1]` whenever the contextvar
    and session-id lookups both missed. Once tenant B had authenticated over
    HTTP, an anonymous/session-less request (no Authorization header, empty
    session-id contextvar) received tenant B's key — auth passed as B.

    The fix removes that fallback: with no request identity, extract_api_key()
    must fall through to env vars only, then return None (fail closed).
    """
    auth = http_transport

    # Tenant B is authenticated and cached under its own session id.
    monkeypatch.setattr(auth, "_session_api_keys", {"session-B": "csp_tenant_B"})
    # This request has NO contextvar key and NO session id (anonymous caller).
    auth._current_api_key_var.set("")
    auth._current_session_id_var.set("")
    # No env-var keys either.
    monkeypatch.delenv("_MCP_CURRENT_API_KEY", raising=False)
    monkeypatch.delenv("CS_PULSE_API_KEY", raising=False)

    # Must resolve to no key, NOT tenant B's cached key.
    assert auth.extract_api_key() is None

    # And get_scoped_customer_id() must not scope this caller to tenant B.
    # With no key present it returns None (stdio/no-key semantics) rather
    # than the other tenant's customer_id.
    monkeypatch.setattr(
        auth, "validate_customer_key",
        lambda k: (_ for _ in ()).throw(
            AssertionError("validate_customer_key called with leaked key: %r" % k)
        ),
    )
    assert auth.get_scoped_customer_id() is None

    # Sanity: the request's OWN session id still resolves correctly.
    auth._current_session_id_var.set("session-B")
    assert auth.extract_api_key() == "csp_tenant_B"
