"""
Ask AI helpers KPI-definitions vertical-coupling guard (bug #4, Aug 21 2026 audit).

_ask_ai_helpers.py's _get_kpi_definitions was a hardcoded two-branch if/else
(saas_premium via direct module import, everything else via a dc2_s import) —
a second, untouched copy of the exact same bug already fixed the same day in
mcp_server/cs_pulse_mcp_server.py's own _get_kpi_definitions. Any vertical
that wasn't 'saas_premium'/'saas' silently got DC2S_KPIS, feeding Ask AI
directly (a flagship conversational surface, high demo-visibility).

Fix: routes through utils.vertical_registry.get_kpis, same fail-closed
registry every other fixed vertical-coupling bug this session now uses.

No DB/Flask app needed — same convention as test_vertical_catalog_consistency.py.
"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import _ask_ai_helpers as helpers  # noqa: E402


def test_datacenter_v1_gets_its_own_kpis_not_dc2s():
    """The exact live-audit failure: datacenter_v1 must not silently
    receive dc2_s's KPI definitions."""
    from utils.vertical_registry import get_kpis

    dc2s_kpis = helpers._get_kpi_definitions('dc2_s')
    dv1_kpis = helpers._get_kpi_definitions('datacenter_v1')

    assert dv1_kpis != dc2s_kpis
    assert dv1_kpis == get_kpis('datacenter_v1')
    # datacenter_v1 has KPIs tagged pillar P6; dc2_s (5 pillars) never does.
    assert any(defn.get('pillar') == 'P6' for defn in dv1_kpis.values()), (
        "datacenter_v1 must have P6-tagged KPIs — dc2_s's KPI set never does"
    )


def test_saas_premium_still_works():
    """Regression guard: the one branch that was already correct
    (saas_premium) must keep returning real SaaS KPI definitions."""
    from utils.vertical_registry import get_kpis

    assert helpers._get_kpi_definitions('saas_premium') == get_kpis('saas_premium')
    assert helpers._get_kpi_definitions('saas') == get_kpis('saas_premium')  # alias


def test_dc2s_unchanged_by_the_refactor():
    """Regression guard: dc2_s's own KPI set must be exactly what it was
    before the fix — routed through the registry, not re-derived differently."""
    from utils.vertical_registry import get_kpis

    assert helpers._get_kpi_definitions('dc2_s') == get_kpis('dc2_s')


def test_every_registered_vertical_returns_real_nonempty_kpis():
    from utils.vertical_registry import SUPPORTED_VERTICALS

    for vertical in SUPPORTED_VERTICALS:
        kpis = helpers._get_kpi_definitions(vertical)
        assert kpis, f"{vertical}: _get_kpi_definitions returned empty/falsy"


def test_unknown_vertical_raises_not_silently_empty():
    """Old behavior silently returned {} for an unresolvable vertical via
    ImportError — now must raise (fail-closed), matching get_kis/get_pillars
    everywhere else in the codebase."""
    import pytest

    with pytest.raises(Exception):
        helpers._get_kpi_definitions('totally_made_up_vertical_xyz')
