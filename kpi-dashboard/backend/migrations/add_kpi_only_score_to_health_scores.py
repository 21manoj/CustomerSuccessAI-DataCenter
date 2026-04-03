#!/usr/bin/env python3
"""
Migration: Add kpi_only_score and composite_score to health_scores table
=========================================================================

Adds two new columns implementing the score separation principle
(spec_recency_signal_dna_scoring.md §1a — Absolute Separation, IMMUTABLE):

  kpi_only_score  NUMERIC(5,2) — pure KPI-weighted score.
                                  Backfilled from health_score (they are equal today).
                                  NRR engine and churn models MUST read this column.
                                  NEVER populate from signals or composite.

  composite_score NUMERIC(5,2) — signal-blended score (NULL until Signal-DNA ships).
                                  Populated only when FEATURE_UNIFIED_SCORING is enabled.

When Signal-DNA unified scoring is enabled in the future:
  - health_score  → continues to hold the composite blend (for UI timeline)
  - kpi_only_score → stays pure KPI-only (feeds NRR/churn)
  - composite_score → same as health_score post-unification

Usage:
    python -m migrations.add_kpi_only_score_to_health_scores

Rollback:
    ALTER TABLE health_scores DROP COLUMN IF EXISTS kpi_only_score;
    ALTER TABLE health_scores DROP COLUMN IF EXISTS composite_score;
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Add kpi_only_score and composite_score to health_scores, backfill kpi_only_score."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()

        # 1. Add columns (idempotent)
        columns_to_add = [
            ("kpi_only_score", "NUMERIC(5,2)"),
            ("composite_score", "NUMERIC(5,2)"),
        ]
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(db.text(
                    f"ALTER TABLE health_scores ADD COLUMN {col_name} {col_type}"
                ))
                conn.commit()
                print(f"  Added column: health_scores.{col_name} ({col_type})")
            except Exception as e:
                conn.rollback()
                if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                    print(f"  Column health_scores.{col_name} already exists, skipping")
                else:
                    print(f"  Error adding {col_name}: {e}")
                    raise

        # 2. Backfill kpi_only_score = health_score for all existing rows
        #    (they are equal today — no Signal-DNA in production yet)
        try:
            result = conn.execute(db.text(
                "UPDATE health_scores SET kpi_only_score = health_score "
                "WHERE kpi_only_score IS NULL AND health_score IS NOT NULL"
            ))
            conn.commit()
            print(f"  Backfilled kpi_only_score for {result.rowcount} rows")
        except Exception as e:
            conn.rollback()
            print(f"  Error backfilling kpi_only_score: {e}")
            raise

        conn.close()
        print("\nMigration complete: kpi_only_score and composite_score added to health_scores")
        print("NOTE: Run this on EC2 after deploying the updated models.py")


def rollback():
    """Remove the two new columns from health_scores."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()
        for col_name in ('kpi_only_score', 'composite_score'):
            try:
                conn.execute(db.text(
                    f"ALTER TABLE health_scores DROP COLUMN IF EXISTS {col_name}"
                ))
                conn.commit()
                print(f"  Dropped column: health_scores.{col_name}")
            except Exception as e:
                conn.rollback()
                print(f"  Error dropping {col_name}: {e}")
        conn.close()
        print("\nRollback complete: kpi_only_score and composite_score removed")


if __name__ == '__main__':
    if '--rollback' in sys.argv:
        rollback()
    else:
        run_migration()
