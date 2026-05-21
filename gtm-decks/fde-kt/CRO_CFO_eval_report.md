# CRO + CFO Persona Eval — First Pass Findings

**Tenant evaluated**: customer_id 333 (`Predictor V3 Demo SaaS Co`), $175.4M ARR, 30 accounts
**Data source**: `results/sanity/after_step8_relogin_ux.json` (deploy 2026-05-12) + dashboard source (`kpi-dashboard/src/components/dashboard/CRODashboard.tsx`, `CFODashboard.tsx`)
**Scoring**: 0 = no, 1 = partial / data exists but not surfaced, 2 = yes / fully present
**Pass threshold**: 16 / 20 per persona

---

## TL;DR scoreboard

| Persona | Score | Threshold | Status | Critical (0) | Partial (1) | Pass (2) |
|---|---|---|---|---|---|---|
| **CRO** | **8 / 20** | 16 | ❌ BELOW | 3 | 5 | 2 |
| **CFO** | **13 / 20** | 16 | ❌ BELOW | 2 | 3 | 5 |
| **Portfolio** | **21 / 40** | 32 | ❌ NEEDS MORE CALIBRATION | | | |

Both personas miss the threshold. The CFO is close enough that 2–3 targeted UI fixes flip it to PASS. The CRO has structural data-join gaps that will take a sprint of UI work.

---

## CRO — 8 / 20

| # | Question | Score | Evidence | Gap |
|---|---|:-:|---|---|
| 1 | Total revenue at risk next quarter, by account, in <10s | 1 | `cro.revenue_at_risk = $39.9M` portfolio total; `v3_top_at_risk` returns 5 accounts with NRR. | "Next quarter" not bound — forecast is 12mo. No Q-bound filter on dashboard. |
| 2 | When NRR forecast moves, can I see which accounts moved it and why | 1 | Per-account `term_decomposition` + `top_drivers_count=3` in v3 response. | No historical comparison — no "what changed since last week / quarter" delta view. |
| 3 | Top 3 expansion ranked by $ + confidence (not vibes) | 1 | `v3_top_expansion` returns 5 ranked by `expansion_lift`; API returns CI bounds. | Confidence intervals NOT rendered on dashboard tile. |
| 4 | Methodology defensible to board | 1 | `v3_engine: predictor_v3`, `calibration_id: wizard_d_7824d7c1f4c8`, Path D CI disclosure shipped (commit `162c0676`). | Methodology disclosure not on CRO dashboard tile — only in API + Ask AI response. |
| 5 | CSM owner shown for each at-risk account | **0** | `CRODashboard.tsx:74-82` RiskAccount interface has no owner field. `team_capacity` API has `csm_names` + `per_csm_breakdown` separately. | **Join `team_capacity.per_csm_breakdown` into the at-risk accounts table** — column missing. |
| 6 | Alert when account flips healthy → at-risk | **0** | `signal_engine` has `AlertRecord` infrastructure + Slack/email routing. | **No CRO-facing UI** for new at-risk flips. Grep across CRO components finds no `alert`, `flipped`, `newly_at_risk`. |
| 7 | Compare this Q's risk vs last Q vs last year | **0** | `ha_historical_nrr_pct_ttm=90.21%` (TTM) + `ha_arr_churned/expanded/contracted` exist. | **No QoQ/YoY comparison tile**. CRODashboard:834-835 has "vs Q3" in metric card text only, no dedicated comparison view. |
| 8 | CI on NRR forecast tile | 1 | Ask AI surfaces "(90% CI: 99.3% – 109.3%)" for Antares. v3 API returns `expected_nrr.{point, ci}`. | `CRODashboard.tsx:1105-1137` Forward NRR card shows two point estimates only — no CI rendered. |
| 9 | Drill from portfolio → single account in 2 clicks | **2** | `CRODashboard.tsx:1281` onClick → `fetchTimeline(account.account_id)` → timeline modal with account detail. | None — works as advertised. |
| 10 | Revenue-at-risk reconcile-able to CRM | 1 | `get_crm_account_data` MCP tool exists; drill-down to account detail exists (Q9). | No explicit "view in Salesforce" link or reconciliation column from a CRO tile. |

**CRO total: 8 / 20** — below 16 pass threshold.

---

## CFO — 13 / 20

| # | Question | Score | Evidence | Gap |
|---|---|:-:|---|---|
| 1 | Prove ROI with a number an auditor will accept | **2** | `proof_realized_roi=23.1×`, `proof_revenue_protected=$20.36M`, `proof_total_cost=$880K`, `proof_executions_total=16`, `proof_executions_resolved=16`. Traceable to playbook executions via `post_load_attribution`. | None — defensible. |
| 2 | Every $ traceable to a specific playbook | **2** | 16 of 16 playbooks resolved = $20.36M attributed. `admin_post_load_attribution.executions_updated=16`. 1:1 attribution. | None. |
| 3 | CS investment scales with ARR — rationale at 2× revenue | 1 | Power-of-1 layer in `ls_layer_names` ("Growth (Po1 1%)") + `ls_layer_values=$6.12M`. 0.50% of ARR investment baseline. | "Rationale at 2× ARR" — explicit projection not on dashboard; needs Ask AI query or new tile. |
| 4 | Headline numbers reconcile-able to GL | **0** | Numbers come from `outcomes.csv` (CRM export), not GL. No GL drill-through. | **Architectural gap** — needs accounting integration or explicit "CRM-sourced" disclosure label. |
| 5 | Audit trail shows every assumption behind ROI | **2** | 3-layer story: "Already Delivered" (realized, 23.1×), "Still Protectable" (forecast, 54.5×), "Growth (Po1 1%)" (5.9×). Path D CI disclosure shipped. Each layer exposes its assumption. | None. |
| 6 | CS investment broken down by playbook category | **0** | `CFODashboard.tsx:735-755` shows flat allocation: Playbook 30% / CSM 45% / Overhead 25%. `get_playbook_economics` MCP tool exists but not surfaced. | **Wire `get_playbook_economics` into a new CFO tile** breaking out the 30% by category. |
| 7 | Po1 lift assumption disclosed and bounded | **2** | `ls_layer_names="Growth (Po1 1%)"` — "1%" explicit in layer label; `ls_layer_values=$6.12M`. | None. |
| 8 | Distinguish realized vs forecasted dollars | **2** | 3-layer story clearly splits realized (Layer 1) vs forecasted (Layers 2+3). Phase badge + Past-Three-Lenses section added in commits `ccde917a`, `1cae6193`. | None. |
| 9 | Export ROI calculation for board materials | 1 | `CFODashboard.tsx:2066-2115` — two CSV exports ("Export CFO Brief", "Export Portfolio Summary"). | No PDF / PPT / XLSX board-ready export. |
| 10 | CI visible where it matters | 1 | v3 API returns CI; Ask AI surfaces CI in Antares query. | Dashboard tiles don't render CI — same gap as CRO Q8. |

**CFO total: 13 / 20** — below 16 pass threshold but only 3 points away.

---

## Gap classification + recommended fix path

Per the FDE Playbook coordination protocol (overlay / PR-to-main / base-dev request).

### Critical gaps (score = 0) — 5 items

| ID | Gap | Fix path | Effort |
|---|---|---|---|
| CRO-5 | CSM owner column missing from at-risk accounts table | **PR to main** — UI-only join of `team_capacity.per_csm_breakdown` into `RiskAccount` interface | ~0.5 day |
| CRO-6 | No CRO-facing alert when account flips healthy → at-risk | **PR to main** — new alert badge consuming existing `AlertRecord` table; surface as toast or sticky banner | ~1.5 day |
| CRO-7 | No quarter-over-quarter / year-over-year revenue-at-risk comparison | **PR to main** — new comparison tile using historical `ha_*` fields; needs time-bucket aggregation | ~1.5 day |
| CFO-4 | Headline numbers not reconcile-able to GL | **Base-dev request** — accounting integration is architectural. Short-term: add "Source: CRM (Salesforce)" disclosure label on every dollar tile. | ~half day for disclosure label; weeks for true GL integration |
| CFO-6 | CS investment not broken down by playbook category | **PR to main** — wire `get_playbook_economics` into CFO investment tile; replace flat 30% with category breakdown | ~1 day |

### Partial gaps (score = 1) — 8 items

| ID | Gap | Fix path | Effort |
|---|---|---|---|
| CRO-1 | "Next quarter" not bound — forecast is 12mo only | **Overlay or PR** — add horizon selector on CRO dashboard (renewal / Q1 / 12mo) | ~half day |
| CRO-2 | No delta-since-last-period view on NRR forecast | **PR to main** — snapshot forecast weekly + delta tile | ~2 days |
| CRO-3, CRO-8, CFO-10 | **CI bounds not rendered on dashboard tiles** (data exists in API + Ask AI) | **PR to main** — single shared `<ForecastWithCI>` component used on all NRR/expansion tiles | ~1 day, fixes 3 questions at once |
| CRO-4 | Methodology disclosure not on CRO tile (only API + Ask AI) | **PR to main** — small "i" info popover on each forecast tile linking to methodology + calibration_id | ~half day |
| CRO-10 | No "view in Salesforce" link on at-risk account drill-down | **Overlay** if SF instance is per-customer; **PR to main** for generic CRM link adapter | ~half day overlay, ~1 day generic |
| CFO-3 | No explicit "rationale at 2× ARR" Po1 projection on dashboard | **PR to main** — scaling-scenario tile using existing Po1 tool | ~1 day |
| CFO-9 | No PDF / PPT export — only CSV | **PR to main** — wire existing CSV export through a print-friendly template; PPT export via separate `report_generation_agent` (referenced in plan.md as GAP-9) | ~1 day for PDF; weeks for PPT |

### Pass items (score = 2) — 7 items

CRO-9 (drill-down), CFO-1 (auditable ROI), CFO-2 (1:1 playbook attribution), CFO-5 (layered audit trail), CFO-7 (Po1 disclosure), CFO-8 (realized vs forecast split).

---

## Recommended punch list — order of operations

This is the order I'd run the fixes if I were the FDE on this account. Sorted by effort × persona-score-lift.

1. **Shared `<ForecastWithCI>` component** — ~1 day, fixes CRO-3, CRO-8, CFO-10 simultaneously. CRO +2, CFO +1. (Largest leverage.)
2. **CFO investment by playbook category tile** — ~1 day, fixes CFO-6. CFO +2.
3. **CSM owner column on at-risk table** — ~half day, fixes CRO-5. CRO +2.
4. **"Source: CRM" disclosure labels** — ~half day, fixes CFO-4 partial. CFO +1.
5. **Horizon selector on CRO dashboard** — ~half day, fixes CRO-1. CRO +1.
6. **Methodology info popover** — ~half day, fixes CRO-4. CRO +1.
7. **QoQ comparison tile** — ~1.5 day, fixes CRO-7. CRO +2.
8. **Alert badge for healthy → at-risk flip** — ~1.5 day, fixes CRO-6. CRO +2.
9. **CFO scaling-scenario tile** — ~1 day, fixes CFO-3. CFO +1.
10. **PDF export for CFO board materials** — ~1 day, fixes CFO-9 partial. CFO +1.

**After items 1–4** (≈3 days work): CRO 8 → 12, CFO 13 → 17. CFO crosses PASS.
**After items 1–8** (≈5 days work): CRO 8 → 18, CFO 13 → 17. Both PASS.
**After all 10 items** (≈7 days work): CRO 18 / 20, CFO 19 / 20. Portfolio 37 / 40 — ready for handover.

---

## Items that need a base-dev coordination ticket (not FDE-shippable)

- **CFO-4 full fix** — true GL integration is an accounting connector, not an overlay. Short-term disclosure label is FDE-shippable; full fix is roadmap.
- **PPT export** — referenced as GAP-9 in `plan.md` (FDE Playbook §6.1 escalation path). Needs `report_generation_agent` from base dev.

---

## Notes for the FDE running this in production

- The eval was scored from a sanity snapshot + source code reading, not a live MCP replay (the MCP endpoint returned "Invalid or revoked API key" in this session — supply credentials before running the canonical eval script `scripts/sanity_check_cust{N}.py`).
- Once credentials are in place, the same questions should be put through Ask AI as the canonical instrument — the dashboard-source scoring above is the conservative case (a question scored 1 because Ask AI surfaces the data may score 2 once the customer accepts Ask AI as the primary surface).
- This snapshot is for `customer_id=333` — a demo tenant. Real customer evals will surface different gaps (different KPI selections, different playbook libraries, different signal channels).

---

*Generated 2026-05-16 · CSPulse_FDE_Discovery.xlsx companion file · Internal — NDA covered*
