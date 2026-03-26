"""
Push Intelligence Config — tunable thresholds for system-generated signals.

Mirrors the health_thresholds.py pattern.
Config file: backend/config/push_intelligence_config.json
API: GET/PUT /api/config/push-intelligence
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'config', 'push_intelligence_config.json'
)
_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        with open(_CONFIG_PATH) as f:
            _cache = json.load(f)
    return _cache


def reload() -> dict:
    """Force reload from disk — called after PUT /api/config/push-intelligence."""
    global _cache
    _cache = None
    return _load()


# ── Layer A ──────────────────────────────────────────────────────────────
def health_drop_trigger() -> float:
    return float(_load()['layer_a_signal_analyst']['health_drop_trigger_pts'])

def max_signals_context() -> int:
    return int(_load()['layer_a_signal_analyst']['max_signals_context'])

def layer_a_enabled() -> bool:
    return bool(_load()['layer_a_signal_analyst']['enabled'])


# ── Layer C ──────────────────────────────────────────────────────────────
def confidence_min() -> float:
    return float(_load()['layer_c_urgent_scanner']['confidence_min'])

def revenue_risk_min() -> float:
    return float(_load()['layer_c_urgent_scanner']['revenue_risk_min_usd'])

def urgency_threshold() -> float:
    return float(_load()['layer_c_urgent_scanner']['urgency_threshold'])

def renewal_window_days() -> int:
    return int(_load()['layer_c_urgent_scanner']['renewal_window_days'])

def layer_c_enabled() -> bool:
    return bool(_load()['layer_c_urgent_scanner']['enabled'])


# ── Wizard A ─────────────────────────────────────────────────────────────
def arc_min_confidence() -> float:
    return float(_load()['wizard_a_arc_classifier']['min_confidence_to_store_node'])

def arc_classifier_enabled() -> bool:
    return bool(_load()['wizard_a_arc_classifier']['enabled'])


# ── Layer B ──────────────────────────────────────────────────────────────
def auto_trigger_on_arc() -> bool:
    return bool(_load()['layer_b_playbook_trigger']['auto_trigger_on_arc'])

def layer_b_enabled() -> bool:
    return bool(_load()['layer_b_playbook_trigger']['enabled'])


# ── Notifications ────────────────────────────────────────────────────────
def unread_ttl_days() -> int:
    return int(_load()['notifications']['unread_ttl_days'])
