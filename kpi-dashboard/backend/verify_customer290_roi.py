#!/usr/bin/env python3
"""
Verify Customer 290 data consistency across the ROI pipeline.
Standalone script using psycopg2 - no Flask dependency.
"""

import psycopg2
import psycopg2.extras
from datetime import datetime

DB_URL = "postgresql://dcuser:dcpass123@localhost:5432/cs_pulse_datacenter"

def main():
    conn = psycopg2.connect(DB_URL)
    conn.set_session(readonly=True)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    customer_id = 290

    # -- 1. Accounts for customer 290 --
    print("=" * 80)
    print(f"  CUSTOMER {customer_id} -- DATA CONSISTENCY VERIFICATION")
    print(f"  Run at: {datetime.now().isoformat()}")
    print("=" * 80)

    cur.execute("""
        SELECT account_id, account_name, vertical,
               revenue, initial_arr, final_arr,
               profile_metadata,
               account_status, region, csm_assigned,
               created_at
        FROM accounts
        WHERE customer_id = %s AND vertical = 'dc2_s'
        ORDER BY account_id
    """, (customer_id,))
    accounts = cur.fetchall()

    print(f"\n[1] ACCOUNTS  (customer_id={customer_id}, vertical=dc2_s)")
    print("-" * 80)
    if not accounts:
        print("  ** No accounts found. Exiting. **")
        conn.close()
        return

    account_ids = []
    for a in accounts:
        acct_id = a['account_id']
        account_ids.append(acct_id)
        # Extract ARR: prefer profile_metadata.arr, then revenue column, then initial/final_arr
        pm = a.get('profile_metadata') or {}
        arr = (pm.get('arr') or pm.get('ARR') or pm.get('annual_revenue')
               or a.get('revenue') or a.get('final_arr') or a.get('initial_arr') or 'N/A')
        arr_str = f"${arr:,.0f}" if isinstance(arr, (int, float)) else str(arr)
        print(f"  account_id={acct_id:<8}  name={a['account_name']:<40}  ARR={arr_str:<16}  status={a.get('account_status', 'N/A')}")

    print(f"\n  Total accounts: {len(accounts)}")

    # -- 2. HealthTrend window (uses month/year columns, not period_start) --
    print(f"\n[2] HEALTH TREND WINDOW")
    print("-" * 80)

    cur.execute("""
        SELECT account_id,
               MIN(year * 100 + month) AS earliest_ym,
               MAX(year * 100 + month) AS latest_ym,
               MIN(year) AS min_year, MIN(month) FILTER (WHERE year = (SELECT MIN(year) FROM health_trends h2 WHERE h2.account_id = health_trends.account_id)) AS min_month,
               COUNT(*) AS record_count,
               ROUND(AVG(overall_health_score), 2) AS avg_health
        FROM health_trends
        WHERE account_id = ANY(%s)
        GROUP BY account_id
        ORDER BY account_id
    """, (account_ids,))
    ht_rows = cur.fetchall()

    if not ht_rows:
        print("  ** No HealthTrend records found for these accounts **")
    else:
        for r in ht_rows:
            earliest = r['earliest_ym']
            latest = r['latest_ym']
            e_str = f"{earliest // 100}-{earliest % 100:02d}" if earliest else "?"
            l_str = f"{latest // 100}-{latest % 100:02d}" if latest else "?"
            print(f"  account_id={r['account_id']:<8}  earliest={e_str}  latest={l_str}  records={r['record_count']}  avg_health={r['avg_health']}")

    # -- 3. ContextNode counts by node_type --
    print(f"\n[3] CONTEXT NODES -- count by node_type")
    print("-" * 80)

    cur.execute("""
        SELECT cn.node_type, COUNT(*) AS cnt
        FROM context_nodes cn
        WHERE cn.account_id = ANY(%s)
        GROUP BY cn.node_type
        ORDER BY cnt DESC
    """, (account_ids,))
    node_counts = cur.fetchall()

    total_nodes = 0
    if not node_counts:
        print("  ** No ContextNode records found **")
    else:
        for r in node_counts:
            print(f"  {r['node_type']:<25} {r['cnt']:>6}")
            total_nodes += r['cnt']
        print(f"  {'TOTAL':<25} {total_nodes:>6}")

    # -- 4. Revenue impact aggregation --
    print(f"\n[4] REVENUE IMPACT -- aggregation by revenue_impact_type")
    print("-" * 80)

    cur.execute("""
        SELECT cn.revenue_impact_type,
               COUNT(*) AS cnt,
               SUM(cn.revenue_impact) AS total_impact,
               ROUND(AVG(cn.revenue_impact), 2) AS avg_impact,
               MIN(cn.revenue_impact) AS min_impact,
               MAX(cn.revenue_impact) AS max_impact
        FROM context_nodes cn
        WHERE cn.account_id = ANY(%s)
          AND cn.revenue_impact IS NOT NULL
          AND cn.revenue_impact_type IS NOT NULL
        GROUP BY cn.revenue_impact_type
        ORDER BY total_impact DESC
    """, (account_ids,))
    rev_rows = cur.fetchall()

    if not rev_rows:
        print("  ** No revenue impact data found **")
    else:
        for r in rev_rows:
            total = r['total_impact'] or 0
            avg_v = r['avg_impact'] or 0
            print(f"  {(r['revenue_impact_type'] or 'NULL'):<20}  count={r['cnt']:>4}  "
                  f"total=${total:>14,.2f}  avg=${avg_v:>12,.2f}  "
                  f"range=[${r['min_impact'] or 0:>12,.2f} .. ${r['max_impact'] or 0:>12,.2f}]")

    # -- 5. ContextEdge count (uses from_node_id / to_node_id) --
    print(f"\n[5] CONTEXT EDGES -- count for these accounts' nodes")
    print("-" * 80)

    cur.execute("""
        SELECT COUNT(*) AS edge_count
        FROM context_edges ce
        WHERE ce.from_node_id IN (
            SELECT cn.node_id FROM context_nodes cn WHERE cn.account_id = ANY(%s)
        )
        OR ce.to_node_id IN (
            SELECT cn.node_id FROM context_nodes cn WHERE cn.account_id = ANY(%s)
        )
    """, (account_ids, account_ids))
    edge_row = cur.fetchone()
    edge_count = edge_row['edge_count'] if edge_row else 0
    print(f"  Total edges: {edge_count}")

    if edge_count > 0:
        cur.execute("""
            SELECT ce.edge_type, COUNT(*) AS cnt
            FROM context_edges ce
            WHERE ce.from_node_id IN (
                SELECT cn.node_id FROM context_nodes cn WHERE cn.account_id = ANY(%s)
            )
            OR ce.to_node_id IN (
                SELECT cn.node_id FROM context_nodes cn WHERE cn.account_id = ANY(%s)
            )
            GROUP BY ce.edge_type
            ORDER BY cnt DESC
        """, (account_ids, account_ids))
        edge_types = cur.fetchall()
        for r in edge_types:
            print(f"  {(r['edge_type'] or 'NULL'):<30} {r['cnt']:>6}")

    # -- 6. Top 5 OUTCOME nodes by |revenue_impact| --
    print(f"\n[6] TOP 5 OUTCOME NODES by |revenue_impact|")
    print("-" * 80)

    cur.execute("""
        SELECT cn.title, cn.revenue_impact, cn.revenue_impact_type,
               cn.occurred_at, cn.account_id
        FROM context_nodes cn
        WHERE cn.account_id = ANY(%s)
          AND cn.node_type = 'OUTCOME'
          AND cn.revenue_impact IS NOT NULL
        ORDER BY ABS(cn.revenue_impact) DESC
        LIMIT 5
    """, (account_ids,))
    outcomes = cur.fetchall()

    if not outcomes:
        print("  ** No OUTCOME nodes with revenue_impact found **")
    else:
        for i, r in enumerate(outcomes, 1):
            impact = r['revenue_impact'] or 0
            print(f"  {i}. [{r['revenue_impact_type'] or '?':>10}]  ${impact:>14,.2f}  "
                  f"account={r['account_id']}  occurred={r['occurred_at']}")
            print(f"     title: {r['title']}")

    # -- 7. Top 5 SIGNAL nodes by |revenue_impact| --
    print(f"\n[7] TOP 5 SIGNAL NODES by |revenue_impact|")
    print("-" * 80)

    cur.execute("""
        SELECT cn.title, cn.revenue_impact, cn.revenue_impact_type,
               cn.occurred_at, cn.account_id
        FROM context_nodes cn
        WHERE cn.account_id = ANY(%s)
          AND cn.node_type = 'SIGNAL'
          AND cn.revenue_impact IS NOT NULL
        ORDER BY ABS(cn.revenue_impact) DESC
        LIMIT 5
    """, (account_ids,))
    signals = cur.fetchall()

    if not signals:
        print("  ** No SIGNAL nodes with revenue_impact found **")
    else:
        for i, r in enumerate(signals, 1):
            impact = r['revenue_impact'] or 0
            print(f"  {i}. [{r['revenue_impact_type'] or '?':>10}]  ${impact:>14,.2f}  "
                  f"account={r['account_id']}  occurred={r['occurred_at']}")
            print(f"     title: {r['title']}")

    # -- Summary --
    print(f"\n{'=' * 80}")
    print(f"  SUMMARY")
    print(f"{'=' * 80}")
    print(f"  Accounts:       {len(accounts)}")
    print(f"  ContextNodes:   {total_nodes}")
    print(f"  ContextEdges:   {edge_count}")
    ht_total = sum(r['record_count'] for r in (ht_rows or []))
    print(f"  HealthTrends:   {ht_total}")

    # Consistency checks
    print(f"\n  --- Consistency Checks ---")
    if len(accounts) == 0:
        print("  [FAIL] No accounts found for customer 290")
    else:
        print(f"  [OK]   {len(accounts)} accounts loaded")

    if ht_total == 0:
        print("  [WARN] No health trend data -- ROI pipeline may not have run")
    else:
        print(f"  [OK]   {ht_total} health trend records across {len(ht_rows)} accounts")

    if total_nodes == 0:
        print("  [WARN] No context graph nodes -- context graph not ingested")
    else:
        print(f"  [OK]   {total_nodes} context graph nodes")

    if edge_count == 0 and total_nodes > 0:
        print("  [WARN] Context nodes exist but no edges -- graph connectivity missing")
    elif edge_count > 0:
        ratio = edge_count / total_nodes if total_nodes > 0 else 0
        print(f"  [OK]   {edge_count} edges (ratio: {ratio:.1f} edges/node)")

    # Check node type coverage
    node_type_set = set(r['node_type'] for r in node_counts) if node_counts else set()
    expected_types = {'SIGNAL', 'DECISION', 'OUTCOME', 'STAKEHOLDER', 'EXTERNAL_CONTEXT'}
    missing = expected_types - node_type_set
    if missing and total_nodes > 0:
        print(f"  [WARN] Missing node types: {', '.join(sorted(missing))}")
    elif total_nodes > 0:
        print(f"  [OK]   All 5 node types present")

    # Revenue impact check
    rev_type_set = set(r['revenue_impact_type'] for r in rev_rows) if rev_rows else set()
    expected_rev = {'at_risk', 'protected', 'expansion', 'lost'}
    missing_rev = expected_rev - rev_type_set
    if missing_rev and rev_rows:
        print(f"  [WARN] Missing revenue impact types: {', '.join(sorted(missing_rev))}")
    elif rev_rows:
        print(f"  [OK]   Revenue impact types present: {', '.join(sorted(rev_type_set))}")

    print(f"{'=' * 80}\n")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
