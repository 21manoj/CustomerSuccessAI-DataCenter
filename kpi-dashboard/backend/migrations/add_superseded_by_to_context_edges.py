#!/usr/bin/env python3
"""
Migration: Add superseded_by column to context_edges
======================================================

WS-2 2g. Adds ``superseded_by`` to ``context_edges`` so a stronger-tier (or
higher-priority same-tier) edge arriving on a triple that already has a live
edge can retire the weaker one without deleting it:

  - NULL (default)  — this edge is live (every existing row, no backfill)
  - <edge_id>        — the edge_id of the edge that superseded this one;
                        the row stays in the table for audit but drops out
                        of causal-chain traversal and other read surfaces
                        that filter on `superseded_by IS NULL`.

Plain typed integer column, no FK constraint — matches how
``customers.data_origin`` was added (see
migrations/add_data_origin_to_customers.py) rather than a `properties` JSON
key, because every edge-reading function needs to filter
`WHERE superseded_by IS NULL` on the hot path, which needs to be indexable.

Forward-only: only new writes going through the fixed upsert_edge() (see
utils/supersession.py) participate. No backfill of existing edges.

Usage:
    python -m migrations.add_superseded_by_to_context_edges

Rollback (down):
    python -m migrations.add_superseded_by_to_context_edges --rollback
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Add superseded_by column (+ index) to context_edges table."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()

        # ── Add superseded_by column ──
        try:
            conn.execute(db.text("""
                ALTER TABLE context_edges
                ADD COLUMN IF NOT EXISTS superseded_by INTEGER
            """))
            conn.commit()
            print("  ✅ Added column: context_edges.superseded_by (INTEGER, NULL default)")
        except Exception as e:
            conn.rollback()
            if 'already exists' in str(e).lower():
                print("  ⏭️  Column context_edges.superseded_by already exists, skipping")
            else:
                print(f"  ⚠️  Error adding superseded_by column: {e}")
                raise

        # ── Index for the WHERE superseded_by IS NULL hot-path predicate ──
        try:
            conn.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_ctx_edge_superseded_by "
                "ON context_edges (superseded_by)"
            ))
            conn.commit()
            print("  ✅ Created index: idx_ctx_edge_superseded_by")
        except Exception as e:
            conn.rollback()
            print(f"  ⚠️  Index idx_ctx_edge_superseded_by: {e}")

        conn.close()
        print("\n✅ Migration complete: context_edges.superseded_by column added")


def rollback():
    """Drop superseded_by column from context_edges (destructive — use with care)."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()

        try:
            conn.execute(db.text(
                "DROP INDEX IF EXISTS idx_ctx_edge_superseded_by"
            ))
            conn.commit()
            print("  ✅ Dropped index: idx_ctx_edge_superseded_by")
        except Exception as e:
            conn.rollback()
            print(f"  ⚠️  Error dropping index: {e}")

        try:
            conn.execute(db.text(
                "ALTER TABLE context_edges DROP COLUMN IF EXISTS superseded_by"
            ))
            conn.commit()
            print("  ✅ Dropped column: context_edges.superseded_by")
        except Exception as e:
            conn.rollback()
            print(f"  ⚠️  Error dropping superseded_by column: {e}")

        conn.close()
        print("\n✅ Rollback complete: context_edges.superseded_by column removed")


if __name__ == '__main__':
    if '--rollback' in sys.argv:
        rollback()
    else:
        run_migration()
