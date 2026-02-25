# Test Results — Customer 200

**Generated:** 2026-02-25 20:48:41
**Backend:** http://localhost:5059
**Customer ID:** 200

---

## Scenario 1: Customer Onboarding

| Field | Value |
|-------|-------|
| **Result** | ✅ **PASS** |
| **Message** | Onboarding partial: customer 12 (1 warnings) |
| **Duration** | 33.97s |
| **API Calls** | 3 |
| **Errors** | 1 |

### Details

| Key | Value |
|-----|-------|
| company_name | LoadTest-Perry, Rice and Bates |
| email | ksanchez@example.net |
| step1_complete | success |
| customer_id | 12 |
| accounts_created | 3 |
| step1_duration_s | 33.95 |
| complete_response | `{"account_details": [{"account_id": 12001, "account_name": "LoadTest-Perry, Rice and Bates-Productio` |
| step2_register | failed: None |
| step3_login | skipped |
| step4_scores | not_available |

### Errors

1. User registration failed (non-critical — customer exists)

### Raw Result (JSON)

```json
{
  "status": "success",
  "message": "Onboarding partial: customer 12 (1 warnings)",
  "duration_seconds": 33.974937,
  "details": {
    "company_name": "LoadTest-Perry, Rice and Bates",
    "email": "ksanchez@example.net",
    "step1_complete": "success",
    "customer_id": 12,
    "accounts_created": 3,
    "step1_duration_s": 33.95,
    "complete_response": {
      "account_details": [
        {
          "account_id": 12001,
          "account_name": "LoadTest-Perry, Rice and Bates-Production",
          "uuid": "dc_acct_019c968f-1e9a-70b8-ac45-8b69a2e4bf71"
        },
        {
          "account_id": 12002,
          "account_name": "LoadTest-Perry, Rice and Bates-Staging",
          "uuid": "dc_acct_019c968f-1e9e-7e6c-8f81-5fbf4fab0998"
        },
        {
          "account_id": 12003,
          "account_name": "LoadTest-Perry, Rice and Bates-Development",
          "uuid": "dc_acct_019c968f-1ea1-7d97-a020-3102c959f607"
        }
      ],
      "account_id_range": "12001 - 12003",
      "accounts": 3,
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
      "customer_id": 12,
      "customer_name": "LoadTest-Perry, Rice and Bates",
      "customer_uuid": "dc_cust_019c968f-1e89-7a7b-88cd-c4ab7a5883f1",
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
