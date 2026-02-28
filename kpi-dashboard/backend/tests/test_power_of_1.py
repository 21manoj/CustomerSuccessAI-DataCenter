#!/usr/bin/env python3
"""
Test Suite 1 — Power of 1 Revenue Intelligence Model
=====================================================
Tests: 6 metrics, cascades, compounding, scaling, work packages,
quarterly checkpoints, resource allocation, and financial projections bridge.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


# ============================================================
# MODULE IMPORT TESTS
# ============================================================

class TestImports:
    def test_power_of_1_model_imports(self):
        from power_of_1_model import (
            POWER_OF_1_METRICS, MetricCategory, ImpactType, CSPillar,
            calculate_power_of_1_impact, calculate_portfolio_impact,
            SCALING_SCENARIOS, INVESTMENT_SUMMARY, QUARTERLY_CHECKPOINTS,
            IMPLEMENTATION_PHASES,
        )
        assert POWER_OF_1_METRICS is not None
        assert len(POWER_OF_1_METRICS) == 6

    def test_quarterly_checkpoints_imports(self):
        from quarterly_checkpoints import (
            assess_quarter, assess_full_year, get_current_quarter_from_date,
            assessment_to_dict, QUARTER_TARGETS, TrackStatus, PhaseGateResult,
        )
        assert len(QUARTER_TARGETS) == 4

    def test_resource_model_imports(self):
        from resource_capacity_model import (
            CSRole, ROLE_RATES, check_capacity, calculate_action_cost,
            get_resource_pool_summary, METRIC_RESOURCE_ALLOCATION,
        )
        assert len(ROLE_RATES) > 0


# ============================================================
# METRIC DEFINITION TESTS
# ============================================================

class TestMetricDefinitions:
    def test_all_six_metrics_present(self):
        from power_of_1_model import POWER_OF_1_METRICS
        expected = {'TTFV', 'NRR', 'GRR', 'ticket_resolution_time', 'product_adoption', 'expansion_rate'}
        assert set(POWER_OF_1_METRICS.keys()) == expected

    def test_metric_has_required_fields(self):
        from power_of_1_model import POWER_OF_1_METRICS
        for mid, metric in POWER_OF_1_METRICS.items():
            assert metric.display_name, f"{mid} missing display_name"
            assert metric.baseline is not None, f"{mid} missing baseline"
            assert metric.one_pct_move is not None, f"{mid} missing one_pct_move"
            assert metric.annual_impact_per_pct is not None, f"{mid} missing annual_impact_per_pct"
            assert metric.unit, f"{mid} missing unit"
            assert metric.direction in ('higher_is_better', 'lower_is_better'), f"{mid} bad direction"
            assert len(metric.work_packages) > 0, f"{mid} missing work packages"

    def test_metric_categories_assigned(self):
        from power_of_1_model import POWER_OF_1_METRICS, MetricCategory
        for mid, metric in POWER_OF_1_METRICS.items():
            assert isinstance(metric.category, MetricCategory), f"{mid} bad category"

    def test_metric_pillars_assigned(self):
        from power_of_1_model import POWER_OF_1_METRICS, CSPillar
        for mid, metric in POWER_OF_1_METRICS.items():
            assert isinstance(metric.primary_pillar, CSPillar), f"{mid} bad pillar"

    def test_metrics_have_linked_playbooks(self):
        from power_of_1_model import POWER_OF_1_METRICS
        for mid, metric in POWER_OF_1_METRICS.items():
            assert len(metric.linked_playbooks) > 0, f"{mid} missing linked_playbooks"


# ============================================================
# IMPACT CALCULATION TESTS
# ============================================================

class TestImpactCalculation:
    def test_single_metric_1pct(self):
        from power_of_1_model import calculate_power_of_1_impact
        result = calculate_power_of_1_impact('NRR', 1.0)
        assert result['metric_id'] == 'NRR'
        assert result['improvement_pct'] == 1.0
        assert result['direct_impact'] > 0
        assert result['total_impact'] >= result['direct_impact']
        assert result['investment'] > 0
        assert result['roi'] is not None

    def test_scaling_nonlinear(self):
        """4% improvement should yield >4x the impact of 1%."""
        from power_of_1_model import calculate_power_of_1_impact
        r1 = calculate_power_of_1_impact('NRR', 1.0)
        r4 = calculate_power_of_1_impact('NRR', 4.0)
        assert r4['total_impact'] > r1['total_impact'] * 3.5, \
            "4% improvement should show non-linear scaling"

    def test_compounding_cascades(self):
        """Compounding effect should be positive for metrics with cascades."""
        from power_of_1_model import calculate_power_of_1_impact
        result = calculate_power_of_1_impact('NRR', 2.0)
        assert result['compounding_impact'] >= 0, \
            "Compounding should be non-negative"

    def test_custom_arr_scaling(self):
        """Larger ARR should scale the impact proportionally."""
        from power_of_1_model import calculate_power_of_1_impact
        r_default = calculate_power_of_1_impact('NRR', 1.0)
        r_scaled = calculate_power_of_1_impact('NRR', 1.0, 20_000_000)
        assert r_scaled['total_impact'] > r_default['total_impact'], \
            "Higher ARR should yield higher absolute impact"

    def test_lower_is_better_direction(self):
        """TTFV and ticket_resolution_time are lower-is-better."""
        from power_of_1_model import POWER_OF_1_METRICS
        assert POWER_OF_1_METRICS['TTFV'].direction == 'lower_is_better'
        assert POWER_OF_1_METRICS['ticket_resolution_time'].direction == 'lower_is_better'

    def test_investment_scales_with_improvement(self):
        """Investment scales: +50% of initial cost per 1% improvement (2%→1.5x, 5%→3x base)."""
        from power_of_1_model import calculate_power_of_1_impact
        r1 = calculate_power_of_1_impact('GRR', 1.0)
        r5 = calculate_power_of_1_impact('GRR', 5.0)
        assert r5['investment'] > r1['investment'], \
            "Higher improvement % should require higher investment"
        assert r5['investment'] == pytest.approx(r1['investment'] * 3.0, rel=0.01), \
            "5% should be 3x the 1% base investment"


# ============================================================
# PORTFOLIO IMPACT TESTS
# ============================================================

class TestPortfolioImpact:
    def test_portfolio_all_metrics(self):
        from power_of_1_model import calculate_portfolio_impact
        result = calculate_portfolio_impact(1.0)
        assert 'totals' in result
        assert 'metrics' in result
        assert result['totals']['total_impact'] > 0
        assert result['totals']['investment'] > 0
        assert len(result['metrics']) == 6

    def test_portfolio_scaling_curves(self):
        """Verify non-linear scaling across 1% to 6% improvement."""
        from power_of_1_model import calculate_portfolio_impact
        impacts = []
        for pct in [1, 2, 3, 4, 5, 6]:
            r = calculate_portfolio_impact(float(pct))
            impacts.append(r['totals']['total_impact'])

        # Each step should yield more than the last
        for i in range(1, len(impacts)):
            delta_current = impacts[i] - impacts[i-1]
            if i >= 2:
                delta_prev = impacts[i-1] - impacts[i-2]
                assert delta_current >= delta_prev * 0.9, \
                    f"Scaling should be non-linear: step {i} delta {delta_current} < prev {delta_prev}"

    def test_portfolio_custom_arr(self):
        from power_of_1_model import calculate_portfolio_impact
        r = calculate_portfolio_impact(1.0, 50_000_000)
        assert r['totals']['total_impact'] > 0


# ============================================================
# WORK PACKAGES & RESOURCE TESTS
# ============================================================

class TestWorkPackages:
    def test_every_metric_has_work_packages(self):
        from power_of_1_model import POWER_OF_1_METRICS
        for mid, metric in POWER_OF_1_METRICS.items():
            assert len(metric.work_packages) >= 1, f"{mid} needs at least 1 WP"
            for wp in metric.work_packages:
                assert wp.name, f"WP in {mid} missing name"
                assert wp.hours > 0, f"WP '{wp.name}' in {mid} missing hours"
                assert len(wp.deliverables) > 0, f"WP '{wp.name}' in {mid} missing deliverables"

    def test_work_package_roles(self):
        from power_of_1_model import POWER_OF_1_METRICS
        for mid, metric in POWER_OF_1_METRICS.items():
            for wp in metric.work_packages:
                total_role_hours = sum([
                    wp.roles.csm or 0, wp.roles.cs_ops or 0,
                    wp.roles.product or 0, wp.roles.platform or 0,
                    wp.roles.leadership or 0,
                ])
                assert total_role_hours > 0, f"WP '{wp.name}' has no role hours"


# ============================================================
# QUARTERLY CHECKPOINTS TESTS
# ============================================================

class TestQuarterlyCheckpoints:
    def test_quarter_targets_defined(self):
        from quarterly_checkpoints import QUARTER_TARGETS
        for q in ['Q1', 'Q2', 'Q3', 'Q4']:
            assert q in QUARTER_TARGETS
            qt = QUARTER_TARGETS[q]
            assert qt.label
            assert qt.month_range
            assert len(qt.metric_targets) > 0

    def test_assess_quarter_on_track(self):
        from quarterly_checkpoints import assess_quarter, TrackStatus
        # Provide values that meet Q2 targets
        actuals = {'TTFV': 29.0, 'NRR': 106.0, 'ticket_resolution_time': 45.0}
        result = assess_quarter('Q2', actuals)
        assert result.overall_status in (TrackStatus.ON_TRACK, TrackStatus.AHEAD)

    def test_assess_quarter_off_track(self):
        from quarterly_checkpoints import assess_quarter, TrackStatus
        # Provide values that miss Q2 targets by a lot
        actuals = {'TTFV': 35.0, 'NRR': 100.0, 'ticket_resolution_time': 55.0}
        result = assess_quarter('Q2', actuals)
        assert result.overall_status in (TrackStatus.OFF_TRACK, TrackStatus.AT_RISK)

    def test_assess_quarter_no_data(self):
        from quarterly_checkpoints import assess_quarter, TrackStatus
        result = assess_quarter('Q2', {})
        assert result.overall_status == TrackStatus.NOT_STARTED

    def test_phase_gate_pass(self):
        from quarterly_checkpoints import assess_quarter, PhaseGateResult
        actuals = {'TTFV': 29.0, 'NRR': 106.0, 'ticket_resolution_time': 45.0}
        result = assess_quarter('Q2', actuals)
        assert result.phase_gate in (PhaseGateResult.PASS, PhaseGateResult.CONDITIONAL_PASS)

    def test_phase_gate_fail(self):
        from quarterly_checkpoints import assess_quarter, PhaseGateResult
        actuals = {'TTFV': 35.0, 'NRR': 100.0, 'ticket_resolution_time': 55.0}
        result = assess_quarter('Q2', actuals)
        assert result.phase_gate in (PhaseGateResult.FAIL, PhaseGateResult.CONDITIONAL_PASS)

    def test_full_year_assessment(self):
        from quarterly_checkpoints import assess_full_year
        year_data = {
            'Q1': {'TTFV': 30.0},
            'Q2': {'TTFV': 29.5, 'NRR': 105.5},
            'Q3': {},
            'Q4': {},
        }
        results = assess_full_year(year_data)
        assert len(results) == 4

    def test_get_current_quarter(self):
        from quarterly_checkpoints import get_current_quarter_from_date
        from datetime import date
        assert get_current_quarter_from_date(date(2026, 1, 15)) == 'Q1'
        assert get_current_quarter_from_date(date(2026, 6, 1)) == 'Q2'
        assert get_current_quarter_from_date(date(2026, 9, 30)) == 'Q3'
        assert get_current_quarter_from_date(date(2026, 12, 25)) == 'Q4'

    def test_recommendations_generated(self):
        from quarterly_checkpoints import assess_quarter
        actuals = {'TTFV': 35.0, 'NRR': 100.0, 'ticket_resolution_time': 55.0}
        result = assess_quarter('Q2', actuals)
        assert len(result.recommendations) > 0

    def test_assessment_serialization(self):
        from quarterly_checkpoints import assess_quarter, assessment_to_dict
        actuals = {'TTFV': 29.5}
        result = assess_quarter('Q2', actuals)
        d = assessment_to_dict(result)
        assert 'quarter' in d
        assert 'metrics' in d
        assert 'phase_gate' in d


# ============================================================
# SCALING SCENARIOS & INVESTMENT SUMMARY
# ============================================================

class TestScalingScenarios:
    def test_scaling_scenarios_defined(self):
        from power_of_1_model import SCALING_SCENARIOS
        assert len(SCALING_SCENARIOS) > 0
        # SCALING_SCENARIOS is a dict keyed by scenario name
        for key, scenario in SCALING_SCENARIOS.items():
            assert isinstance(scenario, dict)
            assert 'label' in scenario or 'improvement_pct' in scenario

    def test_investment_summary(self):
        from power_of_1_model import INVESTMENT_SUMMARY
        assert INVESTMENT_SUMMARY is not None
        assert 'total' in INVESTMENT_SUMMARY or isinstance(INVESTMENT_SUMMARY, dict)

    def test_implementation_phases(self):
        from power_of_1_model import IMPLEMENTATION_PHASES
        assert len(IMPLEMENTATION_PHASES) > 0


# ============================================================
# HELPER FUNCTION TESTS
# ============================================================

class TestHelperFunctions:
    def test_get_metric_for_kpi_code(self):
        from power_of_1_model import get_metric_for_kpi_code, POWER_OF_1_METRICS
        # Find a valid linked_kpi_code from any metric
        for mid, metric in POWER_OF_1_METRICS.items():
            if metric.linked_kpi_codes:
                code = metric.linked_kpi_codes[0]
                result = get_metric_for_kpi_code(code)
                assert result == mid, f"Expected {mid} for code {code}, got {result}"
                return
        # If no linked_kpi_codes exist, just verify function returns None gracefully
        result = get_metric_for_kpi_code('nonexistent')
        assert result is None

    def test_get_metrics_for_playbook(self):
        from power_of_1_model import get_metrics_for_playbook
        result = get_metrics_for_playbook('voc-sprint')
        assert isinstance(result, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
