# CS Pulse MCP Demo Script — Claude as CSM Co-Pilot

## Prerequisites

### 1. Start the Backend
```bash
cd /Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/backend
python app_v3_minimal.py
# Verify: curl http://localhost:5059/health
```

### 2. Verify MCP Server
The `.mcp.json` is already configured. In Claude Code or Claude Desktop, the CS Pulse MCP server starts automatically.

To test standalone:
```bash
cd /Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard
python backend/mcp_server/cs_pulse_mcp_server.py
# Should start without errors. Ctrl+C to stop.
```

### 3. Verify Tools Available
In Claude, ask: **"What CS Pulse tools do you have available?"**

Expected: 15 tools across 6 groups:
- Group 1: Account Intelligence (3) — list_accounts, get_account_health, get_at_risk_accounts
- Group 2: Context Graph (4) — get_revenue_at_risk, get_causal_chain, get_graph_summary, search_signals
- Group 3: Financial (2) — calculate_power_of_1, get_outcome_roi_story
- Group 4: Actions (1) — get_playbook_recommendations
- Group 5: External Systems (3) — get_crm_account_data, get_support_tickets, get_customer_feedback
- Group 6: Operational (2) — get_csm_daily_actions, get_portfolio_roi_summary

### 4. Demo Customers
| Customer | ID | ARR | Accounts | Story |
|----------|----|-----|----------|-------|
| **Tacme** | 292 | $500M | 10 | Churn prevention + turnaround |
| **Sacme** | 291 | $50M | 10 | Expansion + ROI proof |

---

## Opening (30 seconds)

> "CS Pulse isn't a dashboard you click through — it's a revenue intelligence engine that Claude uses as tools. Watch how a CSM works when AI is the interface."

---

## ACT 1: TACME — Predict and Fix Churn (5 minutes)

### Scene 1: Portfolio Overview

**Prompt:**
> "I'm the CSM for Tacme, customer ID 292. Give me a quick health overview — which accounts need my attention today?"

**What Claude does:** Calls `list_accounts(292)`, sorts by health, identifies critical/at-risk accounts with ARR exposure.

**Key data points to highlight:**
- 10 accounts, $500M total ARR
- 2 critical (DR-Backup: 37.2, Integration: 46.7)
- 2 at-risk (Research: 60.8, Edge-Compute: 64.0)
- ~$106M ARR in accounts below healthy threshold

---

### Scene 2: Deep Dive — The Worst Account

**Prompt:**
> "Tell me more about the DR-Backup account. What's the CRM record look like, and do we have any open support issues?"

**What Claude does:** Calls `get_account_health(292, 292007)`, `get_crm_account_data(292, 292007)`, and `get_support_tickets(292, 292007)`.

**Key data points:**
- Health: 37.2 (critical), P2: 16.6 (operational stability collapsed)
- ARR: $28.5M, Telecom industry
- CRM: champion status, contract renewal timeline, executive sponsor
- Tickets: high critical incident count, SLA breaches, MTTR above target
- Risk indicators: elevated RMA rate, thermal management issues

**Demo talking point:**
> "Notice how Claude correlates health data with CRM context and ticket data from three different systems — all through MCP tool calls. In production, these would be real Salesforce and ServiceNow connections."

---

### Scene 3: Root Cause — What Signals Led Here?

**Prompt:**
> "What signals led to this health decline? Show me the causal chain."

**What Claude does:** Calls `search_signals(292, 292007, node_type="SIGNAL")` and `get_graph_summary(292, 292007)`, then may call `get_causal_chain()` for a specific node.

**Key data points:**
- 60 nodes in context graph: 44 signals, 4 decisions, 6 outcomes
- 119 causal edges connecting them
- SIGNAL → DECISION → OUTCOME chain showing how operational degradation led to revenue risk

---

### Scene 4: Customer Sentiment

**Prompt:**
> "What does the customer feedback look like? Any warning signs from NPS?"

**What Claude does:** Calls `get_customer_feedback(292, 292007)`.

**Key data points:**
- NPS score and trend (derived from qualitative signals)
- CSAT score
- Recent VoC summaries (verbatim customer quotes)
- CSM assessment: relationship strength, churn risk level, weakest pillar

---

### Scene 5: Action Plan — What Should I Do Today?

**Prompt:**
> "What should I do today across all Tacme accounts? Give me my prioritized action list."

**What Claude does:** Calls `get_csm_daily_actions(292)`.

**Key data points:**
- Top 10 actions ranked by priority index
- Each linked to a playbook (PB-02 RMA Prevention, PB-05 Health Monitoring, etc.)
- Urgency levels: critical, high, opportunity
- Estimated hours per action
- **ROI projection**: each action linked to Power-of-1 metric with dollar impact

**Demo talking point:**
> "Every action has a dollar sign attached. The CSM doesn't just know what to do — they know exactly how much revenue each action protects or generates."

---

### Scene 6: Financial Justification — Prove the Investment

**Prompt:**
> "Give me the ROI story for Tacme. I need to justify our CS investment to the VP."

**What Claude does:** Calls `get_portfolio_roi_summary(292)`.

**Key data points:**
- Historical ROI: -38.1% (early stage, large investment hasn't matured)
- But trajectory: **accelerating**
- GRR improved 0.44% = $2.2M saved
- Forward projection: 81.1% ROI over next 6 months
- Combined: **$46M total outcome value** on $31.7M investment

**Demo talking point:**
> "The historical ROI is negative because Tacme is a massive $500M customer that just started. But the trajectory is accelerating — the platform predicts $40M in forward returns. That's the story a CRO needs to hear."

---

## ACT 2: SACME — Expansion & ROI Proof (5 minutes)

### Scene 1: The Opposite Story

**Prompt:**
> "Now let's look at Sacme, customer 291. How's the portfolio?"

**What Claude does:** Calls `list_accounts(291)`.

**Key data points:**
- 10 accounts, $50M total ARR
- Mostly healthy (6 above 70)
- 2 critical, 2 at-risk — but the healthy ones are driving expansion

---

### Scene 2: Expansion Opportunities

**Prompt:**
> "Which accounts have expansion potential? What does the CRM data show for the top one?"

**What Claude does:** Calls `get_crm_account_data(291, 291001)` (Sacme-Production, health 77.9).

**Key data points:**
- ARR: $10.7M, Technology industry
- Champion info: name, title, influence level
- Renewal stage and probability
- Usage metrics: GPU utilization, capacity utilization
- Health: 77.9 (healthy) — not just surviving, thriving

---

### Scene 3: Revenue Intelligence — The Context Graph

**Prompt:**
> "Show me the revenue breakdown and context graph for Sacme-Production."

**What Claude does:** Calls `get_revenue_at_risk(291, 291001)` and `get_graph_summary(291, 291001)`, then `search_signals(291, 291001, node_type="OUTCOME")`.

**Key data points:**
- 103 nodes: 60 signals, 18 decisions, 9 outcomes, 5 stakeholders
- 124 causal edges
- Net revenue impact: **$27.7M**
- $15.1M expansion, $12.7M protected, $5.4M at risk
- Key outcomes: ARR grew 3x, $5.2M expansion deal closed, 35x ROI

**Demo talking point:**
> "This isn't a dashboard — it's a causal evidence chain. Every dollar is traced back through decisions to the signals that started it. When the CFO asks 'why are we paying for CS?', this is the answer."

---

### Scene 4: QBR ROI Story

**Prompt:**
> "I have a QBR next week with Sacme's CRO. Build me an ROI story."

**What Claude does:** Calls `get_portfolio_roi_summary(291)`.

**Key data points:**
- Historical ROI: **241.3%** on $819K investment
- GRR improved 2.22% = $1.1M saved
- NRR improved 1.82% = $955K expansion
- Trajectory: **sustaining** — this is a machine, not a spike
- Forward: 81.1% projected
- Combined: **$6.8M total impact** on $3M total investment

---

### Scene 5: Power of 1

**Prompt:**
> "If Sacme improves their NRR by just 1%, what's the dollar impact?"

**What Claude does:** Calls `calculate_power_of_1(291, "NRR", 1.0)`.

**Key data point:**
> "A 1% NRR improvement across Sacme's $50M portfolio = $500K additional annual revenue."

**Demo talking point:**
> "Power of 1 makes CS investments tangible. Every percentage point has a dollar sign."

---

## Closing (30 seconds)

> "Two customers. Two stories. One AI co-pilot.
>
> Tacme: Claude identified churn risk across a $500M portfolio, traced root cause through the causal graph, recommended playbooks with dollar-precise ROI, and built a recovery narrative for the CRO.
>
> Sacme: Claude proved 241% ROI on CS investment, mapped the expansion evidence chain, and quantified that 1% NRR improvement = $500K.
>
> This is what revenue intelligence looks like when AI is the interface — not a dashboard you look at, but a co-pilot that thinks with you."

---

## Backup Prompts (If Audience Asks Questions)

### "How does the health score work?"
> "Show me how the health score is calculated for Tacme-DR-Backup. Break down the 5 pillars."
→ Calls `get_account_health(292, 292007)`, shows P1-P5 breakdown

### "Can you show me what playbooks it recommends?"
> "What specific playbooks should I run for Tacme-Edge-Compute?"
→ Calls `get_playbook_recommendations(292, 292006)`

### "What if we improved a different metric?"
> "Calculate the impact of 2% improvement in GRR for Tacme."
→ Calls `calculate_power_of_1(292, "GRR", 2.0)`

### "How does the causal chain work?"
> "Find the most recent outcome node for Sacme-Production and trace it upstream."
→ Calls `search_signals(291, 291001, "OUTCOME", limit=1)`, then `get_causal_chain(291, <node_id>, "upstream")`

### "Where does the data come from?"
> "Show me all the external system data for Tacme-Edge-Compute — CRM, tickets, and feedback."
→ Calls all three Group 5 tools for account 292006

---

## Technical Notes

- Backend must be running at `localhost:5059` for DB access
- MCP server creates its own lightweight Flask app for DB queries
- Feature toggles: `FEATURE_MCP_SERVER=true` and `FEATURE_CONTEXT_GRAPH=true` set in `.mcp.json`
- Context graph sub-toggles must be enabled per-customer in DB (already done for 291/292)
- All data is deterministic (not random) — re-running produces same results
- External system tools (Group 5) read from the same DB, formatted as CRM/ITSM/survey output
