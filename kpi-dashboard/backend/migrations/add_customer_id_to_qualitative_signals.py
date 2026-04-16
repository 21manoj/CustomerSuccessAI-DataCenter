"""
Migration: Add customer_id to qualitative_signals table.

Fixes signal_id PK collision across customers. Changes:
1. Add customer_id column (backfilled from accounts table)
2. Add auto-increment integer PK (id)
3. Drop signal_id as sole PK → composite unique (customer_id, signal_id)
4. Add indexes for common query patterns
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def run_migration(db_session):
    """Execute the migration within an existing session/connection."""
    conn = db_session.connection()

    # 1. Check if already migrated
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'qualitative_signals' AND column_name = 'customer_id'
    """))
    if result.fetchone():
        logger.info("Migration already applied: qualitative_signals.customer_id exists")
        return

    logger.info("Starting migration: add customer_id to qualitative_signals")

    # 2. Add customer_id column (nullable for backfill)
    conn.execute(text("""
        ALTER TABLE qualitative_signals
        ADD COLUMN customer_id INTEGER
    """))
    logger.info("  Added customer_id column")

    # 3. Backfill customer_id from accounts table (only for recent customers)
    #    Old customers get backfilled lazily; new ones get customer_id on INSERT.
    result = conn.execute(text("""
        UPDATE qualitative_signals qs
        SET customer_id = a.customer_id
        FROM accounts a
        WHERE qs.account_id = a.account_id
          AND qs.customer_id IS NULL
    """))
    backfilled = result.rowcount
    logger.info("  Backfilled customer_id for %d rows", backfilled)

    # 5. Add auto-increment id column
    conn.execute(text("""
        ALTER TABLE qualitative_signals
        ADD COLUMN id SERIAL
    """))
    logger.info("  Added id SERIAL column")

    # 6. Drop old PK, add new PK on id
    conn.execute(text("""
        ALTER TABLE qualitative_signals
        DROP CONSTRAINT IF EXISTS qualitative_signals_pkey
    """))
    conn.execute(text("""
        ALTER TABLE qualitative_signals
        ADD PRIMARY KEY (id)
    """))
    logger.info("  Changed PK from signal_id to id (auto-increment)")

    # 7. Set customer_id NOT NULL + FK
    conn.execute(text("""
        ALTER TABLE qualitative_signals
        ALTER COLUMN customer_id SET NOT NULL
    """))
    conn.execute(text("""
        ALTER TABLE qualitative_signals
        ADD CONSTRAINT fk_qualitative_signals_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    """))
    logger.info("  Added FK constraint to customers")

    # 8. Composite unique constraint
    conn.execute(text("""
        ALTER TABLE qualitative_signals
        ADD CONSTRAINT uq_customer_signal_id
        UNIQUE (customer_id, signal_id)
    """))
    logger.info("  Added UNIQUE(customer_id, signal_id)")

    # 9. Indexes for query patterns
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_signals_customer_account
        ON qualitative_signals(customer_id, account_id)
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_signals_customer_date
        ON qualitative_signals(customer_id, signal_date)
    """))
    logger.info("  Created indexes")

    db_session.commit()
    logger.info("Migration complete: qualitative_signals now has customer_id + auto-increment PK")


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    from app_v3_minimal import app
    from extensions import db

    with app.app_context():
        run_migration(db.session)
