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
from utils.vertical_playbook_routing import playbook_display_names

PLAYBOOK_NAMES = playbook_display_names()

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


# ARR-tiered fully-loaded playbook cost.
#
# Captures full intervention economics (CSM + VP CS + SA + executive sponsor +
# AE + travel + platform allocation + overhead), not just CSM-hours-on-task.
# The old CSM-hours-only calculator (calculate_cost_bridge in
# playbook_cost_bridge.py) is still used for unit-economics analysis; this
# table is the authoritative *total loaded cost* used for CFO ROI math.
#
# Sources for the numbers:
#   - CSM 30hrs × $200/hr = $6K (lead time over a 30-60d intervention)
#   - VP CS 6hrs × $450/hr = $2.7K (oversight + escalation)
#   - SA 16hrs × $300/hr = $4.8K (technical workstream)
#   - Executive sponsor 4hrs × $600/hr = $2.4K (high-touch only at 10M+)
#   - AE 6hrs × $300/hr = $1.8K (deal protection on at-risk renewals)
#   - Travel/onsite $5K (capped per playbook for mid-market+)
#   - Platform/AI allocation $15K (CS Pulse + comms + data tooling)
#   - Overhead 35% of direct labor (recruiting, training, mgmt)
# Tiered down at lower ARR bands (less senior coverage, no travel, etc.)
PLAYBOOK_LOADED_COST_BY_ARR_BAND = {
    '<10K':       3_000,   # mostly automation + ticket; no CSM time
    '10K-100K':  12_000,   # email + light CSM touch
    '100K-1M':   25_000,   # CSM + manager engagement
    '1M-10M':    50_000,   # CSM + VP CS + SA (mid-market default)
    '10M+':      90_000,   # adds executive sponsor + AE + multi-stakeholder time
}

# ARR thresholds (in dollars) used to map raw ARR to a band when arr_band
# isn't passed by the caller. Mirrors features.ARR_BANDS.
_ARR_BAND_THRESHOLDS = [
    (10_000,       '<10K'),
    (100_000,      '10K-100K'),
    (1_000_000,    '100K-1M'),
    (10_000_000,   '1M-10M'),
    (float('inf'), '10M+'),
]


def _arr_to_band(arr: float) -> str:
    """Map a raw ARR value to one of the ARR bands above."""
    for upper, band in _ARR_BAND_THRESHOLDS:
        if arr < upper:
            return band
    return '10M+'


def get_full_playbook_cost(playbook_id: str, arr: float) -> float:
    """Full loaded intervention cost (CSM + VP + SA + exec + AE + travel +
    platform + overhead), tiered by the account's ARR band.

    Realistic numbers from enterprise SaaS CS economics — averages $50K for
    the typical 1M-10M defensive playbook, ranging from $3K (automation-only
    on <10K accounts) to $90K (strategic 10M+ saves with executive sponsor).

    Returns the dollar cost for a single playbook execution on an account
    of the given ARR. playbook_id is reserved for future per-playbook-type
    differentiation (defensive vs expansion); ignored for now.
    """
    band = _arr_to_band(float(arr or 0))
    return float(PLAYBOOK_LOADED_COST_BY_ARR_BAND.get(band, 50_000))


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

    # Get health: use explicit value, or point-in-time query by triggered_at
    if health_at_trigger is not None:
        health_now = health_at_trigger
    else:
        hs_query = HealthScore.query.filter(HealthScore.account_id == account_id)
        if triggered_at is not None:
            # Point-in-time: latest HS on or before triggered_at
            hs_query = hs_query.filter(
                HealthScore.measurement_month <= triggered_at.date()
            )
        latest_hs = hs_query.order_by(HealthScore.measurement_month.desc()).first()
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
            # Latest HS on or before close_date (HS.measurement_month is a Date,
            # stored as the 1st of the month; <= comparison handles mid-month closes).
            hs = (HealthScore.query
                  .filter(HealthScore.account_id == execution.account_id,
                          HealthScore.measurement_month <= close_date.date())
                  .order_by(HealthScore.measurement_month.desc())
                  .first())
            if hs and hs.health_score:
                health_at_close = float(hs.health_score)
        except Exception:
            pass  # Continue without health_at_close

    if health_at_close is not None:
        execution.health_at_close = health_at_close
        execution.health_status_at_close = _classify_health(health_at_close)
        if execution.health_at_trigger:
            execution.health_delta = health_at_close - execution.health_at_trigger

    # ── Revenue attribution (churn probability model) ──
    # Uses execution.health_at_trigger — the health SNAPSHOT taken at
    # start_execution time. This is the canonical anchor: without it we'd
    # be computing attribution against either (a) today's health, which
    # disadvantages retroactive seeding, or (b) a stale field, which can
    # silently shift as KPI ingest changes history.
    #
    # `is not None` (not truthy) — a legitimate 0.0 trigger health must
    # still allow attribution (an account that started at literal zero
    # and reached 50 is the MAXIMUM-impact rescue).
    arr = float(execution.arr_at_trigger or 0)
    if (revenue_protected is None
            and health_at_close is not None
            and execution.health_at_trigger is not None):
        churn_before = health_to_annual_churn_prob(execution.health_at_trigger)
        churn_after = health_to_annual_churn_prob(health_at_close)
        churn_reduction = max(0, churn_before - churn_after)
        revenue_protected = round(churn_reduction * arr * INTERVENTION_ATTRIBUTION, 0)
    elif revenue_protected is None:
        revenue_protected = 0

    # ── Expansion attribution (expansion probability model) ──
    if (revenue_expanded == 0
            and health_at_close is not None
            and execution.health_at_trigger is not None):
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

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Retry commit without context graph (CG write may have caused conflict)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
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
                node_type='OUTCOME', source='inferred', node_subtype='playbook_outcome',
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
                node_type='OUTCOME', source='inferred', node_subtype='playbook_outcome',
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
                node_type='OUTCOME', source='inferred', node_subtype='playbook_outcome',
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

        # ── Causal edges: ABSTAIN (WS-2 review, 2026-08-24) ──
        # This path used to write two heuristic edges on every playbook close:
        #   RESULTED_IN: the account's MOST RECENT decision node → outcome, at
        #     a typed confidence=1.0 (a recency guess wearing full confidence —
        #     the worst confidence-overloading instance found in the audit);
        #   LED_TO: the 3 most recent prior signals → outcome, at a typed 0.7.
        # Neither is a logged causal fact; both were adjudicated `inferred`
        # (cells 12/13). Per the reviewer's direction, the writer now ABSTAINS
        # — no edge at all — rather than keep accumulating typed constants
        # until WS-2 2c ships the EdgeFactory (evidence_tier stamped,
        # confidence NULL for inferred). Reinstate the linkage there, through
        # the factory, or from a real trigger-condition log — never by
        # restoring these constructors. Residue marker:
        # tests/test_playbook_close_edge_abstention.py.
        #
        # The OUTCOME node itself (real execution economics) is still written
        # above — only the fabricated causal linkage stops.

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


def _get_current_step(action_log: list):
    """Get the step_id of the first pending or in-progress step."""
    for step in action_log:
        if step.get('status') in ('pending', 'in-progress'):
            return step.get('step_id')
    return None
