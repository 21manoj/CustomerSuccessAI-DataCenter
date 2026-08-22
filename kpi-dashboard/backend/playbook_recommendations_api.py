"""
Playbook Recommendations API

Analyzes which accounts need which playbooks based on their current KPI data and metrics.

Vertical-aware: For DC2S customers, evaluates PB-01 through PB-06 from
verticals/dc2_s/vertical_config.py using actual KPI values against canonical
trigger conditions. For non-DC2S customers, falls back to generic evaluators.
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from models import db, Account, KPI, KPITimeSeries
from datetime import datetime, timedelta
from sqlalchemy import func
import json
import logging
import utils.health_thresholds as ht

logger = logging.getLogger(__name__)

playbook_recommendations_api = Blueprint('playbook_recommendations_api', __name__)


# ── DC2S Vertical-Specific Playbook Evaluation ──────────────────────────


def _get_playbook_historical_success(playbook_id, customer_id):
    """Get historical success rate for a playbook."""
    try:
        from models import PlaybookExecutionV2
        execs = PlaybookExecutionV2.query.filter_by(
            playbook_id=playbook_id, customer_id=customer_id
        ).all()
        if not execs:
            return None
        resolved = sum(1 for e in execs if e.outcome == 'resolved')
        return {
            'total_runs': len(execs),
            'resolved': resolved,
            'success_rate_pct': round(resolved / len(execs) * 100, 1),
        }
    except Exception:
        return None


# Verticals that use the KPI-threshold config-driven playbook evaluator
# (verticals/{v}/vertical_config.py PLAYBOOK_CONFIG). Other verticals
# (saas_premium, healthcare_provider, …) keep the generic SaaS evaluators below —
# do NOT auto-detect by presence of a PLAYBOOK_CONFIG, since saas_premium has one
# but is intentionally routed to the generic evaluators.
_CONFIG_PLAYBOOK_VERTICALS = {'dc2_s', 'datacenter_v1'}


def _evaluate_dc2s_playbooks(kpi_values, health_score=None, pillar_scores=None,
                             customer_id=None, vertical='dc2_s'):
    """Evaluate config-driven playbooks for a vertical (dc2_s: PB-01..06;
    datacenter_v1: PB-01/03/04/05/06 + PB-07..13).

    Uses OR logic for most playbooks: if ANY trigger condition is met, the
    playbook is recommended. PB-04 (Capacity Planning) uses AND logic because
    expansion requires all three conditions (capacity >80%, growth >10%,
    expansion probability >70%).

    For healthy accounts (health >= 70), adds expansion-readiness
    recommendations (PB-04, PB-06) so they don't get 0 results.

    Args:
        kpi_values: Dict of KPI code → current value (e.g., {"P1-KPI1": 25.0})
        health_score: Account-level health score (0-100) for PB-05
        pillar_scores: Optional dict of pillar code → score (e.g., {"P1": 45.0})
        customer_id: Optional customer/tenant ID for historical success enrichment

    Returns:
        List of recommendation dicts sorted by urgency (highest first)
    """
    import importlib
    try:
        _vc = importlib.import_module(f'verticals.{vertical}.vertical_config')
    except (ImportError, ModuleNotFoundError):
        _vc = importlib.import_module('verticals.dc2_s.vertical_config')
    PLAYBOOK_CONFIG = getattr(_vc, 'PLAYBOOK_CONFIG', {})
    # AND-logic playbooks + pillar→playbook map come from the vertical config,
    # falling back to the dc2_s defaults when a vertical doesn't declare them.
    AND_LOGIC_PLAYBOOKS = getattr(_vc, 'AND_LOGIC_PLAYBOOKS', {"PB-04"})
    PILLAR_PLAYBOOK_MAP = getattr(_vc, 'PILLAR_PLAYBOOK_MAP', {
        'P1': 'PB-01', 'P2': 'PB-02', 'P3': 'PB-03', 'P4': 'PB-05', 'P5': 'PB-04',
    })

    recommendations = []

    for pb_id, config in PLAYBOOK_CONFIG.items():
        conditions = config.get("trigger_conditions", {})
        if not conditions:
            continue

        fired_reasons = []
        all_met = True
        any_met = False
        urgency_score = 0

        for kpi_code, condition in conditions.items():
            operator = condition.get("operator")
            threshold = condition.get("value")

            # PB-05 uses OVERALL_HEALTH (account-level score, not a KPI)
            if kpi_code == "OVERALL_HEALTH":
                if health_score is None:
                    all_met = False
                    continue
                value = health_score
            else:
                if kpi_code not in kpi_values:
                    all_met = False
                    continue
                value = kpi_values[kpi_code]

            # Coerce DB Decimals / strings to float so the urgency arithmetic below
            # never hits `Decimal * float` (KPI values from the DB are Decimal).
            try:
                value = float(value)
                threshold = float(threshold)
            except (TypeError, ValueError):
                all_met = False
                continue

            triggered = False
            if operator == ">" and value > threshold:
                triggered = True
            elif operator == "<" and value < threshold:
                triggered = True
            elif operator == "==" and value == threshold:
                triggered = True

            if triggered:
                any_met = True
                fired_reasons.append(
                    f"{kpi_code} = {value:.1f} ({operator} {threshold} threshold breached)"
                )
                # Urgency contribution: how far past threshold
                if operator == ">":
                    overshoot_pct = (value - threshold) / max(threshold, 1) * 100
                elif operator == "<":
                    overshoot_pct = (threshold - value) / max(threshold, 1) * 100
                else:
                    overshoot_pct = 50
                urgency_score += min(50, 20 + overshoot_pct * 0.3)
            else:
                all_met = False

        # Determine if playbook should be recommended
        use_and = pb_id in AND_LOGIC_PLAYBOOKS
        needed = all_met if use_and else any_met

        if needed and fired_reasons:
            urgency_level = (
                'Critical' if urgency_score >= 60
                else ('High' if urgency_score >= 30 else 'Medium')
            )
            recommendations.append({
                'playbook_id': pb_id,
                'playbook_name': config.get('name', pb_id),
                'urgency_score': round(urgency_score, 1),
                'urgency_level': urgency_level,
                'reasons': fired_reasons,
                'health_score': health_score,
                'estimated_impact': config.get('estimated_impact', ''),
                'estimated_duration': config.get('estimated_duration_display', ''),
                'trigger_logic': 'AND' if use_and else 'OR',
                'sub_components': [
                    {'id': sc['id'], 'name': sc['name'], 'hours': sc['estimated_hours']}
                    for sc in config.get('sub_components', [])
                ],
            })

    # Pillar-weakness recommendations (secondary) — PILLAR_PLAYBOOK_MAP loaded above
    if pillar_scores:
        already_recommended = {r['playbook_id'] for r in recommendations}
        for pillar, score in pillar_scores.items():
            mapped = PILLAR_PLAYBOOK_MAP.get(pillar)
            if score < 50 and mapped and mapped not in already_recommended:
                pb_id = mapped
                pb_config = PLAYBOOK_CONFIG.get(pb_id, {})
                recommendations.append({
                    'playbook_id': pb_id,
                    'playbook_name': pb_config.get('name', pb_id),
                    'urgency_score': max(10, 50 - score),
                    'urgency_level': 'High' if score < 40 else 'Medium',
                    'reasons': [f'{pillar} pillar score {score:.0f} (critical, below 50)'],
                    'recommendation_source': 'pillar_weakness',
                    'health_score': health_score,
                    'estimated_impact': f'+{min(20, int(50 - score))}% improvement potential in {pillar}',
                    'estimated_duration': '7\u201314 days',
                })

    # Expansion recommendations for healthy accounts (health >= 70)
    if health_score and health_score >= 70:
        already_recommended = {r['playbook_id'] for r in recommendations}
        p5_score = (pillar_scores or {}).get('P5', 0)
        # PB-04 if strong P5 (expansion ready)
        if p5_score >= 70 and 'PB-04' not in already_recommended:
            pb_config = PLAYBOOK_CONFIG.get('PB-04', {})
            recommendations.append({
                'playbook_id': 'PB-04',
                'playbook_name': pb_config.get('name', 'Capacity Planning'),
                'urgency_score': 15,
                'urgency_level': 'Opportunity',
                'reasons': [f'Healthy account (health {health_score:.0f}) with strong Revenue & Growth (P5={p5_score:.0f}) — expansion ready'],
                'recommendation_source': 'expansion_readiness',
                'health_score': health_score,
                'estimated_impact': 'Upsell/cross-sell opportunity',
                'estimated_duration': '14–30 days',
            })
        # PB-06 Customer Engagement — proactive for all healthy accounts
        if 'PB-06' not in already_recommended:
            pb_config = PLAYBOOK_CONFIG.get('PB-06', {})
            recommendations.append({
                'playbook_id': 'PB-06',
                'playbook_name': pb_config.get('name', 'Customer Engagement'),
                'urgency_score': 10,
                'urgency_level': 'Opportunity',
                'reasons': ['Healthy account — proactive engagement to protect and expand'],
                'recommendation_source': 'proactive_engagement',
                'health_score': health_score,
                'estimated_impact': 'Strengthen champion relationship, prevent silent churn',
                'estimated_duration': '7–14 days',
            })

    # Enrich with historical success data if customer_id available
    if customer_id:
        for rec in recommendations:
            hist = _get_playbook_historical_success(rec['playbook_id'], customer_id)
            if hist:
                rec['historical_success'] = hist

    # Cap at 3, sort by urgency
    recommendations.sort(key=lambda r: r.get('urgency_score', 0), reverse=True)
    recommendations = recommendations[:3]

    return recommendations


def _resolve_vertical_for_customer(customer_id):
    """Local helper to look up vertical for a customer.

    Mirrors mcp_server.cs_pulse_mcp_server._resolve_customer_vertical but
    inlined here so the HTTP route (which doesn't import the MCP module)
    can route correctly. Reads CustomerConfig.vertical first (canonical
    long form), then Customer.vertical (short code), normalizes via
    vertical_registry.

    Returns canonical long-form vertical: 'saas_premium', 'dc2_s', etc.
    """
    try:
        from models import Customer, CustomerConfig
        from utils.vertical_registry import normalize_vertical

        cfg = CustomerConfig.query.filter_by(customer_id=int(customer_id)).first()
        if cfg and cfg.vertical:
            return normalize_vertical(cfg.vertical)

        cust = Customer.query.get(int(customer_id))
        if cust and getattr(cust, 'vertical', None):
            return normalize_vertical(cust.vertical)
    except Exception as e:
        logger.debug(f"vertical resolution failed for customer {customer_id}: {e}")
    return 'dc2_s'  # legacy fallback


def get_recommendations_for_account(account_id, customer_id, health_score=None,
                                    kpi_values=None):
    """Get ranked playbook recommendations for a specific account.

    Vertical-aware (fixes bug B-4 from May 17 FDE eval):
      - dc2_s tenant: evaluates PB-01 through PB-06 from verticals/dc2_s/vertical_config.py
        using actual KPI values against canonical trigger conditions.
      - saas_premium (and other non-DC) tenants: routes to generic SaaS-flavored
        evaluators (voc-sprint, activation-blitz, sla-stabilizer, renewal-safeguard,
        expansion-timing) — the playbook IDs referenced by power_of_1_economics.json's
        `linked_playbooks` field for the non-DC catalog.

    The previous version unconditionally entered the DC2S branch whenever kpi_values
    were provided (which is the standard MCP call path), so SaaS tenants got
    DC2S playbook recommendations AND a hardcoded `vertical: 'dc2_s'` tag.

    Args:
        account_id: Account identifier
        customer_id: Customer/tenant ID — used to resolve the tenant's vertical
        health_score: Optional pre-calculated health score (0-100)
        kpi_values: Optional dict of KPI code → value. Required for DC2S evaluation;
                    ignored on the SaaS path (the generic evaluators read account/KPI
                    state from the DB themselves).

    Returns:
        dict with ranked recommendations list and the resolved vertical tag.
    """
    account = Account.query.filter_by(
        account_id=int(account_id),
        customer_id=int(customer_id),
    ).first()

    if not account:
        return {"account_id": account_id, "recommendations": [],
                "error": f"Account {account_id} not found"}

    # ── Resolve the customer's vertical (source of truth: CustomerConfig.vertical) ──
    vertical = _resolve_vertical_for_customer(customer_id)

    # ── Retrieve pillar scores from latest HealthScore ──
    pillar_scores = None
    try:
        from models import HealthScore
        _hs = HealthScore.query.filter_by(account_id=int(account_id)) \
            .order_by(HealthScore.measurement_month.desc()).first()
        if _hs and _hs.contributing_pillars:
            pillar_scores = {k: float(v) for k, v in _hs.contributing_pillars.items()}
    except Exception:
        pass

    # ── Config-driven vertical path (dc2_s, datacenter_v1) ──
    if vertical in _CONFIG_PLAYBOOK_VERTICALS and kpi_values is not None:
        recommendations = _evaluate_dc2s_playbooks(kpi_values, health_score, pillar_scores,
                                                    customer_id=customer_id, vertical=vertical)

        # Enrich with historical success rates
        for rec in recommendations:
            hist = _get_playbook_historical_success(rec['playbook_id'], customer_id)
            rec['historical_success'] = hist
            if hist:
                rec['success_summary'] = (
                    f"{hist['success_rate_pct']}% success rate "
                    f"({hist['resolved']}/{hist['total_runs']} resolved)"
                )

        return {
            'account_id': account_id,
            'account_name': account.account_name,
            'health_score': health_score,
            'vertical': vertical,
            'playbook_source': f'vertical_config ({vertical})',
            'total_recommendations': len(recommendations),
            'recommendations': recommendations,
        }

    # ── Generic Path (saas_premium and other non-DC2S verticals) ──
    playbooks = {
        'voc-sprint': ('VoC Sprint', evaluate_account_for_voc_sprint),
        'activation-blitz': ('Activation Blitz', evaluate_account_for_activation_blitz),
        'sla-stabilizer': ('SLA Stabilizer', evaluate_account_for_sla_stabilizer),
        'renewal-safeguard': ('Renewal Safeguard', evaluate_account_for_renewal_safeguard),
        'expansion-timing': ('Expansion Timing', evaluate_account_for_expansion_timing),
    }

    recommendations = []
    for pb_id, (pb_name, evaluator) in playbooks.items():
        try:
            result = evaluator(account, {})
            if result.get('needed'):
                recommendations.append({
                    'playbook_id': pb_id,
                    'playbook_name': pb_name,
                    'urgency_score': result.get('urgency_score', 0),
                    'urgency_level': result.get('urgency_level', 'Medium'),
                    'reasons': result.get('reasons', []),
                    'health_score': result.get('health_score'),
                })
        except Exception as e:
            logger.debug(f"Error evaluating {pb_id} for account {account_id}: {e}")

    recommendations.sort(key=lambda r: r['urgency_score'], reverse=True)

    # Enrich with historical success rates
    for rec in recommendations:
        hist = _get_playbook_historical_success(rec['playbook_id'], customer_id)
        rec['historical_success'] = hist
        if hist:
            rec['success_summary'] = (
                f"{hist['success_rate_pct']}% success rate "
                f"({hist['resolved']}/{hist['total_runs']} resolved)"
            )

    return {
        'account_id': account_id,
        'account_name': account.account_name,
        'health_score': health_score,
        'vertical': vertical,
        'playbook_source': 'generic_saas_evaluators (voc-sprint, activation-blitz, sla-stabilizer, renewal-safeguard, expansion-timing)',
        'total_recommendations': len(recommendations),
        'recommendations': recommendations,
    }



def calculate_health_score_proxy(account_id):
    """Calculate health score - uses HealthScoreEngine when available, falls back to simple proxy."""
    try:
        return _calculate_health_score_via_engine(account_id)
    except Exception:
        return _calculate_health_score_simple(account_id)


def _calculate_health_score_via_engine(account_id):
    """Calculate using the canonical HealthScoreEngine (reference range based)."""
    from health_score_engine import HealthScoreEngine

    kpis = KPI.query.filter_by(account_id=account_id).all()
    if not kpis:
        return 50.0

    # Group KPIs by category
    categories = {}
    for kpi in kpis:
        cat = kpi.category or 'Uncategorized'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            'kpi_parameter': kpi.kpi_parameter,
            'data': kpi.data,
            'impact_level': kpi.impact_level,
            'weight': kpi.weight,
            'category': kpi.category,
            'health_score_component': kpi.health_score_component,
        })

    # Calculate per-category health scores
    category_scores = []
    for cat, kpi_dicts in categories.items():
        cat_result = HealthScoreEngine.calculate_category_health_score(kpi_dicts, cat)
        category_scores.append(cat_result)

    # Calculate overall health score
    overall_result = HealthScoreEngine.calculate_overall_health_score(category_scores)
    return max(0.0, min(100.0, overall_result['overall_score']))


def _calculate_health_score_simple(account_id):
    """Fallback: simplified health score calculation."""
    # Get recent KPIs for the account
    kpis = KPI.query.filter_by(account_id=account_id).all()

    if not kpis:
        return 50.0  # Default middle score

    # Simple health calculation based on KPI data and impact levels
    total_score = 0
    valid_kpis = 0

    for kpi in kpis:
        try:
            # Parse the KPI data value
            data_str = str(kpi.data).replace('%', '').replace('$', '').replace('K', '000').replace('M', '000000')
            value = float(data_str) if data_str.strip() else 0

            # Normalize to 0-100 scale based on KPI type
            if 'score' in kpi.kpi_parameter.lower() or 'rate' in kpi.kpi_parameter.lower():
                # Already in percentage or score format
                normalized_score = min(100, max(0, value))
            elif 'count' in kpi.kpi_parameter.lower() or 'ticket' in kpi.kpi_parameter.lower():
                # Count-based KPIs - lower is better
                if value == 0:
                    normalized_score = 100
                elif value <= 10:
                    normalized_score = 80
                elif value <= 50:
                    normalized_score = 60
                elif value <= 100:
                    normalized_score = 40
                else:
                    normalized_score = 20
            else:
                # Default normalization
                normalized_score = min(100, max(0, value))

            # Weight by impact level
            impact_weight = 1.0
            if kpi.impact_level == 'Critical':
                impact_weight = 3.0
            elif kpi.impact_level == 'High':
                impact_weight = 2.0
            elif kpi.impact_level == 'Medium':
                impact_weight = 1.5

            total_score += normalized_score * impact_weight
            valid_kpis += impact_weight

        except (ValueError, TypeError):
            # Skip invalid KPI data
            continue

    if valid_kpis > 0:
        average_score = total_score / valid_kpis
        return max(0, min(100, average_score))
    else:
        return 50.0  # Default if no valid KPIs


def evaluate_account_for_voc_sprint(account, triggers):
    """Evaluate if account needs VoC Sprint playbook"""
    reasons = []
    score = 0  # Higher score = more urgent need
    
    # Calculate health score proxy
    health_score = calculate_health_score_proxy(account.account_id)
    
    # Check NPS threshold (using health score as proxy)
    nps_threshold = triggers.get('nps_threshold', 10.0)  # Default threshold
    nps_proxy = health_score / 10  # Convert to 0-10 scale
    if nps_proxy < nps_threshold:
        reasons.append(f"Low NPS proxy ({nps_proxy:.1f} < {nps_threshold})")
        score += 30
    
    # Check CSAT threshold (using health score as proxy)
    csat_threshold = triggers.get('csat_threshold', 3.6)  # Default threshold
    csat_proxy = health_score / 20  # Convert to 0-5 scale
    if csat_proxy < csat_threshold:
        reasons.append(f"Low CSAT proxy ({csat_proxy:.1f} < {csat_threshold})")
        score += 25
    
    # Check account status for churn risk
    if account.account_status.lower() == 'at risk':
        reasons.append("Account marked 'At Risk'")
        score += 40
    
    # Check health score drop
    health_drop_threshold = triggers.get('health_score_drop_threshold', 10)
    if health_score < ht.at_risk_min():  # Below at-risk threshold = critical
        reasons.append(f"Low health score ({health_score:.1f})")
        score += 20
    
    
    return {
        'needed': score > 0,
        'urgency_score': score,
        'urgency_level': 'Critical' if score >= 60 else ('High' if score >= 30 else 'Medium'),
        'reasons': reasons,
        'health_score': health_score
    }


def evaluate_account_for_activation_blitz(account, triggers):
    """Evaluate if account needs Activation Blitz playbook"""
    reasons = []
    score = 0
    
    # Calculate adoption proxy from health score
    adoption_proxy = calculate_health_score_proxy(account.account_id)
    
    # Check adoption index
    adoption_threshold = triggers.get('adoption_index_threshold', 60)
    if adoption_proxy < adoption_threshold:
        reasons.append(f"Low adoption index ({adoption_proxy:.1f} < {adoption_threshold})")
        score += 30
    
    # Check active users (estimate from revenue as proxy)
    active_users_threshold = triggers.get('active_users_threshold', 50)
    estimated_users = int(account.revenue / 5000) if account.revenue else 0
    if estimated_users < active_users_threshold:
        reasons.append(f"Low estimated active users (~{estimated_users} < {active_users_threshold})")
        score += 25
    
    # Check for low feature usage
    kpi_count = KPI.query.filter_by(account_id=account.account_id).count()
    if kpi_count < 10:
        reasons.append(f"Limited feature usage ({kpi_count} KPIs tracked)")
        score += 20
    
    # Check DAU/MAU (simulated based on health)
    dau_mau_threshold = triggers.get('dau_mau_threshold', 0.25)
    dau_mau_proxy = 0.15 if adoption_proxy < 60 else 0.35
    if dau_mau_proxy < dau_mau_threshold:
        reasons.append(f"Low DAU/MAU ratio (~{dau_mau_proxy:.2f} < {dau_mau_threshold})")
        score += 20
    
    # Check if high-revenue but low adoption (expansion opportunity)
    if account.revenue and account.revenue > 100000 and adoption_proxy < 60:
        reasons.append(f"High revenue (${account.revenue:,.0f}) but low adoption")
        score += 15
    
    return {
        'needed': score > 0,
        'urgency_score': score,
        'urgency_level': 'Critical' if score >= 60 else ('High' if score >= 30 else 'Medium'),
        'reasons': reasons,
        'adoption_index': adoption_proxy
    }


def evaluate_account_for_sla_stabilizer(account, triggers):
    """Evaluate if account needs SLA Stabilizer playbook"""
    reasons = []
    score = 0
    
    # Get SLA-related KPIs
    kpis = KPI.query.filter_by(account_id=account.account_id).all()
    
    # Check SLA breach threshold (configurable)
    sla_breach_threshold = triggers.get('sla_breach_threshold', 5)
    sla_breach_kpi = next((k for k in kpis if 'sla' in k.kpi_parameter.lower() or 'breach' in k.kpi_parameter.lower()), None)
    if sla_breach_kpi:
        try:
            breach_count = int(sla_breach_kpi.data) if sla_breach_kpi.data else 0
            if breach_count > sla_breach_threshold:
                reasons.append(f"SLA breaches ({breach_count} > {sla_breach_threshold})")
                score += 40
        except:
            if sla_breach_kpi.impact_level == 'Critical':
                reasons.append("SLA breaches detected")
                score += 40
    
    # Check response time multiplier (configurable)
    response_time_multiplier = triggers.get('response_time_multiplier', 2.0)
    response_kpi = next((k for k in kpis if 'response' in k.kpi_parameter.lower()), None)
    if response_kpi:
        try:
            response_time = float(response_kpi.data) if response_kpi.data else 0
            if response_time > (24 * response_time_multiplier):  # 24 hours * multiplier
                reasons.append(f"Slow response times ({response_time:.1f}h > {24 * response_time_multiplier}h)")
                score += 30
        except:
            if response_kpi.impact_level in ['Critical', 'High']:
                reasons.append("Slow response times detected")
                score += 30
    
    # Check escalation trend (configurable)
    escalation_trend = triggers.get('escalation_trend', 'increasing')
    escalation_kpi = next((k for k in kpis if 'escalat' in k.kpi_parameter.lower()), None)
    if escalation_kpi and escalation_trend == 'increasing':
        if escalation_kpi.impact_level == 'Critical':
            reasons.append("High escalation volume")
            score += 20
    
    # Check reopen rate threshold (configurable)
    reopen_rate_threshold = triggers.get('reopen_rate_threshold', 0.20)
    reopen_kpi = next((k for k in kpis if 'reopen' in k.kpi_parameter.lower()), None)
    if reopen_kpi:
        try:
            reopen_rate = float(reopen_kpi.data) if reopen_kpi.data else 0
            if reopen_rate > reopen_rate_threshold:
                reasons.append(f"High reopen rate ({reopen_rate:.1%} > {reopen_rate_threshold:.1%})")
                score += 25
        except:
            pass
    
    return {
        'needed': score > 0,
        'urgency_score': score,
        'urgency_level': 'Critical' if score >= 60 else ('High' if score >= 30 else 'Medium'),
        'reasons': reasons,
        'sla_metrics': len([k for k in kpis if 'sla' in k.kpi_parameter.lower()])
    }


def evaluate_account_for_renewal_safeguard(account, triggers):
    """Evaluate if account needs Renewal Safeguard playbook"""
    reasons = []
    score = 0
    
    # Calculate health score
    health_score = calculate_health_score_proxy(account.account_id)
    
    # Check health score threshold (configurable)
    health_threshold = triggers.get('health_score_threshold', 70)
    if health_score < health_threshold:
        reasons.append(f"Low health score ({health_score:.1f} < {health_threshold})")
        score += 35
    
    # Check renewal window days (configurable)
    renewal_window_days = triggers.get('renewal_window_days', 90)
    # Simplified check - assume accounts with low health are approaching renewal
    if health_score < ht.healthy_min():  # Below healthy threshold
        reasons.append(f"Likely approaching renewal window ({renewal_window_days} days)")
        score += 20
    
    # Check engagement trend (configurable)
    engagement_trend = triggers.get('engagement_trend', 'declining')
    if engagement_trend == 'declining':
        kpis = KPI.query.filter_by(account_id=account.account_id).all()
        engagement_kpis = [k for k in kpis if 'engagement' in k.kpi_parameter.lower() or 'qbr' in k.kpi_parameter.lower()]
        for kpi in engagement_kpis:
            if 'declin' in str(kpi.data).lower() or 'missed' in str(kpi.data).lower():
                reasons.append(f"Declining engagement: {kpi.kpi_parameter}")
                score += 25
                break
    
    # Check budget risk (configurable)
    budget_risk = triggers.get('budget_risk', True)
    if budget_risk and account.account_status.lower() == 'at risk':
        reasons.append("Account marked 'At Risk' - budget concerns")
        score += 30
    
    return {
        'needed': score > 0,
        'urgency_score': score,
        'urgency_level': 'Critical' if score >= 70 else ('High' if score >= 40 else 'Medium'),
        'reasons': reasons,
        'health_score': health_score,
        'revenue_at_risk': float(account.revenue) if account.revenue else 0
    }


def evaluate_account_for_expansion_timing(account, triggers):
    """Evaluate if account is ready for expansion"""
    reasons = []
    score = 0
    
    # Calculate adoption/health score
    health_score = calculate_health_score_proxy(account.account_id)
    
    # Check health score threshold (need HIGH health for expansion)
    health_threshold = triggers.get('health_score_threshold', 80)
    if health_score >= health_threshold:
        reasons.append(f"Excellent health score ({health_score:.1f} ≥ {health_threshold})")
        score += 40
    else:
        # Not ready for expansion if health is low
        return {
            'needed': False,
            'urgency_score': 0,
            'urgency_level': 'Low',
            'reasons': ['Health score too low for expansion'],
            'health_score': health_score
        }
    
    # Check adoption threshold (configurable)
    adoption_threshold = triggers.get('adoption_threshold', 0.85)
    kpi_count = KPI.query.filter_by(account_id=account.account_id).count()
    adoption_proxy = kpi_count / 20  # Fraction (0-1)
    if adoption_proxy >= adoption_threshold:
        reasons.append(f"High adoption ({adoption_proxy:.1%} ≥ {adoption_threshold:.1%})")
        score += 30
    else:
        return {
            'needed': False,
            'urgency_score': 0,
            'urgency_level': 'Low',
            'reasons': ['Insufficient adoption for expansion'],
            'health_score': health_score
        }
    
    # Check usage limit percentage (configurable)
    usage_limit_percentage = triggers.get('usage_limit_percentage', 0.80)
    usage_proxy = min(1.0, kpi_count / 25)  # Simulate usage as percentage of capacity
    if usage_proxy >= usage_limit_percentage:
        reasons.append(f"High usage ({usage_proxy:.1%} ≥ {usage_limit_percentage:.1%}) - expansion opportunity")
        score += 25
    
    # Check budget window (configurable)
    budget_window = triggers.get('budget_window', 'open')
    if budget_window in ['Q1_Q4', 'Q1', 'Q4', 'open']:  # Budget available
        reasons.append(f"Budget window open ({budget_window})")
        score += 20
    
    return {
        'needed': score > 0,
        'urgency_score': score,
        'urgency_level': 'High' if score >= 80 else ('Medium' if score >= 50 else 'Low'),
        'reasons': reasons,
        'health_score': health_score,
        'expansion_potential': float(account.revenue * 0.3) if account.revenue else 0
    }


@playbook_recommendations_api.route('/api/playbooks/test-health-score/<int:account_id>', methods=['GET'])
def test_health_score(account_id):
    """Test endpoint to debug health score calculation"""
    try:
        health_score = calculate_health_score_proxy(account_id)
        return jsonify({
            'account_id': account_id,
            'health_score': health_score,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Error in test_health_score for account {account_id}: {str(e)}", exc_info=True)
        return jsonify({
            'account_id': account_id,
            'error': 'Health score calculation failed. Please try again or contact support.',
            'status': 'error'
        }), 500

@playbook_recommendations_api.route('/api/playbooks/recommendations/<playbook_id>', methods=['POST'])
def get_playbook_recommendations(playbook_id):
    """Get account recommendations for a specific playbook.

    Supports both generic playbook IDs (voc-sprint, activation-blitz, etc.)
    and DC2S vertical IDs (PB-01 through PB-06). DC2S playbooks evaluate
    against actual KPI values using trigger conditions from vertical_config.
    """
    try:
        customer_id = get_current_customer_id()
        data = request.json or {}
        triggers = data.get('triggers', {})

        # Get all accounts for customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()

        # ── Config-Driven Vertical Path: PB-01 through PB-13 ──
        if playbook_id.startswith('PB-'):
            # Vertical-aware PLAYBOOK_CONFIG resolution (was hardcoded to
            # verticals.dc2_s.vertical_config regardless of the requesting
            # customer's vertical — a datacenter_v1 customer's PB-07..13
            # playbooks 404'd as "Unknown DC2S playbook" since they only
            # exist in datacenter_v1's own PLAYBOOK_CONFIG). Mirrors the
            # _CONFIG_PLAYBOOK_VERTICALS/dynamic-import pattern already
            # established in _evaluate_dc2s_playbooks above. Any vertical
            # outside that set falls back to dc2_s's config, matching prior
            # behavior for saas_premium/other tenants (no PB- playbooks of
            # their own).
            import importlib
            _vertical = _resolve_vertical_for_customer(customer_id)
            _config_vertical = _vertical if _vertical in _CONFIG_PLAYBOOK_VERTICALS else 'dc2_s'
            try:
                _vc = importlib.import_module(f'verticals.{_config_vertical}.vertical_config')
            except (ImportError, ModuleNotFoundError):
                _vc = importlib.import_module('verticals.dc2_s.vertical_config')
                _config_vertical = 'dc2_s'
            PLAYBOOK_CONFIG = getattr(_vc, 'PLAYBOOK_CONFIG', {})

            def should_trigger_playbook(pb_id, kpi_values_eval):
                """Generic AND-logic trigger check against the resolved
                vertical's PLAYBOOK_CONFIG (mirrors
                verticals.dc2_s.vertical_config.should_trigger_playbook,
                but takes PLAYBOOK_CONFIG explicitly instead of reading a
                hardcoded dc2_s module-global, so it evaluates correctly
                for any config-driven vertical, not just dc2_s)."""
                cfg = PLAYBOOK_CONFIG.get(pb_id, {})
                for kpi, condition in cfg.get("trigger_conditions", {}).items():
                    if kpi not in kpi_values_eval:
                        return False
                    value = kpi_values_eval[kpi]
                    operator = condition.get("operator")
                    threshold = condition.get("value")
                    if operator == ">" and value <= threshold:
                        return False
                    elif operator == "<" and value >= threshold:
                        return False
                    elif operator == "==" and value != threshold:
                        return False
                return True

            from utils.vertical_health import (
                get_health_calculator, get_trailing_kpi_values_func,
                get_precalculated_scores,
            )
            _get_trailing_kpi_values = get_trailing_kpi_values_func(customer_id)
            calculate_kpi_health = get_health_calculator(customer_id)

            config = PLAYBOOK_CONFIG.get(playbook_id)
            if not config:
                return jsonify({
                    'status': 'error',
                    'message': f"Unknown playbook for vertical '{_config_vertical}': {playbook_id}. "
                               f"Valid: {', '.join(sorted(PLAYBOOK_CONFIG.keys()))}"
                }), 404

            recommendations = []
            for account in accounts:
                kpi_values = _get_trailing_kpi_values(account.account_id)

                precalc_health, _, _ = get_precalculated_scores(account.account_id)
                if precalc_health is not None:
                    health = precalc_health
                else:
                    health, _ = calculate_kpi_health(kpi_values, customer_id)

                # For PB-05 inject OVERALL_HEALTH
                eval_values = dict(kpi_values)
                eval_values['OVERALL_HEALTH'] = health

                triggered = should_trigger_playbook(playbook_id, eval_values)

                # Build per-condition reasons
                reasons = []
                conditions = config.get('trigger_conditions', {})
                for kpi_code, condition in conditions.items():
                    val = eval_values.get(kpi_code)
                    if val is None:
                        continue
                    op = condition['operator']
                    thresh = condition['value']
                    if (op == '>' and val > thresh) or (op == '<' and val < thresh):
                        reasons.append(
                            f"{kpi_code} = {val:.1f} ({op} {thresh} threshold breached)"
                        )

                recommendations.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'industry': account.industry,
                    'region': account.region,
                    'revenue': float(account.revenue) if account.revenue else 0,
                    'account_status': account.account_status,
                    'needed': triggered,
                    'urgency_score': len(reasons) * 30 if triggered else 0,
                    'urgency_level': 'Critical' if len(reasons) >= 2 else (
                        'High' if triggered else 'Low'),
                    'reasons': reasons,
                    'metrics': {'health_score': round(health, 1)},
                })

            recommendations.sort(key=lambda x: x['urgency_score'], reverse=True)
            urgency_counts = {
                'Critical': len([r for r in recommendations if r['urgency_level'] == 'Critical']),
                'High': len([r for r in recommendations if r['urgency_level'] == 'High']),
                'Medium': len([r for r in recommendations if r['urgency_level'] == 'Medium']),
                'Low': len([r for r in recommendations if not r['needed']]),
            }

            return jsonify({
                'status': 'success',
                'playbook_id': playbook_id,
                'playbook_name': config.get('name', playbook_id),
                'vertical': _config_vertical,
                'total_accounts': len(accounts),
                'accounts_needing_playbook': len([r for r in recommendations if r['needed']]),
                'urgency_breakdown': urgency_counts,
                'recommendations': recommendations,
            })

        # ── Generic Path (non-DC2S) ──
        # Always try to fetch from database first, then use provided triggers as fallback
        from models import PlaybookTrigger

        # Map API playbook_id to database playbook_type
        playbook_type_mapping = {
            'voc-sprint': 'voc',
            'activation-blitz': 'activation',
            'sla-stabilizer': 'sla',
            'renewal-safeguard': 'renewal',
            'expansion-timing': 'expansion'
        }
        db_playbook_type = playbook_type_mapping.get(playbook_id, playbook_id)

        trigger_config = PlaybookTrigger.query.filter_by(
            customer_id=customer_id,
            playbook_type=db_playbook_type
        ).first()

        if trigger_config and trigger_config.trigger_config:
            db_triggers = json.loads(trigger_config.trigger_config)
            # Merge provided triggers with database triggers (database takes precedence now)
            triggers = {**triggers, **db_triggers}

        recommendations = []

        for account in accounts:
            # Evaluate based on playbook type
            if playbook_id == 'voc-sprint':
                evaluation = evaluate_account_for_voc_sprint(account, triggers)
            elif playbook_id == 'activation-blitz':
                evaluation = evaluate_account_for_activation_blitz(account, triggers)
            elif playbook_id == 'sla-stabilizer':
                evaluation = evaluate_account_for_sla_stabilizer(account, triggers)
            elif playbook_id == 'renewal-safeguard':
                evaluation = evaluate_account_for_renewal_safeguard(account, triggers)
            elif playbook_id == 'expansion-timing':
                evaluation = evaluate_account_for_expansion_timing(account, triggers)
            else:
                # Unknown generic playbook
                evaluation = {
                    'needed': False,
                    'urgency_score': 0,
                    'urgency_level': 'Low',
                    'reasons': []
                }

            recommendations.append({
                'account_id': account.account_id,
                'account_name': account.account_name,
                'industry': account.industry,
                'region': account.region,
                'revenue': float(account.revenue) if account.revenue else 0,
                'account_status': account.account_status,
                'needed': evaluation['needed'],
                'urgency_score': evaluation['urgency_score'],
                'urgency_level': evaluation['urgency_level'],
                'reasons': evaluation['reasons'],
                'metrics': {
                    k: v for k, v in evaluation.items()
                    if k not in ['needed', 'urgency_score', 'urgency_level', 'reasons']
                }
            })

        # Sort by urgency score (highest first)
        recommendations.sort(key=lambda x: x['urgency_score'], reverse=True)

        # Count by urgency level
        urgency_counts = {
            'Critical': len([r for r in recommendations if r['urgency_level'] == 'Critical']),
            'High': len([r for r in recommendations if r['urgency_level'] == 'High']),
            'Medium': len([r for r in recommendations if r['urgency_level'] == 'Medium']),
            'Low': len([r for r in recommendations if not r['needed']])
        }

        return jsonify({
            'status': 'success',
            'playbook_id': playbook_id,
            'total_accounts': len(accounts),
            'accounts_needing_playbook': len([r for r in recommendations if r['needed']]),
            'urgency_breakdown': urgency_counts,
            'recommendations': recommendations
        })

    except Exception as e:
        logger.error(f"Error getting playbook recommendations for {playbook_id}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to get playbook recommendations. Please try again or contact support.'
        }), 500



def seed_approval_queue_from_recommendations(customer_id, confidence=0.70,
                                             limit_per_account=2):
    """Populate the approval queue with the human-approval-required playbook
    recommendations for a customer's accounts (vertical-aware, idempotent).

    Called at the end of process-data so a config-playbook tenant (dc2_s,
    datacenter_v1) gets a populated approvals queue with vertical-correct
    playbook_ids. Only submits playbooks whose vertical_config marks
    human_approval_required=True; skips accounts that already have a pending
    approval for the same playbook. Non-config verticals (saas_premium, …) are
    left to their own agent pipeline.
    """
    import importlib
    from sqlalchemy import func
    from models import Account, DC2SKPI, HealthScore
    try:
        from approval_queue import ApprovalQueueService, ApprovalRequest
    except Exception:
        return {'seeded': 0, 'reason': 'approval_queue unavailable'}

    vertical = _resolve_vertical_for_customer(customer_id)
    if vertical not in _CONFIG_PLAYBOOK_VERTICALS:
        return {'seeded': 0, 'reason': f'{vertical} not a config-playbook vertical'}
    try:
        _vc = importlib.import_module(f'verticals.{vertical}.vertical_config')
        pconf = getattr(_vc, 'PLAYBOOK_CONFIG', {})
    except Exception:
        return {'seeded': 0}
    approval_needed = {pid for pid, c in pconf.items() if c.get('human_approval_required')}
    if not approval_needed:
        return {'seeded': 0, 'reason': 'no human-approval playbooks'}

    svc = ApprovalQueueService()
    seeded = 0
    for a in Account.query.filter_by(customer_id=customer_id).all():
        kv = {c: float(v) for c, v in db.session.query(
            DC2SKPI.kpi_code, func.avg(DC2SKPI.value)
        ).filter(DC2SKPI.account_id == a.account_id).group_by(DC2SKPI.kpi_code).all()}
        if not kv:
            continue
        hs = HealthScore.query.filter_by(account_id=a.account_id) \
            .order_by(HealthScore.calculated_at.desc()).first()
        rec = get_recommendations_for_account(
            a.account_id, customer_id,
            health_score=(hs.health_score if hs else None), kpi_values=kv)
        n = 0
        for r in rec.get('recommendations', []):
            pid = r.get('playbook_id')
            if pid not in approval_needed:
                continue
            exists = ApprovalRequest.query.filter_by(
                account_id=str(a.account_id), playbook_id=pid, status='pending').first()
            if exists:
                continue
            try:
                svc.submit(
                    customer_id=customer_id, account_id=str(a.account_id),
                    action_type='playbook_trigger', confidence=confidence,
                    predicted_outcome=r.get('estimated_impact'),
                    reasoning=('; '.join(r.get('reasons', []) or [])[:500]
                               or f"{pid} recommended"),
                    dollar_impact=(float(a.revenue) if getattr(a, 'revenue', None) else None),
                    playbook_id=pid,
                    action_payload={'playbook_name': r.get('playbook_name'),
                                    'source': 'recommendation_seed'},
                    agent_id='playbook_recommender',
                )
                seeded += 1
                n += 1
            except Exception as e:
                logger.warning(f"seed approval failed for acct {a.account_id} {pid}: {e}")
            if n >= limit_per_account:
                break
    return {'seeded': seeded, 'vertical': vertical}
