"""
Arc Edge Generator — generates ContextEdge rows for an account from its arc type.

Backend equivalent of load-driver RefRegistry + generate_signal_edges_csv().
Queries real ContextNode rows by occurred_at order, applies arc edge_topology
template, performs temporal validation, INSERTs ContextEdge rows.

4-Phase Model:
  Phase 1 — baseline:       Healthy, stable. Growth signals.
  Phase 2 — deterioration:  Early warning, KPIs declining.
  Phase 3 — intervention:   Critical, CSM actively engaged.
  Phase 4 — resolution:     Recovering from crisis OR confirmed outcome.

All 8 canonical arc types from config/story_arcs/ are supported.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE_ORDER — which phases to include for each detected phase
# ═══════════════════════════════════════════════════════════════════════════════

PHASE_ORDER = ['baseline', 'deterioration', 'intervention', 'resolution']

def phases_up_to(current_phase: str) -> list[str]:
    """Return all phases from baseline up to and including current_phase."""
    if current_phase not in PHASE_ORDER:
        return [current_phase]  # Unknown phase → just use it directly
    idx = PHASE_ORDER.index(current_phase)
    return PHASE_ORDER[:idx + 1]


# ═══════════════════════════════════════════════════════════════════════════════
# ARC_TEMPLATES — 8 canonical arcs with 4-phase edge topology
#
# Reference formats supported by InDBRefRegistry:
#   signal:N       → Nth SIGNAL node (1-indexed by occurred_at)
#   decision:N     → Nth DECISION node (1-indexed)
#   outcome:N      → Nth OUTCOME node (1-indexed, positional)
#   outcome:name   → OUTCOME by subtype/title match (fuzzy)
#
# Each edge_topology entry: {phase, from, to, type, confidence, lag_days, label}
# ═══════════════════════════════════════════════════════════════════════════════

ARC_TEMPLATES: dict[str, dict] = {

    # ── 1. CRISIS RECOVERY ──────────────────────────────────────────────
    # Critical incident → war room → systematic recovery → expansion
    'crisis_recovery': {
        'edge_topology': [
            # Phase 1: Baseline — early signals
            {'phase': 'baseline',      'from': 'signal:1',   'to': 'signal:2',   'type': 'LED_TO',    'confidence': 0.70, 'lag_days': 14, 'label': 'Initial signal preceded escalation'},
            {'phase': 'baseline',      'from': 'signal:2',   'to': 'signal:3',   'type': 'LED_TO',    'confidence': 0.65, 'lag_days': 14, 'label': 'Engagement patterns shifted'},
            # Phase 2: Deterioration — crisis emerges
            {'phase': 'deterioration', 'from': 'signal:3',   'to': 'signal:4',   'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 7,  'label': 'Signals escalated to critical incident'},
            {'phase': 'deterioration', 'from': 'signal:4',   'to': 'decision:1', 'type': 'TRIGGERED', 'confidence': 0.90, 'lag_days': 3,  'label': 'Critical incident triggered war room'},
            {'phase': 'deterioration', 'from': 'signal:1',   'to': 'outcome:1',  'type': 'CAUSED_BY', 'confidence': 0.75, 'lag_days': 30, 'label': 'Early signals caused revenue risk'},
            # Phase 3: Intervention — active response
            {'phase': 'intervention',  'from': 'decision:1', 'to': 'decision:2', 'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 7,  'label': 'War room led to recovery plan'},
            {'phase': 'intervention',  'from': 'decision:2', 'to': 'signal:5',   'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 14, 'label': 'Recovery plan generated new engagement'},
            # Phase 4: Resolution — recovery confirmed
            {'phase': 'resolution',    'from': 'signal:5',   'to': 'outcome:2',  'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 21, 'label': 'Engagement recovery protected revenue'},
            {'phase': 'resolution',    'from': 'decision:1', 'to': 'outcome:2',  'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 45, 'label': 'War room intervention secured renewal'},
        ],
    },

    # ── 2. EXEC SPONSOR CHANGE ──────────────────────────────────────────
    # Champion/exec departs → engagement vacuum → stakeholder mapping → rebuild
    'exec_sponsor_change': {
        'edge_topology': [
            # Phase 1: Baseline — relationship healthy
            {'phase': 'baseline',      'from': 'signal:1',   'to': 'signal:2',   'type': 'LED_TO',    'confidence': 0.65, 'lag_days': 14, 'label': 'Routine engagement before departure'},
            # Phase 2: Deterioration — departure cascade
            {'phase': 'deterioration', 'from': 'signal:2',   'to': 'signal:3',   'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 7,  'label': 'Champion departure created engagement gap'},
            {'phase': 'deterioration', 'from': 'signal:3',   'to': 'signal:4',   'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 14, 'label': 'Engagement gap led to usage decline'},
            {'phase': 'deterioration', 'from': 'signal:3',   'to': 'outcome:1',  'type': 'CAUSED_BY', 'confidence': 0.80, 'lag_days': 30, 'label': 'Champion departure caused renewal uncertainty'},
            # Phase 3: Intervention — stakeholder mapping + exec re-engagement
            {'phase': 'intervention',  'from': 'signal:4',   'to': 'decision:1', 'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Usage decline triggered stakeholder mapping'},
            {'phase': 'intervention',  'from': 'decision:1', 'to': 'decision:2', 'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 14, 'label': 'Mapping led to exec re-engagement plan'},
            # Phase 4: Resolution — new relationship established
            {'phase': 'resolution',    'from': 'decision:2', 'to': 'outcome:2',  'type': 'LED_TO',    'confidence': 0.75, 'lag_days': 21, 'label': 'Re-engagement secured new champion relationship'},
        ],
    },

    # ── 3. COMPETITIVE DISPLACEMENT ─────────────────────────────────────
    # Competitor threat → budget pressure → value defense → retention
    'competitive_displacement': {
        'edge_topology': [
            # Phase 1: Baseline — stable but competitor lurking
            {'phase': 'baseline',      'from': 'signal:1',   'to': 'signal:2',   'type': 'LED_TO',    'confidence': 0.65, 'lag_days': 14, 'label': 'Early engagement before competitive threat'},
            # Phase 2: Deterioration — competitor emerges
            {'phase': 'deterioration', 'from': 'signal:2',   'to': 'signal:3',   'type': 'LED_TO',    'confidence': 0.75, 'lag_days': 14, 'label': 'Competitor mention triggered budget review'},
            {'phase': 'deterioration', 'from': 'signal:3',   'to': 'signal:4',   'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 14, 'label': 'Budget pressure escalated retention risk'},
            {'phase': 'deterioration', 'from': 'signal:2',   'to': 'outcome:1',  'type': 'CAUSED_BY', 'confidence': 0.75, 'lag_days': 30, 'label': 'Competitive threat put revenue at risk'},
            # Phase 3: Intervention — value defense
            {'phase': 'intervention',  'from': 'signal:4',   'to': 'decision:1', 'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Escalation triggered competitive defense'},
            {'phase': 'intervention',  'from': 'decision:1', 'to': 'decision:2', 'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 7,  'label': 'Defense required executive engagement'},
            # Phase 4: Resolution — threat neutralized
            {'phase': 'resolution',    'from': 'decision:2', 'to': 'outcome:2',  'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 21, 'label': 'Executive engagement secured multi-year commitment'},
        ],
    },

    # ── 4. SILENT CHURN ─────────────────────────────────────────────────
    # Hidden risk → engagement fading → NPS drops → late detection
    'silent_churn': {
        'edge_topology': [
            # Phase 1: Baseline — appears healthy
            {'phase': 'baseline',      'from': 'signal:1',   'to': 'signal:2',   'type': 'LED_TO',    'confidence': 0.60, 'lag_days': 14, 'label': 'Routine activity masking disengagement'},
            # Phase 2: Deterioration — subtle decline
            {'phase': 'deterioration', 'from': 'signal:2',   'to': 'signal:3',   'type': 'LED_TO',    'confidence': 0.70, 'lag_days': 14, 'label': 'Engagement gap led to NPS decline'},
            {'phase': 'deterioration', 'from': 'signal:3',   'to': 'signal:4',   'type': 'LED_TO',    'confidence': 0.75, 'lag_days': 14, 'label': 'Dissatisfaction drove usage decline'},
            {'phase': 'deterioration', 'from': 'signal:4',   'to': 'signal:5',   'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 21, 'label': 'Usage decline attracted competitor eval'},
            {'phase': 'deterioration', 'from': 'signal:3',   'to': 'outcome:1',  'type': 'CAUSED_BY', 'confidence': 0.70, 'lag_days': 30, 'label': 'Silent disengagement created churn risk'},
            # Phase 3: Intervention — late detection
            {'phase': 'intervention',  'from': 'signal:5',   'to': 'decision:1', 'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Platform detected hidden risk → exec intervention'},
            {'phase': 'intervention',  'from': 'decision:1', 'to': 'decision:2', 'type': 'LED_TO',    'confidence': 0.75, 'lag_days': 14, 'label': 'Intervention launched re-engagement campaign'},
            # Phase 4: Resolution — saved or lost
            {'phase': 'resolution',    'from': 'decision:2', 'to': 'outcome:2',  'type': 'LED_TO',    'confidence': 0.65, 'lag_days': 21, 'label': 'Re-engagement outcome determined'},
        ],
    },

    # ── 5. STALLED DEPLOYMENT ───────────────────────────────────────────
    # Deployment stalls → idle capacity → acceleration playbook → completion
    'stalled_deployment': {
        'edge_topology': [
            # Phase 1: Baseline — deployment begins
            {'phase': 'baseline',      'from': 'signal:1',   'to': 'signal:2',   'type': 'LED_TO',    'confidence': 0.70, 'lag_days': 14, 'label': 'Initial deployment milestones progressing'},
            # Phase 2: Deterioration — velocity collapse
            {'phase': 'deterioration', 'from': 'signal:2',   'to': 'signal:3',   'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 14, 'label': 'Deployment velocity collapsed'},
            {'phase': 'deterioration', 'from': 'signal:3',   'to': 'signal:4',   'type': 'LED_TO',    'confidence': 0.75, 'lag_days': 14, 'label': 'Stall created support escalations'},
            {'phase': 'deterioration', 'from': 'signal:3',   'to': 'outcome:1',  'type': 'CAUSED_BY', 'confidence': 0.80, 'lag_days': 21, 'label': 'Deployment stall put renewal at risk'},
            # Phase 3: Intervention — acceleration
            {'phase': 'intervention',  'from': 'signal:4',   'to': 'decision:1', 'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Escalation triggered acceleration playbook'},
            {'phase': 'intervention',  'from': 'decision:1', 'to': 'decision:2', 'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 14, 'label': 'Acceleration plan assigned dedicated SE'},
            # Phase 4: Resolution — deployment completed
            {'phase': 'resolution',    'from': 'decision:2', 'to': 'outcome:2',  'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 28, 'label': 'Acceleration completed deployment ahead of schedule'},
        ],
    },

    # ── 6. LAND AND EXPAND ──────────────────────────────────────────────
    # New logo → adoption → value realization → expansion
    'land_and_expand': {
        'edge_topology': [
            # Phase 1: Baseline — onboarding + early adoption
            {'phase': 'baseline',      'from': 'signal:1',   'to': 'signal:2',   'type': 'LED_TO',    'confidence': 0.75, 'lag_days': 14, 'label': 'Onboarding drove initial adoption'},
            {'phase': 'baseline',      'from': 'signal:2',   'to': 'decision:1', 'type': 'TRIGGERED', 'confidence': 0.80, 'lag_days': 14, 'label': 'Adoption velocity triggered value assessment'},
            {'phase': 'baseline',      'from': 'decision:1', 'to': 'outcome:1',  'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 21, 'label': 'Value confirmed — expansion opportunity identified'},
            # Phase 2: Deterioration — N/A for growth arcs (skip)
            # Phase 3: Intervention — expansion push
            {'phase': 'intervention',  'from': 'signal:3',   'to': 'decision:2', 'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Expansion signal triggered proposal'},
            {'phase': 'intervention',  'from': 'decision:2', 'to': 'outcome:2',  'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 21, 'label': 'Expansion proposal approved'},
            # Phase 4: Resolution — expansion closed
            {'phase': 'resolution',    'from': 'outcome:1',  'to': 'outcome:2',  'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 30, 'label': 'Initial value realization led to expansion close'},
        ],
    },

    # ── 7. EXPANSION CHAMPION ───────────────────────────────────────────
    # Champion advocates → multi-dept adoption → capacity expansion
    'expansion_champion': {
        'edge_topology': [
            # Phase 1: Baseline — champion engaged, adoption growing
            {'phase': 'baseline',      'from': 'signal:1',   'to': 'signal:2',   'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 14, 'label': 'Champion advocacy drove cross-team adoption'},
            {'phase': 'baseline',      'from': 'signal:2',   'to': 'signal:3',   'type': 'LED_TO',    'confidence': 0.75, 'lag_days': 14, 'label': 'Adoption breadth created capacity demand'},
            {'phase': 'baseline',      'from': 'signal:3',   'to': 'decision:1', 'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Demand triggered expansion conversation'},
            {'phase': 'baseline',      'from': 'decision:1', 'to': 'outcome:1',  'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 21, 'label': 'Expansion conversation identified opportunity'},
            # Phase 3: Intervention — formalize expansion
            {'phase': 'intervention',  'from': 'signal:4',   'to': 'decision:2', 'type': 'TRIGGERED', 'confidence': 0.90, 'lag_days': 7,  'label': 'Usage milestone triggered expansion proposal'},
            {'phase': 'intervention',  'from': 'decision:2', 'to': 'outcome:2',  'type': 'LED_TO',    'confidence': 0.90, 'lag_days': 14, 'label': 'Expansion closed — ARR uplift secured'},
            # Phase 4: Resolution — growth confirmed
            {'phase': 'resolution',    'from': 'outcome:1',  'to': 'outcome:2',  'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 30, 'label': 'Systematic expansion from champion-driven growth'},
        ],
    },

    # ── 8. SEASONAL SURGE ───────────────────────────────────────────────
    # Predictable pattern → proactive capacity planning → expansion
    'seasonal_surge': {
        'edge_topology': [
            # Phase 1: Baseline — steady state
            {'phase': 'baseline',      'from': 'signal:1',   'to': 'signal:2',   'type': 'LED_TO',    'confidence': 0.70, 'lag_days': 14, 'label': 'Steady engagement patterns established'},
            {'phase': 'baseline',      'from': 'signal:2',   'to': 'decision:1', 'type': 'TRIGGERED', 'confidence': 0.75, 'lag_days': 14, 'label': 'Usage pattern triggered capacity review'},
            # Phase 3: Intervention — proactive planning
            {'phase': 'intervention',  'from': 'decision:1', 'to': 'decision:2', 'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 14, 'label': 'Review led to pre-surge expansion proposal'},
            {'phase': 'intervention',  'from': 'decision:2', 'to': 'outcome:1',  'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 21, 'label': 'Proactive expansion captured surge revenue'},
            # Phase 4: Resolution — surge handled
            {'phase': 'resolution',    'from': 'outcome:1',  'to': 'outcome:2',  'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 14, 'label': 'Surge handled smoothly — cost avoidance confirmed'},
        ],
    },
}

# Causal edge types that require temporal validation (from must precede to)
CAUSAL_EDGE_TYPES: frozenset[str] = frozenset({'LED_TO', 'TRIGGERED', 'CAUSED_BY'})


# ═══════════════════════════════════════════════════════════════════════════════
# InDBRefRegistry — resolves symbolic refs to real ContextNode IDs
# ═══════════════════════════════════════════════════════════════════════════════

class InDBRefRegistry:
    """
    Builds ref→node_id map from real ContextNode rows ordered by occurred_at.

    Symbolic ref formats:
      'signal:N'          → Nth SIGNAL node (1-indexed, ordered by occurred_at)
      'decision:N'        → Nth DECISION node (1-indexed)
      'outcome:N'         → Nth OUTCOME node (1-indexed, positional)
      'outcome:type_name' → OUTCOME node where subtype/title matches (fuzzy)
    """

    def __init__(self, account_id: int):
        self.account_id = account_id
        self._signals: list[tuple[int, Optional[datetime]]] = []
        self._decisions: list[tuple[int, Optional[datetime]]] = []
        self._outcomes: dict[str, tuple[int, Optional[datetime]]] = {}
        self._outcomes_by_idx: list[tuple[int, Optional[datetime]]] = []
        self._build()

    def _build(self):
        from models import ContextNode
        from extensions import db

        nodes = (
            db.session.query(ContextNode)
            .filter_by(account_id=self.account_id)
            .order_by(ContextNode.occurred_at)
            .all()
        )

        for n in nodes:
            ts = n.occurred_at
            if n.node_type == 'SIGNAL':
                self._signals.append((n.node_id, ts))
            elif n.node_type == 'DECISION':
                self._decisions.append((n.node_id, ts))
            elif n.node_type == 'OUTCOME':
                self._outcomes_by_idx.append((n.node_id, ts))
                if n.node_subtype:
                    otype = n.node_subtype.strip().lower()
                    self._outcomes[otype] = (n.node_id, ts)
                props = n.properties or {}
                outcome_type = str(props.get('outcome_type', '')).strip().lower()
                if outcome_type and outcome_type not in self._outcomes:
                    self._outcomes[outcome_type] = (n.node_id, ts)
                if n.title:
                    title_key = n.title.strip().lower().replace(' ', '_')
                    if title_key not in self._outcomes:
                        self._outcomes[title_key] = (n.node_id, ts)

        logger.debug(
            f"InDBRefRegistry: acct={self.account_id} "
            f"signals={len(self._signals)} decisions={len(self._decisions)} "
            f"outcomes={len(self._outcomes_by_idx)}"
        )

    def resolve(self, symbolic: str) -> Optional[tuple[int, Optional[datetime]]]:
        """Resolve a symbolic reference to (node_id, occurred_at)."""
        if not symbolic:
            return None

        if symbolic.startswith('signal:'):
            try:
                idx = int(symbolic.split(':', 1)[1]) - 1
            except (ValueError, IndexError):
                return None
            return self._signals[idx] if 0 <= idx < len(self._signals) else None

        if symbolic.startswith('decision:'):
            try:
                idx = int(symbolic.split(':', 1)[1]) - 1
            except (ValueError, IndexError):
                return None
            return self._decisions[idx] if 0 <= idx < len(self._decisions) else None

        if symbolic.startswith('outcome:'):
            otype = symbolic.split(':', 1)[1].strip().lower()
            # 1. Exact subtype match
            hit = self._outcomes.get(otype)
            if hit:
                return hit
            # 2. Positional (outcome:1, outcome:2)
            try:
                idx = int(otype) - 1
                return self._outcomes_by_idx[idx] if 0 <= idx < len(self._outcomes_by_idx) else None
            except ValueError:
                pass
            # 3. Fuzzy partial match
            for key, val in self._outcomes.items():
                if otype in key or key in otype:
                    return val
            # 4. Last resort: first outcome
            if len(self._outcomes_by_idx) == 1:
                return self._outcomes_by_idx[0]
            return None

        return None


# ═══════════════════════════════════════════════════════════════════════════════
# generate_edges — main public function
# ═══════════════════════════════════════════════════════════════════════════════

def generate_edges(account_id: int, arc_type: str, phase: str = 'baseline') -> int:
    """
    Generate ContextEdge rows for account using arc edge_topology.

    Generates edges for ALL phases up to and including the detected phase.
    E.g., if phase='intervention', generates baseline + deterioration + intervention edges.

    Idempotent: deletes existing edges for this account before inserting new ones.

    Returns count of edges created.
    """
    from models import ContextEdge, ContextNode
    from extensions import db

    # ── Arc type resolution ──
    _ARC_ALIASES = {
        'champion_loss': 'exec_sponsor_change',
        'competitor_evaluation': 'competitive_displacement',
        'ignored_churn': 'silent_churn',
        'proactive_growth': 'expansion_champion',
        'infrastructure_decay': 'stalled_deployment',
        'engagement_decline': 'silent_churn',
        'budget_pressure': 'competitive_displacement',
        'steady_performer': 'seasonal_surge',
        'crisis': 'crisis_recovery',
    }
    resolved_type = _ARC_ALIASES.get(arc_type, arc_type)
    arc_def = ARC_TEMPLATES.get(resolved_type)
    if not arc_def:
        arc_def = ARC_TEMPLATES.get('seasonal_surge', {})

    if resolved_type != arc_type:
        logger.info(f"arc_edge_generator: aliased '{arc_type}' → '{resolved_type}' for account {account_id}")

    # ── Collect edges for ALL phases up to current ──
    active_phases = phases_up_to(phase)
    topology = [
        e for e in arc_def.get('edge_topology', [])
        if e.get('phase', 'baseline') in active_phases
    ]

    if not topology:
        logger.warning(
            f"arc_edge_generator: no topology for arc={resolved_type} "
            f"phases={active_phases} account={account_id}"
        )
        return 0

    # Delete existing edges for this account (idempotent re-run)
    account_node_ids = (
        db.session.query(ContextNode.node_id)
        .filter_by(account_id=account_id)
        .subquery()
    )
    db.session.query(ContextEdge).filter(
        (ContextEdge.from_node_id.in_(account_node_ids))
        | (ContextEdge.to_node_id.in_(account_node_ids))
    ).delete(synchronize_session='fetch')

    registry = InDBRefRegistry(account_id)
    created = 0

    account_node = (
        db.session.query(ContextNode)
        .filter_by(account_id=account_id)
        .first()
    )
    customer_id = account_node.customer_id if account_node else None

    for edge_def in topology:
        from_resolved = registry.resolve(edge_def.get('from', ''))
        to_resolved   = registry.resolve(edge_def.get('to', ''))

        if from_resolved is None or to_resolved is None:
            logger.debug(
                f"arc_edge_generator: unresolved ref acct={account_id} "
                f"arc={resolved_type} phase={edge_def.get('phase')} "
                f"from={edge_def.get('from')!r}→{from_resolved is not None} "
                f"to={edge_def.get('to')!r}→{to_resolved is not None}"
            )
            continue

        from_id, from_date = from_resolved
        to_id,   to_date   = to_resolved

        if from_id == to_id:
            continue  # Self-loop — skip

        edge_type = edge_def.get('type', 'RELATES_TO')

        # Temporal validation for causal edges
        if (edge_type in CAUSAL_EDGE_TYPES
                and from_date is not None
                and to_date is not None
                and from_date >= to_date):
            logger.debug(
                f"arc_edge_generator: temporal skip acct={account_id} "
                f"{edge_def.get('from')!r}→{edge_def.get('to')!r}"
            )
            continue

        edge = ContextEdge(
            customer_id  = customer_id,
            from_node_id = from_id,
            to_node_id   = to_id,
            edge_type    = edge_type,
            confidence   = edge_def.get('confidence', 0.7),
            lag_days     = edge_def.get('lag_days', 0),
            properties   = {
                'label': edge_def.get('label', ''),
                'arc_type': resolved_type,
                'arc_phase': edge_def.get('phase', 'baseline'),
            },
            source_platform = 'wizard_a',
            created_by   = 'arc_edge_generator',
        )
        db.session.add(edge)
        created += 1

    db.session.commit()
    logger.info(
        f"arc_edge_generator: created {created} edges "
        f"acct={account_id} arc={resolved_type} phases={active_phases}"
    )
    return created
