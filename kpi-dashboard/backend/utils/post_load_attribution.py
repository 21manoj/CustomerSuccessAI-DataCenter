"""Post-load attribution: backfill PlaybookExecutionV2.revenue_protected and
revenue_expanded for a freshly-loaded customer.

WHY THIS EXISTS
---------------
The manifest-driven load uploads:
  - outcomes.csv  → context_nodes(node_type='OUTCOME', revenue_impact=...)
  - enhanced_signals.csv → triggers execute_playbook + close_playbook for at-risk accts

`utils.playbook_lifecycle.close_execution` auto-computes revenue_protected
from `(churn_prob_at_trigger - churn_prob_at_close) × ARR`. On synthetic
manifests, health_at_close often equals or falls below health_at_trigger
(the manifest is showing a still-declining trajectory at close-time even
when the OUTCOME says the account was saved). In that case the formula
returns 0 — so PlaybookExecutionV2.revenue_protected ends up $0 even
though context_nodes has churn_averted OUTCOMEs with real impact.

That breaks the CFO dashboard's `proof_data.revenue_protected` and
`proof_data.realized_roi` tiles (and the Investment Allocation Story's
"Already Delivered" panel) because all of those read from
PlaybookExecutionV2, not from context_nodes.

This module backfills the gap: for each account that has both
  (a) PlaybookExecutionV2 rows for the customer with revenue_protected=0
  (b) context_nodes(node_type='OUTCOME', subtype IN ('churn_averted','expansion_closed'))
we split the OUTCOME's revenue_impact across the matching PB executions
and write it back to revenue_protected / revenue_expanded.

Run is idempotent — re-running won't double-count.

USAGE
-----
    from post_load_attribution import backfill_playbook_attribution
    n_updated, total_prot, total_exp = backfill_playbook_attribution(customer_id=333)

Or via the manifest driver, which calls this automatically after process_data
completes.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Tuple

logger = logging.getLogger(__name__)


def backfill_playbook_attribution(customer_id: int) -> Tuple[int, float, float]:
    """Backfill revenue_protected + revenue_expanded on PlaybookExecutionV2
    rows for `customer_id` from matching OUTCOME context_nodes.

    Must be called inside a Flask app context.

    Returns:
        (n_executions_updated, total_revenue_protected, total_revenue_expanded)
    """
    from extensions import db
    from sqlalchemy import text

    # 1) Per-account totals of churn_averted and expansion_closed (positive impacts only)
    rows = db.session.execute(text(
        """
        SELECT account_id, node_subtype, SUM(COALESCE(revenue_impact, 0)) AS total_impact
        FROM context_nodes
        WHERE customer_id = :cust
          AND node_type = 'OUTCOME'
          AND node_subtype IN ('churn_averted', 'expansion_closed')
        GROUP BY account_id, node_subtype
        HAVING SUM(COALESCE(revenue_impact, 0)) > 0
        """
    ), {'cust': customer_id}).fetchall()

    protected_by_acct: dict[int, float] = {}
    expanded_by_acct: dict[int, float] = {}
    for acct_id, subtype, total_impact in rows:
        val = float(total_impact or 0)
        if subtype == 'churn_averted':
            protected_by_acct[acct_id] = val
        elif subtype == 'expansion_closed':
            expanded_by_acct[acct_id] = val

    if not protected_by_acct and not expanded_by_acct:
        logger.info(
            f'post_load_attribution: customer {customer_id} has no positive '
            f'churn_averted / expansion_closed OUTCOMEs — nothing to backfill'
        )
        return 0, 0.0, 0.0

    # 2) Count PB executions per account so we can split account-level impact
    exec_counts = db.session.execute(text(
        """
        SELECT account_id, COUNT(*) AS n
        FROM playbook_executions_v2
        WHERE customer_id = :cust
        GROUP BY account_id
        """
    ), {'cust': customer_id}).fetchall()
    exec_count_by_acct = {acct: n for acct, n in exec_counts}

    if not exec_count_by_acct:
        logger.info(
            f'post_load_attribution: customer {customer_id} has no '
            f'playbook_executions_v2 rows — nothing to backfill'
        )
        return 0, 0.0, 0.0

    # 3) Reset prior backfill state on this customer so the function is idempotent.
    # We ONLY reset rows that were never set by the live close-playbook flow
    # (revenue_protected = 0 AND revenue_expanded = 0). This avoids stomping on
    # rows where the churn-prob auto-compute genuinely produced a positive
    # protected value.
    db.session.execute(text(
        """
        UPDATE playbook_executions_v2
        SET revenue_protected = 0,
            revenue_expanded = 0,
            realized_roi_pct = 0
        WHERE customer_id = :cust
          AND (revenue_protected IS NULL OR revenue_protected = 0)
          AND (revenue_expanded IS NULL OR revenue_expanded = 0)
        """
    ), {'cust': customer_id})

    # 4) Backfill — split account-level OUTCOME impact across PB executions on that account
    pe_rows = db.session.execute(text(
        """
        SELECT id, account_id, total_cost
        FROM playbook_executions_v2
        WHERE customer_id = :cust
          AND (revenue_protected IS NULL OR revenue_protected = 0)
          AND (revenue_expanded IS NULL OR revenue_expanded = 0)
        """
    ), {'cust': customer_id}).fetchall()

    updated = 0
    total_prot = 0.0
    total_exp = 0.0
    for pe_id, acct_id, cost in pe_rows:
        n_execs = exec_count_by_acct.get(acct_id, 1) or 1
        prot_share = protected_by_acct.get(acct_id, 0.0) / n_execs
        exp_share = expanded_by_acct.get(acct_id, 0.0) / n_execs
        if prot_share <= 0 and exp_share <= 0:
            continue

        # full_cost from playbook cost bridge; fall back to seeded $4,560 if missing.
        cost_f = float(cost or 0) or 4560.0
        realized_roi_pct = round(((prot_share + exp_share) / cost_f) * 100, 2)

        db.session.execute(text(
            """
            UPDATE playbook_executions_v2
            SET revenue_protected = :prot,
                revenue_expanded = :exp,
                realized_roi_pct = :roi,
                updated_at = NOW()
            WHERE id = :pe_id
            """
        ), {
            'prot': prot_share,
            'exp': exp_share,
            'roi': realized_roi_pct,
            'pe_id': pe_id,
        })
        updated += 1
        total_prot += prot_share
        total_exp += exp_share

    db.session.commit()

    logger.info(
        f'post_load_attribution: customer {customer_id} — backfilled {updated} '
        f'playbook executions, ${total_prot:,.0f} revenue_protected, '
        f'${total_exp:,.0f} revenue_expanded'
    )
    return updated, total_prot, total_exp


if __name__ == '__main__':
    # CLI invocation: python post_load_attribution.py <customer_id>
    import argparse
    import sys
    import os

    # Make the package importable when run as a script inside cspulse-platform
    sys.path.insert(0, '/app/backend')

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('customer_id', type=int, help='customer_id to backfill')
    args = parser.parse_args()

    from app_v3_minimal import app
    with app.app_context():
        n, prot, exp = backfill_playbook_attribution(args.customer_id)
        print(f'updated={n} revenue_protected=${prot:,.0f} revenue_expanded=${exp:,.0f}')
