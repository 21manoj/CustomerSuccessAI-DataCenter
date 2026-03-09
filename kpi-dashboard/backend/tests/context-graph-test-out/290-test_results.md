# Test Results — Customer 290

**Generated:** 2026-03-05 10:31:47
**Backend:** http://localhost:5059
**Customer ID:** 290

---

## Scenario 8: Context Graph (story arc → 9 CSVs)

| Field | Value |
|-------|-------|
| **Result** | ✅ **PASS** |
| **Message** | Context graph: 9 files uploaded and ingested for customer 290 (arc=arc_expansion_champion) |
| **Duration** | 4.14s |
| **API Calls** | 12 |

### Details

| Key | Value |
|-----|-------|
| customer_id | 290 |
| arc_id | arc_expansion_champion |
| num_accounts | 10 |
| existing_accounts | 10 |
| generation_duration_s | 0.01 |
| files_generated | `["stakeholders", "engagement_events", "account_business_profiles", "decisions", "outcomes", "signal_` |
| upload_duration_s | 0.05 |
| upload_results | `{"stakeholders": "success", "engagement_events": "success", "account_business_profiles": "success", ` |
| process_duration_s | 4.07 |
| steps_completed | `["data_loading", "context_graph_ingestion", "journey_generation", "journey_db_persist", "journey_api` |
| context_graph_result | `{}` |
| verification | skipped |

### Raw Result (JSON)

```json
{
  "status": "success",
  "message": "Context graph: 9 files uploaded and ingested for customer 290 (arc=arc_expansion_champion)",
  "duration_seconds": 4.137551,
  "details": {
    "customer_id": 290,
    "arc_id": "arc_expansion_champion",
    "num_accounts": 10,
    "existing_accounts": 10,
    "generation_duration_s": 0.01,
    "files_generated": [
      "stakeholders",
      "engagement_events",
      "account_business_profiles",
      "decisions",
      "outcomes",
      "signal_edges",
      "decision_evidence",
      "industry_benchmarks",
      "enhanced_signals"
    ],
    "upload_duration_s": 0.05,
    "upload_results": {
      "stakeholders": "success",
      "engagement_events": "success",
      "account_business_profiles": "success",
      "decisions": "success",
      "outcomes": "success",
      "signal_edges": "success",
      "decision_evidence": "success",
      "industry_benchmarks": "success",
      "enhanced_signals": "success"
    },
    "process_duration_s": 4.07,
    "steps_completed": [
      "data_loading",
      "context_graph_ingestion",
      "journey_generation",
      "journey_db_persist",
      "journey_api_ready"
    ],
    "context_graph_result": {},
    "verification": "skipped"
  },
  "api_calls": 12,
  "errors": []
}
```
