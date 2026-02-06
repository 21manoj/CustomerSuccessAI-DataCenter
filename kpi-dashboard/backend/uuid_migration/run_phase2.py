#!/usr/bin/env python3
"""
Phase 2 Orchestrator: SaaS Backfill + Combined Validation

Prerequisites:
  - Phase 1 must be complete (columns exist, DC customer_id=9 backfilled)

Steps:
  2a. Backfill customer_id=1 (SaaS) data
  2b. Validate BOTH DC and SaaS migrations
  Auto-rollback SaaS data if validation fails (DC data preserved).

Usage:
  cd kpi-dashboard/backend
  python uuid_migration/run_phase2.py

  # Dry run (validate only):
  python uuid_migration/run_phase2.py --dry-run

  # Rollback SaaS only:
  python uuid_migration/run_phase2.py --rollback-saas
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from uuid_migration.phase2a_backfill_saas import run as run_phase2a
from uuid_migration.phase2b_validate_all import run as run_phase2b


def soft_rollback_saas(db):
    """Clear uuid values for customer_id=1 only. DC data preserved."""
    from sqlalchemy import text, inspect

    print("\nSOFT ROLLBACK: Clearing uuid values for customer_id=1 (SaaS)")
    with db.engine.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(text(
                "UPDATE customers SET uuid = NULL, vertical = NULL WHERE customer_id = 1"
            ))
            inspector = inspect(db.engine)
            tables = [
                'accounts', 'products', 'users', 'customer_configs',
                'kpi_uploads', 'health_trends', 'kpi_time_series',
                'kpi_reference_ranges', 'playbook_triggers',
                'playbook_executions', 'playbook_reports',
                'feature_toggles', 'query_audits', 'activity_logs',
                'customer_workflow_configs', 'account_notes',
                'account_snapshots',
            ]
            for table in tables:
                try:
                    columns = [col['name'] for col in inspector.get_columns(table)]
                    set_clauses = []
                    for col in ['uuid', 'customer_uuid', 'account_uuid', 'upload_uuid', 'kpi_uuid', 'product_uuid']:
                        if col in columns:
                            set_clauses.append(f'{col} = NULL')
                    if set_clauses:
                        conn.execute(text(
                            f"UPDATE {table} SET {', '.join(set_clauses)} WHERE customer_id = 1"
                        ))
                except Exception:
                    pass

            # KPIs via accounts join
            try:
                columns = [col['name'] for col in inspector.get_columns('kpis')]
                set_clauses = []
                for col in ['uuid', 'account_uuid', 'upload_uuid', 'product_uuid']:
                    if col in columns:
                        set_clauses.append(f'{col} = NULL')
                if set_clauses:
                    conn.execute(text(
                        f"UPDATE kpis SET {', '.join(set_clauses)} WHERE account_id IN "
                        f"(SELECT account_id FROM accounts WHERE customer_id = 1)"
                    ))
            except Exception:
                pass

            trans.commit()
            print("SaaS rollback complete. DC data preserved.")
        except Exception as e:
            trans.rollback()
            print(f"SaaS rollback failed: {e}")


def run_full_phase2(app, db):
    """Run Phase 2: SaaS backfill + combined validation."""

    print("\n" + "=" * 70)
    print("  CS PULSE - UUID MIGRATION PHASE 2")
    print("  Target: customer_id=1 (SaaS)")
    print("  Prerequisite: Phase 1 (DC customer_id=9) must be complete")
    print("=" * 70)

    start = time.time()

    # ---- Phase 2a: Backfill SaaS ----
    print("\n" + "-" * 70)
    print("  PHASE 2a: Backfill UUIDs for customer_id=1 (SaaS)")
    print("-" * 70)
    try:
        result_2a = run_phase2a(db)
        if 'error' in result_2a:
            print(f"\n  PHASE 2a FAILED: {result_2a['error']}")
            print("  Auto-rolling back SaaS data...")
            soft_rollback_saas(db)
            return False
        print(f"\n  Phase 2a complete: {result_2a}")
    except Exception as e:
        print(f"\n  PHASE 2a FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("  Auto-rolling back SaaS data...")
        soft_rollback_saas(db)
        return False

    # ---- Phase 2b: Validate ALL ----
    print("\n" + "-" * 70)
    print("  PHASE 2b: Validate ALL Customers (DC + SaaS)")
    print("-" * 70)
    try:
        validation = run_phase2b(db)
        print(f"\n  Validation: {validation.summary()}")

        if not validation.all_passed:
            print("\n  VALIDATION FAILED - Auto-rolling back SaaS data...")
            soft_rollback_saas(db)
            print("  SaaS rollback complete. DC data preserved.")
            return False
    except Exception as e:
        print(f"\n  PHASE 2b FAILED: {e}")
        print("  Auto-rolling back SaaS data...")
        soft_rollback_saas(db)
        return False

    elapsed = time.time() - start
    print("\n" + "=" * 70)
    print(f"  PHASE 2 COMPLETE - ALL CHECKS PASSED ({elapsed:.1f}s)")
    print("=" * 70)
    print("\n  Both verticals now have UUIDs:")
    print("    customer_id=1 (SaaS): saas_cust_...")
    print("    customer_id=9 (DC):   dc_cust_...")
    print("\n  Dual-write is active for new registrations and uploads.")
    print("  Next steps: Phase 3 (migrate API layers from int to UUID)")
    return True


if __name__ == '__main__':
    from app_v3_minimal import app, db as app_db

    is_dry_run = '--dry-run' in sys.argv
    is_rollback = '--rollback-saas' in sys.argv

    with app.app_context():
        if is_rollback:
            soft_rollback_saas(app_db)
        elif is_dry_run:
            print("DRY RUN: Validating current state...")
            validation = run_phase2b(app_db)
            print(f"\nResult: {validation.summary()}")
        else:
            success = run_full_phase2(app, app_db)
            sys.exit(0 if success else 1)
