# Test Results — Customer 100

**Generated:** 2026-02-25 20:17:11
**Backend:** http://localhost:5059
**Customer ID:** 100

---

## Scenario 1: Customer Onboarding

| Field | Value |
|-------|-------|
| **Result** | ✅ **PASS** |
| **Message** | Onboarding complete: customer 6, pipeline OK |
| **Duration** | 33.17s |
| **API Calls** | 5 |

### Details

| Key | Value |
|-----|-------|
| company_name | LoadTest-Perkins, Anthony and Hayes |
| email | martinkristen@example.com |
| step1_complete | success |
| customer_id | 6 |
| accounts_created | 3 |
| step1_duration_s | 32.91 |
| complete_response | `{"account_details": [{"account_id": 6001, "account_name": "LoadTest-Perkins, Anthony and Hayes-Produ` |
| step2_register | success |
| user_id | 2 |
| user_customer_id | 7 |
| step3_login | success |
| step3_dashboard | accessible |
| accounts_visible | 0 |
| step4_scores | not_available |

### Raw Result (JSON)

```json
{
  "status": "success",
  "message": "Onboarding complete: customer 6, pipeline OK",
  "duration_seconds": 33.173919,
  "details": {
    "company_name": "LoadTest-Perkins, Anthony and Hayes",
    "email": "martinkristen@example.com",
    "step1_complete": "success",
    "customer_id": 6,
    "accounts_created": 3,
    "step1_duration_s": 32.91,
    "complete_response": {
      "account_details": [
        {
          "account_id": 6001,
          "account_name": "LoadTest-Perkins, Anthony and Hayes-Production"
        },
        {
          "account_id": 6002,
          "account_name": "LoadTest-Perkins, Anthony and Hayes-Staging"
        },
        {
          "account_id": 6003,
          "account_name": "LoadTest-Perkins, Anthony and Hayes-Development"
        }
      ],
      "account_id_range": "6001 - 6003",
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
      "customer_id": 6,
      "customer_name": "LoadTest-Perkins, Anthony and Hayes",
      "directory_provisioned": true,
      "message": "Onboarding complete! Customer, user, config, accounts, and demo CSV files created.",
      "onboarding_mode": "demo",
      "success": true
    },
    "step2_register": "success",
    "user_id": 2,
    "user_customer_id": 7,
    "step3_login": "success",
    "step3_dashboard": "accessible",
    "accounts_visible": 0,
    "step4_scores": "not_available"
  },
  "api_calls": 5
}
```
