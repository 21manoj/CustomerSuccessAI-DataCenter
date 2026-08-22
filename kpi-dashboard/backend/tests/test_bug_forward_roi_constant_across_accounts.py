"""
Forward-projected ROI% was a mathematical constant across every account,
regardless of ARR (tracer finding, Aug 2026: 2577.6% for every one of 12 real
accounts on live EC2 customer 393 / datacenter_v1, ARR ranging $900K-$12.5M,
a 14x spread). Also affected: bridge.forward_roi_pct, roadmap.roi_pct, and
scaling_scenarios.{1,4,6}_pct.year_1_roi.

Root cause (outcome_roi_engine.calculate_forward_roi): dollar impact scales
*linearly* with ARR (`arr_scale = account_arr / 10_000_000`, applied
uniformly to every metric). The "realistic investment" ceiling
(`account_arr * 0.015`) is *also* exactly linear in ARR, and — verified here —
the benchmark investment estimate exceeds that ceiling for every realistic
ARR/target-improvement combination, so the ceiling isn't an occasional
safety rail, it *is* the investment figure 100% of the time in practice.
Whenever two linear-in-ARR quantities are divided, roi_pct = (impact -
investment) / investment is mathematically guaranteed to be identical for
every ARR, no matter how different the accounts are. This is an exact
algebraic identity, not a rounding coincidence — reproduced byte-for-byte
against tracer's captured 2577.6% at target_improvement_pct=10.0,
projection_months=12 (the get_outcome_roi_story MCP tool's defaults).

Same root cause, second call site (power_of_1_model._scale_scenarios): scaled
both `investment` and every impact dollar field by the identical `arr_scale`,
so "recalculating" year_1_roi from the scaled values always reproduces the
unscaled baseline ratio — also an algebraic no-op.

Fix: make investment scale *sub-linearly* with ARR (sqrt), consistent with
the sub-linear `inv_arr_scale` the benchmark model already uses elsewhere in
the same function ("smaller accounts get proportionally less, not the same
flat cost"), instead of a purely linear-in-ARR ceiling/scale that exactly
cancels the linear-in-ARR impact term.

Direct-import, no DB/Flask app needed — same convention as
test_outcome_roi_pillar_metric_map.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from outcome_roi_engine import calculate_forward_roi, POWER_OF_1_METRICS  # noqa: E402
from power_of_1_model import _scale_scenarios  # noqa: E402

ARR_VALUES = [900_000, 2_300_000, 4_100_000, 8_200_000, 12_500_000]  # real customer-393 spread


def _current_values():
    return {mid: m.baseline for mid, m in POWER_OF_1_METRICS.items()}


def test_forward_roi_pct_varies_with_account_arr():
    """The exact tracer scenario: get_outcome_roi_story's defaults
    (target_improvement_pct=10.0, projection_months=12) must not produce the
    same roi_pct for a $900K account and a $12.5M account."""
    roi_values = []
    for arr in ARR_VALUES:
        result = calculate_forward_roi(
            current_values=_current_values(),
            target_improvement_pct=10.0,
            account_arr=arr,
            projection_months=12,
        )
        roi_values.append(result.summary.roi_pct)

    assert len(set(roi_values)) > 1, (
        f"forward roi_pct is constant ({roi_values[0]}%) across ARR range "
        f"{ARR_VALUES[0]}-{ARR_VALUES[-1]} — the exact tracer-found bug"
    )
    # Bigger ARR should mean a meaningfully different (in this model, higher)
    # ROI% since investment now scales sub-linearly while impact scales linearly.
    assert roi_values == sorted(roi_values), (
        "forward roi_pct should move monotonically with ARR once investment "
        "and impact no longer scale identically"
    )


def test_forward_investment_no_longer_pure_linear_in_arr():
    """The investment figure itself must not be exactly proportional to ARR
    (that exact proportionality is what cancelled against the linear-in-ARR
    impact and produced the constant roi_pct)."""
    investments = []
    for arr in ARR_VALUES:
        result = calculate_forward_roi(
            current_values=_current_values(),
            target_improvement_pct=10.0,
            account_arr=arr,
            projection_months=12,
        )
        investments.append(result.summary.total_investment)

    ratios = [inv / arr for inv, arr in zip(investments, ARR_VALUES)]
    assert len(set(round(r, 8) for r in ratios)) > 1, (
        "investment/ARR ratio is identical across every account — investment "
        "is still exactly linear in ARR, which will always cancel against "
        "the linear-in-ARR impact term regardless of any other fix"
    )


def test_scaling_scenarios_year_1_roi_varies_with_arr():
    """scaling_scenarios.{1,4,6}_pct.year_1_roi — same algebraic bug, second
    call site (power_of_1_model._scale_scenarios)."""
    for key in ("1_pct", "4_pct", "6_pct"):
        values = []
        for arr in ARR_VALUES:
            arr_scale = arr / 10_000_000
            scaled = _scale_scenarios(arr_scale)
            values.append(scaled[key]["year_1_roi"])
        assert len(set(values)) > 1, (
            f"scaling_scenarios.{key}.year_1_roi is constant ({values[0]}) "
            f"across ARR range {ARR_VALUES[0]}-{ARR_VALUES[-1]}"
        )
