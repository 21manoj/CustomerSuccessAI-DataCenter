#!/usr/bin/env python3
"""
Three-Tier Config Resolver
===========================

Resolves configuration by merging three layers (highest priority wins):
  1. AccountConfigOverride   (if account_id provided + overridable type)
  2. CustomerVerticalConfig   (customer-level override)
  3. VerticalTemplate         (base template for the vertical)

Usage:
    from utils.config_resolver import resolve_config
    cfg = resolve_config(customer_id=1, config_type='kpi_weights', account_id=42, vertical='dc2_s')
"""

import copy
import logging

from extensions import db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config types that can be overridden at the customer level
# ---------------------------------------------------------------------------
OVERRIDABLE_CONFIG_TYPES = [
    'kpi_weights',
    'pillar_weights',
    'kpi_definitions',
    'health_thresholds',
    'scoring_rules',
    'dashboard_layout',
    'alert_rules',
    'playbook_config',
    'notification_config',
    'feature_flags',
]

# ---------------------------------------------------------------------------
# Config types that can additionally be overridden at the account level
# (subset of OVERRIDABLE_CONFIG_TYPES)
# ---------------------------------------------------------------------------
ACCOUNT_OVERRIDABLE_CONFIG_TYPES = [
    'kpi_weights',
    'pillar_weights',
    'health_thresholds',
    'scoring_rules',
    'alert_rules',
]


# ---------------------------------------------------------------------------
# Deep-merge utility
# ---------------------------------------------------------------------------
def deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge *override* into *base*.

    - dict values are merged recursively
    - list / scalar values in *override* replace the value in *base*
    - keys present only in *base* are preserved

    Neither input dict is mutated; returns a new dict.
    """
    if not isinstance(base, dict) or not isinstance(override, dict):
        return copy.deepcopy(override)

    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _apply_merge(base_config: dict, override_config: dict, strategy: str) -> dict:
    """Apply an override using the specified merge strategy."""
    if strategy == 'replace':
        return copy.deepcopy(override_config)
    elif strategy == 'shallow_merge':
        merged = copy.deepcopy(base_config)
        merged.update(copy.deepcopy(override_config))
        return merged
    else:
        # Default: deep_merge
        return deep_merge(base_config, override_config)


# ---------------------------------------------------------------------------
# Main resolver
# ---------------------------------------------------------------------------
def resolve_config(
    customer_id: int,
    config_type: str,
    account_id: int = None,
    vertical: str = None,
) -> dict:
    """
    Three-tier resolution (highest priority wins):
      1. AccountConfigOverride  (if account_id + overridable type)
      2. CustomerVerticalConfig (customer override)
      3. VerticalTemplate       (base template)

    Returns fully merged config dict.  Returns empty dict if no
    template or override exists for the requested config_type.

    Parameters
    ----------
    customer_id : int
        The customer whose config we are resolving.
    config_type : str
        Which config section to resolve (e.g. 'kpi_weights').
    account_id : int, optional
        If provided and config_type is account-overridable, the
        account-level override is applied on top.
    vertical : str, optional
        Vertical to scope the template lookup.  If None, looks up
        the customer's vertical from the Customer record.

    Returns
    -------
    dict
        The fully merged configuration dictionary.
    """
    # Lazy imports to avoid circular import issues at module load time
    from models import (
        VerticalTemplate,
        CustomerVerticalConfig,
        AccountConfigOverride,
        Customer,
    )

    # ------------------------------------------------------------------
    # Determine vertical if not explicitly provided
    # ------------------------------------------------------------------
    if vertical is None:
        customer = db.session.get(Customer, customer_id)
        vertical = getattr(customer, 'vertical', None) or 'dc2_s'

    # ------------------------------------------------------------------
    # Layer 3 (lowest priority): Base template
    # ------------------------------------------------------------------
    template = (
        VerticalTemplate.query
        .filter_by(vertical=vertical, config_type=config_type, is_active=True)
        .order_by(VerticalTemplate.template_id.desc())
        .first()
    )
    config = copy.deepcopy(template.config) if template else {}
    logger.debug(
        "resolve_config: template layer for vertical=%s config_type=%s -> %s keys",
        vertical, config_type, len(config),
    )

    # ------------------------------------------------------------------
    # Layer 2: Customer-level override
    # ------------------------------------------------------------------
    if config_type in OVERRIDABLE_CONFIG_TYPES:
        cvc = (
            CustomerVerticalConfig.query
            .filter_by(customer_id=customer_id, config_type=config_type)
            .first()
        )
        if cvc:
            strategy = cvc.merge_strategy or 'deep_merge'
            config = _apply_merge(config, cvc.config, strategy)
            logger.debug(
                "resolve_config: customer override applied (strategy=%s) for customer_id=%s",
                strategy, customer_id,
            )

    # ------------------------------------------------------------------
    # Layer 1 (highest priority): Account-level override
    # ------------------------------------------------------------------
    if account_id and config_type in ACCOUNT_OVERRIDABLE_CONFIG_TYPES:
        aco = (
            AccountConfigOverride.query
            .filter_by(account_id=account_id, config_type=config_type)
            .first()
        )
        if aco:
            config = deep_merge(config, aco.config)
            logger.debug(
                "resolve_config: account override applied for account_id=%s",
                account_id,
            )

    return config


def get_effective_config_with_sources(
    customer_id: int,
    config_type: str,
    account_id: int = None,
    vertical: str = None,
) -> dict:
    """
    Like resolve_config(), but also returns metadata about which layers
    contributed to the final result.

    Returns
    -------
    dict with keys:
        config   : dict  — the merged config
        sources  : list  — ordered list of sources that contributed
        vertical : str   — the vertical used for template lookup
    """
    from models import (
        VerticalTemplate,
        CustomerVerticalConfig,
        AccountConfigOverride,
        Customer,
    )

    sources = []

    if vertical is None:
        customer = db.session.get(Customer, customer_id)
        vertical = getattr(customer, 'vertical', None) or 'dc2_s'

    # Template
    template = (
        VerticalTemplate.query
        .filter_by(vertical=vertical, config_type=config_type, is_active=True)
        .order_by(VerticalTemplate.template_id.desc())
        .first()
    )
    config = copy.deepcopy(template.config) if template else {}
    if template:
        sources.append({
            'layer': 'template',
            'template_id': template.template_id,
            'version': template.version,
            'is_locked': template.is_locked,
        })

    # Customer override
    if config_type in OVERRIDABLE_CONFIG_TYPES:
        cvc = (
            CustomerVerticalConfig.query
            .filter_by(customer_id=customer_id, config_type=config_type)
            .first()
        )
        if cvc:
            strategy = cvc.merge_strategy or 'deep_merge'
            config = _apply_merge(config, cvc.config, strategy)
            sources.append({
                'layer': 'customer',
                'id': cvc.id,
                'merge_strategy': strategy,
            })

    # Account override
    if account_id and config_type in ACCOUNT_OVERRIDABLE_CONFIG_TYPES:
        aco = (
            AccountConfigOverride.query
            .filter_by(account_id=account_id, config_type=config_type)
            .first()
        )
        if aco:
            config = deep_merge(config, aco.config)
            sources.append({
                'layer': 'account',
                'id': aco.id,
            })

    return {
        'config': config,
        'sources': sources,
        'vertical': vertical,
    }
