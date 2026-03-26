#!/usr/bin/env python3
"""
Migration: Add Arc Intelligence Engine fields to accounts table
===============================================================

Adds three new columns for Wizard A arc classification:
  - arc_type       (VARCHAR 50)  : story arc assigned to this account
                                   e.g. crisis_recovery, champion_loss, steady_performer
  - arc_phase      (VARCHAR 20)  : current arc phase — 'baseline' or 'intervention'
  - arc_confidence (FLOAT)       : classifier confidence score 0.0-1.0

These columns are populated by Wizard A (arc_classifier.py) each time
process_data() or ingest_context_graph_csvs() completes.

Usage:
    python -m migrations.add_arc_fields_to_accounts

Rollback:
    ALTER TABLE accounts DROP COLUMN IF EXISTS arc_type;
    ALTER TABLE accounts DROP COLUMN IF EXISTS arc_phase;
    ALTER TABLE accounts DROP COLUMN IF EXISTS arc_confidence;
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Add arc_type, arc_phase, arc_confidence columns to accounts table."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()

        columns_to_add = [
            ("arc_type",       "VARCHAR(50)"),
            ("arc_phase",      "VARCHAR(20)"),
            ("arc_confidence", "FLOAT"),
        ]

        for col_name, col_type in columns_to_add:
            try:
                conn.execute(db.text(
                    f"ALTER TABLE accounts ADD COLUMN {col_name} {col_type}"
                ))
                conn.commit()
                print(f"  Added column: accounts.{col_name} ({col_type})")
            except Exception as e:
                conn.rollback()
                if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                    print(f"  Column accounts.{col_name} already exists, skipping")
                else:
                    print(f"  Error adding {col_name}: {e}")

        conn.close()
        print("\nMigration complete: arc fields added to accounts table")


def rollback():
    """Remove arc columns from accounts table."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()
        for col_name in ('arc_type', 'arc_phase', 'arc_confidence'):
            try:
                conn.execute(db.text(
                    f"ALTER TABLE accounts DROP COLUMN IF EXISTS {col_name}"
                ))
                conn.commit()
                print(f"  Dropped column: accounts.{col_name}")
            except Exception as e:
                conn.rollback()
                print(f"  Error dropping {col_name}: {e}")
        conn.close()
        print("\nRollback complete: arc fields removed from accounts table")


if __name__ == '__main__':
    if '--rollback' in sys.argv:
        rollback()
    else:
        run_migration()
