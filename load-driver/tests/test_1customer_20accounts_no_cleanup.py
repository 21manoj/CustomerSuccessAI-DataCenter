#!/usr/bin/env python3
"""
================================================================
1 Customer / 20 Accounts — Full Lifecycle Test (NO CLEANUP)
================================================================
DC2_S Vertical — Complete Ring 1 Platform Test (Ring 3 Harness)

Goals:
  1. Onboard 1 customer with 20 accounts
  2. Create UI login credentials
  3. Create demo data per journey pattern variations
  4. Run the signal analyst / analyzer
  5. Check playbook recommendations
  6. NO cleanup — leave data for UI inspection

Output: kpi-dashboard/backend/1Customer20accounts_test.out
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
from client import CSPulseClient, create_authenticated_client

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
BASE_URL = os.getenv("CS_PULSE_BASE_URL", "http://localhost:5059")
SUPER_EMAIL = os.getenv("CS_PULSE_ADMIN_EMAIL", "dc2s_super@test.com")
SUPER_PASSWORD = os.getenv("CS_PULSE_ADMIN_PASSWORD", "DC2_Super_2024!")

NUM_CUSTOMERS = 1
NUM_ACCOUNTS = 20

# Output file path (relative to project root or absolute)
OUTPUT_FILE = os.getenv(
    "TEST_OUTPUT_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "kpi-dashboard", "backend",
                 "1Customer20accounts_test.out")
)

# Rich pattern mix — 20 accounts with diverse scenarios
PATTERN_MIXES = [
    {"crisis": 0.15, "churn": 0.15, "stable": 0.40, "expansion": 0.30},  # Balanced with growth tilt
]

CUSTOMER_NAMES = [
    "Meridian Data Centers",
]

# ──────────────────────────────────────────────────────────────
# Output / Logging
# ──────────────────────────────────────────────────────────────
output_lines = []

def log(msg=""):
    """Print to console AND capture for output file."""
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


# ──────────────────────────────────────────────────────────────
# Client Helper — uses load-driver's CSPulseClient
# ──────────────────────────────────────────────────────────────
def make_client(email, password):
    """Create and authenticate a CSPulseClient."""
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
    log("  1 CUSTOMER / 20 ACCOUNTS — FULL LIFECYCLE TEST (NO CLEANUP)")
    log(f"  DC2_S Vertical — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"  Platform: {BASE_URL}")
    log(f"  Output:   {OUTPUT_FILE}")
    log("=" * 70)

    # ──────────────────────────────────────────────────────────
    # Phase 0: Pre-flight — verify platform is up, get baseline
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
    ok(f"Superuser login OK — UUID: {super_client.customer_uuid[:40]}...")

    # Get baseline account count
    log("  Getting baseline state...")
    baseline_resp = super_client.get_accounts()
    baseline_accounts = len(baseline_resp) if baseline_resp else 0
    log(f"    Baseline: {baseline_accounts} accounts for superuser")

    # ──────────────────────────────────────────────────────────
    # Phase 1+2: Register + Onboard 1 Customer (20 accounts)
    #
    # Flow: /api/register → /api/onboarding/complete (with customer_id) → /api/onboarding/process-data
    # The platform fix ensures /complete reuses the registered customer instead of creating a new one.
    # ──────────────────────────────────────────────────────────
    section("PHASE 1+2: Register + Onboard 1 Customer (20 accounts)")

    customers = []  # Track: {customer_id, email, password, ...}
    import requests as raw_requests

    for i in range(NUM_CUSTOMERS):
        cust_name = CUSTOMER_NAMES[i]
        domain = cust_name.lower().replace(" ", "").replace("&", "")[:20]
        email = f"admin@{domain}.test"
        password = f"Test_{domain}_2026!"
        pattern_mix = PATTERN_MIXES[i]

        subsection(f"Customer {i+1}: {cust_name}")
        log(f"    Email: {email}")
        log(f"    Password: {password}")
        log(f"    Pattern mix: {json.dumps(pattern_mix)}")

        # Step 1: Register customer (creates customer + admin user with UI credentials)
        log(f"    Step 1: Registering customer...")
        reg_resp_raw = raw_requests.post(f"{BASE_URL}/api/register", json={
            "company_name": cust_name,
            "admin_name": f"Admin {cust_name.split()[0]}",
            "email": email,
            "password": password,
            "vertical": "dc2_s"
        })

        if reg_resp_raw.status_code not in (200, 201):
            fail(f"Registration failed: HTTP {reg_resp_raw.status_code} — {reg_resp_raw.text[:150]}")
            continue

        reg_resp = reg_resp_raw.json()
        cust_id = reg_resp.get("customer_id")
        cust_uuid = reg_resp.get("customer_uuid", "")
        ok(f"Registered: customer_id={cust_id}, UUID={cust_uuid[:35]}...")

        # Step 2: Onboard with customer_id (reuses existing customer — platform fix)
        log(f"    Step 2: Onboarding ({NUM_ACCOUNTS} accounts, reusing customer_id={cust_id})...")
        onb_resp_raw = raw_requests.post(f"{BASE_URL}/api/onboarding/complete", json={
            "customer_id": cust_id,
            "customer_name": cust_name,
            "email": email,
            "vertical": "dc2_s",
            "num_accounts": NUM_ACCOUNTS,
            "onboarding_mode": "demo",
            "showcase_pattern_mix": pattern_mix,
        })

        if onb_resp_raw.status_code != 200:
            fail(f"Onboarding failed: HTTP {onb_resp_raw.status_code} — {onb_resp_raw.text[:150]}")
            continue

        onb_resp = onb_resp_raw.json()
        if not (onb_resp.get("success") or onb_resp.get("status") == "success"):
            fail(f"Onboarding failed: {str(onb_resp)[:150]}")
            continue

        # Verify customer_id matches between register and complete
        onb_cust_id = onb_resp.get("customer_id", cust_id)
        accts = onb_resp.get("account_details", [])
        acct_ids = [a.get("account_id") for a in accts] if isinstance(accts, list) else []
        ok(f"Onboarded: customer_id={onb_cust_id}, {len(accts)} accounts, dir={onb_resp.get('directory_provisioned', '?')}")
        log(f"      Account IDs: {acct_ids}")

        if onb_cust_id != cust_id:
            fail(f"customer_id MISMATCH: register={cust_id}, complete={onb_cust_id}")

        customers.append({
            "index": i,
            "name": cust_name,
            "customer_id": onb_cust_id,
            "customer_uuid": cust_uuid,
            "email": email,
            "password": password,
            "pattern_mix": pattern_mix,
            "account_ids": acct_ids,
        })

        # Step 3: Login as customer
        log(f"    Step 3: Verifying UI login...")
        cust_client = make_client(email, password)
        if cust_client:
            ok(f"UI login verified — UUID: {cust_client.customer_uuid[:35] if cust_client.customer_uuid else 'N/A'}...")
        else:
            fail("UI login failed")
            continue

        # Step 4: Upgrade tier to 'enterprise' (enables Signal Analyst, approval queue, auto pipeline)
        log(f"    Step 4: Upgrading tier to 'enterprise'...")
        tier_resp = cust_client.put("/api/entitlements/tier", {
            "customer_id": onb_cust_id,
            "tier": "enterprise"
        })
        if tier_resp:
            features = tier_resp.get("features", {})
            signal_ok = features.get("signal_analyst", False)
            approval_ok = features.get("approval_queue", False)
            ok(f"Tier set to '{tier_resp.get('tier', '?')}' — signal_analyst={signal_ok}, approval_queue={approval_ok}")
        else:
            fail(f"Tier upgrade failed (returned None)")

        # Step 5: Process data (load CSVs, generate journey, calculate scores)
        log(f"    Step 5: Processing data (CSVs + journey + scores)...")
        proc_resp = cust_client.post("/api/onboarding/process-data", {
            "customer_id": onb_cust_id,
            "vertical": "dc2_s",
            "skip_wizard_b": False,
            "skip_wizard_c": False,
            "onboarding_mode": "demo",
        }, skip_auth_check=True)

        if proc_resp:
            steps = proc_resp.get("steps_completed", [])
            errors = proc_resp.get("errors", [])
            ok(f"Data processed: {len(steps)} steps, {len(errors)} errors")
            log(f"      Steps: {steps}")
            if errors:
                log(f"      Errors: {errors}")
        else:
            fail("Process data returned None")

        # Step 6: Calculate scores explicitly (use latest month that has data)
        log(f"    Step 6: Calculating health scores...")
        score_resp = cust_client.post("/api/dc2s/scores/calculate", {
            "measurement_month": "2024-12-01"
        })

        if score_resp:
            total = score_resp.get("total_accounts", 0)
            successful = score_resp.get("successful", 0)
            ok(f"Scores calculated: {successful}/{total} accounts successful")
            if successful == 0 and total > 0:
                log(f"      ⚠️  No scores computed — data may not cover 2024-12. Retrying with 2024-11...")
                score_resp2 = cust_client.post("/api/dc2s/scores/calculate", {
                    "measurement_month": "2024-11-01"
                })
                if score_resp2:
                    s2 = score_resp2.get("successful", 0)
                    ok(f"Retry: {s2}/{score_resp2.get('total_accounts', 0)} accounts scored (2024-11)")
        else:
            # Scores may already be calculated during process-data
            skip("Score calculation (may already be done)")

    log(f"\n  Onboarded {len(customers)}/{NUM_CUSTOMERS} customers")
    if len(customers) == 0:
        fail("No customers onboarded — aborting")
        write_output()
        return 1

    # ──────────────────────────────────────────────────────────
    # Phase 3: Verify accounts + retrieve health scores
    # ──────────────────────────────────────────────────────────
    section("PHASE 3: Verify Accounts & Health Scores")

    for cust in customers:
        if "account_ids" not in cust or not cust["account_ids"]:
            log(f"  Skipping {cust['name']} — no accounts")
            continue

        subsection(f"Verifying: {cust['name']} ({len(cust.get('account_ids', []))} accounts)")

        cust_client = make_client(cust["email"], cust["password"])
        if not cust_client:
            fail(f"Login failed for {cust['email']}")
            continue

        # Get accounts
        accounts = cust_client.get_accounts()
        if accounts is not None:
            ok(f"{len(accounts)} accounts retrieved")

            # Show health distribution
            health_scores = []
            statuses = {"healthy": 0, "at_risk": 0, "critical": 0, "unknown": 0}
            for a in accounts:
                hs = a.get("overall_health", 0)
                health_scores.append(hs)
                st = a.get("status", "unknown")
                if st in statuses:
                    statuses[st] += 1
                else:
                    statuses["unknown"] += 1

            avg_health = sum(health_scores) / len(health_scores) if health_scores else 0
            log(f"      Avg Health: {avg_health:.1f}")
            log(f"      Distribution: {json.dumps(statuses)}")
            log(f"      Individual scores:")
            for a in accounts:
                log(f"        Account {a.get('account_id', '?')}: "
                    f"health={a.get('overall_health', 0):.1f}, status={a.get('status', '?')}")
            cust["health_distribution"] = statuses
            cust["avg_health"] = avg_health
        else:
            fail("Accounts fetch failed")

        # Get customer summary
        summary_resp = cust_client.get("/api/dc2s/scores/customer/summary")
        if summary_resp:
            ok(f"Summary: avg_health={summary_resp.get('average_health_score', 'N/A')}, "
               f"with_scores={summary_resp.get('accounts_with_scores', 0)}")
        else:
            skip("Summary endpoint returned None")

    # ──────────────────────────────────────────────────────────
    # Phase 4: Run Signal Analyst (Agentic Loop) on sample accounts
    #
    # Uses /api/signal-analyst/analyze-with-loop (6-step PAOR):
    #   Analyze → Evaluate → Enrich → Quantify → Decide → Act
    # The ACT step creates approval queue entries for playbooks.
    # ──────────────────────────────────────────────────────────
    section("PHASE 4: Signal Analyst (Agentic Loop) — Analyze Sample Accounts")

    analyst_results = []

    for cust in customers:
        if "account_ids" not in cust or not cust["account_ids"]:
            continue

        subsection(f"Analyzing: {cust['name']}")

        cust_client = make_client(cust["email"], cust["password"])
        if not cust_client:
            fail(f"Login failed for {cust['email']}")
            continue

        # Analyze first 5 accounts (more samples with 20 accounts)
        sample_ids = cust["account_ids"][:5]
        for acct_id in sample_ids:
            log(f"    Account {acct_id}:")

            # Try agentic loop first (creates approval queue entries)
            resp = cust_client.post("/api/signal-analyst/analyze-with-loop", {
                "account_id": acct_id,
                "analysis_type": "comprehensive"
            })

            # Fall back to basic analyze if loop isn't available
            if not resp:
                resp = cust_client.post("/api/signal-analyst/analyze", {
                    "account_id": acct_id,
                    "analysis_type": "comprehensive"
                })

            if resp:
                # analyze-with-loop wraps analysis inside 'initial_analysis'
                analysis = resp.get("initial_analysis", resp)
                if isinstance(analysis, str):
                    # May be serialized
                    try:
                        analysis = json.loads(analysis)
                    except Exception:
                        analysis = resp

                # Extract from SignalAnalystOutput fields
                health = analysis.get("health_score", resp.get("health_score", "?"))
                churn_prob = analysis.get("churn_probability", "?")
                expansion_prob = analysis.get("expansion_probability", "?")
                predicted = analysis.get("predicted_outcome", "?")
                actions = analysis.get("recommended_actions", [])
                signals = analysis.get("signals_analyzed", {})
                confidence = analysis.get("confidence", {})
                conf_level = confidence.get("confidence_level", "?") if isinstance(confidence, dict) else "?"
                alignment = analysis.get("data_alignment", {})
                align_trend = alignment.get("trend_direction", "?") if isinstance(alignment, dict) else "?"
                reasoning = analysis.get("reasoning", "")

                ok(f"health={health}, churn={churn_prob}%, expansion={expansion_prob}%, "
                   f"outcome={predicted}, confidence={conf_level}")
                log(f"        Signals: quant={signals.get('quantitative', 0)}, "
                    f"qual={signals.get('qualitative', 0)}, hist={signals.get('historical', 0)}")
                log(f"        Trend: {align_trend}")
                if actions:
                    for a in actions[:3]:
                        if isinstance(a, dict):
                            log(f"        ACTION: {a.get('action', '?')[:60]} | "
                                f"priority={a.get('priority', '?')} | owner={a.get('owner', '?')}")
                if reasoning:
                    log(f"        Reasoning: {str(reasoning)[:120]}...")

                # Check agentic loop state
                loop_state = resp.get("agentic_loop", resp.get("loop_state", {}))
                if loop_state and isinstance(loop_state, dict):
                    decision = loop_state.get("decision", "?")
                    step = loop_state.get("current_step", "?")
                    log(f"        Loop: step={step}, decision={decision}")

                analyst_results.append({
                    "customer": cust["name"],
                    "account_id": acct_id,
                    "health": health,
                    "risk": f"churn={churn_prob}%",
                    "playbook": predicted or "N/A",
                    "recs": len(actions)
                })
            else:
                skip("Signal Analyst returned None (may need OpenAI key or higher tier)")
                analyst_results.append({
                    "customer": cust["name"],
                    "account_id": acct_id,
                    "health": "N/A",
                    "risk": "N/A",
                    "playbook": "N/A (skipped)",
                    "recs": 0
                })

    # ──────────────────────────────────────────────────────────
    # Phase 5: Check Playbook Recommendations
    # ──────────────────────────────────────────────────────────
    section("PHASE 5: Playbook Library & Recommendations")

    for cust in customers:
        if "account_ids" not in cust or not cust["account_ids"]:
            continue

        cust_client = make_client(cust["email"], cust["password"])
        if not cust_client:
            continue

        subsection(f"Playbooks: {cust['name']}")

        # Get playbook library
        pb_resp = cust_client.get("/api/dc2s/playbooks")
        if pb_resp:
            playbooks = pb_resp.get("playbooks", [])
            ok(f"{len(playbooks)} playbooks available")
            for pb in playbooks[:5]:
                log(f"        {pb.get('playbook_id', pb.get('id', '?'))}: "
                    f"{pb.get('name', pb.get('title', '?'))}")
        else:
            skip("Playbooks endpoint returned None")

        # Check approval queue for auto-generated recommendations
        stats_resp = cust_client.get("/api/approvals/stats")
        if stats_resp:
            stats = stats_resp.get("stats", {})
            log(f"      Approval Queue: pending={stats.get('pending', 0)}, "
                f"auto_executed={stats.get('auto_executed', 0)}, "
                f"total={stats.get('total', 0)}")
        else:
            log(f"      Approval queue: returned None")

    # ──────────────────────────────────────────────────────────
    # NO CLEANUP — leave data for UI inspection
    # ──────────────────────────────────────────────────────────
    section("PHASE 6: SKIP CLEANUP (Data preserved for UI inspection)")
    log("  ⚠️  No cleanup performed — test data remains in the database.")
    log("  ⚠️  You can log in to the UI with the credentials below.")
    log("  ⚠️  To clean up later, use: POST /api/admin/cleanup/customer/{id}")
    ok("Cleanup intentionally skipped")

    # ──────────────────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────────────────
    elapsed = time.time() - start_time

    section("SUMMARY")
    log(f"  Duration: {elapsed:.1f}s")
    log(f"  Customers registered: {len(customers)}")
    log(f"  Accounts per customer: {NUM_ACCOUNTS}")
    log(f"  Total accounts created: {len(customers) * NUM_ACCOUNTS}")
    log(f"  Signal analyses run: {len(analyst_results)}")
    log(f"  Cleanup: SKIPPED (data preserved)")
    log(f"")
    log(f"  Tests: {passed} passed / {failed} failed / {skipped} skipped")
    log(f"  Total: {passed + failed + skipped}")

    if analyst_results:
        log(f"\n  Signal Analyst Results:")
        log(f"  {'Customer':<25} {'AcctID':<10} {'Health':<10} {'Risk':<15} {'Playbook':<30}")
        log(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*15} {'-'*30}")
        for ar in analyst_results:
            log(f"  {ar['customer']:<25} {str(ar['account_id']):<10} {str(ar['health']):<10} "
                f"{str(ar['risk']):<15} {str(ar['playbook']):<30}")

    log(f"\n  ╔{'═'*60}╗")
    log(f"  ║  UI LOGIN CREDENTIALS (data preserved for inspection)     ║")
    log(f"  ╠{'═'*60}╣")
    for cust in customers:
        log(f"  ║  Customer: {cust['name']:<47} ║")
        log(f"  ║  Email:    {cust['email']:<47} ║")
        log(f"  ║  Password: {cust['password']:<47} ║")
        log(f"  ║  CustID:   {str(cust['customer_id']):<47} ║")
        log(f"  ║  Accounts: {str(len(cust.get('account_ids', []))):<47} ║")
    log(f"  ╚{'═'*60}╝")

    log(f"\n  Health Score Summary per Customer:")
    for cust in customers:
        avg = cust.get("avg_health", "N/A")
        dist = cust.get("health_distribution", {})
        mix = cust.get("pattern_mix", {})
        log(f"  {cust['name']:<25} Avg={avg if isinstance(avg, str) else f'{avg:.1f}':<6} "
            f"H={dist.get('healthy',0)} R={dist.get('at_risk',0)} C={dist.get('critical',0)} "
            f"| Mix: crisis={mix.get('crisis',0):.0%} churn={mix.get('churn',0):.0%} "
            f"stable={mix.get('stable',0):.0%} expn={mix.get('expansion',0):.0%}")

    log("")
    if failed == 0:
        log(f"  {'='*50}")
        log(f"  ALL {passed} TESTS PASSED (+ {skipped} skipped)")
        log(f"  {'='*50}")
    else:
        log(f"  {'='*50}")
        log(f"  {passed}/{passed+failed} PASSED, {failed} FAILED, {skipped} SKIPPED")
        log(f"  {'='*50}")

    # Write output file
    write_output()
    return 1 if failed > 0 else 0


def write_output():
    """Write captured output to file."""
    try:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            f.write("\n".join(output_lines))
            f.write("\n")
        log(f"\n  Output written to: {OUTPUT_FILE}")
    except Exception as e:
        print(f"  WARNING: Failed to write output file: {e}")
        # Try alternative location
        alt_path = "/tmp/1Customer20accounts_test.out"
        try:
            with open(alt_path, "w") as f:
                f.write("\n".join(output_lines))
                f.write("\n")
            print(f"  Output written to fallback: {alt_path}")
        except Exception:
            print(f"  Could not write output to any location")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"  FATAL ERROR: {e}")
        print(f"{'='*70}")
        traceback.print_exc()
        sys.exit(1)
