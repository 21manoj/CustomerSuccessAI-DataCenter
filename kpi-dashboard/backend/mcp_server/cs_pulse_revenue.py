#!/usr/bin/env python3
"""
CS Pulse MCP — Revenue & Portfolio Tools.

7 tools moved from cs_pulse_mcp_server.py:
  - calculate_power_of_1
  - get_outcome_roi_story
  - get_playbook_economics
  - get_playbook_recommendations
  - get_portfolio_roi_summary
  - list_portfolio_customers
  - get_portfolio_cross_customer_comparison

All tools register on the shared `mcp` instance from cs_pulse_mcp_server.
"""

from cs_pulse_mcp_server import (
    mcp,
    _check_mcp_enabled,
    _require_auth,
    _require_account_auth,
    _get_flask_app,
    _validate_account_ownership,
    _get_account_arr,
    _resolve_customer_vertical,
    _get_health_functions,
    _ensure_registry,
    _backend_dir,
    ToolError,
)


# ===================================================================
# Tool: calculate_power_of_1
# ===================================================================

@mcp.tool
def calculate_power_of_1(
    customer_id: int,
    metric_id: str,
    improvement_pct: float = 1.0,
    account_arr: float = None,
) -> dict:
    """Calculate the revenue impact of a 1% improvement in a business metric (Power-of-1).

    Args:
        customer_id: The customer (tenant) ID
        metric_id: Metric to improve (e.g. NRR, GRR, product_adoption, expansion_rate, ticket_resolution_time, TTFV)
        improvement_pct: Percentage improvement (default 1.0 = 1%)
        account_arr: Optional account ARR override. If omitted, uses portfolio total.
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from power_of_1_model import calculate_power_of_1_impact

        if account_arr:
            scope = "account"
            arr_source = "explicit_account_arr"
            effective_arr = account_arr
        else:
            scope = "portfolio"
            arr_source = "portfolio_total"
            accounts = Account.query.filter(
                Account.customer_id == int(customer_id),
            ).all()
            effective_arr = sum(_get_account_arr(a) for a in accounts)
            if not effective_arr:
                effective_arr = None

        po1_vertical = _resolve_customer_vertical(customer_id)

        result = calculate_power_of_1_impact(
            metric_id=metric_id,
            improvement_pct=improvement_pct,
            account_arr=effective_arr,
            vertical=po1_vertical,
        )

        if "error" in result:
            raise ToolError(f"Power-of-1 calculation failed: {result['error']}")

        result["scope"] = scope
        result["arr_source"] = arr_source
        return result


# ===================================================================
# Tool: get_outcome_roi_story
# ===================================================================

@mcp.tool
def get_outcome_roi_story(
    customer_id: int,
    account_id: int,
    target_improvement_pct: float = 10.0,
    projection_months: int = 12,
) -> dict:
    """Generate a full ROI narrative with proof points, projections, and context graph insights.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
        target_improvement_pct: Target improvement percentage (default 10%)
        projection_months: Projection horizon in months (default 12)
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        from outcome_roi_engine import calculate_outcome_story
        from power_of_1_model import POWER_OF_1_METRICS

        account = _validate_account_ownership(customer_id, account_id)

        arr = _get_account_arr(account)

        metric_actuals = {}
        for mid, m in POWER_OF_1_METRICS.items():
            metric_actuals[mid] = {"current": m.baseline, "baseline": m.baseline}

        acct_vertical = getattr(account, 'vertical', None)

        story = calculate_outcome_story(
            metric_actuals=metric_actuals,
            target_improvement_pct=target_improvement_pct,
            account_arr=arr,
            projection_months=projection_months,
            customer_id=customer_id,
            account_ids=[account_id],
            vertical=acct_vertical,
        )

        story["scope"] = "account"
        return story


# ===================================================================
# Tool: get_playbook_economics
# ===================================================================

@mcp.tool
def get_playbook_economics(
    customer_id: int,
    account_arr: float = None,
) -> dict:
    """Get playbook cost bridge economics — investment breakdown, hours, ROI per playbook.

    Returns per-metric and per-playbook economics derived from:
      - Power of 1 JSON benchmarks (source of truth for budgets)
      - PLAYBOOK_CONFIG hours (manual vs automated breakdown)
      - CSM hourly rate from resource_rates.json

    Use this to answer: "How much do playbooks cost?", "What's the CSM investment?",
    "Show me the investment breakdown", "What's the ROI per playbook run?"

    Args:
        customer_id: The customer (tenant) ID
        account_arr: Customer ARR for scaling (optional, defaults to sum of account revenues)
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from playbook_cost_bridge import calculate_cost_bridge, bridge_to_dict

        if account_arr:
            effective_arr = float(account_arr)
        else:
            accounts = Account.query.filter(
                Account.customer_id == int(customer_id),
            ).all()
            effective_arr = float(sum(_get_account_arr(a) for a in accounts)) if accounts else 10_000_000

        result = calculate_cost_bridge(account_arr=effective_arr)
        return bridge_to_dict(result)


# ===================================================================
# Tool: get_playbook_recommendations
# ===================================================================

@mcp.tool
def get_playbook_recommendations(
    customer_id: int,
    account_id: int,
) -> dict:
    """Get recommended playbooks for an account based on health score and signals.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to get recommendations for
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _validate_account_ownership(customer_id, account_id)
        _ensure_registry()
        from agent_tool_registry import get_tool_registry

        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)

        kpi_values = _get_trailing_kpi_values(account_id)

        precalc_health, _, _ = get_precalculated_scores(account_id)
        if precalc_health is not None:
            health = precalc_health
        else:
            health, _ = calculate_kpi_health(kpi_values, customer_id)

        registry = get_tool_registry()
        result = registry.invoke(
            "playbook_recommend",
            account_id=account_id,
            customer_id=customer_id,
            health_score=round(health, 1),
            kpi_values=kpi_values,
        )

        if not result.success:
            raise ToolError(f"Playbook recommendations failed: {result.error}")

        data = result.result
        data["scope"] = "account"
        return data


# ===================================================================
# Tool: execute_playbook
# ===================================================================

@mcp.tool
def execute_playbook(
    customer_id: int,
    account_id: int,
    playbook_id: str,
    triggered_by: str = 'csm_manual',
) -> dict:
    """Start a playbook execution for an account.

    Creates a PlaybookExecutionV2 record capturing the account's health,
    ARR, and arc type at trigger time. Returns the execution_id for tracking.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to run the playbook on
        playbook_id: Playbook ID (e.g. 'PB-01', 'PB-02')
        triggered_by: Who triggered it — 'csm_manual', 'health_drop', 'signal_analyst', 'mcp_agent'
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Account, HealthScore, PlaybookExecutionV2
        from extensions import db
        import uuid
        from datetime import datetime

        account = Account.query.filter_by(
            account_id=account_id, customer_id=customer_id
        ).first()
        if not account:
            raise ToolError(f"Account {account_id} not found for customer {customer_id}")

        # Get current health
        latest_hs = (
            HealthScore.query
            .filter_by(account_id=account_id)
            .order_by(HealthScore.measurement_month.desc())
            .first()
        )
        health_now = float(latest_hs.health_score) if latest_hs and latest_hs.health_score else None
        health_status = 'critical' if health_now and health_now < 50 else (
            'at_risk' if health_now and health_now < 70 else 'healthy'
        ) if health_now else None

        arr = float(account.revenue or 0)

        # Playbook name lookup
        pb_names = {
            'PB-01': 'Deployment Acceleration', 'PB-02': 'RMA Prevention',
            'PB-03': 'GPU Optimization', 'PB-04': 'Capacity Planning',
            'PB-05': 'Health Monitoring', 'PB-06': 'Customer Engagement',
            'PB-07': 'Seasonal Planning', 'PB-08': 'Expansion Accelerator',
        }

        # Playbook hours from PLAYBOOK_CONFIG (if available)
        csm_hours = 0
        try:
            from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG
            cfg = PLAYBOOK_CONFIG.get(playbook_id, {})
            csm_hours = sum(sc.get('estimated_hours', 0) for sc in cfg.get('sub_components', []))
        except Exception:
            csm_hours = 40  # default

        execution_id = f"exec-{playbook_id}-{account_id}-{uuid.uuid4().hex[:8]}"

        execution = PlaybookExecutionV2(
            execution_id=execution_id,
            customer_id=customer_id,
            account_id=account_id,
            playbook_id=playbook_id,
            playbook_name=pb_names.get(playbook_id, playbook_id),
            triggered_by=triggered_by,
            arc_type=account.arc_type,
            status='in_progress',
            phase='stabilize',
            csm_hours_planned=csm_hours,
            csm_hourly_rate=85.0,
            total_cost=csm_hours * 85.0,
            health_at_trigger=health_now,
            health_status_at_trigger=health_status,
            arr_at_trigger=arr,
            actions_planned=len(cfg.get('sub_components', [])) if 'cfg' in dir() else 4,
        )
        db.session.add(execution)
        db.session.commit()

        return {
            'scope': 'execution',
            'execution_id': execution_id,
            'customer_id': customer_id,
            'account_id': account_id,
            'account_name': account.account_name,
            'playbook_id': playbook_id,
            'playbook_name': pb_names.get(playbook_id, playbook_id),
            'status': 'in_progress',
            'triggered_by': triggered_by,
            'health_at_trigger': health_now,
            'arr_at_trigger': arr,
            'csm_hours_planned': csm_hours,
            'estimated_cost': round(csm_hours * 85.0, 2),
        }


# ===================================================================
# Tool: close_playbook
# ===================================================================

def _health_to_annual_churn_prob(health: float) -> float:
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


def _get_full_playbook_cost(playbook_id: str, arr: float) -> float:
    """Get full intervention cost including CSM labor, platform, exec time, overhead.

    Industry benchmarks (TSIA, Gainsight Pulse 2024):
      - Crisis/recovery playbook on $5M+ account: $40K-$80K
      - Engagement/retention playbook on $3M+ account: $20K-$40K
      - Deployment acceleration: $15K-$30K

    Uses cost bridge as base, then applies ARR-scaled minimum floors.
    """
    # Base cost from cost bridge
    base_cost = 0
    try:
        from playbook_cost_bridge import calculate_cost_bridge
        bridge = calculate_cost_bridge(account_arr=arr)
        pb_econ = bridge.playbooks.get(playbook_id)
        if pb_econ:
            base_cost = pb_econ.manual_cost * 1.20  # +20% overhead
    except Exception:
        pass

    if base_cost <= 0:
        base_cost = 40 * 85 * 1.20  # 40 hrs × $85 + 20% overhead

    # ARR-scaled floor: real interventions cost ~0.5-1% of ARR at risk
    # Crisis playbooks are more expensive than engagement playbooks
    crisis_pbs = {'PB-01', 'PB-02', 'PB-04'}  # deployment, RMA, capacity
    if playbook_id in crisis_pbs:
        arr_floor = arr * 0.006  # 0.6% of ARR for crisis interventions
    else:
        arr_floor = arr * 0.004  # 0.4% of ARR for engagement interventions

    # Absolute floors by ARR tier (industry benchmarks)
    if arr >= 8_000_000:
        abs_floor = 45_000
    elif arr >= 5_000_000:
        abs_floor = 30_000
    elif arr >= 3_000_000:
        abs_floor = 18_000
    else:
        abs_floor = 10_000

    return max(base_cost, arr_floor, abs_floor)


@mcp.tool
def close_playbook(
    customer_id: int,
    execution_id: str,
    outcome: str,
    outcome_notes: str = '',
    health_at_close: float = None,
    revenue_protected: float = None,
    revenue_expanded: float = 0,
    csm_hours_actual: float = None,
) -> dict:
    """Close a playbook execution with outcome data and realistic ROI.

    ROI model:
      - Cost: Full intervention cost from playbook cost bridge (CSM hours +
        platform + overhead), not just CSM labor.
      - Revenue protected: If not provided, auto-computed from churn probability
        delta: (churn_prob_before - churn_prob_after) × ARR. This attributes
        only the risk reduction caused by the health improvement.
      - ROI: revenue_protected / full_cost as a multiple (e.g., 12.5x).

    Args:
        customer_id: The customer (tenant) ID
        execution_id: The execution_id from execute_playbook
        outcome: Result — 'resolved', 'escalated', 'timeout', 'manual_close'
        outcome_notes: Free-text notes on what happened
        health_at_close: Account health score at close time
        revenue_protected: ARR protected (if None, auto-computed from churn model)
        revenue_expanded: ARR expanded (upsell/cross-sell)
        csm_hours_actual: Actual CSM hours spent (if different from planned)
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import PlaybookExecutionV2
        from extensions import db
        from datetime import datetime

        execution = PlaybookExecutionV2.query.filter_by(
            execution_id=execution_id, customer_id=customer_id
        ).first()
        if not execution:
            raise ToolError(f"Execution {execution_id} not found for customer {customer_id}")

        if execution.status == 'completed':
            raise ToolError(f"Execution {execution_id} is already closed")

        # Update outcome fields
        execution.status = 'completed'
        execution.outcome = outcome
        execution.outcome_notes = outcome_notes
        execution.closed_at = datetime.utcnow()

        if health_at_close is not None:
            execution.health_at_close = health_at_close
            execution.health_status_at_close = (
                'critical' if health_at_close < 50 else
                'at_risk' if health_at_close < 70 else 'healthy'
            )
            if execution.health_at_trigger:
                execution.health_delta = health_at_close - execution.health_at_trigger

        # ── Revenue attribution (churn probability model) ──
        # Attribution = (churn_before - churn_after) × ARR × attribution_factor
        # attribution_factor accounts for:
        #   - Not all recovery is due to the playbook (organic regression to mean)
        #   - Industry benchmark: 40-60% of recovery is attributable to intervention
        #   (Source: TSIA CS Benchmark 2024, Gainsight Pulse)
        INTERVENTION_ATTRIBUTION = 0.50  # 50% of churn reduction attributed to playbook

        arr = float(execution.arr_at_trigger or 0)
        if revenue_protected is None and health_at_close is not None and execution.health_at_trigger:
            churn_before = _health_to_annual_churn_prob(execution.health_at_trigger)
            churn_after = _health_to_annual_churn_prob(health_at_close)
            churn_reduction = max(0, churn_before - churn_after)
            revenue_protected = round(churn_reduction * arr * INTERVENTION_ATTRIBUTION, 0)
        elif revenue_protected is None:
            revenue_protected = 0

        execution.revenue_protected = revenue_protected
        execution.revenue_expanded = revenue_expanded

        # ── Full intervention cost (cost bridge, not just CSM hours) ──
        full_cost = _get_full_playbook_cost(execution.playbook_id, arr)

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

        # ── Write OUTCOME node to context graph (Signal→Decision→Outcome) ──
        try:
            from models import ContextNode, ContextEdge
            from datetime import datetime as _dt

            # Determine revenue_impact_type
            if revenue_protected > 0 and outcome == 'resolved':
                ri_type = 'revenue_protected'
            elif revenue_expanded > 0:
                ri_type = 'expansion_closed'
            elif outcome == 'timeout':
                ri_type = 'revenue_at_risk'
            else:
                ri_type = 'intervention_outcome'

            net_impact = revenue_protected + revenue_expanded
            outcome_node = ContextNode(
                account_id=execution.account_id,
                customer_id=customer_id,
                node_type='OUTCOME',
                source='system',
                node_subtype='playbook_outcome',
                title=f'{outcome.title()}: {execution.playbook_id} — ${net_impact:,.0f} protected',
                revenue_impact=net_impact if net_impact > 0 else -(arr * 0.01),
                revenue_impact_type=ri_type,
                properties={
                    'execution_id': execution_id,
                    'playbook_id': execution.playbook_id,
                    'outcome': outcome,
                    'health_at_trigger': execution.health_at_trigger,
                    'health_at_close': health_at_close,
                    'health_delta': execution.health_delta,
                    'revenue_protected': revenue_protected,
                    'revenue_expanded': revenue_expanded,
                    'total_cost': round(full_cost, 2),
                    'roi_x': execution.realized_roi_pct,
                },
                tier=1,
                occurred_at=_dt.utcnow(),
                source_platform='playbook_execution',
                source_event_id=f'close:{execution_id}',
            )
            db.session.add(outcome_node)
            db.session.flush()

            # Link DECISION → OUTCOME (find the playbook DECISION node)
            decision_node = (
                ContextNode.query
                .filter(
                    ContextNode.account_id == execution.account_id,
                    ContextNode.customer_id == customer_id,
                    ContextNode.node_type == 'DECISION',
                    ContextNode.node_subtype.like('playbook_%'),
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
        except Exception as _cg_err:
            import logging as _log_cg
            _log_cg.getLogger(__name__).warning(f"Context graph OUTCOME write failed (non-fatal): {_cg_err}")

        db.session.commit()

        return {
            'scope': 'execution_closed',
            'execution_id': execution_id,
            'playbook_id': execution.playbook_id,
            'account_id': execution.account_id,
            'outcome': outcome,
            'health_at_trigger': execution.health_at_trigger,
            'health_at_close': health_at_close,
            'health_delta': execution.health_delta,
            'churn_prob_before': round(_health_to_annual_churn_prob(execution.health_at_trigger) * 100, 1),
            'churn_prob_after': round(_health_to_annual_churn_prob(health_at_close) * 100, 1) if health_at_close else None,
            'revenue_protected': revenue_protected,
            'revenue_expanded': revenue_expanded,
            'full_intervention_cost': round(full_cost, 2),
            'realized_roi_x': execution.realized_roi_pct,  # now expressed as multiple (e.g., 12.5x)
            'nrr_impact_pct': execution.nrr_impact_pct,
            'arr': arr,
        }


# ===================================================================
# Tool: generate_playbook_from_description
# ===================================================================

@mcp.tool
def generate_playbook_from_description(
    customer_id: int,
    description: str,
) -> dict:
    """Generate a structured playbook from a natural language description.

    Takes a plain-English description of a playbook and returns structured
    JSON with trigger conditions, actions, estimated hours, and owner roles.
    Does NOT save — returns for review. Use the /api/playbooks/library POST
    endpoint to save after reviewing.

    Example descriptions:
      "When NPS drops below 30, schedule an exec QBR within 7 days"
      "If ticket resolution time exceeds 48 hours and escalation rate > 10%, deploy a dedicated support pod"
      "When a champion departs and health drops below 60, run emergency stakeholder mapping"

    Args:
        customer_id: The customer (tenant) ID (used to load their KPI catalog)
        description: Natural language description of the playbook
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        # Load KPI catalog for this customer to inform condition generation
        kpi_names = {}
        try:
            from utils.vertical_registry import get_catalog
            catalog = get_catalog(customer_id)
            for pillar in catalog.get('pillars', []):
                for kpi in pillar.get('kpis', []):
                    kpi_names[kpi['code']] = kpi.get('name', kpi['code'])
        except Exception:
            # Fallback KPI names
            kpi_names = {
                'P1-KPI1': 'DAU Rate', 'P1-KPI3': 'Time to First Value',
                'P2-KPI1': 'Exec Sponsor Engagement',
                'P3-KPI1': 'Ticket Resolution Time', 'P3-KPI3': 'NPS',
                'P3-KPI4': 'Escalation Rate',
                'P5-KPI1': 'Net Revenue Retention', 'P5-KPI2': 'Gross Revenue Retention',
                'P5-KPI3': 'Expansion Revenue Rate',
            }

        # Pattern-match common playbook descriptions to structured output
        # This is a rule-based generator — Claude (the caller) can refine
        desc_lower = description.lower()

        # Extract trigger conditions from description
        conditions = []
        if 'nps' in desc_lower:
            threshold = _extract_number(desc_lower, 'nps', default=30)
            conditions.append({'kpi_code': 'P3-KPI3', 'kpi_name': 'NPS',
                               'operator': 'less_than', 'threshold': threshold})
        if 'ticket' in desc_lower and ('resolution' in desc_lower or 'time' in desc_lower):
            threshold = _extract_number(desc_lower, 'ticket', default=48)
            conditions.append({'kpi_code': 'P3-KPI1', 'kpi_name': 'Ticket Resolution Time',
                               'operator': 'greater_than', 'threshold': threshold})
        if 'escalation' in desc_lower:
            threshold = _extract_number(desc_lower, 'escalation', default=10)
            conditions.append({'kpi_code': 'P3-KPI4', 'kpi_name': 'Escalation Rate',
                               'operator': 'greater_than', 'threshold': threshold})
        if 'dau' in desc_lower or 'adoption' in desc_lower or 'usage' in desc_lower:
            threshold = _extract_number(desc_lower, 'dau', default=40)
            conditions.append({'kpi_code': 'P1-KPI1', 'kpi_name': 'DAU Rate',
                               'operator': 'less_than', 'threshold': threshold})
        if 'champion' in desc_lower and ('depart' in desc_lower or 'left' in desc_lower or 'loss' in desc_lower):
            conditions.append({'kpi_code': 'P2-KPI1', 'kpi_name': 'Exec Sponsor Engagement',
                               'operator': 'less_than', 'threshold': 3})
        if 'health' in desc_lower:
            threshold = _extract_number(desc_lower, 'health', default=60)
            conditions.append({'kpi_code': 'health_score', 'kpi_name': 'Overall Health Score',
                               'operator': 'less_than', 'threshold': threshold})
        if 'nrr' in desc_lower or 'retention' in desc_lower:
            threshold = _extract_number(desc_lower, 'nrr', default=95)
            conditions.append({'kpi_code': 'P5-KPI1', 'kpi_name': 'Net Revenue Retention',
                               'operator': 'less_than', 'threshold': threshold})
        if 'grr' in desc_lower:
            threshold = _extract_number(desc_lower, 'grr', default=85)
            conditions.append({'kpi_code': 'P5-KPI2', 'kpi_name': 'Gross Revenue Retention',
                               'operator': 'less_than', 'threshold': threshold})

        if not conditions:
            conditions.append({'kpi_code': 'health_score', 'kpi_name': 'Overall Health Score',
                               'operator': 'less_than', 'threshold': 60})

        # Determine trigger logic
        trigger_logic = 'AND' if ' and ' in desc_lower and len(conditions) > 1 else 'OR'

        # Extract actions from description
        actions = []
        action_keywords = {
            'qbr': ('Schedule Executive QBR', 'csm', 8),
            'review': ('Conduct Account Review', 'csm', 6),
            'stakeholder': ('Emergency Stakeholder Mapping', 'csm', 4),
            'support pod': ('Deploy Dedicated Support Pod', 'support_lead', 16),
            'escalat': ('Escalation Response Protocol', 'csm', 4),
            'onboard': ('Re-onboarding Sprint', 'csm', 12),
            'training': ('Customer Training Session', 'csm', 8),
            'roi': ('Deliver Custom ROI Report', 'csm', 6),
        }

        step = 1
        for keyword, (action_name, role, hours) in action_keywords.items():
            if keyword in desc_lower:
                actions.append({'step': step, 'description': action_name,
                                'owner_role': role, 'estimated_hours': hours})
                step += 1

        if not actions:
            # Default action set based on condition severity
            actions = [
                {'step': 1, 'description': 'Assess situation and gather context', 'owner_role': 'csm', 'estimated_hours': 4},
                {'step': 2, 'description': 'Develop intervention plan', 'owner_role': 'csm', 'estimated_hours': 4},
                {'step': 3, 'description': 'Execute intervention', 'owner_role': 'csm', 'estimated_hours': 8},
                {'step': 4, 'description': 'Follow-up and measure impact', 'owner_role': 'csm', 'estimated_hours': 4},
            ]

        total_hours = sum(a['estimated_hours'] for a in actions)

        # Generate playbook name from description
        name = description[:80].strip()
        if not name[0].isupper():
            name = name.capitalize()

        return {
            'scope': 'playbook_draft',
            'status': 'draft',
            'message': 'Review this playbook and save via POST /api/playbooks/library',
            'playbook': {
                'name': name,
                'description': description,
                'trigger_conditions': conditions,
                'trigger_logic': trigger_logic,
                'actions': actions,
                'auto_trigger_enabled': False,
                'cooldown_hours': 168,
                'estimated_total_hours': total_hours,
                'estimated_cost_at_85_per_hour': round(total_hours * 85, 2),
            },
            'available_kpis': kpi_names,
        }


def _extract_number(text: str, keyword: str, default: float = 50) -> float:
    """Extract a number near a keyword in text."""
    import re
    # Find patterns like "NPS drops below 30" or "exceeds 48 hours"
    patterns = [
        rf'{keyword}\D*?(\d+\.?\d*)',
        rf'(\d+\.?\d*)\D*?{keyword}',
        rf'below\s+(\d+\.?\d*)',
        rf'above\s+(\d+\.?\d*)',
        rf'exceeds?\s+(\d+\.?\d*)',
        rf'under\s+(\d+\.?\d*)',
        rf'over\s+(\d+\.?\d*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return default


# ===================================================================
# Tool: get_portfolio_roi_summary
# ===================================================================

@mcp.tool
def get_portfolio_roi_summary(customer_id: int) -> dict:
    """Get the complete ROI story for a customer portfolio — historical proof (what we delivered) + forward projection (what we will deliver) + bridging narrative + trajectory assessment. Covers all accounts.

    Args:
        customer_id: The customer (tenant) ID
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from outcome_roi_engine import calculate_outcome_story
        from outcome_roi_api import _extract_historical_actuals, _extract_accounts_at_risk

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        if not accounts:
            raise ToolError(f"No accounts found for customer {customer_id}")

        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None
        account_ids = [a.account_id for a in accounts]

        metric_actuals, data_source = _extract_historical_actuals(accounts, 6)
        accounts_at_risk = _extract_accounts_at_risk(accounts, customer_id=customer_id)

        portfolio_vertical = getattr(accounts[0], 'vertical', None) if accounts else None

        story = calculate_outcome_story(
            metric_actuals=metric_actuals,
            target_improvement_pct=1.0,
            account_arr=total_arr,
            projection_months=6,
            accounts_at_risk=accounts_at_risk,
            customer_id=customer_id,
            account_ids=account_ids,
            vertical=portfolio_vertical,
        )

        return {
            "scope": "portfolio",
            "customer_id": customer_id,
            "total_arr": total_arr,
            "arr_basis": "portfolio_total",
            "arr_basis_value": total_arr,
            "account_count": len(accounts),
            "data_source": data_source,
            "story": story,
        }


# ===================================================================
# Tool: list_portfolio_customers
# ===================================================================

@mcp.tool
def list_portfolio_customers(portfolio_id: int) -> dict:
    """List all customers in a PE portfolio with health and ARR summary.

    NOTE: This tool uses portfolio_id (not customer_id). A portfolio is a PE fund or
    holding company that owns multiple customers. Each customer has its own accounts.

    Args:
        portfolio_id: The portfolio (PE fund / holding company) ID
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Portfolio, PortfolioMembership, Customer, Account
        import utils.health_thresholds as ht

        portfolio = Portfolio.query.filter_by(
            portfolio_id=portfolio_id, enabled=True,
        ).first()
        if not portfolio:
            raise ToolError(f"Portfolio {portfolio_id} not found or disabled")

        memberships = PortfolioMembership.query.filter_by(
            portfolio_id=portfolio_id,
        ).all()

        if not memberships:
            return {
                "scope": "portfolio",
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio.portfolio_name,
                "customers": [],
                "summary": {"total_customers": 0, "total_arr": 0, "avg_health": 0},
            }

        customer_summaries = []
        for mem in memberships:
            customer = Customer.query.filter_by(
                customer_id=mem.customer_id,
            ).first()
            if not customer:
                continue

            mem_vertical = getattr(customer, 'vertical', None) or mem.vertical or 'dc2_s'
            calc_health, get_trailing, get_precalc = _get_health_functions(mem_vertical)

            accounts = Account.query.filter(
                Account.customer_id == mem.customer_id,
            ).all()

            total_arr = sum(_get_account_arr(a) for a in accounts)
            health_scores = []
            at_risk_count = 0

            for acct in accounts:
                ph, ps, _ = get_precalc(acct.account_id)
                if ph is not None:
                    health_scores.append(ph)
                    if ps in ('at_risk', 'critical'):
                        at_risk_count += 1
                else:
                    kv = get_trailing(acct.account_id)
                    h, _ = calc_health(kv, mem.customer_id)
                    health_scores.append(h)
                    if ht.classify(h) in ('at_risk', 'critical'):
                        at_risk_count += 1

            avg_health = round(
                sum(health_scores) / len(health_scores), 1
            ) if health_scores else 0

            customer_summaries.append({
                "customer_id": mem.customer_id,
                "customer_name": getattr(customer, 'customer_name', None) or getattr(customer, 'company_name', 'Unknown'),
                "created_at": customer.created_at.isoformat() if customer.created_at else None,
                "vertical": mem_vertical,
                "status": mem.status,
                "total_accounts": len(accounts),
                "total_arr": round(total_arr, 2),
                "avg_health_score": avg_health,
                "at_risk_accounts": at_risk_count,
                "synergies_realized": mem.synergies_realized,
                "synergy_value": float(mem.synergy_value or 0),
            })

        customer_summaries.sort(key=lambda x: x["avg_health_score"])

        total_arr = sum(c["total_arr"] for c in customer_summaries)
        total_accounts = sum(c["total_accounts"] for c in customer_summaries)
        avg_health = round(
            sum(c["avg_health_score"] * c["total_accounts"] for c in customer_summaries)
            / total_accounts, 1
        ) if total_accounts else 0

        return {
            "scope": "portfolio",
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "total_aum": float(portfolio.total_aum) if portfolio.total_aum else None,
            "customers": customer_summaries,
            "summary": {
                "total_customers": len(customer_summaries),
                "total_accounts": total_accounts,
                "total_arr": round(total_arr, 2),
                "avg_health_score": avg_health,
                "total_at_risk": sum(c["at_risk_accounts"] for c in customer_summaries),
            },
        }


# ===================================================================
# Tool: get_portfolio_cross_customer_comparison
# ===================================================================

@mcp.tool
def get_portfolio_cross_customer_comparison(portfolio_id: int) -> dict:
    """Compare all customers in a portfolio side-by-side: health, ARR, risk, expansion. CEO-level view.

    NOTE: Uses portfolio_id (not customer_id). Includes context graph revenue intelligence
    when enabled. Use for board-level cross-company benchmarking.

    Args:
        portfolio_id: The portfolio (PE fund / holding company) ID
    """
    _check_mcp_enabled()
    app = _get_flask_app()

    with app.app_context():
        from models import Portfolio, PortfolioMembership, Customer, Account
        import utils.health_thresholds as ht

        portfolio = Portfolio.query.filter_by(
            portfolio_id=portfolio_id, enabled=True,
        ).first()
        if not portfolio:
            raise ToolError(f"Portfolio {portfolio_id} not found or disabled")

        memberships = PortfolioMembership.query.filter_by(
            portfolio_id=portfolio_id,
        ).all()

        comparisons = []
        for mem in memberships:
            customer = Customer.query.filter_by(
                customer_id=mem.customer_id,
            ).first()
            if not customer:
                continue

            mem_vertical = getattr(customer, 'vertical', None) or mem.vertical or 'dc2_s'
            calc_health, get_trailing, get_precalc = _get_health_functions(mem_vertical)

            accounts = Account.query.filter(
                Account.customer_id == mem.customer_id,
            ).all()

            total_arr = sum(_get_account_arr(a) for a in accounts)
            pillar_totals = {}
            health_scores = []
            statuses = {'healthy': 0, 'at_risk': 0, 'critical': 0}

            for acct in accounts:
                ph, ps, pp = get_precalc(acct.account_id)
                if ph is not None:
                    health_scores.append(ph)
                    statuses[ps] = statuses.get(ps, 0) + 1
                    if pp:
                        for k, v in pp.items():
                            pillar_totals.setdefault(k, []).append(v)
                else:
                    kv = get_trailing(acct.account_id)
                    h, pillars = calc_health(kv, mem.customer_id)
                    health_scores.append(h)
                    cls = ht.classify(h)
                    statuses[cls] = statuses.get(cls, 0) + 1
                    for k, v in pillars.items():
                        pillar_totals.setdefault(k, []).append(v)

            avg_health = round(
                sum(health_scores) / len(health_scores), 1
            ) if health_scores else 0

            avg_pillars = {
                k: round(sum(v) / len(v), 1) for k, v in pillar_totals.items()
            } if pillar_totals else {}

            weakest_pillar = min(avg_pillars, key=avg_pillars.get) if avg_pillars else None

            # Context graph revenue (if enabled)
            revenue_data = None
            try:
                from feature_toggles import is_context_graph_enabled
                if is_context_graph_enabled(mem.customer_id):
                    from utils.context_graph import get_revenue_at_risk as _gar
                    total_rev = {'at_risk': 0, 'protected': 0, 'expansion': 0, 'net_impact': 0}
                    for acct in accounts:
                        rev = _gar(acct.account_id)
                        if rev.get('node_count', 0) > 0:
                            for k in total_rev:
                                total_rev[k] += rev.get(k, 0)
                    revenue_data = {k: round(v, 2) for k, v in total_rev.items()}
            except Exception:
                pass

            comparisons.append({
                "customer_id": mem.customer_id,
                "customer_name": getattr(customer, 'customer_name', None) or getattr(customer, 'company_name', 'Unknown'),
                "total_arr": round(total_arr, 2),
                "avg_health_score": avg_health,
                "account_distribution": statuses,
                "total_accounts": len(accounts),
                "avg_pillar_scores": avg_pillars,
                "weakest_pillar": weakest_pillar,
                "revenue_intelligence": revenue_data,
            })

        comparisons.sort(key=lambda x: x["avg_health_score"])

        return {
            "scope": "portfolio",
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "comparisons": comparisons,
        }


# ===================================================================
# Tool: get_nrr_forecast
# ===================================================================

@mcp.tool
def get_nrr_forecast(customer_id: int, months: int = 3) -> dict:
    """Get portfolio NRR forecast based on Wizard B pattern-to-NRR correlations.

    Shows current projected NRR (revenue-weighted across all accounts by arc
    pattern), plus a what-if simulation: "If playbooks executed on at-risk
    accounts, NRR improves from X% to Y%, protecting $Z ARR."

    Enhanced with T+30/60/90 trajectory, renewal risk overlay, and
    per-intervention playbook cost/ROI.

    Requires Wizard B to have run with NRR intelligence enabled.
    Falls back to a live calculation if no cached forecast exists.

    Args:
        customer_id: The customer (tenant) ID
        months: Forecast horizon in months (default 3, max 12)
    """
    _check_mcp_enabled()
    app = _get_flask_app()
    months = min(months, 12)

    with app.app_context():
        from models import WizardLearning

        # Try cached forecast from most recent Wizard B run
        # Only use cache if it has the new trajectory field
        learning = (
            WizardLearning.query
            .filter_by(customer_id=customer_id, is_active=True)
            .order_by(WizardLearning.created_at.desc())
            .first()
        )

        if learning and learning.learnings:
            cached = learning.learnings.get('portfolio_nrr_forecast')
            if cached and cached.get('trajectory'):
                cached['source'] = 'wizard_b_cached'
                cached['wizard_learning_version'] = learning.version
                return cached

        # No cached forecast (or missing trajectory) — run live
        import sys as _sys
        from pathlib import Path
        _wb_dir = str(Path(__file__).parent.parent / 'verticals' / '_template' / 'journey' / 'wizard_b')
        if _wb_dir not in _sys.path:
            _sys.path.insert(0, _wb_dir)

        from wizard_b_pattern_analyzer import PatternAnalyzer

        try:
            analyzer = PatternAnalyzer.from_database(customer_id)
        except ValueError:
            raise ToolError(
                f"No journey data for customer {customer_id}. "
                "Run Wizard A (process-data) then Wizard B first."
            )

        analyzer.analyze_patterns()

        if analyzer.portfolio_nrr_forecast:
            result = analyzer.portfolio_nrr_forecast
            result['source'] = 'live_calculation'
            return result

        raise ToolError(
            f"NRR forecast unavailable for customer {customer_id}. "
            "Ensure accounts have ARR data and context graph outcomes."
        )
