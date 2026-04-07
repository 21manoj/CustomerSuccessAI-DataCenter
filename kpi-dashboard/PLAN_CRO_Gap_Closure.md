# CRO Dashboard — Gap Closure Plan

## Context
Evaluated from two CRO perspectives: $500M (B+, 76/100) and $100M (A-, 83/100).
Mid-market ($100M) replaces spreadsheets immediately. Enterprise ($500M) needs expansion pipeline, segment views, and renewal analytics.
Goal: Mid-market → 90/100, Enterprise → 86/100.

## Current State
- 5 sections: Revenue Cards (3), Metric Cards (4), Story Arcs, Highest Risk Accounts Grid, Right Sidebar (Power-of-1 ROI Engine, Revenue Timeline)
- Sub-views (lazy-loaded): SignalTimelineView, ContextGraphView, ROIEngineView, AccountsView
- API: `GET /api/executive/cro-dashboard` returns ~25 fields including story_arcs, nrr_waterfall, nrr_trajectory, risk_accounts
- Backend: `executive_dashboard_api.py` lines 544-878 (`cro_dashboard()`)
- **Unused data already in API response:** `nrr_trajectory` (never rendered), `nrr_waterfall.accounts[]` (never rendered), `renewals_at_risk` (never rendered)

---

## Sprint 1: Mid-Market Polish (3 days)

### 1.1 Pinned / Favorite Accounts
**Problem:** $100M CRO personally manages top 5 accounts — wants persistent quick-access list, not a sorted table.

| File | Change |
|------|--------|
| `backend/models.py` | Add `AccountPin` model: user_id, account_id, customer_id, pinned_at, display_order. Unique constraint on (user_id, account_id). |
| `backend/verticals/dc2_s/api_routes.py` | Add `GET/POST/DELETE /api/dc2s/accounts/pins` — list/add/remove pinned accounts. Returns account details (health, ARR, classification) for pinned set. |
| `src/components/dashboard/CRODashboard.tsx` | New "My Accounts" strip above Risk Accounts grid: horizontal scrollable cards for pinned accounts (health badge, ARR, trend arrow). Star icon on each risk account card to pin/unpin. Persists across sessions via API. |

### 1.2 Expansion Signal Detail
**Problem:** "Expansion Pipeline: $4.2M" — but which accounts? What signals?
**Infrastructure:** Context graph has SIGNAL nodes with expansion-related subtypes. `_get_expansion_candidates()` already counts them.

| File | Change |
|------|--------|
| `backend/executive_dashboard_api.py` | Enrich `expansion_pipeline` in CRO response: add `expansion_accounts[]` with account_id, account_name, arr, expansion_signal (usage_growth / new_department / champion_advocacy / upsell_request), expansion_probability, estimated_value. Source: ContextNode SIGNAL nodes with positive revenue_impact + Account health ≥70. |
| `src/components/dashboard/CRODashboard.tsx` | Make Expansion Pipeline card clickable → expands to show account list with signal type badges (green tags: "Usage +45%", "New dept onboarding", "Champion request"). Each row shows estimated expansion value. |

### 1.3 Render Existing Unused Data
**Problem:** Backend returns `nrr_trajectory`, `nrr_waterfall.accounts[]`, and `renewals_at_risk` but UI ignores them.

| File | Change |
|------|--------|
| `src/components/dashboard/CRODashboard.tsx` | (a) NRR Projection card: add mini sparkline from `nrr_trajectory` data (T+30/60/90 dots). (b) Revenue Waterfall sidebar: add expandable per-account breakdown from `nrr_waterfall.accounts[]` (account name, churn $, save $, net). (c) New "Renewals at Risk" badge on metrics row when `renewals_at_risk.length > 0` → clickable to show list with days-to-renewal + health. |

### 1.4 CRO-Level Actions
**Problem:** CRO sees risk but can't act from their dashboard — must switch to CSM view.

| File | Change |
|------|--------|
| `src/components/dashboard/CRODashboard.tsx` | On risk account card hover/click, show action buttons: "Draft Email" (opens EmailDraftModal with account context), "View Timeline" (loads revenue timeline in sidebar), "Escalate to VP CS" (creates notification). Import EmailDraftModal from csm components. |

**Sprint 1 files: 4 (3 modified, 1 new model)**

---

## Sprint 2: Revenue Operations (4 days)

### 2.1 Expansion Pipeline by Stage
**Problem:** $500M CRO manages expansion like a sales pipeline — needs funnel stages.

| File | Change |
|------|--------|
| `backend/models.py` | Add `ExpansionOpportunity` model: account_id, customer_id, stage (identified/qualified/proposal/negotiation/closed_won/closed_lost), signal_source, estimated_value, probability, owner_csm, created_at, updated_at, closed_at. |
| `backend/executive_dashboard_api.py` | Add `GET /api/executive/expansion-pipeline` endpoint. If ExpansionOpportunity records exist, return real pipeline. Else, synthesize from ContextNode expansion signals with rule-based stage assignment (signal detected=identified, health≥70 + usage growth=qualified, champion advocacy=proposal). |
| `src/components/dashboard/CRODashboard.tsx` | Replace static Expansion Pipeline card with funnel visualization: horizontal funnel bars (Identified → Qualified → Proposal → Closed). Show $ value + account count per stage. Clickable stages expand to account list. |

### 2.2 Account-Level NRR Attribution
**Problem:** "Which 10 accounts are dragging NRR below 100%?" — needs ranked impact list.

| File | Change |
|------|--------|
| `backend/executive_dashboard_api.py` | Add `nrr_attribution` to CRO response: for each account, compute individual NRR contribution (expansion $ - contraction $ - churn $) / total ARR × 100. Sort by impact (worst first). Flag accounts where NRR contribution < 0 (net detractors). |
| `src/components/dashboard/CRODashboard.tsx` | New "NRR Drivers" panel (expandable below NRR card): ranked list of accounts. Green bars = NRR contributors (expansion), Red bars = NRR detractors (contraction/churn). Each row: account name, ARR, individual NRR %, $ impact. Top 5 shown by default, "Show all" expands. |

### 2.3 Renewal Win/Loss Analysis
**Problem:** "We renewed 47 accounts at 98% GRR — why did 3 shrink?"

| File | Change |
|------|--------|
| `backend/executive_dashboard_api.py` | Add `GET /api/executive/renewal-outcomes` endpoint. Query accounts with renewal_date in past 90 days. Classify: renewed_full (same or higher ARR), renewed_contracted (lower ARR), churned (no renewal). For contracted/churned, pull latest ContextNode signals as reasons. Return: win_rate, grr, outcomes[] with account + reason + $ delta. |
| `src/components/dashboard/CRODashboard.tsx` | New "Renewal Outcomes" view (add as sub-view or sidebar section). Donut chart: renewed (green) / contracted (amber) / churned (red). Below: table with account name, previous ARR, new ARR, delta, reason (from signals). |

### 2.4 Board-Ready Export
**Problem:** Same as CFO — CRO needs board slides.

| File | Change |
|------|--------|
| `src/utils/dashboardExport.ts` | Add `exportCROPdf(data)`: Revenue summary (3 cards), NRR trend chart, story arc distribution, top risk accounts table, expansion pipeline summary. Reuse PDF utility from CFO Sprint 1.3. |
| `src/components/dashboard/CRODashboard.tsx` | Export button in header → "Export PDF" / "Export CSV". |

**Sprint 2 files: 4 (2 modified, 1 new model, dashboardExport.ts extended)**

---

## Sprint 3: Enterprise Intelligence (4 days)

### 3.1 Territory / Segment Views
**Problem:** $500M CRO needs NRR by segment (Enterprise vs Mid-Market), by region, by CSM.

| File | Change |
|------|--------|
| `backend/utils/segment_analyzer.py` | **NEW** — `analyze_by_segment(customer_id, dimension)`: groups accounts by industry, region (from profile_metadata), ARR tier, or assigned CSM. For each segment: account count, total ARR, avg health, NRR, revenue at risk, expansion pipeline. |
| `backend/executive_dashboard_api.py` | Add `GET /api/executive/cro-segments?dimension=industry|region|tier|csm` endpoint. |
| `src/components/dashboard/CRODashboard.tsx` | New "Portfolio Segments" view (add to sidebar nav or as toggle on overview). Dimension selector (Industry / Region / Tier / CSM). Table: segment name, accounts, ARR, health, NRR, risk $. Heatmap coloring on NRR column. Click segment → filters main dashboard to that segment. |

### 3.2 Competitive Displacement Intelligence
**Problem:** Story arc "competitive_displacement" exists but no dedicated competitive view.

| File | Change |
|------|--------|
| `backend/executive_dashboard_api.py` | Add `competitive_intelligence` to CRO response: query ContextNode signals with subtypes containing 'competitive', 'competitor', 'displacement'. Group by competitor name (from signal properties). Return: competitor_name, accounts_affected, total_arr_at_risk, signal_count, latest_signal_date. |
| `src/components/dashboard/CRODashboard.tsx` | New "Competitive Threats" card in metrics row (or expandable section). Table: competitor name, # accounts, $ at risk, trend (growing/stable). Click competitor → shows affected account list with signal details. Only renders when competitive signals exist (graceful empty state). |

### 3.3 QBR/EBR Coverage Tracker
**Problem:** "Have we done QBRs with all accounts >$1M ARR this quarter?"

| File | Change |
|------|--------|
| `backend/models.py` | Add optional `last_qbr_date` and `qbr_cadence_days` to Account profile_metadata schema (no migration needed — JSON field). |
| `backend/executive_dashboard_api.py` | Add `qbr_coverage` to CRO response: for accounts with ARR > threshold ($500K default), check last_qbr_date from profile_metadata or ContextNode meeting signals. Return: total_qualifying, covered (QBR in last 90d), overdue, never_met. |
| `src/components/dashboard/CRODashboard.tsx` | "QBR Coverage" widget in sidebar: circular gauge showing coverage % (e.g., "12/15 accounts covered"). Red text for overdue count. Expandable list of overdue accounts with days-since-last-QBR. |

### 3.4 Logo Churn vs Revenue Churn Split
**Problem:** Board wants both metrics separated.

| File | Change |
|------|--------|
| `backend/executive_dashboard_api.py` | Add `churn_split` to CRO response: `logo_churn_count`, `logo_churn_rate` (lost accounts / total accounts), `revenue_churn_amount`, `revenue_churn_rate` (lost ARR / total ARR). Source: accounts with health < 30 or churned status. |
| `src/components/dashboard/CRODashboard.tsx` | New dual metric in metrics row or sidebar: "Logo Churn: 2 accounts (3.2%)" + "Revenue Churn: $1.8M (1.8%)". Color-coded: green if below benchmark, red if above. |

**Sprint 3 files: 5 (2 modified, 1 new utility, 2 sections added)**

---

## Sprint 4: Forecast & Integration (3 days)

### 4.1 NRR Forecast Scenario Planning
**Problem:** "What happens to NRR if we lose Account X?" or "What if we close the Acme expansion?"

| File | Change |
|------|--------|
| `backend/executive_dashboard_api.py` | Add `GET /api/executive/nrr-scenario?exclude_account=X&add_expansion=Y` endpoint. Recomputes NRR excluding/adding specific accounts. Returns: baseline_nrr, scenario_nrr, delta, affected_accounts. |
| `src/components/dashboard/CRODashboard.tsx` | "What-If" button on NRR card → modal with account checklist. Toggle accounts on/off to see NRR impact. Shows: "If Account X churns → NRR drops to 97.2% (-2.8pp)". Real-time recalculation. |

### 4.2 Salesforce/CRM Revenue Reconciliation
**Problem:** CRO's expansion forecast lives in Salesforce/Clari. Dual systems = credibility gap.

| File | Change |
|------|--------|
| `backend/integrations/crm_connector.py` | **NEW** — Abstract CRM connector interface. Initial implementation: manual CSV upload of Salesforce opportunity extract (opp_id, account_name, stage, amount, close_date). Matches to CS Pulse accounts by name/domain. |
| `backend/executive_dashboard_api.py` | If CRM data exists, add `crm_reconciliation` to CRO response: side-by-side comparison of CS Pulse expansion pipeline vs CRM pipeline. Flag mismatches (CS Pulse sees expansion signal but no CRM opp, or CRM opp exists but CS Pulse health is declining). |
| `src/components/dashboard/CRODashboard.tsx` | "Pipeline Reconciliation" badge on Expansion Pipeline card when CRM data available. Shows match rate and mismatch list. |

**Sprint 4 files: 4 (2 modified, 1 new, 1 new utility)**

---

## Summary

| Sprint | Focus | Days | Grade Impact |
|--------|-------|------|-------------|
| 1 | Mid-market polish (pins, expansion detail, unused data, actions) | 3 | $100M: 83 → 90 |
| 2 | Revenue operations (expansion funnel, NRR attribution, renewal outcomes, export) | 4 | Both: +5 points |
| 3 | Enterprise intelligence (segments, competitive, QBR coverage, churn split) | 4 | $500M: 76 → 84 |
| 4 | Forecast & integration (NRR scenarios, CRM reconciliation) | 3 | $500M: 84 → 86 |

**Total: 17 files across 4 sprints (9 modified, 8 new)**
