# Load Test Results
**Generated:** 2026-03-02 23:24:56
**Base URL:** http://host.docker.internal:5059

## Executive Summary

- **Total Scenarios:** 10
- **Completed:** 9
- **Failed:** 1
- **Success Rate:** 90.0%

## Scenario Results

### ✅ Onboarding

- **Status:** COMPLETED
- **Start:** 2026-03-02T23:24:48.945240
- **End:** 2026-03-02T23:24:52.958730

### ✅ Kpi Simulation

- **Status:** COMPLETED
- **Start:** 2026-03-02T23:24:52.959150
- **End:** 2026-03-02T23:24:53.023439

### ✅ Rag Queries

- **Status:** COMPLETED
- **Start:** 2026-03-02T23:24:53.023505
- **End:** 2026-03-02T23:24:53.101627

### ✅ Signal Detection

- **Status:** COMPLETED
- **Start:** 2026-03-02T23:24:53.101701
- **End:** 2026-03-02T23:24:53.487863

### ✅ Raci Reports

- **Status:** COMPLETED
- **Start:** 2026-03-02T23:24:53.488213
- **End:** 2026-03-02T23:24:53.675980

### ✅ Churn Lifecycle

- **Status:** COMPLETED
- **Start:** 2026-03-02T23:24:53.676065
- **End:** 2026-03-02T23:24:55.732183

### ✅ Tenant Isolation

- **Status:** COMPLETED
- **Start:** 2026-03-02T23:24:55.732497
- **End:** 2026-03-02T23:24:56.548576

### ✅ Cleanup

- **Status:** COMPLETED
- **Start:** 2026-03-02T23:24:56.548895
- **End:** 2026-03-02T23:24:56.709924

### ✅ Roi Power Of 1

- **Status:** COMPLETED
- **Start:** 2026-03-02T23:24:56.710041
- **End:** 2026-03-02T23:24:56.787296

### ❌ N8N Workflow

- **Status:** FAILED
- **Start:** 2026-03-02T23:24:56.787921
- **End:** N/A
- **Error:** module 'scenarios.scenario_n8n_workflow' has no attribute 'ScenarioN8NWorkflow'

---

## Raw Results (JSON)

```json
{
  "timestamp": "2026-03-02T23:24:48.943343",
  "base_url": "http://host.docker.internal:5059",
  "scenarios": {
    "onboarding": {
      "name": "onboarding",
      "status": "completed",
      "start_time": "2026-03-02T23:24:48.945240",
      "customers": [
        3
      ],
      "details": {},
      "end_time": "2026-03-02T23:24:52.958730"
    },
    "kpi_simulation": {
      "name": "kpi_simulation",
      "status": "completed",
      "start_time": "2026-03-02T23:24:52.959150",
      "customers": [
        3
      ],
      "details": {},
      "end_time": "2026-03-02T23:24:53.023439"
    },
    "rag_queries": {
      "name": "rag_queries",
      "status": "completed",
      "start_time": "2026-03-02T23:24:53.023505",
      "customers": [
        3
      ],
      "details": {},
      "end_time": "2026-03-02T23:24:53.101627"
    },
    "signal_detection": {
      "name": "signal_detection",
      "status": "completed",
      "start_time": "2026-03-02T23:24:53.101701",
      "customers": [
        3
      ],
      "details": {},
      "end_time": "2026-03-02T23:24:53.487863"
    },
    "raci_reports": {
      "name": "raci_reports",
      "status": "completed",
      "start_time": "2026-03-02T23:24:53.488213",
      "customers": [
        3
      ],
      "details": {},
      "end_time": "2026-03-02T23:24:53.675980"
    },
    "churn_lifecycle": {
      "name": "churn_lifecycle",
      "status": "completed",
      "start_time": "2026-03-02T23:24:53.676065",
      "customers": [
        3
      ],
      "details": {},
      "end_time": "2026-03-02T23:24:55.732183"
    },
    "tenant_isolation": {
      "name": "tenant_isolation",
      "status": "completed",
      "start_time": "2026-03-02T23:24:55.732497",
      "customers": [
        3
      ],
      "details": {},
      "end_time": "2026-03-02T23:24:56.548576"
    },
    "cleanup": {
      "name": "cleanup",
      "status": "completed",
      "start_time": "2026-03-02T23:24:56.548895",
      "customers": [
        3
      ],
      "details": {},
      "end_time": "2026-03-02T23:24:56.709924"
    },
    "roi_power_of_1": {
      "name": "roi_power_of_1",
      "status": "completed",
      "start_time": "2026-03-02T23:24:56.710041",
      "customers": [
        3
      ],
      "details": {},
      "end_time": "2026-03-02T23:24:56.787296"
    },
    "n8n_workflow": {
      "name": "n8n_workflow",
      "status": "failed",
      "start_time": "2026-03-02T23:24:56.787921",
      "customers": [
        3
      ],
      "details": {},
      "error": "module 'scenarios.scenario_n8n_workflow' has no attribute 'ScenarioN8NWorkflow'"
    }
  },
  "summary": {}
}
```