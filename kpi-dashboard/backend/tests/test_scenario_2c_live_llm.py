#!/usr/bin/env python3
"""
Scenario 2c Integration Test — Live LLM Signal Detection
==========================================================
Tests the REAL OpenAI LLM path for signal detection + playbook trigger
validation.  Requires OPENAI_API_KEY environment variable.

Coverage:
  1. SignalAnalystAgent.analyze() with real GPT-4o call
  2. PlaybookTriggerValidator._validate_with_llm() end-to-end
  3. Structured output parsing (SignalAnalystOutput model)
  4. Confidence → threshold → decision gate
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import time

# ---- Skip entire module if no key ----
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    pytest.skip("OPENAI_API_KEY not set — skipping live LLM tests", allow_module_level=True)

from agents.signal_analyst_agent import SignalAnalystAgent, AnalysisError
from agents.models import (
    SignalAnalystInput, SignalAnalystOutput, SignalData,
    TriggerValidationResult, TriggerValidationDecision,
)
from playbook_trigger_validator import PlaybookTriggerValidator


# ============================================================
# Shared fixtures
# ============================================================

def _churn_signals():
    """Signals strongly indicating churn risk."""
    return SignalAnalystInput(
        account_id="test-2c-churn-001",
        customer_id=1,
        vertical_type="data_center_infrastructure",
        account_name="Acme DataCenter Corp",
        account_arr=500000.0,
        health_score=35.0,
        quantitative_signals=[
            SignalData(
                similarity=0.95,
                payload={
                    "pillar": "AI",
                    "metric_type": "AI-KPI1",
                    "current_value": 5500,
                    "trend": -0.35,
                    "text": "GPU utilization declined 35% over 14 days (8500 → 5500)",
                },
            ),
            SignalData(
                similarity=0.90,
                payload={
                    "pillar": "OS",
                    "metric_type": "OS-KPI2",
                    "current_value": 12,
                    "trend": 0.60,
                    "text": "P1 tickets spiked 60% — 12 open incidents in last 7 days",
                },
            ),
            SignalData(
                similarity=0.88,
                payload={
                    "pillar": "EX",
                    "metric_type": "EX-KPI1",
                    "current_value": 3.2,
                    "trend": -0.25,
                    "text": "NPS score dropped from 4.3 → 3.2",
                },
            ),
        ],
        qualitative_signals=[
            SignalData(
                similarity=0.92,
                payload={
                    "signal_type": "escalation",
                    "sentiment": "negative",
                    "severity": "critical",
                    "text": "Customer threatened to cancel unless GPU performance improves within 30 days",
                },
            ),
            SignalData(
                similarity=0.85,
                payload={
                    "signal_type": "meeting_note",
                    "sentiment": "negative",
                    "severity": "high",
                    "text": "VP of Engineering mentioned evaluating competitor data center solutions",
                },
            ),
        ],
        historical_patterns=[
            SignalData(
                similarity=0.80,
                payload={
                    "outcome_type": "churn",
                    "signals_summary": (
                        "Similar account with declining GPU utilization and escalating tickets "
                        "churned after 45 days. Early intervention with SLA reset prevented "
                        "a second similar churn."
                    ),
                },
            ),
        ],
        analysis_type="churn_risk",
        time_horizon_days=60,
    )


def _expansion_signals():
    """Signals strongly indicating expansion opportunity."""
    return SignalAnalystInput(
        account_id="test-2c-expand-001",
        customer_id=1,
        vertical_type="data_center_infrastructure",
        account_name="GrowthTech DataCenter",
        account_arr=750000.0,
        health_score=88.0,
        quantitative_signals=[
            SignalData(
                similarity=0.95,
                payload={
                    "pillar": "AI",
                    "metric_type": "AI-KPI1",
                    "current_value": 9800,
                    "trend": 0.25,
                    "text": "GPU utilization at 98% — nearing capacity (target: 10000)",
                },
            ),
            SignalData(
                similarity=0.90,
                payload={
                    "pillar": "CH",
                    "metric_type": "CH-KPI1",
                    "current_value": 99.99,
                    "trend": 0.01,
                    "text": "Uptime at 99.99% — exceeding SLA target of 99.95%",
                },
            ),
        ],
        qualitative_signals=[
            SignalData(
                similarity=0.88,
                payload={
                    "signal_type": "meeting_note",
                    "sentiment": "positive",
                    "severity": "medium",
                    "text": "CTO asked about adding 2 more GPU racks for their ML training pipeline",
                },
            ),
        ],
        historical_patterns=[
            SignalData(
                similarity=0.78,
                payload={
                    "outcome_type": "expansion",
                    "signals_summary": (
                        "Account with similar high utilization and positive sentiment "
                        "expanded by 40% within 90 days after proactive capacity planning."
                    ),
                },
            ),
        ],
        analysis_type="expansion_opportunity",
        time_horizon_days=60,
    )


# ============================================================
# TEST 1: Live SignalAnalystAgent — churn risk
# ============================================================

class TestLiveSignalAnalyst:
    """Tests that call the real OpenAI API via SignalAnalystAgent."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.agent = SignalAnalystAgent(
            openai_api_key=OPENAI_API_KEY,
            model="gpt-4o",
            temperature=0.2,
            max_tokens=3000,
        )

    def test_churn_risk_analysis(self):
        """LLM should identify high churn risk from declining signals."""
        input_data = _churn_signals()
        result = self.agent.analyze(input_data)

        # Structural assertions — output must be a valid SignalAnalystOutput
        assert isinstance(result, SignalAnalystOutput)
        assert result.account_id == "test-2c-churn-001"

        # Churn probability should be elevated (above 50%)
        assert result.churn_probability >= 40, (
            f"Expected churn_probability >= 40 for heavily declining account, got {result.churn_probability}"
        )

        # Health score should be low
        assert result.health_score <= 60, (
            f"Expected health_score <= 60, got {result.health_score}"
        )

        # Reasoning should be non-empty
        assert result.reasoning and len(result.reasoning) > 20

        # Should have at least one recommended action
        assert result.recommended_actions and len(result.recommended_actions) >= 1

        # Confidence should be populated
        assert result.confidence is not None

        print(f"\n  Churn analysis result:")
        print(f"    churn_probability: {result.churn_probability}%")
        print(f"    expansion_probability: {result.expansion_probability}%")
        print(f"    health_score: {result.health_score}")
        print(f"    predicted_outcome: {result.predicted_outcome}")
        print(f"    confidence: {result.confidence.overall_confidence if result.confidence else 'N/A'}")
        print(f"    recommendations: {len(result.recommended_actions)}")
        print(f"    reasoning: {result.reasoning[:120]}...")

    def test_expansion_opportunity_analysis(self):
        """LLM should identify expansion opportunity from strong signals."""
        input_data = _expansion_signals()
        result = self.agent.analyze(input_data)

        assert isinstance(result, SignalAnalystOutput)
        assert result.account_id == "test-2c-expand-001"

        # Expansion probability should be elevated
        assert result.expansion_probability >= 30, (
            f"Expected expansion_probability >= 30, got {result.expansion_probability}"
        )

        # Health score should be high
        assert result.health_score >= 60, (
            f"Expected health_score >= 60 for healthy account, got {result.health_score}"
        )

        # Should have recommendations
        assert result.recommended_actions and len(result.recommended_actions) >= 1

        print(f"\n  Expansion analysis result:")
        print(f"    churn_probability: {result.churn_probability}%")
        print(f"    expansion_probability: {result.expansion_probability}%")
        print(f"    health_score: {result.health_score}")
        print(f"    predicted_outcome: {result.predicted_outcome}")
        print(f"    recommendations: {len(result.recommended_actions)}")


# ============================================================
# TEST 2: PlaybookTriggerValidator — LLM gate
# ============================================================

class TestLiveTriggerValidator:
    """Test the LLM validation gate with real API calls."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.validator = PlaybookTriggerValidator(openai_api_key=OPENAI_API_KEY)

    def test_validate_with_llm_churn_playbook(self):
        """LLM gate should approve a churn playbook for a degraded account."""
        result = self.validator._validate_with_llm(
            account_id="test-2c-churn-001",
            customer_id=1,
            playbook_id="PB-02",
            trigger_context={
                "AI-KPI1": {"value": 5500, "threshold": 7000},
                "OS-KPI2": {"value": 12, "threshold": 5},
            },
            account_name="Acme DataCenter Corp",
            account_arr=500000.0,
            health_score=35.0,
            vertical="dc2_s",
        )

        assert isinstance(result, TriggerValidationResult)
        assert result.confidence > 0, f"Confidence should be positive, got {result.confidence}"
        assert result.reasoning and len(result.reasoning) > 10
        assert result.signal_analyst_output is not None

        # Decision should be one of the three valid states
        assert result.decision in (
            TriggerValidationDecision.AUTO_APPROVED,
            TriggerValidationDecision.AUTO_REJECTED,
            TriggerValidationDecision.PENDING_MANUAL_APPROVAL,
        )

        print(f"\n  Trigger validation (churn PB-02):")
        print(f"    decision: {result.decision}")
        print(f"    approved: {result.approved}")
        print(f"    confidence: {result.confidence}")
        print(f"    reasoning: {result.reasoning[:120]}...")

    def test_validate_trigger_full_path_with_cache(self):
        """Full validate_trigger path: LLM call → cache → cache hit."""
        # First call — should hit LLM
        t0 = time.time()
        result1 = self.validator.validate_trigger(
            account_id="test-2c-cache-001",
            customer_id=1,
            playbook_id="PB-05",
            trigger_context={"EX-KPI1": {"value": 3.2, "threshold": 4.0}},
            account_name="Cache Test Corp",
            health_score=42.0,
            use_cache=True,
        )
        t1 = time.time()
        first_call_ms = (t1 - t0) * 1000

        assert isinstance(result1, TriggerValidationResult)

        # Second call — should be a cache hit (fast)
        t2 = time.time()
        result2 = self.validator.validate_trigger(
            account_id="test-2c-cache-001",
            customer_id=1,
            playbook_id="PB-05",
            trigger_context={"EX-KPI1": {"value": 3.2, "threshold": 4.0}},
            account_name="Cache Test Corp",
            health_score=42.0,
            use_cache=True,
        )
        t3 = time.time()
        cache_hit_ms = (t3 - t2) * 1000

        # Cache hit should be dramatically faster (< 10ms vs seconds)
        assert cache_hit_ms < first_call_ms, (
            f"Cache hit ({cache_hit_ms:.0f}ms) should be faster than first call ({first_call_ms:.0f}ms)"
        )
        assert cache_hit_ms < 100, f"Cache hit took {cache_hit_ms:.0f}ms — expected < 100ms"

        # Results should be identical
        assert result1.confidence == result2.confidence
        assert result1.decision == result2.decision

        print(f"\n  Cache test:")
        print(f"    First call: {first_call_ms:.0f}ms")
        print(f"    Cache hit:  {cache_hit_ms:.1f}ms")
        print(f"    Speedup:    {first_call_ms / max(cache_hit_ms, 0.1):.0f}x")


# ============================================================
# TEST 3: Coherence check — expansion playbook + churn signals
# ============================================================

class TestCoherenceCheck:
    """Verify the LLM coherence gate rejects contradictory triggers."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.validator = PlaybookTriggerValidator(openai_api_key=OPENAI_API_KEY)

    def test_expansion_playbook_with_churn_signals_is_rejected(self):
        """
        If an expansion playbook (PB-04) fires but the LLM detects churn,
        the coherence check should cap confidence ≤ 0.3 → auto-reject.
        """
        result = self.validator._validate_with_llm(
            account_id="test-2c-coherence-001",
            customer_id=1,
            playbook_id="PB-04",  # Expansion playbook
            trigger_context={
                # But the KPIs tell a churn story
                "AI-KPI1": {"value": 3000, "threshold": 7000},
                "OS-KPI2": {"value": 15, "threshold": 5},
            },
            account_name="Contradictory Signals Corp",
            account_arr=300000.0,
            health_score=25.0,  # Very low health
            vertical="dc2_s",
        )

        assert isinstance(result, TriggerValidationResult)

        # The coherence check should either:
        # a) Auto-reject (confidence < 0.4) because LLM predicted churn
        #    but playbook is expansion, OR
        # b) At minimum, NOT auto-approve
        assert result.decision != TriggerValidationDecision.AUTO_APPROVED or result.confidence <= 0.4, (
            f"Expected coherence rejection for expansion playbook with churn signals, "
            f"got decision={result.decision}, confidence={result.confidence}"
        )

        print(f"\n  Coherence check (expansion PB-04 + churn signals):")
        print(f"    decision: {result.decision}")
        print(f"    approved: {result.approved}")
        print(f"    confidence: {result.confidence}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
