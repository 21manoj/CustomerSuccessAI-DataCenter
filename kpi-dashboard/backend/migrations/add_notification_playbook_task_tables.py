#!/usr/bin/env python3
"""
Migration: Add notifications and playbook_tasks tables
=======================================================

Creates two new tables for the Actions Pipeline Push infrastructure:
  - notifications     : push notification records (signal insights, urgent alerts, playbook triggers)
  - playbook_tasks    : system-triggered CSM task queue (queued by wizard_a / health thresholds)

Usage:
    python -m migrations.add_notification_playbook_task_tables

Rollback (down):
    python -m migrations.add_notification_playbook_task_tables --rollback
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Create notifications and playbook_tasks tables."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()

        # ── notifications table ──
        try:
            conn.execute(db.text("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id          SERIAL PRIMARY KEY,
                    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
                    account_id  INTEGER REFERENCES accounts(account_id),
                    type        VARCHAR(50) NOT NULL,
                    priority    VARCHAR(20) DEFAULT 'normal',
                    payload     JSONB DEFAULT '{}',
                    created_at  TIMESTAMP DEFAULT NOW(),
                    read_at     TIMESTAMP
                )
            """))
            conn.commit()
            print("  ✅ Created table: notifications")
        except Exception as e:
            conn.rollback()
            if 'already exists' in str(e).lower():
                print("  ⏭️  Table notifications already exists, skipping")
            else:
                print(f"  ⚠️  Error creating notifications: {e}")
                raise

        # ── notifications indexes ──
        indexes = [
            ("idx_notification_customer_unread",   "notifications", "customer_id, read_at"),
            ("idx_notification_customer_type",      "notifications", "customer_id, type"),
            ("idx_notification_priority_created",   "notifications", "priority, created_at"),
            ("idx_notification_account",            "notifications", "account_id"),
        ]
        for idx_name, tbl, cols in indexes:
            try:
                conn.execute(db.text(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl} ({cols})"
                ))
                conn.commit()
                print(f"  ✅ Created index: {idx_name}")
            except Exception as e:
                conn.rollback()
                print(f"  ⚠️  Index {idx_name}: {e}")

        # ── playbook_tasks table ──
        try:
            conn.execute(db.text("""
                CREATE TABLE IF NOT EXISTS playbook_tasks (
                    id             SERIAL PRIMARY KEY,
                    customer_id    INTEGER NOT NULL REFERENCES customers(customer_id),
                    account_id     INTEGER NOT NULL REFERENCES accounts(account_id),
                    playbook_id    VARCHAR(20) NOT NULL,
                    trigger_reason VARCHAR(200),
                    trigger_source VARCHAR(50),
                    assigned_csm   VARCHAR(100),
                    due_date       TIMESTAMP,
                    status         VARCHAR(20) DEFAULT 'pending',
                    created_at     TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.commit()
            print("  ✅ Created table: playbook_tasks")
        except Exception as e:
            conn.rollback()
            if 'already exists' in str(e).lower():
                print("  ⏭️  Table playbook_tasks already exists, skipping")
            else:
                print(f"  ⚠️  Error creating playbook_tasks: {e}")
                raise

        # ── playbook_tasks indexes ──
        task_indexes = [
            ("idx_playbook_task_customer_status", "playbook_tasks", "customer_id, status"),
            ("idx_playbook_task_account_status",  "playbook_tasks", "account_id, status"),
            ("idx_playbook_task_playbook_id",     "playbook_tasks", "playbook_id"),
        ]
        for idx_name, tbl, cols in task_indexes:
            try:
                conn.execute(db.text(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl} ({cols})"
                ))
                conn.commit()
                print(f"  ✅ Created index: {idx_name}")
            except Exception as e:
                conn.rollback()
                print(f"  ⚠️  Index {idx_name}: {e}")

        conn.close()
        print("\n✅ Migration complete: notifications + playbook_tasks tables created")


def rollback():
    """Drop notifications and playbook_tasks tables (destructive — use with care)."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()

        for tbl in ('playbook_tasks', 'notifications'):
            try:
                conn.execute(db.text(f"DROP TABLE IF EXISTS {tbl} CASCADE"))
                conn.commit()
                print(f"  ✅ Dropped table: {tbl}")
            except Exception as e:
                conn.rollback()
                print(f"  ⚠️  Error dropping {tbl}: {e}")

        conn.close()
        print("\n✅ Rollback complete: notifications + playbook_tasks tables dropped")


if __name__ == '__main__':
    if '--rollback' in sys.argv:
        rollback()
    else:
        run_migration()
