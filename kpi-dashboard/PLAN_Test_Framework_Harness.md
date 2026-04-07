# Test Framework & Harness — Comprehensive Plan

## Current State

| Layer | Framework | Files | Coverage | Verdict |
|-------|-----------|-------|----------|---------|
| **Unit tests** | pytest | 30 organized + 75 scattered | Scoring, KPI filtering, ROI model | Fragmented — 75 files at backend root, not in tests/ |
| **Feature tests** | pytest + Flask test client | ~15 | Onboarding, playbook triggers, context graph | Decent but gaps in signal engine, MCP tools |
| **Integration tests** | pytest | ~10 | Cross-tenant isolation, portfolio synergy | Good coverage on security boundaries |
| **E2E pipeline tests** | Custom Python (load-driver) | 9 scenarios | Full lifecycle: create → load → score → wizard → clean | Strong — but runs against live server only, no local mock |
| **Stress/load tests** | Custom Python (docker-compose) | 3 concurrent | 3 customers parallel, 50-60 min each | Works but non-standard (no Locust/k6 metrics) |
| **Frontend tests** | Jest (react-scripts) | 2 files | KPI filtering, playbook definitions | Nearly zero UI test coverage |
| **CI** | GitHub Actions | 1 workflow | KPI filtering only | Critically underpowered — most tests never run in CI |

**Root problems:**
1. 75 test files scattered at `backend/` root — no one knows what's current vs stale
2. CI only runs 1 test workflow — PRs land untested
3. Zero frontend component tests
4. No performance baselines (API latency, DB query time, throughput)

---

## Sprint 1: Foundation — Organize + CI (2 days)

### 1.1 Consolidate Test Files

**Problem:** 75 test files at `backend/` root, 30 in `backend/tests/`. No one knows which are current.

| Action | Details |
|--------|---------|
| Move all `backend/test_*.py` → `backend/tests/` | Organize into subdirectories: `tests/unit/`, `tests/feature/`, `tests/integration/`, `tests/e2e/` |
| Delete stale tests | Any test that imports removed modules or fails on import → delete |
| Create `tests/conftest.py` | Shared fixtures: Flask test app, DB session, sample customer/account factory, mock LLM responses |
| Create `pytest.ini` | Configure: `testpaths = tests`, `markers` for unit/feature/integration/e2e, `--strict-markers` |

**Directory structure after:**
```
backend/tests/
├── conftest.py                  # Shared fixtures, factories
├── unit/                        # Pure logic, no DB, no HTTP
│   ├── test_score_calculator.py
│   ├── test_health_thresholds.py
│   ├── test_arc_classifier.py
│   ├── test_collision.py
│   ├── test_urgency.py
│   ├── test_fusion.py
│   └── test_topology_validator.py
├── feature/                     # Single feature, uses DB, mocked externals
│   ├── test_kpi_filtering.py
│   ├── test_playbook_triggers.py
│   ├── test_signal_enrichment.py
│   ├── test_context_graph_edges.py
│   ├── test_weight_calibration.py
│   └── test_onboarding_upload.py
├── integration/                 # Multiple features, real DB, real HTTP
│   ├── test_tenant_isolation.py
│   ├── test_portfolio_synergy.py
│   ├── test_mcp_interfaces.py
│   └── test_process_data_pipeline.py
└── e2e/                         # Full lifecycle, live server
    ├── test_onboarding_e2e.py
    └── test_context_graph_e2e.py
```

### 1.2 CI Pipeline — Run Tests on Every PR

**Problem:** Only 1 GitHub Actions workflow. PRs land untested.

| File | Change |
|------|--------|
| `.github/workflows/cspulse-tests.yml` | **NEW** — Triggered on PR to main. 3 jobs: (1) `unit-tests`: pytest tests/unit/ (fast, no DB), (2) `feature-tests`: pytest tests/feature/ (needs PostgreSQL service), (3) `frontend-tests`: npm test (Jest). Fail PR if any job fails. |
| `.github/workflows/cspulse-ecr-build-push.yml` | Already runs unit tests on push to main — keep as-is |

**CI matrix:**
```yaml
jobs:
  unit-tests:     # ~30 seconds, no dependencies
  feature-tests:  # ~2 minutes, needs postgres service container
  frontend-tests: # ~1 minute, npm test
```

### 1.3 Test Factories & Fixtures

| File | Change |
|------|--------|
| `tests/conftest.py` | Enhanced with: `create_customer()`, `create_account(customer_id, health=70, arr=1000000)`, `create_kpi_measurement(account_id, kpi_code, value)`, `create_health_score(account_id, score)`, `create_context_node(account_id, node_type, subtype)`. All use `db.session` with transaction rollback per test. |
| `tests/factories.py` | **NEW** — `CustomerFactory`, `AccountFactory`, `KPIFactory` using factory_boy or plain functions. Deterministic seeds for reproducibility. |

---

## Sprint 2: Unit Tests — Cover Business Logic (2 days)

### 2.1 Scoring Engine Unit Tests

| Test File | What It Tests | Key Assertions |
|-----------|---------------|----------------|
| `test_score_calculator.py` | L1 KPI scoring, L2 pillar rollup, L3 health score | Correct weight application, boundary values (0, 50, 70, 100), missing KPI handling |
| `test_health_thresholds.py` | classify(), classifyColor(), threshold boundaries | critical <50, at_risk 50-69, healthy ≥70 |
| `test_arc_classifier.py` | Arc type detection from health trajectory | champion_loss, silent_churn, stalled_deployment patterns |
| `test_topology_validator.py` | Orphan detection, broken chains, score computation | Empty graph=0, perfect graph=100, missing node types flagged |

### 2.2 Signal Engine Unit Tests

| Test File | What It Tests | Key Assertions |
|-----------|---------------|----------------|
| `test_collision.py` | CG collision detection, dedup windows | Collision found within window, no collision outside window, correct action (enrich/suppress) |
| `test_urgency.py` | Structural urgency classification | champion_loss=critical, usage_decline=high, feature_request=low |
| `test_fusion.py` | Composite score fusion (qual + quant) | Correct blending ratios, cold-start ramp, vertical-specific weights |
| `test_enrichment.py` | Enrichment validation, stub fallback | Valid JSON output, intent codes validated, confidence threshold → requires_review |

### 2.3 Context Graph Unit Tests

| Test File | What It Tests | Key Assertions |
|-----------|---------------|----------------|
| `test_arc_edge_generator.py` | Edge topology generation per arc type | Correct edge types (LED_TO, TRIGGERED, INVOLVES), temporal ordering respected |
| `test_story_arc_loader.py` | Arc manifest loading, schema validation | All 8 arcs load, required fields present, phase ordering correct |

---

## Sprint 3: Feature + Integration Tests (2 days)

### 3.1 Feature Tests (Single Feature, Real DB)

| Test File | What It Tests | Setup |
|-----------|---------------|-------|
| `test_onboarding_upload.py` | CSV upload → validation → DB insertion | Create customer, upload accounts.csv, verify Account records created |
| `test_process_data_pipeline.py` | Upload → process_data → health scores | Upload CSVs, trigger pipeline, verify HealthScore records with correct values |
| `test_signal_enrichment.py` | Signal ingest → enrichment worker pickup | POST signal via webhook, wait for enrichment, verify intent_signals populated |
| `test_playbook_auto_trigger.py` | Health drop → arc detection → playbook execution | Create at-risk account, run Wizard A, verify PlaybookExecutionV2 created |
| `test_weight_change_audit.py` | Config update → activity log with before/after | Change pillar weights, verify ActivityLog entry has before_values + after_values |
| `test_context_graph_stakeholder_involves.py` | Signal ingest → stakeholder INVOLVES edges | Upload stakeholders + decisions, verify INVOLVES edges created |

### 3.2 Integration Tests (Cross-Feature)

| Test File | What It Tests | Setup |
|-----------|---------------|-------|
| `test_tenant_isolation.py` | Customer A can't see Customer B's data | Create 2 customers, verify cross-tenant queries return empty |
| `test_mcp_tool_chain.py` | list_accounts → get_account_health → get_playbook_recommendations | Full MCP tool chain with real data |
| `test_nrr_forecast_accuracy.py` | Health scores → NRR projection → waterfall | Verify NRR formula matches expected output for known health distributions |

### 3.3 API Contract Tests

| File | Change |
|------|--------|
| `tests/integration/test_api_contracts.py` | **NEW** — For each critical API endpoint, verify: (1) correct HTTP status codes, (2) response schema matches expected shape, (3) error responses include error field. Covers: /api/dc2s/accounts, /api/executive/cro-dashboard, /api/executive/cfo-dashboard, /api/context-graph/summary, /api/onboarding/upload |

---

## Sprint 4: Frontend Tests + E2E Pipeline (2 days)

### 4.1 Frontend Component Tests

| Test File | What It Tests | Framework |
|-----------|---------------|-----------|
| `CSMDashboard.test.tsx` | Layout switcher renders, focus/cockpit toggle works | Jest + React Testing Library |
| `OnboardingWizard.test.tsx` | 4-step flow, file upload triggers, step navigation | Jest + RTL |
| `SuperAdminConsole.test.tsx` | Activity log filter controls, customer list rendering | Jest + RTL |
| `healthThresholds.test.ts` | classify(), classifyColor() utility | Jest |
| `activityTracker.test.ts` | trackPageView(), trackEvent() fire fetch calls | Jest + fetch mock |

### 4.2 E2E Pipeline Test (User-Complete-V1 Enhanced)

| File | Change |
|------|--------|
| `load-driver/tests/user_complete_v2.py` | **NEW** — 4-phase test against live server: (1) Create customer via manifest, (2) Verify all 5 persona dashboards return data (CSM, VP CS, CRO, CFO, CEO), (3) Run 40 persona questions via Flask REST API, (4) Verify context graph topology score ≥ 50. Uses `topology_test_dc2s.json` manifest. |

### 4.3 Performance Baseline Test

| File | Change |
|------|--------|
| `load-driver/tests/test_performance_baseline.py` | **NEW** — Measure and assert: (1) `/api/dc2s/accounts` < 500ms, (2) `/api/executive/cro-dashboard` < 2s, (3) `/api/onboarding/process-data` completes < 30s for 5 accounts, (4) `/api/context-graph/summary` < 200ms. Store baselines in JSON for regression detection. |

---

## Sprint 5: Stress & Load Tests (1 day)

### 5.1 Locust Load Test

| File | Change |
|------|--------|
| `load-driver/locustfile.py` | **NEW** — Locust load test with user classes: (1) CSMUser: polls accounts, daily-actions, health-summary every 60s, (2) CROUser: polls cro-dashboard, revenue-timeline every 120s, (3) AdminUser: creates customer, uploads CSV, triggers process_data. Target: 50 concurrent users, 5 min run, p95 < 2s. |
| `load-driver/locust.conf` | **NEW** — Config: host, users=50, spawn-rate=5, run-time=5m |

### 5.2 Concurrent Customer Stress Test

| File | Change |
|------|--------|
| `load-driver/tests/test_10customer_concurrent.py` | **NEW** — Create 10 customers simultaneously (ThreadPoolExecutor), each with 5 accounts. Verify: no FK violations, no deadlocks, all 10 complete within 120s, health scores correct for all 50 accounts. |

---

## Files Summary

| Sprint | New Files | Modified Files |
|--------|-----------|----------------|
| 1 | pytest.ini, tests/factories.py, .github/workflows/cspulse-tests.yml | tests/conftest.py, move 75 files |
| 2 | 8 unit test files | — |
| 3 | 9 feature + integration test files | — |
| 4 | 5 frontend test files, user_complete_v2.py, test_performance_baseline.py | — |
| 5 | locustfile.py, locust.conf, test_10customer_concurrent.py | — |

**Total: ~28 new test files, 1 new CI workflow across 5 sprints (~9 days)**

## Test Execution Matrix

| Layer | Command | When | Duration |
|-------|---------|------|----------|
| **Unit** | `pytest tests/unit/ -v` | Every PR (CI) | ~30s |
| **Feature** | `pytest tests/feature/ -v` | Every PR (CI) | ~2 min |
| **Integration** | `pytest tests/integration/ -v` | Nightly or pre-release | ~5 min |
| **Frontend** | `npm test -- --coverage` | Every PR (CI) | ~1 min |
| **E2E pipeline** | `python tests/user_complete_v2.py` | Pre-release | ~3 min |
| **Performance** | `python tests/test_performance_baseline.py` | Weekly | ~1 min |
| **Load/stress** | `locust -f locustfile.py` | Pre-release | ~5 min |
| **Concurrent** | `python tests/test_10customer_concurrent.py` | Pre-release | ~2 min |
