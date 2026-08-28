# Dashboard label-accuracy audit — CFO / CRO / CEO / CSM

Run 2026-08-27, four parallel agents (one per dashboard), each doing the same
pass: enumerate every user-visible label, trace it to its backend source,
judge whether the label honestly describes what the number actually is
(using this session's established bug classes — items 5/6/7/8/12/17/22/34
etc., see `00-start-here/state-of-play.md`), and judge whether the field is
worth keeping at all. All four verified live against EC2 (customers 390,
401, 411-414) rather than relying on static reading alone.

**Per the user's three questions**: (1) keep? (2) accurate? (3) fix if not.
Status column shows what's actually been done vs. what's still open.

---

## CFO Dashboard (`CFODashboard.tsx`, `executive_dashboard_api.py::cfo_dashboard`)

### Already-documented items — live status check
| # | Item | Status |
|---|---|---|
| 5 | Po1 table is SaaS-shaped for every vertical | unchanged, confirmed live on 411/412 |
| 6 | constant `roi_pct` across accounts | still fixed, holding — 412 and 414 show distinct per-account values |
| 7 | Wizard B NRR flat 100 | unchanged — confirmed byte-identical across all 6 sampled customers; correctly hidden by the frontend gate today |
| 8 | disagreeing ROI numbers in one payload | **pinned to a concrete juxtaposition** — see new finding below |
| 10 | `predictor_v3_portfolio_nrr: null` | unchanged, 6/6 fail |
| 12 | `automation_rate: 0` hardcoded | unchanged, confirmed live |
| 22 | pillar_investments numerator/denominator divergence | **numerator now fixed** (doc was stale on this point — updated); denominator (`po1_cost` benchmark vs real spend) still open exactly as documented |

### New findings
| Field | Keep? | Accurate? | Fix | Status |
|---|---|---|---|---|
| "Current portfolio" ROI-scaling tile (`ROIScalingSection`) | yes | was **no** — showed a 10-account benchmark projection under a label promising today's real number | relabeled to "Fixed cost, modeled baseline" | **FIXED** |
| Caption "Portfolio modeled ROI multiple: 3x" directly above a tile reading "777%" | yes | partial — two numbers, same question, two computations | left as-is (root cause is item 8/22, needs a product decision on which basis is canonical) | open |
| "Projected Investment Ramp" fallback chart | yes | was **no** — hardcoded `$235K/month` regardless of customer size (28x a real customer's actual spend on 401) | now scales off `d.cs_investment`; renders empty when investment is genuinely 0 | **FIXED** |
| "Portfolio Pulse" traffic-light widget | yes | was **no** — re-derived health buckets from raw `health_score >= 70/50` instead of the account's already-computed `classification`, violating the centralized-thresholds rule | now buckets by `a.classification` | **FIXED** |
| "Contract renewals due · next 90 days" banner | yes | was **no** — dead code, `renewals_at_risk` was never returned by `cfo_dashboard()` at all | extracted `_compute_renewals_at_risk()` shared helper (also now used by CRO), wired into CFO's response | **FIXED** |
| "NRR Impact / Playbook" ratio | no (meaningless) | **no** — divided NRR uplift by a fixed target-tier account count (10), not a playbook count | replaced with "NRR Impact (Modeled)", no fake denominator | **FIXED** |
| "Foresight NRR" hero tile (Predictor v3 branch) | yes, but blocked | n/a — correctly gated off, unreachable while item 10 is unfixed | no action until item 10 ships | open (blocked) |

---

## CRO Dashboard (`CRODashboard.tsx`, `CROOverviewHonesty.tsx`)

### Already-documented items — live status
Items 91 (Confirmed-overclaim retirement) and 26/27 (Model C) both **holding, no drift**. Items 10, 7, 8, 5/11 all recur here in the same unfixed state as CFO.

### New findings (all open — none fixed yet)
| Field | Keep? | Accurate? | Issue | Recommended fix |
|---|---|---|---|---|
| Sidebar "Estimated Portfolio ROI" widget | yes | **no** | Same number the top "Playbook ROI" tile calls "Actual (playbook executions)" (confirmed live, customer 411: 9.7%) is captioned "Estimated" with a benchmark disclosure two inches away | Gate the sidebar caption on `playbook_roi_estimated`, same flag the tile tooltip already uses |
| "Estimated investment/impact" (sidebar) | yes | **no** | Same issue one level down — real measured spend ($750K) permanently captioned "Estimated" | same fix |
| "ROI scaling by volume" chart (10/50/200 accts, "Non-linear scaling" badge) | fix, don't drop | **no** | Hardcoded `×2.44`/`×3.79` multipliers, sourced nowhere in the codebase, identical for every tenant, sitting under a citation block naming 4 real external benchmarks it never used | Wire to the CFO's real `build_roi_scaling()`, or drop the fabricated chart |
| "Early Warning Lead" delta (`↑ 12d vs Q3`) | yes (value), no (delta) | **no** | Literal hardcoded string — every tenant shows the identical "+12 days" claim | Compute a real QoQ delta or drop the delta/trend arrow |
| "Playbook ROI" trend arrow (always up) + "vs Q3" restating current value | yes (value), no (trend) | **no** | `trend: 'up'` hardcoded regardless of actual value; "vs Q3" line has no real prior-period value behind it | Remove fabricated trend, or compute one |
| "vs Q3" framing generally | yes | partial | Backend's "previous" is prior calendar month, not prior fiscal quarter | Rename to "vs last month" or compute a real quarter boundary |
| "Foresight · Predictor v3 (Wizard D)" caption | yes | **no** | Unconditional — fires even when the real value is the Wizard-B/health-heuristic fallback (100% of 7 sampled tenants) | Reuse the same v3-check branch already written for the tooltip two lines away |
| Metric-guide banner's Predictor v3 description | yes | **no** | Same overclaim, no fallback clause, in the one explainer text a CRO is told to read | Add the fallback clause |
| Revenue cards vs `CROContextGraphStrip` | merge | yes (both) | Same 3 dollar figures rendered twice, seconds apart | Keep one |
| `QuarterlyAtRiskTile` vs `arr_exposure` footnote | keep, note duplication | yes (both agree today) | Two independent code paths compute the same figure — agree only because both read the same snapshot, no cross-check | Have frontend consume backend's `arr_exposure` directly for the "current" bucket |
| Story-arc `revenue_impact` dollar figures | yes | partial | No cross-arc dedup — an account matching two arcs' signal patterns would double-count its ARR (not yet observed live, but no guard exists) | Add a dedup pass or document arcs as non-exclusive |
| NRR Trajectory/Revenue Waterfall panel | yes | partial | Mixes real per-account churn calc with a flat $4,560/account benchmark cost, with **no tier badge at all** — the one persona view most in need of the honesty pattern Track A already built for CFO | Wire `data_source`/tier through, render `ProvenanceTierBadge` |
| "Playbook ROI" tooltip citing Power-of-1 benchmarks | yes | **no** | `cro_dashboard()` has no Power-of-1 import/calculation anywhere — a bare `0` is shown as if it were a benchmark projection; will misfire the moment a tenant has ARR but no playbook execution yet | Call the real Po1 estimator, or change the tooltip to an honest "no activity yet" |

---

## CEO Dashboard (`CEODashboard.tsx`, `PortcoCEODashboard.tsx`)

### Already-documented items — live status
Item 5/11 recurs a second time here (Portco's `POWER_OF_1_LEVER_IDS`, hardcoded SaaS levers for every vertical). Item 6 (constant ROI) **has drifted worse**: `ceo_dashboard()` has its own unfixed re-implementation — `arr_scale` cancels out of both numerator and denominator, so every customer regardless of ARR shows `roi_pct: 8`. Item 7 (NRR heuristic) likewise has its own unfixed copy, duplicated across 4 files, even though `outcome_roi_api.py` already replaced the same heuristic elsewhere and called it a "stale placeholder." Item 8/22 confirmed live as a *third* disagreeing number: customer 390 shows CEO `roi_pct=713`, CFO `roi_pct=500`, CRO `playbook_roi_pct=0.0` simultaneously. The "Confirmed" overclaim retirement never reached CEO's own "Portfolio ROI"/"Platform ROI" sidebar widgets.

### New findings (all open — none fixed yet)
| Field | Keep? | Accurate? | Issue | Recommended fix |
|---|---|---|---|---|
| Header period badge | yes | **no** | Hardcoded `"Q1 2026"` literal; backend correctly returns `"Q3 2026"` | Read `ceoJson.quarter_label` |
| "Updated {time}" | yes | **no** | Hardcoded `"just now"`; backend returns a real timestamp | Read `ceoJson.last_updated` |
| "Top 3 Risks by ARR" widget | yes, rewire | **no** | Discards the backend's real, correctly-ranked top-5-at-risk accounts and synthesizes one fake pseudo-account per company instead (confirmed live: 5 real named accounts ready to render, e.g. Titan Hyperscale Labs @ health 14.7) | Fetch and render `highest_risk_accounts` directly |
| Health Distribution donut (portfolio-mode fallback) | fix mechanism | **no** | Invents a 60/40 critical/at-risk split of each company's real `at_risk_count` with no basis in real data | Have the backend return real per-tier counts; until then show one undifferentiated bucket |
| Company-mapping defaults (`health_score ?? 0`, `nrr ?? 100`) | yes | **no** | Missing NRR silently reads as a perfect 100% ("healthy"); missing health silently reads as 0 ("critical") — opposite failure directions, both wrong | Use null sentinel → "—" with an unavailable tier badge |
| "Accounts At Risk" summary card | yes | partial | Silently pools at_risk + critical into one number while the donut two tiles down shows them split | Rename "Unhealthy Accounts" or split to match |
| "Portfolio ROI" (sidebar) + "Platform ROI" (badge) | merge, drop one | n/a (duplicate) | Identical number, two different names on one page | Keep one |
| `PredictorV3Tile` footer "(enterprise profile...)" | fix | **no** | Dead ternary — both branches return the literal `'saas_enterprise'`; every vertical is labeled a SaaS enterprise account | Fix the ternary; stop forcing SaaS vocabulary onto non-SaaS verticals |
| `get_portfolio_summary()` "Portfolio ROI"/NRR in portfolio mode | fix | **no** | Function name/docstring/route all claim portfolio-wide aggregation; body is single-customer only (`customer_count: 1` hardcoded) | Implement real aggregation or relabel honestly |
| "Portfolio ROI" (CEO, %) vs "Portfolio ROI" (PortCo, ×) | rename one | n/a (divergence risk) | Same label, two unrelated engines/units on two dashboard variants for the same PE persona | Rename one, or reconcile to one engine |
| **PortCo "Synergy Realization Tracker"** — "{X}% of synergy value realized" | **drop until real, or wire it** | **no — worst finding of the whole audit** | The realized/projected split is `withSynergy.slice(0, half)` — an arbitrary array-slice with zero temporal/execution data behind it. A real `synergies_realized` DB column exists and isn't used. | Delete the widget, or wire it to the real column (after confirming that column is ever actually incremented) |
| "CS Initiatives (80%)" / "Platform Cost (20%)" | yes | partial | These are hardcoded default-ratio literals; once a user edits the real Cost Inputs, the percentages shown go stale | Compute from the actual values instead of a literal |

---

## CSM Dashboard (`CSMCockpit.tsx`, `CSMFocusFlow.tsx`)

Two of my own memory notes were checked and corrected by this audit: "needs mock data, empty without backend" is wrong — it's never empty, it silently substitutes fake accounts/actions/approvals on *any* unexpected response shape, with no indicator. "Signal Timeline non-functional" doesn't apply to these files (confirmed absent) — that note is CRO-sidebar-specific.

### Already-documented items recurring here
Item 13's banded churn_pct (80/40/15 by tier) resurfaces as the CSM's own "$ projected impact" and churn-risk chip math. Item 5/11's SaaS-shaped Po1 metrics resurface as the CSM's flat "2% improvement" benchmark assumption. Item 12's fabricated-zero class resurfaces as `account_health: 0.0` for system-triggered actions.

### New findings (all open — none fixed yet)
| Field | Keep? | Accurate? | Issue | Recommended fix |
|---|---|---|---|---|
| **Entire Accounts/Actions/Approvals lists, both layouts** | fix the fallback logic, keep the feature | **no — most consequential finding in the whole audit** | Silently substitutes `mockData.ts` fictional companies/dollar amounts on *any* fetch failure, parse error, **or legitimately-shaped-differently response** — confirmed this is already happening today on customer 390 (real endpoint returns `{"pending":[...]}`, code reads `data.approvals \|\| data.data`, neither exists, so it always shows fake approvals). Approve/Reject on the fake data either only mutates local state or 404s against a fake string ID — nothing is ever approved server-side. | Only fall back on network/parse error, never on a successfully-parsed empty/different-shaped result; add a visible demo-mode banner when mock data renders; fix the key mismatch (`data.pending`) and wire Approve/Reject to the real endpoints |
| "Champion" name in account drawer | yes | **no** | Real `champion_name` exists on every account (confirmed live, customer 411) but Cockpit never maps it (`champion` vs `champion_name`) and FocusFlow's detail endpoint doesn't carry the field under any name | Map the field name; add it to the detail endpoint |
| CSMCockpit "Reports" tab (playbooks completed, $ saved, NPS delta, expansion pipeline, weekly bar chart) | fix or drop | **no** | 100% hardcoded literals, zero backend calls, identical forever for every customer — a CSM could quote these numbers to a manager | Wire to the real (already-existing, unused) playbook-success-metrics endpoint, or delete the tab |
| "Influence: {N}" (People tab) | yes | **no** | Shows the account's own internal CSM/CS-Manager as "stakeholders," and "Influence" is actually raw graph-degree, not a scored metric | Filter internal roles out; rename the field |
| "Group by" dropdown, Tickets tab, History tab, Run Playbook/Ask AI buttons, kanban action buttons | drop or wire | n/a (dead) | No-op state, hardcoded empty arrays, or missing handlers entirely | Wire or remove each |
| FocusFlow "Trend" field (always "Stable") | yes | **no** | No endpoint this component calls ever returns a `trend` key — every account, every session, identical | Compute a real trend from health-score deltas, or remove |
| Health badge fallback (`health_score ?? 70`) | yes | **no** | Adjacent numeric cell honestly shows "—" for missing data; the colored badge on the same row fabricates 70 → green "Healthy" | Use one consistent unavailable-state, never a colored default |
| "{X}% churn risk" chip, "{ARR} ARR" chip (Actions detail) | fix or drop | **no** | Both fields are never serialized by the backend at all — only render in mock mode; even if wired, churn risk is really a 3-bucket constant | Serialize real values and relabel as tiers, or remove |
| **"QBR frequency at {N}/yr" recommended action** | fix | **no — confirmed live, reproducible bug on the CSM's actual task list** | Hardcodes `P4-KPI3` as the QBR-cadence metric; that code means "QBR frequency" only for dc2_s. On datacenter_v1, P4-KPI3 is **Power Efficiency (PUE)** — every healthy datacenter_v1 account (411-414, live) shows its PUE reading mislabeled as an annual QBR count | Resolve QBR-cadence/expansion-trigger KPI codes per-vertical via the KPI catalog's semantic role, not a hardcoded code |
| Playbook "$ projected impact" via `_PLAYBOOK_ROI_MAP` | fix | **no** | Map is keyed to dc2_s's own PB-01..06 ID space; `_VERTICAL_HANDLERS` is permanently empty so every vertical reuses it. datacenter_v1's own PB-03 ("Fleet Utilization") inherits dc2_s's PB-03 mapping ("Product Adoption"); its 7 other real playbooks get `$0 impact` from a pure ID collision | Key the ROI map off each vertical's own playbook catalog |
| "Recent Signals" fallback text | fix | **no** | Conflates leading/trailing signal types under one label; date construction splices a month name into an ISO template with a hardcoded year | Rename the fallback path; fix the date bug |
| "Snooze 1d" button | fix label or wire | **no** | Only removes the item from in-memory state for the current session — doesn't persist or resurface after 24h | Persist server-side, or relabel "Dismiss for now" |
| "Ask AI" button (Actions footer) | wire or drop | n/a (dead) | No handler | Wire or remove |
| CSM filter dropdown, notification bell | keep | **yes** | Verified accurate, real backend-wired, good-pattern controls | none needed |

---

## Totals across all four dashboards

- **~173 distinct labels/fields audited**.
- **CFO: 7 new issues found, all 7 fixed this session** (plus 1 already-documented item's numerator confirmed fixed, updating stale doc state).
- **CRO: 12 new issues found, 0 fixed** (all flagged above, ranked by the auditing agent).
- **CEO: 11 new issues found, 0 fixed** — includes the single worst finding of the whole sweep (fabricated Synergy Realization Tracker).
- **CSM: ~20 new issues found, 0 fixed** — includes the most operationally dangerous finding (silent mock-data fallback covering real approvals with no server-side effect).
- User decision (2026-08-27): stop after CFO fixes + full findings list; CRO/CEO/CSM fixes deferred to a future session, prioritized by the "top 3" each agent already ranked.
