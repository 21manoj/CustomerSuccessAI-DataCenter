# External Load Driver — Gap Analysis & Execution Plan
## CS Pulse Platform — Non-Intrusive E2E Testing via Separate Docker Instance

**Date:** 2026-02-24
**Customer ID:** 1
**Target:** 50 DC accounts, full lifecycle test
**Deployment:** Separate Dockerfile on separate EC2 at AWS
**Constraint:** Zero restarts of the CS Pulse platform

---

## Architecture Overview

```
┌──────────────────────────┐        ┌──────────────────────────┐
│  EC2 #1 — CS Pulse       │        │  EC2 #2 — Load Driver    │
│  (PRODUCTION / STAGING)  │        │  (TEST HARNESS)          │
│                          │        │                          │
│  docker-compose.yml      │  HTTP  │  Dockerfile.loaddriver   │
│  ├─ backend (5059)  ◄────┼────────┤  ├─ driver.py            │
│  ├─ frontend (3000)      │        │  ├─ scenario_*.py        │
│  └─ postgres (5432)      │        │  ├─ config.env           │
│                          │        │  └─ results/             │
└──────────────────────────┘        └──────────────────────────┘
```

The load driver runs in its own Docker container, connects to CS Pulse via HTTP API only, and writes all results to `results/` as `.md` and `.json` files.

---

## Test Scenarios & Gap Analysis

### Scenario 1: Onboard a New DC Customer with 50 Accounts

**Goal:** Create customer_id=1, 50 accounts, synthetic CSV data, full onboarding wizard flow.

#### What EXISTS today

| Component | File | Status |
|-----------|------|--------|
| Onboarding API (config-aware v2) | `onboarding_api_v2_config_aware.py` | EXISTS |
| `POST /api/onboarding/complete` | accepts `num_accounts` param | EXISTS — tested up to 25 |
| `POST /api/onboarding/upload` | CSV upload (kpis, accounts, signals) | EXISTS |
| `POST /api/onboarding/process-data` | Load CSVs → DB | EXISTS |
| Synthetic data generator | `scripts/generate_synthetic_dc2s_data.py` | EXISTS |
| 25-account seed script | `generate_25_accounts_seed_data.py` | EXISTS (SaaS model) |
| DC2_S vertical config | `verticals/dc2_s/vertical_config.py` | EXISTS |
| Customer directory provisioning | Auto-creates `verticals/customer{N}-dc2_s/` | EXISTS |
| Sample account structure | `sample_accounts.py` (10 accounts, 3 tiers) | EXISTS |

#### What's MISSING (Gaps)

| Gap | Description | Effort |
|-----|-------------|--------|
| **GAP-LD-1** | **50-account CSV generator for DC2_S** — `generate_synthetic_dc2s_data.py` exists but needs a wrapper that generates 50 accounts with realistic tier distribution (15 healthy, 20 at-risk, 15 critical) and 12 months of KPI history across all 38 DC2_S KPIs. The existing generator handles per-account CSV but the load driver needs a single orchestrator that calls it for 50 accounts. | LOW |
| **GAP-LD-2** | **Load driver onboarding script** — No script exists that calls the onboarding API endpoints in sequence from an external process: (1) POST `/api/onboarding/complete`, (2) generate CSVs, (3) POST `/api/onboarding/upload` for each file type, (4) POST `/api/onboarding/process-data`. Need a `scenario_onboarding.py` that orchestrates this via HTTP. | MEDIUM |
| **GAP-LD-3** | **Authentication session management** — Load driver needs to authenticate first (`POST /api/login`) and carry the session cookie for all subsequent requests. Existing E2E tests (`test_onboarding_e2e.py`) use `requests.Session()` — pattern exists but no reusable client wrapper. | LOW |
| **GAP-LD-4** | **Health check + readiness gate** — Load driver should verify platform is healthy before starting (`GET /api/health`). Pattern exists in `test_config.py` but no retry/wait logic for startup. | LOW |

#### Existing Code to Leverage

```python
# Onboarding payload (from onboarding_api_v2_config_aware.py)
POST /api/onboarding/complete
{
    "customer_id": 1,
    "customer_name": "Load Test Enterprise",
    "vertical": "dc2_s",
    "email": "loadtest@cspulse.ai",
    "password": "LoadTest2026!",
    "num_accounts": 50,
    "weights": {"AI": 0.25, "CH": 0.20, "DV": 0.30, "EX": 0.10, "OS": 0.15}
}

# CSV upload (from onboarding_api_v2_config_aware.py)
POST /api/onboarding/upload
Form: file=@kpi_measurements.csv, customer_id=1, file_type=kpis

# Process data
POST /api/onboarding/process-data
{"customer_id": 1, "upload_mode": "incremental", "strict_kpi_ranges": true}
```

---

### Scenario 2a: KPI Simulation — Generate Runtime Events/KPIs/Scores for 50 Accounts

**Goal:** Simulate real-world KPI drift over time, trigger health score recalculation, generate events — all without restarting the platform.

#### What EXISTS today

| Component | File | Status |
|-----------|------|--------|
| Health score calculation API | `dc2s_scores_api.py` | EXISTS |
| `POST /api/dc2s/scores/calculate` | Accepts `account_id` or all | EXISTS |
| Event system with subscribers | `event_system.py` | EXISTS |
| Auto-snapshot on data change | `AccountSnapshotSubscriber` | EXISTS |
| Health score rollup subscriber | `HealthScoreRollupSubscriber` | EXISTS |
| KPI upload via CSV | `POST /api/onboarding/upload` | EXISTS |
| KPI data model (DC2SKPI) | `models.py` — `DC2SKPI` table | EXISTS |
| Health trend tracking | `models.py` — `HealthTrend` table | EXISTS |
| Account snapshot API | `account_snapshot_api.py` | EXISTS |

#### What's MISSING (Gaps)

| Gap | Description | Effort |
|-----|-------------|--------|
| **GAP-LD-5** | **KPI mutation simulator** — No script exists that takes current KPI values and applies realistic drift (±5-15% per period, with some accounts degrading toward churn and others improving). Need `scenario_kpi_simulation.py` that: (1) reads current KPIs via API, (2) applies configurable drift profiles per tier, (3) uploads mutated CSVs, (4) triggers score recalculation, (5) verifies events fired. | MEDIUM |
| **GAP-LD-6** | **Bulk score recalculation trigger** — `POST /api/dc2s/scores/calculate` exists but calculates one-at-a-time. For 50 accounts, the load driver needs to batch or loop through all accounts and measure latency. No batch endpoint exists. | LOW |
| **GAP-LD-7** | **Event verification endpoint** — The event audit trail is in-memory only (`event_system.py:68-105`). Load driver can't verify events fired without reading in-memory state. Need either: (a) `GET /api/events/log` endpoint (planned in GAP-10 but not built), or (b) activity log queries via `GET /api/activity-log` (exists). | LOW — activity log exists as proxy |
| **GAP-LD-8** | **Multi-month simulation loop** — Need to simulate 6-12 months of KPI evolution in a compressed timeframe. Each iteration = one month of data: upload → process → score → verify. No such loop exists. | MEDIUM |

#### Existing Code to Leverage

```python
# Score calculation (from dc2s_scores_api.py)
POST /api/dc2s/scores/calculate
{"measurement_month": "2025-06-01"}  # All accounts

# Retrieve scores
GET /api/dc2s/scores/customer/summary

# Check events (via activity log)
GET /api/activity-log?action_type=score_calculation&category=health
```

---

### Scenario 2b: RAG Queries for 5 Random Accounts ($$ cost control)

**Goal:** Run contextual RAG queries for 5 randomly selected accounts, verify response quality, measure latency and cost.

#### What EXISTS today

| Component | File | Status |
|-----------|------|--------|
| Direct RAG query API | `direct_rag_api.py` | EXISTS |
| `POST /api/direct-rag/query` | Full implementation with cost tracking | EXISTS |
| RAG status endpoint | `GET /api/direct-rag/status` | EXISTS |
| Query audit logging | `QueryAudit` model in `models.py` | EXISTS |
| Conversation history support | Multi-turn with customer_id validation | EXISTS |
| Playbook-enhanced responses | Citations from playbook reports | EXISTS |
| Response caching | 5-min TTL for non-conversation queries | EXISTS |
| Cost estimation | `$0.02` per query logged | EXISTS |

#### What's MISSING (Gaps)

| Gap | Description | Effort |
|-----|-------------|--------|
| **GAP-LD-9** | **RAG query scenario script** — No script exists that selects 5 random accounts and runs contextual queries. Need `scenario_rag_queries.py` that: (1) picks 5 accounts randomly, (2) runs 3-5 queries per account (health, risk, expansion, playbook recommendation), (3) validates response contains account-specific data, (4) records latency + cost, (5) grades response quality (contains health score, account name, KPI data). | MEDIUM |
| **GAP-LD-10** | **Query template library** — No predefined query templates for load testing. Need 15-20 templates: `"What is the health status of {account_name}?"`, `"Which KPIs are at risk for {account_name}?"`, `"Should we run a renewal safeguard for {account_name}?"`, etc. | LOW |
| **GAP-LD-11** | **Cost budget enforcement** — No mechanism to cap total RAG spend per test run. Load driver should track cumulative cost and abort if budget exceeded (e.g., $5 max per run = ~250 queries). | LOW |

#### Existing Code to Leverage

```python
# RAG query (from direct_rag_api.py)
POST /api/direct-rag/query
{
    "query": "What is the health status of CloudScale AI Labs?",
    "query_type": "health"
}
# Response includes: response, results_count, cost, playbook_enhanced
```

---

### Scenario 2c: Signal Detection → Churn/Expansion → Playbook Triggers

**Goal:** Run signal analyst on degraded accounts to detect churn signals, run on healthy accounts to detect expansion signals, and trigger appropriate playbooks.

#### What EXISTS today

| Component | File | Status |
|-----------|------|--------|
| Signal analyst API | `agents/signal_analyst_api.py` | EXISTS |
| `POST /api/signal-analyst/analyze` | Full analysis with LLM | EXISTS |
| `POST /api/signal-analyst/analyze-with-loop` | Agentic loop (6-step) | EXISTS |
| Playbook recommendations | `playbook_recommendations_api.py` | EXISTS |
| `POST /api/playbooks/recommendations/{playbook_id}` | Per-playbook recommendations | EXISTS |
| Playbook trigger evaluation | `POST /api/playbook-triggers/evaluate-all` | EXISTS |
| Playbook execution API | `POST /api/playbooks/executions` | EXISTS |
| Approval queue | `approval_queue.py` | EXISTS |
| Event: `PLAYBOOK_AUTO_TRIGGERED` | Published by agentic loop | EXISTS |
| Event: `AGENT_ANALYSIS_COMPLETE` | Published by agentic loop | EXISTS |
| Test endpoint (mock data) | `POST /api/signal-analyst/test` | EXISTS |

#### What's MISSING (Gaps)

| Gap | Description | Effort |
|-----|-------------|--------|
| **GAP-LD-12** | **Signal detection scenario script** — No script that runs signal analysis across multiple accounts and classifies results. Need `scenario_signal_detection.py` that: (1) selects degraded accounts (health < 65), (2) runs `POST /api/signal-analyst/analyze` on each, (3) verifies churn_probability > 0.3 for degraded accounts, (4) selects healthy accounts (health > 80), (5) runs analysis, (6) verifies expansion_probability > 0.5. | MEDIUM |
| **GAP-LD-13** | **Playbook trigger orchestration** — No end-to-end script that goes signal → recommendation → trigger → execute. Need to chain: (1) `POST /api/signal-analyst/analyze-with-loop`, (2) `POST /api/playbooks/recommendations/renewal-safeguard`, (3) `POST /api/playbooks/executions` for triggered accounts. Existing code does each step independently. | MEDIUM |
| **GAP-LD-14** | **Signal analysis costs $$ (LLM)** — Each `POST /api/signal-analyst/analyze` call hits OpenAI/Anthropic (~$0.05-0.15 per call). For 50 accounts, that's $2.50-$7.50. Need: (a) budget cap like RAG, (b) option to use `/api/signal-analyst/test` endpoint (mock data, $0) for non-LLM tests, (c) batch only critical accounts. | LOW |

#### Existing Code to Leverage

```python
# Signal analysis (from signal_analyst_api.py)
POST /api/signal-analyst/analyze
{"account_id": 1001, "analysis_type": "comprehensive", "provider": "openai"}

# With agentic loop (6-step: Analyze → Evaluate → Enrich → Quantify → Decide → Act)
POST /api/signal-analyst/analyze-with-loop
{"account_id": 1001, "analysis_type": "churn_risk"}

# Playbook recommendations
POST /api/playbooks/recommendations/renewal-safeguard
# Returns: accounts_needing_playbook, urgency_counts

# Trigger evaluation
POST /api/playbook-triggers/evaluate-all
# Returns: which triggers fired

# Create execution
POST /api/playbooks/executions
{"playbookId": "renewal-safeguard", "context": {"account_id": 1001}}
```

---

### Scenario 2d: RACI Report Generation

**Goal:** Generate RACI reports for executed playbooks and save to test output files.

#### What EXISTS today

| Component | File | Status |
|-----------|------|--------|
| Playbook report API | `playbook_reports_api.py` | EXISTS |
| `GET /api/playbooks/executions/{id}/report` | Full RACI + outcomes | EXISTS |
| Report export | `GET /api/playbooks/reports/export/{id}` | EXISTS (JSON) |
| Executive summary report | `report_generation_agent.py` | EXISTS |
| `GET /api/reports/executive-summary` | Portfolio-level report | EXISTS |
| GAP-9 report generator | `generate_gap9_report.py` | EXISTS |
| PlaybookReport model | RACI matrix, outcomes, exit criteria in JSON | EXISTS |

#### What's MISSING (Gaps)

| Gap | Description | Effort |
|-----|-------------|--------|
| **GAP-LD-15** | **RACI report scenario script** — No script that retrieves RACI reports and saves them to files. Need `scenario_raci_report.py` that: (1) lists all executions via `GET /api/playbooks/executions`, (2) for each completed execution, fetches report via `GET /api/playbooks/executions/{id}/report`, (3) saves RACI matrix as markdown table, (4) saves outcomes + exit criteria, (5) writes to `results/raci_report_{execution_id}.md`. | LOW |
| **GAP-LD-16** | **Report existence depends on playbook execution** — RACI reports are generated during playbook execution. If Scenario 2c doesn't create executions, there are no reports to fetch. This is a dependency, not a code gap. | N/A — ordering dependency |
| **GAP-LD-17** | **Markdown export** — Report export is JSON only (`GET /api/playbooks/reports/export/{id}`). Load driver needs to convert JSON RACI to markdown table format for human-readable output. | LOW |

#### Existing Code to Leverage

```python
# List executions
GET /api/playbooks/executions?status=completed

# Get RACI report
GET /api/playbooks/executions/{execution_id}/report
# Returns: raci_matrix, outcomes_achieved, exit_criteria, next_steps

# Executive summary (portfolio-level)
GET /api/reports/executive-summary?arr=25000000
```

---

### Scenario 2e: Churned Account Archival & Deletion

**Goal:** Verify that accounts predicted as churned can be archived and deleted, and that deletion cascades correctly.

#### What EXISTS today

| Component | File | Status |
|-----------|------|--------|
| Account model with `account_status` | `models.py` — `active\|inactive\|at_risk` | EXISTS |
| Cleanup API | `cleanup_api.py` | EXISTS |
| Bulk deletion script | `delete_customers_109_112.py` | EXISTS (manual) |
| Cascade delete (20+ tables) | Ordered deletion logic | EXISTS |
| Activity logging for deletions | `ActivityLogger.log_account_update()` | EXISTS |
| Data verification after delete | Count checks per table | EXISTS |
| Foreign key CASCADE | `ondelete='CASCADE'` on customer_id | EXISTS |

#### What's MISSING (Gaps)

| Gap | Description | Effort |
|-----|-------------|--------|
| **GAP-LD-18** | **Account archival API endpoint** — No `PUT /api/accounts/{id}/archive` or `PATCH` endpoint exists. The Account model has `account_status` (active/inactive/at_risk) but there's no API to transition an account to `inactive` status. Current account updates go through `customer_management_api.py` but archival-specific logic (freeze data, mark inactive, log reason) doesn't exist. | MEDIUM |
| **GAP-LD-19** | **Account deletion API endpoint** — No `DELETE /api/accounts/{id}` endpoint exists. Deletion is only via manual scripts (`delete_customers_109_112.py`). Need an API endpoint that: (1) validates account is inactive/churned, (2) cascades deletes across DC2SKPI, HealthTrend, AccountSnapshot, AccountNote, PlaybookExecution, etc., (3) logs deletion in activity log, (4) returns confirmation. | MEDIUM |
| **GAP-LD-20** | **Churn → Archive → Delete lifecycle script** — No end-to-end flow exists. Need `scenario_churn_lifecycle.py` that: (1) identifies churned accounts (churn_probability > 0.7 from signal analyst), (2) marks as `inactive` via archive API, (3) verifies data is frozen (no new scores generated), (4) deletes account via deletion API, (5) verifies cascade (no orphan records in dc2s_kpis, health_trends, etc.), (6) confirms activity log recorded the deletion. | MEDIUM |
| **GAP-LD-21** | **Verification queries** — After deletion, need to verify no orphan records remain. No verification endpoint exists. Load driver needs to query: `GET /api/dc2s/scores/account/{id}/latest` (should return 404), `GET /api/accounts?account_id={id}` (should return empty). | LOW |

#### Existing Code to Leverage

```python
# Deletion pattern (from delete_customers_109_112.py)
# Order: QueryAudit → AccountNote → AccountSnapshot → ActivityLog →
#         PlaybookReport → PlaybookExecution → PlaybookTrigger →
#         FeatureToggle → KPIReferenceRange → KPITimeSeries →
#         HealthTrend → DC2SKPI → KPI → KPIUpload → Product →
#         Account → User → CustomerConfig → Customer

# Account status update pattern (from customer_management_api.py)
# Can update account fields via existing endpoints
```

---

## Infrastructure Gaps (Docker / Deployment)

| Gap | Description | Effort |
|-----|-------------|--------|
| **GAP-LD-22** | **Load driver Dockerfile** — No `Dockerfile.loaddriver` exists. Need a lightweight Python 3.11 image with `requests`, `pandas`, `faker` (for synthetic data), and the scenario scripts. Should NOT include Flask or the full backend — driver is HTTP-only. | LOW |
| **GAP-LD-23** | **Load driver docker-compose** — No `docker-compose.loaddriver.yml` exists. Needs: (1) `CS_PULSE_BASE_URL` env var pointing to CS Pulse EC2, (2) `OPENAI_API_KEY` for RAG/signal tests, (3) volume mount for `results/` output, (4) configurable `CUSTOMER_ID`, `NUM_ACCOUNTS`, `RAG_BUDGET`, `SIGNAL_BUDGET`. | LOW |
| **GAP-LD-24** | **Results aggregator** — No test results aggregation. Need a `results_aggregator.py` that reads all scenario outputs and produces a single `LOAD_TEST_RESULTS.md` with pass/fail per scenario, timing, costs, and error details. | LOW |
| **GAP-LD-25** | **Network connectivity** — Load driver on separate EC2 needs HTTP access to CS Pulse EC2 on port 5059. Security group / VPC peering may be needed. This is infra, not code. | INFRA |

---

## Gap Summary Matrix

| ID | Gap | Scenario | Exists? | Effort | Priority |
|----|-----|----------|---------|--------|----------|
| LD-1 | 50-account CSV generator | 1 | Partial | LOW | P0 |
| LD-2 | Onboarding scenario script | 1 | NO | MEDIUM | P0 |
| LD-3 | Auth session client wrapper | All | Partial | LOW | P0 |
| LD-4 | Health check readiness gate | All | Partial | LOW | P0 |
| LD-5 | KPI mutation simulator | 2a | NO | MEDIUM | P1 |
| LD-6 | Bulk score recalculation | 2a | Partial | LOW | P1 |
| LD-7 | Event verification | 2a | Partial | LOW | P2 |
| LD-8 | Multi-month simulation loop | 2a | NO | MEDIUM | P1 |
| LD-9 | RAG query scenario script | 2b | NO | MEDIUM | P1 |
| LD-10 | Query template library | 2b | NO | LOW | P1 |
| LD-11 | Cost budget enforcement | 2b | NO | LOW | P1 |
| LD-12 | Signal detection scenario | 2c | NO | MEDIUM | P1 |
| LD-13 | Playbook trigger orchestration | 2c | NO | MEDIUM | P1 |
| LD-14 | Signal analysis cost cap | 2c | NO | LOW | P1 |
| LD-15 | RACI report scenario script | 2d | NO | LOW | P2 |
| LD-16 | Report depends on execution | 2d | N/A | N/A | — |
| LD-17 | Markdown export for RACI | 2d | NO | LOW | P2 |
| LD-18 | Account archival API | 2e | NO | MEDIUM | P1 |
| LD-19 | Account deletion API | 2e | NO | MEDIUM | P1 |
| LD-20 | Churn lifecycle script | 2e | NO | MEDIUM | P1 |
| LD-21 | Deletion verification queries | 2e | Partial | LOW | P2 |
| LD-22 | Load driver Dockerfile | Infra | NO | LOW | P0 |
| LD-23 | Load driver docker-compose | Infra | NO | LOW | P0 |
| LD-24 | Results aggregator | Infra | NO | LOW | P2 |
| LD-25 | Network / security groups | Infra | NO | INFRA | P0 |

**Legend:** P0 = Must have before any test runs. P1 = Core test scenarios. P2 = Nice to have.

---

## Effort Estimates

| Category | Gaps | Effort |
|----------|------|--------|
| **P0 — Infrastructure + Foundation** | LD-1,2,3,4,22,23,25 | ~1 day |
| **P1 — Core Scenario Scripts** | LD-5,6,8,9,10,11,12,13,14,18,19,20 | ~2-3 days |
| **P2 — Polish + Reporting** | LD-7,15,17,21,24 | ~0.5 day |
| **Total** | 25 gaps | ~4 days |

---

## Proposed File Structure

```
kpi-dashboard/load-driver/
├── Dockerfile.loaddriver
├── docker-compose.loaddriver.yml
├── config.env.example
├── requirements.txt              # requests, pandas, faker, tabulate
├── driver.py                     # Main orchestrator — runs all scenarios in order
├── client.py                     # HTTP client wrapper (auth, session, retry, health check)
├── scenarios/
│   ├── __init__.py
│   ├── scenario_onboarding.py    # Scenario 1: Create customer + 50 accounts
│   ├── scenario_kpi_simulation.py # Scenario 2a: KPI drift + score recalc
│   ├── scenario_rag_queries.py   # Scenario 2b: 5 random accounts × 3-5 queries
│   ├── scenario_signal_detection.py # Scenario 2c: Churn/expansion signals + playbooks
│   ├── scenario_raci_report.py   # Scenario 2d: Fetch + save RACI reports
│   └── scenario_churn_lifecycle.py # Scenario 2e: Archive + delete churned accounts
├── generators/
│   ├── __init__.py
│   ├── csv_generator.py          # 50-account synthetic DC2_S data
│   ├── kpi_mutator.py            # KPI drift simulator (per-tier profiles)
│   └── query_templates.py        # 20 RAG query templates
├── results/                      # Output directory (volume-mounted)
│   ├── LOAD_TEST_RESULTS.md      # Aggregated results
│   ├── scenario_1_onboarding.json
│   ├── scenario_2a_kpi_simulation.json
│   ├── scenario_2b_rag_queries.json
│   ├── scenario_2c_signal_detection.json
│   ├── scenario_2d_raci_reports/
│   │   └── raci_report_{execution_id}.md
│   └── scenario_2e_churn_lifecycle.json
└── results_aggregator.py         # Combine all results → LOAD_TEST_RESULTS.md
```

---

## Execution Order & Dependencies

```
Scenario 1: Onboarding (50 accounts)
    │
    ▼
Scenario 2a: KPI Simulation (6-12 months compressed)
    │
    ├──► Scenario 2b: RAG Queries (5 random accounts, budget-capped)
    │
    ├──► Scenario 2c: Signal Detection → Playbook Triggers
    │         │
    │         ▼
    │    Scenario 2d: RACI Reports (from executed playbooks)
    │
    └──► Scenario 2e: Churn Lifecycle (archive + delete churned accounts)
```

Scenarios 2b, 2c, and 2e can run in parallel after 2a completes.
Scenario 2d depends on 2c (needs playbook executions to exist).

---

## Platform API Endpoints Used (No Code Changes Needed)

| Endpoint | Method | Scenario | Notes |
|----------|--------|----------|-------|
| `/api/health` | GET | All | Readiness check |
| `/api/login` | POST | All | Session auth |
| `/api/onboarding/complete` | POST | 1 | Creates customer + N accounts |
| `/api/onboarding/upload` | POST | 1, 2a | CSV file upload |
| `/api/onboarding/process-data` | POST | 1, 2a | Load CSVs to DB |
| `/api/dc2s/scores/calculate` | POST | 2a | Health score recalc |
| `/api/dc2s/scores/customer/summary` | GET | 2a | Verify scores |
| `/api/direct-rag/query` | POST | 2b | RAG queries ($$$) |
| `/api/direct-rag/status` | GET | 2b | RAG readiness |
| `/api/signal-analyst/analyze` | POST | 2c | Signal detection ($$$) |
| `/api/signal-analyst/analyze-with-loop` | POST | 2c | Full agentic loop ($$$) |
| `/api/signal-analyst/test` | POST | 2c | Mock signal detection ($0) |
| `/api/playbooks/recommendations/{id}` | POST | 2c | Which accounts need playbook |
| `/api/playbook-triggers/evaluate-all` | POST | 2c | Trigger evaluation |
| `/api/playbooks/executions` | POST/GET | 2c, 2d | Create/list executions |
| `/api/playbooks/executions/{id}/report` | GET | 2d | RACI report |
| `/api/reports/executive-summary` | GET | 2d | Portfolio report |
| `/api/activity-log` | GET | 2e | Verify audit trail |
| `/api/cleanup/status` | GET | 2e | Verify data counts |

## New Platform Endpoints Needed (2 gaps)

| Endpoint | Method | Gap | Purpose |
|----------|--------|-----|---------|
| `PUT /api/accounts/{id}/archive` | PUT | GAP-LD-18 | Transition account to inactive, freeze data |
| `DELETE /api/accounts/{id}` | DELETE | GAP-LD-19 | Cascade delete churned account |

---

## Docker Configuration

### Dockerfile.loaddriver
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["python", "driver.py"]
```

### docker-compose.loaddriver.yml
```yaml
version: '3.8'
services:
  load-driver:
    build:
      context: ./load-driver
      dockerfile: Dockerfile.loaddriver
    environment:
      - CS_PULSE_BASE_URL=http://<cs-pulse-ec2>:5059
      - CUSTOMER_ID=1
      - NUM_ACCOUNTS=50
      - RAG_BUDGET_USD=5.00
      - SIGNAL_BUDGET_USD=10.00
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOGIN_EMAIL=loadtest@cspulse.ai
      - LOGIN_PASSWORD=LoadTest2026!
    volumes:
      - ./results:/app/results
    network_mode: host  # Or use VPC peering
```

### requirements.txt (load-driver)
```
requests>=2.31.0
pandas>=2.1.0
faker>=22.0.0
tabulate>=0.9.0
```

---

## Cost Estimates Per Test Run

| Scenario | API Calls | LLM Calls | Est. Cost |
|----------|-----------|-----------|-----------|
| 1 — Onboarding | ~5 | 0 | $0.00 |
| 2a — KPI Simulation | ~60 (12 months × 5 uploads) | 0 | $0.00 |
| 2b — RAG Queries | 15-25 (5 accounts × 3-5 queries) | 15-25 | $0.30-$0.50 |
| 2c — Signal Detection | ~10 (5 churn + 5 expansion) | 10 | $0.50-$1.50 |
| 2d — RACI Reports | ~5 | 0 | $0.00 |
| 2e — Churn Lifecycle | ~10 | 0 | $0.00 |
| **Total** | **~105-115** | **~25-35** | **$0.80-$2.00** |

---

## Multi-Customer Simulation (2-3 Customers in Parallel)

### How It Works

The load driver can spin up **2-3 customer simulations concurrently**, each with its own session, its own 50 accounts, and its own lifecycle. This is the real-world pattern — multiple tenants running simultaneously.

```
docker-compose.loaddriver.yml
┌──────────────────────────────────────────────┐
│  load-driver-customer-1  (CUSTOMER_ID=1)     │──► 50 accounts (1001-1050)
│  load-driver-customer-2  (CUSTOMER_ID=2)     │──► 50 accounts (2001-2050)
│  load-driver-customer-3  (CUSTOMER_ID=3)     │──► 50 accounts (3001-3050)
└──────────────────────────────────────────────┘
         │  All hit same CS Pulse backend (port 5059)
         ▼
┌──────────────────────────────────────────────┐
│  EC2 #1 — CS Pulse Platform                  │
│  ├─ backend (5059)                           │
│  └─ postgres (5432)                          │
└──────────────────────────────────────────────┘
```

### docker-compose.loaddriver.yml (Multi-Customer)

```yaml
version: '3.8'
services:
  load-driver-cust-1:
    build: { context: ./load-driver, dockerfile: Dockerfile.loaddriver }
    environment:
      - CS_PULSE_BASE_URL=http://<cs-pulse-ec2>:5059
      - CUSTOMER_ID=1
      - CUSTOMER_NAME=Alpha Enterprise
      - LOGIN_EMAIL=admin-alpha@cspulse.ai
      - LOGIN_PASSWORD=Alpha2026!
      - NUM_ACCOUNTS=50
      - RAG_BUDGET_USD=5.00
      - SIGNAL_BUDGET_USD=10.00
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes: [ ./results/customer-1:/app/results ]

  load-driver-cust-2:
    build: { context: ./load-driver, dockerfile: Dockerfile.loaddriver }
    environment:
      - CS_PULSE_BASE_URL=http://<cs-pulse-ec2>:5059
      - CUSTOMER_ID=2
      - CUSTOMER_NAME=Beta Industries
      - LOGIN_EMAIL=admin-beta@cspulse.ai
      - LOGIN_PASSWORD=Beta2026!
      - NUM_ACCOUNTS=50
      - RAG_BUDGET_USD=5.00
      - SIGNAL_BUDGET_USD=10.00
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes: [ ./results/customer-2:/app/results ]

  load-driver-cust-3:
    build: { context: ./load-driver, dockerfile: Dockerfile.loaddriver }
    environment:
      - CS_PULSE_BASE_URL=http://<cs-pulse-ec2>:5059
      - CUSTOMER_ID=3
      - CUSTOMER_NAME=Gamma Corp
      - LOGIN_EMAIL=admin-gamma@cspulse.ai
      - LOGIN_PASSWORD=Gamma2026!
      - NUM_ACCOUNTS=50
      - RAG_BUDGET_USD=5.00
      - SIGNAL_BUDGET_USD=10.00
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes: [ ./results/customer-3:/app/results ]
```

### Account ID Convention

The platform uses `account_id = customer_id × 1000 + N`:

| Customer | customer_id | Account Range | Example |
|----------|-------------|---------------|---------|
| Alpha Enterprise | 1 | 1001 – 1050 | 1001, 1002, ... 1050 |
| Beta Industries | 2 | 2001 – 2050 | 2001, 2002, ... 2050 |
| Gamma Corp | 3 | 3001 – 3050 | 3001, 3002, ... 3050 |

**Important:** This is a **convention, not a DB constraint**. The load driver should always pass `customer_id` in all API calls to enforce proper grouping.

---

## Tenant Isolation Testing (Scenario 3 — NEW)

### Why This Matters

SOC 2 CC6.1 requires logical access controls. Multi-tenant platforms must prove:
1. Customer A cannot see Customer B's data
2. Customer A cannot modify Customer B's accounts
3. Queries are always scoped by `customer_id`

### Current Isolation Model

```
Customer (customer_id=1, uuid=saas_cust_...)
  ├── User (email=admin@alpha.com, customer_id=1) ── SESSION ── all queries scoped
  ├── Account 1001 (customer_id=1)
  │     ├── DC2SKPI (account_id=1001)     ⚠️ NO customer_id FK
  │     ├── HealthScore (account_id=1001)  ⚠️ NO customer_id FK
  │     ├── KPIScore (account_id=1001)     ⚠️ NO customer_id FK
  │     └── QualitativeSignal              ⚠️ NO customer_id FK
  ├── Account 1002 (customer_id=1)
  │     └── ...
  ├── Product (customer_id=1, account_id=1001) ✅ Dual FK
  ├── KPIUpload (customer_id=1) ✅
  ├── HealthTrend (customer_id=1, account_id=1001) ✅ Dual FK
  ├── PlaybookExecution (customer_id=1) ✅
  ├── ActivityLog (customer_id=1) ✅
  └── CustomerConfig (customer_id=1) ✅
```

### Known Isolation Gaps

| Gap | Table | Risk | Current Mitigation |
|-----|-------|------|-------------------|
| **No `customer_id` FK on DC2SKPI** | `dc2s_kpis` | Direct account_id query could leak | Endpoint verifies account ownership first |
| **No `customer_id` FK on HealthScore** | `health_scores` | Same as above | Endpoint verifies account ownership first |
| **No `customer_id` FK on KPIScore** | `kpi_scores` | Same as above | Endpoint verifies account ownership first |
| **No `customer_id` FK on PillarScore** | `pillar_scores` | Same as above | Endpoint verifies account ownership first |
| **No `customer_id` FK on QualitativeSignal** | `qualitative_signals` | Same as above | Endpoint verifies account ownership first |
| **X-Customer-ID header fallback** | `auth_middleware.py:200-209` | Header spoofing if session fails | Global auth middleware blocks unauthenticated |
| **Account ID formula not DB-constrained** | `accounts` | No CHECK constraint on ID range | Convention only |

### Tenant Isolation Test Script: `scenario_tenant_isolation.py`

This script runs **after** 2+ customers are onboarded (Scenario 1). It uses one customer's session to try accessing another customer's data.

```python
# scenario_tenant_isolation.py — Test Plan

class TenantIsolationTests:
    """
    Login as Customer 1, try to access Customer 2's data.
    Every test should return 404 or empty results.
    """

    # ── Test Group 1: Account Visibility ──
    def test_cannot_list_other_customer_accounts(self):
        """GET /api/accounts should only return customer_id=1 accounts"""
        # Login as customer 1
        # GET /api/accounts
        # Assert: all returned account_ids are in range 1001-1050
        # Assert: no account_ids in range 2001-2050

    def test_cannot_access_other_customer_account_by_id(self):
        """GET /api/accounts?account_id=2001 should return 404 or empty"""
        # Login as customer 1
        # Try to fetch account_id=2001 (belongs to customer 2)
        # Assert: 404 or empty result

    # ── Test Group 2: KPI Data Isolation ──
    def test_cannot_read_other_customer_kpis(self):
        """GET /api/dc2s/scores/account/2001/latest should fail"""
        # Login as customer 1
        # Try to fetch scores for account 2001
        # Assert: 404 or 403

    def test_cannot_upload_csv_to_other_customer(self):
        """POST /api/onboarding/upload with customer_id=2 should fail"""
        # Login as customer 1
        # Try to upload CSV with customer_id=2
        # Assert: rejected (403 or customer_id mismatch)

    # ── Test Group 3: RAG Query Isolation ──
    def test_rag_query_only_returns_own_data(self):
        """POST /api/direct-rag/query should only reference customer 1 accounts"""
        # Login as customer 1
        # Query: "List all accounts and their health scores"
        # Assert: response contains ONLY customer 1 account names
        # Assert: response does NOT contain customer 2 account names

    # ── Test Group 4: Playbook Isolation ──
    def test_cannot_see_other_customer_executions(self):
        """GET /api/playbooks/executions should only return customer 1"""
        # Login as customer 1
        # GET /api/playbooks/executions
        # Assert: all execution.customer_id == 1

    def test_cannot_trigger_playbook_on_other_customer_account(self):
        """POST /api/playbooks/executions with account_id=2001 should fail"""
        # Login as customer 1
        # Try to create execution for account 2001
        # Assert: rejected

    # ── Test Group 5: Report Isolation ──
    def test_cannot_access_other_customer_reports(self):
        """GET /api/reports/executive-summary should only show customer 1"""
        # Login as customer 1
        # Assert: report only contains customer 1 data

    # ── Test Group 6: Activity Log Isolation ──
    def test_activity_log_scoped_to_customer(self):
        """GET /api/activity-log should only show customer 1 entries"""
        # Login as customer 1
        # Assert: all entries have customer_id=1

    # ── Test Group 7: Header Spoofing ──
    def test_header_spoofing_rejected(self):
        """Sending X-Customer-ID: 2 while logged in as customer 1 should be ignored"""
        # Login as customer 1
        # Send request with header X-Customer-ID: 2
        # Assert: response still scoped to customer 1 (header ignored)

    def test_unauthenticated_header_rejected(self):
        """Sending X-Customer-ID without auth should return 401"""
        # No login
        # Send request with header X-Customer-ID: 1
        # Assert: 401 Unauthorized

    # ── Test Group 8: Cross-Customer Signal Analysis ──
    def test_signal_analyst_scoped_to_customer(self):
        """POST /api/signal-analyst/analyze with account_id=2001 should fail for customer 1"""
        # Login as customer 1
        # Analyze account 2001
        # Assert: rejected or empty signals
```

### Tenant Isolation Gaps (NEW)

| Gap | Description | Effort |
|-----|-------------|--------|
| **GAP-LD-26** | **Tenant isolation test script** — `scenario_tenant_isolation.py` with 12 cross-tenant tests. Runs after 2+ customers onboarded. | MEDIUM |
| **GAP-LD-27** | **Add `customer_id` FK to leaf tables** — DC2SKPI, QualitativeSignal, KPIScore, PillarScore, HealthScore all lack `customer_id` column. DB migration needed. Without this, isolation relies entirely on endpoint-layer checks. | HIGH (platform change) |
| **GAP-LD-28** | **Add DB CHECK constraint on account_id range** — `account_id BETWEEN (customer_id * 1000) AND ((customer_id + 1) * 1000 - 1)`. Currently convention only. | LOW (platform change) |

---

## Complete Load Driver Script Inventory

> **STATUS: NONE of these scripts are coded yet.** All 13 scripts below are **planned only** — they exist as specifications in this gap analysis document. The `load-driver/` directory does not yet exist.

| # | Script Name | Scenario | Status | What It Does |
|---|-------------|----------|--------|--------------|
| 1 | `driver.py` | All | PLANNED | **Main orchestrator** — runs all scenarios in order, manages timing, writes summary |
| 2 | `client.py` | All | PLANNED | **HTTP client wrapper** — auth session, retry logic, health gate, header management |
| 3 | `scenario_onboarding.py` | 1 | PLANNED | Creates customer + 50 accounts, generates CSVs, uploads, processes data |
| 4 | `scenario_kpi_simulation.py` | 2a | PLANNED | Mutates KPIs over 6-12 months, uploads each month, triggers score recalc |
| 5 | `scenario_rag_queries.py` | 2b | PLANNED | Picks 5 random accounts, runs 3-5 queries each, tracks cost, validates responses |
| 6 | `scenario_signal_detection.py` | 2c | PLANNED | Runs signal analyst on degraded + healthy accounts, triggers playbooks |
| 7 | `scenario_raci_report.py` | 2d | PLANNED | Fetches RACI reports from executed playbooks, saves as markdown |
| 8 | `scenario_churn_lifecycle.py` | 2e | PLANNED | Archives churned accounts, deletes, verifies cascade |
| 9 | `scenario_tenant_isolation.py` | 3 | PLANNED | 12 cross-tenant tests: data visibility, header spoofing, query scoping |
| 10 | `scenario_cleanup.py` | 4 | PLANNED | **Post-test cleanup** — deletes all test data in correct order (NEW) |
| 11 | `csv_generator.py` | 1 | PLANNED | Generates 50-account synthetic DC2_S CSV data (38 KPIs × 12 months) |
| 12 | `kpi_mutator.py` | 2a | PLANNED | Applies realistic drift profiles per tier (healthy/risk/critical) |
| 13 | `query_templates.py` | 2b | PLANNED | 20 RAG query templates with account name placeholders |
| 14 | `scenario_roi_power_of_1.py` | 5 | PLANNED | **ROI validation** — historical, forward, cascades, ActionEconomics (NEW) |
| 15 | `results_aggregator.py` | All | PLANNED | Combines all scenario outputs → `LOAD_TEST_RESULTS.md` |

---

## Post-Load-Test Cleanup (Scenario 4 — NEW)

### What Exists Today in the Platform

The platform already has **partial** cleanup capabilities, but they are scattered and incomplete:

| What Exists | Where | Limitation |
|-------------|-------|------------|
| `POST /api/data/clear` | `data_management_api.py` | Clears KPIs, uploads, accounts for a customer — but NOT playbooks, signals, scores, notes, snapshots |
| `POST /api/data/clear-uploads` | `data_management_api.py` | Clears specific uploads only |
| `POST /api/cleanup/bulk-upload` | `cleanup_api.py` | Wipes and re-uploads, not a pure delete |
| `delete_customers_*.py` (4 scripts) | Backend root | One-off scripts for specific customer ID ranges (41-93, 94-108, 109-112, 200+). **Not reusable.** |
| `cleanup_qdrant_collections.py` | Backend root | Deletes Qdrant vector collections — **not integrated with API** |
| `CASCADE DELETE` on 3 FKs | `models.py` | Only KPIReferenceRange, ActivityLog, CustomerWorkflowConfig cascade. **17+ tables do NOT cascade.** |

### What's Missing — No Foolproof Cleanup

There is **no single "clean up everything for customer X" button**. A post-load-test cleanup today would require:

```
Manual deletion in this exact order (20 tables):
 1. QueryAudit        ← RAG query history
 2. AccountNote       ← CSM notes
 3. AccountSnapshot   ← point-in-time snapshots
 4. ActivityLog       ← CASCADE handles this ✓
 5. PlaybookReport    ← CASCADE from execution ✓
 6. PlaybookExecution ← must delete before triggers
 7. PlaybookTrigger   ← must delete before accounts
 8. CustomerWorkflowConfig ← CASCADE handles this ✓
 9. FeatureToggle     ← per-customer flags
10. KPIReferenceRange ← CASCADE handles this ✓
11. ActionEconomics   ← ROI calculations
12. HealthScore       ← account-level scores (no cascade)
13. PillarScore       ← account-level scores (no cascade)
14. KPIScore          ← account-level scores (no cascade)
15. QualitativeSignal ← account-level signals (no cascade)
16. DC2SKPI           ← raw KPI data (no cascade)
17. HealthTrend       ← time-series health (no cascade)
18. KPI               ← onboarding KPI records
19. KPIUpload         ← upload history
20. Product           ← account products
21. Account           ← customer accounts
22. User              ← customer users
23. CustomerConfig    ← customer configuration
24. Customer          ← the customer record itself
  + Qdrant collections (vector DB, separate system)
```

### Cleanup Script Design: `scenario_cleanup.py`

```python
# scenario_cleanup.py — Post-Load-Test Cleanup

class LoadTestCleanup:
    """
    Foolproof cleanup: deletes all test data for specified customer_ids.
    Runs as Scenario 4 (final step after all tests complete).

    Options:
      --customers 1,2,3      Which customers to clean up
      --dry-run               Show what would be deleted without deleting
      --skip-qdrant           Skip Qdrant collection cleanup
      --preserve-customer     Delete data but keep the customer + user records
    """

    # Required deletion order (FK dependency chain)
    CLEANUP_ORDER = [
        ('query_audits',              'customer_id'),
        ('account_notes',             'customer_id'),
        ('account_snapshots',         'customer_id'),
        ('action_economics',          'customer_id'),
        ('playbook_reports',          'execution_id → customer_id'),  # via execution FK
        ('playbook_executions',       'customer_id'),
        ('playbook_triggers',         'customer_id'),
        ('customer_workflow_configs', 'customer_id'),
        ('feature_toggles',           'customer_id'),
        ('kpi_reference_ranges',      'customer_id'),
        ('health_scores',             'account_id → customer_id'),  # no direct FK
        ('pillar_scores',             'account_id → customer_id'),  # no direct FK
        ('kpi_scores',                'account_id → customer_id'),  # no direct FK
        ('qualitative_signals',       'account_id → customer_id'),  # no direct FK
        ('dc2s_kpis',                 'account_id → customer_id'),  # no direct FK
        ('health_trends',             'customer_id'),
        ('kpis',                      'account_id → customer_id'),
        ('kpi_uploads',               'customer_id'),
        ('products',                  'customer_id'),
        ('accounts',                  'customer_id'),
        ('activity_logs',             'customer_id'),  # CASCADE but explicit
        ('users',                     'customer_id'),
        ('customer_configs',          'customer_id'),
        ('customers',                 'customer_id'),
    ]

    def cleanup_customer(self, customer_id, dry_run=False):
        """Delete all data for a single customer in FK-safe order."""
        # Step 1: Find all account_ids for this customer
        account_ids = self.get_account_ids(customer_id)

        # Step 2: Delete from each table in order
        for table, fk_column in self.CLEANUP_ORDER:
            if 'account_id →' in fk_column:
                # Tables without customer_id FK — must delete by account_ids
                count = self.delete_by_account_ids(table, account_ids, dry_run)
            else:
                # Tables with customer_id FK — direct delete
                count = self.delete_by_customer_id(table, customer_id, dry_run)
            self.log(f"{'[DRY RUN] ' if dry_run else ''}Deleted {count} rows from {table}")

        # Step 3: Cleanup Qdrant collections
        if not self.skip_qdrant:
            self.cleanup_qdrant(customer_id, account_ids, dry_run)

        # Step 4: Verify — count remaining rows
        remaining = self.verify_cleanup(customer_id, account_ids)
        if remaining > 0:
            self.log(f"WARNING: {remaining} orphan rows remain for customer {customer_id}")
        else:
            self.log(f"CLEAN: All data for customer {customer_id} removed successfully")

    def cleanup_qdrant(self, customer_id, account_ids, dry_run=False):
        """Delete Qdrant vector collections for this customer's accounts."""
        # Collection naming convention: account_{account_id}_collection
        for account_id in account_ids:
            collection_name = f"account_{account_id}_collection"
            if dry_run:
                self.log(f"[DRY RUN] Would delete Qdrant collection: {collection_name}")
            else:
                self.qdrant_client.delete_collection(collection_name)

    def verify_cleanup(self, customer_id, account_ids):
        """Post-cleanup verification: count any orphan rows."""
        total_remaining = 0
        for table, fk_column in self.CLEANUP_ORDER:
            if 'account_id →' in fk_column:
                count = self.count_by_account_ids(table, account_ids)
            else:
                count = self.count_by_customer_id(table, customer_id)
            if count > 0:
                self.log(f"ORPHAN: {count} rows in {table}")
                total_remaining += count
        return total_remaining
```

### Cleanup Options (driver.py integration)

```bash
# Full test + cleanup (default)
python driver.py --scenarios 1,2a,2b,2c,2d,2e,3,4

# Run tests only, skip cleanup (for debugging)
python driver.py --scenarios 1,2a,2b,2c,2d,2e,3 --no-cleanup

# Cleanup only (re-run after investigating failures)
python driver.py --scenarios 4 --customers 1,2,3

# Dry run cleanup (see what would be deleted)
python driver.py --scenarios 4 --customers 1,2,3 --dry-run

# Cleanup but keep customer/user records (for re-running tests)
python driver.py --scenarios 4 --customers 1,2,3 --preserve-customer
```

### Cleanup Gaps

| Gap | Description | Effort |
|-----|-------------|--------|
| **GAP-LD-29** | **Cleanup scenario script** — `scenario_cleanup.py` with 24-table FK-safe deletion, dry-run, Qdrant cleanup, and post-delete verification. | MEDIUM |
| **GAP-LD-30** | **Platform: `/api/admin/cleanup/customer/<id>` endpoint** — Currently only one-off scripts exist. Need a reusable API endpoint for full customer data wipe. | MEDIUM (platform) |
| **GAP-LD-31** | **Platform: Add CASCADE DELETE to remaining 17 FKs** — Only 3 of 20+ FKs cascade. Adding cascades makes cleanup atomic and foolproof at the DB level. | HIGH (platform, requires migration) |
| **GAP-LD-32** | **Qdrant cleanup integration** — Qdrant collection deletion is standalone script, not wired into customer deletion flow. | LOW (platform) |

---

## Power of 1 ROI Testing (Scenario 5 — NEW)

### What "Power of 1" Means

The platform has a full economic engine that converts **a 1% improvement in each key metric into dollar impact**. Six metrics drive the model:

| Metric | Baseline | 1% Annual Impact | Investment | ROI @ 1% |
|--------|----------|-------------------|------------|----------|
| **TTFV** (Time to First Value) | 30 days | $61,250 | $75,500 | -0.19 |
| **NRR** (Net Revenue Retention) | 105% | $105,000 | $50,000 | 2.10 |
| **GRR** (Gross Revenue Retention) | 85% | $100,000 | $60,000 | 1.67 |
| **Ticket Resolution Time** | 48 hrs | $38,000 | $26,000 | 1.46 |
| **Product Adoption** | 65% | $25,000 | $21,000 | 1.19 |
| **Expansion Rate** | 20% | $20,000 | $14,500 | 1.38 |

**Total portfolio investment:** $247,000 across all 6 metrics.

**Non-linear scaling** — the core claim:
```
1% improvement → $401K impact → 63% ROI
4% improvement → $1.6M impact → 550% ROI     (4x effort, 8.7x ROI)
6% improvement → $2.4M impact → 876% ROI     (6x effort, 13.9x ROI)
```

### Key Files (Already Coded)

| File | Purpose |
|------|---------|
| `power_of_1_model.py` | Core model: 6 metrics, cascade calculations, portfolio impact |
| `outcome_roi_engine.py` | Historical ROI (actuals) + Forward ROI (projections) |
| `outcome_roi_api.py` | REST endpoints: `/api/outcome-roi/*` |
| `resource_capacity_model.py` | Role hourly rates ($95-$150/hr), FTE capacity |
| `models.py:860-966` | `ActionEconomics` DB model (cost/value per action) |
| `config/power_of_1_economics.json` | All metric definitions, cascades, scaling scenarios |
| `config/investment_summary.json` | Portfolio totals, quarterly checkpoints |

### What the Load Driver Should Test

```python
# scenario_roi_power_of_1.py — ROI Validation via Load Test

class PowerOf1ROITests:
    """
    After KPI simulation (Scenario 2a) has generated 12 months of data,
    test the ROI engine with known metric movements.

    Requires: feature_toggle 'revenue_intelligence' enabled for the customer.
    """

    # ── Test Group 1: Historical ROI (Backward-Looking) ──

    def test_historical_roi_calculation(self):
        """POST /api/outcome-roi/historical with actual metric values"""
        # After 12 months of KPI simulation, accounts have moved:
        #   TTFV: 30 → 27.5 days (8.3% improvement)
        #   NRR: 105% → 108% (2.9% improvement)
        # Submit actual before/after values
        # Assert: historical ROI matches expected formula
        # Assert: dollar_impact > 0
        # Assert: revenue_increase + cost_savings == total_impact

    def test_historical_roi_scales_with_arr(self):
        """Same improvement, different ARR → different dollar impact"""
        # Test with $10M ARR → expect baseline impact
        # Test with $20M ARR → expect 2x dollar impact
        # Assert: linear ARR scaling works

    # ── Test Group 2: Forward ROI (Projections) ──

    def test_forward_roi_at_1_pct(self):
        """POST /api/outcome-roi/forward with 1% target"""
        # Assert: total portfolio impact ≈ $401K
        # Assert: ROI ≈ 63%
        # Assert: payback_months < 12

    def test_forward_roi_at_4_pct(self):
        """POST /api/outcome-roi/forward with 4% target"""
        # Assert: total portfolio impact ≈ $1.6M
        # Assert: ROI ≈ 550%
        # Assert: demonstrates non-linear scaling (4x input, 8.7x output)

    def test_forward_roi_at_6_pct(self):
        """POST /api/outcome-roi/forward with 6% target"""
        # Assert: total portfolio impact ≈ $2.4M
        # Assert: ROI ≈ 876%

    # ── Test Group 3: Metric Cascades (Compounding Flywheel) ──

    def test_ttfv_cascades_to_product_adoption(self):
        """Improving TTFV should amplify product adoption by 0.35x"""
        # Improve TTFV by 4%
        # Assert: compounded product_adoption impact ≈ direct * 0.35 * 0.15
        # Assert: compounding capped at 15% of direct impact

    def test_grr_cascades_to_nrr(self):
        """Improving GRR should amplify NRR by 0.25x"""
        # Improve GRR by 4%
        # Assert: NRR shows cascade amplification

    def test_portfolio_compounding_exceeds_sum_of_parts(self):
        """All 6 metrics improving simultaneously should compound"""
        # Improve all 6 by 4%
        # Assert: total portfolio > sum(individual metric impacts)
        # Assert: compounding delta ≈ 15% of direct total

    # ── Test Group 4: ActionEconomics Integration ──

    def test_action_economics_recorded(self):
        """After playbook execution, ActionEconomics row should exist"""
        # Execute a playbook on an account (from Scenario 2c)
        # Assert: ActionEconomics record created
        # Assert: csm_hours, cs_initiative_cost populated
        # Assert: kpi_before, kpi_after captured
        # Assert: power_of_1_metric mapped
        # Assert: roi calculated

    def test_action_economics_cost_matches_resource_model(self):
        """Verify hourly rates match resource_capacity_model"""
        # CSM hours × $95 should match cs_initiative_cost portion
        # Platform hours × $120 should match platform_cost portion
        # Assert: total_action_cost = sum of all role costs

    # ── Test Group 5: Revenue vs Cost Savings Split ──

    def test_revenue_vs_savings_breakdown(self):
        """NRR improvement should be mostly revenue; TTFV mostly savings"""
        # Get ROI for NRR improvement
        # Assert: revenue_increase > cost_savings (NRR is revenue-driven)
        # Get ROI for TTFV improvement
        # Assert: cost_savings > revenue_increase (TTFV is efficiency-driven)

    # ── Test Group 6: Feature Toggle Gate ──

    def test_roi_endpoints_require_feature_toggle(self):
        """ROI endpoints should return 403 if revenue_intelligence disabled"""
        # Disable feature toggle for customer
        # Hit /api/outcome-roi/historical
        # Assert: 403 or empty response
        # Re-enable toggle

    # ── Test Group 7: Multi-Customer ROI Isolation ──

    def test_customer_1_roi_independent_of_customer_2(self):
        """Customer 1's ROI should not include Customer 2's metric movements"""
        # Login as customer 1
        # Get historical ROI
        # Assert: only customer 1 account data in calculation
        # Assert: customer 2 accounts not referenced
```

### ROI Test Cost Impact

| Test Type | API Calls | LLM Calls | Est. Cost |
|-----------|-----------|-----------|-----------|
| Historical ROI calculations | ~10 | 0 | $0.00 |
| Forward ROI projections | ~10 | 0 | $0.00 |
| Cascade/compounding validation | ~10 | 0 | $0.00 |
| ActionEconomics integration | ~5 | 0 | $0.00 |
| Feature toggle checks | ~5 | 0 | $0.00 |
| **Total Scenario 5** | **~40** | **0** | **$0.00** |

> ROI tests are pure computation — no LLM calls, zero incremental cost.

### ROI Gaps

| Gap | Description | Effort |
|-----|-------------|--------|
| **GAP-LD-33** | **ROI scenario script** — `scenario_roi_power_of_1.py` with 12 tests: historical, forward, cascade, ActionEconomics, feature gates, multi-customer. | MEDIUM |
| **GAP-LD-34** | **KPI mutation profiles aligned to Power-of-1 metrics** — `kpi_mutator.py` must simulate TTFV, NRR, GRR, ticket_resolution, product_adoption, expansion_rate movements at known improvement percentages (1%, 4%, 6%) so ROI can be verified against expected values. | LOW |

---

## Updated Gap Summary Matrix

| ID | Gap | Scenario | Effort | Priority |
|----|-----|----------|--------|----------|
| LD-1 | 50-account CSV generator | 1 | LOW | P0 |
| LD-2 | Onboarding scenario script | 1 | MEDIUM | P0 |
| LD-3 | Auth session client wrapper | All | LOW | P0 |
| LD-4 | Health check readiness gate | All | LOW | P0 |
| LD-5 | KPI mutation simulator | 2a | MEDIUM | P1 |
| LD-6 | Bulk score recalculation | 2a | LOW | P1 |
| LD-7 | Event verification | 2a | LOW | P2 |
| LD-8 | Multi-month simulation loop | 2a | MEDIUM | P1 |
| LD-9 | RAG query scenario script | 2b | MEDIUM | P1 |
| LD-10 | Query template library | 2b | LOW | P1 |
| LD-11 | Cost budget enforcement | 2b | LOW | P1 |
| LD-12 | Signal detection scenario | 2c | MEDIUM | P1 |
| LD-13 | Playbook trigger orchestration | 2c | MEDIUM | P1 |
| LD-14 | Signal analysis cost cap | 2c | LOW | P1 |
| LD-15 | RACI report scenario script | 2d | LOW | P2 |
| LD-16 | Report depends on execution | 2d | N/A | — |
| LD-17 | Markdown export for RACI | 2d | LOW | P2 |
| LD-18 | Account archival API | 2e | MEDIUM | P1 |
| LD-19 | Account deletion API | 2e | MEDIUM | P1 |
| LD-20 | Churn lifecycle script | 2e | MEDIUM | P1 |
| LD-21 | Deletion verification queries | 2e | LOW | P2 |
| LD-22 | Load driver Dockerfile | Infra | LOW | P0 |
| LD-23 | Load driver docker-compose (multi-customer) | Infra | LOW | P0 |
| LD-24 | Results aggregator | Infra | LOW | P2 |
| LD-25 | Network / security groups | Infra | INFRA | P0 |
| **LD-26** | **Tenant isolation test script (12 tests)** | **3** | **MEDIUM** | **P1** |
| **LD-27** | **Add customer_id FK to 5 leaf tables** | **3** | **HIGH** | **P1 (platform)** |
| **LD-28** | **Add DB CHECK constraint on account_id range** | **3** | **LOW** | **P2 (platform)** |
| **LD-29** | **Post-test cleanup script (24 tables, dry-run, verify)** | **4** | **MEDIUM** | **P0** |
| **LD-30** | **Platform: `/api/admin/cleanup/customer/<id>` endpoint** | **4** | **MEDIUM** | **P1 (platform)** |
| **LD-31** | **Platform: Add CASCADE DELETE to remaining 17 FKs** | **4** | **HIGH** | **P2 (platform)** |
| **LD-32** | **Qdrant cleanup integration into customer deletion** | **4** | **LOW** | **P2 (platform)** |
| **LD-33** | **ROI Power-of-1 scenario script (12 tests)** | **5** | **MEDIUM** | **P1** |
| **LD-34** | **KPI mutator aligned to Power-of-1 metrics (1/4/6%)** | **5** | **LOW** | **P1** |

---

## Updated Effort Estimates

| Category | Gaps | Effort |
|----------|------|--------|
| **P0 — Infrastructure + Foundation** | LD-1,2,3,4,22,23,25,29 | ~1.5 days |
| **P1 — Core Scenario Scripts** | LD-5,6,8,9,10,11,12,13,14,18,19,20,26,33,34 | ~4 days |
| **P1 — Platform Changes** | LD-27,30 (customer_id FKs + cleanup API) | ~1 day |
| **P2 — Polish + Reporting** | LD-7,15,17,21,24,28,31,32 | ~1 day |
| **Total** | 34 gaps | ~7.5 days |

---

## Next Steps

1. **Brainstorm** — Review this gap analysis, decide which gaps to close first
2. **Build P0** — Dockerfile, client wrapper, onboarding scenario, multi-customer compose, cleanup script
3. **Build P1** — Core scenario scripts (KPI sim, RAG, signals, archival, tenant isolation, ROI/Power-of-1)
4. **Build P1 Platform** — Add `customer_id` FK to 5 leaf tables + `/api/admin/cleanup/customer/<id>` endpoint
5. **Build P2** — Results aggregator, RACI export, CASCADE DELETE migration, Qdrant cleanup integration
6. **Deploy** — Push to separate EC2, configure security groups
7. **Run** — Execute full test suite across 2-3 customers, verify tenant isolation, validate ROI at 1/4/6%
8. **Cleanup** — Run `scenario_cleanup.py --dry-run` first, then full cleanup, verify zero orphan rows
