# Test Results — Customer 17

**Generated:** 2026-02-26 00:33:51
**Backend:** http://localhost:5059
**Customer ID:** 17

---

## Scenario 4: Customer Cleanup

| Field | Value |
|-------|-------|
| **Result** | ✅ **PASS** |
| **Message** | Cleanup complete: customer 17, 968 rows deleted, 400 files removed |
| **Duration** | 0.68s |
| **API Calls** | 2 |

### Details

| Key | Value |
|-----|-------|
| dry_run | `{"tables_to_delete": ["query_audits", "account_notes", "account_snapshots", "action_economics", "pla` |
| filesystem_preview | `{"directories_found": ["/home/user/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/cust` |
| cleanup | `{"tables_deleted": 23, "rows_deleted": 968, "duration_seconds": 0.09}` |
| filesystem | `{"directories_found": ["/home/user/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/cust` |
| verification | `{"status": "clean", "orphan_rows": 0}` |

### Raw Result (JSON)

```json
{
  "status": "success",
  "message": "Cleanup complete: customer 17, 968 rows deleted, 400 files removed",
  "duration_seconds": 0.684123,
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
      "directories_found": [
        "/home/user/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer17-dc2_s"
      ],
      "directories_removed": [],
      "files_removed": 400,
      "bytes_freed": 9132539
    },
    "cleanup": {
      "tables_deleted": 23,
      "rows_deleted": 968,
      "duration_seconds": 0.09
    },
    "filesystem": {
      "directories_found": [
        "/home/user/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer17-dc2_s"
      ],
      "directories_removed": [
        "/home/user/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer17-dc2_s"
      ],
      "files_removed": 400,
      "bytes_freed": 9132539
    },
    "verification": {
      "status": "clean",
      "orphan_rows": 0
    }
  },
  "api_calls": 2
}
```
