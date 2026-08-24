"""
Arc Decision Node Generator — materializes DECISION ContextNodes from arc manifests.

When customers use 4-CSV onboarding (no decisions.csv), the context graph lacks
DECISION nodes. This module reads the arc manifest's `decisions` array and creates
DECISION nodes so the arc_edge_generator can resolve `decision:N` references.

Called by Wizard A AFTER arc classification but BEFORE edge generation.

Idempotent: deletes existing wizard_a DECISION nodes before re-creating.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Map our 4-phase model to manifest phase_id ranges.
# Manifest phases are 0-indexed (typically 5 phases: 0-4).
# Our model: baseline(0-1), deterioration(1-2), intervention(2-3), resolution(3-4)
PHASE_TO_MANIFEST_IDS: dict[str, set[int]] = {
    'baseline':      {0, 1},
    'deterioration': {0, 1, 2},
    'intervention':  {0, 1, 2, 3},
    'resolution':    {0, 1, 2, 3, 4},
}


def generate_decision_nodes(
    customer_id: int,
    account_id: int,
    arc_type: str,
    phase: str,
    account_name: str = '',
) -> int:
    """
    Generate DECISION ContextNodes from arc manifest templates.

    Only creates decisions for phases up to the detected phase.
    Uses source_event_id for dedup: `wizard_a_dec_{arc_type}_{decision_id}`.

    Args:
        customer_id: The tenant ID
        account_id: The account ID
        arc_type: Canonical arc type (e.g. 'crisis_recovery')
        phase: Detected phase ('baseline', 'deterioration', 'intervention', 'resolution')
        account_name: Account name for title enrichment

    Returns:
        Number of DECISION nodes created
    """
    from models import ContextNode, HealthScore
    from extensions import db
    from utils.story_arc_loader import load_arc

    # Skip if account already has customer-uploaded DECISION nodes (11-CSV mode)
    existing_customer_decisions = (
        ContextNode.query
        .filter_by(
            customer_id=customer_id,
            account_id=account_id,
            node_type='DECISION',
        )
        .filter(ContextNode.source != 'wizard_a')
        .count()
    )
    if existing_customer_decisions > 0:
        logger.info(
            f"arc_decision_generator: skipping account {account_id} — "
            f"{existing_customer_decisions} customer DECISION nodes already exist"
        )
        return 0

    # Resolve arc type aliases (same as arc_edge_generator)
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

    # Load arc manifest — manifest files are named arc_{type}.json
    arc_manifest_id = f'arc_{resolved_type}' if not resolved_type.startswith('arc_') else resolved_type
    arc = load_arc(arc_manifest_id)
    if not arc:
        logger.debug(f"arc_decision_generator: no manifest for arc={resolved_type}")
        return 0

    decisions = arc.get('decisions', [])
    if not decisions:
        logger.debug(f"arc_decision_generator: no decisions in arc={resolved_type}")
        return 0

    # Determine which manifest phase_ids are covered
    allowed_phase_ids = PHASE_TO_MANIFEST_IDS.get(phase, {0, 1, 2, 3, 4})

    # Get the account's earliest health score date for temporal anchoring
    earliest_health = (
        db.session.query(HealthScore.measurement_month)
        .filter_by(account_id=account_id)
        .order_by(HealthScore.measurement_month)
        .first()
    )
    if earliest_health and earliest_health[0]:
        base_date = datetime(
            earliest_health[0].year,
            earliest_health[0].month,
            earliest_health[0].day,
        )
    else:
        base_date = datetime.utcnow() - timedelta(days=180)

    # Delete existing template DECISION nodes for this account (idempotent).
    # Covers both the legacy non-canonical 'wizard_a' source literal and the
    # canonical 'synthetic' now written — re-running the wizard self-heals
    # legacy rows the same way the journey builder's edges do.
    deleted = (
        ContextNode.query
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.account_id == account_id,
            ContextNode.node_type == 'DECISION',
            ContextNode.source.in_(['wizard_a', 'synthetic']),
        )
        .delete(synchronize_session='fetch')
    )
    if deleted:
        logger.debug(
            f"arc_decision_generator: cleaned {deleted} stale DECISION nodes "
            f"for account {account_id}"
        )

    created = 0
    for decision in decisions:
        decision_phase_id = decision.get('phase_id', 0)
        if decision_phase_id not in allowed_phase_ids:
            continue

        decision_id = decision.get('decision_id', f'dec_{created}')
        week = decision.get('week', 0)
        title = decision.get('title', 'Decision')

        # Determine subtype from event context
        title_lower = title.lower()
        if any(kw in title_lower for kw in ('escalat', 'p1 incident', 'declare')):
            subtype = 'escalation'
        elif any(kw in title_lower for kw in ('playbook', 'deploy', 'acceleration')):
            subtype = 'playbook'
        elif any(kw in title_lower for kw in ('executive', 'sponsor', 'cto', 'cro', 'vp')):
            subtype = 'exec_engagement'
        elif any(kw in title_lower for kw in ('renewal', 'retention', 'negotiat')):
            subtype = 'renewal_strategy'
        elif any(kw in title_lower for kw in ('expansion', 'upsell', 'growth', 'capacity')):
            subtype = 'expansion_strategy'
        elif any(kw in title_lower for kw in ('approv', 'budget', 'invest')):
            subtype = 'investment_approval'
        else:
            subtype = 'strategic_decision'

        # Temporal placement: base_date + week offset
        occurred_at = base_date + timedelta(weeks=week)

        # Build properties from manifest decision data.
        # Node-evidence-gap review (2026-08-24): the template's citations used
        # to be written under 'evidence_refs' — a key that reads as
        # corroboration. They are invented narrative ("Reference call: similar
        # customer achieved...") and manufactured corroboration defeats
        # exactly the audit a reviewer would run: it doesn't look like a gap,
        # it looks like diligence. Renamed to narrative_refs; nothing may
        # ever surface these as evidence.
        properties = {
            'arc_type': resolved_type,
            'arc_phase_id': decision_phase_id,
            'decision_id': decision_id,
            'decision_maker_role': decision.get('decision_maker_role', ''),
            'narrative_refs': decision.get('evidence_refs', []),
            'generated_by': 'wizard_a_arc_template',
        }

        # Include chosen option details if available
        options = decision.get('options', [])
        chosen_idx = decision.get('chosen_option')
        if options and chosen_idx is not None and chosen_idx < len(options):
            chosen = options[chosen_idx]
            properties['chosen_option'] = chosen.get('option', '')
            properties['chosen_risk_level'] = chosen.get('risk_level', '')

        outcome_desc = decision.get('outcome_description', '')
        if outcome_desc:
            properties['outcome_description'] = outcome_desc

        # Revenue: template decisions carry NO revenue_impact (node-evidence-
        # gap review, 2026-08-24). A DECISION holding revenue_impact is a
        # category error — an outcome has realized revenue, a decision has a
        # proposal — and the old code compounded it with a sign error
        # (positive expansion money typed 'at_risk' unconditionally) and
        # intra-arc double-counting (the same $5.2M stamped on phase-2 AND
        # phase-3 of one arc; 22 of 103 live rows repeated an amount already
        # counted in the same account). The manifest's figure is preserved as
        # proposal metadata that no aggregator sums.
        manifest_amount = decision.get('revenue_impact')
        if manifest_amount:
            properties['proposed_value'] = manifest_amount

        # Enrich title with account name for readability
        enriched_title = f"{title} — {account_name}" if account_name else title

        node = ContextNode(
            customer_id=customer_id,
            account_id=account_id,
            node_type='DECISION',
            node_subtype=subtype,
            # 'synthetic' is the canonical vocabulary for template fabrication
            # (utils/provenance.py) — the old 'wizard_a' literal was the 5th
            # non-canonical source found, and it slipped every allow-list.
            source='synthetic',
            tier=2,  # template scaffolding, same as the journey arc nodes
            title=enriched_title,
            properties=properties,
            # No confidence: 0.85 was a typed constant, not an estimate.
            confidence=None,
            source_platform='wizard_a',
            source_event_id=f'wizard_a_dec_{resolved_type}_{decision_id}_{account_id}',
            occurred_at=occurred_at,
        )
        db.session.add(node)
        created += 1

    if created:
        db.session.flush()  # Assign node_ids so edge generator can resolve them

    logger.info(
        f"arc_decision_generator: created {created} DECISION nodes "
        f"for account {account_id} arc={resolved_type} phase={phase}"
    )
    return created
