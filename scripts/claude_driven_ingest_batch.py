#!/usr/bin/env python3
"""
claude_driven_ingest_batch.py
==============================

Ingest a Claude-generated synthetic dataset into cs_pulse_test directly,
in-process, bypassing HTTP and the inline-CSV-loader bug in
cs_pulse_onboarding.py._process_data_impl (backlog: KPI inline loader
uses datetime.now() instead of CSV measurement_month — Apr 24 2026).

Design choices:
  - NEVER write CSV files to the filesystem. All records stream into the
    bulk_upsert_* functions from upload_api_v3_improved_duplicates.
    This avoids the inline-loader bug entirely (it only fires when it
    finds a kpi_measurements.csv on disk).
  - Pipeline processing (Wizard A, MOD-007, Wizard B, ROI engine) is
    invoked via `_process_data_impl` which, finding data already in DB,
    takes the DB-native recompute path and never touches the inline loader.
  - DATABASE_URL is resolved from this script's own process env. The
    running cspulse-platform container's DATABASE_URL is irrelevant —
    we never call its HTTP API.

Per-tenant flow:
  1. Create Customer + CustomerConfig (commit so cross-session queries see it)
  2. Bulk-upsert Account records — source_account_id → external_account_id
  3. Fetch back Account rows to build external_id → account_id map
  4. Bulk-upsert DC2SKPI — measured_at derived from CSV measurement_month
  5. Bulk-insert QualitativeSignal — dedup by (customer_id, signal_id)
  6. Insert OUTCOME ContextNodes via utils.context_graph.upsert_node
  7. Stash sidecar onto Account.profile_metadata.synthetic_ground_truth
  8. Call _process_data_impl(cust_id) → DB-native health + wizards + ROI

Safety:
  - Refuses if DATABASE_URL doesn't name a test DB
  - Refuses if target DB has >100 existing customers
  - Synthetic tenants tagged — --purge cleans them without touching others

Usage (on EC2):
    DATABASE_URL=postgresql://postgres:pass@127.0.0.1:5433/cs_pulse_test \
        python3 scripts/claude_driven_ingest_batch.py \
          --input scripts/datasets/claude_driven_backtest_v1.json

    python3 scripts/claude_driven_ingest_batch.py --purge
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent / "kpi-dashboard" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

SYNTHETIC_CUSTOMER_TAG = "claude_driven_backtest_v1"

# Fixed 12-month window: months[i] corresponds to kpi_monthly_values[i]
MONTHS = [
    "2025-05-15", "2025-06-15", "2025-07-15", "2025-08-15",
    "2025-09-15", "2025-10-15", "2025-11-15", "2025-12-15",
    "2026-01-15", "2026-02-15", "2026-03-15", "2026-04-15",
]


# ════════════════════════════════════════════════════════════════════
# Safety + backend import (same pattern as before)
# ════════════════════════════════════════════════════════════════════

def _db_safety_check():
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set. Refusing to run.", file=sys.stderr)
        sys.exit(2)
    lower = db_url.lower()
    if "cs_pulse_test" not in lower and "_test" not in lower:
        print(f"ERROR: DATABASE_URL ({db_url!r}) does not name a test DB.",
              file=sys.stderr)
        print("       Script refuses non-test DB ingests.", file=sys.stderr)
        sys.exit(2)


def _import_backend():
    global app, db, Customer, Account, CustomerConfig, DC2SKPI, QualitativeSignal
    from app_v3_minimal import app as _app, db as _db
    from models import (
        Customer as _C, Account as _A, CustomerConfig as _CC,
        DC2SKPI as _K, QualitativeSignal as _S,
    )
    app, db = _app, _db
    Customer, Account, CustomerConfig = _C, _A, _CC
    DC2SKPI, QualitativeSignal = _K, _S


def _customer_count_sanity():
    n = Customer.query.count()
    if n > 100:
        print(f"ERROR: target DB has {n} customers — looks like prod. Refusing.",
              file=sys.stderr)
        sys.exit(2)
    print(f"✓ safety: {n} existing customers (threshold 100)", file=sys.stderr)


# ════════════════════════════════════════════════════════════════════
# Purge
# ════════════════════════════════════════════════════════════════════

def purge_synthetic():
    with app.app_context():
        custs = Customer.query.filter(
            Customer.customer_name.like(f"%{SYNTHETIC_CUSTOMER_TAG}%")
        ).all()
        if not custs:
            print("no synthetic customers found — nothing to purge", file=sys.stderr)
            return
        print(f"purging {len(custs)} synthetic customers...", file=sys.stderr)

        # Wipe ALL dependent rows via raw SQL. Discover FK'd tables from
        # pg_catalog rather than hand-curating a list (wizard_runs,
        # wizard_learnings, pattern_analyses, nrr_forecast_snapshots, and
        # whatever else the pipeline creates — all get picked up automatically).
        from sqlalchemy import text
        cids = [c.customer_id for c in custs]

        def _fk_tables(referenced_table: str, referenced_column: str) -> list[tuple[str, str]]:
            """Return [(table, column), ...] of tables with FK to (referenced_table.referenced_column)."""
            rows = db.session.execute(text("""
                SELECT tc.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND ccu.table_name = :rtbl
                  AND ccu.column_name = :rcol
            """), {"rtbl": referenced_table, "rcol": referenced_column}).all()
            return [(r[0], r[1]) for r in rows]

        cust_fk_tables = _fk_tables("customers", "customer_id")
        acct_fk_tables = _fk_tables("accounts", "account_id")
        # pass 1: delete rows referencing accounts (must run before customer-scoped
        # pass since some tables have both FKs and we need to clear account FKs first
        # to satisfy constraints on accounts table itself)
        for tbl, col in acct_fk_tables:
            try:
                db.session.execute(text(
                    f"DELETE FROM {tbl} WHERE {col} IN "
                    f"(SELECT account_id FROM accounts WHERE customer_id = ANY(:cids))"
                ), {"cids": cids})
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"  purge acct-fk {tbl}.{col}: {str(e)[:120]}", file=sys.stderr)

        # pass 2: delete rows referencing customers (customer_configs,
        # wizard_runs, wizard_learnings, etc.)
        for tbl, col in cust_fk_tables:
            if tbl == "accounts":
                continue  # handled below
            try:
                db.session.execute(text(
                    f"DELETE FROM {tbl} WHERE {col} = ANY(:cids)"
                ), {"cids": cids})
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"  purge cust-fk {tbl}.{col}: {str(e)[:120]}", file=sys.stderr)
        # Now safe to drop accounts then customer
        db.session.execute(text(
            "DELETE FROM accounts WHERE customer_id = ANY(:cids)"
        ), {"cids": cids})
        db.session.execute(text(
            "DELETE FROM customers WHERE customer_id = ANY(:cids)"
        ), {"cids": cids})
        db.session.commit()
        print(f"✓ purge complete", file=sys.stderr)


# ════════════════════════════════════════════════════════════════════
# Per-tenant builders — in-memory records (no filesystem writes)
# ════════════════════════════════════════════════════════════════════

# KPI code → pillar prefix (codes are P1-KPI*, P2-KPI*, ...)
def _pillar_for(kpi_code: str) -> str:
    return kpi_code.split("-")[0] if "-" in kpi_code else "P1"


def build_records_for_tenant(tenant: dict, customer_id: int):
    """Return (acct_records, kpi_records, signal_records, outcome_records).
    External/synthetic IDs get rewritten to numeric strings so pipeline code
    that does `int(source_account_id)` keeps working.
    """
    accts = tenant.get("accounts") or []
    tenant_idx = tenant.get("tenant_idx", 1)

    # Rewrite syn-tNN-aMM → "{tenant_idx*10000+acct_idx}" (tenant-scoped unique)
    id_map: dict[str, str] = {}
    for acct_idx, a in enumerate(accts, 1):
        syn_id = a.get("account_id") or a.get("csv_1_account_details", {}).get("source_account_id")
        if not syn_id:
            continue
        numeric = str(tenant_idx * 10000 + acct_idx)
        id_map[syn_id] = numeric
        a["account_id"] = numeric
        a["_synthetic_original_id"] = syn_id
        if "csv_1_account_details" in a:
            a["csv_1_account_details"]["source_account_id"] = numeric
            a["csv_1_account_details"]["_synthetic_original_id"] = syn_id

    # 1. Account records — Account.bulk_upsert_accounts expects dicts with
    # fields matching Account model columns. We set customer_id, account_name,
    # external_account_id (the numeric string), revenue, industry, vertical,
    # region. account_id is autoincrement so we omit it.
    acct_records = []
    for a in accts:
        d = a.get("csv_1_account_details", {})
        if not d:
            continue
        acct_records.append({
            "customer_id": customer_id,
            "account_name": d.get("account_name", f"syn-{d.get('source_account_id')}"),
            "external_account_id": str(d.get("source_account_id")),
            "revenue": float(d.get("arr") or 0),
            "industry": d.get("industry"),
            # Force all synthetic accounts onto saas_premium — Claude sometimes
            # invents vertical names ('data_analytics', 'biotech_saas', etc)
            # that the platform's id_generator whitelist rejects.
            "vertical": "saas_premium",
            "region": d.get("region"),
            "account_status": "active",
        })

    # 2. KPI records — keyed by external_account_id for now; we'll remap to
    # numeric account_id AFTER we know the DB-assigned IDs.
    # Monthly values expand: kpi_monthly_values = {"P1-KPI1": [v0..v11]}
    # index i → MONTHS[i] timestamp
    kpi_records_by_extid: list[dict] = []  # each dict has 'external_account_id' + other fields
    for a in accts:
        ext_id = str(a.get("account_id") or a.get("csv_1_account_details", {}).get("source_account_id"))
        compact = a.get("kpi_monthly_values") or {}
        for kpi_code, values in compact.items():
            if not isinstance(values, list):
                continue
            for i, v in enumerate(values[:12]):
                if v is None:
                    continue
                try:
                    value = float(v)
                except (TypeError, ValueError):
                    continue
                kpi_records_by_extid.append({
                    "external_account_id": ext_id,
                    "kpi_code": kpi_code,
                    "value": value,
                    "pillar": _pillar_for(kpi_code),
                    "measured_at": datetime.fromisoformat(f"{MONTHS[i]}T00:00:00"),
                    "status": "valid",
                })

    # 3. Signal records — same pattern, remap ext→int later
    sig_records_by_extid: list[dict] = []
    for a in accts:
        ext_id = str(a.get("account_id") or a.get("csv_1_account_details", {}).get("source_account_id"))
        for s_idx, row in enumerate(a.get("csv_3_qualitative_signals", []), 1):
            try:
                d = datetime.fromisoformat(str(row.get("signal_date", "2026-01-01")))
            except Exception:
                d = datetime(2026, 1, 1)
            sig_records_by_extid.append({
                "external_account_id": ext_id,
                "signal_id": f"syn-t{tenant_idx:02d}-{ext_id}-s{s_idx:03d}",
                "customer_id": customer_id,
                "signal_date": d.date(),
                "signal_type": row.get("signal_type", "unknown"),
                "sentiment": row.get("sentiment", "neutral"),
                "content": row.get("description", "")[:2000],
            })

    # 4. Outcome records — OUTCOME ContextNodes, one per row
    out_records_by_extid: list[dict] = []
    for a in accts:
        ext_id = str(a.get("account_id") or a.get("csv_1_account_details", {}).get("source_account_id"))
        for row in a.get("csv_4_outcomes", []):
            try:
                rev = float(row.get("revenue_value") or 0)
            except (TypeError, ValueError):
                rev = 0.0
            try:
                occurred = datetime.fromisoformat(str(row.get("outcome_date", "2026-01-01")))
            except Exception:
                occurred = datetime(2026, 1, 1)
            out_records_by_extid.append({
                "external_account_id": ext_id,
                "title": (row.get("title") or "")[:200],
                "outcome_type": row.get("outcome_type", "retention"),
                "revenue_value": rev,
                "confidence": float(row.get("confidence") or 0.8),
                "occurred_at": occurred,
            })

    return acct_records, kpi_records_by_extid, sig_records_by_extid, out_records_by_extid


# ════════════════════════════════════════════════════════════════════
# Per-tenant ingest
# ════════════════════════════════════════════════════════════════════

def ingest_tenant(tenant: dict, idx: int) -> int | None:
    tenant_idx = tenant.get("tenant_idx", idx + 1)
    tenant_id = tenant.get("tenant_id") or f"T{tenant_idx:02d}"
    cust_name = f"Synthetic {tenant_id} ({SYNTHETIC_CUSTOMER_TAG})"
    cust_email = f"admin@syn-t{tenant_idx:02d}.test"

    with app.app_context():
        # 1. Customer + CustomerConfig — vertical must be set so score calc
        # and pipeline read the right per-vertical config.
        cust = Customer(
            customer_name=cust_name,
            email=cust_email,
            vertical="saas_premium",
        )
        db.session.add(cust)
        db.session.flush()
        cust_id = cust.customer_id

        cfg = CustomerConfig(
            customer_id=cust_id,
            vertical="saas_premium",
            dc2s_pillar_weights={"P1": 0.25, "P2": 0.25, "P3": 0.25, "P5": 0.25},
        )
        db.session.add(cfg)
        db.session.commit()

        # 2. Build in-memory records
        acct_records, kpi_ext, sig_ext, out_ext = build_records_for_tenant(
            tenant, cust_id
        )
        if not acct_records:
            print(f"  t{tenant_idx:02d} no accounts — skip", file=sys.stderr)
            return cust_id

        # 3. Bulk-upsert accounts (Account model has autoincrement account_id)
        # Rather than calling bulk_upsert_accounts (which targets account_id
        # for conflict resolution — tricky for brand-new customers where IDs
        # are autoassigned), insert them one-by-one and capture the IDs.
        ext_to_acct_id: dict[str, int] = {}
        for rec in acct_records:
            acct = Account(**rec)
            db.session.add(acct)
            db.session.flush()
            ext_to_acct_id[str(rec["external_account_id"])] = acct.account_id
        db.session.commit()
        print(f"  t{tenant_idx:02d} {len(ext_to_acct_id)} accounts created "
              f"(cust_id={cust_id})", file=sys.stderr)

        # 4. Bulk-upsert KPIs — resolve ext_id → numeric account_id
        kpi_records = []
        for r in kpi_ext:
            aid = ext_to_acct_id.get(r["external_account_id"])
            if aid is None:
                continue
            kpi_records.append({
                "account_id": aid,
                "kpi_code": r["kpi_code"],
                "value": r["value"],
                "pillar": r["pillar"],
                "measured_at": r["measured_at"],
                "status": r["status"],
            })
        if kpi_records:
            try:
                import pandas as pd
                from upload_api_v3_improved_duplicates import bulk_upsert_kpis
                df = pd.DataFrame(kpi_records)
                n = bulk_upsert_kpis(df)
                print(f"  t{tenant_idx:02d} {n} KPI rows upserted", file=sys.stderr)
            except Exception as e:
                print(f"  t{tenant_idx:02d} KPI upsert FAILED: {e}", file=sys.stderr)
                db.session.rollback()

        # 5. Bulk-insert signals (skip duplicates)
        sig_records = []
        missing_ext = 0
        for r in sig_ext:
            aid = ext_to_acct_id.get(r["external_account_id"])
            if aid is None:
                missing_ext += 1
                continue
            sig_records.append({
                "signal_id": r["signal_id"],
                "customer_id": r["customer_id"],
                "account_id": aid,
                "signal_date": r["signal_date"],
                "signal_type": r["signal_type"],
                "sentiment": r["sentiment"],
                "content": r["content"],
            })
        print(f"  t{tenant_idx:02d} signal prep: {len(sig_ext)} raw → "
              f"{len(sig_records)} resolved ({missing_ext} unmapped)",
              file=sys.stderr)
        if sig_records:
            # NOTE: bulk_insert_skip_duplicates_signals in
            # upload_api_v3_improved_duplicates uses on_conflict_do_nothing
            # with index_elements=['signal_id'], but the actual unique
            # constraint is composite (customer_id, signal_id) — so that
            # bulk path errors with "no unique constraint matching ON
            # CONFLICT specification". File as backlog. We bypass via
            # direct ORM inserts which are fine at our scale (100/tenant).
            try:
                inserted = 0
                for sr in sig_records:
                    db.session.add(QualitativeSignal(**sr))
                    inserted += 1
                db.session.commit()
                print(f"  t{tenant_idx:02d} {inserted} signals inserted",
                      file=sys.stderr)
            except Exception as e:
                print(f"  t{tenant_idx:02d} signal insert FAILED: {e}", file=sys.stderr)
                import traceback; traceback.print_exc(file=sys.stderr)
                db.session.rollback()

        # 6. Outcomes → OUTCOME ContextNodes (the canonical storage)
        try:
            from utils.context_graph import upsert_node
            n_outcomes = 0
            for r in out_ext:
                aid = ext_to_acct_id.get(r["external_account_id"])
                if aid is None:
                    continue
                rev_type_map = {
                    "expansion_closed": "expansion",
                    "expansion": "expansion",
                    "revenue_growth": "expansion",
                    "renewal_secured": "protected",
                    "revenue_protected": "protected",
                    "churn_averted": "protected",
                    "retention": "protected",
                    "contraction": "lost",
                    "churn_loss": "lost",
                    "revenue_at_risk": "at_risk",
                    "renewal_uncertainty": "at_risk",
                    "engagement_decline": "at_risk",
                }
                rev_impact_type = rev_type_map.get(r["outcome_type"], "protected")
                upsert_node(
                    customer_id=cust_id,
                    account_id=aid,
                    node_type="OUTCOME",
                    title=r["title"],
                    occurred_at=r["occurred_at"],
                    properties={"outcome_type": r["outcome_type"]},
                    source_platform="claude_driven_synthetic",
                    source_event_id=f"syn-t{tenant_idx:02d}-{aid}-{rev_impact_type}-{r['occurred_at'].date()}",
                    confidence=r["confidence"],
                    revenue_impact=r["revenue_value"],
                    revenue_impact_type=rev_impact_type,
                    tier=1,
                )
                n_outcomes += 1
            db.session.commit()
            print(f"  t{tenant_idx:02d} {n_outcomes} OUTCOME nodes inserted",
                  file=sys.stderr)
        except Exception as e:
            print(f"  t{tenant_idx:02d} outcome insert FAILED: {e}", file=sys.stderr)
            db.session.rollback()

        # 7. Stash sidecar onto Account.profile_metadata
        for syn_acct in tenant.get("accounts", []):
            ext_id = str(syn_acct.get("account_id") or
                         syn_acct.get("csv_1_account_details", {}).get("source_account_id"))
            aid = ext_to_acct_id.get(ext_id)
            if aid is None:
                continue
            acct = Account.query.get(aid)
            if not acct:
                continue
            meta = dict(acct.profile_metadata or {})
            meta["synthetic_ground_truth"] = syn_acct.get("future_truth", {})
            meta["synthetic_original_id"] = syn_acct.get("_synthetic_original_id")
            meta["synthetic_tenant_id"] = tenant.get("tenant_id") or f"T{tenant_idx:02d}"
            acct.profile_metadata = meta
        db.session.commit()

        # 8. Trigger pipeline via DB-native path. Because KPIs are already in
        # the DB, _process_data_impl takes Path 1 (recalculate only) and
        # never invokes the inline CSV loader that has the datetime.now() bug.
        try:
            from mcp_server.cs_pulse_onboarding import _process_data_impl
            result = _process_data_impl(cust_id)
            print(f"  t{tenant_idx:02d} process_data: {str(result)[:160]}",
                  file=sys.stderr)
        except Exception as e:
            print(f"  t{tenant_idx:02d} process_data FAILED: {e}", file=sys.stderr)
            # Don't rollback — data is already in DB; MAPE test can still run
            # on what's there even if wizards didn't fire.

        return cust_id


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

def ingest(dataset_path: Path):
    with dataset_path.open() as f:
        dataset = json.load(f)
    tenants = dataset.get("tenants", [])
    print(f"loaded {len(tenants)} tenants from {dataset_path}", file=sys.stderr)

    with app.app_context():
        _customer_count_sanity()
        existing = Customer.query.filter(
            Customer.customer_name.like(f"%{SYNTHETIC_CUSTOMER_TAG}%")
        ).count()
        if existing:
            print(f"ERROR: {existing} synthetic tenants already exist.",
                  file=sys.stderr)
            print(f"       run with --purge first", file=sys.stderr)
            sys.exit(3)

    cust_ids = []
    for i, tenant in enumerate(tenants):
        try:
            cid = ingest_tenant(tenant, i)
            if cid is not None:
                cust_ids.append(cid)
        except Exception as e:
            print(f"ingest tenant {i} FAILED: {e}", file=sys.stderr)
            import traceback; traceback.print_exc(file=sys.stderr)
            with app.app_context():
                db.session.rollback()

    print(f"\n✅ ingested {len(cust_ids)} tenants. customer_ids: {cust_ids}",
          file=sys.stderr)
    print(f"   for pytest:", file=sys.stderr)
    print(f"     export SYNTHETIC_CUSTOMER_IDS=\"{','.join(map(str, cust_ids))}\"",
          file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Claude-driven synthetic ingest")
    parser.add_argument("--input", type=Path,
                        default=Path("scripts/datasets/claude_driven_backtest_v1.json"))
    parser.add_argument("--purge", action="store_true",
                        help="Remove all synthetic customers + rows; exit")
    args = parser.parse_args()

    _db_safety_check()
    _import_backend()

    if args.purge:
        purge_synthetic()
        return

    if not args.input.exists():
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    ingest(args.input)


if __name__ == "__main__":
    main()
