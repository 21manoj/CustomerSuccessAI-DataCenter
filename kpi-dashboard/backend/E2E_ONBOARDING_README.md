# E2E Onboarding + UI Login Test

## What it does

1. **POST /api/onboarding/complete** – Creates customer 102, admin user (email + password), config, accounts, and generates all 6 CSVs in `verticals/customer102-dc2_s/data/`.
2. **POST /api/onboarding/process-data** – Loads CSVs into DB (accounts, dc2s_kpis, qualitative_signals, products, profiles).
3. **POST /api/login** – Verifies UI login works with the created user.
4. Writes **E2E_UI_CREDENTIALS.txt** with email/password for manual UI check.

## Run e2e (backend must be running)

```bash
# Terminal 1: start backend
cd kpi-dashboard/backend
python3 app_v3_minimal.py

# Terminal 2: run e2e test
cd kpi-dashboard/backend
python3 test_onboarding_e2e_ui.py
```

On success you get:

- Customer 102 and user `e2e-ui@test.example.com` / `E2eUiPass123!`
- 6 CSVs generated and loaded
- **E2E_UI_CREDENTIALS.txt** updated with credentials

## UI login

Open the KPI Dashboard UI, go to the login page, and use:

- **Email:** `e2e-ui@test.example.com`
- **Password:** `E2eUiPass123!`

Credentials are also in `backend/E2E_UI_CREDENTIALS.txt`.

## Re-run

The test uses `idempotent: true` for `/complete`, so re-running is safe: existing customer 102 is reused, then process-data and login are run again.
