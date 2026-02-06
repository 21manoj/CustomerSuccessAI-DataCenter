#!/usr/bin/env python3
"""
E2E Onboarding + UI Login Test
==============================
Tests full onboarding flow and creates credentials for UI login.

Flow:
1. POST /api/onboarding/complete (customer_name, email, password, customer_id, num_accounts)
   -> Creates Customer, User with password, Config, Accounts, generates 6 CSVs
2. POST /api/onboarding/process-data (customer_id)
   -> Loads CSVs into DB (accounts, dc2s_kpis, qualitative_signals, products, profiles)
3. POST /api/login (email, password) -> Validates UI login works
4. Writes E2E_UI_CREDENTIALS.txt with email/password for manual UI check

Run: From backend dir, with Flask app running on BASE_URL:
  python3 test_onboarding_e2e_ui.py

Or run backend first:
  python3 app_v3_minimal.py &
  python3 test_onboarding_e2e_ui.py
"""

import sys
import os
import json
import requests
from pathlib import Path
from datetime import datetime

# Backend URL (must match running app)
BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:5059")

# E2E test user - created by /complete, used for UI login
E2E_CUSTOMER_ID = 102
E2E_CUSTOMER_NAME = "E2E UI Test Customer"
E2E_EMAIL = "e2e-ui@test.example.com"
E2E_PASSWORD = "E2eUiPass123!"
E2E_NUM_ACCOUNTS = 5

# Credentials file written after successful onboarding
CREDENTIALS_FILE = Path(__file__).parent / "E2E_UI_CREDENTIALS.txt"


def main():
    print("=" * 60)
    print("E2E Onboarding + UI Login Test")
    print("=" * 60)
    print(f"Backend URL: {BASE_URL}")
    print(f"Customer ID: {E2E_CUSTOMER_ID}")
    print(f"Email: {E2E_EMAIL}")
    print(f"Password: {E2E_PASSWORD}")
    print()

    # Health check
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if r.status_code != 200:
            print(f"ERROR: Backend health returned {r.status_code}")
            return 1
        print("OK Backend is up")
    except Exception as e:
        print(f"ERROR: Cannot reach backend at {BASE_URL}: {e}")
        print("Start backend: cd kpi-dashboard/backend && python3 app_v3_minimal.py")
        return 1

    # Step 1: Complete onboarding (correct API: customer_name, email, password)
    print("\n--- Step 1: POST /api/onboarding/complete ---")
    try:
        r = requests.post(
            f"{BASE_URL}/api/onboarding/complete",
            json={
                "customer_id": E2E_CUSTOMER_ID,
                "customer_name": E2E_CUSTOMER_NAME,
                "email": E2E_EMAIL,
                "password": E2E_PASSWORD,
                "num_accounts": E2E_NUM_ACCOUNTS,
                "vertical": "dc2_s",
                "idempotent": True,  # Re-run safe: return existing customer if already created
            },
            timeout=120,
        )
        if r.status_code != 200:
            print(f"ERROR: complete failed: {r.status_code}")
            print(r.text[:500])
            return 1
        data = r.json()
        print(f"OK customer_id={data.get('customer_id')} accounts={data.get('accounts')}")
        print(f"   csv_files_generated={data.get('csv_files_generated')}")
        if not data.get("csv_files_generated"):
            print("   WARNING: CSVs not generated; process-data may have nothing to load")
        if data.get("user"):
            print(f"   user: {data['user'].get('email')} (created={data['user'].get('created')})")
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    # Step 2: Process data (load CSVs into DB)
    print("\n--- Step 2: POST /api/onboarding/process-data ---")
    try:
        r = requests.post(
            f"{BASE_URL}/api/onboarding/process-data",
            json={"customer_id": E2E_CUSTOMER_ID},
            timeout=300,
        )
        if r.status_code != 200:
            print(f"ERROR: process-data failed: {r.status_code}")
            print(r.text[:800])
            return 1
        data = r.json()
        steps = data.get("steps_completed", [])
        print(f"OK steps_completed: {steps}")
        if "data_loading" not in steps:
            print("   WARNING: data_loading not in steps_completed")
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    # Step 3: UI login
    print("\n--- Step 3: POST /api/login (UI credentials) ---")
    try:
        r = requests.post(
            f"{BASE_URL}/api/login",
            json={"email": E2E_EMAIL, "password": E2E_PASSWORD},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"ERROR: login failed: {r.status_code}")
            print(r.text[:300])
            return 1
        body = r.json()
        print(f"OK login success: {body.get('status', body)}")
        print(f"   user_id/customer_id in response or session")
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    # Write credentials file for UI login
    creds_content = f"""# E2E Onboarding UI Login Credentials
# Generated: {datetime.now().isoformat()}
# Use these to log in via the KPI Dashboard UI.

Backend URL: {BASE_URL}
Login URL:   {BASE_URL.replace('/api','')}/login  or  {BASE_URL}/api/login (POST)

Email:    {E2E_EMAIL}
Password: {E2E_PASSWORD}

Customer ID: {E2E_CUSTOMER_ID}
Customer Name: {E2E_CUSTOMER_NAME}
"""
    CREDENTIALS_FILE.write_text(creds_content, encoding="utf-8")
    print(f"\nOK Wrote credentials to: {CREDENTIALS_FILE}")

    print("\n" + "=" * 60)
    print("E2E onboarding + UI login: ALL STEPS PASSED")
    print("=" * 60)
    print("To check in UI: open app, log in with the email/password above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
