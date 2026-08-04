#!/usr/bin/env python3
"""Tests for onboarding activation plan hook in process_data pipeline."""

from unittest.mock import MagicMock, patch

from agents.onboarding_agent import ActivationPlan, ActivationPlanEntry
from mcp_server.process_data_pipeline import run_onboarding_agent_analyze


def _sample_plan(customer_id: int = 336, n: int = 2) -> ActivationPlan:
    entries = [
        ActivationPlanEntry(
            account_id=f"{customer_id}00{i}",
            account_name=f"Account {i}",
            priority="high" if i == 0 else "medium",
            risk_level="healthy",
            recommended_playbooks=["activation-blitz"],
            ttfv_target_days=30,
            rationale="test",
        )
        for i in range(n)
    ]
    return ActivationPlan(
        customer_id=customer_id,
        customer_name="Test Co",
        industry="Technology",
        total_accounts=n,
        plan_entries=entries,
        global_recommendations=["Kickoff"],
        ttfv_baseline={"avg_target_days": 30},
    )


@patch("agents.onboarding_agent_api._load_customer_data")
@patch("agents.onboarding_agent.OnboardingAgent")
def test_skips_when_plan_already_exists(mock_agent_cls, mock_load):
    agent = MagicMock()
    agent.get_activation_plan.return_value = {"plan_entries": []}
    mock_agent_cls.return_value = agent

    step, _duration = run_onboarding_agent_analyze(336)

    assert step == "onboarding_plan_exists"
    mock_load.assert_not_called()
    agent.analyze_new_customer.assert_not_called()


@patch("agents.onboarding_agent_api._load_customer_data")
@patch("agents.onboarding_agent.OnboardingAgent")
def test_stores_fallback_when_not_entitled(mock_agent_cls, mock_load):
    agent = MagicMock()
    agent.get_activation_plan.return_value = None
    plan = _sample_plan()
    agent._fallback_plan.return_value = plan
    mock_agent_cls.return_value = agent
    mock_load.return_value = {
        "customer_name": "Test Co",
        "industry": "Technology",
        "onboarding_mode": "demo",
        "accounts": [{"account_id": "336001", "account_name": "A1"}],
        "kpi_snapshot": None,
    }

    with patch("entitlements.check_entitlement", return_value=False):
        step, _duration = run_onboarding_agent_analyze(336)

    assert step == "onboarding_plan_fallback_2_accounts"
    agent._fallback_plan.assert_called_once()
    agent._store_plan_in_memory.assert_called_once_with(plan)
    agent.analyze_new_customer.assert_not_called()


@patch("agents.onboarding_agent_api._load_customer_data")
@patch("agents.onboarding_agent.OnboardingAgent")
def test_llm_path_when_entitled(mock_agent_cls, mock_load):
    agent = MagicMock()
    agent.get_activation_plan.return_value = None
    plan = _sample_plan(n=3)
    agent.analyze_new_customer.return_value = plan
    mock_agent_cls.return_value = agent
    mock_load.return_value = {
        "customer_name": "Test Co",
        "industry": "Technology",
        "onboarding_mode": "demo",
        "accounts": [{"account_id": "336001", "account_name": "A1"}],
        "kpi_snapshot": {"P1": {"value": 60}},
    }

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=False):
        with patch("entitlements.check_entitlement", return_value=True):
            step, _duration = run_onboarding_agent_analyze(336)

    assert step == "onboarding_plan_llm_3_accounts"
    agent.analyze_new_customer.assert_called_once()
    agent._fallback_plan.assert_not_called()
