#!/usr/bin/env python3
"""
DC2_S Configuration API
Endpoints for managing customer KPI configurations including custom KPIs
"""

from flask import Blueprint, request, jsonify
from models import db, CustomerConfig, Customer
from auth_middleware import get_current_customer_id
from utils.config_validator import ConfigValidator
import json
import logging

logger = logging.getLogger(__name__)

dc2s_config_api = Blueprint('dc2s_config_api', __name__, url_prefix='/api/dc2s/config')

# Map bootstrap pillar keys (P1_deployment_velocity, etc.) to P-format codes (P1..P5)
BOOTSTRAP_PILLAR_TO_CODE = {
    'P1_deployment_velocity': 'P1',
    'P2_operational_stability': 'P2',
    'P3_ai_workload_performance': 'P3',
    'P4_channel_partner_health': 'P4',
    'P5_expansion_readiness': 'P5',
}

# Load canonical pillar weights from kpi_definitions (single source of truth)
try:
    from verticals.dc2_s.kpi_definitions import DC2S_PILLARS
    DEFAULT_PILLAR_WEIGHTS = {
        pid: info.get('weight_l2', 0.20)
        for pid, info in DC2S_PILLARS.items()
    }
except ImportError:
    DEFAULT_PILLAR_WEIGHTS = {"P1": 0.15, "P2": 0.20, "P3": 0.25, "P4": 0.15, "P5": 0.25}


def _load_bootstrap_full(customer_id):
    """
    Load full bootstrap weights (pillar + KPI) from customer's journey bootstrap config.
    Returns { 'pillar_weights', 'kpi_weights', 'weights_updated_at' } (ISO timestamp or None).
    """
    try:
        from pathlib import Path
        from datetime import datetime
        backend_dir = Path(__file__).resolve().parent
        base_path = backend_dir / 'verticals' / f'customer{customer_id}-dc2_s' / 'journey'
        bootstrap_file = base_path / 'data' / 'bootstrap' / 'bootstrap_weights_config.json'
        if not bootstrap_file.exists():
            return {'pillar_weights': dict(DEFAULT_PILLAR_WEIGHTS), 'kpi_weights': {}, 'weights_updated_at': None}
        with open(bootstrap_file, 'r') as f:
            data = json.load(f)
        pillar_l2 = data.get('pillar_weights_L2') or data.get('pillar_weights') or {}
        kpi_l1 = data.get('kpi_weights_L1') or data.get('kpi_weights') or {}
        pillar_weights = dict(DEFAULT_PILLAR_WEIGHTS)
        for pillar_key, weight in pillar_l2.items():
            code = BOOTSTRAP_PILLAR_TO_CODE.get(pillar_key)
            if code is not None and isinstance(weight, (int, float)):
                pillar_weights[code] = float(weight)
        kpi_weights = {}
        for pillar_key, kpis in kpi_l1.items():
            code = BOOTSTRAP_PILLAR_TO_CODE.get(pillar_key)
            if code and isinstance(kpis, dict):
                kpi_weights[code] = kpis
        # Last update: from file content (last_updated) or file mtime
        weights_updated_at = data.get('last_updated')
        if not weights_updated_at:
            try:
                mtime = bootstrap_file.stat().st_mtime
                weights_updated_at = datetime.utcfromtimestamp(mtime).strftime('%Y-%m-%dT%H:%M:%SZ')
            except Exception:
                weights_updated_at = None
        return {'pillar_weights': pillar_weights, 'kpi_weights': kpi_weights, 'weights_updated_at': weights_updated_at}
    except Exception:
        return {'pillar_weights': dict(DEFAULT_PILLAR_WEIGHTS), 'kpi_weights': {}, 'weights_updated_at': None}


def _load_bootstrap_kpi_weights(customer_id):
    """Load KPI weights from customer's journey bootstrap config (for backward compat)."""
    data = _load_bootstrap_full(customer_id)
    return data.get('kpi_weights') or {}


# ============================================================
# GET CONFIGURATION
# ============================================================

@dc2s_config_api.route('/', methods=['GET'])
def get_config():
    """Get DC2_S configuration for current customer"""
    try:
        customer_id = get_current_customer_id()
    except Exception as e:
        return jsonify({'error': 'Authentication error', 'message': str(e)}), 401
    
    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    
    if not config or config.vertical != 'dc2_s':
        bootstrap = _load_bootstrap_full(customer_id)
        return jsonify({
            'customer_id': customer_id,
            'is_default': True,
            'weights_source': 'bootstrap',
            'weights_updated_at': bootstrap.get('weights_updated_at'),
            'pillar_weights': bootstrap.get('pillar_weights') or DEFAULT_PILLAR_WEIGHTS,
            'enabled_kpis': [],
            'kpi_overrides': {},
            'kpi_weights': bootstrap.get('kpi_weights') or {},
            'kpi_definitions': {},
            'updated_at': None
        })
    
    # Get KPI definitions from customer config, or populate from DC2S catalog
    kpi_definitions = config.dc2s_kpi_definitions or {}
    if not kpi_definitions:
        try:
            from verticals.dc2_s.kpi_definitions import DC2S_KPIS
            for kpi_code, kpi_info in DC2S_KPIS.items():
                pillar = kpi_info.get('pillar', '')
                target = kpi_info.get('target', {})
                kpi_definitions[kpi_code] = {
                    'name': kpi_info.get('name', kpi_code),
                    'pillar': pillar,
                    'unit': kpi_info.get('unit', '%'),
                    'target': target.get('value') if isinstance(target, dict) else target,
                    'operator': target.get('operator', '>') if isinstance(target, dict) else '>',
                    'higher_is_better': kpi_info.get('higher_is_better', True),
                    'weight_l1': kpi_info.get('weight_l1', 0),
                    'ranges': kpi_info.get('ranges', {}),
                }
        except Exception as e:
            import logging
            logging.warning(f"Could not load KPI definitions from catalog: {e}")
    
    # Single source for read-only tab: either learned (Wizard C) or bootstrap — never mix
    has_learned = config.dc2s_kpi_weights and len(config.dc2s_kpi_weights) > 0
    if has_learned:
        pillar_weights = config.dc2s_pillar_weights or DEFAULT_PILLAR_WEIGHTS
        kpi_weights = config.dc2s_kpi_weights
        weights_source = 'learned'
        weights_updated_at = config.updated_at.isoformat() if config.updated_at else None
    else:
        bootstrap = _load_bootstrap_full(customer_id)
        pillar_weights = bootstrap.get('pillar_weights') or DEFAULT_PILLAR_WEIGHTS
        kpi_weights = bootstrap.get('kpi_weights') or {}
        weights_source = 'bootstrap'
        weights_updated_at = bootstrap.get('weights_updated_at')
    
    return jsonify({
        'customer_id': customer_id,
        'is_default': False,
        'weights_source': weights_source,
        'weights_updated_at': weights_updated_at,
        'pillar_weights': pillar_weights,
        'enabled_kpis': config.dc2s_enabled_kpis or [],
        'kpi_overrides': config.dc2s_kpi_overrides or {},
        'kpi_weights': kpi_weights,
        'kpi_definitions': kpi_definitions,
        'updated_at': config.updated_at.isoformat() if config.updated_at else None,
        'customized_by': config.customized_by
    })


# ============================================================
# DC2_S KPI RANGES (from vertical definitions – correct for Data Center)
# ============================================================

@dc2s_config_api.route('/kpi-ranges', methods=['GET'])
def get_dc2s_kpi_ranges():
    """
    GET /api/dc2s/config/kpi-ranges
    Returns KPI reference ranges from Data Center (DC2_S) vertical definitions.
    These are the correct ranges for Data Center; do not use /api/kpi-reference-ranges
    (legacy SaaS table) for DC2_S.
    """
    try:
        from verticals.dc2_s.kpi_definitions import DC2S_KPIS
    except ImportError as e:
        logger.error(f"DC2_S KPI definitions not available: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'DC2_S KPI definitions not available. Please try again or contact support.'
        }), 500

    ranges = []
    for kpi_code, defn in DC2S_KPIS.items():
        r = defn.get('ranges') or {}
        healthy = r.get('healthy', {})
        risk = r.get('risk', {})
        critical = r.get('critical', {})
        critical_min = critical.get('min')
        critical_max = critical.get('max')
        risk_min = risk.get('min')
        risk_max = risk.get('max')
        healthy_min = healthy.get('min')
        healthy_max = healthy.get('max')
        if critical_min is None and critical_max is None and risk_min is None and risk_max is None and healthy_min is None and healthy_max is None:
            continue
        critical_min = float(critical_min) if critical_min is not None else 0
        critical_max = float(critical_max) if critical_max is not None else 0
        risk_min = float(risk_min) if risk_min is not None else 0
        risk_max = float(risk_max) if risk_max is not None else 0
        healthy_min = float(healthy_min) if healthy_min is not None else 0
        healthy_max = float(healthy_max) if healthy_max is not None else 0
        ranges.append({
            'kpi_code': kpi_code,
            'kpi_name': defn.get('name', kpi_code),
            'unit': defn.get('unit', ''),
            'critical_min': critical_min,
            'critical_max': critical_max,
            'risk_min': risk_min,
            'risk_max': risk_max,
            'healthy_min': healthy_min,
            'healthy_max': healthy_max,
            'higher_is_better': defn.get('higher_is_better', True),
            'source': 'dc2_s_definitions',
            'description': defn.get('description', '')
        })
    ranges.sort(key=lambda x: (x['kpi_code'], x['kpi_name']))
    return jsonify({
        'status': 'success',
        'ranges': ranges,
        'total': len(ranges),
        'source': 'Data Center (DC2_S) vertical definitions'
    })


# ============================================================
# UPDATE CONFIGURATION
# ============================================================

@dc2s_config_api.route('/', methods=['PUT'])
def update_config():
    """Update DC2_S configuration"""
    customer_id = get_current_customer_id()
    data = request.json
    user_email = data.get('user_email', 'system')
    
    # Validate configuration
    validator = ConfigValidator()
    is_valid, errors = validator.validate_full_config(data)
    
    if not is_valid:
        return jsonify({
            'error': 'Configuration validation failed',
            'errors': errors
        }), 400
    
    # Get or create config
    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    
    if not config:
        config = CustomerConfig(
            customer_id=customer_id,
            vertical='dc2_s'
        )
        db.session.add(config)
    
    # Update DC2_S fields
    config.vertical = 'dc2_s'
    config.dc2s_pillar_weights = data.get('pillar_weights')
    config.dc2s_enabled_kpis = data.get('enabled_kpis')
    config.dc2s_kpi_overrides = data.get('kpi_overrides', {})
    config.dc2s_kpi_weights = data.get('kpi_weights')
    config.dc2s_kpi_definitions = data.get('kpi_definitions', {})
    config.customized_by = user_email
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Configuration updated successfully'
    })


# ============================================================
# CUSTOM KPI MANAGEMENT
# ============================================================

@dc2s_config_api.route('/custom-kpi', methods=['POST'])
def add_custom_kpi():
    """Add a custom KPI definition"""
    customer_id = get_current_customer_id()
    data = request.json
    
    kpi_code = data.get('kpi_code')
    kpi_definition = data.get('kpi_definition')
    user_email = data.get('user_email', 'system')
    
    if not kpi_code or not kpi_definition:
        return jsonify({'error': 'kpi_code and kpi_definition required'}), 400
    
    # Validate custom KPI
    validator = ConfigValidator()
    is_valid, errors = validator.validate_custom_kpi(kpi_code, kpi_definition)
    
    if not is_valid:
        return jsonify({
            'error': 'Custom KPI validation failed',
            'errors': errors
        }), 400
    
    # Get or create config
    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    
    if not config:
        config = CustomerConfig(
            customer_id=customer_id,
            vertical='dc2_s',
            dc2s_pillar_weights={"P3": 0.25, "P4": 0.15, "P1": 0.15, "P5": 0.25, "P2": 0.20},
            dc2s_enabled_kpis=[],
            dc2s_kpi_overrides={},
            dc2s_kpi_weights={},
            dc2s_kpi_definitions={}
        )
        db.session.add(config)
    
    # Add custom KPI definition
    kpi_defs = config.dc2s_kpi_definitions or {}
    kpi_defs[kpi_code] = kpi_definition
    config.dc2s_kpi_definitions = kpi_defs
    
    # Add to enabled KPIs if not already present
    enabled = config.dc2s_enabled_kpis or []
    if kpi_code not in enabled:
        enabled.append(kpi_code)
        config.dc2s_enabled_kpis = enabled
    
    # Initialize weight for this KPI in its pillar
    pillar = kpi_definition['pillar']
    kpi_weights = config.dc2s_kpi_weights or {}
    if pillar not in kpi_weights:
        kpi_weights[pillar] = {}
    
    # Set equal weight (will need rebalancing)
    pillar_kpis = [k for k in enabled if k.startswith(f"{pillar}-") or 
                   (k.startswith("CUSTOM-") and kpi_defs.get(k, {}).get('pillar') == pillar)]
    equal_weight = 1.0 / len(pillar_kpis) if pillar_kpis else 1.0
    
    for kpi in pillar_kpis:
        kpi_weights[pillar][kpi] = equal_weight
    
    config.dc2s_kpi_weights = kpi_weights
    config.customized_by = user_email
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'kpi_code': kpi_code,
        'message': 'Custom KPI added successfully',
        'note': 'KPI weights in pillar have been rebalanced equally. Please adjust as needed.'
    })


@dc2s_config_api.route('/custom-kpi/<kpi_code>', methods=['PUT'])
def update_custom_kpi(kpi_code):
    """Update a custom KPI definition"""
    customer_id = get_current_customer_id()
    data = request.json
    
    kpi_definition = data.get('kpi_definition')
    user_email = data.get('user_email', 'system')
    
    if not kpi_definition:
        return jsonify({'error': 'kpi_definition required'}), 400
    
    # Validate
    validator = ConfigValidator()
    is_valid, errors = validator.validate_custom_kpi(kpi_code, kpi_definition)
    
    if not is_valid:
        return jsonify({
            'error': 'Custom KPI validation failed',
            'errors': errors
        }), 400
    
    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    
    if not config:
        return jsonify({'error': 'Customer config not found'}), 404
    
    kpi_defs = config.dc2s_kpi_definitions or {}
    
    if kpi_code not in kpi_defs:
        return jsonify({'error': f'Custom KPI {kpi_code} not found'}), 404
    
    # Update definition
    kpi_defs[kpi_code] = kpi_definition
    config.dc2s_kpi_definitions = kpi_defs
    config.customized_by = user_email
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Custom KPI updated successfully'
    })


@dc2s_config_api.route('/custom-kpi/<kpi_code>', methods=['DELETE'])
def delete_custom_kpi(kpi_code):
    """Delete a custom KPI"""
    customer_id = get_current_customer_id()
    
    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    
    if not config:
        return jsonify({'error': 'Customer config not found'}), 404
    
    # Remove from definitions
    kpi_defs = config.dc2s_kpi_definitions or {}
    if kpi_code in kpi_defs:
        pillar = kpi_defs[kpi_code]['pillar']
        del kpi_defs[kpi_code]
        config.dc2s_kpi_definitions = kpi_defs
    else:
        return jsonify({'error': f'Custom KPI {kpi_code} not found'}), 404
    
    # Remove from enabled
    enabled = config.dc2s_enabled_kpis or []
    if kpi_code in enabled:
        enabled.remove(kpi_code)
        config.dc2s_enabled_kpis = enabled
    
    # Remove from weights and rebalance
    kpi_weights = config.dc2s_kpi_weights or {}
    if pillar in kpi_weights and kpi_code in kpi_weights[pillar]:
        del kpi_weights[pillar][kpi_code]
        
        # Rebalance remaining KPIs in pillar
        remaining_kpis = list(kpi_weights[pillar].keys())
        if remaining_kpis:
            equal_weight = 1.0 / len(remaining_kpis)
            for kpi in remaining_kpis:
                kpi_weights[pillar][kpi] = equal_weight
        
        config.dc2s_kpi_weights = kpi_weights
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Custom KPI deleted successfully'
    })


# ============================================================
# PILLAR WEIGHTS
# ============================================================

@dc2s_config_api.route('/pillar-weights', methods=['PUT'])
def update_pillar_weights():
    """Update only pillar weights"""
    customer_id = get_current_customer_id()
    data = request.json
    
    new_weights = data.get('pillar_weights')
    user_email = data.get('user_email', 'system')
    
    if not new_weights:
        return jsonify({'error': 'pillar_weights required'}), 400
    
    # Validate
    validator = ConfigValidator()
    is_valid, errors = validator.validate_pillar_weights(new_weights)
    
    if not is_valid:
        return jsonify({
            'error': 'Pillar weights validation failed',
            'errors': errors
        }), 400
    
    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    
    if not config:
        return jsonify({'error': 'Customer config not found'}), 404
    
    config.dc2s_pillar_weights = new_weights
    config.customized_by = user_email
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Pillar weights updated successfully',
        'pillar_weights': new_weights
    })


# ============================================================
# WEIGHT HISTORY (for change tracking)
# ============================================================

@dc2s_config_api.route('/weight-history', methods=['GET'])
def get_weight_history():
    """Get weight change history (placeholder - returns empty for now)"""
    try:
        customer_id = get_current_customer_id()
    except Exception as e:
        return jsonify({'error': 'Authentication error', 'message': str(e)}), 401
    
    # TODO: Implement weight history tracking in database
    # For now, return empty array
    return jsonify({
        'history': []
    })


# ============================================================
# HEALTH THRESHOLDS CONFIG (single source of truth)
# ============================================================

@dc2s_config_api.route('/health-thresholds', methods=['GET'])
def get_health_thresholds():
    """
    GET /api/dc2s/config/health-thresholds
    Returns the health score thresholds (healthy/at-risk/critical boundaries).
    Frontend and backend both use this as the single source of truth.
    """
    from utils.health_thresholds import get_thresholds
    return jsonify(get_thresholds())


@dc2s_config_api.route('/health-thresholds', methods=['PUT'])
def update_health_thresholds():
    """
    PUT /api/dc2s/config/health-thresholds
    Update health score thresholds from Settings UI.
    Body: { "healthy_min": 70, "at_risk_min": 50 }
    """
    import os
    from utils.health_thresholds import reload, _CONFIG_PATH

    data = request.get_json()
    healthy_min = data.get('healthy_min')
    at_risk_min = data.get('at_risk_min')

    if healthy_min is None or at_risk_min is None:
        return jsonify({'error': 'healthy_min and at_risk_min are required'}), 400
    if not (0 < at_risk_min < healthy_min <= 100):
        return jsonify({'error': 'Must satisfy 0 < at_risk_min < healthy_min <= 100'}), 400

    # Read current config, update, write back
    with open(_CONFIG_PATH, 'r') as f:
        config = json.load(f)

    config['thresholds']['healthy']['min'] = int(healthy_min)
    config['thresholds']['at_risk']['min'] = int(at_risk_min)

    with open(_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')

    # Reload cached values
    thresholds = reload()

    logger.info(f"Health thresholds updated: healthy>={healthy_min}, at_risk>={at_risk_min}")
    return jsonify(thresholds)
