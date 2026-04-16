"""
Playbook Lifecycle — shared V2 execution logic for REST + MCP paths.

Provides start_execution(), close_execution(), and helpers used by both
the DC2S REST endpoints and the MCP execute_playbook/close_playbook tools.
All functions assume the caller is already in a Flask app context.
"""

import logging
import uuid
from datetime import datetime

from extensions import db
from models import Account, HealthScore, PlaybookExecutionV2, ContextNode, ContextEdge

logger = logging.getLogger(__name__)

# ── Playbook name lookup (shared across all callers) ──
PLAYBOOK_NAMES = {
    'PB-01': 'Deployment Acceleration', 'PB-02': 'RMA Prevention',
    'PB-03': 'GPU Optimization', 'PB-04': 'Capacity Planning',
    'PB-05': 'Health Monitoring', 'PB-06': 'Customer Engagement',
    'PB-07': 'Seasonal Planning', 'PB-08': 'Expansion Accelerator',
}

# Industry benchmark: 40-60% of churn reduction attributable to intervention
# (Source: TSIA CS Benchmark 2024, Gainsight Pulse)
INTERVENTION_ATTRIBUTION = 0.50


def health_to_annual_churn_prob(health: float) -> float:
    """Map health score to annualized churn probability.

    Based on industry benchmarks (TSIA, KeyBanc SaaS):
      - Critical (<50): 35-45% annual churn
      - At-risk (50-69): 15-25% annual churn
      - Healthy (>=70): 3-8% annual churn
    Uses linear interpolation within each band.
    """
    if health is None:
        return 0.20  # unknown → assume 20%
    if health < 30:
        return 0.45
    if health < 50:
        return 0.45 - (health - 30) / 20 * 0.10   # 45% → 35%
    if health < 70:
        return 0.25 - (health - 50) / 20 * 0.10   # 25% → 15%
    if health < 85:
        return 0.08 - (health - 70) / 15 * 0.03   # 8% → 5%
    return 0.03                                     # >85: 3%


def health_to_annual_expansion_prob(health: float) -> float:
    """Map health score to annualized expansion probability.

    Based on industry benchmarks (KeyBanc SaaS Survey 2024, Gainsight Pulse):
      - Critical (<50):  0-2% expansion (firefighting, no bandwidth for growth)
      - At-risk (50-69):  5-10% expansion (stabilizing, limited upsell)
      - Healthy (70-84): 15-25% expansion (engaged, open to growth conversations)
      - Champion (>=85): 25-35% expansion (advocates, driving adoption internally)
    Uses linear interpolation within each band.
    """
    if health is None:
        return 0.05  # unknown → assume 5%
    if health < 30:
        return 0.0
    if health < 50:
        return 0.0 + (health - 30) / 20 * 0.02       # 0% → 2%
    if health < 70:
        return 0.05 + (health - 50) / 20 * 0.05       # 5% → 10%
    if health < 85:
        return 0.15 + (health - 70) / 15 * 0.10       # 15% → 25%
    return 0.25 + min((health - 85) / 15 * 0.10, 0.10)  # 25% → 35% (capped)


# Expansion attribution factor: what % of expansion is attributable to CS intervention
# Lower than churn attribution (0.50) because expansion is also driven by product/sales
EXPANSION_ATTRIBUTION = 0.30


def get_full_playbook_cost(playbook_id: str, arr: float) -> float:
    """Get full intervention cost from cost bridge (CSM labor + platform + overhead).

    Uses the same cost bridge as get_playbook_economics for consistency.
    Adds 20% overhead for exec time, coordination, and context-switching.
    """
    try:
        from playbook_cost_bridge import calculate_cost_bridge
        bridge = calculate_cost_bridge(account_arr=arr)
        pb_econ = bridge.playbooks.get(playbook_id)
        if pb_econ:
            return pb_econ.manual_cost * 1.20  # +20% overhead
    except Exception:
        pass
    # Fallback: 40 hrs × CSM rate + 20% overhead
    return 40 * 95 * 1.20


def _classify_health(score):
    """Classify health score into status string."""
    if score is None:
        return None
    if score < 50:
        return 'critical'
    if score < 70:
        return 'at_risk'
    return 'healthy'


def _get_playbook_hours(playbook_id: str) -> tuple:
    """Get CSM hours and sub_components from PLAYBOOK_CONFIG.

    Returns (csm_hours, sub_components_list).
    """
    try:
        from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG
        cfg = PLAYBOOK_CONFIG.get(playbook_id, {})
        sub_components = cfg.get('sub_components', [])
        csm_hours = sum(sc.get('estimated_hours', 0) for sc in sub_components)
        return csm_hours, sub_components
    except Exception:
        return 40, []  # default


def start_execution(
    customer_id: int,
    account_id: int,
    playbook_id: str,
    triggered_by: str = 'csm_manual',
    triggered_at: datetime = None,
    health_at_trigger: float = None,
) -> PlaybookExecutionV2:
    """Create a PlaybookExecutionV2 record with health/ARR snapshot.

    Args:
        triggered_at: Optional explicit timestamp. If None, uses server default (now).
                      Use this for time-aware playbook creation from historical signals.
        health_at_trigger: Optional explicit health score at trigger time.
                           If None, queries the latest HealthScore from DB.

    Returns the persisted V2 record (already committed to DB).
    Raises ValueError if account not found.
    """
    account = Account.query.filter_by(
        account_id=account_id, customer_id=customer_id
    ).first()
    if not account:
        raise ValueError(f"Account {account_id} not found for customer {customer_id}")

    # Get health: use explicit value, or query latest from DB
    if health_at_trigger is not None:
        health_now = health_at_trigger
    else:
        latest_hs = (
            HealthScore.query
            .filter_by(account_id=account_id)
            .order_by(HealthScore.measurement_month.desc())
            .first()
        )
        health_now = float(latest_hs.health_score) if latest_hs and latest_hs.health_score else None
    health_status = _classify_health(health_now)

    arr = float(account.revenue or 0)
    csm_hours, sub_components = _get_playbook_hours(playbook_id)

    # Build action_log from sub_components (maps old step model → V2 action_log)
    action_log = []
    for sc in sub_components:
        action_log.append({
            'step_id': sc.get('id', sc.get('name', '')),
            'name': sc.get('name', ''),
            'description': sc.get('description', ''),
            'estimated_hours': sc.get('estimated_hours', 0),
            'actual_hours': None,
            'status': 'pending',
            'notes': '',
            'started_at': None,
            'completed_at': None,
        })

    execution_id = f"exec-{playbook_id}-{account_id}-{uuid.uuid4().hex[:8]}"

    execution = PlaybookExecutionV2(
        execution_id=execution_id,
        customer_id=customer_id,
        account_id=account_id,
        playbook_id=playbook_id,
        playbook_name=PLAYBOOK_NAMES.get(playbook_id, playbook_id),
        triggered_by=triggered_by,
        arc_type=getattr(account, 'arc_type', None),
        status='in_progress',
        phase='stabilize',
        csm_hours_planned=csm_hours,
        csm_hourly_rate=85.0,
        total_cost=csm_hours * 85.0,
        health_at_trigger=health_now,
        health_status_at_trigger=health_status,
        arr_at_trigger=arr,
        actions_planned=len(action_log),
        actions_completed=0,
        action_log=action_log if action_log else None,
    )
    # Time-aware: set explicit triggered_at if provided (overrides server_default)
    if triggered_at is not None:
        execution.triggered_at = triggered_at
    db.session.add(execution)
    db.session.commit()

    return execution


def close_execution(
    customer_id: int,
    execution_id: str,
    outcome: str,
    outcome_notes: str = '',
    health_at_close: float = None,
    revenue_protected: float = None,
    revenue_expanded: float = 0,
    csm_hours_actual: float = None,
    closed_at: datetime = None,
) -> PlaybookExecutionV2:
    """Close a PlaybookExecutionV2 with outcome data, ROI, and context graph OUTCOME node.

    Args:
        closed_at: Optional explicit close timestamp. If None, uses now.
                   Use for time-aware closure of historical playbooks.

    Returns the updated V2 record (already committed to DB).
    Raises ValueError if execution not found or already closed.
    """
    execution = PlaybookExecutionV2.query.filter_by(
        execution_id=execution_id, customer_id=customer_id
    ).first()
    if not execution:
        raise ValueError(f"Execution {execution_id} not found for customer {customer_id}")
    if execution.status == 'completed':
        raise ValueError(f"Execution {execution_id} is already closed")

    # Update outcome fields
    execution.status = 'completed'
    execution.outcome = outcome
    execution.outcome_notes = outcome_notes
    execution.closed_at = closed_at or datetime.utcnow()

    # ── Auto-lookup health_at_close from HealthScore if not provided ──
    if health_at_close is None:
        try:
            close_date = execution.closed_at or datetime.utcnow()
            close_month = close_date.strftime('%Y-%m')
            hs = HealthScore.query.filter_by(
                account_id=execution.account_id,
                measurement_month=close_month,
            ).first()
            if hs:
                health_at_close = float(hs.health_score)
            else:
                # Fallback: most recent health score before close date
                hs = (HealthScore.query
                      .filter(HealthScore.account_id == execution.account_id,
                              HealthScore.measurement_month <= close_month)
                      .order_by(HealthScore.measurement_month.desc())
                      .first())
                if hs:
                    health_at_close = float(hs.health_score)
        except Exception:
            pass  # Continue without health_at_close

    if health_at_close is not None:
        execution.health_at_close = health_at_close
        execution.health_status_at_close = _classify_health(health_at_close)
        if execution.health_at_trigger:
            execution.health_delta = health_at_close - execution.health_at_trigger

    # ── Revenue attribution (churn probability model) ──
    arr = float(execution.arr_at_trigger or 0)
    if revenue_protected is None and health_at_close is not None and execution.health_at_trigger:
        churn_before = health_to_annual_churn_prob(execution.health_at_trigger)
        churn_after = health_to_annual_churn_prob(health_at_close)
        churn_reduction = max(0, churn_before - churn_after)
        revenue_protected = round(churn_reduction * arr * INTERVENTION_ATTRIBUTION, 0)
    elif revenue_protected is None:
        revenue_protected = 0

    # ── Expansion attribution (expansion probability model) ──
    if revenue_expanded == 0 and health_at_close is not None and execution.health_at_trigger:
        exp_before = health_to_annual_expansion_prob(execution.health_at_trigger)
        exp_after = health_to_annual_expansion_prob(health_at_close)
        exp_increase = max(0, exp_after - exp_before)
        if exp_increase > 0:
            revenue_expanded = round(exp_increase * arr * EXPANSION_ATTRIBUTION, 0)

    execution.revenue_protected = revenue_protected
    execution.revenue_expanded = revenue_expanded

    # ── Full intervention cost (cost bridge, not just CSM hours) ──
    full_cost = get_full_playbook_cost(execution.playbook_id, arr)

    if csm_hours_actual is not None:
        execution.csm_hours_actual = csm_hours_actual
    else:
        execution.csm_hours_actual = execution.csm_hours_planned

    execution.total_cost = round(full_cost, 2)
    total_value = revenue_protected + revenue_expanded
    execution.realized_roi_pct = round(total_value / full_cost, 1) if full_cost > 0 else 0

    if arr > 0:
        execution.nrr_impact_pct = round(
            (revenue_protected + revenue_expanded - (execution.revenue_lost or 0))
            / arr * 100, 2
        )

    # ── Write OUTCOME node to context graph ──
    _write_context_graph_outcome(execution, customer_id, outcome, revenue_protected, revenue_expanded, arr, full_cost,
                                 occurred_at=execution.closed_at)

    db.session.commit()
    return execution


def _write_context_graph_outcome(execution, customer_id, outcome, revenue_protected, revenue_expanded, arr, full_cost,
                                  occurred_at=None):
    """Write OUTCOME node and DECISION→OUTCOME edge to context graph.

    Args:
        occurred_at: Optional timestamp for the OUTCOME node. If None, uses utcnow().
                     Time-aware closures pass execution.closed_at for timeline coherence.
    """
    try:
        # ── Delete old CG nodes for this execution (prevents duplicates on re-close) ──
        eid = execution.execution_id
        old_nodes = ContextNode.query.filter(
            ContextNode.customer_id == customer_id,
            ContextNode.node_subtype == 'playbook_outcome',
            ContextNode.source_event_id.like(f'close:{eid}%'),
        ).all()
        for old in old_nodes:
            ContextEdge.query.filter(
                ContextEdge.customer_id == customer_id,
                db.or_(ContextEdge.from_node_id == old.node_id, ContextEdge.to_node_id == old.node_id),
            ).delete()
            db.session.delete(old)
        if old_nodes:
            db.session.flush()

        common_props = {
            'execution_id': execution.execution_id,
            'playbook_id': execution.playbook_id,
            'outcome': outcome,
            'health_at_trigger': execution.health_at_trigger,
            'health_at_close': execution.health_at_close,
            'health_delta': execution.health_delta,
            'total_cost': round(full_cost, 2),
            'roi_x': execution.realized_roi_pct,
        }
        ts = occurred_at or datetime.utcnow()

        # ── Create separate OUTCOME nodes for protected and expanded ──
        # This ensures the CG page shows correct buckets per account.
        outcome_node = None  # Primary node for edge linking

        if revenue_protected > 0:
            node = ContextNode(
                account_id=execution.account_id, customer_id=customer_id,
                node_type='OUTCOME', source='system', node_subtype='playbook_outcome',
                title=f'{outcome.title()}: {execution.playbook_id} — ${revenue_protected:,.0f} protected',
                revenue_impact=revenue_protected,
                revenue_impact_type='revenue_protected',
                properties={**common_props, 'revenue_protected': revenue_protected},
                tier=1, occurred_at=ts,
                source_platform='playbook_execution',
                source_event_id=f'close:{execution.execution_id}:protected',
            )
            db.session.add(node)
            db.session.flush()
            outcome_node = node

        if revenue_expanded > 0:
            node = ContextNode(
                account_id=execution.account_id, customer_id=customer_id,
                node_type='OUTCOME', source='system', node_subtype='playbook_outcome',
                title=f'{outcome.title()}: {execution.playbook_id} — ${revenue_expanded:,.0f} expansion',
                revenue_impact=revenue_expanded,
                revenue_impact_type='expansion_closed',
                properties={**common_props, 'revenue_expanded': revenue_expanded},
                tier=1, occurred_at=ts,
                source_platform='playbook_execution',
                source_event_id=f'close:{execution.execution_id}:expanded',
            )
            db.session.add(node)
            db.session.flush()
            if not outcome_node:
                outcome_node = node

        if not outcome_node:
            # No revenue — still create a node for tracking
            ri_type = 'revenue_at_risk' if outcome == 'timeout' else 'intervention_outcome'
            outcome_node = ContextNode(
                account_id=execution.account_id, customer_id=customer_id,
                node_type='OUTCOME', source='system', node_subtype='playbook_outcome',
                title=f'{outcome.title()}: {execution.playbook_id}',
                revenue_impact=0,
                revenue_impact_type=ri_type,
                properties=common_props,
                tier=1, occurred_at=ts,
                source_platform='playbook_execution',
                source_event_id=f'close:{execution.execution_id}',
            )
            db.session.add(outcome_node)
            db.session.flush()

        # Link DECISION → OUTCOME (most recent DECISION node for this account)
        decision_node = (
            ContextNode.query
            .filter(
                ContextNode.account_id == execution.account_id,
                ContextNode.customer_id == customer_id,
                ContextNode.node_type == 'DECISION',
            )
            .order_by(ContextNode.occurred_at.desc())
            .first()
        )
        if decision_node:
            db.session.add(ContextEdge(
                customer_id=customer_id,
                from_node_id=decision_node.node_id,
                to_node_id=outcome_node.node_id,
                edge_type='RESULTED_IN',
                confidence=1.0,
                source_platform='playbook_execution',
                properties={'label': f'{execution.playbook_id} → {outcome}'},
            ))

        # ── Link recent SIGNAL nodes → OUTCOME for causal traversal ──
        # Enables "Why did this happen?" queries via get_causal_chain.
        # Connect up to 3 most recent signals for this account.
        recent_signals = (
            ContextNode.query
            .filter(
                ContextNode.account_id == execution.account_id,
                ContextNode.customer_id == customer_id,
                ContextNode.node_type == 'SIGNAL',
            )
            .order_by(ContextNode.occurred_at.desc())
            .limit(3)
            .all()
        )
        for sig in recent_signals:
            db.session.add(ContextEdge(
                customer_id=customer_id,
                from_node_id=sig.node_id,
                to_node_id=outcome_node.node_id,
                edge_type='LED_TO',
                confidence=0.7,
                source_platform='playbook_execution',
                properties={
                    'label': f'{sig.node_subtype or "signal"} contributed to {outcome}',
                    'inferred_by': 'playbook_close_linker',
                },
            ))

    except Exception as cg_err:
        logger.warning(f"Context graph OUTCOME write failed (non-fatal): {cg_err}")


def build_frontend_execution_dict(v2: PlaybookExecutionV2, account_name: str = None) -> dict:
    """Map PlaybookExecutionV2 fields to the response shape DCPlaybooks.tsx expects.

    Handles status format mapping (V2 uses underscores, frontend uses hyphens)
    and reconstructs the steps/progress fields from V2's action_log.
    """
    action_log = v2.action_log or []
    completed_steps = sum(1 for a in action_log if a.get('status') == 'completed')
    total_steps = v2.actions_planned or len(action_log)

    # Resolve account_name if not provided
    if account_name is None:
        try:
            acct = Account.query.filter_by(account_id=v2.account_id).first()
            account_name = acct.account_name if acct else f"Account {v2.account_id}"
        except Exception:
            account_name = f"Account {v2.account_id}"

    return {
        'execution_id': v2.execution_id,
        'playbook_id': v2.playbook_id,
        'playbook_name': v2.playbook_name,
        'account_id': v2.account_id,
        'account_name': account_name,
        'status': (v2.status or 'in_progress').replace('_', '-'),
        'current_step': _get_current_step(action_log),
        'started_at': v2.triggered_at.isoformat() if v2.triggered_at else None,
        'completed_at': v2.closed_at.isoformat() if v2.closed_at else None,
        'steps': action_log,
        'steps_completed': completed_steps,
        'total_steps': total_steps,
        'total_estimated_hours': v2.csm_hours_planned or 0,
        'total_actual_hours': v2.csm_hours_actual or 0,
        'progress': round(completed_steps / total_steps * 100) if total_steps else 0,
        'phase': v2.phase,
        'triggered_by': v2.triggered_by,
        # V2-specific fields (available for enhanced UIs)
        'health_at_trigger': v2.health_at_trigger,
        'health_at_close': v2.health_at_close,
        'health_delta': v2.health_delta,
        'revenue_protected': v2.revenue_protected,
        'revenue_expanded': v2.revenue_expanded,
        'realized_roi_pct': v2.realized_roi_pct,
        'outcome': v2.outcome,
        'outcome_notes': v2.outcome_notes,
    }


def _get_current_step(action_log: list) -> str | None:
    """Get the step_id of the first pending or in-progress step."""
    for step in action_log:
        if step.get('status') in ('pending', 'in-progress'):
            return step.get('step_id')
    return None
