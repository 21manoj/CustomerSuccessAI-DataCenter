"""
Prompt templates for Signal Analyst Agent
Carefully engineered for accuracy and consistency
"""

from typing import List, Dict

class SignalAnalystPrompts:
    """
    Prompt templates for different analysis types
    """
    
    @staticmethod
    def get_system_prompt(vertical_type: str) -> str:
        """
        Get system prompt based on vertical type
        """
        
        base_prompt = """You are an expert Customer Success AI analyst specializing in churn prediction and expansion opportunity identification.

Your role is to analyze customer signals (usage patterns, support interactions, financial trends, external market events) to predict outcomes and recommend actions.

Key principles:
1. **Data-driven**: Base predictions on actual signals, not assumptions
2. **Explainable**: Always explain WHY you predict an outcome
3. **Actionable**: Provide specific, executable recommendations
4. **Honest**: If confidence is low, say so. Don't overstate certainty.
5. **Nuanced**: Consider signal interactions (e.g., low usage + champion left = high risk)
"""
        
        if vertical_type == "saas_customer_success":
            specific_context = """
Vertical: SaaS Customer Success

Key churn indicators:
- Usage decline (DAU/MAU/feature adoption dropping)
- Champion departure (main advocate left company)
- Support ticket spike (especially integration/bug issues)
- Payment failures or downgrade requests
- Negative sentiment in NPS/support interactions

Key expansion indicators:
- Usage growth (hitting plan limits, requesting more)
- Positive NPS trends
- Feature adoption breadth (using more features = stickiness)
- External signals (funding raised, product launches)
- Executive engagement increasing
"""
        
        elif vertical_type == "data_center_infrastructure":
            specific_context = """
Vertical: Data Center Infrastructure (GPU/Hardware)

Key churn indicators:
- GPU health degradation (ECC errors, thermal issues)
- Utilization declining (infrastructure not being used)
- RMA spike (hardware failures causing frustration)
- Support escalations (unresolved hardware issues)
- Competitor evaluation (mentions of alternative vendors)

Key expansion indicators:
- High utilization (nearing capacity)
- External signals (funding for infrastructure expansion)
- Performance benchmarks met or exceeded
- Proactive maintenance requests (long-term commitment signal)
- New workload types being tested
"""
        else:
            specific_context = f"""
Vertical: {vertical_type}

Apply general customer success principles to predict outcomes.
"""
        
        return base_prompt + specific_context
    
    @staticmethod
    def get_analysis_prompt(
        account_id: str,
        account_name: str,
        account_arr: float,
        quantitative_context: str,
        qualitative_context: str,
        historical_context: str,
        analysis_type: str,
        time_horizon_days: int
    ) -> str:
        """
        Get user prompt for analysis
        """
        
        arr_context = f"${account_arr:,.0f}" if account_arr else "Unknown"
        
        prompt = f"""Analyze the following account and predict the most likely outcome within {time_horizon_days} days.

**ACCOUNT INFORMATION**
- Account ID: {account_id}
- Account Name: {account_name}
- Annual Recurring Revenue: {arr_context}

**QUANTITATIVE SIGNALS** ({quantitative_context.count('Signal') if quantitative_context else 0} signals)
{quantitative_context if quantitative_context else "No quantitative signals available"}

**QUALITATIVE SIGNALS** ({qualitative_context.count('Signal') if qualitative_context else 0} signals)
{qualitative_context if qualitative_context else "No qualitative signals available"}

**HISTORICAL PATTERNS** ({historical_context.count('Pattern') if historical_context else 0} similar cases)
{historical_context if historical_context else "No historical patterns available"}

---

**ANALYSIS REQUIREMENTS**

Provide your analysis in the following JSON format (respond ONLY with valid JSON, no markdown code blocks):

{{
  "predicted_outcome": "<churn|expansion|stable|downgrade|contraction>",
  "churn_probability": <0-100>,
  "expansion_probability": <0-100>,
  "health_score": <0-100>,
  "time_to_event": "<e.g., '45-60 days' or '90+ days' or 'immediate'>",
  
  "risk_drivers": [
    {{
      "driver": "<specific risk description>",
      "impact": "<critical|high|medium|low>",
      "supporting_signals": ["<signal 1>", "<signal 2>"],
      "confidence": <0.0-1.0>
    }}
  ],
  
  "growth_drivers": [
    {{
      "driver": "<specific opportunity description>",
      "impact": "<critical|high|medium|low>",
      "supporting_signals": ["<signal 1>", "<signal 2>"],
      "confidence": <0.0-1.0>
    }}
  ],
  
  "confidence": {{
    "overall_confidence": <0.0-1.0>,
    "confidence_factors": {{
      "signal_quality": <0.0-1.0>,
      "signal_quantity": <0.0-1.0>,
      "historical_matches": <0.0-1.0>,
      "pattern_clarity": <0.0-1.0>
    }}
  }},
  
  "reasoning": "<detailed explanation of your prediction, 3-5 sentences>",
  
  "key_insights": [
    "<insight 1>",
    "<insight 2>",
    "<insight 3>"
  ],
  
  "recommended_actions": [
    {{
      "action": "<specific action to take>",
      "priority": "<immediate|high|medium|low>",
      "owner": "<CSM|SE|Executive|Product|Engineering>",
      "deadline_days": <number or null>,
      "expected_impact": "<what will happen if action taken>"
    }}
  ]
}}

**CRITICAL RULES**:
1. Base predictions ONLY on signals provided, not assumptions
2. If signals conflict, explain the conflict and weight them appropriately
3. Consider signal recency (recent signals matter more)
4. Consider signal severity (critical signals override low severity)
5. Look for patterns across quantitative + qualitative signals
6. External signals (funding, exec changes) can override internal signals
7. Be honest about confidence - if data is sparse or contradictory, say so
8. Provide SPECIFIC actions, not vague advice ("Schedule call with CTO" not "Improve engagement")
"""
        
        return prompt.strip()
    
    @staticmethod
    def format_quantitative_signals(signals: List[Dict]) -> str:
        """Format quantitative signals for prompt"""
        if not signals:
            return "No quantitative signals available"
        
        context_lines = []
        for i, signal in enumerate(signals[:10], 1):  # Top 10 signals
            payload = signal.get('payload', {})
            
            pillar = payload.get('pillar', 'unknown')
            metric_type = payload.get('metric_type', 'unknown')
            current_value = payload.get('current_value', 0)
            trend = payload.get('trend', 0)
            
            trend_direction = "↑" if trend > 0 else "↓"
            trend_magnitude = abs(trend * 100)
            
            context_lines.append(
                f"Signal {i} [{pillar.upper()}]: {metric_type} = {current_value} "
                f"({trend_direction} {trend_magnitude:.1f}% trend)"
            )
        
        return "\n".join(context_lines)
    
    @staticmethod
    def format_qualitative_signals(signals: List[Dict]) -> str:
        """Format qualitative signals for prompt"""
        if not signals:
            return "No qualitative signals available"
        
        context_lines = []
        for i, signal in enumerate(signals[:10], 1):  # Top 10 signals
            payload = signal.get('payload', {})
            
            signal_type = payload.get('signal_type', 'unknown')
            signal_source = payload.get('signal_source', 'internal')
            sentiment = payload.get('sentiment', 'neutral')
            severity = payload.get('severity', 'medium')
            text = payload.get('text', '')[:200]  # Truncate long text
            
            source_indicator = "🌐" if signal_source == "external" else "💬"
            
            context_lines.append(
                f"Signal {i} [{signal_type}] {source_indicator}: "
                f"({sentiment}/{severity}) {text}"
            )
        
        return "\n".join(context_lines)
    
    @staticmethod
    def format_historical_patterns(patterns: List[Dict]) -> str:
        """Format historical patterns for prompt"""
        if not patterns:
            return "No historical patterns available"
        
        context_lines = []
        for i, pattern in enumerate(patterns[:5], 1):  # Top 5 patterns
            payload = pattern.get('payload', {})
            
            outcome_type = payload.get('outcome_type', 'unknown')
            signals_summary = payload.get('signals_summary', '')[:300]
            
            context_lines.append(
                f"Pattern {i} [Outcome: {outcome_type.upper()}]: {signals_summary}"
            )
        
        return "\n".join(context_lines)

