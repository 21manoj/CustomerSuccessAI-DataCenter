#!/usr/bin/env python3
"""
Test Decision Matrix Implementation

Tests all scenarios of the decision matrix:
1. AGREEMENT: KPI declining + negative signals
2. DISAGREEMENT: KPI declining + positive signals
3. NEUTRAL: KPI stable + mixed signals
4. POSITIVE_ALIGNMENT: KPI improving + positive signals
5. INSUFFICIENT_DATA: No KPI trend data

Uses realistic test data to verify decision matrix logic.
"""

import sys
import os
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from agents.models import SignalAnalystInput, SignalData
from agents.decision_matrix import (
    calculate_decision_matrix,
    DataAlignment,
    TrendDirection,
    SignalSentiment
)
import os
from openai_key_utils import get_openai_api_key

def create_test_signal_data(signal_type: str, payload: dict, similarity: float = 0.85) -> SignalData:
    """Helper to create SignalData objects"""
    return SignalData(similarity=similarity, payload=payload)


def test_scenario_1_agreement():
    """
    Scenario 1: AGREEMENT
    KPI trend: Declining (healthy → at-risk)
    Signal sentiment: Negative (customer frustrated)
    Expected: AGREEMENT with high confidence
    """
    print("\n" + "="*70)
    print("TEST 1: AGREEMENT - KPI Declining + Negative Signals")
    print("="*70)
    
    # Create quantitative signals showing declining trend
    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "signal_source": "health_score_rollup",
            "account_id": 1001,
            "overall_health_score": 75.0,  # Healthy
            "health_status": "healthy",
            "week_number": 1,
            "month_year": "2026-01"
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "signal_source": "health_score_rollup",
            "account_id": 1001,
            "overall_health_score": 55.0,  # At-risk (declining)
            "health_status": "at-risk",
            "week_number": 2,
            "month_year": "2026-01"
        }),
        create_test_signal_data("kpi_metric", {
            "signal_type": "kpi_metric",
            "kpi_id": 101,
            "account_id": 1001,
            "kpi_parameter": "Daily Active Users",
            "health_status": "at-risk",  # Declining
            "health_score": 45.0
        })
    ]
    
    # Create qualitative signals with negative sentiment
    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "escalation",
            "signal_id": "1",
            "signal_source": "internal",
            "account_id": 1001,
            "sentiment": "negative",
            "content": "Customer frustrated with open tickets too long to resolve",
            "signal_date": "2026-01-15",
            "week_number": 2
        }),
        create_test_signal_data("account_note", {
            "signal_type": "account_note",
            "note_id": 201,
            "signal_source": "internal",
            "account_id": 1001,
            "sentiment": "negative",
            "text": "Support tickets taking 5+ days to resolve, customer escalating",
            "created_at": "2026-01-16T10:00:00"
        })
    ]
    
    # Create input
    input_data = SignalAnalystInput(
        account_id="1001",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 1",
        account_arr=50000.0,
        health_score=55.0,  # Current at-risk
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="churn_risk",
        time_horizon_days=60
    )
    
    # Calculate decision matrix (rule-based - default)
    result = calculate_decision_matrix(
        input_data=input_data,
        openai_api_key=None,  # Not needed for rule-based
        use_llm=False  # Use rule-based (default)
    )
    
    # Verify results
    print(f"\n✅ Result:")
    print(f"   Alignment: {result.alignment.value}")
    print(f"   Trend Direction: {result.trend_direction.value}")
    print(f"   Signal Sentiment: {result.signal_sentiment.value}")
    print(f"   KPI Health Trend: {result.kpi_health_trend}")
    print(f"   Signal Summary: {result.signal_summary}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Reasoning: {result.reasoning}")
    
    # Assertions
    assert result.alignment == DataAlignment.AGREEMENT, f"Expected AGREEMENT, got {result.alignment}"
    assert result.trend_direction == TrendDirection.DECLINING, f"Expected DECLINING, got {result.trend_direction}"
    assert result.signal_sentiment == SignalSentiment.NEGATIVE, f"Expected NEGATIVE, got {result.signal_sentiment}"
    assert result.confidence >= 0.80, f"Expected high confidence (>=0.80), got {result.confidence}"
    
    print("\n✅ TEST 1 PASSED: AGREEMENT scenario works correctly!")


def test_scenario_2_disagreement():
    """
    Scenario 2: DISAGREEMENT
    KPI trend: Declining (healthy → at-risk)
    Signal sentiment: Positive (customer happy)
    Expected: DISAGREEMENT with lower confidence
    """
    print("\n" + "="*70)
    print("TEST 2: DISAGREEMENT - KPI Declining + Positive Signals")
    print("="*70)
    
    # Create quantitative signals showing declining trend
    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1002,
            "overall_health_score": 72.0,  # Healthy
            "health_status": "healthy",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1002,
            "overall_health_score": 58.0,  # At-risk (declining)
            "health_status": "at-risk",
            "week_number": 2
        })
    ]
    
    # Create qualitative signals with positive sentiment
    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "meeting",
            "signal_id": "2",
            "signal_source": "internal",
            "account_id": 1002,
            "sentiment": "positive",
            "content": "Customer happy with overall product usage and support team responsiveness",
            "signal_date": "2026-01-15"
        }),
        create_test_signal_data("account_note", {
            "signal_type": "account_note",
            "note_id": 202,
            "account_id": 1002,
            "sentiment": "positive",
            "text": "QBR went well, customer expanding usage next quarter"
        })
    ]
    
    # Create input
    input_data = SignalAnalystInput(
        account_id="1002",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 2",
        account_arr=75000.0,
        health_score=58.0,  # Current at-risk
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="churn_risk",
        time_horizon_days=60
    )
    
    # Calculate decision matrix (rule-based - default)
    result = calculate_decision_matrix(
        input_data=input_data,
        openai_api_key=None,  # Not needed for rule-based
        use_llm=False  # Use rule-based (default)
    )
    
    # Verify results
    print(f"\n✅ Result:")
    print(f"   Alignment: {result.alignment.value}")
    print(f"   Trend Direction: {result.trend_direction.value}")
    print(f"   Signal Sentiment: {result.signal_sentiment.value}")
    print(f"   KPI Health Trend: {result.kpi_health_trend}")
    print(f"   Signal Summary: {result.signal_summary}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Reasoning: {result.reasoning}")
    
    # Assertions
    assert result.alignment == DataAlignment.DISAGREEMENT, f"Expected DISAGREEMENT, got {result.alignment}"
    assert result.trend_direction == TrendDirection.DECLINING, f"Expected DECLINING, got {result.trend_direction}"
    assert result.signal_sentiment == SignalSentiment.POSITIVE, f"Expected POSITIVE, got {result.signal_sentiment}"
    assert 0.50 <= result.confidence <= 0.70, f"Expected medium confidence (0.50-0.70), got {result.confidence}"
    assert "follow-up call" in result.reasoning.lower() or "investigation" in result.reasoning.lower(), "Should recommend follow-up"
    
    print("\n✅ TEST 2 PASSED: DISAGREEMENT scenario works correctly!")


def test_scenario_3_positive_alignment():
    """
    Scenario 3: POSITIVE_ALIGNMENT
    KPI trend: Improving (at-risk → healthy)
    Signal sentiment: Positive
    Expected: POSITIVE_ALIGNMENT with high confidence
    """
    print("\n" + "="*70)
    print("TEST 3: POSITIVE_ALIGNMENT - KPI Improving + Positive Signals")
    print("="*70)
    
    # Create quantitative signals showing improving trend
    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1003,
            "overall_health_score": 50.0,  # At-risk
            "health_status": "at-risk",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1003,
            "overall_health_score": 75.0,  # Healthy (improving)
            "health_status": "healthy",
            "week_number": 2
        })
    ]
    
    # Create qualitative signals with positive sentiment
    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "meeting",
            "signal_id": "3",
            "account_id": 1003,
            "sentiment": "positive",
            "content": "Customer very satisfied with recent improvements and support"
        })
    ]
    
    # Create input
    input_data = SignalAnalystInput(
        account_id="1003",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 3",
        account_arr=100000.0,
        health_score=75.0,  # Current healthy
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="expansion_opportunity",
        time_horizon_days=60
    )
    
    # Calculate decision matrix (rule-based - default)
    result = calculate_decision_matrix(
        input_data=input_data,
        openai_api_key=None,  # Not needed for rule-based
        use_llm=False  # Use rule-based (default)
    )
    
    # Verify results
    print(f"\n✅ Result:")
    print(f"   Alignment: {result.alignment.value}")
    print(f"   Trend Direction: {result.trend_direction.value}")
    print(f"   Signal Sentiment: {result.signal_sentiment.value}")
    print(f"   KPI Health Trend: {result.kpi_health_trend}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Reasoning: {result.reasoning}")
    
    # Assertions
    assert result.alignment == DataAlignment.POSITIVE_ALIGNMENT, f"Expected POSITIVE_ALIGNMENT, got {result.alignment}"
    assert result.trend_direction == TrendDirection.IMPROVING, f"Expected IMPROVING, got {result.trend_direction}"
    assert result.signal_sentiment == SignalSentiment.POSITIVE, f"Expected POSITIVE, got {result.signal_sentiment}"
    assert result.confidence >= 0.75, f"Expected high confidence (>=0.75), got {result.confidence}"
    assert "expansion" in result.reasoning.lower(), "Should mention expansion opportunity"
    
    print("\n✅ TEST 3 PASSED: POSITIVE_ALIGNMENT scenario works correctly!")


def test_scenario_4_neutral():
    """
    Scenario 4: NEUTRAL
    KPI trend: Stable
    Signal sentiment: Mixed/Neutral
    Expected: NEUTRAL
    """
    print("\n" + "="*70)
    print("TEST 4: NEUTRAL - KPI Stable + Mixed Signals")
    print("="*70)
    
    # Create quantitative signals showing stable trend
    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1004,
            "overall_health_score": 65.0,  # At-risk (stable)
            "health_status": "at-risk",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1004,
            "overall_health_score": 66.0,  # At-risk (stable, slight change)
            "health_status": "at-risk",
            "week_number": 2
        })
    ]
    
    # Create qualitative signals with mixed sentiment
    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "email",
            "signal_id": "4",
            "account_id": 1004,
            "sentiment": "positive",
            "content": "Product working well"
        }),
        create_test_signal_data("qualitative_signal", {
            "signal_type": "ticket",
            "signal_id": "5",
            "account_id": 1004,
            "sentiment": "negative",
            "content": "Minor feature request"
        })
    ]
    
    # Create input
    input_data = SignalAnalystInput(
        account_id="1004",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 4",
        account_arr=60000.0,
        health_score=65.0,  # Current at-risk
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="health_analysis",
        time_horizon_days=60
    )
    
    # Calculate decision matrix (rule-based - default)
    result = calculate_decision_matrix(
        input_data=input_data,
        openai_api_key=None,  # Not needed for rule-based
        use_llm=False  # Use rule-based (default)
    )
    
    # Verify results
    print(f"\n✅ Result:")
    print(f"   Alignment: {result.alignment.value}")
    print(f"   Trend Direction: {result.trend_direction.value}")
    print(f"   Signal Sentiment: {result.signal_sentiment.value}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Reasoning: {result.reasoning}")
    
    # Assertions
    assert result.alignment == DataAlignment.NEUTRAL, f"Expected NEUTRAL, got {result.alignment}"
    assert result.trend_direction == TrendDirection.STABLE, f"Expected STABLE, got {result.trend_direction}"
    assert result.signal_sentiment in [SignalSentiment.MIXED, SignalSentiment.NEUTRAL], f"Expected MIXED/NEUTRAL, got {result.signal_sentiment}"
    
    print("\n✅ TEST 4 PASSED: NEUTRAL scenario works correctly!")


def test_scenario_5_insufficient_data():
    """
    Scenario 5: INSUFFICIENT_DATA
    No KPI trend data available
    Expected: INSUFFICIENT_DATA with low confidence
    """
    print("\n" + "="*70)
    print("TEST 5: INSUFFICIENT_DATA - No KPI Trend Data")
    print("="*70)
    
    # Create input with no quantitative signals
    input_data = SignalAnalystInput(
        account_id="1005",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 5",
        account_arr=30000.0,
        health_score=None,  # No health score
        quantitative_signals=[],  # No quantitative signals
        qualitative_signals=[
            create_test_signal_data("qualitative_signal", {
                "signal_type": "email",
                "signal_id": "6",
                "account_id": 1005,
                "sentiment": "neutral",
                "content": "General inquiry"
            })
        ],
        historical_patterns=[],
        analysis_type="comprehensive",
        time_horizon_days=60
    )
    
    # Calculate decision matrix (rule-based - default)
    result = calculate_decision_matrix(
        input_data=input_data,
        openai_api_key=None,  # Not needed for rule-based
        use_llm=False  # Use rule-based (default)
    )
    
    # Verify results
    print(f"\n✅ Result:")
    print(f"   Alignment: {result.alignment.value}")
    print(f"   Trend Direction: {result.trend_direction.value}")
    print(f"   Signal Sentiment: {result.signal_sentiment.value}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Reasoning: {result.reasoning}")
    
    # Assertions
    assert result.alignment == DataAlignment.INSUFFICIENT_DATA, f"Expected INSUFFICIENT_DATA, got {result.alignment}"
    assert result.trend_direction == TrendDirection.UNKNOWN, f"Expected UNKNOWN, got {result.trend_direction}"
    assert result.confidence <= 0.40, f"Expected low confidence (<=0.40), got {result.confidence}"
    assert "insufficient" in result.reasoning.lower() or "more data" in result.reasoning.lower(), "Should indicate need for more data"
    
    print("\n✅ TEST 5 PASSED: INSUFFICIENT_DATA scenario works correctly!")


def test_edge_case_mixed_signals():
    """
    Edge Case: Mixed signals with declining KPI
    KPI trend: Declining
    Signal sentiment: Mixed (both positive and negative)
    Expected: DISAGREEMENT (mixed signals with declining KPI)
    """
    print("\n" + "="*70)
    print("TEST 6: EDGE CASE - Declining KPI + Mixed Signals")
    print("="*70)
    
    # Create quantitative signals showing declining trend
    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1006,
            "overall_health_score": 70.0,  # Healthy
            "health_status": "healthy",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1006,
            "overall_health_score": 55.0,  # At-risk (declining)
            "health_status": "at-risk",
            "week_number": 2
        })
    ]
    
    # Create qualitative signals with mixed sentiment
    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "meeting",
            "signal_id": "7",
            "account_id": 1006,
            "sentiment": "positive",
            "content": "Product usage is good"
        }),
        create_test_signal_data("qualitative_signal", {
            "signal_type": "ticket",
            "signal_id": "8",
            "account_id": 1006,
            "sentiment": "negative",
            "content": "Support response time is slow"
        })
    ]
    
    # Create input
    input_data = SignalAnalystInput(
        account_id="1006",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 6",
        account_arr=80000.0,
        health_score=55.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="churn_risk",
        time_horizon_days=60
    )
    
    # Calculate decision matrix (rule-based - default)
    result = calculate_decision_matrix(
        input_data=input_data,
        openai_api_key=None,  # Not needed for rule-based
        use_llm=False  # Use rule-based (default)
    )
    
    # Verify results
    print(f"\n✅ Result:")
    print(f"   Alignment: {result.alignment.value}")
    print(f"   Trend Direction: {result.trend_direction.value}")
    print(f"   Signal Sentiment: {result.signal_sentiment.value}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Reasoning: {result.reasoning}")
    
    # Assertions
    assert result.alignment == DataAlignment.DISAGREEMENT, f"Expected DISAGREEMENT, got {result.alignment}"
    assert result.trend_direction == TrendDirection.DECLINING, f"Expected DECLINING, got {result.trend_direction}"
    assert result.signal_sentiment == SignalSentiment.MIXED, f"Expected MIXED, got {result.signal_sentiment}"
    
    print("\n✅ TEST 6 PASSED: Edge case (mixed signals) works correctly!")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("DECISION MATRIX TEST SUITE")
    print("="*70)
    print("\nTesting all scenarios of the decision matrix implementation...")
    
    try:
        # Run all test scenarios
        test_scenario_1_agreement()
        test_scenario_2_disagreement()
        test_scenario_3_positive_alignment()
        test_scenario_4_neutral()
        test_scenario_5_insufficient_data()
        test_edge_case_mixed_signals()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print("\nSummary:")
        print("  ✅ Test 1: AGREEMENT scenario")
        print("  ✅ Test 2: DISAGREEMENT scenario")
        print("  ✅ Test 3: POSITIVE_ALIGNMENT scenario")
        print("  ✅ Test 4: NEUTRAL scenario")
        print("  ✅ Test 5: INSUFFICIENT_DATA scenario")
        print("  ✅ Test 6: Edge case (mixed signals)")
        print("\n🎉 Decision Matrix implementation verified for all scenarios!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
