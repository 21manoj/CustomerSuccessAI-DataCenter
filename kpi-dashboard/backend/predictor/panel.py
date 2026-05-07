"""Panel construction — Block 1 of NRR Predictor v3.

Wraps `sql/build_panel.sql` so callers can build the (account, month)
panel programmatically. The SQL is the source of truth for shape and
joins; this wrapper just handles parameter binding and DataFrame
materialization.

Usage:
    from predictor.panel import build_panel

    df = build_panel(customer_ids=[393])
    df = build_panel(customer_ids=[393, 491])  # multi-tenant from day 1

The returned DataFrame has the schema documented in
`PLAN_nrr_predictor_v3.md` Part 2 + Architecture Decision A5.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY, INTEGER
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Which SQL backs build_panel(). Two layouts supported so the same panel.py
# works on both local dev (v1 and v2 as distinct files) and deployed
# containers (v2 promoted into build_panel.sql, v2 file may be absent):
#
#   Local layout:
#     build_panel.sql            → v1 content (frozen arr, historical)
#     build_panel_v2.sql         → v2 content (time-varying arr)
#     PREDICTOR_BUILD_PANEL_SQL=build_panel_v2.sql → reads build_panel_v2.sql
#
#   Promoted layout (e.g. EC2):
#     build_panel.sql            → v2 content (promoted)
#     build_panel_v2.sql         → absent or stub
#     PREDICTOR_BUILD_PANEL_SQL=build_panel_v2.sql → falls back to build_panel.sql
#
# Default (no env) reads build_panel.sql, so behavior matches whichever
# file the deploy puts at that path.
_SQL_NAME = os.environ.get('PREDICTOR_BUILD_PANEL_SQL', 'build_panel.sql')
_sql_dir = Path(__file__).parent / 'sql'
_SQL_PATH = _sql_dir / _SQL_NAME
# Alias for promoted layout: env asks for v2 but only build_panel.sql exists
if _SQL_NAME == 'build_panel_v2.sql' and not _SQL_PATH.exists():
    _SQL_PATH = _sql_dir / 'build_panel.sql'
if not _SQL_PATH.exists():
    raise FileNotFoundError(
        f'PREDICTOR_BUILD_PANEL_SQL={_SQL_NAME!r} → {_SQL_PATH} not found. '
        f'Allowed values: build_panel.sql, build_panel_v2.sql.'
    )


def _load_sql() -> str:
    """Read panel SQL from disk (file name from PREDICTOR_BUILD_PANEL_SQL)."""
    return _SQL_PATH.read_text()


def build_panel(
    customer_ids: Iterable[int],
    engine: Optional[Engine] = None,
) -> pd.DataFrame:
    """Build the (account, month) panel for the given customer ids.

    Parameters
    ----------
    customer_ids : iterable of int
        Tenants to include. Phase 1 scope: SaaS only (vertical='saas_premium').
        Non-SaaS tenants are filtered out by the SQL.
    engine : SQLAlchemy Engine, optional
        If omitted, uses Flask app's `db.engine` (requires running inside
        the app context).

    Returns
    -------
    DataFrame with columns matching `sample_panel_rows.txt`:
        account_id, tenant_id, saas_profile, segment, arr_band,
        month, month_idx, tenure_in_panel,
        health, health_slope_1mo, health_slope_3mo, volatility_3mo,
        arc_type, days_to_renewal, days_to_renewal_band,
        is_churn_event, is_contraction_event, is_expansion_event,
        arr.

    Notes
    -----
    Returns empty DataFrame (with correct columns) if no SaaS tenants in
    `customer_ids` have any health observations. Caller should treat empty
    panel as a hard fail at G1.5 (data-quality gate).
    """
    cust_ids = list(customer_ids)
    if not cust_ids:
        raise ValueError('customer_ids must contain at least one tenant id')

    if engine is None:
        from extensions import db
        engine = db.engine

    sql = _load_sql()
    stmt = text(sql).bindparams(
        bindparam('target_customer_ids', type_=ARRAY(INTEGER))
    )

    logger.info('build_panel: loading panel for customer_ids=%s', cust_ids)
    with engine.connect() as conn:
        df = pd.read_sql(stmt, conn, params={'target_customer_ids': cust_ids})

    logger.info(
        'build_panel: %d rows across %d accounts × %d tenants',
        len(df),
        df['account_id'].nunique() if not df.empty else 0,
        df['tenant_id'].nunique() if not df.empty else 0,
    )
    return df


def panel_quality_report(
    df: pd.DataFrame,
    engine: Optional[Engine] = None,
    customer_ids: Optional[Iterable[int]] = None,
) -> dict:
    """Produce the G1.5 data-quality report for a constructed panel.

    Per PLAN_nrr_predictor_v3.md G1.5 hard-fail criteria:
      - Any account with > 40% missing months → flag
      - Any segment × tenant with < 3 accounts → flag
      - Any tenant with zero churn events historically → flag (sub-models 2/3
        still applicable; sub-model 1 won't fit on that tenant alone)
      - Any active account in `accounts` table absent from the panel → flag
        (G1.5 v2 enhancement — surfaces accounts with no health_scores at all)

    Returns a dict suitable for printing or rendering as a markdown table.
    """
    if df.empty:
        return {
            'status': 'EMPTY',
            'message': 'Panel is empty — hard fail at G1.5',
        }

    report: dict = {
        'status': 'OK',
        'total_rows': int(len(df)),
        'tenants': int(df['tenant_id'].nunique()),
        'accounts': int(df['account_id'].nunique()),
        'months_observed_per_account': {},
        'segment_x_tenant_counts': {},
        'outcome_event_counts': {},
        'flags': [],
    }

    # Per-account observed-month count
    months_per_acct = df.groupby('account_id').size()
    report['months_observed_per_account'] = {
        'min': int(months_per_acct.min()),
        'p50': float(months_per_acct.median()),
        'mean': float(months_per_acct.mean()),
        'max': int(months_per_acct.max()),
    }

    # Per-account expected vs observed (using account's first/last observed month)
    expected_months_per_acct = (
        df.groupby('account_id')['month']
        .agg(lambda s: ((s.max() - s.min()).days // 30) + 1)
    )
    pct_missing_per_acct = 1 - (months_per_acct / expected_months_per_acct)
    accounts_over_40pct_missing = pct_missing_per_acct[pct_missing_per_acct > 0.4]
    if len(accounts_over_40pct_missing) > 0:
        report['flags'].append({
            'type': 'high_missing_months',
            'severity': 'hard_fail',
            'count': int(len(accounts_over_40pct_missing)),
            'account_ids': accounts_over_40pct_missing.index.tolist(),
            'detail': '> 40% missing months — drop from v1 panel; flag for data-ops',
        })

    # Segment × tenant cardinality
    seg_tenant = (
        df.drop_duplicates(['account_id', 'tenant_id', 'segment'])
        .groupby(['tenant_id', 'segment'])
        .size()
    )
    report['segment_x_tenant_counts'] = {
        f'{tid}/{seg}': int(n) for (tid, seg), n in seg_tenant.items()
    }
    sparse_seg_tenant = seg_tenant[seg_tenant < 3]
    if len(sparse_seg_tenant) > 0:
        report['flags'].append({
            'type': 'sparse_segment_x_tenant',
            'severity': 'hard_fail',
            'pairs': [
                {'tenant_id': int(tid), 'segment': seg, 'n_accounts': int(n)}
                for (tid, seg), n in sparse_seg_tenant.items()
            ],
            'detail': '< 3 accounts in segment×tenant — dissolve into adjacent segment for that tenant',
        })

    # Outcome event counts per tenant
    for evt in ('is_churn_event', 'is_contraction_event', 'is_expansion_event'):
        report['outcome_event_counts'][evt] = (
            df.groupby('tenant_id')[evt].sum().astype(int).to_dict()
        )
    # Tenants with zero churn → sub-model 1 won't fit on them alone
    zero_churn_tenants = [
        tid for tid, n in report['outcome_event_counts']['is_churn_event'].items()
        if n == 0
    ]
    if zero_churn_tenants:
        report['flags'].append({
            'type': 'zero_churn_events',
            'severity': 'warn',
            'tenant_ids': zero_churn_tenants,
            'detail': (
                'Sub-model 1 (churn) will rely on hierarchical pooling from '
                'CDI prior + other tenants. Sub-models 2/3 still applicable.'
            ),
        })

    # G1.5 v2 — flag active accounts in `accounts` table absent from panel
    # (typically: account exists but has no health_scores rows yet)
    if engine is not None and customer_ids is not None:
        from sqlalchemy import bindparam, text
        from sqlalchemy.dialects.postgresql import ARRAY, INTEGER

        cust_ids = list(customer_ids)
        if cust_ids:
            stmt = text(
                "SELECT account_id, customer_id, account_name "
                "FROM accounts "
                "WHERE customer_id = ANY(:cids) "
                "  AND account_status = 'active'"
            ).bindparams(bindparam('cids', type_=ARRAY(INTEGER)))
            with engine.connect() as conn:
                active_accts = pd.read_sql(stmt, conn, params={'cids': cust_ids})

            in_panel = set(df['account_id'].unique().tolist())
            missing = active_accts[~active_accts['account_id'].isin(in_panel)]
            if not missing.empty:
                pct = round(100 * len(missing) / max(len(active_accts), 1), 1)
                report['flags'].append({
                    'type': 'active_accounts_missing_from_panel',
                    'severity': 'hard_fail' if pct > 20 else 'warn',
                    'count': int(len(missing)),
                    'pct_of_active': pct,
                    'account_ids_sample': missing['account_id'].head(10).tolist(),
                    'detail': (
                        f'{len(missing)} of {len(active_accts)} active accounts '
                        f'({pct}%) have no health_scores rows. They are invisible '
                        f'to the predictor until upstream (Wizard A/health pipeline) '
                        f'writes for them. Hard-fail at >20%; warn below.'
                    ),
                })

    if any(f['severity'] == 'hard_fail' for f in report['flags']):
        report['status'] = 'HARD_FAIL'

    return report


if __name__ == '__main__':
    # Dev runner: print panel + quality report for customer 393
    import json
    import os
    from sqlalchemy import create_engine

    db_url = os.environ.get(
        'DATABASE_URL',
        'postgresql://cspulse:cspulse@localhost:5433/cs_pulse',
    )
    engine = create_engine(db_url)
    df = build_panel(customer_ids=[393], engine=engine)
    print(f'Panel: {len(df)} rows, columns:')
    print(df.dtypes)
    print()
    print(df.head(5).to_string(index=False))
    print()
    print('=== G1.5 quality report ===')
    print(json.dumps(panel_quality_report(df), indent=2, default=str))
