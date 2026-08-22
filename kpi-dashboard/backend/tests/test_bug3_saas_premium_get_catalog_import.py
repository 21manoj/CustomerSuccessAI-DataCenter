"""
Regression: SaaS Premium API blueprint failed to register at startup.

Aug 21 2026 vertical-coupling audit, Bug 3. Two call sites imported a
function `get_catalog` from `utils.vertical_registry` that never existed
there (the real name is `get_catalog_for_customer`, plus the standalone
`get_pillars`/`get_kpis` accessors):

  - verticals/saas_premium/api_routes.py (module-level import) — this is
    the one that actually broke app_v3_minimal.py's blueprint registration:
    `from verticals.saas_premium.api_routes import saas_premium_api` raised
    ImportError, which app_v3_minimal.py caught and logged as
    "Warning: SaaS Premium API not available: cannot import name
    'get_catalog' from 'utils.vertical_registry'" — the whole /api/saas/*
    blueprint silently never registered.
  - mcp_server/cs_pulse_revenue.py's generate_playbook_from_description
    tool (line ~713) — a lazily-imported, try/except-wrapped occurrence of
    the same broken import inside a function body (silently fell back to a
    hardcoded KPI name dict rather than crashing at import time, but the
    catalog-driven KPI-name lookup it was meant to provide never worked).

Both are pure-Python / no-Flask-app-context checks: importing the module
and AST-scanning source for the dead symbol.
"""

import ast
import importlib
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

SAAS_API_ROUTES_PY = BACKEND / "verticals" / "saas_premium" / "api_routes.py"
CS_PULSE_REVENUE_PY = BACKEND / "mcp_server" / "cs_pulse_revenue.py"


def _imported_names_from(tree: ast.Module, module_name: str) -> set:
    """Return the set of names imported via `from <module_name> import ...`."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module_name:
            names.update(alias.name for alias in node.names)
    return names


def test_vertical_registry_has_no_get_catalog_symbol():
    """Sanity check: the real registry module. get_catalog was never a real
    symbol — get_catalog_for_customer (customer_id -> (pillars, kpis)) and
    get_pillars/get_kpis(vertical) are the real API."""
    import utils.vertical_registry as vr

    assert not hasattr(vr, "get_catalog"), (
        "utils.vertical_registry now defines get_catalog — if that's "
        "intentional, this guard test should be updated/removed."
    )
    assert hasattr(vr, "get_catalog_for_customer")
    assert hasattr(vr, "get_pillars")
    assert hasattr(vr, "get_kpis")


def test_saas_premium_api_routes_does_not_import_get_catalog():
    """AST-level: verticals/saas_premium/api_routes.py must not import the
    nonexistent get_catalog symbol from vertical_registry."""
    tree = ast.parse(SAAS_API_ROUTES_PY.read_text())
    imported = _imported_names_from(tree, "utils.vertical_registry")
    assert "get_catalog" not in imported, (
        f"verticals/saas_premium/api_routes.py imports nonexistent "
        f"get_catalog from utils.vertical_registry (imported: {imported}) — "
        f"this raises ImportError at module load and silently kills the "
        f"whole SaaS Premium API blueprint registration in app_v3_minimal.py."
    )


def test_saas_premium_api_routes_module_imports_successfully():
    """The actual failure mode: `from verticals.saas_premium.api_routes
    import saas_premium_api` must not raise ImportError (this is exactly
    what app_v3_minimal.py's try/except around blueprint registration
    catches and silently logs as a startup warning)."""
    sys.modules.pop("verticals.saas_premium.api_routes", None)
    mod = importlib.import_module("verticals.saas_premium.api_routes")
    assert hasattr(mod, "saas_premium_api"), "Blueprint object missing after import"


def test_cs_pulse_revenue_does_not_import_get_catalog():
    """AST-level: mcp_server/cs_pulse_revenue.py must not import the
    nonexistent get_catalog symbol from vertical_registry (it should use
    get_catalog_for_customer instead)."""
    tree = ast.parse(CS_PULSE_REVENUE_PY.read_text())
    imported = _imported_names_from(tree, "utils.vertical_registry")
    assert "get_catalog" not in imported, (
        f"mcp_server/cs_pulse_revenue.py imports nonexistent get_catalog "
        f"from utils.vertical_registry (imported: {imported})."
    )
    assert "get_catalog_for_customer" in imported, (
        "Expected mcp_server/cs_pulse_revenue.py to use "
        "get_catalog_for_customer(customer_id) to load the per-customer "
        "KPI catalog."
    )
