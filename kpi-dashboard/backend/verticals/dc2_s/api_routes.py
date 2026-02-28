#!/usr/bin/env python3
"""
DC2_S Vertical API Routes - CORRECTED
Handles dict targets from YOUR Week 1 KPI definitions
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import Account, DC2SKPI, User, PlaybookExecution, PlaybookReport
from datetime import datetime
import logging
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


# ============================================================
# DC PLAYBOOK ENDPOINTS
# ============================================================

# In-memory store for DC playbook executions (mirrors pattern from playbook_execution_api.py)
_dc_executions = {}  # execution_id -> execution_data


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
    Start a new DC playbook execution.
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

        # Verify account
        account = Account.query.filter_by(
            account_id=account_id, customer_id=int(customer_id), vertical='dc2_s'
        ).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404

        # Snapshot current KPI values for before/after comparison
        all_kpis = DC2SKPI.query.filter_by(account_id=account_id).order_by(DC2SKPI.measured_at.desc()).all()
        kpi_snapshot = {}
        for kpi in all_kpis:
            if kpi.kpi_code not in kpi_snapshot:
                kpi_snapshot[kpi.kpi_code] = float(kpi.value)

        execution_id = f"dc-exec-{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()

        # Build step tracking from sub_components
        steps = []
        for sc in pb_cfg.get('sub_components', []):
            steps.append({
                'step_id': sc['id'],
                'name': sc['name'],
                'description': sc.get('description', ''),
                'estimated_hours': sc.get('estimated_hours', 0),
                'actual_hours': None,
                'status': 'pending',
                'notes': '',
                'started_at': None,
                'completed_at': None,
            })

        total_estimated = sum(s['estimated_hours'] for s in steps)

        execution = {
            'execution_id': execution_id,
            'playbook_id': playbook_id,
            'playbook_name': pb_cfg['name'],
            'account_id': account_id,
            'account_name': account.account_name,
            'customer_id': int(customer_id),
            'status': 'in-progress',
            'current_step': steps[0]['step_id'] if steps else None,
            'started_at': now.isoformat(),
            'completed_at': None,
            'steps': steps,
            'total_estimated_hours': total_estimated,
            'total_actual_hours': 0,
            'kpi_snapshot_before': kpi_snapshot,
            'phase': (account.profile_metadata or {}).get('journey_phase', 'deployment'),
        }

        _dc_executions[execution_id] = execution

        # Persist to DB
        try:
            db_exec = PlaybookExecution(
                execution_id=execution_id,
                customer_id=int(customer_id),
                account_id=account_id,
                playbook_id=playbook_id,
                status='in-progress',
                current_step=execution['current_step'],
                execution_data=execution,
                started_at=now,
                execution_mode='dc_playbook',
            )
            db.session.add(db_exec)
            db.session.commit()
        except Exception as db_err:
            logger.warning(f"DB persist failed for DC execution {execution_id}: {db_err}")
            db.session.rollback()

        return jsonify({'status': 'success', 'execution': execution}), 201

    except Exception as e:
        logger.error(f"Error creating DC playbook execution: {e}", exc_info=True)
        return jsonify({'error': 'Failed to create execution'}), 500


@dc2s_api.route('/playbooks/executions', methods=['GET'])
def list_dc2s_playbook_executions():
    """
    List DC playbook executions. Filters: status, account_id, playbook_id
    GET /api/dc2s/playbooks/executions?status=in-progress&account_id=101
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        status_filter = request.args.get('status')
        account_filter = request.args.get('account_id')
        playbook_filter = request.args.get('playbook_id')

        # Merge in-memory with DB (in-memory is authoritative for active executions)
        # Load from DB if memory is empty
        if not _dc_executions:
            try:
                db_execs = PlaybookExecution.query.filter(
                    PlaybookExecution.customer_id == int(customer_id),
                    PlaybookExecution.execution_mode == 'dc_playbook',
                ).order_by(PlaybookExecution.started_at.desc()).all()
                for dbe in db_execs:
                    if dbe.execution_id not in _dc_executions and dbe.execution_data:
                        _dc_executions[dbe.execution_id] = dbe.execution_data
            except Exception:
                pass

        results = []
        for exec_id, ex in _dc_executions.items():
            if ex.get('customer_id') != int(customer_id):
                continue
            if status_filter and ex.get('status') != status_filter:
                continue
            if account_filter and str(ex.get('account_id')) != str(account_filter):
                continue
            if playbook_filter and ex.get('playbook_id') != playbook_filter:
                continue

            completed_steps = sum(1 for s in ex.get('steps', []) if s['status'] == 'completed')
            total_steps = len(ex.get('steps', []))
            results.append({
                'execution_id': exec_id,
                'playbook_id': ex.get('playbook_id'),
                'playbook_name': ex.get('playbook_name'),
                'account_id': ex.get('account_id'),
                'account_name': ex.get('account_name'),
                'status': ex.get('status'),
                'started_at': ex.get('started_at'),
                'completed_at': ex.get('completed_at'),
                'steps_completed': completed_steps,
                'total_steps': total_steps,
                'total_estimated_hours': ex.get('total_estimated_hours', 0),
                'total_actual_hours': ex.get('total_actual_hours', 0),
                'progress': round(completed_steps / total_steps * 100) if total_steps else 0,
            })

        results.sort(key=lambda x: x.get('started_at', ''), reverse=True)
        return jsonify({'executions': results, 'total': len(results)})

    except Exception as e:
        logger.error(f"Error listing DC playbook executions: {e}", exc_info=True)
        return jsonify({'error': 'Failed to list executions'}), 500


@dc2s_api.route('/playbooks/executions/<execution_id>', methods=['GET'])
def get_dc2s_playbook_execution(execution_id):
    """
    Get DC playbook execution detail with all steps and hours.
    GET /api/dc2s/playbooks/executions/<execution_id>
    """
    try:
        execution = _dc_executions.get(execution_id)

        # Fallback to DB
        if not execution:
            db_exec = PlaybookExecution.query.filter_by(execution_id=execution_id).first()
            if db_exec and db_exec.execution_data:
                execution = db_exec.execution_data
                _dc_executions[execution_id] = execution

        if not execution:
            return jsonify({'error': 'Execution not found'}), 404

        return jsonify({'execution': execution})

    except Exception as e:
        logger.error(f"Error fetching DC execution: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch execution'}), 500


@dc2s_api.route('/playbooks/executions/<execution_id>/steps/<step_id>', methods=['PUT'])
def update_dc2s_playbook_step(execution_id, step_id):
    """
    Update a step's status, actual hours, and notes.
    PUT /api/dc2s/playbooks/executions/<execution_id>/steps/<step_id>
    Body: { status, actual_hours, notes }
    """
    try:
        execution = _dc_executions.get(execution_id)
        if not execution:
            db_exec = PlaybookExecution.query.filter_by(execution_id=execution_id).first()
            if db_exec and db_exec.execution_data:
                execution = db_exec.execution_data
                _dc_executions[execution_id] = execution
        if not execution:
            return jsonify({'error': 'Execution not found'}), 404

        data = request.get_json() or {}
        now = datetime.utcnow().isoformat()

        step_found = False
        for step in execution.get('steps', []):
            if step['step_id'] == step_id:
                step_found = True
                if 'status' in data:
                    old_status = step['status']
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

        # Recalculate totals
        execution['total_actual_hours'] = sum(
            s.get('actual_hours') or 0 for s in execution.get('steps', [])
        )

        # Update current_step to next pending step
        for step in execution.get('steps', []):
            if step['status'] in ('pending', 'in-progress'):
                execution['current_step'] = step['step_id']
                break

        # Persist to DB
        try:
            db_exec = PlaybookExecution.query.filter_by(execution_id=execution_id).first()
            if db_exec:
                db_exec.execution_data = execution
                db_exec.current_step = execution.get('current_step')
                db.session.commit()
        except Exception as db_err:
            logger.warning(f"DB update failed for step {step_id}: {db_err}")
            db.session.rollback()

        return jsonify({'status': 'success', 'execution': execution})

    except Exception as e:
        logger.error(f"Error updating DC playbook step: {e}", exc_info=True)
        return jsonify({'error': 'Failed to update step'}), 500


@dc2s_api.route('/playbooks/executions/<execution_id>/complete', methods=['PUT'])
def complete_dc2s_playbook_execution(execution_id):
    """
    Complete a DC playbook execution, generate report, and save to PlaybookReport table.
    PUT /api/dc2s/playbooks/executions/<execution_id>/complete
    """
    try:
        customer_id = get_current_customer_id()
        execution = _dc_executions.get(execution_id)
        if not execution:
            db_exec = PlaybookExecution.query.filter_by(execution_id=execution_id).first()
            if db_exec and db_exec.execution_data:
                execution = db_exec.execution_data
                _dc_executions[execution_id] = execution
        if not execution:
            return jsonify({'error': 'Execution not found'}), 404

        now = datetime.utcnow()
        execution['status'] = 'completed'
        execution['completed_at'] = now.isoformat()

        # Get current KPI values for after-snapshot
        account_id = execution.get('account_id')
        kpi_snapshot_after = {}
        if account_id:
            all_kpis = DC2SKPI.query.filter_by(account_id=account_id).order_by(DC2SKPI.measured_at.desc()).all()
            for kpi in all_kpis:
                if kpi.kpi_code not in kpi_snapshot_after:
                    kpi_snapshot_after[kpi.kpi_code] = float(kpi.value)

        # Build hours tracking
        steps_tracking = []
        for step in execution.get('steps', []):
            est = step.get('estimated_hours', 0)
            act = step.get('actual_hours') or 0
            steps_tracking.append({
                'step_id': step['step_id'],
                'name': step['name'],
                'estimated_hours': est,
                'actual_hours': act,
                'variance': round(act - est, 1),
                'status': step['status'],
                'notes': step.get('notes', ''),
            })

        total_est = execution.get('total_estimated_hours', 0)
        total_act = execution.get('total_actual_hours', 0)
        variance_hrs = round(total_act - total_est, 1)
        variance_pct = round((variance_hrs / total_est) * 100, 1) if total_est else 0

        if variance_pct <= -10:
            efficiency = 'Under Budget'
        elif variance_pct <= 10:
            efficiency = 'On Budget'
        else:
            efficiency = 'Over Budget'

        # Build KPI impact from before/after snapshots
        pb_cfg = get_playbook_config(execution.get('playbook_id', ''))
        trigger_kpis_impact = []
        before_snap = execution.get('kpi_snapshot_before', {})
        for trigger_kpi in (pb_cfg or {}).get('trigger_kpis', []):
            # Normalize code
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

            # Determine if target was met
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

        # Health score before/after
        health_before, _ = calculate_kpi_health(before_snap, customer_id=customer_id)
        health_after, _ = calculate_kpi_health(kpi_snapshot_after, customer_id=customer_id)

        # Build RACI (generic for DC playbooks based on step types)
        raci = {}
        for step in execution.get('steps', []):
            raci[step['name']] = {
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

        # Duration
        started = datetime.fromisoformat(execution['started_at']) if execution.get('started_at') else now
        duration_days = (now - started).days

        playbook_name = execution.get('playbook_name', '')
        account_name = execution.get('account_name', '')

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

        # Build full report
        report_data = {
            'execution_id': execution_id,
            'playbook_id': execution.get('playbook_id'),
            'playbook_name': playbook_name,
            'account_id': account_id,
            'account_name': account_name,
            'phase': execution.get('phase', ''),
            'status': 'Completed',
            'started_at': execution.get('started_at'),
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
        }

        # Save to PlaybookReport table (makes it queryable by AI Insights)
        try:
            completed_count = sum(1 for s in steps_tracking if s['status'] == 'completed')
            db_report = PlaybookReport(
                execution_id=execution_id,
                customer_id=int(customer_id) if customer_id else execution.get('customer_id'),
                account_id=account_id,
                playbook_id=execution.get('playbook_id'),
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

            # Update execution status in DB
            db_exec = PlaybookExecution.query.filter_by(execution_id=execution_id).first()
            if db_exec:
                db_exec.status = 'completed'
                db_exec.completed_at = now
                db_exec.execution_data = execution
                db_exec.outcome = 'resolved'

            db.session.commit()
            logger.info(f"DC playbook report saved for {execution_id}")
        except Exception as db_err:
            logger.warning(f"DB persist failed for DC report {execution_id}: {db_err}")
            db.session.rollback()

        return jsonify({'status': 'success', 'report': report_data})

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
    if health_score < 50:
        trend_component = 30
    elif health_score < 70:
        trend_component = 20
    else:
        trend_component = 5

    # Expansion opportunity (20%)
    expansion_component = min(expansion_prob, 100) * 0.2

    # Weakest pillar severity (10%)
    weakest = min(pillar_averages.values()) if pillar_averages else 50
    if weakest < 50:
        pillar_component = 10
    elif weakest < 70:
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
    """Classify urgency: critical / high / opportunity / medium."""
    if churn_prob > 70 or health_score < 40:
        return 'critical'
    if health_score < 70:
        return 'high'
    if expansion_prob > 75 and health_score > 80:
        return 'opportunity'
    return 'medium'


@dc2s_api.route('/daily-actions', methods=['GET'])
def get_csm_daily_actions():
    """
    CSM Daily Action List — returns top-10 prioritised actions.
    GET /api/dc2s/daily-actions
    Scoring: Priority Index = (impact * 0.6 * arr_weight) - (effort * 0.4)
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        # 1. Fetch all DC accounts
        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
            Account.vertical == 'dc2_s'
        ).all()

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

        for account in accounts:
            # 2. Get latest KPIs
            kpis = DC2SKPI.query.filter_by(
                account_id=account.account_id
            ).order_by(DC2SKPI.measured_at.desc()).all()

            latest_kpis = {}
            if kpis:
                latest_time = kpis[0].measured_at
                latest_kpis = {
                    kpi.kpi_code: float(kpi.value)
                    for kpi in kpis
                    if kpi.measured_at == latest_time
                }

            # Calculate health
            overall_health, pillar_averages = calculate_kpi_health(latest_kpis, customer_id=customer_id)

            # Normalize KPI codes for playbook trigger evaluation
            normalized_kpis = {}
            for code, val in latest_kpis.items():
                norm = _normalize_kpi_code_for_health(code)
                if norm:
                    normalized_kpis[norm] = val
            # Also add OVERALL_HEALTH for PB-05 trigger
            normalized_kpis['OVERALL_HEALTH'] = overall_health

            # ARR weight (0.5-1.5): boost high-value accounts
            arr = (account.profile_metadata or {}).get('arr', 0) or (account.profile_metadata or {}).get('revenue', 0) or 0
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

            # Churn / expansion estimates from health
            churn_prob = 80 if overall_health < 50 else (40 if overall_health < 70 else 15)
            expansion_prob_val = 75 if overall_health > 80 else (30 if overall_health > 60 else 5)

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
                    })

            # 4. Non-playbook actions

            # Health check follow-up (accounts with health < 60)
            if overall_health < 60:
                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 20  # Low effort: just a review call
                priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                all_actions.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'action_title': 'Health Check Follow-up',
                    'action_description': f'Health score at {overall_health:.0f}. Schedule intervention call.',
                    'action_type': 'follow_up',
                    'related_playbook_id': None,
                    'urgency': _determine_urgency(overall_health, churn_prob, expansion_prob_val),
                    'impact_score': impact,
                    'effort_score': effort,
                    'priority_index': priority_index,
                    'account_health': round(overall_health, 1),
                    'estimated_hours': 2,
                    'estimated_duration_display': '1 day',
                })

            # QBR scheduling (P4-KPI3 < target 3)
            qbr_val = normalized_kpis.get('P4-KPI3')
            if qbr_val is not None and qbr_val < 3:
                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 25
                priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
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
                })

            # Expansion call (P5-KPI7 > 70%)
            if exp_kpi is not None and exp_kpi > 70:
                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 30
                priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
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
                })

        # 5. Sort by priority_index DESC, take top 10
        all_actions.sort(key=lambda a: a['priority_index'], reverse=True)
        top_actions = all_actions[:10]

        # Assign rank and id
        for i, action in enumerate(top_actions, 1):
            action['rank'] = i
            action['id'] = f"act-{i:03d}"

        # Summary
        urgency_counts = {'critical': 0, 'high': 0, 'opportunity': 0, 'medium': 0}
        total_hours = 0
        for a in top_actions:
            urgency_counts[a.get('urgency', 'medium')] = urgency_counts.get(a.get('urgency', 'medium'), 0) + 1
            total_hours += a.get('estimated_hours', 0)

        return jsonify({
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'actions': top_actions,
            'summary': {
                'total_actions': len(top_actions),
                'critical_count': urgency_counts.get('critical', 0),
                'high_count': urgency_counts.get('high', 0),
                'opportunity_count': urgency_counts.get('opportunity', 0),
                'total_estimated_hours': total_hours
            }
        })

    except Exception as e:
        logger.error(f"Error computing daily actions: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compute daily actions'}), 500


# Export blueprint
__all__ = ['dc2s_api']
