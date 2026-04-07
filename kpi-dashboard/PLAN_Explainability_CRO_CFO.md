# Explainability for CRO & CFO Dashboards

## Problem

CRO and CFO dashboards show numbers but don't explain WHY. When a CRO sees "Revenue at Risk: $2.5M" they immediately ask "which accounts? what caused it?" When a CFO sees "Playbook ROI: 340%" they ask "is that real or estimated? show me the math."

The backend already returns the evidence — pillar breakdowns, per-account NRR attribution, causal chains, churn probability models. **The frontend doesn't render it.**

## Key Finding

4 out of 5 gaps are **frontend-only fixes** — the backend data is already there, just not displayed:

| Gap | Backend Has Data? | Frontend Renders? | Fix Type |
|-----|-------------------|-------------------|----------|
| Health score pillar decomposition | Yes (`pillar_scores`) | No | Frontend only |
| Revenue at Risk drill-down | Yes (`highest_risk_accounts`) | Static card, no click | Frontend only |
| NRR per-account attribution | Yes (`nrr_waterfall.accounts[]`) | Aggregate only | Frontend only |
| Playbook ROI proof chain | Yes (estimated vs tracked labels) | Partial | Frontend + backend |
| Cost of Inaction formula | Yes (numbers) | Numbers only, no formula | Frontend only |

---

## Sprint 1: HIGH Priority — Render Existing Data (Frontend Only)

### 1.1 Health Score Pillar Decomposition

**CRO Dashboard — Risk Account Cards**

Currently: Card shows health score as single number + bar.
After: Expandable pillar breakdown on click.

```
┌─────────────────────────────────────┐
│ Acme Corp            Health: 42     │
│ ████████░░░░░░░░░░░░ (Critical)    │
│                                     │
│ ▼ Pillar Breakdown                  │
│   P1 Deployment:  35 ████░░░░░░    │
│   P2 Operations:  58 ██████░░░░    │
│   P3 AI Perf:     28 ███░░░░░░░    │ ← Worst pillar highlighted
│   P4 Channel:     62 ██████░░░░    │
│   P5 Expansion:   41 ████░░░░░░    │
└─────────────────────────────────────┘
```

**CFO Dashboard — Account Investment Table**

Currently: Table shows health score as number.
After: Hover tooltip shows pillar scores.

| File | Change |
|------|--------|
| `CRODashboard.tsx` | RiskAccountCard: add expandable section below health bar. Toggle `showPillars` state on click. Map `account.pillar_scores` to horizontal bars (green/amber/red per threshold). Highlight worst pillar with ← arrow. |
| `CFODashboard.tsx` | Account table health column: add tooltip on hover showing pillar breakdown from account data. |

---

### 1.2 Revenue at Risk Drill-Down

**CRO Dashboard — Revenue at Risk Card → Click → Account List with Causal Chain**

Currently: Static card showing "$2.5M at risk, 3 accounts." Subtitle says "Causal evidence chains active" but click does nothing.
After: Click opens expandable panel showing per-account causal evidence.

```
┌─────────────────────────────────────┐
│ Revenue at Risk         $2.5M       │
│ 3 accounts · Causal evidence active │
│                                     │
│ ▼ Account Details                   │
│                                     │
│ ┌─ Acme Corp ($800K ARR) ────────┐  │
│ │ Health: 42 (Critical)          │  │
│ │ Causal chain:                  │  │
│ │  Mar 15: Champion departed     │  │
│ │  Mar 22: GPU utilization ↓47%  │  │
│ │  Apr 01: Competitor RFP issued │  │
│ │ Intervention window: 7 days    │  │
│ └────────────────────────────────┘  │
│                                     │
│ ┌─ Beta Inc ($1.2M ARR) ────────┐  │
│ │ Health: 38 (Critical)          │  │
│ │ Causal chain:                  │  │
│ │  Feb 10: Silent usage decline  │  │
│ │  Mar 01: NPS dropped to 15    │  │
│ └────────────────────────────────┘  │
└─────────────────────────────────────┘
```

| File | Change |
|------|--------|
| `CRODashboard.tsx` | Revenue at Risk card: add onClick toggle for `showRiskDetails`. Render `data.risk_accounts` as expandable account cards. Each card shows: name, ARR, health, classification, signal_count. For causal chain: use `arc_type` + latest signals (already in risk_accounts array from API). |

---

### 1.3 NRR Per-Account Attribution

**CRO Dashboard — NRR Waterfall → Expandable Account Breakdown**

Currently: NRR sidebar shows aggregate bars (expected loss, attributed save, intervention cost, ROI).
After: Expand to show per-account NRR impact.

```
┌─────────────────────────────────────┐
│ NRR Waterfall                       │
│                                     │
│ Expected Loss    ████████  -$450K   │
│ Revenue Saved    ██████    +$320K   │
│ Intervention     ██        -$45K    │
│ Net ROI                    7.1x     │
│                                     │
│ ▼ Per-Account Breakdown             │
│                                     │
│ Acme Corp    $800K  churn 35%  -$280K│ ← Red (dragging NRR)
│ Beta Inc     $1.2M  churn 20%  -$240K│
│ Gamma Ltd    $500K  saved      +$180K│ ← Green (NRR contributor)
│ Delta Star   $3.8M  expand     +$140K│
└─────────────────────────────────────┘
```

| File | Change |
|------|--------|
| `CRODashboard.tsx` | NRR Waterfall sidebar panel: add expandable account list from `data.nrr_waterfall.accounts[]`. Each row: account_name, ARR, churn_prob_pct, expected_loss (red) or attributed_save (green). Sort by impact (largest negative first). |
| `CFODashboard.tsx` | Same treatment for CFO Revenue Waterfall sidebar widget. |

---

### 1.4 Cost of Inaction — Show the Formula

**CFO Dashboard — Cost of Inaction Panel → Add Methodology Tooltip**

Currently: Shows ARR at risk, annual churn exposure, account count + top 3 accounts. Footer: "Projected annual revenue loss if no intervention."
After: Methodology tooltip explaining the formula.

```
┌─────────────────────────────────────┐
│ Cost of Inaction              ℹ️    │ ← info icon → tooltip
│                                     │
│ ARR at Risk        $2.5M            │
│ Annual Exposure    $450K            │
│ Accounts           3                │
│                                     │
│ ┌─ Acme Corp ───────────────────┐  │
│ │ ARR: $800K  Health: 42        │  │
│ │ Churn prob: 35%               │  │
│ │ Annual loss: $280K            │  │
│ │ Formula: $800K × 35% = $280K  │  │ ← NEW: show math
│ └───────────────────────────────┘  │
│                                     │
│ Methodology: Churn probability      │
│ derived from health score:          │
│ churn% = max(5, 50 - health × 0.5) │ ← NEW: show formula
│ Health 42 → churn% = 29%           │
│ Accounts with health < 70 included  │
└─────────────────────────────────────┘
```

| File | Change |
|------|--------|
| `CFODashboard.tsx` | Cost of Inaction panel: (1) Add ℹ️ icon with tooltip showing churn probability formula. (2) Per-account rows: show `churn_pct%` and formula `ARR × churn% = annual_loss`. (3) Add methodology footer explaining the health → churn mapping. |

---

### 1.5 Playbook ROI Proof Chain (Backend + Frontend)

**CFO Dashboard — ROI Card → Click → Show Investment → Outcome Chain**

Currently: Shows ROI percentage with "Estimated (Power-of-1)" or tracked label. Account table shows source column.
After: Click ROI card → detailed proof chain.

```
┌─────────────────────────────────────┐
│ Portfolio ROI          340%         │
│ Source: Tracked (12 playbook runs)  │
│                                     │
│ ▼ ROI Proof Chain                   │
│                                     │
│ Investment:                         │
│   12 playbook runs × $3,750 avg    │
│   = $45,000 total CS investment    │
│                                     │
│ Returns:                            │
│   3 accounts saved from churn      │
│   Revenue protected: $153,000      │
│                                     │
│ Calculation:                        │
│   ROI = $153K / $45K = 340%        │
│                                     │
│ ┌─ Playbook Runs ───────────────┐  │
│ │ PB-02 on Acme    12hrs  $1,020│  │
│ │ PB-04 on Beta    8hrs   $680  │  │
│ │ PB-01 on Gamma   15hrs  $1,275│  │
│ └───────────────────────────────┘  │
│                                     │
│ When estimated: "Based on Power-of-1│
│ industry benchmarks (TSIA, Gainsight│
│ Pulse, KeyBanc). Shows projected ROI│
│ at your ARR scale, not tracked."    │
└─────────────────────────────────────┘
```

| File | Change |
|------|--------|
| `executive_dashboard_api.py` | Add `roi_proof_chain` to CFO response: query PlaybookExecutionV2 for actual runs (playbook_id, account_name, csm_hours, cost, health_at_trigger, health_at_close, revenue_protected). If no executions, return Power-of-1 methodology explanation. |
| `CFODashboard.tsx` | ROI card: add onClick toggle for proof chain panel. If tracked: show investment breakdown, individual playbook runs, calculation formula. If estimated: show Power-of-1 methodology with benchmark sources. |

---

## Verification Plan

| Fix | How to Test | Pass Criteria |
|-----|------------|---------------|
| 1.1 Pillar decomposition | Login as CRO → Risk Accounts grid → click account card | Pillar bars render with P1-P5 scores, worst pillar highlighted |
| 1.2 Revenue at Risk drill-down | CRO → click Revenue at Risk card | Account list expands with ARR, health, causal chain signals |
| 1.3 NRR attribution | CRO → NRR Waterfall sidebar → expand | Per-account rows with churn%, expected_loss, color-coded |
| 1.4 Cost of Inaction formula | CFO → Cost of Inaction → hover ℹ️ | Tooltip shows churn formula, per-account math visible |
| 1.5 ROI proof chain | CFO → ROI card → expand | Investment breakdown, playbook runs list, calculation shown |

---

## Files Modified

| File | Fixes |
|------|-------|
| `CRODashboard.tsx` | 1.1, 1.2, 1.3 |
| `CFODashboard.tsx` | 1.1, 1.3, 1.4, 1.5 |
| `executive_dashboard_api.py` | 1.5 (roi_proof_chain) |

**Total: 3 files, ~300 lines of frontend changes + ~50 lines backend**
