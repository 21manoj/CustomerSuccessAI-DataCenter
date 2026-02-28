# Test Results — Customer 500

**Generated:** 2026-02-27 19:04:58
**Backend:** http://localhost:5059
**Customer ID:** 500

---

## Scenario 1: Customer Onboarding

| Field | Value |
|-------|-------|
| **Result** | ✅ **PASS** |
| **Message** | Onboarding partial: customer 283 (2 warnings) |
| **Duration** | 22.25s |
| **API Calls** | 5 |
| **Errors** | 2 |

### Details

| Key | Value |
|-----|-------|
| company_name | LoadTest-Mendez PLC |
| email | mboyd@example.org |
| step1_complete | success |
| customer_id | 283 |
| accounts_created | 3 |
| step1_duration_s | 11.88 |
| complete_response | `{"account_details": [{"account_id": 283001, "account_name": "LoadTest-Mendez PLC-Production", "uuid"` |
| step2_process_data | warning |
| step2_duration_s | 6.94 |
| steps_completed | `["data_loading", "journey_generation", "journey_api_ready"]` |
| step2_warnings | `["Embedding skipped (Qdrant unavailable): /Users/manojgupta/Library/Python/3.9/lib/python/site-packa` |
| step3_register | failed: None |
| step4_login | skipped |
| step5_scores_calc | partial: No response |
| step6_scores | not_available |

### Errors

1. User registration failed (non-critical — customer exists)
2. Score calculation did not fully succeed (non-critical)

### Raw Result (JSON)

```json
{
  "status": "success",
  "message": "Onboarding partial: customer 283 (2 warnings)",
  "duration_seconds": 22.24977,
  "details": {
    "company_name": "LoadTest-Mendez PLC",
    "email": "mboyd@example.org",
    "step1_complete": "success",
    "customer_id": 283,
    "accounts_created": 3,
    "step1_duration_s": 11.88,
    "complete_response": {
      "account_details": [
        {
          "account_id": 283001,
          "account_name": "LoadTest-Mendez PLC-Production",
          "uuid": "dc_acct_019ca234-831a-78c3-9b52-a39279463879"
        },
        {
          "account_id": 283002,
          "account_name": "LoadTest-Mendez PLC-Staging",
          "uuid": "dc_acct_019ca234-8320-7e6b-b7dc-bbc6c32623bb"
        },
        {
          "account_id": 283003,
          "account_name": "LoadTest-Mendez PLC-Development",
          "uuid": "dc_acct_019ca234-8322-7e0a-bd20-ed99631d93b2"
        }
      ],
      "account_id_range": "283001 - 283003",
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
      "customer_id": 283,
      "customer_name": "LoadTest-Mendez PLC",
      "customer_uuid": "dc_cust_019ca234-818a-707f-b9af-8b1097770920",
      "directory_provisioned": true,
      "message": "Onboarding complete! Customer, user, config, accounts, and demo CSV files created.",
      "onboarding_mode": "demo",
      "success": true
    },
    "step2_process_data": "warning",
    "step2_duration_s": 6.94,
    "steps_completed": [
      "data_loading",
      "journey_generation",
      "journey_api_ready"
    ],
    "step2_warnings": [
      "Embedding skipped (Qdrant unavailable): /Users/manojgupta/Library/Python/3.9/lib/python/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL ",
      "Validation warnings: /Users/manojgupta/Library/Python/3.9/lib/python/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020\n  warnings.warn(\n/Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer283-dc2_s/scripts/04_validate_data_integrity.py:74: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.\n  qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)\n"
    ],
    "step3_register": "failed: None",
    "step4_login": "skipped",
    "step5_scores_calc": "partial: No response",
    "step6_scores": "not_available"
  },
  "api_calls": 5,
  "errors": [
    "User registration failed (non-critical \u2014 customer exists)",
    "Score calculation did not fully succeed (non-critical)"
  ]
}
```
