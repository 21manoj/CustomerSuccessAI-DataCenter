"""
Arc Classifier — assigns arc type to an account from raw DB signals.

Backend equivalent of the load-driver's manifest arc_type assignment.
Reads HealthScore history + ContextNode signals + Account data from DB.
Returns: arc_type (str), confidence (float 0-1), phase ('baseline'|'intervention')

Priority cascade: first matching rule wins.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta

import utils.health_thresholds as ht

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Arc classification rules — (arc_type, base_confidence, condition_fn)
# Evaluated in order; first match wins.
# ---------------------------------------------------------------------------
ARC_RULES: list[tuple[str, float, object]] = [
    (
        'champion_loss', 0.85,
        lambda f: f['has_stakeholder_departure'] and f['slope_30d'] < -3,
    ),
    (
        'crisis_recovery', 0.80,
        lambda f: f['health_now'] < ht.at_risk_min() and 'critical_incident' in f['signal_types'],
    ),
    (
        'infrastructure_decay', 0.75,
        lambda f: (
            f['slope_60d'] < -8
            and f['health_now'] < 65
            and 'critical_incident' not in f['signal_types']
        ),
    ),
    (
        'budget_pressure', 0.75,
        lambda f: (
            any(t in f['signal_types'] for t in ('budget_freeze', 'budget_cut', 'cost_reduction'))
            and f['slope_60d'] < -3
        ),
    ),
    (
        'stalled_deployment', 0.70,
        lambda f: f['p1_delta_30d'] < -15 and abs(f['slope_30d']) < 2,
    ),
    (
        'competitor_evaluation', 0.70,
        lambda f: (
            any(t in f['signal_types'] for t in ('competitor', 'evaluation', 'rfp'))
            and f['days_to_renewal'] < 90
        ),
    ),
    (
        'engagement_decline', 0.65,
        lambda f: f['slope_30d'] < -5 and f['health_now'] >= ht.at_risk_min(),
    ),
    (
        'land_and_expand', 0.75,
        lambda f: (
            f['health_now'] >= ht.healthy_min() + 10
            and any(t in f['signal_types'] for t in ('expansion', 'upsell', 'growth'))
        ),
    ),
    (
        'steady_performer', 0.60,
        lambda f: f['health_now'] >= ht.healthy_min() and f['slope_30d'] >= -2,
    ),
    # Fallback — always matches
    (
        'budget_pressure', 0.55,
        lambda f: True,
    ),
]


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def extract_features(account_id: int, db_session) -> dict:
    """
    Extract numerical and categorical features for arc classification.

    Returns a dict with keys:
      health_now         : most recent health score (float, default 50.0)
      slope_30d          : pts/day change over last 30 days (negative = declining)
      slope_60d          : pts/day change over last 60 days
      signal_types       : Counter of signal subtypes (from ContextNode SIGNAL rows)
      has_stakeholder_departure : bool — any STAKEHOLDER node with departure-related title
      p1_delta_30d       : pillar P1 delta pts over last 30 days (from DC2SKPI)
      days_to_renewal    : days until renewal (from profile_metadata, default 365)
    """
    from models import Account, ContextNode, DC2SKPI, HealthScore

    now = datetime.utcnow()

    # ── 1. Health score history ──────────────────────────────────────────────
    hs_rows = (
        db_session.query(HealthScore)
        .filter(HealthScore.account_id == account_id)
        .order_by(HealthScore.measurement_month)
        .all()
    )

    health_series: list[tuple[datetime, float]] = []
    for hs in hs_rows:
        if hs.measurement_month and hs.health_score is not None:
            # measurement_month is a Date; convert to datetime for arithmetic
            if hasattr(hs.measurement_month, 'year'):
                ts = datetime(hs.measurement_month.year,
                              hs.measurement_month.month,
                              hs.measurement_month.day)
            else:
                ts = hs.measurement_month
            health_series.append((ts, float(hs.health_score)))

    health_now = health_series[-1][1] if health_series else 50.0

    def _slope(days: int) -> float:
        """Compute health change per day over the last `days` days."""
        if len(health_series) < 2:
            return 0.0
        cutoff = now - timedelta(days=days)
        in_window = [(ts, sc) for ts, sc in health_series if ts >= cutoff]
        if not in_window and health_series:
            # Use last 2 points regardless of window
            in_window = health_series[-2:]
        if len(in_window) < 2:
            return 0.0
        earliest_ts, earliest_sc = in_window[0]
        latest_ts, latest_sc = in_window[-1]
        delta_days = (latest_ts - earliest_ts).days or 1
        return (latest_sc - earliest_sc) / delta_days

    slope_30d = _slope(30)
    slope_60d = _slope(60)

    # ── 2. Signal types from ContextNode ────────────────────────────────────
    signal_nodes = (
        db_session.query(ContextNode)
        .filter(
            ContextNode.account_id == account_id,
            ContextNode.node_type == 'SIGNAL',
        )
        .all()
    )

    signal_types: Counter = Counter()
    for sn in signal_nodes:
        # node_subtype holds the signal subtype (e.g. 'kpi_decline', 'critical_incident')
        subtype = (sn.node_subtype or '').strip().lower()
        if subtype:
            signal_types[subtype] += 1
        # Also scan properties for any signal_type field
        props = sn.properties or {}
        st = str(props.get('signal_type', '')).strip().lower()
        if st:
            signal_types[st] += 1

    # ── 3. Stakeholder departure ─────────────────────────────────────────────
    stakeholder_nodes = (
        db_session.query(ContextNode)
        .filter(
            ContextNode.account_id == account_id,
            ContextNode.node_type == 'STAKEHOLDER',
        )
        .all()
    )

    departure_keywords = ('departed', 'left', 'resignation', 'champion_loss',
                          'champion_departure', 'disengaged', 'churned')

    has_stakeholder_departure = False
    for sn in stakeholder_nodes:
        title_lower = (sn.title or '').lower()
        subtype_lower = (sn.node_subtype or '').lower()
        if any(kw in title_lower or kw in subtype_lower for kw in departure_keywords):
            has_stakeholder_departure = True
            break

    # Also check SIGNAL nodes for champion/departure type signals
    if not has_stakeholder_departure:
        departure_signal_types = ('champion_departure', 'champion_loss', 'stakeholder_escalation')
        for st in departure_signal_types:
            if signal_types.get(st, 0) > 0:
                has_stakeholder_departure = True
                break

    # ── 4. Pillar P1 delta from DC2SKPI ─────────────────────────────────────
    cutoff_30d = now - timedelta(days=30)
    cutoff_60d = now - timedelta(days=60)

    # Recent P1 KPIs (last 30 days)
    recent_p1 = (
        db_session.query(DC2SKPI)
        .filter(
            DC2SKPI.account_id == account_id,
            DC2SKPI.pillar == 'P1',
            DC2SKPI.measured_at >= cutoff_30d,
        )
        .all()
    )

    # Prior P1 KPIs (30-60 days ago)
    prior_p1 = (
        db_session.query(DC2SKPI)
        .filter(
            DC2SKPI.account_id == account_id,
            DC2SKPI.pillar == 'P1',
            DC2SKPI.measured_at >= cutoff_60d,
            DC2SKPI.measured_at < cutoff_30d,
        )
        .all()
    )

    def _avg_value(rows) -> float | None:
        vals = [float(r.value) for r in rows if r.value is not None]
        return sum(vals) / len(vals) if vals else None

    recent_p1_avg = _avg_value(recent_p1)
    prior_p1_avg = _avg_value(prior_p1)

    if recent_p1_avg is not None and prior_p1_avg is not None:
        p1_delta_30d = recent_p1_avg - prior_p1_avg
    else:
        p1_delta_30d = 0.0

    # ── 5. Days to renewal ───────────────────────────────────────────────────
    account = db_session.get(Account, account_id)
    days_to_renewal = 365  # default

    if account:
        # Try profile_metadata first
        pm = account.profile_metadata or {}
        renewal_str = pm.get('renewal_date') or pm.get('contract_end_date')
        if renewal_str:
            try:
                renewal_dt = datetime.fromisoformat(str(renewal_str).split('T')[0])
                days_to_renewal = max(0, (renewal_dt - now).days)
            except (ValueError, TypeError):
                pass

    return {
        'health_now': health_now,
        'slope_30d': slope_30d,
        'slope_60d': slope_60d,
        'signal_types': signal_types,
        'has_stakeholder_departure': has_stakeholder_departure,
        'p1_delta_30d': p1_delta_30d,
        'days_to_renewal': days_to_renewal,
    }


# ---------------------------------------------------------------------------
# Phase detection
# ---------------------------------------------------------------------------

def detect_phase(features: dict, arc_type: str) -> str:
    """
    Determine whether this account is in 'baseline' (pre-intervention) or
    'intervention' (active recovery) phase.

    Intervention if health is improving meaningfully AND is above the crisis floor.
    """
    if features['slope_30d'] > 2 and features['health_now'] > 55:
        return 'intervention'
    return 'baseline'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_arc(account_id: int) -> tuple[str, float, str]:
    """
    Classify arc type, confidence, and phase for a single account.

    Must be called inside a Flask app context (db.session available).

    Returns:
        (arc_type, confidence, phase)
        e.g. ('crisis_recovery', 0.80, 'baseline')
    """
    from extensions import db

    try:
        features = extract_features(account_id, db.session)
    except Exception as e:
        logger.error(f"arc_classifier: feature extraction failed for account {account_id}: {e}")
        return 'steady_performer', 0.5, 'baseline'

    for arc_type, confidence, condition in ARC_RULES:
        try:
            if condition(features):
                phase = detect_phase(features, arc_type)
                logger.debug(
                    f"arc_classifier: account={account_id} arc={arc_type} "
                    f"confidence={confidence} phase={phase} "
                    f"health_now={features['health_now']:.1f} "
                    f"slope_30d={features['slope_30d']:.3f}"
                )
                return arc_type, confidence, phase
        except Exception as e:
            logger.warning(
                f"arc_classifier: rule evaluation failed "
                f"account={account_id} arc={arc_type}: {e}"
            )
            continue

    # Should never reach here (last rule is always-true fallback)
    return 'steady_performer', 0.5, 'baseline'
