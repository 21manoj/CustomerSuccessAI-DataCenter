#!/usr/bin/env python3
"""
Migration: Align wizard_learnings with models.WizardLearning
============================================================

Adds nullable customer_id (FK customers), analysis_report, index on customer_id,
and replaces a UNIQUE(version)-only constraint with UNIQUE(customer_id, version).

Idempotent for columns and index; safe to re-run if composite unique already exists.

Usage (inside cs-pulse container):
    python3 /app/backend/migrations/add_customer_id_to_wizard_learnings.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    from sqlalchemy import text

    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        with db.engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE wizard_learnings "
                    "ADD COLUMN IF NOT EXISTS customer_id INTEGER REFERENCES customers(customer_id)"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE wizard_learnings "
                    "ADD COLUMN IF NOT EXISTS analysis_report TEXT"
                )
            )
            print("  OK: columns customer_id, analysis_report")

            res = conn.execute(
                text(
                    """
                    SELECT c.conname, array_agg(a.attname ORDER BY u.ord)
                    FROM pg_constraint c
                    JOIN pg_class t ON c.conrelid = t.oid
                    JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS u(attnum, ord) ON true
                    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = u.attnum
                    WHERE t.relname = 'wizard_learnings' AND c.contype = 'u'
                    GROUP BY c.conname
                    """
                )
            )
            for conname, colnames in res.fetchall():
                cols = list(colnames) if colnames is not None else []
                if cols == ["version"]:
                    conn.execute(text(f'ALTER TABLE wizard_learnings DROP CONSTRAINT "{conname}"'))
                    print(f"  OK: dropped unique(version)-only constraint: {conname}")

            try:
                conn.execute(
                    text(
                        "ALTER TABLE wizard_learnings ADD CONSTRAINT uq_wizard_learning_customer_version "
                        "UNIQUE (customer_id, version)"
                    )
                )
                print("  OK: UNIQUE (customer_id, version)")
            except Exception as e:
                err = str(e).lower()
                if (
                    "already exists" in err
                    or "duplicate" in err
                    or "uq_wizard_learning" in err
                ):
                    print(f"  skip: composite unique — {e}")
                else:
                    raise

            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_wizard_learnings_customer_id "
                    "ON wizard_learnings (customer_id)"
                )
            )
            print("  OK: index ix_wizard_learnings_customer_id")

        print("\nMigration complete: wizard_learnings.customer_id")


if __name__ == "__main__":
    run_migration()
