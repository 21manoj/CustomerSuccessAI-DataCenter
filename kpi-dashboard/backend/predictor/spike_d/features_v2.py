"""Feature engineering for Option D spike.

Adds net-ARR-change outcomes derived from the panel's existing `arr` column.
Reuses production v1 covariates (minus tenure_in_panel which was dropped
in features.py during Phase 1 closeout).

Two-head architecture:
  - hazard       — outcome = is_churn_event (unchanged from v1)
  - net_uplift   — outcome = net_arr_change_pct_h{1,3,12} (new in v2)

The net-uplift outcome is FORWARD-LOOKING: for a panel row at month T,
the outcome is (arr_{T+H} − arr_T) / arr_T conditional on the account
still being in the panel at T+H AND not having churned in the interval.
This makes the outcome a clean continuous quantity that mirrors the
NRR identity:
    NRR_factor_account = arr_end / arr_start  (= 0 if churned)

For accounts that don't have T+H data (last H months of any account's
history), the outcome is NaN — those rows are unfittable for net_uplift
but still fittable for hazard.
"""
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd

# Reuse the production v1 feature set verbatim. The spike's hazard sub-model
# uses the same features as the production hazard sub-model — Exit 1 (hazard
# parity) requires this.
from predictor.features import engineer_features as v1_engineer_features
from predictor.features import feature_columns as v1_feature_columns


# Horizons we compute for net_arr_change_pct. Day 1 diagnostics decide which
# horizon the net_uplift sub-model fits on at Day 2.
NET_UPLIFT_HORIZONS_MONTHS = [1, 3, 12]


def feature_columns() -> List[str]:
    """Spike v2 covariates — identical to v1 (post-tenure-drop).

    Same set used by both hazard and net_uplift sub-models. Net-uplift's
    OUTCOME columns are NOT in this list (those are added by
    `engineer_features`).
    """
    return v1_feature_columns()


def net_uplift_outcome_columns() -> List[str]:
    """Outcome columns produced by `engineer_features` for net_uplift fits."""
    return [f'net_arr_change_pct_h{h}' for h in NET_UPLIFT_HORIZONS_MONTHS]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Apply v1 feature engineering, then add net-ARR-change outcomes.

    The forward-looking ARR change is computed per-account by sorting on
    month and shifting `arr` backward (negative shift = look at the
    future). Rows where the future row doesn't exist for that account
    get NaN — they're left in the DataFrame so callers can drop them
    explicitly when fitting net_uplift, but keep them for hazard fits
    (which only need the row's own outcome).

    Churn handling: rows whose [T+1, T+h] window contains a churn event
    are labeled NaN (not -1.0). Rationale: option D's identity is
    E[NRR] = P(survive) × (1 + E[Δ | survive]) — net_uplift is the
    conditional expectation given survival. Churning rows belong to the
    hazard model's likelihood, not net_uplift's. Including them as -1.0
    poisons the net_uplift fit with full-loss observations that the
    hazard model already accounts for at the architecture level.

    Notes
    -----
    The −1.0 churn-handling is only enabled if both `is_churn_event` and
    `arr` are present and non-null in the input rows. The function is
    safe on partial DataFrames (e.g., upstream tests that drop columns).
    """
    if df.empty:
        return df.copy()

    # Sort to make the per-account shift deterministic and correct
    df = df.sort_values(['account_id', 'month']).reset_index(drop=True)

    # Apply v1 engineering first (one-hots, log_arr, slopes, interactions)
    out = v1_engineer_features(df)

    # Forward-looking arr per account, for each horizon
    has_churn_col = 'is_churn_event' in out.columns
    if has_churn_col:
        # Pre-cast to int so shift produces NaN→fillable numeric, not object
        churn_int = out['is_churn_event'].astype(bool).astype(int)
    grp = out.groupby('account_id', sort=False)

    for h in NET_UPLIFT_HORIZONS_MONTHS:
        # arr at month T+h, per account (shift(-h) brings the future row up)
        future_arr = grp['arr'].shift(-h)
        net_change = (future_arr - out['arr']) / out['arr'].replace(0, np.nan)
        out[f'net_arr_change_pct_h{h}'] = net_change

        # Churn within window → outcome = NaN (drop from net_uplift fit).
        # Conditional on survival per option-D identity: net_uplift only
        # models E[Δ | survive]. The hazard model carries churn separately.
        if has_churn_col:
            churn_within_int = pd.Series(0, index=out.index, dtype=int)
            for k in range(1, h + 1):
                shifted = churn_int.groupby(out['account_id']).shift(-k).fillna(0).astype(int)
                churn_within_int = (churn_within_int | shifted)
            churn_within = churn_within_int.astype(bool)
            out.loc[churn_within, f'net_arr_change_pct_h{h}'] = np.nan

    return out


def net_uplift_fit_panel(df: pd.DataFrame, horizon: int = 12) -> pd.DataFrame:
    """Filter the engineered panel to rows fittable for net_uplift at horizon.

    Drops rows where the outcome is NaN (last `horizon` months of each
    account's history). Returns a DataFrame indexed identically to the
    fittable subset, ready to pass to `glmm_v2.fit_sub_model('net_uplift', ...)`.
    """
    outcome_col = f'net_arr_change_pct_h{horizon}'
    if outcome_col not in df.columns:
        raise KeyError(
            f'{outcome_col} not in DataFrame — call engineer_features first.'
        )
    feat_cols = feature_columns()
    return df.dropna(subset=[outcome_col] + feat_cols).copy()


def hazard_fit_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Filter the engineered panel to rows fittable for hazard.

    Same as v1 hazard fit — drops rows with NaN on slope/volatility (first
    months of each account) but keeps all other rows including the last H
    months that net_uplift can't use.
    """
    feat_cols = feature_columns()
    return df.dropna(subset=feat_cols + ['is_churn_event']).copy()
