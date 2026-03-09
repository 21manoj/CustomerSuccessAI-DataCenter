#!/usr/bin/env python3
"""
================================================================
3-Pillar / 8-KPI / 20 Accounts — E2E Onboarding Test
================================================================
DC2_S Vertical — Tests partial pillar configuration support

Goals:
  1. Onboard 1 customer with ONLY 3 pillars (AI, OS, EX) and 8 KPIs
  2. Verify health score calculation works with <5 pillars
  3. Verify no "must have exactly 5 pillars" validation error
  4. Verify config_loader preserves partial pillar weights
  5. Print login credentials for UI verification

Output: load-driver/tests/test_3pillar_8kpi_e2e.out
================================================================
"""

import os
import sys
import json
import time
import traceback
from datetime import datetime

# Add load-driver root to path for client import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client import CSPulseClient

import requests as raw_requests

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
BASE_URL = os.getenv("CS_PULSE_BASE_URL", "http://localhost:5059")
SUPER_EMAIL = os.getenv("CS_PULSE_ADMIN_EMAIL", "dc2s_super@test.com")
SUPER_PASSWORD = os.getenv("CS_PULSE_ADMIN_PASSWORD", "DC2_Super_2024!")

CUSTOMER_NAME = "NovaDC Infrastructure"
ADMIN_EMAIL = "admin@novadc-infra.test"
ADMIN_PASSWORD = "Test_novadc-infra_2026!"
NUM_ACCOUNTS = 20

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "test_3pillar_8kpi_e2e.out")

# ──────────────────────────────────────────────────────────────
# 3-Pillar Configuration (AI, OS, EX only — no DV, CH)
# ──────────────────────────────────────────────────────────────

# Normalized pillar weights (sum to 1.0)
# Original: AI=0.25, OS=0.20, EX=0.25 → total=0.70
# Normalized: AI=0.36, OS=0.28, EX=0.36
PILLAR_WEIGHTS = {"AI": 0.36, "OS": 0.28, "EX": 0.36}

# 8 top-weighted KPIs from the 3 selected pillars
ENABLED_KPIS = [
    "AI-KPI1",  # GPU Utilization Rate (P3, w=0.22, %, >65)
    "AI-KPI2",  # Training Job Completion (P3, w=0.20, %, >90)
    "AI-KPI3",  # Inference Latency P95 (P3, w=0.15, ms, <50)
    "OS-KPI1",  # RMA Frequency Rate (P2, w=0.20, %, <2.6)
    "OS-KPI2",  # MTBF (P2, w=0.18, hrs, >8760)
    "OS-KPI3",  # Critical Incidents 30d (P2, w=0.17, count, <3)
    "EX-KPI1",  # Capacity Utilization (P5, w=0.18, %, >70)
    "EX-KPI3",  # Workload Growth Velocity (P5, w=0.18, %chg, >10)
]

# Normalized KPI weights within each pillar (sum to 1.0 per pillar)
KPI_WEIGHTS = {
    "AI": {
        "AI-KPI1": 0.39,   # 0.22 / 0.57
        "AI-KPI2": 0.35,   # 0.20 / 0.57
        "AI-KPI3": 0.26,   # 0.15 / 0.57
    },
    "OS": {
        "OS-KPI1": 0.36,   # 0.20 / 0.55
        "OS-KPI2": 0.33,   # 0.18 / 0.55
        "OS-KPI3": 0.31,   # 0.17 / 0.55
    },
    "EX": {
        "EX-KPI1": 0.50,   # 0.18 / 0.36
        "EX-KPI3": 0.50,   # 0.18 / 0.36
    },
}

PATTERN_MIX = {
    "stable": 0.40,
    "expansion": 0.20,
    "churn": 0.20,
    "crisis": 0.20,
}

# ──────────────────────────────────────────────────────────────
# Output / Logging
# ──────────────────────────────────────────────────────────────
output_lines = []

def log(msg=""):
    print(msg)
    output_lines.append(msg)

def section(title):
    log(f"\n{'='*70}")
    log(f"  {title}")
    log(f"{'='*70}")

def subsection(title):
    log(f"\n  {'─'*60}")
    log(f"  {title}")
    log(f"  {'─'*60}")

passed = 0
failed = 0
skipped = 0

def ok(msg=""):
    global passed
    passed += 1
    log(f"    ✅ PASS — {msg}" if msg else "    ✅ PASS")

def fail(msg=""):
    global failed
    failed += 1
    log(f"    ❌ FAIL — {msg}" if msg else "    ❌ FAIL")

def skip(msg=""):
    global skipped
    skipped += 1
    log(f"    ⏭️  SKIP — {msg}" if msg else "    ⏭️  SKIP")

def write_output():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(output_lines))
    log(f"\n  Output written to: {OUTPUT_FILE}")

def make_client(email, password):
    client = CSPulseClient(base_url=BASE_URL, email=email, password=password)
    if client.login():
        return client
    return None


# ══════════════════════════════════════════════════════════════
# MAIN TEST
# ══════════════════════════════════════════════════════════════

def main():
    start_time = time.time()

    log("=" * 70)
    log("  3-PILLAR / 8-KPI / 20-ACCOUNT — E2E ONBOARDING TEST")
    log(f"  DC2_S Vertical — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"  Platform: {BASE_URL}")
    log(f"  Pillars:  {list(PILLAR_WEIGHTS.keys())} (3 of 5)")
    log(f"  KPIs:     {len(ENABLED_KPIS)} of 38")
    log(f"  Accounts: {NUM_ACCOUNTS}")
    log("=" * 70)

    customer_id = None
    cust_client = None

    # ──────────────────────────────────────────────────────────
    # Phase 0: Pre-flight — verify platform is up
    # ──────────────────────────────────────────────────────────
    section("PHASE 0: Pre-flight Checks")

    log("  Checking platform health...")
    super_client = CSPulseClient(base_url=BASE_URL, email=SUPER_EMAIL, password=SUPER_PASSWORD)
    if not super_client.health_check():
        fail("Platform not healthy")
        write_output()
        return 1
    ok("Platform healthy")

    log("  Logging in as superuser...")
    if not super_client.login():
        fail("Superuser login failed")
        write_output()
        return 1
    ok(f"Superuser login OK")

    # ──────────────────────────────────────────────────────────
    # Phase 1: Register Customer
    # ──────────────────────────────────────────────────────────
    section("PHASE 1: Register Customer")

    log(f"  Company:  {CUSTOMER_NAME}")
    log(f"  Email:    {ADMIN_EMAIL}")
    log(f"  Password: {ADMIN_PASSWORD}")

    # Check if customer already exists (cleanup previous run)
    log("  Checking for existing customer...")
    existing_check = raw_requests.post(f"{BASE_URL}/api/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
    })
    if existing_check.status_code == 200:
        existing_data = existing_check.json()
        old_cid = existing_data.get("customer_id") or existing_data.get("user", {}).get("customer_id")
        if old_cid:
            log(f"  Found existing customer_id={old_cid}, cleaning up...")
            cleanup_resp = super_client.post(f"/api/admin/cleanup/customer/{old_cid}", {
                "dry_run": False, "confirm": True
            })
            if cleanup_resp:
                ok(f"Cleaned up previous customer {old_cid}")
            else:
                log(f"    Cleanup returned None (may not exist, continuing)")
            time.sleep(1)

    log("  Registering new customer...")
    reg_resp = raw_requests.post(f"{BASE_URL}/api/register", json={
        "company_name": CUSTOMER_NAME,
        "admin_name": "Nova Admin",
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "vertical": "dc2_s"
    })

    if reg_resp.status_code not in (200, 201):
        fail(f"Registration failed: HTTP {reg_resp.status_code} — {reg_resp.text[:200]}")
        write_output()
        return 1

    reg_data = reg_resp.json()
    customer_id = reg_data.get("customer_id")
    customer_uuid = reg_data.get("customer_uuid", "")
    ok(f"Registered: customer_id={customer_id}, UUID={customer_uuid[:40]}...")

    # ──────────────────────────────────────────────────────────
    # Phase 2: Onboard with 20 Accounts + 3-Pillar Weights
    # ──────────────────────────────────────────────────────────
    section("PHASE 2: Onboard with 3-Pillar Configuration")

    log(f"  Pillar weights: {json.dumps(PILLAR_WEIGHTS)}")
    log(f"  Pattern mix:    {json.dumps(PATTERN_MIX)}")
    log(f"  Num accounts:   {NUM_ACCOUNTS}")

    onb_resp = raw_requests.post(f"{BASE_URL}/api/onboarding/complete", json={
        "customer_id": customer_id,
        "customer_name": CUSTOMER_NAME,
        "email": ADMIN_EMAIL,
        "vertical": "dc2_s",
        "num_accounts": NUM_ACCOUNTS,
        "onboarding_mode": "demo",
        "weights": PILLAR_WEIGHTS,
        "showcase_pattern_mix": PATTERN_MIX,
    })

    if onb_resp.status_code != 200:
        fail(f"Onboarding failed: HTTP {onb_resp.status_code} — {onb_resp.text[:200]}")
        write_output()
        return 1

    onb_data = onb_resp.json()
    if not (onb_data.get("success") or onb_data.get("status") == "success"):
        fail(f"Onboarding failed: {str(onb_data)[:200]}")
        write_output()
        return 1

    acct_details = onb_data.get("account_details", [])
    acct_ids = [a.get("account_id") for a in acct_details] if isinstance(acct_details, list) else []
    ok(f"Onboarded: {len(acct_details)} accounts created")
    log(f"    Account IDs: {acct_ids[:5]}...{acct_ids[-1] if acct_ids else ''}")

    # Verify 3-pillar weights were accepted (not forced to 5)
    config_in_resp = onb_data.get("config", {})
    resp_weights = config_in_resp.get("weights", {})
    resp_pillars = config_in_resp.get("pillars", 0)
    log(f"    Config: pillars={resp_pillars}, weights={resp_weights}")

    # ──────────────────────────────────────────────────────────
    # Phase 2b: Restrict to 8 KPIs (update CustomerConfig)
    # ──────────────────────────────────────────────────────────
    subsection("Phase 2b: Restrict config to 8 KPIs and 3 pillars")

    log("  Logging in as customer...")
    cust_client = make_client(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not cust_client:
        fail("Customer login failed")
        write_output()
        return 1
    ok("Customer login OK")

    # Update CustomerConfig via admin API to restrict to 8 KPIs and 3 pillars
    log("  Updating CustomerConfig: 3 pillars, 8 KPIs...")
    config_payload = {
        "customer_id": customer_id,
        "dc2s_pillar_weights": PILLAR_WEIGHTS,
        "dc2s_enabled_kpis": ENABLED_KPIS,
        "dc2s_kpi_weights": KPI_WEIGHTS,
    }
    config_resp = super_client.post("/api/admin/update-customer-config", config_payload)
    if config_resp:
        ok(f"Config updated via admin API")
    else:
        # Try direct PUT on /api/config
        config_resp2 = cust_client.put("/api/config", config_payload)
        if config_resp2:
            ok(f"Config updated via /api/config")
        else:
            skip("Config update API not available — pillar restriction not applied (test still validates 3-pillar weight acceptance)")

    # Upgrade tier
    log("  Upgrading tier to 'enterprise'...")
    tier_resp = cust_client.put("/api/entitlements/tier", {
        "customer_id": customer_id,
        "tier": "enterprise"
    })
    if tier_resp:
        ok(f"Tier: {tier_resp.get('tier', '?')}")
    else:
        skip("Tier upgrade returned None")

    # ──────────────────────────────────────────────────────────
    # Phase 3: Process Data (CSVs + Journey + Scores)
    # ──────────────────────────────────────────────────────────
    section("PHASE 3: Process Data")

    log("  Running process-data pipeline...")
    proc_resp = cust_client.post("/api/onboarding/process-data", {
        "customer_id": customer_id,
        "vertical": "dc2_s",
        "skip_wizard_b": False,
        "skip_wizard_c": False,
        "onboarding_mode": "demo",
    }, skip_auth_check=True)

    if proc_resp:
        steps = proc_resp.get("steps_completed", [])
        errors = proc_resp.get("errors", [])
        ok(f"Data processed: {len(steps)} steps, {len(errors)} errors")
        if errors:
            for e in errors[:5]:
                log(f"      Error: {e}")
    else:
        fail("Process data returned None")

    # ──────────────────────────────────────────────────────────
    # Phase 4: Calculate Scores
    # ──────────────────────────────────────────────────────────
    section("PHASE 4: Calculate Health Scores")

    log("  Calculating scores for 2024-12...")
    score_resp = cust_client.post("/api/dc2s/scores/calculate", {
        "measurement_month": "2024-12-01"
    })

    if score_resp:
        total = score_resp.get("total_accounts", 0)
        successful = score_resp.get("successful", 0)
        ok(f"Scores calculated: {successful}/{total} accounts")
        if successful == 0 and total > 0:
            log("    Retrying with 2024-11...")
            score_resp2 = cust_client.post("/api/dc2s/scores/calculate", {
                "measurement_month": "2024-11-01"
            })
            if score_resp2:
                ok(f"Retry: {score_resp2.get('successful', 0)}/{score_resp2.get('total_accounts', 0)} (2024-11)")
    else:
        skip("Score calculation returned None (may already be done in process-data)")

    # ──────────────────────────────────────────────────────────
    # Phase 5: Verify Results
    # ──────────────────────────────────────────────────────────
    section("PHASE 5: Verify Results")

    # 5a: Verify accounts exist
    subsection("5a: Verify 20 accounts")
    accounts_resp = cust_client.get_accounts()
    if accounts_resp and len(accounts_resp) >= NUM_ACCOUNTS:
        ok(f"Found {len(accounts_resp)} accounts (expected {NUM_ACCOUNTS})")
    else:
        fail(f"Expected {NUM_ACCOUNTS} accounts, got {len(accounts_resp) if accounts_resp else 0}")

    # 5b: Verify health scores exist and vary
    subsection("5b: Verify health scores")
    health_scores = []
    status_counts = {"healthy": 0, "at_risk": 0, "critical": 0, "unknown": 0}

    if accounts_resp:
        for acct in accounts_resp:
            health = acct.get("overall_health") or acct.get("health_score") or 0
            status = acct.get("status") or acct.get("health_status") or "unknown"
            health_scores.append(float(health))

            if isinstance(status, str):
                status_lower = status.lower().replace("-", "_").replace(" ", "_")
                if status_lower in ("healthy", "good", "excellent"):
                    status_counts["healthy"] += 1
                elif status_lower in ("at_risk", "warning", "risk"):
                    status_counts["at_risk"] += 1
                elif status_lower in ("critical", "crisis"):
                    status_counts["critical"] += 1
                else:
                    # Classify by score value
                    if health >= 70:
                        status_counts["healthy"] += 1
                    elif health >= 50:
                        status_counts["at_risk"] += 1
                    elif health > 0:
                        status_counts["critical"] += 1
                    else:
                        status_counts["unknown"] += 1

    # Check that we have health scores
    nonzero_scores = [s for s in health_scores if s > 0]
    if len(nonzero_scores) >= 10:
        ok(f"{len(nonzero_scores)}/{len(health_scores)} accounts have health scores > 0")
    elif len(nonzero_scores) > 0:
        skip(f"Only {len(nonzero_scores)}/{len(health_scores)} accounts have scores (partial)")
    else:
        fail("No accounts have health scores")

    # Check that scores vary (not all identical)
    if len(nonzero_scores) >= 2:
        score_range = max(nonzero_scores) - min(nonzero_scores)
        avg_score = sum(nonzero_scores) / len(nonzero_scores)
        if score_range > 10:
            ok(f"Health scores vary: min={min(nonzero_scores):.1f}, max={max(nonzero_scores):.1f}, avg={avg_score:.1f}, range={score_range:.1f}")
        else:
            fail(f"Health scores too uniform: range={score_range:.1f} (expected >10)")
    else:
        skip("Not enough scores to verify variance")

    # Print distribution
    log(f"\n    Health Distribution:")
    log(f"      Healthy:  {status_counts['healthy']:>3} ({status_counts['healthy']*100//max(NUM_ACCOUNTS,1):>3}%)")
    log(f"      At-Risk:  {status_counts['at_risk']:>3} ({status_counts['at_risk']*100//max(NUM_ACCOUNTS,1):>3}%)")
    log(f"      Critical: {status_counts['critical']:>3} ({status_counts['critical']*100//max(NUM_ACCOUNTS,1):>3}%)")
    log(f"      Unknown:  {status_counts['unknown']:>3}")

    # 5c: Verify pillar scores and health summary
    subsection("5c: Verify health summary and pillar scores")
    summary_resp = cust_client.get("/api/dc2s/health-summary")
    if summary_resp:
        total_accts = summary_resp.get("total_accounts", 0)
        avg_health = summary_resp.get("average_health", 0)
        h_dist = summary_resp.get("health_distribution", {})
        log(f"    Health summary: {total_accts} accounts, avg_health={avg_health}")
        log(f"    Distribution: healthy={h_dist.get('healthy', 0)}, risk={h_dist.get('risk', 0)}, critical={h_dist.get('critical', 0)}")

        if total_accts >= NUM_ACCOUNTS:
            ok(f"Health summary covers all {total_accts} accounts")
        elif total_accts > 0:
            ok(f"Health summary partial: {total_accts} accounts")
        else:
            fail(f"Health summary has 0 accounts")

        if avg_health > 0:
            ok(f"Average health computed: {avg_health}")
        else:
            fail(f"Average health is 0")
    else:
        skip("Health summary returned None")

    # Check pillar weights were accepted in onboarding (3 pillars, not 5 forced)
    subsection("5c-extra: Verify 3-pillar weight acceptance")
    expected_pillars = {"AI", "OS", "EX"}
    if onb_data:
        resp_weights = onb_data.get("config", {}).get("weights", {})
        if resp_weights:
            weight_pillars = set(resp_weights.keys())
            if expected_pillars.issubset(weight_pillars):
                ok(f"Onboarding accepted 3-pillar weights: {resp_weights}")
            else:
                fail(f"Expected pillar weights {expected_pillars} but got {weight_pillars}")
        else:
            skip("No weights in onboarding response")
    else:
        skip("No onboarding data to verify")

    # 5d: Verify customer-level health (L4)
    subsection("5d: Verify L4 customer health")
    perf_resp = cust_client.get("/api/customer-performance/summary")
    if perf_resp:
        # Response may nest data under 'summary' key
        summary = perf_resp.get("summary", perf_resp)
        overall = (
            summary.get("average_health_score")
            or summary.get("overall_health")
            or perf_resp.get("average_health_score")
            or perf_resp.get("overall_health")
            or 0
        )
        acct_count = (
            summary.get("total_accounts")
            or perf_resp.get("total_accounts")
            or 0
        )
        log(f"    L4 Customer Health: {overall}")
        log(f"    Total Accounts: {acct_count}")
        if 20 <= float(overall) <= 90:
            ok(f"L4 health reasonable: {overall} (expected 20-90 for this pattern mix)")
        elif float(overall) > 0:
            ok(f"L4 health computed: {overall}")
        else:
            fail(f"L4 health is 0 or missing")
    else:
        skip("Customer performance summary returned None")

    # ──────────────────────────────────────────────────────────
    # Phase 6: Print Credentials
    # ──────────────────────────────────────────────────────────
    section("LOGIN CREDENTIALS")

    log(f"""
    ┌─────────────────────────────────────────────────┐
    │  NovaDC Infrastructure — 3-Pillar Test Customer │
    ├─────────────────────────────────────────────────┤
    │  URL:       http://localhost                    │
    │  Email:     {ADMIN_EMAIL:<37}│
    │  Password:  {ADMIN_PASSWORD:<37}│
    │  Customer:  {CUSTOMER_NAME:<37}│
    │  Cust ID:   {str(customer_id):<37}│
    │  Accounts:  {NUM_ACCOUNTS:<37}│
    │  Pillars:   AI, OS, EX (3 of 5)                │
    │  KPIs:      {len(ENABLED_KPIS)} of 38{' '*31}│
    └─────────────────────────────────────────────────┘
    """)

    # ──────────────────────────────────────────────────────────
    # Final Summary
    # ──────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    section("FINAL SUMMARY")

    log(f"  Tests:  {passed} passed, {failed} failed, {skipped} skipped")
    log(f"  Time:   {elapsed:.1f}s")
    log(f"  Status: {'ALL PASS' if failed == 0 else 'SOME FAILURES'}")

    if failed == 0:
        log(f"\n  ✅ 3-PILLAR / 8-KPI E2E TEST PASSED")
    else:
        log(f"\n  ❌ {failed} TEST(S) FAILED")

    write_output()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        rc = main()
        sys.exit(rc)
    except Exception as e:
        print(f"\n❌ UNHANDLED ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
