"""
Vertical resolution fail-closed — guard tests (Phase 1, 2026-08-21).

Two independent resolvers used to silently `return 'dc2_s'` whenever a
customer's vertical couldn't be resolved:

  - utils.vertical_registry.get_vertical_for_customer — no CustomerConfig
    row, or its `vertical` column unset, or any exception during lookup.
  - mcp_server.cs_pulse_mcp_server._resolve_customer_vertical — same idea,
    but with its own 3-tier order (CustomerConfig.vertical, then
    Customer.vertical short-code, then the dc2_s fallback).

Both silently mislabeled the affected customer as dc2_s and served DC2S's
KPI/pillar catalog, playbooks, or dashboard under the customer's own name,
with no error anywhere in the chain.

Fix: both resolvers now raise (ValueError / ToolError respectively) instead
of defaulting to dc2_s. Call sites decide explicitly whether to propagate
(4xx) or skip-with-log (batch pipelines) — but must never catch the
exception and quietly re-substitute 'dc2_s' under a different variable name.
The two resolvers were deliberately NOT merged into one: the mcp_server one
has a real second resolution tier (legacy Customer.vertical short codes,
B-4/B-5) that vertical_registry's does not.

These tests mock the DB layer (Customer/CustomerConfig .query) so they run
without a live Postgres — same no-DB convention as
test_vertical_catalog_consistency.py. (The local dev DB was wiped by an
unrelated test-fixture bug on 2026-08-21; these tests do not depend on it.)
"""

import ast
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@contextmanager
def _mock_query(model_cls, mock_query):
    """Stub `ModelCls.query` without touching flask_sqlalchemy's real
    `_QueryProperty` descriptor.

    `unittest.mock.patch.object` reads the *original* attribute value
    before installing the stub (so it can restore it afterwards), and
    reading flask_sqlalchemy's `query` descriptor requires a live Flask
    app context ("Working outside of application context"). Plain
    class-attribute assignment shadows the inherited descriptor in the
    subclass's own __dict__ without ever invoking it, so this works with
    no app/DB at all — the point of these being pure-Python tests.
    """
    had_own = 'query' in model_cls.__dict__
    original = model_cls.__dict__.get('query')
    model_cls.query = mock_query
    try:
        yield
    finally:
        if had_own:
            model_cls.query = original
        else:
            try:
                delattr(model_cls, 'query')
            except AttributeError:
                pass

VERTICAL_REGISTRY_PY = BACKEND / "utils" / "vertical_registry.py"
MCP_SERVER_PY = BACKEND / "mcp_server" / "cs_pulse_mcp_server.py"

# Call sites fixed alongside the two resolvers: each must no longer contain
# an `except` handler that assigns/returns the literal 'dc2_s' (the
# catch-and-silently-resubstitute pattern the audit found). Deliberately
# excludes outcome_roi_api.py's playbook_economics() inline resolver, a
# separate, still-open, un-deduplicated dc2_s-fallback implementation
# (same bug class, out of this phase's scope — see report).
CALL_SITE_FILES = {
    "api_v1_routes._resolve_vertical": BACKEND / "api_v1_routes.py",
    "signal_engine.worker": BACKEND / "signal_engine" / "worker.py",
    "utils.vertical_playbook_routing.resolve_customer_vertical":
        BACKEND / "utils" / "vertical_playbook_routing.py",
    "mcp_server.cs_pulse_onboarding": BACKEND / "mcp_server" / "cs_pulse_onboarding.py",
}


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Could not find function {name!r} in AST.")


# ──────────────────────────────────────────────────────────────────────────
# 1. utils.vertical_registry.get_vertical_for_customer
# ──────────────────────────────────────────────────────────────────────────

def test_get_vertical_for_customer_raises_when_no_customer_config_row():
    from utils.vertical_registry import get_vertical_for_customer
    import models

    mock_query = MagicMock()
    mock_query.filter_by.return_value.first.return_value = None
    with _mock_query(models.CustomerConfig, mock_query):
        try:
            get_vertical_for_customer(999999)
            raise AssertionError("expected ValueError for missing CustomerConfig row")
        except ValueError as e:
            assert "999999" in str(e)


def test_get_vertical_for_customer_raises_when_vertical_column_unset():
    from utils.vertical_registry import get_vertical_for_customer
    import models

    fake_config = MagicMock()
    fake_config.vertical = None
    mock_query = MagicMock()
    mock_query.filter_by.return_value.first.return_value = fake_config
    with _mock_query(models.CustomerConfig, mock_query):
        try:
            get_vertical_for_customer(42)
            raise AssertionError("expected ValueError when vertical column is unset")
        except ValueError:
            pass


def test_get_vertical_for_customer_still_resolves_normally():
    from utils.vertical_registry import get_vertical_for_customer
    import models

    fake_config = MagicMock()
    fake_config.vertical = 'saas_premium'
    mock_query = MagicMock()
    mock_query.filter_by.return_value.first.return_value = fake_config
    with _mock_query(models.CustomerConfig, mock_query):
        assert get_vertical_for_customer(42) == 'saas_premium'


def test_get_vertical_for_customer_no_longer_has_bare_dc2s_fallback():
    """Structural regression pin: the function body must not `return` the
    bare literal 'dc2_s' anywhere — any remaining 'dc2_s' string may only
    appear inside an error message, not as a returned value."""
    tree = ast.parse(VERTICAL_REGISTRY_PY.read_text())
    fn = _find_function(tree, "get_vertical_for_customer")
    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant):
            assert node.value.value != 'dc2_s', (
                "get_vertical_for_customer still has a bare `return 'dc2_s'` "
                "— the Phase 1 fail-closed fix removed this fallback."
            )


# ──────────────────────────────────────────────────────────────────────────
# 2. mcp_server.cs_pulse_mcp_server._resolve_customer_vertical
# ──────────────────────────────────────────────────────────────────────────

def test_resolve_customer_vertical_raises_when_customer_not_found():
    from mcp_server.cs_pulse_mcp_server import _resolve_customer_vertical
    from fastmcp.exceptions import ToolError
    import models

    mock_customer_query = MagicMock()
    mock_customer_query.get.return_value = None
    with _mock_query(models.Customer, mock_customer_query):
        try:
            _resolve_customer_vertical(999999)
            raise AssertionError("expected ToolError for unknown customer")
        except ToolError:
            pass


def test_resolve_customer_vertical_raises_when_both_tiers_unset():
    from mcp_server.cs_pulse_mcp_server import _resolve_customer_vertical
    from fastmcp.exceptions import ToolError
    import models

    fake_customer = MagicMock()
    fake_customer.vertical = None
    mock_customer_query = MagicMock()
    mock_customer_query.get.return_value = fake_customer

    mock_config_query = MagicMock()
    mock_config_query.filter_by.return_value.first.return_value = None

    with _mock_query(models.Customer, mock_customer_query), \
         _mock_query(models.CustomerConfig, mock_config_query):
        try:
            _resolve_customer_vertical(42)
            raise AssertionError("expected ToolError when both tiers unset")
        except ToolError:
            pass


def test_resolve_customer_vertical_tier2_short_code_still_works():
    """Tier 2 (Customer.vertical short code) must still work, and must
    still be tried before failing closed — this is the meaningful
    difference from vertical_registry.get_vertical_for_customer that kept
    this resolver separate rather than delegating to it (B-4/B-5 short-code
    normalization: 'saas' -> 'saas_premium')."""
    from mcp_server.cs_pulse_mcp_server import _resolve_customer_vertical
    import models

    fake_customer = MagicMock()
    fake_customer.vertical = 'saas'  # legacy short code
    mock_customer_query = MagicMock()
    mock_customer_query.get.return_value = fake_customer

    mock_config_query = MagicMock()
    mock_config_query.filter_by.return_value.first.return_value = None

    with _mock_query(models.Customer, mock_customer_query), \
         _mock_query(models.CustomerConfig, mock_config_query):
        assert _resolve_customer_vertical(42) == 'saas_premium'


def test_resolve_customer_vertical_no_longer_has_bare_dc2s_fallback():
    tree = ast.parse(MCP_SERVER_PY.read_text())
    fn = _find_function(tree, "_resolve_customer_vertical")
    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant):
            assert node.value.value != 'dc2_s', (
                "_resolve_customer_vertical still has a bare `return 'dc2_s'`."
            )


# ──────────────────────────────────────────────────────────────────────────
# 3. Known call sites: catch-and-silently-resubstitute-dc2_s must be gone.
#    Skip-with-log (log + continue/return, no re-default) is fine and, for
#    the batch pipelines here, correct; re-defaulting to dc2_s under a new
#    variable name inside the except block is exactly the bug that shipped.
# ──────────────────────────────────────────────────────────────────────────

def test_known_call_sites_have_no_except_dc2s_resubstitution():
    for label, path in CALL_SITE_FILES.items():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Constant) and stmt.value == 'dc2_s':
                        raise AssertionError(
                            f"{label} ({path}): an except handler still "
                            f"references the literal 'dc2_s' — looks like "
                            f"the catch-and-resubstitute pattern the Phase "
                            f"1 fix removed."
                        )


def test_api_v1_dispatch_returns_4xx_not_dc2s_default_on_resolution_failure():
    """api_v1_routes._dispatch is the central proxy for every /api/v1/*
    dashboard route. An unresolvable customer must get an explicit error
    response, not a silently-wrong DC2S-flavored dashboard."""
    import api_v1_routes

    # jsonify() needs a live Flask app/request context; stub it to identity
    # so this stays a pure-Python test (same no-Flask convention as the
    # rest of this file) while still exercising _dispatch's own status-code
    # decision.
    with patch('api_v1_routes.get_current_customer_id', return_value=4242), \
         patch('api_v1_routes._resolve_vertical', side_effect=ValueError("boom")), \
         patch('api_v1_routes.jsonify', side_effect=lambda x: x):
        resp = api_v1_routes._dispatch('accounts', lambda: None)
        assert resp[1] == 400, f"expected (body, 400), got {resp}"


if __name__ == "__main__":
    test_get_vertical_for_customer_raises_when_no_customer_config_row()
    print("PASS: get_vertical_for_customer raises when no CustomerConfig row")
    test_get_vertical_for_customer_raises_when_vertical_column_unset()
    print("PASS: get_vertical_for_customer raises when vertical column unset")
    test_get_vertical_for_customer_still_resolves_normally()
    print("PASS: get_vertical_for_customer still resolves normally")
    test_get_vertical_for_customer_no_longer_has_bare_dc2s_fallback()
    print("PASS: get_vertical_for_customer has no bare dc2_s fallback")
    test_resolve_customer_vertical_raises_when_customer_not_found()
    print("PASS: _resolve_customer_vertical raises when customer not found")
    test_resolve_customer_vertical_raises_when_both_tiers_unset()
    print("PASS: _resolve_customer_vertical raises when both tiers unset")
    test_resolve_customer_vertical_tier2_short_code_still_works()
    print("PASS: _resolve_customer_vertical tier2 short code still works")
    test_resolve_customer_vertical_no_longer_has_bare_dc2s_fallback()
    print("PASS: _resolve_customer_vertical has no bare dc2_s fallback")
    test_known_call_sites_have_no_except_dc2s_resubstitution()
    print("PASS: known call sites have no except-dc2_s resubstitution")
    test_api_v1_dispatch_returns_4xx_not_dc2s_default_on_resolution_failure()
    print("PASS: api_v1 dispatch returns 4xx not dc2_s default")
    print("\nAll vertical resolution fail-closed tests passed.")
