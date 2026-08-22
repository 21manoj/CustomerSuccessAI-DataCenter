"""
pillar_investments vs layered_story.Growth reconciliation (2026-08-22).

Item 17 (Po1 "Growth" double-count) was fixed by wiring
power_of_1_model.dedupe_portfolio_dollar_impact() into layered_story's
Growth layer and roi_impact. It was NOT wired into pillar_investments'
per-pillar impact values -- those still sum the raw (undeduped) six metric
dollar_impacts, because datacenter_v1's pillar->metric mapping is 1:1 and
each pillar's own row legitimately wants to show its own metric's value.

Before the fix, every surface agreed on 1,746,250: consistent and wrong.
Now layered_story.Growth and roi_impact say 1,331,250 (deduped) while
pillar_investments sums to 1,746,250 (not deduped) -- a live divergence in
one payload, 415,000 apart, with nothing marking which is authoritative.
That's worse to spot than the uniform bug it replaced.

This test intentionally FAILS until pillar_investments' dedup reaches
parity with layered_story's -- it's the marker for open item 22 (see
state-of-play.md), not a passing regression guard yet. Do not "fix" it by
loosening the assertion; fix it by making the two sides agree.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pytest  # noqa: E402

import executive_dashboard_api as api  # noqa: E402
from power_of_1_model import POWER_OF_1_METRICS, dedupe_portfolio_dollar_impact  # noqa: E402


def _po1_metrics_at_customer_393_scale():
    """The six metrics' dollar_impact as observed live on customer 393
    (2026-08-22), which summed to the pre-fix 1,746,250 and now dedupes to
    1,331,250 via dedupe_portfolio_dollar_impact()."""
    return [
        {'metric_id': 'NRR', 'dollar_impact': 525000},
        {'metric_id': 'product_adoption', 'dollar_impact': 125000},
        {'metric_id': 'ticket_resolution_time', 'dollar_impact': 190000},
        {'metric_id': 'GRR', 'dollar_impact': 500000},
        {'metric_id': 'expansion_rate', 'dollar_impact': 100000},
        {'metric_id': 'TTFV', 'dollar_impact': 306250},
    ]


def _pillar_investments_impact_sum(vertical, power_of_1_metrics):
    """Replicates executive_dashboard_api.cfo_dashboard()'s pillar_investments
    impact computation (lines ~1271-1292): for each pillar, sum the raw
    dollar_impact of its mapped metric(s) -- no dedup applied."""
    from utils.vertical_registry import get_pillars

    pillar_codes = sorted(get_pillars(vertical).keys())
    pillar_metric_map, _weights = api._cfo_pillar_investment_config(vertical, pillar_codes)
    po1_by_metric = {m['metric_id']: m.get('dollar_impact', 0) for m in power_of_1_metrics}

    total = 0.0
    for pcode in pillar_codes:
        mapped_metrics = pillar_metric_map.get(pcode, [])
        total += sum(po1_by_metric.get(m, 0) for m in mapped_metrics)
    return total


def test_naive_pillar_sum_matches_naive_metric_sum_sanity_check():
    """Sanity check on the replication itself, not the bug: with datacenter_v1's
    1:1 pillar<->metric mapping, summing pillar_investments' raw impacts must
    equal summing the six metrics' raw dollar_impact directly."""
    metrics = _po1_metrics_at_customer_393_scale()
    naive_metric_sum = sum(m['dollar_impact'] for m in metrics)
    assert naive_metric_sum == 1746250
    assert _pillar_investments_impact_sum('datacenter_v1', metrics) == naive_metric_sum


@pytest.mark.xfail(
    reason="open item 22 (state-of-play.md): pillar_investments' per-pillar "
           "impact values are not deduped by shared playbook, only "
           "layered_story's Growth layer is. Flip to a plain assert (and "
           "remove the xfail marker) once dedup reaches both sides.",
    strict=True,
)
def test_pillar_investments_sum_matches_deduped_growth_total():
    """The reconciliation CC-review asked for: sum(pillar_investments[].impact)
    must equal layered_story.Growth.value. Currently 1,746,250 vs 1,331,250 --
    415,000 (31%) apart, live on customer 393."""
    metrics = _po1_metrics_at_customer_393_scale()
    deduped_growth_total = dedupe_portfolio_dollar_impact(metrics)
    pillar_sum = _pillar_investments_impact_sum('datacenter_v1', metrics)
    assert pillar_sum == deduped_growth_total, (
        f"pillar_investments sums to {pillar_sum}, layered_story Growth is "
        f"{deduped_growth_total} -- {pillar_sum - deduped_growth_total} apart"
    )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
