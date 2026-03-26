#!/usr/bin/env python3
"""
Migration: Add source column to context_nodes
==============================================

Adds a ``source`` column to ``context_nodes`` to distinguish node origin:
  - 'customer' — CSV uploads via onboarding pipeline (default, covers all existing rows)
  - 'system'   — system-generated nodes (Wizard A, signal_analyst, urgent_scanner)

Usage:
    python -m migrations.add_source_to_context_nodes

Rollback (down):
    python -m migrations.add_source_to_context_nodes --rollback
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Add source column to context_nodes table."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()

        # ── Add source column ──
        try:
            conn.execute(db.text("""
                ALTER TABLE context_nodes
                ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'customer'
            """))
            conn.commit()
            print("  ✅ Added column: context_nodes.source (VARCHAR(20) DEFAULT 'customer')")
        except Exception as e:
            conn.rollback()
            if 'already exists' in str(e).lower():
                print("  ⏭️  Column context_nodes.source already exists, skipping")
            else:
                print(f"  ⚠️  Error adding source column: {e}")
                raise

        # ── Index for source filtering (system vs customer node queries) ──
        try:
            conn.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_ctx_node_source_origin "
                "ON context_nodes (account_id, source)"
            ))
            conn.commit()
            print("  ✅ Created index: idx_ctx_node_source_origin")
        except Exception as e:
            conn.rollback()
            print(f"  ⚠️  Index idx_ctx_node_source_origin: {e}")

        conn.close()
        print("\n✅ Migration complete: context_nodes.source column added")


def rollback():
    """Drop source column from context_nodes (destructive — use with care)."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()

        try:
            conn.execute(db.text(
                "DROP INDEX IF EXISTS idx_ctx_node_source_origin"
            ))
            conn.commit()
            print("  ✅ Dropped index: idx_ctx_node_source_origin")
        except Exception as e:
            conn.rollback()
            print(f"  ⚠️  Error dropping index: {e}")

        try:
            conn.execute(db.text(
                "ALTER TABLE context_nodes DROP COLUMN IF EXISTS source"
            ))
            conn.commit()
            print("  ✅ Dropped column: context_nodes.source")
        except Exception as e:
            conn.rollback()
            print(f"  ⚠️  Error dropping source column: {e}")

        conn.close()
        print("\n✅ Rollback complete: context_nodes.source column removed")


if __name__ == '__main__':
    if '--rollback' in sys.argv:
        rollback()
    else:
        run_migration()
