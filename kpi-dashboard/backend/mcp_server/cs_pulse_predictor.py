#!/usr/bin/env python3
"""
CS Pulse MCP — Predictor v3 Tools (per-account NRR forecasting).

Wraps `predictor.inference.predict_for_account_id` and the existing
`/api/v1/predictor/*` endpoints as MCP tools so Ask AI / Claude.ai / any
external LLM consumer can reach Predictor v3 directly.

These tools answer the FORWARD per-account questions:
  - "What's account X's NRR forecast at renewal / 12mo?"
  - "Why does the model predict that value?" (top drivers + decomposition)
  - "What's the portfolio NRR forecast?" (ARR-weighted aggregate)
  - "Which accounts are top expansion bets?"
  - "Which accounts are top at-risk?"

The existing `get_nrr_forecast` tool in cs_pulse_revenue.py stays — that's
the BACKWARD counterfactual (Wizard B). Both engines coexist by design;
see SIGNAL_TO_NRR_AUDIT_NARRATIVE.md for the role split.

Tools registered:
  - get_account_nrr_forecast
  - get_portfolio_nrr_forecast_v3
  - get_top_expansion_opportunities_v3
  - get_top_at_risk_accounts_v3
"""

import logging
from typing import Optional

from cs_pulse_mcp_server import (
    mcp,
    _check_mcp_enabled,
    _require_auth,
    _require_account_auth,
    _get_flask_app,
    ToolError,
)

logger = logging.getLogger(__name__)


# ===================================================================
# Tool: get_account_nrr_forecast
# ===================================================================

@mcp.tool
def get_account_nrr_forecast(account_id: int, horizon: str = '12mo') -> dict:
    """Forward NRR forecast for a single account (Predictor v3).

    Returns the per-account NRR forecast with full decomposition: point
    estimate, 90% CI bounds, churn/survive/expand/contract terms, top
    feature drivers contributing to the prediction, expansion outlook,
    and calibration provenance.

    Use this when the user asks:
      - "What's account X's NRR forecast?"
      - "Why is account X predicted at Y% NRR?"
      - "What's the expected expansion lift for account X?"

    For PORTFOLIO-level NRR, use get_portfolio_nrr_forecast_v3 instead.
    For BACKWARD counterfactual (with vs without CS Pulse), use the
    existing get_nrr_forecast tool (Wizard B).

    Args:
        account_id: The account_id to forecast
        horizon: 'renewal' (default account-specific renewal date) or
                 '12mo' (12 months from now). Defaults to '12mo'.

    Returns:
        dict with expected_nrr {point, lower_90, upper_90, ci_method,
        ci_disclosure}, term_decomposition {p_churn_at_horizon,
        p_survive_at_horizon, e_contract_pct_given_survive,
        e_expand_pct_given_survive, top_drivers[]}, expansion_outlook
        {p_expansion_event_horizon, expected_size_pct_given_event,
        expected_arr_lift, ci_lower/upper, expansion_drivers[]},
        prediction_method ('calibrated' | 'cold_start'), calibration_id,
        calibrated_at.
    """
    _check_mcp_enabled()
    _require_account_auth(account_id)
    app = _get_flask_app()

    with app.app_context():
        try:
            from predictor.inference import predict_for_account_id
        except ImportError as e:
            raise ToolError(f'Predictor v3 not available: {e}')

        if horizon not in ('renewal', '12mo'):
            raise ToolError(
                f"horizon must be 'renewal' or '12mo', got {horizon!r}"
            )

        try:
            result = predict_for_account_id(account_id=account_id, horizon=horizon)
        except ValueError as e:
            raise ToolError(str(e))
        except Exception as e:
            logger.exception('predict_for_account_id failed')
            raise ToolError(f'Predictor v3 inference failed: {e}')

        return result


# ===================================================================
# Tool: get_portfolio_nrr_forecast_v3
# ===================================================================

@mcp.tool
def get_portfolio_nrr_forecast_v3(
    customer_id: int,
    horizon: str = '12mo',
) -> dict:
    """Portfolio-level forward NRR forecast (Predictor v3, ARR-weighted).

    Runs per-account Predictor v3 inference across all accounts in the
    customer's portfolio and aggregates to an ARR-weighted average NRR
    plus a simple-average NRR. Excludes accounts with $0 ARR from the
    ARR-weighted denominator (typically already-churned accounts).

    Use this when the user asks:
      - "What's our forward 12mo NRR portfolio-wide?"
      - "What's the v3 portfolio prediction?"
      - "How does the v3 forecast compare to the Wizard B counterfactual?"

    For BACKWARD counterfactual (with vs without CS Pulse), use the
    existing get_nrr_forecast tool — that runs Wizard B and answers
    a different question.

    Args:
        customer_id: The customer (tenant) ID
        horizon: 'renewal' or '12mo' (default '12mo')

    Returns:
        dict with arr_weighted_nrr, simple_avg_nrr, account_count,
        active_account_count, prediction_method_counts (e.g.,
        {'calibrated': 30}), top_5_nrr, bottom_5_nrr, horizon,
        calibration_freshness (most recent Wizard D calibration), and
        a method_note explaining the math.
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    if horizon not in ('renewal', '12mo'):
        raise ToolError(
            f"horizon must be 'renewal' or '12mo', got {horizon!r}"
        )

    with app.app_context():
        from models import Account, PredictorCalibration
        from predictor.inference import predict_for_account_id

        accts = Account.query.filter_by(customer_id=customer_id).all()
        if not accts:
            return {
                'customer_id': customer_id,
                'arr_weighted_nrr': None,
                'account_count': 0,
                'message': f'No accounts found for customer {customer_id}',
            }

        rows = []
        failed = 0
        for a in accts:
            try:
                pred = predict_for_account_id(
                    account_id=a.account_id, horizon=horizon
                )
                rows.append({
                    'account_id': a.account_id,
                    'account_name': a.account_name,
                    'arr': float(a.revenue or 0),
                    'nrr_point': pred['expected_nrr']['point'],
                    'method': pred.get('prediction_method', '?'),
                })
            except Exception as e:
                failed += 1
                logger.warning(
                    f'portfolio_nrr_forecast_v3 skipped account {a.account_id}: {e}'
                )

        if not rows:
            return {
                'customer_id': customer_id,
                'arr_weighted_nrr': None,
                'account_count': len(accts),
                'failed': failed,
                'message': 'All per-account predictions failed',
            }

        total_arr = sum(r['arr'] for r in rows)
        arr_weighted = (
            sum(r['arr'] * r['nrr_point'] for r in rows) / total_arr
            if total_arr > 0 else 0
        )
        simple_avg = sum(r['nrr_point'] for r in rows) / len(rows)

        method_counts: dict[str, int] = {}
        for r in rows:
            method_counts[r['method']] = method_counts.get(r['method'], 0) + 1

        rows.sort(key=lambda r: r['nrr_point'])
        bottom_5 = [
            {'account_id': r['account_id'], 'account_name': r['account_name'],
             'arr': r['arr'], 'nrr': round(r['nrr_point'], 4)}
            for r in rows[:5]
        ]
        top_5 = [
            {'account_id': r['account_id'], 'account_name': r['account_name'],
             'arr': r['arr'], 'nrr': round(r['nrr_point'], 4)}
            for r in rows[-5:]
        ]

        # Calibration freshness
        latest_cal = (
            PredictorCalibration.query
            .filter(PredictorCalibration.is_active == True)  # noqa: E712
            .order_by(PredictorCalibration.created_at.desc())
            .first()
        )
        cal_freshness = (
            {
                'calibration_id': latest_cal.calibration_id,
                'fit_type': latest_cal.fit_type,
                'created_at': latest_cal.created_at.isoformat(),
            }
            if latest_cal else None
        )

        active_count = sum(1 for r in rows if r['arr'] > 0)

        return {
            'customer_id': customer_id,
            'horizon': horizon,
            'arr_weighted_nrr': round(arr_weighted, 4),
            'simple_avg_nrr': round(simple_avg, 4),
            'total_arr': round(total_arr, 2),
            'account_count': len(rows),
            'active_account_count': active_count,
            'failed': failed,
            'prediction_method_counts': method_counts,
            'top_5_nrr': top_5,
            'bottom_5_nrr': bottom_5,
            'calibration_freshness': cal_freshness,
            'method_note': (
                'arr_weighted_nrr = Σ(ARR × per-account expected_nrr) ÷ Σ ARR. '
                'Excludes $0-ARR accounts from the weight (typically churned). '
                'simple_avg_nrr counts all accounts equally — drops below '
                'arr_weighted when churned accounts are present. Differs '
                'from Wizard B counterfactual NRR (use get_nrr_forecast for '
                'that — different question, different math).'
            ),
        }


# ===================================================================
# Tool: get_top_expansion_opportunities_v3
# ===================================================================

@mcp.tool
def get_top_expansion_opportunities_v3(
    customer_id: int,
    horizon: str = '12mo',
    limit: int = 10,
) -> dict:
    """Top expansion opportunities ranked by Predictor v3 expected ARR lift.

    Per-account expansion forecast (probability of expansion × expected
    size × ARR) over the horizon, sorted descending. Each entry includes
    the expansion outlook breakdown so the LLM can explain why an account
    is ranked where it is.

    Use this when the user asks:
      - "Where should we focus expansion plays this quarter?"
      - "Top expansion bets in the portfolio?"
      - "Which accounts have the highest upside?"

    Args:
        customer_id: The customer (tenant) ID
        horizon: 'renewal' or '12mo' (default '12mo')
        limit: Max number of results to return (default 10)

    Returns:
        dict with results[] (sorted by expected_arr_lift desc), customer_id,
        horizon, limit. Each result entry contains account_id, account_name,
        arr, expansion_outlook with full drivers and CI bounds.
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    if horizon not in ('renewal', '12mo'):
        raise ToolError(
            f"horizon must be 'renewal' or '12mo', got {horizon!r}"
        )

    with app.app_context():
        from models import Account
        from predictor.inference import predict_for_account_id

        accts = Account.query.filter_by(customer_id=customer_id).all()
        rows = []
        for a in accts:
            try:
                pred = predict_for_account_id(
                    account_id=a.account_id, horizon=horizon
                )
                outlook = pred.get('expansion_outlook') or {}
                rows.append({
                    'account_id': a.account_id,
                    'account_name': a.account_name,
                    'arr': float(a.revenue or 0),
                    'expansion_outlook': outlook,
                    'expected_arr_lift': outlook.get('expected_arr_lift', 0),
                    'calibration_id': pred.get('calibration_id'),
                    'calibrated_at': pred.get('calibrated_at'),
                })
            except Exception as e:
                logger.warning(
                    f'top_expansion_v3 skipped account {a.account_id}: {e}'
                )

        rows.sort(key=lambda r: r['expected_arr_lift'], reverse=True)
        return {
            'customer_id': customer_id,
            'horizon': horizon,
            'limit': limit,
            'results': rows[:limit],
        }


# ===================================================================
# Tool: get_top_at_risk_accounts_v3
# ===================================================================

@mcp.tool
def get_top_at_risk_accounts_v3(
    customer_id: int,
    horizon: str = '12mo',
    limit: int = 10,
) -> dict:
    """Top at-risk accounts ranked by Predictor v3 forecast NRR loss.

    Per-account NRR forecast over the horizon, sorted ascending (lowest
    NRR = highest risk). Each entry includes the term decomposition
    (p_churn, p_survive, contract/expand %) and top drivers so the LLM
    can explain the risk.

    Use this when the user asks:
      - "Which accounts are most at-risk?"
      - "Where should defensive playbooks fire?"
      - "What's hurting NRR most?"

    Args:
        customer_id: The customer (tenant) ID
        horizon: 'renewal' or '12mo' (default '12mo')
        limit: Max number of results to return (default 10)

    Returns:
        dict with results[] (sorted by expected_nrr asc), customer_id,
        horizon, limit. Each result entry includes account_id,
        account_name, arr, expected_nrr {point, ci}, term_decomposition
        {p_churn, p_survive, e_contract_pct, e_expand_pct, top_drivers}.
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    if horizon not in ('renewal', '12mo'):
        raise ToolError(
            f"horizon must be 'renewal' or '12mo', got {horizon!r}"
        )

    with app.app_context():
        from models import Account
        from predictor.inference import predict_for_account_id

        accts = Account.query.filter_by(customer_id=customer_id).all()
        rows = []
        for a in accts:
            try:
                pred = predict_for_account_id(
                    account_id=a.account_id, horizon=horizon
                )
                rows.append({
                    'account_id': a.account_id,
                    'account_name': a.account_name,
                    'arr': float(a.revenue or 0),
                    'expected_nrr': pred.get('expected_nrr', {}),
                    'term_decomposition': pred.get('term_decomposition', {}),
                    'forecast_arr_loss': round(
                        float(a.revenue or 0) * (
                            1 - pred['expected_nrr']['point']
                        ),
                        2,
                    ),
                    'calibration_id': pred.get('calibration_id'),
                    'calibrated_at': pred.get('calibrated_at'),
                })
            except Exception as e:
                logger.warning(
                    f'top_at_risk_v3 skipped account {a.account_id}: {e}'
                )

        # Sort by expected_nrr point ascending (lowest NRR = highest risk)
        rows.sort(key=lambda r: r['expected_nrr'].get('point', 1.0))
        return {
            'customer_id': customer_id,
            'horizon': horizon,
            'limit': limit,
            'results': rows[:limit],
        }
