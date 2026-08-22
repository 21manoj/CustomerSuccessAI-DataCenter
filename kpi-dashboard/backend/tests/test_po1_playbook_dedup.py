"""
Power-of-1 playbook-dedup tests — vertical-coupling audit Finding 6 (2026-08-21).

Three of the six Power-of-1 metrics share an underlying playbook with another
metric (PB-01 -> TTFV + product_adoption, PB-02 -> GRR + ticket_resolution_time,
PB-04 -> NRR + expansion_rate). A naive sum of all six metrics' dollar_impact
double-counts each shared playbook's benefit once per metric it's linked to.
`dedupe_portfolio_dollar_impact` keeps only the larger figure per shared
playbook, matching the same "most-conservative claim wins" convention as
`utils.value_provenance.most_conservative`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from power_of_1_model import POWER_OF_1_METRICS, dedupe_portfolio_dollar_impact


def _metrics_at_1pct():
    return [
        {'metric_id': mid, 'dollar_impact': m.annual_impact_per_pct}
        for mid, m in POWER_OF_1_METRICS.items()
    ]


def test_dedup_drops_the_three_shared_playbook_overlaps():
    """349,250 naive sum -> 266,250 deduped (drops product_adoption 25k,
    ticket_resolution_time 38k, expansion_rate 20k -- the smaller metric in
    each of the 3 shared-playbook pairs)."""
    metrics = _metrics_at_1pct()
    naive_sum = sum(m['dollar_impact'] for m in metrics)
    assert naive_sum == 349250

    deduped = dedupe_portfolio_dollar_impact(metrics)
    assert deduped == 266250
    assert deduped < naive_sum


def test_dedup_keeps_the_larger_metric_in_each_shared_pair():
    metrics = _metrics_at_1pct()
    deduped = dedupe_portfolio_dollar_impact(metrics)
    # TTFV (61,250) beats product_adoption (25,000) on PB-01
    # GRR (100,000) beats ticket_resolution_time (38,000) on PB-02
    # NRR (105,000) beats expansion_rate (20,000) on PB-04
    assert deduped == 61250 + 105000 + 100000


def test_dedup_is_order_independent():
    metrics = _metrics_at_1pct()
    forward = dedupe_portfolio_dollar_impact(metrics)
    backward = dedupe_portfolio_dollar_impact(list(reversed(metrics)))
    assert forward == backward


def test_no_overlap_sums_fully():
    """NRR and GRR don't share a playbook with each other -- full sum."""
    metrics = [
        {'metric_id': 'NRR', 'dollar_impact': 105000},
        {'metric_id': 'GRR', 'dollar_impact': 100000},
    ]
    assert dedupe_portfolio_dollar_impact(metrics) == 205000


def test_unknown_metric_id_contributes_without_crashing():
    metrics = [{'metric_id': 'not_a_real_metric', 'dollar_impact': 42}]
    assert dedupe_portfolio_dollar_impact(metrics) == 42


def test_empty_list_returns_zero():
    assert dedupe_portfolio_dollar_impact([]) == 0


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
