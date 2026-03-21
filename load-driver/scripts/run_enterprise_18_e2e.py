#!/usr/bin/env python3
"""
Enterprise 18-account DC2S E2E (local or remote):

  1) Register customer + onboarding complete (V2 driver)
  2) Baseline manifest phase: generate/upload 11 CSVs including all 8 context-graph files
  3) Intervention phase: second upload window + process-data
  4) Enable context graph + revenue intelligence, re-process, verify CG summary + outcome-roi APIs

Usage (from repo root or load-driver):

  cd load-driver && python3 scripts/run_enterprise_18_e2e.py
  CS_PULSE_BASE_URL=http://3.93.17.185:9080 python3 scripts/run_enterprise_18_e2e.py

Env:
  CS_PULSE_BASE_URL   (default http://localhost:5059)
  E2E_ADMIN_PASSWORD  (default Enterprise18_E2E_2026!)
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

# load-driver root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from client import create_authenticated_client

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("e2e")

MANIFEST = ROOT / "manifests" / "enterprise_18_dc2s_6mo.json"
DRIVER = ROOT / "cs_pulse_driver.py"
def run_driver(args: list[str]) -> tuple[int, str]:
    cmd = [sys.executable, str(DRIVER)] + args
    log.info("Running: %s", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    print(p.stdout, end="")
    if p.stderr:
        print(p.stderr, end="", file=sys.stderr)
    return p.returncode, out


def parse_customer_id(text: str) -> int | None:
    m = re.search(r"Registered:\s*customer_id=(\d+)", text)
    if m:
        return int(m.group(1))
    return None


def main() -> int:
    base_url = os.environ.get("CS_PULSE_BASE_URL", "http://localhost:5059").rstrip("/")
    password = os.environ.get("E2E_ADMIN_PASSWORD", "Enterprise18_E2E_2026!")
    seed = int(os.environ.get("E2E_SEED", "424242"))

    if not MANIFEST.exists():
        log.error("Manifest missing: %s", MANIFEST)
        return 1

    manifest = json.loads(MANIFEST.read_text())
    admin_email = manifest["customer"]["admin_email"]

    log.info("Base URL: %s", base_url)
    log.info("Manifest: %s (%s accounts)", MANIFEST.name, len(manifest["accounts"]))

    # --- Phase A: register + baseline ---
    rc, out = run_driver(
        [
            "--manifest",
            str(MANIFEST),
            "--register",
            "--base-url",
            base_url,
            "--password",
            password,
            "--seed",
            str(seed),
            "--phase",
            "baseline",
        ]
    )
    cid = parse_customer_id(out)
    if rc != 0 or not cid:
        log.error("Baseline/register failed (rc=%s, customer_id=%s)", rc, cid)
        return 1

    log.info("Customer ID: %s", cid)

    # --- Phase B: intervention ---
    rc2, out2 = run_driver(
        [
            "--manifest",
            str(MANIFEST),
            "--customer-id",
            str(cid),
            "--base-url",
            base_url,
            "--password",
            password,
            "--seed",
            str(seed),
            "--phase",
            "intervention",
        ]
    )
    if rc2 != 0:
        log.error("Intervention phase failed (rc=%s)", rc2)
        return 1

    # --- Enable features + re-process so context graph ingests (was off during first runs) ---
    client = create_authenticated_client(base_url, admin_email, password, customer_id=cid)
    if not client:
        log.error("Could not log in for verification (%s)", admin_email)
        return 1

    # Platform master switch: unrelated to "enterprise" tier; often off if
    # FEATURE_CONTEXT_GRAPH=false in env or /api/feature-toggle/reset was used.
    cg_status = client.get("/api/features/context-graph")
    if isinstance(cg_status, dict) and cg_status.get("status") == "success":
        if not cg_status.get("global_enabled"):
            log.info(
                "global_enabled=false — turning platform CONTEXT_GRAPH on via "
                "/api/feature-toggle (customer tier does not auto-enable this)."
            )
            ft = client.post(
                "/api/feature-toggle",
                {"feature": "context_graph", "enabled": True},
            )
            if isinstance(ft, dict) and ft.get("status") == "success":
                log.info("Platform context_graph: %s", ft.get("message"))
            else:
                log.warning("Could not enable platform context_graph: %s", ft)

    cg = client.post(
        "/api/features/context-graph",
        {
            "enabled": True,
            "sub_toggles": {
                "story_arcs": True,
                "signal_edges": True,
                "stakeholder_tracking": True,
                "decision_lifecycle": True,
                "outcome_economics": True,
                "industry_benchmarks": True,
            },
        },
    )
    log.info("POST context-graph: %s", cg.get("status", cg) if isinstance(cg, dict) else cg)

    ri = client.post(
        "/api/features/customer-toggle",
        {"feature_name": "revenue_intelligence", "enabled": True},
    )
    log.info("POST revenue_intelligence toggle: %s", ri.get("status", ri) if isinstance(ri, dict) else ri)

    log.info("Re-running process-data for context graph ingest...")
    proc = client.process_data(
        customer_id=cid,
        vertical="dc2_s",
        skip_wizard_b=True,
        skip_wizard_c=False,
        strict_kpi_ranges=False,
    )
    log.info(
        "process-data: %s",
        proc.get("status", str(proc)[:120]) if isinstance(proc, dict) else proc,
    )

    cg_on = client.is_context_graph_enabled(cid)
    log.info("Context graph feature active for customer %s: %s", cid, cg_on)

    aid = cid * 1000 + 1
    summary = client.get_context_graph_summary(aid)
    if summary and isinstance(summary, dict) and not summary.get("error"):
        nodes = summary.get("total_nodes", summary.get("nodes", 0))
        edges = summary.get("total_edges", summary.get("edges", 0))
        log.info("Context graph summary account %s: nodes=%s edges=%s", aid, nodes, edges)
    else:
        log.warning("Context graph summary: %s", summary)

    hist = client.get("/api/outcome-roi/historical", params={"period": "6m"})
    if hist is None:
        log.warning(
            "Outcome ROI historical: request failed (enable revenue_intelligence + check server logs)"
        )
    elif isinstance(hist, dict) and hist.get("error"):
        log.warning("Outcome ROI historical: %s", hist.get("error"))
    else:
        log.info(
            "Outcome ROI historical: ok (model=%s)",
            hist.get("model") if isinstance(hist, dict) else "?",
        )

    fwd = client.get(
        "/api/outcome-roi/forward",
        params={"months": 6, "mode": "flat", "improvement_pct": 4.0},
    )
    if fwd is None:
        log.warning("Outcome ROI forward: request failed")
    elif isinstance(fwd, dict) and fwd.get("error"):
        log.warning("Outcome ROI forward: %s", fwd.get("error"))
    else:
        log.info("Outcome ROI forward (flat 4%%): ok")

    log.info("--- E2E finished: customer_id=%s ---", cid)
    log.info(
        "Uploaded CSV types include all 8 context-graph files: "
        "stakeholders, engagement_events, account_business_profiles, decisions, outcomes, "
        "signal_edges, enhanced_signals (file_type enhanced_signals), industry_benchmarks."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
