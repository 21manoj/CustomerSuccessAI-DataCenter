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

---

## Phase 12: Operational Workflow Tests (HIGH)

**What:** 15 operational workflows that run in production but have zero test coverage today. These are the scenarios that cause real incidents.

### 12a: Config Change Cascade (CRITICAL)

Admin changes pillar weights → health scores recalculate → playbook triggers re-evaluate → CSM actions reprioritize.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Onboard customer, establish baseline scores | Scores populated |
| 2 | Change P3 weight from 0.25 → 0.35 via API | CustomerConfig updated |
| 3 | Trigger health recalculation | Scores changed (not stale) |
| 4 | Verify accounts near thresholds crossed over | At-risk → critical if P3 was weak |
| 5 | Verify CSM actions reprioritized | New top action reflects weight change |

**Risk if untested:** Stale scores after config change — admin changes weights but dashboard shows old numbers.

### 12b: KPI Enable/Disable (CRITICAL)

Customer enables 5 new KPIs or disables 3 → weight re-normalization → scores shift.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Establish baseline with 15 KPIs | Scores stable |
| 2 | Disable 3 KPIs via configure_customer_kpis | Config updated |
| 3 | Trigger health recalc | Remaining KPI weights re-normalized to sum=1.0 per pillar |
| 4 | Enable 5 additional KPIs + upload data | New KPIs appear in scoring |
| 5 | Verify scores changed proportionally | No NaN, no division-by-zero |

**Risk if untested:** Weights don't sum to 1.0 after KPI changes, broken scores.

### 12c: Customer Tier Upgrade/Downgrade (HIGH)

Starter → Professional → new features unlock. Professional → Starter → features locked.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Create customer at Starter tier | Only Starter features accessible |
| 2 | Try accessing Signal Analyst (Professional) | HTTP 403 returned |
| 3 | Upgrade to Professional | Signal Analyst accessible |
| 4 | Try accessing Approval Queue (Enterprise) | HTTP 403 returned |
| 5 | Downgrade back to Starter | Professional features locked again |

**Risk if untested:** Feature leaks after downgrade, or silent lockouts after upgrade.

### 12d: User CRUD + RBAC (HIGH)

Create CSM user, assign accounts, verify they can only see their accounts.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Create admin user for customer | Admin sees all accounts |
| 2 | Create CSM user with 5 assigned accounts | CSM sees only 5 accounts |
| 3 | CSM queries account outside assignment | HTTP 403 or empty result |
| 4 | Admin adds 2 more accounts to CSM | CSM now sees 7 |
| 5 | Delete CSM user | User gone, no orphan sessions |

**Risk if untested:** Cross-user data leakage within same customer.

### 12e: Wizard C Weight Drift Detection (HIGH)

Wizard C recalibrates → weights shift → health scores change → accounts cross thresholds.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Establish baseline scores with default weights | Record scores |
| 2 | Run Wizard C | Weights change (delta logged) |
| 3 | Recalculate health scores | Scores shift by 5-15 points |
| 4 | Verify threshold crossings | Accounts that were 68 (at-risk) may now be 72 (healthy) or vice versa |
| 5 | Verify weight history record created | Timestamp + source=wizard_c |

**Risk if untested:** Silent score drift — accounts change status and nobody notices.

### 12f: Renewal Countdown Triggers (MEDIUM)

Account 30/60/90 days from renewal → playbook triggers → CSM actions escalate.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Create account with renewal_date = today + 90 days | Account created |
| 2 | Run CSM daily actions | Renewal appears as low priority |
| 3 | Advance to 60 days out (update renewal_date or wait) | Priority increases |
| 4 | Advance to 30 days out | Renewal playbook triggers |
| 5 | Advance past renewal | Account status updates |

**Risk if untested:** Missed renewal windows — CSM doesn't see upcoming renewals.

### 12g: Account Lifecycle Transitions (MEDIUM)

Account health: 80 → 65 → 45 → 30 → 55 → 72 (full cycle through all states).

| Step | Action | Validation |
|------|--------|------------|
| 1 | Start healthy (80) | Classification = healthy, arc = expansion_champion |
| 2 | Inject declining KPIs → 65 | Classification = at_risk, arc reclassifies |
| 3 | Continue decline → 45 | Classification = critical, crisis playbook fires |
| 4 | Inject improving KPIs → 55 | Classification = at_risk, arc = crisis_recovery |
| 5 | Continue recovery → 72 | Classification = healthy, ROI captures protected revenue |

**Risk if untested:** Arc doesn't reclassify on threshold crossings, playbooks don't fire.

### 12h: Multi-Vertical Coexistence (MEDIUM)

DC2_S and SaaS Premium customers on same platform, different catalogs, different scoring.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Create DC2_S customer (38 KPIs, P3=AI Workload) | DC2_S catalog loaded |
| 2 | Create SaaS customer (41 KPIs, P1=Product Adoption) | SaaS catalog loaded |
| 3 | Upload KPIs for both | Each uses correct catalog ranges |
| 4 | Calculate health for both | Pillar weights differ correctly (DC2_S P3=25%, SaaS P1=30%) |
| 5 | Query accounts for each | No cross-vertical catalog contamination |

**Risk if untested:** SaaS customer scored with DC2_S ranges, wrong health scores.

### 12i: Data Correction / Re-Upload (CRITICAL)

Customer re-uploads corrected CSV for a month that already has data.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Upload 6 months of KPI data | Baseline scores established |
| 2 | Upload corrected data for month 3 (different values) | UPSERT replaces, not duplicates |
| 3 | Verify row count unchanged for month 3 | No duplicate rows |
| 4 | Verify health score for month 3 changed | Reflects corrected data |
| 5 | Verify months 1,2,4,5,6 unchanged | Only month 3 affected |

**Risk if untested:** Duplicate rows inflate scores, or corrected data ignored.

### 12j: Stakeholder Change Detection (MEDIUM)

Champion leaves → stakeholder CSV re-uploaded → context graph updates → arc reclassifies.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Upload stakeholders with champion "Jane Chen, VP Eng" | STAKEHOLDER node created |
| 2 | Upload new stakeholders CSV: Jane departed, "Tom Park" new | STAKEHOLDER node updated |
| 3 | Verify context graph: departure edge created | CAUSED_BY or LED_TO edge |
| 4 | Run arc classifier | Arc shifts to exec_sponsor_change |
| 5 | Verify playbook recommendation | PB-04 (Champion Recovery) recommended |

**Risk if untested:** Champion departure not detected, no playbook fires.

### 12k: API Rate Limiting (LOW)

Burst 200 requests in 1 minute from single customer.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Send 200 GET /api/dc2s/accounts in rapid succession | First 200 succeed (within limit) |
| 2 | Continue sending | HTTP 429 returned after limit |
| 3 | Wait 60 seconds | Requests succeed again |
| 4 | Verify no data corruption | Accounts unchanged |

**Risk if untested:** Server overload, no rate limiting, or data corruption under load.

### 12l: Concurrent process_data Race Condition (CRITICAL)

Two process_data calls for same customer overlap.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Upload CSVs for customer | Data ready |
| 2 | Trigger process_data (call A) | Starts processing |
| 3 | Immediately trigger process_data again (call B) | Should queue or reject |
| 4 | Wait for both to complete | No duplicate health scores |
| 5 | Verify score count = expected (not 2x) | Data integrity maintained |

**Risk if untested:** Race condition creates duplicate scores, corrupts health data.

### 12m: Large Portfolio Performance (MEDIUM)

Customer with 100+ accounts, 38 KPIs each, 12 months of data.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Generate manifest with 100 accounts | CSVs generated |
| 2 | Upload and process | Completes within 5 minutes |
| 3 | Calculate health for all 100 | All 100 scored |
| 4 | Load CSM daily actions | Returns in < 3 seconds |
| 5 | Load CRO dashboard | Renders in < 5 seconds |

**Risk if untested:** Timeout on large portfolios, memory issues, slow UI.

### 12n: Empty/Sparse Data Handling (CRITICAL)

Customer with 3 of 38 KPIs, or account with 1 month of data.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Upload accounts.csv with 5 accounts | Accounts created |
| 2 | Upload KPIs for only 3 of 38 KPI codes | 3 KPIs ingested |
| 3 | Calculate health | Score computed (not NaN, not 0) — uses available KPIs only |
| 4 | Upload 1 month of data for 1 account | Score computed for that month |
| 5 | Query pillar scores | Pillars with no data show null (not 0), populated pillars scored |

**Risk if untested:** Division by zero, NaN scores, missing pillar scores crash UI.

### 12o: MCP Tool Chain (LOW)

Claude.ai calls sequence of MCP tools in realistic order.

| Step | Action | Validation |
|------|--------|------------|
| 1 | get_platform_instructions() | Returns valid context |
| 2 | list_accounts(customer_id) | Returns account list |
| 3 | get_at_risk_accounts(customer_id) | Returns subset with health < 70 |
| 4 | get_account_health(customer_id, account_id) | Returns pillar breakdown |
| 5 | get_playbook_recommendations(customer_id, account_id) | Returns playbook list |
| 6 | calculate_power_of_1(customer_id, "NRR") | Returns dollar impact |
| 7 | get_context_graph_mermaid(customer_id, account_id) | Returns valid Mermaid diagram |

**Risk if untested:** Tool responses malformed, context lost between calls.

---

### 12p: ROI Dashboard Data Validation (CRITICAL)

End-to-end validation that data flowing into CRO/CFO persona dashboards is correct, consistent, and matches direct MCP tool outputs. This is the "trust but verify" layer — if the pipeline produces numbers, the dashboards must show the same numbers.

**Why CRITICAL:** The CRO/CFO dashboards are the buyer-facing deliverable. If the ROI engine calculates $2.1M protected but the CFO dashboard shows $1.8M (or blank), the deal is dead. Every number must be traceable from pipeline output → API endpoint → dashboard render.

| Step | Action | Validation |
|------|--------|------------|
| 1 | Run full pipeline (onboard + process_data) | Pipeline completes |
| 2 | Call `get_revenue_at_risk(customer, account)` via MCP | Returns at_risk, protected, expansion, lost |
| 3 | Call `GET /api/context-graph/revenue?account_id=X` REST endpoint | Returns SAME numbers as step 2 |
| 4 | Call `get_portfolio_roi_summary(customer)` via MCP | Returns historical ROI, forward ROI, payback |
| 5 | Call `GET /api/outcome-roi/story?account_id=X` REST endpoint | Returns SAME numbers as step 4 |
| 6 | Call `get_playbook_economics(customer)` via MCP | Returns per-playbook cost, hours, ROI |
| 7 | Call `calculate_power_of_1(customer, 'NRR')` via MCP | Returns dollar impact |
| 8 | Call `GET /api/outcome-roi/historical` REST endpoint | Historical ROI includes NRR impact matching step 7 |
| 9 | Verify CRO dashboard data matches | Fetch `/api/executive/cro-dashboard`, compare at_risk ARR, expansion pipeline, protected $ |
| 10 | Verify CFO dashboard data matches | Fetch `/api/executive/cfo-dashboard`, compare ROI %, payback months, investment vs return |

**Cross-validation rules (must ALL pass):**
- `get_revenue_at_risk()` total === context graph revenue API total (no double-counting)
- `get_portfolio_roi_summary()` historical_impact === outcome-roi/historical total
- Power of 1 per-metric impact sums to portfolio ROI total (within 5% tolerance for compounding)
- CRO dashboard at_risk_arr === sum of at_risk accounts' ARR
- CFO dashboard roi_percentage === (total_impact / total_investment) * 100
- Health scores on dashboard match `get_account_health()` for each account
- Account count on dashboard matches `list_accounts()` count

**Consistency across runs (repeatability):**
- Run pipeline twice with same manifest + same seed → IDENTICAL outputs
- Compare: health scores, pillar scores, revenue at risk, ROI numbers, CSM actions
- Any delta > 0 is a bug (deterministic pipeline should produce deterministic output)

**Report output:**
```
ROI Dashboard Validation — Customer 451
────────────────────────────────────────────────────────────
Check                              MCP Tool      REST API    Match
Revenue at risk (total)            $8,241,000    $8,241,000  PASS
  - at_risk                        $5,120,000    $5,120,000  PASS
  - protected                      $2,340,000    $2,340,000  PASS
  - expansion                      $1,890,000    $1,890,000  PASS
  - lost                           $410,000      $410,000    PASS
Historical ROI                     $2,140,000    $2,140,000  PASS
Forward ROI (12mo)                 $4,820,000    $4,820,000  PASS
ROI percentage                     342%          342%        PASS
Payback months                     4.2           4.2         PASS
Power of 1 (NRR, 1%)              $98,200       $98,200     PASS
CRO dashboard at_risk_arr          $5,120,000    $5,120,000  PASS
CFO dashboard roi_pct              342%          342%        PASS
Account count                      30            30          PASS
────────────────────────────────────────────────────────────
Repeatability: Run 1 vs Run 2     IDENTICAL (0 deltas)
RESULT: 13/13 PASS
```

**Files:**
- NEW: `load-driver/scenarios/scenario_roi_dashboard_validation.py` (~250 lines)
- MODIFY: `load-driver/run_scenario.py` — register as scenario '12p'
- MODIFY: `kpi-dashboard/backend/test_runner_api.py` — add to SCENARIO_META

**Effort:** 6-8 hours

---

### Phase 12 Summary

| Sub-phase | Workflow | Priority | Effort | Production Risk |
|-----------|---------|----------|--------|----------------|
| 12a | Config change cascade | CRITICAL | 3h | Stale scores after weight change |
| 12b | KPI enable/disable | CRITICAL | 2h | Broken weight normalization |
| 12c | Tier upgrade/downgrade | HIGH | 2h | Feature leaks or lockouts |
| 12d | User CRUD + RBAC | HIGH | 3h | Cross-user data leakage |
| 12e | Wizard C weight drift | HIGH | 2h | Silent score drift |
| 12f | Renewal countdown | MEDIUM | 2h | Missed renewal windows |
| 12g | Lifecycle transitions | MEDIUM | 3h | Arc reclassification failures |
| 12h | Multi-vertical coexistence | MEDIUM | 2h | Cross-vertical contamination |
| 12i | Data correction re-upload | CRITICAL | 2h | Duplicate rows, inflated scores |
| 12j | Stakeholder change | MEDIUM | 2h | Champion departure undetected |
| 12k | API rate limiting | LOW | 1h | Server overload |
| 12l | Concurrent process_data | CRITICAL | 3h | Race condition, duplicate data |
| 12m | Large portfolio performance | MEDIUM | 3h | Timeouts, memory issues |
| 12n | Empty/sparse data | CRITICAL | 2h | NaN/zero scores, crashes |
| 12o | MCP tool chain | LOW | 2h | Malformed tool responses |
| 12p | ROI Dashboard data validation | CRITICAL | 6-8h | CRO/CFO dashboard shows wrong numbers |

**Total Phase 12: ~40-42 hours**

**Recommended priority order (CRITICAL first):**
1. 12p ROI Dashboard validation (6-8h) — buyer-facing data must be correct + repeatable
2. 12a Config cascade + 12b KPI enable/disable (5h) — most common admin action
3. 12i Data re-upload + 12l Concurrent process_data (5h) — data integrity
4. 12n Sparse data (2h) — new customer onboarding edge case
5. 12e Wizard C drift + 12c Tier changes (4h) — operational safety
6. 12d RBAC + 12g Lifecycle + 12h Multi-vertical (8h) — correctness
7. 12f Renewal + 12j Stakeholder + 12k Rate limit + 12m Perf + 12o MCP (10h) — completeness

---

---

## Phase 13: Ask AI Persona Validation (MEDIUM)

**What:** Automated test harness that runs the 40 validated persona questions from `ASK_AI_WHAT_IF_QUESTIONS.md` against a demo customer and validates responses.

**Why:** Ask AI is the primary interaction surface for CRO/CFO/VP CS. If it returns "I don't have that information" or wrong numbers, the demo fails. These tests ensure every persona gets data-backed answers.

### 13a: Question Execution + Response Validation

Run each of 40 questions against `/api/executive/ask-v2` for a demo customer (e.g., customer 451) and validate:

| Check | Pass Criteria |
|-------|--------------|
| Non-empty response | Response length > 50 chars (not "I don't have that info") |
| Contains data | Response includes at least 1 number (dollar amount, score, percentage) |
| Persona tone | CSM gets tactical language, CFO gets financial, CRO gets revenue |
| Tools called | At least 1 MCP tool invoked (not just LLM hallucination) |
| No errors | HTTP 200, no error/fallback field in response |
| Follow-up works | Ask a clarifying question → response maintains context |

**Test matrix:**

| Persona | Total Questions | Expected Pass (today) | After simulation tools |
|---------|----------------|----------------------|----------------------|
| CSM | 10 | 8/10 | 10/10 |
| CRO | 10 | 8/10 | 10/10 |
| CFO | 10 | 7/10 | 9/10 (benchmark Q still needs external data) |
| VP CS | 10 | 7/10 | 10/10 |

### 13b: Cross-Persona Consistency

Same underlying data, different personas — numbers must match:

| Test | What to compare |
|------|----------------|
| At-risk ARR | CSM "which accounts dropped?" vs CRO "how much ARR at risk?" → same $ |
| ROI total | CFO "investment returning per dollar?" vs CRO "revenue protected?" → consistent |
| Account count | All 4 personas referencing account list → same count |
| Health scores | CSM account detail vs VP CS portfolio summary → same scores |

### 13c: Regression Tracking

Save baseline responses (question → response summary → tools called → key numbers) and compare on subsequent runs:

- New question that previously passed now returns empty → REGRESSION
- Dollar amount changed by >10% with same data → REGRESSION
- Tool that was previously called is no longer called → REGRESSION

**Report output:**
```
Ask AI Persona Validation — Customer 451
──────────────────────────────────────────────
Persona    Passed   Failed   Regressed   New
CSM        8/10     2/10     0           0
CRO        8/10     2/10     0           0
CFO        7/10     3/10     0           0
VP CS      7/10     3/10     0           0
──────────────────────────────────────────────
TOTAL      30/40    10/40    0           0

Failed questions (need simulation tools):
  CSM-9:  "If GPU drops 10%..." → simulate_kpi_change not available
  CRO-2:  "What happens to NRR if..." → simulate_portfolio_loss not available
  CRO-9:  "If we had 2 more CSMs..." → get_csm_workload not available
  CFO-4:  "If we increase investment..." → needs configurable Power of 1
  CFO-9:  "How does efficiency compare..." → needs external benchmarks
  CFO-6:  "Compounding effect..." → partial (explanation ok, numbers uncertain)
  VPCS-7: "If I hire 1 more CSM..." → get_csm_workload not available
  VPCS-9: "Signal to drop lag..." → get_signal_to_health_lag not available
  VPCS-8: "Health up but signals negative..." → complex correlation query
  CRO-10: "Distribution this Q vs last..." → needs historical distribution comparison

Cross-persona consistency: 4/4 PASS
```

**Files:**
- NEW: `load-driver/scenarios/scenario_ask_ai_validation.py` (~300 lines)
- NEW: `load-driver/ask_ai_questions.json` — 40 questions with expected tool calls and validation rules
- MODIFY: `load-driver/run_scenario.py` — register as scenario '13'
- MODIFY: `kpi-dashboard/backend/test_runner_api.py` — add to SCENARIO_META

**Effort:** 8-10 hours

---

## Grand Total (All Phases)

| Phases | Effort | Category |
|--------|--------|----------|
| 1-4 (Bridge + UI polish) | 10-15h | Unblock Test Runner |
| 5-9 (Streaming + reports) | 28-37h | Advanced load driver |
| 10-11 (E2E + push signals) | 16-20h | Pipeline verification |
| 12a-o (Operational workflows) | ~34h | Production safety |
| 12p (ROI Dashboard validation) | 6-8h | Data consistency + repeatability |
| 13 (Ask AI persona validation) | 8-10h | Persona question coverage + regression |
| **TOTAL** | **102-124h** | |

## Decision Needed

- Phase 1 is required — without `run_scenario.py`, the Test Runner UI can't execute scenarios
- Phase 12a/12b/12i/12l/12n are CRITICAL — should these be prioritized above streaming (P5) and reports (P9)?
- Phase 6 (concurrent) — what's the target concurrency? 5 customers? 50? Affects design
- Should the E2E pipeline report be viewable in the Test Runner UI or CLI-only initially?
