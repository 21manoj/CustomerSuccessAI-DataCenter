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
# day's fixes (commits 3d85e74f2..6bad52072) had already landed. Originally
# 85 sites across 44 files. This is a snapshot, not a target — Phase 5
# clears it incrementally; entries disappearing (a site got fixed) never
# fails this test, only NEW entries do.
#
# Phase 5 update (Aug 22 2026): 7 sites cleared — dc2s_config_api.py (3),
# utils/config_loader.py (2), wizards/wizard_c_weight_calibrator_db.py (2) —
# all swapped for utils.vertical_registry.get_pillars/get_kpis. See
# tests/test_phase5_import_inventory_fixes.py for the parity + behavioral
# proofs (that new test file itself adds 1 legitimate ground-truth-import
# site, same pattern as test_scorer_parity.py below). Net after that pass:
# 79 sites across 44 files. playbook_cost_bridge.py's 2 sites
# (PLAYBOOK_CONFIG) were reviewed and deliberately left — no generic
# registry accessor exists for playbook config (only KPI/pillar catalogs),
# and the code already correctly if/elif-gates per vertical, mirroring the
# canonical (out-of-scope) mcp_server/common.py::_get_playbook_config;
# deferred to Phase 3 of the plan.
#
# Phase 5 update #2 (Aug 22 2026, api_v1_routes.py's 11 sites): audited each
# of the 11 handler imports api_v1_routes.py pulled from
# verticals.dc2_s.api_routes. 7 (get_csm_scorecard_api, get_dc2s_health_score,
# get_dc2s_health_summary, get_health_score_history_api,
# get_playbook_success_metrics_api, get_renewals_api, get_team_capacity_api)
# had zero DC2S-specific taxonomy coupling in their bodies — confirmed by
# reading each, not assumed — and were physically relocated to the new
# api_v1_generic_handlers.py (a generic, non-vertical module), clearing
# those 7 api_v1_routes.py entries outright. The relocated module still
# imports 6 vertical-agnostic-in-behavior scoring/query helpers
# (calculate_kpi_health, get_weights_for_customer, get_precalculated_scores,
# _get_trailing_kpi_values, _filter_user_accounts, _sync_journey_phase) from
# verticals.dc2_s.api_routes in a single statement — they're still
# physically homed there (a separate, larger cleanup; see the existing
# scripts/generate_context_graph_data.py, utils/vpcs_dashboard_helpers.py,
# tests/test_account_health_convergence.py, tests/test_scorer_parity.py
# entries below, which already reference the same helpers from the same
# place) — recorded as ONE new baseline entry rather than silently
# duplicating scoring logic in a second location.
#
# The remaining 4 (get_dc2s_accounts, get_dc2s_account_detail,
# get_dc2s_alerts, get_csm_daily_actions) DID have real dc2_s coupling,
# confirmed live against customer 400 (datacenter_v1, 6 pillars P1-P6) on
# EC2: get_dc2s_accounts defaulted `enabled_pillars` to DC2S_PILLARS.keys()
# (5 pillars) whenever no CustomerConfig.dc2s_pillar_weights override was
# set, silently dropping P6; get_dc2s_account_detail and get_dc2s_alerts
# looked KPI metadata up in the hardcoded DC2S_KPIS dict, which has no
# P6-KPI* entries, so datacenter_v1's Facility & Power KPIs were silently
# dropped from account-detail's kpis_by_pillar and never generated an
# alert regardless of value; get_csm_daily_actions unconditionally used
# DC2S's PLAYBOOK_CONFIG/should_trigger_playbook to evaluate playbook
# triggers for every vertical. All 4 were fixed IN PLACE (not relocated —
# they still need something vertical-specific, just resolved from the
# customer's OWN vertical instead of DC2S's) by routing through
# utils.vertical_registry.get_catalog_for_customer /
# get_vertical_for_customer, and (for the playbook-trigger coupling) the
# already-established _ask_ai_helpers.py::_get_playbook_config fail-closed
# per-vertical helper (dc2_s/saas_premium native; safe no-op — no playbook
# actions, not a misfire — for any other vertical). Their 4
# api_v1_routes.py baseline entries below are therefore UNCHANGED (the
# import site itself didn't move, only what happens inside the imported
# function). Also found and fixed in passing: get_dc2s_health_score (now
# relocated) and get_dc2s_accounts/get_dc2s_account_detail (still here)
# unconditionally called `_sync_journey_phase()`, persisting a DC2S-only
# lifecycle label into ANY vertical's Account.profile_metadata — gated to
# dc2_s only. dc2_s (customer 398) and saas_premium (customer 399) parity
# verified live alongside the datacenter_v1 (customer 400) fix — see
# tests/test_phase5_api_v1_routes_fixes.py.
#
# Net: 79 - 7 (relocated) + 1 (api_v1_generic_handlers.py's new helper
# import) + 2 (this Phase 5 pass's own verification test,
# tests/test_phase5_api_v1_routes_fixes.py, which imports
# verticals.dc2_s.api_routes locally in 2 of its test functions) = 75 sites
# across 46 files.
#
# Phase 5 update #3 (Aug 22 2026, mcp_server cluster — common.py,
# _ask_ai_helpers.py, cs_pulse_admin.py, cs_pulse_mcp_server.py): re-scanned
# all 4 files fresh rather than trusting the existing baseline count, since
# 3 of them had already been partially fixed earlier the same day and the
# BASELINE literal had drifted out of sync with the actual post-fix source:
#
#   - mcp_server/common.py: 4 of its 6 baseline entries (DC2S_KPIS,
#     DC2S_PILLARS, SAAS_KPIS, SAAS_PILLARS) no longer exist in the file —
#     get_pillar_labels() and get_kpi_definitions() were already routed
#     through utils.vertical_registry.get_pillars/get_kpis by an earlier
#     pass today, confirmed by reading the current source (both now contain
#     zero verticals.* imports). REMOVED from BASELINE (stale, not a live
#     site — fixing an entry that no longer exists never fails this test,
#     but leaving it in overstates the remaining inventory). The other 2
#     (dc2_s and saas_premium PLAYBOOK_CONFIG/should_trigger_playbook, both
#     inside get_playbook_config()) are genuinely still there and legitimate:
#     no generic registry accessor exists for playbook config, and the code
#     already correctly if/elif-gates per known vertical with a safe no-op
#     default for everything else — same treatment as playbook_cost_bridge.py
#     above. LEFT IN BASELINE.
#   - mcp_server/cs_pulse_mcp_server.py: BOTH baseline entries (dc2_s and
#     saas_premium PLAYBOOK_CONFIG/should_trigger_playbook) are stale —
#     _get_playbook_config() (line ~303) now delegates to the fixed
#     mcp_server.common.get_playbook_config() instead of carrying its own
#     copy of the import, per that function's own docstring ("delegates to
#     that fixed implementation instead of carrying its own stale copy").
#     The file has zero verticals.* imports in the current scan. REMOVED
#     from BASELINE entirely.
#   - _ask_ai_helpers.py: both entries (dc2_s and saas_premium
#     PLAYBOOK_CONFIG/should_trigger_playbook, inside its own
#     _get_playbook_config()) are real and current, and already correctly
#     if/elif-gated per vertical with a safe no-op default — deliberately
#     NOT delegated to mcp_server.common.get_playbook_config because this
#     module has zero fastmcp dependency by design (documented in its own
#     docstring) and common.py imports fastmcp.exceptions at module level.
#     LEFT IN BASELINE, same legitimate-gated treatment as common.py above.
#   - mcp_server/cs_pulse_admin.py: both entries are real and current, inside
#     get_csm_daily_actions() (line ~456). _get_roi_context is already gated
#     `if vertical == 'dc2_s':` with a documented honest-unavailable fallback
#     for every other vertical (no fabricated ROI numbers). The
#     _compute_impact_score/_compute_effort_score/_determine_urgency import
#     is unconditional (not gated) but the function is genuinely
#     vertical-neutral by inspection — it operates only on
#     health/churn/expansion floats and playbook sub-component counts, no
#     vertical-specific KPI codes or playbook IDs — documented inline at the
#     import site (see the file's own Aug 21 2026 comment). Same
#     physically-homed-but-vertical-neutral-reuse pattern already accepted
#     elsewhere in this baseline for utils/vpcs_dashboard_helpers.py and
#     scripts/generate_context_graph_data.py. LEFT IN BASELINE.
#
# No code changes were needed for any of these 4 files this pass — every
# genuinely-unfixed site turned out to already be a documented, gated,
# legitimate exception; the only real bugs in this cluster (resolver +
# _get_kpi_definitions/_get_playbook_config duplication) had already been
# fixed earlier the same day. Net: 75 - 6 (4 stale common.py + 2 stale
# cs_pulse_mcp_server.py, both already-fixed-but-uncounted) = 69 sites
# across 44 files.
#
# Phase 5 update #4 (Aug 22 2026, 7-file scoped pass — onboarding_api_v2_
# config_aware.py, app_v3_minimal.py, customer_playbook_api.py,
# data_quality_api.py, journey_api_dynamic.py, playbook_recommendations_api.py,
# ask_ai_tools.py): 6 real bugs found and fixed (all confirmed via
# tests/test_phase5_import_inventory_fixes_round2.py's AST + behavioral
# proofs):
#
#   - onboarding_api_v2_config_aware.py (2 sites, both cleared): the
#     module-level DC2S_PILLAR_NAMES/ALL_DC2S_KPI_CODES constants (built
#     from a hardcoded DC2S_KPIS/DC2S_PILLARS import) fed
#     complete_onboarding's idempotent-reuse response AND its
#     total_available_kpis field regardless of the customer's actual
#     vertical — a saas_premium/datacenter_v1 customer's onboarding
#     response reported dc2_s's 38-KPI/5-pillar counts. Now resolved
#     per-vertical via utils.vertical_registry at each call site
#     (complete_onboarding already had _v_kpis/_v_pillars in scope for a
#     different field — total_available_kpis just wasn't using them yet).
#     The dead _get_dc2s_kpi_valid_ranges/validate_kpi_values_against_ranges
#     pair (confirmed unreferenced anywhere in the codebase) also gained a
#     `vertical` parameter for correctness, defaulting to 'dc2_s' to
#     preserve exact prior behavior for any future caller.
#   - customer_playbook_api.py (1 site, cleared): _seed_system_playbooks
#     unconditionally seeded every customer's playbook library from dc2_s's
#     PLAYBOOK_CONFIG. Now resolves the customer's real vertical via
#     utils.vertical_registry.get_vertical_for_customer and routes through
#     the established _ask_ai_helpers._get_playbook_config helper (dc2_s/
#     saas_premium native, safe no-op elsewhere) instead of reimplementing
#     the gate.
#   - data_quality_api.py (1 site, cleared): /api/data-quality/
#     kpi-range-discrepancies validated every customer's KPI values against
#     DC2S_KPIS's ranges regardless of their vertical — a saas_premium/
#     datacenter_v1 tenant's KPI codes rarely matched dc2_s's, so the check
#     silently found ~zero discrepancies for them. _get_dc2s_kpi_ranges
#     gained a `vertical` param (default 'dc2_s' preserves old behavior for
#     any other caller) and the route now resolves+passes the requesting
#     customer's real vertical, failing closed (empty report, not a 500) if
#     resolution fails.
#   - journey_api_dynamic.py (1 site, cleared): enrich_weekly_data_with_
#     dc2s_kpis looked up every account's KPI name/unit/target in DC2S_KPIS
#     regardless of the account's actual vertical — since KPI codes are
#     P-format across verticals, a saas_premium/datacenter_v1 code could
#     silently resolve to the wrong (dc2_s) KPI's name/unit in the journey
#     timeline. Now resolves the account's real vertical via
#     utils.vertical_registry and fails closed (skips enrichment for that
#     week) rather than substituting dc2_s's definitions if resolution
#     fails.
#   - playbook_recommendations_api.py (1 site, cleared): POST /api/
#     playbooks/recommendations/<playbook_id> hardcoded dc2_s's
#     PLAYBOOK_CONFIG/should_trigger_playbook for ANY playbook_id starting
#     with 'PB-', and hardcoded the response's 'vertical' field to
#     'dc2_s'. Confirmed datacenter_v1 has its own PB-07..13 playbook ids
#     beyond dc2_s's PB-01..06, so a datacenter_v1 customer requesting one
#     404'd as "Unknown DC2S playbook". Now mirrors the file's own
#     pre-existing _CONFIG_PLAYBOOK_VERTICALS/dynamic-import pattern
#     (already used by _evaluate_dc2s_playbooks above it) via the existing
#     _resolve_vertical_for_customer helper, with a local generic AND-logic
#     trigger check (mirrors verticals.dc2_s.vertical_config.
#     should_trigger_playbook's semantics exactly, but takes the resolved
#     vertical's PLAYBOOK_CONFIG as data instead of reading a hardcoded
#     dc2_s module-global) so it evaluates correctly against ANY
#     config-driven vertical's own playbook set.
#
# 2 sites reviewed and deliberately left (documented at their BASELINE
# entries below):
#   - app_v3_minimal.py (2 sites): Flask Blueprint registration wiring for
#     dc2_s's and saas_premium's own dedicated route surfaces
#     (/api/dc2s/*, /api/saas/*) — app-boot wiring, not a vertical-
#     resolution bug. No generic equivalent exists (datacenter_v1/
#     healthcare_provider use the generic scorer with no Blueprint of
#     their own); each import is independently try/except-gated.
#   - ask_ai_tools.py (1 site): get_csm_daily_actions's PLAYBOOK_CONFIG/
#     should_trigger_playbook half of this same bug was ALREADY fixed
#     (routes through _ask_ai_helpers._get_playbook_config) before this
#     pass started. The remaining 5-name import
#     (_normalize_kpi_code_for_health, _compute_impact_score,
#     _compute_effort_score, _determine_urgency, _get_roi_context) mirrors
#     the exact same residual gap already present, unaddressed, in the
#     canonical reference implementation this module was modeled on
#     (verticals/dc2_s/api_routes.py's own get_csm_daily_actions, fixed by
#     the mcp_server-cluster sibling agent earlier the same day) — fixing
#     the root cause (_normalize_kpi_code_for_health's internal `kpi_code
#     in DC2S_KPIS` check) requires editing verticals/dc2_s/api_routes.py,
#     out of scope for this pass (owned by that sibling agent). Left
#     unfixed for consistency with the canonical reference rather than
#     diverging into an ad hoc, one-off fix.
#
# Net: 69 - 6 (fixed) + 4 (this pass's own verification test,
# tests/test_phase5_import_inventory_fixes_round2.py, which imports
# verticals.dc2_s.vertical_config / verticals.datacenter_v1.vertical_config
# directly in 2 of its test functions as ground-truth comparators) = 67
# sites across 47 files.
# ──────────────────────────────────────────────────────────────────────────
BASELINE = {
    ('_ask_ai_helpers.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG', 'should_trigger_playbook')): 1,
    ('_ask_ai_helpers.py', 'verticals.saas_premium.vertical_config', ('PLAYBOOK_CONFIG', 'should_trigger_playbook')): 1,
    ('agents/signal_analyst_api.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_PILLARS',)): 1,
    ('agents/signal_converter.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 1,
    ('api_v1_generic_handlers.py', 'verticals.dc2_s.api_routes', ('calculate_kpi_health', 'get_weights_for_customer', 'get_precalculated_scores', '_get_trailing_kpi_values', '_filter_user_accounts', '_sync_journey_phase')): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_csm_daily_actions',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_dc2s_account_detail',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_dc2s_accounts',)): 1,
    ('api_v1_routes.py', 'verticals.dc2_s.api_routes', ('get_dc2s_alerts',)): 1,
    # App-boot Flask Blueprint registration for dc2_s's/saas_premium's own
    # dedicated route surfaces (/api/dc2s/*, /api/saas/*) — not a
    # vertical-resolution bug, no generic equivalent exists. See "Phase 5
    # update #4" comment above.
    ('app_v3_minimal.py', 'verticals.dc2_s.api_routes', ('dc2s_api',)): 1,
    ('app_v3_minimal.py', 'verticals.saas_premium.api_routes', ('saas_premium_api',)): 1,
    # PLAYBOOK_CONFIG/should_trigger_playbook half of this bug already fixed
    # (routes through _ask_ai_helpers._get_playbook_config); the remaining
    # 5-name import mirrors an unaddressed gap already present in the
    # canonical reference (verticals/dc2_s/api_routes.py's own
    # get_csm_daily_actions) — see "Phase 5 update #4" comment above.
    ('ask_ai_tools.py', 'verticals.dc2_s.api_routes', ('_normalize_kpi_code_for_health', '_compute_impact_score', '_compute_effort_score', '_determine_urgency', '_get_roi_context')): 1,
    ('debug_import.py', 'verticals.dc2_s', ('DC2S_KPIS',)): 1,
    ('mcp_server/common.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG', 'should_trigger_playbook')): 1,
    ('mcp_server/common.py', 'verticals.saas_premium.vertical_config', ('PLAYBOOK_CONFIG', 'should_trigger_playbook')): 1,
    ('mcp_server/cs_pulse_admin.py', 'verticals.dc2_s.api_routes', ('_compute_impact_score', '_compute_effort_score', '_determine_urgency')): 1,
    ('mcp_server/cs_pulse_admin.py', 'verticals.dc2_s.api_routes', ('_get_roi_context',)): 1,
    ('playbook_cost_bridge.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG',)): 1,
    ('playbook_cost_bridge.py', 'verticals.saas_premium.vertical_config', ('PLAYBOOK_CONFIG',)): 1,
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
    # Same pattern as test_scorer_parity.py below: imports the dc2_s module
    # directly to call its (still dc2_s-homed) get_dc2s_accounts/
    # get_dc2s_account_detail/get_dc2s_alerts/get_csm_daily_actions and
    # inspect their source for the vertical_registry routing this Phase 5
    # pass added — a verification tool, not a coupling bug.
    ('tests/test_phase5_api_v1_routes_fixes.py', 'verticals.dc2_s.api_routes', ('dr',)): 2,
    ('tests/test_scorer_parity.py', 'verticals.dc2_s.api_routes', ('_score_kpi_value',)): 1,
    ('tests/test_scorer_parity.py', 'verticals.dc2_s.api_routes', ('calculate_kpi_health',)): 1,
    # Same pattern as test_scorer_parity.py above: a direct DC2S_PILLARS
    # import used as the ground-truth comparator to PROVE the Phase 5 fix
    # (get_pillars('dc2_s')) is byte-identical — not a coupling bug.
    ('tests/test_phase5_import_inventory_fixes.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_PILLARS',)): 1,
    # Same pattern again: direct dc2_s/datacenter_v1 vertical_config imports
    # used as ground-truth comparators to prove
    # playbook_recommendations_api.py's new local should_trigger_playbook
    # closure reproduces verticals.dc2_s.vertical_config.
    # should_trigger_playbook's AND-logic semantics exactly, AND that it
    # (unlike the old hardcoded-dc2_s version) also works against
    # datacenter_v1's own PLAYBOOK_CONFIG — not a coupling bug.
    ('tests/test_phase5_import_inventory_fixes_round2.py', 'verticals.datacenter_v1.vertical_config', ('PLAYBOOK_CONFIG',)): 2,
    ('tests/test_phase5_import_inventory_fixes_round2.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG',)): 1,
    ('tests/test_phase5_import_inventory_fixes_round2.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG', 'should_trigger_playbook')): 1,
    ('tests/test_vertical_playbook_routing.py', 'verticals.saas_premium.vertical_config', ('PLAYBOOK_CONFIG',)): 2,
    ('tests/test_vertical_playbook_routing.py', 'verticals.saas_premium.vertical_config', ('should_trigger_playbook',)): 1,
    ('utils/account_config_manager.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS', 'DC2S_PILLARS')): 1,
    ('utils/playbook_lifecycle.py', 'verticals.dc2_s.vertical_config', ('PLAYBOOK_CONFIG',)): 1,
    ('utils/story_arc_loader.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS',)): 1,
    ('utils/vertical_playbook_routing.py', 'verticals.saas_premium.vertical_config', ('PLAYBOOK_CONFIG',)): 1,
    ('utils/vertical_registry.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_KPIS', 'DC2S_PILLARS')): 1,
    ('utils/vertical_registry.py', 'verticals.saas_premium.kpi_definitions', ('SAAS_KPIS', 'SAAS_PILLARS')): 1,
    ('utils/vpcs_dashboard_helpers.py', 'verticals.dc2_s.api_routes', ('get_precalculated_scores',)): 1,
    ('verticals/_template/services/bootstrap_weights_loader.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_PILLARS',)): 1,
    ('verticals/customer295-dc/services/bootstrap_weights_loader.py', 'verticals.dc2_s.kpi_definitions', ('DC2S_PILLARS',)): 1,
}

assert sum(BASELINE.values()) == 67, (
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
