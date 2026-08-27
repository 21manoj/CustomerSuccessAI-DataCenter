#!/usr/bin/env python3
"""
Migration: Add data_origin column to customers
================================================

WS-2 2a. Adds ``data_origin`` to ``customers`` to distinguish real customer
tenants from tenants whose data was generated rather than asserted by a
customer:
  - NULL (default)             — real customer data (every existing row)
  - 'synthetic_eval_profile'   — load-driver/eval_profile-generated tenant
                                  (see load-driver/eval_profile/ground_truth.py,
                                  which forward-declared this exact value)

One column on customers rather than on context_nodes/context_edges: a
tenant's data_origin doesn't vary row-by-row the way an individual node's
observed/inferred/synthetic provenance (utils/provenance.py) does — an
eval-profile tenant's entire dataset shares one origin, matching how
ground_truth.json carries this as a single top-level field for the whole
tenant, not per-event.

Usage:
    python -m migrations.add_data_origin_to_customers

Rollback (down):
    python -m migrations.add_data_origin_to_customers --rollback
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Add data_origin column to customers table."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()

        try:
            conn.execute(db.text("""
                ALTER TABLE customers
                ADD COLUMN IF NOT EXISTS data_origin VARCHAR(30)
            """))
            conn.commit()
            print("  ✅ Added column: customers.data_origin (VARCHAR(30), NULL default)")
        except Exception as e:
            conn.rollback()
            if 'already exists' in str(e).lower():
                print("  ⏭️  Column customers.data_origin already exists, skipping")
            else:
                print(f"  ⚠️  Error adding data_origin column: {e}")
                raise

        conn.close()
        print("\n✅ Migration complete: customers.data_origin column added")


def rollback():
    """Drop data_origin column from customers (destructive — use with care)."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()

        try:
            conn.execute(db.text(
                "ALTER TABLE customers DROP COLUMN IF EXISTS data_origin"
            ))
            conn.commit()
            print("  ✅ Dropped column: customers.data_origin")
        except Exception as e:
            conn.rollback()
            print(f"  ⚠️  Error dropping data_origin column: {e}")

        conn.close()
        print("\n✅ Rollback complete: customers.data_origin column removed")


if __name__ == '__main__':
    if '--rollback' in sys.argv:
        rollback()
    else:
        run_migration()
