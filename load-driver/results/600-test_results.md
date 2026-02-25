# Test Results — Customer 600

**Generated:** 2026-02-25 21:32:00
**Backend:** http://localhost:5059
**Customer ID:** 600

---

## Scenario 1: Customer Onboarding

| Field | Value |
|-------|-------|
| **Result** | ✅ **PASS** |
| **Message** | Onboarding partial: customer 14 (3 warnings) |
| **Duration** | 24.48s |
| **API Calls** | 5 |
| **Errors** | 3 |

### Details

| Key | Value |
|-----|-------|
| company_name | LoadTest-Kane Ltd |
| email | montgomerymark@example.com |
| step1_complete | success |
| customer_id | 14 |
| accounts_created | 20 |
| step1_duration_s | 24.2 |
| complete_response | `{"account_details": [{"account_id": 14001, "account_name": "LoadTest-Kane Ltd-Production", "uuid": "` |
| step2_process_data | failed: No response |
| step3_scores_calc | partial: No response |
| step4_register | failed: None |
| step5_login | skipped |
| step6_scores | not_available |

### Errors

1. process-data did not fully succeed: No response
2. Score calculation did not fully succeed (non-critical)
3. User registration failed (non-critical — customer exists)

### Raw Result (JSON)

```json
{
  "status": "success",
  "message": "Onboarding partial: customer 14 (3 warnings)",
  "duration_seconds": 24.47712,
  "details": {
    "company_name": "LoadTest-Kane Ltd",
    "email": "montgomerymark@example.com",
    "step1_complete": "success",
    "customer_id": 14,
    "accounts_created": 20,
    "step1_duration_s": 24.2,
    "complete_response": {
      "account_details": [
        {
          "account_id": 14001,
          "account_name": "LoadTest-Kane Ltd-Production",
          "uuid": "dc_acct_019c96b6-e997-7758-9c97-895d37ea4f44"
        },
        {
          "account_id": 14002,
          "account_name": "LoadTest-Kane Ltd-Staging",
          "uuid": "dc_acct_019c96b6-e999-720f-97a6-e6799c6400a5"
        },
        {
          "account_id": 14003,
          "account_name": "LoadTest-Kane Ltd-Development",
          "uuid": "dc_acct_019c96b6-e99b-7918-8ae0-3542825d3b4a"
        },
        {
          "account_id": 14004,
          "account_name": "LoadTest-Kane Ltd-Environment",
          "uuid": "dc_acct_019c96b6-e99c-7bfd-8661-d8f73c6f6b74"
        },
        {
          "account_id": 14005,
          "account_name": "LoadTest-Kane Ltd-Workspace",
          "uuid": "dc_acct_019c96b6-e99e-74b4-9dfd-2b90f9a3da97"
        },
        {
          "account_id": 14006,
          "account_name": "LoadTest-Kane Ltd-Cluster",
          "uuid": "dc_acct_019c96b6-e99f-75ae-a4bd-5627cccb1816"
        },
        {
          "account_id": 14007,
          "account_name": "LoadTest-Kane Ltd-Instance",
          "uuid": "dc_acct_019c96b6-e9a1-79ed-90ea-f697ba53fb8e"
        },
        {
          "account_id": 14008,
          "account_name": "LoadTest-Kane Ltd-Node",
          "uuid": "dc_acct_019c96b6-e9a2-7338-a1a2-bfbf081ddcaa"
        },
        {
          "account_id": 14009,
          "account_name": "LoadTest-Kane Ltd-Server",
          "uuid": "dc_acct_019c96b6-e9a4-712d-bb55-d054e1f24ec1"
        },
        {
          "account_id": 14010,
          "account_name": "LoadTest-Kane Ltd-System",
          "uuid": "dc_acct_019c96b6-e9a5-7cd1-8448-e0c89cae3865"
        },
        {
          "account_id": 14011,
          "account_name": "LoadTest-Kane Ltd-Account-11",
          "uuid": "dc_acct_019c96b6-e9a7-746d-8a52-fddcb2c989c7"
        },
        {
          "account_id": 14012,
          "account_name": "LoadTest-Kane Ltd-Account-12",
          "uuid": "dc_acct_019c96b6-e9a8-72a5-9579-40c1a0024b77"
        },
        {
          "account_id": 14013,
          "account_name": "LoadTest-Kane Ltd-Account-13",
          "uuid": "dc_acct_019c96b6-e9aa-74f5-80e5-9b20a1691d4c"
        },
        {
          "account_id": 14014,
          "account_name": "LoadTest-Kane Ltd-Account-14",
          "uuid": "dc_acct_019c96b6-e9ab-74a7-955f-14106da56050"
        },
        {
          "account_id": 14015,
          "account_name": "LoadTest-Kane Ltd-Account-15",
          "uuid": "dc_acct_019c96b6-e9ad-7627-853b-9c1d660d5f76"
        },
        {
          "account_id": 14016,
          "account_name": "LoadTest-Kane Ltd-Account-16",
          "uuid": "dc_acct_019c96b6-e9ae-7901-87d9-89ec647d2a05"
        },
        {
          "account_id": 14017,
          "account_name": "LoadTest-Kane Ltd-Account-17",
          "uuid": "dc_acct_019c96b6-e9b0-7b2b-86bc-f71db280e4c4"
        },
        {
          "account_id": 14018,
          "account_name": "LoadTest-Kane Ltd-Account-18",
          "uuid": "dc_acct_019c96b6-e9b1-70a1-96b4-1d24ae102e69"
        },
        {
          "account_id": 14019,
          "account_name": "LoadTest-Kane Ltd-Account-19",
          "uuid": "dc_acct_019c96b6-e9b3-779b-a7ba-260a9a985241"
        },
        {
          "account_id": 14020,
          "account_name": "LoadTest-Kane Ltd-Account-20",
          "uuid": "dc_acct_019c96b6-e9b5-7fa6-a3a3-65ef1a6bc31e"
        }
      ],
      "account_id_range": "14001 - 14020",
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
      "customer_id": 14,
      "customer_name": "LoadTest-Kane Ltd",
      "customer_uuid": "dc_cust_019c96b6-e990-7f44-8dd2-fad2b5a48b73",
      "directory_provisioned": false,
      "message": "Onboarding complete! Customer, user, config, accounts, and demo CSV files created.",
      "onboarding_mode": "demo",
      "success": true
    },
    "step2_process_data": "failed: No response",
    "step3_scores_calc": "partial: No response",
    "step4_register": "failed: None",
    "step5_login": "skipped",
    "step6_scores": "not_available"
  },
  "api_calls": 5,
  "errors": [
    "process-data did not fully succeed: No response",
    "Score calculation did not fully succeed (non-critical)",
    "User registration failed (non-critical \u2014 customer exists)"
  ]
}
```
