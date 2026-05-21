#!/usr/bin/env python3
"""Post-deploy HTTP acceptance for executive dashboards (env-driven).

Runs user-perspective checks against a live CS Pulse host (local, EC2, or CloudFront).

Environment (see scripts/.env.acceptance.example):
  CS_PULSE_BASE_URL, CS_PULSE_EMAIL, CS_PULSE_PASSWORD, ACCEPTANCE_CUSTOMER_ID

Usage:
  python3 scripts/verify_executive_phases_ec2.py --suite all
  python3 scripts/verify_executive_phases_ec2.py --suite cfo,cro,vpcs
  python3 scripts/verify_executive_phases_ec2.py --suite cfo-phase1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python3 scripts/verify_executive_phases_ec2.py` from repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.ec2_acceptance.config import load_config
from scripts.ec2_acceptance.http_client import AcceptanceClient
from scripts.ec2_acceptance import checks


SUITES = {
    "cfo": ("CFO Phases 0–5", checks.verify_cfo_phases),
    "cfo-phase1": ("CFO Phase 0–2", checks.verify_cfo_phase1),
    "cro": ("CRO Phases 0–5", checks.verify_cro_phases),
    "vpcs": ("VPCS Phases 0–5", checks.verify_vpcs_phases),
}


def _run_suite(name: str, fn, client: AcceptanceClient) -> bool:
    print(f"\n{'=' * 60}")
    print(f"  {SUITES[name][0]}")
    print(f"  base={client.config.base_url_normalized} customer={client.config.customer_id}")
    print("=" * 60)
    ok = fn(client)
    print("\n" + ("PASS" if ok else "FAIL"))
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Executive dashboard acceptance (HTTP)")
    ap.add_argument(
        "--suite",
        default="all",
        help="Comma-separated: cfo,cfo-phase1,cro,vpcs,all (default: all)",
    )
    args = ap.parse_args()

    requested = [s.strip() for s in args.suite.split(",")]
    if "all" in requested:
        names = list(SUITES.keys())
    else:
        unknown = [s for s in requested if s not in SUITES]
        if unknown:
            print(f"Unknown suite(s): {unknown}. Choose from: {', '.join(SUITES)}")
            return 2
        names = requested

    cfg = load_config()
    print(
        f"Acceptance target: {cfg.base_url_normalized} "
        f"customer_id={cfg.customer_id} email={cfg.email}"
    )

    client = AcceptanceClient(cfg)
    if not client.login():
        return 1

    all_ok = True
    for name in names:
        if not _run_suite(name, SUITES[name][1], client):
            all_ok = False

    print(f"\n{'=' * 60}")
    print("OVERALL:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
