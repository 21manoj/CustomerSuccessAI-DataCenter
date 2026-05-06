#!/usr/bin/env python3
"""
Migration: Create predictor_calibrations table
===============================================

NRR Predictor v3 — calibrated coefficients per (customer_id, saas_profile,
sub_model). Per Architecture Decision A2 in PLAN_nrr_predictor_v3.md, the
predictor splits offline calibration (Wizard D writes here) from online
inference (`backend/predictor/` reads here).

Per A6, sub_models include both churn and expansion as first-class:
  - hazard, contraction, expansion_event, expansion_size

One row per (customer_id, saas_profile, sub_model) is_active=True at any time.
Wizard D INSERTs new rows and flips previous active row to is_active=False
(audit-trail preserving — never UPDATEs in place).

Usage:
    python -m migrations.add_predictor_calibrations_table

Rollback:
    DROP INDEX IF EXISTS idx_predcal_active_lookup;
    DROP TABLE IF EXISTS predictor_calibrations;
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text  # noqa: E402

from extensions import db  # noqa: E402


def column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(db.engine)
    if table_name not in inspector.get_table_names():
        return False
    cols = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in cols


def run_migration():
    print('=' * 70)
    print('Migration: Create predictor_calibrations table')
    print('=' * 70)

    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()

    if 'predictor_calibrations' in existing_tables:
        print('  predictor_calibrations table already exists — skipping create')
    else:
        print('  Creating predictor_calibrations table...')
        with db.engine.begin() as conn:
            conn.execute(text('''
                CREATE TABLE predictor_calibrations (
                    id              SERIAL PRIMARY KEY,
                    calibration_id  VARCHAR(60) NOT NULL UNIQUE,

                    customer_id     INTEGER REFERENCES customers(customer_id),
                    vertical        VARCHAR(50) NOT NULL,
                    saas_profile    VARCHAR(50),
                    sub_model       VARCHAR(50) NOT NULL,

                    fit_type        VARCHAR(50) NOT NULL,
                    coefficients    JSONB NOT NULL,
                    prior_used      JSONB,

                    metrics         JSONB,
                    panel_summary   JSONB,

                    fit_started_at  TIMESTAMP,
                    fit_completed_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    fitted_by       VARCHAR(100),
                    notes           TEXT,

                    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
                );
            '''))
            conn.execute(text('''
                CREATE INDEX idx_predcal_calibration_id
                  ON predictor_calibrations(calibration_id);
            '''))
            conn.execute(text('''
                CREATE INDEX idx_predcal_customer_id
                  ON predictor_calibrations(customer_id);
            '''))
            conn.execute(text('''
                CREATE INDEX idx_predcal_vertical
                  ON predictor_calibrations(vertical);
            '''))
            conn.execute(text('''
                CREATE INDEX idx_predcal_sub_model
                  ON predictor_calibrations(sub_model);
            '''))
            conn.execute(text('''
                CREATE INDEX idx_predcal_is_active
                  ON predictor_calibrations(is_active);
            '''))
            conn.execute(text('''
                CREATE INDEX idx_predcal_created_at
                  ON predictor_calibrations(created_at);
            '''))
            conn.execute(text('''
                CREATE INDEX idx_predcal_active_lookup
                  ON predictor_calibrations(
                    customer_id, vertical, saas_profile, sub_model, is_active
                  );
            '''))
        print('  + Created predictor_calibrations table with 7 indexes')

    print()
    print('Migration complete.')
    print()
    print('Next: Wizard D (predictor calibrator) will INSERT calibrated')
    print('coefficients here. The predictor inference module will read them.')


if __name__ == '__main__':
    from app_v3_minimal import app

    with app.app_context():
        run_migration()
