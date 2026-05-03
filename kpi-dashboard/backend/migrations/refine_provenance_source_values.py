#!/usr/bin/env python3
"""
Migration: Refine context_nodes.source vocabulary
==================================================

Refines the ``source`` column on ``context_nodes`` from the original 2-value
vocabulary {customer, system} to a 3-value vocabulary {observed, synthetic,
inferred}. Required by the Wizard B predictive-quality roadmap (Tier 1 #1):
without separating "synthetic" (Wizard A arc-template fabrications) from
"inferred" (LLM/runtime detection over real signals), Wizard B's correlation
fitting cannot exclude its own self-reinforcing evidence.

Backfill rules:
  customer                                                        → observed
  system  AND  node_subtype = 'arc_detection'                     → synthetic
  system  AND  source_platform IN ('arc_edge_generator',
                                   'arc_decision_generator',
                                   'wizard_a')                    → synthetic
  system  AND  properties->>'triggered_by' = 'wizard_a'           → synthetic
  system  (everything else: signal_analyst, urgent_scanner,
            push_intelligence, signal_engine, playbook_lifecycle) → inferred

The default for new rows is changed from 'customer' to 'observed'.

Companion: also adds a ``source`` column to ``context_edges`` and backfills
from ``source_platform``. Wizard A edges (source_platform='wizard_a') get
'synthetic'; LLM-enriched edges (source_platform='llm_enrichment') get
'inferred'; everything else (CSV imports) gets 'observed'.

Usage:
    python -m migrations.refine_provenance_source_values

Rollback (down):
    python -m migrations.refine_provenance_source_values --rollback
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()
        trx = conn.begin()
        try:
            # ── 1. Backfill context_nodes.source ─────────────────────────
            print("\n📋 Backfilling context_nodes.source ...")

            res = conn.execute(db.text(
                "UPDATE context_nodes SET source = 'observed' "
                "WHERE source = 'customer'"
            ))
            print(f"  ✅ customer → observed: {res.rowcount} rows")

            res = conn.execute(db.text("""
                UPDATE context_nodes SET source = 'synthetic'
                WHERE source = 'system'
                  AND (
                       node_subtype = 'arc_detection'
                    OR source_platform IN (
                         'arc_edge_generator',
                         'arc_decision_generator',
                         'wizard_a'
                       )
                    OR (properties::jsonb -> 'triggered_by') = '"wizard_a"'::jsonb
                  )
            """))
            print(f"  ✅ system → synthetic (Wizard A): {res.rowcount} rows")

            res = conn.execute(db.text(
                "UPDATE context_nodes SET source = 'inferred' "
                "WHERE source = 'system'"
            ))
            print(f"  ✅ system → inferred (runtime detection): {res.rowcount} rows")

            # ── 2. Update default for new rows ───────────────────────────
            conn.execute(db.text(
                "ALTER TABLE context_nodes "
                "ALTER COLUMN source SET DEFAULT 'observed'"
            ))
            print("  ✅ Updated context_nodes.source DEFAULT → 'observed'")

            # ── 3. Add source to context_edges ───────────────────────────
            print("\n📋 Adding context_edges.source ...")
            conn.execute(db.text("""
                ALTER TABLE context_edges
                ADD COLUMN IF NOT EXISTS source VARCHAR(20)
                NOT NULL DEFAULT 'observed'
            """))
            print("  ✅ Added column: context_edges.source")

            # ── 4. Backfill context_edges.source from source_platform ────
            res = conn.execute(db.text("""
                UPDATE context_edges SET source = 'synthetic'
                WHERE source_platform IN (
                    'wizard_a', 'arc_edge_generator', 'arc_decision_generator'
                )
            """))
            print(f"  ✅ source_platform=wizard_a/arc_* → synthetic: {res.rowcount} rows")

            res = conn.execute(db.text("""
                UPDATE context_edges SET source = 'inferred'
                WHERE source_platform IN ('llm_enrichment', 'llm_inference')
            """))
            print(f"  ✅ source_platform=llm_* → inferred: {res.rowcount} rows")

            # Everything else stays 'observed' (CSV imports, default)

            # ── 5. Index for source filtering on edges ───────────────────
            conn.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_ctx_edge_source "
                "ON context_edges (source)"
            ))
            print("  ✅ Created index: idx_ctx_edge_source")

            trx.commit()

            # ── 6. Report final distribution ─────────────────────────────
            print("\n📊 Final distribution:")
            for tbl in ('context_nodes', 'context_edges'):
                rows = conn.execute(db.text(
                    f"SELECT source, COUNT(*) FROM {tbl} GROUP BY source ORDER BY source"
                )).fetchall()
                print(f"  {tbl}:")
                for src, cnt in rows:
                    print(f"    {src:>10s}: {cnt:>6d}")

            print("\n✅ Migration complete.\n")

        except Exception as e:
            trx.rollback()
            print(f"\n❌ Migration failed: {e}")
            raise
        finally:
            conn.close()


def rollback():
    """Rollback to the 2-value vocabulary.

    Note: this is a one-way mapping — ``synthetic`` and ``inferred`` both
    map back to ``system``. The distinction will be lost.
    """
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()
        trx = conn.begin()
        try:
            print("\n📋 Rolling back context_nodes.source ...")
            res = conn.execute(db.text(
                "UPDATE context_nodes SET source = 'customer' "
                "WHERE source = 'observed'"
            ))
            print(f"  ✅ observed → customer: {res.rowcount} rows")
            res = conn.execute(db.text(
                "UPDATE context_nodes SET source = 'system' "
                "WHERE source IN ('synthetic', 'inferred')"
            ))
            print(f"  ✅ synthetic/inferred → system: {res.rowcount} rows")

            conn.execute(db.text(
                "ALTER TABLE context_nodes "
                "ALTER COLUMN source SET DEFAULT 'customer'"
            ))
            print("  ✅ Reverted DEFAULT → 'customer'")

            print("\n📋 Dropping context_edges.source ...")
            conn.execute(db.text("DROP INDEX IF EXISTS idx_ctx_edge_source"))
            conn.execute(db.text(
                "ALTER TABLE context_edges DROP COLUMN IF EXISTS source"
            ))
            print("  ✅ Dropped column: context_edges.source")

            trx.commit()
            print("\n✅ Rollback complete.\n")

        except Exception as e:
            trx.rollback()
            print(f"\n❌ Rollback failed: {e}")
            raise
        finally:
            conn.close()


if __name__ == '__main__':
    if '--rollback' in sys.argv:
        rollback()
    else:
        run_migration()
