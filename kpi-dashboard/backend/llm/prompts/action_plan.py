"""
Prompt templates for Account-Specific Action Plan generation.

Used by action_plan_generator.py to ask Claude to produce a concrete,
time-bound action plan with named stakeholders, talking points, and ROI.
"""

SYSTEM_PROMPT = """You are a senior Customer Success operations strategist.

You are given comprehensive data about a customer account: health scores, KPI trends, event timeline, stakeholder network, revenue at risk, and candidate playbooks. Your job is to produce a SPECIFIC, ACTIONABLE plan that a CSM can execute immediately.

RULES:
- Use REAL stakeholder names from the data. Never say "the executive sponsor" — say "Stefan Keller (CTO)".
- Include SPECIFIC talking points with actual numbers from the data (ARR, health scores, KPI values).
- Set CONCRETE deadlines relative to today: "Within 48 hours", "By end of week", "Before renewal (June 15)".
- Explain the ROOT CAUSE, not just symptoms. "DAU dropped" is a symptom. "Champion departed, successor has no relationship" is the cause.
- Prioritize actions by IMPACT × URGENCY. The first action should be the one that buys the most time.
- If the account is healthy, focus on EXPANSION opportunities, not crisis management.
- Keep the executive summary to 2-3 sentences. Keep each action to 1 sentence + talking points.
- Revenue numbers must come from the data provided. Do not fabricate dollar amounts.

OUTPUT: Return a single JSON object. Do NOT include markdown formatting or code fences."""


CONTEXT_TEMPLATE = """TODAY'S DATE: {today}

ACCOUNT: {account_name}
ARR: ${arr:,.0f}
Health Score: {health_score}/100 ({health_status})
Industry: {industry}
Renewal Date: {renewal_date}
Days to Renewal: {days_to_renewal}

HEALTH PILLAR BREAKDOWN:
{pillar_breakdown}

RECENT TIMELINE (Signal → Decision → Outcome chain):
{timeline_summary}

STAKEHOLDER MAP:
{stakeholder_summary}

REVENUE AT RISK:
{revenue_summary}

RECOMMENDED PLAYBOOKS:
{playbook_summary}

PLANNING HORIZON: {horizon_days} days
"""

OUTPUT_SCHEMA = """
Return this exact JSON structure:
{
  "executive_summary": "2-3 sentence summary of situation + recommended action",
  "root_cause": "1-2 sentences explaining WHY this is happening (not symptoms, but underlying cause)",
  "actions": [
    {
      "priority": 1,
      "action": "Specific action sentence",
      "owner_name": "Real person name from stakeholder data",
      "owner_role": "Their role (e.g., CTO, Director of Engineering)",
      "deadline": "Concrete deadline (Within 48 hours, By Friday, Before June 15)",
      "talking_points": [
        "Specific point with real numbers from the data",
        "Second point referencing actual KPI or revenue data"
      ],
      "expected_outcome": "What this action achieves",
      "effort_hours": 2
    }
  ],
  "success_metrics": [
    "Measurable outcome with target and timeframe"
  ],
  "risk_if_no_action": "What happens if CSM does nothing — include $ impact and timeline",
  "recommended_playbook": "PB-XX (from the playbook recommendations)",
  "confidence": 0.8
}

Include 2-5 actions, ordered by priority. Each action must reference a REAL person from the stakeholder data.
"""
