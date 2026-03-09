#!/usr/bin/env python3
"""
Decision Matrix for Signal Analyst (LLM-Based)

Uses LLM to intelligently correlate quantitative (KPI) trends with qualitative (signal) sentiment
to determine agreement/disagreement between data sources with nuanced understanding.

Enhanced Decision Matrix (v2):
1. AGREEMENT: KPI trend down + negative signals = both point to same issue
2. DISAGREEMENT: KPI trend down + positive signals = conflicting signals
3. NEUTRAL: KPI stable + neutral signals = neutral
4. POSITIVE_ALIGNMENT: KPI trend up + positive signals = positive alignment
5. INSUFFICIENT_DATA: Brand-new account, no data yet
6. DATA_QUALITY_ISSUE: Has some data but not enough for trend analysis

Enhancements over v1:
- Severity weighting for qualitative signal types (#1)
- Urgency/priority on alignment output (#2)
- Temporal decay for qual signals with 8-week half-life (#3)
- Split insufficient_data vs data_quality_issue (#4)
- Revised STABLE x POSITIVE / IMPROVING x NEUTRAL mappings (#6)
- External signal confidence boost (#7)
- Velocity dimension for trend acceleration/deceleration (#8)
"""

from typing import List, Dict, Optional, Literal
from enum import Enum
import logging
import json
import math
from datetime import datetime, timedelta
from openai import OpenAI
from .models import SignalData, SignalAnalystInput

logger = logging.getLogger(__name__)


# ============================================================
# Enums
# ============================================================

class DataAlignment(str, Enum):
    """Alignment between quantitative and qualitative data"""
    AGREEMENT = "agreement"                    # Both point to same issue (KPI down + negative signals)
    DISAGREEMENT = "disagreement"              # Conflicting signals (KPI down + positive signals)
    NEUTRAL = "neutral"                        # KPI stable + neutral signals
    POSITIVE_ALIGNMENT = "positive_alignment"  # KPI up + positive signals
    INSUFFICIENT_DATA = "insufficient_data"    # Brand-new account, truly no data yet
    DATA_QUALITY_ISSUE = "data_quality_issue"  # Has some data but not enough for trend (#4)


class TrendDirection(str, Enum):
    """KPI trend direction"""
    IMPROVING = "improving"      # healthy -> healthy, at-risk -> healthy, critical -> at-risk
    DECLINING = "declining"      # healthy -> at-risk, at-risk -> critical, healthy -> critical
    STABLE = "stable"            # No change in health status
    UNKNOWN = "unknown"          # Cannot determine


class TrendVelocity(str, Enum):
    """Rate of change in the KPI trend (#8)"""
    ACCELERATING = "accelerating"    # Getting worse/better faster
    STEADY = "steady"                # Constant rate of change
    DECELERATING = "decelerating"    # Rate of change is slowing


class SignalSentiment(str, Enum):
    """Aggregated signal sentiment"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class Urgency(str, Enum):
    """Action urgency derived from alignment (#2)"""
    IMMEDIATE = "immediate"    # agreement (churn risk) — act now
    HIGH = "high"              # disagreement (conflicting) — investigate soon
    MEDIUM = "medium"          # data_quality_issue — fix data gaps
    LOW = "low"                # neutral / positive_alignment — monitor
    NONE = "none"              # insufficient_data — wait for data


# ============================================================
# Signal Severity Weights (#1)
# ============================================================

SIGNAL_SEVERITY_WEIGHTS: Dict[str, float] = {
    # High-severity: escalations / executive changes carry more weight
    'escalation': 3.0,
    'executive_change': 2.5,
    'context_graph_decision': 2.5,
    # Medium-severity: tickets, usage alerts
    'ticket': 2.0,
    'support_ticket': 2.0,
    'nps_response': 2.0,
    'csat_response': 2.0,
    'product_usage': 1.5,
    'context_graph_signal': 1.5,
    # Low-severity: meetings, emails, notes
    'meeting': 1.0,
    'email': 1.0,
    'note': 1.0,
    'account_note': 1.0,
    'qualitative_signal': 1.0,
}

# Default weight for unknown signal types
_DEFAULT_SEVERITY_WEIGHT = 1.0


def _get_severity_weight(signal_type: str) -> float:
    """Return severity weight for a signal type, case-insensitive partial match."""
    signal_type_lower = signal_type.lower()
    # Try exact match first
    if signal_type_lower in SIGNAL_SEVERITY_WEIGHTS:
        return SIGNAL_SEVERITY_WEIGHTS[signal_type_lower]
    # Partial match (e.g., 'context_graph_signal' matches 'context_graph_signal')
    for key, weight in SIGNAL_SEVERITY_WEIGHTS.items():
        if key in signal_type_lower:
            return weight
    return _DEFAULT_SEVERITY_WEIGHT


# ============================================================
# Temporal Decay (#3)
# ============================================================

_DECAY_HALF_LIFE_DAYS = 56  # 8 weeks


def _temporal_decay_weight(signal_date: Optional[datetime], anchor: Optional[datetime] = None) -> float:
    """
    Exponential decay weight based on signal age.
    Half-life = 8 weeks.  Returns 1.0 for today, 0.5 for 8 weeks ago, 0.25 for 16 weeks ago, etc.
    If signal_date is None, returns 0.5 (neutral — age unknown).
    """
    if signal_date is None:
        return 0.5
    anchor = anchor or datetime.utcnow()
    age_days = max((anchor - signal_date).days, 0)
    return math.exp(-0.693 * age_days / _DECAY_HALF_LIFE_DAYS)  # ln(2) ~ 0.693


# ============================================================
# External Signal Classification (#7)
# ============================================================

# Signal types considered "external" — harder to fake, higher predictive value
_EXTERNAL_SIGNAL_TYPES = frozenset({
    'escalation', 'executive_change', 'competitor_mention',
    'nps_response', 'csat_response', 'context_graph_signal',
    'context_graph_decision',
})

_INTERNAL_SIGNAL_TYPES = frozenset({
    'meeting', 'email', 'note', 'account_note',
    'qualitative_signal', 'product_usage',
})


def _classify_signal_source(signal_type: str) -> str:
    """Classify signal as 'external' or 'internal'."""
    st = signal_type.lower()
    for ext in _EXTERNAL_SIGNAL_TYPES:
        if ext in st:
            return 'external'
    return 'internal'


# ============================================================
# Urgency Mapping (#2)
# ============================================================

_ALIGNMENT_URGENCY: Dict[DataAlignment, Urgency] = {
    DataAlignment.AGREEMENT: Urgency.IMMEDIATE,
    DataAlignment.DISAGREEMENT: Urgency.HIGH,
    DataAlignment.DATA_QUALITY_ISSUE: Urgency.MEDIUM,
    DataAlignment.NEUTRAL: Urgency.LOW,
    DataAlignment.POSITIVE_ALIGNMENT: Urgency.LOW,
    DataAlignment.INSUFFICIENT_DATA: Urgency.NONE,
}


# ============================================================
# Result Model
# ============================================================

class DecisionMatrixResult:
    """Result of decision matrix analysis"""

    def __init__(
        self,
        alignment: DataAlignment,
        trend_direction: TrendDirection,
        signal_sentiment: SignalSentiment,
        kpi_health_trend: str,           # e.g., "healthy -> at-risk"
        signal_summary: str,             # e.g., "Customer frustrated with open tickets"
        confidence: float,               # 0.0-1.0
        reasoning: str,
        recommended_actions: Optional[List[str]] = None,
        urgency: Optional[Urgency] = None,                # #2
        trend_velocity: Optional[TrendVelocity] = None,   # #8
        external_signal_ratio: Optional[float] = None,    # #7
        sentiment_details: Optional[Dict] = None,         # #1 weighted breakdown
    ):
        self.alignment = alignment
        self.trend_direction = trend_direction
        self.signal_sentiment = signal_sentiment
        self.kpi_health_trend = kpi_health_trend
        self.signal_summary = signal_summary
        self.confidence = confidence
        self.reasoning = reasoning
        self.recommended_actions = recommended_actions or []
        self.urgency = urgency or _ALIGNMENT_URGENCY.get(alignment, Urgency.LOW)
        self.trend_velocity = trend_velocity
        self.external_signal_ratio = external_signal_ratio
        self.sentiment_details = sentiment_details

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = {
            "alignment": self.alignment.value,
            "trend_direction": self.trend_direction.value,
            "signal_sentiment": self.signal_sentiment.value,
            "kpi_health_trend": self.kpi_health_trend,
            "signal_summary": self.signal_summary,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "recommended_actions": self.recommended_actions,
            # --- New fields (additive, backward-compatible) ---
            "urgency": self.urgency.value if self.urgency else None,
        }
        if self.trend_velocity is not None:
            result["trend_velocity"] = self.trend_velocity.value
        if self.external_signal_ratio is not None:
            result["external_signal_ratio"] = round(self.external_signal_ratio, 2)
        if self.sentiment_details:
            result["sentiment_details"] = self.sentiment_details
        return result


# ============================================================
# KPI Health Trend Analysis (with Velocity — #8)
# ============================================================

def analyze_kpi_health_trend(
    quantitative_signals: List[SignalData],
    current_health_score: Optional[float]
) -> tuple:
    """
    Analyze KPI health trend from quantitative signals.

    Returns:
        Tuple of (TrendDirection, trend_description, TrendVelocity)
    """
    if not quantitative_signals:
        return TrendDirection.UNKNOWN, "No KPI data available", TrendVelocity.STEADY

    # Extract health scores (numeric) and statuses in order
    health_scores: List[float] = []
    health_statuses: List[str] = []
    current_health_status = None

    for signal in quantitative_signals:
        payload = signal.payload
        signal_type = payload.get('signal_type', '')

        # Check for account health score signal
        if signal_type == 'account_health_score':
            score = payload.get('overall_health_score')
            if score is not None:
                health_scores.append(float(score))
                if score >= 67:
                    health_statuses.append('healthy')
                elif score >= 34:
                    health_statuses.append('at-risk')
                else:
                    health_statuses.append('critical')

        # Check for KPI health status
        hs = payload.get('health_status')
        if hs:
            health_statuses.append(hs.lower())

    # Use current health score if available
    if current_health_score is not None:
        if current_health_score >= 67:
            current_health_status = 'healthy'
        elif current_health_score >= 34:
            current_health_status = 'at-risk'
        else:
            current_health_status = 'critical'

    # ── Velocity analysis (#8) ────────────────────────────────
    # Use signal-derived scores only (not current_health_score, which
    # may duplicate the last signal and distort the rate-of-change).
    velocity = TrendVelocity.STEADY
    if len(health_scores) >= 3:
        # Compare first-half delta vs second-half delta
        mid = len(health_scores) // 2
        first_half_delta = health_scores[mid] - health_scores[0]
        second_half_delta = health_scores[-1] - health_scores[mid]
        # If both deltas are in the same direction and second is larger → accelerating
        if abs(second_half_delta) > abs(first_half_delta) * 1.3:
            velocity = TrendVelocity.ACCELERATING
        elif abs(second_half_delta) < abs(first_half_delta) * 0.7:
            velocity = TrendVelocity.DECELERATING
        # else stays STEADY

    # ── Trend direction ───────────────────────────────────────
    if len(health_statuses) >= 2:
        unique_statuses = list(set(health_statuses))
        if len(unique_statuses) == 1:
            status = unique_statuses[0]
            return TrendDirection.STABLE, f"Health status stable at {status}", velocity

        # Check for improving trend
        if 'critical' in unique_statuses and 'at-risk' in unique_statuses:
            if health_statuses[-1] == 'at-risk' and 'critical' in health_statuses[:-1]:
                return TrendDirection.IMPROVING, "critical -> at-risk", velocity
        if 'at-risk' in unique_statuses and 'healthy' in unique_statuses:
            if health_statuses[-1] == 'healthy' and 'at-risk' in health_statuses[:-1]:
                return TrendDirection.IMPROVING, "at-risk -> healthy", velocity

        # Check for declining trend
        if 'healthy' in unique_statuses and 'at-risk' in unique_statuses:
            if health_statuses[-1] == 'at-risk' and 'healthy' in health_statuses[:-1]:
                return TrendDirection.DECLINING, "healthy -> at-risk", velocity
        if 'at-risk' in unique_statuses and 'critical' in unique_statuses:
            if health_statuses[-1] == 'critical' and 'at-risk' in health_statuses[:-1]:
                return TrendDirection.DECLINING, "at-risk -> critical", velocity
        if 'healthy' in unique_statuses and 'critical' in unique_statuses:
            if health_statuses[-1] == 'critical' and 'healthy' in health_statuses[:-1]:
                return TrendDirection.DECLINING, "healthy -> critical", velocity

    # Use current health status if available
    if current_health_status:
        return TrendDirection.STABLE, f"Current health status: {current_health_status}", velocity

    return TrendDirection.UNKNOWN, "Cannot determine trend from available data", velocity


# ============================================================
# Sentiment Analysis (with severity weighting #1, temporal decay #3, external tracking #7)
# ============================================================

def analyze_signal_sentiment(
    qualitative_signals: List[SignalData]
) -> tuple:
    """
    Analyze aggregated sentiment from qualitative signals.
    Uses severity weighting (#1) and temporal decay (#3).

    Returns:
        Tuple of (SignalSentiment, summary_description, sentiment_details_dict, external_signal_ratio)
    """
    if not qualitative_signals:
        return (
            SignalSentiment.NEUTRAL,
            "No qualitative signals available",
            {"positive_weight": 0, "negative_weight": 0, "neutral_weight": 0, "total_raw": 0},
            0.0,
        )

    weighted_positive = 0.0
    weighted_negative = 0.0
    weighted_neutral = 0.0
    signal_summaries = []
    external_count = 0
    total_count = 0

    now = datetime.utcnow()

    for signal in qualitative_signals:
        payload = signal.payload
        raw_sentiment = payload.get('sentiment', 'neutral')
        signal_type = payload.get('signal_type', '')
        content = payload.get('content') or payload.get('text', '')

        # Severity weight (#1)
        severity = _get_severity_weight(signal_type)

        # Temporal decay weight (#3)
        signal_date = None
        for date_key in ('occurred_at', 'created_at', 'date', 'timestamp'):
            raw_date = payload.get(date_key)
            if raw_date:
                try:
                    if isinstance(raw_date, datetime):
                        signal_date = raw_date
                    elif isinstance(raw_date, str):
                        # Try common formats
                        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                            try:
                                signal_date = datetime.strptime(raw_date, fmt)
                                break
                            except ValueError:
                                continue
                except Exception:
                    pass
                if signal_date:
                    break
        decay = _temporal_decay_weight(signal_date, now)

        combined_weight = severity * decay

        # External classification (#7)
        total_count += 1
        if _classify_signal_source(signal_type) == 'external':
            external_count += 1

        # Normalize sentiment and apply weight
        if raw_sentiment in ('positive', 'good', 'happy', 'satisfied'):
            weighted_positive += combined_weight
        elif raw_sentiment in ('negative', 'bad', 'frustrated', 'unhappy', 'dissatisfied'):
            weighted_negative += combined_weight
        else:
            weighted_neutral += combined_weight

        # Extract key themes from content
        if content:
            content_lower = content.lower()
            if any(word in content_lower for word in ('frustrated', 'disappointed', 'concerned', 'issue', 'problem', 'escalat')):
                signal_summaries.append(f"Customer {raw_sentiment}: {content[:100]}")
            elif any(word in content_lower for word in ('happy', 'satisfied', 'pleased', 'excellent', 'great')):
                signal_summaries.append(f"Customer {raw_sentiment}: {content[:100]}")
            else:
                signal_summaries.append(f"{signal_type}: {content[:100]}")

    # Determine overall sentiment using weighted counts (#1 + #3)
    total_weight = weighted_positive + weighted_negative + weighted_neutral
    external_ratio = external_count / total_count if total_count > 0 else 0.0

    sentiment_details = {
        "positive_weight": round(weighted_positive, 2),
        "negative_weight": round(weighted_negative, 2),
        "neutral_weight": round(weighted_neutral, 2),
        "total_raw": total_count,
        "external_count": external_count,
    }

    if total_weight == 0:
        return SignalSentiment.NEUTRAL, "Neutral signals, no strong sentiment", sentiment_details, external_ratio

    pos_ratio = weighted_positive / total_weight
    neg_ratio = weighted_negative / total_weight

    if neg_ratio > pos_ratio and neg_ratio > 0.4:
        sentiment = SignalSentiment.NEGATIVE
        summary = f"Customer frustrated with: {', '.join(signal_summaries[:3])}"
    elif pos_ratio > neg_ratio and pos_ratio > 0.4:
        sentiment = SignalSentiment.POSITIVE
        summary = f"Customer happy with: {', '.join(signal_summaries[:3])}"
    elif weighted_negative > 0 and weighted_positive > 0:
        sentiment = SignalSentiment.MIXED
        summary = f"Mixed signals: {weighted_positive:.1f} positive weight, {weighted_negative:.1f} negative weight"
    else:
        sentiment = SignalSentiment.NEUTRAL
        summary = "Neutral signals, no strong sentiment"

    return sentiment, summary, sentiment_details, external_ratio


# ============================================================
# LLM-Based Decision Matrix
# ============================================================

def _calculate_decision_matrix_llm(
    input_data: SignalAnalystInput,
    openai_api_key: str,
    trend_direction: TrendDirection,
    kpi_health_trend: str,
    signal_sentiment: SignalSentiment,
    signal_summary: str,
    trend_velocity: TrendVelocity = TrendVelocity.STEADY,
    sentiment_details: Optional[Dict] = None,
    external_signal_ratio: float = 0.0,
) -> DecisionMatrixResult:
    """
    Use LLM to intelligently correlate quantitative and qualitative data.
    Enhanced with velocity (#8), urgency (#2), and external signals (#7).
    """
    try:
        client = OpenAI(api_key=openai_api_key)

        # Build context from signals
        quantitative_context = []
        for signal in input_data.quantitative_signals[:10]:
            payload = signal.payload
            signal_type = payload.get('signal_type', '')
            if signal_type == 'account_health_score':
                quantitative_context.append(f"Health Score: {payload.get('overall_health_score', 'N/A')} ({payload.get('health_status', 'unknown')})")
            elif signal_type == 'kpi_metric':
                quantitative_context.append(f"KPI: {payload.get('kpi_parameter', 'unknown')} - Status: {payload.get('health_status', 'unknown')}")

        qualitative_context = []
        for signal in input_data.qualitative_signals[:10]:
            payload = signal.payload
            content = payload.get('content') or payload.get('text', '')
            raw_sentiment = payload.get('sentiment', 'neutral')
            signal_type = payload.get('signal_type', '')
            source_class = _classify_signal_source(signal_type)
            if content:
                qualitative_context.append(f"{signal_type} ({raw_sentiment}, {source_class}): {content[:150]}")

        # Velocity context (#8)
        velocity_text = ""
        if trend_velocity != TrendVelocity.STEADY:
            velocity_text = f"\n- Trend Velocity: {trend_velocity.value} (the rate of change is {'increasing' if trend_velocity == TrendVelocity.ACCELERATING else 'decreasing'})"

        # Severity/external context (#1, #7)
        severity_text = ""
        if sentiment_details:
            severity_text = (
                f"\n- Severity-Weighted Sentiment: positive={sentiment_details.get('positive_weight', 0):.1f}, "
                f"negative={sentiment_details.get('negative_weight', 0):.1f}, "
                f"neutral={sentiment_details.get('neutral_weight', 0):.1f}"
            )
        external_text = f"\n- External Signal Ratio: {external_signal_ratio:.0%} of signals are external (harder to fake, higher predictive value)" if external_signal_ratio > 0 else ""

        prompt = f"""You are an expert Customer Success analyst analyzing the correlation between quantitative (KPI) data and qualitative (customer signal) data.

**QUANTITATIVE DATA (KPI Trends):**
- Trend Direction: {trend_direction.value}
- KPI Health Trend: {kpi_health_trend}{velocity_text}
- Current Health Score: {input_data.health_score if input_data.health_score else 'N/A'}
- Quantitative Context:
{chr(10).join(quantitative_context) if quantitative_context else '  No quantitative signals available'}

**QUALITATIVE DATA (Customer Signals):**
- Overall Sentiment: {signal_sentiment.value}
- Signal Summary: {signal_summary}{severity_text}{external_text}
- Qualitative Context:
{chr(10).join(qualitative_context) if qualitative_context else '  No qualitative signals available'}

**YOUR TASK:**
Analyze the correlation between the quantitative KPI trends and qualitative customer signals to determine if they agree or disagree. Consider all signal types, their severity, recency, and whether they are external vs internal.

**Decision Matrix:**
1. **AGREEMENT**: KPI declining + negative signals = Both point to same issue (high confidence churn risk)
2. **DISAGREEMENT**: KPI declining + positive signals = Conflicting signals (lower confidence, needs investigation)
3. **NEUTRAL**: KPI stable + neutral signals = Stable account, no immediate concerns
4. **POSITIVE_ALIGNMENT**: KPI improving/stable + positive signals = Both confirm positive trajectory (expansion opportunity)
5. **INSUFFICIENT_DATA**: Brand-new account, truly no data yet
6. **DATA_QUALITY_ISSUE**: Has some data but gaps prevent reliable trend analysis

**CRITICAL ANALYSIS REQUIREMENTS:**
1. **Signal Differentiation**: Distinguish between different signal types and their relative severity (escalations > tickets > meetings)
2. **Recency Weighting**: Recent signals matter more than old ones — factor in temporal decay
3. **External vs Internal**: External signals (escalations, NPS, competitor mentions) carry more predictive weight than internal notes
4. **Velocity Awareness**: Consider whether the trend is accelerating, decelerating, or steady — a declining+accelerating account is more urgent than declining+decelerating
5. **Actionable Insights**: Provide specific, actionable recommendations for resolution
6. **Confidence Calibration**: Confidence should reflect signal quality, quantity, and diversity

**Urgency Scale** (set based on alignment):
- immediate: agreement/churn risk — act now
- high: disagreement — investigate soon
- medium: data quality issue — fix data gaps
- low: neutral/positive — monitor

**Respond in JSON format:**
{{
    "alignment": "agreement" | "disagreement" | "neutral" | "positive_alignment" | "insufficient_data" | "data_quality_issue",
    "confidence": 0.0-1.0,
    "urgency": "immediate" | "high" | "medium" | "low" | "none",
    "reasoning": "Detailed explanation including signal differentiation, velocity context, and external/internal signal analysis",
    "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
    "recommended_actions": ["Action 1 for resolution", "Action 2 for resolution", "Action 3 for resolution"]
}}"""

        # Call LLM
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert Customer Success analyst specializing in correlating quantitative metrics with qualitative customer signals."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )

        result_data = json.loads(response.choices[0].message.content)

        # Map alignment string to enum
        alignment_str = result_data.get('alignment', 'insufficient_data')
        alignment_map = {
            'agreement': DataAlignment.AGREEMENT,
            'disagreement': DataAlignment.DISAGREEMENT,
            'neutral': DataAlignment.NEUTRAL,
            'positive_alignment': DataAlignment.POSITIVE_ALIGNMENT,
            'insufficient_data': DataAlignment.INSUFFICIENT_DATA,
            'data_quality_issue': DataAlignment.DATA_QUALITY_ISSUE,
        }
        alignment = alignment_map.get(alignment_str, DataAlignment.INSUFFICIENT_DATA)

        # Get confidence and reasoning
        confidence = float(result_data.get('confidence', 0.5))
        confidence = max(0.0, min(1.0, confidence))

        reasoning = result_data.get('reasoning', '')
        key_insights = result_data.get('key_insights', [])
        recommended_actions = result_data.get('recommended_actions', [])

        # Enhance reasoning with key insights and recommended actions
        if key_insights:
            reasoning += f"\n\nKey Insights: {'; '.join(key_insights)}"
        if recommended_actions:
            reasoning += f"\n\nRecommended Actions for Quicker Resolution: {'; '.join(recommended_actions)}"

        # Map urgency from LLM response or derive from alignment (#2)
        urgency_str = result_data.get('urgency')
        urgency_map = {
            'immediate': Urgency.IMMEDIATE,
            'high': Urgency.HIGH,
            'medium': Urgency.MEDIUM,
            'low': Urgency.LOW,
            'none': Urgency.NONE,
        }
        urgency = urgency_map.get(urgency_str) if urgency_str else _ALIGNMENT_URGENCY.get(alignment, Urgency.LOW)

        logger.info(f"LLM Decision Matrix: {alignment.value} (confidence: {confidence:.2f}, urgency: {urgency.value}, velocity: {trend_velocity.value})")

        return DecisionMatrixResult(
            alignment=alignment,
            trend_direction=trend_direction,
            signal_sentiment=signal_sentiment,
            kpi_health_trend=kpi_health_trend,
            signal_summary=signal_summary,
            confidence=confidence,
            reasoning=reasoning,
            recommended_actions=recommended_actions,
            urgency=urgency,
            trend_velocity=trend_velocity,
            external_signal_ratio=external_signal_ratio,
            sentiment_details=sentiment_details,
        )

    except Exception as e:
        logger.warning(f"LLM decision matrix failed: {e}, falling back to rule-based", exc_info=True)
        raise  # Will fall back to rule-based


# ============================================================
# Rule-Based Decision Matrix (fallback)
# ============================================================

def _calculate_decision_matrix_rule_based(
    trend_direction: TrendDirection,
    kpi_health_trend: str,
    signal_sentiment: SignalSentiment,
    signal_summary: str,
    trend_velocity: TrendVelocity = TrendVelocity.STEADY,
    sentiment_details: Optional[Dict] = None,
    external_signal_ratio: float = 0.0,
    has_some_quant_data: bool = False,
    has_some_qual_data: bool = False,
) -> DecisionMatrixResult:
    """
    Fallback rule-based decision matrix (used if LLM fails).
    Enhanced with revised mappings (#6), velocity (#8), and external boost (#7).
    """
    alignment = DataAlignment.INSUFFICIENT_DATA
    confidence = 0.5
    reasoning = ""
    urgency = Urgency.LOW

    # ── Velocity modifier for confidence (#8) ─────────────────
    # Accelerating trends increase confidence; decelerating decreases it
    velocity_modifier = 0.0
    velocity_note = ""
    if trend_velocity == TrendVelocity.ACCELERATING:
        velocity_modifier = 0.05
        velocity_note = " Trend is accelerating — urgency elevated."
    elif trend_velocity == TrendVelocity.DECELERATING:
        velocity_modifier = -0.05
        velocity_note = " Trend is decelerating — may be stabilizing."

    # ── External signal confidence boost (#7) ─────────────────
    external_boost = 0.0
    external_note = ""
    if external_signal_ratio >= 0.5:
        external_boost = 0.10
        external_note = " High external signal ratio confirms sentiment."
    elif external_signal_ratio >= 0.25:
        external_boost = 0.05
        external_note = " Moderate external signals support sentiment."

    # ── Decision Matrix Logic (revised #6) ────────────────────
    if trend_direction == TrendDirection.DECLINING:
        if signal_sentiment == SignalSentiment.NEGATIVE:
            alignment = DataAlignment.AGREEMENT
            confidence = 0.85 + velocity_modifier + external_boost
            urgency = Urgency.IMMEDIATE
            reasoning = (
                f"AGREEMENT: KPI data shows declining trend ({kpi_health_trend}) and qualitative signals "
                f"indicate customer frustration ({signal_summary}). Both data sources point to the same "
                f"underlying issue. High confidence in churn risk prediction.{velocity_note}{external_note}"
            )
        elif signal_sentiment == SignalSentiment.POSITIVE:
            alignment = DataAlignment.DISAGREEMENT
            confidence = 0.60 + velocity_modifier
            urgency = Urgency.HIGH
            reasoning = (
                f"DISAGREEMENT: KPI data shows declining trend ({kpi_health_trend}) but qualitative signals "
                f"indicate customer satisfaction ({signal_summary}). Conflicting signals suggest either: "
                f"(1) KPI lagging indicator, (2) Temporary KPI dip, or (3) Need for deeper investigation. "
                f"Lower confidence in churn risk prediction - recommend follow-up call.{velocity_note}"
            )
        elif signal_sentiment == SignalSentiment.MIXED:
            # #6: DECLINING x MIXED → agreement (partial), not disagreement
            alignment = DataAlignment.AGREEMENT
            confidence = 0.65 + velocity_modifier + external_boost
            urgency = Urgency.IMMEDIATE
            reasoning = (
                f"AGREEMENT (partial): KPI data shows declining trend ({kpi_health_trend}) and qualitative signals "
                f"are mixed ({signal_summary}). Mixed sentiment with declining KPIs indicates partial "
                f"confirmation of issues — the negative signals align with the KPI trend while positive signals "
                f"may reflect isolated bright spots. Treat as churn risk with investigation needed.{velocity_note}{external_note}"
            )
        else:  # NEUTRAL
            alignment = DataAlignment.NEUTRAL
            confidence = 0.50 + velocity_modifier
            urgency = Urgency.HIGH  # Declining KPIs with neutral sentiment still needs attention
            reasoning = (
                f"NEUTRAL: KPI data shows declining trend ({kpi_health_trend}) but qualitative signals "
                f"are neutral ({signal_summary}). Insufficient qualitative context to confirm KPI trend. "
                f"Recommend monitoring and proactive engagement.{velocity_note}"
            )

    elif trend_direction == TrendDirection.IMPROVING:
        if signal_sentiment == SignalSentiment.POSITIVE:
            alignment = DataAlignment.POSITIVE_ALIGNMENT
            confidence = 0.80 + velocity_modifier + external_boost
            urgency = Urgency.LOW
            reasoning = (
                f"POSITIVE_ALIGNMENT: KPI data shows improving trend ({kpi_health_trend}) and qualitative signals "
                f"indicate customer satisfaction ({signal_summary}). Both data sources confirm positive "
                f"trajectory. Good opportunity for expansion discussions.{velocity_note}{external_note}"
            )
        elif signal_sentiment == SignalSentiment.NEGATIVE:
            alignment = DataAlignment.DISAGREEMENT
            confidence = 0.60 + velocity_modifier
            urgency = Urgency.HIGH
            reasoning = (
                f"DISAGREEMENT: KPI data shows improving trend ({kpi_health_trend}) but qualitative signals "
                f"indicate concerns ({signal_summary}). Conflicting signals suggest either: "
                f"(1) Recent improvement not yet reflected in sentiment, (2) KPI improvement may be temporary, "
                f"or (3) Need for deeper investigation. Recommend follow-up call.{velocity_note}"
            )
        elif signal_sentiment == SignalSentiment.NEUTRAL:
            # #6: IMPROVING x NEUTRAL → positive_alignment (weak), not neutral
            alignment = DataAlignment.POSITIVE_ALIGNMENT
            confidence = 0.55 + velocity_modifier
            urgency = Urgency.LOW
            reasoning = (
                f"POSITIVE_ALIGNMENT (weak): KPI data shows improving trend ({kpi_health_trend}) with "
                f"neutral qualitative signals ({signal_summary}). Improving KPIs are a positive signal "
                f"even without strong qualitative confirmation — the lack of negative feedback is itself "
                f"a good sign. Monitor for qualitative confirmation to strengthen confidence.{velocity_note}"
            )
        else:  # MIXED
            # #6: IMPROVING x MIXED → positive_alignment (weak), not neutral
            alignment = DataAlignment.POSITIVE_ALIGNMENT
            confidence = 0.50 + velocity_modifier
            urgency = Urgency.LOW
            reasoning = (
                f"POSITIVE_ALIGNMENT (weak): KPI data shows improving trend ({kpi_health_trend}) with "
                f"mixed qualitative signals ({signal_summary}). Improving KPIs suggest underlying progress "
                f"despite mixed feedback. Investigate negative signals to ensure they don't indicate "
                f"emerging issues that could reverse the trend.{velocity_note}"
            )

    elif trend_direction == TrendDirection.STABLE:
        if signal_sentiment == SignalSentiment.NEGATIVE:
            alignment = DataAlignment.DISAGREEMENT
            confidence = 0.55 + velocity_modifier + external_boost
            urgency = Urgency.HIGH
            reasoning = (
                f"DISAGREEMENT: KPI data shows stable trend ({kpi_health_trend}) but qualitative signals "
                f"indicate concerns ({signal_summary}). Qualitative signals may be a leading indicator "
                f"of future KPI decline. Recommend proactive engagement.{velocity_note}{external_note}"
            )
        elif signal_sentiment == SignalSentiment.POSITIVE:
            # #6: STABLE x POSITIVE → positive_alignment (weak), not neutral
            alignment = DataAlignment.POSITIVE_ALIGNMENT
            confidence = 0.60 + external_boost
            urgency = Urgency.LOW
            reasoning = (
                f"POSITIVE_ALIGNMENT (weak): KPI data shows stable trend ({kpi_health_trend}) and qualitative "
                f"signals are positive ({signal_summary}). Positive sentiment while metrics are stable is a "
                f"leading indicator of expansion potential. Monitor for KPI improvement to confirm.{external_note}"
            )
        else:  # NEUTRAL or MIXED
            alignment = DataAlignment.NEUTRAL
            confidence = 0.60
            urgency = Urgency.LOW
            reasoning = (
                f"NEUTRAL: KPI data shows stable trend ({kpi_health_trend}) and qualitative signals "
                f"are neutral/mixed ({signal_summary}). Stable account, no immediate concerns or opportunities."
            )

    else:  # UNKNOWN trend
        # #4: Split insufficient_data vs data_quality_issue
        if has_some_quant_data or has_some_qual_data:
            alignment = DataAlignment.DATA_QUALITY_ISSUE
            confidence = 0.30
            urgency = Urgency.MEDIUM
            reasoning = (
                f"DATA_QUALITY_ISSUE: Some data exists but it is not sufficient to determine KPI trend "
                f"({kpi_health_trend}). Qualitative signals: {signal_summary}. "
                f"Investigate data gaps: ensure KPI uploads are complete and health scores are being calculated."
            )
        else:
            alignment = DataAlignment.INSUFFICIENT_DATA
            confidence = 0.20
            urgency = Urgency.NONE
            reasoning = (
                f"INSUFFICIENT_DATA: No KPI trend data available ({kpi_health_trend}). "
                f"This may be a brand-new account. Wait for initial data ingestion before analysis."
            )

    # Clamp confidence
    confidence = max(0.0, min(1.0, confidence))

    return DecisionMatrixResult(
        alignment=alignment,
        trend_direction=trend_direction,
        signal_sentiment=signal_sentiment,
        kpi_health_trend=kpi_health_trend,
        signal_summary=signal_summary,
        confidence=confidence,
        reasoning=reasoning,
        urgency=urgency,
        trend_velocity=trend_velocity,
        external_signal_ratio=external_signal_ratio,
        sentiment_details=sentiment_details,
    )


# ============================================================
# Public Entry Point
# ============================================================

def calculate_decision_matrix(
    input_data: SignalAnalystInput,
    openai_api_key: Optional[str] = None,
    use_llm: bool = True  # Default to LLM for better context and future extensibility
) -> DecisionMatrixResult:
    """
    Calculate decision matrix comparing quantitative and qualitative data.

    Uses LLM by default for nuanced correlation analysis, better context understanding,
    and future extensibility (playbook feedback, additional signal channels).
    Falls back to rule-based if LLM unavailable.

    Enhanced with:
    - Severity weighting for qual signal types (#1)
    - Urgency/priority on alignment output (#2)
    - Temporal decay for qual signals (#3)
    - Split insufficient_data vs data_quality_issue (#4)
    - Revised STABLE x POSITIVE / IMPROVING x NEUTRAL/MIXED mappings (#6)
    - External signal confidence boost (#7)
    - Velocity dimension for trend acceleration/deceleration (#8)
    """
    # Analyze KPI health trend (now returns velocity too — #8)
    trend_direction, kpi_health_trend, trend_velocity = analyze_kpi_health_trend(
        input_data.quantitative_signals,
        input_data.health_score
    )

    # Analyze signal sentiment (now returns details + external ratio — #1, #3, #7)
    signal_sentiment, signal_summary, sentiment_details, external_signal_ratio = analyze_signal_sentiment(
        input_data.qualitative_signals
    )

    # Use LLM if requested and API key available
    if use_llm and openai_api_key:
        try:
            return _calculate_decision_matrix_llm(
                input_data=input_data,
                openai_api_key=openai_api_key,
                trend_direction=trend_direction,
                kpi_health_trend=kpi_health_trend,
                signal_sentiment=signal_sentiment,
                signal_summary=signal_summary,
                trend_velocity=trend_velocity,
                sentiment_details=sentiment_details,
                external_signal_ratio=external_signal_ratio,
            )
        except Exception as e:
            logger.warning(f"LLM decision matrix failed, using rule-based fallback: {e}")
            # Fall through to rule-based

    # Use rule-based logic (fallback)
    return _calculate_decision_matrix_rule_based(
        trend_direction=trend_direction,
        kpi_health_trend=kpi_health_trend,
        signal_sentiment=signal_sentiment,
        signal_summary=signal_summary,
        trend_velocity=trend_velocity,
        sentiment_details=sentiment_details,
        external_signal_ratio=external_signal_ratio,
        has_some_quant_data=bool(input_data.quantitative_signals),
        has_some_qual_data=bool(input_data.qualitative_signals),
    )
