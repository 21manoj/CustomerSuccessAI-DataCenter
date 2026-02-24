#!/usr/bin/env python3
"""
Account-level Wizard Configuration Manager
Three-tier config resolution: account → customer → catalog defaults
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from extensions import db
from models import AccountWizardConfig, CustomerConfig, Account

logger = logging.getLogger(__name__)

# ── Template directory (shared scripts, no customer-stamped paths) ──
BACKEND_DIR = Path(__file__).parent.parent
TEMPLATE_DIR = BACKEND_DIR / "verticals" / "customer9-dc2_s"


def _get_catalog_defaults() -> Dict:
    """Tier 3: Catalog defaults from kpi_definitions.py"""
    try:
        from verticals.dc2_s.kpi_definitions import DC2S_KPIS, DC2S_PILLARS
        pillar_weights = {
            code: info.get('weight_l2', 0.20)
            for code, info in DC2S_PILLARS.items()
        }
        enabled_kpis = list(DC2S_KPIS.keys())
    except ImportError:
        pillar_weights = {'AI': 0.25, 'CH': 0.20, 'DV': 0.15, 'EX': 0.20, 'OS': 0.20}
        enabled_kpis = []

    return {
        'pillar_weights': pillar_weights,
        'enabled_kpis': enabled_kpis,
        'pattern_mix': {"crisis": 0.15, "churn": 0.15, "stable": 0.50, "expansion": 0.20},
        'kpi_overrides': {},
        'source': 'catalog',
    }


def _get_customer_config(customer_id: int) -> Optional[Dict]:
    """Tier 2: Customer-level config from CustomerConfig table"""
    cfg = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    if not cfg:
        return None
    return {
        'pillar_weights': cfg.dc2s_pillar_weights,
        'enabled_kpis': cfg.dc2s_enabled_kpis,
        'kpi_overrides': cfg.dc2s_kpi_overrides,
        'kpi_weights': cfg.dc2s_kpi_weights,
        'source': 'customer',
    }


def get_effective_config(account_id: int, customer_id: int, wizard_type: str = 'a') -> Dict:
    """
    Resolve effective config for a wizard run using three-tier inheritance.

    Priority: account override (if flag set) → customer config → catalog defaults.
    Returns a merged dict with a 'source' key indicating provenance.
    """
    catalog = _get_catalog_defaults()
    customer = _get_customer_config(customer_id) or {}
    account_cfg = AccountWizardConfig.query.filter_by(account_id=account_id).first()

    # Start from catalog, overlay customer, then account
    merged = {**catalog}

    # Tier 2 — customer overrides
    if customer:
        for key in ('pillar_weights', 'enabled_kpis', 'kpi_overrides', 'kpi_weights'):
            if customer.get(key):
                merged[key] = customer[key]
        merged['source'] = 'customer'

    # Tier 1 — account overrides (only if flag is set)
    if account_cfg:
        flag_key = f'is_wizard_{wizard_type}_override'
        if getattr(account_cfg, flag_key, False):
            if wizard_type == 'a':
                if account_cfg.wizard_a_pillar_weights:
                    merged['pillar_weights'] = account_cfg.wizard_a_pillar_weights
                if account_cfg.wizard_a_kpi_overrides:
                    merged['kpi_overrides'] = account_cfg.wizard_a_kpi_overrides
                if account_cfg.wizard_a_pattern_mix:
                    merged['pattern_mix'] = account_cfg.wizard_a_pattern_mix
            elif wizard_type == 'b':
                if account_cfg.wizard_b_custom_rules:
                    merged['custom_rules'] = account_cfg.wizard_b_custom_rules
            elif wizard_type == 'c':
                if account_cfg.wizard_c_manual_overrides:
                    merged['manual_overrides'] = account_cfg.wizard_c_manual_overrides
                if account_cfg.wizard_c_learned_weights:
                    merged['learned_weights'] = account_cfg.wizard_c_learned_weights
            merged['source'] = 'account'

    merged['account_id'] = account_id
    merged['customer_id'] = customer_id
    return merged


def get_or_create_account_config(account_id: int, customer_id: int) -> AccountWizardConfig:
    """Return existing AccountWizardConfig or create a new default row."""
    cfg = AccountWizardConfig.query.filter_by(account_id=account_id).first()
    if cfg:
        return cfg
    cfg = AccountWizardConfig(account_id=account_id, customer_id=customer_id)
    db.session.add(cfg)
    db.session.flush()
    return cfg


def save_account_override(account_id: int, customer_id: int, wizard_type: str, config_data: Dict) -> AccountWizardConfig:
    """Save account-level override for a wizard and set the override flag."""
    cfg = get_or_create_account_config(account_id, customer_id)
    flag_attr = f'is_wizard_{wizard_type}_override'
    setattr(cfg, flag_attr, True)

    if wizard_type == 'a':
        if 'pattern_mix' in config_data:
            cfg.wizard_a_pattern_mix = config_data['pattern_mix']
        if 'kpi_overrides' in config_data:
            cfg.wizard_a_kpi_overrides = config_data['kpi_overrides']
        if 'pillar_weights' in config_data:
            cfg.wizard_a_pillar_weights = config_data['pillar_weights']
    elif wizard_type == 'b':
        if 'custom_rules' in config_data:
            cfg.wizard_b_custom_rules = config_data['custom_rules']
    elif wizard_type == 'c':
        if 'manual_overrides' in config_data:
            cfg.wizard_c_manual_overrides = config_data['manual_overrides']
        if 'learned_weights' in config_data:
            cfg.wizard_c_learned_weights = config_data['learned_weights']

    db.session.commit()
    return cfg


def reset_to_customer(account_id: int, wizard_type: str):
    """Clear account override, fall back to customer config."""
    cfg = AccountWizardConfig.query.filter_by(account_id=account_id).first()
    if cfg:
        setattr(cfg, f'is_wizard_{wizard_type}_override', False)
        db.session.commit()


def track_run(account_id: int, customer_id: int, wizard_type: str, status: str, message: str = ''):
    """Record wizard execution result."""
    cfg = get_or_create_account_config(account_id, customer_id)
    setattr(cfg, f'wizard_{wizard_type}_last_run', datetime.utcnow())
    setattr(cfg, f'wizard_{wizard_type}_last_status', status)
    setattr(cfg, f'wizard_{wizard_type}_last_message', message)
    db.session.commit()


def get_wizard_status_for_customer(customer_id: int) -> List[Dict]:
    """Get wizard run status for all accounts belonging to a customer."""
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    result = []
    for acct in accounts:
        cfg = AccountWizardConfig.query.filter_by(account_id=acct.account_id).first()
        row = {
            'account_id': acct.account_id,
            'account_name': acct.account_name,
            'wizard_a': {'last_run': None, 'status': None, 'override': False},
            'wizard_b': {'last_run': None, 'status': None, 'override': False},
            'wizard_c': {'last_run': None, 'status': None, 'override': False},
        }
        if cfg:
            for wiz in ('a', 'b', 'c'):
                lr = getattr(cfg, f'wizard_{wiz}_last_run', None)
                row[f'wizard_{wiz}'] = {
                    'last_run': lr.isoformat() if lr else None,
                    'status': getattr(cfg, f'wizard_{wiz}_last_status', None),
                    'override': getattr(cfg, f'is_wizard_{wiz}_override', False),
                }
        result.append(row)
    return result


def resolve_template_dir() -> Path:
    """Return the shared template directory for wizard scripts."""
    if TEMPLATE_DIR.exists():
        return TEMPLATE_DIR
    # Fallback: look for any customer directory
    verticals_dir = BACKEND_DIR / "verticals"
    for d in sorted(verticals_dir.iterdir()):
        if d.is_dir() and d.name.startswith('customer') and d.name.endswith('-dc2_s'):
            return d
    raise FileNotFoundError("No DC2_S template directory found under verticals/")


def write_config_file(config: Dict, account_id: int, wizard_type: str) -> Path:
    """Write merged config to a temp JSON file for wizard scripts to consume."""
    runs_dir = BACKEND_DIR / "verticals" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    config_path = runs_dir / f"account_{account_id}_wizard_{wizard_type}_{timestamp}.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2, default=str)
    return config_path
