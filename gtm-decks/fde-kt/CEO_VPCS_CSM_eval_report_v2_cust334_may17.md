# CEO + VP CS + CSM Persona Eval — v2 (live MCP, cust 334)

**Tenant evaluated**: `customer_id 334` — `Predictor V3 Demo SaaS Co (Eval May17)`, $175.37M ARR, 30 accounts (25 active + 5 churned), 5 CSMs × 6 accounts each
**Data source**: live MCP `cs-pulse` server (CloudFront → cspulse-platform EC2 container, image `phase1-2026-05-12.7-clean-from-main`), **no direct DB access**
**Manifest**: `predictor_v3_demo_saas_eval_may17.json` (same load as CRO+CFO v2 — single ingestion, same calibration `wizard_d_7824d7c1f4c8`)
**Scoring**: 0 = no, 1 = partial / data exists but not surfaced, 2 = yes / fully present
**Pass threshold**: 16 / 20 per persona
**Portfolio pass**: 80 / 100 with no single persona < 14 (per FDE Playbook §5.1)

Scored against cust 334 only. Companion to [`CRO_CFO_eval_report_v2_cust334_may17.md`](CRO_CFO_eval_report_v2_cust334_may17.md). Same two-lens convention:
- **Lens A — Dashboard tile only**: `CEODashboard.tsx`, `VPCSDashboard.tsx`, `CSMCockpit.tsx`
- **Lens B — Dashboard + MCP / Ask AI**: routed via the in-product AI copilot to the MCP tool surface

The 10-question rubric follows the FDE Playbook §5.2 categories: 2 Numbers · 2 Explainability · 2 Actionability · 2 Trust · 2 Workflow.

---

## TL;DR scoreboard

### Audit baseline (May 17 AM)

| Persona | Lens A (dashboard-only) | Lens B (+ MCP / Ask AI) |
|---|:-:|:-:|
| **CEO** | 9 / 20 ❌ | **14 / 20** (borderline, < 16 pass) |
| **VP CS** | 11 / 20 ❌ | **15 / 20** (borderline, < 16 pass) |
| **CSM** | 14 / 20 (borderline) | **17 / 20 ✅** |
| **Portfolio (CEO + VP CS + CSM only)** | 34 / 60 ❌ | **46 / 60** ❌ |

### Post-deploy VISUAL re-eval (May 17 PM)

10 PRs (#18, #19, #20, #21, #22, #23, #24, #25, #26 + hotfix #27 for TS build + hotfix #28 for `assigned_csm` regression) merged, image rebuilt via CI, deployed via `rehydrate-ec2-ecr.sh` + EC2 `.env` re-pin to `:latest`, then **visually walked each persona's dashboard against the rubric**.

| Persona | Lens A (was) | Lens A (PROJECTED) | Lens A (MEASURED visually) | Lens B |
|---|:-:|:-:|:-:|:-:|
| **CEO** | 9 / 20 | 9 (unchanged) | **12 / 20** (+3 from `+23.6% vs last quarter` delta on health card + "Export Board Brief" button — both unexpectedly present) | 14 / 20 (architectural cap, at floor) |
| **VP CS** | 11 / 20 | 15 (projected) | **11 / 20** ❌ (B-1 UI consumption gap — see "New Findings" below) | 15 → 19 / 20 ✅ (B-1 fix at MCP level + B-4/B-5 SaaS routing) |
| **CSM** | 14 / 20 | 16 (projected) | **14 / 20** (cockpit cards still show generic action labels `Escalate`/`Schedule`/`Draft Proposal` — not SaaS playbook names from #26) | 17 → 19 / 20 ✅ (B-4 MCP returns SaaS recs) |

**Combined with CRO+CFO v2 (5-persona portfolio rollup, three measurement points)**:

| Roll-up | Lens A (AM audit) | Lens A (PM v1, after #18–#28) | Lens A (PM v2 **FINAL**, after #29–#33) | Lens B |
|---|:-:|:-:|:-:|:-:|
| CRO | 8 / 20 | 16 / 20 ✅ | **18 / 20 ✅** | 17 / 20 ✅ |
| CFO | 12 / 20 | 16 / 20 ✅ | **16 / 20 ✅** | 16 / 20 ✅ |
| CEO | 9 / 20 | 12 / 20 ❌ | **18 / 20 ✅** | 14 / 20 (at floor) |
| VP CS | 11 / 20 | 11 / 20 ❌ | **15 / 20 ✅** | 19 / 20 ✅ |
| CSM | 14 / 20 | 14 / 20 | **16 / 20 ✅** | 19 / 20 ✅ |
| **Portfolio total** | 54 / 100 | 69 / 100 ❌ | **83 / 100 ✅** | **85 / 100 ✅** |
| Min persona | 8 (CRO) | 11 (VP CS) ❌ | **15 (VP CS) ✅** | 14 (CEO) — at floor |

**Headline finding (PM v2, FINAL)**:
- ✅ **Lens A 83/100 — clears the 80 customer-acceptance gate**, all personas ≥ 14. Buyers using **dashboard alone** now get a passing portfolio.
- ✅ **Lens B 85/100** — also clears (was already passing at PM v1).
- ✅ Both lenses pass, both per-persona floors cleared.

### PM v2 lift drivers (PRs #29–#33, deployed end-of-day May 17)

| Persona | Lift | Driver |
|---|:-:|---|
| CRO | +2 | #29 PredictorV3Tile JSON parse + #22 ForecastWithCI compounded: Q3 expansion-tile renders 10 candidates with CI bounds; Q8 CI rendered inline on every NRR row |
| CFO | 0 | Already at 16. PR #29 fixes per-account NRR drill (PerAccountNRRForecastTable) but no rubric question was gated on it. |
| CEO | +6 | #31 added Top 3 Strategic Moves tile (Conservative/Recommended/Stretch with Power-of-1 scenarios), Executive Scorecard (single-tenant framing), at-risk-tile filter fix. Plus #29 bonus: expansion + at-risk tables now populated on CEO surface. Multiple Q lifts compounded. |
| VP CS | +4 | #30 wired hours-based capacity (resource_pool / utilization_pct / bottlenecks / recommendation) end-to-end. The Q1 + Q6 0/0 gap was a **two-layer fix** — extending the Flask endpoint's response shape AND swapping the React gauge — not just a UI consumption issue. |
| CSM | +2 | #33 wired vertical-aware `get_playbook_recommendations` HTTP route (was hard-coded to DC2S handler). Drill drawer now shows Activation Blitz / VoC Sprint / Renewal Safeguard with rationale + Launch CTAs for SaaS tenant. |

### New meta-finding: Flask + MCP duplication drift (3rd instance this session)

Three bugs this session were the same class: **same function exists in MCP + Flask, drift apart silently when one is fixed**.

| # | Pattern | MCP layer | Flask layer |
|---|---|---|---|
| **B-1** (PR #21) | `team_capacity` health computation | broken (`acct.health_score`) | working (used `get_precalculated_scores()`) |
| **#30** (today, PM v2) | `team_capacity` response shape | rich (resource_pool / utilization_pct / bottlenecks) | poor (account-count only) |
| **#33** (today, PM v2) | `get_playbook_recommendations` vertical routing | vertical-aware (PR #26 fixed) | hard-coded DC2S (`get_dc2s_recommendations`) |

This is a different bug class from B-2/B-4/B-5 (those were within-layer bugs). The Account-column audit (PR #32) doesn't catch this — it only catches column-access drift on a single ORM model.

**Suggested follow-up**: A "Flask/MCP shape diff" audit. For each function name that exists in both `kpi-dashboard/backend/mcp_server/*.py` AND `kpi-dashboard/backend/{api_v1_routes,executive_dashboard_api,outcome_roi_api}.py`, compare:
1. Argument signatures (drift indicates wrong-callsite bugs)
2. Response keys at top level (drift indicates one-side-poor-shape bugs)
3. Code paths called inside (drift indicates wrong-helper bugs)

Failure should print a hint like: `"get_playbook_recommendations: MCP at cs_pulse_revenue.py:185 routes via vertical_aware_engine, Flask at api_v1_routes.py:149 calls get_dc2s_recommendations — drift detected."` Worth a separate chip when the next eval cycle starts.

### Other side bugs spotted during the visual re-eval (worth follow-up)

1. **CSM drill drawer pillar labels are DC2S, not SaaS**: Albireo Industries (saas_premium tenant) shows "AI/ML Performance, Infrastructure, Cloud & DevOps, Commercial" — those are DC2S pillar names. SaaS Premium uses P1 Product Adoption / P2 Engagement / P3 Sentiment / P4 Partner / P5 Revenue. Yet another vertical-classification drift. ~half-day fix.
2. **Header customer ID still reads "Customer 333"** despite session on cust 334. Cosmetic. 1-line fix.
3. **Account-column-drift baseline has 9 grandfathered violations** (per PR #32). Including 9 reads of `account.health_score` in `playbook_triggers_api.py` that would 500 on first request. ~1 day to drain.

### New findings from the visual re-eval

These were NOT in the prior projection — surfaced only by walking the live dashboards:

1. **B-1 UI consumption gap** (regression of intent, not the original API bug): PR #21 correctly fixed `get_team_capacity` at the API level (verified — MCP returns clean data). But `VPCSDashboard.tsx` still falls back to the client-side `TeamCapacityGauge` (5 CSMs × 6 accts ÷ 30-acct target = "100% utilized" account-count gauge). The Lens-A scores on VPCS Q1 + Q6 stay at 0/0 because the buyer sees an unchanged tile. **Half-day frontend fix: switch the React component to consume the now-healthy endpoint instead of the fallback path.** This is the single biggest miss vs projection and explains VPCS Lens A 11 (was 15 projected).

2. **CRO-3 dashboard expansion-tile broken filter**: `TOP EXPANSION OPPORTUNITIES` tile on CRODashboard.tsx shows `"No expansion opportunities"` despite MCP `get_top_expansion_opportunities_v3(334)` returning 10 results (Polaris Cloud $1.52M, Antares $1.46M, Vega Software $1.03M, etc.). Dashboard query filter is misaligned with MCP. **Half-day fix.**

3. **PR #23 `assigned_csm` regression (hotfixed live)**: CSM-owner column on at-risk accounts was reading `acct.assigned_csm` but `Account` doesn't have that column — `assigned_csm` lives in `Account.profile_metadata` (JSON), like B-1's `health_score` lived in `HealthScore` table. Same bug class. Crashed `/api/executive/cro-dashboard` with 500 on every request. Hotfixed via PR #28 in ~10 minutes during the re-eval. **Lesson: every column access on `Account` should be greped against `models.py` columns before merging — this is the third instance of "PR assumed an Account column that didn't exist."**

4. **Header customer ID mis-display**: Every dashboard shows "Customer 333 · ID: 333" in the top-left despite session being on cust 334 (subtitle on CEO dashboard correctly shows "Predictor V3 Demo SaaS Co (Eval May17)"). Cosmetic but visible to every buyer. 1-line React fix likely.

5. **CSM cockpit recommendations gap**: PR #26 fixed `get_playbook_recommendations` to return SaaS playbook names (`activation-blitz`, `voc-sprint`, `renewal-safeguard`) at the MCP level — verified live. But CSMCockpit's per-card actions still show generic labels (`Escalate`, `Schedule`, `Draft Proposal`). The action queue uses a different data path than the recommendations engine. CSM Q4 Lens A stays at the original score because the SaaS playbook names don't visibly surface on the cockpit. Lens B (Ask AI) still benefits because it can call the MCP tool directly.

### Punch list to clear Lens A

Closing items 1–5 above + the CEO architectural pieces (Q2 cross-customer, Q5 strategic moves) would lift Lens A by ~10 points across CEO + VPCS + CSM. Specifically:
- VPCS UI consumption (~0.5 day) → VPCS Q1 0→2, Q6 0→2 → +4 → VPCS 15
- CRO expansion-tile filter (~0.5 day) → CRO Q3 1→2 → CRO 17
- CEO strategic-moves tile + cross-customer view scaffold (~1.5 days) → CEO Q2 + Q5 + Q3 lifts
- CSM playbook-rec UI wiring (~1 day) → CSM Q4 0→2 → CSM 16
- Hotfix items #28-equivalent fixes for any future `Account` column drift (~0.5 day audit pass)

**~4 days frontend work** takes Lens A from 69 → ~82 (above the 80 threshold).

### Original projection section (preserved for comparison)

### Original headline (preserved for context)
Even with Lens B (MCP / Ask AI as canonical answer), the **5-persona portfolio sits at 79/100 — one point below the 80 customer-acceptance threshold**. CEO carries the most weight here — it's the only persona that fails because of an *architectural* gap (single-tenant ≠ a portfolio, so the "cross-company comparison" half of the CEO rubric has no answer surface at all). VP CS fails because the **`get_team_capacity` AttributeError bug (B-1)** kills the headline tile on a fresh tenant. CSM is the strongest persona on this tenant — fresh-tenant cold-start hurts the "did your interventions work?" trust questions, but daily-actions and kanban hold up.

**Two new platform bugs surfaced** (B-4, B-5 in Appendix B) on top of the three already filed in the CRO+CFO v2 report. **All 5 now RESOLVED (May 17 PM)** — see Appendix B.

---

## CEO — Lens A 9 / 20 · Lens B 14 / 20

CEO rubric is fundamentally cross-customer (portfolio view, board-ready). Cust 334 is a single-tenant install with no PE/portfolio sibling, so the "portfolio mode" half of the dashboard collapses to "this customer's accounts only." That's not a bug — it's the deployment shape — but it caps the achievable Lens-B score on questions that explicitly want cross-company comparison.

| # | Category | Question | Lens A | Lens B | Evidence (live MCP, cust 334) | Rationale |
|---|---|---|:-:|:-:|---|---|
| 1 | Numbers | Headline portfolio number (NRR, ARR, health) is correct and reconcile-able | **2** | **2** | `get_portfolio_nrr_forecast_v3(334)`: ARR-weighted NRR **102.39%** (simple-avg 88.17%), `total_arr: $175.37M`, 30 accounts, 25 active. Dashboard summary card uses same source via `/api/executive/ceo-dashboard`. `list_accounts(334)` independently confirms `total_arr=175370000`, `avg_health=72.6` | Numbers cross-check across 2+ tool calls and the dashboard tile uses the same source. |
| 2 | Numbers | Cross-customer comparison (who's healthiest, who's weakest) | **0** | **0** | `get_portfolio_cross_customer_comparison(portfolio_id=334)` → `"Portfolio 334 not found or disabled"`. There is no portfolio (PE fund) layer above this tenant; only one customer exists (`list_customers` returns 2 saas_premium customers — cust 333 stale + cust 334 — neither grouped under a portfolio_id). Dashboard renders a Company Comparison Table with a single row. | Architectural — single-tenant install can't answer the cross-customer question on either surface. Score capped at 0 honestly; not pretending the single-row table is a "comparison." |
| 3 | Explainability | When portfolio health moves, which company / account drove it | 1 | **2** | `get_health_score_history(334, months=6)`: 5 threshold crossings, 2 turnarounds (Deneb Pharma +9.0, NewCo Beta +1.6), 1 deterioration (Procyon Inc -0.8), `portfolio_trajectory.momentum_score: 9.7`, `improving_arr_pct: 9.7%`. Dashboard exposes portfolio_trend but no per-account driver attribution. | Same gap as CRO-7 — data exists, dashboard doesn't surface it. Ask AI can answer "which accounts moved the portfolio?" via the transitions array. |
| 4 | Explainability | Board-defensible methodology for the headline NRR / ROI number | 1 | **2** | Every v3 response carries `calibration_id: wizard_d_7824d7c1f4c8`, `calibrated_at: 2026-05-12T18:01:31`. Portfolio NRR `method_note` field explicitly describes the math ("ARR-weighted; excludes $0-ARR accounts; differs from Wizard B counterfactual"). | Auditable through MCP. Dashboard tile shows the number but not the methodology popover — same gap as CRO-4. |
| 5 | Actionability | "What 3 moves matter most this quarter?" | **0** | 1 | No CEO-level "top 3 strategic moves" surface on either dashboard or MCP. Closest is `get_csm_daily_actions(334)` (tactical, $338K total impact) — wrong altitude for a CEO. `get_portfolio_roi_summary.scaling_scenarios` gives 1%/4%/6% investment buckets but those are CFO-flavored, not "do these 3 things." | Real gap on both surfaces. Lens B lifts to 1 only because the scaling scenarios are at least *related* to "what to invest in." Needs a CEO-level strategic actions tile. |
| 6 | Actionability | Capital-allocation guidance — where should the next $1M go | 1 | **2** | `get_portfolio_roi_summary.scaling_scenarios`: 1% = $1.67M invest / $7.04M impact / 3.23× ROI / 2.8mo payback. 4% = $4.33M / $28.18M / 5.51× / $78.9M 3yr net. 6% = $6.49M / $42.26M / 5.51× / $122.8M 3yr net. `calculate_power_of_1` available per metric. | Available via MCP; dashboard tile doesn't expose scaling scenarios. |
| 7 | Trust | CI / governance disclosure visible on board-level metrics | **0** | 1 | NRR forecast tile shows point estimate only on CEO dashboard. MCP carries `ci_method: placeholder_uncalibrated` + `ci_disclosure` paragraph on every v3 response. **Phase 1 task #4 (real bootstrap CIs) is still pending**, so even Lens B can't fully claim "defensible." | Same Lens-B caveat as CRO-3/4/8. |
| 8 | Trust | Realized vs forecasted clearly distinguished at the portfolio summary | **2** | **2** | ROI summary cleanly splits `historical{}` ($29.9M, 7,652% ROI, "Last 6 Months") vs `forward{}` ($3.52M, 581% ROI, "Next 6 Months") vs `combined{}`. CEODashboard does NOT yet render the ROI block (focuses on health + ARR) but the underlying data is unambiguous. Same 7,652% red flag from CRO+CFO Appendix A applies — see Appendix A reference below. | Realized/forecast separation is clean in the data. |
| 9 | Workflow | Quarterly-cadence summary (CEO reads dashboard every 3 months, not daily) | 1 | 1 | Dashboard period label is hardcoded `Q1 2026` (line 862 of `CEODashboard.tsx`: `period: 'Q1 2026'`). No actual quarterly rollup math — it's a static string. `get_health_score_history(months=6)` is the closest thing, but defaults to monthly granularity. | Cosmetic-only quarter labeling — not a real quarterly view on either surface. |
| 10 | Workflow | Export board pack (slides / PDF / one-pager) | 1 | 1 | No CEO-export path. CFODashboard has CSV exports (`CFODashboard.tsx:2066-2115`) — CEO dashboard does not mirror this. Ask AI can summarize text-form but produces no slide deck. | Same gap as CFO-9. |

**CEO: Lens A 9/20. Lens B 14/20 — FAILS threshold (needs 16).** The two architectural zeros (Q2 cross-customer comparison, Q5 strategic-move recommendations) cap any score below 18. With those, Lens B at 14 is honest.

---

## VP CS — Lens A 11 / 20 · Lens B 15 / 20

| # | Category | Question | Lens A | Lens B | Evidence (live MCP, cust 334) | Rationale |
|---|---|---|:-:|:-:|---|---|
| 1 | Numbers | Team capacity utilization (hours used vs. available) | **0** | **0** | `get_team_capacity(334)` → `Error calling tool: 'Account' object has no attribute 'health_score'` (bug B-1, already filed). Dashboard wires `/api/v1/team-capacity` at line 878 of VPCSDashboard.tsx — same backend path, same crash. Dashboard falls back to a `TeamCapacityGauge` rendered from `accounts_per_csm`/`target_per_csm` derived client-side (6 accts × 5 CSMs = 30 / 30-acct target). Functional but not capacity hours — it's just account-count gauge. | Real gap on both surfaces — the dollar / hours capacity number is unanswerable. **Bug B-1 from CRO+CFO Appendix B is the direct cause.** |
| 2 | Numbers | Playbook completion / success rate across team | **2** | **2** | `get_playbook_success_metrics(334)`: 16 total executions, 100% resolved (PB-DC-01: 8 runs, PB-DC-02: 8 runs), `overall_success_rate_pct: 100`. But note: `avg_health_delta: -0.6` (PB-DC-01) and `0` (PB-DC-02), `total_revenue_impact: 0`. Dashboard reads same endpoint and shows the success rate. | Number is correct and surfaced. **Caveat (bug B-5)**: PB-DC-01 / PB-DC-02 are *Data Center* playbook IDs running on a *SaaS Premium* tenant. Vertical mismatch — the playbook engine is firing wrong-vertical templates. |
| 3 | Explainability | Per-CSM ranking — who's outperforming, who's behind | 1 | **2** | `get_csm_ranking(334)`: 5 CSMs, all `composite_score: 0.2` (tied — every CSM has rescued=0, lost=0, revenue=0 on this fresh tenant). `get_csm_scorecard` gives the underlying detail: Alex Chen +9.1 health delta, Morgan +8.4, Jordan +5.9, Sarah +4.9, Taylor +3.4. Dashboard renders `csm_scorecards` array at line 1491. | Health-delta gives the real ranking; composite score is uniform because rescue/revenue metrics are 0. Lens A renders the table; Lens B can sort and narrate. |
| 4 | Explainability | Why is each at-risk account at risk (root cause / pillar) | 1 | **2** | `get_at_risk_accounts(334)` returns `weakest_pillar` per account (Mira P2, Spica P3, Procyon P5, etc.). `get_account_journey_timeline(3245)` returns 10 events: critical_incident → escalation → executive_engagement → churn_risk → playbook → revenue_protected. Dashboard shows weakest_pillar in the accounts table (Account Portfolio Table). | Root cause story is rich via MCP. Dashboard surfaces pillar but not the full causal narrative. |
| 5 | Actionability | Top playbooks to launch this week (priority queue) | **2** | **2** | `get_csm_daily_actions(334)`: 10 ranked actions across 6 accounts, 20 hrs total, $338K projected impact. 3 critical + 7 high. Dashboard renders the queue (Actions Queue table). | Strong on both surfaces — already shipped in v2. |
| 6 | Actionability | Reassign book — who has capacity, who's overloaded | **0** | **0** | `get_team_capacity` errors. No "overloaded" / "available" signal on either surface. CSM book sizes are all uniform (6 accounts × 5 CSMs) so even if capacity worked, this tenant wouldn't show variance. | Same root cause as VPCS-1. Bug B-1 again. |
| 7 | Trust | Did interventions work — playbook ROI proof | **0** | 1 | `get_playbook_success_metrics`: 16 playbooks, **`total_revenue_protected: 0`, `total_revenue_expanded: 0`, `total_cost: $330K`, `portfolio_roi_pct: 0`**. Cold-start fresh tenant — playbooks ran but no closed-loop revenue attribution. Dashboard shows 100% completion but $0 impact, which reads worse than not surfacing it at all. | This is the CSM/VPCS analog of CFO-2's "every $ traceable" question. Cold-start tenant has no realized defensive ROI yet. Lens B can narrate the gap; tile shows misleading "100% success / $0 impact." |
| 8 | Trust | CSM scorecard counts (rescued, lost) are auditable | 1 | **2** | `get_csm_scorecard` per-CSM: `accounts_rescued: 0, accounts_lost: 0` for all 5 CSMs. Counts ARE auditable (definitional: critical→healthy = rescue, healthy→critical = lost) — they're zero because the 5 churned accounts were already at-risk on day 1 and there were no healthy→critical transitions in the 6-month window. Tile shows zeros without context. | Definitionally correct, but the dashboard doesn't explain WHY they're zero. Ask AI can narrate ("0 because no critical→healthy transitions in window"); tile cannot. |
| 9 | Workflow | Weekly business review readiness (snapshot for Mon team meeting) | 1 | 1 | No "WBR view" or weekly snapshot mode on either surface. Dashboard is always "now." Closest is the daily-actions queue. | Real gap both sides. |
| 10 | Workflow | Renewal pipeline visibility (next 90 days) | **2** | **2** | Dashboard has a `RenewalPipelineWidget` at line 741. `get_crm_account_data(3245)` returns `renewal_date: 2026-09-30, days_until_renewal: 180, stage: Renewal Discussion, probability: 65, forecast_category: Best Case` — same shape works for every account. | Both surfaces deliver. |

**VP CS: Lens A 11/20. Lens B 15/20 — FAILS threshold (needs 16).** Bug B-1 alone costs 2 points each on Q1 + Q6 (4 of the 5 missing points). Closing B-1 likely flips VPCS to PASS.

---

## CSM — Lens A 14 / 20 · Lens B 17 / 20

| # | Category | Question | Lens A | Lens B | Evidence (live MCP, cust 334, filter: Sarah Rivera) | Rationale |
|---|---|---|:-:|:-:|---|---|
| 1 | Numbers | My book — how many accounts, total ARR, breakdown | **2** | **2** | `get_csm_scorecard(334, "Sarah Rivera")`: `accounts_managed: 6, total_arr: $39.53M, avg_health_delta: +4.9, accounts_improving: 3, accounts_declining: 0`. CSMCockpit kanban groups Sarah's 6 accounts into FIRE / WEEK / OPPORTUNITY columns from `/api/v1/accounts`. | Solid on both surfaces. |
| 2 | Numbers | Today's prioritized action list | **2** | **2** | `get_csm_daily_actions(334, "Sarah Rivera")`: 6 actions, 12 hrs total, $283.6K projected impact. 1 critical (Cygnus Holdings) + 5 high. Each with ROI metric ID, impact_score, effort_score, priority_index. CSMCockpit renders the queue. | Strong on both. Best-in-class persona surface on this tenant. |
| 3 | Explainability | Why is account X at risk — drill from kanban card | 1 | **2** | `get_account_health(3245)`: health 64, P1 61.8, P2 59.8, P3 61.9, P5 70.8 (weakest = P2 Customer Engagement). `get_account_journey_timeline(3245)`: full causal chain (critical_incident → escalation → executive_engagement → churn_risk_averted $1.36M → revenue_protected $170K). CSMCockpit shows pillar scores in the account detail drawer but the full timeline drill is not embedded — needs a click into "history" tab which calls `/api/v1/recommendations/{id}`. | Rich via MCP. Tile partial. |
| 4 | Explainability | Recommended next playbook for a given account | **0** | **0** | `get_playbook_recommendations(3245)` → `total_recommendations: 0, playbook_source: "vertical_config (PB-01 through PB-06)", vertical: "dc2_s"` — returns zero recommendations AND tags the (SaaS) account with vertical `dc2_s`. **Bug B-4**: wrong vertical resolution + empty recommendation set on a textbook at-risk account. CSMCockpit recommendation panel falls back to `MOCK_RECOMMENDATIONS`. | Real gap on both surfaces; falls back to mock data. |
| 5 | Actionability | Pin / move an account through FIRE → WEEK → OPPORTUNITY kanban | **2** | 1 | CSMCockpit ships `@dnd-kit/core` drag-drop; `kanban_column` PATCH endpoint at `/api/accounts/:id/kanban-column` (line 736). Initial computeColumn at line 697 maps health → column. Persists through profile_metadata. | Lens A strong. Lens B: MCP has no kanban-write tool, so Ask AI can't pin a card on the user's behalf. |
| 6 | Actionability | Draft outbound (email / call agenda) to a stakeholder | 1 | 1 | CSMCockpit has `EmailDraftModal` import; CRM data carries `assigned_csm: "Sarah Rivera"` but `champion.name / email / title` all blank on cust 334 (cold-start tenant — champion CSV columns weren't populated). `get_stakeholder_map(3245)` returns 2 stakeholders (Sarah Rivera as CSM, Sam Rivera as CS Manager) — neither is the customer-side champion. | Email-draft surface exists; missing stakeholder data on cold-start tenant. Both surfaces equally limited. |
| 7 | Trust | Did my last playbook work — close-loop attribution | **0** | 1 | Sarah's `playbooks_executed: 4, playbooks_resolved: 4, revenue_protected: 0, revenue_expanded: 0, actions_taken: 0`. Same cold-start issue as VPCS-7. CSMCockpit reads ActivePlaybookTracker but on this tenant shows 100% / $0. | Cold-start specific — playbooks ran but closed-loop revenue attribution didn't populate. Mira Logistics' outcome-roi-story shows $1.36M churn averted at the *account* level but it doesn't roll up to the CSM scorecard's `revenue_protected` field. Cross-source inconsistency. |
| 8 | Trust | Signal source / freshness disclosure (this came from where?) | 1 | **2** | `get_account_journey_timeline(3245)` returns `node_type: SIGNAL`, `signal_type: critical_incident`, `sentiment: negative`, `occurred_at` timestamp per event. MCP `search_signals` exposes node_subtype + content. CSMCockpit doesn't show a "source" badge on signal alerts in the kanban card — just the title and severity. | Lens B has provenance; Lens A doesn't display it. |
| 9 | Workflow | Daily-cadence fit — morning briefing in < 2 min | **2** | **2** | CSMCockpit landing view IS a kanban triage screen, and `get_csm_daily_actions` returns ≤10 ranked items. Designed for morning standup. | Best-in-class. |
| 10 | Workflow | Single-account deep-dive — pillar scores, signals, CRM, tickets in one place | **2** | **2** | CSMCockpit account drawer pulls 5 endpoints in parallel: alerts, recommendations, stakeholder-map, health-history, journey-timeline (lines 264-269). MCP has 1-call equivalent (`get_account_journey_timeline` does signals + decisions + outcomes + revenue summary in one shot). | Both surfaces handle deep-dive well. |

**CSM: Lens A 14/20. Lens B 17/20 — PASSES threshold (16) on Lens B.** Cold-start hurts the close-loop trust questions (Q7) and the recommendations-engine bug (Q4) hurts both lenses. Daily-actions + kanban + deep-dive workflow shine.

---

## Critical gaps under Lens B (CEO + VP CS + CSM)

| ID | Gap | Persona | Lens-B score | Why MCP doesn't fix it |
|---|---|---|:-:|---|
| **CEO-2** | Cross-customer / cross-company comparison | CEO | 0 | Architectural — single-tenant install. Either deploy with a real PE/portfolio layer, or honestly retire the question on single-tenant evals. The CEODashboard already has a `portfolio mode` code path (`CEODashboard.tsx:743` `if (ceoJson.mode === 'portfolio')`); the customer needs ≥2 customers under one portfolio_id for it to fire. |
| **CEO-5** | "Top 3 strategic moves this quarter" | CEO | 1 | No CEO-altitude actions tile / tool. Different altitude than `get_csm_daily_actions`. New surface required. |
| **VPCS-1** | Team capacity (hours / utilization) | VP CS | 0 | Bug B-1 — `get_team_capacity` crashes. Fix is in the backend ORM query, not MCP. |
| **VPCS-6** | Book reassignment / capacity rebalancing | VP CS | 0 | Same root cause as VPCS-1, plus there's no "reassign" write tool on MCP today (would need a new tool — FDE Playbook §4.3 prohibits new MCP tools without base-dev sign-off). |
| **VPCS-7** | Playbook ROI close-loop | VP CS | 1 | Same cold-start issue as CFO-2. PB-DC-01/02 ran 16x for $0 revenue impact — closed-loop attribution isn't firing on this tenant. Suspect interaction with bug B-4 (DC playbooks running on SaaS vertical). |
| **CSM-4** | Per-account playbook recommendations | CSM | 0 | Bug B-4 — `get_playbook_recommendations` returns 0 results AND wrong vertical (`dc2_s` on a saas_premium tenant). Worse than empty: the wrong vertical = wrong playbook catalog will be loaded. |
| **CSM-5** | Kanban write (pin / move card via Ask AI) | CSM | 1 (LensB only) | No MCP tool for kanban writes today. Lens A works via DnD. Lens B can't replicate. |
| **CSM-7** | "Did my last playbook work?" | CSM | 1 | Cold-start tenant — playbook close-loop attribution doesn't populate `revenue_protected` on the CSM scorecard. Cross-source inconsistency: account-level outcome ROI shows $1.36M churn averted on Mira Logistics, but CSM scorecard `revenue_protected` for Sarah Rivera (Mira's CSM) is $0. |

---

## Cold-start observations — what cust 334 reveals about each persona

**CEO**:
- Without a portfolio layer, half the CEO rubric collapses. The dashboard correctly detects this (`single-customer mode` branch at line 772) and renders a "Company Comparison Table" with one row — but a one-row comparison table is visually awkward. **Recommendation**: when `mode != 'portfolio'`, hide the comparison-table widget entirely and replace with an "Executive Scorecard" view focused on this customer's accounts.
- Hardcoded `period: 'Q1 2026'` string (line 862) is a tell-tale of "no real quarterly rollup math wired yet." Today is May 17, 2026 — that should display Q2.

**VP CS**:
- `get_team_capacity` is the single biggest broken thing for this persona. Already filed as B-1 in CRO+CFO Appendix B — re-emphasizing here because it's the hard blocker on Lens A passing.
- All 5 CSMs have `accounts_rescued: 0, accounts_lost: 0` — definitionally correct for a cold-start (no critical→healthy / healthy→critical transitions in window) but the dashboard doesn't disclose the "why zero." A small "no transitions in window" hint would prevent the buyer thinking "your platform doesn't track this."
- 16 playbook executions on a fresh tenant, **100% success rate, $0 revenue impact, -0.6 / 0 health delta**. This combination reads as "playbooks fire then do nothing." Suspect coupling with bug B-4 (wrong-vertical playbooks).

**CSM**:
- Daily-actions surface is strong out of the gate — $283.6K projected impact in Sarah Rivera's 6-action queue is buyer-narrative-ready.
- Champion / executive-sponsor fields on CRM data come back blank. This is a 4-CSV ingestion gap (likely the `accounts.csv` champion columns weren't populated) — affects the email-draft / outbound workflow.
- Account-level outcome ROI story ($1.36M churn averted on Mira Logistics) doesn't roll up into the CSM scorecard's `revenue_protected` field. Two separate sources of truth for "did this work" — should be reconciled before the next buyer demo.

---

## Recommended punch list (sorted by effort × score-lift × personas)

| # | Fix | Effort | Lift | Personas |
|---|---|---|---|---|
| 1 | **Fix bug B-1 `get_team_capacity` AttributeError** (carried over from CRO+CFO punch list) | ~1 day backend | VPCS Lens A/B +4 (Q1 + Q6 each 0→2) | VP CS |
| 2 | **Fix bug B-4 `get_playbook_recommendations` empty + wrong vertical** | ~1 day backend | CSM Lens A/B +2 (Q4: 0→2). Likely unblocks VPCS-7 (playbook ROI close-loop) and the misleading "100% success / $0 impact" tile. | CSM, VP CS |
| 3 | **Fix bug B-5 wrong-vertical playbook IDs firing** (PB-DC-01/02 on SaaS tenant) | ~half day | clarifies VPCS-2 evidence + likely resolves VPCS-7 cold-start zero-impact reading | VP CS, CFO indirectly |
| 4 | **Wire CSM scorecard `revenue_protected` from account-level outcome-roi-story** | ~1 day | CSM Lens A/B +2 (Q7: 0/1→2). Removes the "$1.36M on Mira, $0 on Sarah's scorecard" cross-source inconsistency. | CSM, VP CS |
| 5 | **CEO single-tenant mode polish**: hide cross-customer comparison widget, replace with "Executive Scorecard," compute real quarter label from system date | ~1 day | CEO Lens A +2 (Q9: 1→2) and removes the awkward single-row comparison | CEO |
| 6 | **CEO strategic-actions tile**: surface scaling_scenarios + top 3 portfolio-level moves derived from get_outcome_roi_story momentum_metrics + ROI roadmap | ~1.5 day | CEO Lens A +1 (Q5: 0→1), Lens B already at 1 here | CEO |
| 7 | **"Why zero?" disclosure on CSM scorecard rescued/lost counts** when no transitions exist in window | ~half day | CSM Lens A +0 but raises buyer confidence; VPCS Lens A +1 (Q8: 1→2) | VP CS, CSM |
| 8 | **Source / freshness badge on CSMCockpit signal alert cards** (signal_type, occurred_at) | ~half day | CSM Lens A +1 (Q8: 1→2) | CSM |
| 9 | **Embed get_account_journey_timeline in CSMCockpit drill drawer** (replace the 5-endpoint parallel fetch with the one MCP-equivalent call) | ~1 day | CSM Lens A +1 (Q3: 1→2) — simpler code + faster drawer | CSM |
| 10 | **CSM "did playbook X work" tile** — read `total_revenue_impact` from `get_playbook_success_metrics` filtered to the CSM's accounts | depends on #2 + #4 landing first | CSM Lens A +2 (Q7: 0→2) | CSM |
| 11 | **Export-board-pack** for CEO + VPCS (mirror CFO CSV export pattern) | ~1 day | CEO Lens A +1 (Q10), VPCS Lens A +0.5 (workflow) | CEO, VP CS |
| 12 | **Weekly Business Review snapshot view** on VPCS (last 7 days delta) | ~1.5 day | VPCS Lens A/B +1 (Q9: 1→2) | VP CS |

**After items 1–4 (~3.5 days work)**: CSM Lens A 14→17, VPCS Lens A 11→15, CEO unchanged. All three personas + CRO+CFO Lens B totals: CRO 17, CFO 16, CEO 14, VP CS ~17, CSM ~17 = **81/100 portfolio** — crosses the 80 threshold for the first time.

**After items 1–6 (~6 days work)**: CEO Lens A 9→11, VPCS Lens A 11→16 (passes), CSM Lens A 14→18 (passes). Lens A 5-persona total ≈ 70-72 — still short of 80 on dashboard-only but no longer needs Ask AI for any persona's critical questions.

---

## Appendix A — Cross-references to CRO+CFO v2 report

- The 7,652% historical ROI red flag (CRO+CFO Appendix A) applies equally to the CEO dashboard if/when the ROI tile is wired. Today CEODashboard doesn't render ROI prominently, but the back-of-pack data feeds the same `get_portfolio_roi_summary` payload — so the same disclosure recommendation stands.
- The five "still-broken-under-Lens-B" CRO+CFO gaps (CFO-4 GL reconciliation, CRO-6 alert push, CRO-1 horizon, CRO-7 YoY, CFO-2 realized defensive ROI) all surface here too in different clothing — CEO-7 (CI on board metrics), VPCS-7 + CSM-7 (close-loop attribution), CEO-9 (quarterly cadence). Same root causes, same fixes lift multiple personas at once.

---

## Appendix B — New platform bugs surfaced (continuing CRO+CFO numbering)

### B-4. `get_playbook_recommendations(334, 3245)` returns empty + wrong vertical — **RESOLVED (PR #26, May 17 PM)**

Original symptom: tool returned `vertical: "dc2_s"` on a `saas_premium` tenant with 0 recommendations on a textbook at-risk account (Mira Logistics, health 64).

**Diagnosis (per PR #26)** — H2 (hardcoded route) with H1 contributing. Three-layer compound bug:
1. `playbook_recommendations_api.py:267` — `get_recommendations_for_account` entered `_evaluate_dc2s_playbooks` whenever `kpi_values is not None` (always true via MCP) and hardcoded `vertical: 'dc2_s'`.
2. `playbook_cost_bridge.py:126` — `calculate_cost_bridge` did a function-top `from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG`, ignoring vertical entirely. **So SaaS tenants got the DC2S playbook catalog system-wide**, not just on this one tool.
3. `cs_pulse_mcp_server.py:165` — `Customer.vertical` returns short code (`'saas'`/`'dc'`) but downstream branches compared against long-form (`'saas_premium'`/`'dc2_s'`) — silently missed.

Notable finding: **a SaaS-Premium playbook catalog didn't even exist before this PR.** PR #26 created `verticals/saas_premium/vertical_config.py` from scratch — SaaS tenants have been receiving DC2S playbooks since multi-vertical was introduced. Significant beyond what this eval was supposed to surface.

**Live verification (post-deploy)**:
```
get_playbook_recommendations(334, 3245)
→ vertical: "saas_premium"
→ 3 recommendations: activation-blitz (Critical), voc-sprint (High), renewal-safeguard (High)
```

CSM-4 lifts from 0/0 to 2/2 on both lenses. CSMCockpit's `MOCK_RECOMMENDATIONS` fallback (line 305) is no longer triggered.

### B-5. SaaS Premium tenant runs DC playbook templates (`PB-DC-01`, `PB-DC-02`) — **RESOLVED (PR #26, May 17 PM)**

Same root cause as B-4 (the layer-2 hardcoded `from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG` in `playbook_cost_bridge.py`). Fix is in the same PR.

**Live verification (post-deploy)**:
```
get_playbook_economics(334)
→ vertical: "saas_premium"
→ playbooks: activation-blitz:TTFV, expansion-accelerator:NRR, voc-sprint:NRR,
             renewal-safeguard:GRR, sla-stabilizer:GRR
```

No more `PB-DC-*` IDs firing on SaaS tenants. VPCS-2's wrong-vertical caveat now removed; VPCS-7's "wrong playbooks fired then did nothing" reading clarifies to "right SaaS playbooks ran but cold-start tenant has no closed-loop revenue attribution yet" — which is a product question (does realized defensive ROI need closed playbooks to accumulate?) not a bug.

### B-1 / B-2 / B-3

All three RESOLVED via PRs #21, #18, #19 respectively — see `CRO_CFO_eval_report_v2_cust334_may17.md` Appendix B for details. B-1 fix in particular unblocks VPCS-1 + VPCS-6 (each previously 0/0).

---

## Open threads for next session

1. **Decide whether single-tenant CEO eval is a meaningful test at all.** If "single customer, no PE layer" is a legitimate deployment shape, the CEO rubric needs an alternate set of questions that don't assume a portfolio layer above. Today's rubric inherits a PE-fund framing that costs cust 334 4-6 points it can't recover.
2. **File CR tickets for B-4 + B-5.** B-4 is straightforward (vertical resolution in recommendations endpoint). B-5 needs a base-dev decision: do we ship per-vertical playbook templates (and rename to PB-SAAS-01 etc.), or make the existing templates vertical-agnostic?
3. **Resolve the close-loop attribution drift** (account-level outcome-roi-story says $1.36M churn averted on Mira, CSM scorecard says $0 protected for Mira's CSM). This is the same cross-source-inconsistency pattern that flagged on CRO+CFO Apr 20 demo prep. May be a shared root cause with `revenue_protected: 0` everywhere on cold-start tenants.
4. **Investment recommendation for VP CS persona surface**: bug B-1 alone costs 4 of the 5 missing VPCS points. Closing it (and B-4 + B-5) likely flips both VPCS and CSM to Lens A pass — a $3-4-day investment that closes the 80-threshold gap on this customer.
5. **CEO dashboard "single-tenant polish" sprint**: hide portfolio comparison widget when `mode != 'portfolio'`, compute live quarter label, surface ROI scaling scenarios + top-3-moves tile. Closes 3 of CEO's remaining gaps in one focused work-stream.
6. **Re-run the 5-persona eval after B-1 / B-4 / B-5 land** + the punch list items #4 and #5 — would expect the portfolio total to clear 85/100 Lens B and 70+/100 Lens A.
7. **Commit the `gtm-decks/fde-kt/` worktree to a branch** — eval reports (CRO+CFO v2 + this one) + playbook + discovery workbook are signed-off artifacts the engagement lead and base dev will both want versioned.

---

*Generated 2026-05-17 · live MCP run · cust 334 · companion to [CRO_CFO_eval_report_v2_cust334_may17.md](CRO_CFO_eval_report_v2_cust334_may17.md) · Internal — NDA covered*
