#!/usr/bin/env python3
"""
Integration test for arc_decision_generator — runs against EC2 server.

Tests that Wizard A now generates DECISION nodes from arc templates
for 4-CSV customers (which lack decisions.csv).

Usage:
    python3 tests/test_arc_decision_generator.py [--base-url URL] [--api-key KEY]

Default: uses EC2 production instance.
"""

import argparse
import json
import requests
import sys
from datetime import datetime

BASE_URL = "https://d2oqfugrb2ltg9.cloudfront.net"
API_KEY = "csp_server_KxJnbLJQw5MzNYezCEhO10GRg8ZuMn5GCJ9tFKjw"


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def api(method, endpoint, data=None, customer_id=None):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    if customer_id:
        headers["X-Customer-ID"] = str(customer_id)
    url = f"{BASE_URL}{endpoint}"
    if method == "GET":
        r = requests.get(url, headers=headers, timeout=30)
    else:
        r = requests.post(url, json=data, headers=headers, timeout=60)
    return r.status_code, r.json() if r.content else {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--api-key", default=API_KEY)
    parser.add_argument("--customer-id", type=int, default=None,
                        help="Existing 4-CSV customer ID to test with")
    args = parser.parse_args()

    global BASE_URL, API_KEY
    BASE_URL = args.base_url
    API_KEY = args.api_key

    log("=" * 60)
    log("Arc Decision Generator Integration Test")
    log("=" * 60)

    # Step 1: Find or use a 4-CSV customer
    cid = args.customer_id
    if not cid:
        log("Finding a customer to test with...")
        status, data = api("GET", "/api/v1/customers")
        if status != 200:
            log(f"FAIL: Cannot list customers: {status}")
            return 1
        # Use any DC2S customer
        customers = data if isinstance(data, list) else data.get("customers", [])
        for c in customers:
            if c.get("vertical") == "dc2_s":
                cid = c.get("customer_id")
                log(f"Using customer {cid}: {c.get('customer_name', c.get('name', '?'))}")
                break
        if not cid:
            log("FAIL: No DC2S customer found")
            return 1

    # Step 2: Get accounts and check current DECISION node counts
    status, accounts = api("GET", f"/api/v1/accounts", customer_id=cid)
    if status != 200:
        log(f"FAIL: Cannot list accounts: {status}")
        return 1

    acct_list = accounts if isinstance(accounts, list) else accounts.get("accounts", [])
    if not acct_list:
        log(f"FAIL: No accounts for customer {cid}")
        return 1

    log(f"Customer {cid} has {len(acct_list)} accounts")

    # Check DECISION nodes before Wizard A
    sample_acct = acct_list[0]
    aid = sample_acct.get("account_id")
    log(f"Sample account: {aid} ({sample_acct.get('account_name', '?')})")

    status, nodes_before = api(
        "GET",
        f"/api/dc2s/{cid}/accounts/{aid}/context-graph/nodes?node_type=DECISION",
        customer_id=cid,
    )
    decision_count_before = len(nodes_before) if isinstance(nodes_before, list) else 0
    log(f"DECISION nodes before Wizard A: {decision_count_before}")

    # Step 3: Trigger Wizard A
    log("Triggering Wizard A...")
    status, result = api(
        "POST",
        f"/api/dc2s/{cid}/wizards/a/run",
        customer_id=cid,
    )
    if status not in (200, 201):
        # Try alternate endpoint
        status, result = api(
            "POST",
            f"/api/onboarding/{cid}/process-data",
            data={"wizard": "a"},
            customer_id=cid,
        )

    log(f"Wizard A result: status={status}")
    if isinstance(result, dict):
        log(f"  processed: {result.get('processed', '?')}")
        log(f"  decisions_created: {result.get('decisions_created', '?')}")
        log(f"  edges_created: {result.get('edges_created', '?')}")

    # Step 4: Check DECISION nodes after
    status, nodes_after = api(
        "GET",
        f"/api/dc2s/{cid}/accounts/{aid}/context-graph/nodes?node_type=DECISION",
        customer_id=cid,
    )
    decision_count_after = len(nodes_after) if isinstance(nodes_after, list) else 0
    log(f"DECISION nodes after Wizard A: {decision_count_after}")

    # Step 5: Assertions
    passed = 0
    failed = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            log(f"  PASS: {name}")
            passed += 1
        else:
            log(f"  FAIL: {name} {detail}")
            failed += 1

    log("\n--- Assertions ---")
    check("Wizard A completed", status in (200, 201), f"status={status}")
    check("DECISION nodes created", decision_count_after > 0,
          f"got {decision_count_after}")

    if isinstance(result, dict) and 'decisions_created' in result:
        check("decisions_created in result",
              result['decisions_created'] > 0,
              f"got {result['decisions_created']}")

    log(f"\nResults: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
