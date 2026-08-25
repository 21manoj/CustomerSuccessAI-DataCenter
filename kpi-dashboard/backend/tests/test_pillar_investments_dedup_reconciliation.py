"""pillar_investments reconciles to the single canonical program value.

Item 22 (state-of-play.md) — RESOLVED 2026-08-24 (owner decision).

History: item 17 fixed the Po1 "Growth" double-count by wiring
``dedupe_portfolio_dollar_impact()`` into ``layered_story``'s Growth layer and
``roi_impact``, but NOT into ``pillar_investments`` — those kept summing the raw
(undeduped) per-metric dollar_impacts, so one payload carried two program-value
figures: 1,331,250 (deduped, canonical) and 1,746,250 (pillar sum), 415,000
apart, implying a 5.3× ROI beside the 4.0× headline.

Decision: there is exactly one modeled value per program; the pillar table is an
ALLOCATION of it, never an independent second source. ``_build_pillar_investments``
now splits the canonical ``roi_impact`` / ``effective_investment`` by pillar
weight, so ``sum(impact) == roi_impact`` by construction. This test calls the
REAL builder (not a replica) and guards that reconciliation — if anyone reverts
to summing raw per-metric impacts, the sum jumps back to 1,746,250 and this
fails.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import executive_dashboard_api as api  # noqa: E402
from power_of_1_model import dedupe_portfolio_dollar_impact  # noqa: E402
from utils.vertical_registry import get_pillars  # noqa: E402


def _po1_metrics_at_customer_393_scale():
    """The six metrics' dollar_impact as observed live on customer 393
    (2026-08-22): raw sum 1,746,250, deduped 1,331,250."""
    return [
        {'metric_id': 'NRR', 'dollar_impact': 525000},
        {'metric_id': 'product_adoption', 'dollar_impact': 125000},
        {'metric_id': 'ticket_resolution_time', 'dollar_impact': 190000},
        {'metric_id': 'GRR', 'dollar_impact': 500000},
        {'metric_id': 'expansion_rate', 'dollar_impact': 100000},
        {'metric_id': 'TTFV', 'dollar_impact': 306250},
    ]


def _real_pillar_rows(vertical, roi_impact, effective_investment):
    pillar_codes = sorted(get_pillars(vertical).keys())
    _map, weights = api._cfo_pillar_investment_config(vertical, pillar_codes)
    vertical_pillars = get_pillars(vertical)
    return api._build_pillar_investments(
        pillar_codes, weights, vertical_pillars, roi_impact, effective_investment,
    )


def test_pillar_investments_sum_matches_deduped_canonical_value():
    """sum(pillar_investments[].impact) == the deduped canonical value, NOT the
    raw 1,746,250 metric sum."""
    metrics = _po1_metrics_at_customer_393_scale()
    canonical = dedupe_portfolio_dollar_impact(metrics)  # 1,331,250
    assert canonical == 1331250
    rows = _real_pillar_rows('datacenter_v1', canonical, 331120.0)
    pillar_sum = sum(r['impact'] for r in rows)
    # weight-allocated + rounded per pillar; tolerance covers rounding only
    assert abs(pillar_sum - canonical) < len(rows), (
        f"pillar impact sum {pillar_sum} != canonical {canonical}"
    )
    # and it must NOT have drifted back toward the old double-counted total
    assert abs(pillar_sum - 1746250) > 100000


def test_pillar_investment_sum_matches_effective_spend():
    """The spend side sums to the real effective_investment (no third basis)."""
    rows = _real_pillar_rows('datacenter_v1', 1331250.0, 331120.0)
    inv_sum = sum(r['investment'] for r in rows)
    assert abs(inv_sum - 331120.0) < len(rows)


def test_pillar_roi_equals_headline_roi():
    """Allocation view: every pillar ROI is the headline ROI (impact/spend),
    because both sides split by the same weight — an honest 'this is the one ROI,
    allocated' rather than fabricated per-pillar variation."""
    roi_impact, spend = 1331250.0, 331120.0
    headline = round(roi_impact / spend, 1)
    rows = _real_pillar_rows('datacenter_v1', roi_impact, spend)
    for r in rows:
        assert r['roi'] == headline


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
