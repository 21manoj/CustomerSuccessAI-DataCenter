"""
Prompt templates for Tier 1 KPI-based context inference.

Used by tier1_inference.py to ask Claude to infer signals, outcomes,
decisions, and causal edges from KPI time series + health scores alone.
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
- Revenue impact on outcomes should be proportional to the account's ARR.
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
      "revenue_impact": 0,
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
      "revenue_impact": -6000000,
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
