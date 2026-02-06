#!/usr/bin/env python3
"""
Decision Matrix Comparison Test

Compares rule-based vs LLM-based decision matrix implementations
to show differences in reasoning, confidence, and alignment detection.
"""

import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from agents.models import SignalAnalystInput, SignalData
from agents.decision_matrix import (
    calculate_decision_matrix,
    DataAlignment,
    TrendDirection,
    SignalSentiment
)
from openai_key_utils import get_openai_api_key
from app_v3_minimal import app

def create_test_signal_data(signal_type: str, payload: dict, similarity: float = 0.85) -> SignalData:
    """Helper to create SignalData objects"""
    return SignalData(similarity=similarity, payload=payload)


def compare_scenario(scenario_name: str, input_data: SignalAnalystInput, openai_api_key: str = None):
    """
    Compare rule-based vs LLM-based decision matrix for a scenario
    """
    print("\n" + "="*80)
    print(f"SCENARIO: {scenario_name}")
    print("="*80)
    
    # Test rule-based
    print("\n📊 RULE-BASED IMPLEMENTATION:")
    print("-" * 80)
    try:
        rule_result = calculate_decision_matrix(
            input_data=input_data,
            openai_api_key=None,
            use_llm=False
        )
        print(f"   Alignment: {rule_result.alignment.value}")
        print(f"   Trend Direction: {rule_result.trend_direction.value}")
        print(f"   Signal Sentiment: {rule_result.signal_sentiment.value}")
        print(f"   KPI Health Trend: {rule_result.kpi_health_trend}")
        print(f"   Signal Summary: {rule_result.signal_summary[:100]}...")
        print(f"   Confidence: {rule_result.confidence:.2f}")
        print(f"   Reasoning: {rule_result.reasoning[:200]}...")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        rule_result = None
    
    # Test LLM-based
    print("\n🤖 LLM-BASED IMPLEMENTATION:")
    print("-" * 80)
    try:
        if not openai_api_key:
            print("   ⚠️  OpenAI API key not available, skipping LLM test")
            llm_result = None
        else:
            llm_result = calculate_decision_matrix(
                input_data=input_data,
                openai_api_key=openai_api_key,
                use_llm=True
            )
            print(f"   Alignment: {llm_result.alignment.value}")
            print(f"   Trend Direction: {llm_result.trend_direction.value}")
            print(f"   Signal Sentiment: {llm_result.signal_sentiment.value}")
            print(f"   KPI Health Trend: {llm_result.kpi_health_trend}")
            print(f"   Signal Summary: {llm_result.signal_summary[:100]}...")
            print(f"   Confidence: {llm_result.confidence:.2f}")
            print(f"   Reasoning: {llm_result.reasoning[:300]}...")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        llm_result = None
    
    # Compare results
    if rule_result and llm_result:
        print("\n🔍 COMPARISON:")
        print("-" * 80)
        
        # Alignment comparison
        alignment_match = rule_result.alignment == llm_result.alignment
        print(f"   Alignment Match: {'✅ SAME' if alignment_match else '⚠️  DIFFERENT'}")
        if not alignment_match:
            print(f"      Rule-based: {rule_result.alignment.value}")
            print(f"      LLM-based:  {llm_result.alignment.value}")
        
        # Confidence comparison
        confidence_diff = abs(rule_result.confidence - llm_result.confidence)
        print(f"   Confidence Difference: {confidence_diff:.2f}")
        print(f"      Rule-based: {rule_result.confidence:.2f}")
        print(f"      LLM-based:  {llm_result.confidence:.2f}")
        if confidence_diff > 0.10:
            print(f"      ⚠️  Significant difference (>0.10)")
        
        # Reasoning comparison
        print(f"   Reasoning Length:")
        print(f"      Rule-based: {len(rule_result.reasoning)} chars")
        print(f"      LLM-based:  {len(llm_result.reasoning)} chars")
        
        # Key differences
        print(f"\n   Key Differences:")
        if llm_result.reasoning and len(llm_result.reasoning) > len(rule_result.reasoning):
            print(f"      ✅ LLM provides more detailed reasoning")
        if confidence_diff > 0.05:
            print(f"      ✅ LLM adjusts confidence based on context")
        if not alignment_match:
            print(f"      ⚠️  LLM detected different alignment")


def test_scenario_1_agreement(openai_api_key: str = None):
    """Scenario 1: AGREEMENT - KPI Declining + Negative Signals"""
    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1001,
            "overall_health_score": 75.0,
            "health_status": "healthy",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1001,
            "overall_health_score": 55.0,
            "health_status": "at-risk",
            "week_number": 2
        })
    ]
    
    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "escalation",
            "signal_id": "1",
            "account_id": 1001,
            "sentiment": "negative",
            "content": "Customer frustrated with open tickets too long to resolve. Support team taking 5+ days to respond to critical issues. Customer escalating to executive team.",
            "signal_date": "2026-01-15"
        }),
        create_test_signal_data("account_note", {
            "signal_type": "account_note",
            "note_id": 201,
            "account_id": 1001,
            "sentiment": "negative",
            "text": "Support tickets taking 5+ days to resolve, customer escalating. Integration issues not being addressed promptly."
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
    
    compare_scenario("AGREEMENT - KPI Declining + Negative Signals", input_data, openai_api_key)


def test_scenario_2_disagreement(openai_api_key: str = None):
    """Scenario 2: DISAGREEMENT - KPI Declining + Positive Signals"""
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
            "account_id": 1002,
            "sentiment": "positive",
            "content": "Customer happy with overall product usage and support team responsiveness. QBR went very well, customer expanding usage next quarter. Product is meeting all their needs.",
            "signal_date": "2026-01-15"
        }),
        create_test_signal_data("account_note", {
            "signal_type": "account_note",
            "note_id": 202,
            "account_id": 1002,
            "sentiment": "positive",
            "text": "QBR went well, customer expanding usage next quarter. Very satisfied with product and support."
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
    
    compare_scenario("DISAGREEMENT - KPI Declining + Positive Signals", input_data, openai_api_key)


def test_scenario_3_complex_mixed(openai_api_key: str = None):
    """Scenario 3: Complex Mixed Signals - Declining KPI + Mixed Signals"""
    quantitative_signals = [
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1003,
            "overall_health_score": 70.0,
            "health_status": "healthy",
            "week_number": 1
        }),
        create_test_signal_data("account_health_score", {
            "signal_type": "account_health_score",
            "account_id": 1003,
            "overall_health_score": 55.0,
            "health_status": "at-risk",
            "week_number": 2
        }),
        create_test_signal_data("kpi_metric", {
            "signal_type": "kpi_metric",
            "kpi_id": 101,
            "account_id": 1003,
            "kpi_parameter": "Daily Active Users",
            "health_status": "at-risk",
            "health_score": 45.0
        })
    ]
    
    qualitative_signals = [
        create_test_signal_data("qualitative_signal", {
            "signal_type": "meeting",
            "signal_id": "3",
            "account_id": 1003,
            "sentiment": "positive",
            "content": "Product usage is excellent, customer very happy with core features. Daily active users are high and engagement is strong.",
            "signal_date": "2026-01-15"
        }),
        create_test_signal_data("qualitative_signal", {
            "signal_type": "ticket",
            "signal_id": "4",
            "account_id": 1003,
            "sentiment": "negative",
            "content": "Support response time is slow for non-critical issues. Some feature requests not being prioritized. Customer wants faster response times.",
            "signal_date": "2026-01-16"
        }),
        create_test_signal_data("account_note", {
            "signal_type": "account_note",
            "note_id": 203,
            "account_id": 1003,
            "sentiment": "neutral",
            "text": "Customer is generally satisfied but has concerns about support responsiveness for non-critical issues."
        })
    ]
    
    input_data = SignalAnalystInput(
        account_id="1003",
        customer_id=1,
        vertical_type="saas_customer_success",
        account_name="Test Account 3",
        account_arr=80000.0,
        health_score=55.0,
        quantitative_signals=quantitative_signals,
        qualitative_signals=qualitative_signals,
        historical_patterns=[],
        analysis_type="churn_risk",
        time_horizon_days=60
    )
    
    compare_scenario("COMPLEX - Declining KPI + Mixed Signals", input_data, openai_api_key)


def main():
    """Run comparison tests"""
    print("\n" + "="*80)
    print("DECISION MATRIX COMPARISON: RULE-BASED vs LLM-BASED")
    print("="*80)
    
    # Get OpenAI API key
    openai_api_key = None
    try:
        with app.app_context():
            openai_api_key = get_openai_api_key(1)  # Try customer_id=1
            if openai_api_key:
                print(f"\n✅ OpenAI API key found: {openai_api_key[:20]}...")
            else:
                print("\n⚠️  OpenAI API key not found, LLM tests will be skipped")
    except Exception as e:
        print(f"\n⚠️  Error getting OpenAI API key: {e}")
        print("   LLM tests will be skipped, but rule-based tests will run")
    
    # Run comparison tests
    try:
        with app.app_context():
            test_scenario_1_agreement(openai_api_key)
            test_scenario_2_disagreement(openai_api_key)
            test_scenario_3_complex_mixed(openai_api_key)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("COMPARISON COMPLETE")
    print("="*80)
    print("\nSummary:")
    print("  ✅ Rule-based: Fast, deterministic, no cost")
    print("  🤖 LLM-based:  More nuanced, context-aware, higher cost")
    print("\n💡 Use LLM when:")
    print("  - Complex scenarios with mixed signals")
    print("  - Nuanced context understanding needed")
    print("  - Cost and latency are acceptable")


if __name__ == "__main__":
    main()
