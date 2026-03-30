# Test Runner ↔ Load Driver Alignment Plan

**Date:** March 30, 2026
**Status:** For Review

---

## Problem Statement

The Test Runner UI/API and the Load Driver are misaligned at three levels:

1. **Broken invocation chain** — `test_runner_api.py` calls `run_scenario.py` which doesn't exist
2. **Silent entitlement stripping** — backend strips advanced options without telling the UI
3. **Missing manifest support** — 17 manifests exist in load-driver but aren't exposed in the UI

---

## Current State

| Component | Status |
|-----------|--------|
| Test Runner UI (ScenariosTab.tsx) | Feature-complete: 13 scenarios, advanced options, sliders, dropdowns |
| Test Runner API (test_runner_api.py) | Scenario metadata correct, subprocess invocation broken (missing script) |
| Load Driver scenarios (13 classes) | Working via Python class instantiation (`_legacy_driver.py`) |
| Load Driver manifests (17 files) | Working via CLI (`cs_pulse_driver.py --manifest X.json`) |
| `run_scenario.py` | **Does not exist** — backend expects it at line 71 |

---

## Phase 1: Create `run_scenario.py` Bridge Script (CRITICAL)

**What:** Create the missing `load-driver/run_scenario.py` that the Test Runner API already expects.

**Design:**
- Argparse CLI matching all flags the backend sends (lines 232-271 of test_runner_api.py)
- Maps `--scenario 1` to `ScenarioOnboarding`, `--scenario 8` to `ScenarioContextGraph`, etc.
- Wraps scenario class instantiation + `run()` call
- Writes JSON result to `--output-dir/scenario_{id}.json` (already expected by backend)
- Passes `--num-accounts`, `--seed`, `--industry` etc. into scenario via args object

**Required CLI flags:**
```
--scenario ID          (required)
--customer-id INT      (required)
--base-url URL         (required)
--output-dir PATH      (required)
--verbose              (flag)
--num-accounts INT     (optional, default from scenario)
--seed INT             (optional)
--dry-run              (flag, scenario 4 only)
--industry STR         (optional, scenario 1)
--onboarding-mode STR  (optional, scenario 1)
--arc-id STR           (optional, scenario 8)
--months INT           (optional, scenario 9)
--improvement FLOAT    (optional, scenario 9)
--manifest PATH        (optional, scenario 0/manifest mode)
--weights JSON         (optional)
--enabled-kpis JSON    (optional)
--enabled-pillars JSON (optional)
--showcase-pattern-mix JSON (optional)
```

**Files:**
- NEW: `load-driver/run_scenario.py` (~150 lines)
- MODIFY: `load-driver/scenarios/base.py` — add `self.cli_args` to BaseScenario.__init__

**Effort:** 4-6 hours

---

## Phase 2: Entitlement Feedback to UI (HIGH)

**What:** When backend strips advanced options due to tier limits, tell the UI which options were removed.

**Design:**
- Modify `start_run()` response to include `options_stripped: [...]`
- Frontend shows info banner: "2 advanced options require Professional tier: numAccounts, seed"
- Disabled scenario cards show tier badge instead of being hidden

**Files:**
- MODIFY: `kpi-dashboard/backend/test_runner_api.py` — add `options_stripped` to response
- MODIFY: `kpi-dashboard/src/components/dc/test-runner/tabs/ScenariosTab.tsx` — show banner + disabled cards

**Effort:** 2-3 hours

---

## Phase 3: Expose Manifests in UI (MEDIUM)

**What:** Add a "Manifest Mode" option to the Test Runner that lets users select and run one of the 17 available manifests.

**Design:**
- Add new SCENARIO_META entry: `'0': {'name': 'Manifest Load', 'group': 'Core', ...}`
- Backend: `GET /api/test-runner/manifests` lists available .json files from `load-driver/manifests/`
- UI: When scenario '0' is selected, show manifest dropdown populated from API
- `run_scenario.py` handles `--manifest path.json` by delegating to cs_pulse_driver manifest mode

**Current manifests (17):**

| Name | Vertical | Purpose |
|------|----------|---------|
| gainsight_15kpi_e2e.json | SaaS Premium | Primary demo (15 KPIs, lifecycle stages) |
| everest_gold_dc2s.json | DC2_S | Gold reference |
| enterprise_18_dc2s_6mo.json | DC2_S | 18 accounts, 6 months |
| novastar_dc2s.json | DC2_S | 18 accounts, $62M ARR |
| mount_hamilton_saas.json | SaaS | SaaS 12 accounts |
| sandalwood_capital_dc2s.json | DC2_S | PE portfolio |
| alpine_saas_partners.json | SaaS | Partner-focused |
| dr1_ai_dc2s.json | DC2_S | AI infrastructure |
| mount_shasta_saas.json | SaaS | SaaS mid-market |
| ... (8 more) | Mixed | Various test profiles |

**Files:**
- MODIFY: `kpi-dashboard/backend/test_runner_api.py` — add manifest listing endpoint + SCENARIO_META entry
- MODIFY: `kpi-dashboard/src/components/dc/test-runner/tabs/ScenariosTab.tsx` — manifest dropdown
- MODIFY: `load-driver/run_scenario.py` — handle `--manifest` flag

**Effort:** 3-4 hours

---

## Phase 4: Scenario-Specific Validation (LOW)

**What:** Frontend validates required options before calling start_run().

**Examples:**
- Scenario 8 (Context Graph): warn if no `arcId` selected
- Scenario 9 (ROI Simulation): require `months` and `improvement`
- Scenario 1 (Onboarding): validate `industry` is in allowed set

**Effort:** 1-2 hours

---

## Summary

| Phase | Priority | Effort | Impact |
|-------|----------|--------|--------|
| 1: `run_scenario.py` bridge | CRITICAL | 4-6h | Unblocks all Test Runner execution |
| 2: Entitlement feedback | HIGH | 2-3h | Eliminates silent option stripping |
| 3: Manifest support in UI | MEDIUM | 3-4h | Exposes 17 manifests to users |
| 4: Option validation | LOW | 1-2h | Prevents invalid scenario configs |

**Total: 10-15 hours across 4 phases**

**Recommended order:** Phase 1 first (blocking), then Phase 3 (high demo value), then Phase 2 + 4.

---

---

## Phase 5: Streaming/Incremental Data Mode (HIGH)

**What:** Add a `--stream` flag to `run_scenario.py` and manifest mode that uploads data month-by-month with configurable delay, simulating real-time data flow.

**Why:** Demos and integration tests need to show how CS Pulse reacts to data arriving over time — health score changes, signal detection triggers, playbook fires. Bulk upload doesn't demonstrate this.

**What exists:** Scenario 2a (KPI Simulation) already loops through 12 months and uploads per-month. Manifest mode has `--phase baseline` / `--phase intervention` split.

**Design:**
- `run_scenario.py --scenario 1 --stream --stream-interval 5` → uploads month 1, waits 5 seconds, uploads month 2, etc.
- Manifest mode: `--manifest X.json --stream --months 12 --stream-interval 10`
- Each month: upload KPIs → trigger health recalc → wait interval → next month
- Progress callback: emit JSON progress events for UI consumption (`{"month": 3, "health": 67.2, "status": "at_risk"}`)
- Checkpointing: write `stream_checkpoint.json` after each month so interrupted streams can resume with `--resume`

**Files:**
- MODIFY: `load-driver/run_scenario.py` — add `--stream`, `--stream-interval`, `--resume` flags
- MODIFY: `load-driver/scenarios/scenario_manifest.py` — extract month-by-month upload into reusable `StreamUploader` class
- MODIFY: `kpi-dashboard/backend/test_runner_api.py` — pass stream options to subprocess, add SSE progress endpoint

**Effort:** 6-8 hours

---

## Phase 6: Concurrent Load Testing (MEDIUM)

**What:** Run N customers in parallel threads against the server to test multi-tenant performance.

**What exists:** `test_3customer_concurrent.py` already threads 3 customers with staggered start. Works but is a standalone test file, not integrated into the driver CLI.

**Design:**
- `cs_pulse_driver.py --concurrent 5 --manifest X.json` → creates 5 customers, runs manifest for each in parallel ThreadPoolExecutor
- Each thread gets its own CSPulseClient with unique customer_id
- Rate limiter: `--max-rps 50` caps total requests/second across all threads
- Per-thread logging: `results/concurrent/{customer_id}/` separate log + results
- Aggregate report: total requests, p50/p95/p99 latency, errors, health score distribution across customers

**Files:**
- MODIFY: `load-driver/cs_pulse_driver.py` — add `--concurrent N` and `--max-rps` flags
- NEW: `load-driver/concurrent_runner.py` — ThreadPoolExecutor wrapper with per-thread client, rate limiter, latency tracking
- MODIFY: `load-driver/client.py` — add request timing instrumentation (elapsed_ms per call)

**Effort:** 6-8 hours

---

## Phase 7: Cleanup + Replay Mode (HIGH)

**What:** Single command to cleanup all test data for a customer and immediately re-run the same scenario/manifest.

**What exists:** `scenario_cleanup.py` does FK-safe 24-table deletion + filesystem cleanup. `test_5customer_10accounts_recycle.py` demonstrates the pattern manually.

**Design:**
- `run_scenario.py --scenario 1 --customer-id 451 --cleanup-first` → runs scenario 4 (cleanup), then scenario 1 (onboarding)
- `cs_pulse_driver.py --manifest X.json --customer-id 451 --replay` → cleanup + full manifest re-run on same customer_id
- Safety: `--replay` requires explicit `--confirm-cleanup` to prevent accidental data loss
- Pre-cleanup snapshot: save health scores + account count to `pre_cleanup_snapshot.json` for comparison
- Post-replay comparison: diff health scores before cleanup vs after replay → flag regressions

**Files:**
- MODIFY: `load-driver/run_scenario.py` — add `--cleanup-first` and `--replay` flags
- MODIFY: `load-driver/cs_pulse_driver.py` — add `--replay` + `--confirm-cleanup`
- NEW: `load-driver/snapshot.py` — capture/compare pre/post health snapshots (~60 lines)

**Effort:** 3-4 hours

---

## Phase 8: Structured Logging (MEDIUM)

**What:** Per-customer, per-scenario structured JSON logs with performance metrics.

**What exists:** Dual-stream logging (file + console), verbose flag, thread-name tagging. All plain text, single file.

**Design:**
- Each run writes to `results/{run_id}/logs/`
  - `run.log` — human-readable master log
  - `run.jsonl` — structured JSON lines (one JSON object per log entry)
  - `scenario_{id}.jsonl` — per-scenario log
  - `customer_{id}.jsonl` — per-customer log (concurrent mode)
- Each log entry: `{"ts": "ISO", "level": "INFO", "scenario": "1", "customer_id": 451, "msg": "...", "elapsed_ms": 234, "api_endpoint": "/api/dc2s/accounts"}`
- API call instrumentation: every `client.py` request logs endpoint, method, status_code, elapsed_ms, response_size
- Summary metrics at end of run: total API calls, avg latency, error rate, slowest endpoints

**Files:**
- NEW: `load-driver/structured_logger.py` — JSON line logger with context (scenario, customer, API call) (~100 lines)
- MODIFY: `load-driver/client.py` — wrap every request with timing + structured log emission
- MODIFY: `load-driver/scenarios/base.py` — pass structured logger to all scenarios

**Effort:** 4-5 hours

---

## Phase 9: Test Reports with Regression Detection (HIGH)

**What:** After each run, generate a report comparing results to a saved baseline. Flag regressions.

**What exists:** Markdown + JSON results per run. ROI 2-pager. No baseline comparison or regression detection.

**Design:**
- **Baseline save:** `run_scenario.py --save-baseline` writes `results/baselines/{customer_id}_baseline.json`
  - Contents: per-scenario status, health scores, account count, API call count, latency p95, error count
- **Regression check:** Every subsequent run auto-compares to baseline (if one exists)
  - Report shows: `[PASS]` / `[REGRESSED]` / `[NEW]` per scenario
  - Health score regression: flag if any account health changed by > 5 points
  - Latency regression: flag if p95 increased by > 50%
  - Error regression: flag if error count increased
- **Report format:** Markdown + JSON, written to `results/{run_id}/report.md`
  - Section 1: Executive Summary — X passed, Y regressed, Z new
  - Section 2: Per-scenario results table with status, timing, delta from baseline
  - Section 3: Health score comparison (baseline vs current per account)
  - Section 4: Performance metrics (latency distribution, API call counts)
  - Section 5: Errors and warnings
- **UI integration:** `GET /api/test-runner/runs/{run_id}/report` returns the markdown report

**Files:**
- NEW: `load-driver/regression.py` — baseline save/load + comparison logic (~150 lines)
- NEW: `load-driver/report_generator.py` — markdown report builder (~200 lines)
- MODIFY: `load-driver/run_scenario.py` — add `--save-baseline` flag, auto-compare on each run
- MODIFY: `kpi-dashboard/backend/test_runner_api.py` — add report retrieval endpoint

**Effort:** 6-8 hours

---

## Updated Summary

| Phase | Feature | Priority | Effort | Impact |
|-------|---------|----------|--------|--------|
| 1 | `run_scenario.py` bridge script | CRITICAL | 4-6h | Unblocks all Test Runner execution |
| 2 | Entitlement feedback to UI | HIGH | 2-3h | Eliminates silent option stripping |
| 3 | Manifest support in UI | MEDIUM | 3-4h | Exposes 17 manifests to users |
| 4 | Scenario option validation | LOW | 1-2h | Prevents invalid configs |
| 5 | Streaming/incremental data | HIGH | 6-8h | Enables realistic time-series demos |
| 6 | Concurrent load testing | MEDIUM | 6-8h | Multi-tenant perf validation |
| 7 | Cleanup + replay mode | HIGH | 3-4h | Fast iteration on same customer |
| 8 | Structured logging | MEDIUM | 4-5h | Debuggability + perf metrics |
| 9 | Reports with regression detection | HIGH | 6-8h | Automated pass/fail/regress tracking |

**Total: 35-52 hours across 9 phases**

**Recommended implementation order:**
1. Phase 1 (bridge script) — unblocks everything
2. Phase 7 (cleanup + replay) — fast iteration, low effort
3. Phase 5 (streaming) — demo value
4. Phase 9 (reports + regression) — quality assurance
5. Phase 8 (structured logging) — debuggability
6. Phase 3 (manifests in UI) — UI completeness
7. Phase 6 (concurrent) — perf testing
8. Phase 2 + 4 (entitlement + validation) — polish

---

## Phase 10: E2E Pipeline Benchmark (HIGH)

**What:** A single scenario that runs the full platform pipeline, instruments every step, validates intermediate outputs, and produces a pipeline timing report.

**Why:** No existing scenario exercises the full chain. Manifest mode comes closest but skips ROI calc and Signal Analyst. We need a single command that proves every subsystem works together.

**Pipeline steps measured (in order):**

| Step | Input | Output | Validation |
|------|-------|--------|------------|
| 1. CSV Generation | Manifest JSON | 10 CSV files | File count, row counts, schema valid |
| 2. CSV Upload | 10 CSVs | Upload confirmations | All accepted, no schema errors |
| 3. process_data | customer_id | HTTP 202 → completion | Status = complete, no errors |
| 4. Health Score Calc | KPI data in DB | HealthScore rows | N accounts scored, scores in 0-100, distribution reasonable |
| 5. Wizard A (Journey) | Health + KPI data | Journey JSONs per account | N journeys created, arc types assigned |
| 6. Wizard B (Patterns) | Journey data | Pattern + early warning rules | At least 1 pattern found |
| 7. Wizard C (Weights) | Health + KPI correlation | Calibrated weights | Weights sum to 1.0 per pillar, delta from defaults logged |
| 8. Context Graph Build | Outcome/decision/signal CSVs | ContextNode + ContextEdge rows | Node count > 0, edge count > 0, revenue_impact on outcomes |
| 9. Signal Analyst | KPI + signals | Per-account analysis | All accounts analyzed, churn_probability in 0-1 |
| 10. ROI Calc | Health deltas + Power of 1 | Historical + forward ROI | ROI > 0, metrics populated |
| 11. CSM Actions | Health + signals + playbooks | Prioritized action list | At least 1 action generated |

**Report output:**
```
Pipeline Report — Customer 451 (30 accounts, Gainsight manifest)
──────────────────────────────────────────────────────────────────
Step                     Duration   Status   Detail
1. CSV Generation         4.2s      PASS     10 files, 30 accounts, 4,320 KPI rows
2. CSV Upload            12.1s      PASS     All schemas valid, 0 warnings
3. process_data           8.7s      PASS     Completed in 8.7s (async)
4. Health Score Calc      3.4s      PASS     30/30 scored, mean=64.2, 8 critical
5. Wizard A              5.1s      PASS     30 journeys, 6 arc types assigned
6. Wizard B              2.8s      PASS     12 patterns, 4 early warnings
7. Wizard C              1.9s      PASS     Weights calibrated (P3: 0.25→0.28)
8. Context Graph          6.2s      PASS     847 nodes, 1,203 edges, $12.4M at risk
9. Signal Analyst        14.3s      PASS     30 analyzed, avg confidence 0.72
10. ROI Calc              2.1s      PASS     Historical $2.1M, Forward $4.8M
11. CSM Actions           1.4s      PASS     5 actions, top: K2 churn prevention
──────────────────────────────────────────────────────────────────
TOTAL                    62.2s      PASS     Full pipeline verified
```

**Files:**
- NEW: `load-driver/scenarios/scenario_e2e_pipeline.py` — full pipeline orchestrator (~300 lines)
- MODIFY: `load-driver/run_scenario.py` — register as scenario '10'
- MODIFY: `kpi-dashboard/backend/test_runner_api.py` — add to SCENARIO_META

**Effort:** 8-10 hours

---

## Phase 11: Push Signal Pipeline + Incremental Data Lifecycle (HIGH)

**What:** Test the "day 2+" workflows — push signals via real-time API, incremental monthly data, and the automatic downstream cascade (arc reclassification, playbook triggers, approval queue, ROI update).

**Why:** Phase 10 tests the batch onboarding pipeline. Phase 11 tests what happens after onboarding — the ongoing operational loop that runs every day/week/month. This is the pipeline customers actually live in.

**Two sub-scenarios:**

### 11a: Push Signal Pipeline

Tests the real-time signal → action cascade:

| Step | What happens | Validation |
|------|-------------|------------|
| 1. POST signal | `POST /api/data-ingestion/signals` with a champion_departure signal | HTTP 200, signal stored |
| 2. Signal Engine | Auto-enriches: LLM sentiment, urgency classification | Signal has sentiment + urgency |
| 3. Context Graph | SIGNAL node created, edges to account + stakeholder | Node exists, edges correct |
| 4. Arc Reclassifier | Account arc re-evaluated (should shift to exec_sponsor_change) | Arc type updated |
| 5. Push Intelligence | Evaluates playbook triggers | Trigger event emitted |
| 6. Approval Queue | Action routed by confidence | ApprovalRequest created (pending or auto-executed) |
| 7. Event Bus | PLAYBOOK_AUTO_TRIGGERED or APPROVAL_REQUESTED published | Event logged |

**Signal types to test:**
- `champion_departure` → should trigger PB-04 (Champion Recovery)
- `competitive_threat` → should trigger PB-03 (Competitive Defense)
- `expansion_signal` → should trigger PB-05 (Expansion)
- `critical_incident` → should trigger PB-02 (Crisis Recovery)

### 11b: Incremental Monthly Data Lifecycle

Tests the month-over-month operational loop:

| Month | Action | Expected Outcome |
|-------|--------|------------------|
| M1 (Baseline) | Full onboarding via manifest | Baseline health scores established |
| M2 | Upload new KPI measurements (slight decline) | Health scores update, deltas computed |
| M3 | Upload declining KPIs + negative qualitative signal | Health drops to at-risk, Signal Analyst fires |
| M4 | Health crosses critical threshold (<50) | Playbook auto-triggers, approval queued, arc reclassified |
| M5 | Upload improving KPIs (intervention effect) | Health recovers, ROI engine captures delta |
| M6 | Upload strong KPIs + positive signal | Healthy again, ROI shows $X protected, expansion signal |

**Per-month validation:**
- Health score updated and delta correct
- Arc classification matches expected trajectory
- Playbook triggers fire at correct thresholds
- ROI engine captures before/after deltas
- CSM actions reprioritize based on new data

**Report output:**
```
Incremental Lifecycle — Customer 451, Account K2 Computing
───────────────────────────────────────────────────────────
Month   Health   Delta   Arc                      Triggers           ROI Impact
M1      72       —       land_and_expand           —                  —
M2      65      -7       silent_churn              —                  —
M3      54      -11      silent_churn              Signal Analyst     —
M4      43      -11      exec_sponsor_change       PB-04 (queued)     $680K at risk
M5      58      +15      crisis_recovery           —                  $340K protected
M6      74      +16      expansion_champion        PB-05 (expansion)  $960K pipeline
───────────────────────────────────────────────────────────
Total pipeline ROI: $1.3M protected, $960K expansion pipeline
```

**Files:**
- NEW: `load-driver/scenarios/scenario_push_signals.py` — push signal pipeline test (~150 lines)
- NEW: `load-driver/scenarios/scenario_incremental_lifecycle.py` — 6-month lifecycle test (~250 lines)
- MODIFY: `load-driver/run_scenario.py` — register as scenarios '11a' and '11b'
- MODIFY: `kpi-dashboard/backend/test_runner_api.py` — add to SCENARIO_META

**Effort:** 8-10 hours

---

## Updated Summary

| Phase | Feature | Priority | Effort | Impact |
|-------|---------|----------|--------|--------|
| 1 | `run_scenario.py` bridge script | CRITICAL | 4-6h | Unblocks all Test Runner execution |
| 2 | Entitlement feedback to UI | LOW | 2-3h | Eliminates silent option stripping |
| 3 | Manifest support in UI | MEDIUM | 3-4h | Exposes 17 manifests to users |
| 4 | Scenario option validation | LOW | 1-2h | Prevents invalid configs |
| 5 | Streaming/incremental data | HIGH | 6-8h | Enables realistic time-series demos |
| 6 | Concurrent load testing | MEDIUM | 6-8h | Multi-tenant perf validation |
| 7 | Cleanup + replay mode | HIGH | 3-4h | Fast iteration on same customer |
| 8 | Structured logging | MEDIUM | 4-5h | Debuggability + perf metrics |
| 9 | Reports with regression detection | HIGH | 6-8h | Automated pass/fail/regress tracking |
| 10 | E2E pipeline benchmark | HIGH | 8-10h | Full pipeline verification + timing |
| 11 | Push signals + incremental lifecycle | HIGH | 8-10h | Day-2 operational loop testing |

**Total: 51-72 hours across 11 phases**

**Recommended implementation order:**
1. Phase 1 (bridge script) — unblocks everything
2. Phase 7 (cleanup + replay) — fast iteration, low effort
3. Phase 10 (E2E pipeline) — proves the whole system works
4. Phase 11 (push + incremental) — proves day-2 operations work
5. Phase 9 (reports + regression) — captures pass/fail baselines
6. Phase 5 (streaming) — demo value
7. Phase 8 (structured logging) — feeds into reports
8. Phase 6 (concurrent) — perf testing
9. Phase 3 (manifests in UI) — UI completeness
10. Phase 2 + 4 (entitlement + validation) — polish

## Decision Needed

- Phase 1 is required — without `run_scenario.py`, the Test Runner UI can't execute scenarios
- Phase 10 vs 11 — E2E pipeline benchmark (batch) or push+incremental (operational loop) first?
- Phase 6 (concurrent) — what's the target concurrency? 5 customers? 50? Affects design
- Should the E2E pipeline report be viewable in the Test Runner UI or CLI-only initially?
