"""
CS Pulse AI Agents
Signal Analyst Agent, Onboarding Agent, and supporting models
"""

from .signal_analyst_agent import SignalAnalystAgent, AnalysisError, ResponseParseError
from .claude_signal_analyst_agent import ClaudeSignalAnalystAgent, create_signal_analyst_agent
from .onboarding_agent import OnboardingAgent, ActivationPlan, TTFVStatus
from .models import (
    SignalAnalystInput,
    SignalAnalystOutput,
    SignalData,
    RiskDriver,
    GrowthDriver,
    RecommendedAction,
    PredictionConfidence,
    OutcomeType,
    ConfidenceLevel,
    SignalContribution
)

__version__ = "1.1.0"

__all__ = [
    "SignalAnalystAgent",
    "ClaudeSignalAnalystAgent",
    "create_signal_analyst_agent",
    "OnboardingAgent",
    "ActivationPlan",
    "TTFVStatus",
    "AnalysisError",
    "ResponseParseError",
    "SignalAnalystInput",
    "SignalAnalystOutput",
    "SignalData",
    "RiskDriver",
    "GrowthDriver",
    "RecommendedAction",
    "PredictionConfidence",
    "OutcomeType",
    "ConfidenceLevel",
    "SignalContribution"
]

