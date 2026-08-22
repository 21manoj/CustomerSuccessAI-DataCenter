"""
Phase 5 fixes for api_v1_routes.py's 11 verticals.dc2_s.api_routes imports
(2026-08-22, vertical-registry fail-closed refactor).

api_v1_routes.py's `_dispatch()` proxied every /api/v1/* endpoint to a
`default_handler` imported directly from verticals.dc2_s.api_routes — 11
import sites, flagged by tests/test_cross_vertical_import_inventory.py.
A prior read found 7 of them (get_csm_scorecard_api, get_dc2s_health_score,
get_dc2s_health_summary, get_health_score_history_api,
get_playbook_success_metrics_api, get_renewals_api, get_team_capacity_api)
had zero DC2S-specific taxonomy coupling in their bodies and were simply
homed in the wrong package; this session confirmed that read by inspecting
each function's source directly, then relocated them to the new
api_v1_generic_handlers.py.

The remaining 4 (get_dc2s_accounts, get_dc2s_account_detail,
get_dc2s_alerts, get_csm_daily_actions) DID have real dc2_s coupling,
confirmed live against customer 400 (datacenter_v1, 6 pillars P1-P6) on
EC2 — see the BASELINE comment in test_cross_vertical_import_inventory.py
for the exact observed-before/fixed-after behavior. They were fixed in
place (still imported from verticals.dc2_s.api_routes — the import site
itself is legitimate, since these 4 genuinely need vertical-specific
config; only what happens INSIDE them changed) to resolve KPI/pillar/
playbook config from the CUSTOMER'S OWN vertical via
utils.vertical_registry / _ask_ai_helpers._get_playbook_config instead of
always using DC2S's.

These tests are static/source-inspection based (no Flask app, no DB) —
same convention as test_vertical_catalog_consistency.py and
test_cross_vertical_import_inventory.py, since local Postgres is empty in
this environment. The live-data proof (customer 398 dc2_s, 399
saas_premium, 400 datacenter_v1 on EC2) is the primary evidence for this
change and is documented in the session's report, not re-derivable here.
"""

import ast
import inspect
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

RELOCATED_FUNCTIONS = [
    "get_dc2s_health_score",
    "get_dc2s_health_summary",
    "get_health_score_history_api",
    "get_csm_scorecard_api",
    "get_team_capacity_api",
    "get_renewals_api",
    "get_playbook_success_metrics_api",
]

STILL_COUPLED_FUNCTIONS = [
    "get_dc2s_accounts",
    "get_dc2s_account_detail",
    "get_dc2s_alerts",
    "get_csm_daily_actions",
]


def _import_from_names(tree, module_suffix):
    """Return {name: [imported_names...]} for every `from X import (...)`
    in `tree` whose module ends with `module_suffix`."""
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith(module_suffix):
            out.setdefault(node.module, []).extend(a.name for a in node.names)
    return out


def test_api_v1_generic_handlers_module_exists_and_defines_all_seven():
    """The relocation target module exists and defines exactly the 7
    functions confirmed to have no DC2S-specific taxonomy coupling."""
    path = BACKEND / "api_v1_generic_handlers.py"
    assert path.exists(), "api_v1_generic_handlers.py was not created"

    src = path.read_text()
    tree = ast.parse(src, filename=str(path))
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

    missing = set(RELOCATED_FUNCTIONS) - defined
    assert not missing, f"api_v1_generic_handlers.py is missing: {sorted(missing)}"


def test_relocated_functions_have_no_dc2s_taxonomy_coupling():
    """Regression guard: none of the 7 relocated functions should
    reference DC2S_KPIS / DC2S_PILLARS / PLAYBOOK_CONFIG /
    should_trigger_playbook directly. If a future edit reintroduces one of
    these, this is exactly the bug class the whole Phase 5 cleanup fixed —
    catch it here instead of relying on another live audit.
    """
    import api_v1_generic_handlers as gh

    forbidden = ("DC2S_KPIS", "DC2S_PILLARS", "PLAYBOOK_CONFIG", "should_trigger_playbook")
    offenders = {}
    for fn_name in RELOCATED_FUNCTIONS:
        fn = getattr(gh, fn_name)
        src = inspect.getsource(fn)
        hits = [n for n in forbidden if n in src]
        if hits:
            offenders[fn_name] = hits

    assert not offenders, (
        f"Relocated function(s) reference DC2S-specific taxonomy: {offenders}. "
        "These were relocated to api_v1_generic_handlers.py on the premise "
        "that they contain zero such coupling — route through "
        "utils.vertical_registry instead, or move the function back to "
        "verticals/dc2_s/api_routes.py if it turns out to be genuinely "
        "DC2S-specific after all."
    )


def test_api_v1_routes_imports_relocated_functions_from_generic_module():
    """api_v1_routes.py must import the 7 relocated functions from
    api_v1_generic_handlers, not verticals.dc2_s.api_routes — that's the
    whole point of the relocation (clears 7 of 11
    test_cross_vertical_import_inventory.py baseline sites)."""
    path = BACKEND / "api_v1_routes.py"
    tree = ast.parse(path.read_text(), filename=str(path))

    from_generic = _import_from_names(tree, "api_v1_generic_handlers")
    from_dc2s = _import_from_names(tree, "verticals.dc2_s.api_routes")

    imported_from_generic = set()
    for names in from_generic.values():
        imported_from_generic.update(names)
    imported_from_dc2s = set()
    for names in from_dc2s.values():
        imported_from_dc2s.update(names)

    missing_from_generic = set(RELOCATED_FUNCTIONS) - imported_from_generic
    assert not missing_from_generic, (
        f"api_v1_routes.py does not import {sorted(missing_from_generic)} "
        "from api_v1_generic_handlers — relocation incomplete."
    )

    still_from_dc2s = set(RELOCATED_FUNCTIONS) & imported_from_dc2s
    assert not still_from_dc2s, (
        f"api_v1_routes.py still imports {sorted(still_from_dc2s)} from "
        "verticals.dc2_s.api_routes — the whole point of relocating these "
        "was to stop doing that."
    )

    still_coupled_present = set(STILL_COUPLED_FUNCTIONS) & imported_from_dc2s
    assert still_coupled_present == set(STILL_COUPLED_FUNCTIONS), (
        "api_v1_routes.py should still import the 4 genuinely-coupled "
        f"functions from verticals.dc2_s.api_routes: {STILL_COUPLED_FUNCTIONS}. "
        f"Found: {sorted(still_coupled_present)}. These were fixed IN PLACE, "
        "not relocated — the import site itself is legitimate."
    )


def test_still_coupled_functions_route_through_vertical_registry():
    """The 4 functions that keep real vertical-specific logic must resolve
    it from the CUSTOMER'S OWN vertical (utils.vertical_registry /
    _ask_ai_helpers._get_playbook_config) rather than unconditionally using
    DC2S_KPIS / DC2S_PILLARS / DC2S's PLAYBOOK_CONFIG as a silent default —
    the exact bug confirmed live against customer 400 (datacenter_v1) on
    EC2 (see test_cross_vertical_import_inventory.py's BASELINE comment for
    the observed-before/fixed-after behavior)."""
    import verticals.dc2_s.api_routes as dr

    expectations = {
        "get_dc2s_accounts": ("get_catalog_for_customer",),
        "get_dc2s_account_detail": ("get_catalog_for_customer", "get_vertical_for_customer"),
        "get_dc2s_alerts": ("get_catalog_for_customer",),
        "get_csm_daily_actions": ("get_vertical_for_customer", "_get_playbook_config"),
    }

    offenders = {}
    for fn_name, must_contain in expectations.items():
        fn = getattr(dr, fn_name)
        src = inspect.getsource(fn)
        missing = [needle for needle in must_contain if needle not in src]
        if missing:
            offenders[fn_name] = missing

    assert not offenders, (
        f"Function(s) no longer route vertical-specific lookups through "
        f"the customer's own vertical: {offenders}"
    )


def test_journey_phase_sync_gated_to_dc2s_only():
    """_sync_journey_phase() persists a DC2S-only lifecycle label
    (deployment/performance/excellence) into Account.profile_metadata.
    get_dc2s_health_score (relocated), get_dc2s_accounts, and
    get_dc2s_account_detail (still in verticals/dc2_s/api_routes.py) all
    call it — each call site must be gated so it only fires for dc2_s
    customers, not silently applied to every vertical."""
    import api_v1_generic_handlers as gh
    import verticals.dc2_s.api_routes as dr

    health_score_src = inspect.getsource(gh.get_dc2s_health_score)
    accounts_src = inspect.getsource(dr.get_dc2s_accounts)
    account_detail_src = inspect.getsource(dr.get_dc2s_account_detail)

    for name, src in (
        ("get_dc2s_health_score", health_score_src),
        ("get_dc2s_accounts", accounts_src),
        ("get_dc2s_account_detail", account_detail_src),
    ):
        assert "_sync_journey_phase(account)" in src, f"{name} should still call _sync_journey_phase"
        assert "== 'dc2_s'" in src, (
            f"{name} calls _sync_journey_phase() but doesn't appear to gate "
            "it to dc2_s only — found live during the 2026-08-22 cleanup "
            "that this silently mislabeled other verticals' accounts."
        )


if __name__ == "__main__":
    test_api_v1_generic_handlers_module_exists_and_defines_all_seven()
    print("PASS: api_v1_generic_handlers.py defines all 7 relocated functions")
    test_relocated_functions_have_no_dc2s_taxonomy_coupling()
    print("PASS: relocated functions have no DC2S taxonomy coupling")
    test_api_v1_routes_imports_relocated_functions_from_generic_module()
    print("PASS: api_v1_routes.py imports from the generic module, not verticals.dc2_s.api_routes")
    test_still_coupled_functions_route_through_vertical_registry()
    print("PASS: still-coupled functions route through vertical_registry")
    test_journey_phase_sync_gated_to_dc2s_only()
    print("PASS: journey_phase sync gated to dc2_s only")
