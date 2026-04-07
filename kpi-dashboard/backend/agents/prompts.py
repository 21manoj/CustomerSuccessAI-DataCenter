"""
Prompt templates for Signal Analyst Agent
Carefully engineered for accuracy and consistency
"""

from typing import List, Dict, Optional

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
        health_score: Optional[float],
        quantitative_context: str,
        qualitative_context: str,
        historical_context: str,
        analysis_type: str,
        time_horizon_days: int
    ) -> str:
        """
        Get user prompt for analysis
        """
        from typing import Optional
        
        arr_context = f"${account_arr:,.0f}" if account_arr else "Unknown"
        
        # Format health score context
        if health_score is not None:
            if health_score >= 67:
                health_status = "Healthy"
            elif health_score >= 34:
                health_status = "At-Risk"
            else:
                health_status = "Critical"
            health_context = f"{health_score:.1f}/100 ({health_status})"
        else:
            health_context = "Not available"
        
        prompt = f"""Analyze the following account and predict the most likely outcome within {time_horizon_days} days.

**ACCOUNT INFORMATION**
- Account ID: {account_id}
- Account Name: {account_name}
- Annual Recurring Revenue: {arr_context}
- Overall Health Score: {health_context}

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
  
  "reasoning": "<detailed explanation in markdown format. MUST include: ## KPI vs Signal Channel section (see rules below). Use headers (##), bold, numbered lists, and bullet points. Cite specific references [K1], [Q2] etc.>",

  "key_insights": [
    "<insight citing [Kn] and/or [Qn] references>",
    "<insight 2>",
    "<insight 3>"
  ],

  "data_alignment": {{
    "alignment": "<agree|disagree|mixed>",
    "kpi_summary": "<one line: which KPIs drive the assessment, citing [K1]-[Kn]>",
    "signal_summary": "<one line: which signals drive the assessment, citing [Q1]-[Qn]>",
    "combined_reason": "<one line: why at-risk or healthy, combining both channels>"
  }},

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
1. **Account Health Context**: Use the overall health score as primary context for all predictions:
   - Health score < 50 = High churn risk, focus on retention
   - Health score 50-70 = At-risk, monitor closely and engage proactively
   - Health score > 70 = Healthy, focus on expansion opportunities
2. **Temporal Correlation**: Both [Kn] and [Qn] signals include dates. USE THEM to find cause-and-effect:
   - If [Q1] champion_loss on Mar 15 and [K2] usage dropped on Mar 22 → [Q1] CAUSED [K2] (7-day lag = intervention window)
   - Multiple signals in same week → correlated events, cite all
   - The GAP between a qualitative signal and the KPI change is the INTERVENTION WINDOW — call it out explicitly
   - Example: "[Q1] champion loss (Mar 15) preceded [K2] GPU utilization crash (Mar 22) by 7 days — this was the window for intervention"
3. Base predictions ONLY on signals provided, not assumptions
4. If signals conflict, explain the conflict and weight them appropriately
5. Consider signal recency (recent signals matter more, especially last 4 weeks)
6. Consider signal severity (critical signals override low severity)
7. External signals (funding, exec changes) can override internal signals
8. Be honest about confidence - if data is sparse or contradictory, say so
9. Provide SPECIFIC actions, not vague advice ("Schedule call with CTO" not "Improve engagement")

**CITATION RULES** (mandatory):
10. **Cite KPI references**: In reasoning, key_insights, and supporting_signals, cite specific KPIs using their [K1]-[Kn] references from the QUANTITATIVE SIGNALS section. Say "[K2] GPU utilization at 38%" not "usage is declining".
11. **Cite signal references**: Cite specific qualitative signals using their [Q1]-[Qn] references from the QUALITATIVE SIGNALS section. Say "[Q3] email from CTO indicates competitive evaluation" not "signals suggest churn".
12. **Stakeholder attribution**: When a qualitative signal is from an Executive or Champion (marked in the signal), mention the role. "[Q2] from CTO" carries more weight than "[Q5] routine check-in".
13. **Only cite references that exist**: Only use [K1]-[Kn] and [Q1]-[Qn] references provided in the input. Never invent references.

**KPI vs SIGNAL CHANNEL CORRELATION** (mandatory):
14. **Include a ## KPI vs Signal Channel section in reasoning** that explicitly states:
    - Whether KPIs and qualitative signals **agree**, **disagree**, or are **mixed**
    - The **combined reason** for your prediction using both channels:
      - KPIs healthy + signals bad → "At-risk due to relationship/experience, not usage. [K1],[K2] in range but [Q1] champion loss + [Q3] competitor mention = churn risk."
      - Signals positive + KPIs declining → "At-risk despite engagement. [Q1] positive QBR but [K2],[K4] declining = usage/adoption problem."
      - Both bad → "Clear at-risk. Both [K1]-[K3] and [Q1]-[Q3] negative."
      - Both good → "Healthy. [K1]-[K3] in range, [Q1] positive engagement."
15. **Populate data_alignment**: Fill the data_alignment JSON with alignment (agree/disagree/mixed), kpi_summary, signal_summary, and combined_reason citing specific [Kn] and [Qn] refs.
"""
        
        return prompt.strip()
    
    @staticmethod
    def format_quantitative_signals(signals: List[Dict]) -> str:
        """Format quantitative signals with stable [K1]-[Kn] references, dates, and ranges.

        Each KPI gets a traceable ref + measurement date so the LLM can
        build a timeline: '[K2] Mar 22: GPU utilization = 52% ⚠ below target'.
        Signals are sorted chronologically for temporal correlation.
        """
        if not signals:
            return "No quantitative signals available"

        # Sort by date (most recent last = natural timeline reading)
        def _sort_key(s):
            p = s.get('payload', {})
            d = p.get('measurement_month') or p.get('measurement_date') or p.get('date') or ''
            return str(d)

        sorted_signals = sorted(signals[:20], key=_sort_key)

        context_lines = []
        for i, signal in enumerate(sorted_signals[:15], 1):  # Top 15 KPIs
            payload = signal.get('payload', {})

            pillar = payload.get('pillar', 'unknown')
            metric_type = payload.get('metric_type', 'unknown')
            current_value = payload.get('current_value', 0)
            trend = payload.get('trend', 0)
            healthy_min = payload.get('healthy_min')
            healthy_max = payload.get('healthy_max')
            kpi_code = payload.get('kpi_code', '')

            # Date context
            raw_date = payload.get('measurement_month') or payload.get('measurement_date') or payload.get('date') or ''
            date_str = ''
            if raw_date:
                # Format: "Mar 22" or "2026-03" → "Mar 2026"
                try:
                    from datetime import datetime as _dt
                    if len(str(raw_date)) <= 7:  # YYYY-MM
                        d = _dt.strptime(str(raw_date)[:7], '%Y-%m')
                        date_str = d.strftime('%b %Y')
                    else:
                        d = _dt.fromisoformat(str(raw_date)[:10])
                        date_str = d.strftime('%b %d')
                except (ValueError, TypeError):
                    date_str = str(raw_date)[:10]

            trend_direction = "↑" if trend > 0 else "↓" if trend < 0 else "→"
            trend_magnitude = abs(trend * 100)

            # Value vs range context
            range_ctx = ""
            if healthy_min is not None and healthy_max is not None:
                if current_value < healthy_min:
                    range_ctx = f" ⚠ BELOW target range [{healthy_min}-{healthy_max}]"
                elif current_value > healthy_max:
                    range_ctx = f" ⚠ ABOVE target range [{healthy_min}-{healthy_max}]"
                else:
                    range_ctx = f" ✓ in range [{healthy_min}-{healthy_max}]"
            elif healthy_min is not None:
                if current_value < healthy_min:
                    range_ctx = f" ⚠ below target (>{healthy_min})"
                else:
                    range_ctx = f" ✓ above target (>{healthy_min})"

            kpi_label = f" ({kpi_code})" if kpi_code else ""
            date_prefix = f" {date_str}:" if date_str else ""

            context_lines.append(
                f"[K{i}]{date_prefix} [{pillar.upper()}] {metric_type}{kpi_label} = {current_value}"
                f" ({trend_direction} {trend_magnitude:.1f}% trend){range_ctx}"
            )

        return "\n".join(context_lines)
    
    # Stakeholder role normalization for high-impact signal attribution
    _EXECUTIVE_KEYWORDS = {
        'ceo', 'cto', 'cio', 'cfo', 'coo', 'ciso', 'cmo', 'cro',
        'vp', 'vice president', 'svp', 'evp', 'president', 'chief',
        'director', 'head of', 'general manager',
    }
    _CHAMPION_KEYWORDS = {'champion', 'sponsor', 'advocate'}

    @classmethod
    def _normalize_sender_role(cls, title: str, level: str) -> str:
        """Derive sender_role from stakeholder_title and stakeholder_level.

        Returns: 'executive', 'champion', or '' (empty = no special role).
        """
        combined = f"{title} {level}".lower()
        if any(kw in combined for kw in cls._CHAMPION_KEYWORDS):
            return 'Champion'
        if any(kw in combined for kw in cls._EXECUTIVE_KEYWORDS):
            return 'Executive'
        return ''

    @staticmethod
    def format_qualitative_signals(signals: List[Dict]) -> str:
        """Format qualitative signals with stable [Q1]-[Qn] references, dates, and stakeholder roles.

        Each signal gets a traceable ref + date so the LLM can build a timeline:
        '[Q2] Mar 15: [champion_loss] From: Sarah, CTO [Executive] — VP departed...'
        Signals are sorted chronologically for temporal correlation with KPIs.
        """
        if not signals:
            return "No qualitative signals available"

        # Sort by date (chronological — oldest first for timeline reading)
        def _sort_key(s):
            p = s.get('payload', {})
            d = p.get('signal_date') or p.get('date') or p.get('occurred_at') or ''
            return str(d)

        sorted_signals = sorted(signals[:20], key=_sort_key)

        context_lines = []
        for i, signal in enumerate(sorted_signals[:15], 1):  # Top 15 signals
            payload = signal.get('payload', {})

            signal_type = payload.get('signal_type', 'unknown')
            signal_source = payload.get('signal_source', 'internal')
            sentiment = payload.get('sentiment', 'neutral')
            severity = payload.get('severity', 'medium')
            text = payload.get('text', '')[:200]

            # Date context
            raw_date = payload.get('signal_date') or payload.get('date') or payload.get('occurred_at') or ''
            date_str = ''
            if raw_date:
                try:
                    from datetime import datetime as _dt
                    if isinstance(raw_date, str) and len(raw_date) >= 10:
                        d = _dt.fromisoformat(raw_date[:10])
                        date_str = d.strftime('%b %d')
                    elif hasattr(raw_date, 'strftime'):
                        date_str = raw_date.strftime('%b %d')
                    else:
                        date_str = str(raw_date)[:10]
                except (ValueError, TypeError):
                    date_str = str(raw_date)[:10]

            # Stakeholder attribution
            stakeholder_title = payload.get('stakeholder_title', '')
            stakeholder_level = payload.get('stakeholder_level', '')
            stakeholder_name = payload.get('stakeholder_name', '')
            sender_role = SignalAnalystPrompts._normalize_sender_role(
                stakeholder_title or '', stakeholder_level or '',
            )

            source_indicator = "🌐" if signal_source == "external" else "💬"

            # Build "From:" line when stakeholder info available
            from_ctx = ""
            if stakeholder_title or stakeholder_name:
                parts = []
                if stakeholder_name:
                    parts.append(stakeholder_name)
                if stakeholder_title:
                    parts.append(stakeholder_title)
                if sender_role:
                    parts.append(f"[{sender_role}]")
                from_ctx = f" From: {', '.join(parts)} —"

            date_prefix = f" {date_str}:" if date_str else ""

            context_lines.append(
                f"[Q{i}]{date_prefix} [{signal_type}] {source_indicator} "
                f"({sentiment}/{severity}){from_ctx} {text}"
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

