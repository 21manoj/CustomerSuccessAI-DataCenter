#!/usr/bin/env python3
"""
Need-to-know runtime explorer — run inside cspulse-platform on EC2.

No git clone required. Inspect pipeline code paths, tenant CSVs, DB exports,
and live API JSON from the running stack.

Usage (on EC2 host):
  sudo docker exec -e CUSTOMER_ID=336 cspulse-platform \\
    python3 /app/backend/scripts/runtime_explorer.py map

  sudo docker exec -e CUSTOMER_ID=336 cspulse-platform \\
    python3 /app/backend/scripts/runtime_explorer.py audit

  sudo docker exec -e CUSTOMER_ID=336 cspulse-platform \\
    python3 /app/backend/scripts/runtime_explorer.py csv-ls

  sudo docker exec -e CUSTOMER_ID=336 -e RUNTIME_EXPORT_DIR=/tmp/runtime_export cspulse-platform \\
    python3 /app/backend/scripts/runtime_explorer.py export-db --types signals,accounts

  sudo docker cp cspulse-platform:/tmp/runtime_export/336 ./cust336_export
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

CUSTOMER_ID = int(os.environ.get("CUSTOMER_ID", "336"))
LOAD_DRIVER = Path(os.environ.get("LOAD_DRIVER_DIR", "/app/load-driver"))

# Need-to-know allowlist — only these paths matter for dashboard lineage / pipelines.
NEED_TO_KNOW = [
    ("Manifest (336)", LOAD_DRIVER / "manifests/predictor_v3_demo_saas_cust336.json"),
    ("CSV generator", LOAD_DRIVER / "scenarios/scenario_manifest.py"),
    ("Load-driver CLI", LOAD_DRIVER / "cs_pulse_driver.py"),
    ("process_data stages", BACKEND / "mcp_server/process_data_pipeline.py"),
    ("Onboarding / MCP tools", BACKEND / "mcp_server/cs_pulse_onboarding.py"),
    ("Wizard A", BACKEND / "wizards/wizard_a_journey_db.py"),
    ("Wizard B (trailing NRR)", BACKEND / "wizards/wizard_b_pattern_db.py"),
    ("Wizard C (weights)", BACKEND / "wizards/wizard_c_weight_calibrator_db.py"),
    ("Wizard D (predictor cal)", BACKEND / "wizards/wizard_d_predictor_calibrator.py"),
    ("Health rollup", BACKEND / "utils/score_calculator.py"),
    ("Revenue @ risk", BACKEND / "utils/context_graph.py"),
    ("CRO/CFO API", BACKEND / "executive_dashboard_api.py"),
    ("Predictor inference", BACKEND / "predictor/inference.py"),
    ("Health thresholds", BACKEND / "config/health_thresholds.json"),
    ("ORM models", BACKEND / "models.py"),
]

PROCESS_DATA_STAGES = [
    "1  proactive signal scan",
    "2  health score calculation (L1→L4)",
    "3  Wizard A — journey / DECISION nodes",
    "3a tier1 LLM inference (optional OUTCOME nodes)",
    "3b Wizard B — trailing NRR / patterns",
    "4  signal analyst",
    "5  urgent signal scanner",
    "6  ROI engine",
    "7  Qdrant indexing",
    "8  health score events + onboarding activation plan",
]


def _vertical_data_dir(customer_id: int) -> Path | None:
    base = BACKEND / "verticals"
    if not base.is_dir():
        return None
    matches = sorted(base.glob(f"customer{customer_id}-*"))
    for d in matches:
        data = d / "data"
        if data.is_dir():
            return data
    return None


def cmd_map(_args: argparse.Namespace) -> None:
    print("CS Pulse — need-to-know runtime map")
    print(f"  CUSTOMER_ID={CUSTOMER_ID}  BACKEND={BACKEND}  LOAD_DRIVER={LOAD_DRIVER}\n")
    print("process_data stage order:")
    for line in PROCESS_DATA_STAGES:
        print(f"  {line}")
    print("\nReadable paths (inspect with: less <path>):")
    for label, path in NEED_TO_KNOW:
        flag = "OK" if path.exists() else "MISSING"
        print(f"  [{flag:7}] {label:28} {path}")
    data = _vertical_data_dir(CUSTOMER_ID)
    if data:
        n = len(list(data.glob("*.csv")))
        print(f"\n  Ingested CSV pack: {data} ({n} files)")
    else:
        print(f"\n  Ingested CSV pack: not found for customer {CUSTOMER_ID}")


def cmd_csv_ls(args: argparse.Namespace) -> None:
    cid = args.customer_id or CUSTOMER_ID
    data = _vertical_data_dir(cid)
    if not data:
        print(json.dumps({"error": f"No verticals/.../data for customer {cid}"}))
        sys.exit(1)
    rows = []
    for p in sorted(data.glob("*.csv")):
        with p.open(newline="", encoding="utf-8") as f:
            line_count = sum(1 for _ in f) - 1
        rows.append({"file": p.name, "bytes": p.stat().st_size, "data_rows": max(0, line_count)})
    print(json.dumps({"customer_id": cid, "data_dir": str(data), "files": rows}, indent=2))


def cmd_csv_head(args: argparse.Namespace) -> None:
    cid = args.customer_id or CUSTOMER_ID
    data = _vertical_data_dir(cid)
    if not data:
        sys.exit(f"No data dir for customer {cid}")
    path = data / args.file
    if not path.exists():
        sys.exit(f"Not found: {path}")
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i > args.lines:
                break
            print(line, end="")


def cmd_audit(args: argparse.Namespace) -> None:
    cid = args.customer_id or CUSTOMER_ID
    os.environ["CUSTOMER_ID"] = str(cid)
    audit_script = BACKEND / "scripts/ec2_persona_audit.py"
    if audit_script.exists():
        import runpy
        runpy.run_path(str(audit_script), run_name="__main__")
        return
    print(json.dumps({"error": "ec2_persona_audit.py not in image; redeploy with runtime kit"}))


def cmd_endpoints(args: argparse.Namespace) -> None:
    cid = args.customer_id or CUSTOMER_ID
    import io
    from contextlib import redirect_stdout, redirect_stderr

    paths = [
        ("health_summary", "/api/v1/health-summary"),
        ("cro", "/api/executive/cro-dashboard"),
        ("cfo", "/api/executive/cfo-dashboard"),
        ("accounts", "/api/v1/accounts"),
        ("daily_actions", "/api/v1/daily-actions"),
    ]
    email = os.environ.get("AUDIT_EMAIL", os.environ.get("CS_PULSE_EMAIL", ""))
    password = os.environ.get("AUDIT_PASSWORD", os.environ.get("CS_PULSE_PASSWORD", ""))

    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        from app_v3_minimal import app

        out = {"customer_id": cid, "endpoints": {}}
        with app.app_context():
            client = app.test_client()
            if email and password:
                client.post("/api/login", json={"email": email, "password": password})
            for key, path in paths:
                r = client.get(path, headers={"X-Customer-ID": str(cid)})
                body = r.get_json(silent=True) or {}
                if key == "accounts" and isinstance(body, list):
                    sample = {"count": len(body), "first_account_id": body[0].get("account_id") if body else None}
                elif key in ("cro", "cfo"):
                    sample = {
                        k: body.get(k)
                        for k in (
                            "revenue_at_risk", "revenue_protected", "expansion_pipeline",
                            "predictor_v3_portfolio_nrr",
                        )
                        if k in body
                    }
                    if not sample and body.get("revenue_summary"):
                        sample = body["revenue_summary"]
                elif key == "health_summary":
                    sample = {k: body.get(k) for k in ("total_arr", "avg_health", "account_count") if k in body}
                else:
                    sample = body if len(json.dumps(body, default=str)) < 2000 else {"_truncated": True, "keys": list(body)[:20]}
                out["endpoints"][key] = {"status": r.status_code, "body": sample}
    print(json.dumps(out, indent=2, default=str))


def cmd_export_db(args: argparse.Namespace) -> None:
    cid = args.customer_id or CUSTOMER_ID
    out_dir = Path(os.environ.get("RUNTIME_EXPORT_DIR", f"/tmp/runtime_export/{cid}"))
    out_dir.mkdir(parents=True, exist_ok=True)
    types = [t.strip() for t in args.types.split(",") if t.strip()]

    import io
    from contextlib import redirect_stdout, redirect_stderr

    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        from app_v3_minimal import app
        from extensions import db
        from models import Account, DC2SKPI, QualitativeSignal, ContextNode

        written = []
        with app.app_context():
            accounts = Account.query.filter_by(customer_id=cid).all()
            account_ids = [a.account_id for a in accounts]

            if "accounts" in types:
                path = out_dir / "accounts.csv"
                cols = ["account_id", "account_name", "revenue", "account_status", "assigned_csm"]
                with path.open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                    w.writeheader()
                    for a in accounts:
                        w.writerow({
                            "account_id": a.account_id,
                            "account_name": a.account_name,
                            "revenue": a.revenue,
                            "account_status": a.account_status,
                            "assigned_csm": a.assigned_csm,
                        })
                written.append(str(path))

            if "kpi_measurements" in types:
                path = out_dir / "kpi_measurements.csv"
                kpis = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).limit(50000).all()
                cols = ["account_id", "kpi_code", "value", "measured_at", "pillar"]
                with path.open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                    w.writeheader()
                    for k in kpis:
                        w.writerow({
                            "account_id": k.account_id,
                            "kpi_code": k.kpi_code,
                            "value": k.value,
                            "measured_at": k.measured_at.isoformat() if k.measured_at else None,
                            "pillar": k.pillar,
                        })
                written.append(str(path))

            if "signals" in types:
                path = out_dir / "qualitative_signals.csv"
                sigs = QualitativeSignal.query.filter(
                    QualitativeSignal.account_id.in_(account_ids)
                ).limit(50000).all()
                cols = ["signal_id", "account_id", "signal_type", "sentiment", "stakeholder_title", "content"]
                with path.open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                    w.writeheader()
                    for s in sigs:
                        w.writerow({
                            "signal_id": s.signal_id,
                            "account_id": s.account_id,
                            "signal_type": s.signal_type,
                            "sentiment": s.sentiment,
                            "stakeholder_title": getattr(s, "stakeholder_title", None),
                            "content": (s.content or "")[:500],
                        })
                written.append(str(path))

            if "outcomes" in types:
                path = out_dir / "outcomes.csv"
                nodes = ContextNode.query.filter_by(customer_id=cid, node_type="OUTCOME").limit(10000).all()
                cols = ["node_id", "account_id", "title", "revenue_impact", "confidence"]
                with path.open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                    w.writeheader()
                    for n in nodes:
                        w.writerow({
                            "node_id": n.node_id,
                            "account_id": n.account_id,
                            "title": n.title,
                            "revenue_impact": float(n.revenue_impact) if n.revenue_impact else None,
                            "confidence": float(n.confidence) if n.confidence else None,
                        })
                written.append(str(path))

            manifest_src = LOAD_DRIVER / "manifests/predictor_v3_demo_saas_cust336.json"
            if cid == 336 and manifest_src.exists():
                dest = out_dir / "manifest_predictor_v3_demo_saas_cust336.json"
                dest.write_text(manifest_src.read_text(encoding="utf-8"))
                written.append(str(dest))

    print(json.dumps({
        "customer_id": cid,
        "export_dir": str(out_dir),
        "files": written,
        "pull_hint": f"sudo docker cp cspulse-platform:{out_dir} ./cust{cid}_export",
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="CS Pulse runtime explorer (EC2 container)")
    parser.add_argument("--customer-id", type=int, default=None, help=f"default: CUSTOMER_ID env or {CUSTOMER_ID}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("map", help="Print need-to-know paths and process_data stages")
    sub.add_parser("audit", help="Full persona + parity audit (JSON)")
    sub.add_parser("pipeline", help="Print process_data stage order")

    p_csv = sub.add_parser("csv-ls", help="List ingested CSV files on disk")
    p_csv.set_defaults(func=cmd_csv_ls)

    p_head = sub.add_parser("csv-head", help="Print first lines of an ingested CSV")
    p_head.add_argument("file", help="e.g. qualitative_signals.csv")
    p_head.add_argument("--lines", type=int, default=5)
    p_head.set_defaults(func=cmd_csv_head)

    p_ep = sub.add_parser("endpoints", help="Sample live API JSON via in-process test client")
    p_ep.set_defaults(func=cmd_endpoints)

    p_ex = sub.add_parser("export-db", help="Export DB slices + manifest to RUNTIME_EXPORT_DIR")
    p_ex.add_argument(
        "--types",
        default="accounts,signals,kpi_measurements,outcomes",
        help="comma-separated: accounts,signals,kpi_measurements,outcomes",
    )
    p_ex.set_defaults(func=cmd_export_db)

    args = parser.parse_args()
    if args.command == "map":
        cmd_map(args)
    elif args.command == "pipeline":
        for line in PROCESS_DATA_STAGES:
            print(line)
    elif args.command == "audit":
        cmd_audit(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
