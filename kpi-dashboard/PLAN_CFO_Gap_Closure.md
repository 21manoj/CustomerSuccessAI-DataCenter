# CFO Dashboard — Gap Closure Plan

## Context
Evaluated from two CFO perspectives: $500M (B+, 75/100) and $100M (A-, 82/100).
Mid-market ($100M) is ready-now with minor polish. Enterprise ($500M) needs cohort analysis, budget modeling, and TTM trends.
Goal: Mid-market → 88/100, Enterprise → 85/100.

## Current State
- 7 sections: Financial Summary Cards, Power-of-1 Table, Pillar Investment Bars, Investment Timeline, Non-Linear ROI Scaling, Account Investment Table, Right Sidebar (efficiency gauge, waterfall, financial ratios)
- API: `GET /api/executive/cfo-dashboard` returns ~30 fields including power_of_1_metrics, cost_of_inaction, nrr_waterfall, per-account ROI
- Backend: `executive_dashboard_api.py` lines 879-1202 (`cfo_dashboard()`)
- Existing infra: Power-of-1 economics JSON, sample_industry_benchmarks.csv, ROISnapshot model, PlaybookExecutionV2 costs

---

## Sprint 1: Mid-Market Polish (3 days)

### 1.1 Traffic Light Summary View
**Problem:** $100M CFO wants a one-page "are we OK?" view — current dashboard is data-rich but scan-unfriendly.

| File | Change |
|------|--------|
| `src/components/dashboard/CFODashboard.tsx` | Add collapsible "Portfolio Pulse" hero section at top: 3 large circles (green/amber/red) with account counts + ARR per bucket. Single sentence: "5 accounts healthy ($62M), 3 at risk ($28M), 2 critical ($10M)." Clickable to filter account table below. |

### 1.2 Email/Push Alerts for Threshold Crossings
**Problem:** CFO wants "email me when any account drops below 50 health" — notifications exist for CSM but not CFO persona.

| File | Change |
|------|--------|
| `backend/models.py` | Add `AlertSubscription` model: customer_id, user_id, persona (cfo/cro/vpcs), metric (health_score/nrr/arr), threshold, direction (below/above), channel (email/in_app), enabled |
| `backend/alert_subscription_api.py` | **NEW** — CRUD endpoints: `GET/POST/PUT/DELETE /api/alerts/subscriptions`. Evaluation hook called from `push_intelligence_subscriber.py` after health score writes. |
| `src/components/dashboard/CFODashboard.tsx` | Add "Alert Settings" gear icon in header → modal with threshold config (metric dropdown, threshold slider, email toggle) |

### 1.3 Board-Ready Export (PDF + CSV)
**Problem:** CFO needs one-click board package. No export exists today.

| File | Change |
|------|--------|
| `package.json` | Add `jspdf` + `jspdf-autotable` |
| `src/utils/dashboardExport.ts` | **NEW** — `exportCFOPdf(data)`: header (logo, date, period), portfolio summary table, Power-of-1 table, account investment table, NRR/GRR metrics. `exportCFOCsv(data)`: flat account-level CSV. |
| `src/components/dashboard/CFODashboard.tsx` | Export button (Download icon) in header → dropdown: "Export PDF" / "Export CSV" |

### 1.4 Render Existing Unused Data
**Problem:** Backend returns `nrr_waterfall.accounts[]` and `renewals_at_risk` but UI doesn't render them.

| File | Change |
|------|--------|
| `src/components/dashboard/CFODashboard.tsx` | Revenue Waterfall sidebar widget: add expandable account list under the waterfall bars (account name, $ lost/saved, health). Show "Renewals at Risk" count badge on Financial Summary cards. |

**Sprint 1 files: 5 (3 modified, 2 new)**

---

## Sprint 2: Financial Depth (4 days)

### 2.1 TTM Trend Charts (NRR, GRR, Churn Rate)
**Problem:** Board slides need trailing 12-month trends, not point-in-time snapshots.

| File | Change |
|------|--------|
| `backend/executive_dashboard_api.py` | In `cfo_dashboard()`, add `ttm_trends` field: query HealthScore + ROISnapshot by month for last 12 months. Compute monthly NRR (from health-to-NRR formula), GRR, logo churn count, revenue churn $. Return as time series. |
| `src/components/dashboard/CFODashboard.tsx` | Replace static NRR/GRR dual card with interactive 12-month line chart (NRR + GRR on same axes). Hover shows monthly values. Toggle: "TTM" / "QoQ" / "Current". |

### 2.2 CS-to-CAC Payback View
**Problem:** CFO wants "we spend $X on CS per account → payback in Z months."

| File | Change |
|------|--------|
| `backend/executive_dashboard_api.py` | Add `payback_analysis` to CFO response: per account, compute cs_cost (from PlaybookExecutionV2 or Power-of-1 estimate) and revenue_protected. Payback months = cs_cost / (revenue_protected / 12). Portfolio average payback. |
| `src/components/dashboard/CFODashboard.tsx` | New "CS Payback" card in Financial Summary row: "Avg Payback: 2.3 months" with mini bar chart showing per-account payback distribution. |

### 2.3 Variance Analysis (NRR Decomposition)
**Problem:** "Why did NRR drop 2pp?" — no automated root cause attribution.

| File | Change |
|------|--------|
| `backend/executive_dashboard_api.py` | Add `nrr_variance` to CFO response: decompose NRR change into components: churn_impact (lost accounts), contraction_impact (downsells), expansion_impact (upsells), new_logo_impact. Each with $ amount and account list. |
| `src/components/dashboard/CFODashboard.tsx` | New "NRR Variance" expandable panel below NRR card: waterfall chart showing +expansion, -contraction, -churn = net NRR change. Each bar clickable to show account list. |

### 2.4 Industry Benchmark Comparison
**Problem:** "How does our NRR compare to SaaS median?"
**Infrastructure:** `sample_industry_benchmarks.csv` exists with percentile data.

| File | Change |
|------|--------|
| `backend/executive_dashboard_api.py` | Load benchmarks CSV, match customer's vertical + size. Add `benchmarks` field to CFO response: for each metric (NRR, GRR, churn, health), return customer_value + p25/p50/p75/p90. |
| `src/components/dashboard/CFODashboard.tsx` | Financial Ratios sidebar widget: add benchmark bars (gray p25-p75 range, green dot = customer position). Tooltip: "Your NRR (103%) is at the 72nd percentile for mid-market SaaS." |

**Sprint 2 files: 2 (both modified — executive_dashboard_api.py + CFODashboard.tsx)**

---

## Sprint 3: Enterprise Scale (4 days)

### 3.1 Cohort-Based Retention Analysis
**Problem:** $500M CFO needs NRR by cohort year, by segment, by ACV tier.

| File | Change |
|------|--------|
| `backend/utils/cohort_analyzer.py` | **NEW** — `analyze_cohorts(customer_id, dimension)`: groups accounts by contract_start year (cohort), industry (segment), or ARR tier (small <$500K, mid $500K-$2M, large >$2M). For each cohort: account count, total ARR, avg health, NRR, GRR, churn count. Returns time series per cohort. |
| `backend/executive_dashboard_api.py` | Add `GET /api/executive/cfo-cohorts?dimension=year|segment|tier` endpoint. |
| `src/components/dashboard/CFODashboard.tsx` | New "Cohort Analysis" view (add to sidebar or as expandable section). Dimension toggle (Year / Segment / Tier). Heatmap table: rows = cohorts, columns = months, cells = NRR color-coded. Summary row: best/worst cohort callout. |

### 3.2 Budget Planning / Headcount Model
**Problem:** "If I hire 2 more CSMs, what's the projected NRR improvement?"

| File | Change |
|------|--------|
| `backend/utils/headcount_simulator.py` | **NEW** — `simulate_headcount(customer_id, delta_csms)`: current accounts_per_csm → new ratio → projected health improvement (from capacity utilization curve) → NRR delta → $ impact. Uses team-capacity data + Power-of-1 correlation. |
| `backend/executive_dashboard_api.py` | Add `GET /api/executive/cfo-headcount-sim?delta=2` endpoint. |
| `src/components/dashboard/CFODashboard.tsx` | New "What-If Simulator" card: slider for +/- CSMs (range: -2 to +5). Shows: new accounts/CSM ratio, projected health change, projected NRR change, $ impact, annual CS cost delta. Real-time recalculation on slider move. |

### 3.3 Contract Value Tracking (TCV/ACV/Billing)
**Problem:** CFO cares about TCV, ACV, billing terms — not just ARR.

| File | Change |
|------|--------|
| `backend/models.py` | Add optional fields to Account: `contract_value` (TCV), `contract_term_months`, `billing_frequency` (monthly/annual/multi-year). Nullable — only populated when data available. |
| `backend/executive_dashboard_api.py` | Include contract fields in CFO account details when present. Add `contract_summary` to CFO response: total TCV, avg contract length, billing mix. |
| `src/components/dashboard/CFODashboard.tsx` | Account Investment Table: add TCV and Term columns (hidden when null). Contract Summary card in sidebar when data available. |

**Sprint 3 files: 5 (2 modified, 3 new)**

---

## Summary

| Sprint | Focus | Days | Grade Impact |
|--------|-------|------|-------------|
| 1 | Mid-market polish (traffic light, alerts, export) | 3 | $100M: 82 → 88 |
| 2 | Financial depth (TTM, payback, variance, benchmarks) | 4 | Both: +5 points |
| 3 | Enterprise scale (cohorts, headcount sim, contract tracking) | 4 | $500M: 75 → 85 |

**Total: 12 files across 3 sprints (7 modified, 5 new)**
