# Test Results — Customer 14

**Generated:** 2026-02-25 21:34:49
**Backend:** http://localhost:5059
**Customer ID:** 14

---

## Scenario 4: Customer Cleanup

| Field | Value |
|-------|-------|
| **Result** | ✅ **PASS** |
| **Message** | Cleanup complete: customer 14, 21 rows deleted, 0 files removed |
| **Duration** | 0.19s |
| **API Calls** | 2 |

### Details

| Key | Value |
|-----|-------|
| dry_run | `{"tables_to_delete": ["query_audits", "account_notes", "account_snapshots", "action_economics", "pla` |
| filesystem_preview | `{"directories_found": [], "directories_removed": [], "files_removed": 0, "bytes_freed": 0}` |
| cleanup | `{"tables_deleted": 23, "rows_deleted": 21, "duration_seconds": 0.09}` |
| filesystem | `{"directories_found": [], "directories_removed": [], "files_removed": 0, "bytes_freed": 0}` |
| verification | `{"status": "clean", "orphan_rows": 0}` |

### Raw Result (JSON)

```json
{
  "status": "success",
  "message": "Cleanup complete: customer 14, 21 rows deleted, 0 files removed",
  "duration_seconds": 0.191999,
  "details": {
    "dry_run": {
      "tables_to_delete": [
        "query_audits",
        "account_notes",
        "account_snapshots",
        "action_economics",
        "playbook_reports",
        "playbook_executions",
        "playbook_triggers",
        "customer_workflow_configs",
        "feature_toggles",
        "kpi_reference_ranges",
        "health_scores",
        "pillar_scores",
        "kpi_scores",
        "qualitative_signals",
        "dc2s_kpis",
        "kpis",
        "health_trends",
        "kpi_uploads",
        "products",
        "accounts",
        "activity_logs",
        "users",
        "customer_configs"
      ],
      "rows_to_delete": 0
    },
    "filesystem_preview": {
      "directories_found": [],
      "directories_removed": [],
      "files_removed": 0,
      "bytes_freed": 0
    },
    "cleanup": {
      "tables_deleted": 23,
      "rows_deleted": 21,
      "duration_seconds": 0.09
    },
    "filesystem": {
      "directories_found": [],
      "directories_removed": [],
      "files_removed": 0,
      "bytes_freed": 0
    },
    "verification": {
      "status": "clean",
      "orphan_rows": 0
    }
  },
  "api_calls": 2
}
```
