"""
Outcome ROI pillar→metric map — vertical-coupling guard (Aug 21 2026).

A live audit against customer 390 (datacenter_v1, 12 real accounts) found
outcome_roi_api's PillarScore-data-path functions (_extract_historical_actuals,
_extract_current_values, _extract_accounts_at_risk) using a module-level
DC2S_PILLAR_METRIC_MAP unconditionally for every customer, regardless of
vertical. Confirmed live: _extract_current_values(customer 390) returned
{'TTFV', 'NRR', 'GRR', 'ticket_resolution_time', 'product_adoption',
'expansion_rate'} — pure dc2_s pillar semantics (P1=Deployment Velocity, etc.)
fabricated as the dollar-figure ROI story for a datacenter customer whose real
P1 is "Revenue & Unit Economics". The NRR-synthesis step (P4*0.4 + P5*0.6,
"retention + expansion") had the same defect — datacenter_v1's P4 is "Power &
Facility", not a retention pillar.

Fix: DC2S_PILLAR_METRIC_MAP replaced with POWER_OF_1_PILLAR_MAPS, a per-vertical
table, resolved via _pillar_metric_map_for_customer(customer_id) ->
utils.vertical_registry.get_vertical_for_customer. Verticals without an
explicit entry get a generic positional fallback (distinct real metric_ids,
never dc2_s's mislabeled onto a different vertical).

No DB/Flask app needed — same convention as test_vertical_catalog_consistency.py.
"""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import outcome_roi_api as api  # noqa: E402
from power_of_1_model import POWER_OF_1_METRICS  # noqa: E402

VALID_METRIC_IDS = set(POWER_OF_1_METRICS.keys())


def test_dc2s_map_unchanged_by_the_refactor():
    """Regression guard: dc2_s's own mapping must be byte-for-byte what it was
    before the fix (P1->TTFV, P2->ticket_resolution_time, P3->product_adoption,
    P4->GRR, P5->expansion_rate, NRR synthesized 0.4*P4 + 0.6*P5)."""
    pillar_map, nrr = api._get_pillar_metric_map('dc2_s')
    assert pillar_map == {
        'P1': 'TTFV',
        'P2': 'ticket_resolution_time',
        'P3': 'product_adoption',
        'P4': 'GRR',
        'P5': 'expansion_rate',
    }
    assert nrr == {
        'retention_pillar': 'P4', 'retention_weight': 0.4,
        'expansion_pillar': 'P5', 'expansion_weight': 0.6,
    }


def test_datacenter_v1_does_not_inherit_dc2s_semantics():
    """The exact live-audit failure: datacenter_v1's P1 ('Revenue & Unit
    Economics') must not be reported as TTFV ('Deployment Velocity') -- that
    was dc2_s's P1, not datacenter_v1's."""
    pillar_map, _nrr = api._get_pillar_metric_map('datacenter_v1')
    assert pillar_map != api._get_pillar_metric_map('dc2_s')[0]
    assert pillar_map['P1'] != 'TTFV', (
        "datacenter_v1 P1 is 'Revenue & Unit Economics', not dc2_s's "
        "'Deployment Velocity' -- must not map to TTFV"
    )


def test_every_registered_vertical_gets_a_distinct_real_metric_per_pillar():
    """Every pillar_code in every vertical's own catalog must map to a real
    Power-of-1 metric_id, and no two pillars within the same vertical should
    silently collide on the same metric_id (would flatten the ROI story)."""
    from utils.vertical_registry import SUPPORTED_VERTICALS, get_pillars

    for vertical in SUPPORTED_VERTICALS:
        pillar_map, _nrr = api._get_pillar_metric_map(vertical)
        catalog_codes = set(get_pillars(vertical).keys())

        assert set(pillar_map.keys()) == catalog_codes, (
            f"{vertical}: pillar_metric_map keys {set(pillar_map.keys())} "
            f"don't match its own catalog's pillar codes {catalog_codes}"
        )
        for pillar_code, metric_id in pillar_map.items():
            assert metric_id in VALID_METRIC_IDS, (
                f"{vertical} pillar {pillar_code} maps to unknown metric_id {metric_id!r}"
            )
        assert len(set(pillar_map.values())) == len(pillar_map), (
            f"{vertical}: two pillars collide on the same Power-of-1 metric_id: {pillar_map}"
        )


def test_nrr_synthesis_pillars_belong_to_the_same_vertical():
    """If a vertical declares nrr_synthesis, its retention/expansion pillar
    codes must be pillars that vertical actually has (no cross-vertical P4/P5
    hardcode bleeding into a vertical with a different pillar count)."""
    from utils.vertical_registry import SUPPORTED_VERTICALS, get_pillars

    for vertical in SUPPORTED_VERTICALS:
        _pillar_map, nrr = api._get_pillar_metric_map(vertical)
        if nrr is None:
            continue
        catalog_codes = set(get_pillars(vertical).keys())
        assert nrr['retention_pillar'] in catalog_codes
        assert nrr['expansion_pillar'] in catalog_codes


def test_pillar_metric_map_for_customer_falls_back_to_dc2s_only_without_customer_id():
    pillar_map, nrr = api._pillar_metric_map_for_customer(None)
    assert (pillar_map, nrr) == api._get_pillar_metric_map('dc2_s')


def test_nrr_synthesis_expansion_pillar_matches_phase2_pillar_roles_registry():
    """Phase 3 retrofit (2026-08-21): nrr_synthesis's expansion_pillar must be
    sourced from utils.vertical_registry.role(vertical, 'expansion') -- Phase 2's
    pillar_roles registry -- not just hand-authored a second time in
    POWER_OF_1_PILLAR_MAPS. 'expansion' has an exact match in the registry's
    shared vocabulary (unlike 'retention', which has none, so retention_pillar
    stays hand-authored on purpose and is NOT checked here)."""
    from utils.vertical_registry import role, SUPPORTED_VERTICALS

    checked_any = False
    for vertical in SUPPORTED_VERTICALS:
        _pillar_map, nrr = api._get_pillar_metric_map(vertical)
        if nrr is None:
            continue
        expected = role(vertical, 'expansion')
        assert expected is not None, (
            f"{vertical} declares nrr_synthesis but pillar_roles has no "
            f"'expansion' role for it -- registry and Power-of-1 map disagree"
        )
        assert nrr['expansion_pillar'] == expected, (
            f"{vertical}: nrr_synthesis.expansion_pillar={nrr['expansion_pillar']!r} "
            f"does not match pillar_roles' role('expansion')={expected!r}"
        )
        checked_any = True

    assert checked_any, "no vertical with nrr_synthesis was found to check"


def test_nrr_synthesis_expansion_pillar_is_actually_wired_through_role():
    """Prove the resolution goes THROUGH utils.vertical_registry.role() at call
    time -- not just that the hand-authored dict happens to already agree with
    it (it does, for every vertical today, which would let a no-op pass a
    naive equality check). Monkeypatch role() to return a distinguishable
    sentinel pillar code and confirm _get_pillar_metric_map picks it up."""
    import utils.vertical_registry as registry

    original_role = registry.role
    try:
        registry.role = lambda vertical, role_name: (
            'P9-SENTINEL' if role_name == 'expansion' else original_role(vertical, role_name)
        )
        _pillar_map, nrr = api._get_pillar_metric_map('dc2_s')
        assert nrr['expansion_pillar'] == 'P9-SENTINEL', (
            "expansion_pillar did not pick up the monkeypatched role() return value "
            "-- _get_pillar_metric_map is not actually resolving it dynamically"
        )
        # retention_pillar must be unaffected by patching the 'expansion' role
        assert nrr['retention_pillar'] == 'P4'
    finally:
        registry.role = original_role


def test_nrr_synthesis_retention_pillar_stays_hand_authored_no_partner_role_used():
    """retention_pillar must NOT be silently sourced from role(vertical, 'partner')
    -- pillar_roles has no 'retention' role, and 'partner' is not the same concept
    even though they land on the same pillar for dc2_s/saas_premium today. This
    guards against a future refactor collapsing the two without a deliberate
    decision (see Phase 3 report's open question)."""
    for vertical in ('dc2_s', 'saas_premium'):
        _pillar_map, nrr = api._get_pillar_metric_map(vertical)
        assert nrr['retention_pillar'] == \
            api.POWER_OF_1_PILLAR_MAPS[vertical]['nrr_synthesis']['retention_pillar']
