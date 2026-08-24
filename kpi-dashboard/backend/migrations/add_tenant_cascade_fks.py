#!/usr/bin/env python3
"""
Migration: tenant-deletion cascade FKs (context graph + core tenant tables)
===========================================================================

Root cause of the 2026-08-24 orphan cleanup (6,082 context edges + 8,312
nodes owned by long-deleted customers, 60% of the graph): customer deletion
never cascaded. On the live DB, context_nodes.customer_id and
context_edges.customer_id had NO foreign key at all (models.py declares
them, but the tables predate those declarations and create_all never
ALTERs existing tables), accounts.customer_id had none either, and
context_nodes.account_id was ON DELETE NO ACTION.

This migration makes orphaning structurally impossible for any deletion
path — ORM, raw SQL, ad-hoc script — by putting the control in the
database, the same principle as WS-2's NOT NULL argument:

  Named constraints (dropped/recreated to guarantee CASCADE):
    accounts.customer_id        -> customers  ON DELETE CASCADE
    context_nodes.customer_id   -> customers  ON DELETE CASCADE
    context_nodes.account_id    -> accounts   ON DELETE CASCADE
    context_edges.customer_id   -> customers  ON DELETE CASCADE
    (context_edges.from/to_node_id -> context_nodes CASCADE already exist)

  Dynamic sweep (best-effort, per-table):
    every other public table with an INTEGER customer_id column gets an
    ON DELETE CASCADE FK to customers, and every one with an INTEGER
    account_id column gets one to accounts — ONLY if the table currently
    has zero violating rows. Tables with violations (or non-integer id
    columns, e.g. agent_memory's varchar account_id) are logged and
    skipped, never silently cleaned.

Idempotent: constraints are checked before creation. Postgres-only (no-op
with a notice on other dialects). Safe to run at every startup.

Usage (inside cs-pulse container):
    python3 /app/backend/migrations/add_tenant_cascade_fks.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (table, column, referenced_table, referenced_column)
CORE_CASCADES = [
    ('accounts', 'customer_id', 'customers', 'customer_id'),
    ('context_nodes', 'customer_id', 'customers', 'customer_id'),
    ('context_nodes', 'account_id', 'accounts', 'account_id'),
    ('context_edges', 'customer_id', 'customers', 'customer_id'),
]

# Tables the dynamic sweep must never touch (system/session/meta tables,
# or ones where customer_id/account_id is not a tenant reference).
SWEEP_SKIP = {'customers', 'accounts', 'context_nodes', 'context_edges', 'sessions'}


def _fk_state(conn, table, column):
    """Return (constraint_name, delete_rule) for an FK on table.column, or (None, None)."""
    from sqlalchemy import text
    row = conn.execute(text("""
        SELECT tc.constraint_name, rc.delete_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema
        JOIN information_schema.referential_constraints rc
          ON rc.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
          AND tc.table_name = :t AND kcu.column_name = :c
        LIMIT 1
    """), {'t': table, 'c': column}).fetchone()
    return (row[0], row[1]) if row else (None, None)


def _violations(conn, table, column, ref_table, ref_column):
    from sqlalchemy import text
    return conn.execute(text(
        f'SELECT COUNT(*) FROM "{table}" x WHERE x.{column} IS NOT NULL '
        f'AND NOT EXISTS (SELECT 1 FROM "{ref_table}" r WHERE r.{ref_column} = x.{column})'
    )).fetchone()[0]


def _ensure_cascade(conn, table, column, ref_table, ref_column, results):
    from sqlalchemy import text
    key = f'{table}.{column}'
    name, rule = _fk_state(conn, table, column)
    if name and rule == 'CASCADE':
        results['ok'].append(key)
        return
    n_bad = _violations(conn, table, column, ref_table, ref_column)
    if n_bad:
        # Never silently clean data here — report and skip.
        results['skipped'].append(f'{key} ({n_bad} orphaned rows — clean first)')
        return
    if name:  # exists with wrong delete rule — replace
        conn.execute(text(f'ALTER TABLE "{table}" DROP CONSTRAINT "{name}"'))
    cname = f'fk_{table}_{column}_cascade'
    conn.execute(text(
        f'ALTER TABLE "{table}" ADD CONSTRAINT "{cname}" '
        f'FOREIGN KEY ({column}) REFERENCES "{ref_table}"({ref_column}) ON DELETE CASCADE'
    ))
    results['added'].append(key)


def run_migration(verbose=True):
    from sqlalchemy import text
    from extensions import db

    if db.engine.dialect.name != 'postgresql':
        if verbose:
            print('   tenant-cascade migration: non-Postgres dialect, skipping')
        return {'ok': [], 'added': [], 'skipped': ['non-postgres dialect']}

    results = {'ok': [], 'added': [], 'skipped': []}
    with db.engine.begin() as conn:
        for table, column, ref_t, ref_c in CORE_CASCADES:
            _ensure_cascade(conn, table, column, ref_t, ref_c, results)

        # Dynamic sweep: every other integer customer_id / account_id column.
        for ref_t, ref_c, col in (('customers', 'customer_id', 'customer_id'),
                                  ('accounts', 'account_id', 'account_id')):
            rows = conn.execute(text("""
                SELECT c.table_name FROM information_schema.columns c
                JOIN information_schema.tables t
                  ON t.table_name = c.table_name AND t.table_schema = 'public'
                 AND t.table_type = 'BASE TABLE'
                WHERE c.column_name = :col AND c.table_schema = 'public'
                  AND c.data_type IN ('integer', 'bigint')
                ORDER BY c.table_name
            """), {'col': col}).fetchall()
            for (table,) in rows:
                if table in SWEEP_SKIP:
                    continue
                try:
                    _ensure_cascade(conn, table, col, ref_t, ref_c, results)
                except Exception as e:
                    results['skipped'].append(f'{table}.{col} (error: {e})')

    if verbose:
        print(f"   tenant-cascade FKs: {len(results['ok'])} already ok, "
              f"{len(results['added'])} added, {len(results['skipped'])} skipped")
        for s in results['added']:
            print(f'     + {s}')
        for s in results['skipped']:
            print(f'     ! skipped {s}')
    return results


if __name__ == '__main__':
    from app_v3_minimal import app
    with app.app_context():
        run_migration()
