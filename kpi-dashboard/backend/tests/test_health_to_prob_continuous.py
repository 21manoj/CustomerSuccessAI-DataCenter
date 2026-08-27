"""Item 13 — health_to_annual_churn_prob/expansion_prob must be continuous,
not banded with flat regions or boundary discontinuities.

Reviewer finding, live on eval-profile customer_id=405/406/407 (2026-08-27):
cost_of_inaction.churn_pct read exactly 45.0 for both health=14.7 and
health=19.8 — health_to_annual_churn_prob returned a flat 0.45 for every
health below 30. Deeper look found a second, unreported defect: the
if/elif band boundaries didn't connect (health=49.9 -> ~35%, health=50.0 ->
25%, a sudden 10-point drop for a 0.1-point health change; same at the
health=70 boundary). Both functions rewritten as continuous piecewise-
linear interpolation over the same documented band anchors.

Pure function tests — no DB.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from utils.playbook_lifecycle import (  # noqa: E402
    health_to_annual_churn_prob,
    health_to_annual_expansion_prob,
)


def test_below_30_is_no_longer_flat():
    # The exact reported case: two different health scores under 30 must
    # no longer produce the identical churn probability.
    assert health_to_annual_churn_prob(14.7) != health_to_annual_churn_prob(19.8)


def test_no_discontinuity_at_any_band_boundary():
    for boundary in (30, 50, 70, 85):
        just_below = health_to_annual_churn_prob(boundary - 0.1)
        at_boundary = health_to_annual_churn_prob(boundary)
        just_above = health_to_annual_churn_prob(boundary + 0.1)
        assert abs(just_below - at_boundary) < 0.01, (boundary, just_below, at_boundary)
        assert abs(at_boundary - just_above) < 0.01, (boundary, at_boundary, just_above)


def test_monotonically_decreasing_with_health():
    healths = [0, 20, 40, 49, 50, 60, 69, 70, 85, 100]
    values = [health_to_annual_churn_prob(h) for h in healths]
    assert values == sorted(values, reverse=True), values


def test_documented_band_anchors_still_hold():
    # Same reference values the original bands' own endpoints already
    # documented — the fix must not change the model's intent, only its
    # continuity.
    assert health_to_annual_churn_prob(50) == 0.25
    assert health_to_annual_churn_prob(70) == 0.08
    assert health_to_annual_churn_prob(100) == 0.03


def test_expansion_prob_also_continuous_and_monotonic():
    healths = [0, 20, 40, 49, 50, 60, 69, 70, 85, 100]
    values = [health_to_annual_expansion_prob(h) for h in healths]
    assert values == sorted(values), values  # increasing with health
    for boundary in (30, 50, 70, 85):
        just_below = health_to_annual_expansion_prob(boundary - 0.1)
        just_above = health_to_annual_expansion_prob(boundary + 0.1)
        assert abs(just_above - just_below) < 0.01, (boundary, just_below, just_above)


def test_none_health_still_returns_documented_default():
    assert health_to_annual_churn_prob(None) == 0.20
    assert health_to_annual_expansion_prob(None) == 0.05


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
