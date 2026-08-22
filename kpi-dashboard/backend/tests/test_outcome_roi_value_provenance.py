#!/usr/bin/env python3
"""
outcome_roi_api.py's value_provenance retrofit — pins the mapping from
Wizard-C calibration state to the new measured/derived/benchmark/default/
unavailable tiers, and the ValueProvenance shape returned by
_extract_pillar_velocities's terminal (no-data) branches.

No DB/Flask app needed — same convention as
test_outcome_roi_pillar_metric_map.py. `_tag_real_data_source` and the
UNAVAILABLE-tagging in `_extract_pillar_velocities`'s early-return
branches are pure functions/pure-Python control flow with no DB access,
so they're directly unit-testable.
"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import outcome_roi_api as api  # noqa: E402
import utils.value_provenance as vp  # noqa: E402


def test_tag_real_data_source_calibrated_is_derived():
    ds = api._tag_real_data_source('kpi_actuals', calibrated=True)
    assert ds == vp.DERIVED
    assert ds.tier == vp.DERIVED
    assert ds.detail == 'kpi_actuals_calibrated'


def test_tag_real_data_source_uncalibrated_is_benchmark():
    ds = api._tag_real_data_source('health_trends', calibrated=False)
    assert ds == vp.BENCHMARK
    assert ds.tier == vp.BENCHMARK
    assert ds.detail == 'health_trends_benchmark'


def test_tag_real_data_source_preserves_stable_window_breadcrumb():
    """Option-A stable-window skip must still be visible in .detail even
    though the primary tier collapses to the 5-value vocabulary."""
    ds = api._tag_real_data_source(
        'health_score_pillars', calibrated=True, stable_tag='_stable_skip3',
    )
    assert ds == vp.DERIVED
    assert ds.detail == 'health_score_pillars_calibrated_stable_skip3'

    ds2 = api._tag_real_data_source(
        'health_score_pillars', calibrated=False, stable_tag='_stable_skip3',
    )
    assert ds2 == vp.BENCHMARK
    assert ds2.detail == 'health_score_pillars_benchmark_stable_skip3'


def test_tag_real_data_source_returns_value_provenance_instance():
    ds = api._tag_real_data_source('kpi_actuals', calibrated=True)
    assert isinstance(ds, vp.ValueProvenance)
    assert isinstance(ds, str)  # backward-compat: still a plain string


def test_extract_pillar_velocities_no_accounts_is_unavailable():
    velocities, data_source = api._extract_pillar_velocities([], months=6)
    assert velocities == {}
    assert data_source == vp.UNAVAILABLE
    assert data_source.detail == 'no_data'


def test_baseline_defaults_data_source_is_default_tier():
    """_extract_historical_actuals / _extract_current_values with no
    accounts must resolve to the DEFAULT tier (static fallback, zero
    real customer signal) — not BENCHMARK, which implies real data was
    blended in."""
    metric_actuals, data_source = api._extract_historical_actuals([], months=6)
    assert data_source == vp.DEFAULT
    assert data_source.detail == 'baseline_defaults'
    assert metric_actuals == api._get_baseline_actuals()

    current_values, data_source2 = api._extract_current_values([])
    assert data_source2 == vp.DEFAULT
    assert current_values == api._get_baseline_current_values()
