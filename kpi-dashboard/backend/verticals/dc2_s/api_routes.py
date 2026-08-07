#!/usr/bin/env python3
"""
DC2_S Vertical API Routes - CORRECTED
Handles dict targets from YOUR Week 1 KPI definitions
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import Account, DC2SKPI, User, PlaybookExecutionV2, PlaybookReport, CustomerConfig, HealthScore, PillarScore, ActionEconomics
from utils.playbook_lifecycle import (
    start_execution as _lifecycle_start,
    close_execution as _lifecycle_close,
    build_frontend_execution_dict as _build_exec_dict,
)
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import math
import uuid

# Import DC2_S vertical modules - matching YOUR file structure
from .kpi_definitions import DC2S_KPIS, DC2S_PILLARS
from .pillar_weights import get_current_weights, get_weights_for_customer
from .vertical_config import (
    determine_customer_phase, PLAYBOOK_CONFIG, should_trigger_playbook,
    get_playbook_config, get_playbooks_for_phase, get_playbook_duration_and_sub_components,
    PHASE_CONFIG,
)
from .metadata_schema import calculate_days_since_deployment
import utils.health_thresholds as ht

logger = logging.getLogger(__name__)

dc2s_api = Blueprint('dc2s_api', __name__)


def _filter_user_accounts(accounts_data, key='account_id'):
    """Filter account data by current user's allowed_account_ids.
    Works with both list-of-dicts and list-of-Account-objects.
    """
    try:
        from flask_login import current_user
        user_restrictions = getattr(current_user, 'allowed_account_ids', None)
        if user_restrictions is None:
            return accounts_data
        allowed = set(int(x) for x in user_restrictions)
        result = []
        for item in accounts_data:
            acct_id = item.get(key) if isinstance(item, dict) else getattr(item, key, None)
            if acct_id is not None and int(acct_id) in allowed:
                result.append(item)
        return result
    except Exception:
        return accounts_data

def _normalize_kpi_code_for_health(kpi_code):
    """Validate kpi_code exists in the catalog. Returns kpi_code or None."""
    return kpi_code if kpi_code in DC2S_KPIS else None


def _record_action_economics(
    customer_id, account_id, execution_id, playbook_id, playbook_name,
    total_hours, steps, kpi_before, kpi_after, health_before, health_after,
    started_at, completed_at,
):
    """
    Record ActionEconomics when a playbook completes — the Playbook Economic Bridge.
    Connects actual execution costs to Power-of-1 metrics for traceable ROI.
    """
    import json as _json
    import os

    # Playbook → Power-of-1 metric mapping
    PB_METRIC_MAP = {
        'PB-01': 'TTFV', 'PB-02': 'ticket_resolution_time',
        'PB-03': 'product_adoption', 'PB-04': 'expansion_rate',
        'PB-05': 'GRR', 'PB-06': 'expansion_rate',
    }

    # Load resource rates
    rates_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'resource_rates.json')
    try:
        with open(rates_path) as f:
            rates = _json.load(f)
        role_rates = {k: v['hourly_rate'] for k, v in rates.get('roles', {}).items()}
    except Exception:
        role_rates = {'csm': 95, 'cs_ops': 85, 'product': 110, 'platform': 120, 'leadership': 150}

    # Estimate role-hour split from playbook config
    pb_cfg = get_playbook_config(playbook_id)
    sub_components = (pb_cfg or {}).get('sub_components', [])
    total_cfg_hours = sum(sc.get('estimated_hours', 0) for sc in sub_components) or total_hours

    # Default role split: 40% CSM, 30% CS Ops, 15% Platform, 10% Product, 5% Leadership
    csm_hours = round(total_hours * 0.40, 2)
    cs_ops_hours = round(total_hours * 0.30, 2)
    platform_hours = round(total_hours * 0.15, 2)
    product_hours = round(total_hours * 0.10, 2)
    leadership_hours = round(total_hours * 0.05, 2)

    # Calculate costs
    cs_initiative_cost = round(
        csm_hours * role_rates.get('csm', 95)
        + cs_ops_hours * role_rates.get('cs_ops', 85)
        + leadership_hours * role_rates.get('leadership', 150),
        2
    )
    platform_cost = round(
        platform_hours * role_rates.get('platform', 120)
        + product_hours * role_rates.get('product', 110),
        2
    )
    total_cost = round(cs_initiative_cost + platform_cost, 2)

    # KPI deltas
    kpi_deltas = {}
    for code in kpi_before:
        if code in kpi_after and kpi_before[code] and kpi_after[code]:
            try:
                kpi_deltas[code] = round(float(kpi_after[code]) - float(kpi_before[code]), 4)
            except (TypeError, ValueError):
                pass

    # Health improvement as percentage
    improvement_pct = round(health_after - health_before, 2) if health_before and health_after else 0

    # Dollar impact from Power-of-1 economics
    po1_metric = PB_METRIC_MAP.get(playbook_id, '')
    dollar_impact = 0
    if po1_metric and improvement_pct > 0:
        try:
            po1_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'power_of_1_economics.json')
            with open(po1_path) as f:
                po1 = _json.load(f)
            metric_data = po1.get('metrics', {}).get(po1_metric, {})
            impact_per_pct = metric_data.get('annual_impact_per_pct', 0)
            # Scale by account ARR vs baseline
            acct = Account.query.get(account_id)
            arr_scale = (float(acct.revenue) / 10_000_000) if acct and acct.revenue else 1
            dollar_impact = round(impact_per_pct * (improvement_pct / 100) * arr_scale, 2)
        except Exception:
            pass

    # ROI
    roi = round((dollar_impact / total_cost - 1), 4) if total_cost > 0 and dollar_impact > 0 else 0
    payback_days = round((total_cost / (dollar_impact / 365)), 0) if dollar_impact > 0 else 0

    ae = ActionEconomics(
        customer_id=customer_id,
        account_id=account_id,
        execution_id=execution_id,
        action_type='playbook_execution',
        action_id=playbook_id,
        action_name=playbook_name,
        csm_hours=csm_hours,
        cs_ops_hours=cs_ops_hours,
        product_hours=product_hours,
        platform_hours=platform_hours,
        leadership_hours=leadership_hours,
        cs_initiative_cost=cs_initiative_cost,
        platform_cost=platform_cost,
        total_action_cost=total_cost,
        kpi_before=kpi_before,
        kpi_after=kpi_after,
        kpi_deltas=kpi_deltas,
        power_of_1_metric=po1_metric,
        dollar_impact_annual=dollar_impact,
        dollar_impact_monthly=round(dollar_impact / 12, 2) if dollar_impact else 0,
        roi=roi,
        payback_days=int(payback_days),
        improvement_pct=improvement_pct,
        started_at=started_at,
        completed_at=completed_at,
    )
    db.session.add(ae)
    logger.info(f"ActionEconomics recorded: {playbook_id} on account {account_id}, cost=${total_cost}, impact=${dollar_impact}")


def get_precalculated_scores(account_id):
    """
    Fetch the latest pre-calculated health score and pillar scores.

    Returns (health_score, health_status, pillar_dict, measurement_month) or
    (None, None, None, None) if no pre-calculated scores exist.

    Wave 1 Workstream A (Aug 4 2026): delegates to the canonical service in
    utils/account_health.py — this was the 4-tuple member of a four-copy
    fan-out (the others return 3-tuples; that arity fork is why the shim
    keeps with_month=True here). New code: use get_account_health() directly.
    """
    try:
        from utils.account_health import get_precalculated_scores_tuple
        return get_precalculated_scores_tuple(account_id, with_month=True)
    except Exception as e:
        logger.debug(f"Could not fetch pre-calculated scores for account {account_id}: {e}")
        return None, None, None, None


def _sync_journey_phase(account):
    """
    Persist the current journey phase in Account.profile_metadata (DC vertical).
    Shared Account model has no journey_phase column; DC stores it in profile_metadata.
    """
    try:
        metadata = dict(account.profile_metadata or {})
        deployment_date = metadata.get("deployment_date", "")
        days = calculate_days_since_deployment(deployment_date) if deployment_date else 0
        account_data = {**metadata, "days_since_deployment": days}
        new_phase = determine_customer_phase(account_data)
        current = metadata.get("journey_phase")
        if current != new_phase:
            logger.info(
                "Account %s journey_phase %s -> %s",
                account.account_id, current, new_phase,
            )
            metadata["journey_phase"] = new_phase
            account.profile_metadata = metadata
            db.session.add(account)
            db.session.commit()
    except Exception as exc:
        logger.warning("Failed to sync journey_phase for account %s: %s", account.account_id, exc)
        db.session.rollback()


def _score_kpi_value(value, kpi_def):
    """
    Score a single KPI value using 4-band interpolation aligned to health thresholds.

    Bands (higher_is_better example):
      critical.min  → 0
      risk boundary → at_risk_min (50)
      target        → healthy_min (70)
      healthy.max   → 100

    This produces meaningful score differentiation instead of flat 100 for all
    values that merely meet their target.
    """
    target_raw = kpi_def.get('target', 100)
    if isinstance(target_raw, dict):
        target = target_raw.get('value', 100)
        operator = target_raw.get('operator', '>')
    else:
        target = target_raw
        operator = '>'

    ranges = kpi_def.get('ranges', {})
    higher_is_better = kpi_def.get('higher_is_better', operator in ('>', '>='))

    # Health threshold anchor points
    SCORE_AT_TARGET = ht.healthy_min()    # 70
    SCORE_AT_RISK   = ht.at_risk_min()    # 50

    if ranges and target:
        healthy_range = ranges.get('healthy', {})
        critical_range = ranges.get('critical', {})
        risk_range = ranges.get('risk', {})

        if higher_is_better:
            # Higher is better: critical low, healthy high
            floor = critical_range.get('min', 0)
            risk_boundary = risk_range.get('min', critical_range.get('max', floor))
            healthy_max = healthy_range.get('max', target * 1.2 if target else 100)

            if value <= floor:
                score = 0.0
            elif value < risk_boundary:
                # Critical zone: 0 → SCORE_AT_RISK
                span = risk_boundary - floor
                score = (SCORE_AT_RISK * (value - floor) / span) if span > 0 else 0.0
            elif value < target:
                # Risk zone: SCORE_AT_RISK → SCORE_AT_TARGET
                span = target - risk_boundary
                score = SCORE_AT_RISK + ((SCORE_AT_TARGET - SCORE_AT_RISK) * (value - risk_boundary) / span) if span > 0 else SCORE_AT_RISK
            elif value >= healthy_max:
                score = 100.0
            else:
                # Healthy zone: SCORE_AT_TARGET → 100
                span = healthy_max - target
                score = SCORE_AT_TARGET + ((100.0 - SCORE_AT_TARGET) * (value - target) / span) if span > 0 else 100.0
        else:
            # Lower is better: critical high, healthy low
            ceiling = critical_range.get('max', target * 4 if target else 100)
            risk_boundary = risk_range.get('max', critical_range.get('min', ceiling))
            healthy_min_val = healthy_range.get('min', 0)

            if value >= ceiling:
                score = 0.0
            elif value > risk_boundary:
                # Critical zone: 0 → SCORE_AT_RISK
                span = ceiling - risk_boundary
                score = (SCORE_AT_RISK * (ceiling - value) / span) if span > 0 else 0.0
            elif value > target:
                # Risk zone: SCORE_AT_RISK → SCORE_AT_TARGET
                span = risk_boundary - target
                score = SCORE_AT_RISK + ((SCORE_AT_TARGET - SCORE_AT_RISK) * (risk_boundary - value) / span) if span > 0 else SCORE_AT_RISK
            elif value <= healthy_min_val:
                score = 100.0
            else:
                # Healthy zone: SCORE_AT_TARGET → 100
                span = target - healthy_min_val
                score = SCORE_AT_TARGET + ((100.0 - SCORE_AT_TARGET) * (target - value) / span) if span > 0 else 100.0
    elif target and target > 0:
        # Fallback: simple ratio scoring (no range info)
        if operator in ('<', '<='):
            score = min(100, (target / max(value, 0.01)) * 100)
        else:
            score = min(100, (value / target) * 100)
    else:
        score = value

    return max(0.0, min(100.0, score))


# ============================================================
# TRAILING WEIGHTED AVERAGE — L1 KPI STABILIZER
# ============================================================

def _get_trailing_kpi_values(account_id, days=30):
    """
    Compute a trailing time-weighted average of KPI values for an account.

    Instead of using only the single most recent measurement, this queries
    the last ``days`` worth of data from dc2s_kpis and applies exponential
    time-decay weighting: more recent measurements count more.

    If the data is monthly (gaps > 20 days), it automatically expands the
    window to cover the last 3 measurement periods so there's enough data
    to average.

    Weight formula (exponential decay with half-life = ``days / 2``):
        w_i = exp(-ln(2) * age_days / half_life)

    Returns:
        dict[str, float]: {kpi_code: weighted_average_value}
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days)

    kpis = DC2SKPI.query.filter(
        DC2SKPI.account_id == account_id,
        DC2SKPI.measured_at >= cutoff,
    ).order_by(DC2SKPI.measured_at.desc()).all()

    # If fewer than 2 distinct timestamps in the window, widen it
    # (handles monthly data where a 30-day window may only catch 1 point)
    if kpis:
        distinct_times = set(k.measured_at for k in kpis)
        if len(distinct_times) < 2:
            # Expand to last 3 measurement periods (all data, take last 3 distinct)
            all_kpis = DC2SKPI.query.filter(
                DC2SKPI.account_id == account_id,
            ).order_by(DC2SKPI.measured_at.desc()).all()

            all_times = sorted(set(k.measured_at for k in all_kpis), reverse=True)
            if len(all_times) >= 2:
                third_time = all_times[min(2, len(all_times) - 1)]
                kpis = [k for k in all_kpis if k.measured_at >= third_time]
                # Recalculate cutoff for weight computation
                cutoff = third_time
    else:
        # No data in window — fall back to latest available
        kpis = DC2SKPI.query.filter(
            DC2SKPI.account_id == account_id,
        ).order_by(DC2SKPI.measured_at.desc()).all()
        if kpis:
            latest_time = kpis[0].measured_at
            return {k.kpi_code: float(k.value) for k in kpis if k.measured_at == latest_time}
        return {}

    if not kpis:
        return {}

    # Find the most recent timestamp for age calculation
    most_recent = max(k.measured_at for k in kpis)
    half_life = max(days / 2.0, 7.0)  # minimum 7-day half-life

    # Group by kpi_code and compute time-weighted average
    kpi_groups = defaultdict(list)
    for k in kpis:
        kpi_groups[k.kpi_code].append(k)

    trailing_values = {}
    for kpi_code, measurements in kpi_groups.items():
        weighted_sum = 0.0
        weight_sum = 0.0
        for m in measurements:
            age_days = (most_recent - m.measured_at).total_seconds() / 86400.0
            weight = math.exp(-math.log(2) * age_days / half_life)
            weighted_sum += float(m.value) * weight
            weight_sum += weight

        if weight_sum > 0:
            trailing_values[kpi_code] = weighted_sum / weight_sum
        else:
            trailing_values[kpi_code] = float(measurements[0].value)

    return trailing_values


def calculate_kpi_health(kpi_values, customer_id=None, vertical=None,
                         pillar_weight_overrides=None, kpi_weight_overrides=None):
    """
    Calculate health score from KPI values using config-aware weights when possible.
    Vertical-aware: uses the correct KPI catalog (DC2_S=38 KPIs, SaaS Premium=41 KPIs).
    When customer_id is provided, auto-detects vertical from CustomerConfig.
    Normalizes AI/CH/DV/EX/OS KPI codes to P1-P5 catalog codes (GAP 1.3).
    Only includes pillars that have non-zero weight in customer config (enabled pillars).

    Optional overrides (used by lifecycle-stage weight profiles):
        pillar_weight_overrides: dict of {pillar: weight} — overrides L2 weights
        kpi_weight_overrides: dict of {pillar: {kpi: weight}} — overrides L1 weights
    """
    from utils.vertical_registry import get_kpis, get_pillars, get_vertical_for_customer, normalize_vertical

    # Resolve vertical
    if vertical:
        resolved_vertical = normalize_vertical(vertical)
    elif customer_id is not None:
        resolved_vertical = get_vertical_for_customer(customer_id)
    else:
        resolved_vertical = 'dc2_s'

    # Load the correct KPI catalog and pillar definitions
    kpi_catalog = get_kpis(resolved_vertical)
    pillar_catalog = get_pillars(resolved_vertical)

    # Config-aware: use CustomerConfig.dc2s_pillar_weights when customer_id provided
    weights = get_weights_for_customer(customer_id) if customer_id is not None else get_current_weights()

    # Determine enabled pillars from customer config (pillars with explicit weight > 0)
    enabled_pillars = None
    if customer_id is not None:
        try:
            from models import CustomerConfig as CC
            cc = CC.query.filter_by(customer_id=int(customer_id)).first()
            if cc and cc.dc2s_pillar_weights:
                enabled_pillars = set(cc.dc2s_pillar_weights.keys())
        except Exception:
            pass

    # Normalize kpi codes (AI-KPI1 → P3-KPI1 etc.) so catalog lookup works
    kpi_values_for_calc = {}
    for kpi_code, value in kpi_values.items():
        lookup_code = _normalize_kpi_code_for_health(kpi_code)
        if lookup_code:
            kpi_values_for_calc[lookup_code] = value
    kpi_values = kpi_values_for_calc

    # Group KPIs by pillar using L1 weighted average (not simple average)
    pillar_scores = {}

    for kpi_code, value in kpi_values.items():
        if kpi_code not in kpi_catalog:
            continue

        kpi_def = kpi_catalog[kpi_code]
        pillar = kpi_def.get('pillar', kpi_def.get('l1_category'))

        # Skip KPIs from disabled pillars
        if enabled_pillars is not None and pillar not in enabled_pillars:
            continue

        if pillar not in pillar_scores:
            pillar_scores[pillar] = {'weighted_sum': 0, 'total_weight': 0}

        # 4-band scoring: critical→0, risk→50, target→70, healthy_max→100
        score = _score_kpi_value(value, kpi_def)

        # Use L1 weight: lifecycle override → KPI definition → equal weight fallback
        l1_weight = None
        if kpi_weight_overrides and pillar in kpi_weight_overrides:
            l1_weight = kpi_weight_overrides[pillar].get(kpi_code)
        if not l1_weight:
            l1_weight = kpi_def.get('weight_l1', 0)
        if not l1_weight or l1_weight <= 0:
            l1_weight = 1.0  # equal weight fallback

        pillar_scores[pillar]['weighted_sum'] += score * l1_weight
        pillar_scores[pillar]['total_weight'] += l1_weight

    # Calculate pillar weighted averages (clamped to 0-100)
    pillar_averages = {}
    for pillar, data in pillar_scores.items():
        if data['total_weight'] > 0:
            avg = data['weighted_sum'] / data['total_weight']
        else:
            avg = 0
        pillar_averages[pillar] = max(0.0, min(100.0, avg))

    # Calculate overall weighted health (only enabled pillars)
    overall_health = 0
    total_weight = 0

    for pillar, score in pillar_averages.items():
        # L2 weight: lifecycle override → CustomerConfig → catalog weight_l2
        if pillar_weight_overrides and pillar in pillar_weight_overrides:
            weight = pillar_weight_overrides[pillar]
        else:
            pillar_data = weights.get(pillar, {})
            weight = pillar_data.get('weight', pillar_catalog.get(pillar, {}).get('weight_l2', 0.2))
        overall_health += score * weight
        total_weight += weight

    if total_weight > 0:
        overall_health = overall_health / total_weight

    # Clamp final health score to 0-100
    overall_health = max(0.0, min(100.0, overall_health))

    return overall_health, pillar_averages


@dc2s_api.route('/accounts', methods=['GET'])
def get_dc2s_accounts():
    """
    Get all DC2_S accounts for current user's customer
    GET /api/dc2s/accounts
    """
    try:
        customer_id = get_current_customer_id()
        
        logger.info(f"[DEBUG /api/dc2s/accounts] customer_id: {customer_id}")
        
        if not customer_id:
            logger.error("[DEBUG /api/dc2s/accounts] No customer_id found!")
            return jsonify({'error': 'Customer ID required'}), 400
        
        # Get all DC2_S accounts for this customer
        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
        ).all()
        
        logger.info(f"[DEBUG /api/dc2s/accounts] Found {len(accounts)} accounts for customer {customer_id}")
        if accounts:
            logger.info(f"[DEBUG /api/dc2s/accounts] Account IDs: {[a.account_id for a in accounts[:5]]}")
        
        # Determine enabled pillars from customer config (once per request)
        enabled_pillar_codes = list(DC2S_PILLARS.keys())  # default: all
        try:
            cc = CustomerConfig.query.filter_by(customer_id=int(customer_id)).first()
            if cc and cc.dc2s_pillar_weights:
                enabled_pillar_codes = list(cc.dc2s_pillar_weights.keys())
        except Exception:
            pass

        results = []
        for account in accounts:
            # Prefer pre-calculated scores from HealthScore/PillarScore tables
            # (single source of truth, populated by the score calculator).
            # Fall back to on-the-fly calculation only when no scores exist.
            precalc_health, precalc_status, precalc_pillars, precalc_month = get_precalculated_scores(account.account_id)

            if precalc_health is not None and precalc_pillars:
                overall_health = precalc_health
                pillar_scores = precalc_pillars
                status = precalc_status
            else:
                # Fallback: on-the-fly calculation from trailing KPI values
                trailing_kpis = _get_trailing_kpi_values(account.account_id, days=30)
                overall_health, pillar_scores = calculate_kpi_health(trailing_kpis, customer_id=customer_id)
                status = ht.classify(overall_health)

            # Also get latest timestamp for metadata
            latest_row = DC2SKPI.query.filter_by(
                account_id=account.account_id
            ).order_by(DC2SKPI.measured_at.desc()).first()
            latest_time = latest_row.measured_at if latest_row else None

            # Phase 0.2: persist journey_phase on every health recalculation
            _sync_journey_phase(account)

            # Extract useful fields from profile_metadata for frontend
            meta = account.profile_metadata or {}
            renewal_date = meta.get('renewal_date') or meta.get('contract_renewal_date')
            last_contact = meta.get('last_contact') or meta.get('last_engagement_date')
            csm_name = meta.get('assigned_csm') or meta.get('csm_name')
            champion_name = meta.get('primary_champion_name')
            champion_title = meta.get('primary_champion_title')
            products = meta.get('products', [])

            results.append({
                'account_id': account.account_id,
                'customer_id': account.customer_id,
                'account_name': account.account_name,
                'industry': account.industry,
                'region': account.region,
                'revenue': float(account.revenue) if account.revenue else 0,
                'overall_health': round(overall_health, 1),
                'health_score': round(overall_health, 1),
                'status': status,
                'classification': status,
                'pillar_scores': {k: round(v, 1) for k, v in pillar_scores.items()},
                'enabled_pillars': enabled_pillar_codes,
                'metadata': meta,
                'kpi_count': len(pillar_scores) * 3 if precalc_health is not None else 15,  # approximate
                'last_measured': latest_time.isoformat() if latest_time else None,
                'renewal_date': renewal_date,
                'last_contact': last_contact,
                'csm_name': csm_name,
                'champion_name': champion_name,
                'champion_title': champion_title,
                'products': products,
                'arr': float(account.revenue) if account.revenue else 0,
                'kanban_column': meta.get('kanban_column'),
                'health_as_of': precalc_month.strftime('%Y-%m') if precalc_month else None,
            })

        # Apply user-level account filtering (contractors/restricted users)
        results = _filter_user_accounts(results, key='account_id')

        # Include customer context for top-bar resolution (super admin sessions)
        from models import Customer as _Cust
        _cust = _Cust.query.filter_by(customer_id=int(customer_id)).first()
        return jsonify({
            'accounts': results,
            'total': len(results),
            'enabled_pillars': enabled_pillar_codes,
            'customer_id': int(customer_id),
            'customer_name': _cust.customer_name if _cust else f'Customer {customer_id}',
        })

    except Exception as e:
        logger.error(f"Error fetching DC2_S accounts: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch accounts'}), 500


@dc2s_api.route('/accounts/<int:account_id>', methods=['GET'])
def get_dc2s_account_detail(account_id):
    """
    Get detailed information for a specific DC2_S account
    GET /api/dc2s/accounts/123
    """
    try:
        customer_id = get_current_customer_id()
        
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400
        
        # Get account
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=int(customer_id),
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Trailing 30-day weighted average for stable health scores
        trailing_kpis = _get_trailing_kpi_values(account_id, days=30)

        # Also get latest timestamp for metadata
        latest_row = DC2SKPI.query.filter_by(
            account_id=account_id
        ).order_by(DC2SKPI.measured_at.desc()).first()

        # Calculate health (config-aware: uses CustomerConfig.dc2s_pillar_weights when set)
        overall_health, pillar_scores = calculate_kpi_health(trailing_kpis, customer_id=customer_id)

        # Phase 0.2: persist journey_phase on every health recalculation
        _sync_journey_phase(account)

        # Group KPIs by pillar (use trailing averaged values)
        kpis_by_pillar = {}
        for kpi_code, value in trailing_kpis.items():
            if kpi_code in DC2S_KPIS:
                kpi_def = DC2S_KPIS[kpi_code]
                pillar = kpi_def.get('pillar', kpi_def.get('l1_category', 'Unknown'))

                if pillar not in kpis_by_pillar:
                    kpis_by_pillar[pillar] = []

                # Extract target value
                target_raw = kpi_def.get('target')
                if isinstance(target_raw, dict):
                    target_value = target_raw.get('value')
                else:
                    target_value = target_raw

                kpis_by_pillar[pillar].append({
                    'code': kpi_code,
                    'name': kpi_def.get('name', kpi_def.get('kpi_name', kpi_code)),
                    'value': round(value, 2),
                    'target': target_value,
                    'unit': kpi_def.get('unit', ''),
                })

        return jsonify({
            'account_id': account.account_id,
            'account_name': account.account_name,
            'industry': account.industry,
            'region': account.region,
            'vertical': account.vertical,
            'revenue': float(account.revenue) if account.revenue else 0,
            'overall_health': round(overall_health, 1),
            'pillar_scores': {k: round(v, 1) for k, v in pillar_scores.items()},
            'kpis_by_pillar': kpis_by_pillar,
            'metadata': account.profile_metadata or {},
            'total_kpis': len(trailing_kpis),
            'last_measured': latest_row.measured_at.isoformat() if latest_row else None
        })
        
    except Exception as e:
        logger.error(f"Error fetching DC2_S account detail: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch account details'}), 500


@dc2s_api.route('/kpis', methods=['GET'])
def get_dc2s_kpi_definitions():
    """
    Get DC2_S KPI definitions (config-aware: uses CustomerConfig.dc2s_pillar_weights when set).
    GET /api/dc2s/kpis
    """
    try:
        customer_id = get_current_customer_id()
        weights = get_weights_for_customer(customer_id)
        
        return jsonify({
            'kpis': DC2S_KPIS,
            'pillars': DC2S_PILLARS,
            'weights': weights,
            'total_kpis': len(DC2S_KPIS)
        })
        
    except Exception as e:
        logger.error(f"Error fetching DC2_S KPI definitions: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch KPI definitions'}), 500


@dc2s_api.route('/accounts/<int:account_id>/kpis', methods=['GET'])
def get_dc2s_account_kpis(account_id):
    """
    Get KPIs for a specific account in SaaS-compatible format
    GET /api/dc2s/accounts/123/kpis
    """
    try:
        customer_id = get_current_customer_id()
        
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400
        
        # Verify account belongs to customer
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=int(customer_id),
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Get all KPIs for this account, then get latest per kpi_code
        all_kpis = DC2SKPI.query.filter_by(
            account_id=account_id
        ).order_by(DC2SKPI.measured_at.desc()).all()
        
        # Group by kpi_code, keeping latest
        latest_kpis = {}
        for kpi in all_kpis:
            if kpi.kpi_code not in latest_kpis:
                latest_kpis[kpi.kpi_code] = kpi
        
        # Transform to SaaS-compatible format with unit, target, status
        # Normalize kpi_code (AI-KPI1 → P3-KPI1) so catalog lookup returns correct pillar P1-P5
        result_kpis = []
        for kpi_code, kpi in latest_kpis.items():
            lookup_code = _normalize_kpi_code_for_health(kpi_code) or kpi_code
            kpi_def = DC2S_KPIS.get(lookup_code, {})
            kpi_name = kpi_def.get('name', kpi_def.get('kpi_name', kpi_code))
            pillar = kpi_def.get('pillar', kpi_def.get('l1_category', 'Uncategorized'))
            
            # Extract target value
            target_raw = kpi_def.get('target')
            if isinstance(target_raw, dict):
                target_value = target_raw.get('value')
                operator = target_raw.get('operator', '>')
            else:
                target_value = target_raw
                operator = '>'
            
            # Calculate status based on value vs target
            status = None
            if target_value is not None:
                value_float = float(kpi.value)
                target_float = float(target_value)
                
                if operator == '<':
                    # Lower is better
                    percentage = (target_float / max(value_float, 0.01)) * 100
                else:
                    # Higher is better (default)
                    percentage = (value_float / target_float) * 100 if target_float > 0 else 0
                
                if percentage >= 90:
                    status = 'healthy'
                elif percentage >= 70:
                    status = 'at_risk'
                else:
                    status = 'critical'
            
            result_kpis.append({
                'kpi_id': kpi.kpi_id,
                'account_id': account_id,
                'account_name': account.account_name,
                'kpi_code': kpi_code,
                'kpi_parameter': kpi_name,
                'category': pillar,
                'pillar': pillar,
                'value': float(kpi.value),
                'data': str(kpi.value),  # String format for compatibility
                'target': float(target_value) if target_value else None,
                'unit': kpi_def.get('unit', ''),
                'weight': float(kpi.weight) if kpi.weight else None,
                'status': status,
                'measured_at': kpi.measured_at.isoformat() if kpi.measured_at else None,
                'impact_level': kpi_def.get('impact_level', 'Medium'),
                'measurement_frequency': kpi_def.get('frequency', 'Monthly'),
            })
        
        return jsonify({
            'account_id': account_id,
            'account_name': account.account_name,
            'kpis': result_kpis,
            'total': len(result_kpis)
        })
        
    except Exception as e:
        logger.error(f"Error fetching DC2_S account KPIs: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch KPIs'}), 500


@dc2s_api.route('/kpis/all', methods=['GET'])
def get_all_dc2s_kpis():
    """
    Get all DC2_S KPIs for all accounts (similar to /api/kpis/customer/all for SaaS)
    Returns KPIs in a format compatible with SaaS KPI structure for UI consistency
    GET /api/dc2s/kpis/all
    """
    try:
        customer_id = get_current_customer_id()
        
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400
        
        # Get all DC2_S accounts for this customer
        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
        ).all()
        
        account_dict = {acc.account_id: acc for acc in accounts}
        
        # Get all KPIs for these accounts
        account_ids = [acc.account_id for acc in accounts]
        if not account_ids:
            return jsonify([])
        
        # Get latest KPIs for each account (by measured_at)
        all_kpis = DC2SKPI.query.filter(
            DC2SKPI.account_id.in_(account_ids)
        ).order_by(DC2SKPI.measured_at.desc()).all()
        
        # Group by account_id and kpi_code, keeping only the latest
        latest_kpis = {}
        for kpi in all_kpis:
            key = (kpi.account_id, kpi.kpi_code)
            if key not in latest_kpis:
                latest_kpis[key] = kpi
            else:
                # Keep the one with the latest measured_at
                if kpi.measured_at > latest_kpis[key].measured_at:
                    latest_kpis[key] = kpi
        
        # Transform to SaaS-compatible format
        result = []
        for (account_id, kpi_code), kpi in latest_kpis.items():
            account = account_dict.get(account_id)
            if not account:
                continue

            # Get KPI definition — normalize code (AI-KPI1 → P3-KPI1) for catalog lookup
            lookup_code = _normalize_kpi_code_for_health(kpi_code) or kpi_code
            kpi_def = DC2S_KPIS.get(lookup_code, {})
            kpi_name = kpi_def.get('name', kpi_def.get('kpi_name', kpi_code))
            pillar = kpi_def.get('pillar', kpi_def.get('l1_category', 'Uncategorized'))
            
            # Extract target value
            target_raw = kpi_def.get('target')
            if isinstance(target_raw, dict):
                target_value = target_raw.get('value')
            else:
                target_value = target_raw
            
            result.append({
                'kpi_id': kpi.kpi_id,
                'account_id': account_id,
                'account_name': account.account_name,
                'account_revenue': float(account.revenue) if account.revenue else 0,
                'account_industry': account.industry or 'Unknown',
                'account_region': account.region or 'Unknown',
                'product_id': None,  # DC KPIs are account-level only
                'product_name': None,
                'aggregation_type': None,
                'category': pillar,  # Use pillar as category
                'row_index': None,
                'health_score_component': None,
                'weight': float(kpi.weight) if kpi.weight else None,
                'data': str(kpi.value),  # Convert to string to match SaaS format
                'source_review': 'System',
                'kpi_parameter': kpi_name,  # Use KPI name as parameter
                'impact_level': kpi_def.get('impact_level', 'Medium'),
                'measurement_frequency': kpi_def.get('frequency', 'Monthly'),
                'last_edited_by': None,
                'last_edited_at': kpi.measured_at.isoformat() if kpi.measured_at else None,
                'upload_id': None,
                'upload_filename': None,
                # DC-specific fields
                'kpi_code': kpi_code,
                'target': float(target_value) if target_value else None,
                'pillar': pillar,
                'unit': kpi_def.get('unit', ''),
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error fetching all DC2_S KPIs: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch KPIs'}), 500


@dc2s_api.route('/accounts/<int:account_id>/kpis/timeseries', methods=['GET'])
def get_dc2s_kpi_timeseries(account_id):
    """
    Get KPI time-series data for a specific account.
    Returns KPI values aggregated by week for charting.
    GET /api/dc2s/accounts/123/kpis/timeseries?range=30d&kpi_code=AI-KPI1

    Query params:
        range: '7d', '30d', '90d', '180d' (default: '30d')
        kpi_code: Optional specific KPI code to filter (default: all)
        granularity: 'daily', 'weekly', 'monthly' (default: 'weekly')
    """
    try:
        customer_id = get_current_customer_id()

        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        # Verify account belongs to customer
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=int(customer_id),
        ).first()

        if not account:
            return jsonify({'error': 'Account not found'}), 404

        from sqlalchemy import func, extract
        from datetime import datetime, timedelta

        # Parse range
        range_param = request.args.get('range', '30d')
        range_days = {'7d': 7, '30d': 30, '90d': 90, '180d': 180}.get(range_param, 30)
        kpi_code_filter = request.args.get('kpi_code')
        granularity = request.args.get('granularity', 'weekly')

        cutoff_date = datetime.utcnow() - timedelta(days=range_days * 365)  # Sim dates may be in past
        # For simulated data, find the actual date range in db
        date_range_q = db.session.query(
            func.min(DC2SKPI.measured_at),
            func.max(DC2SKPI.measured_at)
        ).filter(DC2SKPI.account_id == account_id)
        if kpi_code_filter:
            date_range_q = date_range_q.filter(DC2SKPI.kpi_code == kpi_code_filter)
        date_range = date_range_q.first()

        if not date_range or not date_range[0]:
            return jsonify({'account_id': account_id, 'timeseries': [], 'total': 0})

        min_date, max_date = date_range
        # Use actual date range from data, limited by range_days
        actual_cutoff = max_date - timedelta(days=range_days)
        if actual_cutoff < min_date:
            actual_cutoff = min_date

        # Build the query
        query = DC2SKPI.query.filter(
            DC2SKPI.account_id == account_id,
            DC2SKPI.measured_at >= actual_cutoff
        )
        if kpi_code_filter:
            query = query.filter(DC2SKPI.kpi_code == kpi_code_filter)

        all_kpis = query.order_by(DC2SKPI.measured_at.asc()).all()

        if granularity == 'daily':
            # Group by date
            grouped = defaultdict(lambda: defaultdict(list))
            for kpi in all_kpis:
                day_key = kpi.measured_at.strftime('%Y-%m-%d')
                grouped[day_key][kpi.kpi_code].append(float(kpi.value))
        elif granularity == 'monthly':
            # Group by month
            grouped = defaultdict(lambda: defaultdict(list))
            for kpi in all_kpis:
                month_key = kpi.measured_at.strftime('%Y-%m')
                grouped[month_key][kpi.kpi_code].append(float(kpi.value))
        else:
            # Weekly (default) — group by ISO week
            grouped = defaultdict(lambda: defaultdict(list))
            for kpi in all_kpis:
                week_key = kpi.measured_at.strftime('%Y-W%W')
                grouped[week_key][kpi.kpi_code].append(float(kpi.value))

        # Build timeseries result
        timeseries = []
        for period_key in sorted(grouped.keys()):
            period_data = {'period': period_key}
            for kpi_code, values in grouped[period_key].items():
                avg_val = sum(values) / len(values)
                # Normalize code for name lookup
                lookup_code = _normalize_kpi_code_for_health(kpi_code) or kpi_code
                kpi_def = DC2S_KPIS.get(lookup_code, {})
                target_raw = kpi_def.get('target')
                if isinstance(target_raw, dict):
                    target_value = target_raw.get('value')
                else:
                    target_value = target_raw

                period_data[kpi_code] = {
                    'value': round(avg_val, 2),
                    'count': len(values),
                    'min': round(min(values), 2),
                    'max': round(max(values), 2),
                    'target': float(target_value) if target_value else None,
                    'name': kpi_def.get('name', kpi_code),
                    'pillar': kpi_def.get('pillar', 'Unknown'),
                }
            timeseries.append(period_data)

        # Also return KPI summary for chart legend
        kpi_summary = {}
        for kpi_code in set(k.kpi_code for k in all_kpis):
            lookup_code = _normalize_kpi_code_for_health(kpi_code) or kpi_code
            kpi_def = DC2S_KPIS.get(lookup_code, {})
            target_raw = kpi_def.get('target')
            if isinstance(target_raw, dict):
                target_value = target_raw.get('value')
            else:
                target_value = target_raw
            kpi_summary[kpi_code] = {
                'name': kpi_def.get('name', kpi_code),
                'pillar': kpi_def.get('pillar', 'Unknown'),
                'unit': kpi_def.get('unit', ''),
                'target': float(target_value) if target_value else None,
            }

        return jsonify({
            'account_id': account_id,
            'account_name': account.account_name,
            'range': range_param,
            'granularity': granularity,
            'date_range': {
                'from': actual_cutoff.isoformat(),
                'to': max_date.isoformat(),
            },
            'kpi_summary': kpi_summary,
            'timeseries': timeseries,
            'total': len(timeseries),
        })

    except Exception as e:
        logger.error(f"Error fetching DC2_S KPI timeseries: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch KPI timeseries'}), 500


@dc2s_api.route('/alerts/<int:account_id>', methods=['GET'])
def get_dc2s_alerts(account_id):
    """
    Get alerts for a specific DC2_S account based on KPI status
    GET /api/dc2s/alerts/123
    """
    try:
        customer_id = get_current_customer_id()
        
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400
        
        # Verify account belongs to customer
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=int(customer_id),
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Get latest KPIs for this account
        all_kpis = DC2SKPI.query.filter_by(
            account_id=account_id
        ).order_by(DC2SKPI.measured_at.desc()).all()
        
        # Group by kpi_code, keeping latest
        latest_kpis = {}
        for kpi in all_kpis:
            if kpi.kpi_code not in latest_kpis:
                latest_kpis[kpi.kpi_code] = kpi
        
        # Generate alerts based on KPI status
        alerts = []
        for kpi_code, kpi in latest_kpis.items():
            kpi_def = DC2S_KPIS.get(kpi_code, {})
            kpi_name = kpi_def.get('name', kpi_def.get('kpi_name', kpi_code))
            
            # Extract target value
            target_raw = kpi_def.get('target')
            if isinstance(target_raw, dict):
                target_value = target_raw.get('value')
                operator = target_raw.get('operator', '>')
            else:
                target_value = target_raw
                operator = '>'
            
            # Calculate status and generate alerts for at_risk and critical
            if target_value is not None:
                value_float = float(kpi.value)
                target_float = float(target_value)
                
                if operator == '<':
                    # Lower is better
                    percentage = (target_float / max(value_float, 0.01)) * 100
                else:
                    # Higher is better (default)
                    percentage = (value_float / target_float) * 100 if target_float > 0 else 0
                
                status = None
                severity = None
                message = None
                
                if percentage >= 90:
                    status = 'healthy'
                elif percentage >= 70:
                    status = 'at_risk'
                    severity = 'warning'
                    message = f"{kpi_name} is below target ({(percentage/100*100):.1f}% of target). Value: {value_float}, Target: {target_float}"
                else:
                    status = 'critical'
                    severity = 'critical'
                    message = f"{kpi_name} is critically below target ({(percentage/100*100):.1f}% of target). Value: {value_float}, Target: {target_float}"
                
                # Only create alerts for at_risk and critical
                if severity:
                    alerts.append({
                        'alert_id': f'{account_id}-{kpi_code}',
                        'kpi_id': str(kpi.kpi_id),
                        'kpi_code': kpi_code,
                        'kpi_name': kpi_name,
                        'severity': severity,
                        'message': message,
                        'timestamp': kpi.measured_at.isoformat() if kpi.measured_at else datetime.utcnow().isoformat(),
                        'value': float(kpi.value),
                        'target': float(target_value),
                        'percentage': round(percentage, 1)
                    })
        
        # Also fetch context graph signals for this account
        signals = []
        try:
            from models import ContextNode
            cg_signals = ContextNode.query.filter(
                ContextNode.customer_id == int(customer_id),
                ContextNode.account_id == account_id,
                ContextNode.node_type == 'SIGNAL',
            ).order_by(ContextNode.occurred_at.desc()).limit(20).all()
            for s in cg_signals:
                signals.append({
                    'id': s.node_id,
                    'date': s.occurred_at.isoformat() if s.occurred_at else None,
                    'type': s.node_subtype or 'signal',
                    'subtype': s.node_subtype,
                    'title': s.title or f'{s.node_subtype or "Signal"} detected',
                    'description': (s.properties or {}).get('description', s.title or ''),
                    'severity': 'critical' if s.tier == 1 else 'warning' if s.tier == 2 else 'info',
                })
        except Exception as sig_err:
            logger.warning(f"Could not fetch context graph signals: {sig_err}")

        # Also build stakeholders and tickets from context graph
        stakeholders = []
        try:
            from models import ContextNode as CN2
            cg_stakeholders = CN2.query.filter(
                CN2.customer_id == int(customer_id),
                CN2.account_id == account_id,
                CN2.node_type == 'STAKEHOLDER',
            ).limit(10).all()
            for st in cg_stakeholders:
                props = st.properties or {}
                stakeholders.append({
                    'id': st.node_id,
                    'name': st.title or props.get('name', 'Unknown'),
                    'role': props.get('role', props.get('stakeholder_role', '')),
                    'influence_score': props.get('influence_score'),
                    'engagement_level': props.get('engagement_level', ''),
                })
        except Exception:
            pass

        return jsonify({
            'account_id': account_id,
            'account_name': account.account_name,
            'alerts': alerts,
            'signals': signals,
            'stakeholders': stakeholders,
            'tickets': [],
            'total': len(alerts)
        })

    except Exception as e:
        logger.error(f"Error fetching DC2_S alerts: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch alerts'}), 500


@dc2s_api.route('/recommendations/<int:account_id>', methods=['GET'])
def get_dc2s_recommendations(account_id):
    """
    Get playbook recommendations for a specific DC2_S account.
    Phase 0.3: Uses real trigger conditions from PLAYBOOK_CONFIG + journey phase
    instead of the old proxy pillar-to-playbook mapping.
    GET /api/dc2s/recommendations/123
    """
    try:
        customer_id = get_current_customer_id()

        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        # Verify account belongs to customer
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=int(customer_id),
        ).first()

        if not account:
            return jsonify({'error': 'Account not found'}), 404

        # Get latest KPIs for this account
        all_kpis = DC2SKPI.query.filter_by(
            account_id=account_id
        ).order_by(DC2SKPI.measured_at.desc()).all()

        # Group by kpi_code, keeping latest
        latest_kpis_raw = {}
        for kpi in all_kpis:
            if kpi.kpi_code not in latest_kpis_raw:
                latest_kpis_raw[kpi.kpi_code] = kpi

        # Build a kpi_code->value dict using *catalog* codes (P1-KPI1 etc.)
        kpi_values = {}
        for kpi_code, kpi in latest_kpis_raw.items():
            catalog_code = _normalize_kpi_code_for_health(kpi_code) or kpi_code
            kpi_values[catalog_code] = float(kpi.value)

        # Also compute overall health so we can pass it as "OVERALL_HEALTH"
        overall_health, _ = calculate_kpi_health(
            {k: float(v.value) for k, v in latest_kpis_raw.items()},
            customer_id=customer_id,
        )
        kpi_values["OVERALL_HEALTH"] = overall_health

        # Determine current journey phase (stored in profile_metadata for DC)
        _sync_journey_phase(account)
        current_phase = (account.profile_metadata or {}).get("journey_phase") or "deployment"

        # ---- Real trigger evaluation against PLAYBOOK_CONFIG ----
        recommendations = []
        for pb_id, pb_cfg in PLAYBOOK_CONFIG.items():
            # Only recommend playbooks valid for the current phase
            if current_phase not in pb_cfg.get("phases", []):
                continue

            if should_trigger_playbook(pb_id, kpi_values):
                # Build human-readable action items from breached conditions
                action_items = []
                for trigger_kpi, condition in pb_cfg.get("trigger_conditions", {}).items():
                    if trigger_kpi in kpi_values:
                        action_items.append(
                            f"{trigger_kpi}: current {kpi_values[trigger_kpi]:.1f} "
                            f"(threshold {condition['operator']} {condition['value']})"
                        )

                # Assign priority: critical (0-50), at-risk/high (50-80), healthy/medium (80-100)
                if overall_health < 50:
                    priority = "critical"
                elif pb_cfg.get("human_approval_required"):
                    priority = "high"
                elif overall_health < 80:
                    priority = "high"
                else:
                    priority = "medium"

                recommendations.append({
                    "recommendation_id": f"{account_id}-{pb_id}",
                    "playbook_id": pb_id,
                    "playbook_name": pb_cfg["name"],
                    "description": pb_cfg["description"],
                    "priority": priority,
                    "estimated_impact": pb_cfg.get("estimated_impact", ""),
                    "automation_level": pb_cfg.get("automation_level", "medium"),
                    "requires_approval": pb_cfg.get("human_approval_required", False),
                    "action_items": action_items or [f"Review {pb_cfg['name']} triggers"],
                    "phase": current_phase,
                })

        # Sort by priority (critical > high > medium > low)
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 4))

        return jsonify({
            "account_id": account_id,
            "account_name": account.account_name,
            "journey_phase": current_phase,
            "overall_health": round(overall_health, 1),
            "recommendations": recommendations,
            "total": len(recommendations),
        })

    except Exception as e:
        logger.error(f"Error fetching DC2_S recommendations: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch recommendations"}), 500


@dc2s_api.route('/health-score/<int:account_id>', methods=['GET'])
def get_dc2s_health_score(account_id):
    """
    Get health score for a specific DC2_S account
    GET /api/dc2s/health-score/123?month=aggregate
    """
    try:
        customer_id = get_current_customer_id()
        
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400
        
        # Verify account belongs to customer
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=int(customer_id),
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Get month parameter (for DC, we'll use 'aggregate' to show all KPIs)
        month = request.args.get('month', 'aggregate')
        is_aggregate = (month == 'aggregate')
        
        # Get all KPIs for this account
        all_kpis = DC2SKPI.query.filter_by(
            account_id=account_id
        ).order_by(DC2SKPI.measured_at.desc()).all()
        
        # Group by kpi_code, keeping latest (DC KPIs don't have monthly data like SaaS)
        latest_kpis = {}
        for kpi in all_kpis:
            if kpi.kpi_code not in latest_kpis:
                latest_kpis[kpi.kpi_code] = kpi
        
        # Convert to dict for calculate_kpi_health function
        kpi_values = {kpi_code: float(kpi.value) for kpi_code, kpi in latest_kpis.items()}
        
        # Calculate overall health score and pillar scores (config-aware)
        overall_health, pillar_scores = calculate_kpi_health(kpi_values, customer_id=customer_id)

        # Phase 0.2: persist journey_phase on every health recalculation
        _sync_journey_phase(account)

        health_status = ht.classify(overall_health)
        
        # Format category scores for frontend
        category_scores = {}
        for pillar, score in pillar_scores.items():
            category_scores[pillar] = {
                'score': score,
                'weight': get_weights_for_customer(customer_id).get(pillar, {}).get('weight', 0.2)
            }
        
        return jsonify({
            'account_id': account_id,
            'account_name': account.account_name,
            'overall_score': round(overall_health, 2),
            'health_status': health_status,
            'category_scores': category_scores,
            'kpi_count': len(latest_kpis),
            'month': month if not is_aggregate else None,
            'is_aggregate': is_aggregate,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching DC2_S health score: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch health score'}), 500


@dc2s_api.route('/health-summary', methods=['GET'])
def get_dc2s_health_summary():
    """
    Get health summary across all DC2_S accounts for current customer
    GET /api/dc2s/health-summary
    """
    try:
        customer_id = get_current_customer_id()
        
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400
        
        # Get all DC2_S accounts
        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
        ).all()

        # Apply user-level account filtering (contractors/restricted users)
        accounts = _filter_user_accounts(accounts, key='account_id')

        account_health = []  # list of (health_score, revenue)
        healthy_count = 0
        risk_count = 0
        critical_count = 0

        for account in accounts:
            # Trailing 30-day weighted average for stable health scores
            trailing_kpis = _get_trailing_kpi_values(account.account_id, days=30)

            if trailing_kpis:
                health, _ = calculate_kpi_health(trailing_kpis, customer_id=customer_id)
                revenue = float(account.revenue) if account.revenue else 0
                account_health.append((health, revenue))

                if health >= ht.healthy_min():
                    healthy_count += 1
                elif health >= ht.at_risk_min():
                    risk_count += 1
                else:
                    critical_count += 1

        # L4: Revenue-weighted average of L3 account health scores
        total_revenue = sum(rev for _, rev in account_health)
        if total_revenue > 0:
            avg_health = sum(h * r for h, r in account_health) / total_revenue
        else:
            avg_health = sum(h for h, _ in account_health) / len(account_health) if account_health else 0

        # Also compute simple (unweighted) average for comparison
        simple_avg = (
            round(sum(h for h, _ in account_health) / len(account_health), 1)
            if account_health else 0
        )

        # ARR Exposure = total ARR sitting in at-risk/critical accounts
        arr_exposure = sum(
            rev for h, rev in account_health
            if h < ht.healthy_min()
        )

        return jsonify({
            'total_accounts': len(accounts),
            'average_health': round(avg_health, 1),
            'avg_health_simple': simple_avg,
            'health_avg_method': 'revenue_weighted' if total_revenue > 0 else 'simple',
            'health_avg_method_label': (
                'Revenue-weighted average' if total_revenue > 0
                else 'Simple average (no revenue data)'
            ),
            'healthy_accounts': healthy_count,
            'risk_accounts': risk_count,
            'critical_accounts': critical_count,
            'total_arr': round(total_revenue),
            'arr_exposure': round(arr_exposure, 2),
            'arr_exposure_label': 'Exposure (ARR in at-risk accounts)',
            'health_distribution': {
                'healthy': healthy_count,
                'risk': risk_count,
                'critical': critical_count
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching DC2_S health summary: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch health summary'}), 500


# ============================================================
# DC PLAYBOOK ENDPOINTS
# ============================================================

# NOTE: Old in-memory _dc_executions dict removed — all executions now use PlaybookExecutionV2 (DB-first)


@dc2s_api.route('/playbooks', methods=['GET'])
def get_dc2s_playbooks():
    """
    Get all 6 DC playbook definitions with sub-components and estimated hours.
    GET /api/dc2s/playbooks
    """
    try:
        playbooks = []
        for pb_id, pb_cfg in PLAYBOOK_CONFIG.items():
            total_hours = sum(s.get('estimated_hours', 0) for s in pb_cfg.get('sub_components', []))
            playbooks.append({
                'id': pb_id,
                'name': pb_cfg['name'],
                'description': pb_cfg['description'],
                'trigger_kpis': pb_cfg.get('trigger_kpis', []),
                'trigger_conditions': pb_cfg.get('trigger_conditions', {}),
                'automation_level': pb_cfg.get('automation_level', 'medium'),
                'human_approval_required': pb_cfg.get('human_approval_required', False),
                'estimated_impact': pb_cfg.get('estimated_impact', ''),
                'phases': pb_cfg.get('phases', []),
                'estimated_duration_days': pb_cfg.get('estimated_duration_days'),
                'estimated_duration_display': pb_cfg.get('estimated_duration_display', ''),
                'sub_components': pb_cfg.get('sub_components', []),
                'total_estimated_hours': total_hours,
            })
        return jsonify({'playbooks': playbooks, 'total': len(playbooks)})
    except Exception as e:
        logger.error(f"Error fetching DC playbooks: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch playbooks'}), 500


@dc2s_api.route('/playbooks/<playbook_id>', methods=['GET'])
def get_dc2s_playbook_detail(playbook_id):
    """
    Get a single DC playbook definition.
    GET /api/dc2s/playbooks/PB-01
    """
    try:
        pb_cfg = get_playbook_config(playbook_id)
        if not pb_cfg:
            return jsonify({'error': 'Playbook not found'}), 404
        total_hours = sum(s.get('estimated_hours', 0) for s in pb_cfg.get('sub_components', []))
        return jsonify({
            'id': pb_cfg['id'],
            'name': pb_cfg['name'],
            'description': pb_cfg['description'],
            'trigger_kpis': pb_cfg.get('trigger_kpis', []),
            'trigger_conditions': pb_cfg.get('trigger_conditions', {}),
            'automation_level': pb_cfg.get('automation_level', 'medium'),
            'human_approval_required': pb_cfg.get('human_approval_required', False),
            'estimated_impact': pb_cfg.get('estimated_impact', ''),
            'phases': pb_cfg.get('phases', []),
            'estimated_duration_days': pb_cfg.get('estimated_duration_days'),
            'estimated_duration_display': pb_cfg.get('estimated_duration_display', ''),
            'sub_components': pb_cfg.get('sub_components', []),
            'total_estimated_hours': total_hours,
        })
    except Exception as e:
        logger.error(f"Error fetching DC playbook detail: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch playbook'}), 500


@dc2s_api.route('/playbooks/executions', methods=['POST'])
def create_dc2s_playbook_execution():
    """
    Start a new DC playbook execution (V2).
    POST /api/dc2s/playbooks/executions
    Body: { playbook_id, account_id }
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        data = request.get_json() or {}
        playbook_id = data.get('playbook_id')
        account_id = data.get('account_id')

        if not playbook_id or not account_id:
            return jsonify({'error': 'playbook_id and account_id are required'}), 400

        pb_cfg = get_playbook_config(playbook_id)
        if not pb_cfg:
            return jsonify({'error': 'Playbook not found'}), 404

        # Verify account exists
        account = Account.query.filter_by(
            account_id=account_id, customer_id=int(customer_id)
        ).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404

        # Snapshot current KPI values for before/after comparison (stored in action_log metadata)
        all_kpis = DC2SKPI.query.filter_by(account_id=account_id).order_by(DC2SKPI.measured_at.desc()).all()
        kpi_snapshot = {}
        for kpi in all_kpis:
            if kpi.kpi_code not in kpi_snapshot:
                kpi_snapshot[kpi.kpi_code] = float(kpi.value)

        # Create V2 execution via lifecycle module
        v2 = _lifecycle_start(
            customer_id=int(customer_id),
            account_id=account_id,
            playbook_id=playbook_id,
            triggered_by='csm_manual',
        )

        # Store KPI snapshot in action_log metadata for before/after comparison on complete
        if v2.action_log is not None:
            # Store snapshot as metadata on the execution's action_log
            log_with_snapshot = list(v2.action_log)
        else:
            log_with_snapshot = []
        v2.action_log = log_with_snapshot
        # Store kpi_snapshot_before as a JSON property we can retrieve on complete
        existing_props = v2.skill_output or {}
        existing_props['kpi_snapshot_before'] = kpi_snapshot
        v2.skill_output = existing_props
        db.session.commit()

        execution_dict = _build_exec_dict(v2, account_name=account.account_name)
        execution_dict['kpi_snapshot_before'] = kpi_snapshot
        return jsonify({'status': 'success', 'execution': execution_dict}), 201

    except ValueError as ve:
        return jsonify({'error': str(ve)}), 404
    except Exception as e:
        logger.error(f"Error creating DC playbook execution: {e}", exc_info=True)
        return jsonify({'error': 'Failed to create execution'}), 500


@dc2s_api.route('/playbooks/executions', methods=['GET'])
def list_dc2s_playbook_executions():
    """
    List DC playbook executions (V2). Filters: status, account_id, playbook_id
    GET /api/dc2s/playbooks/executions?status=in-progress&account_id=101
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        status_filter = request.args.get('status')
        account_filter = request.args.get('account_id')
        playbook_filter = request.args.get('playbook_id')

        # Query V2 table directly (DB-first, no in-memory cache)
        query = PlaybookExecutionV2.query.filter(
            PlaybookExecutionV2.customer_id == int(customer_id),
        )

        if status_filter:
            # Frontend sends 'in-progress', V2 stores 'in_progress'
            db_status = status_filter.replace('-', '_')
            query = query.filter(PlaybookExecutionV2.status == db_status)
        if account_filter:
            query = query.filter(PlaybookExecutionV2.account_id == int(account_filter))
        if playbook_filter:
            query = query.filter(PlaybookExecutionV2.playbook_id == playbook_filter)

        v2_records = query.order_by(PlaybookExecutionV2.triggered_at.desc()).all()

        results = [_build_exec_dict(v2) for v2 in v2_records]
        return jsonify({'executions': results, 'total': len(results)})

    except Exception as e:
        logger.error(f"Error listing DC playbook executions: {e}", exc_info=True)
        return jsonify({'error': 'Failed to list executions'}), 500


@dc2s_api.route('/playbooks/executions/<execution_id>', methods=['GET'])
def get_dc2s_playbook_execution(execution_id):
    """
    Get DC playbook execution detail with all steps and hours (V2).
    GET /api/dc2s/playbooks/executions/<execution_id>
    """
    try:
        v2 = PlaybookExecutionV2.query.filter_by(execution_id=execution_id).first()
        if not v2:
            return jsonify({'error': 'Execution not found'}), 404

        return jsonify({'execution': _build_exec_dict(v2)})

    except Exception as e:
        logger.error(f"Error fetching DC execution: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch execution'}), 500


@dc2s_api.route('/playbooks/executions/<execution_id>/steps/<step_id>', methods=['PUT'])
def update_dc2s_playbook_step(execution_id, step_id):
    """
    Update a step's status, actual hours, and notes (V2 — updates action_log).
    PUT /api/dc2s/playbooks/executions/<execution_id>/steps/<step_id>
    Body: { status, actual_hours, notes }
    """
    try:
        v2 = PlaybookExecutionV2.query.filter_by(execution_id=execution_id).first()
        if not v2:
            return jsonify({'error': 'Execution not found'}), 404

        data = request.get_json() or {}
        now = datetime.utcnow().isoformat()

        action_log = list(v2.action_log or [])
        step_found = False
        for step in action_log:
            if step.get('step_id') == step_id:
                step_found = True
                if 'status' in data:
                    step['status'] = data['status']
                    if data['status'] == 'in-progress' and not step.get('started_at'):
                        step['started_at'] = now
                    if data['status'] == 'completed':
                        step['completed_at'] = now
                if 'actual_hours' in data:
                    step['actual_hours'] = data['actual_hours']
                if 'notes' in data:
                    step['notes'] = data['notes']
                break

        if not step_found:
            return jsonify({'error': 'Step not found'}), 404

        # Persist updated action_log and recalculate totals
        # NOTE: SQLAlchemy JSON columns need flag_modified for reliable dirty detection
        from sqlalchemy.orm.attributes import flag_modified
        v2.action_log = action_log
        flag_modified(v2, 'action_log')
        v2.actions_completed = sum(1 for s in action_log if s.get('status') == 'completed')
        v2.csm_hours_actual = sum(s.get('actual_hours') or 0 for s in action_log)
        db.session.commit()

        return jsonify({'status': 'success', 'execution': _build_exec_dict(v2)})

    except Exception as e:
        logger.error(f"Error updating DC playbook step: {e}", exc_info=True)
        return jsonify({'error': 'Failed to update step'}), 500


@dc2s_api.route('/playbooks/executions/<execution_id>/complete', methods=['PUT'])
def complete_dc2s_playbook_execution(execution_id):
    """
    Complete a DC playbook execution (V2), generate report, and save to PlaybookReport table.
    PUT /api/dc2s/playbooks/executions/<execution_id>/complete
    """
    try:
        customer_id = get_current_customer_id()

        # Load V2 record
        v2 = PlaybookExecutionV2.query.filter_by(execution_id=execution_id).first()
        if not v2:
            return jsonify({'error': 'Execution not found'}), 404

        now = datetime.utcnow()
        account_id = v2.account_id
        action_log = v2.action_log or []

        # Get current KPI values for after-snapshot
        kpi_snapshot_after = {}
        if account_id:
            all_kpis = DC2SKPI.query.filter_by(account_id=account_id).order_by(DC2SKPI.measured_at.desc()).all()
            for kpi in all_kpis:
                if kpi.kpi_code not in kpi_snapshot_after:
                    kpi_snapshot_after[kpi.kpi_code] = float(kpi.value)

        # Retrieve KPI before-snapshot stored at creation time
        before_snap = (v2.skill_output or {}).get('kpi_snapshot_before', {})

        # Health score before/after
        health_before, _ = calculate_kpi_health(before_snap, customer_id=customer_id)
        health_after, _ = calculate_kpi_health(kpi_snapshot_after, customer_id=customer_id)

        # Close via lifecycle module (sets V2 fields, ROI, context graph OUTCOME)
        v2 = _lifecycle_close(
            customer_id=int(customer_id),
            execution_id=execution_id,
            outcome='resolved',
            health_at_close=health_after,
            csm_hours_actual=v2.csm_hours_actual or sum(s.get('actual_hours') or 0 for s in action_log),
        )

        # ── Build report (same rich format as before) ──

        # Build hours tracking from action_log
        steps_tracking = []
        for step in action_log:
            est = step.get('estimated_hours', 0)
            act = step.get('actual_hours') or 0
            steps_tracking.append({
                'step_id': step.get('step_id', ''),
                'name': step.get('name', ''),
                'estimated_hours': est,
                'actual_hours': act,
                'variance': round(act - est, 1),
                'status': step.get('status', 'pending'),
                'notes': step.get('notes', ''),
            })

        total_est = v2.csm_hours_planned or 0
        total_act = v2.csm_hours_actual or 0
        variance_hrs = round(total_act - total_est, 1)
        variance_pct = round((variance_hrs / total_est) * 100, 1) if total_est else 0

        if variance_pct <= -10:
            efficiency = 'Under Budget'
        elif variance_pct <= 10:
            efficiency = 'On Budget'
        else:
            efficiency = 'Over Budget'

        # Build KPI impact from before/after snapshots
        pb_cfg = get_playbook_config(v2.playbook_id or '')
        trigger_kpis_impact = []
        for trigger_kpi in (pb_cfg or {}).get('trigger_kpis', []):
            catalog_code = trigger_kpi
            before_val = before_snap.get(trigger_kpi)
            after_val = kpi_snapshot_after.get(trigger_kpi)

            # Also try DB-style codes
            if before_val is None:
                for db_code, raw_val in before_snap.items():
                    norm = _normalize_kpi_code_for_health(db_code)
                    if norm == trigger_kpi:
                        before_val = raw_val
                        break
            if after_val is None:
                for db_code, raw_val in kpi_snapshot_after.items():
                    norm = _normalize_kpi_code_for_health(db_code)
                    if norm == trigger_kpi:
                        after_val = raw_val
                        break

            kpi_def = DC2S_KPIS.get(catalog_code, {})
            target_raw = kpi_def.get('target')
            target_val = target_raw.get('value') if isinstance(target_raw, dict) else target_raw

            if before_val is not None and after_val is not None and before_val != 0:
                change_pct = round(((after_val - before_val) / abs(before_val)) * 100, 1)
                improvement = f"{'+' if change_pct >= 0 else ''}{change_pct}%"
            else:
                improvement = 'N/A'

            kpi_status = 'Pending'
            if target_val is not None and after_val is not None:
                cond = (pb_cfg or {}).get('trigger_conditions', {}).get(trigger_kpi, {})
                op = cond.get('operator', '>')
                if op == '<':
                    kpi_status = 'Achieved' if after_val < target_val else 'In Progress'
                else:
                    kpi_status = 'Achieved' if after_val > target_val else 'In Progress'

            trigger_kpis_impact.append({
                'kpi_code': catalog_code,
                'kpi_name': kpi_def.get('name', kpi_def.get('kpi_name', catalog_code)),
                'before': before_val,
                'after': after_val,
                'target': target_val,
                'unit': kpi_def.get('unit', ''),
                'improvement': improvement,
                'status': kpi_status,
            })

        # Build RACI
        raci = {}
        for step in action_log:
            raci[step.get('name', '')] = {
                'CSM': 'Responsible',
                'Field Engineer': 'Consulted',
                'Platform': 'Informed',
                'Exec Sponsor': 'Informed',
            }

        # Exit criteria from playbook trigger conditions
        exit_criteria = []
        for trigger_kpi, cond in (pb_cfg or {}).get('trigger_conditions', {}).items():
            kpi_def = DC2S_KPIS.get(trigger_kpi, {})
            after_val = kpi_snapshot_after.get(trigger_kpi)
            if after_val is None:
                for db_code, raw_val in kpi_snapshot_after.items():
                    norm = _normalize_kpi_code_for_health(db_code)
                    if norm == trigger_kpi:
                        after_val = raw_val
                        break
            met = False
            if after_val is not None:
                if cond['operator'] == '<':
                    met = after_val < cond['value']
                elif cond['operator'] == '>':
                    met = after_val > cond['value']
            exit_criteria.append({
                'criteria': f"{kpi_def.get('name', trigger_kpi)} {cond['operator']} {cond['value']}",
                'status': 'Met' if met else 'Not Met',
                'evidence': f"Current value: {after_val}" if after_val is not None else 'No data',
            })

        # Duration & names
        started = v2.triggered_at or now
        duration_days = (now - started).days

        account = Account.query.filter_by(account_id=account_id).first()
        playbook_name = v2.playbook_name or ''
        account_name = account.account_name if account else f"Account {account_id}"

        # Executive summary
        kpi_summaries = []
        for ki in trigger_kpis_impact:
            if ki['before'] is not None and ki['after'] is not None:
                kpi_summaries.append(f"{ki['kpi_name']}: {ki['before']} -> {ki['after']} ({ki['improvement']})")
        exec_summary = (
            f"{playbook_name} completed for {account_name} in {duration_days} days. "
            f"Total hours: {total_act}h (estimated {total_est}h, {efficiency}). "
            + "; ".join(kpi_summaries[:3])
        )

        report_data = {
            'execution_id': execution_id,
            'playbook_id': v2.playbook_id,
            'playbook_name': playbook_name,
            'account_id': account_id,
            'account_name': account_name,
            'phase': v2.phase or '',
            'status': 'Completed',
            'started_at': v2.triggered_at.isoformat() if v2.triggered_at else None,
            'completed_at': now.isoformat(),
            'duration_days': duration_days,
            'executive_summary': exec_summary,
            'hours_tracking': {
                'total_estimated_hours': total_est,
                'total_actual_hours': total_act,
                'variance_hours': variance_hrs,
                'variance_percent': variance_pct,
                'efficiency_rating': efficiency,
                'steps': steps_tracking,
            },
            'kpi_impact': {
                'trigger_kpis': trigger_kpis_impact,
                'health_score_before': round(health_before, 1),
                'health_score_after': round(health_after, 1),
                'health_improvement': f"{'+' if health_after >= health_before else ''}{round(health_after - health_before, 1)} points",
                'financial_impact': (pb_cfg or {}).get('estimated_impact', ''),
            },
            'raci_matrix': raci,
            'exit_criteria': exit_criteria,
            'next_steps': [
                f"Schedule {duration_days + 30}-day follow-up health check",
                f"Monitor trigger KPIs for sustained improvement",
            ],
            'learnings': [
                f"Playbook completed {'under' if variance_pct < 0 else 'over'} estimated hours by {abs(variance_pct)}%",
            ],
            # V2-specific ROI fields
            'revenue_protected': v2.revenue_protected,
            'revenue_expanded': v2.revenue_expanded,
            'realized_roi_pct': v2.realized_roi_pct,
            'total_cost': v2.total_cost,
        }

        # Save to PlaybookReport table (makes it queryable by AI Insights)
        try:
            completed_count = sum(1 for s in steps_tracking if s['status'] == 'completed')
            db_report = PlaybookReport(
                execution_id=execution_id,
                customer_id=int(customer_id) if customer_id else v2.customer_id,
                account_id=account_id,
                playbook_id=v2.playbook_id,
                playbook_name=playbook_name,
                account_name=account_name,
                status='completed',
                report_data=report_data,
                duration=f"{duration_days} days",
                steps_completed=completed_count,
                total_steps=len(steps_tracking),
                started_at=started,
                completed_at=now,
                report_generated_at=now,
            )
            db.session.add(db_report)

            # ── Record ActionEconomics (Playbook Economic Bridge) ──
            try:
                _record_action_economics(
                    customer_id=int(customer_id) if customer_id else v2.customer_id,
                    account_id=account_id,
                    execution_id=execution_id,
                    playbook_id=v2.playbook_id or '',
                    playbook_name=playbook_name,
                    total_hours=total_act or total_est,
                    steps=action_log,
                    kpi_before=before_snap,
                    kpi_after=kpi_snapshot_after,
                    health_before=health_before,
                    health_after=health_after,
                    started_at=started,
                    completed_at=now,
                )
            except Exception as ae_err:
                logger.warning(f"ActionEconomics record failed for {execution_id}: {ae_err}")

            db.session.commit()
            logger.info(f"DC playbook report saved for {execution_id}")
        except Exception as db_err:
            logger.warning(f"DB persist failed for DC report {execution_id}: {db_err}")
            db.session.rollback()

        return jsonify({'status': 'success', 'report': report_data})

    except ValueError as ve:
        return jsonify({'error': str(ve)}), 404
    except Exception as e:
        logger.error(f"Error completing DC playbook execution: {e}", exc_info=True)
        return jsonify({'error': 'Failed to complete execution'}), 500


@dc2s_api.route('/playbooks/executions/<execution_id>/report', methods=['GET'])
def get_dc2s_playbook_report(execution_id):
    """
    Get the generated report for a completed DC playbook execution.
    GET /api/dc2s/playbooks/executions/<execution_id>/report
    """
    try:
        # Check DB first
        db_report = PlaybookReport.query.filter_by(execution_id=execution_id).first()
        if db_report:
            return jsonify({'status': 'success', 'report': db_report.report_data})

        return jsonify({'error': 'Report not found'}), 404

    except Exception as e:
        logger.error(f"Error fetching DC playbook report: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch report'}), 500


# ============================================================
# CSM DAILY ACTIONS – "Low Cost, High Impact" scoring
# ============================================================

def _compute_impact_score(health_score, churn_prob, expansion_prob, pillar_averages):
    """Impact Score (0-100): how much value this action can protect/generate."""
    # Churn contribution (40%)
    churn_component = min(churn_prob, 100) * 0.4

    # Health trend proxy (30%): lower health = more impact
    h_cls = ht.classify(health_score)
    if h_cls == 'critical':
        trend_component = 30
    elif h_cls == 'at_risk':
        trend_component = 20
    else:
        trend_component = 5

    # Expansion opportunity (20%)
    expansion_component = min(expansion_prob, 100) * 0.2

    # Weakest pillar severity (10%)
    weakest = min(pillar_averages.values()) if pillar_averages else 50
    w_cls = ht.classify(weakest)
    if w_cls == 'critical':
        pillar_component = 10
    elif w_cls == 'at_risk':
        pillar_component = 5
    else:
        pillar_component = 0

    return round(churn_component + trend_component + expansion_component + pillar_component, 1)


def _compute_effort_score(playbook_cfg):
    """Effort Score (0-100): lower effort = better priority. Based on playbook complexity."""
    if not playbook_cfg:
        return 30  # Default for non-playbook actions

    subs = playbook_cfg.get('sub_components', [])
    total_hours = sum(s.get('estimated_hours', 0) for s in subs)
    duration_days = playbook_cfg.get('estimated_duration_days', 14)

    # Duration weight (40%): scale 0-100 where 60+ days = 100
    duration_score = min(100, (duration_days / 60) * 100) * 0.4

    # Prerequisites complexity (35%): more sub-components = more complex
    prereq_score = min(100, len(subs) * 20) * 0.35

    # Total hours (25%): scale 0-100 where 144+ hours = 100
    hours_score = min(100, (total_hours / 144) * 100) * 0.25

    return round(duration_score + prereq_score + hours_score, 1)


def _determine_urgency(health_score, churn_prob, expansion_prob):
    """Classify urgency based on centralized health thresholds."""
    h_cls = ht.classify(health_score)
    if churn_prob > 70 or h_cls == 'critical':
        return 'critical'
    if h_cls == 'at_risk':
        return 'high'
    if expansion_prob > 75 and h_cls == 'healthy':
        return 'opportunity'
    return 'medium'


# ──────────────────────────────────────────────────────────────
# CSM Action ↔ ROI Roadmap Correlation
# Maps playbooks and ad-hoc actions to Power of 1 metrics
# ──────────────────────────────────────────────────────────────

# Playbook → Power of 1 metric mapping
_PLAYBOOK_ROI_MAP = {
    'PB-01': {'metric_id': 'TTFV',  'metric_name': 'Time to First Value',  'impact_type': 'foundation'},
    'PB-02': {'metric_id': 'ticket_resolution_time', 'metric_name': 'Ticket Resolution Time', 'impact_type': 'efficiency'},
    'PB-03': {'metric_id': 'product_adoption', 'metric_name': 'Product Adoption', 'impact_type': 'growth'},
    'PB-04': {'metric_id': 'expansion_rate', 'metric_name': 'Expansion Rate', 'impact_type': 'revenue'},
    'PB-05': {'metric_id': 'GRR',   'metric_name': 'Gross Revenue Retention', 'impact_type': 'retention'},
    'PB-06': {'metric_id': 'expansion_rate', 'metric_name': 'Expansion Rate', 'impact_type': 'revenue'},
}

# Non-playbook action types → Power of 1 metric mapping
_ACTION_ROI_MAP = {
    'follow_up':  {'metric_id': 'GRR',   'metric_name': 'Gross Revenue Retention', 'impact_type': 'retention'},
    'qbr':        {'metric_id': 'NRR',   'metric_name': 'Net Revenue Retention',   'impact_type': 'retention'},
    'expansion':  {'metric_id': 'expansion_rate', 'metric_name': 'Expansion Rate', 'impact_type': 'revenue'},
}


def _get_roi_context(action_type, playbook_id, account_revenue=0):
    """
    Return ROI roadmap context for a CSM action.
    Includes which Power of 1 metric this action impacts and estimated dollar value.
    """
    roi = None
    if playbook_id and playbook_id in _PLAYBOOK_ROI_MAP:
        roi = _PLAYBOOK_ROI_MAP[playbook_id].copy()
    elif action_type in _ACTION_ROI_MAP:
        roi = _ACTION_ROI_MAP[action_type].copy()

    if not roi:
        return {'roi_metric_id': None, 'roi_metric_name': None, 'roi_projected_impact': 0}

    # Estimate dollar impact: use Power of 1 annual_impact_per_pct scaled to account ARR
    try:
        from power_of_1_model import POWER_OF_1_METRICS
        metric = POWER_OF_1_METRICS.get(roi['metric_id'])
        if metric:
            # Scale to account's ARR relative to $10M base
            arr_scale = max(account_revenue, 100_000) / 10_000_000
            projected = round(metric.annual_impact_per_pct * 2.0 * arr_scale)  # Assume 2% target improvement
        else:
            projected = 0
    except Exception:
        projected = 0

    return {
        'roi_metric_id': roi['metric_id'],
        'roi_metric_name': roi['metric_name'],
        'roi_projected_impact': projected,
        'roi_impact_type': roi['impact_type'],
    }


@dc2s_api.route('/daily-actions', methods=['GET'])
def get_csm_daily_actions():
    """
    CSM Daily Action List — returns top-10 prioritised actions.
    GET /api/dc2s/daily-actions
    Scoring: Priority Index = (impact * 0.6 * arr_weight) - (effort * 0.4)
    Each action is correlated to a Power of 1 ROI metric with projected dollar impact.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        # Optional CSM name filter
        csm_name_filter = request.args.get('csm_name', None)

        # 1. Fetch all DC accounts
        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
        ).all()

        # Filter by CSM assignment if csm_name provided
        if csm_name_filter and accounts:
            filtered = []
            for acct in accounts:
                meta = acct.profile_metadata if hasattr(acct, 'profile_metadata') and acct.profile_metadata else {}
                csm = meta.get('assigned_csm') or meta.get('csm_name') or 'Unassigned'
                if csm_name_filter.lower() in csm.lower():
                    filtered.append(acct)
            accounts = filtered

        if not accounts:
            return jsonify({
                'date': datetime.utcnow().strftime('%Y-%m-%d'),
                'actions': [],
                'summary': {
                    'total_actions': 0,
                    'critical_count': 0,
                    'high_count': 0,
                    'opportunity_count': 0,
                    'total_estimated_hours': 0
                }
            })

        all_actions = []

        # ── Batch-load stakeholder context for all accounts (single query) ──
        _stakeholder_map = {}  # {account_id: {'champion': str, 'decision_makers': [str]}}
        try:
            from models import ContextNode as _CNode
            _acct_ids = [a.account_id for a in accounts]
            if _acct_ids:
                _stk_nodes = _CNode.query.filter(
                    _CNode.account_id.in_(_acct_ids),
                    _CNode.customer_id == int(customer_id),
                    _CNode.node_type == 'STAKEHOLDER',
                ).all()
                for sn in _stk_nodes:
                    aid = sn.account_id
                    if aid not in _stakeholder_map:
                        _stakeholder_map[aid] = {'champion': None, 'champion_title': None, 'decision_makers': []}
                    props = sn.properties or {}
                    subtype = (sn.node_subtype or '').lower()
                    title_lower = (sn.title or '').lower()
                    name = sn.title or ''
                    role = sn.node_subtype or ''
                    # Identify champion
                    if 'champion' in subtype or 'champion' in title_lower:
                        _stakeholder_map[aid]['champion'] = name
                        _stakeholder_map[aid]['champion_title'] = role
                    # Identify decision-makers (executives, directors, VPs)
                    elif any(r in subtype for r in ['executive', 'director', 'vp', 'cto', 'cio', 'cfo', 'svp']):
                        _stakeholder_map[aid]['decision_makers'].append(f"{name} ({role})")
        except Exception as _stk_err:
            logger.debug(f"Stakeholder batch load (non-fatal): {_stk_err}")

        # ── Prepend system-triggered PlaybookTask records (status='pending') ──
        # These are created by signal_analyst / urgent_signal_scanner and take
        # precedence over generated recommendations.
        try:
            from models import PlaybookTask
            from .vertical_config import PLAYBOOK_CONFIG as _PB_CFG

            pending_tasks = (
                PlaybookTask.query
                .filter_by(customer_id=int(customer_id), status='pending')
                .order_by(PlaybookTask.created_at.desc())
                .limit(20)
                .all()
            )

            for task in pending_tasks:
                # Fetch account name and ARR for context
                task_account = next(
                    (a for a in accounts if a.account_id == task.account_id), None
                )
                task_account_name = task_account.account_name if task_account else f"Account {task.account_id}"
                task_arr = 0
                if task_account:
                    meta = task_account.profile_metadata or {}
                    task_arr = meta.get('arr', 0) or float(task_account.revenue or 0)

                pb_cfg = _PB_CFG.get(task.playbook_id, {})
                total_hours = sum(
                    s.get('estimated_hours', 0)
                    for s in pb_cfg.get('sub_components', [])
                ) or 4

                all_actions.append({
                    'account_id':               task.account_id,
                    'account_name':             task_account_name,
                    'action_title':             f"[System] {pb_cfg.get('name', task.playbook_id)} Playbook",
                    'action_description':       task.trigger_reason or f"System-triggered: {task.trigger_source}",
                    'action_type':              'playbook',
                    'related_playbook_id':      task.playbook_id,
                    'urgency':                  'critical',
                    'impact_score':             90,
                    'effort_score':             30,
                    'priority_index':           999.0,  # always sorted to top
                    'account_health':           0.0,    # will be overwritten by account-level loop below if same account
                    'estimated_hours':          total_hours,
                    'estimated_duration_display': pb_cfg.get('estimated_duration_display', ''),
                    'source':                   'system_triggered',
                    'playbook_task_id':         task.id,
                    'trigger_source':           task.trigger_source,
                    'assigned_csm':             task.assigned_csm,
                    'due_date':                 task.due_date.isoformat() if task.due_date else None,
                    'roi_metric_name':          None,
                    'roi_projected_impact':     0,
                    'roi_explanation':          'System-triggered task — see signal analysis for ROI context.',
                })
        except Exception as _pt_err:
            logger.warning(f"PlaybookTask prepend failed (non-fatal): {_pt_err}")

        # ── Arc-type labels for personalized action titles ──
        _ARC_LABELS = {
            'champion_loss':        ('Champion Recovery', 'Re-establish executive sponsor relationship'),
            'infrastructure_decay': ('Infrastructure Stabilization', 'Address degrading operational metrics'),
            'crisis_recovery':      ('Crisis Recovery', 'Stabilize account after critical incident'),
            'land_and_expand':      ('Expansion Nurture', 'Capitalize on healthy growth trajectory'),
            'steady_state':         ('Retention Assurance', 'Maintain engagement and prevent drift'),
            'seasonal_pattern':     ('Seasonal Prep', 'Prepare for upcoming demand cycle'),
            'competitive_threat':   ('Competitive Defense', 'Counter competitor engagement signals'),
            'budget_pressure':      ('Financial Alignment', 'Navigate budget constraints to protect renewal'),
        }

        for account in accounts:
            _arc = getattr(account, 'arc_type', None) or ''
            _arc_label, _arc_hint = _ARC_LABELS.get(_arc, (None, None))

            # 2. Trailing 30-day weighted average for stable health scores
            trailing_kpis = _get_trailing_kpi_values(account.account_id, days=30)

            # Calculate health
            overall_health, pillar_averages = calculate_kpi_health(trailing_kpis, customer_id=customer_id)

            # Normalize KPI codes for playbook trigger evaluation
            normalized_kpis = {}
            for code, val in trailing_kpis.items():
                norm = _normalize_kpi_code_for_health(code)
                if norm:
                    normalized_kpis[norm] = val
            # Also add OVERALL_HEALTH for PB-05 trigger
            normalized_kpis['OVERALL_HEALTH'] = overall_health

            # ARR weight (0.5-1.5): boost high-value accounts
            arr = (account.profile_metadata or {}).get('arr', 0) or (account.profile_metadata or {}).get('revenue', 0) or 0
            if not arr:
                arr = float(account.revenue) if account.revenue else 0
            if arr > 10_000_000:
                arr_weight = 1.5
            elif arr > 5_000_000:
                arr_weight = 1.3
            elif arr > 2_000_000:
                arr_weight = 1.1
            elif arr > 0:
                arr_weight = 1.0
            else:
                arr_weight = 0.8  # Unknown ARR — slight penalty

            # Churn / expansion estimates from health using centralized thresholds
            h_cls = ht.classify(overall_health)
            churn_prob = 80 if h_cls == 'critical' else (40 if h_cls == 'at_risk' else 15)
            expansion_prob_val = 75 if h_cls == 'healthy' else (30 if h_cls == 'at_risk' else 5)

            # Check expansion KPI if available
            exp_kpi = normalized_kpis.get('P5-KPI7')
            if exp_kpi is not None:
                expansion_prob_val = max(expansion_prob_val, exp_kpi)

            # 3. Evaluate all 6 playbook triggers
            for pb_id, pb_cfg in PLAYBOOK_CONFIG.items():
                if should_trigger_playbook(pb_id, normalized_kpis):
                    impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                    effort = _compute_effort_score(pb_cfg)
                    priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)

                    total_hours = sum(s.get('estimated_hours', 0) for s in pb_cfg.get('sub_components', []))

                    # Build description from trigger KPI values
                    trigger_details = []
                    for tk in pb_cfg.get('trigger_kpis', []):
                        if tk in normalized_kpis:
                            cond = pb_cfg.get('trigger_conditions', {}).get(tk, {})
                            threshold = cond.get('value', '?')
                            kpi_name = DC2S_KPIS.get(tk, {}).get('name', tk)
                            trigger_details.append(f"{kpi_name}: {normalized_kpis[tk]:.1f} (threshold {threshold})")

                    description = '; '.join(trigger_details) if trigger_details else pb_cfg.get('estimated_impact', '')

                    roi_ctx = _get_roi_context('playbook', pb_id, arr)
                    all_actions.append({
                        'account_id': account.account_id,
                        'account_name': account.account_name,
                        'action_title': f"Start {pb_cfg['name']} Playbook",
                        'action_description': description,
                        'action_type': 'playbook',
                        'related_playbook_id': pb_id,
                        'urgency': _determine_urgency(overall_health, churn_prob, expansion_prob_val),
                        'impact_score': impact,
                        'effort_score': effort,
                        'priority_index': priority_index,
                        'account_health': round(overall_health, 1),
                        'estimated_hours': total_hours,
                        'estimated_duration_display': pb_cfg.get('estimated_duration_display', ''),
                        **roi_ctx,
                    })

            # 4. Non-playbook actions

            # Health check follow-up for critical and at-risk accounts (health < 80)
            if overall_health < 80:
                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 20  # Low effort: just a review call
                priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                roi_ctx = _get_roi_context('follow_up', None, arr)
                # Personalize title based on arc type
                _follow_title = f'{_arc_label} Check-in' if _arc_label else 'Health Check Follow-up'
                _follow_desc = f'{_arc_hint}. ' if _arc_hint else ''
                _follow_desc += f'Health score at {overall_health:.0f}. Schedule intervention call.'
                all_actions.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'action_title': _follow_title,
                    'action_description': _follow_desc,
                    'action_type': 'follow_up',
                    'related_playbook_id': None,
                    'urgency': _determine_urgency(overall_health, churn_prob, expansion_prob_val),
                    'impact_score': impact,
                    'effort_score': effort,
                    'priority_index': priority_index,
                    'account_health': round(overall_health, 1),
                    'estimated_hours': 2,
                    'estimated_duration_display': '1 day',
                    **roi_ctx,
                })

            # QBR scheduling (P4-KPI3 < target 3)
            qbr_val = normalized_kpis.get('P4-KPI3')
            if qbr_val is not None and qbr_val < 3:
                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 25
                priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                roi_ctx = _get_roi_context('qbr', None, arr)
                all_actions.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'action_title': 'Schedule QBR',
                    'action_description': f'QBR frequency at {qbr_val:.0f}/yr (target 3+). Schedule next review.',
                    'action_type': 'qbr',
                    'related_playbook_id': None,
                    'urgency': 'high',
                    'impact_score': impact,
                    'effort_score': effort,
                    'priority_index': priority_index,
                    'account_health': round(overall_health, 1),
                    'estimated_hours': 4,
                    'estimated_duration_display': '1-2 days',
                    **roi_ctx,
                })

            # Expansion call (P5-KPI7 > 70%)
            if exp_kpi is not None and exp_kpi > 70:
                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 30
                priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                roi_ctx = _get_roi_context('expansion', None, arr)
                all_actions.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'action_title': 'Expansion Opportunity Call',
                    'action_description': f'Expansion probability at {exp_kpi:.0f}%. Schedule capacity planning discussion.',
                    'action_type': 'expansion',
                    'related_playbook_id': None,
                    'urgency': 'opportunity',
                    'impact_score': impact,
                    'effort_score': effort,
                    'priority_index': priority_index,
                    'account_health': round(overall_health, 1),
                    'estimated_hours': 3,
                    'estimated_duration_display': '1 day',
                    **roi_ctx,
                })

        # 5. Sort by priority_index DESC, deduplicate per account (keep highest), take top 10
        all_actions.sort(key=lambda a: a['priority_index'], reverse=True)
        seen_accounts = set()
        deduped_actions = []
        for a in all_actions:
            aid = a.get('account_id')
            if aid not in seen_accounts:
                seen_accounts.add(aid)
                deduped_actions.append(a)
        top_actions = deduped_actions[:10]

        # Batch-load recent signals for trigger context ("Why this action?")
        _trigger_signal_map = {}
        try:
            from models import ContextNode
            action_account_ids = list({a.get('account_id') for a in top_actions if a.get('account_id')})
            if action_account_ids:
                recent_signals = (
                    ContextNode.query
                    .filter(
                        ContextNode.customer_id == int(customer_id),
                        ContextNode.account_id.in_(action_account_ids),
                        ContextNode.node_type == 'SIGNAL',
                    )
                    .order_by(ContextNode.occurred_at.desc())
                    .all()
                )
                for sig in recent_signals:
                    if sig.account_id not in _trigger_signal_map:
                        _trigger_signal_map[sig.account_id] = {
                            'signal_type': sig.node_subtype or (sig.properties or {}).get('signal_type', 'unknown'),
                            'signal_summary': (sig.title or '')[:200],
                            'signal_date': str(sig.occurred_at)[:10] if sig.occurred_at else None,
                            'sentiment': (sig.properties or {}).get('sentiment', 'neutral'),
                        }
        except Exception:
            pass  # Context graph may not be enabled

        # Assign rank, id, and stakeholder context
        for i, action in enumerate(top_actions, 1):
            action['rank'] = i
            action['id'] = f"act-{i:03d}"
            # Inject stakeholder context from batch-loaded map
            stk = _stakeholder_map.get(action.get('account_id'), {})
            action['primary_champion'] = stk.get('champion')
            action['champion_title'] = stk.get('champion_title')
            action['decision_makers'] = stk.get('decision_makers', [])[:3]
            # Inject arc_type and kanban_column for frontend personalization
            if 'arc_type' not in action:
                acct_obj = next((a for a in accounts if a.account_id == action.get('account_id')), None)
                action['arc_type'] = getattr(acct_obj, 'arc_type', None) if acct_obj else None
            if 'kanban_column' not in action:
                acct_obj = acct_obj if 'acct_obj' in dir() else next((a for a in accounts if a.account_id == action.get('account_id')), None)
                action['kanban_column'] = (getattr(acct_obj, 'profile_metadata', None) or {}).get('kanban_column') if acct_obj else None
            # Inject trigger context ("Why this action?")
            action['trigger_context'] = _trigger_signal_map.get(action.get('account_id'))

        # Summary
        urgency_counts = {'critical': 0, 'high': 0, 'opportunity': 0, 'medium': 0}
        total_hours = 0
        for a in top_actions:
            urgency_counts[a.get('urgency', 'medium')] = urgency_counts.get(a.get('urgency', 'medium'), 0) + 1
            total_hours += a.get('estimated_hours', 0)

        # ROI summary: total projected impact across all top actions
        total_roi_impact = sum(a.get('roi_projected_impact', 0) for a in top_actions)
        roi_metrics_involved = list({a['roi_metric_name'] for a in top_actions if a.get('roi_metric_name')})

        return jsonify({
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'actions': top_actions,
            'summary': {
                'total_actions': len(top_actions),
                'critical_count': urgency_counts.get('critical', 0),
                'high_count': urgency_counts.get('high', 0),
                'opportunity_count': urgency_counts.get('opportunity', 0),
                'total_estimated_hours': total_hours,
                'total_roi_projected_impact': total_roi_impact,
                'roi_metrics_involved': roi_metrics_involved,
            }
        })

    except Exception as e:
        logger.error(f"Error computing daily actions: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compute daily actions'}), 500


# =============================================================================
# CSM Scorecard — per-CSM performance attribution
# =============================================================================

@dc2s_api.route('/csm-scorecard', methods=['GET'])
def get_csm_scorecard_api():
    """GET /api/dc2s/csm-scorecard?csm_name=<optional>
    Returns per-CSM accounts managed, health delta, playbook success, revenue impact.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        csm_name_filter = request.args.get('csm_name', None)
        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()

        # Group accounts by assigned CSM from profile metadata
        csm_accounts = defaultdict(list)
        for acct in accounts:
            meta = acct.profile_metadata if hasattr(acct, 'profile_metadata') and acct.profile_metadata else {}
            csm = meta.get('assigned_csm') or meta.get('csm_name') or 'Unassigned'
            if csm_name_filter and csm_name_filter.lower() not in csm.lower():
                continue
            csm_accounts[csm].append(acct)

        scorecards = {}
        for csm, accts in csm_accounts.items():
            acct_ids = [a.account_id for a in accts]
            total_arr = sum(float(a.revenue or 0) for a in accts)

            # Health deltas from HealthScore table
            health_deltas = []
            for aid in acct_ids:
                scores = (HealthScore.query
                    .filter_by(account_id=aid)
                    .order_by(HealthScore.measurement_month.asc())
                    .all())
                if len(scores) >= 2:
                    delta = float(scores[-1].health_score or 0) - float(scores[0].health_score or 0)
                    health_deltas.append(delta)

            # Playbook executions on this CSM's accounts
            try:
                from models import PlaybookExecutionV2
                execs = PlaybookExecutionV2.query.filter(
                    PlaybookExecutionV2.account_id.in_(acct_ids),
                    PlaybookExecutionV2.customer_id == int(customer_id),
                ).all()
            except Exception:
                execs = []

            resolved = sum(1 for e in execs if e.outcome == 'resolved')
            rev_protected = sum(float(e.revenue_protected or 0) for e in execs)
            rev_expanded = sum(float(e.revenue_expanded or 0) for e in execs)

            scorecards[csm] = {
                'csm_name': csm,
                'accounts_managed': len(accts),
                'total_arr': total_arr,
                'avg_health_delta': round(sum(health_deltas) / len(health_deltas), 1) if health_deltas else 0,
                'accounts_improving': sum(1 for d in health_deltas if d > 5),
                'accounts_declining': sum(1 for d in health_deltas if d < -5),
                'playbooks_executed': len(execs),
                'playbooks_resolved': resolved,
                'success_rate_pct': round(resolved / len(execs) * 100, 1) if execs else 0,
                'revenue_protected': rev_protected,
                'revenue_expanded': rev_expanded,
                'total_revenue_impact': rev_protected + rev_expanded,
            }

        return jsonify({
            'csm_count': len(scorecards),
            'scorecards': scorecards,
        })

    except Exception as e:
        logger.error(f"Error computing CSM scorecard: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compute CSM scorecard'}), 500


# =============================================================================
# Team Capacity — FTE utilization by role
# =============================================================================

@dc2s_api.route('/team-capacity', methods=['GET'])
def get_team_capacity_api():
    """GET /api/dc2s/team-capacity
    Returns team capacity utilization, bottleneck detection, portfolio context.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        total_arr = sum(float(a.revenue or 0) for a in accounts)

        # Pre-load health scores for at-risk count
        _health_map = {}
        for acct in accounts:
            h, _, _, _ = get_precalculated_scores(acct.account_id)
            _health_map[acct.account_id] = h or 100
        at_risk_count = sum(1 for a in accounts if _health_map.get(a.account_id, 100) < ht.healthy_min())

        # Group accounts by CSM for real CSM count
        csm_set = set()
        for acct in accounts:
            meta = acct.profile_metadata if hasattr(acct, 'profile_metadata') and acct.profile_metadata else {}
            csm = meta.get('assigned_csm') or meta.get('csm_name')
            if csm and csm != 'Unassigned':
                csm_set.add(csm)
        csm_count = max(len(csm_set), 1)
        accounts_per_csm = round(len(accounts) / csm_count, 1)

        # Active playbook executions
        try:
            from models import PlaybookExecutionV2
            active_execs = PlaybookExecutionV2.query.filter_by(
                customer_id=int(customer_id)
            ).filter(
                PlaybookExecutionV2.outcome.is_(None)
            ).all()
            recent_cutoff = datetime.utcnow() - timedelta(days=90)
            recent_execs = PlaybookExecutionV2.query.filter(
                PlaybookExecutionV2.customer_id == int(customer_id),
                PlaybookExecutionV2.triggered_at >= recent_cutoff,
            ).all()
        except Exception:
            active_execs = []
            recent_execs = []

        active_csm_hours = sum(float(e.csm_hours_planned or 0) for e in active_execs)
        target_per_csm = 6

        # ── Per-CSM capacity breakdown ──
        per_csm_breakdown = []
        acct_by_csm = {}
        for acct in accounts:
            meta = acct.profile_metadata if hasattr(acct, 'profile_metadata') and acct.profile_metadata else {}
            csm = meta.get('assigned_csm') or meta.get('csm_name') or 'Unassigned'
            acct_by_csm.setdefault(csm, []).append(acct)

        # Map active playbook executions to accounts for per-CSM aggregation
        active_exec_by_acct = {}
        for ex in active_execs:
            active_exec_by_acct.setdefault(ex.account_id, []).append(ex)

        hours_per_week = 40  # Standard CSM work week
        for csm_name in sorted(acct_by_csm.keys()):
            csm_accts = acct_by_csm[csm_name]
            csm_acct_ids = {a.account_id for a in csm_accts}
            csm_active_execs = [ex for aid in csm_acct_ids for ex in active_exec_by_acct.get(aid, [])]
            hours_committed = sum(float(e.csm_hours_planned or 0) for e in csm_active_execs)
            csm_arr = sum(float(a.revenue or 0) for a in csm_accts)
            csm_at_risk = sum(1 for a in csm_accts if _health_map.get(a.account_id, 100) < ht.healthy_min())
            per_csm_breakdown.append({
                'csm_name': csm_name,
                'accounts_managed': len(csm_accts),
                'total_arr': csm_arr,
                'active_playbooks': len(csm_active_execs),
                'hours_committed': round(hours_committed, 1),
                'hours_available': hours_per_week,
                'utilization_pct': round(hours_committed / hours_per_week * 100, 1) if hours_per_week > 0 else 0,
                'at_risk_accounts': csm_at_risk,
            })

        # ── Hours-based resource-pool view (mirrors MCP get_team_capacity) ──
        # PR-29 (May 17 visual re-eval fix): the prior response exposed an
        # account-count utilization (accounts_per_csm / target_per_csm) which
        # always pinned at ~100% for any tenant with the target load. The buyer
        # needs an HOURS-based utilization gauge anchored to a real resource
        # pool with totals + bottleneck detection. We compute that here and
        # keep the legacy account-count fields for backward compat.
        resource_pool = None
        hours_utilization_pct = {}
        hours_feasible = True
        bottleneck_roles: list = []
        overflow_hours = 0.0
        recommendation_text = ''
        try:
            import resource_capacity_model as rcm
            resource_pool = rcm.get_resource_pool_summary()

            # Roll planned hours across the 5 roles using the same heuristic
            # as the MCP tool: CSM hours come from PlaybookExecutionV2; CS_OPS
            # and PLATFORM are approximated as a fraction of CSM hours so the
            # gauge reflects multi-role load, not just CSM.
            hours_by_role = {
                rcm.CSRole.CSM: 0.0,
                rcm.CSRole.CS_OPS: 0.0,
                rcm.CSRole.PRODUCT: 0.0,
                rcm.CSRole.PLATFORM: 0.0,
                rcm.CSRole.LEADERSHIP: 0.0,
            }
            for e in active_execs:
                csm_hrs = float(getattr(e, 'csm_hours_planned', 0) or 0)
                hours_by_role[rcm.CSRole.CSM] += csm_hrs
                hours_by_role[rcm.CSRole.CS_OPS] += csm_hrs * 0.5
                hours_by_role[rcm.CSRole.PLATFORM] += csm_hrs * 0.2

            try:
                cap = rcm.check_capacity(hours_by_role)
                hours_feasible = cap.is_feasible
                hours_utilization_pct = {r: round(u * 100, 1) for r, u in cap.utilization_by_role.items()}
                bottleneck_roles = [cap.bottleneck_role] if cap.bottleneck_role and not cap.is_feasible else []
                overflow_hours = float(cap.overflow_hours or 0.0)
            except Exception:
                hours_utilization_pct = {r.value: 0.0 for r in hours_by_role.keys()}

            planned_hours_out = {r.value: round(h, 1) for r, h in hours_by_role.items()}

            # Aggregate annual hours/cost across the pool
            totals = (resource_pool or {}).get('totals', {}) or {}
            total_hours_available = float(totals.get('total_hours', 0) or 0)
            total_hours_planned = sum(planned_hours_out.values())
            total_hours_utilization_pct = round(
                (total_hours_planned / total_hours_available * 100), 1
            ) if total_hours_available > 0 else 0.0

            recommendation_text = (
                f"Team is {'within' if hours_feasible else 'over'} capacity. "
                + ("No bottlenecks." if not bottleneck_roles else f"Bottleneck roles: {', '.join(bottleneck_roles)}.")
                + f" {at_risk_count} at-risk accounts need attention."
            )
        except Exception as _cap_err:
            logger.debug("team-capacity hours rollup unavailable: %s", _cap_err)
            planned_hours_out = {}
            total_hours_available = 0.0
            total_hours_planned = 0.0
            total_hours_utilization_pct = 0.0

        capacity_planning = {}
        uncovered_at_risk = []
        try:
            from utils.vpcs_dashboard_helpers import (
                build_capacity_planning,
                build_uncovered_at_risk,
            )
            capacity_planning = build_capacity_planning(int(customer_id), accounts)
            uncovered_at_risk = build_uncovered_at_risk(int(customer_id), accounts)
        except Exception as _vpcs_err:
            logger.debug("VPCS capacity planning unavailable: %s", _vpcs_err)

        return jsonify({
            # ── Legacy fields (preserved for callers that consume them) ──
            'csm_count': csm_count,
            'csm_names': sorted(csm_set),
            'accounts_per_csm': accounts_per_csm,
            'target_per_csm': target_per_csm,
            'total_accounts': len(accounts),
            'active_playbooks': len(active_execs),
            'recent_playbooks_90d': len(recent_execs),
            'active_csm_hours': round(active_csm_hours, 1),
            'at_risk_accounts': at_risk_count,
            'total_arr': total_arr,
            # NOTE: this is the old account-count utilization; kept for
            # back-compat. Frontend should prefer `hours_utilization_pct` /
            # `total_hours_utilization_pct` below.
            'utilization_pct': round(accounts_per_csm / target_per_csm * 100, 1),
            'per_csm_breakdown': per_csm_breakdown,
            # ── Hours-based resource view (new, mirrors MCP get_team_capacity) ──
            'resource_pool': resource_pool,
            'planned_hours': planned_hours_out,
            'hours_utilization_pct': hours_utilization_pct,
            'total_hours_available': total_hours_available,
            'total_hours_planned': total_hours_planned,
            'total_hours_utilization_pct': total_hours_utilization_pct,
            'feasible': hours_feasible,
            'bottleneck_roles': bottleneck_roles,
            'overflow_hours': overflow_hours,
            'recommendation': recommendation_text,
            'capacity_planning': capacity_planning,
            'uncovered_at_risk': uncovered_at_risk,
        })

    except Exception as e:
        logger.error(f"Error computing team capacity: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compute team capacity'}), 500


# =============================================================================
# Renewals Pipeline — accounts with upcoming renewals + risk assessment
# =============================================================================

@dc2s_api.route('/renewals', methods=['GET'])
def get_renewals_api():
    """GET /api/dc2s/renewals?days=90
    Returns accounts with renewal_date within window, sorted by risk.
    Risk = health score × days until renewal.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        days_window = int(request.args.get('days', 90))
        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()

        from datetime import date as _date
        today = _date.today()
        renewals = []

        for acct in accounts:
            meta = acct.profile_metadata or {}
            rd_str = meta.get('renewal_date') or meta.get('contract_renewal_date') or meta.get('contract_end')
            if not rd_str:
                continue
            try:
                rd = datetime.strptime(str(rd_str)[:10], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                continue

            days_until = (rd - today).days
            if days_until < 0 or days_until > days_window:
                continue

            # Get health score
            h, status, _, _ = get_precalculated_scores(acct.account_id)
            health = h or 50

            # Risk level based on health + days
            if health < ht.at_risk_min() and days_until <= 30:
                risk_level = 'critical'
            elif health < ht.healthy_min() and days_until <= 60:
                risk_level = 'high'
            elif health < ht.healthy_min() or days_until <= 30:
                risk_level = 'medium'
            else:
                risk_level = 'low'

            csm = meta.get('assigned_csm') or meta.get('csm_name') or 'Unassigned'
            champion = meta.get('primary_champion_name')

            renewals.append({
                'account_id': acct.account_id,
                'account_name': acct.account_name,
                'arr': float(acct.revenue or 0),
                'health_score': round(health, 1),
                'renewal_date': str(rd),
                'days_until': days_until,
                'risk_level': risk_level,
                'csm_name': csm,
                'champion_name': champion,
                'industry': acct.industry,
            })

        # Sort: critical first, then by days_until ascending
        risk_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        renewals.sort(key=lambda r: (risk_order.get(r['risk_level'], 9), r['days_until']))

        total_arr = sum(r['arr'] for r in renewals)
        critical_count = sum(1 for r in renewals if r['risk_level'] in ('critical', 'high'))
        critical_arr = sum(r['arr'] for r in renewals if r['risk_level'] in ('critical', 'high'))

        return jsonify({
            'renewals': renewals,
            'summary': {
                'total_count': len(renewals),
                'total_arr': total_arr,
                'critical_count': critical_count,
                'critical_arr': critical_arr,
                'days_window': days_window,
            },
        })

    except Exception as e:
        logger.error(f"Error computing renewals: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compute renewals'}), 500


# =============================================================================
# Playbook Success Metrics — aggregated by playbook_id
# =============================================================================

@dc2s_api.route('/playbook-success-metrics', methods=['GET'])
def get_playbook_success_metrics_api():
    """GET /api/dc2s/playbook-success-metrics
    Returns per-playbook execution outcomes, success rates, and ROI.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        try:
            from models import PlaybookExecutionV2
            execs = PlaybookExecutionV2.query.filter_by(customer_id=int(customer_id)).all()
        except Exception:
            execs = []

        if not execs:
            return jsonify({
                'total_executions': 0,
                'playbooks': {},
                'portfolio_summary': {
                    'total_runs': 0,
                    'overall_success_rate_pct': 0,
                    'total_revenue_impact': 0,
                },
            })

        by_pb = defaultdict(list)
        for e in execs:
            by_pb[e.playbook_id].append(e)

        playbooks = {}
        total_resolved = 0
        total_runs = 0
        total_revenue = 0

        for pb_id, pb_execs in by_pb.items():
            n = len(pb_execs)
            resolved = sum(1 for e in pb_execs if e.outcome == 'resolved')
            rev_protected = sum(float(e.revenue_protected or 0) for e in pb_execs)
            rev_expanded = sum(float(e.revenue_expanded or 0) for e in pb_execs)
            health_deltas = [float(e.health_delta or 0) for e in pb_execs if e.health_delta]

            playbooks[pb_id] = {
                'playbook_id': pb_id,
                'total_executions': n,
                'resolved': resolved,
                'success_rate_pct': round(resolved / n * 100, 1) if n else 0,
                'avg_health_delta': round(sum(health_deltas) / len(health_deltas), 1) if health_deltas else 0,
                'total_revenue_protected': rev_protected,
                'total_revenue_expanded': rev_expanded,
            }

            total_resolved += resolved
            total_runs += n
            total_revenue += rev_protected + rev_expanded

        return jsonify({
            'total_executions': total_runs,
            'playbooks': playbooks,
            'portfolio_summary': {
                'total_runs': total_runs,
                'overall_success_rate_pct': round(total_resolved / total_runs * 100, 1) if total_runs else 0,
                'total_revenue_impact': total_revenue,
            },
        })

    except Exception as e:
        logger.error(f"Error computing playbook success metrics: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compute playbook success metrics'}), 500


# =============================================================================
# Health Score History — portfolio trajectory + per-account monthly scores
# =============================================================================

@dc2s_api.route('/health-score-history', methods=['GET'])
def get_health_score_history_api():
    """GET /api/dc2s/health-score-history?account_id=<optional>&months=<optional>
    Returns monthly health score trajectory for portfolio (account_id=0 or omitted)
    or a single account.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        account_id = request.args.get('account_id', 0, type=int)
        months = min(max(request.args.get('months', 6, type=int), 1), 12)

        cutoff = (datetime.utcnow() - timedelta(days=months * 31)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0,
        )

        if account_id and account_id != 0:
            accounts = [Account.query.filter_by(
                account_id=account_id, customer_id=int(customer_id)
            ).first()]
            if not accounts[0]:
                return jsonify({'error': f'Account {account_id} not found'}), 404
        else:
            accounts = Account.query.filter_by(customer_id=int(customer_id)).all()

        if not accounts:
            return jsonify({'error': 'No accounts found'}), 404

        portfolio_history = []
        transitions = []

        for acct in accounts:
            scores = (HealthScore.query
                .filter(
                    HealthScore.account_id == acct.account_id,
                    HealthScore.measurement_month >= cutoff,
                )
                .order_by(HealthScore.measurement_month.asc())
                .all())

            if not scores:
                continue

            monthly = []
            prev_status = None
            for s in scores:
                score_val = float(s.health_score) if s.health_score else 0
                status = ht.classify(score_val)
                change = float(s.change_from_last_month) if s.change_from_last_month else 0

                entry = {
                    'month': s.measurement_month.strftime('%Y-%m'),
                    'health_score': round(score_val, 1),
                    'status': status,
                    'change': round(change, 1),
                    'pillars': s.contributing_pillars or {},
                }
                monthly.append(entry)

                if prev_status and prev_status != status:
                    transitions.append({
                        'account_id': acct.account_id,
                        'account_name': acct.account_name,
                        'month': s.measurement_month.strftime('%Y-%m'),
                        'from_status': prev_status,
                        'to_status': status,
                        'score': round(score_val, 1),
                        'arr': float(acct.revenue or 0),
                    })
                prev_status = status

            if monthly:
                first_score = monthly[0]['health_score']
                last_score = monthly[-1]['health_score']
                portfolio_history.append({
                    'account_id': acct.account_id,
                    'account_name': acct.account_name,
                    'arr': float(acct.revenue or 0),
                    'current_health': last_score,
                    'current_status': monthly[-1]['status'],
                    'starting_health': first_score,
                    'net_change': round(last_score - first_score, 1),
                    'trajectory': (
                        'improving' if last_score - first_score > 5
                        else 'declining' if last_score - first_score < -5
                        else 'stable'
                    ),
                    'monthly_scores': monthly,
                })

        portfolio_history.sort(key=lambda x: x['net_change'])

        improving = [a for a in portfolio_history if a['trajectory'] == 'improving']
        declining = [a for a in portfolio_history if a['trajectory'] == 'declining']
        stable = [a for a in portfolio_history if a['trajectory'] == 'stable']

        turnarounds = [
            {'account': a['account_name'], 'arr': a['arr'], 'change': a['net_change']}
            for a in portfolio_history
            if a.get('current_status') == 'healthy' and a['starting_health'] < ht.healthy_min()
        ]
        deteriorations = [
            {'account': a['account_name'], 'arr': a['arr'], 'change': a['net_change']}
            for a in portfolio_history
            if a['current_health'] < ht.healthy_min() and a['starting_health'] >= ht.healthy_min()
        ]

        # Portfolio trajectory
        total_arr = sum(a['arr'] for a in portfolio_history) or 1
        portfolio_trajectory = {
            'improving_count': len(improving),
            'declining_count': len(declining),
            'stable_count': len(stable),
            'improving_arr_pct': round(sum(a['arr'] for a in improving) / total_arr * 100, 1),
            'declining_arr_pct': round(sum(a['arr'] for a in declining) / total_arr * 100, 1),
        }

        return jsonify({
            'months': months,
            'account_count': len(portfolio_history),
            'accounts': portfolio_history,
            'transitions': transitions,
            'turnarounds': turnarounds,
            'deteriorations': deteriorations,
            'portfolio_trajectory': portfolio_trajectory,
        })

    except Exception as e:
        logger.error(f"Error computing health score history: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compute health score history'}), 500


# Export blueprint
__all__ = ['dc2s_api']
