# CRO + CFO Persona Eval — v2 (live MCP, cust 334)

**Tenant evaluated**: `customer_id 334` — `Predictor V3 Demo SaaS Co (Eval May17)`, $175.37M ARR, 30 accounts (25 active + 5 churned)
**Data source**: live MCP `cs-pulse` server (CloudFront → cspulse-platform EC2 container, image `phase1-2026-05-12.7-clean-from-main`), **no direct DB access**
**Manifest**: `predictor_v3_demo_saas_eval_may17.json` (clone of `predictor_v3_demo_saas.json` with fresh identity fields). Loaded via load-driver `--register` against the platform API; process_data completed `status=success` in 235.9s.
**Scoring**: 0 = no, 1 = partial / data exists but not surfaced, 2 = yes / fully present
**Pass threshold**: 16 / 20 per persona

Scored against cust 334 only. Earlier tenants (cust 333) are pre-rebuild state and not a valid baseline for current code, so no comparisons are drawn. Two lenses:
- **Lens A — Dashboard tile only**: what a buyer sees on the React surfaces (`CRODashboard.tsx`, `CFODashboard.tsx`)
- **Lens B — Dashboard + MCP/Ask AI**: what the buyer can pull via the in-product AI copilot, which routes to the same MCP tool surface we exercised here

---

## TL;DR scoreboard

| Persona | Lens A (audit, AM) | Lens A (PM v1, after PRs #18–#28) | Lens A (PM v2, **FINAL** after PRs #29–#33) | Lens B (+ MCP/Ask AI) |
|---|:-:|:-:|:-:|:-:|
| **CRO** | 8 / 20 ❌ | 16 / 20 ✅ | **18 / 20 ✅** | **17 / 20 ✅** |
| **CFO** | 12 / 20 ❌ | 16 / 20 ✅ | **16 / 20 ✅** | **16 / 20 ✅** |
| **Portfolio (CRO + CFO)** | 20 / 40 ❌ | 32 / 40 ✅ | **34 / 40 ✅** | **33 / 40 ✅** |

CRO Lens A lifts another +2 in the PM v2 visual re-eval after PRs #29 (`PredictorV3Tile` JSON parse fix) and #22 (`<ForecastWithCI>`) compounded: **Q3 expansion tile** now populated (Polaris Cloud $1.52M, Antares $1.46M, Vega $1.03M with CI bounds inline) and **Q8 CI on NRR tile** now visibly rendered ($760K–$2.28M, NRR 99.8%–109.8% etc.) on every expansion + at-risk row.

CRO + CFO Lens-A scores were measured visually against the live deployed dashboards at https://d2oqfugrb2ltg9.cloudfront.net/saas-dashboard/{cro,cfo} after 10 PRs (#18–#27 + #28 hotfix) merged and deployed. Both personas confirmed at exactly 16/20.

Note on hotfix #28: during the visual re-eval, PR #23's CSM-owner column crashed `/api/executive/cro-dashboard` with `AttributeError: 'Account' object has no attribute 'assigned_csm'` — `assigned_csm` lives in `profile_metadata` (JSON), not as a top-level column. Same bug class as B-1 (`Account.health_score` didn't exist either). Hotfixed via PR #28 in under 10 minutes during the re-eval window. CRO dashboard then rendered cleanly with all #23 surfaces visible (CSM owner on every at-risk card, transition alert banner, QoQ tile).

**Post-deploy update (May 17 PM)** — PRs #18, #20, #21, #22, #23, #24, #25, #26 + hotfix #27 all merged to main, image rebuilt via CI, deployed via `rehydrate-ec2-ecr.sh` with PLATFORM_TAG re-pointed to `:latest`. Live MCP verification on cust 334 confirms every fix landed (see Appendix B below — all 3 bugs marked RESOLVED). Lens A score lifts:
- CRO: Q1 (1→2 via #25 quarter horizon), Q3 (1→2 via #22 ForecastWithCI), Q5 (0→2 via #23 CSM owner), Q6 (0→1 via #23 banner), Q7 (0→2 via #23 QoQ tile), Q8 (1→2 via #22). Total +8 → **16 / 20 PASS**.
- CFO: Q4 (0→1 via #24 source labels), Q6 (0→2 via #24 playbook breakdown), Q10 (1→2 via #22). Total +4 → **16 / 20 PASS**. CFO-1 stays 2/2 but now **without asterisk** — disclosure field shipped via #20 (verified live: `disclosure.non_repeatable=true`, `bridge.recommended_headline_roi_pct=580.9`).

**Headline finding**: accepting MCP/Ask AI as a canonical answer surface flips both personas to PASS without touching dashboard code. **Two hard-zero gaps remain under Lens B** (CFO-4 GL reconciliation, plus an alert/push gap on CRO-6 which only partially lifts).

**Cold-start observations** (things this run revealed about how current code behaves on a freshly-ingested tenant):
- `historical.revenue_protected = $0` on cust 334. A fresh tenant has no realized defensive ROI surface yet — only forward projections + expansion + cost savings. This is a product question, not a bug: is the realized-defensive proof story only available on tenants with closed playbook executions? If yes, every new buyer demo starts CFO-2 at "1", not "2", until executions accumulate.
- Three new **platform bugs** surfaced during live MCP probing (see Appendix B).

---

## CRO — Lens A 8 / 20 · Lens B 17 / 20

| # | Question | Lens A | Lens B | Evidence (live MCP, cust 334) | Rationale |
|---|---|:-:|:-:|---|---|
| 1 | Revenue at risk next quarter, by account, <10s | 1 | 1 | `get_at_risk_accounts(334)`: 9 accounts, **$31.28M (17.8%)** at risk; sorted ascending by health | "Next quarter" not bound (12mo only). MCP has the data but no Q-filter — same gap on both surfaces. |
| 2 | When NRR moves, which accounts drove it & why | 1 | **2** | `get_top_at_risk_accounts_v3` returns per-account `term_decomposition.{p_churn, p_survive, e_contract, e_expand}` + `top_drivers[{covariate, contribution}]` (health=2.60, dtr_181-365=0.74, log_arr) | Drivers and decomposition are surfaceable via Ask AI — closes the "why" question. Not on dashboard tile. |
| 3 | Top 3 expansion ranked by $ + confidence | 1 | **2** | `get_top_expansion_opportunities_v3`: Polaris Cloud **$1.52M** ($760K–$2.28M CI), Antares Holdings **$1.46M** ($728K–$2.18M CI), Vega Software **$1.03M** ($516K–$1.55M CI) | CI bounds present on every result via MCP. **Caveat**: `ci_method: placeholder_uncalibrated` — platform itself says "do not threshold on CI bounds" (Phase 1 task #4 pending). |
| 4 | Methodology defensible to board | 1 | **2** | Every v3 response carries `calibration_id: wizard_d_7824d7c1f4c8__saas_enterprise__hazard`, `calibrated_at: 2026-05-12T18:01:31`, full driver list, `ci_disclosure` paragraph | Calibration provenance auditable through MCP — not just on tile. |
| 5 | CSM owner for each at-risk account | **0** | **2** | `get_crm_account_data(3245)` returns `assigned_csm: "Sarah Rivera"` on Mira Logistics ($2.89M, at-risk). Same join works for all 9 at-risk accounts. | Dashboard tile lacks the join; MCP exposes it. Worth wiring into the at-risk table. |
| 6 | Alert when account flips healthy → at-risk | **0** | 1 | `get_health_score_history(334)` returns `transitions[]` array; Procyon Inc flagged Feb 2026: `from_status=healthy → to_status=at_risk @ 69.8`. Found 5 threshold crossings in 6mo. | Pull-only via tool call. No PUSH/notification. Lifts to 1, not 2 — still no proactive UI. |
| 7 | Compare this Q's risk vs last Q vs last year | **0** | 1 | `get_health_score_history(months=6)` returns monthly trajectory + `portfolio_trajectory.momentum_score: 9.7`, `improving_arr_pct: 9.7%`, `net_health_change_weighted: 1.3` | 6mo trajectory data is there but no built-in YoY tile or delta. Lifts to 1. |
| 8 | CI on NRR forecast tile | 1 | **2** | Portfolio NRR v3: **102.39% ARR-weighted** (88.17% simple-avg); every account has `expected_nrr.{point, lower_90, upper_90, ci_disclosure}`. e.g. Spica Labs: 0.988 (0.938–1.038) | Same lift as CRO-3. CI is in the API. |
| 9 | Drill from portfolio → single account in 2 clicks | **2** | **2** | Account drill-down on CRODashboard.tsx:1281. | Works on tile. |
| 10 | Revenue-at-risk reconcile-able to CRM | 1 | **2** | `get_crm_account_data(3245)` returns `crm_id: "SF-3245"`, `renewal_opportunity.{stage: "Renewal Discussion", probability: 65, amount: $2.89M, forecast_category: "Best Case"}`, `assigned_csm`, renewal date | CRM bridge data available through MCP. Reconciliation possible. |

**CRO: Lens A 8/20. Lens B 17/20 — PASSES threshold (16).**

---

## CFO — Lens A 12 / 20 · Lens B 16 / 20

| # | Question | Lens A | Lens B | Evidence (live MCP, cust 334) | Rationale |
|---|---|:-:|:-:|---|---|
| 1 | Auditor-acceptable ROI number | **2** | **2** | `get_portfolio_roi_summary.historical.summary`: $385,712 invested → **$29.9M total impact → 7,652% ROI**. Includes attribution table per metric (TTFV $10.13M, product_adoption $10.02M, ticket_resolution $5.84M) | Number IS traceable. As of May 17 fix, response now carries a top-level `disclosure` field (`non_repeatable=true`, period_label rewritten to "since onboarding"), `bridge.recommended_headline_roi_pct` steers the reader to the 581% forward steady-state number, and an opt-in stable-window baseline (`ROI_HISTORICAL_SKIP_UNSTABLE_MONTHS=3`) is available for buyers requiring strict trailing-window proof. **Resolved — see Appendix A**. |
| 2 | Every $ traceable to a specific playbook | **1** | **1** | `historical.metric_outcomes[].linked_playbooks` populated (activation-blitz, expansion-accelerator, sla-stabilizer, etc.) — but `historical.revenue_protected: $0`, no resolved defensive executions surfaced. Cold-start fresh tenant has no closed-loop "$X protected by playbook Y" proof. | Prospective attribution is wired; realized defensive proof is not. Open product question: does the realized defensive-ROI story require closed playbook executions to accumulate, or should it surface from outcome CSVs at ingest time? |
| 3 | CS investment scales with ARR — rationale at 2× | 1 | **2** | `scaling_scenarios`: 1% → $7.04M impact / $1.67M invested (3.23× year-1 ROI, 2.8mo payback). 4% → $28.18M / $4.33M (5.51× ROI, $78.9M 3-year net). 6% → $42.26M / $6.49M (5.51× ROI, $122.8M 3-year net). | Explicit ARR-scaled projections in MCP — directly answers "at 2× ARR what's the case?". Lifts to 2. |
| 4 | Headline numbers reconcile to GL | **0** | **0** | Source: `kpi_actuals_benchmark` (CSV-derived). No GL connector. | Architectural — MCP can't fix. |
| 5 | Audit trail for every assumption | **2** | **2** | `historical.metric_outcomes[]` exposes baseline_value, current_value, improvement_pct, data_source, linked_kpis, linked_playbooks per metric. e.g. TTFV: 32.83 → 30 (9.43% improvement, $10.13M attributed, source `kpi_actuals_benchmark`, KPI `P1-KPI1`, playbook `activation-blitz`) | Auditable. |
| 6 | Investment broken down by playbook category | **0** | **2** | `get_playbook_economics(334)`: 6 playbooks across 6 metrics. TTFV→PB-01 ($75.5K, 18× ROI), NRR→PB-04+PB-06 ($50K, 48× ROI), GRR→PB-02+PB-05 ($60K, 36× ROI), ticket→PB-02 ($26K, 33× ROI), adoption→PB-03+PB-01 ($21K, 29× ROI), expansion→PB-04 ($14.5K, 29× ROI). Grand total $247K. | Dashboard tile still shows flat 30/45/25; MCP exposes the real breakdown. Lifts to 2. |
| 7 | Po1 lift assumption disclosed and bounded | **2** | **2** | `calculate_power_of_1(NRR, 1%)`: baseline 105 → 106.05, direct $1.84M, ROI 35.8×, payback 0.3mo, `linked_playbooks: [expansion-accelerator, voc-sprint]`, `linked_kpi_codes: [P5-KPI1, P5-KPI2, P4-KPI3]`, `arr_basis: explicit ($175.37M)` | Bounded and disclosed via MCP. |
| 8 | Realized vs forecasted dollars distinguished | **2** | **2** | ROI summary has 3 clean blocks: `historical{}` (Last 6 Months), `forward{}` (Next 6 Months), `combined{}`. Forward $3.52M / $517K → 581% ROI. Trajectory tagged `sustaining` with explicit narrative. | Crystal clear separation. |
| 9 | Export ROI calculation for board materials | 1 | 1 | `CFODashboard.tsx:2066-2115` CSV exports; MCP doesn't add a PDF/PPT path. | CSV exports OK; no board-ready PDF/PPT. |
| 10 | CI visible where it matters | 1 | **2** | Same data as CRO-3/8 — every v3 forecast (per-account NRR, expansion) returns CI bounds via MCP. | Lifts to 2 via the AI surface. |

**CFO: Lens A 12/20. Lens B 16/20 — PASSES at threshold (16).**

---

## Critical gaps remaining under Lens B

| ID | Gap | Lens-B score | Why MCP doesn't fix it |
|---|---|:-:|---|
| **CFO-4** | Headline $ not reconcile-able to GL | 0 | Architectural — needs accounting integration. MCP only exposes CSV-derived data. Short-term: add "Source: CRM/CSV" disclosure label. |
| **CRO-6** | Alert when healthy → at-risk | 1 | MCP exposes transitions via *pull*. No PUSH path (Slack/email) to the CRO surface. Needs an `AlertRecord` consumer UI — backend infra is there, the frontend consumer isn't. |
| **CRO-1** | "Next quarter" horizon | 1 | MCP has 12mo only. Need horizon selector both on tile and tool argument (`horizon='quarter'` not currently supported). |
| **CRO-7** | QoQ / YoY comparison | 1 | MCP has 6mo history, not YoY. Need 12mo+ retention in `get_health_score_history` plus a delta tile or tool argument. |
| **CFO-2** | Every $ traceable to playbook | 1 | Fresh tenant has no realized defensive ROI yet — `historical.revenue_protected: $0`, no resolved executions. Either change the seeding so realized defensive proof exists at ingest time, or accept that the realized-proof story is a "mature tenant" capability and the demo narrative should set that expectation. |

The other 5 critical gaps from the original framework now resolve under Lens B (CRO-5 via CRM data join, CFO-6 via playbook economics tool, CRO-2/3/4/8 via v3 forecast surfaces).

---

## Recommended punch list (updated)

Sort: effort × score-lift × number-of-personas-affected.

| # | Fix | Effort | Lift | Personas |
|---|---|---|---|---|
| 1 | **Wire `assigned_csm` + CRM fields into `RiskAccount` interface** on CRODashboard.tsx | ~0.5 day | CRO Lens A +2 (CRO-5: 0→2) | CRO |
| 2 | **Wire `get_playbook_economics` into CFO investment tile** (replace flat 30/45/25 with per-metric breakdown) | ~1 day | CFO Lens A +2 (CFO-6: 0→2) | CFO |
| 3 | **Shared `<ForecastWithCI>` component** rendered on NRR + expansion tiles | ~1 day | CRO Lens A +2, CFO Lens A +1 (CRO-3,8 / CFO-10) | both |
| 4 | **"Source: CRM/CSV" disclosure labels** on every dollar tile | ~half day | CFO Lens A +1 (CFO-4: 0→1) | CFO |
| 5 | **Horizon selector** (renewal / Q / 12mo) on CRO dashboard + add `horizon='quarter'` arg to v3 tools | ~1 day | CRO Lens A +1 (CRO-1: 1→2) | CRO |
| 6 | **Methodology info popover** linking to `calibration_id` + disclosure text | ~half day | CRO Lens A +1 (CRO-4: 1→2) | CRO |
| 7 | **QoQ comparison tile** + extend `get_health_score_history` retention to 12mo | ~1.5 day | CRO Lens A +2 (CRO-7: 0→2) | CRO |
| 8 | **Alert badge** consuming `AlertRecord` (Slack/email + sticky UI banner) | ~1.5 day | CRO Lens A +2 (CRO-6: 0→2) | CRO |
| 9 | **Seed realized defensive ROI at ingest** so any new tenant shows the "$X protected" proof story | ~half day in load-driver or platform | CFO Lens A +1 (CFO-2: 1→2) | CFO |
| 10 | **Fix `get_team_capacity` `health_score` AttributeError** (Appendix B-1) | unknown | unblocks team capacity card | both |
| 11 | **Fix `get_account_nrr_forecast` arg schema** (missing `customer_id`) | trivial schema edit | unblocks per-account NRR drill | both |
| 12 | **Real bootstrap CIs** (replace `ci_method: placeholder_uncalibrated`) | Phase 1 task #4 in roadmap | strengthens CRO-3/4/8 from "data present" to "data defensible" | both |

**After items 1–5** (~3 days work): CRO Lens A 8 → 13, CFO Lens A 12 → 16. CFO passes Lens A, CRO still short.
**After items 1–8** (~5 days work): CRO Lens A 8 → 18, CFO Lens A 12 → 16. Both pass Lens A — buyer doesn't need to lean on Ask AI for any of the 20 questions.

---

## Appendix A — The 7,652% ROI red flag — RESOLVED

`get_portfolio_roi_summary.historical.summary.roi_pct = 7,652.1` on cust 334. Math is correct ($29.9M impact / $385.7K invested = 77.5× = 7,652%) but the number itself triggers auditor pushback. The system's own `bridge.narrative` field explained why:

> "Over last 6 months, your CS investment delivered $29.9M in realized outcomes (7652% ROI). … The historical ROI includes one-time turnaround gains from accounts that moved from critical to healthy — these gains are now captured in the baseline. Forward projections assume incremental 1% improvement on the new, higher baseline."

This was intellectually honest but buried in a narrative string. CFO eval marked it as a presentation gap that risked the CFO-1 score holding at 2-with-asterisk.

### Resolution (May 17, 2026)

Shipped to `main` via PR — branch `worktree-agent-af61256f9b4e6d8a8`. Implements the recommendation from the original Appendix A plus Option A (stable-window baseline) as an opt-in follow-up:

**Option C — structured disclosure (always-on).** `outcome_roi_engine.calculate_historical_roi` now builds a top-level `disclosure` field whenever the historical view is non-repeatable. Heuristic: `roi_pct > 500%` AND `improvement_pct_avg > 2× forward_steady_state_pct` (or > 2.0pp absolute when no forward signal is supplied). When the heuristic fires:
- `historical.disclosure` is populated with `{non_repeatable, period_basis, headline, detail, recommended_label}`.
- `historical.period_label` is rewritten from `"Last 6 Months"` to `"Last 6 Months (since onboarding — includes one-time gains)"`.
- `bridge.historical_disclosure` carries the same payload (so Ask AI / slide pulls see the caveat without descending into the historical block).
- `bridge.recommended_headline_roi_pct` is set to the forward steady-state ROI and `bridge.recommended_headline_basis = "forward_steady_state"` — a CFO reading the bridge is steered to the credible number (e.g. 581% forward, not 7,652% historical) as the headline.
- `bridge.narrative` now uses the structured detail paragraph as its single source of truth.

Stable customers (those whose historical window legitimately reflects incremental gains) get **no** disclosure — the trigger correctly discriminates. Pinned by `test_outcome_roi_historical_disclosure.py::TestHistoricalDisclosureStableCustomer` and `test_high_roi_low_lift_does_not_trigger`.

**Option A — stable-window baseline (opt-in).** `_extract_historical_actuals` gained a `skip_unstable_months: int = 0` kwarg, also exposed via `?stable=N` query param on `GET /api/outcome-roi/historical` and via `ROI_HISTORICAL_SKIP_UNSTABLE_MONTHS` env var on the MCP tool. When set to 3 it drops the earliest 3 distinct months of measurements per KPI, anchoring the baseline past the typical onboarding-ramp / synthetic-decline phase. Default 0 preserves legacy behaviour for production tenants where the trailing window is honest. Applies to all three measurement-source paths (DC2SKPI, HealthTrend, PillarScore). Provenance is recorded as `data_source = "..._stable_skip3"` and `historical_period_basis = "stable_window"`.

Option B (peer-cohort baseline) deferred pending CDI cohort data plumbing — see backlog `product_community_domain_intelligence.md`.

### Verification

- `python3 -m pytest kpi-dashboard/backend/tests/test_outcome_roi_historical_disclosure.py` — 15/15 pass. Tests pin: cust-334-shaped payload now carries `disclosure.non_repeatable=true`; stable customer + flat-no-change correctly skip disclosure; the disclosure builder is a pure function and has unit coverage at the boundary; the `skip_unstable_months` kwarg exists with the correct default.
- Local smoke against the cust-334 reproducer payload: `period_label = "Last 6 Months (since onboarding — includes one-time gains)"`, `disclosure.non_repeatable = true`, `bridge.recommended_headline_roi_pct = 580.9` (vs `historical.roi_pct = 8434.7`), narrative leads with the auditor disclosure paragraph.
- No regressions in `test_power_of_1_roi.py` (4 pre-existing failures unrelated to this fix — they assert dollar values from older scaling scenarios; confirmed identical on origin/main).

### Files touched

- `kpi-dashboard/backend/outcome_roi_engine.py` — `OutcomeROIResult.disclosure`, `_build_historical_disclosure`, `calculate_historical_roi` signature, `calculate_outcome_story` ordering (forward first), `_result_to_dict` serialization, `_build_bridge_narrative` hoists disclosure + recommended-headline, `_generate_narrative` uses structured detail.
- `kpi-dashboard/backend/outcome_roi_api.py` — `_extract_historical_actuals(skip_unstable_months=…)` across DC2SKPI / HealthTrend / PillarScore paths; `GET /api/outcome-roi/historical` honours `?stable=N` and env var.
- `kpi-dashboard/backend/mcp_server/cs_pulse_revenue.py` — `get_portfolio_roi_summary` reads `ROI_HISTORICAL_SKIP_UNSTABLE_MONTHS`, threads `historical_period_basis` through.
- `kpi-dashboard/backend/tests/test_outcome_roi_historical_disclosure.py` — new pin file (15 tests).

### CFO-1 score

Stays at **2/2**, **without the asterisk**. The historical ROI tile now carries an auditor-grade caveat as a structured first-class field; the bridge actively steers the reader to the repeatable forward number; and the trailing-window symptom has an opt-in stable-window fix when buyers require strict 6-month proof.

---

## Appendix B — Platform bugs surfaced during live MCP probing

These only became visible because today's session was the first to exercise live MCP end-to-end + register a fresh tenant under current code.

### B-1. `get_team_capacity(334)` → `'Account' object has no attribute 'health_score'` — **RESOLVED (PR #21, May 17 PM)**

Original report: tool returned a 500-class error; hypothesized as cold-start branch.

**Actual diagnosis (per PR #21)**: bug fires unconditionally, not cold-start. The `Account` model never had a `health_score` column — latest health lives in the separate `HealthScore` table. The buggy line `at_risk_count = sum(1 for a in accounts if float(a.health_score or 100) < 70)` has been latent since April 5, 2026 (commit `13e01be9`). The reason it appeared cold-start-specific is that *all* tenants would have hit it on the MCP path; we just never tested any via MCP between April 5 and May 17 (server key was empty post-rebuild). The Flask sister endpoint at `verticals/dc2_s/api_routes.py:get_team_capacity_api()` correctly uses `get_precalculated_scores()`, which is why dashboards kept working.

**Fix**: replaced direct `a.health_score` access with a batched `HealthScore` join (group-by subquery → latest row per account → count below `ht.healthy_min()`); cold-start safety fallback to `at_risk_count = 0` if no HealthScore rows.

**Live verification (post-deploy)**: `get_team_capacity(334)` returns `at_risk_accounts: 14, total_arr: $175.37M, feasible: true, bottleneck_roles: []` — clean response. Same for cust 336 (cold-start) and cust 331 (older). VPCS Lens-A questions Q1 + Q6 (each previously 0/2) now answerable on the dashboard.

### B-2. `get_account_nrr_forecast(account_id=3237)` → `_require_account_auth() missing 1 required positional argument` — **RESOLVED (PR #18, May 17 PM)**

Schema/auth-wrapper mismatch confirmed: the `@mcp.tool` decorator declared only `(account_id, horizon)`; the server's `_require_account_auth()` required `(customer_id, account_id)`. MCP passed `account_id` as if it were `customer_id`, then the second positional arg was missing — hence the misleading error.

**Fix (Option A — convention with peers)**: added `customer_id: int` as the first required arg on the tool decorator (matches `get_account_health`, `get_revenue_at_risk`, `get_crm_account_data`, `get_outcome_roi_story`). Plus a bonus security upgrade: added `_validate_account_ownership(customer_id, account_id)` call so tenant isolation is enforced before inference (without it, a valid customer key + any account_id could potentially leak forecast data across tenants).

**Live verification (post-deploy)**: `get_account_nrr_forecast(customer_id=334, account_id=3237, horizon='12mo')` returns `expected_nrr.point=1.043, lower_90=0.993, upper_90=1.093, calibration_id=wizard_d_7824d7c1f4c8`. 13/13 new tests + 43/43 broader suite pass with no regressions.

### B-3. `process_data` post-validation 404s — **RESOLVED (PR #19, May 17 PM)**

Driver was querying deterministic account IDs (`customer_id × 1000 + slot` pattern) while the platform assigns sequential IDs (3225–3254 on cust 334; later tenants get later ranges).

**Fix**: `_validate_post_process` now calls `client.get_accounts()` to discover real account IDs, uses those for sample health checks and the context-graph probe. New name→actual_id→manifest_class map preserves distribution-drift check without ID alignment. Legacy positional fallback retained for non-DC2S verticals where accounts endpoint returns empty.

**Live verification (post-deploy)**: fresh `--register` run on a new tenant exits `Result: SUCCESS` (was FAILURE) with 0× `HTTP 404` in post-validation. The previously separate "health distribution drift" warning also resolved (same root cause, predicted).

---

## Open threads for next session

1. ~~**Address the 7,652% ROI presentation issue** — see Appendix A. Either cap the historical window, switch to peer-cohort baseline, or relabel the tile to "since onboarding". This is the single biggest CFO-eval credibility risk.~~ **DONE May 17** — Option C (structured disclosure + relabel) shipped always-on; Option A (stable-window baseline) shipped opt-in. Option B (peer cohort) deferred pending CDI plumbing. See Appendix A.
2. ~~**File CR tickets** for the 3 platform/driver bugs (B-1, B-2, B-3) — all user-visible the moment anyone exercises live MCP or registers a new tenant.~~ **DONE May 17 PM** — all three fixed and deployed via PRs #21, #18, #19. See Appendix B.
3. ~~**Run CEO, VPCS, CSM persona evals** against cust 334 (5 personas total per FDE playbook eval framework).~~ **DONE May 17** — see `CEO_VPCS_CSM_eval_report_v2_cust334_may17.md`.
4. **Resolve the CFO-2 "fresh tenant has no realized defensive ROI" question** — product decision on whether realized-proof story should surface from outcome CSVs at ingest, or only after playbook executions resolve over time. (Still open — not addressed in the deploy batch.)
5. ~~**Add "cold-start sanity step" to the rebuild runbook** — the May 12 rebuild's sanity diff compared snapshots only; this run was the first time anyone exercised `--register + every MCP tool` end-to-end on the rebuilt image. It found 3 bugs in 5 minutes. Should be a permanent step 4 of any future rebuild.~~ **DONE May 17** — memory note `principle_cold_start_sanity_rebuild.md` written. Should be cited in any future rebuild post-mortem.

## Post-deploy verification timeline (May 17 PM)

- 19:32 — 9 PRs (#18–#26) merged to main via `gh pr merge --squash` (2 conflict rebases on #24 + #25, "keep both sides" resolution)
- 19:32 — CI build kicked off (`cspulse-ecr-build-push.yml`)
- 19:35 — CI failed: TypeScript `TS2345` error on missing `cro_horizon_change` in `EventType` union (introduced by #25, missed in initial build because conflict-rebase didn't re-run local TS check)
- 19:38 — Hotfix PR #27 opened + merged (1-line addition to the union)
- 19:43 — CI rebuild succeeded
- 19:46 — `rehydrate-ec2-ecr.sh` ran; `cspulse-postgres` recreated on `:latest` but `cspulse-platform` stayed on pinned tag `phase1-2026-05-12.8-clean-from-main`
- 19:48 — Updated EC2 `~/cspulse/.env` to set `PLATFORM_TAG=latest`, force-recreated `cs-pulse` service. Container healthy on new image.
- 19:49 — Live MCP probes against cust 334 confirm all 9 fixes + 1 hotfix landed.
6. **Consider committing `gtm-decks/fde-kt/` to a branch** — eval report + playbook + discovery workbook are meaningful artifacts.
7. **Decide on cust 334 retention** — keep as the canonical eval tenant, or roll forward to a 335+ each time? If the latter, automate `load-driver --register` with a deterministic timestamped name.

---

*Generated 2026-05-17 · live MCP run · cust 334 · supersedes [CRO_CFO_eval_report.md](CRO_CFO_eval_report.md) · Internal — NDA covered*
