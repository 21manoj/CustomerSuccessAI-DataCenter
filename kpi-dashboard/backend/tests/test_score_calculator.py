"""
Unit tests for ScoreCalculator — L1 (KPI), L2 (Pillar), L3 (Health) scoring.

These tests are CRITICAL — health scores drive every decision in the platform:
turnaround narratives, ROI attribution, playbook recommendations, NRR forecasts.

Run: pytest kpi-dashboard/backend/tests/test_score_calculator.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.score_calculator import ScoreCalculator


# ═══════════════════════════════════════════════════════════════
# Helpers — create ScoreCalculator without DB
# ═══════════════════════════════════════════════════════════════

def _make_calculator(pillar_weights=None, kpi_weights=None, kpi_overrides=None):
    """Create a ScoreCalculator with injected config (no DB needed)."""
    calc = object.__new__(ScoreCalculator)
    calc.customer_id = 0  # test customer
    calc.vertical = 'dc2_s'
    calc.config = {
        'pillar_weights': pillar_weights or {
            'P1': 0.15, 'P2': 0.20, 'P3': 0.25, 'P4': 0.15, 'P5': 0.25
        },
        'kpi_weights': kpi_weights or {},
        'kpi_overrides': kpi_overrides or {},
        'enabled_kpis': [],
    }
    return calc


# ═══════════════════════════════════════════════════════════════
# L1: KPI Score Tests
# ═══════════════════════════════════════════════════════════════

class TestL1KPIScoring:
    """Test individual KPI score normalization (0-100).

    Uses kpi_overrides to test operators independently of catalog definitions.
    This makes tests catalog-independent and deterministic.
    """

    def _calc_with_override(self, target=85, operator='>', range_vals=None):
        """Helper: create calculator with a test KPI override."""
        return _make_calculator(kpi_overrides={
            'P1-KPI99': {
                'target': target,
                'operator': operator,
                'range': range_vals or [0.0, 100.0],
            }
        })

    def test_higher_is_better_at_target(self):
        """'>' operator: value at target → score 100."""
        calc = self._calc_with_override(target=85, operator='>')
        score, status = calc.calculate_kpi_score('P1-KPI99', 85.0)
        assert score == 100.0
        assert status == 'healthy'

    def test_higher_is_better_above_target(self):
        """'>' operator: value above target → capped at 100."""
        calc = self._calc_with_override(target=85, operator='>')
        score, _ = calc.calculate_kpi_score('P1-KPI99', 99.0)
        assert score == 100.0

    def test_higher_is_better_at_zero(self):
        """'>' operator: value at range min → score 0."""
        calc = self._calc_with_override(target=85, operator='>')
        score, status = calc.calculate_kpi_score('P1-KPI99', 0.0)
        assert score == 0.0
        assert status == 'critical'

    def test_higher_is_better_midpoint(self):
        """'>' operator: midpoint value → score ~50."""
        calc = self._calc_with_override(target=85, operator='>')
        score, _ = calc.calculate_kpi_score('P1-KPI99', 42.5)
        assert 45.0 <= score <= 55.0

    def test_higher_is_better_negative(self):
        """'>' operator: negative value → floor at 0."""
        calc = self._calc_with_override(target=85, operator='>')
        score, _ = calc.calculate_kpi_score('P1-KPI99', -10.0)
        assert score == 0.0

    def test_lower_is_better_below_target(self):
        """'<' operator: value below target → score 100."""
        calc = self._calc_with_override(target=5, operator='<', range_vals=[0, 50])
        score, _ = calc.calculate_kpi_score('P1-KPI99', 3.0)
        assert score == 100.0

    def test_lower_is_better_at_range_max(self):
        """'<' operator: value at range max → score 0."""
        calc = self._calc_with_override(target=5, operator='<', range_vals=[0, 50])
        score, _ = calc.calculate_kpi_score('P1-KPI99', 50.0)
        assert score == 0.0

    def test_equals_operator_exact(self):
        """'=' operator: exact match → score 100."""
        calc = self._calc_with_override(target=50, operator='=')
        score, _ = calc.calculate_kpi_score('P1-KPI99', 50.0)
        assert score == 100.0

    def test_equals_operator_far_away(self):
        """'=' operator: value far from target → low score."""
        calc = self._calc_with_override(target=50, operator='=')
        score, _ = calc.calculate_kpi_score('P1-KPI99', 0.0)
        assert score < 10.0

    def test_unknown_kpi_raises(self):
        """Unknown KPI code (non-P-format) should raise ValueError."""
        calc = _make_calculator()
        with pytest.raises(ValueError, match="No definition found"):
            calc.calculate_kpi_score('NONEXISTENT', 50.0)

    def test_catalog_kpi_loads(self):
        """Real DC2_S catalog KPI (P1-KPI1) should load and score without error."""
        calc = _make_calculator()
        score, status = calc.calculate_kpi_score('P1-KPI1', 10.0)
        # P1-KPI1 is TTFW (lower is better, target=14 days)
        # 10 days < 14 target → should score 100
        assert score == 100.0


# ═══════════════════════════════════════════════════════════════
# L2: Pillar Score Tests
# ═══════════════════════════════════════════════════════════════

class TestL2PillarScoring:
    """Test pillar-level weighted averaging of KPI scores."""

    def test_equal_weights_average(self):
        """With equal weights, pillar score should be simple average."""
        calc = _make_calculator(kpi_weights={
            'P1': {'P1-KPI1': 0.5, 'P1-KPI2': 0.5}
        })
        score, status, _ = calc.calculate_pillar_score(
            'P1', {'P1-KPI1': 80.0, 'P1-KPI2': 60.0}
        )
        assert score == 70.0
        assert status == 'healthy'

    def test_weighted_average(self):
        """With unequal weights, pillar score should be weighted average."""
        calc = _make_calculator(kpi_weights={
            'P1': {'P1-KPI1': 0.8, 'P1-KPI2': 0.2}
        })
        score, _, _ = calc.calculate_pillar_score(
            'P1', {'P1-KPI1': 80.0, 'P1-KPI2': 40.0}
        )
        # 80*0.8 + 40*0.2 = 64+8 = 72
        assert abs(score - 72.0) < 0.1

    def test_single_kpi_pillar(self):
        """Pillar with 1 KPI should equal that KPI's score."""
        calc = _make_calculator(kpi_weights={
            'P2': {'P2-KPI1': 1.0}
        })
        score, _, _ = calc.calculate_pillar_score(
            'P2', {'P2-KPI1': 65.0}
        )
        assert score == 65.0

    def test_partial_kpis_normalizes(self):
        """If only some KPIs have data, normalize by available weight."""
        calc = _make_calculator(kpi_weights={
            'P1': {'P1-KPI1': 0.6, 'P1-KPI2': 0.4}
        })
        # Only P1-KPI1 has data — weight 0.6 normalizes to 1.0
        score, _, _ = calc.calculate_pillar_score(
            'P1', {'P1-KPI1': 80.0}
        )
        assert score == 80.0

    def test_all_healthy_kpis(self):
        """All KPIs at 100 should produce pillar score 100."""
        calc = _make_calculator(kpi_weights={
            'P3': {'P3-KPI1': 0.33, 'P3-KPI2': 0.33, 'P3-KPI3': 0.34}
        })
        score, _, _ = calc.calculate_pillar_score(
            'P3', {'P3-KPI1': 100.0, 'P3-KPI2': 100.0, 'P3-KPI3': 100.0}
        )
        assert abs(score - 100.0) < 0.1

    def test_all_critical_kpis(self):
        """All KPIs at 0 should produce pillar score 0."""
        calc = _make_calculator(kpi_weights={
            'P3': {'P3-KPI1': 0.5, 'P3-KPI2': 0.5}
        })
        score, _, _ = calc.calculate_pillar_score(
            'P3', {'P3-KPI1': 0.0, 'P3-KPI2': 0.0}
        )
        assert score == 0.0


# ═══════════════════════════════════════════════════════════════
# L3: Health Score Tests
# ═══════════════════════════════════════════════════════════════

class TestL3HealthScoring:
    """Test overall health score from pillar weighted average."""

    def test_equal_pillar_weights(self):
        """With equal pillar weights, health = simple average of pillars."""
        calc = _make_calculator(pillar_weights={
            'P1': 0.25, 'P2': 0.25, 'P3': 0.25, 'P5': 0.25
        })
        health, status, _, _ = calc.calculate_health_score({
            'P1': 80.0, 'P2': 60.0, 'P3': 70.0, 'P5': 90.0
        })
        # (80+60+70+90)/4 = 75
        assert abs(health - 75.0) < 0.1
        assert status == 'healthy'

    def test_weighted_pillar_scores(self):
        """With unequal weights, health is weighted average."""
        calc = _make_calculator(pillar_weights={
            'P1': 0.10, 'P3': 0.40, 'P5': 0.50
        })
        health, _, _, _ = calc.calculate_health_score({
            'P1': 100.0, 'P3': 50.0, 'P5': 80.0
        })
        # 100*0.10 + 50*0.40 + 80*0.50 = 10+20+40 = 70
        assert abs(health - 70.0) < 0.1

    def test_partial_pillars_normalizes(self):
        """Starter 9 with only 4 pillars should normalize correctly."""
        calc = _make_calculator(pillar_weights={
            'P1': 0.25, 'P2': 0.25, 'P3': 0.25, 'P5': 0.25
        })
        # Only 3 pillars have data — should normalize
        health, _, _, _ = calc.calculate_health_score({
            'P1': 80.0, 'P3': 60.0, 'P5': 70.0
        })
        # (80*0.25 + 60*0.25 + 70*0.25) / 0.75 = 52.5/0.75 = 70
        assert abs(health - 70.0) < 0.1

    def test_all_healthy_pillars(self):
        """All pillars at 100 → health 100."""
        calc = _make_calculator(pillar_weights={
            'P1': 0.25, 'P2': 0.25, 'P3': 0.25, 'P5': 0.25
        })
        health, status, _, _ = calc.calculate_health_score({
            'P1': 100.0, 'P2': 100.0, 'P3': 100.0, 'P5': 100.0
        })
        assert health == 100.0
        assert status == 'healthy'

    def test_all_zero_pillars(self):
        """All pillars at 0 → health 0 → critical."""
        calc = _make_calculator(pillar_weights={
            'P1': 0.25, 'P2': 0.25, 'P3': 0.25, 'P5': 0.25
        })
        health, status, _, _ = calc.calculate_health_score({
            'P1': 0.0, 'P2': 0.0, 'P3': 0.0, 'P5': 0.0
        })
        assert health == 0.0
        assert status == 'critical'

    def test_no_matching_pillar_weights(self):
        """Health calc with mismatched pillar codes should produce 0 weight → raise."""
        calc = _make_calculator(pillar_weights={'P9': 1.0})
        with pytest.raises(ValueError):
            calc.calculate_health_score({'P1': 80.0})


# ═══════════════════════════════════════════════════════════════
# Health Threshold Tests
# ═══════════════════════════════════════════════════════════════

class TestHealthThresholds:
    """Test health score → status classification boundaries."""

    def test_critical_below_50(self):
        """Score < 50 → critical."""
        import utils.health_thresholds as ht
        assert ht.classify(0) == 'critical'
        assert ht.classify(49) == 'critical'
        assert ht.classify(49.9) == 'critical'

    def test_at_risk_50_to_69(self):
        """Score 50-69 → at_risk."""
        import utils.health_thresholds as ht
        assert ht.classify(50) == 'at_risk'
        assert ht.classify(60) == 'at_risk'
        assert ht.classify(69) == 'at_risk'
        assert ht.classify(69.9) == 'at_risk'

    def test_healthy_70_plus(self):
        """Score >= 70 → healthy."""
        import utils.health_thresholds as ht
        assert ht.classify(70) == 'healthy'
        assert ht.classify(85) == 'healthy'
        assert ht.classify(100) == 'healthy'

    def test_boundary_50(self):
        """Score exactly 50 → at_risk (not critical)."""
        import utils.health_thresholds as ht
        assert ht.classify(50) == 'at_risk'

    def test_boundary_70(self):
        """Score exactly 70 → healthy (not at_risk)."""
        import utils.health_thresholds as ht
        assert ht.classify(70) == 'healthy'


# ═══════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases that have caused production bugs."""

    def test_starter_9_four_pillar_health(self):
        """Starter 9 tier with P4 excluded should still produce valid health."""
        calc = _make_calculator(pillar_weights={
            'P1': 0.25, 'P2': 0.25, 'P3': 0.25, 'P5': 0.25
        })
        health, status, _, _ = calc.calculate_health_score({
            'P1': 72.0, 'P2': 68.0, 'P3': 65.0, 'P5': 75.0
        })
        expected = (72 + 68 + 65 + 75) / 4  # 70.0
        assert abs(health - expected) < 0.1
        assert status == 'healthy'

    def test_single_pillar_health(self):
        """Edge case: only 1 pillar has data."""
        calc = _make_calculator(pillar_weights={
            'P1': 0.25, 'P2': 0.25, 'P3': 0.25, 'P5': 0.25
        })
        health, _, _, _ = calc.calculate_health_score({'P5': 80.0})
        assert health == 80.0

    def test_zero_weight_pillar_ignored(self):
        """Pillar with weight 0 should not affect health score."""
        calc = _make_calculator(pillar_weights={
            'P1': 0.50, 'P2': 0.50, 'P4': 0.0
        })
        health, _, _, _ = calc.calculate_health_score({
            'P1': 80.0, 'P2': 60.0, 'P4': 100.0
        })
        # P4 weight=0, so health = (80*0.5 + 60*0.5) / 1.0 = 70
        assert abs(health - 70.0) < 0.1
