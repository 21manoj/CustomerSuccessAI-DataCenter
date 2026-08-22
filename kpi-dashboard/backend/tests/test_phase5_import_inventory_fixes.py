"""
Phase 5 of the vertical-registry fail-closed refactor (Aug 22 2026) — sites
cleared in dc2s_config_api.py, utils/config_loader.py, and
wizards/wizard_c_weight_calibrator_db.py from the Phase 4 baseline
(tests/test_cross_vertical_import_inventory.py).

Each fixed site swapped a direct `from verticals.dc2_s.kpi_definitions
import DC2S_KPIS/DC2S_PILLARS` for `utils.vertical_registry.get_kpis`/
`get_pillars`. Two kinds of proof, mirroring
tests/test_vertical_catalog_consistency.py's own style:

  1. AST-level: the fixed function/block no longer imports
     `verticals.dc2_s.*` directly, and DOES reference
     `utils.vertical_registry`.
  2. Behavioral: for the two sites that are genuinely vertical-generic
     fixes (wizard_c's `get_kpi_definitions` fallback), execute the actual
     extracted source (not a reimplementation) against multiple verticals
     to prove it resolves per-vertical instead of silently defaulting to
     dc2_s. For the sites that are intentionally dc2_s-only (dc2s_config_api,
     config_loader — both scoped to DC2_S by design), prove parity: the
     registry-routed value equals the old direct-import value exactly.

These tests import no Flask app and need no DB — same convention as
test_vertical_catalog_consistency.py (local Postgres is empty on this
branch; the fixed code paths here don't touch it).
"""

import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

DC2S_CONFIG_API_PY = BACKEND / "dc2s_config_api.py"
CONFIG_LOADER_PY = BACKEND / "utils" / "config_loader.py"
WIZARD_C_PY = BACKEND / "wizards" / "wizard_c_weight_calibrator_db.py"


# ──────────────────────────────────────────────────────────────────────────
# Shared AST helpers (same shape as test_vertical_catalog_consistency.py)
# ──────────────────────────────────────────────────────────────────────────

def _find_function(tree: ast.Module, name: str) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"Could not find function {name!r} in AST.")


def _imported_names(node: ast.AST) -> set:
    names = set()
    for n in ast.walk(node):
        if isinstance(n, ast.ImportFrom) and n.module:
            for alias in n.names:
                names.add(f"{n.module}.{alias.name}")
    return names


def _has_direct_vertical_import(node: ast.AST) -> set:
    """Any `from verticals.<x>.kpi_definitions import ...` inside node."""
    return {
        n for n in _imported_names(node)
        if n.startswith("verticals.") and n.endswith(("PILLARS", "KPIS"))
    }


def _references_vertical_registry(node: ast.AST) -> bool:
    return any(
        isinstance(n, ast.ImportFrom) and n.module == "utils.vertical_registry"
        for n in ast.walk(node)
    )


# ──────────────────────────────────────────────────────────────────────────
# 1. dc2s_config_api.py — 3 baseline sites, all DC2_S-only by design
#    (module docstring + url_prefix='/api/dc2s/config').
# ──────────────────────────────────────────────────────────────────────────

def test_dc2s_config_api_module_level_weights_no_direct_import():
    tree = ast.parse(DC2S_CONFIG_API_PY.read_text())
    module_level_imports = {
        n for n in _imported_names(tree)
        if n.startswith("verticals.") and n.endswith(("PILLARS", "KPIS"))
    }
    assert not module_level_imports, (
        f"dc2s_config_api.py module scope still directly imports vertical "
        f"constants: {sorted(module_level_imports)} — should route through "
        f"utils.vertical_registry.get_pillars('dc2_s')."
    )
    assert _references_vertical_registry(tree), (
        "dc2s_config_api.py no longer references utils.vertical_registry at all."
    )


def test_dc2s_config_api_get_config_and_kpi_ranges_no_direct_import():
    tree = ast.parse(DC2S_CONFIG_API_PY.read_text())
    for fn_name in ("get_config", "get_dc2s_kpi_ranges"):
        fn = _find_function(tree, fn_name)
        forbidden = _has_direct_vertical_import(fn)
        assert not forbidden, (
            f"{fn_name} in dc2s_config_api.py still directly imports "
            f"{sorted(forbidden)} instead of routing through "
            f"utils.vertical_registry.get_kpis('dc2_s')."
        )


def test_dc2s_config_api_default_pillar_weights_parity_with_registry():
    """Behavioral: DEFAULT_PILLAR_WEIGHTS (now built via get_pillars('dc2_s'))
    must be byte-identical to what the old direct DC2S_PILLARS import
    produced — this is a DC2_S-only file, so no behavior change is expected
    or acceptable.
    """
    import importlib
    import dc2s_config_api as m
    importlib.reload(m)  # in case an earlier test imported a stale module

    from utils.vertical_registry import get_pillars
    from verticals.dc2_s.kpi_definitions import DC2S_PILLARS

    expected = {pid: info.get('weight_l2', 0.20) for pid, info in DC2S_PILLARS.items()}
    assert m.DEFAULT_PILLAR_WEIGHTS == expected
    assert m.DEFAULT_PILLAR_WEIGHTS == {
        pid: info.get('weight_l2', 0.20) for pid, info in get_pillars('dc2_s').items()
    }


# ──────────────────────────────────────────────────────────────────────────
# 2. utils/config_loader.py — 2 baseline sites, DC2_S-only by design
#    (module docstring: "Configuration Loader for DC2_S Wizards").
# ──────────────────────────────────────────────────────────────────────────

def test_config_loader_no_direct_vertical_import():
    tree = ast.parse(CONFIG_LOADER_PY.read_text())
    forbidden = {
        n for n in _imported_names(tree)
        if n.startswith("verticals.") and n.endswith(("PILLARS", "KPIS"))
    }
    assert not forbidden, (
        f"utils/config_loader.py still directly imports {sorted(forbidden)} "
        f"instead of routing through utils.vertical_registry."
    )
    assert _references_vertical_registry(tree), (
        "utils/config_loader.py no longer references utils.vertical_registry at all."
    )


def test_config_loader_vertical_definition_parity_with_registry():
    """Behavioral: ConfigLoader.vertical_definition (DC2_S-only loader) must
    still produce the same pillar/KPI catalog it did via the direct
    DC2S_PILLARS/DC2S_KPIS import — proves the registry swap is parity-safe,
    not a silent default. Does not touch the DB (vertical_definition is
    lazy and independent of customer_config).
    """
    from utils.config_loader import ConfigLoader
    from utils.vertical_registry import get_pillars, get_kpis

    loader = ConfigLoader(customer_id=999999999)  # no DB row needed for this property
    vd = loader.vertical_definition

    expected_pillars = get_pillars('dc2_s')
    expected_kpis = get_kpis('dc2_s')

    assert len(vd['pillars']) == len(expected_pillars) == 5
    assert len(vd['default_kpis']) == len(expected_kpis) == 38

    got_weights = {p['code']: p['default_weight'] for p in vd['pillars']}
    expected_weights = {pid: info.get('weight_l2', 0.20) for pid, info in expected_pillars.items()}
    assert got_weights == expected_weights

    got_codes = {k['code'] for k in vd['default_kpis']}
    assert got_codes == set(expected_kpis.keys())


# ──────────────────────────────────────────────────────────────────────────
# 3. wizards/wizard_c_weight_calibrator_db.py — 2 baseline sites.
# ──────────────────────────────────────────────────────────────────────────

def test_wizard_c_run_wizard_c_no_direct_vertical_import():
    tree = ast.parse(WIZARD_C_PY.read_text())
    fn = _find_function(tree, "run_wizard_c")
    forbidden = _has_direct_vertical_import(fn)
    assert not forbidden, (
        f"run_wizard_c still directly imports {sorted(forbidden)} instead of "
        f"routing through utils.vertical_registry."
    )
    assert _references_vertical_registry(fn), (
        "run_wizard_c no longer references utils.vertical_registry at all."
    )


def test_wizard_c_get_kpi_definitions_fallback_resolves_per_vertical():
    """Behavioral: the ImportError fallback for `get_kpi_definitions` used to
    unconditionally `return DC2S_KPIS` regardless of the `vertical` argument
    — a real bug (silent dc2_s substitution) in the rare case
    mcp_server.common fails to import. This extracts and EXECUTES the actual
    fixed source (not a reimplementation) to prove it now resolves
    per-vertical.
    """
    source = WIZARD_C_PY.read_text()
    tree = ast.parse(source)
    run_fn = _find_function(tree, "run_wizard_c")

    inner = None
    for node in ast.walk(run_fn):
        if isinstance(node, ast.FunctionDef) and node.name == "get_kpi_definitions":
            inner = node
            break
    assert inner is not None, "Could not find the get_kpi_definitions fallback closure."

    src = ast.get_source_segment(source, inner)
    assert src is not None
    namespace: dict = {}
    exec(compile(src, "<wizard_c_fallback>", "exec"), namespace)
    get_kpi_definitions = namespace["get_kpi_definitions"]

    from utils.vertical_registry import get_kpis

    dc2s_result = get_kpi_definitions("dc2_s")
    saas_result = get_kpi_definitions("saas_premium")

    # The old bug: this would have been True (both == DC2S_KPIS).
    assert dc2s_result != saas_result, (
        "get_kpi_definitions fallback still returns the same catalog for "
        "dc2_s and saas_premium — silently re-defaulting to dc2_s."
    )
    assert dc2s_result == get_kpis("dc2_s")
    assert saas_result == get_kpis("saas_premium")


def test_wizard_c_base_l2_dc2s_branch_parity_and_saas_unchanged():
    """Behavioral: the `if vertical == 'dc2_s':` base_l2 branch was swapped
    from a direct DC2S_PILLARS import to get_pillars('dc2_s') — must be
    byte-identical (dc2_s parity). The non-dc2_s branch (equal-weight
    fallback, which saas_premium and datacenter_v1 both hit) is untouched —
    verified here too, since extending catalog-based weights to those
    verticals would be an out-of-scope behavior change per the standing
    constraint.
    """
    source = WIZARD_C_PY.read_text()
    tree = ast.parse(source)
    run_fn = _find_function(tree, "run_wizard_c")

    try_node = None
    for node in ast.walk(run_fn):
        if isinstance(node, ast.Try):
            seg = ast.get_source_segment(source, node) or ""
            if "base_l2" in seg and "get_pillars" in seg:
                try_node = node
                break
    assert try_node is not None, "Could not find the base_l2 try/except block."

    src = ast.get_source_segment(source, try_node)
    assert src is not None
    forbidden = _has_direct_vertical_import(try_node)
    assert not forbidden, (
        f"base_l2 block still directly imports {sorted(forbidden)}:\n{src}"
    )
    assert "get_pillars" in src

    def _run(vertical: str, pillar_codes):
        import textwrap
        namespace = {"vertical": vertical, "pillar_codes": pillar_codes, "base_l2": None}
        # ast.get_source_segment only dedents the FIRST line of a multi-line
        # statement to col 0; continuation lines (e.g. `except Exception:`)
        # keep their original absolute indentation. Re-pad the first line to
        # match before dedenting uniformly, then indent for the wrapper.
        lines = src.splitlines()
        base_indent = min(
            len(l) - len(l.lstrip()) for l in lines[1:] if l.strip()
        )
        lines[0] = (" " * base_indent) + lines[0]
        normalized = textwrap.dedent("\n".join(lines))
        indented = "\n".join("    " + line for line in normalized.splitlines())
        wrapper = f"def _f(vertical, pillar_codes):\n{indented}\n    return base_l2\n"
        exec(compile(wrapper, "<wizard_c_base_l2>", "exec"), namespace)
        return namespace["_f"](vertical, pillar_codes)

    from utils.vertical_registry import get_pillars

    dc2s_pillar_codes = sorted(get_pillars('dc2_s').keys())
    dc2s_base_l2 = _run("dc2_s", dc2s_pillar_codes)
    expected = {pid: info.get('weight_l2', info.get('weight', 0.2))
                for pid, info in get_pillars('dc2_s').items()}
    assert dc2s_base_l2 == expected

    saas_pillar_codes = ["P1", "P2", "P3"]
    saas_base_l2 = _run("saas_premium", saas_pillar_codes)
    assert saas_base_l2 == {p: 1.0 / len(saas_pillar_codes) for p in saas_pillar_codes}, (
        "saas_premium base_l2 behavior changed — expected the untouched "
        "equal-weight fallback."
    )


if __name__ == "__main__":
    import traceback

    tests = [
        test_dc2s_config_api_module_level_weights_no_direct_import,
        test_dc2s_config_api_get_config_and_kpi_ranges_no_direct_import,
        test_dc2s_config_api_default_pillar_weights_parity_with_registry,
        test_config_loader_no_direct_vertical_import,
        test_config_loader_vertical_definition_parity_with_registry,
        test_wizard_c_run_wizard_c_no_direct_vertical_import,
        test_wizard_c_get_kpi_definitions_fallback_resolves_per_vertical,
        test_wizard_c_base_l2_dc2s_branch_parity_and_saas_unchanged,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL: {t.__name__}")
            traceback.print_exc()
    if failed:
        raise SystemExit(f"{failed} test(s) failed")
    print(f"\nAll {len(tests)} tests passed.")
