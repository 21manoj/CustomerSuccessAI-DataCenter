# CS Pulse — Dashboard Data Lineage, Data Flow & Eval KT

**Audience:** New developers who will **validate the UI dashboard numbers** for the CSM, VP CS, CRO, and CFO personas, run evals, test persona robustness, and flag gaps.

**What you'll be able to do after reading this:** take any number on any persona dashboard, trace it backwards through the API → computation module → source table → the synthetic-data manifest that produced it; run the acceptance + persona-grading evals; and know where the current gaps are.

> **Anchor on file + function names, not line numbers.** Line numbers drift. When a reference looks stale, `grep` the function name. All paths are relative to **repo root** (`CustomerSuccessAI-DataCenter/`).

---

## Day 1 checklist (start here)

1. **Pick tenant 336** — SaaS Premium demo with live EC2 data (`load-driver/manifests/predictor_v3_demo_saas_cust336.json`). Confirm `process_data` has run (30 accounts, KPIs loaded).
2. **Quick smoke** — `ACCEPTANCE_CUSTOMER_ID=336 python3 scripts/spot_check_cust336.py` (10 checks: accounts, CRO/CFO parity, Predictor v3, VPCS capacity).
3. **Offline generator guard** — `pytest load-driver/tests/test_seed_data_quality.py -q` (15 tests; run before trusting a new manifest).
4. **Pick one number** — e.g. CRO **Revenue at Risk = $39.9M** on EC2 → follow §4 recipe → compare API JSON vs hand recompute vs manifest.
5. **HTTP acceptance** — `ACCEPTANCE_CUSTOMER_ID=336 python3 scripts/verify_executive_phases_ec2.py --suite cro,cfo,vpcs`.
6. **Number correctness (optional but recommended)** — `ACCEPTANCE_CUSTOMER_ID=336 python3 scripts/verify_dashboard_number_correctness_ec2.py`.
7. **Read §3f** — Customer 336 worked examples with live dashboard anchors.
8. **Read §3g + `EC2_RUNTIME_ACCESS.md`** — SSH-first access; no git clone required.

---

## Prerequisites (before validating KPIs)

| Requirement | Why |
|---|---|
| Tenant has completed **`process_data`** | Health scores, context graph, Wizard B outputs exist |
| Auth: session cookie **or** `Authorization: Bearer` + `X-Customer-ID: 336` | All `/api/v1/*` and executive routes are tenant-scoped |
| **`FEATURE_PREDICTOR_API=true`** (default) | Predictor v3 tiles; `false` → 503 + Wizard B fallback |
| Wizard **D calibration** rows for tenant (336: all 30 accounts `calibrated`) | Without calibration, NRR forecast is cold-start/pooled |
| Know **trailing vs leading** (§0) | Same label ("at risk") can mean health band, ARR exposure, or context-graph $ |

**When numbers look wrong — quick triage**

| Symptom | Likely cause |
|---|---|
| `0` accounts / empty dashboard | `process_data` not run or wrong `X-Customer-ID` |
| Predictor tile missing / 503 | `FEATURE_PREDICTOR_API=false` or no calibration |
| CRO ≠ CFO on `revenue_*` | Bug — must match (same `get_revenue_at_risk()` path) |
| Health band count ≠ VPCS "at risk" | **Different definitions** — health-summary uses `classify()`; team-capacity uses workload model |
| Manifest ARR ($200M) ≠ dashboard ARR ($175M) | Post-ingest expansion/contraction lifecycle events adjusted account ARR |
| SaaS tenant shows `PB-DC-*` playbooks | Known gap §7(1) — vertical playbook routing leak |

---

## Glossary (10 terms)

| Term | Meaning |
|---|---|
| **Trailing** | Realized / historical — KPIs, health scores, booked OUTCOME nodes, Wizard B NRR |
| **Leading** | Forecast / causal — signals, context-graph confirmed $, Predictor v3 NRR |
| **Exposure (revenue@risk)** | Modeled $ at risk from unhealthy accounts (health band × ARR × churn %) |
| **Confirmed (revenue@risk)** | Sum of OUTCOME node impacts with causal edges, conf ≥ 0.5 |
| **Wizard B NRR** | Trailing counterfactual NRR (with vs without CS interventions) |
| **Wizard D / Predictor v3** | Leading forward NRR forecast from calibrated sub-models |
| **arr_exposure** | `health-summary` field: ARR in accounts below healthy threshold |
| **Cold-start** | Predictor inference without tenant-specific calibration row |
| **process_data** | Ingestion pipeline: health scores, Wizard A/B, signal analyst, optional onboarding activation plan |
| **Manifest** | `load-driver/manifests/*.json` — declarative synthetic customer spec |

---

## 0. The one mental model to hold

CS Pulse is a **two-layer indicator system** (product design intent):

- **TRAILING / realized** — what already happened. KPI rollups (health score), booked outcomes, Wizard B NRR. Sourced from `DC2SKPI`, `HealthScore`, `ContextNode(OUTCOME)`.
- **LEADING / forecast** — what's *about* to happen. Qualitative signals → causal graph, and **Wizard D / Predictor v3** NRR forecast. Sourced from `QualitativeSignal`, `ContextEdge`, `PredictorCalibration`.

Every dashboard number is one or the other (or a blend). When you validate a number, the **first question is always: is this trailing or leading?** — because they have different source tables and different "correct" definitions.

---

## 1. End-to-end data flow

```
┌─ GENERATION (load-driver/, no DB) ──────────────────────────────────────┐
│ manifests/<name>.json         declarative spec: accounts, story_arc,    │
│        │                      classification, kpi_trajectory, lifecycle  │
│        ▼                                                                  │
│ scenarios/scenario_manifest.py :: ManifestCSVGenerator                   │
│   ├─ NarrativeTimelinePlanner   plans event dates, baseline vs interv.   │
│   ├─ ARC SPINES                 per-arc {baseline[], intervention[], edges}│
│   ├─ catalog_loader.py          vertical KPI catalog (set_vertical)      │
│   ├─ _generate_kpi_series       KPI time series + recovery V-shape       │
│   └─ generate_all() ─► 7 core CSVs (+ optional context-graph pack):      │
│        account_details · kpi_measurements · qualitative_signals ·       │
│        decisions · outcomes · signal_edges · engagement_events            │
└──────────────────────────────────────────────────────────────────────────┘
        │  load-driver/client.py  ──HTTP──►
        ▼
┌─ INGESTION (kpi-dashboard/backend) ─────────────────────────────────────┐
│ MCP/onboarding tools: create_customer → upload_csv → process_data       │
│   mcp_server/cs_pulse_onboarding.py :: _process_data_impl               │
│   + onboarding_api_v2_config_aware.py :: ingest_context_graph_csvs       │
│        writes models.py: DC2SKPI · QualitativeSignal · Account ·         │
│                          ContextNode · ContextEdge                       │
│        ▼                                                                  │
│ AUTO per process_data:                                                    │
│   • Wizard A → journey/DECISION nodes                                     │
│   • Wizard B → playbook_outcome + realized NRR rollup   (TRAILING)       │
│   • tier1_inference (LLM) → extra OUTCOME nodes @conf 0.3                 │
│   • Signal analyst + urgent scanner + ROI + Qdrant                        │
│   • Onboarding activation plan (fallback or LLM if entitled) — once/tenant│
│ DECOUPLED (offline / on-trigger, NOT per process_data):                  │
│   • Wizard C → weight calibration                                        │
│   • Wizard D → Predictor v3 calibration                 (LEADING)        │
│        ▼                                                                  │
│ utils/score_calculator.py  L1(KPI)→L2(pillar)→L3(account)→L4(cust)       │
│ utils/context_graph.py     Signal→Decision→Outcome chains, revenue@risk  │
└──────────────────────────────────────────────────────────────────────────┘
        ▼
┌─ READ / UI ─────────────────────────────────────────────────────────────┐
│ Flask APIs + MCP tools  →  React dashboards (CSM / VP CS / CRO / CFO)    │
│ predictor/inference.py  →  Predictor v3 forecasts (on demand, read time) │
│ download_customer_csv   →  data export (round-trips the tenant to CSV)   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1a. The Wizards (what computes what)

| Wizard | Runs | Produces | Trailing/Leading |
|---|---|---|---|
| **A** | auto / process_data | Journey + DECISION context nodes | n/a (structure) |
| **B** `wizards/wizard_b_pattern_db.py` | auto / process_data | Realized NRR (with-vs-without-CS counterfactual), `arr_protected`, `accounts_saved` | **Trailing** |
| **C** | on trigger (`trigger_wizard wizard='c'`) | KPI/pillar weight calibration → `CustomerConfig` | n/a (weights) |
| **D** `wizards/wizard_d_predictor_calibrator.py` | offline / cron / `trigger_wizard wizard='d'` | `PredictorCalibration` rows (4 sub-models: hazard, contraction, expansion_event, expansion_size) | **Leading** |
| tier1_inference | auto / process_data | LLM-enriched OUTCOME nodes @conf 0.3 | both |

> **Why Wizard D isn't in the process_data lane:** Architecture Decision A2 splits **offline calibration** (Wizard D writes `PredictorCalibration`) from **online inference** (`predictor/inference.py` reads it at query time). Calibration is quarterly/triggered; inference runs per dashboard load.

---

## 2. How "intervention" (recovery) data is applied — important for NRR numbers

Intervention is **not a separate dataset** — it is the **second half of each account's story arc** (`scenario_manifest.py` arc spines, `intervention[]` lists + `phase:'intervention'` edges). It shows up in three layers:

| Layer | Source | Becomes |
|---|---|---|
| Signals | auto-recovery block in `generate_signals_csv`, vertical recovery templates | `*_auto_recovery_*` signals ("Time-to-value improved 30%…", "120 seats…") |
| Outcomes | arc intervention phase in `generate_outcomes_csv` | `churn_averted`, `revenue_protected`, `expansion_approved` |
| KPIs | `_generate_kpi_series` | the V-shape recovery |

**Two application modes:**

- **Single-pass / merged (`phase=None`)** — baseline + intervention generated together in one upload. **This is what cust 336 used** (signal refs are `narrative_sig_*` + `auto_recovery_*` with no `intervention_` prefix).
- **Create + extend (`extend_mode=True, phase='intervention'`)** — baseline uploaded first, then a continuation delta uploaded as a second batch and re-processed. Canonical pattern for incremental NRR testing.

**Why this matters for validation:** lifecycle outcomes are the **event labels Wizard D calibrates on** — `churn_lost → is_churn_event`, `expansion_closed → is_expansion_event`, `contraction → is_contraction_event`. A churn account that *also* carried `churn_averted`, or a doubled `revenue_protected`, poisons both Wizard B realized NRR and Wizard D forecast. (Those exact bugs existed in the first cut of 336 — see §7.)

---

## 3. Data lineage by persona

Each table reads: **Metric on screen → UI component → API/MCP → compute module → source table(s) → trailing/leading.**

### 3a. CSM (CSMCockpit)

UI: `kpi-dashboard/src/components/csm/CSMCockpit.tsx` (account list, kanban Fire/Week/Opportunity, daily actions, account drawer).

| Metric | API | Compute (fn @ file) | Source table | T/L |
|---|---|---|---|---|
| Account health score | `GET /api/v1/accounts` | `calculate_kpi_health()` → L1→L2→L3 @ `verticals/dc2_s/api_routes.py` + `utils/score_calculator.py` | `DC2SKPI`, `HealthScore`, `CustomerConfig` (weights) | Trailing |
| Pillar breakdown P1–P5 | `GET /api/v1/accounts` / drawer | `HealthScore.contributing_pillars` or `PillarScore` | `HealthScore` / `PillarScore` | Trailing |
| Health trend (6mo) | `GET /api/v1/health-score-history` | `get_health_score_history_api()` | `HealthScore` by `measurement_month` | Trailing |
| Daily actions / priority | `GET /api/v1/daily-actions` | `get_csm_daily_actions()`, `_compute_impact_score`, `_compute_effort_score` | `HealthScore` (churn/expansion prob), `Account.revenue`, playbook config | Leading (action priority) |
| Recommended playbooks | `GET /api/v1/recommendations/<id>` | `should_trigger_playbook()` @ `verticals/dc2_s/vertical_config.py` | `DC2SKPI` (KPI vs trigger thresholds) | Leading |
| At-risk / critical flag | classification | `classify()` @ `utils/health_thresholds.py` | `config/health_thresholds.json` (70 / 50) | Trailing |
| Stakeholder / signals (drawer) | `GET /api/context-graph/stakeholder-map`, `/nodes` | `utils/context_graph.py` | `ContextNode(SIGNAL/STAKEHOLDER)`, `QualitativeSignal` | both |

### 3b. VP CS (VPCSDashboard)

UI: `kpi-dashboard/src/components/dashboard/VPCSDashboard.tsx` (summary cards, health distribution, actions queue, renewals, team capacity, CSM scorecards).

| Metric | API | Compute | Source table | T/L |
|---|---|---|---|---|
| Avg health (ARR-weighted) | `GET /api/v1/health-summary` | `get_dc2s_health_summary()` (`SUM(health·arr)/SUM(arr)`) | `HealthScore`, `Account.revenue` | Trailing |
| Health distribution (3 buckets) | `GET /api/v1/health-summary` | `classify()` buckets + ARR sum | `HealthScore`, `Account` | Trailing |
| CSM scorecard (rank, Δhealth, success%, rev protected/expanded) | `GET /api/v1/csm-scorecard` | `get_csm_scorecard_api()` | `HealthScore`, `PlaybookExecutionV2` | Trailing |
| Team capacity (util%, recommended CSM count) | `GET /api/v1/team-capacity` | `get_team_capacity_api()` → `resource_capacity_model.check_capacity()` | `PlaybookExecutionV2.csm_hours_planned`, `assigned_csm` | Leading (capacity plan) |
| Renewals (90d) | `GET /api/v1/renewals?days=90` | filter `renewal_date` | `Account.profile_metadata['renewal_date']` | Trailing |
| Playbook success % | `/api/v1/playbook-success-metrics` | `resolved/executed` | `PlaybookExecutionV2.outcome` | Trailing |
| Portfolio revenue summary | `/api/outcome-roi/portfolio-summary` | `aggregate_revenue_across_accounts()` | `ContextNode(OUTCOME)` | Trailing |

### 3c. CRO (CRODashboard) — growth/opportunity lens

UI: `kpi-dashboard/src/components/dashboard/CRODashboard.tsx`. API: `GET /api/executive/cro-dashboard` (`executive_dashboard_api.py`). MCP: `get_cro_dashboard_summary`.

| Metric | Compute (fn @ file) | Source table | T/L |
|---|---|---|---|
| Revenue at Risk — **Exposure** (ARR in unhealthy accts) | `context_graph.get_revenue_at_risk()` (health × ARR × churn-prob: crit 40%, at-risk 20%, healthy 5%) | `HealthScore`, `Account` | Trailing |
| Revenue at Risk — **Confirmed** (causally linked) | same fn, OUTCOME nodes + edges, conf ≥ 0.5, 20% dedup | `ContextNode(OUTCOME)`, `ContextEdge` | Leading |
| Revenue Protected / Expansion pipeline | `get_revenue_at_risk()` by `revenue_impact_type` | `ContextNode(OUTCOME)` | Trailing |
| Story arcs | `_build_story_arcs()` @ `executive_dashboard_api.py` | `ContextNode(SIGNAL)` pattern match | Leading |
| Highest-risk accounts grid | Account + HealthScore + SIGNAL count | `Account`, `HealthScore`, `ContextNode` | both |
| **Wizard B NRR (realized)** | `run_wizard_b()` (with-vs-without counterfactual) | `HealthScore` journey, `ContextNode(OUTCOME)`, `PlaybookExecutionV2` | **Trailing** |
| **Predictor v3 NRR (forecast)** | `predictor.inference.predict_for_account_id()` | `PredictorCalibration`, `Account`, `HealthScore` | **Leading** |
| Top expansion opps (v3) | `/api/v1/predictor/customer/<id>/top-expansion-opportunities` rank by `expected_arr_lift` | `PredictorCalibration` + panel | Leading |
| Top at-risk (v3) | `/top-at-risk-accounts` rank by `p_churn × arr` | `PredictorCalibration` + panel | Leading |
| Power-of-1 ROI | `power_of_1_model.calculate_power_of_1_impact()` | `POWER_OF_1_METRICS` const × `Account.revenue` | Model-based |

### 3d. CFO (CFODashboard) — proof/cost lens

UI: `kpi-dashboard/src/components/dashboard/CFODashboard.tsx`. API: `GET /api/executive/cfo-dashboard`. MCP: `get_cfo_dashboard_summary`.

| Metric | Compute | Source table | T/L |
|---|---|---|---|
| Total ARR | `SUM(Account.revenue)` | `Account` | Trailing |
| CS Investment | `resource_capacity_model` + `playbook_cost_bridge` | resource rates JSON, `PLAYBOOK_CONFIG` hours | Projected |
| Revenue Protected (proof) | `get_revenue_at_risk()` protected bucket | `ContextNode(OUTCOME)` | Trailing |
| Portfolio ROI % | `power_of_1_model.calculate_portfolio_impact()` | `POWER_OF_1_METRICS`, `PillarScore` | Model |
| Historical / realized ROI | `outcome_roi_api.get_historical_roi()` → `_extract_historical_actuals()` | `HealthTrend`, `PillarScore`, `KPIScore`, `ROISnapshot` | Trailing |
| Power-of-1 outcomes table | `_extract_current_values()` (DC2S) or baseline (SaaS) | `PillarScore`, `POWER_OF_1_METRICS` | Trailing+Model |
| Pillar investment breakdown | `get_playbook_economics()` per pillar | `PLAYBOOK_CONFIG` work packages, resource rates | Model |
| Predictor v3 portfolio NRR (CI bounds) | per-account `predict_for_account_id()` → ARR-weighted | `PredictorCalibration` | **Leading** |

> **CRO/CFO $ parity rule:** `revenue_at_risk`, `revenue_protected`, `expansion_pipeline` **must be identical** on CRO and CFO (both call the same context-graph aggregation). The acceptance suite asserts this (§5). If they differ, it's a bug.

### 3e. Predictor v3 forecast — the lineage to internalize

```
predictor/sql/build_panel.sql  →  build_panel.py     (account×month covariates:
                                                       health, slope, days_to_renewal,
                                                       arc_type, segment, ARR)
        ▼
predictor/features.py  engineer_features()           (one-hot arc_type; 3 targets:
                                                       is_churn/contraction/expansion_event)
        ▼  OFFLINE
wizards/wizard_d_predictor_calibrator.py  →  glmm.fit_all_sub_models
        →  PredictorCalibration rows (immutable; prior active flipped off)
        ▼  ONLINE (read time)
predictor/inference.py  predict_for_account_id(horizon=renewal|quarter|12mo)
        →  expected_nrr {point, lower_90, upper_90} · term_decomposition
           {p_churn, e_contract%, e_expand%} · expansion_outlook {arr_lift ± CI}
        ▼
predictor_api.py  /api/v1/predictor/...   +   mcp_server/cs_pulse_predictor.py
```

The manifest's `story_arc` maps ~1:1 onto the predictor's `arc_type` feature (`recovery`, `competitive_displacement`, `silent_churn`, `stalled_deployment` exist in both). **Calibration is per `(customer, saas_profile, sub_model)`; inference is verified ID-agnostic across 334/335/336** — that's exactly what the "Predictor V3 Verify" tenants exist to prove.

**Kill switches:** `FEATURE_PREDICTOR_API=false` → endpoints 503 with `{fallback:'wizard_b_legacy'}` (UI falls back to Wizard B). `FEATURE_PREDICTOR_V3_UI` toggles the tile independently (API-on/UI-off soak testing).

---

## 3f. Customer 336 — reference tenant & live dashboard anchors

Use **customer 336** as the primary hands-on validation tenant. It is a **SaaS Premium** portfolio regenerated with vertical-aware signals, P4 KPI coverage, lifecycle-safe outcomes, and full Predictor v3 calibration.

### Source artifacts

| Artifact | Path |
|---|---|
| Manifest | `load-driver/manifests/predictor_v3_demo_saas_cust336.json` |
| Generated CSV pack | `load-driver/output/customer336-saas_premium/data/` |
| Spot-check script | `scripts/spot_check_cust336.py` |
| Seed quality tests | `load-driver/tests/test_seed_data_quality.py` (uses cust336 pack) |

### Manifest design (what the generator intended)

| Field | Value |
|---|---|
| Customer name | Predictor V3 Demo SaaS Co (336) |
| Vertical | `saas_premium` |
| Accounts | 30 |
| Manifest total ARR | $200M (design target; post-lifecycle ingest → **$175.4M** live) |
| Time range | 2024-10 → 2026-05 (20 monthly KPI points) |
| KPIs | 10 codes (`starter_9_plus_p4`, includes **P4-KPI1**) |
| Classification mix | 20 healthy · 5 at_risk · 5 critical |
| Story arcs | `land_and_expand` (13), `expansion_champion` (7), `crisis_recovery` (3), `competitive_displacement` (3), `silent_churn` (2), `stalled_deployment` (2) |

**Example accounts to trace manually**

| Account | ID | Manifest class | target_health | story_arc | Notes |
|---|---|---|---|---|---|
| Polaris Cloud | 336001 | healthy | 82 | land_and_expand | Top ARR; expansion lifecycle |
| Deneb Pharma | — | at_risk | 62 | crisis_recovery | Recovery arc; auto_recovery signals |
| Cassiopeia Insurance | — | critical | 48 | competitive_displacement | `lifecycle.event: churn` |
| Cygnus Holdings | — | critical | 38 | silent_churn | `lifecycle.event: churn` |

### Sample CSV rows (336) — real values from the generated pack

Source: `load-driver/output/customer336-saas_premium/data/` (same files ingested to EC2 at `verticals/customer336-saas_premium/data/`). Headers shown; values are verbatim (long fields truncated with `…`). Use these to recognize the schema and trace a row end-to-end.

**`account_details.csv`** — accounts, ARR, CSM, products (JSON), renewal:

```text
source_account_id,customer_id,account_name,industry,region,vertical,tier,arr,revenue,contract_start,contract_end,renewal_date,csm_name,…,account_status,uuid,…,products,employee_count,tech_stack,cloud_provider,deployment_type
336001,336,Polaris Cloud,Telecommunications,North America,saas_premium,Enterprise,20160000,20160000,2025-09-30,2026-09-30,2026-09-30,Sarah Rivera,…,active,dc_acct_fbfe97129dee,…,"[{""name"":""Mobile App"",""arr"":5575070}, …]",4592,"Next.js, Go, Redis",Azure,hybrid
336002,336,Vega Software,AI/ML,North America,saas_premium,Enterprise,13500000,13500000,2025-09-30,2026-09-30,2026-09-30,Alex Chen,…,active,dc_acct_6264ac3a216c,…,"[{""name"":""Data Export & BI"",""arr"":4696042}, …]",509,"React, Node.js, PostgreSQL",On-Prem,hybrid
```

**`qualitative_signals.csv`** — `narrative_sig_*` (baseline) + `auto_recovery_*` (recovery phase), populated `stakeholder_name`, `arc_id`, `story_phase`:

```text
signal_id,source_account_id,signal_date,signal_type,content,sentiment,sentiment_score,stakeholder_name,stakeholder_title,arc_id,story_phase,linked_node_id,signal_ref
narrative_sig_336001_1,336001,2025-01-29,routine_review,Routine quarterly review completed (Polaris Cloud),positive,0.65,Sarah Rivera,Customer Success Manager,land_and_expand,baseline,,narrative_sig_336001_1
auto_recovery_336001_2,336001,2026-01-02,expansion_signal,Account adding 120 seats across 3 departments. Expansion PO in procurement. — Polaris Cloud,positive,0.97,Jordan Kim,VP Engineering,land_and_expand,recovery,,auto_recovery_336001_2
narrative_sig_336013_2,336013,2024-12-30,usage_spike,Significant usage increase detected (Antares Holdings),positive,0.65,Taylor Blake,Director of IT,expansion_champion,baseline,,narrative_sig_336013_2
```

**`kpi_measurements.csv`** — monthly time series; `kpi_code`/`pillar`/`status` per account (20 points × 10 KPIs × 30 accounts):

```text
source_account_id,kpi_code,kpi_name,pillar,measured_at,value,target,weight,unit,status
336001,P1-KPI1,Daily Active Users (DAU) Rate,P1,2024-10-01,73.68,60,0.16,percentage,healthy
336001,P1-KPI1,Daily Active Users (DAU) Rate,P1,2024-10-31,74.78,60,0.16,percentage,healthy
336001,P1-KPI1,Daily Active Users (DAU) Rate,P1,2024-11-30,76.08,60,0.16,percentage,healthy
```

**`outcomes.csv`** — lifecycle $ events (these are the labels Wizard B/D learn from). Note signed `revenue_value` and `outcome_type`:

```text
source_account_id,outcome_date,outcome_type,title,description,revenue_value,status,linked_signal_id
336001,2025-03-14,renewal_secured,Renewal Secured — Polaris Cloud,Renewal confirmed…,900000.0,resolved,narrative_sig_336001_1
336001,2025-03-30,expansion_closed,ARR Expansion Closed — Polaris Cloud,Contract expansion executed…,2160000.0,resolved,
336019,2026-05-24,churn_averted,Churn Risk Averted — Deneb Pharma,Retention plan executed…,3560000.0,resolved,narrative_sig_336019_1
336022,2026-02-23,churn_lost,ARR Lost — Churn — Cassiopeia Insurance,Account churned. Full ARR lost.,-11200000,resolved,
336021,2025-05-29,contraction,ARR Contraction — Mira Logistics,Account reduced scope…,-510000.0,resolved,
```

> **How these rows explain the dashboard (§3f):**
> - **CRO/CFO Revenue Protected $13.28M** ← positive lifecycle outcomes (`revenue_protected`, `churn_averted`) like 336019/336020/336021.
> - **Expansion pipeline $24.46M** ← `expansion_closed` / `expansion_approved` (336001 +$2.16M, 336013 +$4.125M, …).
> - **Revenue at Risk** ← `churn_lost` accounts (336022–336026, e.g. Cassiopeia −$11.2M) + health-band exposure.
> - **Manifest ARR $200M → live $175.4M** ← the five `churn_lost` rows remove ~$33.4M post-ingest.
> - **Recovery arc** ← `auto_recovery_*` signals (`story_phase=recovery`) feed Deneb/Albireo `crisis_recovery` OUTCOME nodes.

**Other files in the pack:** `decisions.csv` (DECISION nodes / playbooks), `engagement_events.csv` (meetings, tickets, QBRs), `signal_edges.csv` (causal Signal→Decision→Outcome edges). Inspect on EC2 with `runtime_explorer.py csv-head <file>`.

### Live EC2 dashboard anchors (June 2026 — re-run spot check to refresh)

Captured via `ACCEPTANCE_CUSTOMER_ID=336 python3 scripts/spot_check_cust336.py` against `http://3.94.106.197`:

| Persona / surface | Metric | Live value | API |
|---|---|---|---|
| **All** | Account count | 30 | `GET /api/v1/accounts` |
| **VP CS** | Total ARR | $175.37M | `GET /api/v1/health-summary` |
| **VP CS** | Avg health (ARR-weighted) | 82.3 | `GET /api/v1/health-summary` |
| **VP CS** | Health bands | 18 healthy · 7 at-risk · 5 critical | `health_distribution` in health-summary |
| **VP CS** | ARR exposure (unhealthy) | $26.0M | `arr_exposure` in health-summary |
| **VP CS** | Team capacity at-risk count | 11 | `GET /api/v1/team-capacity` (≠ 7 — different model) |
| **CRO / CFO** | Total ARR | $175.37M | `GET /api/executive/cro-dashboard` |
| **CRO / CFO** | Revenue at risk | **$39.95M** | same (context-graph exposure) |
| **CRO / CFO** | Revenue protected | **$13.28M** | same |
| **CRO / CFO** | Expansion pipeline | **$24.46M** | same |
| **CRO / CFO** | $ parity | CRO == CFO on all three | spot check asserts match |
| **CFO** | Predictor v3 portfolio NRR | **102.87%** | `predictor_v3_portfolio_nrr.arr_weighted_nrr_pct` |
| **CFO** | Calibration coverage | 30/30 `calibrated` | `prediction_method_counts` |
| **Predictor** | Top at-risk (12mo) | Antares Holdings ($20.6M), Polaris Cloud ($20.2M) | `/api/v1/predictor/customer/336/top-at-risk-accounts` |
| **CSM** | Daily actions queue | 10 items; top: Albireo Industries "Health Check Follow-up" (high) | `GET /api/v1/daily-actions` |
| **CSM** | Sample account health | Capella Networks 87.7 (healthy) | `GET /api/v1/accounts` |

**UI routes for 336**

| Persona | URL |
|---|---|
| CSM | `/saas-dashboard/csm` or `/csm` |
| VP CS | `/saas-dashboard/vpcs` or `/vpcs` |
| CRO | `/saas-dashboard/cro` or `/cro` |
| CFO | `/saas-dashboard/cfo` or `/cfo` |

### Worked trace — CRO "Revenue at Risk $39.9M" on customer 336

1. **Classify:** Leading/trailing blend — exposure uses health bands (trailing) × churn probability weights (model).
2. **API:** `GET /api/executive/cro-dashboard` with `X-Customer-ID: 336` → `revenue_at_risk: 39945000`.
3. **Compute path:** `executive_dashboard_api.py` → `context_graph.get_revenue_at_risk(customer_id=336)`.
4. **Cross-check CFO:** same field on `GET /api/executive/cfo-dashboard` — must match exactly.
5. **Do not confuse with:** `arr_exposure` on health-summary ($26.0M) — that is **only** ARR in sub-healthy accounts, not the full context-graph revenue-at-risk model.
6. **Manifest trace:** critical accounts (Cassiopeia, Cygnus, …) carry `lifecycle.event: churn`; recovery accounts (Deneb, Albireo) carry `crisis_recovery` arcs feeding OUTCOME nodes after ingest.

### Worked trace — CFO Predictor v3 NRR 102.87% on customer 336

1. **Classify:** **Leading** — forward forecast, not realized NRR.
2. **API:** `GET /api/executive/cfo-dashboard` → `predictor_v3_portfolio_nrr.arr_weighted_nrr_pct`.
3. **Verify calibration:** `prediction_method_counts: {calibrated: 30}` — if any account is `cold_start`, portfolio NRR is not fully tenant-fit.
4. **Per-account drill:** `GET /api/v1/predictor/account/<account_id>/nrr-forecast?horizon=12mo`.
5. **Manifest link:** `story_arc` per account (`competitive_displacement`, `silent_churn`, …) → predictor `arc_type` feature in `predictor/features.py`.

---

## 3g. Independent access — EC2 runtime (need-to-know)

**Default for new validators:** SSH to EC2, explore the **running container** — not a full git clone.

**Full playbook:** [`EC2_RUNTIME_ACCESS.md`](EC2_RUNTIME_ACCESS.md) (companion to this doc).

### What validators receive vs operators

| Validators (need-to-know) | Operators only |
|---|---|
| SSH key → `ec2-user@<EC2>` | Git clone on host (`~/CustomerSuccessAI-DataCenter`) |
| Demo login for tenant **336** | Deploy scripts, `.env`, AWS/ECR |
| `~/cspulse-runtime-kit/docs/` on EC2 | Full monorepo, infra, unrelated tenants |

### Quick start (all via SSH)

```bash
# Laptop helper (optional)
./scripts/ec2-connect.sh map
./scripts/ec2-connect.sh audit

# Or on EC2 directly
sudo docker exec -e CUSTOMER_ID=336 cspulse-platform \
  python3 /app/backend/scripts/runtime_explorer.py map

sudo docker exec -e CUSTOMER_ID=336 \
  -e AUDIT_EMAIL='…' -e AUDIT_PASSWORD='…' \
  cspulse-platform \
  python3 /app/backend/scripts/runtime_explorer.py audit
```

**`runtime_explorer.py` commands:** `map` · `pipeline` · `csv-ls` · `csv-head <file>` · `endpoints` · `audit` · `export-db`

Pull DB export to laptop: see EC2_RUNTIME_ACCESS.md § Step 4.

### Need-to-know paths (inside `cspulse-platform` container)

Prefix `/app/` — repo-relative paths in §1–§3 map here:

| Stage | Container path |
|---|---|
| Manifest 336 | `/app/load-driver/manifests/predictor_v3_demo_saas_cust336.json` |
| CSV generator | `/app/load-driver/scenarios/scenario_manifest.py` |
| Ingested CSV pack | `/app/backend/verticals/customer336-saas_premium/data/` |
| `process_data` | `/app/backend/mcp_server/process_data_pipeline.py` |
| Wizards A–D | `/app/backend/wizards/wizard_*.py` |
| Revenue @ risk | `/app/backend/utils/context_graph.py` |
| CRO/CFO API | `/app/backend/executive_dashboard_api.py` |
| Predictor v3 | `/app/backend/predictor/inference.py` |

Ignore `verticals/customer290-*/journey/` — historical copies.

### Three data layers (compare on EC2)

| Layer | Inspect with |
|---|---|
| Design intent | `less /app/load-driver/manifests/…cust336.json` |
| Uploaded CSV | `runtime_explorer.py csv-ls` / `csv-head` |
| DB after wizards | `runtime_explorer.py export-db` → `docker cp` |
| Dashboard numbers | `runtime_explorer.py audit` or browser UI |

### Operators: sync docs + scripts to EC2

```bash
./scripts/sync_ec2_runtime_kit.sh   # ~/cspulse-runtime-kit/ + hot-copy into container
```

### Repo-clone access (engineers only)

If you have the full git repo: local paths in earlier KT revisions (`load-driver/output/…`, `scripts/spot_check_cust336.py`, `pytest load-driver/tests/…`) still apply. Validators without git should use **`runtime_explorer.py`** equivalents on EC2 instead.

---

## 4. How to validate a dashboard number (the recipe)

For any number on screen:

1. **Classify it** — trailing or leading? (§0). Picks your source table.
2. **Find the API** — open the persona component (§3), find the `apiCall(...)` for that widget. Or hit the MCP tool directly.
3. **Hit the endpoint** for the tenant and read the raw JSON field.
4. **Re-derive from source** — query the source table(s) and recompute by hand:
   - Health: pull `DC2SKPI` for the account, normalize per `kpi_definitions`, weight by `CustomerConfig.dc2s_kpi_weights` (L1→L2), then `dc2s_pillar_weights` (L2→L3). Classify via `health_thresholds.json`.
   - Revenue@risk: `Account.revenue × churn-prob(band)` for exposure; sum `ContextNode(OUTCOME).revenue_impact` (conf ≥ 0.5, 20% dedup) for confirmed.
   - Predictor: confirm a `PredictorCalibration` row exists for the `(customer, profile, sub_model)`; if not, inference is on cold-start/pooled — the number is a fallback, not a fit.
5. **Trace to the manifest** — `download_customer_csv` round-trips the tenant to CSV; compare against `load-driver/manifests/predictor_v3_demo_saas_cust336.json` lifecycle/outcomes. This catches generation-time errors.
6. **Cross-check parity** — CRO vs CFO revenue fields must match; portfolio NRR (Wizard B) vs Predictor v3 are *different questions* and may legitimately differ.

**Example curl (customer 336, server API key)**

```bash
export CS_PULSE_BASE_URL=http://3.94.106.197
export CSP_SERVER_API_KEY=<key>
curl -s -H "X-Customer-ID: 336" -H "Authorization: Bearer $CSP_SERVER_API_KEY" \
  "$CS_PULSE_BASE_URL/api/executive/cro-dashboard" | jq '{total_arr, revenue_at_risk, revenue_protected, expansion_pipeline}'
```

---

## 5. Running the evals

There are **three eval lanes** for dashboard KPI work (plus persona grading for Ask AI quality).

### Lane A — HTTP acceptance ($0, no LLM): presence + parity

`scripts/verify_executive_phases_ec2.py` (legacy per-suite modules: `scripts/ec2_acceptance/checks.py`).

```bash
cp scripts/.env.acceptance.example scripts/.env.acceptance   # edit host/creds/customer
export ACCEPTANCE_CUSTOMER_ID=336
python3 scripts/verify_executive_phases_ec2.py --suite cfo,cro,vpcs   # or: all
```

Asserts: **CRO/CFO context-graph $ parity**, CFO ROI scaling > 0, VP CS capacity-planning fields, renewals API, UI bundle markers. See `scripts/ec2_acceptance/README.md` for all env vars.

### Lane A½ — Number correctness ($0, no LLM): arithmetic re-derivation

`scripts/verify_dashboard_number_correctness_ec2.py` → `scripts/ec2_acceptance/number_correctness.py`

Independently re-derives portfolio aggregates from `GET /api/v1/accounts` and asserts dashboard endpoints return the **arithmetically correct** value (not just present / matching each other).

```bash
export ACCEPTANCE_CUSTOMER_ID=336
python3 scripts/verify_dashboard_number_correctness_ec2.py
python3 scripts/verify_dashboard_number_correctness_ec2.py --predictor --predictor-limit 30
```

**Use this when:** you need proof that `average_health`, `arr_exposure`, and CRO/CFO `revenue_*` match hand recomputation from account primitives.

> Not wired into `run_acceptance_ec2.sh` by default — run explicitly after Lane A or before sign-off.

### Lane B — Persona grading (LLM-as-judge, ~$3–5/run): Ask AI answer quality

`kpi-dashboard/backend/tests/persona_grading/runner.py` — Claude Sonnet grader role-playing a veteran of each persona. 5 personas × 5–7 rubric questions.

```bash
docker exec -e ANTHROPIC_API_KEY=sk-ant-... cspulse-platform \
  python3 -m tests.persona_grading.runner \
    --customer 336 --shots 3 --personas cro,cfo,vpcs,csm \
    --output /app/backend/scripts/datasets/persona_grades_336_$(date +%Y%m%d).json
```

Grades A–F on a 4.0 scale with `must_cite_check`, `must_call_tools_check`, `tone_pass`, `anti_hallucination_pass`. **Use `--shots 3`** — single-shot variance is high (±0.3–0.9 grade-pts).

**Note:** Lane B validates **Ask AI prose quality**, not whether dashboard tiles match DB math.

### Orchestrated (Lane A + optional B + gate)

```bash
cp scripts/.env.acceptance.example scripts/.env.acceptance
ACCEPTANCE_CUSTOMER_ID=336 ACCEPTANCE_RUN_PERSONA=1 ACCEPTANCE_PERSONA_SHOTS=3 \
ACCEPTANCE_MIN_GRADE_NUMERIC=3.3 ./scripts/run_acceptance_ec2.sh
```

Gate: every persona's `avg_numeric ≥ MIN_GRADE` or exit 1. Historical bar from session logs: **persona ≥ 14/20 equiv (~B)**.

### Snapshot diff (regression of actual numbers)

```bash
python3 scripts/sanity_check_cust333.py before.json   # template works for any tenant if adapted
# ...deploy / refit...
python3 scripts/sanity_check_cust333.py after.json
diff <(jq -S . before.json) <(jq -S . after.json)
```

For **336 specifically**, prefer `scripts/spot_check_cust336.py` as the fast before/after smoke.

### Seed-data quality (offline, generator regression)

```bash
pytest load-driver/tests/test_seed_data_quality.py -q
```

**15 offline tests** asserting generator output is clean (no DC vocab in SaaS, sentiment bounds, no churn contradiction, no duplicate revenue, P4 present, `kpi_name` populated, classification↔health-band agreement, `stakeholder_name` populated, referential integrity). Run **before** trusting any tenant a new manifest produced.

---

## 6. Persona robustness testing

"Robustness" = the persona gives a consistent, correct answer regardless of phrasing and across repeated runs.

- **Cross-run stability:** the `--shots N` mechanism measures it — read `shot_stats.stddev` per question. `stddev ≤ 0.3` = stable; `≥ 0.9` = flaky question/data source.
- **Phrasing robustness (gap, see §7):** no harness yet that asks the same question 3–5 ways and checks grade stability. Do manually via paraphrased fixtures until one exists.
- **Tool-dispatch robustness:** every persona answer records `raw_tool_calls`. A robust answer calls the *right* tool (CRO revenue-at-risk → `get_portfolio_revenue_breakdown` or `get_revenue_at_risk`, not bare `list_accounts`). Watch for personas that pass on text but fail `must_call_tools_check`.

---

## 7. Known gaps to flag

### Data / lineage gaps

1. **DC playbook IDs leak into SaaS causal graph.** `causal_chain_ref` on critical/churn accounts may still show `PB-DC-01/PB-DC-02` for SaaS tenants. Source: playbook layer hardcodes `PB-DC-*`. Surfaces in CRO/CFO causal drill-down. **Open** — verify on 336 after each vertical-routing fix.
2. **`stakeholder_name` in export** — generator now populates per-signal stakeholders for cust336; older tenants may still have blanks. Guard: `test_signal_stakeholder_name_populated`.
3. **Manifest classification ↔ health-band drift** (fixed for 336): guarded by `test_manifest_classification_matches_health_band`.
4. **`content_map` vertical leak** (fixed for 336): guarded by `test_saas_freetext_has_no_datacenter_terms`.
5. **`download_customer_csv` was lossy** (fixed): re-verify after any export refactor.
6. **Manifest ARR vs live ARR drift** — lifecycle events (expand/churn) adjust account ARR post-ingest; expect $200M design → ~$175M live on 336.

### Eval-harness gaps

7. **Lane A does not replace Lane A½** — presence/parity ≠ arithmetic correctness. Run `verify_dashboard_number_correctness_ec2.py` for derivation proof.
8. **No phrasing-robustness harness** (see §6).
9. **Lane B ≠ dashboard KPI validation** — grades Ask AI answers, not tile math.
10. **Single-shot variance** up to ±0.9 grade-pts — always `--shots ≥ 3`.
11. **Local DB schema drift** vs `models.py` — run evals against fresh EC2/clean image.

### Recently fixed (remove from your mental "open" list)

- **CSM persona prompt** — `ask_ai_endpoint.py` now includes dedicated `'csm'` in `PERSONA_PROMPTS` (no longer falls back to VPCS at runtime).
- **Onboarding activation plan 404** — `process_data` now calls `run_onboarding_agent_analyze()` (LLM if entitled, else rule-based fallback) so `GET /activation-plan` has data after first ingest.

---

## 8. Quick reference

**Personas → primary API → component**

| Persona | API | Component |
|---|---|---|
| CSM | `/api/v1/accounts`, `/api/v1/daily-actions` | `csm/CSMCockpit.tsx` |
| VP CS | `/api/v1/health-summary`, `/csm-scorecard`, `/team-capacity` | `dashboard/VPCSDashboard.tsx` |
| CRO | `/api/executive/cro-dashboard` | `dashboard/CRODashboard.tsx` |
| CFO | `/api/executive/cfo-dashboard` | `dashboard/CFODashboard.tsx` |
| NRR forecast tile | `/api/v1/predictor/...` | Predictor v3 tile in CRO/CFO dashboards |

**Source tables**

`Account` · `DC2SKPI` · `HealthScore` · `PillarScore` · `PlaybookExecutionV2` · `ContextNode`/`ContextEdge` · `PredictorCalibration` · `CustomerConfig` · `ROISnapshot`

**Health thresholds** (`config/health_thresholds.json`, never hardcode): healthy ≥ 70 · at-risk 50–69 · critical < 50.

**Reference tenants**

| ID | Role |
|---|---|
| 331 | Slide-deck reference |
| 334 | Canonical eval tenant (VPCS demo seed) |
| **336** | **Primary KPI validation tenant — SaaS Premium, Predictor v3 fully calibrated** |
| 333–335 | Predictor V3 Verify line |

**Eval commands**

| Goal | Command |
|---|---|
| Fast smoke (336) | `ACCEPTANCE_CUSTOMER_ID=336 python3 scripts/spot_check_cust336.py` |
| Dashboard numbers (HTTP) | `python3 scripts/verify_executive_phases_ec2.py --suite all` |
| Number correctness | `python3 scripts/verify_dashboard_number_correctness_ec2.py` |
| Persona quality (LLM) | `python3 -m tests.persona_grading.runner --customer 336 --shots 3 --personas cro,cfo,vpcs,csm` |
| Both + gate | `ACCEPTANCE_RUN_PERSONA=1 ACCEPTANCE_PERSONA_SHOTS=3 ./scripts/run_acceptance_ec2.sh` |
| Seed-data quality | `pytest load-driver/tests/test_seed_data_quality.py -q` |
| **Repo / pipeline map** | **§3g** + **`EC2_RUNTIME_ACCESS.md`** |
| Runtime explorer (SSH) | `sudo docker exec -e CUSTOMER_ID=336 cspulse-platform python3 /app/backend/scripts/runtime_explorer.py map` |
| Sync kit to EC2 (operators) | `./scripts/sync_ec2_runtime_kit.sh` |
