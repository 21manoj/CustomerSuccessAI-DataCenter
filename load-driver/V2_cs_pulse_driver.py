#!/usr/bin/env python3
"""
V2 CS Pulse Driver.

Same behavior as cs_pulse_driver.py, but manifest mode uses ScenarioManifestV2
with post-process correctness assertions.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

_root = str(Path(__file__).resolve().parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from V2_client import CSPulseClientV2
from V2_scenario_manifest import ScenarioManifestV2
from scenarios.scenario_manifest import ManifestCSVGenerator

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("V2_cs_pulse_driver.log"), logging.StreamHandler()],
)
logger = logging.getLogger("V2_cs_pulse_driver")


def _phase_banner_label(phase: Optional[str]) -> str:
    """Human-readable segment name for the two-step mountain / V2 load."""
    if phase == "baseline":
        return (
            "Segment 1/2 — BASELINE: early time window (~first 2/3 of KPI points); "
            "declining narratives; customer register + onboard (if --register)."
        )
    if phase == "intervention":
        return (
            "Segment 2/2 — INTERVENTION & OUTCOMES: later window (~last 1/3 of points); "
            "recovery KPI trajectories + CSVs including outcomes, decisions, signals/signal_edges."
        )
    return f"Segment (single run): {phase or 'full manifest window'}"


def _fmt_money(val: Any) -> str:
    if val is None:
        return "-"
    try:
        return f"{float(val):,.0f}"
    except (TypeError, ValueError):
        return str(val)


def _log_context_graph_report(report: Optional[Dict[str, Any]]) -> None:
    """Log whether context graphs exist and a per-account table (node/edge/revenue summary)."""
    logger.info("")
    logger.info("  --- Context graphs (DB state after process-data) ---")
    if not report:
        logger.info("  (No context graph report attached to this run.)")
        logger.info("  --- end context graphs ---")
        return

    toggle = report.get("feature_toggle_on")
    ingest_step = report.get("context_graph_ingestion_step_ran")
    in_db = report.get("graphs_present_in_db")
    produced = report.get("context_graphs_produced")
    cg_proc = report.get("process_data_context_graph") or {}

    if toggle:
        logger.info(
            f"  Feature toggle: ON | process-data ran context_graph_ingestion step: {ingest_step} | "
            f"any nodes in DB (per /api/context-graph/summary): {in_db}"
        )
        if cg_proc:
            logger.info(f"  process-data payload.context_graph (if returned): {cg_proc}")
    else:
        logger.info(
            "  Feature toggle: OFF — context graph CSVs were not ingested into context_nodes/context_edges. "
            "Enable via POST /api/features/context-graph and upload context graph CSVs (or rely on server auto-gen) "
            "to produce graphs."
        )

    if produced:
        logger.info("  Verdict: context graph data IS present for at least one account (or ingest reported nodes).")
    elif not toggle:
        logger.info(
            "  Verdict: no context graph rows — customer feature toggle is OFF (or global platform context_graph off)."
        )
    else:
        logger.info(
            "  Verdict: toggles ON and process-data may have run context_graph_ingestion, but "
            "**0 context_nodes** in DB for these accounts. V2 manifest load uploads core onboarding CSVs only "
            "(not the 7 context_graph/*.csv types); add Scenario 8–style graph CSV uploads or extend the "
            "manifest pipeline to populate data/context_graph/ so ingest creates nodes/edges."
        )

    accounts: List[Dict[str, Any]] = list(report.get("accounts") or [])
    if not accounts:
        logger.info("  --- end context graphs ---")
        return

    type_order = (
        "ACCOUNT",
        "SIGNAL",
        "STAKEHOLDER",
        "DECISION",
        "OUTCOME",
        "EXTERNAL_CONTEXT",
    )
    seen: set = set()
    for row in accounts:
        seen.update((row.get("nodes_by_type") or {}).keys())
    ordered_nt = [k for k in type_order if k in seen]
    ordered_nt += sorted(seen - set(ordered_nt))

    sep = (
        "  "
        + "|".join(
            [
                f"{'account_id':>12}",
                f"{'nodes':>6}",
                f"{'edges':>6}",
                f"{'api':>7}",
            ]
            + [f"{k[:3]:>4}" for k in ordered_nt]
            + [
                f"{'at_risk$':>10}",
                f"{'protected$':>10}",
                f"{'expansion$':>10}",
                f"{'net$':>10}",
                f"{'note':<20}",
            ]
        )
    )
    logger.info("  Per-account context graph summary:")
    logger.info(sep)
    logger.info("  " + "-" * (len(sep) - 2))
    for row in sorted(accounts, key=lambda r: int(r.get("account_id") or 0)):
        aid = row.get("account_id")
        nbt = row.get("nodes_by_type") or {}
        nt_cols = [str(nbt.get(k, "") if nbt.get(k) is not None else "") for k in ordered_nt]
        line = (
            "  "
            + "|".join(
                [
                    f"{str(aid):>12}",
                    f"{str(row.get('total_nodes') if row.get('total_nodes') is not None else '-'):>6}",
                    f"{str(row.get('total_edges') if row.get('total_edges') is not None else '-'):>6}",
                    f"{str(row.get('api_status') or '-'):>7}",
                ]
                + [f"{(str(c) if c != '' else '-'):>4}" for c in nt_cols]
                + [
                    f"{_fmt_money(row.get('revenue_at_risk')):>10}",
                    f"{_fmt_money(row.get('revenue_protected')):>10}",
                    f"{_fmt_money(row.get('revenue_expansion')):>10}",
                    f"{_fmt_money(row.get('revenue_net_impact')):>10}",
                    f"{str(row.get('note') or '')[:20]:<20}",
                ]
            )
        )
        logger.info(line)
    logger.info(
        "  Column hints: 3-letter headers = first 3 chars of node types "
        f"({', '.join(ordered_nt)}). Full counts in nodes_by_type from API."
    )
    logger.info("  --- end context graphs ---")


def _log_business_outcome_from_details(details: dict) -> None:
    """Log health / KPI validation summary (the ingest + scoring outcome)."""
    if not details:
        return
    val = details.get("validation") or {}
    metrics = val.get("metrics") or {}
    if metrics:
        logger.info("")
        logger.info("  --- Business outcome (post-ingest validation) ---")
        phase = details.get("phase")
        if phase:
            logger.info(f"  {_phase_banner_label(phase)}")
        exp = details.get("expected") or {}
        if exp:
            logger.info(
                f"  Accounts in manifest: {exp.get('accounts')} | "
                f"KPIs per account (expected): {exp.get('kpi_count_per_account')}"
            )
        dist_a = metrics.get("sample_distribution_actual") or {}
        dist_e = metrics.get("sample_distribution_expected") or {}
        if dist_a or dist_e:
            logger.info(f"  Health mix (sample): actual {dist_a} | expected≈ {dist_e}")
        scores = metrics.get("sample_scores") or {}
        if scores:
            parts = []

            def _aid_key(item):
                try:
                    return int(item[0])
                except (TypeError, ValueError):
                    return 0

            for aid, row in sorted(scores.items(), key=_aid_key)[:8]:
                parts.append(
                    f"id {aid}: score={row.get('health_score')} {row.get('status')} "
                    f"(kpis={row.get('kpi_count')})"
                )
            more = len(scores) - 8
            logger.info(
                "  Sample account health scores: " + "; ".join(parts) + (f" … +{more} more" if more > 0 else "")
            )
        lat = metrics.get("validation_latency_summary_s")
        if lat:
            logger.info(f"  Validation API latency (s): min={lat.get('min')} max={lat.get('max')} avg={lat.get('avg')}")
        logger.info("  --- end business outcome ---")

    _log_context_graph_report(details.get("context_graph_report"))


def run_manifest(args):
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)
    customer_info = manifest["customer"]

    logger.info("=" * 60)
    logger.info("CS Pulse Driver V2 — Manifest Mode")
    logger.info("=" * 60)
    logger.info(f"  Manifest:  {manifest_path.name}")
    logger.info(f"  Customer:  {customer_info['name']}")
    logger.info(f"  Vertical:  {customer_info.get('vertical', 'dc2_s')}")
    logger.info(f"  Accounts:  {len(manifest['accounts'])}")
    logger.info(f"  KPIs:      {manifest['kpis']['count']}")
    if getattr(args, "phase", None):
        logger.info("")
        logger.info(f"  >>> {_phase_banner_label(args.phase)}")

    if args.generate_only:
        output_dir = args.generate_only
        logger.info(f"\n  Generate-only mode → {output_dir}")
        gen = ManifestCSVGenerator(
            manifest_path=str(manifest_path),
            customer_id=args.customer_id or 0,
            seed=args.seed,
        )
        files = gen.generate_all(output_dir)
        logger.info(f"\n  Generated {len(files)} files")
        return

    base_url = args.base_url
    email = args.email or os.getenv("CS_PULSE_ADMIN_EMAIL", "admin@sacme.com")
    password = args.password or os.getenv("CS_PULSE_ADMIN_PASSWORD", "test123")
    customer_id = args.customer_id

    if args.register:
        logger.info("\n  Registering new customer...")
        reg_client = CSPulseClientV2(base_url=base_url, timeout=30)
        resp = reg_client.register_customer(
            company_name=customer_info["name"],
            admin_name=customer_info.get("admin_name", "Admin"),
            email=customer_info.get("admin_email", email),
            password=password,
            vertical=customer_info.get("vertical", "dc2_s"),
        )
        if not (resp and resp.get("customer_id")):
            logger.error(f"  Registration failed: {resp}")
            sys.exit(1)
        customer_id = int(resp["customer_id"])
        logger.info(f"  Registered: customer_id={customer_id}")

        num_accounts = len(manifest.get("accounts", [])) or 3
        complete = reg_client.complete_onboarding(
            customer_id=customer_id,
            customer_name=customer_info["name"],
            vertical=customer_info.get("vertical", "dc2_s"),
            num_accounts=num_accounts,
            onboarding_mode="custom",
        )
        if not complete or not complete.get("success"):
            logger.error(f"  Onboarding complete failed: {complete}")
            sys.exit(1)

    if not customer_id:
        logger.error("--customer-id required (or use --register)")
        sys.exit(1)

    client = CSPulseClientV2(
        base_url=base_url,
        email=email,
        password=password,
        customer_id=int(customer_id),
        timeout=60,
    )
    if not client.health_check() or not client.login():
        logger.error("Server unavailable or login failed")
        sys.exit(1)

    if getattr(args, "enterprise_toggles", True) and not args.generate_only:
        logger.info("")
        logger.info("  Applying enterprise subscription tier + per-customer feature toggles...")
        ent = client.ensure_enterprise_all_toggles(int(customer_id))
        for step, ok in sorted((ent.get("steps") or {}).items()):
            logger.info("    %s: %s", step, "ok" if ok else "FAILED")
        if ent.get("errors"):
            for e in ent["errors"]:
                logger.warning("    toggle setup: %s", e)

    scenario_args = argparse.Namespace(
        manifest=str(manifest_path),
        customer_id=int(customer_id),
        seed=args.seed,
        phase=args.phase,
        validate_strict=args.validate_strict,
        validate_sample_size=args.validate_sample_size,
        health_tolerance=args.health_tolerance,
    )
    scenario = ScenarioManifestV2(client=client, args=scenario_args)
    result = scenario.run()

    logger.info("\n" + "=" * 60)
    logger.info(f"  Result: {result.get('status', 'unknown').upper()}")
    logger.info(f"  {result.get('message', '')}")
    if result.get("duration_seconds"):
        logger.info(f"  Duration: {result['duration_seconds']:.1f}s")
    # Technical noise (vertical YAML load) may appear on stderr; real outcome is here:
    _log_business_outcome_from_details(result.get("details") or {})
    if result.get("errors"):
        for err in result["errors"]:
            logger.warning(f"    - {err}")
    logger.info("=" * 60)

    if result.get("status") != "success":
        sys.exit(1)


def run_scenarios(args):
    from driver import LoadDriver

    scenario_ids = [s.strip() for s in args.scenarios.split(",")]
    customer_ids = [int(c.strip()) for c in args.customers.split(",")]
    driver = LoadDriver(base_url=args.base_url, results_dir=args.results_dir)
    driver.run_all(scenario_ids, customer_ids, args)


def main():
    parser = argparse.ArgumentParser(
        description="V2 CS Pulse Driver (manifest validations enabled)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--manifest", "-m")
    parser.add_argument("--generate-only", "-g", metavar="DIR")
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--scenarios")
    parser.add_argument("--customers", default="1")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--customer-id", "-c", type=int)
    parser.add_argument("--base-url", "-u", default=os.getenv("CS_PULSE_BASE_URL", "http://localhost:5059"))
    parser.add_argument("--email")
    parser.add_argument("--password")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verbose", "-v", action="store_true")

    # V2 validation knobs
    parser.add_argument("--validate-strict", dest="validate_strict", action="store_true", default=True)
    parser.add_argument("--no-validate-strict", dest="validate_strict", action="store_false")
    parser.add_argument("--validate-sample-size", type=int, default=5)
    parser.add_argument("--health-tolerance", type=int, default=1)
    parser.add_argument(
        "--phase",
        choices=["baseline", "intervention"],
        default=None,
        help="Manifest time window: baseline≈first 2/3 of KPI points, intervention≈last 1/3 + recovery KPI trajectories",
    )
    parser.add_argument(
        "--no-enterprise-toggles",
        dest="enterprise_toggles",
        action="store_false",
        default=True,
        help="Do not set subscription tier=enterprise or enable context graph / revenue / MCP toggles",
    )

    # passthrough args for legacy driver paths
    parser.add_argument("--arc-id", default="arc_expansion_champion")
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--improvement", type=float, default=2.5)
    parser.add_argument("--num-accounts", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.manifest:
        run_manifest(args)
    elif args.scenarios:
        run_scenarios(args)
    else:
        parser.print_help()
        print("\nError: specify --manifest or --scenarios")
        sys.exit(1)


if __name__ == "__main__":
    main()
