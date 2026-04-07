# Repository Module Boundaries — Developer Responsibility Split

## Context

CS Pulse is ~970K lines across backend (885K), frontend (82K), and load-driver (3K). Currently single-developer. Need to split across 3-4 developers + 1 tester while protecting IP (no single developer sees the full picture).

## Principles

1. **Vertical slicing** — each developer owns a full vertical (API + business logic + tests), not a horizontal layer
2. **Interface contracts** — modules communicate via defined Python ABCs / TypeScript interfaces, not direct imports
3. **IP compartmentalization** — scoring algorithm, context graph intelligence, and LLM prompts are separated across developers
4. **CODEOWNERS enforcement** — GitHub CODEOWNERS file requires PR approval from module owner

---

## Module Map (4 Developers + 1 Tester)

### Developer 1: Platform Core & Scoring Engine
**IP sensitivity: HIGH** (scoring algorithm is the secret sauce)

| Area | Files | Lines |
|------|-------|-------|
| **Models & schema** | `models.py`, `extensions.py`, `migrations/` | 2,500 |
| **App startup** | `app_v3_minimal.py`, `vertical_config.py` | 2,100 |
| **Scoring engine** | `utils/score_calculator.py`, `health_score_engine.py`, `health_score_config.py`, `health_score_storage.py` | 1,700 |
| **Health thresholds** | `config/health_thresholds.json`, `utils/health_thresholds.py` | 300 |
| **KPI definitions** | `verticals/dc2_s/kpi_definitions.py`, `config/dc2s_kpi_catalog.json` | 800 |
| **Wizards A/B/C** | `wizards/wizard_a_journey_db.py`, `wizard_b_pattern_db.py`, `wizard_c_weight_calibrator_db.py` | 1,150 |
| **Weight management** | `config/bootstrap_weights_config.json`, CustomerConfig weight fields | 500 |
| **Lifecycle stages** | `utils/lifecycle_stages.py` | 280 |

**Total: ~9,300 lines**

**Interfaces this module EXPORTS:**
```python
# scoring_interface.py — the ONLY way other modules call scoring
def calculate_health_score(account_id, customer_id) -> HealthScoreResult
def get_pillar_weights(customer_id) -> dict[str, float]
def classify_health(score: float) -> str  # 'critical' | 'at_risk' | 'healthy'
def run_wizard(customer_id, wizard: str) -> dict
```

**What this developer CANNOT see:** LLM prompts, context graph intelligence, frontend dashboards

---

### Developer 2: APIs, Integrations & Data Pipeline
**IP sensitivity: MEDIUM** (plumbing, not algorithms)

| Area | Files | Lines |
|------|-------|-------|
| **Onboarding pipeline** | `onboarding_api_v2_config_aware.py`, `data_ingestion_api.py` | 3,500 |
| **Admin APIs** | `admin_ui_api.py`, `admin_cleanup_api.py`, `contractor_access_api.py` | 3,500 |
| **Export/backup** | `export_api.py`, `backup_restore_api.py`, `rehydration_api.py` | 2,700 |
| **Auth & security** | `auth_middleware.py`, `registration_api.py`, `api_key_service.py` | 1,500 |
| **Providers** | `providers/salesforce_provider.py`, `jira_provider.py`, `slack_provider.py`, `email_provider.py` | 1,450 |
| **Integration framework** | `integration_api.py`, `integration_models.py` | 1,800 |
| **MCP server** | `mcp_server/cs_pulse_onboarding.py`, `cs_pulse_admin.py`, `auth.py`, `common.py` | 4,700 |
| **Activity logging** | `activity_logging.py`, `activity_log_api.py` | 1,200 |
| **CSV utilities** | `utils/csv_upload.py`, `config/csv_schemas.json` | 1,000 |
| **Config APIs** | `dc2s_config_api.py`, `feature_toggle_api.py`, `workflow_config_api.py` | 1,600 |
| **Scripts** | `scripts/` (48 files — seeding, migration, admin) | 11,000 |

**Total: ~34,000 lines**

**Interfaces this module EXPORTS:**
```python
# data_pipeline_interface.py
def upload_csv(customer_id, file_type, csv_content) -> UploadResult
def process_data(customer_id) -> ProcessResult
def get_onboarding_status(customer_id) -> dict
def create_customer(name, domain, vertical, admin_email) -> CustomerResult
```

**What this developer CANNOT see:** Scoring algorithm internals, LLM prompts, arc classification logic

---

### Developer 3: Intelligence Layer (Context Graph, Signals, LLM Agents)
**IP sensitivity: HIGHEST** (AI/ML intelligence, competitive moat)

| Area | Files | Lines |
|------|-------|-------|
| **Context graph** | `context_graph_api.py`, `utils/context_graph.py`, `utils/arc_classifier.py`, `utils/arc_edge_generator.py`, `utils/story_arc_loader.py`, `utils/topology_validator.py` | 3,900 |
| **Story arcs** | `story_arc_api.py`, `config/story_arcs/*.json` (8 arcs) | 1,500 |
| **Signal engine** | `signal_engine/` (8 files: enrichment, ingest, collision, urgency, fusion, worker, models, cleanup) | 2,000 |
| **Signal analyst** | `utils/signal_analyst.py`, `utils/urgent_signal_scanner.py` | 1,100 |
| **LLM agents** | `agents/` (15 files: signal_analyst_agent, decision_matrix, prompts, models) | 5,700 |
| **Push intelligence** | `push_intelligence_subscriber.py`, `utils/push_intelligence_config.py` | 1,200 |
| **Vector search** | `utils/qdrant_signal_search.py`, `enhanced_rag_qdrant.py` | 600 |
| **MCP intelligence** | `mcp_server/cs_pulse_intelligence.py`, `cs_pulse_revenue.py` | 2,300 |
| **Revenue/ROI** | `outcome_roi_engine.py`, `outcome_roi_api.py`, `revenue_intelligence_api.py` | 3,500 |
| **Executive APIs** | `executive_dashboard_api.py`, `portfolio_api.py` | 2,700 |

**Total: ~24,500 lines**

**Interfaces this module EXPORTS:**
```python
# intelligence_interface.py
def get_account_journey_timeline(customer_id, account_id) -> list[Event]
def get_revenue_at_risk(customer_id, account_id) -> RevenueBreakdown
def classify_arc(account_id) -> tuple[str, float, str]  # arc_type, confidence, phase
def enrich_signal(signal_id, raw_text, account_id, customer_id) -> EnrichmentResult
def get_nrr_forecast(customer_id) -> NRRForecast
def get_csm_daily_actions(customer_id) -> list[Action]
```

**What this developer CANNOT see:** Scoring algorithm (uses it via interface), auth internals, admin APIs

---

### Developer 4: Frontend & UX
**IP sensitivity: LOW** (UI is visible to customers anyway)

| Area | Files | Lines |
|------|-------|-------|
| **CSM dashboards** | `csm/CSMDashboard.tsx`, `CSMFocusFlow.tsx`, `CSMCockpit.tsx` + 6 sprint components | 4,500 |
| **VP CS dashboard** | `dashboard/VPCSDashboard.tsx` | 1,100 |
| **CRO dashboard** | `dashboard/CRODashboard.tsx` + sub-views | 1,500 |
| **CFO dashboard** | `dashboard/CFODashboard.tsx` | 1,100 |
| **CEO dashboard** | `dashboard/CEODashboard.tsx` | 900 |
| **Admin UI** | `SuperAdminConsole.tsx`, `admin/` (6 files) | 1,800 |
| **Onboarding wizard** | `onboarding/OnboardingWizard.tsx` | 300 |
| **Shared components** | `utils/`, `contexts/`, `hooks/`, charts | 3,000 |
| **DC platform** | `dc/platform/` (37 files) | 15,000 |
| **Journey visualizer** | `journey-visualizer/` (10 files) | 3,000 |
| **App routing** | `App.tsx`, `LoginComponent.tsx` | 500 |

**Total: ~82,000 lines**

**Interfaces this module CONSUMES:**
```typescript
// api.ts — all backend calls go through this
function apiCall(url: string, options?: RequestInit): Promise<Response>
// getCustomerIdentifier(session) — from SessionContext
// classify(score), classifyColor(score) — from healthThresholds
```

**What this developer CANNOT see:** Backend business logic, scoring algorithm, LLM prompts

---

### Tester: QA & Test Automation
**IP sensitivity: MEDIUM** (sees test data and expected outputs)

| Area | Files | Lines |
|------|-------|-------|
| **Backend tests** | `tests/` (unit, feature, integration, e2e) | ~5,000 |
| **Frontend tests** | `src/**/*.test.tsx` | ~1,000 |
| **Load driver** | `load-driver/` (37 files) | 3,000 |
| **Test data** | `tests/test_data/`, manifests, fixtures | 2,000 |
| **CI workflows** | `.github/workflows/` | 500 |
| **Performance baselines** | `load-driver/tests/test_performance_baseline.py` | 300 |

**Total: ~12,000 lines**

---

## CODEOWNERS File

```
# /CODEOWNERS — enforce PR approval per module

# Developer 1: Platform Core & Scoring
/kpi-dashboard/backend/models.py                    @dev1-scoring
/kpi-dashboard/backend/app_v3_minimal.py             @dev1-scoring
/kpi-dashboard/backend/utils/score_calculator.py     @dev1-scoring
/kpi-dashboard/backend/health_score_*.py             @dev1-scoring
/kpi-dashboard/backend/wizards/                      @dev1-scoring
/kpi-dashboard/backend/verticals/                    @dev1-scoring
/kpi-dashboard/backend/config/health_thresholds.json @dev1-scoring

# Developer 2: APIs & Integrations
/kpi-dashboard/backend/*_api.py                      @dev2-apis
/kpi-dashboard/backend/mcp_server/cs_pulse_onboarding.py @dev2-apis
/kpi-dashboard/backend/mcp_server/cs_pulse_admin.py  @dev2-apis
/kpi-dashboard/backend/mcp_server/auth.py            @dev2-apis
/kpi-dashboard/backend/providers/                    @dev2-apis
/kpi-dashboard/backend/integration_*.py              @dev2-apis
/kpi-dashboard/backend/activity_logging.py           @dev2-apis
/kpi-dashboard/backend/scripts/                      @dev2-apis

# Developer 3: Intelligence Layer
/kpi-dashboard/backend/agents/                       @dev3-intelligence
/kpi-dashboard/backend/signal_engine/                @dev3-intelligence
/kpi-dashboard/backend/utils/signal_analyst.py       @dev3-intelligence
/kpi-dashboard/backend/utils/context_graph.py        @dev3-intelligence
/kpi-dashboard/backend/utils/arc_classifier.py       @dev3-intelligence
/kpi-dashboard/backend/utils/arc_edge_generator.py   @dev3-intelligence
/kpi-dashboard/backend/utils/topology_validator.py   @dev3-intelligence
/kpi-dashboard/backend/utils/qdrant_signal_search.py @dev3-intelligence
/kpi-dashboard/backend/push_intelligence_subscriber.py @dev3-intelligence
/kpi-dashboard/backend/outcome_roi_*.py              @dev3-intelligence
/kpi-dashboard/backend/executive_dashboard_api.py    @dev3-intelligence
/kpi-dashboard/backend/mcp_server/cs_pulse_intelligence.py @dev3-intelligence
/kpi-dashboard/backend/mcp_server/cs_pulse_revenue.py @dev3-intelligence
/kpi-dashboard/backend/config/story_arcs/            @dev3-intelligence

# Developer 4: Frontend
/kpi-dashboard/src/                                  @dev4-frontend

# Tester: Test Infrastructure
/kpi-dashboard/backend/tests/                        @tester-qa
/load-driver/                                        @tester-qa
/.github/workflows/                                  @tester-qa
```

---

## Interface Contracts (Cross-Module Boundaries)

### Rule: No direct imports across module boundaries

| From → To | Interface File | Methods |
|-----------|---------------|---------|
| APIs → Scoring | `interfaces/scoring_interface.py` | calculate_health_score, classify_health, get_pillar_weights, run_wizard |
| APIs → Intelligence | `interfaces/intelligence_interface.py` | get_journey_timeline, get_revenue_at_risk, classify_arc, enrich_signal |
| Intelligence → Scoring | `interfaces/scoring_interface.py` | classify_health, get_pillar_weights (read-only) |
| Frontend → APIs | `src/utils/api.ts` | apiCall() — all HTTP calls centralized |
| MCP → All | `mcp_server/common.py` | Delegates to interface functions |

### Implementation

```python
# interfaces/scoring_interface.py (created by Dev 1, consumed by Dev 2 & 3)
from abc import ABC, abstractmethod

class ScoringInterface(ABC):
    @abstractmethod
    def calculate_health_score(self, account_id: int, customer_id: int) -> dict: ...
    @abstractmethod
    def classify_health(self, score: float) -> str: ...
    @abstractmethod
    def get_pillar_weights(self, customer_id: int) -> dict: ...
```

Dev 1 implements. Dev 2 and Dev 3 import the interface, never the implementation directly.

---

## IP Protection Matrix

| Component | Dev 1 | Dev 2 | Dev 3 | Dev 4 | Tester |
|-----------|-------|-------|-------|-------|--------|
| **Scoring algorithm** (weights, rollups, calibration) | FULL | interface only | interface only | none | test outputs only |
| **LLM prompts** (signal analysis, enrichment) | none | none | FULL | none | test outputs only |
| **Context graph intelligence** (arcs, causal chains, topology) | none | none | FULL | none | test outputs only |
| **Auth & admin** (API keys, user mgmt, tenant isolation) | none | FULL | none | none | test scenarios |
| **UI/UX** (dashboards, components, navigation) | none | none | none | FULL | visual testing |
| **Data pipeline** (CSV ingestion, validation, processing) | none | FULL | none | none | E2E testing |

---

## Onboarding a New Developer

1. **Day 1:** Read MEMORY.md + architecture.md + their module's plan file
2. **Day 2:** Set up local dev (docker-compose), run tests in their module
3. **Day 3:** First PR — small fix within their module boundary
4. **Week 1:** Own a sprint item from their module's backlog
5. **Ongoing:** PR reviews only for files in their CODEOWNERS scope

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Dev quits, takes IP | No single dev has full algorithm + intelligence + pipeline |
| Cross-module breakage | Interface contracts + integration tests in CI |
| Merge conflicts | CODEOWNERS ensures only module owner edits their files |
| Knowledge silos | Tester sees all modules (test-level), catches integration gaps |
| Model.py bottleneck | Dev 1 owns schema, but changes require Dev 2+3 review (shared dependency) |
