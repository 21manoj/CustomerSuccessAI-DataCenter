"""Feature engineering — Block 1 of NRR Predictor v3.

The panel from `panel.py` carries raw covariates (health, slope, days_to_renewal,
arc_type, segment, etc.). The hazard / contraction / expansion sub-models need
these turned into model-ready features: one-hot encodings, interactions,
imputation flags, and a few derived quantities not worth doing in SQL.

Two functions:
  - `engineer_features(df)` → DataFrame ready for `statsmodels.MixedLM` /
    `lme4::glmer` consumption.
  - `feature_columns()` → list of model covariate column names, ordered.

Per A6: same panel, same features, three outcome targets (is_churn_event,
is_contraction_event, is_expansion_event). Features are model-agnostic.
"""

from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------------
# Categorical level definitions — pinned for stable one-hot dimensionality
# across calibration runs. Adding a new level requires re-fitting; missing
# levels are encoded as the reference (first listed).
# ----------------------------------------------------------------------------

ARC_TYPES = [
    'land_and_expand',           # reference (most common in saas_premium)
    'expansion_champion',
    'steady_growth',
    'recovery',
    'competitive_displacement',
    'silent_churn',
    'exec_sponsor_change',
    'stalled_deployment',
    'seasonal_surge',
]

SEGMENTS_ENTERPRISE = ['mid_market', 'enterprise', 'strategic']
SEGMENTS_SMB = ['smb', 'mid_market', 'enterprise']

DAYS_TO_RENEWAL_BANDS = ['0-30', '31-90', '91-180', '181-365', '>365', 'unknown']
ARR_BANDS = ['<10K', '10K-100K', '100K-1M', '1M-10M', '10M+']


def feature_columns() -> List[str]:
    """Ordered list of model covariate columns produced by engineer_features.

    Used by the GLMM fit code and the inference code to ensure column-order
    parity between training and serving (mismatch = silent prediction errors).
    """
    cols: List[str] = []

    # Continuous / numeric covariates
    cols.extend([
        'health',
        'health_slope_1mo',
        'health_slope_3mo',
        'volatility_3mo',
        'tenure_in_panel',
        'log_arr',
    ])

    # Imputation flags — important for hazard model interpretability
    cols.extend([
        'health_slope_1mo_missing',
        'health_slope_3mo_missing',
        'volatility_3mo_missing',
    ])

    # One-hot: arc_type (drop reference 'land_and_expand')
    for arc in ARC_TYPES[1:]:
        cols.append(f'arc_{arc}')

    # One-hot: days_to_renewal_band (drop reference '>365')
    for band in DAYS_TO_RENEWAL_BANDS:
        if band != '>365':
            cols.append(f'dtr_{band}')

    # One-hot: arr_band (drop reference '100K-1M' — the SaaS modal band)
    for band in ARR_BANDS:
        if band != '100K-1M':
            cols.append(f'arr_{band}')

    # Interaction terms surfaced for the hazard model
    cols.extend([
        'health_slope_3mo_x_dtr_0_30',   # slope effect strongest near renewal
        'arc_competitive_displacement_x_recovering',
    ])

    return cols


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Turn raw panel into model-ready feature matrix.

    Input: DataFrame from `build_panel()`.
    Output: same rows, additional feature columns appended. Original
    columns preserved for downstream interpretability.
    """
    if df.empty:
        return df.copy()

    out = df.copy()

    # Continuous covariates
    out['log_arr'] = np.log1p(out['arr'].astype(float))

    # Imputation flags — flip-on when source covariate is null. Keep the
    # original null in the column too; missing values get imputed downstream
    # by the hazard model's missing-data handler (forward-fill within account).
    for col in ['health_slope_1mo', 'health_slope_3mo', 'volatility_3mo']:
        out[f'{col}_missing'] = out[col].isna().astype(int)

    # One-hot: arc_type
    for arc in ARC_TYPES[1:]:
        out[f'arc_{arc}'] = (out['arc_type'] == arc).astype(int)

    # One-hot: days_to_renewal_band
    for band in DAYS_TO_RENEWAL_BANDS:
        if band != '>365':
            out[f'dtr_{band}'] = (out['days_to_renewal_band'] == band).astype(int)

    # One-hot: arr_band
    for band in ARR_BANDS:
        if band != '100K-1M':
            out[f'arr_{band}'] = (out['arr_band'] == band).astype(int)

    # Interaction terms
    out['health_slope_3mo_x_dtr_0_30'] = (
        out['health_slope_3mo'].fillna(0) * out['dtr_0-30']
    )
    # Competitive-displacement accounts that are recovering signal high
    # expansion potential per A6 — capture the interaction explicitly.
    out['arc_competitive_displacement_x_recovering'] = (
        out['arc_competitive_displacement']
        * (out['health_slope_3mo'].fillna(0) > 0).astype(int)
    )

    return out
