# Test Results — Customer 16

**Generated:** 2026-02-25 21:37:11
**Backend:** http://localhost:5059
**Customer ID:** 16

---

## Scenario 4: Customer Cleanup

| Field | Value |
|-------|-------|
| **Result** | ✅ **PASS** |
| **Message** | Cleanup complete: customer 16, 8 rows deleted, 0 files removed |
| **Duration** | 0.11s |
| **API Calls** | 2 |

### Details

| Key | Value |
|-----|-------|
| dry_run | `{"tables_to_delete": ["query_audits", "account_notes", "account_snapshots", "action_economics", "pla` |
| filesystem_preview | `{"directories_found": [], "directories_removed": [], "files_removed": 0, "bytes_freed": 0}` |
| cleanup | `{"tables_deleted": 17, "rows_deleted": 8, "duration_seconds": 0.04}` |
| filesystem | `{"directories_found": [], "directories_removed": [], "files_removed": 0, "bytes_freed": 0}` |
| verification | `{"status": "clean", "orphan_rows": 0}` |

### Raw Result (JSON)

```json
{
  "status": "success",
  "message": "Cleanup complete: customer 16, 8 rows deleted, 0 files removed",
  "duration_seconds": 0.109061,
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
      "tables_deleted": 17,
      "rows_deleted": 8,
      "duration_seconds": 0.04
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
