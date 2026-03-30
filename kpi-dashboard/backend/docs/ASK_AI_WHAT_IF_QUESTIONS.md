# Ask AI — "What If" Questions by Persona

Comprehensive list of questions each persona should be able to ask and get
accurate, data-backed answers from Ask AI. Use this as:
1. **Acceptance criteria** — every question should produce a useful answer
2. **Test scenarios** — run each question against a demo customer and validate
3. **Default suggestions** — top 4-5 per persona go into the UI suggestion chips

---

## CSM (Customer Success Manager)

Focus: daily execution, account health, playbook actions, renewals, signals.

| # | Question | Expected Data Source | Tests |
|---|----------|---------------------|-------|
| 1 | What should I focus on today? | `get_csm_daily_actions` | Prioritized action list with $impact |
| 2 | Which of my accounts dropped health score this month? | `get_health_score_history` | Month-over-month delta, flagged accounts |
| 3 | What's the causal chain behind K2 Computing's health decline? | `get_account_journey_timeline` + `get_causal_chain` | Signal → decision → outcome chain |
| 4 | If I run the Champion Recovery playbook on Matterhorn, what's the projected ROI? | `get_playbook_recommendations` + `calculate_power_of_1` | Dollar impact estimate |
| 5 | Which accounts have renewals in the next 60 days and are at-risk? | `list_accounts` (filter renewal_date + health < 70) | Account list with ARR + renewal date |
| 6 | What signals fired for Everest Cloud this quarter? | `search_signals` + `get_account_journey_timeline` | Signal timeline with types and dates |
| 7 | How did my critical accounts change after I ran playbooks last month? | `get_health_score_history` + playbook execution data | Before/after health with attribution |
| 8 | What's the stakeholder map for my top 3 at-risk accounts? | `get_stakeholder_map` x3 | Champions, detractors, engagement levels |
| 9 | If GPU utilization drops another 10% at K2, what happens to their health score? | Health score simulation with modified KPI | Projected score + threshold crossing |
| 10 | Which accounts have open support tickets with no CSM response in 7+ days? | `get_support_tickets` across accounts | Ticket list with SLA breach flags |

---

## CRO (Chief Revenue Officer)

Focus: revenue at risk, pipeline, churn prevention ROI, competitive threats, expansion.

| # | Question | Expected Data Source | Tests |
|---|----------|---------------------|-------|
| 1 | How much ARR is at risk right now and why? | `get_at_risk_accounts` + `get_revenue_at_risk` | Total $at_risk with top accounts |
| 2 | What would happen to our NRR if we lose the 3 most at-risk accounts? | `list_accounts` + ARR math | NRR impact calculation |
| 3 | Which accounts are being evaluated by competitors? | `search_signals(node_subtype='competitive_threat')` | Account list with competitor signals |
| 4 | What's our expansion pipeline and probability by account? | `list_accounts` (healthy + expansion signals) + `get_revenue_at_risk(expansion)` | Pipeline total with per-account probability |
| 5 | If we improve NRR by 1%, what's the dollar impact? | `calculate_power_of_1('NRR')` | Annual dollar impact + breakdown |
| 6 | Show me the revenue story for our worst-performing account | `get_outcome_roi_story` for lowest health account | Revenue narrative with causal chain |
| 7 | How much revenue did CS protect this quarter through interventions? | `get_portfolio_roi_summary` | Protected $, expanded $, lost $ |
| 8 | What's our churn concentration risk — how much ARR is in critical accounts? | `get_at_risk_accounts(threshold=50)` + ARR sum | $ in critical vs total portfolio |
| 9 | If we had 2 more CSMs, which accounts would benefit most? | `get_csm_daily_actions` + capacity analysis | Underserved accounts ranked by $impact |
| 10 | Compare our health distribution this quarter vs last quarter | `get_health_score_history(months=6)` | Distribution shift (more/fewer at-risk) |

---

## CFO (Chief Financial Officer)

Focus: ROI proof, investment efficiency, cost per outcome, payback, board narrative.

| # | Question | Expected Data Source | Tests |
|---|----------|---------------------|-------|
| 1 | What's our CS investment returning per dollar? | `get_portfolio_roi_summary` | ROI %, total investment vs total impact |
| 2 | What's the payback period on our CS Pulse investment? | `get_portfolio_roi_summary` (payback_months) | Months to break even |
| 3 | Break down the cost per playbook run vs the revenue it protected | `get_playbook_economics` | Per-playbook cost, hours, ROI |
| 4 | If we increase CS investment by 20%, what's the projected additional return? | `calculate_power_of_1` with scaling | Projected incremental $ |
| 5 | Which metrics have the highest ROI — where should we invest next? | `get_portfolio_roi_summary` per-metric breakdown | Ranked metrics by $/investment |
| 6 | What's the compounding effect — how do metric improvements multiply? | ROI engine compounding multiplier | Cross-metric cascade explanation |
| 7 | Give me the board-ready CS investment summary with proof points | `get_portfolio_roi_summary` + `get_outcome_roi_story` | Formatted executive summary |
| 8 | What's our cost of inaction — what do we lose if we don't act on critical accounts? | `get_at_risk_accounts` + ARR at risk | Total $ at risk with timeline |
| 9 | How does our CS efficiency compare — cost per $1M ARR managed? | Investment / total ARR ratio | Benchmark against industry |
| 10 | Show me the quarterly implementation roadmap with resource costs | `get_portfolio_roi_summary` (work packages) | Quarterly breakdown: hours, cost, deliverables |

---

## VP CS (VP of Customer Success)

Focus: team performance, portfolio health trends, playbook effectiveness, hiring, process.

| # | Question | Expected Data Source | Tests |
|---|----------|---------------------|-------|
| 1 | How is my portfolio health trending — improving or declining? | `get_health_score_history(account_id=0)` | Trend chart, # accounts improving vs declining |
| 2 | Which CSM has the most at-risk accounts and are they overloaded? | `get_at_risk_accounts` + account-CSM assignment | Per-CSM risk load |
| 3 | Which playbooks are most effective at moving accounts from at-risk to healthy? | Playbook executions + health score deltas | Playbook effectiveness ranking |
| 4 | What's our renewal rate forecast for next quarter? | Accounts with renewal_date in next 90d + health | Predicted renewal rate + $ |
| 5 | Are there accounts that have been at-risk for 3+ months with no intervention? | `get_health_score_history` (persistent at-risk) | Stale at-risk accounts |
| 6 | What story arcs are most common in my portfolio and what do they predict? | Arc classification distribution | Arc breakdown with outcome probabilities |
| 7 | If I hire 1 more CSM, which accounts should they own? | Unserved/underserved accounts ranked by ARR + risk | Account assignment recommendation |
| 8 | Show me accounts where health improved but signals are still negative | Health up + recent negative signals | False positive recovery candidates |
| 9 | What's the average time from first negative signal to health score drop? | Signal dates vs health score crossing dates | Leading indicator lag analysis |
| 10 | Which KPI pillars are driving the most health score declines across the portfolio? | Pillar scores across declining accounts | Pillar weakness heatmap |

---

## Validation Approach

For each question:
1. **Run against demo customer** (Gainsight 15KPI, customer_id=451)
2. **Check response contains data** — not just "I don't have that information"
3. **Verify numbers match** — cross-reference with MCP tool direct calls
4. **Check persona tone** — CSM gets tactical, CFO gets financial, CRO gets revenue-focused
5. **Test follow-up** — ask a clarifying question and verify context is maintained

### Test Matrix

| Persona | Questions | Expected Pass Rate | Notes |
|---------|-----------|-------------------|-------|
| CSM | 10 | 8/10 minimum | Q9 (simulation) may need custom tool |
| CRO | 10 | 8/10 minimum | Q9 (capacity) may need custom analysis |
| CFO | 10 | 7/10 minimum | Q9 (benchmark) needs external data |
| VP CS | 10 | 7/10 minimum | Q7 (hiring), Q9 (lag analysis) are complex |

### Questions That Likely FAIL Today

| # | Question | Why It Fails | What's Missing |
|---|----------|-------------|----------------|
| CSM-9 | "If GPU drops 10%, what happens?" | No simulation/what-if tool in MCP | Need a `simulate_kpi_change` tool |
| CRO-2 | "What happens to NRR if we lose 3 accounts?" | No NRR simulation tool | Need portfolio-level what-if |
| CRO-9 | "If we had 2 more CSMs..." | No capacity planning tool | Need CSM workload model |
| CFO-4 | "If we increase investment 20%..." | Power of 1 is fixed 1% model | Need configurable improvement % (already exists as param) |
| CFO-9 | "How does our efficiency compare?" | No external benchmarks | Need industry_benchmarks data |
| VPCS-7 | "If I hire 1 more CSM..." | No account assignment optimization | Need workload balancer |
| VPCS-9 | "Average time from signal to drop?" | No signal-to-health lag analysis | Need temporal correlation query |

These failures point to 4 new MCP tools that would unlock the "what if" capability:
1. `simulate_kpi_change(account_id, kpi_code, new_value)` — project health score change
2. `simulate_portfolio_loss(account_ids)` — project NRR/GRR impact of losing accounts
3. `get_csm_workload(customer_id)` — per-CSM account load + risk distribution
4. `get_signal_to_health_lag(customer_id)` — temporal correlation between signals and health drops
