"""Day 1 diagnostics — score Exit 3 (fat-tail tractability).

Exit 3 (from SPIKE_PLAN.md):
  Histogram of net_arr_change_pct_h12 shows < 5% of observations beyond
  ±50%, OR the two-part variant resolves the issue.

Run from backend root:

    python -m predictor.spike_d.scripts.diagnostics --customer-id 395

Or against a saved panel CSV (when DB is unavailable):

    python -m predictor.spike_d.scripts.diagnostics --panel-csv panel_395.csv

Outputs:
  - Tabular distribution summary (printed)
  - Exit 3 score (printed: PASS / FAIL_USE_TWO_PART / FAIL_KILL_SPIKE)
  - Histogram values per horizon (printed)
  - Optional matplotlib PNG if --plot is passed (path printed)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Allow `python -m predictor.spike_d.scripts.diagnostics` to find imports
# regardless of cwd.
_THIS = Path(__file__).resolve()
_BACKEND = _THIS.parents[3]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from predictor.spike_d.features_v2 import (   # noqa: E402
    NET_UPLIFT_HORIZONS_MONTHS,
    engineer_features,
)


def load_panel(customer_id: Optional[int], panel_csv: Optional[str]) -> pd.DataFrame:
    """Load panel from DB (preferred) or from CSV fallback.

    DB path uses the production `build_panel` function, which the spike
    is not allowed to modify. CSV path lets diagnostics run in
    environments where the DB is unreachable.
    """
    if panel_csv:
        df = pd.read_csv(panel_csv, parse_dates=['month'])
        # Postgres COPY emits booleans as 'f'/'t'; pandas reads as strings.
        # Normalize: any string-typed boolean column → real bool.
        for col in ('is_churn_event', 'is_contraction_event', 'is_expansion_event'):
            s = df[col]
            if s.dtype == object:
                df[col] = s.map({'t': True, 'f': False, True: True, False: False}).astype(bool)
            else:
                df[col] = s.astype(bool)
        return df
    if customer_id is None:
        raise ValueError('Provide --customer-id or --panel-csv')
    from predictor.build_panel import build_panel
    return build_panel(customer_ids=[customer_id])


def histogram_summary(values: pd.Series, bins=None) -> dict:
    """Compact summary of a numeric distribution suitable for printing."""
    if bins is None:
        bins = [-np.inf, -1.0, -0.5, -0.2, -0.05, 0.0, 0.05, 0.2, 0.5, 1.0, np.inf]
    s = values.dropna()
    if s.empty:
        return {'n': 0, 'note': 'no observations'}
    cuts = pd.cut(s, bins=bins, include_lowest=True)
    counts = cuts.value_counts().sort_index()
    return {
        'n': int(s.shape[0]),
        'mean': float(s.mean()),
        'median': float(s.median()),
        'std': float(s.std(ddof=1)),
        'p01': float(s.quantile(0.01)),
        'p05': float(s.quantile(0.05)),
        'p25': float(s.quantile(0.25)),
        'p75': float(s.quantile(0.75)),
        'p95': float(s.quantile(0.95)),
        'p99': float(s.quantile(0.99)),
        'min': float(s.min()),
        'max': float(s.max()),
        'pct_zero': round(100.0 * float((s == 0).mean()), 2),
        'pct_negative': round(100.0 * float((s < 0).mean()), 2),
        'pct_positive': round(100.0 * float((s > 0).mean()), 2),
        'pct_beyond_50pct': round(100.0 * float((s.abs() > 0.5).mean()), 2),
        'pct_beyond_100pct': round(100.0 * float((s.abs() > 1.0).mean()), 2),
        'bin_counts': {str(k): int(v) for k, v in counts.items()},
    }


def score_exit_3(summary_h12: dict) -> dict:
    """Score Exit 3: pass / fail_use_two_part / fail_kill_spike.

    Per spike plan:
      - PASS                   : pct_beyond_50pct < 5
      - FAIL_USE_TWO_PART      : 5 <= pct_beyond_50pct <= 25 (manageable
                                 with a logit + Gaussian two-part model)
      - FAIL_KILL_SPIKE        : pct_beyond_50pct > 25 (the outcome is too
                                 wild to be modeled cleanly even two-part —
                                 keep 4-head)

    The two-part threshold (25%) is judgement, not from the plan; we use it
    so the spike doesn't quietly accept a heavy-tailed outcome that will
    misbehave under bootstrap. If pct_beyond exceeds 25, we want a hard
    decision, not a "let's try harder."
    """
    pct = summary_h12.get('pct_beyond_50pct', 100.0)
    if pct < 5.0:
        verdict = 'PASS'
        action = 'Single-Gaussian net_uplift is viable. Proceed to Day 2.'
    elif pct <= 25.0:
        verdict = 'FAIL_USE_TWO_PART'
        action = (
            'Single-Gaussian rejected; switch glmm_v2 to two-part model '
            '(logit on Δ≠0, Gaussian on signed Δ given non-zero). Day 2 '
            'sub-model count rises from 2 to 3 — still fewer than the '
            'production 4-head and identification still cleaner.'
        )
    else:
        verdict = 'FAIL_KILL_SPIKE'
        action = (
            'pct_beyond_50pct > 25 — the net-Δ outcome is too heavy-tailed '
            'on this panel to fit cleanly. Kill the spike, keep 4-head, '
            're-evaluate when more panel data accumulates.'
        )
    return {
        'pct_beyond_50pct': pct,
        'verdict': verdict,
        'action': action,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Day 1 diagnostics for Option D spike (Exit 3 score).'
    )
    parser.add_argument('--customer-id', type=int, default=395)
    parser.add_argument(
        '--panel-csv',
        type=str,
        default=None,
        help='Path to a CSV dump of the panel (overrides --customer-id).',
    )
    parser.add_argument(
        '--plot',
        action='store_true',
        help='Save histogram PNGs alongside the JSON output.',
    )
    parser.add_argument(
        '--out-dir',
        type=str,
        default='predictor/spike_d/diagnostics_out',
        help='Directory for saved artifacts.',
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f'[1/4] Loading panel (customer_id={args.customer_id}, csv={args.panel_csv})')
    panel = load_panel(args.customer_id, args.panel_csv)
    print(f'      {len(panel)} rows × {panel["account_id"].nunique()} accounts'
          f' × {panel["tenant_id"].nunique()} tenants')

    print('[2/4] Engineering features (v2: v1 features + net_arr_change outcomes)')
    eng = engineer_features(panel)

    print('[3/4] Distribution summary per horizon')
    summaries: dict = {}
    for h in NET_UPLIFT_HORIZONS_MONTHS:
        col = f'net_arr_change_pct_h{h}'
        s = histogram_summary(eng[col])
        summaries[col] = s
        n_fittable = int(eng[col].dropna().shape[0])
        print(f'\n  --- {col} (n_fittable={n_fittable}) ---')
        print(f'    mean={s.get("mean", float("nan")):.4f}  '
              f'median={s.get("median", float("nan")):.4f}  '
              f'std={s.get("std", float("nan")):.4f}')
        print(f'    pct_zero={s.get("pct_zero")}%  '
              f'pct_neg={s.get("pct_negative")}%  '
              f'pct_pos={s.get("pct_positive")}%')
        print(f'    pct_beyond_50%={s.get("pct_beyond_50pct")}%  '
              f'pct_beyond_100%={s.get("pct_beyond_100pct")}%')
        print(f'    p01={s.get("p01"):.3f}  p05={s.get("p05"):.3f}  '
              f'p25={s.get("p25"):.3f}  p75={s.get("p75"):.3f}  '
              f'p95={s.get("p95"):.3f}  p99={s.get("p99"):.3f}')

    print('\n[4/4] Exit 3 score (using h=12 outcome)')
    exit_3 = score_exit_3(summaries['net_arr_change_pct_h12'])
    print(f'    pct_beyond_50pct = {exit_3["pct_beyond_50pct"]}%')
    print(f'    VERDICT: {exit_3["verdict"]}')
    print(f'    action : {exit_3["action"]}')

    if args.plot:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            for h in NET_UPLIFT_HORIZONS_MONTHS:
                col = f'net_arr_change_pct_h{h}'
                vals = eng[col].dropna().clip(-1.5, 1.5)
                fig, ax = plt.subplots(figsize=(7, 4))
                ax.hist(vals, bins=60)
                ax.set_title(f'{col} distribution (clipped to ±1.5)')
                ax.set_xlabel('net ARR change pct')
                ax.set_ylabel('count')
                ax.axvline(-0.5, color='red', linestyle='--', alpha=0.5)
                ax.axvline(0.5, color='red', linestyle='--', alpha=0.5)
                fig.tight_layout()
                out_path = out_dir / f'hist_{col}.png'
                fig.savefig(out_path)
                plt.close(fig)
                print(f'    histogram saved → {out_path}')
        except ImportError:
            print('    [skip] matplotlib not installed; histogram PNGs skipped')

    out_path = out_dir / 'day1_diagnostics.json'
    with open(out_path, 'w') as f:
        json.dump(
            {
                'customer_id': args.customer_id,
                'panel_csv': args.panel_csv,
                'n_rows': int(len(panel)),
                'n_accounts': int(panel['account_id'].nunique()),
                'summaries': summaries,
                'exit_3': exit_3,
            },
            f,
            indent=2,
            default=str,
        )
    print(f'\nFull results → {out_path}')

    sys.exit(0 if exit_3['verdict'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
