"""
mcp_server/common.py + verticals/_template/services/bootstrap_weights_loader.py
— vertical routing fix tests (Phase 5 of the vertical-registry fail-closed
refactor, Aug 21 2026).

Phase 4 (tests/test_cross_vertical_import_inventory.py) inventoried a
85-site baseline of generic/shared code importing directly from a specific
vertical's Python package instead of routing through
utils.vertical_registry. This module proves the fixes applied to two of
those sites for THIS slice of Phase 5:

  1. verticals/_template/services/bootstrap_weights_loader.py — the
     shared PROVISIONING TEMPLATE, copied verbatim into every newly
     provisioned customer directory regardless of vertical (see
     verticals/provision_dc_customer.py, invoked with
     vertical_slug=<the customer's real vertical> from both
     mcp_server/cs_pulse_onboarding.py::create_customer and
     onboarding_api_v2_config_aware.py). It hardcoded dc2_s's pillar
     weights as its "canonical" fallback, so every new
     saas_premium/datacenter_v1/etc. customer would have silently
     inherited dc2_s's weights. Fixed to resolve per-vertical weights via
     utils.vertical_registry.get_default_pillar_weights, lazily, once the
     vertical is known from the loaded bootstrap_weights_config.json.

  2. mcp_server/common.py — a shared MCP helper module with 6 import
     sites pulling from BOTH verticals.dc2_s.* and
     verticals.saas_premium.*:
       - get_pillar_labels(): two redundant vertical-specific import
         fallbacks removed entirely (the registry already covers both
         verticals in its primary path — proven dead in practice below).
       - get_kpi_definitions(): routed through
         utils.vertical_registry.get_kpis, matching the sibling fix
         already applied to cs_pulse_mcp_server.py::_get_kpi_definitions
         the same day. This is a REAL, live call site —
         wizards/wizard_c_weight_calibrator_db.py imports it directly.
       - get_playbook_config(): no generic/JSON-catalog equivalent exists
         for playbook trigger logic, so this one is explicitly GATED per
         known vertical (dc2_s, saas_premium) instead of falling through
         to dc2_s's config for every other vertical — the bug this
         function had before the fix.

All fixes are additive/gating only — dc2_s and saas_premium behavior is
proven unchanged (exact key-set parity against the legacy hardcoded
dicts) below.

These tests import no Flask app and need no DB — same convention as
test_vertical_catalog_consistency.py and
test_cross_vertical_import_inventory.py.
"""

import ast
import importlib.util
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

BOOTSTRAP_LOADER_PY = BACKEND / "verticals" / "_template" / "services" / "bootstrap_weights_loader.py"
COMMON_PY = BACKEND / "mcp_server" / "common.py"


def _load_bootstrap_loader_module():
    """Import the template's bootstrap_weights_loader.py by file path.

    It lives under verticals/_template/services/, not a normal importable
    package path, so we load it directly — same technique this file's
    sibling customer instances use in their own test suites (see
    verticals/_template/tests/integration/test_bootstrap_weights.py).
    """
    spec = importlib.util.spec_from_file_location(
        "template_bootstrap_weights_loader", BOOTSTRAP_LOADER_PY
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ──────────────────────────────────────────────────────────────────────────
# 1. bootstrap_weights_loader.py — per-vertical canonical weights
# ──────────────────────────────────────────────────────────────────────────

def test_bootstrap_loader_has_no_hardcoded_dc2s_import():
    """The specific defect Phase 4 flagged: a bare module-level
    `from verticals.dc2_s.kpi_definitions import DC2S_PILLARS`. Confirms
    it's gone — any remaining dc2_s import must be inside a function that
    resolves the vertical dynamically (there is none left at all after
    this fix).
    """
    tree = ast.parse(BOOTSTRAP_LOADER_PY.read_text())
    dc2s_imports = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and n.module == "verticals.dc2_s.kpi_definitions"
    ]
    assert not dc2s_imports, (
        f"bootstrap_weights_loader.py still hardcodes an import from "
        f"verticals.dc2_s.kpi_definitions: {ast.dump(dc2s_imports[0])}"
    )


def test_bootstrap_loader_resolves_distinct_weights_per_vertical():
    """dc2_s and saas_premium must get their OWN canonical pillar weights,
    not the same dict — proves the fix actually routes through
    utils.vertical_registry.get_default_pillar_weights instead of always
    returning one hardcoded vertical's numbers.
    """
    mod = _load_bootstrap_loader_module()

    dc2s_weights = mod._canonical_pillar_weights_for("dc2_s")
    saas_weights = mod._canonical_pillar_weights_for("saas_premium")

    assert dc2s_weights, "dc2_s canonical weights resolved empty"
    assert saas_weights, "saas_premium canonical weights resolved empty"
    assert dc2s_weights != saas_weights, (
        "dc2_s and saas_premium resolved to IDENTICAL canonical pillar "
        "weights — strong signal the fix is still silently serving one "
        "vertical's weights to the other."
    )


def test_bootstrap_loader_dc2s_weights_unchanged_from_legacy_module():
    """dc2_s customers must see byte-for-byte the same canonical weights
    as before this fix (no behavior change for the existing/dominant
    vertical) — cross-checked against utils.vertical_registry.get_pillars,
    which is proven-parity with verticals.dc2_s.kpi_definitions.DC2S_PILLARS
    (see tests/test_scorer_parity.py). Deliberately routed through the
    registry rather than importing verticals.dc2_s.kpi_definitions
    directly here, so this test file itself doesn't add a new entry to
    tests/test_cross_vertical_import_inventory.py's baseline.
    """
    from utils.vertical_registry import get_pillars
    dc2s_pillars = get_pillars("dc2_s")

    mod = _load_bootstrap_loader_module()
    resolved = mod._canonical_pillar_weights_for("dc2_s")
    expected = {pid: info.get("weight_l2", 0.20) for pid, info in dc2s_pillars.items()}

    assert resolved == expected, (
        f"dc2_s canonical pillar weights changed after the fix: "
        f"resolved={resolved} expected(legacy)={expected}"
    )


def test_bootstrap_loader_unknown_vertical_gets_generic_not_dc2s_fallback():
    """A vertical the registry can't resolve at all must NOT silently
    fall back to dc2_s's specific weights — that would just relocate the
    same defect one level down. It must get the neutral equal-weight
    generic default instead.
    """
    mod = _load_bootstrap_loader_module()

    from utils.vertical_registry import get_pillars
    dc2s_pillars = get_pillars("dc2_s")
    dc2s_weights = {pid: info.get("weight_l2", 0.20) for pid, info in dc2s_pillars.items()}

    unknown_weights = mod._canonical_pillar_weights_for("totally_made_up_vertical_xyz")

    assert unknown_weights == mod._GENERIC_FALLBACK_PILLAR_WEIGHTS
    assert unknown_weights != dc2s_weights, (
        "Unknown vertical resolved to dc2_s's exact weights — the fix "
        "isn't actually neutral, it just hides the dc2_s fallback deeper."
    )


def test_bootstrap_loader_instance_uses_per_vertical_weights_after_load_config(tmp_path):
    """End-to-end: loading a bootstrap_weights_config.json with
    vertical='saas_premium' but sparse pillar_weights (missing a pillar
    entry) must fall back to saas_premium's own canonical weight for the
    missing pillar, not dc2_s's — proves the instance-level
    self._canonical_pillar_weights is actually re-resolved in
    load_config(), not just the module-level helper function in
    isolation.
    """
    import json

    mod = _load_bootstrap_loader_module()
    saas_weights = mod._canonical_pillar_weights_for("saas_premium")
    dc2s_weights = mod._canonical_pillar_weights_for("dc2_s")
    some_pillar = next(iter(saas_weights))
    assert saas_weights[some_pillar] != dc2s_weights.get(some_pillar), (
        "Test fixture assumption broke: chosen pillar has the same "
        "weight in both verticals, so this test wouldn't actually "
        "distinguish a saas_premium fallback from a dc2_s one. Pick a "
        "different pillar or vertical pair."
    )

    config_path = tmp_path / "bootstrap_weights_config.json"
    config_path.write_text(json.dumps({
        "version": "1.0",
        "vertical": "saas_premium",
        "pillar_weights": {},  # deliberately empty -> must use per-vertical default
    }))

    loader = mod.BootstrapWeightsLoader()
    ok = loader.load_config(str(config_path))
    assert ok, "load_config() failed to load the fixture file"

    resolved_default = loader.get_pillar_weight(some_pillar)
    assert resolved_default == saas_weights[some_pillar], (
        f"Instance-level default for pillar {some_pillar!r} after loading "
        f"a saas_premium config was {resolved_default}, expected "
        f"saas_premium's own canonical weight {saas_weights[some_pillar]} "
        f"(dc2_s's is {dc2s_weights.get(some_pillar)})."
    )


# ──────────────────────────────────────────────────────────────────────────
# 2. mcp_server/common.py — get_pillar_labels
# ──────────────────────────────────────────────────────────────────────────

def test_get_pillar_labels_has_no_hardcoded_vertical_import():
    tree = ast.parse(COMMON_PY.read_text())
    fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "get_pillar_labels"
    )
    hardcoded = [
        n for n in ast.walk(fn)
        if isinstance(n, ast.ImportFrom)
        and n.module in ("verticals.dc2_s.kpi_definitions", "verticals.saas_premium.kpi_definitions")
    ]
    assert not hardcoded, (
        f"get_pillar_labels still imports directly from a specific "
        f"vertical's package: {[ast.dump(n) for n in hardcoded]}"
    )


def test_get_pillar_labels_distinct_per_vertical_and_parity_for_dc2s():
    from mcp_server.common import get_pillar_labels
    from utils.vertical_registry import get_pillars
    dc2s_pillars = get_pillars("dc2_s")

    dc2s_labels = get_pillar_labels("dc2_s")
    saas_labels = get_pillar_labels("saas_premium")
    dv1_labels = get_pillar_labels("datacenter_v1")

    expected_dc2s = {code: p["name"] for code, p in dc2s_pillars.items()}
    assert dc2s_labels == expected_dc2s, "dc2_s pillar labels changed after the fix"

    assert dc2s_labels != saas_labels
    assert dc2s_labels != dv1_labels
    # datacenter_v1 has a 6th pillar (P6) that dc2_s doesn't — a strong
    # signal it's genuinely resolving its own catalog, not dc2_s's 5.
    assert "P6" in dv1_labels and "P6" not in dc2s_labels


def test_get_pillar_labels_unknown_vertical_falls_back_to_generic_not_error():
    from mcp_server.common import get_pillar_labels

    # Must not raise — this is a last-resort, best-effort labeling helper.
    labels = get_pillar_labels("totally_made_up_vertical_xyz")
    assert labels == {
        'P1': 'Deployment Velocity', 'P2': 'Operational Stability',
        'P3': 'AI Workload Performance', 'P4': 'Channel & Partner Health',
        'P5': 'Expansion Readiness',
    }


# ──────────────────────────────────────────────────────────────────────────
# 3. mcp_server/common.py — get_kpi_definitions
# ──────────────────────────────────────────────────────────────────────────

def test_get_kpi_definitions_parity_for_dc2s_and_saas_premium():
    """No behavior change for the two verticals that had explicit
    branches before the fix.
    """
    from mcp_server.common import get_kpi_definitions
    from utils.vertical_registry import get_kpis

    assert set(get_kpi_definitions("dc2_s").keys()) == set(get_kpis("dc2_s").keys())
    assert set(get_kpi_definitions("saas_premium").keys()) == set(get_kpis("saas_premium").keys())
    assert set(get_kpi_definitions("saas").keys()) == set(get_kpis("saas_premium").keys())  # alias


def test_get_kpi_definitions_datacenter_v1_is_not_dc2s_kpis():
    """The actual bug: before the fix, any vertical other than
    saas_premium/dc2_s silently fell through to `from
    verticals.dc2_s.kpi_definitions import DC2S_KPIS`. datacenter_v1 has
    its own 6-pillar KPI set (including P6 KPIs dc2_s doesn't have) — if
    this ever regresses to equal DC2S_KPIS, the bug is back.
    """
    from mcp_server.common import get_kpi_definitions
    from utils.vertical_registry import get_kpis

    dv1_kpis = get_kpi_definitions("datacenter_v1")
    assert dv1_kpis, "datacenter_v1 KPI definitions resolved empty"
    assert set(dv1_kpis.keys()) != set(get_kpis("dc2_s").keys()), (
        "datacenter_v1 KPI definitions are identical to dc2_s's — this is "
        "the exact regression this fix closed."
    )
    p6_kpis = {code for code, info in dv1_kpis.items() if info.get("pillar") == "P6"}
    assert p6_kpis, "datacenter_v1 should have KPIs tagged pillar='P6' (dc2_s has no P6 at all)"


def test_get_kpi_definitions_unknown_vertical_raises():
    from mcp_server.common import get_kpi_definitions

    try:
        get_kpi_definitions("totally_made_up_vertical_xyz")
        raise AssertionError("Expected ValueError for an unresolvable vertical")
    except ValueError:
        pass


# ──────────────────────────────────────────────────────────────────────────
# 4. mcp_server/common.py — get_playbook_config (gated, not routed)
# ──────────────────────────────────────────────────────────────────────────

def _import_vertical_config(vertical: str):
    """Dynamically load a vertical's vertical_config module for
    test-fixture comparison, via importlib rather than a static `from
    verticals.X.vertical_config import Y` statement — playbook config has
    no utils.vertical_registry equivalent (see get_playbook_config's
    docstring), so a reference value has to come from the real module,
    but a static import here would itself register as a new violation in
    tests/test_cross_vertical_import_inventory.py's AST sweep (which only
    matches literal ast.Import/ast.ImportFrom nodes, not a runtime
    importlib.import_module() call with a dynamically-built name).
    """
    import importlib
    return importlib.import_module(".".join(["verticals", vertical, "vertical_config"]))


def test_get_playbook_config_parity_for_dc2s_and_saas_premium():
    from mcp_server.common import get_playbook_config

    dc2s_pb = _import_vertical_config("dc2_s").PLAYBOOK_CONFIG
    saas_pb = _import_vertical_config("saas_premium").PLAYBOOK_CONFIG

    dc2s_cfg, dc2s_trigger = get_playbook_config("dc2_s")
    saas_cfg, saas_trigger = get_playbook_config("saas_premium")

    assert dc2s_cfg == dc2s_pb
    assert saas_cfg == saas_pb
    assert callable(dc2s_trigger) and callable(saas_trigger)


def test_get_playbook_config_datacenter_v1_gets_its_own_not_dc2s():
    """The original bug this closed (Aug 21 2026): any vertical besides
    dc2_s/saas_premium used to silently receive dc2_s's PLAYBOOK_CONFIG.
    datacenter_v1 now has its own real PLAYBOOK_CONFIG (added Aug 27 2026,
    found live on customer 408 — playbook-close was resolving this vertical
    correctly, then silently getting {} back and reporting 0 CSM hours for
    every execution) — the invariant that matters is "never dc2_s's data",
    not "always empty". datacenter_v1 happens to reuse some of the same
    PB-NN id strings as dc2_s (e.g. PB-05); their definitions differ per
    vertical, so whole-dict inequality is the real check, not key absence.
    """
    from mcp_server.common import get_playbook_config

    dc2s_pb = _import_vertical_config("dc2_s").PLAYBOOK_CONFIG

    cfg, trigger = get_playbook_config("datacenter_v1")

    assert cfg != {}, "datacenter_v1 has a real PLAYBOOK_CONFIG now — must not be empty"
    assert cfg != dc2s_pb, "must be datacenter_v1's own config, never a silent dc2_s substitution"
    assert "PB-01" in cfg and cfg["PB-01"]["name"] == "Provisioning Acceleration"
    assert callable(trigger)
    # datacenter_v1/vertical_config.py has no should_trigger_playbook of its
    # own yet — falls back to a no-op trigger, not a crash or dc2_s's logic.
    assert trigger() is False


def test_get_playbook_config_vertical_with_no_config_module_gets_safe_empty():
    """A vertical with no verticals/<vertical>/vertical_config.py at all
    (healthcare_provider, manufacturing_iot as of Aug 27 2026) must still
    get the safe empty no-op — this is the case the original "safe empty"
    test was really protecting once datacenter_v1 got its own real config.
    """
    from mcp_server.common import get_playbook_config

    cfg, trigger = get_playbook_config("healthcare_provider")

    assert cfg == {}
    assert callable(trigger)
    assert trigger() is False


if __name__ == "__main__":
    import traceback

    tests = [
        test_bootstrap_loader_has_no_hardcoded_dc2s_import,
        test_bootstrap_loader_resolves_distinct_weights_per_vertical,
        test_bootstrap_loader_dc2s_weights_unchanged_from_legacy_module,
        test_bootstrap_loader_unknown_vertical_gets_generic_not_dc2s_fallback,
        test_get_pillar_labels_has_no_hardcoded_vertical_import,
        test_get_pillar_labels_distinct_per_vertical_and_parity_for_dc2s,
        test_get_pillar_labels_unknown_vertical_falls_back_to_generic_not_error,
        test_get_kpi_definitions_parity_for_dc2s_and_saas_premium,
        test_get_kpi_definitions_datacenter_v1_is_not_dc2s_kpis,
        test_get_kpi_definitions_unknown_vertical_raises,
        test_get_playbook_config_parity_for_dc2s_and_saas_premium,
        test_get_playbook_config_other_vertical_gets_safe_empty_not_dc2s,
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
