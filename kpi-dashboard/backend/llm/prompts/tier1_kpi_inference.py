"""
Prompt templates for Tier 1 KPI-based context inference.

Used by tier1_inference.py to ask Claude to infer signals, outcomes,
decisions, and causal edges from KPI time series + health scores alone.

Two modes:
- Full inference: infer signals + decisions + outcomes + edges (2-CSV mode)
- Edge enrichment: signals exist from CSV; infer decisions + outcomes + causal edges (3-CSV mode)
"""

SYSTEM_PROMPT = """You are a Customer Success analyst AI for CS Pulse, a B2B revenue intelligence platform.

You are given KPI time series, health score trajectories, product portfolio, and stakeholder context
for a batch of customer accounts. Your job is to INFER what likely happened — what signals fired,
what decisions were made, and what outcomes occurred — using the data patterns AND contextual clues.

RULES:
- Only infer events that the data strongly supports. Don't fabricate.
- Each inference must have a confidence score (0.5-0.9). Higher = more certain.
- Signals should precede decisions, which should precede outcomes (temporal ordering).
- Use specific dates from the KPI data (when a metric changed significantly).
- Do NOT include revenue_impact in outcomes — revenue is computed deterministically by the platform from health scores × ARR. Your job is to infer the outcome TYPE, not the dollar amount.
- If health is stable (±5 points), infer minimal events — don't over-explain stability.
- Reference specific PRODUCTS when a KPI change maps to a product (e.g., "GPU Compute utilization declined").
- Reference STAKEHOLDERS by name when inferring decisions (e.g., "CTO Michael Torres likely escalated").
- When renewal is < 90 days AND health < 60, always infer a churn_risk or renewal_risk signal.

SIGNAL TYPE GUIDANCE (use these HIGH_RISK types when evidence supports them):
- champion_loss / champion_change: Champion engagement score < 40, or stakeholder sentiment=departed
- stakeholder_departure / executive_change: Key role changes visible in engagement patterns
- budget_cut / budget_pressure: Sudden ARR contraction, capacity utilization drops
- usage_decline / engagement_gap: DAU/adoption drops > 20%, product adoption declining
- escalation / support_escalation: Ticket resolution time spikes, escalation rate increases
- competitor_mention: Usage decline + engagement gap together (competitive displacement pattern)
- critical_incident: Uptime drops, MTBF spikes, SLA violations

OUTPUT FORMAT: Return a JSON object for each account. Do NOT include markdown formatting."""

ACCOUNT_TEMPLATE = """Account: {account_name}
ARR: ${arr:,.0f}
Industry: {industry}
Products: {products}
Key Stakeholders: {stakeholders}
Product Adoption Score: {product_adoption}
Contract: {contract_info}
Health trajectory (monthly): {health_trajectory}
Current health: {current_health} ({health_status})
Health change: {health_delta:+.1f} over {months} months

Top KPI changes (biggest movers):
{kpi_changes}
"""

BATCH_PROMPT = """Analyze these {n_accounts} accounts and infer what likely happened.

{accounts_block}

For EACH account, return a JSON object with this exact schema:
{{
  "account_name": "...",
  "inferred_signals": [
    {{
      "type": "champion_loss|champion_change|stakeholder_departure|executive_change|budget_cut|budget_pressure|usage_decline|engagement_gap|escalation|support_escalation|critical_incident|competitor_mention|nps_decline|feature_adoption_drop|churn_risk",
      "date": "YYYY-MM-DD",
      "content": "Brief description of what likely happened",
      "sentiment": "negative|neutral|positive",
      "confidence": 0.5-0.9
    }}
  ],
  "inferred_outcomes": [
    {{
      "type": "churn_risk|revenue_at_risk|churn_averted|revenue_protected|expansion_opportunity|renewal_secured",
      "date": "YYYY-MM-DD",
      "title": "Brief title",
      "confidence": 0.5-0.9
    }}
  ],
  "inferred_decisions": [
    {{
      "type": "escalation|intervention|renewal_strategy|feature_adoption_push|executive_engagement",
      "date": "YYYY-MM-DD",
      "title": "Brief description of decision likely made",
      "confidence": 0.5-0.9
    }}
  ],
  "causal_chain": "Brief 1-sentence narrative: signal → decision → outcome"
}}

Return a JSON array of objects, one per account. Only include accounts where you infer meaningful events (skip stable accounts with no significant changes).
"""

# Few-shot example for the prompt (appended when available)
FEW_SHOT_EXAMPLE = """
EXAMPLE INPUT:
Account: Acme Corp
ARR: $12,000,000
Health trajectory: [78, 76, 72, 58, 42, 38]
Current health: 38 (critical)
Health change: -40.0 over 6 months
Top KPI changes: P1-KPI1 (DAU) dropped 65% in month 3-4, P3-KPI2 (NPS) dropped from 45→12 in month 4

EXAMPLE OUTPUT:
{
  "account_name": "Acme Corp",
  "inferred_signals": [
    {
      "type": "usage_decline",
      "date": "2025-12-15",
      "content": "DAU dropped 65% over 4 weeks — likely team change or champion departure disrupted adoption",
      "sentiment": "negative",
      "confidence": 0.85
    },
    {
      "type": "nps_decline",
      "date": "2026-01-15",
      "content": "NPS collapsed from 45 to 12 — deep dissatisfaction spreading beyond initial trigger",
      "sentiment": "negative",
      "confidence": 0.9
    }
  ],
  "inferred_outcomes": [
    {
      "type": "revenue_at_risk",
      "date": "2026-02-01",
      "title": "Revenue at Risk — Acme Corp",
      "confidence": 0.8
    }
  ],
  "inferred_decisions": [
    {
      "type": "escalation",
      "date": "2026-01-01",
      "title": "Likely escalation to executive sponsor after health crossed critical threshold",
      "confidence": 0.7
    }
  ],
  "causal_chain": "Usage decline (DAU -65%) triggered escalation, but intervention came too late — NPS collapsed, $6M ARR at risk"
}
"""

# ═══════════════════════════════════════════════════════════════════════════════
# Edge Enrichment Mode — signals exist from CSV, infer decisions + outcomes + edges
# ═══════════════════════════════════════════════════════════════════════════════

EDGE_ENRICHMENT_SYSTEM_PROMPT = """You are a Customer Success analyst AI for CS Pulse, a B2B revenue intelligence platform.

You are given KPI time series, health score trajectories, AND existing qualitative signals
for a batch of customer accounts. The signals are REAL observations from the field — they
were uploaded by the CS team, not inferred. Your job is to CONNECT THE DOTS:

1. Infer what DECISIONS were likely made in response to these signals.
2. Infer what OUTCOMES resulted from the combination of signals + decisions.
3. Map the CAUSAL EDGES: which signal led to which decision, which decision led to which outcome.

RULES:
- Do NOT infer new signals — they already exist from CSV. Reference them by their signal_ref.
- Each inference must have a confidence score (0.5-0.9).
- Temporal ordering: signals precede decisions, decisions precede outcomes.
- Use specific dates from the signals and KPI data.
- Do NOT include revenue_impact in outcomes — revenue is computed deterministically by the platform.
- Reference specific PRODUCTS and STAKEHOLDERS when available.
- When multiple signals cluster in time (within 30 days), they likely share a causal chain.
- Create edges between existing signals when one clearly caused or amplified another.

OUTPUT FORMAT: Return a JSON object for each account. Do NOT include markdown formatting."""

EDGE_ENRICHMENT_ACCOUNT_TEMPLATE = """Account: {account_name}
ARR: ${arr:,.0f}
Industry: {industry}
Products: {products}
Key Stakeholders: {stakeholders}
Product Adoption Score: {product_adoption}
Contract: {contract_info}
Health trajectory (monthly): {health_trajectory}
Current health: {current_health} ({health_status})
Health change: {health_delta:+.1f} over {months} months

Top KPI changes (biggest movers):
{kpi_changes}

Existing signals (from CSV — these are REAL observations, reference by signal_ref):
{existing_signals}
"""

EDGE_ENRICHMENT_BATCH_PROMPT = """Analyze these {n_accounts} accounts. Signals already exist — your job is to infer DECISIONS, OUTCOMES, and CAUSAL EDGES that connect the story.

{accounts_block}

For EACH account, return a JSON object with this exact schema:
{{
  "account_name": "...",
  "inferred_decisions": [
    {{
      "type": "escalation|intervention|renewal_strategy|feature_adoption_push|executive_engagement|resource_reallocation|contract_negotiation",
      "date": "YYYY-MM-DD",
      "title": "Brief description of decision likely made",
      "confidence": 0.5-0.9,
      "triggered_by_signals": ["signal_ref_1", "signal_ref_2"]
    }}
  ],
  "inferred_outcomes": [
    {{
      "type": "churn_risk|revenue_at_risk|churn_averted|revenue_protected|expansion_opportunity|renewal_secured|partial_recovery|escalation_resolved",
      "date": "YYYY-MM-DD",
      "title": "Brief title",
      "confidence": 0.5-0.9,
      "caused_by_decisions": ["decision index 0", "decision index 1"]
    }}
  ],
  "causal_edges": [
    {{
      "from_ref": "signal_ref or decision:index",
      "to_ref": "decision:index or outcome:index",
      "edge_type": "LED_TO|TRIGGERED|CAUSED_BY|AMPLIFIED",
      "confidence": 0.5-0.9,
      "label": "Brief explanation of causal relationship"
    }}
  ],
  "signal_to_signal_edges": [
    {{
      "from_signal_ref": "signal_ref_1",
      "to_signal_ref": "signal_ref_2",
      "edge_type": "LED_TO|AMPLIFIED|CAUSED_BY",
      "confidence": 0.5-0.9,
      "label": "How signal 1 caused or amplified signal 2"
    }}
  ],
  "causal_chain": "Brief 1-sentence narrative: signal → decision → outcome"
}}

IMPORTANT:
- "from_ref" and "to_ref" use signal_ref for existing signals, "decision:0" for first inferred decision, "outcome:0" for first inferred outcome, etc.
- Create signal_to_signal_edges when one signal clearly led to or amplified another (e.g., champion_loss → usage_decline).
- Each decision should reference which signals triggered it via "triggered_by_signals".
- Return a JSON array of objects, one per account. Skip accounts with no meaningful causal story.
"""

EDGE_ENRICHMENT_FEW_SHOT = """
EXAMPLE INPUT:
Account: DataFlow Inc
ARR: $8,500,000
Health trajectory: [82, 79, 74, 62, 55, 48]
Current health: 48 (critical)
Existing signals:
  [sig_df_001] champion_loss (2025-10-15): "VP Engineering Sarah Chen departed" (negative, confidence 0.9)
  [sig_df_002] usage_decline (2025-11-01): "Platform DAU dropped 45% following team restructure" (negative, confidence 0.85)
  [sig_df_003] escalation (2025-12-01): "CTO escalated to VP CS about degraded support response" (negative, confidence 0.8)
  [sig_df_004] nps_decline (2025-12-15): "NPS survey returned score of 15, down from 52" (negative, confidence 0.9)

EXAMPLE OUTPUT:
{
  "account_name": "DataFlow Inc",
  "inferred_decisions": [
    {
      "type": "executive_engagement",
      "date": "2025-12-05",
      "title": "VP CS likely initiated executive-to-executive engagement after CTO escalation",
      "confidence": 0.75,
      "triggered_by_signals": ["sig_df_003"]
    },
    {
      "type": "resource_reallocation",
      "date": "2025-12-10",
      "title": "Dedicated support pod likely assigned to address response time concerns",
      "confidence": 0.65,
      "triggered_by_signals": ["sig_df_003", "sig_df_002"]
    }
  ],
  "inferred_outcomes": [
    {
      "type": "revenue_at_risk",
      "date": "2026-01-01",
      "title": "Revenue at Risk — DataFlow Inc showing churn indicators",
      "confidence": 0.85,
      "caused_by_decisions": []
    }
  ],
  "causal_edges": [
    {"from_ref": "sig_df_001", "to_ref": "decision:0", "edge_type": "LED_TO", "confidence": 0.6, "label": "Champion loss created leadership vacuum that escalation tried to fill"},
    {"from_ref": "sig_df_003", "to_ref": "decision:0", "edge_type": "TRIGGERED", "confidence": 0.8, "label": "CTO escalation directly triggered exec engagement"},
    {"from_ref": "sig_df_003", "to_ref": "decision:1", "edge_type": "TRIGGERED", "confidence": 0.75, "label": "Escalation about support drove resource reallocation"},
    {"from_ref": "sig_df_002", "to_ref": "decision:1", "edge_type": "LED_TO", "confidence": 0.65, "label": "Usage decline justified dedicated support investment"},
    {"from_ref": "decision:0", "to_ref": "outcome:0", "edge_type": "LED_TO", "confidence": 0.7, "label": "Executive engagement couldn't prevent revenue risk given depth of issues"},
    {"from_ref": "decision:1", "to_ref": "outcome:0", "edge_type": "LED_TO", "confidence": 0.65, "label": "Support pod assigned too late to stem NPS collapse"}
  ],
  "signal_to_signal_edges": [
    {"from_signal_ref": "sig_df_001", "to_signal_ref": "sig_df_002", "edge_type": "LED_TO", "confidence": 0.85, "label": "Champion departure caused team disengagement and usage drop"},
    {"from_signal_ref": "sig_df_002", "to_signal_ref": "sig_df_003", "edge_type": "LED_TO", "confidence": 0.7, "label": "Usage decline and poor experience led to CTO escalation"},
    {"from_signal_ref": "sig_df_003", "to_signal_ref": "sig_df_004", "edge_type": "AMPLIFIED", "confidence": 0.6, "label": "Unresolved escalation amplified negative sentiment in NPS survey"}
  ],
  "causal_chain": "Champion departure → usage collapse → CTO escalation → exec engagement + support pod → but interventions came too late, $8.5M ARR at risk"
}
"""
