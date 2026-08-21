"""
Vertical catalog consistency — guard tests (Aug 21 2026, vertical-coupling audit).

A live audit against customer 390 (datacenter_v1) found get_kpi_catalog serving
dc2_s's 5-pillar names/weights to a 6-pillar customer, with its own vertical
field correctly reporting 'datacenter_v1' — an internally inconsistent
response. Root cause: get_kpi_catalog hardcoded a two-branch if/else
(saas_premium via a direct module import, everything else silently defaulted
to DC2S_PILLARS) instead of using utils.vertical_registry, the loader the
rest of the codebase already uses correctly. The saas_premium branch was
ALSO broken — verticals/saas_premium/kpi_definitions.py has no
SAAS_PILLAR_WEIGHTS symbol — so its except ImportError fell through to the
same dc2_s default. Every vertical except dc2_s was silently served dc2_s's
catalog. Separately, get_vertical_config referenced _get_playbook_config
without importing it — a NameError on a prospect-facing, no-auth discovery
tool. And partner_portal hardcoded pillar_code='P4' as "the partner pillar,"
which is only true in dc2_s/saas_premium — in datacenter_v1, P4 is Power &
Facility, so the portal was handing a channel partner the customer's
facility data under partner labels.

Fixes:
  - get_kpi_catalog now sources PILLARS/default_l2 from vertical_registry
    and raises ToolError (no silent fallback) if that fails.
  - get_vertical_config's cs_pulse_onboarding.py import list now includes
    _get_playbook_config.
  - partner_portal refuses to serve (ToolError) unless the tenant's own
    declared P4 pillar name is literally "Channel & Partner Health" — a
    content check, not a per-vertical lookup table (which would just
    relocate the same defect). A pillar_roles registry replaces this with
    a proper role lookup later; this is the interim control.

These tests import no Flask app and need no DB — same convention as
test_mcp_tool_auth_coverage.py and test_vertical_playbook_routing.py.
"""

import ast
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

MCP_SERVER_PY = BACKEND / "mcp_server" / "cs_pulse_mcp_server.py"
ONBOARDING_PY = BACKEND / "mcp_server" / "cs_pulse_onboarding.py"
ADMIN_PY = BACKEND / "mcp_server" / "cs_pulse_admin.py"


# ──────────────────────────────────────────────────────────────────────────
# 1. Data-level: vertical_registry itself must serve a complete, consistent
#    catalog for every registered vertical. This is the thing get_kpi_catalog
#    now depends on entirely — if the registry has a gap, the tool inherits
#    it, so the registry's completeness is load-bearing, not incidental.
# ──────────────────────────────────────────────────────────────────────────

def test_every_registered_vertical_has_complete_pillar_data():
    from utils.vertical_registry import SUPPORTED_VERTICALS, get_pillars, get_kpis

    assert SUPPORTED_VERTICALS, "No verticals registered — registry itself is empty."

    for vertical in sorted(SUPPORTED_VERTICALS):
        pillars = get_pillars(vertical)
        kpis = get_kpis(vertical)

        assert pillars, f"{vertical!r}: get_pillars() returned no pillars."
        assert kpis, f"{vertical!r}: get_kpis() returned no KPIs."

        for pcode, pdata in pillars.items():
            assert pdata.get('name'), (
                f"{vertical!r} pillar {pcode!r} has no 'name' — "
                f"get_kpi_catalog would render the bare code."
            )
            assert pdata.get('weight_l2') is not None, (
                f"{vertical!r} pillar {pcode!r} has no weight_l2 — "
                f"get_kpi_catalog's default_l2 would silently omit it."
            )

        # Every KPI's declared pillar must actually exist in this vertical's
        # pillar set — otherwise it's invisible to any pillar_catalog build
        # that iterates pillars and filters KPIs by pillar membership
        # (exactly the mechanism that dropped 3 P6 KPIs to 35 from 38 in
        # the audited response, once the hardcoded catalog omitted P6).
        pillar_codes = set(pillars.keys())
        orphaned = {
            kcode for kcode, kdata in kpis.items()
            if kdata.get('pillar') not in pillar_codes
        }
        assert not orphaned, (
            f"{vertical!r}: KPIs {sorted(orphaned)} reference a pillar not "
            f"in get_pillars({vertical!r}) — they would silently vanish "
            f"from any pillar-keyed catalog view."
        )


# ──────────────────────────────────────────────────────────────────────────
# 2. Structural: get_kpi_catalog must not hardcode a per-vertical import.
#    AST sweep of the one function, not the whole file — verticals/*/
#    kpi_definitions.py modules legitimately define PILLARS constants for
#    their own internal use; the defect was this specific tool importing
#    them directly instead of going through the registry.
# ──────────────────────────────────────────────────────────────────────────

def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Could not find function {name!r} in AST.")


def _imported_names(node: ast.AST) -> set:
    names = set()
    for n in ast.walk(node):
        if isinstance(n, ast.ImportFrom) and n.module:
            for alias in n.names:
                names.add(f"{n.module}.{alias.name}")
    return names


def test_get_kpi_catalog_has_no_hardcoded_vertical_import():
    tree = ast.parse(MCP_SERVER_PY.read_text())

    # get_kpi_catalog itself, plus _get_kpi_definitions — the sibling helper
    # it calls, found to carry the identical defect (same file, same
    # if/else-bypassing-vertical_registry shape) while verifying this fix
    # live: PILLARS knew about P6, but kpi_defs never tagged any KPI
    # pillar='P6' because _get_kpi_definitions still hardcoded DC2S_KPIS.
    for fn_name in ("get_kpi_catalog", "_get_kpi_definitions"):
        fn = _find_function(tree, fn_name)
        imported = _imported_names(fn)

        forbidden = {
            n for n in imported
            if n.startswith("verticals.")
            and n.endswith(("PILLARS", "PILLAR_WEIGHTS", "KPIS"))
        }
        assert not forbidden, (
            f"{fn_name} imports vertical-specific constants directly: "
            f"{sorted(forbidden)}. This is the exact defect the Aug 21 audit "
            f"found (a hardcoded branch that silently served dc2_s's catalog "
            f"to every other vertical) — route through utils.vertical_registry "
            f"instead."
        )
        assert any(
            isinstance(n, ast.ImportFrom) and n.module == "utils.vertical_registry"
            for n in ast.walk(fn)
        ), f"{fn_name} no longer references utils.vertical_registry at all."


# ──────────────────────────────────────────────────────────────────────────
# 3. Structural: get_vertical_config's module must import every name its
#    function body references as a bare name. Regression pin for the
#    NameError — the same bug class the file's own Apr 28 2026 comment
#    documents for _require_auth; this is the second occurrence.
# ──────────────────────────────────────────────────────────────────────────

def test_get_vertical_config_imports_are_complete():
    tree = ast.parse(ONBOARDING_PY.read_text())

    imported = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    builtins_and_locals = set(dir(__builtins__)) | {
        'self', 'cls', 'True', 'False', 'None',
    }

    fn = _find_function(tree, "get_vertical_config")
    loaded_names = {
        n.id for n in ast.walk(fn)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
    }
    # Names bound as parameters or local assignments inside the function
    # are legitimately "defined" without a module-level import.
    locally_bound = {
        t.id for node in ast.walk(fn)
        for t in (getattr(node, 'targets', []) or [getattr(node, 'target', None)])
        if t is not None and isinstance(t, ast.Name)
    }
    locally_bound |= {a.arg for a in fn.args.args}

    unresolved = loaded_names - imported - locally_bound - builtins_and_locals
    # ToolError, ht (utils.health_thresholds alias), and dict/list/etc.
    # builtins are all legitimately resolved some other way (module-level
    # import elsewhere in the file, or a local `import X as Y` inside the
    # function body) — only flag names whose ONLY plausible source is a
    # top-of-file import block, i.e. names ending in a helper-style
    # underscore-prefixed pattern matching this file's known import block.
    suspicious = {n for n in unresolved if n.startswith('_get_') or n.startswith('_resolve_')}
    assert not suspicious, (
        f"get_vertical_config references {sorted(suspicious)} as bare "
        f"names with no matching import in cs_pulse_onboarding.py. This is "
        f"the exact shape of the Aug 21 2026 NameError "
        f"(_get_playbook_config) — a prospect-facing, no-auth discovery "
        f"tool that would raise a raw stack trace instead of a ToolError."
    )


# ──────────────────────────────────────────────────────────────────────────
# 4. Structural: partner_portal must gate on the tenant's actual P4 pillar
#    name, not skip straight to querying P4 data.
# ──────────────────────────────────────────────────────────────────────────

def test_partner_portal_gates_on_pillar_content():
    source = ADMIN_PY.read_text()
    tree = ast.parse(source)
    fn = _find_function(tree, "partner_portal")
    fn_source = ast.get_source_segment(source, fn) or ""

    assert "Channel & Partner Health" in fn_source, (
        "partner_portal no longer checks the tenant's actual P4 pillar "
        "name before serving. This is the Finding-2 data-exposure gate — "
        "removing it re-opens serving a non-partner vertical's P4 data "
        "(e.g. datacenter_v1's Power & Facility) under partner labels."
    )
    assert "get_pillars" in fn_source, (
        "partner_portal's gate should resolve the tenant's real pillar "
        "name via vertical_registry.get_pillars(), not a hardcoded "
        "per-vertical map — the latter relocates the defect instead of "
        "fixing it."
    )


if __name__ == "__main__":
    test_every_registered_vertical_has_complete_pillar_data()
    print("PASS: every registered vertical has complete pillar data")
    test_get_kpi_catalog_has_no_hardcoded_vertical_import()
    print("PASS: get_kpi_catalog has no hardcoded vertical import")
    test_get_vertical_config_imports_are_complete()
    print("PASS: get_vertical_config imports are complete")
    test_partner_portal_gates_on_pillar_content()
    print("PASS: partner_portal gates on pillar content")
    print("\nAll vertical catalog consistency tests passed.")
