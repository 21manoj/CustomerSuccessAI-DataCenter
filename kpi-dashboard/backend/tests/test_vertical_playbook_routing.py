#!/usr/bin/env python3
"""
Regression: vertical-aware playbook routing.

Pins the fix for bugs B-4 and B-5 from the May 17 FDE persona eval, where a
SaaS Premium tenant (cust 334) was getting DC2S playbooks (PB-01..PB-06) on
both get_playbook_recommendations and get_playbook_economics MCP tools.

These tests run pure-Python (no DB / Flask) — they exercise the cost-bridge
and the SaaS PLAYBOOK_CONFIG directly. The MCP-level integration is covered
by the live verification documented in the PR body.
"""

import os
import sys

# Make backend importable when the test runner is launched from repo root.
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


# ──────────────────────────────────────────────────────────────────────────
# SaaS vertical_config has the expected playbook IDs (the ones referenced
# by config/power_of_1_economics.json's `linked_playbooks` field).
# ──────────────────────────────────────────────────────────────────────────

def test_saas_vertical_config_has_expected_playbooks():
    from verticals.saas_premium.vertical_config import PLAYBOOK_CONFIG

    expected = {
        'activation-blitz', 'voc-sprint', 'expansion-accelerator',
        'renewal-safeguard', 'sla-stabilizer', 'health-check',
    }
    assert expected.issubset(set(PLAYBOOK_CONFIG.keys())), (
        f"SaaS PLAYBOOK_CONFIG missing playbooks. Have: {set(PLAYBOOK_CONFIG.keys())}; "
        f"Expected to include: {expected}"
    )

    # Each must have the shape PLAYBOOK_CONFIG consumers (cost_bridge) expect.
    for pb_id, cfg in PLAYBOOK_CONFIG.items():
        assert 'sub_components' in cfg, f"{pb_id} missing sub_components"
        assert cfg['sub_components'], f"{pb_id} sub_components empty"
        for sc in cfg['sub_components']:
            assert 'estimated_hours' in sc, f"{pb_id} sub-component missing estimated_hours"


def test_saas_vertical_config_has_no_dc_playbooks():
    """SaaS catalog must NOT contain DC2S playbook IDs (PB-01..PB-06)."""
    from verticals.saas_premium.vertical_config import PLAYBOOK_CONFIG

    dc_prefixed = [pb for pb in PLAYBOOK_CONFIG.keys() if pb.startswith('PB-')]
    assert not dc_prefixed, (
        f"SaaS PLAYBOOK_CONFIG contains DC2S-style playbook IDs: {dc_prefixed}. "
        f"These belong in verticals/dc2_s/vertical_config.py."
    )


def test_should_trigger_playbook_and_logic():
    """should_trigger_playbook uses AND-logic across trigger_conditions."""
    from verticals.saas_premium.vertical_config import should_trigger_playbook

    # activation-blitz triggers on (DAU<60 AND TTFV<60)
    assert should_trigger_playbook('activation-blitz',
                                   {'P1-KPI1': 30, 'P1-KPI3': 40}) is True
    assert should_trigger_playbook('activation-blitz',
                                   {'P1-KPI1': 30, 'P1-KPI3': 85}) is False  # one met
    assert should_trigger_playbook('activation-blitz',
                                   {'P1-KPI1': 90, 'P1-KPI3': 90}) is False  # none met
    # Missing KPI → False (can't confirm trigger)
    assert should_trigger_playbook('activation-blitz', {'P1-KPI1': 30}) is False


# ──────────────────────────────────────────────────────────────────────────
# Cost bridge routes by vertical (closes B-5)
# ──────────────────────────────────────────────────────────────────────────

def test_cost_bridge_dc2s_returns_pb_playbooks():
    """DC2S vertical → cost bridge surfaces PB-01..PB-06."""
    from playbook_cost_bridge import calculate_cost_bridge

    bridge = calculate_cost_bridge(account_arr=10_000_000, vertical='dc2_s')

    assert bridge.vertical == 'dc2_s'
    # Each key is "playbook_id:metric_id" — collect the PB IDs.
    pb_ids = {key.split(':')[0] for key in bridge.playbooks.keys()}
    assert pb_ids, "DC2S bridge produced no playbooks"
    for pb in pb_ids:
        assert pb.startswith('PB-'), (
            f"DC2S bridge surfaced non-DC playbook {pb!r}; expected PB-* only."
        )


def test_cost_bridge_saas_returns_saas_playbooks_not_dc():
    """SaaS vertical → cost bridge surfaces SaaS playbooks, NEVER PB-DC- or PB-01..PB-06."""
    from playbook_cost_bridge import calculate_cost_bridge

    bridge = calculate_cost_bridge(account_arr=10_000_000, vertical='saas_premium')

    assert bridge.vertical == 'saas_premium'
    pb_ids = {key.split(':')[0] for key in bridge.playbooks.keys()}
    assert pb_ids, "SaaS bridge produced no playbooks"

    # No DC2S-flavored IDs allowed
    dc_leaks = {pb for pb in pb_ids if pb.startswith('PB-')}
    assert not dc_leaks, (
        f"SaaS cost bridge leaked DC2S playbooks: {dc_leaks}. "
        f"This is the regression of bug B-5."
    )

    # At least one canonical SaaS playbook is present
    expected_saas = {'activation-blitz', 'voc-sprint', 'expansion-accelerator',
                     'renewal-safeguard', 'sla-stabilizer'}
    assert pb_ids & expected_saas, (
        f"SaaS cost bridge missing all expected SaaS playbooks. Got: {pb_ids}"
    )


def test_cost_bridge_vertical_alias_normalization():
    """'saas' short-code should resolve to saas_premium (no DC2S fallback)."""
    from playbook_cost_bridge import calculate_cost_bridge

    bridge = calculate_cost_bridge(account_arr=10_000_000, vertical='saas')

    assert bridge.vertical == 'saas_premium'
    pb_ids = {key.split(':')[0] for key in bridge.playbooks.keys()}
    assert not any(pb.startswith('PB-') for pb in pb_ids), (
        f"Short-code 'saas' fell back to DC2S — got: {pb_ids}"
    )


def test_bridge_to_dict_carries_vertical():
    """bridge_to_dict must surface the resolved vertical so MCP responses can
    show it. Otherwise downstream UIs would have no way to know the SaaS
    tenant got the SaaS catalog vs the DC default."""
    from playbook_cost_bridge import calculate_cost_bridge, bridge_to_dict

    result = bridge_to_dict(calculate_cost_bridge(account_arr=10_000_000,
                                                  vertical='saas_premium'))
    assert result.get('vertical') == 'saas_premium'


# ──────────────────────────────────────────────────────────────────────────
# Recommendation engine: SaaS path doesn't run DC2S evaluator
# ──────────────────────────────────────────────────────────────────────────

def test_recommendations_api_imports_vertical_resolver():
    """The recommendations module exposes a vertical resolver helper —
    presence is the contract that get_recommendations_for_account routes
    by tenant vertical, not by 'is kpi_values non-None'."""
    import playbook_recommendations_api as mod
    assert hasattr(mod, '_resolve_vertical_for_customer'), (
        "playbook_recommendations_api must expose a vertical-resolver — "
        "without it, get_recommendations_for_account silently routes "
        "every tenant with KPI data into the DC2S branch (bug B-4)."
    )


def test_get_playbook_economics_single_lookup_routes_by_vertical():
    """Single-playbook lookup must accept vertical and surface SaaS catalog
    for SaaS playbook IDs."""
    from playbook_cost_bridge import get_playbook_economics

    # DC2S lookup
    pb_dc = get_playbook_economics('PB-01', account_arr=10_000_000, vertical='dc2_s')
    assert pb_dc is not None, "DC2S PB-01 not found in DC2S cost bridge"
    assert pb_dc.playbook_id == 'PB-01'

    # SaaS lookup
    pb_saas = get_playbook_economics('activation-blitz', account_arr=10_000_000,
                                     vertical='saas_premium')
    assert pb_saas is not None, "SaaS activation-blitz not found in SaaS cost bridge"
    assert pb_saas.playbook_id == 'activation-blitz'

    # Cross-vertical lookup must NOT silently succeed: PB-01 doesn't exist in SaaS
    pb_cross = get_playbook_economics('PB-01', account_arr=10_000_000,
                                      vertical='saas_premium')
    assert pb_cross is None, (
        "SaaS cost bridge silently returned DC2S playbook PB-01 — "
        "this would re-introduce bug B-5."
    )
