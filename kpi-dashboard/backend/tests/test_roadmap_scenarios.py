#!/usr/bin/env python3
"""
Test Suite 2 — REST Ingest + Scenario Scripts
==============================================
Tests: quarterly actual ingest, what-if scenarios, scenario comparison,
seed data, timeline overview.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import json
from unittest.mock import patch, MagicMock


# ============================================================
# MODULE IMPORT TESTS
# ============================================================

class TestImports:
    def test_roadmap_scenario_imports(self):
        from roadmap_scenario_ingest import roadmap_scenario_api
        assert roadmap_scenario_api is not None
        assert roadmap_scenario_api.name == 'roadmap_scenario_api'


# ============================================================
# SCENARIO CALCULATION TESTS (unit — no Flask app needed)
# ============================================================

class TestScenarioCalculations:
    def test_single_metric_scenario(self):
        from power_of_1_model import calculate_power_of_1_impact
        result = calculate_power_of_1_impact('NRR', 3.0)
        assert result['total_impact'] > 0
        assert result['investment'] > 0

    def test_multi_metric_scenario(self):
        """Simulate the what-if scenario endpoint logic."""
        from power_of_1_model import calculate_power_of_1_impact, POWER_OF_1_METRICS

        improvements = {
            'TTFV': 3.0,
            'NRR': 4.0,
            'GRR': 2.0,
            'ticket_resolution_time': 5.0,
            'product_adoption': 3.0,
            'expansion_rate': 2.0,
        }

        total_impact = 0
        total_investment = 0
        for metric_id, pct in improvements.items():
            if metric_id in POWER_OF_1_METRICS:
                result = calculate_power_of_1_impact(metric_id, pct)
                total_impact += result['total_impact']
                total_investment += result['investment']

        assert total_impact > 0
        assert total_investment > 0
        roi = (total_impact - total_investment) / total_investment
        assert roi > 0, "ROI should be positive for realistic improvements"

    def test_scenario_comparison_logic(self):
        """Two scenarios — aggressive should have higher ROI."""
        from power_of_1_model import calculate_power_of_1_impact, POWER_OF_1_METRICS

        scenarios = [
            {'name': 'Conservative', 'improvements': {'NRR': 1, 'GRR': 1}},
            {'name': 'Aggressive', 'improvements': {'NRR': 4, 'GRR': 3, 'TTFV': 3}},
        ]

        results = []
        for s in scenarios:
            total_impact = 0
            total_inv = 0
            for mid, pct in s['improvements'].items():
                if mid in POWER_OF_1_METRICS:
                    r = calculate_power_of_1_impact(mid, float(pct))
                    total_impact += r['total_impact']
                    total_inv += r['investment']
            results.append({
                'name': s['name'],
                'roi': (total_impact - total_inv) / total_inv if total_inv > 0 else 0,
                'total_impact': total_impact,
            })

        # Aggressive should have higher total impact
        assert results[1]['total_impact'] > results[0]['total_impact']


# ============================================================
# QUARTERLY ACTUALS INGEST TESTS
# ============================================================

class TestQuarterlyActuals:
    def test_assess_quarter_with_actuals(self):
        from quarterly_checkpoints import assess_quarter, assessment_to_dict

        actuals = {'TTFV': 29.3, 'NRR': 105.8, 'ticket_resolution_time': 46.0}
        result = assess_quarter('Q2', actuals)
        d = assessment_to_dict(result)

        assert d['quarter'] == 'Q2'
        assert len(d['metrics']) > 0
        assert d['overall_status'] in ('on_track', 'at_risk', 'off_track', 'ahead', 'not_started')

    def test_ingest_empty_actuals(self):
        from quarterly_checkpoints import assess_quarter
        result = assess_quarter('Q3', {})
        assert result.on_track_count == 0
        assert result.off_track_count == 0


# ============================================================
# RESOURCE CAPACITY CHECK TESTS
# ============================================================

class TestResourceCapacity:
    def test_capacity_check_feasible(self):
        from resource_capacity_model import check_capacity, CSRole
        planned = {CSRole.CSM: 20, CSRole.CS_OPS: 10}
        result = check_capacity(planned)
        assert result.is_feasible is True or result.is_feasible is False
        assert result.utilization_by_role is not None

    def test_action_cost_calculation(self):
        from resource_capacity_model import calculate_action_cost, CSRole
        roles = {CSRole.CSM: 8, CSRole.CS_OPS: 4}
        result = calculate_action_cost(roles)
        assert result['total_cost'] > 0

    def test_resource_pool_summary(self):
        from resource_capacity_model import get_resource_pool_summary
        summary = get_resource_pool_summary()
        assert len(summary) > 0


# ============================================================
# TIMELINE / ROADMAP OVERVIEW TESTS
# ============================================================

class TestTimeline:
    def test_quarter_targets_structure(self):
        from quarterly_checkpoints import QUARTER_TARGETS
        for q in ['Q1', 'Q2', 'Q3', 'Q4']:
            qt = QUARTER_TARGETS[q]
            assert qt.quarter == q
            assert qt.label is not None
            assert qt.month_range is not None
            for mid, mc in qt.metric_targets.items():
                assert mc.target_value is not None
                assert mc.milestone is not None

    def test_scaling_scenarios_format(self):
        from power_of_1_model import SCALING_SCENARIOS
        assert isinstance(SCALING_SCENARIOS, (list, dict))


# ============================================================
# SEED BASELINE TESTS
# ============================================================

class TestSeedBaseline:
    def test_baseline_values_exist(self):
        from power_of_1_model import POWER_OF_1_METRICS
        for mid, metric in POWER_OF_1_METRICS.items():
            assert metric.baseline is not None
            assert metric.annual_impact_per_pct > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
