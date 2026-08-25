"""Item 6 — per-account CFO ROI must not collapse to a constant.

The benchmark branch of ``_build_cfo_account_details`` used to scale BOTH
investment and impact by the same ``arr_share``, so the share cancelled in the
ROI ratio and every account reported the identical portfolio ROI (302% on 390)
regardless of ARR or health — a constant column that read as if measured.

Fix: investment stays ∝ ARR (servicing cost ≈ account size); impact is
allocated ∝ recoverable revenue = ARR × churn_pct(health) (the sanctioned
40/20/5 band, single source ``churn_pct_for_health``) and renormalized so the
per-account impacts still sum to the portfolio total.

Two invariants this pins:
  1. ROI varies by health band (equal-ARR accounts in different bands differ).
  2. Reconciliation: sum(acct_impact) == total_impact (renormalization holds).

Pure re-implementation of the allocation contract — no DB — plus a direct
check of the shared band function.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from utils.context_graph import churn_pct_for_health  # noqa: E402


def test_band_function_matches_sanctioned_model():
    assert churn_pct_for_health(30) == 0.40   # critical
    assert churn_pct_for_health(49.9) == 0.40
    assert churn_pct_for_health(50) == 0.20    # at-risk
    assert churn_pct_for_health(69.9) == 0.20
    assert churn_pct_for_health(70) == 0.05    # healthy
    assert churn_pct_for_health(95) == 0.05


def _allocate(accounts, total_investment, total_impact):
    """Mirror of the benchmark allocation in _build_cfo_account_details."""
    total_arr = sum(a['arr'] for a in accounts)
    weights = {a['id']: a['arr'] * churn_pct_for_health(a['health']) for a in accounts}
    total_w = sum(weights.values())
    out = []
    for a in accounts:
        arr_share = a['arr'] / total_arr if total_arr else 0
        impact_share = weights[a['id']] / total_w if total_w else arr_share
        inv = total_investment * arr_share
        imp = total_impact * impact_share
        roi = round((imp / inv - 1) * 100) if inv > 0 else 0
        out.append({'id': a['id'], 'investment': inv, 'impact': imp, 'roi': roi})
    return out


def test_equal_arr_different_health_gives_different_roi():
    # same ARR, different health band -> ROI must differ (used to be identical)
    accts = [
        {'id': 1, 'arr': 1_000_000, 'health': 30},   # critical, 0.40
        {'id': 2, 'arr': 1_000_000, 'health': 85},   # healthy, 0.05
    ]
    rows = _allocate(accts, total_investment=200_000, total_impact=800_000)
    roi = {r['id']: r['roi'] for r in rows}
    assert roi[1] != roi[2]
    # critical account protects more recoverable revenue per servicing dollar
    assert roi[1] > roi[2]


def test_impact_reconciles_to_portfolio_total():
    accts = [
        {'id': 1, 'arr': 3_000_000, 'health': 35},
        {'id': 2, 'arr': 2_000_000, 'health': 62},
        {'id': 3, 'arr': 5_000_000, 'health': 78},
    ]
    total_impact = 1_331_250
    rows = _allocate(accts, total_investment=331_120, total_impact=total_impact)
    assert abs(sum(r['impact'] for r in rows) - total_impact) < 1e-6
    # and it is genuinely non-constant across the three bands
    assert len({r['roi'] for r in rows}) == 3


def test_all_same_band_is_legitimately_constant():
    # if every account shares a band the ROI IS constant — but that is a real
    # property (identical risk profile), not the cancellation artifact.
    accts = [
        {'id': 1, 'arr': 1_000_000, 'health': 80},
        {'id': 2, 'arr': 4_000_000, 'health': 90},
    ]
    rows = _allocate(accts, total_investment=200_000, total_impact=800_000)
    assert len({r['roi'] for r in rows}) == 1


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
