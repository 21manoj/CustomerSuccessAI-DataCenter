#!/usr/bin/env python3
"""
Clear stale revenue_impact values from SIGNAL nodes.

Revenue impact belongs exclusively on OUTCOME nodes.  SIGNAL nodes
previously carried cumulative risk estimates (e.g. -$400K → -$800K →
-$1.2M for the same escalating event) and positive expansion values
that duplicated OUTCOME figures.  This migration NULLs them out.

The at_risk metric is now derived from health-score × ARR in
utils/context_graph.py:_calculate_at_risk_from_health().

Usage:
    python3 scripts/migrate_clear_signal_revenue_impact.py           # Dry-run
    python3 scripts/migrate_clear_signal_revenue_impact.py --apply   # Apply changes
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2


def get_db_url():
    """Get database URL from environment or default."""
    return os.environ.get(
        'DATABASE_URL',
        'postgresql://dcuser:dcpass123@localhost:5432/cs_pulse_datacenter',
    )


def run(apply: bool = False):
    conn = psycopg2.connect(get_db_url())
    conn.autocommit = False
    cur = conn.cursor()

    # ── Count affected rows ──
    cur.execute("""
        SELECT count(*)
        FROM context_nodes
        WHERE node_type = 'SIGNAL'
          AND revenue_impact IS NOT NULL
    """)
    total = cur.fetchone()[0]

    # ── Preview (top 20) ──
    cur.execute("""
        SELECT node_id, customer_id, account_id,
               node_subtype, revenue_impact,
               left(title, 80) AS title_preview
        FROM context_nodes
        WHERE node_type = 'SIGNAL'
          AND revenue_impact IS NOT NULL
        ORDER BY abs(revenue_impact) DESC
        LIMIT 20
    """)
    rows = cur.fetchall()

    print(f"\n{'='*80}")
    print(f"SIGNAL nodes with non-NULL revenue_impact: {total}")
    print(f"{'='*80}")
    for r in rows:
        print(f"  node {r[0]:>6}  cust={r[1]}  acct={r[2]}  "
              f"sub={r[3]:<12}  rev={r[4]:>14,.2f}  {r[5]}")

    if not apply:
        print(f"\n  DRY RUN — {total} rows would be updated.  "
              f"Re-run with --apply to execute.\n")
        conn.close()
        return

    # ── Apply: NULL out revenue_impact on all SIGNAL nodes ──
    cur.execute("""
        UPDATE context_nodes
        SET revenue_impact = NULL,
            revenue_impact_type = NULL
        WHERE node_type = 'SIGNAL'
          AND revenue_impact IS NOT NULL
    """)
    updated = cur.rowcount
    conn.commit()

    print(f"\n  ✅ Applied — {updated} SIGNAL nodes cleared.\n")
    cur.close()
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Clear stale revenue_impact from SIGNAL nodes')
    parser.add_argument(
        '--apply', action='store_true',
        help='Apply changes (default is dry-run)')
    args = parser.parse_args()
    run(apply=args.apply)
