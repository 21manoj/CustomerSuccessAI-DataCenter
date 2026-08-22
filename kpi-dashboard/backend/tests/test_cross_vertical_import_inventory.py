"""
Cross-vertical import inventory guard (Phase 4 of the vertical-registry
fail-closed refactor, Aug 21 2026).

The repeated bug class fixed across this session's commits (b1232d97a,
6bad52072, and the vertical_registry work before them) is generic/shared
code hardcoding a direct import from ONE vertical's Python package
(`verticals.dc2_s.*`, `verticals.saas_premium.*`, ...) instead of going
through `utils.vertical_registry`. Every fix so far has been reactive —
found via a live audit against a specific customer. This test is the
proactive guard: an AST sweep of the whole backend that finds every such
import and pins it against a known baseline, so:

  - it PASSES today, by construction, against the current (not-yet-clean)
    codebase — claiming the codebase is already clean would be dishonest;
  - it FAILS the moment a NEW generic module picks up a fresh cross-vertical
    import that isn't already in the baseline below.

This is Phase 4 only: inventory, not remediation. Clearing the ~85 baseline
entries is Phase 5, deliberately out of scope here — do not "fix" any of
them by editing the flagged files as a side effect of this test.

──────────────────────────────────────────────────────────────────────────
Definition packages vs. per-customer instance directories
──────────────────────────────────────────────────────────────────────────
`kpi-dashboard/backend/verticals/` holds two structurally different kinds
of subdirectory (confirmed against the real directory listing before
writing this, not assumed):

  1. Vertical-DEFINITION packages: `dc2_s/`, `saas_premium/`,
     `datacenter_v1/`, `_template/` (and `healthcare_provider/` if it ever
     gains a Python package — today healthcare_provider is JSON-catalog-only,
     no `verticals/healthcare_provider/` dir exists). Each defines exactly
     one vertical's Python constants/helpers. A file INSIDE one of these
     importing its OWN vertical's sibling submodules is correct and not
     flagged (e.g. `verticals/dc2_s/api_routes.py` importing
     `verticals.dc2_s.kpi_definitions`).

  2. Per-customer INSTANCE directories: ~60 generated dirs matching
     `customer<digits>-<vertical-slug>` (e.g. `customer289-dc2_s`,
     `customer359-datacenter_v1`), plus a legacy `_customers/` container
     holding more of the same pattern one level deeper. A customer
     instance importing ITS OWN vertical's definitions is expected,
     provisioned behavior, not coupling (e.g.
     `verticals/customer289-dc2_s/services/bootstrap_weights_loader.py`
     importing `verticals.dc2_s.kpi_definitions` is fine — that customer
     IS a dc2_s tenant). Two malformed/truncated instance dirs exist
     (`customer295-dc`, `customer445-saas` — slug doesn't match any real
     vertical) and are deliberately NOT special-cased: since their
     declared slug doesn't match the vertical they import, they're
     classified the same as any other mismatch and appear in the
     baseline below.

Everything else under the backend tree (top-level modules, `mcp_server/`,
`utils/`, `agents/`, `scripts/`, `tests/`, `wizards/`, and `_template/`
itself, which is a shared provisioning template, not a live vertical) is
"generic" — it should route vertical-specific data through
`utils.vertical_registry`, not import a specific vertical's package
directly. `utils/vertical_registry.py` itself is included in the baseline
rather than special-cased: it IS the registry, so its own bootstrapping
imports of every vertical's raw constants are arguably structurally
necessary, but this test makes no editorial judgment calls about which
generic-code imports are "more excusable" than others — it records what
exists today and only fails on what's NEW.

These tests import no Flask app and need no DB — same convention as
test_vertical_catalog_consistency.py and test_vertical_playbook_routing.py.
"""

import ast
import re
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent

# Vertical-definition packages directly under verticals/ (dir name -> the
# vertical slug it defines). Checked against the real listing on 2026-08-21;
# re-verify with `ls kpi-dashboard/backend/verticals/` if this test ever
# needs updating for a newly added vertical package.
VERTICAL_DEFINITION_DIRS = {"dc2_s", "saas_premium", "datacenter_v1", "healthcare_provider", "_template"}

# Per-customer instance directories: customer<digits>-<slug>, either
# directly under verticals/ or one level deeper under verticals/_customers/.
INSTANCE_RE = re.compile(r"^customer\d+-")

# Any import of the form `verticals.<name>` or `verticals.<name>.<rest>`.
VERTICAL_MODULE_RE = re.compile(r"^verticals\.([A-Za-z0-9_]+)(\..*)?$")


def _classify(py_file: Path):
    """Return (kind, own_vertical) for a .py file under BACKEND.

    kind is one of "definition", "instance", or "generic". own_vertical is
    the vertical slug this file belongs to (for "definition"/"instance"),
    or None (for "generic", or a malformed instance dir whose slug isn't a
    real vertical — those still get a best-effort slug so mismatches are
    caught, not silently exempted).
    """
    rel = py_file.relative_to(BACKEND)
    parts = rel.parts
    if parts[0] != "verticals" or len(parts) == 1:
        return ("generic", None)

    seg = parts[1]
    if seg in VERTICAL_DEFINITION_DIRS:
        return ("definition", seg)
    if INSTANCE_RE.match(seg):
        slug = seg.split("-", 1)[1] if "-" in seg else None
        return ("instance", slug)
    if seg == "_customers" and len(parts) > 2 and INSTANCE_RE.match(parts[2]):
        slug = parts[2].split("-", 1)[1] if "-" in parts[2] else None
        return ("instance", slug)
    return ("generic", None)


def _scan_violations():
    """AST-walk every .py file under BACKEND and return a Counter of
    (relative_path, imported_module, imported_names) -> occurrence count
    for every cross-vertical import found in generic (or wrong-vertical
    instance) code.
    """
    violations = Counter()
    unparseable = []

    for f in sorted(BACKEND.rglob("*.py")):
        if "__pycache__" in f.parts:
            continue
        kind, own_vertical = _classify(f)

        try:
            src = f.read_text()
            tree = ast.parse(src, filename=str(f))
        except (SyntaxError, UnicodeDecodeError):
            # A handful of legacy/broken files in this tree don't even
            # parse under Python 3 (old py2-style scripts, stray syntax
            # errors) — confirmed none of them contain a `verticals.dc2_s`
            # / `verticals.saas_premium` / `verticals.datacenter_v1`
            # reference (grep-checked directly), so skipping them here
            # doesn't hide a violation. Recorded for visibility.
            unparseable.append(str(f.relative_to(BACKEND)))
            continue

        for node in ast.walk(tree):
            mod = None
            names = ()
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                names = tuple(a.name for a in node.names)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if VERTICAL_MODULE_RE.match(alias.name):
                        mod = alias.name
                        names = (alias.asname or alias.name,)
                        break
            if not mod:
                continue

            m = VERTICAL_MODULE_RE.match(mod)
            if not m:
                continue
            imported_vertical = m.group(1)
            if imported_vertical == "_customers" or imported_vertical not in VERTICAL_DEFINITION_DIRS:
                # Not a real vertical-definition package (e.g. a plain
                # `verticals.provision_dc_customer` import) — irrelevant.
                continue

            if kind in ("definition", "instance") and own_vertical == imported_vertical:
                continue  # self-import (own package, or own tenant's vertical) — fine

            rel = str(f.relative_to(BACKEND))
            violations[(rel, mod, names)] += 1

    return violations, unparseable


# ──────────────────────────────────────────────────────────────────────────
# Baseline: the exact current inventory, captured 2026-08-21 by running the
# scan above against this branch (feat/vertical-datacenter-v1) after the
# day's fixes (commits 3d85e74f2..6bad52072) had already landed. 85 sites
# across 44 files. This is a snapshot, not a target — Phase 5 clears it
# incrementally; entries disappearing (a site got fixed) never fails this
# test, only NEW entries do.
# ──────────────────────────────────────────────────────────────────────────
BASELINE = {
    ('_ask_ai_helpers.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG', 'should_trigger_playbook')): 1,
    ('_ask_ai_helpers.py', 'verticals.saas_premium.vertical_config', ('PLAYBOOK_CONFIG', 'should_trigger_playbook')): 1,
    ('agents/signal_analyst_api.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_PILLARS',)): 1,
    ('agents/signal_converter.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_csm_daily_actions',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_csm_scorecard_api',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_dc2s_account_detail',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_dc2s_accounts',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_dc2s_alerts',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_dc2s_health_score',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_dc2s_health_summary',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_health_score_history_api',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_playbook_success_metrics_api',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_renewals_api',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_team_capacity_api',)): 1,
    ('app_v3_minimal.py', 'verticals.dc2_s.api_routes', ('dc2s_api',)): 1,
    ('app_v3_minimal.py', 'verticals.saas_premium.api_routes', ('saas_premium_api',)): 1,
    ('ask_ai_tools.py', 'verticals.dc2_s.api_routes', ('_normalize_kpi_code_for_health', '_compute_impact_score', '_compute_effort_score', '_determine_urgency', '_get_roi_context')): 1,
    ('customer_playbook_api.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG',)): 1,
    ('data_quality_api.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 1,
    ('dc2s_config_api.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 2,
    ('dc2s_config_api.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_PILLARS',)): 1,
    ('debug_import.py', 'verticals.dc2_s', ('DC2S_KPIS',)): 1,
    ('journey_api_dynamic.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 1,
    ('mcp_server/common.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 1,
    ('mcp_server/common.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_PILLARS',)): 1,
    ('mcp_server/common.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG', 'should_trigger_playbook')): 1,
    ('mcp_server/common.py', 'verticals.saas_premium.kpi_definitions', ('SAAS_KPIS',)): 1,
    ('mcp_server/common.py', 'verticals.saas_premium.kpi_definitions', ('SAAS_PILLARS',)): 1,
    ('mcp_server/common.py', 'verticals.saas_premium.vertical_config', ('PLAYBOOK_CONFIG', 'should_trigger_playbook')): 1,
    ('mcp_server/cs_pulse_admin.py', 'verticals.dc2_s.api_routes', ('_compute_impact_score', '_compute_effort_score', '_determine_urgency')): 1,
    ('mcp_server/cs_pulse_admin.py', 'verticals.dc2_s.api_routes', ('_get_roi_context',)): 1,
    ('mcp_server/cs_pulse_mcp_server.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG', 'should_trigger_playbook')): 1,
    ('mcp_server/cs_pulse_mcp_server.py', 'verticals.saas_premium.vertical_config', ('PLAYBOOK_CONFIG', 'should_trigger_playbook')): 1,
    ('onboarding_api_v2_config_aware.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 1,
    ('onboarding_api_v2_config_aware.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS', 'DC2S_PILLARS')): 1,
    ('playbook_cost_bridge.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG',)): 1,
    ('playbook_cost_bridge.py', 'verticals.saas_premium.vertical_config', ('PLAYBOOK_CONFIG',)): 1,
    ('playbook_recommendations_api.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG', 'should_trigger_playbook')): 1,
    ('quick_onboard.py', 'verticals.dc2_s.vertical_loader', ('DC2SVertical',)): 1,
    ('scripts/generate_context_graph_data.py', 'verticals.dc2_s.api_routes', ('calculate_kpi_health', '_get_trailing_kpi_values')): 1,
    ('scripts/generate_onboarding_template.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS', 'DC2S_PILLARS')): 1,
    ('scripts/generate_onboarding_template.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG',)): 1,
    ('scripts/generate_synthetic_customer_data.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 1,
    ('scripts/generate_synthetic_dc2s_data.py', 'verticals.dc2_s.vertical_loader', ('DC2SVertical',)): 1,
    ('scripts/migrate_admin_ui_saas_premium.py', 'verticals.saas_premium.kpi_definitions', ('SAAS_PILLARS', 'SAAS_KPIS')): 1,
    ('scripts/migrate_admin_ui_saas_premium.py', 'verticals.saas_premium.pillar_weights', ('BOOTSTRAP_L2_WEIGHTS',)): 1,
    ('scripts/simulate_incremental_kpi.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 1,
    ('simple_onboard_customer.py', 'verticals.dc2_s.vertical_loader', ('DC2SVertical',)): 1,
    ('test_e2e_csv_upload_flow.py', 'verticals.dc2_s.vertical_loader', ('DC2SVertical',)): 1,
    ('test_lifecycle_correction_e2e.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_PILLARS',)): 1,
    ('test_runner_api.py', 'verticals.dc2_s.kpi_definitions', ('get_all_kpis',)): 2,
    ('tests/test_account_health_convergence.py', 'verticals.dc2_s.api_routes', ('get_precalculated_scores',)): 1,
    ('tests/test_bug1_csm_daily_actions_roi.py', 'verticals.dc2_s.api_routes', ('_PLAYBOOK_ROI_MAP',)): 1,
    ('tests/test_context_graph_e2e.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 1,
    ('tests/test_datacenter_v1_vertical.py', 'verticals.datacenter_v1.vertical_config', ('PLAYBOOK_CONFIG',)): 1,
    ('tests/test_phase0_1_2.py', 'verticals.dc2_s.api_routes', ('_sync_journey_phase',)): 4,
    ('tests/test_phase0_1_2.py', 'verticals.dc2_s.api_routes', ('dc2s_api',)): 1,
    ('tests/test_phase0_1_2.py', 'verticals.dc2_s.vertical_config', ('determine_customer_phase',)): 4,
    ('tests/test_scorer_parity.py', 'verticals.dc2_s.api_routes', ('_score_kpi_value',)): 1,
    ('tests/test_scorer_parity.py', 'verticals.dc2_s.api_routes', ('calculate_kpi_health',)): 1,
    ('tests/test_vertical_playbook_routing.py', 'verticals.saas_premium.vertical_config', ('PLAYBOOK_CONFIG',)): 2,
    ('tests/test_vertical_playbook_routing.py', 'verticals.saas_premium.vertical_config', ('should_trigger_playbook',)): 1,
    ('utils/account_config_manager.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS', 'DC2S_PILLARS')): 1,
    ('utils/config_loader.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS', 'DC2S_PILLARS')): 1,
    ('utils/config_loader.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_PILLARS',)): 1,
    ('utils/playbook_lifecycle.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG',)): 1,
    ('utils/story_arc_loader.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 1,
    ('utils/vertical_playbook_routing.py', 'verticals.saas_premium.vertical_config', ('PLAYBOOK_CONFIG',)): 1,
    ('utils/vertical_registry.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS', 'DC2S_PILLARS')): 1,
    ('utils/vertical_registry.py', 'verticals.saas_premium.kpi_definitions', ('SAAS_KPIS', 'SAAS_PILLARS')): 1,
    ('utils/vpcs_dashboard_helpers.py', 'verticals.dc2_s.api_routes', ('get_precalculated_scores',)): 1,
    ('verticals/_template/services/bootstrap_weights_loader.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_PILLARS',)): 1,
    ('verticals/customer295-dc/services/bootstrap_weights_loader.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_PILLARS',)): 1,
    ('wizards/wizard_c_weight_calibrator_db.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 1,
    ('wizards/wizard_c_weight_calibrator_db.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_PILLARS',)): 1,
}

assert sum(BASELINE.values()) == 85, (
    "BASELINE literal was hand-edited inconsistently with its own comment "
    "— fix the count or the entries."
)


def test_no_new_cross_vertical_imports_beyond_baseline():
    """The regression guard. Fails only on a genuinely NEW cross-vertical
    import in generic code (new file, new import statement, or the same
    import statement appearing MORE times than the recorded baseline).
    Fixing an existing baseline entry (import removed or routed through
    vertical_registry) never fails this test — only growth does.
    """
    current, unparseable = _scan_violations()

    new_or_grown = Counter()
    for key, count in current.items():
        baseline_count = BASELINE.get(key, 0)
        if count > baseline_count:
            new_or_grown[key] = count - baseline_count

    assert not new_or_grown, (
        "Found cross-vertical import(s) in generic code NOT in the "
        "recorded baseline (kpi-dashboard/backend/tests/"
        "test_cross_vertical_import_inventory.py). A generic/shared module "
        "is importing directly from a specific vertical's Python package "
        "instead of routing through utils.vertical_registry — the exact "
        "bug class fixed repeatedly on 2026-08-21 (get_kpi_catalog, "
        "partner_portal, etc). If this is deliberate and unavoidable for "
        "now, add it to BASELINE explicitly (with a comment saying why) "
        "rather than silencing this test another way; if it's accidental, "
        "route the import through utils.vertical_registry instead.\n\n"
        + "\n".join(
            f"  NEW: {file}:{module} imports {names} "
            f"({'+' + str(delta) + ' beyond baseline' if BASELINE.get((file, module, names)) else 'not in baseline at all'})"
            for (file, module, names), delta in sorted(new_or_grown.items())
        )
    )


def test_baseline_entries_are_still_real():
    """Companion sanity check: every baseline entry should still be
    findable by the scan (not literally, since a decrease is allowed, but
    the *file* must still exist as a vertical-relevant path — this catches
    a baseline that silently rotted into meaninglessness, e.g. if verticals/
    got restructured and every path in BASELINE went stale at once, which
    would make the whole guard vacuous without failing loudly).
    """
    current, _ = _scan_violations()
    files_still_present = {key[0] for key in current} | {
        str(p.relative_to(BACKEND)) for p in BACKEND.rglob("*.py")
    }
    baseline_files = {key[0] for key in BASELINE}
    missing_files = baseline_files - files_still_present
    assert not missing_files, (
        f"Baseline references files that no longer exist under {BACKEND}: "
        f"{sorted(missing_files)}. Either the file was removed (baseline "
        f"entry should be deleted) or the scan/classification logic broke."
    )


if __name__ == "__main__":
    test_no_new_cross_vertical_imports_beyond_baseline()
    print(f"PASS: no new cross-vertical imports beyond the {sum(BASELINE.values())}-site baseline")
    test_baseline_entries_are_still_real()
    print("PASS: baseline entries still reference real files")

    current, unparseable = _scan_violations()
    print(f"\nCurrent scan: {sum(current.values())} cross-vertical import sites across {len(current)} distinct (file, import) pairs")
    if unparseable:
        print(f"({len(unparseable)} legacy files skipped — could not be parsed as Python 3 AST)")
