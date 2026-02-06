#!/usr/bin/env python3
"""
Phase 1 Orchestrator: UUID Migration for customer_id=9 (Data Center)

Runs all phases in order with automatic rollback on failure:
  1a. Add uuid + vertical columns (DDL)
  1b. Backfill customer_id=9 data
  1c. Validate the migration
  1d. (Auto-rollback if 1c fails)

Usage:
  cd kpi-dashboard/backend
  python uuid_migration/run_phase1.py

  # Dry run (validate only, no changes):
  python uuid_migration/run_phase1.py --dry-run

  # Rollback only:
  python uuid_migration/run_phase1.py --rollback
  python uuid_migration/run_phase1.py --rollback --hard
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Phase imports
from uuid_migration.phase1a_add_uuid_columns import run as run_phase1a
from uuid_migration.phase1b_backfill_dc import run as run_phase1b
from uuid_migration.phase1c_validate import run as run_phase1c
from uuid_migration.phase1d_rollback import soft_rollback, hard_rollback


def run_full_migration(app, db):
    """Run the complete Phase 1 migration with auto-rollback."""

    print("\n" + "=" * 70)
    print("  CS PULSE - UUID MIGRATION PHASE 1")
    print("  Target: customer_id=9 (Data Center)")
    print("=" * 70)

    start = time.time()

    # ---- Phase 1a: Add columns ----
    print("\n" + "-" * 70)
    print("  PHASE 1a: Add UUID + Vertical Columns")
    print("-" * 70)
    try:
        result_1a = run_phase1a(db)
        if result_1a.get('errors'):
            print(f"\n  PHASE 1a ERRORS: {result_1a['errors']}")
            print("  ABORTING - Cannot proceed without required tables")
            return False
        print(f"\n  Phase 1a complete: {result_1a['added']} added, {result_1a['skipped']} skipped")
    except Exception as e:
        print(f"\n  PHASE 1a FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ---- Phase 1b: Backfill ----
    print("\n" + "-" * 70)
    print("  PHASE 1b: Backfill UUIDs for customer_id=9")
    print("-" * 70)
    try:
        result_1b = run_phase1b(db)
        if 'error' in result_1b:
            print(f"\n  PHASE 1b FAILED: {result_1b['error']}")
            print("  Auto-rolling back...")
            soft_rollback(db)
            return False
        print(f"\n  Phase 1b complete: {result_1b}")
    except Exception as e:
        print(f"\n  PHASE 1b FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("  Auto-rolling back...")
        soft_rollback(db)
        return False

    # ---- Phase 1c: Validate ----
    print("\n" + "-" * 70)
    print("  PHASE 1c: Validate Migration")
    print("-" * 70)
    try:
        validation = run_phase1c(db)
        print(f"\n  Validation: {validation.summary()}")

        if not validation.all_passed:
            print("\n  VALIDATION FAILED - Auto-rolling back...")
            failed_checks = [c for c in validation.checks if not c['passed']]
            for c in failed_checks:
                print(f"    FAIL: {c['name']} -- {c['detail']}")
            soft_rollback(db)
            print("  Rollback complete. Fix issues and re-run.")
            return False
    except Exception as e:
        print(f"\n  PHASE 1c FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("  Auto-rolling back...")
        soft_rollback(db)
        return False

    # ---- Success ----
    elapsed = time.time() - start
    print("\n" + "=" * 70)
    print(f"  PHASE 1 COMPLETE - ALL CHECKS PASSED ({elapsed:.1f}s)")
    print("=" * 70)
    print("\n  Summary:")
    print(f"    Columns added: {result_1a['added']}")
    print(f"    Records backfilled: {sum(v for v in result_1b.values() if isinstance(v, int))}")
    print(f"    Validation checks: {validation.summary()}")
    print("\n  Next steps:")
    print("    - Review the migration output above")
    print("    - If satisfied, proceed to Phase 2 (dual-write for new registrations)")
    print("    - To rollback: python migrations/uuid_migration/run_phase1.py --rollback")
    print()
    return True


def run_dry_run(app, db):
    """Dry run: only validate current state without making changes."""
    print("\n" + "=" * 70)
    print("  DRY RUN - Validate Only (no changes)")
    print("=" * 70)
    try:
        validation = run_phase1c(db)
        print(f"\n  Result: {validation.summary()}")
    except Exception as e:
        print(f"  Validation error: {e}")


if __name__ == '__main__':
    from app_v3_minimal import app, db as app_db

    is_dry_run = '--dry-run' in sys.argv
    is_rollback = '--rollback' in sys.argv
    is_hard = '--hard' in sys.argv

    with app.app_context():
        if is_rollback:
            if is_hard:
                print("HARD ROLLBACK requested")
                confirm = input("Type 'yes' to confirm: ")
                if confirm.strip().lower() == 'yes':
                    hard_rollback(app_db)
                else:
                    print("Aborted.")
            else:
                soft_rollback(app_db)
        elif is_dry_run:
            run_dry_run(app, app_db)
        else:
            success = run_full_migration(app, app_db)
            sys.exit(0 if success else 1)
