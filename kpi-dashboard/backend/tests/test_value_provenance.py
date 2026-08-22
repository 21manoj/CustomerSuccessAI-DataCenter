#!/usr/bin/env python3
"""
utils.value_provenance unit tests — no DB/Flask app needed (same
convention as test_outcome_roi_pillar_metric_map.py / test_vertical_
catalog_consistency.py).

Pins the customer-facing NUMBER provenance vocabulary (measured / derived
/ benchmark / default / unavailable) that outcome_roi_api.py's
data_source strings were retrofitted onto in the Aug 21 2026 session,
and asserts it stays a distinct vocabulary from utils/provenance.py's
graph-node vocabulary (observed / inferred / synthetic).
"""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import utils.value_provenance as vp  # noqa: E402
import utils.provenance as graph_provenance  # noqa: E402


def test_five_canonical_tiers_exact():
    assert vp.ALL_TIERS == ('measured', 'derived', 'benchmark', 'default', 'unavailable')
    assert vp.MEASURED == 'measured'
    assert vp.DERIVED == 'derived'
    assert vp.BENCHMARK == 'benchmark'
    assert vp.DEFAULT == 'default'
    assert vp.UNAVAILABLE == 'unavailable'


def test_is_valid():
    for t in vp.ALL_TIERS:
        assert vp.is_valid(t)
    assert not vp.is_valid('observed')     # graph-provenance value, not ours
    assert not vp.is_valid('customer')     # legacy graph-provenance value
    assert not vp.is_valid(None)
    assert not vp.is_valid('bogus')


def test_distinct_vocabulary_from_graph_provenance():
    """The two provenance modules must not share values — conflating them
    is exactly the mistake this module's docstring warns against."""
    assert set(vp.ALL_TIERS).isdisjoint(set(graph_provenance.ALL_SOURCES)), (
        "value_provenance tiers must never overlap with utils.provenance "
        "graph-node source values"
    )


def test_is_real_signal():
    assert vp.is_real_signal(vp.MEASURED) is True
    assert vp.is_real_signal(vp.DERIVED) is True
    assert vp.is_real_signal(vp.BENCHMARK) is True
    assert vp.is_real_signal(vp.DEFAULT) is False
    assert vp.is_real_signal(vp.UNAVAILABLE) is False
    assert vp.is_real_signal(None) is False


def test_calibration_tier():
    assert vp.calibration_tier(calibrated=True) == vp.DERIVED
    assert vp.calibration_tier(calibrated=False) == vp.BENCHMARK


def test_most_conservative_picks_weakest_link():
    # Any DEFAULT/UNAVAILABLE input drags the combined tier down.
    assert vp.most_conservative([vp.MEASURED, vp.DERIVED]) == vp.DERIVED
    assert vp.most_conservative([vp.MEASURED, vp.BENCHMARK]) == vp.BENCHMARK
    assert vp.most_conservative([vp.MEASURED, vp.DEFAULT]) == vp.DEFAULT
    assert vp.most_conservative([vp.DERIVED, vp.UNAVAILABLE]) == vp.UNAVAILABLE
    assert vp.most_conservative([vp.MEASURED]) == vp.MEASURED


def test_most_conservative_empty_is_unavailable():
    assert vp.most_conservative([]) == vp.UNAVAILABLE
    assert vp.most_conservative([None, None]) == vp.UNAVAILABLE


def test_label_covers_every_tier():
    for t in vp.ALL_TIERS:
        lbl = vp.label(t)
        assert isinstance(lbl, str) and lbl


def test_value_provenance_behaves_as_plain_str():
    """ValueProvenance must be a drop-in str so existing `data_source ==
    'benchmark'` / jsonify() callers keep working unchanged."""
    ds = vp.tag(vp.DERIVED, 'kpi_actuals_calibrated')
    assert ds == vp.DERIVED
    assert ds == 'derived'
    assert isinstance(ds, str)
    assert f"tier is {ds}" == "tier is derived"


def test_value_provenance_carries_detail_breadcrumb():
    ds = vp.tag(vp.BENCHMARK, 'health_score_pillars_benchmark_stable_skip3')
    assert ds.tier == vp.BENCHMARK
    assert ds.detail == 'health_score_pillars_benchmark_stable_skip3'


def test_value_provenance_default_detail_falls_back_to_tier():
    ds = vp.tag(vp.DEFAULT)
    assert ds.detail == vp.DEFAULT


def test_value_provenance_json_serializable():
    import json
    ds = vp.tag(vp.MEASURED, 'dc2s_kpi_row')
    payload = json.dumps({'data_source': ds})
    assert '"data_source": "measured"' in payload
    # The detail breadcrumb intentionally does NOT leak into default JSON
    # serialization — callers opt in explicitly via `.detail`.
    assert 'dc2s_kpi_row' not in payload
