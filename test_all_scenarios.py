#!/usr/bin/env python3
"""
Comprehensive Test: All 9 Scenarios × 3 KPI Configurations × 15 Accounts

Test Matrix:
  A) Toggle OFF  — Default (38 KPIs, all 5 pillars)
  B) Toggle ON   — Minimal (12 KPIs, all 5 pillars)  [Power-of-1 compliant]
  C) Toggle ON   — Medium  (15 KPIs, all 5 pillars)

Flow per config:
  1. Scenario 1 (Onboarding) → creates new customer with 15 accounts
  2. Scenarios 2a, 2b, 2c, 2d, 2e (Analytics suite)
  3. Scenario 3 (Tenant Isolation)
  4. Scenario 5 (ROI Power-of-1)
  5. Scenario 8 (Context Graph)
  6. Scenario 9 (ROI Simulation)
  7. Scenario 4 (Cleanup) — at the very end

Skipped:
  - Scenario 6 (N8N Workflow) — requires external n8n service
  - Scenario 7 (Data Ingestion) — requires Google Sheets integration
"""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:5059"
LOGIN_EMAIL = "dc2s_super@test.com"
LOGIN_PASSWORD = "DC2_Super_2024!"

# KPI Presets
MINIMAL_KPIS = [
    'P1-KPI1', 'P2-KPI1', 'P2-KPI2', 'P2-KPI3',
    'P3-KPI2', 'P3-KPI3', 'P4-KPI1', 'P4-KPI2',
    'P4-KPI3', 'P5-KPI1', 'P5-KPI2', 'P5-KPI3',
]

MEDIUM_KPIS = MINIMAL_KPIS + ['P1-KPI2', 'P2-KPI4', 'P3-KPI1']

ALL_PILLARS = ['P1', 'P2', 'P3', 'P4', 'P5']

# Scenarios to run (in order) — 2-phase: onboarding first, then rest
ONBOARDING = ['1']
POST_ONBOARDING = ['2a', '2b', '2c', '2d', '2e', '3', '5', '8', '9']

# Polling config
POLL_INTERVAL = 10  # seconds
MAX_POLL_TIME = 900  # 15 minutes max per batch


# ─────────────────────────────────────────────────────────────────
# Session & Auth
# ─────────────────────────────────────────────────────────────────

session = requests.Session()


def login():
    resp = session.post(f"{BASE_URL}/api/login", json={
        "email": LOGIN_EMAIL,
        "password": LOGIN_PASSWORD,
    })
    if resp.status_code == 200:
        print("✅ Login: success")
        return True
    else:
        print(f"❌ Login failed: {resp.status_code} — {resp.text[:200]}")
        return False


# ─────────────────────────────────────────────────────────────────
# Run & Poll helpers
# ─────────────────────────────────────────────────────────────────

def start_run(scenario_ids, customer_id, options=None):
    """Start a test run and return (run_id, response_json) or (None, error_text)."""
    payload = {
        "scenario_ids": scenario_ids,
        "customer_id": customer_id,
        "options": options or {},
    }
    resp = session.post(f"{BASE_URL}/api/test-runner/start", json=payload)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("run_id"), data
    else:
        return None, f"HTTP {resp.status_code}: {resp.text[:300]}"


def poll_run(run_id, label=""):
    """Poll until completed or timeout. Returns final status dict."""
    start = time.time()
    last_status = ""
    while time.time() - start < MAX_POLL_TIME:
        resp = session.get(f"{BASE_URL}/api/test-runner/status/{run_id}")
        if resp.status_code != 200:
            print(f"  ⚠️  Poll error: {resp.status_code}")
            time.sleep(POLL_INTERVAL)
            continue

        data = resp.json()
        status = data.get("status", "unknown")

        # Build scenario status line
        scenarios = data.get("scenarios", [])
        scenario_statuses = [(s.get("id", "?"), s.get("status", "?")) for s in scenarios]
        status_str = " | ".join(f"{sid}:{st}" for sid, st in scenario_statuses)
        elapsed = int(time.time() - start)

        if status_str != last_status:
            print(f"  [{elapsed:>4}s] {status} | {status_str}")
            last_status = status_str

        if status in ("completed", "error"):
            return data

        time.sleep(POLL_INTERVAL)

    print(f"  ⏰ TIMEOUT after {MAX_POLL_TIME}s")
    return {"status": "timeout", "scenarios": []}


def extract_scenario_results(poll_data):
    """Extract per-scenario pass/fail from poll response."""
    results = {}
    for s in poll_data.get("scenarios", []):
        sid = s.get("id", "?")
        status = s.get("status", "unknown")
        result = s.get("result", {})
        msg = result.get("message", "") if result else ""
        duration = result.get("duration_seconds", 0) if result else 0
        errors = result.get("errors", []) if result else []
        results[sid] = {
            "status": status,
            "message": msg,
            "duration": duration,
            "errors": errors[:2],  # first 2 errors only
        }
    return results


def get_customer_id_from_db(approx_id=None):
    """Get the most recently created customer_id from the customers endpoint."""
    resp = session.get(f"{BASE_URL}/api/test-runner/customers")
    if resp.status_code == 200:
        data = resp.json()
        # Handle both formats: {"customers": [...]} and [...]
        if isinstance(data, dict):
            customers = data.get("customers", [])
        else:
            customers = data
        if customers and isinstance(customers, list):
            # Return the highest customer_id (most recently created)
            latest = max(customers, key=lambda c: c.get("customer_id", 0) if isinstance(c, dict) else 0)
            if isinstance(latest, dict):
                return latest.get("customer_id")
    return None


# ─────────────────────────────────────────────────────────────────
# Test Configuration
# ─────────────────────────────────────────────────────────────────

CONFIGS = [
    {
        "name": "A: Toggle OFF — Default (38 KPIs)",
        "short": "Default-38",
        "options": {
            "numAccounts": 15,
        },
        # No enabled_kpis/enabled_pillars → backend uses all 38
    },
    {
        "name": "B: Toggle ON — Minimal (12 KPIs)",
        "short": "Minimal-12",
        "options": {
            "numAccounts": 15,
            "kpiPreset": "minimal",
            "enabledKpis": MINIMAL_KPIS,
            "enabledPillars": ALL_PILLARS,
        },
    },
    {
        "name": "C: Toggle ON — Medium (15 KPIs)",
        "short": "Medium-15",
        "options": {
            "numAccounts": 15,
            "kpiPreset": "medium",
            "enabledKpis": MEDIUM_KPIS,
            "enabledPillars": ALL_PILLARS,
        },
    },
]


# ─────────────────────────────────────────────────────────────────
# Main Test Runner
# ─────────────────────────────────────────────────────────────────

def run_test_set(config):
    """Run full scenario suite for one KPI configuration."""
    name = config["name"]
    options = config["options"]
    all_results = {}
    customer_id = None

    print(f"\n{'='*70}")
    print(f"  {name}")
    print(f"  Accounts: {options.get('numAccounts', 'default')}")
    if 'enabledKpis' in options:
        print(f"  KPIs: {len(options['enabledKpis'])} | Pillars: {len(options.get('enabledPillars', []))}")
    else:
        print(f"  KPIs: ALL (38) | Pillars: ALL (5)")
    print(f"{'='*70}")

    # ── Phase 1: Onboarding (creates customer) ──────────────────
    print(f"\n─── Phase 1: Onboarding (Scenario 1) ───")
    run_id, resp = start_run(ONBOARDING, "auto", options)
    if not run_id:
        print(f"  ❌ Failed to start: {resp}")
        return {"1": {"status": "start_failed", "message": str(resp), "duration": 0, "errors": []}}

    print(f"  Run ID: {run_id}")
    poll_data = poll_run(run_id, "Onboarding")
    results_1 = extract_scenario_results(poll_data)
    all_results.update(results_1)

    # Get the real customer_id — try from scenario result details first, then DB
    if results_1.get("1", {}).get("status") == "pass":
        # Try to extract from scenario result details
        for s in poll_data.get("scenarios", []):
            if s.get("id") == "1" and s.get("result"):
                details = s["result"].get("details", {})
                if details.get("customer_id"):
                    customer_id = details["customer_id"]
                    break

        # Fallback: get from DB (most recently created)
        if not customer_id:
            customer_id = get_customer_id_from_db()

        if customer_id:
            print(f"  ✅ Customer created: ID={customer_id}")

            # Verify KPI count
            resp2 = session.get(f"{BASE_URL}/api/dc2s/customer-config/{customer_id}")
            if resp2.status_code == 200:
                cc = resp2.json()
                kpi_count = cc.get("enabled_kpi_count", "?")
                print(f"  📊 Enabled KPIs: {kpi_count}")
        else:
            print(f"  ⚠️  Could not determine customer_id — using temp ID from run")
            customer_id = poll_data.get("customer_id")
    else:
        print(f"  ❌ Onboarding failed — skipping remaining scenarios")
        # Mark all remaining as skipped
        for sid in POST_ONBOARDING:
            all_results[sid] = {"status": "skipped", "message": "Onboarding failed", "duration": 0, "errors": []}
        return all_results

    # ── Phase 2: Post-onboarding scenarios ──────────────────────
    print(f"\n─── Phase 2: Scenarios {', '.join(POST_ONBOARDING)} (customer={customer_id}) ───")

    # Run post-onboarding scenarios in batches to avoid overwhelming
    # Batch 1: 2a, 2b, 2c, 2d, 2e (analytics suite)
    # Batch 2: 3, 5 (isolation + ROI)
    # Batch 3: 8, 9 (context graph + ROI sim)
    batches = [
        ("Analytics (2a-2e)", ['2a', '2b', '2c', '2d', '2e']),
        ("Isolation + ROI (3, 5)", ['3', '5']),
        ("Context Graph + ROI Sim (8, 9)", ['8', '9']),
    ]

    for batch_name, batch_ids in batches:
        print(f"\n  ▶ Batch: {batch_name}")
        # Strip options that only apply to onboarding
        post_options = {"numAccounts": options.get("numAccounts", 15)}

        run_id, resp = start_run(batch_ids, customer_id, post_options)
        if not run_id:
            print(f"    ❌ Failed to start: {resp}")
            for sid in batch_ids:
                all_results[sid] = {"status": "start_failed", "message": str(resp)[:200], "duration": 0, "errors": []}
            continue

        print(f"    Run ID: {run_id}")
        poll_data = poll_run(run_id, batch_name)
        batch_results = extract_scenario_results(poll_data)
        all_results.update(batch_results)

        # Brief pause between batches
        time.sleep(2)

    return all_results


def print_summary(all_configs_results):
    """Print final summary table."""
    print(f"\n\n{'='*90}")
    print(f"  COMPREHENSIVE TEST RESULTS MATRIX")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*90}")

    # All scenario IDs in order
    all_sids = ['1'] + POST_ONBOARDING

    # Header
    header = f"  {'Scenario':<30}"
    for config in CONFIGS:
        header += f" | {config['short']:^14}"
    print(header)
    print(f"  {'─'*30}" + "─┼─".join(["─"*14] * len(CONFIGS)) + "─")

    # Scenario names
    scenario_names = {
        '1': 'Onboarding',
        '2a': 'KPI Simulation',
        '2b': 'RAG Queries',
        '2c': 'Signal Detection',
        '2d': 'RACI Reports',
        '2e': 'Churn Lifecycle',
        '3': 'Tenant Isolation',
        '5': 'ROI Power-of-1',
        '8': 'Context Graph',
        '9': 'ROI Simulation',
    }

    # Rows
    totals = {config["short"]: {"pass": 0, "fail": 0, "skip": 0} for config in CONFIGS}

    for sid in all_sids:
        sname = scenario_names.get(sid, f"Scenario {sid}")
        row = f"  {sid + ': ' + sname:<30}"
        for config, results in zip(CONFIGS, all_configs_results):
            r = results.get(sid, {})
            status = r.get("status", "—")
            dur = r.get("duration", 0)

            if status == "pass":
                cell = f"✅ {dur}s"
                totals[config["short"]]["pass"] += 1
            elif status == "fail":
                cell = f"❌ FAIL"
                totals[config["short"]]["fail"] += 1
            elif status in ("skipped", "start_failed"):
                cell = f"⏭️  SKIP"
                totals[config["short"]]["skip"] += 1
            else:
                cell = f"⚠️  {status[:8]}"
                totals[config["short"]]["fail"] += 1

            row += f" | {cell:^14}"
        print(row)

    # Totals
    print(f"  {'─'*30}" + "─┼─".join(["─"*14] * len(CONFIGS)) + "─")
    row = f"  {'TOTALS':<30}"
    for config in CONFIGS:
        t = totals[config["short"]]
        cell = f"P:{t['pass']} F:{t['fail']} S:{t['skip']}"
        row += f" | {cell:^14}"
    print(row)

    # Print errors for failed scenarios
    has_errors = False
    for config, results in zip(CONFIGS, all_configs_results):
        for sid in all_sids:
            r = results.get(sid, {})
            if r.get("status") == "fail" and r.get("errors"):
                if not has_errors:
                    print(f"\n{'─'*70}")
                    print(f"  ERRORS")
                    print(f"{'─'*70}")
                    has_errors = True
                print(f"\n  [{config['short']}] Scenario {sid}:")
                for err in r.get("errors", [])[:2]:
                    print(f"    → {err[:200]}")
            elif r.get("status") == "fail" and r.get("message"):
                if not has_errors:
                    print(f"\n{'─'*70}")
                    print(f"  ERRORS")
                    print(f"{'─'*70}")
                    has_errors = True
                print(f"\n  [{config['short']}] Scenario {sid}: {r['message'][:200]}")


# ─────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"{'='*70}")
    print(f"  CS Pulse — Comprehensive Scenario Test")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Configs: 3 (Default/Minimal/Medium)")
    print(f"  Accounts: 15 per customer")
    print(f"  Scenarios: {len(ONBOARDING) + len(POST_ONBOARDING)} per config")
    print(f"{'='*70}")

    if not login():
        sys.exit(1)

    all_results = []
    customer_ids = []

    for config in CONFIGS:
        results = run_test_set(config)
        all_results.append(results)

    # Print comprehensive summary
    print_summary(all_results)

    print(f"\n✅ Test suite complete.\n")
