#!/usr/bin/env python3
"""
DC2_S Vertical API Routes - CORRECTED
Handles dict targets from YOUR Week 1 KPI definitions
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import Account, DC2SKPI, User
from datetime import datetime
import logging

# Import DC2_S vertical modules - matching YOUR file structure
from .kpi_definitions import DC2S_KPIS, DC2S_PILLARS
from .pillar_weights import get_current_weights, get_weights_for_customer
from .vertical_config import determine_customer_phase, PLAYBOOK_CONFIG, should_trigger_playbook
from .metadata_schema import calculate_days_since_deployment

logger = logging.getLogger(__name__)

dc2s_api = Blueprint('dc2s_api', __name__)

# GAP 1.3 / Issue 4: Map DB/customer KPI codes (AI-KPI1, CH-KPI1, ...) to catalog codes (P3-KPI1, P4-KPI1, ...)
# Catalog uses P1-P5; CustomerConfig/onboarding use AI, CH, DV, EX, OS. Pillar mapping: AI→P3, CH→P4, DV→P1, EX→P5, OS→P2
DB_PILLAR_TO_CATALOG = {"AI": "P3", "CH": "P4", "DV": "P1", "EX": "P5", "OS": "P2"}


def _normalize_kpi_code_for_health(kpi_code):
    """Map AI/CH/DV/EX/OS KPI codes to P1-P5 catalog codes so health calculation finds definitions."""
    if kpi_code in DC2S_KPIS:
        return kpi_code
    if "-" in kpi_code:
        parts = kpi_code.split("-", 1)
        if len(parts) == 2 and parts[0] in DB_PILLAR_TO_CATALOG:
            catalog_code = DB_PILLAR_TO_CATALOG[parts[0]] + "-" + parts[1]
            if catalog_code in DC2S_KPIS:
                return catalog_code
    return None


def _sync_journey_phase(account):
    """
    Persist the current journey phase on the Account row.
    Called after every health-score recalculation so playbook triggers
    that depend on lifecycle phase always have fresh data.
    """
    try:
        metadata = account.profile_metadata or {}
        deployment_date = metadata.get("deployment_date", "")
        days = calculate_days_since_deployment(deployment_date) if deployment_date else 0
        account_data = {**metadata, "days_since_deployment": days}
        new_phase = determine_customer_phase(account_data)
        if account.journey_phase != new_phase:
            logger.info(
                "Account %s journey_phase %s -> %s",
                account.account_id, account.journey_phase, new_phase,
            )
            account.journey_phase = new_phase
            db.session.add(account)
            db.session.commit()
    except Exception as exc:
        logger.warning("Failed to sync journey_phase for account %s: %s", account.account_id, exc)
        db.session.rollback()


def calculate_kpi_health(kpi_values, customer_id=None):
    """
    Calculate health score from KPI values using config-aware weights when possible.
    When customer_id is provided and CustomerConfig (dc2_s) exists, uses DB pillar weights;
    otherwise falls back to code default weights (logged explicitly).
    Normalizes AI/CH/DV/EX/OS KPI codes to P1-P5 catalog codes (GAP 1.3).
    """
    # Config-aware: use CustomerConfig.dc2s_pillar_weights when customer_id provided
    weights = get_weights_for_customer(customer_id) if customer_id is not None else get_current_weights()
    
    # Normalize kpi codes (AI-KPI1 → P3-KPI1 etc.) so catalog lookup works
    kpi_values_for_calc = {}
    for kpi_code, value in kpi_values.items():
        lookup_code = _normalize_kpi_code_for_health(kpi_code)
        if lookup_code:
            kpi_values_for_calc[lookup_code] = value
    kpi_values = kpi_values_for_calc
    
    # Group KPIs by pillar
    pillar_scores = {}
    
    for kpi_code, value in kpi_values.items():
        if kpi_code not in DC2S_KPIS:
            continue
            
        kpi_def = DC2S_KPIS[kpi_code]
        pillar = kpi_def.get('pillar', kpi_def.get('l1_category'))
        
        if pillar not in pillar_scores:
            pillar_scores[pillar] = {'total': 0, 'count': 0}
        
        # Extract target - handle dict or simple number
        target_raw = kpi_def.get('target', 100)
        if isinstance(target_raw, dict):
            target = target_raw.get('value', 100)
            operator = target_raw.get('operator', '>')
        else:
            target = target_raw
            operator = '>'
        
        # Simple scoring: closer to target = higher score
        if target and target > 0:
            if operator == '<':
                # Lower is better
                score = min(100, (target / max(value, 0.01)) * 100)
            else:
                # Higher is better (default)
                score = min(100, (value / target) * 100)
        else:
            score = value
        
        pillar_scores[pillar]['total'] += score
        pillar_scores[pillar]['count'] += 1
    
    # Calculate pillar averages
    pillar_averages = {}
    for pillar, data in pillar_scores.items():
        if data['count'] > 0:
            pillar_averages[pillar] = data['total'] / data['count']
        else:
            pillar_averages[pillar] = 0
    
    # Calculate overall weighted health
    overall_health = 0
    total_weight = 0
    
    for pillar, score in pillar_averages.items():
        # Get weight from your L2 weights structure
        weight = weights.get(pillar, {}).get('weight', 0.2)  # Default 0.2 if not found
        overall_health += score * weight
        total_weight += weight
    
    if total_weight > 0:
        overall_health = overall_health / total_weight
    
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
            Account.vertical == 'dc2_s'
        ).all()
        
        logger.info(f"[DEBUG /api/dc2s/accounts] Found {len(accounts)} accounts for customer {customer_id}")
        if accounts:
            logger.info(f"[DEBUG /api/dc2s/accounts] Account IDs: {[a.account_id for a in accounts[:5]]}")
        
        results = []
        for account in accounts:
            # Get latest KPIs
            kpis = DC2SKPI.query.filter_by(
                account_id=account.account_id
            ).order_by(DC2SKPI.measured_at.desc()).all()
            
            # Get latest measurement time
            latest_kpis = {}
            if kpis:
                latest_time = kpis[0].measured_at
                latest_kpis = {
                    kpi.kpi_code: float(kpi.value) 
                    for kpi in kpis 
                    if kpi.measured_at == latest_time
                }
            
            # Calculate health scores (config-aware: uses CustomerConfig.dc2s_pillar_weights when set)
            overall_health, pillar_scores = calculate_kpi_health(latest_kpis, customer_id=customer_id)

            # Phase 0.2: persist journey_phase on every health recalculation
            _sync_journey_phase(account)

            # Determine status
            if overall_health >= 80:
                status = 'healthy'
            elif overall_health >= 60:
                status = 'risk'
            else:
                status = 'critical'
            
            results.append({
                'account_id': account.account_id,
                'account_name': account.account_name,
                'industry': account.industry,
                'region': account.region,
                'overall_health': round(overall_health, 1),
                'status': status,
                'pillar_scores': {k: round(v, 1) for k, v in pillar_scores.items()},
                'metadata': account.profile_metadata or {},
                'kpi_count': len(latest_kpis),
                'last_measured': latest_time.isoformat() if kpis else None
            })
        
        return jsonify({
            'accounts': results,
            'total': len(results)
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
            vertical='dc2_s'
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Get all KPIs for this account
        kpis = DC2SKPI.query.filter_by(
            account_id=account_id
        ).order_by(DC2SKPI.measured_at.desc()).all()
        
        # Get latest KPIs
        latest_kpis = {}
        if kpis:
            latest_time = kpis[0].measured_at
            latest_kpis = {
                kpi.kpi_code: float(kpi.value) 
                for kpi in kpis 
                if kpi.measured_at == latest_time
            }
        
        # Calculate health (config-aware: uses CustomerConfig.dc2s_pillar_weights when set)
        overall_health, pillar_scores = calculate_kpi_health(latest_kpis, customer_id=customer_id)

        # Phase 0.2: persist journey_phase on every health recalculation
        _sync_journey_phase(account)

        # Group KPIs by pillar
        kpis_by_pillar = {}
        for kpi_code, value in latest_kpis.items():
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
                    'value': value,
                    'target': target_value,
                    'unit': kpi_def.get('unit', ''),
                })
        
        return jsonify({
            'account_id': account.account_id,
            'account_name': account.account_name,
            'industry': account.industry,
            'region': account.region,
            'vertical': account.vertical,
            'overall_health': round(overall_health, 1),
            'pillar_scores': {k: round(v, 1) for k, v in pillar_scores.items()},
            'kpis_by_pillar': kpis_by_pillar,
            'metadata': account.profile_metadata or {},
            'total_kpis': len(latest_kpis),
            'last_measured': kpis[0].measured_at.isoformat() if kpis else None
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
            vertical='dc2_s'
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
            Account.vertical == 'dc2_s'
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
            
            # Get KPI definition
            kpi_def = DC2S_KPIS.get(kpi_code, {})
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
            vertical='dc2_s'
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
        
        return jsonify({
            'account_id': account_id,
            'account_name': account.account_name,
            'alerts': alerts,
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
            vertical='dc2_s'
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

        # Determine current journey phase
        _sync_journey_phase(account)
        current_phase = account.journey_phase or "deployment"

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

                # Assign priority: critical if overall health < 50 or
                # if the playbook has human_approval_required (high-value)
                if overall_health < 50:
                    priority = "critical"
                elif pb_cfg.get("human_approval_required"):
                    priority = "high"
                elif overall_health < 70:
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
            vertical='dc2_s'
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

        # Determine health status based on overall score
        if overall_health >= 70:
            health_status = 'healthy'
        elif overall_health >= 50:
            health_status = 'at_risk'
        else:
            health_status = 'critical'
        
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
            Account.vertical == 'dc2_s'
        ).all()
        
        health_scores = []
        healthy_count = 0
        risk_count = 0
        critical_count = 0
        
        for account in accounts:
            # Get latest KPIs
            kpis = DC2SKPI.query.filter_by(
                account_id=account.account_id
            ).order_by(DC2SKPI.measured_at.desc()).all()
            
            if kpis:
                latest_time = kpis[0].measured_at
                latest_kpis = {
                    kpi.kpi_code: float(kpi.value) 
                    for kpi in kpis 
                    if kpi.measured_at == latest_time
                }
                
                health, _ = calculate_kpi_health(latest_kpis, customer_id=customer_id)
                health_scores.append(health)
                
                if health >= 80:
                    healthy_count += 1
                elif health >= 60:
                    risk_count += 1
                else:
                    critical_count += 1
        
        avg_health = sum(health_scores) / len(health_scores) if health_scores else 0
        
        return jsonify({
            'total_accounts': len(accounts),
            'average_health': round(avg_health, 1),
            'healthy_accounts': healthy_count,
            'risk_accounts': risk_count,
            'critical_accounts': critical_count,
            'health_distribution': {
                'healthy': healthy_count,
                'risk': risk_count,
                'critical': critical_count
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching DC2_S health summary: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch health summary'}), 500


# Export blueprint
__all__ = ['dc2s_api']
