#!/usr/bin/env python3
"""
Idempotent Schema Sync — ensures PostgreSQL DB matches SQLAlchemy ORM models.

Reads all ORM model definitions from models.py + product_analytics_models.py,
compares against the live DB schema, and applies any missing:
  - Tables (CREATE TABLE)
  - Columns (ALTER TABLE ADD COLUMN)
  - Indexes (CREATE INDEX IF NOT EXISTS)
  - Unique constraints

Safe to run on every deployment. Every operation is idempotent:
  - Checks before creating (IF NOT EXISTS patterns)
  - Never drops columns, tables, or data
  - Logs every action for audit trail

Usage:
  # From backend/ directory:
  python3 scripts/migrate_schema_sync.py

  # Or from Docker entrypoint:
  python3 /app/backend/scripts/migrate_schema_sync.py

  # Dry-run (show what would change without applying):
  python3 scripts/migrate_schema_sync.py --dry-run

Requires DATABASE_URL environment variable.
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [SCHEMA-SYNC] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger('schema_sync')


# SQLAlchemy type → PostgreSQL DDL mapping
TYPE_MAP = {
    'INTEGER': 'INTEGER',
    'BIGINTEGER': 'BIGINT',
    'SMALLINTEGER': 'SMALLINT',
    'VARCHAR': 'VARCHAR',
    'STRING': 'VARCHAR',
    'TEXT': 'TEXT',
    'BOOLEAN': 'BOOLEAN',
    'DATE': 'DATE',
    'DATETIME': 'TIMESTAMP WITHOUT TIME ZONE',
    'FLOAT': 'DOUBLE PRECISION',
    'NUMERIC': 'NUMERIC',
    'JSON': 'JSON',
    'LARGEBINARY': 'BYTEA',
}


def sa_type_to_ddl(col):
    """Convert SQLAlchemy column type to PostgreSQL DDL string."""
    sa_type = type(col.type).__name__.upper()

    if sa_type in ('VARCHAR', 'STRING'):
        length = getattr(col.type, 'length', None)
        if length:
            return f'VARCHAR({length})'
        return 'VARCHAR'
    elif sa_type == 'NUMERIC':
        precision = getattr(col.type, 'precision', None)
        scale = getattr(col.type, 'scale', None)
        if precision and scale:
            return f'NUMERIC({precision},{scale})'
        elif precision:
            return f'NUMERIC({precision})'
        return 'NUMERIC'
    elif sa_type in TYPE_MAP:
        return TYPE_MAP[sa_type]
    else:
        log.warning(f"Unknown type {sa_type} for column {col.name}, defaulting to TEXT")
        return 'TEXT'


def get_default_clause(col):
    """Extract DEFAULT clause from SQLAlchemy column."""
    if col.server_default is not None:
        text = str(col.server_default.arg)
        # Handle common server_default patterns
        if 'now()' in text.lower() or 'current_timestamp' in text.lower():
            return "DEFAULT now()"
        if 'current_date' in text.lower():
            return "DEFAULT CURRENT_DATE"
        return f"DEFAULT {text}"
    if col.default is not None:
        val = col.default.arg
        if callable(val):
            return ""  # Can't express Python callables as SQL defaults
        if isinstance(val, bool):
            return f"DEFAULT {'true' if val else 'false'}"
        if isinstance(val, (int, float)):
            return f"DEFAULT {val}"
        if isinstance(val, str):
            return f"DEFAULT '{val}'"
        if isinstance(val, list):
            # JSON array default
            import json
            return f"DEFAULT '{json.dumps(val)}'::json"
    return ""


def run_sync(dry_run=False):
    """Main sync logic."""
    from sqlalchemy import create_engine, inspect, text

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        from dotenv import load_dotenv
        load_dotenv()
        database_url = os.environ.get('DATABASE_URL')

    if not database_url:
        log.error("DATABASE_URL not set. Cannot sync schema.")
        sys.exit(1)

    engine = create_engine(database_url)
    inspector = inspect(engine)

    # Get all existing tables
    existing_tables = set(inspector.get_table_names())
    log.info(f"DB has {len(existing_tables)} existing tables")

    # Load ORM models
    # We need a Flask app context to import models
    try:
        from app_v3_minimal import create_app
        app = create_app()
    except Exception:
        # Fallback: create minimal Flask app for model loading
        from flask import Flask
        from extensions import db
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)

    with app.app_context():
        from extensions import db as _db

        # Import all model modules to register them
        import models  # noqa
        try:
            import product_analytics_models  # noqa
        except ImportError:
            pass

        # Get all registered models
        all_models = _db.Model.__subclasses__()
        # Also get subclasses of subclasses (if any inheritance)
        all_model_classes = []
        for m in all_models:
            all_model_classes.append(m)
            all_model_classes.extend(m.__subclasses__())

        log.info(f"ORM defines {len(all_model_classes)} model classes")

        actions_taken = 0
        actions_skipped = 0

        with engine.begin() as conn:
            for model in all_model_classes:
                table_name = getattr(model, '__tablename__', None)
                if not table_name:
                    continue

                # --- Step 1: Create table if missing ---
                if table_name not in existing_tables:
                    log.info(f"  TABLE {table_name}: MISSING — creating")
                    if not dry_run:
                        try:
                            model.__table__.create(engine, checkfirst=True)
                            actions_taken += 1
                            log.info(f"  TABLE {table_name}: CREATED")
                        except Exception as e:
                            log.error(f"  TABLE {table_name}: CREATE FAILED: {e}")
                    else:
                        actions_taken += 1
                        log.info(f"  TABLE {table_name}: WOULD CREATE (dry-run)")
                    continue

                # --- Step 2: Check for missing columns ---
                db_columns = {col['name']: col for col in inspector.get_columns(table_name)}

                for col in model.__table__.columns:
                    if col.name in db_columns:
                        actions_skipped += 1
                        continue

                    # Column missing in DB — add it
                    ddl_type = sa_type_to_ddl(col)
                    nullable = "NULL" if col.nullable else "NOT NULL"
                    default = get_default_clause(col)

                    # For NOT NULL columns without a default, make them nullable
                    # (can't add NOT NULL to existing table with data without a default)
                    if nullable == "NOT NULL" and not default:
                        nullable = "NULL"
                        log.warning(f"  {table_name}.{col.name}: NOT NULL but no default — adding as NULL")

                    alter_sql = f'ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS "{col.name}" {ddl_type} {default} {nullable}'
                    alter_sql = alter_sql.strip()

                    if not dry_run:
                        try:
                            conn.execute(text(alter_sql))
                            actions_taken += 1
                            log.info(f"  {table_name}.{col.name}: ADDED ({ddl_type})")
                        except Exception as e:
                            log.error(f"  {table_name}.{col.name}: ADD FAILED: {e}")
                    else:
                        actions_taken += 1
                        log.info(f"  {table_name}.{col.name}: WOULD ADD ({ddl_type}) (dry-run)")

                # --- Step 3: Check for missing indexes ---
                db_indexes = {idx['name']: idx for idx in inspector.get_indexes(table_name)}
                for idx in model.__table__.indexes:
                    if idx.name and idx.name in db_indexes:
                        actions_skipped += 1
                        continue
                    if not idx.name:
                        continue

                    cols = ', '.join(f'"{c.name}"' for c in idx.columns)
                    unique = "UNIQUE " if idx.unique else ""
                    create_idx_sql = f'CREATE {unique}INDEX IF NOT EXISTS "{idx.name}" ON {table_name} ({cols})'

                    if not dry_run:
                        try:
                            conn.execute(text(create_idx_sql))
                            actions_taken += 1
                            log.info(f"  INDEX {idx.name}: CREATED on {table_name}({cols})")
                        except Exception as e:
                            log.error(f"  INDEX {idx.name}: CREATE FAILED: {e}")
                    else:
                        actions_taken += 1
                        log.info(f"  INDEX {idx.name}: WOULD CREATE on {table_name}({cols}) (dry-run)")

                # --- Step 4: Check for missing unique constraints ---
                db_unique = set()
                for uc in inspector.get_unique_constraints(table_name):
                    db_unique.add(tuple(sorted(uc['column_names'])))

                for uc in model.__table__.constraints:
                    from sqlalchemy import UniqueConstraint
                    if not isinstance(uc, UniqueConstraint):
                        continue
                    uc_cols = tuple(sorted(c.name for c in uc.columns))
                    if uc_cols in db_unique:
                        actions_skipped += 1
                        continue
                    if not uc_cols:
                        continue

                    uc_name = uc.name or f"uq_{table_name}_{'_'.join(uc_cols)}"
                    cols_str = ', '.join(f'"{c}"' for c in uc_cols)
                    # Can't use IF NOT EXISTS for constraints, check first
                    check_sql = f"""
                        SELECT 1 FROM pg_constraint
                        WHERE conname = :name AND conrelid = :table::regclass
                    """
                    exists = conn.execute(text(check_sql), {"name": uc_name, "table": table_name}).fetchone()
                    if exists:
                        actions_skipped += 1
                        continue

                    add_uc_sql = f'ALTER TABLE {table_name} ADD CONSTRAINT "{uc_name}" UNIQUE ({cols_str})'
                    if not dry_run:
                        try:
                            conn.execute(text(add_uc_sql))
                            actions_taken += 1
                            log.info(f"  UNIQUE {uc_name}: CREATED on {table_name}({cols_str})")
                        except Exception as e:
                            log.warning(f"  UNIQUE {uc_name}: SKIPPED (may already exist): {e}")
                    else:
                        actions_taken += 1
                        log.info(f"  UNIQUE {uc_name}: WOULD CREATE on {table_name}({cols_str}) (dry-run)")

        engine.dispose()

        mode = "DRY-RUN" if dry_run else "APPLIED"
        log.info(f"Schema sync complete ({mode}): {actions_taken} changes, {actions_skipped} already in sync")
        return actions_taken


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Idempotent schema sync: ORM → PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("CS Pulse Schema Sync")
    log.info(f"Mode: {'DRY-RUN' if args.dry_run else 'APPLY'}")
    log.info(f"Time: {datetime.utcnow().isoformat()}")
    log.info("=" * 60)

    changes = run_sync(dry_run=args.dry_run)
    if changes > 0 and not args.dry_run:
        log.info(f"✅ {changes} schema changes applied successfully")
    elif changes > 0:
        log.info(f"⚠️  {changes} schema changes detected (dry-run, not applied)")
    else:
        log.info("✅ Schema is in sync — no changes needed")
