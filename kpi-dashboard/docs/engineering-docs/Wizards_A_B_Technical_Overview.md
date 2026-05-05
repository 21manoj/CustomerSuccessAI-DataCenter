# Wizard A & Wizard B — Technical Overview

*Last updated: Apr 25 2026*

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

**Purpose.** Two outputs: (a) per-pattern NRR correlation across the
portfolio, (b) revenue-weighted portfolio NRR forecast (with-CS-Pulse and
without-CS-Pulse projections).

**Source:** `backend/wizards/wizard_b_pattern_db.py` (DB wrapper) calling
`backend/verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py`
(core analyzer).

**Workflow (numbered in Wizard B's own stdout):**
1. Load patterns: group accounts by `arc_type`/`pattern_type` from Wizard A.
2. Compute pattern-level NRR correlations (avg NRR, ARR exposed,
   intervention success rate per pattern).
3. Phase-transition analysis — map account moves between phases.
4. Early-warning extraction — surface signals that historically preceded
   churn.
5. Pattern → NRR impact correlation.
6. **Portfolio NRR forecast** — weighted aggregation across accounts
   producing `without_cs_pulse_nrr_pct`, `current_nrr_pct`,
   `with_interventions_nrr_pct`, `cs_pulse_arr_protected`.
7. Trajectory at T+30/60/90 days + revenue waterfall (per-account
   exposure, expected loss, residual risk, attributed save, intervention
   cost, projected ROI).

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
