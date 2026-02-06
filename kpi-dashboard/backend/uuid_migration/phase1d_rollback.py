#!/usr/bin/env python3
"""
Phase 1d: Rollback UUID Migration

Two rollback modes:
  1. SOFT rollback (default): Clear uuid/vertical VALUES for customer_id=9 only.
     Columns remain. Safe to re-run backfill after fixing issues.

  2. HARD rollback: Drop all uuid/vertical COLUMNS from all tables.
     Full revert to pre-migration schema.

Usage:
  python phase1d_rollback.py          # Soft rollback (clear values only)
  python phase1d_rollback.py --hard   # Hard rollback (drop columns)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text, inspect

TARGET_CUSTOMER_ID = 9


def soft_rollback(db):
    """
    Clear uuid/vertical values for customer_id=9 only.
    Columns remain in place. Other customers unaffected.
    """
    print("\nSOFT ROLLBACK: Clearing uuid values for customer_id=9")

    with db.engine.connect() as conn:
        trans = conn.begin()
        try:
            # Customer
            conn.execute(text(
                "UPDATE customers SET uuid = NULL, vertical = NULL WHERE customer_id = :cid"
            ), {'cid': TARGET_CUSTOMER_ID})
            print("  Cleared customers")

            # Direct child tables with customer_id
            tables_with_customer_fk = [
                'accounts', 'products', 'users', 'customer_configs',
                'kpi_uploads', 'health_trends', 'kpi_time_series',
                'kpi_reference_ranges', 'playbook_triggers',
                'playbook_executions', 'playbook_reports',
                'feature_toggles', 'query_audits', 'activity_logs',
                'customer_workflow_configs', 'account_notes',
                'account_snapshots',
            ]

            # Build the SET clause dynamically based on which columns exist
            inspector = inspect(db.engine)
            for table in tables_with_customer_fk:
                try:
                    columns = [col['name'] for col in inspector.get_columns(table)]
                    set_clauses = []
                    if 'uuid' in columns:
                        set_clauses.append('uuid = NULL')
                    if 'customer_uuid' in columns:
                        set_clauses.append('customer_uuid = NULL')
                    if 'account_uuid' in columns:
                        set_clauses.append('account_uuid = NULL')
                    if 'upload_uuid' in columns:
                        set_clauses.append('upload_uuid = NULL')
                    if 'kpi_uuid' in columns:
                        set_clauses.append('kpi_uuid = NULL')
                    if 'product_uuid' in columns:
                        set_clauses.append('product_uuid = NULL')

                    if set_clauses:
                        set_sql = ', '.join(set_clauses)
                        count = conn.execute(text(
                            f"UPDATE {table} SET {set_sql} WHERE customer_id = :cid"
                        ), {'cid': TARGET_CUSTOMER_ID}).rowcount
                        print(f"  Cleared {table} ({count} rows)")
                except Exception as e:
                    print(f"  WARN: Could not clear {table}: {e}")

            # KPIs (joined through accounts)
            try:
                columns = [col['name'] for col in inspector.get_columns('kpis')]
                set_clauses = []
                for col in ['uuid', 'account_uuid', 'upload_uuid', 'product_uuid']:
                    if col in columns:
                        set_clauses.append(f'{col} = NULL')
                if set_clauses:
                    set_sql = ', '.join(set_clauses)
                    count = conn.execute(text(
                        f"UPDATE kpis SET {set_sql} WHERE account_id IN "
                        f"(SELECT account_id FROM accounts WHERE customer_id = :cid)"
                    ), {'cid': TARGET_CUSTOMER_ID}).rowcount
                    print(f"  Cleared kpis ({count} rows)")
            except Exception as e:
                print(f"  WARN: Could not clear kpis: {e}")

            trans.commit()
            print("\nSOFT ROLLBACK COMPLETE - Values cleared, columns preserved")

        except Exception as e:
            trans.rollback()
            print(f"\nROLLBACK FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

    return True


def hard_rollback(db):
    """
    Drop all uuid/vertical columns from all tables.
    Full revert to pre-migration schema.
    """
    print("\nHARD ROLLBACK: Dropping uuid/vertical columns from all tables")
    print("WARNING: This removes ALL uuid data for ALL customers!\n")

    columns_to_drop = {
        'customers': ['uuid', 'vertical'],
        'accounts': ['uuid', 'customer_uuid'],
        'products': ['uuid', 'customer_uuid', 'account_uuid'],
        'users': ['uuid', 'customer_uuid'],
        'customer_configs': ['uuid', 'customer_uuid'],
        'kpi_uploads': ['uuid', 'customer_uuid', 'account_uuid'],
        'kpis': ['uuid', 'account_uuid', 'upload_uuid', 'product_uuid'],
        'health_trends': ['uuid', 'account_uuid', 'customer_uuid'],
        'kpi_time_series': ['uuid', 'kpi_uuid', 'account_uuid', 'customer_uuid'],
        'kpi_reference_ranges': ['uuid', 'customer_uuid'],
        'playbook_triggers': ['uuid', 'customer_uuid'],
        'playbook_executions': ['uuid', 'customer_uuid', 'account_uuid'],
        'playbook_reports': ['uuid', 'customer_uuid', 'account_uuid'],
        'feature_toggles': ['uuid', 'customer_uuid'],
        'query_audits': ['uuid', 'customer_uuid'],
        'activity_logs': ['uuid', 'customer_uuid'],
        'customer_workflow_configs': ['uuid', 'customer_uuid'],
        'account_notes': ['uuid', 'account_uuid', 'customer_uuid'],
        'account_snapshots': ['uuid', 'account_uuid', 'customer_uuid'],
    }

    dropped = 0
    skipped = 0

    with db.engine.connect() as conn:
        inspector = inspect(db.engine)

        for table, cols in columns_to_drop.items():
            try:
                existing_cols = [c['name'] for c in inspector.get_columns(table)]
                for col in cols:
                    if col in existing_cols:
                        conn.execute(text(f'ALTER TABLE {table} DROP COLUMN {col}'))
                        print(f"  DROP {table}.{col}")
                        dropped += 1
                    else:
                        skipped += 1
            except Exception as e:
                print(f"  ERROR dropping columns from {table}: {e}")

        conn.commit()

    print(f"\nHARD ROLLBACK COMPLETE - {dropped} columns dropped, {skipped} already absent")
    return True


if __name__ == '__main__':
    from app_v3_minimal import app, db as app_db

    hard = '--hard' in sys.argv

    print("=" * 60)
    if hard:
        print("Phase 1d: HARD Rollback (drop columns)")
        print("=" * 60)
        confirm = input("Type 'yes' to confirm HARD rollback (drops ALL uuid columns): ")
        if confirm.strip().lower() != 'yes':
            print("Aborted.")
            sys.exit(1)
    else:
        print(f"Phase 1d: SOFT Rollback (clear values for customer_id={TARGET_CUSTOMER_ID})")
        print("=" * 60)

    with app.app_context():
        if hard:
            success = hard_rollback(app_db)
        else:
            success = soft_rollback(app_db)

    sys.exit(0 if success else 1)
