---
name: Champion Recovery Playbook
description: Execute PB-02 champion recovery workflow — assess, analyze stakeholders, quantify risk, build action plan
---

# Champion Recovery Playbook (PB-02)

You are executing the Champion Recovery playbook for a CS Pulse customer account. This playbook is triggered when a champion (key stakeholder who drove the buying decision or renewal) has departed, disengaged, or been reassigned — creating renewal risk.

## Invocation

This skill is triggered by `/playbook champion-recovery <account_id>` or `/playbook champion-recovery` (no argument).

## Input Resolution

1. Parse the argument. If an `account_id` is provided, use it directly.
2. If NO `account_id` is provided, ask the user: "Which account would you like to run the Champion Recovery playbook for? Please provide the account ID, or I can list your at-risk accounts."
   - If the user asks to list accounts, call `list_accounts` for the active customer, then call `get_at_risk_accounts` and present a table so they can choose.
3. You need a `customer_id`. Check if the user has established one in the conversation already. If not, call `list_customers` and ask the user to confirm which customer (tenant) they are working with.

Once you have both `customer_id` and `account_id`, proceed with the 7-step framework below.

## Data Collection Phase

Before generating the report, gather all intelligence by calling these MCP tools. Make all independent calls in parallel for speed:

**Batch 1 (parallel):**
- `get_account_health(customer_id, account_id)` — current health score, pillar breakdown, trend
- `get_stakeholder_map(customer_id, account_id)` — full stakeholder network, roles, engagement
- `get_account_journey_timeline(customer_id, account_id, limit=100)` — chronological event history
- `get_revenue_at_risk(customer_id, account_id)` — revenue exposure breakdown
- `get_customer_feedback(customer_id, account_id)` — NPS/CSAT trend data

**Batch 2 (parallel, after Batch 1 completes):**
- `get_playbook_recommendations(customer_id, account_id)` — platform-recommended playbooks
- `search_signals(customer_id, account_id, node_type='SIGNAL')` — all signals including champion_loss, engagement_drop
- `search_signals(customer_id, account_id, node_type='DECISION')` — pending and completed decisions
- `search_signals(customer_id, account_id, node_type='OUTCOME')` — outcomes linked to this account
- `get_crm_account_data(customer_id, account_id)` — contract details, renewal date, usage metrics

If any tool returns an error, note it in the report as "[Data unavailable]" and continue with remaining data. Do not halt the playbook.

## Report Generation — 7-Step Framework

Generate a comprehensive report with the following structure. Use markdown formatting with headers, tables, bold text, and bullet points throughout. The tone should be direct, analytical, and action-oriented — written for a Senior CSM or VP of Customer Success.

---

### Output Format

Begin with a header block:

```
# Champion Recovery Playbook — [Account Name]
**Generated:** [current date]  |  **Account ID:** [id]  |  **Health:** [score]/100 ([status])  |  **ARR:** $[amount]
```

Then produce each of the 7 steps as a section:

---

#### STEP 1: ASSESS — Health Score & Trend Analysis

Present the current health state:

| Metric | Value | Trend |
|--------|-------|-------|
| Overall Health | [score]/100 | [direction] |
| P1: [pillar_label from get_account_health] | [score] | [direction] |
| P2: [pillar_label from get_account_health] | [score] | [direction] |
| P3: [pillar_label from get_account_health] | [score] | [direction] |
| P4: [pillar_label from get_account_health] | [score] | [direction] |
| P5: [pillar_label from get_account_health] | [score] | [direction] |

Below the table, write 2-3 sentences interpreting the scores. Identify which pillars are dragging overall health down. Flag any pillar that crossed from healthy to at-risk or critical in recent months. Classify the overall situation:
- **Critical (score < 50):** Immediate intervention required. Escalate to VP/CRO.
- **At-Risk (50-69):** Active recovery needed. 30-day action window.
- **Early Warning (70-79, declining):** Proactive engagement recommended.

---

#### STEP 2: STAKEHOLDER ANALYSIS — Champion Departure Impact

Using the stakeholder map data, build a stakeholder table:

| Name | Role | Status | Engagement Level | Last Active | Champion? |
|------|------|--------|-----------------|-------------|-----------|

For each stakeholder, assess:
- **Departed Champion:** Who left? What was their role in the buying decision, renewal advocacy, and internal sponsorship? When did they leave?
- **Power Vacuum:** Who inherits their responsibilities? Is the successor identified? Are they favorable, neutral, or hostile to our platform?
- **Remaining Allies:** Which stakeholders are still engaged and supportive? Who can become the new internal champion?
- **Engagement Gaps:** Which key personas (economic buyer, technical decision-maker, end-user champion) are now unengaged or missing?

Write a 3-4 sentence "Stakeholder Risk Assessment" summarizing the political landscape post-departure.

---

#### STEP 3: EVIDENCE CHAIN — Departure Cascade Timeline

Using the journey timeline and signals, reconstruct the chronological story of the champion departure and its downstream effects. Present this as a timeline:

```
[Date] — [Event Type] — [Description] — [Impact]
```

Identify and call out:
- The **trigger event** (champion departure signal, role change, or last engagement)
- **Cascade effects** — what broke after the champion left (engagement drops, missed QBRs, stalled expansions, support escalations)
- **Leading indicators** that preceded the departure (declining login frequency, missed meetings, reduced NPS scores)
- **Current state signals** — what is happening right now

If there are causal chain links (signal led to decision led to outcome), connect them explicitly. Reference specific context graph node types where available.

---

#### STEP 4: REVENUE IMPACT — Financial Exposure Quantification

Using `get_revenue_at_risk` data, present:

| Revenue Category | Amount | % of Account ARR |
|-----------------|--------|------------------|
| At-Risk Revenue | $[amount] | [pct]% |
| Protected Revenue | $[amount] | [pct]% |
| Expansion Pipeline (stalled) | $[amount] | [pct]% |
| Revenue Already Lost | $[amount] | [pct]% |

Then calculate and present:
- **Total Exposure** = at-risk + stalled expansion + already lost
- **Recovery Window** = days until renewal or next decision point
- **Cost of Inaction** = projected revenue loss if no intervention (use total at-risk as baseline)

Write 2-3 sentences contextualizing the financial impact. Compare the exposure to the cost of the recovery effort (CSM hours, executive time, potential concessions).

---

#### STEP 5: COMPETITIVE INTELLIGENCE — Threat Assessment

Search the signals and timeline for any competitive indicators:
- Competitor mentions in signals or feedback
- RFP or evaluation signals
- Vendor consolidation or multi-vendor strategy signals
- New technology adoption signals that conflict with our platform

Present findings as:
- **Threat Level:** None Detected / Low / Medium / High / Active Displacement
- **Competitors Identified:** [list or "None detected in current signals"]
- **Evidence:** [specific signals or "No direct competitive signals found — monitor proactively"]

If no competitive signals exist, state this clearly but recommend proactive competitive monitoring as part of the action plan.

---

#### STEP 6: ACTION PLAN — 30/60/90 Day Recovery Roadmap

Build a concrete, time-bound action plan. Use the playbook recommendations from the platform as input, but augment with champion-recovery-specific actions.

**Phase 1: Stabilize (Days 1-30)**

| # | Action | Owner | Due | Success Metric |
|---|--------|-------|-----|---------------|
| 1 | Schedule emergency intro meeting with champion's successor | CSM | Day 3 | Meeting confirmed |
| 2 | [context-specific action based on data] | [role] | [date] | [metric] |
| ... | | | | |

**Phase 2: Rebuild (Days 31-60)**

| # | Action | Owner | Due | Success Metric |
|---|--------|-------|-----|---------------|
| ... | | | | |

**Phase 3: Secure (Days 61-90)**

| # | Action | Owner | Due | Success Metric |
|---|--------|-------|-----|---------------|
| ... | | | | |

For each phase, include 3-5 specific actions drawn from the account data. Actions should be:
- **Specific** — name the person, meeting, or deliverable
- **Measurable** — define what success looks like
- **Time-bound** — specific day or week target
- **Assigned** — CSM, CS Leader, Sales, Executive Sponsor, or Solutions Engineer

Standard champion recovery actions to include where relevant:
- Executive sponsor alignment (VP/CRO outreach to new economic buyer)
- Value realization workshop with successor stakeholder
- Renewed business review cadence (weekly check-ins during Phase 1)
- Custom ROI report for the new decision-maker
- Technical health check / optimization session
- Expansion roadmap refresh tied to successor's priorities
- Risk escalation to internal leadership if successor is hostile or absent

---

#### STEP 7: EXECUTIVE BRIEFING — CRO-Ready Summary

Draft a single paragraph (4-6 sentences) that a CSM can copy-paste into an email or Slack message to their CRO or VP of CS. The briefing should cover:
1. Account name and ARR at stake
2. What happened (champion departure, one sentence)
3. Current health status and trajectory
4. Revenue at risk (specific dollar amount)
5. Recovery plan summary (key actions and timeline)
6. What executive support is needed (specific ask)

Format this as a blockquote so it stands out visually.

---

### Closing

End the report with:

```
---
**Playbook:** PB-02 Champion Recovery  |  **Confidence:** [High/Medium/Low based on data completeness]
**Next Review:** [date 14 days from now]  |  **Escalation Required:** [Yes/No]
**Data Sources:** [list which MCP tools returned data successfully]
```

## Quality Standards

- Never fabricate data. Every number must come from an MCP tool response. If data is unavailable, say so.
- Use the health score thresholds from the platform: critical < 50, at-risk 50-69, healthy >= 70.
- Revenue figures must come from `get_revenue_at_risk` — never manually sum context graph node values (causes double-counting).
- Stakeholder names and roles must come from `get_stakeholder_map` — do not invent personas.
- The action plan should be realistic for a CSM managing 15-20 accounts. Do not overload with 20+ action items.
- The executive briefing must be concise enough to read in 30 seconds.
