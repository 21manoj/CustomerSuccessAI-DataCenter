# Test Results — Customer 700

**Generated:** 2026-02-25 21:35:50
**Backend:** http://localhost:5059
**Customer ID:** 700

---

## Scenario 1: Customer Onboarding

| Field | Value |
|-------|-------|
| **Result** | ✅ **PASS** |
| **Message** | Onboarding partial: customer 15 (2 warnings) |
| **Duration** | 50.48s |
| **API Calls** | 7 |
| **Errors** | 2 |

### Details

| Key | Value |
|-----|-------|
| company_name | LoadTest-Bell, Huang and Jones |
| email | duncanrebecca@example.org |
| step1_complete | success |
| customer_id | 15 |
| accounts_created | 20 |
| step1_duration_s | 24.01 |
| complete_response | `{"account_details": [{"account_id": 15001, "account_name": "LoadTest-Bell, Huang and Jones-Productio` |
| step2_process_data | failed: No response |
| step3_register | success |
| user_id | 3 |
| user_customer_id | 16 |
| step4_login | success |
| step4_dashboard | accessible |
| accounts_visible | 0 |
| step5_scores_calc | partial: No response |
| step6_scores | not_available |

### Errors

1. process-data did not fully succeed: No response
2. Score calculation did not fully succeed (non-critical)

### Raw Result (JSON)

```json
{
  "status": "success",
  "message": "Onboarding partial: customer 15 (2 warnings)",
  "duration_seconds": 50.475641,
  "details": {
    "company_name": "LoadTest-Bell, Huang and Jones",
    "email": "duncanrebecca@example.org",
    "step1_complete": "success",
    "customer_id": 15,
    "accounts_created": 20,
    "step1_duration_s": 24.01,
    "complete_response": {
      "account_details": [
        {
          "account_id": 15001,
          "account_name": "LoadTest-Bell, Huang and Jones-Production",
          "uuid": "dc_acct_019c96ba-08c0-7af3-b712-6786cd9c8ab2"
        },
        {
          "account_id": 15002,
          "account_name": "LoadTest-Bell, Huang and Jones-Staging",
          "uuid": "dc_acct_019c96ba-08c3-75b3-8243-4151e834a845"
        },
        {
          "account_id": 15003,
          "account_name": "LoadTest-Bell, Huang and Jones-Development",
          "uuid": "dc_acct_019c96ba-08c5-7bb6-b0b1-be868b924098"
        },
        {
          "account_id": 15004,
          "account_name": "LoadTest-Bell, Huang and Jones-Environment",
          "uuid": "dc_acct_019c96ba-08c7-7442-bf36-1de50f2b593e"
        },
        {
          "account_id": 15005,
          "account_name": "LoadTest-Bell, Huang and Jones-Workspace",
          "uuid": "dc_acct_019c96ba-08c9-79c9-a677-6bb544b023fd"
        },
        {
          "account_id": 15006,
          "account_name": "LoadTest-Bell, Huang and Jones-Cluster",
          "uuid": "dc_acct_019c96ba-08ca-770b-8b64-aed6e89ede4a"
        },
        {
          "account_id": 15007,
          "account_name": "LoadTest-Bell, Huang and Jones-Instance",
          "uuid": "dc_acct_019c96ba-08cc-7531-9c62-a01d615da82f"
        },
        {
          "account_id": 15008,
          "account_name": "LoadTest-Bell, Huang and Jones-Node",
          "uuid": "dc_acct_019c96ba-08ce-70b0-a1be-eceb175d2d73"
        },
        {
          "account_id": 15009,
          "account_name": "LoadTest-Bell, Huang and Jones-Server",
          "uuid": "dc_acct_019c96ba-08cf-76f1-9e0f-44a11a0bbd0b"
        },
        {
          "account_id": 15010,
          "account_name": "LoadTest-Bell, Huang and Jones-System",
          "uuid": "dc_acct_019c96ba-08d1-7cf7-8893-fb029f183400"
        },
        {
          "account_id": 15011,
          "account_name": "LoadTest-Bell, Huang and Jones-Account-11",
          "uuid": "dc_acct_019c96ba-08d3-736f-a136-c50eede5fff7"
        },
        {
          "account_id": 15012,
          "account_name": "LoadTest-Bell, Huang and Jones-Account-12",
          "uuid": "dc_acct_019c96ba-08d4-7210-a9f7-8c5c0ce5454f"
        },
        {
          "account_id": 15013,
          "account_name": "LoadTest-Bell, Huang and Jones-Account-13",
          "uuid": "dc_acct_019c96ba-08d6-7303-8075-e39cecb7b159"
        },
        {
          "account_id": 15014,
          "account_name": "LoadTest-Bell, Huang and Jones-Account-14",
          "uuid": "dc_acct_019c96ba-08d8-749d-ad96-4c801ed5c757"
        },
        {
          "account_id": 15015,
          "account_name": "LoadTest-Bell, Huang and Jones-Account-15",
          "uuid": "dc_acct_019c96ba-08d9-7fa0-82f5-498a1b83005c"
        },
        {
          "account_id": 15016,
          "account_name": "LoadTest-Bell, Huang and Jones-Account-16",
          "uuid": "dc_acct_019c96ba-08db-7a20-99ce-5dbd0a3a4860"
        },
        {
          "account_id": 15017,
          "account_name": "LoadTest-Bell, Huang and Jones-Account-17",
          "uuid": "dc_acct_019c96ba-08dc-7b18-933f-499275da65b7"
        },
        {
          "account_id": 15018,
          "account_name": "LoadTest-Bell, Huang and Jones-Account-18",
          "uuid": "dc_acct_019c96ba-08de-7d2e-bb6b-878c43ef3c09"
        },
        {
          "account_id": 15019,
          "account_name": "LoadTest-Bell, Huang and Jones-Account-19",
          "uuid": "dc_acct_019c96ba-08e0-731f-b762-26ff8217ba06"
        },
        {
          "account_id": 15020,
          "account_name": "LoadTest-Bell, Huang and Jones-Account-20",
          "uuid": "dc_acct_019c96ba-08e1-7a66-ab79-5cf0c7e41036"
        }
      ],
      "account_id_range": "15001 - 15020",
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
      "customer_id": 15,
      "customer_name": "LoadTest-Bell, Huang and Jones",
      "customer_uuid": "dc_cust_019c96ba-08b9-7a02-bc98-70ceb3a14a8e",
      "directory_provisioned": false,
      "message": "Onboarding complete! Customer, user, config, accounts, and demo CSV files created.",
      "onboarding_mode": "demo",
      "success": true
    },
    "step2_process_data": "failed: No response",
    "step3_register": "success",
    "user_id": 3,
    "user_customer_id": 16,
    "step4_login": "success",
    "step4_dashboard": "accessible",
    "accounts_visible": 0,
    "step5_scores_calc": "partial: No response",
    "step6_scores": "not_available"
  },
  "api_calls": 7,
  "errors": [
    "process-data did not fully succeed: No response",
    "Score calculation did not fully succeed (non-critical)"
  ]
}
```
