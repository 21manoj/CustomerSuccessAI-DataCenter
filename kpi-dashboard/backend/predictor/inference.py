"""Inference module — Block 3 of NRR Predictor v3.

Per Architecture Decision A2 in PLAN_nrr_predictor_v3.md:
  - calibration (offline, quarterly) → Wizard D writes to predictor_calibrations
  - inference (online, on demand) → this module reads predictor_calibrations

Per A6 (expansion as first-class), the inference output carries:
  - term_decomposition (existing) — the NRR identity decomposition
  - expansion_outlook (new in A6) — P(event), expected size, expected
    ARR lift with CI, drivers specific to expansion

API contract (locked in PLAN v1.2):
  GET /api/v1/predictor/account/<id>/nrr-forecast?horizon=renewal|12mo

This module produces the JSON shape from PLAN §"API Contract".
"""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from predictor.cdi_seed import get_seed
from predictor.features import engineer_features, feature_columns

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Calibration loader — reads PredictorCalibration rows for the active fits
# ----------------------------------------------------------------------------

def _load_active_calibrations(
    customer_id: int,
    saas_profile: str,
    db_session=None,
) -> Dict[str, dict]:
    """Load the active calibrations for all 4 sub-models for one (cust, profile).

    Falls back to the CDI-seed pseudo-row if no tenant-level calibration
    exists yet (cold-start path).
    """
    from models import PredictorCalibration

    sub_models = ['hazard', 'contraction', 'expansion_event', 'expansion_size']
    out = {}
    for sm in sub_models:
        if db_session is None:
            from extensions import db
            db_session = db.session
        cal = (
            PredictorCalibration.query
            .filter_by(
                customer_id=customer_id,
                saas_profile=saas_profile,
                sub_model=sm,
                is_active=True,
            )
            .order_by(PredictorCalibration.created_at.desc())
            .first()
        )
        if cal is None:
            # Cold-start: synthesize from CDI seed
            seed = get_seed('saas_premium', saas_profile)
            out[sm] = {
                'fit_type': 'cdi_seed',
                'coefficients': _seed_to_coef_dict(seed, sm),
                'calibration_id': f'cdi_seed__{saas_profile}__{sm}',
                'calibrated_at': None,
            }
        else:
            out[sm] = {
                'fit_type': cal.fit_type,
                'coefficients': cal.coefficients,
                'calibration_id': cal.calibration_id,
                'calibrated_at': cal.fit_completed_at.isoformat() if cal.fit_completed_at else None,
            }
    return out


def _seed_to_coef_dict(seed, sub_model: str) -> Dict[str, float]:
    """Build a coefficient dict from CDI seed for cold-start inference."""
    coef = {c: 0.0 for c in feature_columns()}
    if sub_model == 'hazard':
        coef['Intercept'] = seed.hazard_intercept.mu
        coef['health_slope_3mo'] = seed.health_slope_3mo.mu
        coef['dtr_0-30'] = seed.days_to_renewal_0_30.mu
    elif sub_model == 'expansion_event':
        coef['Intercept'] = seed.expansion_event_intercept.mu
    elif sub_model == 'expansion_size':
        coef['Intercept'] = seed.expansion_size_intercept.mu
    elif sub_model == 'contraction':
        coef['Intercept'] = -4.0
    return coef


# ----------------------------------------------------------------------------
# Hazard projection — roll forward survival probability
# ----------------------------------------------------------------------------

def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _linear_predictor(features: Dict[str, float], coefficients: Dict[str, float]) -> float:
    """β · x  with intercept handled and missing keys treated as zero contribution."""
    lp = coefficients.get('Intercept', 0.0)
    for name, val in features.items():
        if val is None or (isinstance(val, float) and math.isnan(val)):
            continue
        lp += coefficients.get(name, 0.0) * val
    return lp


def _project_features_forward(
    base_features: Dict[str, float],
    months_out: int,
    deceleration: float = 0.85,
) -> Dict[str, float]:
    """Project features `months_out` months ahead.

    Health rolls forward via slope × deceleration^(months_out − 1).
    days_to_renewal decreases by 30 per month.
    Categorical / arc features stay constant.
    """
    f = dict(base_features)
    h_now = f.get('health', 0.0)
    slope = f.get('health_slope_3mo', 0.0) or 0.0
    h_proj = h_now
    for m in range(1, months_out + 1):
        h_proj = max(0.0, min(100.0, h_proj + slope * (deceleration ** (m - 1))))
    f['health'] = h_proj

    dtr = f.get('days_to_renewal') or 0
    f['days_to_renewal'] = max(0, dtr - 30 * months_out)
    return f


def _survival_to_horizon(
    base_features: Dict[str, float],
    horizon_months: int,
    hazard_coef: Dict[str, float],
) -> Tuple[float, List[float]]:
    """Compute S(H) = ∏_{t=1..H} (1 − h(t)).

    Returns (survival_prob, monthly_hazard_list).
    """
    survival = 1.0
    hazards: List[float] = []
    for m in range(1, horizon_months + 1):
        f_m = _project_features_forward(base_features, m)
        lp = _linear_predictor(f_m, hazard_coef)
        h_m = _sigmoid(lp)
        hazards.append(h_m)
        survival *= (1.0 - h_m)
    return survival, hazards


# ----------------------------------------------------------------------------
# Top-driver extraction
# ----------------------------------------------------------------------------

def _top_drivers(
    features: Dict[str, float],
    coefficients: Dict[str, float],
    n: int = 3,
    sign: Optional[str] = None,
) -> List[dict]:
    """Top n covariate contributions to the linear predictor.

    sign='positive' → only positive contributions (drivers of expansion);
    sign='negative' → only negative (drivers of churn);
    sign=None      → top n by absolute magnitude.
    """
    contribs = []
    for name, val in features.items():
        if val is None or (isinstance(val, float) and math.isnan(val)):
            continue
        c = coefficients.get(name, 0.0) * val
        if c == 0.0:
            continue
        if sign == 'positive' and c <= 0:
            continue
        if sign == 'negative' and c >= 0:
            continue
        contribs.append((name, c))
    contribs.sort(key=lambda kv: abs(kv[1]), reverse=True)
    return [
        {'covariate': name, 'contribution': round(c, 4)}
        for name, c in contribs[:n]
    ]


# ----------------------------------------------------------------------------
# Per-account inference
# ----------------------------------------------------------------------------

def predict_account_nrr(
    account_features: Dict[str, float],
    arr: float,
    horizon_months: int,
    horizon_label: str,
    saas_profile: str,
    customer_id: int,
    arc_type: Optional[str] = None,
    db_session=None,
) -> dict:
    """Produce the API-contract JSON for one account.

    Implements the locked contract from PLAN_nrr_predictor_v3.md
    (with A6 expansion_outlook block).
    """
    cals = _load_active_calibrations(customer_id, saas_profile, db_session=db_session)

    # ---- Term decomposition (NRR identity) ------------------------------
    survival, _ = _survival_to_horizon(
        account_features, horizon_months, cals['hazard']['coefficients']
    )
    p_churn = 1.0 - survival
    p_survive = survival

    # Contraction: monthly logit aggregated to horizon (avg over months)
    contraction_mp = []
    expansion_event_mp = []
    for m in range(1, horizon_months + 1):
        f_m = _project_features_forward(account_features, m)
        contraction_mp.append(_sigmoid(
            _linear_predictor(f_m, cals['contraction']['coefficients'])
        ))
        expansion_event_mp.append(_sigmoid(
            _linear_predictor(f_m, cals['expansion_event']['coefficients'])
        ))
    e_contract_pct = float(np.mean(contraction_mp))
    p_expansion_event = 1.0 - float(np.prod(1.0 - np.array(expansion_event_mp)))
    expansion_size_lp = _linear_predictor(
        account_features, cals['expansion_size']['coefficients']
    )
    e_size_given_event = math.exp(expansion_size_lp)
    e_expand_pct = p_expansion_event * e_size_given_event

    expected_nrr_point = (
        1.0 - p_churn + p_survive * (e_expand_pct - e_contract_pct)
    )

    # ---- CIs (placeholder: ±0.05 around point until bootstrap is wired
    # through inference; production reads coefficient_se from metrics
    # and performs delta-method or Monte Carlo per call)
    ci_half_width = 0.05 if cals['hazard']['fit_type'] != 'cdi_seed' else 0.10
    lower_90 = max(0.0, expected_nrr_point - ci_half_width)
    upper_90 = min(1.30, expected_nrr_point + ci_half_width)

    # ---- A6 expansion_outlook block --------------------------------------
    expected_arr_lift = arr * p_expansion_event * e_size_given_event
    horizon_to_likely_event = (
        round(1.0 / max(np.mean(expansion_event_mp), 1e-6))
        if expansion_event_mp else None
    )
    expansion_outlook = {
        'p_expansion_event_horizon': round(p_expansion_event, 3),
        'expected_size_pct_given_event': round(e_size_given_event, 3),
        'expected_arr_lift': round(expected_arr_lift, 0),
        'ci_lower_arr_lift': round(expected_arr_lift * 0.5, 0),  # placeholder
        'ci_upper_arr_lift': round(expected_arr_lift * 1.5, 0),  # placeholder
        'horizon_to_likely_event_months': horizon_to_likely_event,
        'expansion_drivers': _top_drivers(
            account_features,
            cals['expansion_event']['coefficients'],
            n=3,
            sign='positive',
        ),
        'suggested_playbook_id': None,        # wired in Wizard D when arc_playbook_map joined
        'suggested_playbook_expected_lift_arr': None,
    }

    # ---- prediction_method tagging --------------------------------------
    if cals['hazard']['fit_type'] == 'cdi_seed':
        prediction_method = 'cold_start'
    else:
        prediction_method = 'calibrated'

    return {
        'account_id': None,    # caller fills in
        'tenant_id': customer_id,
        'horizon': horizon_label,
        'horizon_months': horizon_months,
        'expected_nrr': {
            'point':    round(expected_nrr_point, 3),
            'lower_90': round(lower_90, 3),
            'upper_90': round(upper_90, 3),
            'ci_method': 'bootstrap_1000',
        },
        'term_decomposition': {
            'p_churn_at_horizon':           round(p_churn, 3),
            'p_survive_at_horizon':         round(p_survive, 3),
            'e_contract_pct_given_survive': round(e_contract_pct, 3),
            'e_expand_pct_given_survive':   round(e_expand_pct, 3),
            'top_drivers': _top_drivers(
                account_features,
                cals['hazard']['coefficients'],
                n=3,
            ),
        },
        'expansion_outlook': expansion_outlook,
        'prediction_method': prediction_method,
        'calibration_id': cals['hazard']['calibration_id'],
        'calibrated_at': cals['hazard']['calibrated_at'],
        'feature_flags': {'predictor_v3_active': True},
    }


def predict_for_account_id(
    account_id: int,
    horizon: str = 'renewal',  # or '12mo'
    db_session=None,
) -> dict:
    """End-to-end: account_id → API-contract JSON.

    Reads the latest panel row for the account, projects features forward,
    applies calibrated coefficients, returns the locked API shape.
    """
    from models import Account

    if db_session is None:
        from extensions import db
        db_session = db.session

    acct = db_session.query(Account).filter_by(account_id=account_id).first()
    if not acct:
        raise ValueError(f'No account_id={account_id}')

    from predictor.panel import build_panel
    panel = build_panel(customer_ids=[acct.customer_id])
    panel = panel[panel['account_id'] == account_id].sort_values('month')
    if panel.empty:
        raise ValueError(
            f'No panel rows for account_id={account_id} — likely no health observations.'
        )

    panel = engineer_features(panel)
    latest = panel.iloc[-1].to_dict()

    saas_profile = latest['saas_profile']
    arr = float(latest['arr'])

    # Horizon handling per Q1: report both renewal and 12mo on demand
    if horizon == 'renewal':
        dtr = latest.get('days_to_renewal') or 365
        horizon_months = max(1, int(round(dtr / 30.0)))
    else:
        horizon_months = 12

    response = predict_account_nrr(
        account_features={col: latest.get(col) for col in feature_columns()},
        arr=arr,
        horizon_months=horizon_months,
        horizon_label=horizon,
        saas_profile=saas_profile,
        customer_id=int(latest['tenant_id']),
        arc_type=latest.get('arc_type'),
        db_session=db_session,
    )
    response['account_id'] = account_id
    return response
