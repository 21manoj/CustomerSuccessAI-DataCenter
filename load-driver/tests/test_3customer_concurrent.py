#!/usr/bin/env python3
"""
================================================================
3-Customer Concurrent Load Test
================================================================
Runs 3 customer types concurrently with incremental KPI injection,
score updates, playbook execution, and ROI validation.

Customer Profiles:
  C1 — "MidScale Compute"    : 3 pillars (P3,P2,P5), 12 KPIs, 5 accounts
  C2 — "FullStack DataCore"  : 5 pillars,             15 KPIs, 10 accounts  + playbooks + ROI
  C3 — "Enterprise CloudMax" : 5 pillars,             38 KPIs, 20 accounts  (full catalog)

Incremental Cadence:
  - KPI data injected every 60 s  (1 minute = 1 simulated day)
  - Scores recalculated every 30 days (= 30 minutes wall-clock)
  - Each run simulates 90 days (= 90 minutes wall-clock)
  - Drift profiles are coherent with demo manifest (stable/expansion/churn/crisis)

Usage:
  python tests/test_3customer_concurrent.py [--days 90] [--interval 60] [--base-url http://localhost:5059]

Output: load-driver/tests/test_3customer_concurrent.out
================================================================
"""

import os
import sys
import json
import time
import math
import random
import logging
import argparse
import traceback
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add load-driver root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client import CSPulseClient
from catalog_loader import get_kpis, get_pillar_code_map, get_kpi_list_for_load_driver, get_kpi_target

import requests as raw_requests

# ──────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)-18s] %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "test_3customer_concurrent.out")

# ──────────────────────────────────────────────────────────────
# CUSTOMER PROFILES
# ──────────────────────────────────────────────────────────────

# Pillar code map: P1=DV, P2=OS, P3=AI, P4=CH, P5=EX
PILLAR_CODE_MAP = get_pillar_code_map()   # {P1: DV, P2: OS, ...}
REVERSE_PILLAR  = {v: k for k, v in PILLAR_CODE_MAP.items()}  # {DV: P1, OS: P2, ...}
FULL_KPI_CATALOG = get_kpis()             # {P1-KPI1: {...}, ...}
ALL_DRIVER_KPIS  = get_kpi_list_for_load_driver()  # [{code: AI-KPI1, ...}]

PROFILES = {
    "C1": {
        "company_name": "MidScale Compute",
        "email": "admin@midscale-compute.test",
        "password": "MidScale_2026!",
        "num_accounts": 5,
        "pillar_weights": {"P3": 0.36, "P2": 0.28, "P5": 0.36},   # 3 pillars
        "enabled_kpis": [
            # P3 (AI) pillar — 5 KPIs (top weights)
            "P3-KPI1", "P3-KPI2", "P3-KPI3", "P3-KPI4", "P3-KPI5",
            # P2 (OS) pillar — 4 KPIs
            "P2-KPI1", "P2-KPI2", "P2-KPI3", "P2-KPI4",
            # P5 (EX) pillar — 3 KPIs
            "P5-KPI1", "P5-KPI2", "P5-KPI3",
        ],
        "pattern_mix": {"stable": 0.40, "expansion": 0.20, "churn": 0.20, "crisis": 0.20},
        "run_playbooks": False,
        "run_roi": False,
    },
    "C2": {
        "company_name": "FullStack DataCore",
        "email": "admin@fullstack-datacore.test",
        "password": "FullStack_2026!",
        "num_accounts": 10,
        "pillar_weights": {"P3": 0.25, "P4": 0.15, "P1": 0.15, "P5": 0.25, "P2": 0.20},  # all 5
        "enabled_kpis": [
            # 3 KPIs per pillar = 15 total (top-weighted from each)
            "P1-KPI1", "P1-KPI2", "P1-KPI3",
            "P2-KPI1", "P2-KPI2", "P2-KPI3",
            "P3-KPI1", "P3-KPI2", "P3-KPI3",
            "P4-KPI1", "P4-KPI2", "P4-KPI3",
            "P5-KPI1", "P5-KPI2", "P5-KPI3",
        ],
        "pattern_mix": {"stable": 0.30, "expansion": 0.20, "churn": 0.30, "crisis": 0.20},
        "run_playbooks": True,
        "run_roi": True,
    },
    "C3": {
        "company_name": "Enterprise CloudMax",
        "email": "admin@enterprise-cloudmax.test",
        "password": "CloudMax_2026!",
        "num_accounts": 20,
        "pillar_weights": {"P3": 0.25, "P4": 0.15, "P1": 0.15, "P5": 0.25, "P2": 0.20},  # all 5
        "enabled_kpis": [kpi["code"] for kpi in ALL_DRIVER_KPIS],  # all 38
        "pattern_mix": {"stable": 0.50, "expansion": 0.15, "churn": 0.15, "crisis": 0.10, "recovering": 0.10},
        "run_playbooks": False,
        "run_roi": False,
    },
}

# ──────────────────────────────────────────────────────────────
# DEMO-COHERENT DRIFT PROFILES
# ──────────────────────────────────────────────────────────────
# Maps showcase pattern names → KPI drift behaviour
# "stable"    → healthy drifts (small noise around baseline)
# "expansion" → improving KPIs (move toward/exceed target)
# "churn"     → declining KPIs (gradual degradation)
# "crisis"    → sharp drops then stabilisation
# "recovering"→ was low, improving steadily


class DemoCoherentMutator:
    """
    Generates KPI values that are coherent with the demo manifest pattern.
    Each account is assigned a pattern from the showcase_pattern_mix; subsequent
    daily data follows that pattern's drift profile.
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    # ── Assign showcase patterns to accounts ──────────────────
    def assign_patterns(self, num_accounts: int, mix: Dict[str, float]) -> Dict[int, str]:
        """Return {account_offset: pattern_name}"""
        patterns = list(mix.keys())
        weights  = list(mix.values())
        return {
            i: self.rng.choices(patterns, weights=weights, k=1)[0]
            for i in range(num_accounts)
        }

    # ── Generate one day of KPI data for one account ──────────
    def generate_day(
        self,
        account_id: int,
        kpi_codes: List[str],
        baselines: Dict[str, float],
        pattern: str,
        day_offset: int,
    ) -> List[Dict]:
        """
        Return list of KPI measurement rows for one simulated day.
        Values drift according to the pattern and day_offset.
        """
        rows = []
        for code in kpi_codes:
            baseline = baselines.get(code, 85.0)
            target   = get_kpi_target(code)
            value    = self._drift(baseline, target, day_offset, pattern, code)

            pillar_short = code.split("-")[0]  # P1, P2, P3, P4, P5
            p_code = REVERSE_PILLAR.get(pillar_short, pillar_short)

            # Determine status for the CSV
            if target and target > 0:
                ratio = value / target
                if ratio >= 0.95:
                    status = "healthy"
                elif ratio >= 0.75:
                    status = "risk"
                else:
                    status = "critical"
            else:
                status = "healthy"

            rows.append({
                "account_id": account_id,
                "kpi_code": code,
                "value": round(value, 2),
                "target": target,
                "pillar": pillar_short,
                "status": status,
            })
        return rows

    # ── Internal drift function ───────────────────────────────
    def _drift(self, baseline: float, target: float, day: int, pattern: str, kpi_code: str) -> float:
        noise = self.rng.gauss(0, 1.5)

        # Look up whether higher is better for this KPI
        hib = True
        for kpi in ALL_DRIVER_KPIS:
            if kpi["code"] == kpi_code:
                hib = kpi.get("higher_is_better", True)
                break

        if pattern == "stable":
            # Small daily noise, very slight improvement
            drift = day * 0.05 + noise
            v = baseline + drift if hib else baseline - drift
        elif pattern == "expansion":
            # Steady improvement toward target
            daily_step = (target - baseline) * 0.008 if hib else (baseline - target) * 0.008
            drift = day * abs(daily_step) + noise
            v = baseline + drift if hib else baseline - drift
        elif pattern == "churn":
            # Gradual degradation
            drift = -day * 0.4 + noise
            v = baseline + drift if hib else baseline - drift
        elif pattern == "crisis":
            # Sharp drop first 15 days, then stabilise
            if day <= 15:
                drift = -day * 1.2 + noise
            else:
                drift = -18.0 + noise * 0.5
            v = baseline + drift if hib else baseline - drift
        elif pattern == "recovering":
            # Start 15% below baseline, then improve
            low_start = baseline - 15.0 if hib else baseline + 15.0
            drift = day * 0.5 + noise
            v = low_start + drift if hib else low_start - drift
        else:
            v = baseline + noise

        return max(0.0, min(100.0 if hib else max(target * 4, 100), v))


# ──────────────────────────────────────────────────────────────
# CUSTOMER RUNNER (executed per-thread)
# ──────────────────────────────────────────────────────────────

class CustomerRunner:
    """Manages the full lifecycle for one customer inside its own thread."""

    def __init__(
        self,
        profile_key: str,
        profile: Dict[str, Any],
        base_url: str,
        total_days: int,
        interval_s: int,
        score_every_n_days: int,
    ):
        self.key = profile_key
        self.profile = profile
        self.base_url = base_url
        self.total_days = total_days
        self.interval_s = interval_s
        self.score_every_n_days = score_every_n_days

        self.customer_id: Optional[int] = None
        self.client: Optional[CSPulseClient] = None
        self.accounts: List[Dict] = []
        self.baselines: Dict[int, Dict[str, float]] = {}   # {acct_id: {kpi: value}}
        self.account_patterns: Dict[int, str] = {}

        self.mutator = DemoCoherentMutator(seed=hash(profile_key) % 100000)
        self.results: Dict[str, Any] = {
            "profile_key": profile_key,
            "company_name": profile["company_name"],
            "status": "pending",
            "days_injected": 0,
            "score_calcs": 0,
            "playbooks_triggered": 0,
            "roi_results": {},
            "errors": [],
            "health_snapshots": [],
        }

    # ── PHASE 1: Onboard ──────────────────────────────────────
    def onboard(self) -> bool:
        p = self.profile
        tag = f"[{self.key}]"
        logger.info(f"{tag} Registering {p['company_name']}...")

        # Clean up previous run if exists
        try:
            check = raw_requests.post(f"{self.base_url}/api/login", json={
                "email": p["email"], "password": p["password"]
            }, timeout=15)
            if check.status_code == 200:
                old_cid = check.json().get("customer_id") or check.json().get("user", {}).get("customer_id")
                if old_cid:
                    logger.info(f"{tag} Cleaning up old customer {old_cid}")
                    # Use the test-runner cleanup endpoint (FK-safe cascade)
                    cleanup_resp = raw_requests.post(
                        f"{self.base_url}/api/test-runner/cleanup",
                        json={"customer_id": old_cid, "confirm": True},
                        timeout=120,
                    )
                    if cleanup_resp.status_code != 200:
                        # Fallback: admin cleanup
                        raw_requests.post(
                            f"{self.base_url}/api/admin/cleanup/customer/{old_cid}",
                            json={"dry_run": False, "confirm": True},
                            timeout=120,
                        )
                    time.sleep(2)
        except Exception as e:
            logger.warning(f"{tag} Cleanup warning: {e}")

        # Register (or reuse existing customer)
        reused = False
        reg = raw_requests.post(f"{self.base_url}/api/register", json={
            "company_name": p["company_name"],
            "admin_name": f"{p['company_name']} Admin",
            "email": p["email"],
            "password": p["password"],
            "vertical": "dc2_s",
        }, timeout=30)
        if reg.status_code in (200, 201):
            self.customer_id = reg.json().get("customer_id")
            logger.info(f"{tag} Registered customer_id={self.customer_id}")
        elif "already registered" in reg.text.lower():
            # Customer exists from a previous run — reuse by logging in
            logger.info(f"{tag} Customer already exists, reusing...")
            # Direct login to get customer_id from response
            login_resp = raw_requests.post(f"{self.base_url}/api/login", json={
                "email": p["email"],
                "password": p["password"],
            }, timeout=30)
            if login_resp.status_code != 200:
                self.results["errors"].append(f"Login failed for existing customer: {login_resp.text[:200]}")
                return False
            login_data = login_resp.json()
            self.customer_id = login_data.get("user", {}).get("customer_id")
            logger.info(f"{tag} Got customer_id={self.customer_id} from login")

            # Create authenticated client
            self.client = CSPulseClient(base_url=self.base_url, email=p["email"], password=p["password"])
            if not self.client.login():
                self.results["errors"].append("Client login failed for existing customer")
                return False
            # Get existing accounts
            accts = self.client.get_accounts()
            if accts:
                self.accounts = accts
                reused = True
                logger.info(f"{tag} Reused customer_id={self.customer_id} with {len(accts)} accounts")
            else:
                self.results["errors"].append("Could not fetch accounts for existing customer")
                return False
        else:
            self.results["errors"].append(f"Registration failed: {reg.text[:200]}")
            return False

        if not reused:
            # Onboard (only for newly registered customers)
            logger.info(f"{tag} Onboarding {p['num_accounts']} accounts...")
            onb = raw_requests.post(f"{self.base_url}/api/onboarding/complete", json={
                "customer_id": self.customer_id,
                "customer_name": p["company_name"],
                "email": p["email"],
                "vertical": "dc2_s",
                "num_accounts": p["num_accounts"],
                "onboarding_mode": "demo",
                "weights": p["pillar_weights"],
                "showcase_pattern_mix": p["pattern_mix"],
            }, timeout=300)

            if onb.status_code != 200:
                self.results["errors"].append(f"Onboarding failed: {onb.text[:200]}")
                return False

            onb_data = onb.json()
            if not (onb_data.get("success") or onb_data.get("status") == "success"):
                self.results["errors"].append(f"Onboarding incomplete: {str(onb_data)[:200]}")
                return False

            logger.info(f"{tag} Onboarded successfully")

            # Login
            self.client = CSPulseClient(base_url=self.base_url, email=p["email"], password=p["password"])
            if not self.client.login():
                self.results["errors"].append("Login failed after onboarding")
                return False
            logger.info(f"{tag} Logged in OK")

        # Update config: restrict KPIs and pillar weights via PUT /api/dc2s/config/
        config_payload = {
            "dc2s_pillar_weights": p["pillar_weights"],
            "dc2s_enabled_kpis": p["enabled_kpis"],
        }
        config_resp = self.client.put("/api/dc2s/config/", config_payload)
        if config_resp:
            logger.info(f"{tag} Config updated: {len(p['pillar_weights'])} pillars, {len(p['enabled_kpis'])} KPIs")
        else:
            logger.warning(f"{tag} Config update returned None (proceeding with defaults)")

        # Enable revenue intelligence feature toggle for ROI testing
        if p.get("run_roi"):
            logger.info(f"{tag} Enabling revenue_intelligence feature toggle...")
            feat_resp = self.client.post("/api/entitlements/features", {
                "feature_name": "revenue_intelligence",
                "enabled": True,
            })
            if feat_resp:
                logger.info(f"{tag} Feature toggle enabled")
            else:
                # Use docker exec to insert into DB (running inside Docker network)
                logger.warning(f"{tag} Feature toggle API not available; inserting via docker exec...")
                try:
                    import subprocess
                    sql = (
                        f"INSERT INTO feature_toggles (customer_id, feature_name, enabled) "
                        f"VALUES ({self.customer_id}, 'revenue_intelligence', true) "
                        f"ON CONFLICT (customer_id, feature_name) DO UPDATE SET enabled = true;"
                    )
                    result = subprocess.run(
                        ["docker", "exec", "cspulse-postgres", "psql", "-U", "cspulse", "-d", "cs_pulse", "-c", sql],
                        capture_output=True, text=True, timeout=10,
                    )
                    if "INSERT" in result.stdout:
                        logger.info(f"{tag} Feature toggle enabled via docker exec")
                    else:
                        logger.warning(f"{tag} Feature toggle insert: {result.stdout} {result.stderr}")
                except Exception as e:
                    logger.warning(f"{tag} Could not enable feature toggle: {e}")

        if not reused:
            # Process data (only for newly onboarded customers)
            logger.info(f"{tag} Processing data pipeline...")
            proc = self.client.post("/api/onboarding/process-data", {
                "customer_id": self.customer_id,
                "vertical": "dc2_s",
                "skip_wizard_b": True,
                "skip_wizard_c": True,
                "onboarding_mode": "demo",
            }, skip_auth_check=True)
            if proc:
                logger.info(f"{tag} Data processed: {proc.get('steps_completed', [])}")

            # Fetch accounts
            accts = self.client.get_accounts()
            if not accts:
                self.results["errors"].append("No accounts returned after onboarding")
                return False
            self.accounts = accts
            logger.info(f"{tag} Got {len(self.accounts)} accounts")
        else:
            logger.info(f"{tag} Reused existing {len(self.accounts)} accounts (skipping onboarding pipeline)")

        # Initial score calculation
        self.client.post("/api/dc2s/scores/calculate", {
            "measurement_month": "2024-12-01",
        })

        # Assign patterns (demo coherent)
        pat_map = self.mutator.assign_patterns(len(self.accounts), p["pattern_mix"])
        logger.info(f"{tag} Pattern assignments: { {self.accounts[i].get('account_name','?')[:20]: pat for i, pat in pat_map.items()} }")

        # Build baselines from catalog targets + noise
        for i, acc in enumerate(self.accounts):
            acct_id = acc.get("account_id")
            self.account_patterns[acct_id] = pat_map[i]
            bl = {}
            for code in p["enabled_kpis"]:
                target = get_kpi_target(code)
                # Baseline near target with some noise (pattern shapes the drift later)
                pat = pat_map[i]
                if pat == "crisis":
                    bl[code] = target * self.mutator.rng.uniform(0.70, 0.85)
                elif pat == "churn":
                    bl[code] = target * self.mutator.rng.uniform(0.80, 0.95)
                elif pat == "recovering":
                    bl[code] = target * self.mutator.rng.uniform(0.65, 0.78)
                elif pat == "expansion":
                    bl[code] = target * self.mutator.rng.uniform(0.90, 1.05)
                else:  # stable
                    bl[code] = target * self.mutator.rng.uniform(0.88, 1.02)
            self.baselines[acct_id] = bl

        self.results["status"] = "onboarded"
        self.results["num_accounts"] = len(self.accounts)
        self.results["kpis"] = len(p["enabled_kpis"])
        self.results["pillars"] = len(p["pillar_weights"])
        return True

    # ── PHASE 2: Incremental KPI Injection Loop ──────────────
    def run_incremental_loop(self):
        tag = f"[{self.key}]"
        p = self.profile
        start_date = datetime(2025, 1, 1)

        for day in range(1, self.total_days + 1):
            sim_date = start_date + timedelta(days=day)
            date_str = sim_date.strftime("%Y-%m-%d")
            logger.info(f"{tag} Day {day}/{self.total_days} ({date_str})")

            # Generate + inject KPI data for all accounts
            all_rows = []
            for acc in self.accounts:
                acct_id = acc.get("account_id")
                pattern = self.account_patterns.get(acct_id, "stable")
                rows = self.mutator.generate_day(
                    account_id=acct_id,
                    kpi_codes=p["enabled_kpis"],
                    baselines=self.baselines[acct_id],
                    pattern=pattern,
                    day_offset=day,
                )
                all_rows.extend(rows)

            # Inject via data-ingestion API
            # API expects { "source": "...", "records": [{account_id, kpi_code, measured_at, value, target, pillar}] }
            records = [
                {
                    "account_id": row["account_id"],
                    "kpi_code": row["kpi_code"],
                    "measured_at": date_str,
                    "value": row["value"],
                    "target": row.get("target"),
                    "pillar": row.get("pillar"),
                }
                for row in all_rows
            ]
            inject_resp = self.client.post("/api/data-ingestion/kpis", {
                "source": "load_driver",
                "records": records,
            })

            if inject_resp and inject_resp.get("status") not in ("error", None):
                inserted = inject_resp.get("inserted", 0)
                updated  = inject_resp.get("updated", 0)
                self.results["days_injected"] += 1
                if day <= 3 or day % 10 == 0:
                    logger.info(f"{tag}   Injected: {inserted} new, {updated} updated ({len(records)} records)")
            else:
                err_msg = str(inject_resp)[:120] if inject_resp else "No response"
                self.results["errors"].append(f"Day {day} inject failed: {err_msg}")
                if day <= 3:
                    logger.warning(f"{tag}   Inject failed: {err_msg}")

            # Recalculate scores every N days
            if day % self.score_every_n_days == 0:
                logger.info(f"{tag} Recalculating scores (day {day})...")
                score_resp = self.client.post("/api/dc2s/scores/calculate", {
                    "measurement_month": date_str,
                })
                if score_resp:
                    self.results["score_calcs"] += 1

                # Snapshot health
                snapshot = self._take_health_snapshot(date_str)
                if snapshot:
                    self.results["health_snapshots"].append(snapshot)
                    logger.info(
                        f"{tag}   Health snapshot: avg={snapshot['avg_health']:.1f} "
                        f"H={snapshot['healthy']} R={snapshot['at_risk']} C={snapshot['critical']}"
                    )

            # Wait interval
            if day < self.total_days:
                time.sleep(self.interval_s)

        self.results["status"] = "injection_complete"

    # ── PHASE 3: Playbook Execution (C2 only) ────────────────
    def run_playbooks(self):
        if not self.profile["run_playbooks"]:
            return
        tag = f"[{self.key}]"
        logger.info(f"{tag} Running playbook execution phase...")

        # Find at-risk and critical accounts
        at_risk = []
        healthy = []
        for acc in self.accounts:
            score = self.client.get_account_scores(acc.get("account_id"))
            if not score:
                continue
            health = score.get("health_score", {})
            overall = health.get("overall_health_score", 50) if isinstance(health, dict) else 50
            if overall < 60:
                at_risk.append((acc, overall))
            elif overall >= 80:
                healthy.append((acc, overall))

        logger.info(f"{tag}   At-risk: {len(at_risk)}, Healthy: {len(healthy)}")

        # Trigger at-risk playbooks for up to 3 at-risk accounts
        # Playbook IDs: PB-02 (RMA Prevention), PB-05 (Health Monitoring)
        # Use DC2S playbook endpoint: POST /api/dc2s/playbooks/executions
        pb_at_risk = ["PB-02", "PB-05", "PB-02"]  # cycle through for 3 accounts
        for idx, (acc, health) in enumerate(at_risk[:3]):
            acct_id = acc.get("account_id")
            acct_name = acc.get("account_name", "?")
            pb_id = pb_at_risk[idx]
            resp = self.client.post("/api/dc2s/playbooks/executions", {
                "playbook_id": pb_id,
                "account_id": acct_id,
                "context": {
                    "trigger": "load_test_signal",
                    "risk_level": "high" if health < 40 else "medium",
                    "health_score": health,
                },
            })
            if resp and resp.get("execution_id"):
                self.results["playbooks_triggered"] += 1
                exec_id = resp["execution_id"]
                logger.info(f"{tag}   Triggered {pb_id} for {acct_name} (exec={exec_id})")

                # Wait and check status
                time.sleep(2)
                status = self.client.get(f"/api/dc2s/playbooks/executions/{exec_id}")
                if status:
                    logger.info(f"{tag}     Status: {status.get('status', '?')}")
            else:
                logger.warning(f"{tag}   Playbook trigger failed for {acct_name}: {resp}")

        # Trigger expansion playbooks for up to 2 healthy accounts (PB-04 Capacity Planning)
        for acc, health in healthy[:2]:
            acct_id = acc.get("account_id")
            resp = self.client.post("/api/dc2s/playbooks/executions", {
                "playbook_id": "PB-04",
                "account_id": acct_id,
                "context": {
                    "trigger": "load_test_signal",
                    "health_score": health,
                    "expansion_signal": "high_adoption",
                },
            })
            if resp and resp.get("execution_id"):
                self.results["playbooks_triggered"] += 1
                logger.info(f"{tag}   Triggered expansion for {acc.get('account_name','?')}")

        self.results["status"] = "playbooks_complete"

    # ── PHASE 4: ROI Validation (C2 only) ─────────────────────
    def run_roi(self):
        if not self.profile["run_roi"]:
            return
        tag = f"[{self.key}]"
        logger.info(f"{tag} Running ROI validation...")

        roi_results = {}

        # Historical ROI
        hist = self.client.get("/api/outcome-roi/historical", params={
            "customer_id": self.customer_id,
        })
        roi_results["historical"] = {
            "available": hist is not None,
            "summary": str(hist)[:200] if hist else "N/A",
        }

        # Forward projections at 1%, 4%, 6%
        for pct in [1.0, 4.0, 6.0]:
            fwd = self.client.get("/api/outcome-roi/forward", params={
                "customer_id": self.customer_id,
                "improvement_pct": pct,
            })
            roi_results[f"forward_{int(pct)}pct"] = {
                "available": fwd is not None,
                "total_roi": self._extract_roi(fwd),
                "summary": str(fwd)[:200] if fwd else "N/A",
            }

        # ROI story
        story = self.client.get("/api/outcome-roi/story", params={
            "customer_id": self.customer_id,
        })
        roi_results["story"] = {
            "available": story is not None,
            "summary": str(story)[:300] if story else "N/A",
        }

        self.results["roi_results"] = roi_results
        self.results["status"] = "roi_complete"

        # Log summary
        for pct in [1, 4, 6]:
            roi_val = roi_results.get(f"forward_{pct}pct", {}).get("total_roi", "N/A")
            logger.info(f"{tag}   ROI at {pct}% improvement: {roi_val}")

    # ── Health snapshot helper ────────────────────────────────
    def _take_health_snapshot(self, date_str: str) -> Optional[Dict]:
        accts = self.client.get_accounts()
        if not accts:
            return None
        scores = []
        for acc in accts:
            health = acc.get("overall_health") or acc.get("health_score") or 0
            scores.append(float(health))
        nonzero = [s for s in scores if s > 0]
        if not nonzero:
            return None
        return {
            "date": date_str,
            "avg_health": sum(nonzero) / len(nonzero),
            "min": min(nonzero),
            "max": max(nonzero),
            "healthy": sum(1 for s in nonzero if s >= 70),
            "at_risk": sum(1 for s in nonzero if 50 <= s < 70),
            "critical": sum(1 for s in nonzero if s < 50),
        }

    def _extract_roi(self, resp) -> Optional[float]:
        if resp is None:
            return None
        if isinstance(resp, dict):
            for field in ["total_roi", "roi_value", "projected_roi", "total", "value"]:
                if field in resp:
                    try:
                        return float(resp[field])
                    except (TypeError, ValueError):
                        pass
        return None


# ──────────────────────────────────────────────────────────────
# THREAD FUNCTION
# ──────────────────────────────────────────────────────────────

def run_customer(runner: CustomerRunner):
    """Thread target: onboard → inject → playbooks → ROI"""
    tag = f"[{runner.key}]"
    try:
        # Phase 1: Onboard
        if not runner.onboard():
            runner.results["status"] = "onboard_failed"
            logger.error(f"{tag} Onboarding failed: {runner.results['errors']}")
            return

        # Phase 2: Incremental injection loop
        runner.run_incremental_loop()

        # Phase 3: Playbooks (C2 only)
        runner.run_playbooks()

        # Phase 4: ROI (C2 only)
        runner.run_roi()

        runner.results["status"] = "complete"
        logger.info(f"{tag} ✅ Customer run complete")

    except Exception as e:
        runner.results["status"] = "error"
        runner.results["errors"].append(f"Unhandled: {traceback.format_exc()}")
        logger.error(f"{tag} ❌ Error: {e}")


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="3-Customer Concurrent Load Test")
    parser.add_argument("--days", type=int, default=90, help="Simulated days (default: 90)")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between days (default: 60)")
    parser.add_argument("--score-every", type=int, default=30, help="Score recalc every N days (default: 30)")
    parser.add_argument("--base-url", type=str, default="http://localhost:5059", help="Backend URL")
    args = parser.parse_args()

    start_time = time.time()

    print("=" * 74)
    print("  3-CUSTOMER CONCURRENT LOAD TEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Backend:     {args.base_url}")
    print(f"  Days:        {args.days}  (wall-clock: ~{args.days * args.interval // 60} min)")
    print(f"  Interval:    {args.interval}s per day")
    print(f"  Score every: {args.score_every} days ({args.score_every * args.interval // 60} min)")
    print("=" * 74)

    # Health check
    try:
        health = raw_requests.get(f"{args.base_url}/api/health", timeout=10)
        if health.status_code != 200:
            print("❌ Platform health check failed")
            return 1
        print("✅ Platform healthy")
    except Exception as e:
        print(f"❌ Platform unreachable: {e}")
        return 1

    # Create runners
    runners = {}
    for key, profile in PROFILES.items():
        runners[key] = CustomerRunner(
            profile_key=key,
            profile=profile,
            base_url=args.base_url,
            total_days=args.days,
            interval_s=args.interval,
            score_every_n_days=args.score_every,
        )

    print(f"\n  Customer profiles:")
    for key, runner in runners.items():
        p = runner.profile
        print(f"    {key}: {p['company_name']}")
        print(f"         Pillars: {len(p['pillar_weights'])} ({', '.join(p['pillar_weights'].keys())})")
        print(f"         KPIs:    {len(p['enabled_kpis'])}")
        print(f"         Accounts:{p['num_accounts']}")
        print(f"         Playbooks: {'Yes' if p['run_playbooks'] else 'No'}")
        print(f"         ROI:      {'Yes' if p['run_roi'] else 'No'}")
        print(f"         Patterns: {p['pattern_mix']}")

    # Launch threads
    print(f"\n{'─'*74}")
    print("  Launching concurrent customer threads...")
    print(f"{'─'*74}\n")

    threads = {}
    for key, runner in runners.items():
        t = threading.Thread(
            target=run_customer,
            args=(runner,),
            name=f"Customer-{key}",
            daemon=True,
        )
        threads[key] = t
        t.start()
        time.sleep(2)  # Stagger starts slightly

    # Wait for all threads
    for key, t in threads.items():
        t.join()

    elapsed = time.time() - start_time

    # ──────────────────────────────────────────────────────
    # REPORT
    # ──────────────────────────────────────────────────────
    output_lines = []

    def out(msg=""):
        print(msg)
        output_lines.append(msg)

    out("\n" + "=" * 74)
    out("  FINAL REPORT")
    out("=" * 74)

    for key, runner in runners.items():
        r = runner.results
        p = runner.profile
        out(f"\n  {'─'*70}")
        out(f"  {key}: {p['company_name']}")
        out(f"  {'─'*70}")
        out(f"  Status:          {r['status']}")
        out(f"  Customer ID:     {runner.customer_id}")
        out(f"  Accounts:        {r.get('num_accounts', '?')}")
        out(f"  Pillars:         {r.get('pillars', '?')} ({', '.join(p['pillar_weights'].keys())})")
        out(f"  KPIs:            {r.get('kpis', '?')}")
        out(f"  Days injected:   {r['days_injected']}/{args.days}")
        out(f"  Score calcs:     {r['score_calcs']}")
        if r.get("playbooks_triggered"):
            out(f"  Playbooks:       {r['playbooks_triggered']}")
        if r.get("roi_results"):
            out(f"  ROI results:")
            for rkey, rval in r["roi_results"].items():
                out(f"    {rkey}: {'✅' if rval.get('available') else '❌'} {rval.get('total_roi', rval.get('summary', '')[:60])}")
        if r.get("errors"):
            out(f"  Errors ({len(r['errors'])}):")
            for err in r["errors"][:5]:
                out(f"    • {err[:100]}")

        # Health trend
        if r.get("health_snapshots"):
            out(f"\n  Health Trend ({len(r['health_snapshots'])} snapshots):")
            out(f"    {'Date':<12} {'Avg':>6} {'Min':>6} {'Max':>6} {'H':>3} {'R':>3} {'C':>3}")
            out(f"    {'─'*48}")
            for snap in r["health_snapshots"]:
                out(f"    {snap['date']:<12} {snap['avg_health']:>6.1f} {snap['min']:>6.1f} {snap['max']:>6.1f} {snap['healthy']:>3} {snap['at_risk']:>3} {snap['critical']:>3}")

    # Login credentials
    out(f"\n{'='*74}")
    out("  LOGIN CREDENTIALS")
    out(f"{'='*74}")
    out(f"  URL: http://localhost\n")
    for key, runner in runners.items():
        p = runner.profile
        out(f"  ┌──────────────────────────────────────────────────────┐")
        out(f"  │ {key}: {p['company_name']:<50}│")
        out(f"  ├──────────────────────────────────────────────────────┤")
        out(f"  │ Email:    {p['email']:<44}│")
        out(f"  │ Password: {p['password']:<44}│")
        out(f"  │ Cust ID:  {str(runner.customer_id or '?'):<44}│")
        out(f"  │ Accounts: {p['num_accounts']:<44}│")
        out(f"  │ Pillars:  {', '.join(p['pillar_weights'].keys()):<44}│")
        out(f"  │ KPIs:     {len(p['enabled_kpis']):<44}│")
        out(f"  └──────────────────────────────────────────────────────┘")

    out(f"\n  Total elapsed: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    all_ok = all(r.results["status"] == "complete" for r in runners.values())
    out(f"  Overall: {'✅ ALL COMPLETE' if all_ok else '⚠️  SOME ISSUES'}")

    # Write output file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(output_lines))
    out(f"\n  Output written to: {OUTPUT_FILE}")

    # Also write JSON results
    json_file = OUTPUT_FILE.replace(".out", ".json")
    with open(json_file, "w") as f:
        json.dump({
            key: runner.results for key, runner in runners.items()
        }, f, indent=2, default=str)
    out(f"  JSON results: {json_file}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        rc = main()
        sys.exit(rc)
    except Exception as e:
        print(f"\n❌ UNHANDLED ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
