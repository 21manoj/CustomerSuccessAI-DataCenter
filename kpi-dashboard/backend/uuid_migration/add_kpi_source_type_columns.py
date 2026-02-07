#!/usr/bin/env python3
"""
Migration: Add kpi_source_type and derivation_formula columns to dc2s_kpis table.

Supports the raw vs leading indicator classification.
  - kpi_source_type: 'raw' (directly measured) or 'leading' (derived/composite/predictive)
  - derivation_formula: SQL/pseudocode formula for leading indicators (NULL for raw)

NON-DESTRUCTIVE: Only ADDs new columns.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text, inspect


def column_exists(inspector, table_name, column_name):
    """Check if a column already exists in a table."""
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def run_migration(app=None):
    """Add kpi_source_type and derivation_formula to dc2s_kpis."""
    if app is None:
        from app import create_app
        app = create_app()

    with app.app_context():
        from extensions import db
        inspector = inspect(db.engine)

        # Check if table exists
        tables = inspector.get_table_names()
        if 'dc2s_kpis' not in tables:
            print("Table dc2s_kpis does not exist yet — skipping migration.")
            return

        added = []

        if not column_exists(inspector, 'dc2s_kpis', 'kpi_source_type'):
            db.session.execute(text(
                "ALTER TABLE dc2s_kpis ADD COLUMN kpi_source_type VARCHAR(20) DEFAULT 'raw'"
            ))
            added.append('kpi_source_type')

        if not column_exists(inspector, 'dc2s_kpis', 'derivation_formula'):
            db.session.execute(text(
                "ALTER TABLE dc2s_kpis ADD COLUMN derivation_formula TEXT"
            ))
            added.append('derivation_formula')

        if added:
            db.session.commit()
            print(f"Migration complete: added columns {added} to dc2s_kpis")

            # Create index on kpi_source_type for filtering queries
            try:
                db.session.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_dc2s_kpi_source_type "
                    "ON dc2s_kpis (kpi_source_type)"
                ))
                db.session.commit()
                print("Created index idx_dc2s_kpi_source_type")
            except Exception as e:
                print(f"Index creation skipped (may already exist): {e}")
        else:
            print("Migration skipped: columns already exist in dc2s_kpis")


if __name__ == '__main__':
    run_migration()
