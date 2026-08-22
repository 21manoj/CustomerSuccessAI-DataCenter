"""
Power-of-1 playbook/KPI-code cross-vertical leak guard (Aug 22 2026).

Live acceptance test (customers 398/399/400, created 2026-08-21 on EC2 to
validate the day's vertical-registry refactor) found PowerOf1Metric.get_playbooks()
falling through to `linked_playbooks` for any non-dc2_s vertical — but
`linked_playbooks` isn't a true generic default, it's saas_premium's own real
playbook catalog (activation-blitz, voc-sprint, etc., from
config/power_of_1_economics.json). A real datacenter_v1 test customer's
outcome-roi/story response returned playbook slugs byte-identical to a real
saas_premium customer's — SaaS's playbooks leaking into a vertical that has
none defined yet.

Separately, `linked_kpi_codes` (P1-KPI1-style, dc2_s-specific codes) had no
per-vertical override at all and was displayed unconditionally in
metric_outcomes[].linked_kpis for every vertical, even though the only real
consumer of these codes for scoring (outcome_roi_api.py's Path 0) was already
gated to dc2_s-only earlier the same day.

Fix: get_playbooks() returns dc2s_linked_playbooks for dc2_s, linked_playbooks
(real data) for saas_premium and for vertical=None (preserves the /demo route
with no resolved customer), and [] for every other named vertical. The 3
MetricOutcome/dict construction sites in outcome_roi_engine.py now suppress
linked_kpis the same way: real codes only for vertical in (None, 'dc2_s').

No DB/Flask app needed — calculate_historical_roi/calculate_forward_roi take
plain dicts, same convention as test_outcome_roi_historical_disclosure.py.
"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from power_of_1_model import POWER_OF_1_METRICS  # noqa: E402
from outcome_roi_engine import calculate_historical_roi, calculate_forward_roi  # noqa: E402

SAMPLE_ACTUALS = {
    "TTFV": {"baseline": 32.83, "current": 30.0},
    "product_adoption": {"baseline": 57.57, "current": 72.43},
    "ticket_resolution_time": {"baseline": 52.21, "current": 48.0},
    "NRR": {"baseline": 102.0, "current": 105.0},
    "GRR": {"baseline": 91.0, "current": 93.0},
    "expansion_rate": {"baseline": 11.0, "current": 13.0},
}


def _metric_with_both_playbook_lists():
    """Find a real Po1 metric that has both dc2s_linked_playbooks and
    linked_playbooks populated, so dc2_s vs saas_premium is a meaningful
    (non-trivially-equal) comparison."""
    for metric in POWER_OF_1_METRICS.values():
        if metric.dc2s_linked_playbooks and metric.linked_playbooks:
            return metric
    raise AssertionError("no Po1 metric has both playbook lists populated — fixture assumption broken")


def test_get_playbooks_dc2s_unchanged():
    metric = _metric_with_both_playbook_lists()
    assert metric.get_playbooks("dc2_s") == metric.dc2s_linked_playbooks


def test_get_playbooks_saas_premium_returns_its_own_real_catalog():
    metric = _metric_with_both_playbook_lists()
    assert metric.get_playbooks("saas_premium") == metric.linked_playbooks
    assert metric.get_playbooks("saas_premium") != metric.get_playbooks("dc2_s")


def test_get_playbooks_no_vertical_preserves_demo_route():
    """vertical=None (e.g. /api/outcome-roi/demo, no resolved customer)
    must keep returning the generic catalog, not an empty list."""
    metric = _metric_with_both_playbook_lists()
    assert metric.get_playbooks(None) == metric.linked_playbooks


def test_get_playbooks_datacenter_v1_gets_empty_not_saas_slugs():
    """The exact live-audit failure: datacenter_v1 must not receive
    saas_premium's real playbook slugs."""
    metric = _metric_with_both_playbook_lists()
    result = metric.get_playbooks("datacenter_v1")
    assert result == []
    assert result != metric.linked_playbooks


def test_get_playbooks_new_vertical_also_gets_empty():
    metric = _metric_with_both_playbook_lists()
    assert metric.get_playbooks("manufacturing_iot") == []


def test_historical_roi_linked_kpis_suppressed_for_non_dc2s_vertical():
    result_dc2s = calculate_historical_roi(dict(SAMPLE_ACTUALS), account_arr=5_000_000, vertical="dc2_s")
    result_other = calculate_historical_roi(dict(SAMPLE_ACTUALS), account_arr=5_000_000, vertical="datacenter_v1")

    dc2s_linked = {m.metric_id: m.linked_kpis for m in result_dc2s.metric_outcomes}
    other_linked = {m.metric_id: m.linked_kpis for m in result_other.metric_outcomes}

    assert any(v for v in dc2s_linked.values()), "dc2_s result should have at least one non-empty linked_kpis"
    assert all(v == [] for v in other_linked.values()), (
        f"datacenter_v1 must not display dc2_s KPI codes: {other_linked}"
    )


def test_historical_roi_linked_kpis_preserved_for_no_vertical():
    result = calculate_historical_roi(dict(SAMPLE_ACTUALS), account_arr=5_000_000, vertical=None)
    linked = {m.metric_id: m.linked_kpis for m in result.metric_outcomes}
    assert any(v for v in linked.values()), "vertical=None (demo route) should keep the generic linked_kpis display"


def test_forward_roi_linked_kpis_and_playbooks_suppressed_for_non_dc2s_vertical():
    result = calculate_forward_roi(
        current_values={mid: m.baseline for mid, m in POWER_OF_1_METRICS.items()},
        target_improvement_pct=1.0,
        account_arr=5_000_000,
        vertical="datacenter_v1",
    )
    for m in result.metric_outcomes:
        assert m.linked_kpis == [], f"{m.metric_id}: linked_kpis leaked for datacenter_v1: {m.linked_kpis}"
        assert m.linked_playbooks != POWER_OF_1_METRICS[m.metric_id].linked_playbooks or not m.linked_playbooks, (
            f"{m.metric_id}: linked_playbooks looks like it leaked saas_premium's real catalog"
        )
