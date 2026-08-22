"""
CFO dashboard pillar-investment breakdown — vertical-coupling guard (bug #2,
Aug 21 2026 audit).

Live audit against customer 390 (datacenter_v1, 12 real accounts) found
executive_dashboard_api.cfo_dashboard() serving dc2_s's 5 pillar names
(DC2S_PILLAR_DISPLAY) and a hardcoded ['P1'..'P5'] loop to every vertical,
regardless of the tenant's real pillars. Worse than a label bug: datacenter_v1
has 6 pillars, so its 6th pillar (Provisioning Velocity) was silently dropped
from the CFO report's real-dollar breakdown entirely — not mislabeled, just
absent.

Fix: DC2S_PILLAR_DISPLAY + the hardcoded loop replaced with
CFO_PILLAR_INVESTMENT_CONFIG (per-vertical metric_groups + weights) and
_cfo_pillar_investment_config(), resolved via the tenant's real
utils.vertical_registry.get_pillars(vertical) — same pattern as the
DC2S_PILLAR_METRIC_MAP -> POWER_OF_1_PILLAR_MAPS fix shipped earlier today in
outcome_roi_api.py.

No DB/Flask app needed — same convention as test_vertical_catalog_consistency.py.
"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import executive_dashboard_api as api  # noqa: E402
from power_of_1_model import POWER_OF_1_METRICS  # noqa: E402

VALID_METRIC_IDS = set(POWER_OF_1_METRICS.keys())


def test_dc2s_config_unchanged_by_the_refactor():
    """Regression guard: dc2_s's own metric groups/weights must be
    byte-for-byte what the original hardcode was."""
    groups, weights = api._cfo_pillar_investment_config('dc2_s', ['P1', 'P2', 'P3', 'P4', 'P5'])
    assert groups == {
        'P1': ['TTFV', 'product_adoption'],
        'P2': ['ticket_resolution_time'],
        'P3': ['NRR', 'GRR'],
        'P4': [],
        'P5': ['expansion_rate'],
    }
    assert weights == {'P1': 0.25, 'P2': 0.15, 'P3': 0.30, 'P4': 0.10, 'P5': 0.20}


def test_datacenter_v1_gets_all_six_pillars_not_five():
    """The exact live-audit failure: datacenter_v1's P6 (Provisioning
    Velocity) must not be silently dropped from the CFO breakdown."""
    from utils.vertical_registry import get_pillars

    pillar_codes = sorted(get_pillars('datacenter_v1').keys())
    assert 'P6' in pillar_codes, "datacenter_v1 must have 6 pillars for this test to be meaningful"

    groups, weights = api._cfo_pillar_investment_config('datacenter_v1', pillar_codes)
    assert set(weights.keys()) == set(pillar_codes), (
        "every datacenter_v1 pillar must get an investment weight — none silently dropped"
    )
    assert 'P6' in groups


def test_every_registered_vertical_gets_real_weights_summing_to_one():
    """Every vertical's CFO pillar weights must sum to 1.0 (investment
    allocation must be exhaustive, not partial) and reference real metric_ids."""
    from utils.vertical_registry import SUPPORTED_VERTICALS, get_pillars

    for vertical in SUPPORTED_VERTICALS:
        pillar_codes = sorted(get_pillars(vertical).keys())
        groups, weights = api._cfo_pillar_investment_config(vertical, pillar_codes)

        assert set(weights.keys()) == set(pillar_codes), (
            f"{vertical}: weight keys {set(weights.keys())} don't match its own "
            f"catalog's pillar codes {set(pillar_codes)}"
        )
        assert abs(sum(weights.values()) - 1.0) < 0.01, (
            f"{vertical}: pillar weights sum to {sum(weights.values())}, not 1.0"
        )
        for pcode, metric_ids in groups.items():
            for metric_id in metric_ids:
                assert metric_id in VALID_METRIC_IDS, (
                    f"{vertical} pillar {pcode} references unknown metric_id {metric_id!r}"
                )


def test_datacenter_v1_does_not_inherit_dc2s_pillar_names():
    """datacenter_v1's real pillar names must be used, not dc2_s's."""
    from utils.vertical_registry import get_pillars

    dc_pillars = get_pillars('datacenter_v1')
    assert dc_pillars['P1']['name'] != 'Deployment Velocity', (
        "datacenter_v1 P1 is 'Revenue & Unit Economics', not dc2_s's own P1 name"
    )


def test_unregistered_vertical_falls_back_to_even_weights_not_dc2s():
    """A vertical with no curated CFO config must get an even split across
    its OWN pillar codes, never dc2_s's config silently reused."""
    groups, weights = api._cfo_pillar_investment_config('some_future_vertical', ['P1', 'P2', 'P3'])
    assert groups == {}
    assert set(weights.keys()) == {'P1', 'P2', 'P3'}
    assert abs(sum(weights.values()) - 1.0) < 0.01
