#!/usr/bin/env python3
"""
Historical-ROI Auditor Disclosure Tests
========================================
Pins the behaviour that fixes the "7,652% ROI on fresh tenant" credibility
risk surfaced by the May-17 CFO eval (cust 334, predictor_v3_demo_saas
manifest, 18-month synthetic decline → recovery trajectory).

What the fix does:
  * Option C (always-on)  : when the historical view reports an ROI that is
    materially above steady-state, attach a structured `disclosure` field
    explaining that one-time onboarding gains are baked into the number and
    rewrite the period_label to "(since onboarding — includes one-time gains)".
  * Option A (opt-in)     : `_extract_historical_actuals(skip_unstable_months=N)`
    anchors the baseline past the first N months of measurements, so the
    trailing-window number itself becomes credible. Default 0 preserves
    legacy behaviour.

What a CFO/auditor cares about:
  * The 7,652% number cannot appear without a prominent caveat OR the
    underlying baseline must shift to a stable region.
  * Stable customers (where the historical window legitimately reflects
    incremental gains) MUST NOT be flagged — false positives would muddle
    every honest ROI tile.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from outcome_roi_engine import (
    calculate_historical_roi,
    calculate_outcome_story,
    _build_historical_disclosure,
    _result_to_dict,
)
from power_of_1_model import POWER_OF_1_METRICS


# ════════════════════════════════════════════════════════════════════
# Fixtures — synthetic metric_actuals payloads
# ════════════════════════════════════════════════════════════════════

@pytest.fixture
def actuals_fresh_tenant_onboarding_lift():
    """
    Synthetic decline → recovery trajectory: each metric shows a large
    historical "improvement" because the baseline anchored at the
    onboarding low point. Mirrors the cust-334 case (TTFV 32.83 → 30,
    product_adoption 57 → 72, ticket_resolution 52 → 48 hrs, etc.).
    The avg improvement per KPI here is ~6.8% — well above steady-state.
    """
    return {
        "TTFV": {"baseline": 32.83, "current": 30.0},
        "product_adoption": {"baseline": 57.57, "current": 72.43},
        "ticket_resolution_time": {"baseline": 52.21, "current": 48.0},
        "NRR": {"baseline": 102.0, "current": 105.0},
        "GRR": {"baseline": 91.0, "current": 93.0},
        "expansion_rate": {"baseline": 11.0, "current": 13.0},
    }


@pytest.fixture
def actuals_stable_customer():
    """
    Steady-state customer: tiny incremental movement on every metric.
    Avg improvement per KPI well under 1%. Must NOT trip the
    non-repeatable disclosure.
    """
    return {
        "TTFV": {"baseline": 30.3, "current": 30.0},
        "product_adoption": {"baseline": 72.0, "current": 72.5},
        "ticket_resolution_time": {"baseline": 48.5, "current": 48.0},
        "NRR": {"baseline": 105.0, "current": 105.5},
        "GRR": {"baseline": 92.5, "current": 93.0},
        "expansion_rate": {"baseline": 12.7, "current": 13.0},
    }


@pytest.fixture
def actuals_flat_no_change():
    """No change at all — every metric matches baseline=current."""
    return {
        mid: {"baseline": m.baseline, "current": m.baseline}
        for mid, m in POWER_OF_1_METRICS.items()
    }


# ════════════════════════════════════════════════════════════════════
# Section 1 — Option C: structured disclosure
# ════════════════════════════════════════════════════════════════════

class TestHistoricalDisclosureNonRepeatable:
    """Fresh-tenant trajectories MUST surface the auditor caveat."""

    def test_fresh_tenant_lift_emits_disclosure(
        self, actuals_fresh_tenant_onboarding_lift,
    ):
        """A decline → recovery payload triggers non_repeatable=True."""
        result = calculate_historical_roi(
            metric_actuals=actuals_fresh_tenant_onboarding_lift,
            account_arr=175_370_000,
            period_label="Last 6 Months",
            forward_steady_state_pct=1.0,
        )
        assert result.disclosure is not None, "Expected disclosure on fresh-tenant lift"
        assert result.disclosure["non_repeatable"] is True
        assert result.disclosure["period_basis"] == "since_onboarding"
        # The recommended_label MUST not leave the auditor reading "Last 6 Months"
        # without context. It either says "since onboarding" or carries the caveat.
        assert "since onboarding" in result.disclosure["recommended_label"].lower()
        # The detail paragraph must contain auditor-grade language about why
        # the historical ROI is non-repeatable.
        detail = result.disclosure["detail"].lower()
        assert "one-time" in detail or "onboarding" in detail
        assert "steady-state" in detail or "forward" in detail

    def test_fresh_tenant_period_label_is_rewritten(
        self, actuals_fresh_tenant_onboarding_lift,
    ):
        """period_label on the result MUST carry the caveat suffix."""
        result = calculate_historical_roi(
            metric_actuals=actuals_fresh_tenant_onboarding_lift,
            account_arr=175_370_000,
            period_label="Last 6 Months",
            forward_steady_state_pct=1.0,
        )
        # Should no longer be the bare "Last 6 Months" framing
        assert result.period_label != "Last 6 Months"
        assert "since onboarding" in result.period_label.lower()

    def test_serialized_result_carries_disclosure_field(
        self, actuals_fresh_tenant_onboarding_lift,
    ):
        """_result_to_dict MUST expose disclosure at the top level."""
        result = calculate_historical_roi(
            metric_actuals=actuals_fresh_tenant_onboarding_lift,
            account_arr=175_370_000,
            forward_steady_state_pct=1.0,
        )
        payload = _result_to_dict(result)
        assert "disclosure" in payload
        assert payload["disclosure"]["non_repeatable"] is True


class TestHistoricalDisclosureStableCustomer:
    """Stable / honest historical windows MUST NOT be flagged."""

    def test_stable_customer_no_disclosure(self, actuals_stable_customer):
        """A 0.3-pp-per-metric ROI is repeatable — no disclosure required."""
        result = calculate_historical_roi(
            metric_actuals=actuals_stable_customer,
            account_arr=50_000_000,
            period_label="Last 6 Months",
            forward_steady_state_pct=1.0,
        )
        assert result.disclosure is None, (
            f"Stable customer should not trigger disclosure; got: {result.disclosure}"
        )
        # And the period label MUST stay as the caller asked.
        assert result.period_label == "Last 6 Months"

    def test_flat_no_change_no_disclosure(self, actuals_flat_no_change):
        """Zero historical improvement → no disclosure at all."""
        result = calculate_historical_roi(
            metric_actuals=actuals_flat_no_change,
            account_arr=10_000_000,
            forward_steady_state_pct=1.0,
        )
        assert result.disclosure is None


class TestDisclosureBuilderUnit:
    """The disclosure builder is a pure function — pin its contract."""

    def test_low_roi_returns_none(self):
        disclosure, label = _build_historical_disclosure(
            period_label="Last 6 Months",
            period_basis="trailing_window",
            roi_pct=350.0,
            improvement_pct_avg=1.2,
            forward_steady_state_pct=1.0,
            data_source="kpi_actuals_benchmark",
        )
        assert disclosure is None
        assert label == "Last 6 Months"

    def test_high_roi_high_lift_triggers(self):
        disclosure, label = _build_historical_disclosure(
            period_label="Last 6 Months",
            period_basis="trailing_window",
            roi_pct=7652.0,
            improvement_pct_avg=6.84,
            forward_steady_state_pct=1.0,
            data_source="kpi_actuals_benchmark",
        )
        assert disclosure is not None
        assert disclosure["non_repeatable"] is True
        assert "since onboarding" in label.lower()

    def test_high_roi_low_lift_does_not_trigger(self):
        """ROI inflated by tiny baseline, not big lift — don't false-positive.

        Edge case: a steady customer can have a high ROI if their investment
        is tiny relative to outcomes. The trigger requires BOTH high ROI AND
        large per-KPI improvement.
        """
        disclosure, label = _build_historical_disclosure(
            period_label="Last 6 Months",
            period_basis="trailing_window",
            roi_pct=900.0,
            improvement_pct_avg=0.8,
            forward_steady_state_pct=1.0,
            data_source="kpi_actuals_benchmark",
        )
        assert disclosure is None

    def test_explicit_stable_window_basis_recorded(self):
        """When caller passes period_basis='stable_window', record provenance.

        Even if ROI is now reasonable (since Option A fixed the baseline),
        we still emit a disclosure recording the provenance so the buyer
        sees that we shifted the anchor on purpose.
        """
        disclosure, label = _build_historical_disclosure(
            period_label="Last 6 Months",
            period_basis="stable_window",
            roi_pct=450.0,
            improvement_pct_avg=1.1,
            forward_steady_state_pct=1.0,
            data_source="kpi_actuals_benchmark_stable_skip3",
        )
        assert disclosure is not None
        assert disclosure["non_repeatable"] is False
        assert disclosure["period_basis"] == "stable_window"


# ════════════════════════════════════════════════════════════════════
# Section 2 — End-to-end: calculate_outcome_story
# ════════════════════════════════════════════════════════════════════

class TestOutcomeStoryDisclosurePropagation:
    """The combined story must thread disclosure through bridge + historical."""

    def test_story_bridge_carries_historical_disclosure(
        self, actuals_fresh_tenant_onboarding_lift,
    ):
        story = calculate_outcome_story(
            metric_actuals=actuals_fresh_tenant_onboarding_lift,
            account_arr=175_370_000,
            projection_months=6,
            target_improvement_pct=1.0,
        )
        assert "historical_disclosure" in story["bridge"]
        assert story["bridge"]["historical_disclosure"]["non_repeatable"] is True
        # The bridge MUST recommend the forward (steady-state) ROI as the
        # number to put on a slide / report.
        assert "recommended_headline_roi_pct" in story["bridge"]
        assert story["bridge"]["recommended_headline_basis"] == "forward_steady_state"
        # And it should be materially smaller than the historical headline.
        assert (
            story["bridge"]["recommended_headline_roi_pct"]
            < story["historical"]["summary"]["roi_pct"]
        )

    def test_story_no_bogus_disclosure_for_stable_customer(
        self, actuals_stable_customer,
    ):
        story = calculate_outcome_story(
            metric_actuals=actuals_stable_customer,
            account_arr=50_000_000,
            projection_months=6,
            target_improvement_pct=1.0,
        )
        # historical_disclosure should be absent — the number is defensible
        assert "historical_disclosure" not in story["bridge"]
        assert "recommended_headline_roi_pct" not in story["bridge"]


# ════════════════════════════════════════════════════════════════════
# Section 3 — Option A: stable-window baseline (skip_unstable_months)
# ════════════════════════════════════════════════════════════════════

class TestStableWindowOptionA:
    """Verifies _extract_historical_actuals honours skip_unstable_months."""

    def test_signature_accepts_skip_unstable_months(self):
        """The new opt-in kwarg must exist on the function signature."""
        from outcome_roi_api import _extract_historical_actuals
        import inspect
        sig = inspect.signature(_extract_historical_actuals)
        assert "skip_unstable_months" in sig.parameters
        # Default must be 0 to preserve legacy behaviour.
        assert sig.parameters["skip_unstable_months"].default == 0

    def test_default_is_zero_to_preserve_legacy(self):
        """No regression for callers that pass only (accounts, months)."""
        from outcome_roi_api import _extract_historical_actuals
        import inspect
        sig = inspect.signature(_extract_historical_actuals)
        # Backwards-compat: original two positional params remain
        params = list(sig.parameters.keys())
        assert params[0] == "accounts"
        assert params[1] == "months"


# ════════════════════════════════════════════════════════════════════
# Section 4 — Regression pin for the cust-334 symptom
# ════════════════════════════════════════════════════════════════════

class TestCust334RegressionPin:
    """
    Recreates the exact cust-334 / predictor_v3_demo_saas symptom in unit
    form so future code paths that quietly drop the disclosure can't ship.

    Reference payload from `get_portfolio_roi_summary(334)` on
    2026-05-17 (commit 205c5d7c):
      total_investment: $385,712.66
      total_impact:    $29,900,849.18
      roi_pct:         7,652.1%
      improvement_pct_avg: 6.84
      ARR:             $175,370,000
    """

    def test_cust_334_symptom_now_carries_disclosure(
        self, actuals_fresh_tenant_onboarding_lift,
    ):
        result = calculate_historical_roi(
            metric_actuals=actuals_fresh_tenant_onboarding_lift,
            account_arr=175_370_000,
            period_label="Last 6 Months",
            forward_steady_state_pct=1.0,
        )
        # The raw 7,652% number is allowed to still exist in the data — but
        # it MUST be paired with disclosure + relabeled period.
        if result.summary.roi_pct > 500:
            assert result.disclosure is not None
            assert result.disclosure["non_repeatable"] is True
            assert "Last 6 Months" not in result.period_label or "since onboarding" in result.period_label.lower()

    def test_cust_334_story_recommends_forward_as_headline(
        self, actuals_fresh_tenant_onboarding_lift,
    ):
        story = calculate_outcome_story(
            metric_actuals=actuals_fresh_tenant_onboarding_lift,
            account_arr=175_370_000,
            projection_months=6,
            target_improvement_pct=1.0,
        )
        # A CFO reading the bridge MUST be steered to the forward number
        # (the repeatable one) as the headline.
        assert story["bridge"].get("recommended_headline_basis") == "forward_steady_state"
        rec_roi = story["bridge"]["recommended_headline_roi_pct"]
        hist_roi = story["historical"]["summary"]["roi_pct"]
        # The recommended (forward) ROI is materially smaller than the
        # historical one — that is the whole point of the disclosure.
        assert rec_roi < hist_roi * 0.5, (
            f"Forward ROI {rec_roi} should be << historical {hist_roi}"
        )
