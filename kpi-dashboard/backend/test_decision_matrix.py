#!/usr/bin/env python3
"""
Test Decision Matrix Implementation (v2)

Tests all scenarios of the enhanced decision matrix:
1. AGREEMENT: KPI declining + negative signals
2. DISAGREEMENT: KPI declining + positive signals
3. NEUTRAL: KPI stable + neutral signals
4. POSITIVE_ALIGNMENT: KPI improving + positive signals
5. INSUFFICIENT_DATA: No data at all (brand-new account)
6. DATA_QUALITY_ISSUE: Some data but not enough for trend (#4)
7. DECLINING x MIXED → AGREEMENT (partial) (#6)
8. STABLE x POSITIVE → POSITIVE_ALIGNMENT (weak) (#6)
9. IMPROVING x NEUTRAL → POSITIVE_ALIGNMENT (weak) (#6)
10. Velocity detection (accelerating/decelerating) (#8)
11. Severity weighting (escalation outweighs meeting) (#1)
12. Urgency mapping (#2)
13. External signal confidence boost (#7)

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
    TrendVelocity,
    SignalSentiment,
    Urgency,
)
import os
from openai_key_utils import get_openai_api_key

def create_test_signal_data(signal_type: str, payload: dict, similarity: float = 0.85) -> SignalData:
    """Helper to create SignalData objects"""
    return SignalData(similarity=similarity, payload=payload)


def _print_result(result, label=""):
    """Helper to print DecisionMatrixResult"""
    d = result.to_dict()
    print(f"\n  Result{f' ({label})' if label else ''}:")
    for k, v in d.items():
        if k == 'reasoning':
            print(f"   {k}: {str(v)[:200]}...")
        elif isinstance(v, dict):
            print(f"   {k}: {v}")
        else:
            print(f"   {k}: {v}")


# ── Core Scenario Tests (updated for v2) ──────────────────────────────────

def test_scenario_1_agreement():
    """
    Scenario 1: AGREEMENT
    KPI trend: Declining (healthy -> at-risk)
    Signal sentiment: Negative (customer frustrated)
    Expected: AGREEMENT with high confidence, IMMEDIATE urgency
    """
    print("\n" + "="*70)
    print("TEST 1: AGREEMENT - KPI Declining + Negative Signals")
    print("="*70)

    today = datetime.utcnow().strftime('%Y-%m-%d')

    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "signal_source": "health_score_rollup",
            "account_id": 1001,
            "overall_health_score": 75.0,
            "health_status": "healthy",
            "week_number": 1,
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "signal_source": "health_score_rollup",
            "account_id": 1001,
            "overall_health_score": 55.0,
            "health_status": "at-risk",
            "week_number": 2,
        }),
    ]

    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "escalation",
            "signal_id": "1",
            "signal_source": "internal",
            "account_id": 1001,
            "sentiment": "negative",
            "content": "Customer frustrated with open tickets too long to resolve",
            "date": today,
        }),
        create_test_signal_data("account_note", {
            "signal_type": "account_note",
            "note_id": 201,
            "signal_source": "internal",
            "account_id": 1001,
            "sentiment": "negative",
            "text": "Support tickets taking 5+ days to resolve, customer escalating",
            "date": today,
        })
    ]

    input_data = SignalAnalystInput(
        account_id="1001",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 1",
        account_arr=50000.0,
        health_score=55.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="churn_risk",
        time_horizon_days=60
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    assert result.alignment == DataAlignment.AGREEMENT, f"Expected AGREEMENT, got {result.alignment}"
    assert result.trend_direction == TrendDirection.DECLINING, f"Expected DECLINING, got {result.trend_direction}"
    assert result.signal_sentiment == SignalSentiment.NEGATIVE, f"Expected NEGATIVE, got {result.signal_sentiment}"
    assert result.confidence >= 0.75, f"Expected high confidence (>=0.75), got {result.confidence}"
    assert result.urgency == Urgency.IMMEDIATE, f"Expected IMMEDIATE urgency, got {result.urgency}"

    print("\n  TEST 1 PASSED")


def test_scenario_2_disagreement():
    """
    Scenario 2: DISAGREEMENT
    KPI trend: Declining (healthy -> at-risk)
    Signal sentiment: Positive (customer happy)
    Expected: DISAGREEMENT with lower confidence, HIGH urgency
    """
    print("\n" + "="*70)
    print("TEST 2: DISAGREEMENT - KPI Declining + Positive Signals")
    print("="*70)

    today = datetime.utcnow().strftime('%Y-%m-%d')

    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1002,
            "overall_health_score": 72.0,
            "health_status": "healthy",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1002,
            "overall_health_score": 58.0,
            "health_status": "at-risk",
            "week_number": 2
        })
    ]

    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "meeting",
            "signal_id": "2",
            "signal_source": "internal",
            "account_id": 1002,
            "sentiment": "positive",
            "content": "Customer happy with overall product usage and support team responsiveness",
            "date": today,
        }),
        create_test_signal_data("account_note", {
            "signal_type": "account_note",
            "note_id": 202,
            "account_id": 1002,
            "sentiment": "positive",
            "text": "QBR went well, customer expanding usage next quarter",
            "date": today,
        })
    ]

    input_data = SignalAnalystInput(
        account_id="1002",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 2",
        account_arr=75000.0,
        health_score=58.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="churn_risk",
        time_horizon_days=60
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    assert result.alignment == DataAlignment.DISAGREEMENT, f"Expected DISAGREEMENT, got {result.alignment}"
    assert result.trend_direction == TrendDirection.DECLINING, f"Expected DECLINING, got {result.trend_direction}"
    assert result.signal_sentiment == SignalSentiment.POSITIVE, f"Expected POSITIVE, got {result.signal_sentiment}"
    assert 0.45 <= result.confidence <= 0.75, f"Expected medium confidence (0.45-0.75), got {result.confidence}"
    assert result.urgency == Urgency.HIGH, f"Expected HIGH urgency, got {result.urgency}"

    print("\n  TEST 2 PASSED")


def test_scenario_3_positive_alignment():
    """
    Scenario 3: POSITIVE_ALIGNMENT
    KPI trend: Improving (at-risk -> healthy)
    Signal sentiment: Positive
    Expected: POSITIVE_ALIGNMENT with high confidence, LOW urgency
    """
    print("\n" + "="*70)
    print("TEST 3: POSITIVE_ALIGNMENT - KPI Improving + Positive Signals")
    print("="*70)

    today = datetime.utcnow().strftime('%Y-%m-%d')

    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1003,
            "overall_health_score": 50.0,
            "health_status": "at-risk",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1003,
            "overall_health_score": 75.0,
            "health_status": "healthy",
            "week_number": 2
        })
    ]

    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "meeting",
            "signal_id": "3",
            "account_id": 1003,
            "sentiment": "positive",
            "content": "Customer very satisfied with recent improvements and support",
            "date": today,
        })
    ]

    input_data = SignalAnalystInput(
        account_id="1003",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 3",
        account_arr=100000.0,
        health_score=75.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="expansion_opportunity",
        time_horizon_days=60
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    assert result.alignment == DataAlignment.POSITIVE_ALIGNMENT, f"Expected POSITIVE_ALIGNMENT, got {result.alignment}"
    assert result.trend_direction == TrendDirection.IMPROVING, f"Expected IMPROVING, got {result.trend_direction}"
    assert result.signal_sentiment == SignalSentiment.POSITIVE, f"Expected POSITIVE, got {result.signal_sentiment}"
    assert result.confidence >= 0.70, f"Expected high confidence (>=0.70), got {result.confidence}"
    assert result.urgency == Urgency.LOW, f"Expected LOW urgency, got {result.urgency}"

    print("\n  TEST 3 PASSED")


def test_scenario_4_neutral():
    """
    Scenario 4: NEUTRAL
    KPI trend: Stable
    Signal sentiment: Neutral (equal weighted signals cancel out)
    Expected: NEUTRAL
    """
    print("\n" + "="*70)
    print("TEST 4: NEUTRAL - KPI Stable + Neutral Signals")
    print("="*70)

    today = datetime.utcnow().strftime('%Y-%m-%d')

    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1004,
            "overall_health_score": 65.0,
            "health_status": "at-risk",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1004,
            "overall_health_score": 66.0,
            "health_status": "at-risk",
            "week_number": 2
        })
    ]

    # Use equal-weight signal types with neutral sentiment to get true NEUTRAL
    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "email",
            "signal_id": "4",
            "account_id": 1004,
            "sentiment": "neutral",
            "content": "General status update, no issues reported",
            "date": today,
        }),
        create_test_signal_data("qualitative_signal", {
            "signal_type": "meeting",
            "signal_id": "5",
            "account_id": 1004,
            "sentiment": "neutral",
            "content": "Routine check-in, everything on track",
            "date": today,
        })
    ]

    input_data = SignalAnalystInput(
        account_id="1004",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 4",
        account_arr=60000.0,
        health_score=65.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="health_analysis",
        time_horizon_days=60
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    assert result.alignment == DataAlignment.NEUTRAL, f"Expected NEUTRAL, got {result.alignment}"
    assert result.trend_direction == TrendDirection.STABLE, f"Expected STABLE, got {result.trend_direction}"
    assert result.signal_sentiment == SignalSentiment.NEUTRAL, f"Expected NEUTRAL, got {result.signal_sentiment}"
    assert result.urgency == Urgency.LOW, f"Expected LOW urgency, got {result.urgency}"

    print("\n  TEST 4 PASSED")


def test_scenario_5_insufficient_data():
    """
    Scenario 5: INSUFFICIENT_DATA
    Brand-new account — no KPI data AND no qual signals
    Expected: INSUFFICIENT_DATA with low confidence, NONE urgency
    """
    print("\n" + "="*70)
    print("TEST 5: INSUFFICIENT_DATA - Brand-New Account, No Data")
    print("="*70)

    input_data = SignalAnalystInput(
        account_id="1005",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 5",
        account_arr=30000.0,
        health_score=None,
        quantitative_signals=[],
        qualitative_signals=[],
        historical_patterns=[],
        analysis_type="comprehensive",
        time_horizon_days=60
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    assert result.alignment == DataAlignment.INSUFFICIENT_DATA, f"Expected INSUFFICIENT_DATA, got {result.alignment}"
    assert result.trend_direction == TrendDirection.UNKNOWN, f"Expected UNKNOWN, got {result.trend_direction}"
    assert result.confidence <= 0.30, f"Expected very low confidence (<=0.30), got {result.confidence}"
    assert result.urgency == Urgency.NONE, f"Expected NONE urgency, got {result.urgency}"

    print("\n  TEST 5 PASSED")


# ── New v2 Scenario Tests ─────────────────────────────────────────────────

def test_scenario_6_data_quality_issue():
    """
    Scenario 6: DATA_QUALITY_ISSUE (#4)
    Has qualitative data but no KPI trend — investigate data gaps
    Expected: DATA_QUALITY_ISSUE with low confidence, MEDIUM urgency
    """
    print("\n" + "="*70)
    print("TEST 6: DATA_QUALITY_ISSUE - Has Qual Data But No KPI Trend")
    print("="*70)

    input_data = SignalAnalystInput(
        account_id="1006",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 6",
        account_arr=40000.0,
        health_score=None,
        quantitative_signals=[],
        qualitative_signals=[
            create_test_signal_data("qualitative_signal", {
                "signal_type": "email",
                "signal_id": "6",
                "account_id": 1006,
                "sentiment": "neutral",
                "content": "General inquiry about product features"
            })
        ],
        historical_patterns=[],
        analysis_type="comprehensive",
        time_horizon_days=60
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    assert result.alignment == DataAlignment.DATA_QUALITY_ISSUE, f"Expected DATA_QUALITY_ISSUE, got {result.alignment}"
    assert result.confidence <= 0.40, f"Expected low confidence (<=0.40), got {result.confidence}"
    assert result.urgency == Urgency.MEDIUM, f"Expected MEDIUM urgency, got {result.urgency}"
    assert "data" in result.reasoning.lower(), "Should mention data gaps"

    print("\n  TEST 6 PASSED")


def test_scenario_7_declining_mixed_agreement_partial():
    """
    Scenario 7: DECLINING x MIXED → AGREEMENT (partial) (#6)
    KPI declining + mixed signals = partial agreement, the negative signals align with KPI
    Note: With severity weighting, if negative has higher weight, sentiment may flip to NEGATIVE
    """
    print("\n" + "="*70)
    print("TEST 7: DECLINING x MIXED → AGREEMENT (partial)")
    print("="*70)

    today = datetime.utcnow().strftime('%Y-%m-%d')

    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1007,
            "overall_health_score": 70.0,
            "health_status": "healthy",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1007,
            "overall_health_score": 55.0,
            "health_status": "at-risk",
            "week_number": 2
        })
    ]

    # Use equal-weight signal types so MIXED sentiment survives severity weighting
    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "email",
            "signal_id": "7",
            "account_id": 1007,
            "sentiment": "positive",
            "content": "Product usage is good, team is satisfied",
            "date": today,
        }),
        create_test_signal_data("qualitative_signal", {
            "signal_type": "email",
            "signal_id": "8",
            "account_id": 1007,
            "sentiment": "negative",
            "content": "Support response time is slow",
            "date": today,
        })
    ]

    input_data = SignalAnalystInput(
        account_id="1007",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 7",
        account_arr=80000.0,
        health_score=55.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="churn_risk",
        time_horizon_days=60
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    # With equal-weight types, MIXED sentiment survives → DECLINING x MIXED → AGREEMENT (partial)
    assert result.alignment == DataAlignment.AGREEMENT, f"Expected AGREEMENT, got {result.alignment}"
    assert result.trend_direction == TrendDirection.DECLINING, f"Expected DECLINING, got {result.trend_direction}"
    assert result.signal_sentiment == SignalSentiment.MIXED, f"Expected MIXED, got {result.signal_sentiment}"
    assert result.urgency == Urgency.IMMEDIATE, f"Expected IMMEDIATE urgency, got {result.urgency}"
    assert "partial" in result.reasoning.lower(), "Should mention partial agreement"

    print("\n  TEST 7 PASSED")


def test_scenario_8_stable_positive_alignment():
    """
    Scenario 8: STABLE x POSITIVE → POSITIVE_ALIGNMENT (weak) (#6)
    Positive sentiment while metrics are stable is a leading indicator of expansion
    """
    print("\n" + "="*70)
    print("TEST 8: STABLE x POSITIVE → POSITIVE_ALIGNMENT (weak)")
    print("="*70)

    today = datetime.utcnow().strftime('%Y-%m-%d')

    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1008,
            "overall_health_score": 75.0,
            "health_status": "healthy",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1008,
            "overall_health_score": 78.0,
            "health_status": "healthy",
            "week_number": 2
        })
    ]

    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "meeting",
            "signal_id": "9",
            "account_id": 1008,
            "sentiment": "positive",
            "content": "Customer very happy with product and expanding usage",
            "date": today,
        }),
        create_test_signal_data("qualitative_signal", {
            "signal_type": "email",
            "signal_id": "10",
            "account_id": 1008,
            "sentiment": "positive",
            "content": "Great support experience, exceeded expectations",
            "date": today,
        })
    ]

    input_data = SignalAnalystInput(
        account_id="1008",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 8",
        account_arr=90000.0,
        health_score=78.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="expansion_opportunity",
        time_horizon_days=60
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    assert result.alignment == DataAlignment.POSITIVE_ALIGNMENT, f"Expected POSITIVE_ALIGNMENT, got {result.alignment}"
    assert result.trend_direction == TrendDirection.STABLE, f"Expected STABLE, got {result.trend_direction}"
    assert result.signal_sentiment == SignalSentiment.POSITIVE, f"Expected POSITIVE, got {result.signal_sentiment}"
    assert result.urgency == Urgency.LOW, f"Expected LOW urgency, got {result.urgency}"
    assert "expansion" in result.reasoning.lower() or "leading indicator" in result.reasoning.lower(), "Should mention expansion potential"

    print("\n  TEST 8 PASSED")


def test_scenario_9_improving_neutral_positive_alignment():
    """
    Scenario 9: IMPROVING x NEUTRAL → POSITIVE_ALIGNMENT (weak) (#6)
    Improving KPIs with neutral sentiment — absence of negative is good
    """
    print("\n" + "="*70)
    print("TEST 9: IMPROVING x NEUTRAL → POSITIVE_ALIGNMENT (weak)")
    print("="*70)

    today = datetime.utcnow().strftime('%Y-%m-%d')

    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1009,
            "overall_health_score": 55.0,
            "health_status": "at-risk",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1009,
            "overall_health_score": 72.0,
            "health_status": "healthy",
            "week_number": 2
        })
    ]

    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "email",
            "signal_id": "11",
            "account_id": 1009,
            "sentiment": "neutral",
            "content": "Routine status update, nothing to report",
            "date": today,
        })
    ]

    input_data = SignalAnalystInput(
        account_id="1009",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 9",
        account_arr=55000.0,
        health_score=72.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="health_analysis",
        time_horizon_days=60
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    assert result.alignment == DataAlignment.POSITIVE_ALIGNMENT, f"Expected POSITIVE_ALIGNMENT, got {result.alignment}"
    assert result.trend_direction == TrendDirection.IMPROVING, f"Expected IMPROVING, got {result.trend_direction}"
    assert result.signal_sentiment == SignalSentiment.NEUTRAL, f"Expected NEUTRAL, got {result.signal_sentiment}"
    assert "weak" in result.reasoning.lower(), "Should indicate weak positive alignment"

    print("\n  TEST 9 PASSED")


def test_scenario_10_velocity_accelerating():
    """
    Scenario 10: Velocity detection - accelerating decline (#8)
    Health scores: 80 → 65 → 40 (second-half drop > first-half drop → accelerating)
    """
    print("\n" + "="*70)
    print("TEST 10: VELOCITY - Accelerating Decline")
    print("="*70)

    today = datetime.utcnow().strftime('%Y-%m-%d')

    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1010,
            "overall_health_score": 80.0,
            "health_status": "healthy",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1010,
            "overall_health_score": 65.0,
            "health_status": "at-risk",
            "week_number": 2
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1010,
            "overall_health_score": 30.0,
            "health_status": "critical",
            "week_number": 3
        }),
    ]

    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "escalation",
            "signal_id": "12",
            "account_id": 1010,
            "sentiment": "negative",
            "content": "Urgent escalation - multiple systems down, customer threatening to leave",
            "date": today,
        })
    ]

    input_data = SignalAnalystInput(
        account_id="1010",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 10",
        account_arr=200000.0,
        health_score=30.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="churn_risk",
        time_horizon_days=30
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    assert result.alignment == DataAlignment.AGREEMENT, f"Expected AGREEMENT, got {result.alignment}"
    assert result.trend_velocity == TrendVelocity.ACCELERATING, f"Expected ACCELERATING, got {result.trend_velocity}"
    assert result.urgency == Urgency.IMMEDIATE, f"Expected IMMEDIATE urgency, got {result.urgency}"
    # Accelerating should boost confidence
    assert result.confidence >= 0.85, f"Expected very high confidence (>=0.85), got {result.confidence}"
    assert "accelerat" in result.reasoning.lower(), "Should mention acceleration"

    print("\n  TEST 10 PASSED")


def test_scenario_11_severity_weighting():
    """
    Scenario 11: Severity weighting (#1)
    1 escalation (negative, weight=3.0) should outweigh 2 meetings (positive, weight=1.0 each)
    """
    print("\n" + "="*70)
    print("TEST 11: SEVERITY WEIGHTING - Escalation Outweighs Meetings")
    print("="*70)

    today = datetime.utcnow().strftime('%Y-%m-%d')

    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1011,
            "overall_health_score": 60.0,
            "health_status": "at-risk",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1011,
            "overall_health_score": 60.0,
            "health_status": "at-risk",
            "week_number": 2
        }),
    ]

    qualitative_signals = [
        # 1 escalation (negative, weight=3.0)
        create_test_signal_data("qualitative_signal", {
            "signal_type": "escalation",
            "signal_id": "13",
            "account_id": 1011,
            "sentiment": "negative",
            "content": "Executive escalation - critical integration failure",
            "date": today,
        }),
        # 2 meetings (positive, weight=1.0 each)
        create_test_signal_data("qualitative_signal", {
            "signal_type": "meeting",
            "signal_id": "14",
            "account_id": 1011,
            "sentiment": "positive",
            "content": "Regular check-in went well",
            "date": today,
        }),
        create_test_signal_data("qualitative_signal", {
            "signal_type": "meeting",
            "signal_id": "15",
            "account_id": 1011,
            "sentiment": "positive",
            "content": "Product demo was successful",
            "date": today,
        }),
    ]

    input_data = SignalAnalystInput(
        account_id="1011",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 11",
        account_arr=120000.0,
        health_score=60.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="health_analysis",
        time_horizon_days=60
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    # Escalation (3.0) > 2 meetings (1.0+1.0) → NEGATIVE sentiment wins
    assert result.signal_sentiment == SignalSentiment.NEGATIVE, f"Expected NEGATIVE (escalation outweighs meetings), got {result.signal_sentiment}"
    # Verify sentiment_details show the weighting
    assert result.sentiment_details is not None, "Expected sentiment_details to be populated"
    assert result.sentiment_details['negative_weight'] > result.sentiment_details['positive_weight'], \
        "Expected negative weight > positive weight due to escalation severity"

    print("\n  TEST 11 PASSED")


def test_scenario_12_external_signal_boost():
    """
    Scenario 12: External signal confidence boost (#7)
    External signals (NPS, escalation) should boost confidence vs internal-only signals
    """
    print("\n" + "="*70)
    print("TEST 12: EXTERNAL SIGNAL BOOST")
    print("="*70)

    today = datetime.utcnow().strftime('%Y-%m-%d')

    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1012,
            "overall_health_score": 72.0,
            "health_status": "healthy",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1012,
            "overall_health_score": 55.0,
            "health_status": "at-risk",
            "week_number": 2
        }),
    ]

    # All external signals (escalation, NPS)
    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "escalation",
            "signal_id": "16",
            "account_id": 1012,
            "sentiment": "negative",
            "content": "VP of Engineering escalated critical bug",
            "date": today,
        }),
        create_test_signal_data("qualitative_signal", {
            "signal_type": "nps_response",
            "signal_id": "17",
            "account_id": 1012,
            "sentiment": "negative",
            "content": "NPS score dropped to 3/10 - detractor",
            "date": today,
        }),
    ]

    input_data = SignalAnalystInput(
        account_id="1012",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 12",
        account_arr=150000.0,
        health_score=55.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="churn_risk",
        time_horizon_days=60
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    # All external signals → external_signal_ratio = 1.0 → +0.10 boost
    assert result.external_signal_ratio >= 0.5, f"Expected high external ratio, got {result.external_signal_ratio}"
    assert result.confidence >= 0.85, f"Expected boosted confidence (>=0.85), got {result.confidence}"
    assert "external" in result.reasoning.lower(), "Should mention external signals"

    print("\n  TEST 12 PASSED")


def test_scenario_13_temporal_decay():
    """
    Scenario 13: Temporal decay (#3)
    Recent negative signal should outweigh old positive signals even with same severity
    """
    print("\n" + "="*70)
    print("TEST 13: TEMPORAL DECAY - Recent Signals Weight More")
    print("="*70)

    today = datetime.utcnow().strftime('%Y-%m-%d')
    old_date = (datetime.utcnow() - timedelta(days=120)).strftime('%Y-%m-%d')  # ~4 months ago

    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1013,
            "overall_health_score": 65.0,
            "health_status": "at-risk",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1013,
            "overall_health_score": 65.0,
            "health_status": "at-risk",
            "week_number": 2
        }),
    ]

    qualitative_signals = [
        # Old positive signal (120 days ago, decay ~ 0.23)
        create_test_signal_data("qualitative_signal", {
            "signal_type": "email",
            "signal_id": "18",
            "account_id": 1013,
            "sentiment": "positive",
            "content": "Everything is going great, love the product",
            "date": old_date,
        }),
        # Recent negative signal (today, decay ~ 1.0)
        create_test_signal_data("qualitative_signal", {
            "signal_type": "email",
            "signal_id": "19",
            "account_id": 1013,
            "sentiment": "negative",
            "content": "Frustrated with recent service degradation",
            "date": today,
        }),
    ]

    input_data = SignalAnalystInput(
        account_id="1013",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 13",
        account_arr=70000.0,
        health_score=65.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="health_analysis",
        time_horizon_days=60
    )

    result = calculate_decision_matrix(input_data=input_data, use_llm=False)
    _print_result(result)

    # Recent negative should outweigh old positive due to temporal decay
    assert result.signal_sentiment == SignalSentiment.NEGATIVE, \
        f"Expected NEGATIVE (recent signal dominates with decay), got {result.signal_sentiment}"
    # Verify the negative weight is larger
    details = result.sentiment_details
    assert details['negative_weight'] > details['positive_weight'], \
        f"Expected neg_weight > pos_weight due to decay: neg={details['negative_weight']}, pos={details['positive_weight']}"

    print("\n  TEST 13 PASSED")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("DECISION MATRIX v2 TEST SUITE")
    print("="*70)
    print("\nTesting all scenarios including v2 enhancements...")

    try:
        # Core scenarios (updated for v2)
        test_scenario_1_agreement()
        test_scenario_2_disagreement()
        test_scenario_3_positive_alignment()
        test_scenario_4_neutral()
        test_scenario_5_insufficient_data()

        # New v2 scenarios
        test_scenario_6_data_quality_issue()
        test_scenario_7_declining_mixed_agreement_partial()
        test_scenario_8_stable_positive_alignment()
        test_scenario_9_improving_neutral_positive_alignment()
        test_scenario_10_velocity_accelerating()
        test_scenario_11_severity_weighting()
        test_scenario_12_external_signal_boost()
        test_scenario_13_temporal_decay()

        print("\n" + "="*70)
        print("ALL 13 TESTS PASSED!")
        print("="*70)
        print("\nSummary:")
        print("  Core Scenarios:")
        print("    TEST 1:  AGREEMENT scenario")
        print("    TEST 2:  DISAGREEMENT scenario")
        print("    TEST 3:  POSITIVE_ALIGNMENT scenario")
        print("    TEST 4:  NEUTRAL scenario")
        print("    TEST 5:  INSUFFICIENT_DATA (brand-new account)")
        print("  v2 Enhancements:")
        print("    TEST 6:  DATA_QUALITY_ISSUE (#4 split)")
        print("    TEST 7:  DECLINING x MIXED → AGREEMENT partial (#6)")
        print("    TEST 8:  STABLE x POSITIVE → POSITIVE_ALIGNMENT weak (#6)")
        print("    TEST 9:  IMPROVING x NEUTRAL → POSITIVE_ALIGNMENT weak (#6)")
        print("    TEST 10: VELOCITY accelerating decline (#8)")
        print("    TEST 11: SEVERITY WEIGHTING escalation > meetings (#1)")
        print("    TEST 12: EXTERNAL SIGNAL confidence boost (#7)")
        print("    TEST 13: TEMPORAL DECAY recent > old (#3)")
        print("\n  Decision Matrix v2 implementation verified!")

    except AssertionError as e:
        print(f"\n  TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
