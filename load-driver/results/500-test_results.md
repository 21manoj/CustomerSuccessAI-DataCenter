# Test Results — Customer 500

**Generated:** 2026-02-25 21:23:31
**Backend:** http://localhost:5059
**Customer ID:** 500

---

## Scenario 1: Customer Onboarding

| Field | Value |
|-------|-------|
| **Result** | ✅ **PASS** |
| **Message** | Onboarding partial: customer 13 (1 warnings) |
| **Duration** | 27.28s |
| **API Calls** | 3 |
| **Errors** | 1 |

### Details

| Key | Value |
|-----|-------|
| company_name | LoadTest-Young Group |
| email | harriswhitney@example.net |
| step1_complete | success |
| customer_id | 13 |
| accounts_created | 20 |
| step1_duration_s | 27.26 |
| complete_response | `{"account_details": [{"account_id": 13001, "account_name": "LoadTest-Young Group-Production", "uuid"` |
| step2_register | failed: None |
| step3_login | skipped |
| step4_scores | not_available |

### Errors

1. User registration failed (non-critical — customer exists)

### Raw Result (JSON)

```json
{
  "status": "success",
  "message": "Onboarding partial: customer 13 (1 warnings)",
  "duration_seconds": 27.28175,
  "details": {
    "company_name": "LoadTest-Young Group",
    "email": "harriswhitney@example.net",
    "step1_complete": "success",
    "customer_id": 13,
    "accounts_created": 20,
    "step1_duration_s": 27.26,
    "complete_response": {
      "account_details": [
        {
          "account_id": 13001,
          "account_name": "LoadTest-Young Group-Production",
          "uuid": "dc_acct_019c96af-1d32-7f48-b353-629c3b71d72f"
        },
        {
          "account_id": 13002,
          "account_name": "LoadTest-Young Group-Staging",
          "uuid": "dc_acct_019c96af-1d35-76d1-8028-4cf97332bbb8"
        },
        {
          "account_id": 13003,
          "account_name": "LoadTest-Young Group-Development",
          "uuid": "dc_acct_019c96af-1d37-78a3-af5e-1d945270609a"
        },
        {
          "account_id": 13004,
          "account_name": "LoadTest-Young Group-Environment",
          "uuid": "dc_acct_019c96af-1d38-73d4-b6a6-d85692fa68b5"
        },
        {
          "account_id": 13005,
          "account_name": "LoadTest-Young Group-Workspace",
          "uuid": "dc_acct_019c96af-1d3b-7741-8d5d-83ce7356d0e8"
        },
        {
          "account_id": 13006,
          "account_name": "LoadTest-Young Group-Cluster",
          "uuid": "dc_acct_019c96af-1d3c-7a84-a76d-61534f6c6b9d"
        },
        {
          "account_id": 13007,
          "account_name": "LoadTest-Young Group-Instance",
          "uuid": "dc_acct_019c96af-1d3e-7d2f-b48a-85f84ec80d45"
        },
        {
          "account_id": 13008,
          "account_name": "LoadTest-Young Group-Node",
          "uuid": "dc_acct_019c96af-1d3f-7758-8869-25bd5218ac55"
        },
        {
          "account_id": 13009,
          "account_name": "LoadTest-Young Group-Server",
          "uuid": "dc_acct_019c96af-1d41-7beb-963e-ffcd03c1718b"
        },
        {
          "account_id": 13010,
          "account_name": "LoadTest-Young Group-System",
          "uuid": "dc_acct_019c96af-1d43-7485-8ce3-533ac431fb59"
        },
        {
          "account_id": 13011,
          "account_name": "LoadTest-Young Group-Account-11",
          "uuid": "dc_acct_019c96af-1d44-7d3c-9679-e491dbf002e1"
        },
        {
          "account_id": 13012,
          "account_name": "LoadTest-Young Group-Account-12",
          "uuid": "dc_acct_019c96af-1d45-7b36-b75e-8d7d733d1b69"
        },
        {
          "account_id": 13013,
          "account_name": "LoadTest-Young Group-Account-13",
          "uuid": "dc_acct_019c96af-1d47-701a-8e84-d18780e3feab"
        },
        {
          "account_id": 13014,
          "account_name": "LoadTest-Young Group-Account-14",
          "uuid": "dc_acct_019c96af-1d48-798a-95ca-9666ae88e5c1"
        },
        {
          "account_id": 13015,
          "account_name": "LoadTest-Young Group-Account-15",
          "uuid": "dc_acct_019c96af-1d4a-7a0a-8c6f-6032940cd45f"
        },
        {
          "account_id": 13016,
          "account_name": "LoadTest-Young Group-Account-16",
          "uuid": "dc_acct_019c96af-1d4b-7880-b5ab-19d387063c4f"
        },
        {
          "account_id": 13017,
          "account_name": "LoadTest-Young Group-Account-17",
          "uuid": "dc_acct_019c96af-1d4c-764e-a2d5-ab8641d84ec7"
        },
        {
          "account_id": 13018,
          "account_name": "LoadTest-Young Group-Account-18",
          "uuid": "dc_acct_019c96af-1d4e-762b-b45f-c8142899e7e9"
        },
        {
          "account_id": 13019,
          "account_name": "LoadTest-Young Group-Account-19",
          "uuid": "dc_acct_019c96af-1d4f-7cd1-8433-2df57096e29a"
        },
        {
          "account_id": 13020,
          "account_name": "LoadTest-Young Group-Account-20",
          "uuid": "dc_acct_019c96af-1d51-77bb-9fec-77046e1205c2"
        }
      ],
      "account_id_range": "13001 - 13020",
      "accounts": 20,
      "config": {
        "enabled_kpis": 15,
        "pillars": 5,
        "vertical": "dc2_s",
        "weights": {
          "AI": 0.25,
          "CH": 0.2,
          "DV": 0.15,
          "EX": 0.2,
          "OS": 0.2
        }
      },
      "csv_files_generated": true,
      "customer_id": 13,
      "customer_name": "LoadTest-Young Group",
      "customer_uuid": "dc_cust_019c96af-1d22-77de-83d0-afae3bc1d323",
      "directory_provisioned": false,
      "message": "Onboarding complete! Customer, user, config, accounts, and demo CSV files created.",
      "onboarding_mode": "demo",
      "success": true
    },
    "step2_register": "failed: None",
    "step3_login": "skipped",
    "step4_scores": "not_available"
  },
  "api_calls": 3,
  "errors": [
    "User registration failed (non-critical \u2014 customer exists)"
  ]
}
```
