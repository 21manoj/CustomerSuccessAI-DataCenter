"""
Adversarial validation of Module 07 (Agent / MCP Tool Layer) from SPEC.md alone.

Two kinds of tests:
  * test_ac_*      — Acceptance Criteria that PASS (the spec logic is correct there).
  * test_defect_*  — each PROVES a real spec defect by executing the spec's literal
                     logic and showing the failure, then shows the corrected form
                     passing alongside.
"""
from __future__ import annotations

import os
import sys
import time
import logging
import importlib

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import impl  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Reset all process state and env between tests."""
    impl.Account.reset()
    impl.CustomerApiKey.reset()
    impl._session_api_keys.clear()
    impl._current_api_key_var.set("")
    impl._current_session_id_var.set("")
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    monkeypatch.delenv("CS_PULSE_API_KEY", raising=False)
    impl.MCP_AUTH_REQUIRED = True
    impl.MCP_SERVER_API_KEY = ""
    impl.feature_toggles._state[impl.FeatureToggle.MCP_SERVER] = True
    yield


def mkkey(raw, customer_id, scopes=None, allowed=None, expires_at=None):
    return impl.CustomerApiKey.add(raw, customer_id, scopes=scopes,
                                   allowed_account_ids=allowed, expires_at=expires_at)


# ===========================================================================
# ACCEPTANCE CRITERIA (expected to pass — the spec is right here)
# ===========================================================================
def test_ac_registration_count_derived():
    names = impl.registered_tool_names()
    assert len(names) > 0
    # tool_count in platform_instructions is derived, not a literal
    impl.MCP_SERVER_API_KEY = ""  # stdio path -> require_read_key no-op
    assert impl.platform_instructions()["tool_count"] == len(names)


def test_ac_impl_directly_callable_tool_is_not_fn():
    assert callable(impl._get_account_health_impl)
    impl.Account.add(1, 100)
    out = impl._get_account_health_impl(100, 1)
    assert out["scope"] == "account" and out["account_id"] == 1
    assert type(impl.get_account_health).__name__ == "FunctionTool"
    assert impl.get_account_health.fn.__name__ == "get_account_health"


def test_ac_envelope_scope_and_arr_basis():
    impl.Account.add(1, 100)
    acct = impl._get_account_health_impl(100, 1)
    assert acct["scope"] == "account"
    port = impl._get_portfolio_arr_impl(100)
    assert port["scope"] == "portfolio"
    assert port["arr_basis"] == "explicit" and port["arr_basis_value"] == 10_000_000
    with pytest.raises(AssertionError):
        impl.envelope("bogus", {})


def test_ac_tenant_isolation_ownership_independent_of_auth():
    # A owns acct1, B owns acct2; A asking for acct2 must raise on stdio (no auth)
    impl.Account.add(1, 100)  # customer A=100
    impl.Account.add(2, 200)  # customer B=200
    with pytest.raises(impl.ToolError):
        impl._get_account_health_impl(100, 2)


def test_ac_scope_hierarchy(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    rk = mkkey("readkey1_x", 100, scopes=["read"])
    wk = mkkey("writeky1_x", 100, scopes=["write"])
    ak = mkkey("adminky1_x", 100, scopes=["admin"])
    # read key: read ok, write raises
    impl.require_auth(100, "read", api_key="readkey1_x")
    with pytest.raises(impl.ToolError):
        impl.require_auth(100, "write", api_key="readkey1_x")
    # write key: both ok
    impl.require_auth(100, "read", api_key="writeky1_x")
    impl.require_auth(100, "write", api_key="writeky1_x")
    # admin: everything
    impl.require_auth(100, "write", api_key="adminky1_x")


def test_ac_customer_isolation_wrong_tenant(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    mkkey("custAkey_x", 100, scopes=["read"])
    with pytest.raises(impl.ToolError):
        impl.require_auth(200, "read", api_key="custAkey_x")


def test_ac_cross_customer_rejects_customer_key(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    impl.MCP_SERVER_API_KEY = "SERVER-SUPER"
    mkkey("custkey11_x", 100, scopes=["admin"])
    impl.require_cross_customer_auth("t", api_key="SERVER-SUPER")  # ok
    with pytest.raises(impl.ToolError):
        impl.require_cross_customer_auth("t", api_key="custkey11_x")  # valid cust key
    with pytest.raises(impl.ToolError):
        impl.require_cross_customer_auth("t", api_key=None)  # no key on http


def test_ac_get_scoped_customer_id_fail_closed(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    impl.MCP_SERVER_API_KEY = "SERVER-SUPER"
    # no key -> None
    assert impl.get_scoped_customer_id() is None
    # server key -> None
    impl._current_api_key_var.set("SERVER-SUPER")
    assert impl.get_scoped_customer_id() is None
    # valid customer key -> id
    impl._current_api_key_var.set("")
    mkkey("scopekey1_x", 100)
    impl._current_api_key_var.set("scopekey1_x")
    assert impl.get_scoped_customer_id() == 100
    # invalid key -> PermissionError, not None
    impl._current_api_key_var.set("not-a-real-key")
    with pytest.raises(PermissionError):
        impl.get_scoped_customer_id()


def test_ac_account_restriction_null_and_restricted(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    # NULL allowed_account_ids => ALL accounts
    mkkey("nullacct_x", 100, scopes=["read"], allowed=None)
    for aid in (1, 2, 99):
        impl.require_account_auth(100, aid, "read", api_key="nullacct_x")
    # restricted [1,3]
    mkkey("restrict1_x", 100, scopes=["read"], allowed=[1, 3])
    impl.require_account_auth(100, 1, "read", api_key="restrict1_x")
    impl.require_account_auth(100, 3, "read", api_key="restrict1_x")
    with pytest.raises(impl.ToolError):
        impl.require_account_auth(100, 2, "read", api_key="restrict1_x")


def test_ac_expiry_null_and_past():
    # NULL expires_at => never expires
    mkkey("neverexp_x", 100, expires_at=None)
    assert impl.validate_customer_key("neverexp_x") is not None
    # past expiry => invalid
    mkkey("pastexp1_x", 100, expires_at=time.time() - 100)
    assert impl.validate_customer_key("pastexp1_x") is None


def test_ac_stdio_trusted_http_enforced(monkeypatch):
    # stdio: no key is a no-op
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")
    impl.require_auth(100, "read")  # no raise
    # http: no key raises
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    with pytest.raises(impl.ToolError):
        impl.require_auth(100, "read")


def test_ac_async_task_session_fallback():
    # contextvar empty; token only in session cache -> extract still finds it
    impl._current_api_key_var.set("")
    impl._current_session_id_var.set("sid-1")
    impl._session_api_keys["sid-1"] = "tok-from-session"
    assert impl.extract_api_key() == "tok-from-session"


def test_ac_registry_parity():
    live = impl.registered_tool_names()
    impl.assert_registry_parity(set(live))  # ok
    with pytest.raises(AssertionError):
        impl.assert_registry_parity(set(live) - {next(iter(live))})  # missing
    with pytest.raises(AssertionError):
        impl.assert_registry_parity(set(live) | {"phantom_tool"})  # extra


def test_ac_feature_gate():
    impl.feature_toggles._state[impl.FeatureToggle.MCP_SERVER] = False
    impl.Account.add(1, 100)
    with pytest.raises(impl.ToolError):
        impl._get_account_health_impl(100, 1)


def test_ac_dual_instance_fix_and_bug():
    """Prove Gotcha 1 both ways with a fake module system."""
    # --- WITHOUT the alias: submodule 'from server import mcp' re-imports the
    #     file under its canonical name -> a SECOND FastMCP instance.
    running = impl.FastMCP("running")           # served instance (the __main__ one)
    canonical = impl.FastMCP("canonical")       # phantom second instance
    fake_sys = {"__main__": running}            # canonical name NOT aliased

    def import_server_mcp():
        # Python resolves 'from cs_pulse_mcp_server import mcp' via canonical name
        return fake_sys.get("cs_pulse_mcp_server", canonical)

    got = import_server_mcp()
    got.tool(lambda customer_id: {"ok": 1})     # register onto whatever we got
    assert got is not running                    # BUG: onto phantom
    assert len(running._tool_manager._tools) == 0  # served instance is empty

    # --- WITH the alias set BEFORE imports:
    fake_sys["cs_pulse_mcp_server"] = fake_sys["__main__"]  # the fix
    got2 = import_server_mcp()
    assert got2 is running                        # resolves to served instance
    got2.tool(lambda customer_id: {"ok": 2})
    assert len(running._tool_manager._tools) == 1  # tool visible to the server


# ===========================================================================
# DEFECT-PROVING TESTS
# ===========================================================================
def test_defect_1_http_entrypoint_never_sets_mcp_transport(monkeypatch):
    """DEFECT 1  (shape a + b + d) — SEVERE auth bypass.

    Spec section: Build Prompt piece 2 `if __name__ == '__main__'` block calls
    `run_server(transport=sys.argv[1] ...)` with "http" but NEVER executes
    `os.environ['MCP_TRANSPORT'] = 'http'`. `run_server` is referenced-but-
    undefined. Every enforcer (piece 3) gates the trusted-vs-enforced decision
    on `os.environ.get('MCP_TRANSPORT','stdio') != 'http'`. Gotcha 7's own fix
    text says set it "in the HTTP startup path (not left to the environment)" —
    but no pseudocode does. So the shipped entrypoint serves HTTP while the
    enforcers still take the trusted stdio path: auth is skipped for real HTTP
    traffic. Cite shape (a) contradiction with Gotcha 7 and shape (b)/(d): a
    MUST that lives only in prose, whose natural code impl reproduces the
    anti-pattern.
    """
    monkeypatch.delenv("MCP_TRANSPORT", raising=False)  # deployer forgot to set it
    result = impl.entrypoint(["server.py", "http"])

    # The server *believes* it is serving http ...
    assert result["served_transport"] == "http"
    # ... yet the env the enforcers read is still stdio:
    assert result["mcp_transport_env"] == "stdio"
    # PROOF of the leak: an unauthenticated HTTP request is treated as trusted.
    impl.require_auth(customer_id=999)  # NO key, NO raise -> auth bypassed
    assert os.environ.get("MCP_TRANSPORT", "stdio") != "http"

    # --- Corrected entrypoint (the SPEC fix): set the env in the startup path.
    def entrypoint_fixed(argv):
        impl.register_tool_modules()
        transport = argv[1] if len(argv) > 1 else "stdio"
        if transport == "http":
            os.environ["MCP_TRANSPORT"] = "http"   # <-- the missing line
        return impl.run_server(transport=transport)

    entrypoint_fixed(["server.py", "http"])
    assert os.environ["MCP_TRANSPORT"] == "http"
    with pytest.raises(impl.ToolError):
        impl.require_auth(customer_id=999)  # now enforced


def test_defect_2_last_session_key_cross_tenant_leak(monkeypatch):
    """DEFECT 2  (shape a) — SEVERE cross-tenant / auth-bypass leak.

    Spec section: Build Prompt piece 3 `extract_api_key` final fallback
    `if _session_api_keys: return list(_session_api_keys.values())[-1]`
    (echoed verbatim in Gotcha 5: "then to the last session key"). This ignores
    session identity entirely. `_session_api_keys` is a PROCESS-GLOBAL dict, so
    once ANY session has authenticated, an UNAUTHENTICATED request (no header,
    no session-id, empty contextvar) borrows that other tenant's key. Combined
    with `require_read_key` + `get_scoped_customer_id` on a no-customer_id
    discovery tool, an anonymous HTTP caller passes auth and is scoped to a
    DIFFERENT customer's data. Contradicts the Purpose ("leak one client's data
    to another ... the worst possible outcome") and Gotcha 4 (anonymous
    enumeration).
    """
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    # Customer A (id 100) authenticated earlier; their key sits in the cache.
    mkkey("custA_secret_x", 100, scopes=["read"])
    impl._session_api_keys["sessionA"] = "custA_secret_x"

    # A brand-new ANONYMOUS request: no Authorization header, no session-id.
    impl._current_api_key_var.set("")
    impl._current_session_id_var.set("")

    # PROOF: the anonymous caller is authenticated as customer A.
    assert impl.extract_api_key() == "custA_secret_x"          # borrowed key
    impl.require_read_key("list_catalog")                       # passes (should raise)
    assert impl.get_scoped_customer_id() == 100                 # scoped to A's tenant!
    leaked = impl._list_catalog_impl()
    assert leaked["scope_customer"] == 100                      # anon sees A's scope

    # --- Corrected extract_api_key: drop the identity-blind last-value fallback.
    def extract_api_key_fixed():
        k = impl._current_api_key_var.get("")
        if k:
            return k
        sid = impl._current_session_id_var.get("")
        if sid and sid in impl._session_api_keys:
            return impl._session_api_keys[sid]
        return os.environ.get("CS_PULSE_API_KEY", "") or None   # NO last-value guess

    monkeypatch.setattr(impl, "extract_api_key", extract_api_key_fixed)
    assert impl.extract_api_key() is None                       # anon stays anon
    with pytest.raises(impl.ToolError):
        impl.require_read_key("list_catalog")                   # correctly rejected


def test_defect_3_expiry_ac_has_no_build_prompt_piece():
    """DEFECT 3  (shape c) — MODERATE: an Acceptance Criterion with no owning code.

    Spec section: Acceptance Criteria "Expiry NULL case" requires THIS module to
    prove NULL expires_at validates and a past expires_at fails. But Build Prompt
    piece 3 `validate_customer_key` merely delegates to `module01_validate_api_key`
    and contains NO expiry logic; Boundary explicitly assigns expiry to Module 01.
    So Module 07's own Build Prompt ships nothing that satisfies its own AC — the
    behaviour under test lives entirely in a dependency the FDE must also invent.
    We prove the AC can only be met by code the Build Prompt never provides:
    grepping the reconstructed module-07 auth core for any expiry handling finds
    none.
    """
    import inspect
    core_src = "\n".join(
        inspect.getsource(fn) for fn in (
            impl.validate_customer_key, impl.check_scope, impl.has_account_access,
            impl.resolve_key, impl.require_auth, impl.require_account_auth,
            impl.require_read_key, impl.require_cross_customer_auth,
            impl.get_scoped_customer_id,
        ))
    # No expiry FIELD read and no expiry COMPARISON anywhere in Module 07's
    # Build-Prompt auth core. (The token "expired" appears ONLY inside a
    # ToolError message string — prose, never a check — which is itself the
    # point: the AC's behaviour is nowhere in this module's logic.)
    assert "expires_at" not in core_src
    assert "time.time()" not in core_src  # no expiry comparison lives here
    # The AC only passes because we (the FDE) had to write module01_validate_api_key
    # ourselves — a dependency stub, not a Module-07 deliverable:
    assert "expires_at" in inspect.getsource(impl.module01_validate_api_key)


def test_defect_4_auth_required_frozen_at_import(monkeypatch):
    """DEFECT 4  (shape a / d) — MINOR: kill-switch captured at import contradicts
    the Reference Test Harness.

    Spec section: Build Prompt piece 3 sets `MCP_AUTH_REQUIRED` as a module
    constant at import; the Reference Test Harness item 2 promises "a driver that
    sets MCP_TRANSPORT/MCP_AUTH_REQUIRED per case". MCP_TRANSPORT is read live in
    every enforcer, but MCP_AUTH_REQUIRED is frozen — setting the env AFTER import
    changes nothing, so a naive matrix suite silently tests a stale value (and can
    believe auth is enforced when it is disabled, or vice-versa). We prove the env
    var is inert post-import.
    """
    # Import happened with default MCP_AUTH_REQUIRED=true.
    monkeypatch.setenv("MCP_AUTH_REQUIRED", "false")   # deployer/tester flips it
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    importlib.reload_was_called = False
    # The module constant is UNCHANGED by the env edit:
    assert impl.MCP_AUTH_REQUIRED is True
    # Enforcement is therefore STILL on, despite MCP_AUTH_REQUIRED=false in env:
    with pytest.raises(impl.ToolError):
        impl.require_auth(100, "read")   # a "per case" driver would wrongly expect a no-op

    # Only a reload (fresh import) actually applies it — proving it is import-time:
    reloaded = importlib.reload(impl)
    assert reloaded.MCP_AUTH_REQUIRED is False
    # restore for other tests
    monkeypatch.setenv("MCP_AUTH_REQUIRED", "true")
    importlib.reload(impl)
