"""Predictor v3 Flask API — Block 3 of NRR Predictor v3.

Per Architecture Decision A2 in PLAN_nrr_predictor_v3.md, this module
serves the online inference HTTP layer. Per A3 + the rollback design,
two independent feature flags gate this:

  FEATURE_PREDICTOR_API     — API-level kill switch
                               Off → 503 with fallback hint; UI falls
                               back to Wizard B legacy NRR
  FEATURE_PREDICTOR_V3_UI   — UI-level swap; the dashboard reads this
                               to decide whether to render predictor v3
                               output or Wizard B legacy. Not enforced
                               here — the API still serves regardless of
                               this flag (so soak testing is possible
                               with API on / UI off).

Endpoints (per A6, three of them):

  GET /api/v1/predictor/account/<account_id>/nrr-forecast?horizon=renewal|12mo
  GET /api/v1/predictor/customer/<customer_id>/top-expansion-opportunities?horizon=12mo&limit=10
  GET /api/v1/predictor/customer/<customer_id>/top-at-risk-accounts?horizon=12mo&limit=10
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

predictor_api = Blueprint('predictor', __name__, url_prefix='/api/v1/predictor')


# ----------------------------------------------------------------------------
# Kill-switch helper
# ----------------------------------------------------------------------------

def _api_killed() -> Optional[tuple]:
    """Return (response, status) tuple if API is killed, else None.

    Per the rollback design in PLAN v1.2: when FEATURE_PREDICTOR_API=false,
    every endpoint returns 503 with an explicit fallback hint so the
    frontend can render Wizard B legacy NRR.
    """
    if os.environ.get('FEATURE_PREDICTOR_API', 'true').lower() != 'true':
        return jsonify({
            'error': 'predictor_disabled',
            'fallback': 'wizard_b_legacy',
            'message': (
                'NRR predictor v3 API is currently disabled '
                '(FEATURE_PREDICTOR_API=false). The dashboard should '
                'render Wizard B legacy NRR until the flag is restored.'
            ),
        }), 503
    return None


# ----------------------------------------------------------------------------
# Per-account endpoint
# ----------------------------------------------------------------------------

@predictor_api.route('/account/<int:account_id>/nrr-forecast', methods=['GET'])
def get_account_nrr_forecast(account_id: int):
    """Per-account NRR forecast — returns the locked PLAN v1.2 API contract."""
    killed = _api_killed()
    if killed:
        return killed

    horizon = request.args.get('horizon', 'renewal')
    if horizon not in ('renewal', '12mo'):
        return jsonify({
            'error': 'invalid_horizon',
            'message': "horizon must be 'renewal' or '12mo'",
        }), 400

    from extensions import db
    from predictor.inference import predict_for_account_id
    try:
        result = predict_for_account_id(
            account_id=account_id,
            horizon=horizon,
            db_session=db.session,
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({
            'error': 'no_panel_data',
            'message': str(e),
            'account_id': account_id,
        }), 404
    except Exception as e:
        logger.exception('predictor: per-account inference failed for account_id=%s', account_id)
        return jsonify({
            'error': 'predictor_internal',
            'message': str(e),
        }), 500


# ----------------------------------------------------------------------------
# Portfolio endpoints (per A6 — two ranked lists)
# ----------------------------------------------------------------------------

def _ranked_portfolio(
    customer_id: int,
    horizon: str,
    limit: int,
    sort_key: str,  # 'expansion_lift' | 'churn_loss'
):
    """Build a ranked list of per-account predictions for a tenant.

    Used by both top-expansion-opportunities and top-at-risk-accounts.
    Sort key determines the ranking direction; output schema is the
    full per-account prediction (as locked in the API contract) plus
    a ranking_score field so the UI can show the sort criterion.
    """
    from extensions import db
    from models import Account
    from predictor.inference import predict_for_account_id

    accts = (
        db.session.query(Account)
        .filter(Account.customer_id == customer_id)
        .filter(Account.account_status.notin_(['cancelled', 'inactive']))
        .all()
    )

    rows = []
    for a in accts:
        try:
            pred = predict_for_account_id(
                account_id=a.account_id,
                horizon=horizon,
                db_session=db.session,
            )
        except ValueError:
            continue  # account has no panel data — skip
        if sort_key == 'expansion_lift':
            score = float(pred['expansion_outlook'].get('expected_arr_lift', 0))
        elif sort_key == 'churn_loss':
            arr = float(a.revenue or 0)
            score = float(pred['term_decomposition']['p_churn_at_horizon']) * arr
        else:
            score = 0.0
        pred['account_name'] = a.account_name
        pred['arr'] = float(a.revenue or 0)
        pred['ranking_score'] = round(score, 0)
        rows.append(pred)

    rows.sort(key=lambda r: r['ranking_score'], reverse=True)
    return rows[:limit]


@predictor_api.route('/customer/<int:customer_id>/top-expansion-opportunities', methods=['GET'])
def get_top_expansion_opportunities(customer_id: int):
    """Top accounts by expected ARR lift (P(event) × E[size] × ARR).

    Per A6, this is the demo-leading endpoint for CRO/CFO dashboards.
    """
    killed = _api_killed()
    if killed:
        return killed

    horizon = request.args.get('horizon', '12mo')
    if horizon not in ('renewal', '12mo'):
        return jsonify({'error': 'invalid_horizon'}), 400
    try:
        limit = int(request.args.get('limit', 10))
    except ValueError:
        return jsonify({'error': 'invalid_limit'}), 400
    limit = max(1, min(limit, 100))

    rows = _ranked_portfolio(
        customer_id=customer_id,
        horizon=horizon,
        limit=limit,
        sort_key='expansion_lift',
    )
    return jsonify({
        'customer_id': customer_id,
        'horizon': horizon,
        'limit': limit,
        'sort_by': 'expected_arr_lift',
        'results': rows,
    }), 200


@predictor_api.route('/customer/<int:customer_id>/top-at-risk-accounts', methods=['GET'])
def get_top_at_risk_accounts(customer_id: int):
    """Top accounts by expected ARR loss (P(churn) × ARR).

    Companion to top-expansion-opportunities. UI renders by saas_profile:
    saas_enterprise leads with this in the at-risk side; saas_smb leads
    with the expansion view and renders this secondary.
    """
    killed = _api_killed()
    if killed:
        return killed

    horizon = request.args.get('horizon', '12mo')
    if horizon not in ('renewal', '12mo'):
        return jsonify({'error': 'invalid_horizon'}), 400
    try:
        limit = int(request.args.get('limit', 10))
    except ValueError:
        return jsonify({'error': 'invalid_limit'}), 400
    limit = max(1, min(limit, 100))

    rows = _ranked_portfolio(
        customer_id=customer_id,
        horizon=horizon,
        limit=limit,
        sort_key='churn_loss',
    )
    return jsonify({
        'customer_id': customer_id,
        'horizon': horizon,
        'limit': limit,
        'sort_by': 'expected_arr_loss',
        'results': rows,
    }), 200


# ----------------------------------------------------------------------------
# Health check (always responds — bypasses the kill switch)
# ----------------------------------------------------------------------------

@predictor_api.route('/health', methods=['GET'])
def health():
    """Liveness probe — always 200, includes both flags' state."""
    return jsonify({
        'status': 'ok',
        'feature_flags': {
            'FEATURE_PREDICTOR_API': os.environ.get('FEATURE_PREDICTOR_API', 'true'),
            'FEATURE_PREDICTOR_V3_UI': os.environ.get('FEATURE_PREDICTOR_V3_UI', 'false'),
        },
    }), 200
