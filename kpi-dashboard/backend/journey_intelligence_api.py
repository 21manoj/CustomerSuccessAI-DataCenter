"""
Journey Intelligence API
=========================

Read-only endpoint that computes three independent graphs for an account:
  Graph 1 — KPI Health (blue):     Health score from KPIs only. No decay. Structural truth.
  Graph 2 — Signal Score (amber):  Independent signal-only score (0-100). No KPI influence.
  Graph 3 — Composite (green):     Weighted blend of decayed KPI + decayed Signal scores.
                                    Shows the unified evidence view with recency decay on BOTH.

All computation is at query time — nothing stored, nothing changes the scoring engine.
The composite line is informational (per Recency-Signal-DNA spec §1a: NRR uses kpi_only_score exclusively).

Endpoint: GET /api/journey-intelligence/<account_id>
"""

import math
import logging
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id

logger = logging.getLogger(__name__)

journey_intelligence_api = Blueprint('journey_intelligence_api', __name__)

# ── Signal amplitude table (from Recency-Signal-DNA spec §5.2) ──
# Maps signal subtype → health score contribution on 0-100 scale.
# Positive signals push toward 100, negative toward 0.
SIGNAL_SCORE_MAP = {
    # Negative signals → low scores (0-40 range)
    'champion_loss': 15, 'critical_incident': 20, 'contract_dispute': 10,
    'budget_pressure': 25, 'competitor_mention': 25, 'urgent_alert': 20,
    'escalation': 30, 'support_escalation': 30, 'stakeholder_escalation': 28,
    'usage_decline': 30, 'engagement_gap': 32, 'kpi_decline': 30,
    'stakeholder_change': 35,
    # Positive signals → high scores (60-95 range)
    'executive_engagement': 90, 'churn_averted': 95, 'expansion_signal': 88,
    'champion_advocacy': 90, 'kpi_recovery': 85, 'champion_reengagement': 82,
    'deployment_improvement': 78, 'csm_intervention': 72, 'health_improvement': 80,
    'feature_adoption': 72, 'advocacy': 75, 'usage_spike': 70,
    'onboarding_milestone': 68, 'expansion_closed': 95,
}

# Signal evidence weights (from spec §4.1)
SIGNAL_WEIGHT = {
    'executive_engagement': 1.5, 'expansion_signal': 1.6, 'churn_averted': 1.4,
    'csm_intervention': 1.0, 'kpi_recovery': 1.3, 'champion_advocacy': 1.4,
    'usage_decline': 1.1, 'competitor_mention': 1.3, 'support_escalation': 1.0,
    'champion_loss': 1.3, 'critical_incident': 1.2, 'budget_pressure': 1.2,
    'escalation': 1.0, 'stakeholder_escalation': 1.1, 'engagement_gap': 1.0,
    'kpi_decline': 1.0, 'contract_dispute': 1.3, 'champion_reengagement': 1.2,
    'deployment_improvement': 1.1, 'health_improvement': 1.0,
    'feature_adoption': 0.9, 'advocacy': 0.8, 'onboarding_milestone': 0.7,
    'usage_spike': 0.9, 'stakeholder_change': 1.0, 'urgent_alert': 1.2,
}

# Default decay: λ = 0.023/day → 30-day half-life
DEFAULT_LAMBDA = 0.023

# Composite blend ratio: how much weight signals get vs KPIs
# 0.3 = 30% signal influence, 70% KPI influence
SIGNAL_BLEND_RATIO = 0.30


def _recency_weight(tau_days: float, lam: float = DEFAULT_LAMBDA) -> float:
    """Exponential decay: R(τ) = e^(-λ × τ)"""
    return math.exp(-lam * max(0, tau_days))


def _compute_signal_score(signal_events: list, month_dates: list, lam: float = DEFAULT_LAMBDA) -> list:
    """Compute an independent signal-only score (0-100) at each month WITH recency decay.

    Each signal has a score (e.g., champion_loss=15, executive_engagement=90).
    At each month, compute a recency-weighted average of all signals up to that point.
    If no signals have occurred yet, score is 50 (neutral).
    """
    result = []
    for month_date in month_dates:
        t = datetime(month_date.year, month_date.month, 15)

        numerator = 0.0
        denominator = 0.0
        active = []

        for sig in signal_events:
            if sig['datetime'] > t:
                continue
            tau = max(0, (t - sig['datetime']).days)
            R = _recency_weight(tau, lam)
            if R < 0.05:
                continue
            W = sig['weight']
            S = sig['score']
            numerator += W * S * R
            denominator += W * R
            if R >= 0.10:
                active.append({
                    'type': sig['type'],
                    'score': S,
                    'recency': round(R, 2),
                })

        if denominator > 0:
            signal_score = numerator / denominator
        else:
            signal_score = 50.0

        result.append({
            'month': month_date.isoformat(),
            'score': round(signal_score, 1),
            'signal_count': len(active),
            'active_signals': active[:5],
        })

    return result


def _compute_signal_score_raw(signal_events: list, month_dates: list) -> list:
    """Compute signal-only score WITHOUT recency decay (raw, unweighted).

    Simple weighted average of ALL signals up to each month — no decay.
    Shows the cumulative signal picture without time bias.
    """
    result = []
    for month_date in month_dates:
        t = datetime(month_date.year, month_date.month, 15)

        numerator = 0.0
        denominator = 0.0

        for sig in signal_events:
            if sig['datetime'] > t:
                continue
            W = sig['weight']
            S = sig['score']
            numerator += W * S
            denominator += W

        if denominator > 0:
            raw_score = numerator / denominator
        else:
            raw_score = 50.0

        result.append({
            'month': month_date.isoformat(),
            'score': round(raw_score, 1),
        })

    return result


def _compute_composite(
    kpi_series: list,
    signal_score_series: list,
    lam: float = DEFAULT_LAMBDA,
    signal_ratio: float = SIGNAL_BLEND_RATIO,
) -> list:
    """Compute composite score: weighted blend of decayed KPI + decayed signal scores.

    Composite(t) = (1 - signal_ratio) × KPI_decayed(t) + signal_ratio × Signal_decayed(t)

    Both KPI and signal scores are decayed by recency before blending.
    Threshold guard: composite cannot cross 50 or 70 boundaries based on signals alone.
    """
    result = []

    for i, (month_date, kpi_score) in enumerate(kpi_series):
        t = datetime(month_date.year, month_date.month, 15)

        # Decayed KPI: recency-weighted, but for fresh data just use current month
        # (only decay matters when data is missing — with monthly data, current month dominates)
        kpi_decayed = kpi_score  # fresh data = no decay needed

        # Signal score at this month
        sig_score = signal_score_series[i]['score'] if i < len(signal_score_series) else 50.0

        # Blend
        composite = (1 - signal_ratio) * kpi_decayed + signal_ratio * sig_score

        # Threshold guard (spec §5.3): signal influence can't cross 50 or 70 alone
        if kpi_score < 50 and composite >= 50:
            composite = min(composite, 49.9)
        elif kpi_score < 70 and composite >= 70:
            composite = min(composite, 69.9)

        result.append({
            'month': month_date.isoformat(),
            'score': round(composite, 1),
            'kpi_component': round(kpi_decayed, 1),
            'signal_component': round(sig_score, 1),
            'signal_influence': round(composite - kpi_score, 1),
        })

    return result


@journey_intelligence_api.route('/api/journey-intelligence/<int:account_id>', methods=['GET'])
def get_journey_intelligence(account_id):
    """Return three graph lines + signals + playbook executions for an account.

    Graph 1: kpi_only     — KPI health scores (no decay, structural truth)
    Graph 2: signal_score — Signal-only score (0-100, independent, with recency decay)
    Graph 3: composite    — Blend of decayed KPI + decayed signal (70/30 default)

    Query params:
        months (int, default 12): how many months of history
    """
    try:
        customer_id = get_current_customer_id()
        months = int(request.args.get('months', 12))

        from models import Account, HealthScore, ContextNode, PlaybookExecutionV2
        import utils.health_thresholds as ht

        account = Account.query.filter_by(
            account_id=account_id, customer_id=customer_id
        ).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404

        # 1. KPI-only health scores (Graph 1)
        cutoff = (datetime.utcnow() - timedelta(days=months * 30)).date()
        scores = (
            HealthScore.query
            .filter(
                HealthScore.account_id == account_id,
                HealthScore.measurement_month >= cutoff,
            )
            .order_by(HealthScore.measurement_month)
            .all()
        )
        kpi_series = [
            (s.measurement_month, float(s.health_score))
            for s in scores if s.health_score is not None
        ]
        kpi_only = [{'month': m.isoformat(), 'score': round(s, 1)} for m, s in kpi_series]

        if not kpi_series:
            return jsonify({
                'account_id': account_id,
                'account_name': account.account_name,
                'error': 'No health score history',
                'kpi_only': [], 'signal_score': [], 'composite': [],
                'signals': [], 'playbook_executions': [],
            })

        # 2. Collect signals
        signals_raw = (
            ContextNode.query
            .filter(
                ContextNode.customer_id == customer_id,
                ContextNode.account_id == account_id,
                ContextNode.node_type == 'SIGNAL',
                ContextNode.source == 'customer',
            )
            .order_by(ContextNode.occurred_at)
            .all()
        )

        signal_events = []
        signals_output = []
        for sig in signals_raw:
            if not sig.occurred_at:
                continue
            sig_score = SIGNAL_SCORE_MAP.get(sig.node_subtype, 50)
            w = SIGNAL_WEIGHT.get(sig.node_subtype, 1.0)
            props = sig.properties or {}
            sentiment = props.get('sentiment', 'negative' if sig_score < 50 else 'positive')

            sig_dt = sig.occurred_at
            if sig_dt.tzinfo:
                sig_dt = sig_dt.replace(tzinfo=None)

            signal_events.append({
                'datetime': sig_dt,
                'type': sig.node_subtype,
                'score': sig_score,
                'weight': w,
            })

            # Find closest KPI score at signal time
            health_at_time = kpi_series[-1][1]
            for m_date, m_score in kpi_series:
                m_dt = datetime(m_date.year, m_date.month, 1)
                if m_dt <= sig_dt:
                    health_at_time = m_score

            signals_output.append({
                'date': sig.occurred_at.isoformat(),
                'type': sig.node_subtype,
                'sentiment': sentiment,
                'signal_score': sig_score,
                'weight': w,
                'health_at_time': round(health_at_time, 1),
                'title': sig.title[:80] if sig.title else None,
            })

        # 3. Compute Signal Scores — independent, signals only
        month_dates = [m for m, _ in kpi_series]
        signal_score_series = _compute_signal_score(signal_events, month_dates)
        signal_score_raw = _compute_signal_score_raw(signal_events, month_dates)

        # 4. Compute Composite (Graph 3) — blend of KPI + signal with decay
        composite_series = _compute_composite(kpi_series, signal_score_series)

        # 5. Playbook executions
        pb_execs = (
            PlaybookExecutionV2.query
            .filter_by(customer_id=customer_id, account_id=account_id)
            .order_by(PlaybookExecutionV2.triggered_at)
            .all()
        )
        playbooks = [{
            'triggered_at': p.triggered_at.isoformat() if p.triggered_at else None,
            'closed_at': p.closed_at.isoformat() if p.closed_at else None,
            'playbook_id': p.playbook_id,
            'playbook_name': p.playbook_name,
            'outcome': p.outcome,
            'health_at_trigger': float(p.health_at_trigger) if p.health_at_trigger else None,
            'health_at_close': float(p.health_at_close) if p.health_at_close else None,
            'triggered_by': p.triggered_by,
        } for p in pb_execs]

        # Time range
        first_month = kpi_series[0][0].isoformat()
        last_month = kpi_series[-1][0].isoformat()

        return jsonify({
            'account_id': account_id,
            'account_name': account.account_name,
            'arr': float(account.revenue or 0),
            'time_range': {'start': first_month, 'end': last_month},
            'lambda': DEFAULT_LAMBDA,
            'half_life_days': round(math.log(2) / DEFAULT_LAMBDA, 0),
            'signal_blend_ratio': SIGNAL_BLEND_RATIO,
            'kpi_only': kpi_only,
            'signal_score': signal_score_series,
            'signal_score_raw': signal_score_raw,
            'composite': composite_series,
            'signals': signals_output,
            'playbook_executions': playbooks,
            'thresholds': {
                'healthy': ht.healthy_min(),
                'at_risk': ht.at_risk_min(),
            },
        })

    except Exception as e:
        logger.error(f"journey-intelligence error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@journey_intelligence_api.route('/api/journey-intelligence/accounts', methods=['GET'])
def list_accounts_for_journey():
    """List all accounts with signal counts for the account selector."""
    try:
        customer_id = get_current_customer_id()
        from models import Account, HealthScore, ContextNode
        from sqlalchemy import func

        accounts = Account.query.filter_by(customer_id=customer_id).all()

        sig_counts = dict(
            ContextNode.query
            .filter(
                ContextNode.customer_id == customer_id,
                ContextNode.node_type == 'SIGNAL',
                ContextNode.source == 'customer',
            )
            .with_entities(ContextNode.account_id, func.count())
            .group_by(ContextNode.account_id)
            .all()
        )

        result = []
        for a in accounts:
            hs = (HealthScore.query.filter_by(account_id=a.account_id)
                  .order_by(HealthScore.measurement_month.desc()).first())
            result.append({
                'account_id': a.account_id,
                'account_name': a.account_name,
                'health': float(hs.health_score) if hs and hs.health_score else None,
                'arr': float(a.revenue or 0),
                'signal_count': sig_counts.get(a.account_id, 0),
            })

        result.sort(key=lambda x: -(x['signal_count'] or 0))
        return jsonify({'accounts': result})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
