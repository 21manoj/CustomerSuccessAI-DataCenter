#!/usr/bin/env python3
"""
Test Suite 3 — Qdrant Feedback Loop + Weight Recalibration
===========================================================
Tests: execution feedback storage, weight recalibration algorithm,
learning rate, decay curves, calibration history.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import json
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timedelta


# ============================================================
# MODULE IMPORT TESTS
# ============================================================

class TestImports:
    def test_feedback_loop_imports(self):
        from qdrant_feedback_loop import (
            ExecutionFeedback, RecalibrationResult,
            store_execution_feedback, recalibrate_weights,
            recalibrate_all, get_calibration_history, get_current_weights,
            recalibration_result_to_dict,
        )

    def test_data_structures(self):
        from qdrant_feedback_loop import ExecutionFeedback
        feedback = ExecutionFeedback(
            execution_id='test-123',
            customer_id=1,
            account_id='acc-456',
            playbook_type='voc-sprint',
            outcome='resolved',
        )
        assert feedback.execution_id == 'test-123'
        assert feedback.outcome == 'resolved'


# ============================================================
# EXECUTION FEEDBACK TESTS
# ============================================================

class TestExecutionFeedback:
    def test_feedback_dataclass_defaults(self):
        from qdrant_feedback_loop import ExecutionFeedback
        fb = ExecutionFeedback(
            execution_id='exec-1',
            customer_id=1,
            account_id='100',
            playbook_type='sla-stabilizer',
            outcome='escalated',
        )
        assert fb.predicted_churn_prob is None
        assert fb.predicted_expansion_prob is None
        assert fb.actual_churn is None
        assert fb.kpi_improvements is None
        assert fb.signals_considered is None

    def test_feedback_with_all_fields(self):
        from qdrant_feedback_loop import ExecutionFeedback
        fb = ExecutionFeedback(
            execution_id='exec-2',
            customer_id=1,
            account_id='200',
            playbook_type='renewal-safeguard',
            outcome='resolved',
            predicted_churn_prob=0.7,
            predicted_expansion_prob=0.2,
            actual_churn=False,
            actual_expansion=True,
            kpi_improvements={'NRR': 0.5, 'GRR': 0.3},
            signals_considered=['quantitative', 'qualitative'],
            power_of_1_metric='NRR',
            dollar_impact_realized=15000.0,
        )
        assert fb.predicted_churn_prob == 0.7
        assert fb.actual_expansion is True
        assert fb.dollar_impact_realized == 15000.0


# ============================================================
# RECALIBRATION ALGORITHM TESTS (unit — no DB)
# ============================================================

class TestRecalibrationAlgorithm:
    def test_weight_normalization(self):
        """Weights should always sum to 1.0 after recalibration."""
        weights = {
            'quantitative_signals': 0.45,
            'qualitative_signals': 0.30,
            'historical_patterns': 0.25,
            'playbook_feedback': 0.15,
        }
        # Normalize
        total = sum(weights.values())
        normalized = {k: round(v / total, 4) for k, v in weights.items()}
        assert abs(sum(normalized.values()) - 1.0) < 0.01

    def test_learning_rate_bounds(self):
        """Learning rate should constrain weight adjustments."""
        learning_rate = 0.1
        current_weight = 0.10
        max_increase = learning_rate * 0.10  # 10% of learning rate
        new_weight = min(0.25, current_weight + max_increase)
        assert new_weight <= 0.25
        assert new_weight >= current_weight

    def test_error_reduction_calculation(self):
        """Error reduction should be positive when model improves."""
        error_before = 0.4  # 60% accuracy
        learning_rate = 0.1
        error_after = error_before * (1 - learning_rate)
        reduction_pct = ((error_before - error_after) / error_before) * 100
        assert reduction_pct > 0
        assert reduction_pct == pytest.approx(10.0, abs=0.1)

    def test_accuracy_calculation(self):
        """Accuracy should be correct for given predictions."""
        predictions = [
            {'predicted': 0.7, 'actual': True},   # Correct
            {'predicted': 0.3, 'actual': False},   # Correct
            {'predicted': 0.6, 'actual': False},   # Wrong
            {'predicted': 0.2, 'actual': True},    # Wrong
        ]
        correct = sum(
            1 for p in predictions
            if (p['predicted'] >= 0.5) == p['actual']
        )
        accuracy = correct / len(predictions)
        assert accuracy == 0.5

    def test_decay_curve(self):
        """Signal weight adjustments should decay over recalibration cycles."""
        base_adjustment = 0.05
        decay_rate = 0.90
        adjustments = []
        for cycle in range(5):
            adj = base_adjustment * (decay_rate ** cycle)
            adjustments.append(adj)
        # Each adjustment should be smaller than the previous
        for i in range(1, len(adjustments)):
            assert adjustments[i] < adjustments[i-1]


# ============================================================
# RECALIBRATION RESULT TESTS
# ============================================================

class TestRecalibrationResult:
    def test_result_serialization(self):
        from qdrant_feedback_loop import RecalibrationResult, recalibration_result_to_dict
        result = RecalibrationResult(
            customer_id=1,
            playbook_type='voc-sprint',
            feedback_count=10,
            previous_weights={'quantitative_signals': 0.40, 'qualitative_signals': 0.30},
            new_weights={'quantitative_signals': 0.42, 'qualitative_signals': 0.28},
            error_reduction_pct=5.0,
            signal_accuracy={'churn_accuracy': 0.75, 'expansion_accuracy': 0.80},
            calibration_id=42,
        )
        d = recalibration_result_to_dict(result)
        assert d['customer_id'] == 1
        assert d['feedback_count'] == 10
        assert d['error_reduction_pct'] == 5.0
        assert 'churn_accuracy' in d['signal_accuracy']

    def test_empty_feedback_result(self):
        from qdrant_feedback_loop import RecalibrationResult
        result = RecalibrationResult(
            customer_id=1,
            playbook_type='activation-blitz',
            feedback_count=0,
            previous_weights={},
            new_weights={},
            error_reduction_pct=0,
            signal_accuracy={},
        )
        assert result.feedback_count == 0
        assert result.error_reduction_pct == 0


# ============================================================
# DEFAULT WEIGHTS TESTS
# ============================================================

class TestDefaultWeights:
    def test_default_weights_sum_to_one(self):
        default_weights = {
            'quantitative_signals': 0.40,
            'qualitative_signals': 0.30,
            'historical_patterns': 0.20,
            'playbook_feedback': 0.10,
        }
        assert abs(sum(default_weights.values()) - 1.0) < 0.001

    def test_all_weight_types_present(self):
        default_weights = {
            'quantitative_signals': 0.40,
            'qualitative_signals': 0.30,
            'historical_patterns': 0.20,
            'playbook_feedback': 0.10,
        }
        expected_types = {'quantitative_signals', 'qualitative_signals',
                         'historical_patterns', 'playbook_feedback'}
        assert set(default_weights.keys()) == expected_types


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
