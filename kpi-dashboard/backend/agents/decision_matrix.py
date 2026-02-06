#!/usr/bin/env python3
"""
Decision Matrix for Signal Analyst (LLM-Based)

Uses LLM to intelligently correlate quantitative (KPI) trends with qualitative (signal) sentiment
to determine agreement/disagreement between data sources with nuanced understanding.

Decision Matrix:
1. AGREEMENT: KPI trend down + negative signals = both point to same issue
2. DISAGREEMENT: KPI trend down + positive signals = conflicting signals
3. NEUTRAL: KPI stable + mixed signals = neutral
4. POSITIVE_ALIGNMENT: KPI trend up + positive signals = positive alignment
"""

from typing import List, Dict, Optional, Literal
from enum import Enum
import logging
import json
from openai import OpenAI
from .models import SignalData, SignalAnalystInput

logger = logging.getLogger(__name__)


class DataAlignment(str, Enum):
    """Alignment between quantitative and qualitative data"""
    AGREEMENT = "agreement"                    # Both point to same issue (KPI down + negative signals)
    DISAGREEMENT = "disagreement"              # Conflicting signals (KPI down + positive signals)
    NEUTRAL = "neutral"                        # KPI stable + mixed signals
    POSITIVE_ALIGNMENT = "positive_alignment"  # KPI up + positive signals
    INSUFFICIENT_DATA = "insufficient_data"   # Not enough data to determine


class TrendDirection(str, Enum):
    """KPI trend direction"""
    IMPROVING = "improving"      # healthy → healthy, at-risk → healthy, critical → at-risk
    DECLINING = "declining"      # healthy → at-risk, at-risk → critical, healthy → critical
    STABLE = "stable"            # No change in health status
    UNKNOWN = "unknown"          # Cannot determine


class SignalSentiment(str, Enum):
    """Aggregated signal sentiment"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class DecisionMatrixResult:
    """Result of decision matrix analysis"""
    
    def __init__(
        self,
        alignment: DataAlignment,
        trend_direction: TrendDirection,
        signal_sentiment: SignalSentiment,
        kpi_health_trend: str,  # e.g., "healthy → at-risk"
        signal_summary: str,    # e.g., "Customer frustrated with open tickets"
        confidence: float,      # 0.0-1.0
        reasoning: str,
        recommended_actions: Optional[List[str]] = None  # Actions for quicker resolution
    ):
        self.alignment = alignment
        self.trend_direction = trend_direction
        self.signal_sentiment = signal_sentiment
        self.kpi_health_trend = kpi_health_trend
        self.signal_summary = signal_summary
        self.confidence = confidence
        self.reasoning = reasoning
        self.recommended_actions = recommended_actions or []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "alignment": self.alignment.value,
            "trend_direction": self.trend_direction.value,
            "signal_sentiment": self.signal_sentiment.value,
            "kpi_health_trend": self.kpi_health_trend,
            "signal_summary": self.signal_summary,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "recommended_actions": self.recommended_actions
        }


def analyze_kpi_health_trend(
    quantitative_signals: List[SignalData],
    current_health_score: Optional[float]
) -> tuple:
    """
    Analyze KPI health trend from quantitative signals
    
    Args:
        quantitative_signals: List of quantitative SignalData objects
        current_health_score: Current overall health score (0-100)
        
    Returns:
        Tuple of (TrendDirection, trend_description)
    """
    if not quantitative_signals:
        return TrendDirection.UNKNOWN, "No KPI data available"
    
    # Extract health statuses from signals
    health_statuses = []
    previous_health_status = None
    current_health_status = None
    
    for signal in quantitative_signals:
        payload = signal.payload
        signal_type = payload.get('signal_type', '')
        
        # Check for account health score signal
        if signal_type == 'account_health_score':
            health_score = payload.get('overall_health_score')
            if health_score is not None:
                if health_score >= 67:
                    health_statuses.append('healthy')
                elif health_score >= 34:
                    health_statuses.append('at-risk')
                else:
                    health_statuses.append('critical')
        
        # Check for KPI health status
        health_status = payload.get('health_status')
        if health_status:
            health_statuses.append(health_status.lower())
    
    # Use current health score if available
    if current_health_score is not None:
        if current_health_score >= 67:
            current_health_status = 'healthy'
        elif current_health_score >= 34:
            current_health_status = 'at-risk'
        else:
            current_health_status = 'critical'
    
    # Determine trend from health statuses
    if len(health_statuses) >= 2:
        # Look for trend in health statuses
        unique_statuses = list(set(health_statuses))
        if len(unique_statuses) == 1:
            status = unique_statuses[0]
            return TrendDirection.STABLE, f"Health status stable at {status}"
        
        # Check for improving trend
        if 'critical' in unique_statuses and 'at-risk' in unique_statuses:
            if health_statuses[-1] == 'at-risk' and 'critical' in health_statuses[:-1]:
                return TrendDirection.IMPROVING, "critical → at-risk"
        if 'at-risk' in unique_statuses and 'healthy' in unique_statuses:
            if health_statuses[-1] == 'healthy' and 'at-risk' in health_statuses[:-1]:
                return TrendDirection.IMPROVING, "at-risk → healthy"
        
        # Check for declining trend
        if 'healthy' in unique_statuses and 'at-risk' in unique_statuses:
            if health_statuses[-1] == 'at-risk' and 'healthy' in health_statuses[:-1]:
                return TrendDirection.DECLINING, "healthy → at-risk"
        if 'at-risk' in unique_statuses and 'critical' in unique_statuses:
            if health_statuses[-1] == 'critical' and 'at-risk' in health_statuses[:-1]:
                return TrendDirection.DECLINING, "at-risk → critical"
        if 'healthy' in unique_statuses and 'critical' in unique_statuses:
            if health_statuses[-1] == 'critical' and 'healthy' in health_statuses[:-1]:
                return TrendDirection.DECLINING, "healthy → critical"
    
    # Use current health status if available
    if current_health_status:
        return TrendDirection.STABLE, f"Current health status: {current_health_status}"
    
    return TrendDirection.UNKNOWN, "Cannot determine trend from available data"


def analyze_signal_sentiment(
    qualitative_signals: List[SignalData]
) -> tuple:
    """
    Analyze aggregated sentiment from qualitative signals
    
    Args:
        qualitative_signals: List of qualitative SignalData objects
        
    Returns:
        Tuple of (SignalSentiment, summary_description)
    """
    if not qualitative_signals:
        return SignalSentiment.NEUTRAL, "No qualitative signals available"
    
    sentiments = []
    signal_summaries = []
    
    for signal in qualitative_signals:
        payload = signal.payload
        sentiment = payload.get('sentiment', 'neutral')
        signal_type = payload.get('signal_type', '')
        content = payload.get('content') or payload.get('text', '')
        
        # Normalize sentiment
        if sentiment in ['positive', 'good', 'happy', 'satisfied']:
            sentiments.append('positive')
        elif sentiment in ['negative', 'bad', 'frustrated', 'unhappy', 'dissatisfied']:
            sentiments.append('negative')
        else:
            sentiments.append('neutral')
        
        # Extract key themes from content
        if content:
            # Look for common themes
            content_lower = content.lower()
            if any(word in content_lower for word in ['frustrated', 'disappointed', 'concerned', 'issue', 'problem']):
                signal_summaries.append(f"Customer {sentiment}: {content[:100]}")
            elif any(word in content_lower for word in ['happy', 'satisfied', 'pleased', 'excellent', 'great']):
                signal_summaries.append(f"Customer {sentiment}: {content[:100]}")
            else:
                signal_summaries.append(f"{signal_type}: {content[:100]}")
    
    # Determine overall sentiment
    positive_count = sentiments.count('positive')
    negative_count = sentiments.count('negative')
    neutral_count = sentiments.count('neutral')
    
    if negative_count > positive_count and negative_count > neutral_count:
        sentiment = SignalSentiment.NEGATIVE
        summary = f"Customer frustrated with: {', '.join(signal_summaries[:3])}"
    elif positive_count > negative_count and positive_count > neutral_count:
        sentiment = SignalSentiment.POSITIVE
        summary = f"Customer happy with: {', '.join(signal_summaries[:3])}"
    elif negative_count > 0 and positive_count > 0:
        sentiment = SignalSentiment.MIXED
        summary = f"Mixed signals: {positive_count} positive, {negative_count} negative"
    else:
        sentiment = SignalSentiment.NEUTRAL
        summary = "Neutral signals, no strong sentiment"
    
    return sentiment, summary


def _calculate_decision_matrix_llm(
    input_data: SignalAnalystInput,
    openai_api_key: str,
    trend_direction: TrendDirection,
    kpi_health_trend: str,
    signal_sentiment: SignalSentiment,
    signal_summary: str
) -> DecisionMatrixResult:
    """
    Use LLM to intelligently correlate quantitative and qualitative data
    
    Args:
        input_data: SignalAnalystInput with signals
        openai_api_key: OpenAI API key
        trend_direction: KPI trend direction
        kpi_health_trend: Description of KPI trend
        signal_sentiment: Aggregated signal sentiment
        signal_summary: Summary of qualitative signals
        
    Returns:
        DecisionMatrixResult with LLM-generated alignment and reasoning
    """
    try:
        client = OpenAI(api_key=openai_api_key)
        
        # Build context from signals
        quantitative_context = []
        for signal in input_data.quantitative_signals[:10]:  # Limit to top 10
            payload = signal.payload
            signal_type = payload.get('signal_type', '')
            if signal_type == 'account_health_score':
                quantitative_context.append(f"Health Score: {payload.get('overall_health_score', 'N/A')} ({payload.get('health_status', 'unknown')})")
            elif signal_type == 'kpi_metric':
                quantitative_context.append(f"KPI: {payload.get('kpi_parameter', 'unknown')} - Status: {payload.get('health_status', 'unknown')}")
        
        qualitative_context = []
        for signal in input_data.qualitative_signals[:10]:  # Limit to top 10
            payload = signal.payload
            content = payload.get('content') or payload.get('text', '')
            sentiment = payload.get('sentiment', 'neutral')
            signal_type = payload.get('signal_type', '')
            if content:
                qualitative_context.append(f"{signal_type} ({sentiment}): {content[:150]}")
        
        # Build prompt with future extensibility in mind
        prompt = f"""You are an expert Customer Success analyst analyzing the correlation between quantitative (KPI) data and qualitative (customer signal) data.

**QUANTITATIVE DATA (KPI Trends):**
- Trend Direction: {trend_direction.value}
- KPI Health Trend: {kpi_health_trend}
- Current Health Score: {input_data.health_score if input_data.health_score else 'N/A'}
- Quantitative Context:
{chr(10).join(quantitative_context) if quantitative_context else '  No quantitative signals available'}

**QUALITATIVE DATA (Customer Signals):**
- Overall Sentiment: {signal_sentiment.value}
- Signal Summary: {signal_summary}
- Qualitative Context:
{chr(10).join(qualitative_context) if qualitative_context else '  No qualitative signals available'}

**YOUR TASK:**
Analyze the correlation between the quantitative KPI trends and qualitative customer signals to determine if they agree or disagree. Consider all signal types and their nuanced context.

**Decision Matrix:**
1. **AGREEMENT**: KPI declining + negative signals = Both point to same issue (high confidence churn risk)
2. **DISAGREEMENT**: KPI declining + positive signals = Conflicting signals (lower confidence, needs investigation)
3. **NEUTRAL**: KPI stable + mixed/neutral signals = Stable account, no immediate concerns
4. **POSITIVE_ALIGNMENT**: KPI improving + positive signals = Both confirm positive trajectory (expansion opportunity)
5. **INSUFFICIENT_DATA**: Cannot determine trend or insufficient signals

**CRITICAL ANALYSIS REQUIREMENTS:**
1. **Signal Differentiation**: Distinguish between different signal types (support tickets, product usage, meetings, escalations, etc.) and their relative importance
2. **Context Understanding**: Consider nuanced context (e.g., "tickets taking long" vs "product working well" - identify which issue is more critical)
3. **Pattern Recognition**: Look for subtle patterns in signal content that might explain KPI trends
4. **Future Extensibility**: Consider that additional signal channels may be added (playbook execution feedback, RAG DB insights, etc.) - your analysis should be structured to accommodate these
5. **Actionable Insights**: Provide specific, actionable recommendations for resolution based on the correlation analysis
6. **Confidence Calibration**: Confidence should reflect how strongly the data sources align, considering signal quality and quantity

**Respond in JSON format:**
{{
    "alignment": "agreement" | "disagreement" | "neutral" | "positive_alignment" | "insufficient_data",
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation of why quantitative and qualitative data align or conflict, including nuanced context, specific examples from signals, and differentiation between signal types",
    "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
    "recommended_actions": ["Action 1 for resolution", "Action 2 for resolution", "Action 3 for resolution"]
}}"""

        # Call LLM
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use cheaper model for decision matrix
            messages=[
                {"role": "system", "content": "You are an expert Customer Success analyst specializing in correlating quantitative metrics with qualitative customer signals."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1200,  # Increased for recommended_actions
            response_format={"type": "json_object"}
        )
        
        # Parse response
        result_data = json.loads(response.choices[0].message.content)
        
        # Map alignment string to enum
        alignment_str = result_data.get('alignment', 'insufficient_data')
        alignment_map = {
            'agreement': DataAlignment.AGREEMENT,
            'disagreement': DataAlignment.DISAGREEMENT,
            'neutral': DataAlignment.NEUTRAL,
            'positive_alignment': DataAlignment.POSITIVE_ALIGNMENT,
            'insufficient_data': DataAlignment.INSUFFICIENT_DATA
        }
        alignment = alignment_map.get(alignment_str, DataAlignment.INSUFFICIENT_DATA)
        
        # Get confidence and reasoning
        confidence = float(result_data.get('confidence', 0.5))
        confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
        
        reasoning = result_data.get('reasoning', '')
        key_insights = result_data.get('key_insights', [])
        recommended_actions = result_data.get('recommended_actions', [])
        
        # Enhance reasoning with key insights and recommended actions
        if key_insights:
            reasoning += f"\n\nKey Insights: {'; '.join(key_insights)}"
        if recommended_actions:
            reasoning += f"\n\nRecommended Actions for Quicker Resolution: {'; '.join(recommended_actions)}"
        
        logger.info(f"LLM Decision Matrix: {alignment.value} (confidence: {confidence:.2f})")
        
        return DecisionMatrixResult(
            alignment=alignment,
            trend_direction=trend_direction,
            signal_sentiment=signal_sentiment,
            kpi_health_trend=kpi_health_trend,
            signal_summary=signal_summary,
            confidence=confidence,
            reasoning=reasoning,
            recommended_actions=recommended_actions  # LLM provides actionable recommendations
        )
        
    except Exception as e:
        logger.warning(f"LLM decision matrix failed: {e}, falling back to rule-based", exc_info=True)
        raise  # Will fall back to rule-based


def _calculate_decision_matrix_rule_based(
    trend_direction: TrendDirection,
    kpi_health_trend: str,
    signal_sentiment: SignalSentiment,
    signal_summary: str
) -> DecisionMatrixResult:
    """
    Fallback rule-based decision matrix (used if LLM fails)
    """
    alignment = DataAlignment.INSUFFICIENT_DATA
    confidence = 0.5
    reasoning = ""
    
    # Decision Matrix Logic (rule-based)
    if trend_direction == TrendDirection.DECLINING:
        if signal_sentiment == SignalSentiment.NEGATIVE:
            alignment = DataAlignment.AGREEMENT
            confidence = 0.85
            reasoning = f"AGREEMENT: KPI data shows declining trend ({kpi_health_trend}) and qualitative signals indicate customer frustration ({signal_summary}). Both data sources point to the same underlying issue. High confidence in churn risk prediction."
        elif signal_sentiment == SignalSentiment.POSITIVE:
            alignment = DataAlignment.DISAGREEMENT
            confidence = 0.60
            reasoning = f"DISAGREEMENT: KPI data shows declining trend ({kpi_health_trend}) but qualitative signals indicate customer satisfaction ({signal_summary}). Conflicting signals suggest either: (1) KPI lagging indicator, (2) Temporary KPI dip, or (3) Need for deeper investigation. Lower confidence in churn risk prediction - recommend follow-up call."
        elif signal_sentiment == SignalSentiment.MIXED:
            alignment = DataAlignment.DISAGREEMENT
            confidence = 0.55
            reasoning = f"DISAGREEMENT: KPI data shows declining trend ({kpi_health_trend}) but qualitative signals are mixed ({signal_summary}). Conflicting signals require investigation. Recommend follow-up call to clarify situation."
        else:
            alignment = DataAlignment.NEUTRAL
            confidence = 0.50
            reasoning = f"NEUTRAL: KPI data shows declining trend ({kpi_health_trend}) but qualitative signals are neutral ({signal_summary}). Insufficient qualitative context to confirm KPI trend. Recommend monitoring and proactive engagement."
    
    elif trend_direction == TrendDirection.IMPROVING:
        if signal_sentiment == SignalSentiment.POSITIVE:
            alignment = DataAlignment.POSITIVE_ALIGNMENT
            confidence = 0.80
            reasoning = f"POSITIVE_ALIGNMENT: KPI data shows improving trend ({kpi_health_trend}) and qualitative signals indicate customer satisfaction ({signal_summary}). Both data sources confirm positive trajectory. Good opportunity for expansion discussions."
        elif signal_sentiment == SignalSentiment.NEGATIVE:
            alignment = DataAlignment.DISAGREEMENT
            confidence = 0.60
            reasoning = f"DISAGREEMENT: KPI data shows improving trend ({kpi_health_trend}) but qualitative signals indicate concerns ({signal_summary}). Conflicting signals suggest either: (1) Recent improvement not yet reflected in sentiment, (2) KPI improvement may be temporary, or (3) Need for deeper investigation. Recommend follow-up call to understand customer perspective."
        else:
            alignment = DataAlignment.NEUTRAL
            confidence = 0.65
            reasoning = f"NEUTRAL: KPI data shows improving trend ({kpi_health_trend}) but qualitative signals are neutral/mixed ({signal_summary}). Positive KPI trend is encouraging, but need more qualitative feedback."
    
    elif trend_direction == TrendDirection.STABLE:
        if signal_sentiment == SignalSentiment.NEGATIVE:
            alignment = DataAlignment.DISAGREEMENT
            confidence = 0.55
            reasoning = f"DISAGREEMENT: KPI data shows stable trend ({kpi_health_trend}) but qualitative signals indicate concerns ({signal_summary}). Qualitative signals may be leading indicator of future KPI decline. Recommend proactive engagement."
        elif signal_sentiment == SignalSentiment.POSITIVE:
            alignment = DataAlignment.NEUTRAL
            confidence = 0.70
            reasoning = f"NEUTRAL: KPI data shows stable trend ({kpi_health_trend}) and qualitative signals are positive ({signal_summary}). Stable account with positive sentiment. Monitor for expansion opportunities."
        else:
            alignment = DataAlignment.NEUTRAL
            confidence = 0.60
            reasoning = f"NEUTRAL: KPI data shows stable trend ({kpi_health_trend}) and qualitative signals are neutral/mixed ({signal_summary}). Stable account, no immediate concerns or opportunities."
    
    else:
        alignment = DataAlignment.INSUFFICIENT_DATA
        confidence = 0.30
        reasoning = f"INSUFFICIENT_DATA: Cannot determine KPI trend ({kpi_health_trend}). Qualitative signals: {signal_summary}. Need more data to make informed decision."
    
    return DecisionMatrixResult(
        alignment=alignment,
        trend_direction=trend_direction,
        signal_sentiment=signal_sentiment,
        kpi_health_trend=kpi_health_trend,
        signal_summary=signal_summary,
        confidence=confidence,
        reasoning=reasoning
    )


def calculate_decision_matrix(
    input_data: SignalAnalystInput,
    openai_api_key: Optional[str] = None,
    use_llm: bool = True  # Default to LLM for better context and future extensibility
) -> DecisionMatrixResult:
    """
    Calculate decision matrix comparing quantitative and qualitative data
    
    Uses LLM by default for nuanced correlation analysis, better context understanding,
    and future extensibility (playbook feedback, additional signal channels).
    Falls back to rule-based if LLM unavailable.
    
    Args:
        input_data: SignalAnalystInput with quantitative and qualitative signals
        openai_api_key: OpenAI API key (required if use_llm=True)
        use_llm: Whether to use LLM (True, default) or rule-based (False)
        
    Returns:
        DecisionMatrixResult with alignment, trend, sentiment, and reasoning
    """
    # Analyze KPI health trend
    trend_direction, kpi_health_trend = analyze_kpi_health_trend(
        input_data.quantitative_signals,
        input_data.health_score
    )
    
    # Analyze signal sentiment
    signal_sentiment, signal_summary = analyze_signal_sentiment(
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
                signal_summary=signal_summary
            )
        except Exception as e:
            logger.warning(f"LLM decision matrix failed, using rule-based fallback: {e}")
            # Fall through to rule-based
    
    # Use rule-based logic (default)
    return _calculate_decision_matrix_rule_based(
        trend_direction=trend_direction,
        kpi_health_trend=kpi_health_trend,
        signal_sentiment=signal_sentiment,
        signal_summary=signal_summary
    )
