#!/usr/bin/env python3
"""
Phase 1a: Add UUID + Vertical Columns to All Tables

This is a NON-DESTRUCTIVE migration. It only ADDs new columns.
Existing integer PKs and FKs are completely untouched.

Tables affected (18 total):
  - customers: uuid, vertical
  - accounts: uuid, customer_uuid
  - products: uuid, customer_uuid, account_uuid
  - users: uuid, customer_uuid
  - customer_configs: uuid, customer_uuid
  - kpi_uploads: uuid, customer_uuid, account_uuid
  - kpis: uuid, account_uuid, upload_uuid, product_uuid
  - health_trends: uuid, account_uuid, customer_uuid
  - kpi_time_series: uuid, kpi_uuid, account_uuid, customer_uuid
  - kpi_reference_ranges: uuid, customer_uuid
  - playbook_triggers: uuid, customer_uuid
  - playbook_executions: uuid, customer_uuid, account_uuid
  - playbook_reports: uuid, customer_uuid, account_uuid
  - feature_toggles: uuid, customer_uuid
  - query_audits: uuid, customer_uuid
  - activity_logs: uuid, customer_uuid
  - customer_workflow_configs: uuid, customer_uuid
  - account_notes: uuid, account_uuid, customer_uuid
  - account_snapshots: uuid, account_uuid, customer_uuid

Rollback: phase1d_rollback.py drops these columns.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text, inspect


def column_exists(inspector, table_name, column_name):
    """Check if a column already exists in a table."""
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def table_exists(inspector, table_name):
    """Check if a table exists."""
    return table_name in inspector.get_table_names()


def add_column_if_not_exists(conn, inspector, table, column, col_type='VARCHAR(60)'):
    """Safely add a column only if it doesn't already exist."""
    if column_exists(inspector, table, column):
        print(f"  SKIP {table}.{column} (already exists)")
        return False
    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}'))
    print(f"  ADD  {table}.{column} ({col_type})")
    return True


def run(db):
    """
    Add uuid and vertical columns to all tables.

    Args:
        db: SQLAlchemy db instance (from extensions.py)

    Returns:
        dict with counts of columns added and skipped
    """
    added = 0
    skipped = 0
    errors = []

    with db.engine.connect() as conn:
        inspector = inspect(db.engine)

        # ---- customers ----
        if table_exists(inspector, 'customers'):
            print("\n[customers]")
            if add_column_if_not_exists(conn, inspector, 'customers', 'uuid'):
                added += 1
            else:
                skipped += 1
            if add_column_if_not_exists(conn, inspector, 'customers', 'vertical', 'VARCHAR(20)'):
                added += 1
            else:
                skipped += 1
        else:
            errors.append("Table 'customers' not found")

        # ---- accounts ----
        if table_exists(inspector, 'accounts'):
            print("\n[accounts]")
            for col in ['uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'accounts', col):
                    added += 1
                else:
                    skipped += 1
        else:
            errors.append("Table 'accounts' not found")

        # ---- products ----
        if table_exists(inspector, 'products'):
            print("\n[products]")
            for col in ['uuid', 'customer_uuid', 'account_uuid']:
                if add_column_if_not_exists(conn, inspector, 'products', col):
                    added += 1
                else:
                    skipped += 1
        else:
            errors.append("Table 'products' not found")

        # ---- users ----
        if table_exists(inspector, 'users'):
            print("\n[users]")
            for col in ['uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'users', col):
                    added += 1
                else:
                    skipped += 1
        else:
            errors.append("Table 'users' not found")

        # ---- customer_configs ----
        if table_exists(inspector, 'customer_configs'):
            print("\n[customer_configs]")
            for col in ['uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'customer_configs', col):
                    added += 1
                else:
                    skipped += 1

        # ---- kpi_uploads ----
        if table_exists(inspector, 'kpi_uploads'):
            print("\n[kpi_uploads]")
            for col in ['uuid', 'customer_uuid', 'account_uuid']:
                if add_column_if_not_exists(conn, inspector, 'kpi_uploads', col):
                    added += 1
                else:
                    skipped += 1

        # ---- kpis ----
        if table_exists(inspector, 'kpis'):
            print("\n[kpis]")
            for col in ['uuid', 'account_uuid', 'upload_uuid', 'product_uuid']:
                if add_column_if_not_exists(conn, inspector, 'kpis', col):
                    added += 1
                else:
                    skipped += 1

        # ---- health_trends ----
        if table_exists(inspector, 'health_trends'):
            print("\n[health_trends]")
            for col in ['uuid', 'account_uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'health_trends', col):
                    added += 1
                else:
                    skipped += 1

        # ---- kpi_time_series ----
        if table_exists(inspector, 'kpi_time_series'):
            print("\n[kpi_time_series]")
            for col in ['uuid', 'kpi_uuid', 'account_uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'kpi_time_series', col):
                    added += 1
                else:
                    skipped += 1

        # ---- kpi_reference_ranges ----
        if table_exists(inspector, 'kpi_reference_ranges'):
            print("\n[kpi_reference_ranges]")
            for col in ['uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'kpi_reference_ranges', col):
                    added += 1
                else:
                    skipped += 1

        # ---- playbook_triggers ----
        if table_exists(inspector, 'playbook_triggers'):
            print("\n[playbook_triggers]")
            for col in ['uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'playbook_triggers', col):
                    added += 1
                else:
                    skipped += 1

        # ---- playbook_executions ----
        if table_exists(inspector, 'playbook_executions'):
            print("\n[playbook_executions]")
            for col in ['uuid', 'customer_uuid', 'account_uuid']:
                if add_column_if_not_exists(conn, inspector, 'playbook_executions', col):
                    added += 1
                else:
                    skipped += 1

        # ---- playbook_reports ----
        if table_exists(inspector, 'playbook_reports'):
            print("\n[playbook_reports]")
            for col in ['uuid', 'customer_uuid', 'account_uuid']:
                if add_column_if_not_exists(conn, inspector, 'playbook_reports', col):
                    added += 1
                else:
                    skipped += 1

        # ---- feature_toggles ----
        if table_exists(inspector, 'feature_toggles'):
            print("\n[feature_toggles]")
            for col in ['uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'feature_toggles', col):
                    added += 1
                else:
                    skipped += 1

        # ---- query_audits ----
        if table_exists(inspector, 'query_audits'):
            print("\n[query_audits]")
            for col in ['uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'query_audits', col):
                    added += 1
                else:
                    skipped += 1

        # ---- activity_logs ----
        if table_exists(inspector, 'activity_logs'):
            print("\n[activity_logs]")
            for col in ['uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'activity_logs', col):
                    added += 1
                else:
                    skipped += 1

        # ---- customer_workflow_configs ----
        if table_exists(inspector, 'customer_workflow_configs'):
            print("\n[customer_workflow_configs]")
            for col in ['uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'customer_workflow_configs', col):
                    added += 1
                else:
                    skipped += 1

        # ---- account_notes ----
        if table_exists(inspector, 'account_notes'):
            print("\n[account_notes]")
            for col in ['uuid', 'account_uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'account_notes', col):
                    added += 1
                else:
                    skipped += 1

        # ---- account_snapshots ----
        if table_exists(inspector, 'account_snapshots'):
            print("\n[account_snapshots]")
            for col in ['uuid', 'account_uuid', 'customer_uuid']:
                if add_column_if_not_exists(conn, inspector, 'account_snapshots', col):
                    added += 1
                else:
                    skipped += 1

        conn.commit()

    return {'added': added, 'skipped': skipped, 'errors': errors}


if __name__ == '__main__':
    # Allow running standalone
    from app_v3_minimal import app, db as app_db
    print("=" * 60)
    print("Phase 1a: Adding UUID + Vertical Columns")
    print("=" * 60)
    with app.app_context():
        result = run(app_db)
    print(f"\nDone: {result['added']} columns added, {result['skipped']} skipped")
    if result['errors']:
        print(f"Errors: {result['errors']}")
