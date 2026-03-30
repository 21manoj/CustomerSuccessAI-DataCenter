"""
Arc Classifier — assigns arc type to an account from raw DB signals.

Backend equivalent of the load-driver's manifest arc_type assignment.
Reads HealthScore history + ContextNode signals + Account data from DB.
Returns: arc_type (str), confidence (float 0-1), phase ('baseline'|'intervention')

Priority cascade: first matching rule wins.

SLOPE UNITS: all slope values are pts/MONTH (not pts/day).
  -3 = 3-point decline per month  (mild decline)
  -8 = 8-point decline per month  (severe decline)
  Monthly resolution because health scores are stored monthly.

SIGNAL TYPES: we match both:
  (a) Load-driver arc subtypes (e.g. 'stakeholder_escalation', 'expansion_signal')
  (b) CRM-native field values  (e.g. 'stakeholder_departure', 'budget_freeze')
  (c) Title/description keyword hits injected as synthetic signal types during
      feature extraction.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta

import utils.health_thresholds as ht

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signal-type keyword sets — include both load-driver subtypes AND
# CRM-native values so the classifier works for both synthetic and real data.
# ---------------------------------------------------------------------------

# Champion / stakeholder departure signals
_CHAMPION_LOSS_SIGNALS = frozenset([
    # load-driver subtypes
    'stakeholder_escalation',    # champion_loss + crisis_recovery arc
    'champion_disengagement',    # ignored_churn arc
    'executive_engagement',      # champion_loss intervention (exec brought in)
    'champion_change',           # ACTUAL load-driver subtype for VP/exec departure
    # CRM / Gainsight
    'champion_departure', 'champion_loss',
    'stakeholder_departure', 'executive_departure',
    # synthetic (injected by title scan below)
    '_champion_departure_detected',
])

# Explicit champion change signals — strongest indicator, no slope required
# These are direct "person left the account" events vs generic escalation
_CHAMPION_CHANGE_SIGNALS = frozenset([
    'champion_change',           # load-driver: "VP resigned, replaced by..."
    'champion_disengagement',    # ignored_churn arc: champion pulling away
    'champion_departure',        # CRM/Gainsight field value
    'executive_departure',       # CRM/Gainsight field value
    '_champion_departure_detected',  # title scan hit
])

# Infrastructure / technical incident signals
_INFRA_SIGNALS = frozenset([
    # load-driver subtypes
    'critical_incident',         # infrastructure_decay + crisis_recovery
    'support_escalation',        # infrastructure_decay (also appears in others)
    # CRM / Gainsight
    'performance_degradation', 'system_outage', 'sla_breach',
    'infrastructure_issue', 'technical_blocker',
])

# Stakeholder-driven crisis signals (differentiates crisis_recovery from infra_decay)
_STAKEHOLDER_CRISIS_SIGNALS = frozenset([
    'stakeholder_escalation',    # load-driver crisis_recovery arc
    'escalation_to_exec',        # decision subtype (may appear in signal nodes)
    'executive_sponsor_engaged',
])

# Budget / cost pressure signals
_BUDGET_SIGNALS = frozenset([
    # CRM / Gainsight (not in load-driver — load-driver budget_pressure uses kpi_decline)
    'budget_freeze', 'budget_cut', 'cost_reduction',
    'financial_concern', 'contract_risk',
    # synthetic
    '_budget_concern_detected',
])

# Competitor / evaluation signals
_COMPETITOR_SIGNALS = frozenset([
    # CRM / Gainsight
    'competitor', 'rfp', 'evaluation',
    'competitive_threat', 'vendor_review', 'competitive_analysis',
    # synthetic
    '_competitor_detected',
])

# Deployment / technical blocker signals
_STALLED_SIGNALS = frozenset([
    # load-driver subtypes
    'kpi_decline',               # stalled_deployment baseline
    'deployment_improvement',    # stalled_deployment intervention
    # CRM / Gainsight
    'deployment_blocked', 'technical_blocker', 'integration_failure',
    # synthetic
    '_deployment_blocked_detected',
])

# Growth / expansion signals
_EXPANSION_SIGNALS = frozenset([
    # load-driver subtypes
    'expansion_signal',          # expansion_champion arc
    'champion_advocacy',         # expansion_champion arc
    'usage_spike',               # expansion_champion arc
    'advocacy',                  # multiple healthy arcs
    'champion_engages',          # stakeholder subtype — healthy arcs
    # CRM / Gainsight
    'expansion', 'upsell', 'growth', 'upsell_signal',
    # synthetic
    '_expansion_detected',
])


# ---------------------------------------------------------------------------
# Arc classification rules — (arc_type, base_confidence, condition_fn)
# Evaluated in order; first match wins.
# ---------------------------------------------------------------------------

def _has(signal_types: Counter, keyword_set: frozenset) -> bool:
    """Return True if any key in signal_types intersects keyword_set."""
    return bool(signal_types.keys() & keyword_set)


ARC_RULES: list[tuple[str, float, object]] = [
    # ── All arc_type values use canonical names from config/story_arcs/ ──
    #
    # Canonical 8: exec_sponsor_change, crisis_recovery, stalled_deployment,
    #   competitive_displacement, silent_churn, land_and_expand,
    #   expansion_champion, seasonal_surge

    # 1a. Exec Sponsor Change (explicit) — champion/exec departure signal present
    #     Strongest indicator: a named person left the account.
    (
        'exec_sponsor_change', 0.85,
        lambda f: (
            _has(f['signal_types'], _CHAMPION_CHANGE_SIGNALS)
            and f['health_now'] < ht.at_risk_min()
            and not _has(f['signal_types'], frozenset(['critical_incident']))
        ),
    ),
    # 1b. Exec Sponsor Change (slope-based) — departure signal + actively declining
    (
        'exec_sponsor_change', 0.80,
        lambda f: (
            f['has_stakeholder_departure']
            and f['slope_30d'] < -3            # > 3 pts/month active decline
        ),
    ),
    # 2a. Crisis Recovery — critical incident + stakeholder-driven escalation
    (
        'crisis_recovery', 0.80,
        lambda f: (
            f['health_now'] < ht.at_risk_min()
            and _has(f['signal_types'], frozenset(['critical_incident']))
            and _has(f['signal_types'], _STAKEHOLDER_CRISIS_SIGNALS)
        ),
    ),
    # 2b. Crisis Recovery (relaxed) — critical incident, very low health
    (
        'crisis_recovery', 0.75,
        lambda f: (
            f['health_now'] < ht.at_risk_min() - 10   # health < 40
            and _has(f['signal_types'], frozenset(['critical_incident']))
        ),
    ),
    # 3. Stalled Deployment — infra/tech signals driving prolonged decline
    (
        'stalled_deployment', 0.75,
        lambda f: (
            f['slope_60d'] < -8                        # > 8 pts/month decline over 2 months
            and f['health_now'] < 65
            and _has(f['signal_types'], _INFRA_SIGNALS)
            and not _has(f['signal_types'], _STAKEHOLDER_CRISIS_SIGNALS)
        ),
    ),
    # 3b. Stalled Deployment — P1 pillar decline with flat overall slope
    (
        'stalled_deployment', 0.70,
        lambda f: (
            f['p1_delta_30d'] < -5             # P1 infra pillar declining
            and abs(f['slope_30d']) < 3        # overall health relatively flat
            and f['health_now'] < ht.healthy_min()
        ),
    ),
    # 4. Competitive Displacement — competitor signals + budget pressure
    (
        'competitive_displacement', 0.75,
        lambda f: (
            _has(f['signal_types'], _BUDGET_SIGNALS)
            and f['slope_60d'] < -3
        ),
    ),
    # 4b. Competitive Displacement — competitor signals + approaching renewal
    (
        'competitive_displacement', 0.70,
        lambda f: (
            _has(f['signal_types'], _COMPETITOR_SIGNALS)
            and f['days_to_renewal'] < 90
        ),
    ),
    # 5. Silent Churn — declining engagement, no crisis, no champion departure
    (
        'silent_churn', 0.65,
        lambda f: (
            f['slope_30d'] < -5                # > 5 pts/month rapid decline
            and f['health_now'] < ht.at_risk_min() + 15
            and not _has(f['signal_types'], frozenset(['critical_incident']))
            and not f['has_stakeholder_departure']
        ),
    ),
    # 5b. Silent Churn (mild) — moderate decline in at-risk range
    (
        'silent_churn', 0.60,
        lambda f: (
            f['slope_30d'] < -3
            and f['health_now'] >= ht.at_risk_min()
            and f['health_now'] < ht.healthy_min()
        ),
    ),
    # 6. Expansion Champion — healthy, high confidence, growing with expansion signals
    (
        'expansion_champion', 0.75,
        lambda f: (
            f['health_now'] >= ht.healthy_min() + 10      # health >= 80
            and f['slope_30d'] >= 0
            and _has(f['signal_types'], _EXPANSION_SIGNALS)
        ),
    ),
    # 7. Land and Expand — healthy account with expansion signals
    (
        'land_and_expand', 0.75,
        lambda f: (
            f['health_now'] >= ht.healthy_min()
            and _has(f['signal_types'], _EXPANSION_SIGNALS)
        ),
    ),
    # 8. Seasonal Surge — healthy, stable (seasonal patterns detected by Wizard B)
    (
        'seasonal_surge', 0.60,
        lambda f: f['health_now'] >= ht.healthy_min() and f['slope_30d'] >= -2,
    ),
    # 9. Fallback — always matches (competitive pressure is the safe default)
    (
        'competitive_displacement', 0.55,
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
      slope_30d          : pts/MONTH change over last 30 days (negative = declining)
      slope_60d          : pts/MONTH change over last 60 days
      signal_types       : Counter of signal subtypes + synthetic _*_detected tags
      has_stakeholder_departure : bool — any STAKEHOLDER node with departure-related title
                                  OR matching SIGNAL node subtype
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
        """
        Compute health change per MONTH over the last `days` days.

        Returns pts/month so thresholds like -3 mean "3-point monthly decline".
        Health scores are stored monthly, so raw pts/day would be tiny fractions.
        Multiply raw pts/day by 30 to get pts/month.
        """
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
        pts_per_day = (latest_sc - earliest_sc) / delta_days
        return pts_per_day * 30  # convert to pts/month

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

    # ── 2b. Title/description keyword scan (secondary signal source) ─────────
    # Many real-customer nodes have rich text but narrow subtype values.
    # Inject synthetic signal type tags so rules can match on semantics.
    _all_nodes = signal_nodes + (
        db_session.query(ContextNode)
        .filter(
            ContextNode.account_id == account_id,
            ContextNode.node_type.in_(['DECISION', 'OUTCOME', 'STAKEHOLDER']),
        )
        .all()
    )

    _TITLE_CHAMPION_KW = ('champion', 'executive left', 'executive depart',
                          'sponsor left', 'sponsor depart', 'key contact left',
                          'disengag', 'no longer', 'resigned')
    _TITLE_BUDGET_KW = ('budget', 'cost cut', 'cost reduction', 'freeze',
                        'financial constraint', 'headcount', 'procurement hold')
    _TITLE_COMPETITOR_KW = ('competitor', 'competing vendor', 'rfp', 'evaluation',
                             'bake-off', 'competitive', 'vendor review')
    _TITLE_DEPLOY_KW = ('deployment blocked', 'deploy stuck', 'integration fail',
                        'blocker', 'technical issue', 'implementation stall')
    _TITLE_EXPANSION_KW = ('expansion', 'upsell', 'growth opportunity', 'new use case',
                           'additional license', 'upgrade')

    for node in _all_nodes:
        text = ((node.title or '') + ' ' + str(node.properties or '')).lower()
        if any(kw in text for kw in _TITLE_CHAMPION_KW):
            signal_types['_champion_departure_detected'] += 1
        if any(kw in text for kw in _TITLE_BUDGET_KW):
            signal_types['_budget_concern_detected'] += 1
        if any(kw in text for kw in _TITLE_COMPETITOR_KW):
            signal_types['_competitor_detected'] += 1
        if any(kw in text for kw in _TITLE_DEPLOY_KW):
            signal_types['_deployment_blocked_detected'] += 1
        if any(kw in text for kw in _TITLE_EXPANSION_KW):
            signal_types['_expansion_detected'] += 1

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
                          'champion_departure', 'disengaged', 'churned',
                          'no longer at', 'left the company', 'stepped down')

    has_stakeholder_departure = False
    for sn in stakeholder_nodes:
        title_lower = (sn.title or '').lower()
        subtype_lower = (sn.node_subtype or '').lower()
        if any(kw in title_lower or kw in subtype_lower for kw in departure_keywords):
            has_stakeholder_departure = True
            break

    # Also check SIGNAL nodes for champion/departure type signals
    if not has_stakeholder_departure:
        if _has(signal_types, _CHAMPION_LOSS_SIGNALS):
            has_stakeholder_departure = True

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
    Determine which of 4 phases the account is in, based on health score,
    trajectory slope, and signal composition.

    4-Phase Model (maps to NRR Death Spiral):
      Phase 1 — Baseline:       Healthy, stable. No action needed.
      Phase 2 — Deterioration:  Early warning signs, KPIs declining.
      Phase 3 — Intervention:   Critical, CSM actively engaged.
      Phase 4 — Resolution:     Recovering from crisis OR confirmed churn.

    Falls back to legacy 2-phase labels ('baseline'/'intervention') for arcs
    that haven't been updated to 4-phase format yet.
    """
    health = features['health_now']
    slope = features['slope_30d']

    # Phase 4 — Resolution: recovering from crisis, health rebuilding
    # Must check first: an improving account above crisis floor
    if health >= 55 and slope > 3:
        return 'resolution'

    # Phase 3 — Intervention: in crisis or just starting recovery
    if health < 50:
        return 'intervention'

    # Phase 2 — Deterioration: declining, early warning zone
    if slope < -1 and health < 75:
        return 'deterioration'

    # Phase 1 — Baseline: healthy and stable
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
        return 'seasonal_surge', 0.5, 'baseline'

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
