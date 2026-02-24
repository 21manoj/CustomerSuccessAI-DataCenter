#!/usr/bin/env python3
"""
Seed Customer 5 via Onboarding API (loads directly into DB, no 02_Load* scripts).

POST /api/onboarding/complete writes directly to the database:
- Creates/updates Customer, CustomerConfig, and Account rows (no CSV, no 02_load*).
- Does NOT run any 02_load* scripts.

After a successful call, dc2s_super@test.com (customer_id=5) will see accounts.

Recommended: run with backend server already up (avoids startup DB errors in test client).

  curl -s -X POST http://localhost:8001/api/onboarding/complete \\
    -H "Content-Type: application/json" \\
    -d '{"customer_id":5,"customer_name":"DC2S Customer 5","vertical":"dc2_s","num_accounts":10,"idempotent":true}'
"""

import os
import sys
import json
import urllib.request

def main():
    base = os.getenv("API_BASE_URL", "http://localhost:8001")
    url = f"{base}/api/onboarding/complete"
    payload = {
        "customer_id": 5,
        "customer_name": "DC2S Customer 5",
        "vertical": "dc2_s",
        "num_accounts": 10,
        "industry": "Technology",
        "idempotent": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {"error": body}
        print(f"HTTP {e.code}: {json.dumps(data, indent=2)}")
        sys.exit(1)
    except Exception as e:
        print(f"Request failed: {e}")
        print("Ensure the backend is running (e.g. port 8001) and try again.")
        sys.exit(1)
    if data.get("success"):
        print("OK: Onboarding complete for customer 5.")
        print(f"   Accounts: {data.get('accounts', 'N/A')}")
        print("   Log in as dc2s_super@test.com to see data.")
    else:
        print(json.dumps(data, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
