# Wizard A & Wizard B — Technical Overview

*Last updated: May 6 2026*

CS Pulse runs three deterministic "wizards" inside `process_data`. Wizard A
classifies each account's behavior into a known arc; Wizard B uses that
classification plus revenue outcomes to produce a portfolio NRR forecast.
Wizard C calibrates per-customer KPI weights and is out of scope here.

---

## 1. Overview, Purpose, Workflow

### Wizard A — Arc Intelligence Engine

**Purpose.** Convert each account's 12-month KPI/health/signal trajectory
into a labeled "arc" + phase, so downstream consumers (Wizard B, CSM
dashboard, Ask AI) can reason about the *story* the data tells, not just
the raw numbers.

**Source:** `backend/wizards/wizard_a_journey_db.py` and
`backend/verticals/_template/journey/wizard_a/`. DB-native — no filesystem.

**Workflow per account:**
1. Build a journey object: starting_health, ending_health, lowest_health,
   12-month trajectory, signals, outcomes — all from PostgreSQL.
2. **Phase detection** — labels `baseline`, `deterioration`, `intervention`,
   `resolution` based on health-trajectory inflections.
3. **Arc classification** — pattern-matches the journey shape against 8
   templates in `backend/config/story_arcs/*.json` (silent_churn,
   crisis_recovery, expansion_champion, land_and_expand,
   exec_sponsor_change, competitive_displacement, stalled_deployment,
   seasonal_surge). Returns `arc_type` + `arc_confidence` ∈ [0, 1].
4. **DECISION + edge synthesis** — for the matched arc, generates
   ContextNode rows of type DECISION and ContextEdge causal links via
   `arc_decision_generator.py` and `arc_edge_generator.py`.

### Wizard B — Pattern Analysis & NRR Forecast

**Purpose.** Three outputs: (a) per-arc NRR correlation across the
portfolio, (b) per-account NRR forecast + 90-day health trajectory, (c)
revenue-weighted portfolio NRR forecast with both *without-CS-Pulse* and
*with-further-interventions* counterfactuals.

**Source:** `backend/wizards/wizard_b_pattern_db.py` (DB wrapper) calling
`backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py`
(core analyzer, ~1500 lines).

**Workflow (numbered in Wizard B's own stdout):**
1. Profile patterns — group accounts by `arc_type` from Wizard A.
2. Phase-transition matrix.
3. Early-warning rule extraction.
4. Success-factor analysis — what differentiated recovered accounts.
5. **NRR correlation** — bucket accounts by arc, compute avg NRR per arc using definitive lifecycle outcomes only.
6. **Portfolio NRR forecast** — per-account current NRR, T+30/60/90 trajectory, with/without CS Pulse counterfactuals, revenue waterfall, renewal risk overlay, top-10 intervention ranking, then aggregated portfolio metrics.

§1b below walks through Step 5 + Step 6 in detail with formulas and line refs.

---

## 1b. Wizard B NRR Pipeline (detailed)

The full forecast is built in one orchestrated pass through `forecast_portfolio_nrr()` ([line 695](../../backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py)). 11 conceptual steps:

### Step 0 — Wizard A pre-condition
Every account already has an `arc_type` (steady_growth, crisis_recovery, slow_decline, expansion_heavy, …) from Wizard A. Wizard B reads this from `accounts.arc_type`.

### Step 1 — Per-arc NRR correlation ([line 489](../../backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py))

**Inputs:**
- `arr_map` — `Account.revenue` per account (current contract ARR)
- `OUTCOME` ContextNode rows where `revenue_impact_type` is in the *definitive* lifecycle set: `{churn_lost, contraction, expansion_closed, new_logo}`. Narrative outcomes (`revenue_protected`, `churn_averted`) are **excluded** — they're stories, not actual ARR movements.
- Taxonomy from `config/taxonomy_base.json` — single source of truth so Wizard B can't drift from production bucket-mapping.

**Per arc pattern:**
```
NRR_arc                  = (Σ ARR − Σ lost + Σ expansion) / Σ ARR
intervention_success_rate = % of accounts where ending_health > lowest_health + 5
```

`new_logo` contributes to expansion **and** is excluded from the denominator (new ARR, not retained).

### Step 2 — Gather per-account inputs ([line 716–757](../../backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py))
- `arr_map`, `arc_map`, `renewal_map` (from `Account.profile_metadata.renewal_date`)
- `slope_map` — health momentum from last 2 `HealthScore` rows: `(latest − prev) / Δdays × 30`
- `arc_playbook_map` — JSON config mapping each arc to prescribed playbooks

### Step 3 — Build per-account forecast record ([line 845](../../backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py))
For every account:
```
{ account_id, arr,
  current_nrr,                    ← from Step 5 (lifecycle outcomes)
  health_start, health_end, health_lowest, health_slope_30d,
  intervention_success_rate,      ← from Step 1
  renewal_date, days_to_renewal, renewal_urgency,
  health_trajectory: [T+1, T+2, T+3]   ← from Step 4
}
```

### Step 4 — Project health forward ([line 664](../../backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py))
```
_extrapolate_health(h_now, slope, months, deceleration=0.85)
```
Slope dampens 15% per month (linear trends rarely hold long). Detects threshold crossings (healthy → at-risk → critical).

### Step 5 — Detect "saved" accounts ([line 875](../../backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py))

An account counts as saved-by-CS-Pulse if **all three** are true:
1. Had a crisis (`lowest_health < 60`)
2. Recovered (`ending_health > lowest_health + 10`)
3. Has a positive outcome OUTCOME node (`churn_averted`, `revenue_protected`, `renewal_secured`)

`saved_arr` is the sum of ARR across these accounts.

### Step 6 — Compute current NRR ("with CS Pulse") ([line 934](../../backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py))
```
current_nrr = (total_arr − total_lost + total_expansion) / total_arr
```
Direct from definitive lifecycle outcomes. **No projection.** This is the truthful "today" number.

### Step 7 — Without CS Pulse counterfactual

Two modes, controlled by `FEATURE_WIZARD_B_V2_FORECAST`:

**v1.5 (default)** — only saved accounts get downgraded ([line 950](../../backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py)). Their organic retention is banded by ending health:

| Ending health | Organic retention |
|---|---|
| `< 50` | 40% |
| `< 70` | 70% |
| `< 85` | 85% |
| `≥ 85` | 95% |

Plus a self-recovery modifier: `recovery_pp ≥ 15` → **+0.15** (more credit to organic, less to CS Pulse); `recovery_pp ≤ −5` → **−0.10**.

**v2 (opt-in, `FEATURE_WIZARD_B_V2_FORECAST=true`)** — continuous projection over **all** accounts ([line 992](../../backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py)). Uses `(h_end, h_start, h_lowest, arc_type)` to produce a value in [0%, 130%]. Added April 25 because v1.5 returned 100% NRR for cold-start tenants with no rich OUTCOME data (6-tenant probe showed portfolio MAPE 23pp).

### Step 8 — With-further-interventions counterfactual

For each at-risk account (`current_nrr < 1.0`):
```
intervened_nrr  = success_rate × 1.0 + (1 − success_rate) × current_nrr
projected_save  = arr × (intervened_nrr − current_nrr)
```
`success_rate` comes from Step 1's per-arc `intervention_success_rate`.

### Step 9 — Revenue waterfall (backward-looking attribution) ([line 1191](../../backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py))

Uses a fixed health → annual churn probability table:

| Health band | Annual churn prob |
|---|---|
| `< 30` | 45% |
| `< 50` | 45% → 35% (linear) |
| `< 70` | 25% → 15% (linear) |
| `< 85` | 8% → 5% (linear) |
| `≥ 85` | 3% |

Then per account:
```
expected_loss_before  = churn_prob(health_lowest) × arr      ← past worst point
expected_loss_after   = churn_prob(health_now)    × arr      ← today
gross_saved           = expected_loss_before − expected_loss_after
attributed_save       = gross_saved × ATTRIBUTION_FACTOR     ← 0.5 today
```

**`ATTRIBUTION_FACTOR = 0.5`** — only half the recovery is credited to CS Pulse; the rest to organic factors. This is one of the two main trust knobs.

### Step 10 — Renewal risk overlay ([line 828–840](../../backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py))

| Tier | Trigger |
|---|---|
| **urgent** | `days_to_renewal ≤ 30 AND projected_health_at_renewal < 50` |
| **warning** | `≤ 60 AND projected < 60` |
| **watch** | `≤ 90 AND slope < −1` |

### Step 11 — Top-10 intervention ranking

At-risk accounts sorted by `projected_save / playbook_cost` ROI. Each gets a deadline string ("Act within 7/14/21 days") based on renewal proximity or health severity. Playbook cost comes from `playbook_cost_bridge` with ARR-scaled floors (e.g., $45K min for $8M+ ARR crisis playbooks).

### Step 12 — Aggregate to `portfolio_nrr_forecast` ([line 1303](../../backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py))

The single dict returned to the API/UI:
```
{
  current_nrr_pct,                  ← Step 6
  without_cs_pulse_nrr_pct,         ← Step 7
  with_interventions_nrr_pct,       ← Step 8
  cs_pulse_delta_pct,               ← current − without
  cs_pulse_arr_protected,           ← saved_arr from Step 5
  cs_pulse_accounts_saved,
  trajectory,                       ← portfolio T+30/60/90
  revenue_waterfall,                ← Step 9
  renewals_at_risk,                 ← Step 10
  pattern_breakdown,                ← per-arc summary
  top_interventions[:10],           ← Step 11
}
```

### What it ISN'T

- **Not ML.** Deterministic, auditable, feature-flagged. Health → churn probability is a fixed lookup table, not a learned model.
- **Not real-time.** Wizard B runs on `_process_data_impl` after every CSV ingest; cached in `WizardLearning.learnings.portfolio_nrr_forecast`.
- **Not a full account-level surface.** Per-account NRR is computed in Step 3 but only top-10 surface to the UI today (gap — exposing per-account NRR is a half-day add: read the cached dict, add an endpoint, add a row on the account detail page).

### The two trust knobs (what to tune if a buyer challenges accuracy)

1. **`ATTRIBUTION_FACTOR = 0.5`** (Step 9) — how much of the recovery to credit to CS Pulse vs. organic factors. Tunable per customer.
2. **`FEATURE_WIZARD_B_V2_FORECAST`** — switches the without-CS-Pulse counterfactual from "only saved accounts dropped" to a continuous projection over all accounts. v2 is more accurate for cold-start tenants but less conservative.

---

## 2. Inputs, Outputs, Consumers, Storage

### Inputs (PostgreSQL only — both wizards are DB-native)

| Wizard | Tables read |
|---|---|
| A | `dc2s_kpis`, `health_scores`, `qualitative_signals`, `accounts`, `context_nodes` |
| B | All of A's + `context_nodes` (OUTCOME), `accounts.arc_type` (Wizard A's output), `playbook_executions_v2` |

### Outputs and storage

| Output | Where stored | Path |
|---|---|---|
| `arc_type`, `arc_phase`, `arc_confidence` | `accounts` row columns | DB native |
| Wizard A DECISION nodes + causal edges | `context_nodes` (`node_type=DECISION`), `context_edges` | DB native |
| Wizard B full output (forecast + waterfall) | `wizard_runs.results` (JSON) | DB native |
| Wizard B per-account churn probabilities, per-pattern NRR | `wizard_runs.results.nrr_intelligence` | DB native |

### Consumers

| Consumer | Surface | What it reads |
|---|---|---|
| CSM Cockpit (`/dc-dashboard/csm`) | UI | account.arc_type, journey timeline |
| VP CS Dashboard (`/dc-dashboard/vpcs`) | UI | `nrr_intelligence.forecast`, waterfall |
| CRO/CFO Dashboards | UI | revenue_at_risk, NRR trajectory |
| Ask AI (`/api/executive/ask-v2`) | LLM tool | get_nrr_forecast MCP tool reads `wizard_runs.results` |
| MCP tools (Claude.ai) | API | `get_nrr_forecast`, `get_at_risk_accounts`, `get_account_journey_timeline`, `get_revenue_at_risk` |
| Outcome ROI Engine | Pipeline | reads Wizard B forecast for ROI math |
| Frontend Journey Intelligence component | UI | `/api/journey/<account_id>`, `/api/journey-intelligence/*` |

---

## 3. Internal Tuning Parameters

### Wizard A
| Parameter | Location | Effect |
|---|---|---|
| Arc template definitions | `config/story_arcs/*.json` (8 files) | Pattern shapes Wizard A matches against |
| Health-band thresholds | `config/health_thresholds.json` (0-49 critical / 50-69 at-risk / 70+ healthy) | Phase detection cutoffs |
| `arc_confidence` floor | `wizard_a_journey_db.py` | Minimum confidence to assign an arc |

### Wizard B
| # | Parameter | Location | Influence |
|---|---|---|---|
| 1 | `_DEFINITIVE_LOST` set | `wizard_b_pattern_analyzer.py:535` | Subtypes that count as ARR loss in NRR |
| 2 | `_DEFINITIVE_EXPANSION` set | `:536` | Subtypes that count as ARR expansion |
| 3 | `_positive_outcome_types` | `:846` | Subtypes that mark "saved by CS Pulse" |
| 4 | `_organic_retention()` health bands | `:931-944` (40/70/85/95% retention by health band + 0.15 recovery modifier) | v1.5 organic NRR calculation |
| 5 | `ATTRIBUTION_FACTOR = 0.50` | `:1015` | Halves CS Pulse intervention attribution in waterfall |
| 6 | `_churn_prob(h)` curve | `:1017-1024` (5 bands: <30→45%, <50→linear, <70→linear, <85→linear, ≥85→3%) | Account-level churn probability from health |
| 7 | Saved-account criteria | `:868-874` (`ending > lowest + 10` AND (`lowest < 50` OR `starting < 50`) AND `has_positive_outcome`) | Defines "this account was rescued" |
| 8 | `_continuous_renewal_projection()` (feature-flagged v2) | `:962-1010` | Continuous projection: base health curve + trend modifier + arc modifier |
| 9 | `FEATURE_WIZARD_B_V2_FORECAST` env var | runtime | Toggles between v1.5 and v2 forecast paths |
| 10 | `health_thresholds.json` (shared) | `config/` | Defines critical/at-risk/healthy bands used by all wizards |

---

## 4. Visualization Capabilities

### Currently available

| Visualization | Where | Backend endpoint |
|---|---|---|
| Per-account 6-month health trajectory | CSM Cockpit, VP CS deck | `/api/journey/<account_id>` |
| Health distribution bar chart (Healthy/At-Risk/Critical) | VP CS dashboard | `/api/dc2s/scores/*` |
| Story arc label + phase badge | Account drill-down | `accounts.arc_type` |
| NRR forecast headline numbers | VP CS / CFO dashboards | `wizard_runs.results.nrr_intelligence.forecast` |
| Revenue waterfall (text/table) | Wizard B output (currently CLI-printed only) | not yet rendered as chart |
| ASCII forecast in pipeline logs | stdout during `process_data` | "1️⃣ Analyzing patterns…" through "6️⃣ Forecasting portfolio NRR…" |
| Context graph mermaid render | Per-account | `get_context_graph_mermaid` MCP tool |

### Gap: there is no single chart that overlays journey + arc + Wizard B prediction

To visualize *journey, arcs, and prediction curves together*, build:

**New endpoint** `/api/wizards/visualize/<account_id>` returning JSON:
- 12 monthly historical health points (from `health_scores`)
- Phase boundaries as colored bands (from Wizard A's phase detection)
- Wizard B's `t30/t60/t90` projected NRR points + confidence band
- OUTCOME nodes plotted as event markers
- Without/With CS Pulse forecast lines (two series for comparison)

**Frontend component** `<JourneyForecastChart>` (recharts, ~1 day):
- X-axis: months (12 historical + 3 projected)
- Y-axis left: health score 0-100
- Y-axis right: NRR % 0-150
- Phase bands as background fills
- OUTCOME events as scatter markers with hover tooltip
- Forecast lines as dashed extensions

**Recommended location:** account drill-down in CSM Cockpit
(`src/components/csm/AccountDeepDive.tsx`), and a portfolio-aggregate
variant for the VP CS dashboard.

---

## Quick reference

- **To re-run wizards manually:** `trigger_wizard` MCP tool (`wizard='a' | 'b' | 'c'`).
- **To rollback Wizard B v2:** `unset FEATURE_WIZARD_B_V2_FORECAST` (default OFF).
- **To inspect a tenant's Wizard B output:** `SELECT results FROM wizard_runs WHERE customer_id=<id> ORDER BY completed_at DESC LIMIT 1;`
- **Backtest harness:** `kpi-dashboard/backend/tests/e2e/test_claude_driven_backtest.py`.
- **Latest accuracy results:** `scripts/datasets/claude_driven_backtest_v15_6tenants_results.json`,
  `scripts/datasets/loaddriver_v15_v21_results.json`.
