# Competitive Gap Roadmap: Kanban Persistence + Renewal Forecast

## Executive Summary

Two gaps identified in the competitive matrix against Gainsight and Planhat. Both are **smaller than they appear** — CS Pulse has 70-80% of the infrastructure built; the gap is in the last-mile persistence and modeling layers.

| Gap | Current Grade | Target Grade | Effort | Sprint |
|-----|--------------|-------------|--------|--------|
| Kanban backend persistence | B- | A- | **S (2-3 days)** | Sprint 1 |
| Renewal probabilistic forecast | B+ | A | **M (4-5 days)** | Sprint 2 |

---

## Gap 1: Kanban Backend Persistence

### Statement Under Evaluation
> "Planhat leads on visual kanban workflows — CS Pulse Cockpit exists but uses mock data (needs backend persistence)"

### Verdict: **PARTIALLY TRUE — less bad than it sounds**

**What actually exists:**
- CSMCockpit.tsx calls **real APIs** (`/api/v1/accounts`, `/api/v1/daily-actions`) with mock fallbacks
- Urgency-to-column mapping **already works** (critical→Fire, high→This Week, opportunity→Growth)
- Contextual drawer with 6 tabs fetches **real data** (alerts, recommendations, stakeholder map, health history)
- Approval flow calls **real endpoints** (`/api/approvals/{id}/approve|reject`)

**What's actually missing (3 things):**
1. **No drag-and-drop** — cards are static in their computed columns
2. **No column override persistence** — a CSM can't move a card and have it stay
3. **No decision audit trail** — kanban moves aren't logged for analytics

**Why it's smaller than it sounds:** The data is real. The gap is UX interactivity + one PATCH endpoint + one DB field. Not a data architecture problem.

### Fix Roadmap (Sprint 1 — 2-3 days)

#### Step 1: Backend — Column Override (0.5 day)
**File:** `backend/verticals/dc2_s/api_routes.py`

```
PATCH /api/v1/accounts/{account_id}/kanban-position
  body: { column: 'fire' | 'week' | 'opportunity', notes?: string }
  → Stores in Account.profile_metadata['kanban_override'] = { column, moved_by, moved_at }
  → No DB migration needed — profile_metadata is JSON
```

**File:** `backend/mcp_server/cs_pulse_admin.py`
- Update `get_csm_daily_actions` to include `kanban_override` if present

#### Step 2: Frontend — Drag-and-Drop (1 day)
**File:** `kpi-dashboard/package.json` — add `@dnd-kit/core` + `@dnd-kit/sortable`
**File:** `src/components/csm/CSMCockpit.tsx`

- Wrap each column in `<SortableContext>` / `<DroppableContainer>`
- Wrap `KanbanCard` in `<Draggable>`
- Add `onDragEnd` handler:
  ```
  onDragEnd → PATCH /api/v1/accounts/{id}/kanban-position
            → update local state optimistically
  ```
- Column bucketing: check `kanban_override.column` first, fall back to computed urgency

#### Step 3: Decision Audit Trail (0.5 day)
**File:** `backend/verticals/dc2_s/api_routes.py`

- Log every kanban move as a ContextNode (type=DECISION, subtype=kanban_move)
- Fields: from_column, to_column, moved_by, rationale (optional)
- This feeds the context graph — moves become evidence for future analysis

#### Step 4: MCP Tool (0.5 day)
**File:** `backend/mcp_server/cs_pulse_admin.py`

```python
@mcp.tool()
def update_kanban_position(customer_id, account_id, column, notes=None):
    """Move account to a different kanban column (fire/week/opportunity)."""
```

#### Result
- **Grade moves:** B- → A-
- **Planhat comparison:** Planhat still has calendar view + customer portal (A-), but CS Pulse matches on kanban + adds MCP queryability + context graph audit trail
- **Unique advantage retained:** Every kanban move becomes a ContextNode decision, building causal intelligence

---

## Gap 2: Renewal Probabilistic Forecast

### Statement Under Evaluation
> "Gainsight Renewal Center is the most mature renewal forecast engine — CS Pulse has pipeline view but no probabilistic forecast"

### Verdict: **TRUE — but CS Pulse has stronger building blocks**

**What actually exists:**
- `renewal_date` stored in `Account.profile_metadata` — load driver generates it
- VPCSDashboard.tsx shows 90-day renewal pipeline with health, ARR, days left
- `_compute_renewal_stage()` in cs_pulse_admin.py calculates 3-bucket probability (90%/65%/35%)
- NRR forecast engine (Wizard B) does renewal risk overlay with T+30/60/90 trajectory
- Story arcs flag renewal-relevant patterns (Silent Churn, Exec Sponsor Loss)
- `churn_prob` field exists in signal analysis output

**What's actually missing (4 things):**
1. **No multi-factor renewal probability model** — current is 3-bucket (health only), not a regression
2. **No renewal risk score** exposed in UI — `(1 - prob) × ARR × trend_weight`
3. **No renewal outcome tracking** — no win/loss/downsell capture post-renewal
4. **No renewal-specific playbooks** — generic health playbooks, not renewal motions

**Why CS Pulse has an advantage Gainsight doesn't:**
- Context Graph provides **causal evidence** for why a renewal is at risk (signal chains, not just a score)
- Power-of-1 quantifies **what improving 1% of a metric does to NRR** — Gainsight can't do this
- Playbook ROI engine can prove **what the intervention cost and returned** — Gainsight reports CTA completion, not revenue attribution

### Fix Roadmap (Sprint 2 — 4-5 days)

#### Step 1: Multi-Factor Renewal Probability (1.5 days)
**File:** `backend/wizards/wizard_b_pattern_analyzer.py`

Add `compute_renewal_probability(account)` function:

**Input features:**
- `health_score` (current, 0-100)
- `health_trend` (6-month slope: improving/declining/stable)
- `days_until_renewal` (urgency factor)
- `engagement_recency` (days since last exec contact)
- `open_tickets_p1` (support quality signal)
- `champion_status` (active/departed/unknown)
- `story_arc_type` (silent_churn = high risk, expansion_champion = low risk)
- `nps_score` (if available)

**Model:** Logistic regression with interpretable coefficients:
```
logit(P_renew) = β0 + β1·health + β2·trend + β3·days + β4·engagement + β5·tickets + β6·champion + β7·arc
```

Coefficients bootstrap from historical data (Wizard C correlation analysis) or use platform defaults:
```python
DEFAULT_COEFFICIENTS = {
    'health': 0.04,           # each health point adds 4% log-odds
    'trend_declining': -0.8,  # declining trend penalty
    'champion_departed': -1.2, # champion loss is severe
    'silent_churn_arc': -1.5,  # story arc penalty
    'days_under_30': -0.5,    # urgency pressure
    'p1_tickets_gt_3': -0.6,  # support quality
}
```

**Output:** `renewal_probability: 0.0-1.0` with `confidence_interval` and `top_risk_factors[]`

#### Step 2: Renewal Risk Score + MCP Tool (1 day)
**File:** `backend/mcp_server/cs_pulse_intelligence.py`

```python
@mcp.tool()
def get_renewal_forecast(customer_id, horizon_days=90):
    """Get probabilistic renewal forecast for accounts renewing within horizon.
    Returns per-account: renewal_probability, risk_score, ARR_at_risk, 
    top_risk_factors, recommended_playbook, confidence_interval.
    Portfolio summary: expected_retention_rate, total_ARR_at_risk, 
    weighted_avg_probability.
    """
```

**Risk score formula:**
```
risk_score = (1 - renewal_probability) × ARR × trend_weight
where trend_weight = 1.3 if declining, 1.0 if stable, 0.7 if improving
```

**Sort renewals by risk_score descending** — highest dollar-risk first.

#### Step 3: Renewal Outcome Tracking (1 day)
**File:** `backend/models.py`

Add to existing ContextNode types:
```python
# New node subtypes for renewal tracking
RENEWAL_SUBTYPES = [
    'renewal_approaching',  # auto-created at 90/60/30 days
    'renewal_won',          # account renewed
    'renewal_lost',         # account churned
    'renewal_downsell',     # renewed at lower ARR
    'renewal_expansion',    # renewed at higher ARR
]
```

**File:** `backend/mcp_server/cs_pulse_intelligence.py`

```python
@mcp.tool()
def log_renewal_outcome(customer_id, account_id, outcome, new_arr=None, notes=None):
    """Record renewal outcome (won/lost/downsell/expansion).
    Creates ContextNode with revenue_impact for ROI attribution.
    """
```

This feeds the context graph — renewal outcomes become Outcome nodes with causal chains (Signal → Decision → Renewal Outcome).

#### Step 4: Dashboard Enhancement (1 day)
**File:** `src/components/dashboard/VPCSDashboard.tsx`

Enhance Renewals tab:
- Add **probability column** with color gradient (red < 50%, amber 50-80%, green > 80%)
- Add **risk score column** (ARR × probability × trend)
- Add **top risk factor** badge (champion_loss, silent_churn, etc.)
- Add **portfolio renewal forecast card**: "Expected retention: 87% | ARR at risk: $5.2M | Weighted probability: 72%"
- Sort by risk_score descending (highest dollar-risk first)

#### Step 5: Renewal-Specific Playbook Seeds (0.5 day)
**File:** `backend/config/playbook_config.py` or playbook template seeder

Add 2 renewal-specific playbooks:
```
PB-RENEW-01: Pre-Renewal Health Review (triggered at 90 days)
  Steps: Stakeholder mapping → QBR prep → Executive alignment → Proposal review
  
PB-RENEW-02: At-Risk Renewal Recovery (triggered when renewal_probability < 0.5)
  Steps: Root cause analysis → Emergency exec meeting → Value narrative → Contract negotiation
```

#### Result
- **Grade moves:** B+ → A
- **Gainsight comparison:** Gainsight still has pipeline stage management and multi-year forecasting (A), but CS Pulse matches on probability + adds causal evidence chains + Power-of-1 integration
- **Unique advantage:** Every renewal probability traces to context graph evidence — "72% renewal risk BECAUSE champion departed AND adoption dropped AND 3 P1 tickets"

---

## Sprint Plan

| Sprint | Gap | Days | Key Deliverable | Grade Impact |
|--------|-----|------|-----------------|-------------|
| **Sprint 1** | Kanban persistence | 2-3d | Drag-and-drop + PATCH endpoint + ContextNode audit | B- → A- |
| **Sprint 2** | Renewal forecast | 4-5d | Multi-factor probability + risk score + outcome tracking | B+ → A |
| **Total** | Both gaps | **6-8d** | Two competitive gaps closed | |

## Post-Fix Competitive Position

| Feature | CS Pulse | Gainsight | Planhat |
|---------|----------|-----------|---------|
| Kanban workflows | **A-** (drag + MCP + CG audit) | D (no kanban) | A- (native kanban + calendar) |
| Renewal forecast | **A** (probabilistic + causal evidence) | A (Renewal Center, most mature) | B+ (NRR trends) |
| MCP integration | **A+** (47 tools after additions) | B- (connector only) | D |

**Net effect:** CS Pulse eliminates two "competitor leads" callouts from the competitive matrix while retaining unique advantages (context graph, MCP, Power-of-1) that no competitor can match.
