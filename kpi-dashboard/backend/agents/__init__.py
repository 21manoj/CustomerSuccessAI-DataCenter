"""
CS Pulse AI Agents
Signal Analyst Agent and supporting models
"""

from .signal_analyst_agent import SignalAnalystAgent, AnalysisError, ResponseParseError
from .claude_signal_analyst_agent import ClaudeSignalAnalystAgent, create_signal_analyst_agent
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

__version__ = "1.0.0"

__all__ = [
    "SignalAnalystAgent",
    "ClaudeSignalAnalystAgent",
    "create_signal_analyst_agent",
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

