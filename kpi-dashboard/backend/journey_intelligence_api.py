"""
Journey Intelligence API
=========================

Read-only endpoint that computes three health score lines for an account:
  Line 1 — KPI-only (no decay): structural truth from HealthScore table
  Line 2 — KPI-decayed: same scores with exponential recency decay
  Line 3 — Signal-DNA composite: decayed KPIs + signal impact (unified evidence formula)

All computation is at query time — nothing stored, nothing changes the scoring engine.
The composite line is informational (per Recency-Signal-DNA spec §1a: NRR uses kpi_only_score exclusively).

Endpoint: GET /api/journey-intelligence/<account_id>
"""

import math
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id

logger = logging.getLogger(__name__)

journey_intelligence_api = Blueprint('journey_intelligence_api', __name__)

# ── Signal amplitude table (from Recency-Signal-DNA spec §5.2) ──
# Maps signal subtype → max health delta. Positive = improvement, negative = risk.
SIGNAL_AMPLITUDE = {
    'champion_loss': -8, 'critical_incident': -6, 'budget_pressure': -5,
    'competitor_mention': -5, 'contract_dispute': -7, 'escalation': -4,
    'support_escalation': -4, 'stakeholder_escalation': -4,
    'stakeholder_change': -3, 'usage_decline': -3, 'engagement_gap': -3,
    'kpi_decline': -3, 'urgent_alert': -5,
    'champion_reengagement': +4, 'executive_engagement': +12,
    'deployment_improvement': +3, 'kpi_recovery': +10,
    'health_improvement': +3, 'expansion_signal': +3,
    'feature_adoption': +2, 'advocacy': +2, 'csm_intervention': +3,
    'champion_advocacy': +9, 'usage_spike': +2, 'onboarding_milestone': +2,
    'churn_averted': +12,
}

# ── Signal evidence weights (from spec §4.1) ──
SIGNAL_BASE_WEIGHT = {
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


def _recency_weight(tau_days: float, lam: float = DEFAULT_LAMBDA) -> float:
    """Exponential decay: R(τ) = e^(-λ × τ)"""
    return math.exp(-lam * max(0, tau_days))


def _compute_composite(
    kpi_series: list,
    signal_events: list,
    lam: float = DEFAULT_LAMBDA,
) -> list:
    """Compute the composite score at each month using unified evidence formula.

    Score(t) = Σ[Wi × Hi × R(t-ti)] / Σ[Wi × R(t-ti)]

    All KPI measurements and signals up to time t contribute, weighted by recency.
    Threshold guard: signal adjustment cannot cross 50 or 70 boundaries alone.
    """
    result = []

    for month_date, kpi_score in kpi_series:
        t = datetime(month_date.year, month_date.month, 15)  # mid-month

        numerator = 0.0
        denominator = 0.0
        active_signals = []

        # KPI evidence: all months up to t
        for m_date, m_score in kpi_series:
            m_dt = datetime(m_date.year, m_date.month, 15)
            if m_dt > t:
                continue
            tau = max(0, (t - m_dt).days)
            R = _recency_weight(tau, lam)
            W = 1.0  # KPI base weight
            numerator += W * m_score * R
            denominator += W * R

        # Signal evidence: all signals up to t
        for sig in signal_events:
            sig_dt = sig['datetime']
            if sig_dt > t:
                continue
            tau = max(0, (t - sig_dt).days)
            R = _recency_weight(tau, lam)
            if R < 0.05:
                continue  # negligible

            # H(signal) = kpi_score_at_signal_time + amplitude
            closest_kpi = kpi_score
            for m_date, m_score in kpi_series:
                m_dt = datetime(m_date.year, m_date.month, 1)
                if m_dt <= sig_dt:
                    closest_kpi = m_score
            H_sig = max(0, min(100, closest_kpi + sig['amplitude']))
            W = sig['weight']
            numerator += W * H_sig * R
            denominator += W * R

            if R >= 0.10:
                active_signals.append({
                    'type': sig['type'],
                    'recency': round(R, 2),
                    'impact': sig['amplitude'],
                })

        composite = numerator / denominator if denominator > 0 else kpi_score

        # Threshold guard (spec §5.3): signals can't cross 50 or 70 alone
        signal_delta = composite - kpi_score
        if kpi_score < 50 and composite >= 50:
            composite = min(composite, 49.9)
        elif kpi_score < 70 and composite >= 70:
            composite = min(composite, 69.9)
        elif kpi_score >= 70 and composite < 70:
            composite = max(composite, 70.0)

        result.append({
            'month': month_date.isoformat(),
            'score': round(composite, 1),
            'signal_adjustment': round(composite - kpi_score, 1),
            'active_signals': active_signals[:5],
        })

    return result


def _compute_decayed(kpi_series: list, lam: float = DEFAULT_LAMBDA) -> list:
    """Compute KPI-decayed series: same scores with exponential recency decay applied.

    For each month, the score is a recency-weighted average of all KPI scores
    up to that point — NOT just the current month's value.
    """
    result = []
    for i, (month_date, kpi_score) in enumerate(kpi_series):
        t = datetime(month_date.year, month_date.month, 15)
        numerator = 0.0
        denominator = 0.0
        for m_date, m_score in kpi_series:
            m_dt = datetime(m_date.year, m_date.month, 15)
            if m_dt > t:
                continue
            tau = max(0, (t - m_dt).days)
            R = _recency_weight(tau, lam)
            numerator += m_score * R
            denominator += R
        decayed = numerator / denominator if denominator > 0 else kpi_score
        decay_factor = round(_recency_weight(0 if i == len(kpi_series) - 1
                                             else (datetime(kpi_series[-1][0].year, kpi_series[-1][0].month, 15) - t).days,
                                             lam), 2)
        result.append({
            'month': month_date.isoformat(),
            'score': round(decayed, 1),
            'decay_factor': decay_factor,
        })
    return result


@journey_intelligence_api.route('/api/journey-intelligence/<int:account_id>', methods=['GET'])
def get_journey_intelligence(account_id):
    """Return three health score lines + signals + playbook executions for an account.

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

        # 1. KPI-only health scores
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
                'kpi_only': [], 'kpi_decayed': [], 'signal_dna': [],
                'signals': [], 'playbook_executions': [],
            })

        # 2. Signals
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
            amp = SIGNAL_AMPLITUDE.get(sig.node_subtype, 0)
            w = SIGNAL_BASE_WEIGHT.get(sig.node_subtype, 1.0)
            props = sig.properties or {}
            sentiment = props.get('sentiment', 'negative' if amp < 0 else 'positive')

            sig_dt = sig.occurred_at
            if sig_dt.tzinfo:
                sig_dt = sig_dt.replace(tzinfo=None)

            signal_events.append({
                'datetime': sig_dt,
                'type': sig.node_subtype,
                'amplitude': amp,
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
                'impact': amp,
                'weight': w,
                'health_at_time': round(health_at_time, 1),
                'title': sig.title[:80] if sig.title else None,
            })

        # 3. Compute KPI-decayed line
        kpi_decayed = _compute_decayed(kpi_series)

        # 4. Compute Signal-DNA composite line
        signal_dna = _compute_composite(kpi_series, signal_events)

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
            'kpi_only': kpi_only,
            'kpi_decayed': kpi_decayed,
            'signal_dna': signal_dna,
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

        # Signal counts per account
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

        # Sort: most signals first (most interesting for the graph)
        result.sort(key=lambda x: -(x['signal_count'] or 0))
        return jsonify({'accounts': result})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
