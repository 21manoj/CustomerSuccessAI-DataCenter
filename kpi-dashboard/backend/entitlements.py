#!/usr/bin/env python3
"""
Customer Entitlements — Tier-Based Feature Gating for CS Pulse
================================================================
Controls what AI features and platform capabilities each customer
can access, based on their subscription tier.

Tiers:
  - starter       — Core dashboards + manual analysis only
  - professional   — + Signal Analyst + Playbook triggers + Test Runner advanced
  - enterprise     — + Onboarding Agent + Auto-trigger pipeline + MCP connectors + Copilot

Each feature is checked via:
    from entitlements import check_entitlement, require_entitlement
    if check_entitlement(customer_id, 'signal_analyst'):
        ...run analysis...

Uses the existing `feature_toggles` table for per-customer overrides.
Falls back to tier defaults when no explicit toggle exists.
"""

import os
import logging
from typing import Any, Dict, List, Optional
from functools import wraps
from flask import jsonify

logger = logging.getLogger(__name__)


# ============================================================
# FEATURE CATALOG — every gateable capability
# ============================================================

FEATURE_CATALOG = {
    # ── Core (available to all tiers) ──────────────────────
    'dashboards':              {'description': 'Core KPI dashboards and health scores',       'tier': 'starter'},
    'data_upload':             {'description': 'CSV/Excel data upload and validation',        'tier': 'starter'},
    'health_scores':           {'description': 'Pillar-based health score calculation',       'tier': 'starter'},
    'journey_generation':      {'description': 'Customer journey visualization',              'tier': 'starter'},
    'reports_basic':           {'description': 'Basic RACI and status reports',               'tier': 'starter'},

    # ── Professional ───────────────────────────────────────
    'signal_analyst':          {'description': 'AI Signal Analyst (churn/expansion prediction)',  'tier': 'professional'},
    'agent_loop':              {'description': 'Agentic reasoning loop (6-step PAOR)',            'tier': 'professional'},
    'playbook_triggers':       {'description': 'Manual playbook triggering and execution',        'tier': 'professional'},
    'power_of_1':              {'description': 'Power of 1 financial impact calculator',          'tier': 'professional'},
    'decision_matrix':         {'description': 'AI-powered decision matrix (quant vs qual)',      'tier': 'professional'},
    'test_runner_advanced':    {'description': 'Test Runner advanced options (presets, sliders)',  'tier': 'professional'},
    'revenue_intelligence':    {'description': 'Revenue intelligence and portfolio analysis',     'tier': 'professional'},
    'rag_queries':             {'description': 'RAG-powered natural language queries',            'tier': 'professional'},

    # ── Enterprise ─────────────────────────────────────────
    'onboarding_agent':        {'description': 'AI Onboarding Agent (TTFV, activation plans)',    'tier': 'enterprise'},
    'auto_trigger_pipeline':   {'description': 'Event-driven auto-analysis + auto-playbook',     'tier': 'enterprise'},
    'approval_queue':          {'description': 'Human-in-the-loop approval workflow',             'tier': 'enterprise'},
    'feedback_loop':           {'description': 'Playbook outcome → agent learning loop',         'tier': 'enterprise'},
    'mcp_connectors':          {'description': 'MCP external connectors (Salesforce, ServiceNow)', 'tier': 'enterprise'},
    'copilot_integration':     {'description': 'Microsoft Copilot / Teams integration',           'tier': 'enterprise'},
    'multi_provider':          {'description': 'Multi-LLM provider (OpenAI + Claude + Azure)',    'tier': 'enterprise'},
    'agent_memory_shared':     {'description': 'Cross-agent shared memory and intelligence',      'tier': 'enterprise'},

    # ── Add-on (disabled by default, enabled via per-customer override) ───
    'api_key_self_service':    {'description': 'Allow customers to create their own API keys',     'tier': 'addon'},
}


# ============================================================
# TIER HIERARCHY
# ============================================================

TIER_HIERARCHY = {
    'starter':      0,
    'professional': 1,
    'enterprise':   2,
}

# Tier → list of included tiers (for entitlement check)
TIER_INCLUDES = {
    'starter':      ['starter'],
    'professional': ['starter', 'professional'],
    'enterprise':   ['starter', 'professional', 'enterprise'],
}

# Default tier for new customers
DEFAULT_TIER = os.getenv('DEFAULT_CUSTOMER_TIER', 'starter')


# ============================================================
# TIER PRESETS — quick-reference of what each tier gets
# ============================================================

def get_tier_features(tier: str) -> Dict[str, bool]:
    """Get all features and their enabled status for a given tier."""
    included_tiers = TIER_INCLUDES.get(tier, ['starter'])
    result = {}
    for feature_name, feature_info in FEATURE_CATALOG.items():
        result[feature_name] = feature_info['tier'] in included_tiers
    return result


def get_tier_summary() -> Dict[str, Dict]:
    """Return a summary of all tiers and their features (for UI display)."""
    return {
        tier: {
            'level': level,
            'features': get_tier_features(tier),
            'feature_count': sum(1 for v in get_tier_features(tier).values() if v),
        }
        for tier, level in TIER_HIERARCHY.items()
    }


# ============================================================
# CUSTOMER TIER RESOLUTION
# ============================================================

def get_customer_tier(customer_id: int) -> str:
    """
    Get the subscription tier for a customer.

    Resolution order:
      1. feature_toggles table (feature_name='subscription_tier')
      2. Customer model field (if tier column exists)
      3. DEFAULT_TIER environment variable
      4. 'starter' fallback
    """
    try:
        from models import db, FeatureToggle

        toggle = FeatureToggle.query.filter_by(
            customer_id=customer_id,
            feature_name='subscription_tier',
        ).first()

        if toggle and toggle.config and 'tier' in toggle.config:
            tier = toggle.config['tier']
            if tier in TIER_HIERARCHY:
                return tier

    except Exception as e:
        logger.debug(f"Could not query tier from DB for customer {customer_id}: {e}")

    return DEFAULT_TIER


def set_customer_tier(customer_id: int, tier: str) -> bool:
    """
    Set the subscription tier for a customer.

    Stores in the feature_toggles table as feature_name='subscription_tier'.
    """
    if tier not in TIER_HIERARCHY:
        raise ValueError(f"Invalid tier '{tier}'. Must be one of: {list(TIER_HIERARCHY.keys())}")

    try:
        from models import db, FeatureToggle

        toggle = FeatureToggle.query.filter_by(
            customer_id=customer_id,
            feature_name='subscription_tier',
        ).first()

        if toggle:
            toggle.config = {'tier': tier}
            toggle.enabled = True
        else:
            toggle = FeatureToggle(
                customer_id=customer_id,
                feature_name='subscription_tier',
                enabled=True,
                config={'tier': tier},
                description=f'Subscription tier: {tier}',
            )
            db.session.add(toggle)

        db.session.commit()
        logger.info(f"Set customer {customer_id} tier to '{tier}'")
        return True

    except Exception as e:
        logger.error(f"Failed to set tier for customer {customer_id}: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


# ============================================================
# ENTITLEMENT CHECK — the core gating function
# ============================================================

def check_entitlement(customer_id: int, feature_name: str) -> bool:
    """
    Check if a customer is entitled to use a feature.

    Resolution order:
      1. Per-customer explicit override (feature_toggles table)
      2. Tier-based default (from FEATURE_CATALOG)
      3. False (deny by default)

    Args:
        customer_id: Customer ID
        feature_name: Feature name from FEATURE_CATALOG

    Returns:
        True if the customer can use this feature.
    """
    # 1. Check per-customer explicit override
    try:
        from models import db, FeatureToggle

        override = FeatureToggle.query.filter_by(
            customer_id=customer_id,
            feature_name=feature_name,
        ).first()

        if override is not None:
            # Explicit override exists — use it regardless of tier
            return override.enabled

    except Exception as e:
        logger.debug(f"Could not query feature override: {e}")

    # 2. Check tier-based default
    if feature_name not in FEATURE_CATALOG:
        logger.warning(f"Unknown feature '{feature_name}' — denying access")
        return False

    feature_tier = FEATURE_CATALOG[feature_name]['tier']
    customer_tier = get_customer_tier(customer_id)
    included_tiers = TIER_INCLUDES.get(customer_tier, ['starter'])

    return feature_tier in included_tiers


def check_entitlement_with_detail(customer_id: int, feature_name: str) -> Dict[str, Any]:
    """
    Like check_entitlement but returns detailed context (for API responses).
    """
    allowed = check_entitlement(customer_id, feature_name)
    customer_tier = get_customer_tier(customer_id)
    feature_info = FEATURE_CATALOG.get(feature_name, {})
    required_tier = feature_info.get('tier', 'unknown')

    return {
        'feature': feature_name,
        'allowed': allowed,
        'customer_tier': customer_tier,
        'required_tier': required_tier,
        'description': feature_info.get('description', ''),
        'upgrade_needed': not allowed,
        'upgrade_to': required_tier if not allowed else None,
    }


def get_customer_entitlements(customer_id: int) -> Dict[str, bool]:
    """Get all entitlements for a customer (for UI to render feature gates)."""
    result = {}
    for feature_name in FEATURE_CATALOG:
        result[feature_name] = check_entitlement(customer_id, feature_name)
    return result


# ============================================================
# DECORATOR — for gating Flask API endpoints
# ============================================================

def require_entitlement(feature_name: str):
    """
    Flask endpoint decorator — returns 403 if customer lacks entitlement.

    Usage:
        @app.route('/api/signal-analyst/analyze', methods=['POST'])
        @require_entitlement('signal_analyst')
        def analyze():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                from auth_middleware import get_current_customer_id
                customer_id = get_current_customer_id()
            except Exception:
                # If auth is not available, try extracting from request body
                from flask import request
                data = request.get_json(silent=True) or {}
                customer_id = data.get('customer_id')

            if not customer_id:
                return jsonify({
                    'error': 'Customer ID required for entitlement check',
                    'feature': feature_name,
                }), 401

            detail = check_entitlement_with_detail(int(customer_id), feature_name)
            if not detail['allowed']:
                return jsonify({
                    'error': 'Feature not available on your current plan',
                    'feature': feature_name,
                    'required_tier': detail['required_tier'],
                    'current_tier': detail['customer_tier'],
                    'upgrade_to': detail['upgrade_to'],
                    'description': detail['description'],
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


# ============================================================
# TEST RUNNER SPECIFIC — which advanced options are allowed
# ============================================================

TEST_RUNNER_OPTION_GATES = {
    # option_name → required feature
    'numAccounts':         'test_runner_advanced',
    'seed':                'test_runner_advanced',
    'industry':            'test_runner_advanced',
    'onboardingMode':      'test_runner_advanced',
    'showcasePatternMix':  'test_runner_advanced',
    'weights':             'test_runner_advanced',
    'dryRun':              'test_runner_advanced',
}


def filter_test_runner_options(customer_id: int, options: dict) -> dict:
    """
    Filter test runner options based on customer entitlements.

    Strips out options the customer's tier doesn't allow.
    Returns the filtered dict + a list of stripped keys.
    """
    if not options:
        return {}, []

    has_advanced = check_entitlement(customer_id, 'test_runner_advanced')

    if has_advanced:
        return options, []

    # Strip advanced options
    filtered = {}
    stripped = []
    for key, value in options.items():
        # Map camelCase (from UI) to snake_case (used in gates)
        if key in TEST_RUNNER_OPTION_GATES:
            stripped.append(key)
        else:
            filtered[key] = value

    return filtered, stripped


# ============================================================
# ENTITLEMENT API — Flask Blueprint
# ============================================================

from flask import Blueprint

entitlement_api = Blueprint('entitlement_api', __name__)


@entitlement_api.route('/api/entitlements', methods=['GET'])
def get_entitlements():
    """Get all entitlements for the current customer."""
    try:
        from auth_middleware import get_current_customer_id
        customer_id = get_current_customer_id()
    except Exception:
        from flask import request
        customer_id = request.args.get('customer_id', type=int)

    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 401

    entitlements = get_customer_entitlements(customer_id)
    tier = get_customer_tier(customer_id)

    return jsonify({
        'status': 'success',
        'customer_id': customer_id,
        'tier': tier,
        'entitlements': entitlements,
    })


@entitlement_api.route('/api/entitlements/check/<feature_name>', methods=['GET'])
def check_feature(feature_name: str):
    """Check a single feature entitlement."""
    try:
        from auth_middleware import get_current_customer_id
        customer_id = get_current_customer_id()
    except Exception:
        from flask import request
        customer_id = request.args.get('customer_id', type=int)

    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 401

    detail = check_entitlement_with_detail(customer_id, feature_name)
    return jsonify({'status': 'success', **detail})


@entitlement_api.route('/api/entitlements/tier', methods=['GET'])
def get_tier():
    """Get the current customer's tier."""
    try:
        from auth_middleware import get_current_customer_id
        customer_id = get_current_customer_id()
    except Exception:
        from flask import request
        customer_id = request.args.get('customer_id', type=int)

    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 401

    tier = get_customer_tier(customer_id)
    features = get_tier_features(tier)
    return jsonify({
        'status': 'success',
        'customer_id': customer_id,
        'tier': tier,
        'features': features,
    })


@entitlement_api.route('/api/entitlements/tier', methods=['PUT'])
def update_tier():
    """Set the customer's tier (admin only)."""
    from flask import request
    data = request.get_json(silent=True) or {}

    customer_id = data.get('customer_id')
    tier = data.get('tier')

    if not customer_id or not tier:
        return jsonify({'error': 'customer_id and tier are required'}), 400

    if tier not in TIER_HIERARCHY:
        return jsonify({
            'error': f"Invalid tier '{tier}'",
            'valid_tiers': list(TIER_HIERARCHY.keys()),
        }), 400

    success = set_customer_tier(int(customer_id), tier)
    if success:
        return jsonify({
            'status': 'success',
            'customer_id': customer_id,
            'tier': tier,
            'features': get_tier_features(tier),
        })
    else:
        return jsonify({'error': 'Failed to update tier'}), 500


@entitlement_api.route('/api/entitlements/override', methods=['PUT'])
def set_override():
    """
    Set a per-customer feature override (admin only).

    Body: { "customer_id": 1, "feature": "signal_analyst", "enabled": true }
    """
    from flask import request
    data = request.get_json(silent=True) or {}

    customer_id = data.get('customer_id')
    feature_name = data.get('feature')
    enabled = data.get('enabled')

    if not customer_id or not feature_name or enabled is None:
        return jsonify({'error': 'customer_id, feature, and enabled are required'}), 400

    if feature_name not in FEATURE_CATALOG:
        return jsonify({
            'error': f"Unknown feature '{feature_name}'",
            'valid_features': list(FEATURE_CATALOG.keys()),
        }), 400

    try:
        from models import db, FeatureToggle

        toggle = FeatureToggle.query.filter_by(
            customer_id=int(customer_id),
            feature_name=feature_name,
        ).first()

        if toggle:
            toggle.enabled = bool(enabled)
        else:
            toggle = FeatureToggle(
                customer_id=int(customer_id),
                feature_name=feature_name,
                enabled=bool(enabled),
                description=FEATURE_CATALOG[feature_name]['description'],
            )
            db.session.add(toggle)

        db.session.commit()

        return jsonify({
            'status': 'success',
            'customer_id': customer_id,
            'feature': feature_name,
            'enabled': bool(enabled),
            'note': 'Per-customer override — takes precedence over tier defaults',
        })

    except Exception as e:
        logger.error(f"Failed to set feature override: {e}")
        return jsonify({'error': str(e)}), 500


@entitlement_api.route('/api/entitlements/catalog', methods=['GET'])
def get_catalog():
    """Get the full feature catalog with tier requirements."""
    return jsonify({
        'status': 'success',
        'catalog': FEATURE_CATALOG,
        'tiers': get_tier_summary(),
    })
