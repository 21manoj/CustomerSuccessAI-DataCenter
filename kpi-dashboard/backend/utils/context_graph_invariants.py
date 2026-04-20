"""
Context Graph Invariants — data-quality validators that catch systemic bugs.

Runs as a non-blocking audit after Wizard A and after context graph ingest.
Each invariant is a pure function that takes customer_id and returns a list
of Violations. Violations are logged as WARN; they never raise or roll back.

Built in response to an external investigation that surfaced 7 platform-level
data bugs (April 2026, customer 385 / Relay Healthcare / Nimbus Logistics):
- OUTCOME→OUTCOME edges (backwards causality)
- Positive signals linked as causes of churn outcomes
- Orphan OUTCOME nodes with revenue impact
- confidence > 1.0
- account_status not reconciled with lifecycle events
- Duplicate churn outcomes
- Churn-averted coexisting with churn-lost on same account
- Revenue bucket mislabels

Any new invariant: add to INVARIANTS_REGISTRY at the bottom.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════
# Violation schema
# ═════════════════════════════════════════════════════════════════════


@dataclass
class Violation:
    """A single data-quality violation found by an invariant check."""

    invariant_id: str  # e.g. 'I1'
    invariant_name: str
    severity: Literal['error', 'warning']
    customer_id: int
    message: str
    account_id: Optional[int] = None
    node_ids: List[int] = field(default_factory=list)
    edge_ids: List[int] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═════════════════════════════════════════════════════════════════════
# Canonical polarity + arc taxonomy (single source of truth)
# ═════════════════════════════════════════════════════════════════════


NEGATIVE_OUTCOME_SUBTYPES = {
    'churn_lost', 'contraction', 'renewal_at_risk', 'revenue_at_risk',
    'escalation', 'intervention_outcome',
}

POSITIVE_OUTCOME_SUBTYPES = {
    'expansion_closed', 'new_logo', 'revenue_protected',
    'playbook_outcome', 'recovery_milestone', 'churn_averted',
}

NEGATIVE_SIGNAL_SUBTYPES = {
    'champion_loss', 'engagement_drop', 'usage_decline', 'kpi_decline',
    'escalation', 'support_escalation', 'executive_escalation',
    'critical_incident', 'competitive_eval', 'silent_churn',
    'budget_cut', 'contract_dispute', 'downgrade_request',
    'arc_detection', 'crisis_event', 'integration_stall', 'churn_signal',
}

POSITIVE_SIGNAL_SUBTYPES = {
    'kpi_recovery', 'usage_spike', 'champion_reengagement',
    'executive_engagement', 'expansion_signal', 'csm_intervention',
    'feature_adoption_push', 'deployment_improvement',
    'recovery_milestone', 'qbr_positive', 'qbr_alignment',
    'adoption_growth', 'seasonal_peak', 'capacity_add',
    'health_improvement',
}

CAUSAL_EDGE_TYPES = {'CAUSED_BY', 'LED_TO', 'TRIGGERED', 'INDICATES', 'RESULTED_IN'}

# Canonical arc taxonomy — any arc_type value not in this set is invalid.
# Kept narrow intentionally: extend via explicit review, not by accretion.
CANONICAL_ARC_TYPES = {
    'crisis_recovery', 'expansion_champion', 'champion_loss',
    'silent_churn', 'infrastructure_decay', 'stalled_deployment',
    'competitive_displacement', 'land_and_expand', 'seasonal_surge',
    'exec_sponsor_change', 'stable_healthy', 'new_onboarding',
    # Legacy / trajectory-classifier vocabulary — allowed during migration.
    # Remove these entries once wizard_a_journey_db.py emits canonical values.
    'crisis', 'improving', 'recovery', 'declining', 'stable',
}

# Revenue buckets — which outcome subtypes belong in which bucket.
# Used by I11 to catch mis-classifications like 'capacity_constraint' in 'lost'.
REVENUE_BUCKET_MAP = {
    'at_risk': {'renewal_at_risk', 'revenue_at_risk'},
    'lost': {'churn_lost', 'contraction'},
    'expansion': {'expansion_closed', 'new_logo', 'revenue_expanded'},
    'protected': {'revenue_protected', 'churn_averted', 'playbook_outcome'},
}


# ═════════════════════════════════════════════════════════════════════
# Individual invariant functions
# ═════════════════════════════════════════════════════════════════════


def invariant_i1_no_outcome_to_outcome(customer_id: int) -> List[Violation]:
    """I1: No OUTCOME→OUTCOME causal edges (backwards causality).

    An OUTCOME is a realized result. It can't be the CAUSE of another OUTCOME
    in the same account without an intermediate DECISION or SIGNAL.
    """
    from models import ContextEdge, ContextNode, db  # noqa: PLC0415

    from_alias = db.aliased(ContextNode)
    to_alias = db.aliased(ContextNode)

    rows = (
        db.session.query(ContextEdge, from_alias, to_alias)
        .join(from_alias, ContextEdge.from_node_id == from_alias.node_id)
        .join(to_alias, ContextEdge.to_node_id == to_alias.node_id)
        .filter(
            ContextEdge.customer_id == customer_id,
            ContextEdge.edge_type.in_(CAUSAL_EDGE_TYPES),
            from_alias.node_type == 'OUTCOME',
            to_alias.node_type == 'OUTCOME',
        )
        .all()
    )

    violations: List[Violation] = []
    for edge, fn, tn in rows:
        violations.append(Violation(
            invariant_id='I1',
            invariant_name='no_outcome_to_outcome_edges',
            severity='error',
            customer_id=customer_id,
            account_id=tn.account_id,
            node_ids=[fn.node_id, tn.node_id],
            edge_ids=[edge.edge_id],
            message=(
                f'OUTCOME→OUTCOME edge: "{fn.title[:50]}" ({fn.node_subtype}) '
                f'--{edge.edge_type}--> "{tn.title[:50]}" ({tn.node_subtype}) '
                f'via {edge.source_platform}'
            ),
            details={
                'from_subtype': fn.node_subtype,
                'to_subtype': tn.node_subtype,
                'edge_type': edge.edge_type,
                'source_platform': edge.source_platform,
            },
        ))
    return violations


def invariant_i2_polarity_consistency(customer_id: int) -> List[Violation]:
    """I2: No positive-signal → negative-outcome causal edges (and vice versa).

    kpi_recovery cannot CAUSE churn_lost. executive_engagement cannot cause
    a renewal_at_risk. Polarity must match through causal chains.
    """
    from models import ContextEdge, ContextNode, db  # noqa: PLC0415

    from_alias = db.aliased(ContextNode)
    to_alias = db.aliased(ContextNode)

    rows = (
        db.session.query(ContextEdge, from_alias, to_alias)
        .join(from_alias, ContextEdge.from_node_id == from_alias.node_id)
        .join(to_alias, ContextEdge.to_node_id == to_alias.node_id)
        .filter(
            ContextEdge.customer_id == customer_id,
            ContextEdge.edge_type.in_(CAUSAL_EDGE_TYPES),
            from_alias.node_type == 'SIGNAL',
            to_alias.node_type == 'OUTCOME',
        )
        .all()
    )

    violations: List[Violation] = []
    for edge, fn, tn in rows:
        fs = fn.node_subtype or ''
        ts = tn.node_subtype or ''
        mismatch = None
        if ts in NEGATIVE_OUTCOME_SUBTYPES and fs in POSITIVE_SIGNAL_SUBTYPES:
            mismatch = 'positive_signal_to_negative_outcome'
        elif ts in POSITIVE_OUTCOME_SUBTYPES and fs in NEGATIVE_SIGNAL_SUBTYPES:
            mismatch = 'negative_signal_to_positive_outcome'
        if not mismatch:
            continue
        violations.append(Violation(
            invariant_id='I2',
            invariant_name='polarity_consistency',
            severity='error',
            customer_id=customer_id,
            account_id=tn.account_id,
            node_ids=[fn.node_id, tn.node_id],
            edge_ids=[edge.edge_id],
            message=(
                f'Polarity mismatch ({mismatch}): '
                f'{fs} --{edge.edge_type}--> {ts} via {edge.source_platform}'
            ),
            details={'mismatch_type': mismatch, 'source_platform': edge.source_platform},
        ))
    return violations


def invariant_i3_no_orphan_revenue_outcomes(customer_id: int) -> List[Violation]:
    """I3: Every OUTCOME node with revenue_impact has ≥1 inbound causal edge.

    Orphan revenue nodes are audit-indefensible ("we lost $500K here but we
    can't point to why"). Either provenance exists or the node shouldn't.
    """
    from sqlalchemy import exists  # noqa: PLC0415

    from models import ContextEdge, ContextNode, db  # noqa: PLC0415

    has_inbound = (
        db.session.query(ContextEdge.to_node_id)
        .filter(
            ContextEdge.customer_id == customer_id,
            ContextEdge.to_node_id == ContextNode.node_id,
            ContextEdge.edge_type.in_(CAUSAL_EDGE_TYPES),
        )
        .exists()
    )

    orphans = (
        ContextNode.query
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.node_type == 'OUTCOME',
            ContextNode.revenue_impact.isnot(None),
            ~has_inbound,
        )
        .all()
    )

    violations: List[Violation] = []
    for n in orphans:
        violations.append(Violation(
            invariant_id='I3',
            invariant_name='no_orphan_revenue_outcomes',
            severity='error',
            customer_id=customer_id,
            account_id=n.account_id,
            node_ids=[n.node_id],
            message=(
                f'Orphan OUTCOME ${float(n.revenue_impact or 0):,.0f}: '
                f'"{n.title[:70]}" ({n.node_subtype}) has zero inbound causal edges'
            ),
            details={
                'revenue_impact': float(n.revenue_impact or 0),
                'node_subtype': n.node_subtype,
                'revenue_impact_type': n.revenue_impact_type,
            },
        ))
    return violations


def invariant_i4_confidence_bounds(customer_id: int) -> List[Violation]:
    """I4: All confidence values ∈ [0, 1] — on both top-level fields and
    inside properties JSONB blobs.

    Confidence > 1 is mathematically invalid and leaks into ROI math.
    """
    from models import ContextEdge, ContextNode  # noqa: PLC0415

    violations: List[Violation] = []

    # Top-level confidence on nodes.
    bad_nodes = (
        ContextNode.query
        .filter(
            ContextNode.customer_id == customer_id,
            (ContextNode.confidence < 0) | (ContextNode.confidence > 1),
        )
        .all()
    )
    for n in bad_nodes:
        violations.append(Violation(
            invariant_id='I4',
            invariant_name='confidence_bounds',
            severity='error',
            customer_id=customer_id,
            account_id=n.account_id,
            node_ids=[n.node_id],
            message=(
                f'Node {n.node_id} confidence={n.confidence} (out of [0,1]): '
                f'"{n.title[:60]}"'
            ),
            details={
                'field': 'context_nodes.confidence',
                'value': float(n.confidence) if n.confidence is not None else None,
            },
        ))

    # Top-level confidence on edges.
    bad_edges = (
        ContextEdge.query
        .filter(
            ContextEdge.customer_id == customer_id,
            (ContextEdge.confidence < 0) | (ContextEdge.confidence > 1),
        )
        .all()
    )
    for e in bad_edges:
        violations.append(Violation(
            invariant_id='I4',
            invariant_name='confidence_bounds',
            severity='error',
            customer_id=customer_id,
            edge_ids=[e.edge_id],
            message=f'Edge {e.edge_id} confidence={e.confidence} (out of [0,1])',
            details={
                'field': 'context_edges.confidence',
                'value': float(e.confidence) if e.confidence is not None else None,
                'source_platform': e.source_platform,
            },
        ))

    # properties.confidence on nodes (JSONB).
    nodes_with_props = (
        ContextNode.query
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.properties.isnot(None),
        )
        .all()
    )
    for n in nodes_with_props:
        props = n.properties or {}
        if not isinstance(props, dict):
            continue
        v = props.get('confidence')
        try:
            vf = float(v)
        except (TypeError, ValueError):
            continue
        if vf < 0 or vf > 1:
            violations.append(Violation(
                invariant_id='I4',
                invariant_name='confidence_bounds',
                severity='warning',
                customer_id=customer_id,
                account_id=n.account_id,
                node_ids=[n.node_id],
                message=(
                    f'Node {n.node_id} properties.confidence={vf} (out of [0,1]): '
                    f'"{n.title[:60]}"'
                ),
                details={'field': 'context_nodes.properties.confidence', 'value': vf},
            ))
    return violations


def invariant_i5_arc_type_enum(customer_id: int) -> List[Violation]:
    """I5: Every arc_type value is in the canonical enum."""
    from models import ContextEdge, ContextNode  # noqa: PLC0415

    violations: List[Violation] = []

    # Nodes — arc_type may live in properties.arc_type OR as a column.
    nodes = (
        ContextNode.query
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.properties.isnot(None),
        )
        .all()
    )
    for n in nodes:
        props = n.properties or {}
        if not isinstance(props, dict):
            continue
        arc = props.get('arc_type')
        if arc is None:
            continue
        if arc not in CANONICAL_ARC_TYPES:
            violations.append(Violation(
                invariant_id='I5',
                invariant_name='arc_type_enum',
                severity='warning',
                customer_id=customer_id,
                account_id=n.account_id,
                node_ids=[n.node_id],
                message=f'Node {n.node_id} arc_type={arc!r} not in canonical enum',
                details={'arc_type': arc, 'field': 'context_nodes.properties.arc_type'},
            ))

    # Edges — arc_type in properties as well.
    edges = (
        ContextEdge.query
        .filter(
            ContextEdge.customer_id == customer_id,
            ContextEdge.properties.isnot(None),
        )
        .all()
    )
    for e in edges:
        props = e.properties or {}
        if not isinstance(props, dict):
            continue
        arc = props.get('arc_type')
        if arc is None:
            continue
        if arc not in CANONICAL_ARC_TYPES:
            violations.append(Violation(
                invariant_id='I5',
                invariant_name='arc_type_enum',
                severity='warning',
                customer_id=customer_id,
                edge_ids=[e.edge_id],
                message=f'Edge {e.edge_id} arc_type={arc!r} not in canonical enum',
                details={'arc_type': arc, 'field': 'context_edges.properties.arc_type'},
            ))
    return violations


def invariant_i6_churned_no_future_expansion(customer_id: int) -> List[Violation]:
    """I6: Churned accounts cannot have future-dated expansion_closed outcomes."""
    from models import Account, ContextNode  # noqa: PLC0415

    churned_accts = (
        Account.query
        .filter_by(customer_id=customer_id, account_status='churned')
        .all()
    )
    if not churned_accts:
        return []

    violations: List[Violation] = []
    for acct in churned_accts:
        # Use created_at as churn-time proxy if there's no explicit field.
        churn_time_proxy = acct.updated_at or acct.created_at
        bad = (
            ContextNode.query
            .filter(
                ContextNode.customer_id == customer_id,
                ContextNode.account_id == acct.account_id,
                ContextNode.node_type == 'OUTCOME',
                ContextNode.revenue_impact_type == 'expansion_closed',
            )
            .all()
        )
        for n in bad:
            if churn_time_proxy and n.occurred_at and n.occurred_at > churn_time_proxy:
                violations.append(Violation(
                    invariant_id='I6',
                    invariant_name='churned_no_future_expansion',
                    severity='error',
                    customer_id=customer_id,
                    account_id=acct.account_id,
                    node_ids=[n.node_id],
                    message=(
                        f'Churned account {acct.account_name!r} has expansion_closed '
                        f'OUTCOME at {n.occurred_at} after churn at ~{churn_time_proxy}'
                    ),
                    details={
                        'account_name': acct.account_name,
                        'expansion_occurred_at': str(n.occurred_at),
                        'churn_proxy_at': str(churn_time_proxy),
                    },
                ))
    return violations


def invariant_i8_churn_lost_reconciled(customer_id: int) -> List[Violation]:
    """I8: Every churn_lost OUTCOME ⇒ Account.account_status = 'churned'."""
    from models import Account, ContextNode  # noqa: PLC0415

    churn_outcomes = (
        ContextNode.query
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.node_type == 'OUTCOME',
            ContextNode.node_subtype == 'churn_lost',
        )
        .all()
    )
    if not churn_outcomes:
        return []

    acct_ids = {n.account_id for n in churn_outcomes if n.account_id}
    accts = {a.account_id: a for a in
             Account.query.filter(Account.account_id.in_(acct_ids)).all()}

    violations: List[Violation] = []
    for n in churn_outcomes:
        acct = accts.get(n.account_id)
        if not acct:
            continue
        if (acct.account_status or '').lower() != 'churned':
            violations.append(Violation(
                invariant_id='I8',
                invariant_name='churn_lost_reconciled',
                severity='error',
                customer_id=customer_id,
                account_id=acct.account_id,
                node_ids=[n.node_id],
                message=(
                    f'Account {acct.account_name!r} has churn_lost OUTCOME '
                    f'but account_status={acct.account_status!r} (expected churned)'
                ),
                details={
                    'account_name': acct.account_name,
                    'current_status': acct.account_status,
                },
            ))
    return violations


def invariant_i9_no_duplicate_lifecycle_outcomes(customer_id: int) -> List[Violation]:
    """I9: At most one churn_lost OUTCOME per account (no double-churn)."""
    from sqlalchemy import func  # noqa: PLC0415

    from models import Account, ContextNode, db  # noqa: PLC0415

    rows = (
        db.session.query(
            ContextNode.account_id,
            func.count(ContextNode.node_id).label('cnt'),
            func.array_agg(ContextNode.node_id).label('nids'),
        )
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.node_type == 'OUTCOME',
            ContextNode.node_subtype == 'churn_lost',
        )
        .group_by(ContextNode.account_id)
        .having(func.count(ContextNode.node_id) > 1)
        .all()
    )

    violations: List[Violation] = []
    for account_id, cnt, nids in rows:
        acct = Account.query.filter_by(account_id=account_id).first()
        violations.append(Violation(
            invariant_id='I9',
            invariant_name='no_duplicate_lifecycle_outcomes',
            severity='error',
            customer_id=customer_id,
            account_id=account_id,
            node_ids=list(nids or []),
            message=(
                f'Account {acct.account_name if acct else account_id!r} has {cnt} '
                f'churn_lost OUTCOME nodes (expected ≤1)'
            ),
            details={'account_name': acct.account_name if acct else None, 'count': cnt},
        ))
    return violations


def invariant_i10_no_averted_with_lost(customer_id: int) -> List[Violation]:
    """I10: A single account cannot have BOTH churn_averted and churn_lost OUTCOMEs.

    Either the churn was averted (stayed) OR lost (churned). Both flags on the
    same account means one of them is stale/wrong — a narrative contradiction.
    """
    from sqlalchemy import func  # noqa: PLC0415

    from models import Account, ContextNode, db  # noqa: PLC0415

    subtype_sets_by_account = (
        db.session.query(
            ContextNode.account_id,
            func.array_agg(func.distinct(ContextNode.node_subtype)).label('subs'),
        )
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.node_type == 'OUTCOME',
            ContextNode.node_subtype.in_(['churn_lost', 'churn_averted']),
        )
        .group_by(ContextNode.account_id)
        .all()
    )

    violations: List[Violation] = []
    for account_id, subs in subtype_sets_by_account:
        if not subs or len(set(subs)) < 2:
            continue  # only one of the two, fine
        acct = Account.query.filter_by(account_id=account_id).first()
        bad_nodes = (
            ContextNode.query
            .filter(
                ContextNode.customer_id == customer_id,
                ContextNode.account_id == account_id,
                ContextNode.node_subtype.in_(['churn_lost', 'churn_averted']),
            )
            .all()
        )
        violations.append(Violation(
            invariant_id='I10',
            invariant_name='no_averted_with_lost',
            severity='error',
            customer_id=customer_id,
            account_id=account_id,
            node_ids=[n.node_id for n in bad_nodes],
            message=(
                f'Account {acct.account_name if acct else account_id!r} has both '
                f'churn_averted AND churn_lost OUTCOMEs — mutually exclusive'
            ),
            details={
                'account_name': acct.account_name if acct else None,
                'subtypes': sorted(set(subs)),
            },
        ))
    return violations


def invariant_i11_revenue_bucket_consistency(customer_id: int) -> List[Violation]:
    """I11: revenue_impact_type falls in the documented bucket for its subtype.

    Catches cases like a capacity_constraint outcome being tagged as
    revenue_impact_type='lost' — the bucket map says that subtype isn't lost.
    """
    from models import ContextNode  # noqa: PLC0415

    # Build reverse map: subtype → allowed impact_types
    # (impact_type = the bucket name like 'lost', 'expansion', etc.)
    known_subtypes = set()
    for types in REVENUE_BUCKET_MAP.values():
        known_subtypes.update(types)

    nodes = (
        ContextNode.query
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.node_type == 'OUTCOME',
            ContextNode.revenue_impact_type.isnot(None),
            ContextNode.node_subtype.isnot(None),
        )
        .all()
    )

    violations: List[Violation] = []
    for n in nodes:
        sub = n.node_subtype
        bucket = n.revenue_impact_type  # e.g. 'lost', 'expansion', 'at_risk'
        if sub not in known_subtypes:
            continue  # unknown subtype — skip rather than false-positive
        allowed = REVENUE_BUCKET_MAP.get(bucket, set())
        if sub not in allowed:
            # Find what bucket it SHOULD be in
            expected = [b for b, subs in REVENUE_BUCKET_MAP.items() if sub in subs]
            violations.append(Violation(
                invariant_id='I11',
                invariant_name='revenue_bucket_consistency',
                severity='warning',
                customer_id=customer_id,
                account_id=n.account_id,
                node_ids=[n.node_id],
                message=(
                    f'Node {n.node_id} subtype={sub!r} is tagged revenue_impact_type='
                    f'{bucket!r} but belongs in {expected!r}'
                ),
                details={
                    'subtype': sub,
                    'actual_bucket': bucket,
                    'expected_buckets': expected,
                },
            ))
    return violations


def invariant_i12_account_status_health_consistency(customer_id: int) -> List[Violation]:
    """I12: Account.account_status should not be 'at_risk' if health_score >= 70.

    account_status is either (a) an independent business field that should
    never contradict health, or (b) a stale artifact that should be removed.
    Either way, a healthy (≥70) account tagged at_risk is a contradiction.
    """
    from models import Account, HealthScore, db  # noqa: PLC0415
    from sqlalchemy import func  # noqa: PLC0415

    # Latest health score per account
    latest_hs_subq = (
        db.session.query(
            HealthScore.account_id,
            func.max(HealthScore.measurement_month).label('mm'),
        )
        .group_by(HealthScore.account_id)
        .subquery()
    )
    latest_scores = (
        db.session.query(HealthScore.account_id, HealthScore.health_score)
        .join(
            latest_hs_subq,
            (HealthScore.account_id == latest_hs_subq.c.account_id)
            & (HealthScore.measurement_month == latest_hs_subq.c.mm),
        )
        .all()
    )
    score_map = {aid: float(s or 0) for aid, s in latest_scores}

    accts = Account.query.filter_by(customer_id=customer_id).all()
    violations: List[Violation] = []
    for a in accts:
        status = (a.account_status or '').lower()
        score = score_map.get(a.account_id)
        if score is None:
            continue
        # Don't flag churned accounts — that's a legitimate terminal state.
        if status == 'churned':
            continue
        if score >= 70 and status == 'at_risk':
            violations.append(Violation(
                invariant_id='I12',
                invariant_name='account_status_health_consistency',
                severity='warning',
                customer_id=customer_id,
                account_id=a.account_id,
                message=(
                    f'Account {a.account_name!r} health={score:.1f} (healthy) '
                    f'but account_status={status!r}'
                ),
                details={
                    'account_name': a.account_name,
                    'health_score': score,
                    'account_status': a.account_status,
                },
            ))
        elif score < 50 and status == 'active':
            violations.append(Violation(
                invariant_id='I12',
                invariant_name='account_status_health_consistency',
                severity='warning',
                customer_id=customer_id,
                account_id=a.account_id,
                message=(
                    f'Account {a.account_name!r} health={score:.1f} (critical) '
                    f'but account_status={status!r} (expected at_risk or intervention)'
                ),
                details={
                    'account_name': a.account_name,
                    'health_score': score,
                    'account_status': a.account_status,
                },
            ))
    return violations


# ═════════════════════════════════════════════════════════════════════
# Registry + public API
# ═════════════════════════════════════════════════════════════════════


INVARIANTS_REGISTRY: Dict[str, Callable[[int], List[Violation]]] = {
    'I1': invariant_i1_no_outcome_to_outcome,
    'I2': invariant_i2_polarity_consistency,
    'I3': invariant_i3_no_orphan_revenue_outcomes,
    'I4': invariant_i4_confidence_bounds,
    'I5': invariant_i5_arc_type_enum,
    'I6': invariant_i6_churned_no_future_expansion,
    'I8': invariant_i8_churn_lost_reconciled,
    'I9': invariant_i9_no_duplicate_lifecycle_outcomes,
    'I10': invariant_i10_no_averted_with_lost,
    'I11': invariant_i11_revenue_bucket_consistency,
    'I12': invariant_i12_account_status_health_consistency,
    # I7 (MCP param contract) is a pure code check — lives in tests, not here.
}


def run_all_invariants(customer_id: int) -> List[Violation]:
    """Run every invariant and return the flat list of violations."""
    all_violations: List[Violation] = []
    for inv_id, fn in INVARIANTS_REGISTRY.items():
        try:
            vs = fn(customer_id)
            all_violations.extend(vs)
        except Exception as e:
            logger.warning(
                'Invariant %s failed to execute for customer %d: %s',
                inv_id, customer_id, e,
            )
    return all_violations


def run_invariant(invariant_id: str, customer_id: int) -> List[Violation]:
    """Run a single invariant by ID."""
    fn = INVARIANTS_REGISTRY.get(invariant_id)
    if not fn:
        raise ValueError(f'Unknown invariant: {invariant_id!r}')
    return fn(customer_id)


def log_violations_summary(violations: List[Violation], customer_id: int) -> Dict[str, Any]:
    """Log a one-line WARN summary + per-invariant counts. Return the summary dict."""
    if not violations:
        logger.info('[context_graph_invariants] customer=%d: clean (0 violations)', customer_id)
        return {'customer_id': customer_id, 'total': 0, 'by_invariant': {}}

    by_inv: Dict[str, int] = {}
    for v in violations:
        by_inv[v.invariant_id] = by_inv.get(v.invariant_id, 0) + 1

    logger.warning(
        '[context_graph_invariants] customer=%d: %d violations — %s',
        customer_id, len(violations),
        ', '.join(f'{k}:{v}' for k, v in sorted(by_inv.items())),
    )
    # Log up to 5 example violations per invariant.
    for inv_id, _cnt in sorted(by_inv.items()):
        examples = [v for v in violations if v.invariant_id == inv_id][:5]
        for ex in examples:
            logger.warning(
                '  [%s] %s (account=%s, nodes=%s, edges=%s)',
                ex.invariant_id, ex.message, ex.account_id, ex.node_ids, ex.edge_ids,
            )

    return {
        'customer_id': customer_id,
        'total': len(violations),
        'by_invariant': by_inv,
        'timestamp': datetime.utcnow().isoformat(),
    }
