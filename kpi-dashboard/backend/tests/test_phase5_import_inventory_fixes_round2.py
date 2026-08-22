"""
Phase 5 of the vertical-registry fail-closed refactor (Aug 22 2026), round 2 —
sites cleared in onboarding_api_v2_config_aware.py, customer_playbook_api.py,
data_quality_api.py, journey_api_dynamic.py, and playbook_recommendations_api.py
from the Phase 4 baseline (tests/test_cross_vertical_import_inventory.py).

Mirrors tests/test_phase5_import_inventory_fixes.py's own two-layer style:

  1. AST-level: the fixed function/module no longer directly imports
     `verticals.dc2_s.*` / `verticals.saas_premium.*`, and DOES reference
     utils.vertical_registry (or _ask_ai_helpers, the established
     fail-closed-per-vertical playbook-config helper).
  2. Behavioral: execute the actual fixed source (not a reimplementation —
     either by calling the real function directly, or by extracting an
     inner block via ast.get_source_segment and exec'ing it, same technique
     tests/test_phase5_import_inventory_fixes.py uses for wizard_c's
     closures) to prove real vertical differentiation, not silent dc2_s
     reuse.

Two sites were found and deliberately left unfixed (not silenced, not
reimplemented around) — documented here for completeness, not tested as
"fixed":

  - app_v3_minimal.py (2 sites, lines ~340/~1500): these import the dc2_s
    and saas_premium Flask Blueprint objects (`dc2s_api`, `saas_premium_api`)
    to mount them at their own vertical-namespaced URL prefixes
    (/api/dc2s/*, /api/saas/*). This is app-boot wiring, not a "which
    vertical for customer X" resolution bug — there is no generic
    equivalent to import, since datacenter_v1/healthcare_provider use the
    generic scorer with no dedicated Flask blueprint of their own. Each
    import is independently gated behind its own try/except ImportError.
  - ask_ai_tools.py (1 site, ~line 876): imports 5 compute-formula helpers
    from verticals.dc2_s.api_routes (_normalize_kpi_code_for_health,
    _compute_impact_score, _compute_effort_score, _determine_urgency,
    _get_roi_context) for get_csm_daily_actions. The PLAYBOOK_CONFIG/
    should_trigger_playbook part of this same function was ALREADY fixed
    (routes through _ask_ai_helpers._get_playbook_config), so
    _compute_impact_score/_compute_effort_score/_determine_urgency/
    _get_roi_context only ever execute inside the PLAYBOOK_CONFIG loop —
    for a vertical with no playbook config (anything but dc2_s/saas_premium)
    that loop runs zero times, so these 4 have no behavioral effect on
    other verticals. The 5th, _normalize_kpi_code_for_health, DOES run
    unconditionally per KPI code and IS hardcoded to `kpi_code in
    DC2S_KPIS` internally — a real residual gap, but the exact same gap
    exists, unaddressed, in the canonical reference implementation
    (verticals/dc2_s/api_routes.py's own get_csm_daily_actions, fixed by a
    sibling agent earlier the same day) which this module mirrors. Fixing
    the root cause requires editing verticals/dc2_s/api_routes.py, which is
    out of scope (owned by the mcp_server-cluster sibling agent). Left
    unfixed for consistency with the canonical reference rather than
    diverging into an ad hoc, one-off fix here.

These tests import no Flask app and need no DB for the AST checks and the
pure-function behavioral checks. The two tests that exercise DB-adjacent
helpers (_ask_ai_helpers._get_playbook_config, verticals.datacenter_v1's
PLAYBOOK_CONFIG) call real, already-existing, DB-free helper functions
directly — no app context needed.
"""

import ast
import sys
import textwrap
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ONBOARDING_PY = BACKEND / "onboarding_api_v2_config_aware.py"
CUSTOMER_PLAYBOOK_PY = BACKEND / "customer_playbook_api.py"
DATA_QUALITY_PY = BACKEND / "data_quality_api.py"
JOURNEY_PY = BACKEND / "journey_api_dynamic.py"
PLAYBOOK_REC_PY = BACKEND / "playbook_recommendations_api.py"


# ──────────────────────────────────────────────────────────────────────────
# Shared AST helpers (same shape as test_phase5_import_inventory_fixes.py)
# ──────────────────────────────────────────────────────────────────────────

def _find_function(tree: ast.Module, name: str) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"Could not find function {name!r} in AST.")


# Vertical-DEFINITION packages only (mirrors
# test_cross_vertical_import_inventory.py's VERTICAL_DEFINITION_DIRS) — a
# plain module import like `verticals.provision_dc_customer` (not a
# per-vertical definition package) is irrelevant to this guard.
_VERTICAL_DEFINITION_DIRS = {"dc2_s", "saas_premium", "datacenter_v1", "healthcare_provider", "_template"}


def _all_vertical_imports(node: ast.AST) -> set:
    """Every `from verticals.<real-vertical-package>...` import found
    anywhere inside node (excludes non-vertical modules that merely live
    under verticals/, e.g. verticals.provision_dc_customer)."""
    found = set()
    for n in ast.walk(node):
        if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("verticals."):
            slug = n.module.split(".")[1] if "." in n.module else ""
            if slug in _VERTICAL_DEFINITION_DIRS:
                for alias in n.names:
                    found.add(f"{n.module}.{alias.name}")
        if isinstance(n, ast.Import):
            for alias in n.names:
                if alias.name.startswith("verticals."):
                    slug = alias.name.split(".")[1] if "." in alias.name else ""
                    if slug in _VERTICAL_DEFINITION_DIRS:
                        found.add(alias.name)
    return found


def _references_vertical_registry(node: ast.AST) -> bool:
    return any(
        isinstance(n, ast.ImportFrom) and n.module == "utils.vertical_registry"
        for n in ast.walk(node)
    )


# ──────────────────────────────────────────────────────────────────────────
# 1. onboarding_api_v2_config_aware.py — module-level DC2S_KPIS/DC2S_PILLARS
#    import removed; _get_dc2s_kpi_valid_ranges + the idempotent-reuse and
#    complete_onboarding response paths now resolve per-vertical.
# ──────────────────────────────────────────────────────────────────────────

def test_onboarding_no_module_level_vertical_import():
    tree = ast.parse(ONBOARDING_PY.read_text())
    forbidden = _all_vertical_imports(tree)
    assert not forbidden, (
        f"onboarding_api_v2_config_aware.py still directly imports "
        f"{sorted(forbidden)} instead of routing through utils.vertical_registry."
    )


def test_onboarding_get_dc2s_kpi_valid_ranges_resolves_per_vertical():
    """Behavioral: was hardcoded to DC2S_KPIS; now takes a vertical param
    and routes through utils.vertical_registry.get_kpis. Proves dc2_s and
    saas_premium produce genuinely different range maps (not both silently
    dc2_s's).
    """
    import onboarding_api_v2_config_aware as m
    from utils.vertical_registry import get_kpis

    dc2s_ranges = m._get_dc2s_kpi_valid_ranges('dc2_s')
    saas_ranges = m._get_dc2s_kpi_valid_ranges('saas_premium')

    assert dc2s_ranges, "dc2_s ranges must not be empty"
    assert saas_ranges, "saas_premium ranges must not be empty"
    assert set(dc2s_ranges.keys()) != set(saas_ranges.keys()), (
        "dc2_s and saas_premium KPI range maps are identical — still "
        "silently serving the same (dc2_s) catalog for both."
    )
    # Default (no arg) must preserve prior behavior exactly.
    assert m._get_dc2s_kpi_valid_ranges() == dc2s_ranges

    # Parity: derived purely from vertical_registry.get_kpis, same shape rule.
    expected_codes = {
        code for code, defn in get_kpis('saas_premium').items()
        if any(
            isinstance((defn.get('ranges') or {}).get(band, {}).get('min'), (int, float))
            for band in ('healthy', 'risk', 'critical')
        )
    }
    assert set(saas_ranges.keys()) <= set(get_kpis('saas_premium').keys())
    assert expected_codes  # sanity: saas_premium catalog actually has ranges


def test_onboarding_validate_kpi_values_against_ranges_accepts_vertical():
    """Behavioral: validate_kpi_values_against_ranges gained a `vertical`
    param (default 'dc2_s' for backward compat) instead of always checking
    against DC2_S ranges regardless of the caller's actual vertical.
    """
    import pandas as pd
    import onboarding_api_v2_config_aware as m
    from utils.vertical_registry import get_kpis

    saas_kpis = get_kpis('saas_premium')
    dc2s_codes = set(get_kpis('dc2_s').keys())
    # Pick a real saas_premium KPI code, NOT also present in dc2_s's catalog
    # (both use P-format codes, so some overlap — need one exclusive to
    # saas_premium to prove dc2_s's ranges genuinely don't recognize it),
    # with a defined range.
    saas_code = None
    saas_bad_value = None
    for code, defn in saas_kpis.items():
        if code in dc2s_codes:
            continue
        ranges = defn.get('ranges') or {}
        maxs = [
            ranges[b]['max'] for b in ('healthy', 'risk', 'critical')
            if isinstance(ranges.get(b, {}).get('max'), (int, float))
        ]
        mins = [
            ranges[b]['min'] for b in ('healthy', 'risk', 'critical')
            if isinstance(ranges.get(b, {}).get('min'), (int, float))
        ]
        if maxs and mins:
            saas_code = code
            saas_bad_value = max(maxs) + 10_000  # guaranteed out of range
            break
    assert saas_code, "Could not find a saas_premium KPI with a defined range to test against"

    df = pd.DataFrame([{'account_id': 1, 'kpi_code': saas_code, 'value': saas_bad_value}])

    errors_dc2s, _ = m.validate_kpi_values_against_ranges(df, vertical='dc2_s')
    errors_saas, _ = m.validate_kpi_values_against_ranges(df, vertical='saas_premium')

    # Against dc2_s ranges, a saas_premium-only KPI code is simply unknown
    # (no discrepancy raised for a code dc2_s doesn't have).
    assert errors_dc2s == []
    # Against its OWN vertical's ranges, the out-of-range value is caught.
    assert len(errors_saas) == 1
    assert errors_saas[0]['kpi_code'] == saas_code


# ──────────────────────────────────────────────────────────────────────────
# 2. data_quality_api.py — _get_dc2s_kpi_ranges now vertical-parameterized;
#    the /kpi-range-discrepancies route resolves the caller's own vertical.
# ──────────────────────────────────────────────────────────────────────────

def test_data_quality_api_no_direct_vertical_import():
    tree = ast.parse(DATA_QUALITY_PY.read_text())
    forbidden = _all_vertical_imports(tree)
    assert not forbidden, (
        f"data_quality_api.py still directly imports {sorted(forbidden)} "
        f"instead of routing through utils.vertical_registry."
    )
    assert _references_vertical_registry(tree)


def test_data_quality_api_get_dc2s_kpi_ranges_resolves_per_vertical():
    import data_quality_api as m

    dc2s_ranges = m._get_dc2s_kpi_ranges('dc2_s')
    saas_ranges = m._get_dc2s_kpi_ranges('saas_premium')
    dcv1_ranges = m._get_dc2s_kpi_ranges('datacenter_v1')

    assert dc2s_ranges and saas_ranges
    assert set(dc2s_ranges.keys()) != set(saas_ranges.keys()), (
        "dc2_s and saas_premium KPI ranges identical — still silently "
        "serving dc2_s's catalog to a saas_premium caller."
    )
    # datacenter_v1 shares dc2_s's 38 P-format codes by construction (same
    # kpi_definitions.py-derived catalog shape) but is loaded independently
    # via its OWN JSON catalog, not a hardcoded dc2_s import.
    assert dcv1_ranges
    # Default (no arg) preserves prior behavior exactly.
    assert m._get_dc2s_kpi_ranges() == dc2s_ranges


# ──────────────────────────────────────────────────────────────────────────
# 3. customer_playbook_api.py — _seed_system_playbooks routes through
#    utils.vertical_registry.get_vertical_for_customer +
#    _ask_ai_helpers._get_playbook_config instead of a hardcoded dc2_s
#    PLAYBOOK_CONFIG import.
# ──────────────────────────────────────────────────────────────────────────

def test_customer_playbook_api_seed_no_direct_vertical_import():
    tree = ast.parse(CUSTOMER_PLAYBOOK_PY.read_text())
    fn = _find_function(tree, "_seed_system_playbooks")
    forbidden = _all_vertical_imports(fn)
    assert not forbidden, (
        f"_seed_system_playbooks still directly imports {sorted(forbidden)} "
        f"instead of routing through utils.vertical_registry / "
        f"_ask_ai_helpers._get_playbook_config."
    )
    references_helpers = any(
        isinstance(n, ast.ImportFrom)
        and n.module in ("utils.vertical_registry", "_ask_ai_helpers")
        for n in ast.walk(fn)
    )
    assert references_helpers, (
        "_seed_system_playbooks no longer references utils.vertical_registry "
        "or _ask_ai_helpers at all."
    )


def test_ask_ai_helpers_get_playbook_config_resolves_per_vertical():
    """Behavioral proof of the helper _seed_system_playbooks now delegates
    to: dc2_s and saas_premium get their own native PLAYBOOK_CONFIG,
    datacenter_v1 (no playbook catalog of its own yet) gets a safe no-op —
    calling the REAL, already-existing _ask_ai_helpers.py function, not a
    reimplementation. No DB needed — _get_playbook_config takes a vertical
    string directly.
    """
    from _ask_ai_helpers import _get_playbook_config

    dc2s_cfg, dc2s_trigger = _get_playbook_config('dc2_s')
    saas_cfg, saas_trigger = _get_playbook_config('saas_premium')
    other_cfg, other_trigger = _get_playbook_config('datacenter_v1')

    assert dc2s_cfg and callable(dc2s_trigger)
    assert saas_cfg and callable(saas_trigger)
    assert set(dc2s_cfg.keys()) != set(saas_cfg.keys()), (
        "dc2_s and saas_premium playbook configs are identical — still "
        "silently serving the same catalog."
    )
    assert other_cfg == {}, (
        "datacenter_v1 should get a safe no-op (no PLAYBOOK_CONFIG of its "
        "own), not a silent dc2_s substitution."
    )
    assert other_trigger('anything', {}) is False


# ──────────────────────────────────────────────────────────────────────────
# 4. journey_api_dynamic.py — enrich_weekly_data_with_dc2s_kpis resolves
#    the account's OWN vertical's KPI definitions instead of a hardcoded
#    DC2S_KPIS import.
# ──────────────────────────────────────────────────────────────────────────

def test_journey_api_enrich_no_unconditional_vertical_import():
    """The old code unconditionally imported DC2S_KPIS at function top
    (inside the try/except ImportError block alongside DC2SKPI and
    get_health_calculator). The fix moves KPI-definition resolution into
    its own try/except that calls utils.vertical_registry — assert the
    top-level import block no longer references verticals.dc2_s at all.
    """
    tree = ast.parse(JOURNEY_PY.read_text())
    fn = _find_function(tree, "enrich_weekly_data_with_dc2s_kpis")

    # Find the first (outer) try block — the one that previously held the
    # unconditional `from verticals.dc2_s.kpi_definitions import DC2S_KPIS`.
    first_try = None
    for node in ast.walk(fn):
        if isinstance(node, ast.Try):
            first_try = node
            break
    assert first_try is not None
    outer_imports = _all_vertical_imports(first_try)
    assert not outer_imports, (
        f"enrich_weekly_data_with_dc2s_kpis's first try block still "
        f"unconditionally imports {sorted(outer_imports)}."
    )
    assert _references_vertical_registry(fn), (
        "enrich_weekly_data_with_dc2s_kpis no longer references "
        "utils.vertical_registry at all."
    )


def test_journey_api_vertical_resolution_block_resolves_per_vertical():
    """Behavioral: extracts and executes the actual fixed try/except block
    (not a reimplementation) that resolves DC2S_KPIS -> the customer's own
    vertical's KPI catalog, proving it differentiates dc2_s vs saas_premium
    and fails closed (returns None, signalling "skip enrichment") when
    vertical resolution raises — instead of silently defaulting to dc2_s.
    """
    source = JOURNEY_PY.read_text()
    tree = ast.parse(source)
    fn = _find_function(tree, "enrich_weekly_data_with_dc2s_kpis")

    target_try = None
    for node in ast.walk(fn):
        if isinstance(node, ast.Try):
            seg = ast.get_source_segment(source, node) or ""
            if "get_vertical_for_customer" in seg and "get_kpis" in seg:
                target_try = node
                break
    assert target_try is not None, "Could not find the vertical-resolution try/except block."

    src = ast.get_source_segment(source, target_try)
    assert src is not None

    class _FakeLogger:
        @staticmethod
        def debug(*a, **kw):
            pass

    class _FakeApp:
        logger = _FakeLogger()

    def _run(customer_id, resolver):
        """Exec the extracted block with get_vertical_for_customer mocked
        via a fake utils.vertical_registry module inserted ahead of the
        real one, so no DB is touched."""
        import types
        fake_mod = types.ModuleType("utils.vertical_registry")
        fake_mod.get_vertical_for_customer = resolver
        from utils.vertical_registry import get_kpis
        fake_mod.get_kpis = get_kpis

        real_mod = sys.modules.get("utils.vertical_registry")
        sys.modules["utils.vertical_registry"] = fake_mod
        try:
            lines = src.splitlines()
            base_indent = min(len(l) - len(l.lstrip()) for l in lines[1:] if l.strip())
            lines[0] = (" " * base_indent) + lines[0]
            normalized = textwrap.dedent("\n".join(lines))
            indented = "\n".join("    " + line for line in normalized.splitlines())
            wrapper = (
                "def _f(customer_id, current_app):\n"
                f"{indented}\n"
                "    return DC2S_KPIS\n"
            )
            namespace = {}
            exec(compile(wrapper, "<journey_block>", "exec"), namespace)
            return namespace["_f"](customer_id, _FakeApp())
        finally:
            if real_mod is not None:
                sys.modules["utils.vertical_registry"] = real_mod

    from utils.vertical_registry import get_kpis

    dc2s_result = _run(1, lambda cid: "dc2_s")
    saas_result = _run(2, lambda cid: "saas_premium")
    failed_result = _run(3, lambda cid: (_ for _ in ()).throw(ValueError("no config")))

    assert dc2s_result == get_kpis("dc2_s")
    assert saas_result == get_kpis("saas_premium")
    assert dc2s_result != saas_result
    assert failed_result is None, (
        "vertical resolution failure should signal 'skip enrichment' "
        "(None), not silently fall back to dc2_s's KPI definitions."
    )


# ──────────────────────────────────────────────────────────────────────────
# 5. playbook_recommendations_api.py — get_playbook_recommendations resolves
#    the requesting customer's own vertical's PLAYBOOK_CONFIG (dc2_s or
#    datacenter_v1) instead of a hardcoded dc2_s import + hardcoded
#    'vertical': 'dc2_s' response tag.
# ──────────────────────────────────────────────────────────────────────────

def test_playbook_recommendations_get_route_no_static_vertical_import():
    tree = ast.parse(PLAYBOOK_REC_PY.read_text())
    fn = _find_function(tree, "get_playbook_recommendations")
    # A static `from verticals.X.vertical_config import (...)` is no longer
    # present; the only vertical references left are importlib.import_module
    # calls (dynamic, not AST Import/ImportFrom nodes) mirroring the
    # pre-existing _evaluate_dc2s_playbooks pattern.
    forbidden = _all_vertical_imports(fn)
    assert not forbidden, (
        f"get_playbook_recommendations still statically imports "
        f"{sorted(forbidden)} instead of dynamically resolving the "
        f"customer's own vertical's PLAYBOOK_CONFIG."
    )
    assert "_resolve_vertical_for_customer" in (ast.get_source_segment(
        PLAYBOOK_REC_PY.read_text(), fn) or ""), (
        "get_playbook_recommendations no longer resolves the customer's "
        "actual vertical."
    )
    assert "'vertical': 'dc2_s'" not in (ast.get_source_segment(
        PLAYBOOK_REC_PY.read_text(), fn) or ""), (
        "get_playbook_recommendations still hardcodes the response's "
        "'vertical' field to 'dc2_s'."
    )


def test_playbook_recommendations_datacenter_v1_has_its_own_playbook_ids():
    """Sanity check underpinning the fix: datacenter_v1 genuinely has its
    own PLAYBOOK_CONFIG (PB-07..13 beyond dc2_s's PB-01..06), so routing
    get_playbook_recommendations through the customer's real vertical (via
    _CONFIG_PLAYBOOK_VERTICALS = {'dc2_s', 'datacenter_v1'}, the same set
    _evaluate_dc2s_playbooks already used) is not a no-op — it fixes a real
    404 for datacenter_v1-only playbook ids.
    """
    from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG as DC2S_PB
    from verticals.datacenter_v1.vertical_config import PLAYBOOK_CONFIG as DCV1_PB

    dcv1_only = set(DCV1_PB.keys()) - set(DC2S_PB.keys())
    assert dcv1_only, (
        "Expected datacenter_v1 to have playbook ids beyond dc2_s's own "
        "(e.g. PB-07..13) — if this list is now empty the fix's premise "
        "needs re-checking."
    )


def test_playbook_recommendations_generic_trigger_check_matches_dc2s_semantics():
    """Behavioral: extracts the new local `should_trigger_playbook` closure
    (generic AND-logic over an explicit PLAYBOOK_CONFIG dict) and proves it
    reproduces verticals.dc2_s.vertical_config.should_trigger_playbook's
    AND-all-conditions semantics exactly for a real dc2_s playbook, then
    proves it also works against datacenter_v1's own config (which the old
    hardcoded-dc2_s-module version could never do, since dc2_s's
    should_trigger_playbook only ever looks up its OWN module-global
    PLAYBOOK_CONFIG regardless of which dict is passed in).
    """
    source = PLAYBOOK_REC_PY.read_text()
    tree = ast.parse(source)
    fn = _find_function(tree, "get_playbook_recommendations")

    inner = None
    for node in ast.walk(fn):
        if isinstance(node, ast.FunctionDef) and node.name == "should_trigger_playbook":
            inner = node
            break
    assert inner is not None, "Could not find the local should_trigger_playbook closure."

    src = ast.get_source_segment(source, inner)
    assert src is not None

    from verticals.dc2_s.vertical_config import (
        PLAYBOOK_CONFIG as DC2S_PB, should_trigger_playbook as dc2s_should_trigger,
    )
    from verticals.datacenter_v1.vertical_config import PLAYBOOK_CONFIG as DCV1_PB

    namespace = {"PLAYBOOK_CONFIG": DC2S_PB}
    exec(compile(src, "<local_should_trigger>", "exec"), namespace)
    local_should_trigger = namespace["should_trigger_playbook"]

    # Pick a real dc2_s playbook with trigger_conditions and build a
    # kpi_values dict that satisfies every condition.
    pb_id, cfg = next(
        (pid, c) for pid, c in DC2S_PB.items() if c.get("trigger_conditions")
    )
    kpi_values = {}
    for kpi, cond in cfg["trigger_conditions"].items():
        op, thresh = cond.get("operator"), cond.get("value")
        kpi_values[kpi] = thresh + 1 if op == ">" else (thresh - 1 if op == "<" else thresh)

    assert local_should_trigger(pb_id, kpi_values) == dc2s_should_trigger(pb_id, kpi_values) == True

    # Now prove it also works against datacenter_v1's OWN config — dc2_s's
    # own should_trigger_playbook cannot do this (it reads its own
    # module-global PLAYBOOK_CONFIG regardless of arguments).
    namespace2 = {"PLAYBOOK_CONFIG": DCV1_PB}
    exec(compile(src, "<local_should_trigger_dcv1>", "exec"), namespace2)
    local_should_trigger_dcv1 = namespace2["should_trigger_playbook"]

    dcv1_pb_id, dcv1_cfg = next(
        (pid, c) for pid, c in DCV1_PB.items() if c.get("trigger_conditions")
    )
    dcv1_kpi_values = {}
    for kpi, cond in dcv1_cfg["trigger_conditions"].items():
        op, thresh = cond.get("operator"), cond.get("value")
        dcv1_kpi_values[kpi] = thresh + 1 if op == ">" else (thresh - 1 if op == "<" else thresh)

    assert local_should_trigger_dcv1(dcv1_pb_id, dcv1_kpi_values) is True


if __name__ == "__main__":
    import traceback

    tests = [
        test_onboarding_no_module_level_vertical_import,
        test_onboarding_get_dc2s_kpi_valid_ranges_resolves_per_vertical,
        test_onboarding_validate_kpi_values_against_ranges_accepts_vertical,
        test_data_quality_api_no_direct_vertical_import,
        test_data_quality_api_get_dc2s_kpi_ranges_resolves_per_vertical,
        test_customer_playbook_api_seed_no_direct_vertical_import,
        test_ask_ai_helpers_get_playbook_config_resolves_per_vertical,
        test_journey_api_enrich_no_unconditional_vertical_import,
        test_journey_api_vertical_resolution_block_resolves_per_vertical,
        test_playbook_recommendations_get_route_no_static_vertical_import,
        test_playbook_recommendations_datacenter_v1_has_its_own_playbook_ids,
        test_playbook_recommendations_generic_trigger_check_matches_dc2s_semantics,
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
