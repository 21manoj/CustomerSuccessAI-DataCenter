"""
Composite-site value-provenance wiring — Track A (state-of-play.md).

The two composite sites named by the plan (`_build_layered_story`,
`nrr_waterfall.roi_x`) blend sub-values of different provenance tiers into
one displayed number. Per the display-treatment convention, the honest
label for a blend is most_conservative() of its inputs — a ROI is only as
grounded as the weaker of its numerator and denominator.

Expected tiers, from what actually feeds each number:
  Layer 1 (Already Delivered): PlaybookExecutionV2 rows both sides
      -> measured
  Layer 2 (Still Protectable): value = real health/ARR through
      health_to_annual_churn_prob (derived); cost = fixed 4560/account
      cost-bridge constant (benchmark) -> benchmark
  Layer 3 (Growth Po1): deck benchmarks both sides -> benchmark
  Blended totals: weakest of all six inputs -> benchmark
  nrr_waterfall.roi_x: derived / benchmark -> benchmark

No Flask/DB needed — _build_layered_story is a pure function.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from executive_dashboard_api import _build_layered_story  # noqa: E402
from utils import value_provenance as vp  # noqa: E402


def _story(**overrides):
    kwargs = dict(
        proof_data={'revenue_protected': 100_000, 'revenue_expanded': 50_000, 'total_cost': 30_000},
        total_arr=10_000_000,
        wf_protectable=200_000,
        wf_expandable=80_000,
        wf_cost=45_600,
        power_of_1_metrics=[
            {'metric_id': 'NRR', 'dollar_impact': 105_000},
            {'metric_id': 'GRR', 'dollar_impact': 100_000},
        ],
    )
    kwargs.update(overrides)
    return _build_layered_story(**kwargs)


def test_per_layer_tiers():
    story = _story()
    by_name = {l['name']: l for l in story['layers']}
    assert by_name['Already Delivered']['data_source'] == vp.MEASURED
    assert by_name['Still Protectable']['data_source'] == vp.BENCHMARK, (
        "layer 2's cost is the fixed cost-bridge constant — its ROI must "
        "not be labeled 'derived' just because the numerator is"
    )
    assert by_name['Growth (Po1 1%)']['data_source'] == vp.BENCHMARK


def test_blended_totals_carry_weakest_input_tier():
    story = _story()
    assert story['data_source'] == vp.BENCHMARK
    # and it's a valid tier, not an arbitrary string
    assert vp.is_valid(story['data_source'])


def test_every_layer_declares_a_valid_tier():
    story = _story()
    for layer in story['layers']:
        assert vp.is_valid(layer.get('data_source')), (
            f"layer {layer['name']!r} missing or invalid data_source"
        )


def test_most_conservative_derived_benchmark_is_benchmark():
    """Pins the exact blend nrr_waterfall.roi_x declares inline."""
    assert vp.most_conservative([vp.DERIVED, vp.BENCHMARK]) == vp.BENCHMARK


def test_nrr_waterfall_response_block_declares_the_blend():
    """Source-level guard: the nrr_waterfall dict in the CFO response must
    carry a data_source computed via most_conservative, not a bare literal
    that can silently drift from the components it describes."""
    import inspect
    import executive_dashboard_api as api

    src = inspect.getsource(api)
    wf_start = src.index("'nrr_waterfall': {")
    wf_block = src[wf_start:wf_start + 900]
    assert "'data_source': _vp.most_conservative(" in wf_block, (
        "nrr_waterfall must declare its provenance via most_conservative() "
        "over its components' tiers"
    )


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
