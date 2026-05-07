"""Confirm v2 build_panel.sql changed only `arr` and `arr_band`.

Pre-flight check before swapping v1→v2 in production. Loads two CSV
dumps of the same customer's panel (one from v1 SQL, one from v2 SQL)
and asserts:

  - Same row count
  - Same (account_id, month) keys
  - Every column except `arr` and `arr_band` is byte-identical row-by-row

If anything else differs, v2 has an unintended side-effect and the swap
should be held until it's understood.

Usage:

    python -m predictor.spike_d.scripts.check_v1_v2_parity \\
        --v1 predictor/spike_d/panel_cust_395.csv \\
        --v2 predictor/spike_d/panel_cust_395_v2.csv

Exit codes:
  0 — parity confirmed (only arr / arr_band differ)
  1 — parity broken (other columns shifted or row sets differ)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


# Columns that v2 is permitted to differ from v1 on.
EXPECTED_DIFFERENT = {'arr', 'arr_band'}


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce booleans + dates so v1/v2 comparisons aren't dtype-confused."""
    df = df.copy()
    df['month'] = pd.to_datetime(df['month'])
    for col in ('is_churn_event', 'is_contraction_event', 'is_expansion_event'):
        if df[col].dtype == object:
            df[col] = df[col].map({'t': True, 'f': False, True: True, False: False}).astype(bool)
        else:
            df[col] = df[col].astype(bool)
    # Sort to a canonical order for direct row-by-row comparison
    return df.sort_values(['account_id', 'month']).reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--v1', required=True, help='Path to v1 panel CSV dump')
    parser.add_argument('--v2', required=True, help='Path to v2 panel CSV dump')
    args = parser.parse_args()

    v1 = normalize(pd.read_csv(args.v1))
    v2 = normalize(pd.read_csv(args.v2))

    print(f'v1: {len(v1):>4d} rows, {v1["account_id"].nunique():>3d} accounts')
    print(f'v2: {len(v2):>4d} rows, {v2["account_id"].nunique():>3d} accounts')

    if list(v1.columns) != list(v2.columns):
        print('FAIL: column lists differ')
        print(f'  v1 cols: {list(v1.columns)}')
        print(f'  v2 cols: {list(v2.columns)}')
        sys.exit(1)

    if len(v1) != len(v2):
        print(f'FAIL: row counts differ ({len(v1)} vs {len(v2)})')
        sys.exit(1)

    # Verify keys line up — sorted normalize means rows should match by index
    keys_match = (
        (v1['account_id'].values == v2['account_id'].values).all()
        and (v1['month'].values == v2['month'].values).all()
    )
    if not keys_match:
        print('FAIL: (account_id, month) sequences differ between v1 and v2')
        sys.exit(1)

    # For every non-allowed column, count cell-level mismatches
    fail = False
    print('\nColumn-by-column parity:')
    for col in v1.columns:
        v1c = v1[col]
        v2c = v2[col]
        # Element-wise comparison: NaN==NaN should be treated as equal
        diff_mask = ~((v1c == v2c) | (v1c.isna() & v2c.isna()))
        n_diff = int(diff_mask.sum())
        flag = ''
        if col in EXPECTED_DIFFERENT:
            flag = '(expected)' if n_diff > 0 else '(no change — odd)'
        else:
            if n_diff > 0:
                fail = True
                flag = 'FAIL'
        print(f'  {col:<25s} mismatches={n_diff:>4d}  {flag}')

    if fail:
        print('\nOverall: FAIL — non-allowed columns shifted between v1 and v2.')
        sys.exit(1)

    # Bonus: summarize what the arr / arr_band changes look like
    print('\narr summary:')
    print(f'  rows where v1.arr != v2.arr: {int((v1["arr"] != v2["arr"]).sum())}')
    print(f'  accounts with any arr change: '
          f'{int((v1.groupby("account_id")["arr"].apply(list) != v2.groupby("account_id")["arr"].apply(list)).sum())}')
    n_band_changes = int((v1['arr_band'] != v2['arr_band']).sum())
    print(f'  rows where v1.arr_band != v2.arr_band: {n_band_changes}')

    print('\nOverall: PASS — only arr and arr_band changed. Safe to swap v2 in as production.')
    sys.exit(0)


if __name__ == '__main__':
    main()
