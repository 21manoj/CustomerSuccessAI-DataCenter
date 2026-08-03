"""
Vertical-aware playbook IDs for signal-triggered executions.

Signal analyst historically hardcoded PB-DC-* for every tenant, which leaked
datacenter playbook names into SaaS causal_chain_ref exports
(close:exec-PB-DC-01-…). This module centralizes per-vertical routing.
"""

from __future__ import annotations

from typing import Dict, Optional

# Shared metadata — playbook ID is resolved per vertical below.
_SIGNAL_RISK_BASE: Dict[str, Dict[str, str]] = {
    'champion_change':        {'priority': 'critical', 'label': 'Champion departed or changed'},
    'champion_loss':          {'priority': 'critical', 'label': 'Key champion lost'},
    'executive_change':       {'priority': 'critical', 'label': 'Executive sponsor changed'},
    'stakeholder_departure':  {'priority': 'high',     'label': 'Key stakeholder departed'},
    'stakeholder_escalation': {'priority': 'high',     'label': 'Stakeholder escalated concern'},
    'budget_cut':             {'priority': 'high',     'label': 'Budget reduction signaled'},
    'budget_pressure':        {'priority': 'high',     'label': 'Budget pressure detected'},
    'contract_dispute':       {'priority': 'critical', 'label': 'Contract dispute escalated'},
    'downgrade_request':      {'priority': 'critical', 'label': 'Downgrade or cancellation request'},
    'escalation':             {'priority': 'high',     'label': 'Issue escalated'},
    'support_escalation':     {'priority': 'high',     'label': 'Support ticket escalated'},
    'executive_escalation':   {'priority': 'critical', 'label': 'Executive-level escalation'},
    'critical_incident':      {'priority': 'critical', 'label': 'Critical incident reported'},
    'competitor_mention':     {'priority': 'high',     'label': 'Competitor mentioned by customer'},
    'usage_decline':          {'priority': 'high',     'label': 'Product usage declining'},
    'engagement_gap':         {'priority': 'high',     'label': 'Customer engagement gap detected'},
    'nps_decline':            {'priority': 'high',     'label': 'NPS score declining — friction vs value risk'},
    'nps_drop':               {'priority': 'high',     'label': 'NPS dropped significantly'},
}

_DC_PLAYBOOK_BY_SIGNAL: Dict[str, str] = {
    'champion_change': 'PB-DC-02', 'champion_loss': 'PB-DC-02',
    'executive_change': 'PB-DC-02', 'stakeholder_departure': 'PB-DC-02',
    'stakeholder_escalation': 'PB-DC-02',
    'budget_cut': 'PB-DC-03', 'budget_pressure': 'PB-DC-03',
    'contract_dispute': 'PB-DC-01', 'downgrade_request': 'PB-DC-01',
    'escalation': 'PB-DC-01', 'support_escalation': 'PB-DC-01',
    'executive_escalation': 'PB-DC-01', 'critical_incident': 'PB-DC-01',
    'competitor_mention': 'PB-DC-04', 'usage_decline': 'PB-DC-04',
    'engagement_gap': 'PB-DC-04', 'nps_decline': 'PB-DC-04', 'nps_drop': 'PB-DC-04',
}

# SaaS Premium slugs — match verticals/saas_premium/vertical_config.py + cost bridge.
_SAAS_PLAYBOOK_BY_SIGNAL: Dict[str, str] = {
    'champion_change': 'renewal-safeguard', 'champion_loss': 'renewal-safeguard',
    'executive_change': 'renewal-safeguard', 'stakeholder_departure': 'renewal-safeguard',
    'stakeholder_escalation': 'renewal-safeguard',
    'budget_cut': 'voc-sprint', 'budget_pressure': 'voc-sprint',
    'contract_dispute': 'sla-stabilizer', 'downgrade_request': 'sla-stabilizer',
    'escalation': 'sla-stabilizer', 'support_escalation': 'sla-stabilizer',
    'executive_escalation': 'sla-stabilizer', 'critical_incident': 'sla-stabilizer',
    'competitor_mention': 'activation-blitz', 'usage_decline': 'activation-blitz',
    'engagement_gap': 'activation-blitz', 'nps_decline': 'activation-blitz',
    'nps_drop': 'activation-blitz',
}

_PLAYBOOK_DURATION_DAYS: Dict[str, int] = {
    # DC
    'PB-DC-01': 21, 'PB-DC-02': 14, 'PB-DC-03': 30, 'PB-DC-04': 21,
    'PB-DC-05': 21, 'PB-DC-06': 30,
    'PB-01': 21, 'PB-02': 14, 'PB-03': 21, 'PB-04': 14,
    'PB-05': 21, 'PB-06': 30, 'PB-07': 21, 'PB-08': 30,
    # SaaS slugs
    'activation-blitz': 30, 'voc-sprint': 28, 'expansion-accelerator': 21,
    'renewal-safeguard': 21, 'sla-stabilizer': 14, 'health-check': 21,
    # SaaS-PB legacy IDs (seed scripts / work packages)
    'SaaS-PB-01': 21, 'SaaS-PB-02': 14, 'SaaS-PB-03': 21, 'SaaS-PB-04': 21,
    'SaaS-PB-05': 30, 'SaaS-PB-06': 21, 'SaaS-PB-07': 14, 'SaaS-PB-08': 21,
}

_SAAS_PLAYBOOK_NAMES: Dict[str, str] = {
    'activation-blitz': 'Activation Blitz',
    'voc-sprint': 'VoC Sprint',
    'expansion-accelerator': 'Expansion Accelerator',
    'renewal-safeguard': 'Renewal Safeguard',
    'sla-stabilizer': 'SLA Stabilizer',
    'health-check': 'Health Check',
}


def is_saas_vertical(vertical: Optional[str]) -> bool:
    return 'saas' in (vertical or '').lower()


def _playbook_map_for_vertical(vertical: Optional[str]) -> Dict[str, str]:
    return _SAAS_PLAYBOOK_BY_SIGNAL if is_saas_vertical(vertical) else _DC_PLAYBOOK_BY_SIGNAL


def get_high_risk_signal_types(vertical: Optional[str]) -> Dict[str, Dict[str, str]]:
    """Return signal_type → {priority, label, playbook} for the tenant vertical."""
    playbook_map = _playbook_map_for_vertical(vertical)
    out: Dict[str, Dict[str, str]] = {}
    for sig_type, base in _SIGNAL_RISK_BASE.items():
        playbook_id = playbook_map.get(sig_type)
        if not playbook_id:
            continue
        out[sig_type] = {**base, 'playbook': playbook_id}
    return out


def resolve_customer_vertical(customer_id: int) -> str:
    try:
        from mcp_server.cs_pulse_mcp_server import _resolve_customer_vertical
        return _resolve_customer_vertical(customer_id)
    except Exception:
        try:
            from models import Customer
            cust = Customer.query.get(int(customer_id))
            return (getattr(cust, 'vertical', None) or 'dc2_s') if cust else 'dc2_s'
        except Exception:
            return 'dc2_s'


def get_playbook_duration_days(playbook_id: str, vertical: Optional[str] = None) -> int:
    if playbook_id in _PLAYBOOK_DURATION_DAYS:
        return _PLAYBOOK_DURATION_DAYS[playbook_id]
    if vertical and is_saas_vertical(vertical):
        try:
            from verticals.saas_premium.vertical_config import PLAYBOOK_CONFIG
            cfg = PLAYBOOK_CONFIG.get(playbook_id) or {}
            return int(cfg.get('estimated_duration_days') or 21)
        except Exception:
            pass
    return 21


def saas_recovery_playbook_ids() -> tuple:
    return ('renewal-safeguard', 'sla-stabilizer', 'activation-blitz')


def saas_expansion_playbook_ids() -> tuple:
    return ('expansion-accelerator', 'activation-blitz', 'renewal-safeguard')


def dc_recovery_playbook_ids() -> tuple:
    return ('PB-DC-01', 'PB-DC-02', 'PB-DC-04')


def dc_expansion_playbook_ids() -> tuple:
    return ('PB-DC-04', 'PB-DC-06', 'PB-DC-01')


def playbook_ids_for_vertical(vertical: Optional[str]) -> tuple:
    """(expansion_playbooks, recovery_playbooks) for seed/attribution scripts."""
    if is_saas_vertical(vertical):
        return saas_expansion_playbook_ids(), saas_recovery_playbook_ids()
    return dc_expansion_playbook_ids(), dc_recovery_playbook_ids()


def playbook_display_names() -> Dict[str, str]:
    names = {
        'PB-01': 'Deployment Acceleration', 'PB-02': 'RMA Prevention',
        'PB-03': 'GPU Optimization', 'PB-04': 'Capacity Planning',
        'PB-05': 'Health Monitoring', 'PB-06': 'Customer Engagement',
        'PB-07': 'Seasonal Planning', 'PB-08': 'Expansion Accelerator',
        'PB-DC-01': 'Deployment Acceleration', 'PB-DC-02': 'RMA Prevention',
        'PB-DC-03': 'GPU Optimization', 'PB-DC-04': 'Capacity Planning',
        'PB-DC-05': 'Health Monitoring', 'PB-DC-06': 'Customer Engagement',
    }
    names.update(_SAAS_PLAYBOOK_NAMES)
    return names
