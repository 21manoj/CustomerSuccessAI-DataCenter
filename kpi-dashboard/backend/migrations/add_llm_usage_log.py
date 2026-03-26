#!/usr/bin/env python3
"""
Migration: Add llm_usage_log table
===================================

Stores per-call LLM usage records for the centralized Budget Controller.
Indexed by (customer_id, created_at) for fast daily/monthly aggregates
and by module for per-caller breakdowns.

Run:
    python backend/migrations/add_llm_usage_log.py
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from extensions import db
from flask import Flask


SQL = """
CREATE TABLE IF NOT EXISTS llm_usage_log (
    log_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    module VARCHAR(50) NOT NULL,
    model VARCHAR(50),
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_estimate_usd NUMERIC(10,6) DEFAULT 0,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_customer_date
    ON llm_usage_log(customer_id, created_at);

CREATE INDEX IF NOT EXISTS idx_llm_usage_module
    ON llm_usage_log(module);
"""


def run_migration():
    """Execute the migration SQL."""
    app = Flask(__name__)

    database_url = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL or SQLALCHEMY_DATABASE_URI not set")
        sys.exit(1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        for statement in SQL.strip().split(';'):
            statement = statement.strip()
            if statement:
                db.session.execute(db.text(statement))
        db.session.commit()
        print("Migration complete: llm_usage_log table created with indexes")


if __name__ == '__main__':
    run_migration()
