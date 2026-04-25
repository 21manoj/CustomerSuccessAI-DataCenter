#!/usr/bin/env python3
"""
loaddriver_to_pulse_test.py
============================

Ingest a load-driver-generated 7-CSV dataset into cs_pulse_test, alongside
the Claude-driven synthetic tenants. Used to A/B test whether the Wizard B
MAPE difference is driven by data shape (load-driver vocabulary aligns with
Wizard A's classifier) or by Wizard B algorithmic limitation.

The sidecar (`future_truth`) is derived from the manifest's
`lifecycle_events` field — explicit ground-truth pin for each named account.

Usage (inside cspulse-platform container):
    DATABASE_URL=postgresql://.../cs_pulse_test \
        python3 /tmp/loaddriver_to_pulse_test.py \
          --csv-dir /tmp/loaddriver_slides_demo/ \
          --manifest /tmp/load-driver-source/manifests/slides_demo_saas_v2_deck_aligned.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/app/backend")


def _safety_check():
    db = os.environ.get("DATABASE_URL", "")
    if "cs_pulse_test" not in db.lower() and "_test" not in db.lower():
        print("ERROR: DATABASE_URL must point to test DB", file=sys.stderr)
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    args = ap.parse_args()

    _safety_check()

    from app_v3_minimal import app, db
    from models import Customer, Account, CustomerConfig, DC2SKPI, QualitativeSignal

    manifest = json.load(args.manifest.open())
    # Derive a stable per-manifest customer name + email so multiple
    # manifests can coexist in cs_pulse_test without unique-constraint clashes.
    manifest_stem = args.manifest.stem  # e.g. "phoenix_4phase_saas"
    cust_name = f"LoadDriver {manifest_stem} (claude_driven_backtest_v1)"
    cust_email = f"admin@ld-{manifest_stem.replace('_','-')}.test"

    with app.app_context():
        # 1. Customer + CustomerConfig
        cust = Customer(
            customer_name=cust_name, email=cust_email, vertical="saas_premium"
        )
        db.session.add(cust)
        db.session.flush()
        cust_id = cust.customer_id

        cfg = CustomerConfig(
            customer_id=cust_id, vertical="saas_premium",
            dc2s_pillar_weights={"P1": 0.25, "P2": 0.25, "P3": 0.25, "P5": 0.25},
        )
        db.session.add(cfg)
        db.session.commit()
        print(f"  cust_id={cust_id}", file=sys.stderr)

        # 2. Accounts — load-driver schema has more cols; pick what Account model uses
        ext_to_acct_id = {}
        with (args.csv_dir / "account_details.csv").open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                acct = Account(
                    customer_id=cust_id,
                    account_name=row.get("account_name") or "",
                    external_account_id=str(row["source_account_id"]),
                    revenue=float(row.get("arr") or row.get("revenue") or 0),
                    industry=row.get("industry"),
                    vertical="saas_premium",
                    region=row.get("region"),
                    account_status=row.get("account_status") or "active",
                )
                db.session.add(acct)
                db.session.flush()
                ext_to_acct_id[str(row["source_account_id"])] = acct.account_id
        db.session.commit()
        print(f"  {len(ext_to_acct_id)} accounts created", file=sys.stderr)

        # 3. KPIs via direct bulk upsert (load-driver weekly schedule preserved)
        from upload_api_v3_improved_duplicates import bulk_upsert_kpis
        import pandas as pd
        kpi_records = []
        with (args.csv_dir / "kpi_measurements.csv").open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                aid = ext_to_acct_id.get(str(row["source_account_id"]))
                if aid is None:
                    continue
                try:
                    val = float(row["value"])
                except (KeyError, ValueError, TypeError):
                    continue
                try:
                    dt = datetime.fromisoformat(str(row["measured_at"]))
                except Exception:
                    continue
                kpi_records.append({
                    "account_id": aid,
                    "kpi_code": row["kpi_code"],
                    "value": val,
                    "pillar": row.get("pillar") or row["kpi_code"].split("-")[0],
                    "measured_at": dt,
                    "status": row.get("status") or "valid",
                })
        if kpi_records:
            df_k = pd.DataFrame(kpi_records)
            n = bulk_upsert_kpis(df_k)
            print(f"  {n} KPI rows upserted", file=sys.stderr)

        # 4. Signals — direct ORM inserts (load-driver carries arc_id which we keep)
        sig_count = 0
        with (args.csv_dir / "qualitative_signals.csv").open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                aid = ext_to_acct_id.get(str(row["source_account_id"]))
                if aid is None:
                    continue
                try:
                    sd = datetime.fromisoformat(str(row["signal_date"])).date()
                except Exception:
                    continue
                try:
                    db.session.add(QualitativeSignal(
                        signal_id=row.get("signal_id") or f"ld-{cust_id}-{sig_count}",
                        customer_id=cust_id,
                        account_id=aid,
                        signal_date=sd,
                        signal_type=row.get("signal_type") or "unknown",
                        content=(row.get("content") or "")[:2000],
                        sentiment=row.get("sentiment") or "neutral",
                    ))
                    sig_count += 1
                except Exception as e:
                    db.session.rollback()
                    print(f"  signal insert err: {e}", file=sys.stderr)
        db.session.commit()
        print(f"  {sig_count} signals inserted", file=sys.stderr)

        # 5. Outcomes via context_graph upsert_node
        # Apr 25 2026: filter by status='resolved' so mid-lifecycle states
        # (in_progress) don't double-count with their resolved counterparts.
        # Load-driver writes the same expansion event as 3 rows
        # (expansion_approved → revenue_growth → expansion_closed) — only
        # the closed/resolved one represents an actual ARR change.
        # For terminal-only subtypes (churn_lost, expansion_closed) we
        # accept any status since they're terminal by name.
        from utils.context_graph import upsert_node
        TERMINAL_BY_NAME = {
            'expansion_closed', 'churn_lost', 'contraction', 'new_logo',
        }
        out_count = 0
        out_skipped = 0
        with (args.csv_dir / "outcomes.csv").open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                aid = ext_to_acct_id.get(str(row["source_account_id"]))
                if aid is None:
                    continue
                outcome_type = row.get("outcome_type", "retention")
                status = (row.get("status") or "").strip().lower()
                # Skip mid-lifecycle states for non-terminal-by-name subtypes
                if outcome_type not in TERMINAL_BY_NAME and status and status != "resolved":
                    out_skipped += 1
                    continue
                try:
                    occurred = datetime.fromisoformat(str(row["outcome_date"]))
                except Exception:
                    occurred = datetime(2026, 1, 1)
                try:
                    rev = float(row.get("revenue_value") or 0)
                except (TypeError, ValueError):
                    rev = 0.0
                # Mirror production bucket-map from
                # onboarding_api_v2_config_aware.py:1218. The shorter map
                # I had was missing `expansion_approved` (5 instances on
                # phoenix_4phase load-driver dataset), causing expansion
                # to mis-classify as 'protected' and Wizard B to under-
                # forecast portfolio NRR by ~7pp.
                rev_type_map = {
                    'expansion': 'expansion',
                    'expansion_approved': 'expansion',
                    'expansion_closed': 'expansion',
                    'expansion_opportunity': 'expansion',
                    'revenue_growth': 'expansion',
                    'retention': 'protected',
                    'revenue_protected': 'protected',
                    'churn_averted': 'protected',
                    'renewal_secured': 'protected',
                    'engagement_recovery': 'protected',
                    'cost_reduction': 'protected',
                    'partial_recovery': 'protected',
                    'churn_loss': 'lost',
                    'revenue_at_risk': 'at_risk',
                    'engagement_decline': 'at_risk',
                    'renewal_uncertainty': 'at_risk',
                    'capacity_constraint': 'at_risk',
                    'partner_friction': 'at_risk',
                }
                upsert_node(
                    customer_id=cust_id, account_id=aid,
                    node_type="OUTCOME",
                    title=(row.get("title") or "")[:200],
                    occurred_at=occurred,
                    properties={"outcome_type": outcome_type},
                    source_platform="load_driver",
                    source_event_id=f"ld-{aid}-{outcome_type}-{occurred.date()}",
                    confidence=0.85,
                    revenue_impact=rev,
                    revenue_impact_type=rev_type_map.get(outcome_type, "protected"),
                    tier=1,
                )
                out_count += 1
        db.session.commit()
        print(f"  {out_count} OUTCOME nodes inserted ({out_skipped} mid-lifecycle skipped)",
              file=sys.stderr)

        # 6. Sidecar from manifest lifecycle_events
        events = manifest.get("lifecycle_events", {})
        accounts = manifest.get("accounts", [])
        # Build name → external id from CSV (since accounts CSV had source_account_id as integer)
        name_to_ext = {}
        with (args.csv_dir / "account_details.csv").open() as f:
            for row in csv.DictReader(f):
                name_to_ext[row["account_name"]] = str(row["source_account_id"])

        for ainfo in accounts:
            name = ainfo["name"]
            ext_id = name_to_ext.get(name)
            if not ext_id:
                continue
            aid = ext_to_acct_id.get(ext_id)
            if not aid:
                continue
            ev = events.get(name)
            if ev:
                # Handle event types: churn/expand have delta_pct; "new" = new logo (no delta yet)
                if ev.get("event") == "new":
                    realized = 100
                    outcome = "renewed_flat"  # new logos held at parity for sidecar
                else:
                    delta = ev.get("delta_pct", 0)
                    realized = max(0, 100 + delta)
                    if delta <= -100:
                        outcome = "churned"
                    elif delta > 0:
                        outcome = "renewed_expansion"
                    else:
                        outcome = "contracted"
            else:
                realized = 100
                outcome = "renewed_flat"
            sidecar = {
                "scenario": "organic_no_cs_pulse_intervention",
                "difficulty": "EASY" if not ev else (
                    "HARD" if abs(ev.get("delta_pct", 0)) >= 50 else "MEDIUM"),
                "narrative": ainfo.get("story_arc") or "n/a",
                "realized_renewal_date": "2026-10-15",
                "realized_nrr_outcome": outcome,
                "realized_nrr_pct_for_account": realized,
                "is_nrr_forecastable_from_history": True,
                "organic_cs_investment_usd_annual": int(ainfo["arr"] * 0.015),
                "realized_protected_arr_usd": ainfo["arr"] if realized >= 100 else 0,
                "realized_expanded_arr_usd": int(ainfo["arr"] * (realized - 100) / 100) if realized > 100 else 0,
                "realized_lost_arr_usd": int(ainfo["arr"] * (100 - realized) / 100) if realized < 100 else 0,
                "is_roi_forecastable_from_history": True,
            }
            acct = Account.query.get(aid)
            if acct:
                meta = dict(acct.profile_metadata or {})
                meta["synthetic_ground_truth"] = sidecar
                meta["synthetic_tenant_id"] = "loaddriver-slides-demo"
                acct.profile_metadata = meta
        db.session.commit()
        print(f"  sidecar stashed on accounts", file=sys.stderr)

        # 7. Trigger process_data — DB-native path
        from mcp_server.cs_pulse_onboarding import _process_data_impl
        result = _process_data_impl(cust_id)
        print(f"  process_data: {str(result)[:120]}", file=sys.stderr)

        print(f"\n✅ load-driver tenant ingested as customer_id={cust_id}", file=sys.stderr)
        print(f"   for pytest: SYNTHETIC_CUSTOMER_IDS={cust_id}", file=sys.stderr)


if __name__ == "__main__":
    main()
