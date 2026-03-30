# Backlog: 4 Simulation MCP Tools for Ask AI "What If" Queries

**Date:** March 30, 2026
**Status:** Backlog — not started
**Depends on:** Ask AI v2 endpoint (`/api/executive/ask-v2`)
**Reference:** `ASK_AI_WHAT_IF_QUESTIONS.md` — 7 of 40 persona questions fail without these tools

---

## Problem

Ask AI can answer "what is" questions (current health, current revenue at risk) but cannot answer "what if" questions (what happens if GPU drops 10%, what if we lose 3 accounts). 7 of 40 validated persona questions fail because no simulation/projection tools exist.

---

## 4 Proposed Tools

### 1. `simulate_kpi_change`

**Purpose:** Project health score change if a KPI value changes.

**Signature:**
```
simulate_kpi_change(customer_id, account_id, kpi_code, new_value)
→ { current_health, projected_health, delta, current_pillars, projected_pillars, threshold_crossing }
```

**Implementation:** Load account's current KPI values from DB, override the specified KPI, run `calculate_kpi_health()` in-memory (no DB write), return before/after comparison.

**Unlocks questions:**
- CSM-9: "If GPU utilization drops another 10% at K2, what happens to their health score?"
- Any "what if KPI X changes to Y" question

**Effort:** 3-4 hours (backend function + MCP tool + REST endpoint)

---

### 2. `simulate_portfolio_loss`

**Purpose:** Project NRR/GRR impact if specific accounts are lost.

**Signature:**
```
simulate_portfolio_loss(customer_id, account_ids)
→ { current_nrr, projected_nrr, nrr_delta, current_grr, projected_grr, arr_lost, remaining_arr, accounts_removed }
```

**Implementation:** Load all accounts with ARR, remove specified account_ids, recalculate NRR/GRR ratios. Pure math, no DB write.

**Unlocks questions:**
- CRO-2: "What would happen to our NRR if we lose the 3 most at-risk accounts?"
- Any "what if we lose account X" question

**Effort:** 2-3 hours

---

### 3. `get_csm_workload`

**Purpose:** Show per-CSM account distribution, risk load, and capacity.

**Signature:**
```
get_csm_workload(customer_id)
→ { csms: [{ user_id, name, account_count, at_risk_count, critical_count, total_arr, avg_health }] }
```

**Implementation:** Join User (role=csm) → Account (via allowed_account_ids or assignment) → HealthScore. Aggregate per CSM.

**Unlocks questions:**
- CRO-9: "If we had 2 more CSMs, which accounts would benefit most?"
- VPCS-2: "Which CSM has the most at-risk accounts and are they overloaded?"
- VPCS-7: "If I hire 1 more CSM, which accounts should they own?"

**Effort:** 3-4 hours

---

### 4. `get_signal_to_health_lag`

**Purpose:** Measure how far in advance signals predict health score declines.

**Signature:**
```
get_signal_to_health_lag(customer_id)
→ { avg_lag_days, median_lag_days, samples: [{ account_id, signal_date, signal_type, health_crossing_date, lag_days }] }
```

**Implementation:** For each account that crossed healthy→at_risk, find the earliest negative signal before the crossing date. Compute lag = crossing_date - signal_date. Aggregate across accounts.

**Unlocks questions:**
- VPCS-9: "What's the average time from first negative signal to health score drop?"
- Validates the "3-6 months early detection" claim with real data

**Effort:** 3-4 hours

---

## Summary

| Tool | Effort | Personas Served | Questions Unlocked |
|------|--------|----------------|-------------------|
| simulate_kpi_change | 3-4h | CSM, CRO | 2 |
| simulate_portfolio_loss | 2-3h | CRO, CFO | 1 |
| get_csm_workload | 3-4h | CRO, VP CS | 3 |
| get_signal_to_health_lag | 3-4h | VP CS | 1 |
| **Total** | **11-15h** | **All 4** | **7 questions** |

## Implementation Notes

- All 4 tools are **read-only** — no DB writes, no side effects
- Each needs: backend function, MCP tool wrapper (in `cs_pulse_intelligence.py`), REST endpoint
- `simulate_kpi_change` reuses existing `calculate_kpi_health()` — lowest risk
- `get_csm_workload` depends on CSM-to-account assignment model (currently `allowed_account_ids` on User model)
- `get_signal_to_health_lag` depends on ContextNode signal dates + HealthScore crossing dates — both exist in DB
