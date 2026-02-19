#!/usr/bin/env python3
"""
Power of 1 ROI Tests
=====================
Validates the complete "Power of 1" economic model that underpins every
playbook decision and every CSM investment justification.

Tests cover:
  1. Individual metric dollar impacts at 1%, 4%, 6% improvement
  2. Portfolio-level ROI across all 6 metrics
  3. Non-linear scaling thesis (same $247K investment → 5.5x at 4%)
  4. Metric cascade / compounding flywheel
  5. Playbook → metric linkage (every playbook improves at least one metric)
  6. Feedback loop integration — playbook outcomes → Power of 1 dollar proof
  7. Investment summary arithmetic
  8. Time economics (3-year savings)
  9. Quarterly checkpoints
"""

import sys
import os
import json
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

from power_of_1_model import (
    POWER_OF_1_METRICS,
    SCALING_SCENARIOS,
    INVESTMENT_SUMMARY,
    METRIC_CASCADES,
    COMPOUNDING_MULTIPLIER,
    TIME_ECONOMICS,
    QUARTERLY_CHECKPOINTS,
    MetricCategory,
    ImpactType,
    calculate_power_of_1_impact,
    calculate_portfolio_impact,
    get_metric_for_kpi_code,
    get_metrics_for_playbook,
)


# ============================================================
# 1. INDIVIDUAL METRIC DOLLAR IMPACTS
# ============================================================

class TestIndividualMetricImpacts:
    """Each metric must produce correct dollar values at key improvement levels."""

    @pytest.mark.parametrize("metric_id,expected_impact_1pct", [
        ("TTFV", 61250),
        ("NRR", 105000),
        ("GRR", 100000),
        ("ticket_resolution_time", 38000),
        ("product_adoption", 25000),
        ("expansion_rate", 20000),
    ])
    def test_1_pct_direct_impact(self, metric_id, expected_impact_1pct):
        """1% improvement should yield the deck-defined annual impact."""
        result = calculate_power_of_1_impact(metric_id, 1.0)
        assert result["direct_impact"] == expected_impact_1pct, (
            f"{metric_id}: expected ${expected_impact_1pct:,}, got ${result['direct_impact']:,}"
        )

    @pytest.mark.parametrize("metric_id", list(POWER_OF_1_METRICS.keys()))
    def test_4_pct_is_4x_direct(self, metric_id):
        """4% improvement → exactly 4x the 1% direct impact (linear scaling)."""
        r1 = calculate_power_of_1_impact(metric_id, 1.0)
        r4 = calculate_power_of_1_impact(metric_id, 4.0)
        assert abs(r4["direct_impact"] - r1["direct_impact"] * 4) < 1.0

    @pytest.mark.parametrize("metric_id", list(POWER_OF_1_METRICS.keys()))
    def test_investment_is_fixed(self, metric_id):
        """Investment is the same regardless of improvement % (non-linear scaling thesis)."""
        r1 = calculate_power_of_1_impact(metric_id, 1.0)
        r6 = calculate_power_of_1_impact(metric_id, 6.0)
        assert r1["investment"] == r6["investment"]


# ============================================================
# 2. ROI AT EACH TIER
# ============================================================

class TestROIByTier:
    """Validate ROI numbers match the CS GrowthPulse deck."""

    @pytest.mark.parametrize("metric_id,expected_roi", [
        ("TTFV", -0.19),
        ("NRR", 2.10),
        ("GRR", 1.67),
        ("ticket_resolution_time", 1.46),
        ("product_adoption", 1.19),
        ("expansion_rate", 1.38),
    ])
    def test_roi_at_1_pct(self, metric_id, expected_roi):
        """ROI at 1% matches the deck values."""
        metric = POWER_OF_1_METRICS[metric_id]
        assert metric.roi_at_1pct == expected_roi

    def test_ttfv_is_foundation_investment(self):
        """TTFV has negative ROI at 1% — it's the foundation investment."""
        ttfv = POWER_OF_1_METRICS["TTFV"]
        assert ttfv.roi_at_1pct < 0
        assert ttfv.category == MetricCategory.FOUNDATION_INVESTMENT

    def test_nrr_is_highest_roi(self):
        """NRR should have the highest ROI among all 6 metrics."""
        rois = {mid: m.roi_at_1pct for mid, m in POWER_OF_1_METRICS.items()}
        assert max(rois, key=rois.get) == "NRR"
        assert rois["NRR"] == 2.10


# ============================================================
# 3. NON-LINEAR SCALING THESIS
# ============================================================

class TestNonLinearScaling:
    """Same $247K investment produces exponentially higher returns."""

    def test_investment_identical_across_scenarios(self):
        """All 3 scenarios use the same $247K investment."""
        for scenario in SCALING_SCENARIOS.values():
            assert scenario["investment"] == 247000

    def test_1_pct_roi(self):
        assert SCALING_SCENARIOS["1_pct"]["year_1_roi"] == pytest.approx(0.63, abs=0.01)

    def test_4_pct_roi(self):
        assert SCALING_SCENARIOS["4_pct"]["year_1_roi"] == pytest.approx(5.50, abs=0.01)

    def test_6_pct_roi(self):
        assert SCALING_SCENARIOS["6_pct"]["year_1_roi"] == pytest.approx(8.76, abs=0.01)

    def test_scaling_is_nonlinear(self):
        """4x improvement → >4x ROI (proves non-linearity)."""
        roi_1 = SCALING_SCENARIOS["1_pct"]["year_1_roi"]
        roi_4 = SCALING_SCENARIOS["4_pct"]["year_1_roi"]
        # 4% improvement should yield >4x the ROI of 1%
        assert roi_4 / roi_1 > 4, "Scaling should be super-linear"

    def test_portfolio_impact_at_4_pct(self):
        """Portfolio calculation at 4% should match deck's $1.397M direct."""
        result = calculate_portfolio_impact(4.0)
        # Direct impact: sum of 6 metrics * 4
        assert result["totals"]["direct_impact"] == pytest.approx(
            SCALING_SCENARIOS["4_pct"]["direct_impact"], rel=0.01
        )


# ============================================================
# 4. METRIC CASCADE / COMPOUNDING FLYWHEEL
# ============================================================

class TestMetricCascades:
    """Improving one metric cascades to others via the flywheel."""

    def test_ttfv_amplifies_adoption_and_expansion(self):
        """TTFV → product_adoption (0.35x) + expansion_rate (0.40x)."""
        cascade = METRIC_CASCADES["TTFV"]["amplifies"]
        targets = {a["target_metric"] for a in cascade}
        assert "product_adoption" in targets
        assert "expansion_rate" in targets

    def test_grr_amplifies_nrr(self):
        """GRR → NRR (0.25x) — retained base is expandable base."""
        cascade = METRIC_CASCADES["GRR"]["amplifies"]
        targets = {a["target_metric"] for a in cascade}
        assert "NRR" in targets

    def test_nrr_is_terminal(self):
        """NRR amplifies nothing — it's the terminal output metric."""
        assert METRIC_CASCADES["NRR"]["amplifies"] == []

    def test_compounding_capped_at_15_pct(self):
        """Conservative compounding cap is 15%."""
        assert COMPOUNDING_MULTIPLIER == 0.15

    def test_cascade_impact_included_in_calculation(self):
        """TTFV at 4% should include compounding > 0."""
        result = calculate_power_of_1_impact("TTFV", 4.0)
        assert result["compounding_impact"] > 0

    def test_all_cascades_have_lag_weeks(self):
        """Every cascade relationship should have a lag_weeks field."""
        for metric_id, data in METRIC_CASCADES.items():
            for amp in data.get("amplifies", []):
                assert "lag_weeks" in amp, f"{metric_id} → {amp['target_metric']} missing lag_weeks"
                assert amp["lag_weeks"] > 0


# ============================================================
# 5. PLAYBOOK → METRIC LINKAGE
# ============================================================

class TestPlaybookMetricLinkage:
    """Every playbook should map to at least one Power of 1 metric."""

    ALL_PLAYBOOK_IDS = [
        "activation-blitz", "voc-sprint", "sla-stabilizer",
        "renewal-safeguard", "expansion-accelerator",
    ]

    @pytest.mark.parametrize("playbook_id", ALL_PLAYBOOK_IDS)
    def test_playbook_has_linked_metrics(self, playbook_id):
        """Each playbook improves at least one Power of 1 metric."""
        metrics = get_metrics_for_playbook(playbook_id)
        assert len(metrics) >= 1, f"{playbook_id} has no linked metrics"

    def test_renewal_safeguard_improves_grr(self):
        metrics = get_metrics_for_playbook("renewal-safeguard")
        assert "GRR" in metrics

    def test_expansion_accelerator_improves_nrr_and_expansion(self):
        metrics = get_metrics_for_playbook("expansion-accelerator")
        assert "NRR" in metrics or "expansion_rate" in metrics

    def test_activation_blitz_improves_ttfv_and_adoption(self):
        metrics = get_metrics_for_playbook("activation-blitz")
        assert "TTFV" in metrics
        assert "product_adoption" in metrics

    def test_sla_stabilizer_improves_ticket_resolution(self):
        metrics = get_metrics_for_playbook("sla-stabilizer")
        assert "ticket_resolution_time" in metrics


# ============================================================
# 6. KPI CODE → METRIC MAPPING
# ============================================================

class TestKPICodeMapping:
    """DC2_S KPI codes should map to Power of 1 metrics."""

    @pytest.mark.parametrize("kpi_code,expected_metric", [
        ("P1-KPI1", "TTFV"),
        ("EX-KPI1", "NRR"),
        ("CH-KPI1", "GRR"),
        ("OS-KPI1", "ticket_resolution_time"),
        ("AI-KPI2", "product_adoption"),
        ("EX-KPI3", "expansion_rate"),
    ])
    def test_kpi_to_metric_mapping(self, kpi_code, expected_metric):
        result = get_metric_for_kpi_code(kpi_code)
        assert result == expected_metric, f"{kpi_code} should map to {expected_metric}, got {result}"

    def test_unknown_kpi_returns_none(self):
        assert get_metric_for_kpi_code("UNKNOWN-999") is None


# ============================================================
# 7. INVESTMENT SUMMARY ARITHMETIC
# ============================================================

class TestInvestmentSummary:
    """The investment numbers should be internally consistent."""

    def test_total_investment_is_sum(self):
        """Total = CS initiatives + platform cost."""
        assert (
            INVESTMENT_SUMMARY["cs_initiatives"] + INVESTMENT_SUMMARY["platform_cost"]
            == INVESTMENT_SUMMARY["total_investment"]
        )

    def test_80_20_split(self):
        """80% human effort, 20% platform — per the deck."""
        cs_pct = INVESTMENT_SUMMARY["cs_initiatives"] / INVESTMENT_SUMMARY["total_investment"]
        platform_pct = INVESTMENT_SUMMARY["platform_cost"] / INVESTMENT_SUMMARY["total_investment"]
        assert cs_pct == pytest.approx(0.80, abs=0.01)
        assert platform_pct == pytest.approx(0.20, abs=0.01)

    def test_revenue_cost_split(self):
        """Revenue increase + cost savings = total direct impact."""
        assert (
            INVESTMENT_SUMMARY["revenue_increase_total"]
            + INVESTMENT_SUMMARY["cost_savings_total"]
            == INVESTMENT_SUMMARY["direct_impact_total"]
        )

    def test_direct_plus_compounding_equals_total(self):
        """Direct + compounding = total year 1 impact."""
        assert (
            INVESTMENT_SUMMARY["direct_impact_total"]
            + INVESTMENT_SUMMARY["compounding_effect"]
            == INVESTMENT_SUMMARY["total_year_1_impact"]
        )

    def test_total_matches_247k(self):
        assert INVESTMENT_SUMMARY["total_investment"] == 247000

    def test_sum_of_6_metrics_equals_direct_total(self):
        """Sum of all 6 metrics' annual_impact_per_pct should equal direct_impact_total."""
        total = sum(m.annual_impact_per_pct for m in POWER_OF_1_METRICS.values())
        assert total == INVESTMENT_SUMMARY["direct_impact_total"]


# ============================================================
# 8. TIME ECONOMICS (3-YEAR MODEL)
# ============================================================

class TestTimeEconomics:
    """Validate the 3-year time savings model from the deck."""

    def test_year_1_is_investment_year(self):
        """Year 1 has highest hours invested."""
        y1 = TIME_ECONOMICS["year_1"]
        y2 = TIME_ECONOMICS["year_2"]
        assert y1["hours_invested"] > y2["hours_invested"]

    def test_year_2_maintenance_only(self):
        """Year 2 drops to maintenance — <1000 hours."""
        y2 = TIME_ECONOMICS["year_2"]
        assert y2["hours_invested"] <= 1000

    def test_3_year_roi_multiplier(self):
        """3-year time ROI is 3.1x."""
        totals = TIME_ECONOMICS["three_year_totals"]
        assert totals["time_roi_multiplier"] == pytest.approx(3.1, abs=0.1)

    def test_3_year_fte_freed(self):
        """7.4 FTEs freed over 3 years."""
        totals = TIME_ECONOMICS["three_year_totals"]
        assert totals["fte_equivalent_freed"] == pytest.approx(7.4, abs=0.5)

    def test_net_savings_grow_year_over_year(self):
        """Net savings should increase each year."""
        y2 = TIME_ECONOMICS["year_2"]["net_savings"]
        y3 = TIME_ECONOMICS["year_3"]["net_savings"]
        assert y3 > y2

    def test_3_year_totals_sum_correctly(self):
        """Total hours invested = sum of 3 years."""
        total = (
            TIME_ECONOMICS["year_1"]["hours_invested"]
            + TIME_ECONOMICS["year_2"]["hours_invested"]
            + TIME_ECONOMICS["year_3"]["hours_invested"]
        )
        assert total == TIME_ECONOMICS["three_year_totals"]["hours_invested"]


# ============================================================
# 9. PORTFOLIO-LEVEL IMPACT CALCULATION
# ============================================================

class TestPortfolioImpact:

    def test_portfolio_at_1_pct(self):
        """Portfolio at 1% should produce ~$349K direct."""
        result = calculate_portfolio_impact(1.0)
        assert result["totals"]["direct_impact"] == pytest.approx(349250, rel=0.01)

    def test_portfolio_includes_all_6_metrics(self):
        result = calculate_portfolio_impact(1.0)
        assert len(result["metrics"]) == 6
        for mid in POWER_OF_1_METRICS:
            assert mid in result["metrics"]

    def test_portfolio_includes_scaling_scenarios(self):
        result = calculate_portfolio_impact(1.0)
        assert "1_pct" in result["scaling_scenarios"]
        assert "4_pct" in result["scaling_scenarios"]
        assert "6_pct" in result["scaling_scenarios"]

    def test_portfolio_arr_scaling(self):
        """$5M ARR should produce half the impact of $10M base."""
        r_base = calculate_portfolio_impact(1.0, total_arr=10_000_000)
        r_half = calculate_portfolio_impact(1.0, total_arr=5_000_000)
        assert r_half["totals"]["direct_impact"] == pytest.approx(
            r_base["totals"]["direct_impact"] / 2, rel=0.01
        )


# ============================================================
# 10. METRIC COMPLETENESS & STRUCTURAL INTEGRITY
# ============================================================

class TestMetricCompleteness:
    """Every metric must have all required economic fields."""

    @pytest.mark.parametrize("metric_id", list(POWER_OF_1_METRICS.keys()))
    def test_metric_has_all_fields(self, metric_id):
        m = POWER_OF_1_METRICS[metric_id]
        assert m.display_name
        assert m.baseline > 0
        assert m.unit in ("days", "hours", "percent")
        assert m.direction in ("higher_is_better", "lower_is_better")
        assert m.annual_impact_per_pct > 0
        assert m.total_investment > 0
        assert m.total_hours > 0
        assert len(m.linked_playbooks) >= 1
        assert len(m.linked_kpi_codes) >= 1
        assert len(m.work_packages) >= 1
        assert len(m.quarters) >= 1

    @pytest.mark.parametrize("metric_id", list(POWER_OF_1_METRICS.keys()))
    def test_metric_has_impact_breakdown(self, metric_id):
        m = POWER_OF_1_METRICS[metric_id]
        total_breakdown = sum(m.impact_breakdown.values())
        assert total_breakdown == m.annual_impact_per_pct, (
            f"{metric_id}: breakdown sum ${total_breakdown:,} != impact ${m.annual_impact_per_pct:,}"
        )

    @pytest.mark.parametrize("metric_id", list(POWER_OF_1_METRICS.keys()))
    def test_work_package_hours_sum(self, metric_id):
        """Work package hours should sum to total_hours."""
        m = POWER_OF_1_METRICS[metric_id]
        wp_total = sum(wp.hours for wp in m.work_packages)
        assert wp_total == m.total_hours, (
            f"{metric_id}: work packages sum to {wp_total}h, expected {m.total_hours}h"
        )


# ============================================================
# 11. POWER OF 1 → FEEDBACK LOOP INTEGRATION
# ============================================================

class TestPowerOf1FeedbackIntegration:
    """Verify feedback loop correctly references Power of 1 metrics."""

    def test_execution_feedback_carries_po1_metric(self):
        """ExecutionFeedback dataclass supports power_of_1_metric field."""
        from qdrant_feedback_loop import ExecutionFeedback
        fb = ExecutionFeedback(
            execution_id="test-po1",
            customer_id=1,
            account_id="100",
            playbook_type="voc-sprint",
            outcome="resolved",
            power_of_1_metric="NRR",
            dollar_impact_realized=105000.0,
        )
        assert fb.power_of_1_metric == "NRR"
        assert fb.dollar_impact_realized == 105000.0

    def test_all_po1_metrics_are_valid_feedback_values(self):
        """Every Power of 1 metric ID should be usable in feedback."""
        from qdrant_feedback_loop import ExecutionFeedback
        for metric_id in POWER_OF_1_METRICS:
            fb = ExecutionFeedback(
                execution_id=f"test-{metric_id}",
                customer_id=1,
                account_id="100",
                playbook_type="test",
                outcome="resolved",
                power_of_1_metric=metric_id,
                dollar_impact_realized=POWER_OF_1_METRICS[metric_id].annual_impact_per_pct,
            )
            assert fb.power_of_1_metric == metric_id

    def test_playbook_to_po1_dollar_proof(self):
        """
        Prove the ROI chain: playbook execution → metric improvement → dollar value.

        Scenario: renewal-safeguard playbook improves GRR by 1%
        Expected: $100,000 annual impact (per the deck)
        """
        playbook_id = "renewal-safeguard"
        metrics_improved = get_metrics_for_playbook(playbook_id)
        assert "GRR" in metrics_improved

        impact = calculate_power_of_1_impact("GRR", 1.0)
        assert impact["direct_impact"] == 100000
        assert impact["roi"] > 0  # Positive ROI

    def test_activation_blitz_roi_chain(self):
        """
        activation-blitz → TTFV + product_adoption → combined dollar impact.
        """
        metrics = get_metrics_for_playbook("activation-blitz")
        total_impact = sum(
            calculate_power_of_1_impact(m, 1.0)["direct_impact"]
            for m in metrics
        )
        # TTFV ($61,250) + product_adoption ($25,000) = $86,250
        assert total_impact == 86250

    def test_voc_sprint_expansion_roi(self):
        """
        voc-sprint → NRR → $105K at 1% improvement.
        NRR has the highest ROI among all 6 metrics.
        The deck's roi_at_1pct (2.10) = impact/investment.
        The calculate function's roi = (impact - investment)/investment = 1.1.
        """
        metrics = get_metrics_for_playbook("voc-sprint")
        assert "NRR" in metrics
        impact = calculate_power_of_1_impact("NRR", 1.0)
        assert impact["direct_impact"] == 105000
        assert impact["roi"] > 1.0  # Positive, strong ROI

    def test_full_portfolio_roi_at_4_pct(self):
        """
        The headline number: 4% improvement across all metrics
        with $247K investment → 5.5x ROI.
        """
        result = calculate_portfolio_impact(4.0)
        # ROI should be in the 5.5x range
        assert result["totals"]["roi"] > 5.0


# ============================================================
# 12. QUARTERLY CHECKPOINT VALIDATION
# ============================================================

class TestQuarterlyCheckpoints:

    def test_all_4_quarters_present(self):
        assert set(QUARTERLY_CHECKPOINTS.keys()) == {"Q1", "Q2", "Q3", "Q4"}

    def test_q1_is_foundation(self):
        assert "Foundation" in QUARTERLY_CHECKPOINTS["Q1"]["label"]

    def test_q4_validates_roi(self):
        q4 = QUARTERLY_CHECKPOINTS["Q4"]
        assert "ROI" in q4["label"] or "roi" in str(q4.get("targets", {}).get("overall_roi", ""))


# ============================================================
# 13. WORK PACKAGE ROLE ALLOCATIONS
# ============================================================

class TestWorkPackageRoles:
    """Validate that work packages have sensible role allocations."""

    @pytest.mark.parametrize("metric_id", list(POWER_OF_1_METRICS.keys()))
    def test_role_hours_match_wp_hours(self, metric_id):
        """Sum of role hours should equal work package hours."""
        m = POWER_OF_1_METRICS[metric_id]
        for wp in m.work_packages:
            role_total = wp.roles.total_hours
            assert role_total == wp.hours, (
                f"{metric_id}/{wp.name}: role hours {role_total} != wp hours {wp.hours}"
            )

    @pytest.mark.parametrize("metric_id", list(POWER_OF_1_METRICS.keys()))
    def test_each_wp_has_deliverables(self, metric_id):
        m = POWER_OF_1_METRICS[metric_id]
        for wp in m.work_packages:
            assert len(wp.deliverables) >= 1, f"{metric_id}/{wp.name} has no deliverables"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
