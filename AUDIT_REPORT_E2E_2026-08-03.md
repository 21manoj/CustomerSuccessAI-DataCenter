# CS Pulse — End-to-End Codebase Audit

**Date:** August 3, 2026 (overnight audit)
**Scope:** Full repo — dead/junk code, duplicated code paths, and end-to-end verification of the customer journey (registration → onboarding → data processing → scoring → wizards → predictions → dashboards).
**Method:** Four parallel investigation agents (dead code / duplicated paths / journey trace / frontend+load-driver) plus three deep-scan sub-agents. All findings carry file:line citations verified against the working tree at commit `868479ed2` on `main`.

## 1. Executive Summary

**The customer journey works end-to-end, but almost every safety net around it is missing, silent, or lying.** No stage of registration → upload → processing → scoring → prediction → dashboards is broken outright; the canonical 4-CSV path flows. But all 6 stages are COVERED-WITH-GAPS, and the failure modes are uniformly *silent*: upload validation doesn't exist (phantom import), every pipeline stage swallows its own failures while reporting success, prediction honesty labels overstate calibration, and multiple "fallback" paths render fabricated data instead of errors.

**Headline numbers:**
- **19 critical findings (C-1..C-19)** where the product gives wrong, contradictory, or fabricated answers today — including 2 registered API blueprints that 500 on every call (self-recursion bug), the SaaS Premium API broken since March by an import of a function that never existed, and a regression interaction from tonight's own WizardRun fix.
- **~9,000+ lines of verified-dead backend Python** (4 abandoned RAG generations, a dead celery wizard chain, 17 orphaned root modules), plus ~16 orphaned frontend components including a full duplicate test-runner and the pre-consolidation chatbot.
- **Duplication is the dominant disease:** 3 arc vocabularies, 4-5 account-health read paths over 2 parallel score stores, 4 competing churn-probability models, 2 drifted NRR waterfall implementations (different dollar answers UI vs Claude.ai), 4 divergent sentiment maps (one sign-flips `very_negative` to positive), ~150 hardcoded health-threshold sites (several with *different* boundaries — the same score renders healthy in one component and at-risk in another), 24 duplicate currency formatters, 60 on-disk copies of the Wizard B analyzer.
- **The existing drift-audit tooling reports "clean" while all of this exists** — it parses a 9-file allowlist and can't read `jsonify()` returns. Fixing the auditor is the single highest-leverage change in this report.
- **~230MB of removable git-tracked bloat** (an unrelated 89MB project, 113MB of synthetic tenant data, a 10.5MB committed log) + 7.7GB of stale worktrees on disk.
- **Positive findings worth naming:** `_process_data_impl` and `_upload_csv_impl` are genuinely shared Flask+MCP paths; revenue-at-risk, portfolio breakdown, Power-of-1, playbook lifecycle, Predictor v3 inference, and magic-link auth are properly factored; the primary Ask AI path correctly delegates to MCP implementations; and no large commented-out code blocks exist anywhere.

---

## 2. Critical Findings (P0/P1 — fix before next customer-facing milestone)

These are the findings where the platform gives **wrong or contradictory answers to users today**, or where a silent failure is already live.

| # | Finding | Where | Impact |
|---|---|---|---|
| C-1 | **Upload validation is a no-op.** `utils/csv_upload.py:274-286` imports `utils/csv_validator.py`, **which does not exist** — the ImportError is swallowed. Only header-presence and non-empty checks run. Three validator functions in `onboarding_api_v2_config_aware.py` (`validate_kpi_csv_schema:454`, `validate_kpi_values_against_ranges:516`, `validate_account_ids_in_file:246`) are defined but never called. Flask upload passes `strict_validation=False` (`:2564`) so even missing required columns are accepted with warnings. | Upload layer | The documented shift-left Layer-1 validation doesn't exist. Garbage KPI values flow into scoring with no error anywhere. |
| C-2 | **Journey Intelligence forecast reads the wrong WizardRun** — `journey_intelligence_api.py:315-321` takes the latest WizardRun with non-null results *without filtering on wizard type*. Since commit `cce93f7c4` (tonight's `record_wizard_run` fix), every `process_data` run writes a newer completed row with results but no `nrr_intelligence` key — shadowing any real Wizard B run. | `journey_intelligence_api.py` | Forecast lines go empty/identical again after every data refresh, even for tenants where Wizard B ran. **Regression interaction with tonight's fix — needs a `config->>'wizard'` filter.** |
| C-3 | **Unpinned password hashes at 6 live user-creation sites.** The scrypt-overflow bug fixed tonight in `registration_api.py` (pinned `pbkdf2:sha256`) is still live at: `contractor_access_api.py:141`, `admin_ui_api.py:288`, `admin_ui_api.py:677`, `onboarding_api_v2_config_aware.py:1915`, `mcp_server/cs_pulse_onboarding.py:617` (create_customer), `:2975` (clone_customer). `users.password_hash` is `VARCHAR(128)` (`models.py:160`); scrypt hashes overflow it. | Auth | Any environment resolving to scrypt-default Werkzeug silently bricks login for users created via admin UI, contractor flow, MCP create/clone. Failure surfaces only at login time. |
| C-4 | **UI and Claude.ai give contradictory answers to "what should I do today?"** — CSM daily actions has two independent ~500-line implementations: Flask `verticals/dc2_s/api_routes.py:2175` (max 1 action/account, includes `PlaybookTask` system-urgent tasks, DC2S-hardcoded playbook config) vs MCP `cs_pulse_admin.py:456` (max 2-3 actions/account, different priority weights `0.7/0.3` at `:843` vs `0.6/0.4`, no system tasks, vertical-aware). | CSM surface | System-generated urgent tasks from signal_analyst are invisible in Claude.ai; same tenant same day gets different action lists per surface. |
| C-5 | **UI signal submissions earn zero CSM credit.** MCP `submit_signal` (`cs_pulse_intelligence.py:355-374`) writes an ActivityLogger entry; Flask signal-ingest (`signal_engine/ingest_api.py`) writes nothing. `get_csm_scorecard.actions_taken` counts ActivityLog rows (`cs_pulse_admin.py:1281-1286`), and `get_csm_ranking` weights 40% on `accounts_rescued`. | Signal engine | CSM performance metrics are silently corrupted: only Claude.ai-submitted signals count. Also opposite feature-toggle behavior: MCP auto-enables `signal_engine`; Flask rejects when disabled. |
| C-6 | **Every process_data stage failure is swallowed.** All 9 post-processing stages in `mcp_server/process_data_pipeline.py` catch their own exceptions; `status='partial'` only fires for CSV/context-graph loader errors. A run where health-scores AND Wizard A both fail still returns `status='success'`. If `DATABASE_URL` is unset, health scores are computed and silently never written (`process_data_pipeline.py:174-175`). | Pipeline | Operators cannot distinguish a healthy run from a degraded one. No alerting hook exists. |
| C-7 | **`prediction_method='calibrated'` on prior-fallback fits.** `predictor/inference.py:345-348`: only `fit_type=='cdi_seed'` maps to `cold_start`; `fallback_to_prior` fits (insufficient events — the common case for small tenants) report as `calibrated`. | Predictor v3 | Dashboards and AI-DD reviewers are told a tenant-specific model exists when it's the generic prior. Trust/honesty issue on the headline NRR number. |
| C-8 | **`skip_wizard_b` / `skip_wizard_c` / `strict_kpi_ranges` are silently ignored** — sent by load-driver (`client.py:437`, `scenario_manifest.py:4412`) but read nowhere in the Flask route or `_process_data_impl` (grep-verified). Wizard B actually auto-runs whenever ≥5 journeys exist. | API contract | The load-driver believes it controls behavior it doesn't; months of test results are mislabeled (tests thought Wizard B was skipped — it ran). |
| C-9 | **Load-driver sentiment fallback flips `very_negative` to +0.7.** `scenario_manifest.py:2244`: `auto_score_map.get(sentiment, 0.7)` — the map at `:2230-2233` is missing the `very_negative` key, so a very-negative recovery signal gets scored **positive**. | Seed data | Live sign-flip bug in generated data; also 4 divergent sentiment maps across the repo (see §4). |
| C-10 | **21 MCP tools have no auth check** — including write paths: `trigger_wizard`, `upload_csv`, `process_data`, `create_customer`, `execute_playbook`, `close_playbook`, `get_portfolio_cross_customer_comparison` (`customer_id` is caller-supplied). Tenant isolation rests entirely on `_check_mcp_enabled()`. | MCP security | Aligns with the existing MCP-security backlog item — now with a concrete tool list. |
| C-11 | **Probable live `TypeError`:** `llm/context_helpers.py:139` calls `get_revenue_at_risk(customer_id, account_id)` with two positional args; every other caller passes one. | LLM context | Whichever LLM path hits this line throws — needs a runtime check. |
| C-12 | **Two REGISTERED blueprints 500 on every call** — `analytics_api.py:21-29` and `cache_api.py:15-23` import `get_current_customer_id` from `auth_middleware`, then redefine a same-named local function whose first statement calls itself → guaranteed `RecursionError`. Both blueprints are registered (`app_v3_minimal.py:401,403`); 13+1 routes affected. Nothing calls them today, which is why nobody noticed. Same bug in `enhanced_rag_historical_api.py:16`. | `/api/analytics/*`, `/api/cache/*` | Every endpoint in both blueprints is a guaranteed 500. Repro-confirmed. |
| C-13 | **SaaS Premium API permanently broken since March** — `verticals/saas_premium/api_routes.py:24` imports `get_catalog` from `utils/vertical_registry`, a function that has **never existed in any revision** (git-verified). The try/except at `app_v3_minimal.py:1486` makes it look like a conditional skip; it's a permanent defect. All `/api/saas/*` routes unreachable. | SaaS vertical | The startup warning seen every boot is a defect, not a dependency skip. |
| C-14 | **Load-driver Docker path is entirely broken** — `load-driver/Dockerfile:43` `ENTRYPOINT ["python","-u","driver.py"]` but `driver.py` no longer exists (renamed to `cs_pulse_driver.py` ~Mar 21). `docker-compose.loaddriver.yml` + `docker-compose.ec2-loaddriver.yml` inherit the broken entrypoint; `docker-compose.loaddriver-standalone.yml` is a `services:{}` tombstone that **two docs still instruct users to run** (`docs/ARCHITECTURE_CONTAINERS.md:45-66`, `docs/V6_DEPLOYMENT_CONFIRMATIONS.md:11`). | Deployment | Any containerized load-driver run fails at start; documented commands silently no-op. |
| C-15 | **CSM mock data renders on *empty* API responses, not just errors** — `CSMFocusFlow.tsx:350` / `CSMCockpit.tsx:1046`: `setActions(list.length > 0 ? list : MOCK_ACTIONS)`. A real customer with a legitimately empty portfolio sees 8 fabricated accounts ("Matterhorn AI Labs" etc.) with fake ARR up to $8.5M presented as real. Survived the March fallback cleanup. | CSM UI | Fabricated business data shown to real users under normal (empty-state) conditions. |
| C-16 | **Wizard B reports `total_warnings: 0` as if computed** — `identify_early_warnings()` (`wizard_b_pattern_analyzer.py:399`) and `extract_success_factors()` (`:457`) both filter on pattern_type values (`ignored_churn`/`churn`, `proactive_growth`/`expansion`) that Wizard A's classifier never emits. Both branches have never executed for any customer; consumers receive always-zero counts presented as analysis output. | Wizard B | Extends tonight's memory finding — success-factor extraction is dead too, not just early warnings. |
| C-17 | **ARR resolution has opposite precedence in two live copies** — `mcp_server/common.py:123-130` prefers `profile_metadata['arr']` then `account.revenue`; `utils/context_graph.py:341-345` prefers `account.revenue` then `profile_metadata['arr']` — reversed. Ask AI fallback uses `revenue` only. | Revenue math | Any account where the two fields differ shows different ARR (and revenue-at-risk denominators) per surface. |
| C-18 | **Cross-tenant data read** — `health_score_storage.py:261 get_account_health_trends` has no `customer_id` filter and `time_series_api.py:44` trusts a raw `account_id` query param. | Security | A valid session can read health trends for another tenant's account_id. Needs verification + fix. |
| C-19 | **Flask accounts list uses `health_score == 50.0` as a "no data" sentinel** (`kpi_api.py:151`) — `calculate_health_score_proxy` returns exactly 50.0 for missing data, and the recompute trigger fires on `score == 50.0`. | Accounts API | An account legitimately scoring exactly 50 is treated as missing data and recomputed; missing-data defaults also differ per surface (50.0 Flask / 0 Ask-AI-fallback / computed MCP). |

---

## 3. Customer Journey Verification (registration → predictions)

**Overall verdict: no stage is BROKEN end-to-end.** The canonical 4-CSV happy path flows registration → upload → scores → Wizard A/B → dashboards. But **every stage is COVERED-WITH-GAPS**, and the degraded paths are all silent.

| Stage | Verdict | Key gaps |
|---|---|---|
| 1. Registration (`registration_api.py:33-249`) | COVERED-WITH-GAPS | Creates Customer/User/CustomerConfig/PlaybookTriggers/API-key + auto-login. No verticals dir (lazy-created on first upload) and no FeatureToggle rows — diverges from MCP `create_customer` which does both. CustomerConfig gets legacy text pillar names, no `vertical` set. 6 unpinned password-hash sites (C-3). |
| 2. CSV Upload (`utils/csv_upload.py:194-334`, shared by Flask + MCP) | COVERED-WITH-GAPS | Validation no-op (C-1). Unknown file types rejected cleanly; unknown columns warn-and-ignore. Disk mode **appends** on re-upload (`:379-385`) → duplicate rows, dedup only partial at process time. |
| 3. process_data (`_process_data_impl`, `cs_pulse_onboarding.py:1078-2206`) | COVERED-WITH-GAPS | Single source of truth for both Flask+MCP ✅. All stage failures swallowed (C-6). Wizard A auto-runs ✅. Wizard B auto-runs if ≥5 journeys (silently absent below that; `skip_wizard_b` ignored — C-8). Wizard C decoupled per policy ✅. **Wizard D absent from pipeline** — only `admin_api.py:1056` + load-driver post-load call; UI-onboarded customers never get predictor calibration. `trigger_wizard('d')` branch unreachable (validation rejects 'd' at `cs_pulse_onboarding.py:2272` before the fully-written branch at `:2320-2335`). |
| 4. Scoring | COVERED-WITH-GAPS | **Two scoring stacks with different weight resolution**: pipeline uses `utils/generic_scorer.py` reading only `CustomerConfig.dc2s_pillar_weights` + catalog `weight_l1`; the `bootstrap_weights_config.json` tier and `dc2s_kpi_weights` are consulted only by `ScoreCalculator` (used by `dc2s_scores_api.py`, not the pipeline). PillarScore/KPIScore/HealthTrend tables populated only by the ScoreCalculator path — dashboards fall back to `contributing_pillars` JSON. L4 computed read-time, never persisted. SaaS→DC2S fallback **resolved** (generic scorer is vertical-aware) — but the last-resort noop scorer returns 0.0 silently (`cs_pulse_mcp_server.py:289-292`): a catalog load failure flips a whole tenant to critical with only a log line. |
| 5. Predictions | COVERED-WITH-GAPS | Chain verified (build_panel → engineer_features → inference). Calibration hierarchy: per-tenant → pooled → CDI seed. `prediction_method` honesty gap (C-7). Wizard B consumer 1: CRO dashboard runs `run_wizard_b()` **synchronously on every page load** (`executive_dashboard_api.py:791`), exception swallowed. Consumer 2: Journey Intelligence reads stored WizardRun — wrong-row bug (C-2). |
| 6. Dashboards (all 5 personas) | COVERED-WITH-GAPS | CRO/CFO/CEO trace to real pipeline outputs with labeled fallbacks (`is_estimated`, `nrr_projection_lens`). CFO fresh-tenant shows modeled Power-of-1 numbers (labeled). VP CS capacity/scorecard depend on `profile_metadata.assigned_csm` — accounts silently bucket to "Unassigned" without CSM columns. CSM surfaces read real data (but see C-4 for MCP divergence). |

### Ranked silent-degradation list (customer-visible impact order)

1. No value/type/range validation at upload (C-1)
2. Journey Intelligence forecast reads wrong WizardRun (C-2)
3. `calibrated` label on prior fallbacks (C-7)
4. Wizard D never runs for UI-onboarded customers + dead `trigger_wizard('d')` branch
5. Unpinned password hashes ×6 (C-3)
6. Ignored `skip_wizard_*` request params (C-8)
7. All pipeline stage failures swallowed (C-6)
8. <5-account tenants silently never get Wizard B
9. `DATABASE_URL` unset → scores computed but never written, run still "success"
10. Qdrant absent → semantic signal search silently off (debug-level log only)
11. Noop scorer returns 0.0 for catalog-load failure → whole tenant flips critical
12. Disk-append upload semantics duplicate rows on re-upload

---

## 4. Duplicated Code Paths — Backend Business Logic

Legend: **DRIFTED** = copies already behave differently today. **AT-RISK** = identical today, no shared function keeping them so.

### 4.1 NRR / revenue math

| Finding | Copies | Status |
|---|---|---|
| Health→NRR heuristic ladder `100 + (h-70)*0.33` | 4: `executive_dashboard_api.py:826` (CRO tier-3 fallback), `:1730` (CEO — **primary**, no predictor/wizard-B chain), `ask_ai_endpoint.py:351`, `ask_ai_tools.py:1108` | AT-RISK arithmetic; **DRIFTED precedence** — CEO and CRO report different NRR for the same tenant whenever Predictor v3 or Wizard B has data |
| Predictor v3 portfolio NRR | 2: `executive_dashboard_api.py:587` vs `mcp_server/cs_pulse_predictor.py:179` | DRIFTED — different horizon handling, units (pct-2dp vs fraction-4dp), key names, account filtering |
| NRR trajectory + revenue waterfall | 2: `executive_dashboard_api.py:864-955` vs `cs_pulse_revenue.py:1231-1352` | **DRIFTED ×3**: (a) churn model — shared `health_to_annual_churn_prob` vs inline `max(5, 50-h*0.5)`; (b) decay — from tenant's actual NRR ×0.6 vs from literal 100 ×0.61; (c) intervention cost — flat $4,560 vs 0.3% of ARR. Same tenant gets two different waterfall ROIs depending on UI vs MCP |
| NRR-forecast retrieval (cache→live) | 2: `revenue_intelligence_api.py:504` vs `cs_pulse_revenue.py:1162` | DRIFTED — MCP adds ~220 lines of enrichment (trajectory/waterfall/renewals) REST never gets; both have a dead `months` parameter |
| CFO `arr_at_risk` vs MCP `total_arr_at_risk` | `executive_dashboard_api.py:1288-1302` vs `cs_pulse_mcp_server.py:847-887` | DRIFTED — CFO copy has **no churned-account exclusion**, double-counting churned ARR; violates the invariant documented in `tests/test_context_graph_invariants.py:631` |
| Health→churn probability | 4 competing models: `utils/playbook_lifecycle.py:28` (canonical piecewise), `utils/context_graph.py:356` (3-band flat), `cs_pulse_revenue.py:1299` (linear), `agents/signal_analyst_api.py:634` (3-band, different values) | DRIFTED — at health=45: 38.5% / 40% / 27.5% / **80%**. CRO dashboard tooltip (`CRODashboard.tsx:600,624,648`) documents the retired formula |
| Renewal probability | Single formula `outcome_roi_engine.py:1024` + separate 3-bucket table `cs_pulse_admin.py:138` | Two unrelated formulas for the same concept, no shared constant |

**Properly shared (no action):** revenue-at-risk via `utils/context_graph.get_revenue_at_risk` (~20 call sites), portfolio breakdown via `utils/portfolio_revenue_breakdown` (with parity test), CRO/CFO/CEO MCP tools via `fetch_executive_dashboard` (invokes Flask views in-process), CSV upload via `_upload_csv_impl`, process_data via `_process_data_impl`, Power-of-1, playbook lifecycle, Predictor v3 inference, magic-link auth.

### 4.2 Flask ↔ MCP drift (same feature, independent code)

| Finding | Flask | MCP | Drift |
|---|---|---|---|
| CSM daily actions (C-4) | `verticals/dc2_s/api_routes.py:2175` | `cs_pulse_admin.py:456` | Dedupe rules, data sources, priority weights all differ |
| CSM scorecard | `api_routes.py:2570` | `cs_pulse_admin.py:1200` | MCP has `accounts_rescued`/`accounts_lost`/`actions_taken`; Flask has delta only. Ranking weights 40% on a metric the UI can't show |
| Health score history | `api_routes.py:3017` | `cs_pulse_intelligence.py:932` | 130-line near-verbatim copy; summary math diverges (ARR-weighted momentum vs counts); ARR typed string vs float |
| Playbook success metrics | `outcome_roi_api.py:1851` + `api_routes.py:2941` | `cs_pulse_revenue.py:441` | **Three copies, three ROI conventions** (pct-1dp / multiple-x / none). Route collision: `/api/v1/playbook-success-metrics` registered twice — `api_v1_routes.py` dispatch is dead code |
| Renewals at risk | `api_routes.py:2851` (config thresholds, 4 levels, excludes overdue) | `cs_pulse_revenue.py:1355-1383` (hardcoded 50/70, includes overdue) | MCP ignores tenant-configured health thresholds |
| Signal submission (C-5) | `signal_engine/ingest_api.py:67` | `cs_pulse_intelligence.py:236` | Audit trail MCP-only; opposite feature-toggle behavior; Flask keeps participants + caller timestamp, MCP drops both |
| Integrations ×3 | `integration_api.py:951/1019/132` | `cs_pulse_integrations.py:136/208/48` | Health summary shape differs; sync-logs byte-identical (AT-RISK); connector ordering differs |
| Wizard B trigger | `data_management_api.py:130` imports `wizard_b_pattern_analyzer` (template) | `cs_pulse_onboarding.py:2301` imports `wizards.wizard_b_pattern_db` | **Two different Wizard B modules with different WizardRun/result conventions**; Flask wizard routes write no WizardRun/ActivityLog audit trail at all |
| `get_precalculated_scores` | 4 copies: `utils/vertical_health.py:202`, `mcp_server/common.py:179`, `cs_pulse_mcp_server.py:206`, `verticals/dc2_s/api_routes.py:180` | — | **Arity fork**: Flask copy returns 4-tuple, others 3-tuple — code moved between layers raises ValueError |

**Why the existing drift audit missed all of this:** `scripts/audit_flask_mcp_drift.py` (a) only parses a 9-file allowlist — `integration_api.py`, `revenue_intelligence_api.py`, `signal_engine/`, `data_management_api.py`, `admin_api.py` are structurally invisible; (b) its return-key comparison only reads `return {...}` literals — every Flask `return jsonify({...})` sets `return_unknown=True` and skips the diff. The audit "passes clean" while all of the above exists.

### 4.3 Health-threshold bypasses (policy: never hardcode 70/50)

- **Backend:** 4 duplicated `classify()` function copies (`context_graph_regen_subscriber.py:34`, `utils/playbook_lifecycle.py:139`, `scripts/simulate_incremental_kpi.py:130`, `scripts/generate_context_graph_data.py:95` — three claim in comments/docstrings to use the centralized config while hardcoding); ~30 inline comparison sites; **DRIFTED**: `verticals/dc2_s/__init__.py:189` uses healthy≥**75** and label `"risk"` instead of `at_risk`.
- **Hardcoded in LLM prompt text** (`cs_pulse_mcp_server.py:401,649,762`, `agents/prompts.py:194`, `ask_ai_endpoint.py:287`) — will contradict config if thresholds change in Settings.
- **load-driver:** 4 more copies; `scenario_manifest.py:1614` emits `'risk'` vs `:3363` emitting `'at_risk'` — same file, two conventions.
- **Frontend:** see §6.

### 4.4 Sentiment maps

4 divergent copies: `excel_import_service.py:599` (positive=0.5, neutral=0.0, negative=−0.5) vs `scenario_manifest.py:2064` (0.7/0.1/−0.6) vs `:2230` (missing `very_negative` — C-9 sign-flip) vs `simulation/data_generator.py:200` (±0.7/0.0). Plus an inverse mapping at `scripts/generate_context_graph_data.py:420` with ±0.3 cutoffs inconsistent with all producers.

### 4.5 Per-tenant vertical trees

`backend/verticals/` holds **47 `customer<N>-*` directories** — full clones of `verticals/_template/` (~2,000 files). Sampled `customer20-dc2_s`: 31 files byte-identical to template, **12 already drifted** (including `wizard_b_pattern_analyzer.py`). Template fixes don't reach clones. Additionally `wizard_b_pattern_analyzer.py` exists **twice inside `_template` itself** (`journey/wizard_b/` 1632 lines vs `journey/wizard_a/` 564-line stale fork — import-shadowable since both define the same module name on sys.path).

### 4.6 API-key hashing

`utils/api_token_auth.py:32-35` reimplements `api_key_service.validate_api_key` (same prefix slice, same hash) instead of calling it — kept in sync only by a comment.

### 4.7 Consolidation-pass additions (final cross-check)

- **Account health — still 4-5 read paths over TWO parallel persistence stores** (known Open Decision #22 — NOT converged): `HealthTrend` (written by rollup subscriber/storage/trend API/rehydration) vs `HealthScore`/`PillarScore` (written by score_calculator/MCP onboarding/admin). Readers: MCP `get_account_health` (HealthScore, pillar rows month-pinned), Flask `/api/accounts` (`kpi_api.py:96-170`, HealthTrend → 50.0-proxy → recompute), Ask AI `_execute_direct` fallback (`ask_ai_tools.py:596-620`, HealthScore, default **0**, pillars NOT month-pinned, no churned exclusion), `health_trend_api.py:255` + trigger evaluators (HealthTrend direct), `time_series_api.py:44` (HealthTrend, no tenant filter — C-18). Primary Ask AI path properly delegates to MCP; the fallback covers only 22/26 tools (missing `analyze_root_cause`, `explain_kpi_anomaly`, `generate_action_plan`, `get_calibration_history`).
- **Tool-registry counts (current):** Ask AI `TOOL_DEFINITIONS` = **26** (all dispatch via `_execute_via_mcp` — properly shared on the primary path); MCP `@mcp.tool` = **71**; **45 MCP tools have no in-product Ask AI surface**. The auto-derivation backlog item stands.
- **CSV validation parity claim is false:** MCP `validate_csv` uses `_upload_csv_impl(dry_run=True)`; Flask `POST /api/onboarding/validate-csv` (`onboarding_api_v2_config_aware.py:2619`) calls a different validator (`validate_csv_against_config:325`) with a different response shape — despite the MCP docstring claiming they're the same path. A CSV can pass UI pre-validation and fail MCP upload, or vice versa.
- **WizardRun creation — 4 creators, 3 conventions:** MCP `trigger_wizard` (two-phase, `config['wizard']`), `record_wizard_run` (one-shot, `config['wizard']`), template `save_to_database` (**`config['type']`** — different key, results without `nrr_intelligence`), legacy `wizard_blueprint.py:193` (no `customer_id`). **Admin recalibrate routes (`admin_api.py` wizard-c/wizard-d) create no WizardRun rows at all** — admin-triggered recalibrations are invisible to the wizard audit trail (governance gap). A dead duplicate `class WizardRun` also exists in `wizard_models.py:18`.
- **`wizard_b_pattern_analyzer.py` exists in 60 on-disk copies** (4 generations: 1632/692/564/481 lines). Only the `_template/journey/wizard_b/` copy is live, but all 5 importers use bare-module-name `sys.path.insert` injection — whichever directory is injected first wins for the whole process (`run_wizard_a_customer56.py:11` already injects a dir containing a stale copy). Make it a real package module.
- **Arc vocabulary gap quantified:** ~23 load-driver `story_arc` labels (e.g. `budget_cut`, `engagement_drop`, `growth_trajectory`) have no canonical-arc counterpart; needs an explicit `label → canonical_arc` mapping validated in CI.
- **May-17 Flask+MCP drift trio status:** #33 recommendations CONVERGED (shared function + comment); #30 team capacity fixed-by-copying — AT-RISK identical copy with magic multipliers duplicated (`cs_pulse_revenue.py:532` vs `api_routes.py:2651`, Flask comment admits "mirrors MCP"); B-1 guarded by `scripts/audit_account_column_access.py`.
- **KPI catalog copies** (backend `kpi_definitions.py`/JSON vs load-driver JSONs): separately maintained, no import relationship, field-level diff not performed — recommend a CI diff job.

---

## 5. Dead / Junk Code (Backend)

**Rough totals: ~9,000+ lines of verified-dead Python (P1+P2), ~11MB committed log/artifact junk, 125MB per-tenant data dirs, and 4 genuine defects where dead code misrepresents product behavior.** All grep/AST-verified; entry points `app_v3_minimal.py` + both MCP servers.

### P1 — dead code that actively misleads
1. **SaaS Premium API permanently broken** (C-13) — `verticals/saas_premium/api_routes.py:24` imports `get_catalog`, which never existed in any git revision. All `/api/saas/*` unreachable since March; startup message masquerades as a dependency skip. **Fix the import.**
2. **Infinite-recursion `get_current_customer_id` shadows** (C-12) — 6 files import the canonical function then redefine a same-named local that calls itself. Two are registered blueprints (analytics, cache → every route 500s); one conditional (enhanced_rag_historical); three orphaned RAG files. **2-line fix each or unregister.**
3. **Unreachable `trigger_wizard('d')` branch** — `cs_pulse_onboarding.py:2272` rejects 'd' before the fully-written branch at `:2320-2335`; `wizard_d_predictor_calibrator.py:9` docstring documents the broken path as working. **Add 'd' to the tuple (intent is clear) or delete the branch.**
4. **Wizard B dead analysis branches** (C-16) — `identify_early_warnings` + `extract_success_factors` never fire (vocabulary mismatch); `ADVANCED_CLUSTERING` imports KMeans/fastdtw, flag assigned and never read, fastdtw not even installed. **Fix vocabulary filters (the real feature gap), delete clustering block.**
5. **Dead upload validators** (C-1) — the three shift-left validation functions with zero callers.
6. **Startup "Skipped …" messages lie** — `app_v3_minimal.py:571,577,583` hardcode "(qdrant_client not available)" regardless of the real exception; qdrant-client has been in requirements-core since Mar 30, so if prod still shows the skip, something *else* is failing and the message masks it. The celery skip ("Wizard A blueprint") IS permanent — celery isn't in requirements at all.

### P2 — abandoned parallel implementations (delete ≈7,500+ lines)
- **Four abandoned RAG API generations** (~2,000+ lines): `rag_api.py`, `simple_rag_api.py`+system, `simple_working_rag_api.py`+system, `working_rag_api.py`, `enhanced_rag_system.py` — zero registrations, zero importers. Live RAG = direct_rag + enhanced_rag_openai + governance_rag + 3 conditional enhanced_*.
- **Legacy celery Wizard-A chain**: `wizard_blueprint.py` → `wizard_tasks.py` → `celery_app.py` → 5 subprocess generators in `_template/journey/wizard_a/`. Dead in production (no celery). Plus committed backups `wizard_tasks.py.backup2/3/4` (~56KB) and dead duplicate `wizard_models.py` (second `WizardRun` class, undefined `db`).
- **17 orphaned root modules** (~5,400 lines, zero importers incl. shell/Docker/string refs): `learning_api.py` (730), `vertical_config.py` (763), `continuous_learning.py` (458 — its feature toggle gates nothing), `api_manager.py`, `hot_reload_system.py`+`hot_reload_api.py` (738 — includes runtime code-writing), `signal_analyst_v2_openai.py`, `playbook_work_packages.py`, `config.py`, `journey_viz_api.py`, `customer_management_api.py`, `license_service.py`, `query_classifier.py`, `auth_decorators.py`, `simple_customer_api.py`, `rag_logging_utils.py`, `rag_templates.py`, `models_future_n8n.py`.
- **`signal_engine/fusion.py` unwired** (`fuse_scores`, `compute_pillar_modifiers` — zero importers) + dead `enrich_pending_signals` batch path. **Keep-with-comment** — overlaps the approved Recency-Signal-DNA spec; mark as "not yet wired; spec phase N" rather than delete.
- **13 dead functions >30 lines** (individually verified) — incl. three *unwired security decorators* (`require_api_key`, `require_api_token_or_session`, `require_webhook_signature`) that deserve a wire-in-vs-delete decision, since unwired security is its own kind of misleading.

### P3 — cruft
- **159 one-off scripts at backend root** (4× cleanup_customers variants, 5× load_dc2s variants, seed_v2/v3/v4, ~40 root test_*.py outside tests/). Archive.
- Committed runtime artifacts: `backend.log.1` (10.5MB), `backend.log` (526KB), `analyst.out`, `cookies.txt`, result JSONs, `.before_industry_fix` file, migration logs.
- Dead config: `config/context_graph_schema.json` (zero refs). **Do NOT delete** `taxonomy_*.json` / `healthcare_provider_kpi_catalog.json` — pattern-loaded via glob, alive.
- 52 `verticals/customer{id}-*` dirs (125MB) + empty husks in `verticals/_customers/`; `predictor/spike_d/` spike workspace.
- No commented-out code blocks >20 lines found anywhere (clean on that axis).

---

## 6. Frontend Findings

### 6.1 Health-threshold hardcoding (central utility: `src/utils/healthThresholds.ts`)

- **18 files** import the utility correctly.
- **~19 files** never import it and hardcode 70/50 classification (full local classifier copies in `AccountHealthHeatmap.tsx:43`, `TenantList_dc.tsx:41`, `HealthScore_dc.tsx:101`, `SignalAnalyst.tsx:60` — which exists as **two duplicate live component files** (`components/` + `components/shared/`), journey-visualizer files, others).
- **DRIFTED boundaries — same score classifies differently across live components:**
  - `HealthScoreCard.tsx:51` uses 80/60; `dc_TenantPlacard.tsx:96` uses 80/50 (and 70/50 elsewhere *in the same file*); `dc_InfrastructureHealth.tsx:207` and `dc_TenantKPIDetails.tsx:315` use 80/50; `dc_TenantHub.tsx:198` defines a local 80/50 classifier while importing and using `classify()` 40 lines later; `Dashboard_dc.tsx:163` uses 80/50 and at `:465` renders a 75-score **yellow** while the utility says healthy/green; `CSPlatform.tsx` contains **three different schemes** (80/50, 75/50, 80/60) across ~28 hardcoded sites.
- **Half-migrated (import + still hardcode):** `CRODashboard.tsx:899,1396,1527`, `CFODashboard.tsx:2333,2357`, `AESalesDashboard.tsx:656-690`, `NRRDashboard.tsx:194`, `CSMFocusFlow.tsx:441` (whose header comment claims "thresholds from centralized utils"), `AnalysisResultsPage.tsx:158` (label hardcoded, color from utility — can disagree if config changes).
- `dc_TenantKPIDetails.tsx:193` **fabricates a score** (85/60/40) when the API omits it.

### 6.2 Formatting helpers

No shared currency/number formatter exists. **24 local definitions across 22 files** — 5 byte-identical `formatCompact` copies in the 5 main dashboards, plus variants whose K-rounding differs (output disagrees on the same input), 4 `formatCurrency` copies, 4 B/M/K-tier copies, assorted one-offs. Percent formatters triplicated with inconsistent `+`-prefix behavior. ~50 additional raw `toLocaleString()` call sites.

### 6.3 API-fetch wrappers

9 distinct wrapper implementations; canonical `apiCall` (`src/utils/api.ts:24`) adopted by 29 files, but **~250 raw `fetch()` call sites bypass it**. `X-Customer-ID` hand-injected in 44 files/96 occurrences despite an exported helper. **P1:** `healthThresholds.ts:47` — the canonical threshold helper itself fetches without `credentials:'include'`, silently falling back to DEFAULTS when the session cookie is required. A third undocumented identity header (`X-User-ID`) used only in `CSPlatform.tsx`. 4 identical copies of the settings `apiUrl(path)` helper.

### 6.4 Mock/fallback data still shipping (P1 — fabricated business data)

- `csm/mockData.ts` (fake accounts w/ ARR) rendered by `CSMFocusFlow.tsx:350-393` and `CSMCockpit.tsx:1033-1072` on any fetch error.
- `ContextGraphSettings.tsx:102` — Data Status table **always** renders fake filenames/row counts (never fetches).
- `dc_InfrastructureHealth.tsx:64-123` — mock KPIs are the **sole** data source (TODO comment).
- `dashboard/ExecutiveDashboard.tsx:212` — `MOCK_TREND_DATA` always charted; `setTrendData` never called. (Note: this 1,427-line component is routed via `dc_Platform.tsx:55`; an unrelated 244-line `ExecutiveDashboard.tsx` is routed from `App.tsx` — duplicate-name trap.)
- `CSPlatform.tsx:901-919` — falls back to `Math.random()`-generated health trend charted as real; `:326` random health score fallback.
- `AESalesDashboard.tsx:672-736` — fabricated `products_used`, `days_to_renewal`, win-rate trend spliced into live payloads.
- P2: DC2S pillar-name fallbacks shown for wrong verticals (`CSMCockpit.tsx:456`, `CustomerDetailPage.tsx:691`).
- P3 dead mock constants: `VPCSDashboard.tsx:271` (~90 lines), `JourneyDashboardV3.tsx:134,220`, `ExecutiveDashboard.tsx:125-179`.

### 6.5 Orphaned components (zero importers, verified incl. React.lazy scan)

**P2 — plausible-looking duplicates of live code (delete):** `Login.tsx` (live one is `LoginComponent.tsx`), `dashboard/AskAnythingDialog.tsx` (491 lines — the pre-consolidation chatbot; AskAIPortal is mounted in all 6 persona dashboards, so Phase-4 consolidation is effectively done and this is the last remnant), `TenantDetails_dc.tsx`, the complete second test-runner (`test-runner/TestRunnerLayout.tsx` + `ConsoleTab.tsx`; live one is `dc/test-runner/DCTestRunner.tsx`), `settings/SettingsPage.tsx` (keep sibling `ApiKeysTab.tsx` — it IS used), the whole `charts/` directory (3 files).

**P3 (delete/adopt):** `ErrorBoundary.tsx` (app ships with no error boundary mounted — adopt or delete), `N8NWorkflowSettings.tsx`, `analysis/AnalysisResultsPage.tsx`, `csm/PlaybookCompletionForm.tsx`, `dashboard/AccountInfoPlacard.tsx`, `dashboard/AnalysisProgressModal.tsx`, `dataQuality/DataLineageViewer.tsx`, `journey-visualizer/QualitativeSignalsView.tsx`, `journey-visualizer/RCAEnhancedAnalysis.tsx`, `shared/FriendlyError.tsx` (ironic orphan given the March error-state cleanup).

### 6.6 Routing traps

- **Two ExecutiveDashboards, stale one routed:** `/executive-dashboard` (App.tsx:390) serves the 244-line stale `components/ExecutiveDashboard.tsx` (last touched June); the actively-maintained 1,427-line `components/dashboard/ExecutiveDashboard.tsx` is reachable only through DC-platform tabs (`dc_Platform.tsx:55`). The `dataQuality/` components are alive **only** through the stale one — a consolidation decision cascades.
- `Dashboard_dc.tsx` is legacy-only (`/dc-dashboard-legacy`) and is the sole thing keeping ~6 satellite components alive (`AlertBanner_dc`, `PlaybookPanel_dc`, `KPIChart_dc`, partially `HealthScore_dc`/`KPICard_dc`/`TenantList_dc`). Removing the legacy route releases them all.
- `src/lib/` is a 1,495-line mini-framework with exactly one consumer (`Playbooks.tsx`, using 3 exports); `PlaybookManager`, `usePlaybookExecution`, `PlaybookUtils/Validator/Renderer` are exported and never consumed. `lib/playbooks.ts` hardcoded template catalog = third playbook registry vs backend truth (known backlog).

---

## 7. Load-Driver, Scripts & Repo Hygiene

### 7.1 Scenarios & entry points
All 13 numbered legacy scenarios are **still reachable** via `cs_pulse_driver.py:333-343` → `_legacy_driver.py` (deprecated-but-live, not dead files; last touched March). Recommendation: keep `scenario_manifest.py` + `scenario_context_graph.py` (8) + `base.py`; move the rest + `_legacy_driver.py` behind an explicit legacy package. Delete `test_all_scenarios.py` (zero refs) and root `load_driver_phase1.py` (shell cheat-sheet with a hardcoded EC2 IP).

### 7.2 Manifests (36 tracked JSONs)
- **Keep (canonical/active):** `predictor_v3_demo_saas`, `slides_demo_saas_v2_deck_aligned`, `e2e_eval_saas`, `silent_churn_observation_test`, `novastar_dc2s`, `phoenix_4phase_*`, `granite_peak_dc2s`, `sandalwood_capital_dc2s`.
- **Byte-identical duplicate:** `slides_demo_saas.json` ≡ `slides_demo_saas_v1_10acct.json` (same md5) — delete the `_v1_10acct` copy (zero refs).
- **~10 stale zero-reference manifests** ≥4 months old (cascade_*, gainsight_saas_demo, gainsight_turnaround, hamilton_15, mount_diablo/pike, Mount-Everest) — archive. ~15 referenced-once manifests: confirm with demo owner before archiving.
- Deprecation tombstone advertises `mont_blanc_saas.json`, **which doesn't exist** — misleading doc pointer.

### 7.3 CSV generators & schema truth
Three current generator systems (`generate_synthetic_customer_data.py` — in-product path; `generate_context_graph_data.py` — context-graph; `ManifestCSVGenerator` — load-driver manifest mode). The retired Apr-2026 simulation engine (`simulation/`, `simulation_engine.py`, harness test) is still present — archive per policy. **`load-driver/csv_schemas.json` is dead AND drifted** (zero readers; backend copy now requires `arr`+`renewal_date` and adds signal enums the load-driver copy lacks) while `ManifestCSVGenerator` hardcodes its columns inline (`scenario_manifest.py:1669-1672`) — currently compatible, drift invisible. Delete the dead file + add a test asserting generator headers ⊆ backend `csv_schemas.json`.

### 7.4 Docker (C-14)
`load-driver/Dockerfile:43` ENTRYPOINT references non-existent `driver.py`; both loaddriver compose files inherit it; the standalone compose is a `services:{}` tombstone still documented as runnable in 2 docs; compose also references non-existent `run_scenario.py` (backend Test Runner docs expect the same missing file).

### 7.5 Repo bloat (git-tracked)
| Item | Size | Disposition |
|---|---|---|
| `ejouurnal/` — unrelated fulfillment project (286 files, incl. 29.7MB sim JSON, 21.4MB tar.gz, 7.3MB SQLite) | **89.1MB** | Remove from repo |
| `verticals/customer{N}-*/` synthetic data (49 dirs, 6,116 files) | **112.8MB** | Stop tracking; regenerate on demand |
| `kpi-dashboard/backend/backend.log.1` (rotated runtime log; `.gitignore` covers `*.log` but not `.log.1`) | 10.5MB | Delete + extend ignore |
| `kpi-dashboard-v3*.tar.gz` ×2 (app snapshots inside the app) | 9.4MB | Delete |
| `cs_pulse_backup_pre_phase4.sql` (repo-root DB dump) | 3.3MB | Delete (pg_dump→S3 exists) |
| `src/components/onboarding.zip` (Jan snapshot of live components) | 50KB | Delete |
| Side projects at root: `msu-vision-2020-mvp/` (157 files), `new-app/`, `client/`, `server/` | — | Archive out |
| Tracked test outputs: `load-driver/results/`, `reports/roi_report_*`, root `results/` | — | Gitignore + delete |
| `.claude/worktrees/` — 20 abandoned worktrees (disk, not git) | **7.7GB** | Prune |

---

## 8. Recommendations — Priority Order

### Immediate (this week)
1. **C-2** — add `filter(WizardRun.config['wizard'].astext == 'b')` (or equivalent) to `_fetch_forecast_layer`; regression from tonight's fix.
2. **C-12** — delete the 6 self-recursive `get_current_customer_id` shadows (2-line fix each).
3. **C-13** — fix the `get_catalog` import in `saas_premium/api_routes.py` (or delete the vertical API if superseded).
4. **C-1** — either create the missing `csv_validator.py` (wire the three orphaned validators) or delete the phantom import and orphans; decide, don't leave the silent no-op.
5. **C-3** — pin `method='pbkdf2:sha256'` at the 6 remaining call sites (mechanical, 15 min).
6. **C-9** — add `very_negative` to `auto_score_map` (1-line fix).
7. **C-11** — fix the 2-arg `get_revenue_at_risk` call.
8. **C-14** — fix the load-driver Dockerfile ENTRYPOINT (`driver.py` → `cs_pulse_driver.py`) or deprecate all three compose files + fix the 2 docs.
9. **C-18** — add tenant filters to `health_score_storage.py:261` / `time_series_api.py:44` (verify exposure first).

### Near-term (next sprint)
6. **C-4/C-5** — extract shared `daily_actions_core()` and add ActivityLogger to Flask signal ingest (the C-5 half is small and unblocks honest CSM metrics).
7. **C-8** — either honor `skip_wizard_*` params or reject unknown params; update load-driver accordingly.
8. **C-7** — add `fit_type` passthrough to `prediction_method` (report `prior_fallback` distinctly).
9. Fix `audit_flask_mcp_drift.py`'s two blind spots (file allowlist + jsonify parsing) so drift stays caught going forward — highest leverage single fix in this list.
10. Consolidate the NRR trajectory/waterfall pair (F-3) — two different dollar answers to the same CRO question.

### Structural (roadmap items)
11. Health-threshold consolidation pass, backend + frontend (~150 sites) — mechanical but large; consider a lint rule.
12. Shared frontend `formatters.ts` + fetch-wrapper adoption; kill mock fallbacks in favor of labeled error states (per the March cleanup pattern) — incl. the empty-list-triggers-mock bug (C-15).
13. Per-tenant verticals tree strategy: stop cloning `_template` per customer, or add a sync/version mechanism (47-52 dirs, 12+ already drifted in sample); make `wizard_b_pattern_analyzer` a real package module (60 copies, import-shadow hazard).
14. Wizard D wiring: add to onboarding path (or an explicit post-onboarding calibration prompt) + fix/remove the unreachable `trigger_wizard('d')` branch.
15. MCP auth pass over the 21 unauthenticated tools (C-10).
16. Dead-code deletion sweep: 4 RAG generations + celery wizard chain + 17 orphaned root modules (~9,000 lines) + ~16 orphaned frontend components; archive 159 one-off scripts.
17. Repo hygiene: remove `ejouurnal/` (89MB), untrack per-customer data dirs (113MB), delete committed logs/tarballs/dumps, prune 7.7GB of worktrees.
18. Account-health convergence (Open Decision #22): one `get_account_health()` service, one score store (HealthTrend vs HealthScore — pick and drain); fix the 50.0 sentinel (C-19) and the divergent missing-data defaults.
19. Single `get_account_arr()` helper (C-17); single sentiment-map constant; `label → canonical_arc` mapping table validated in CI; CI diff job for backend↔load-driver KPI catalogs.
20. Standardize WizardRun creation (one helper, `config['wizard']` key everywhere); make admin recalibrate routes write audit rows.

---

*Report generated by 4 parallel audit agents + 3 deep-scan sub-agents, August 3-4, 2026. All findings file:line-verified read-only against `main` @ `868479ed2`. Honest-uncertainty caveats: frontend reachability is static-analysis only; legacy scenarios 1-7 unverified against live APIs; prod-container state (qdrant skip messages) unverified while EC2 is stopped; KPI-catalog field-level diff not performed.*
