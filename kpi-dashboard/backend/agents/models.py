"""
Pydantic models for Signal Analyst Agent
Type-safe inputs and outputs
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Literal
from datetime import datetime
from enum import Enum

# ============================================================
# Enums
# ============================================================

class OutcomeType(str, Enum):
    CHURN = "churn"
    EXPANSION = "expansion"
    STABLE = "stable"
    DOWNGRADE = "downgrade"
    CONTRACTION = "contraction"

class ConfidenceLevel(str, Enum):
    VERY_HIGH = "very_high"  # 90%+
    HIGH = "high"             # 75-90%
    MEDIUM = "medium"         # 60-75%
    LOW = "low"               # 40-60%
    VERY_LOW = "very_low"     # <40%

class SignalContribution(str, Enum):
    CRITICAL = "critical"     # Major impact on prediction
    HIGH = "high"             # Significant impact
    MEDIUM = "medium"         # Moderate impact
    LOW = "low"               # Minor impact

# ============================================================
# Input Models
# ============================================================

class SignalData(BaseModel):
    """Individual signal from Qdrant"""
    similarity: float = Field(..., ge=0, le=1, description="Similarity score from vector search")
    payload: Dict = Field(..., description="Signal payload from Qdrant")
    
    @property
    def signal_type(self) -> str:
        return self.payload.get('signal_type', 'unknown')
    
    @property
    def text(self) -> str:
        return self.payload.get('text', '')

class SignalAnalystInput(BaseModel):
    """Input for Signal Analyst Agent"""
    
    # Account identification
    account_id: str = Field(..., description="Unique account identifier")
    customer_id: int = Field(..., description="Customer/tenant ID")
    vertical_type: str = Field(..., description="Vertical type (saas_customer_success, etc.)")
    
    # Account context (optional but helpful)
    account_name: Optional[str] = None
    account_arr: Optional[float] = None
    account_segment: Optional[str] = None  # smb, mid_market, enterprise
    
    # Signals from Qdrant
    quantitative_signals: List[SignalData] = Field(default_factory=list)
    qualitative_signals: List[SignalData] = Field(default_factory=list)
    historical_patterns: List[SignalData] = Field(default_factory=list)
    
    # Analysis parameters
    analysis_type: Literal["churn_risk", "expansion_opportunity", "health_analysis", "comprehensive"] = "comprehensive"
    time_horizon_days: int = Field(default=60, description="Prediction time horizon (30, 60, 90 days)")

# ============================================================
# Output Models
# ============================================================

class RiskDriver(BaseModel):
    """Individual risk driver contributing to churn"""
    driver: str = Field(..., description="Description of risk driver")
    impact: SignalContribution = Field(..., description="Impact level on churn risk")
    supporting_signals: List[str] = Field(default_factory=list, description="Signals that support this driver")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in this driver")

class GrowthDriver(BaseModel):
    """Individual growth driver for expansion"""
    driver: str = Field(..., description="Description of growth opportunity")
    impact: SignalContribution = Field(..., description="Impact level on expansion potential")
    supporting_signals: List[str] = Field(default_factory=list, description="Signals that support this driver")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in this driver")

class RecommendedAction(BaseModel):
    """Actionable recommendation"""
    action: str = Field(..., description="Specific action to take")
    priority: Literal["immediate", "high", "medium", "low"] = Field(..., description="Action priority")
    owner: str = Field(..., description="Suggested owner (CSM, SE, Exec, etc.)")
    deadline_days: Optional[int] = Field(None, description="Suggested deadline in days")
    expected_impact: str = Field(..., description="Expected outcome if action taken")

class PredictionConfidence(BaseModel):
    """Confidence breakdown"""
    overall_confidence: float = Field(..., ge=0, le=1, description="Overall prediction confidence")
    confidence_level: ConfidenceLevel = Field(..., description="Categorical confidence level")
    confidence_factors: Dict[str, float] = Field(default_factory=dict, description="What contributed to confidence")
    
    @classmethod
    def _infer_confidence_level(cls, overall_confidence: float) -> ConfidenceLevel:
        """Helper to infer confidence level from score"""
        if overall_confidence >= 0.90:
            return ConfidenceLevel.VERY_HIGH
        elif overall_confidence >= 0.75:
            return ConfidenceLevel.HIGH
        elif overall_confidence >= 0.60:
            return ConfidenceLevel.MEDIUM
        elif overall_confidence >= 0.40:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

class SignalAnalystOutput(BaseModel):
    """Output from Signal Analyst Agent"""
    
    # Account identification
    account_id: str
    customer_id: int
    vertical_type: str
    
    # Primary predictions
    predicted_outcome: OutcomeType = Field(..., description="Most likely outcome")
    churn_probability: float = Field(..., ge=0, le=100, description="Churn probability (0-100%)")
    expansion_probability: Optional[float] = Field(None, ge=0, le=100, description="Expansion probability (0-100%)")
    health_score: float = Field(..., ge=0, le=100, description="Overall health score (0-100)")
    
    # Time-based predictions
    time_to_event: Optional[str] = Field(None, description="Estimated time to predicted outcome (e.g., '45-60 days')")
    
    # Risk analysis
    risk_drivers: List[RiskDriver] = Field(default_factory=list, description="Top risk drivers for churn")
    
    # Growth analysis
    growth_drivers: List[GrowthDriver] = Field(default_factory=list, description="Top growth opportunities")
    
    # Confidence
    confidence: PredictionConfidence = Field(..., description="Prediction confidence breakdown")
    
    # Reasoning
    reasoning: str = Field(..., description="Detailed explanation of prediction")
    key_insights: List[str] = Field(default_factory=list, description="Key takeaways (3-5 bullets)")
    
    # Actions
    recommended_actions: List[RecommendedAction] = Field(default_factory=list, description="Prioritized action plan")
    
    # Signal breakdown
    signals_analyzed: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of signals analyzed by type"
    )
    
    # Metadata
    analysis_timestamp: datetime = Field(default_factory=datetime.now)
    model_used: str = Field(default="gpt-4o", description="AI model used for analysis")
    analysis_duration_ms: Optional[int] = None

    class Config:
        use_enum_values = True

