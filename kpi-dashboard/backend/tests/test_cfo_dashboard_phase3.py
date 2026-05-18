"""CFO dashboard Phase 3 — modeled ROI scaling + efficiency helpers."""

from utils.cfo_dashboard_helpers import (
    ROI_PCT_DISPLAY_CAP,
    build_cfo_efficiency_metrics,
    build_roi_scaling,
    resolve_cfo_roi_pct,
)


class _Snap:
    historical_roi_pct = 0
    combined_roi_pct = 0
    historical_impact = 0
    forward_impact = 0
    historical_investment = None


def test_resolve_roi_pct_from_po1_when_snapshot_zero():
    metrics = [
        {'metric_id': 'NRR', 'dollar_impact': 500_000},
        {'metric_id': 'GRR', 'dollar_impact': 300_000},
    ]
    roi_pct, multiple, is_modeled = resolve_cfo_roi_pct(
        _Snap(), metrics, estimated_investment=100_000,
    )
    assert roi_pct > 0
    assert is_modeled is True
    assert multiple > 1


def test_resolve_roi_pct_capped():
    metrics = [{'metric_id': 'NRR', 'dollar_impact': 50_000_000}]
    roi_pct, _, _ = resolve_cfo_roi_pct(None, metrics, estimated_investment=100_000)
    assert roi_pct <= ROI_PCT_DISPLAY_CAP


def test_build_roi_scaling_growth_bars_track_roi():
    scaling = build_roi_scaling(100, 30, is_modeled=True)
    rois = [p['roi'] for p in scaling['projections']]
    bars = [p['growth_bar'] for p in scaling['projections']]
    assert all(r > 0 for r in rois)
    assert bars[-1] >= bars[0]
    assert scaling['is_modeled'] is True


def test_build_roi_scaling_zeros_when_no_roi():
    scaling = build_roi_scaling(0, 10)
    assert all(p['roi'] == 0 for p in scaling['projections'])
    assert all(p['growth_bar'] == 0 for p in scaling['projections'])


def test_efficiency_from_proof():
    block = build_cfo_efficiency_metrics(
        334,
        10_000_000,
        {
            'total_cost': 100_000,
            'revenue_protected': 500_000,
            'revenue_expanded': 0,
            'csm_hours': 200,
        },
        effective_investment=100_000,
        roi_impact=500_000,
    )
    assert block['available'] is True
    assert block['source'] == 'csPulseProof'
    assert block['efficiency_score'] > 0
    assert block['rev_per_cs_dollar'] == 5.0


def test_efficiency_modeled_from_cost_bridge():
    block = build_cfo_efficiency_metrics(
        334,
        50_000_000,
        {'total_cost': 0, 'revenue_protected': 0, 'revenue_expanded': 0},
        effective_investment=500_000,
        roi_impact=2_000_000,
    )
    assert block['available'] is True
    assert block['source'] == 'benchmark'
    assert block['efficiency_score'] > 0 or block['rev_per_cs_dollar'] > 0


def test_cfo_phase3_efficiency_panel_in_ui():
    tsx = (
        __import__('pathlib').Path(__file__).resolve().parents[2]
        / 'src' / 'components' / 'dashboard' / 'CFODashboard.tsx'
    )
    source = tsx.read_text(encoding='utf-8')
    assert 'CFOEfficiencyPanel' in source
    assert 'growth_bar: s.growth_bar' in source
    assert 'Modeled · Po1' in source
