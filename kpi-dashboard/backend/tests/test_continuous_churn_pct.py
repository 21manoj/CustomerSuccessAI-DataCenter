"""Item 6, part 2 — CFO per-account ROI must vary continuously with health,
not just by band.

Reviewer finding, live on eval-profile customer_id=406/407 (2026-08-27):
after item 6's first fix (health-band-weighted impact allocation), roi_pct
still showed exactly 3 distinct values — one per band, bit-identical for
every account sharing a band, because both impact_share and arr_share scale
linearly with ARR and the STEP function's per-band churn_pct made ARR
cancel out of the ratio again, one level deeper than the original bug.
_continuous_churn_pct linearly interpolates between the same three band
anchors instead of stepping, so ARR no longer cancels for two accounts in
the same band with different health.

Pure function test — no DB.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from executive_dashboard_api import _continuous_churn_pct  # noqa: E402


def test_band_anchors_match_the_sanctioned_step_function():
    # Same three reference points as context_graph.churn_pct_for_health.
    assert _continuous_churn_pct(0) == 0.40
    assert _continuous_churn_pct(50) == 0.20
    assert _continuous_churn_pct(70) == 0.05


def test_monotonically_decreasing_as_health_improves():
    healths = [0, 20, 40, 49, 50, 60, 69, 70, 85, 100]
    values = [_continuous_churn_pct(h) for h in healths]
    assert values == sorted(values, reverse=True), values


def test_two_accounts_in_the_same_band_get_different_values():
    # Both "critical" (health < 50) — the exact case that used to collapse
    # to a bit-identical roi_pct for the whole band.
    a = _continuous_churn_pct(25.9)
    b = _continuous_churn_pct(38.1)
    assert a != b


def test_out_of_range_health_is_clamped_not_extrapolated_wild():
    assert _continuous_churn_pct(-10) == 0.40
    assert _continuous_churn_pct(150) == 0.02


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
