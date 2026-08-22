#!/usr/bin/env python3
"""
Regression: CSMCockpit drill drawer PILLAR BREAKDOWN renders vertical-correct
labels (SaaS Premium tenants see SaaS labels, DC2S tenants see DC2S labels).

Bug context (May 18 eval):
  On cust 334 (SaaS Premium) the CSM cockpit drill drawer was rendering DC2S
  pillar labels — "AI/ML Performance", "Infrastructure", "Cloud & DevOps",
  "Commercial" — because the React component had a hardcoded
  pillarNames map keyed on the DC2S vertical. SaaS Premium customers should
  see "Product Adoption & Usage", "Customer Engagement", "Customer Sentiment
  & Support", "Partner & Ecosystem Health", "Revenue & Growth".

Same vertical-classification drift family as B-4 / B-5 / PR #26 / #33. PR #26
fixed it at the playbook routing layer; PR #33 wired the drawer's playbook
recommendations panel; this fix wires the drawer's pillar breakdown.

These tests run pure-Python (no DB / Flask). They pin:
  1. utils.vertical_registry returns the correct pillar catalog per vertical.
  2. api_v1_routes._inject_vertical_context injects `pillar_labels` so the
     /api/v1/accounts response carries vertical-aware labels to the frontend.
  3. The /api/v1/accounts dispatch hook actually invokes the injector (source
     check — catches regressions where someone bypasses _dispatch).
  4. CSMCockpit.tsx (the React drawer) reads `pillar_labels` from the response
     and feeds it into AccountDrawer instead of using its hardcoded DC2S map.
"""

import os
import sys

# Make backend importable when the test runner is launched from repo root.
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


# ──────────────────────────────────────────────────────────────────────────
# 1. Vertical registry returns the correct catalog per vertical.
# ──────────────────────────────────────────────────────────────────────────


def test_saas_premium_catalog_has_saas_pillar_names():
    """SaaS Premium tenants must surface SaaS pillar names, not DC2S."""
    from utils.vertical_registry import get_pillars

    pillars = get_pillars('saas_premium')
    names = {code: p.get('name', '') for code, p in pillars.items()}

    # The five canonical SaaS Premium pillars (per saas_premium_kpi_catalog.json).
    assert names.get('P1') == 'Product Adoption & Usage', (
        f"SaaS P1 label drifted from catalog: {names.get('P1')!r}"
    )
    assert names.get('P2') == 'Customer Engagement', (
        f"SaaS P2 label drifted from catalog: {names.get('P2')!r}"
    )
    assert names.get('P3') == 'Customer Sentiment & Support', (
        f"SaaS P3 label drifted from catalog: {names.get('P3')!r}"
    )
    assert names.get('P4') == 'Partner & Ecosystem Health', (
        f"SaaS P4 label drifted from catalog: {names.get('P4')!r}"
    )
    assert names.get('P5') == 'Revenue & Growth', (
        f"SaaS P5 label drifted from catalog: {names.get('P5')!r}"
    )

    # And explicitly: none of the DC2S labels should leak into SaaS.
    saas_label_values = set(names.values())
    dc_legacy_labels = {
        'AI/ML Performance', 'Infrastructure', 'Cloud & DevOps', 'Commercial',
    }
    leak = saas_label_values & dc_legacy_labels
    assert not leak, (
        f"SaaS Premium pillar catalog leaks DC2S-flavoured labels: {leak}. "
        f"This is the regression of the May 18 CSM drawer bug."
    )


def test_dc2s_catalog_still_has_dc2s_pillar_names():
    """Regression guard: DC2S tenants must still see DC2S labels."""
    from utils.vertical_registry import get_pillars

    pillars = get_pillars('dc2_s')
    names = {code: p.get('name', '') for code, p in pillars.items()}

    # All five DC2S pillar codes must resolve to DC2S labels from the catalog.
    # We assert that none of the SaaS labels appear (which would mean the
    # DC2S catalog file was overwritten with SaaS data).
    saas_only_labels = {
        'Product Adoption & Usage', 'Customer Sentiment & Support',
        'Partner & Ecosystem Health', 'Revenue & Growth',
    }
    leak = set(names.values()) & saas_only_labels
    assert not leak, (
        f"DC2S pillar catalog leaks SaaS-only labels: {leak}. The "
        f"DC2S catalog must remain DC2S-specific."
    )
    # And confirm we got non-empty labels for every code.
    assert all(names.values()), f"DC2S pillar names contain empties: {names}"


# ──────────────────────────────────────────────────────────────────────────
# 2 + 3. The /api/v1 dispatch helper injects pillar_labels into responses.
# ──────────────────────────────────────────────────────────────────────────


def test_inject_vertical_context_emits_pillar_labels():
    """_inject_vertical_context must add a `pillar_labels` map and a
    `vertical` slug to every dispatched response."""
    from unittest.mock import patch
    import api_v1_routes

    data = {'accounts': []}
    # Phase 1 fail-closed fix (2026-08-21): get_vertical_for_customer no
    # longer silently defaults to dc2_s when it can't resolve a customer
    # (e.g. no DB/Flask app context here in a pure-Python test) — it raises
    # instead. Stub _resolve_vertical so this test exercises only the
    # injection plumbing (vertical/pillar_labels keys land in the response),
    # not real DB resolution semantics — those are covered by
    # tests/test_vertical_resolution_fail_closed.py.
    with patch('api_v1_routes._resolve_vertical', return_value='saas_premium'):
        out = api_v1_routes._inject_vertical_context(data, customer_id=42)
    assert 'vertical' in out, (
        "_inject_vertical_context must add a 'vertical' slug — the React "
        "drawer can't decide whether labels are DC2S or SaaS without it."
    )
    assert 'pillar_labels' in out, (
        "_inject_vertical_context must add a 'pillar_labels' map — without "
        "it, CSMCockpit.tsx has no source of truth and falls back to its "
        "hardcoded DC2S pillarNames (bug B-4/B-5 family)."
    )
    assert isinstance(out['pillar_labels'], dict)


def test_v1_accounts_route_goes_through_dispatch():
    """The /api/v1/accounts handler must go through _dispatch so that
    _inject_vertical_context fires and pillar_labels lands in the response.

    Source-level check (no Flask/DB): catches regressions where someone
    inlines the DC2S handler call and bypasses the injector.
    """
    import inspect
    import api_v1_routes

    src = inspect.getsource(api_v1_routes.v1_accounts)
    assert '_dispatch' in src, (
        "/api/v1/accounts must call _dispatch — bypassing it skips "
        "_inject_vertical_context, so the response loses pillar_labels and "
        "the CSM drawer falls back to its hardcoded DC2S labels."
    )


# ──────────────────────────────────────────────────────────────────────────
# 4. CSMCockpit.tsx reads pillar_labels from the API and forwards it to
#    the drill drawer.
# ──────────────────────────────────────────────────────────────────────────


def _read_csm_cockpit_source():
    """Locate and read CSMCockpit.tsx from the React app."""
    path = os.path.abspath(os.path.join(
        _BACKEND, '..', 'src', 'components', 'csm', 'CSMCockpit.tsx',
    ))
    assert os.path.exists(path), f"CSMCockpit.tsx not found at {path}"
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def test_csm_cockpit_reads_pillar_labels_from_api():
    """CSMCockpit.tsx must read `pillar_labels` from the /api/v1/accounts
    response. Without this, the drawer's PILLAR BREAKDOWN section silently
    falls back to the legacy DC2S hardcoded labels for every tenant."""
    src = _read_csm_cockpit_source()
    assert 'data.pillar_labels' in src or 'pillar_labels' in src, (
        "CSMCockpit.tsx must read `pillar_labels` from the API response. "
        "If this line goes missing, SaaS tenants see DC2S labels in the "
        "drill drawer (bug B-4/B-5 family, May 18 eval finding)."
    )
    assert 'setPillarLabels(' in src, (
        "CSMCockpit.tsx must persist pillar_labels into component state "
        "via setPillarLabels — otherwise the value is read but discarded."
    )


def test_account_drawer_accepts_pillar_labels_prop():
    """AccountDrawer must accept a `pillarLabels` prop and the parent must
    pass it. This is the wiring between the API and the rendered labels."""
    src = _read_csm_cockpit_source()
    # The drawer's prop declaration.
    assert 'pillarLabels?: Record<string, string>' in src, (
        "AccountDrawer must declare `pillarLabels?: Record<string, string>` "
        "in DrawerProps so the parent can pass vertical-aware labels."
    )
    # The parent passes it on render.
    assert 'pillarLabels={pillarLabels}' in src, (
        "CSMCockpit must pass pillarLabels prop to <AccountDrawer>; "
        "otherwise the drawer never receives the API-provided labels."
    )


def test_csm_cockpit_dc2s_labels_only_in_fallback_block():
    """The DC2S pillar labels ('AI/ML Performance', etc.) may still appear
    in CSMCockpit.tsx, but ONLY inside the fallback constant used when the
    API doesn't return pillar_labels. They must NOT be referenced as the
    primary label source.

    Specifically: 'AI/ML Performance' should appear exactly once (inside
    the FALLBACK_DC2S_PILLAR_NAMES constant) — any other occurrence means
    the hardcoded map is back in the primary code path.
    """
    src = _read_csm_cockpit_source()
    # The label should appear, but only in the fallback constant.
    count = src.count("'AI/ML Performance'")
    assert count == 1, (
        f"'AI/ML Performance' appears {count} times in CSMCockpit.tsx — "
        f"expected exactly 1 (inside FALLBACK_DC2S_PILLAR_NAMES). Multiple "
        f"occurrences mean the hardcoded DC2S map is leaking back into the "
        f"primary render path."
    )
    # And the fallback constant itself must exist (so we know the single
    # occurrence is in the right place).
    assert 'FALLBACK_DC2S_PILLAR_NAMES' in src, (
        "Expected FALLBACK_DC2S_PILLAR_NAMES constant in CSMCockpit.tsx "
        "to contain the legacy DC2S labels for offline/mock fallback only."
    )
