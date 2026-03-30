"""
Arc Edge Generator — generates ContextEdge rows for an account from its arc type.

Backend equivalent of load-driver RefRegistry + generate_signal_edges_csv().
Queries real ContextNode rows by occurred_at order, applies arc edge_topology
template, performs temporal validation, INSERTs ContextEdge rows.

ARC_TEMPLATES copied from load-driver/scenarios/scenario_manifest.py
(NarrativeTimelinePlanner.ARC_TEMPLATES). Must stay in sync with load-driver.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ARC_TEMPLATES — ported verbatim from load-driver/scenarios/scenario_manifest.py
# NarrativeTimelinePlanner.ARC_TEMPLATES
# Only edge_topology is used by this module; full dict preserved for reference.
# ═══════════════════════════════════════════════════════════════════════════════

ARC_TEMPLATES: dict[str, dict] = {
    'silent_churn': {  # was: ignored_churn
        'classification': 'critical',
        'baseline': [
            {'type': 'signal',      'subtype': 'kpi_decline',              'month': 3, 'offset_days': 0},
            {'type': 'signal',      'subtype': 'support_escalation',       'month': 3, 'offset_days': 7},
            {'type': 'stakeholder', 'subtype': 'champion_disengagement',   'month': 3, 'offset_days': 14},
            {'type': 'decision',    'subtype': 'escalation_to_exec',       'month': 4, 'offset_days': 0},
            {'type': 'decision',    'subtype': 'emergency_retention',      'month': 4, 'offset_days': 7},
            {'type': 'outcome',     'subtype': 'churn_risk',               'month': 5, 'offset_days': 0},
            {'type': 'outcome',     'subtype': 'engagement_decline',       'month': 5, 'offset_days': 3},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'csm_intervention',  'month': 0, 'offset_days': 0},
            {'type': 'signal',   'subtype': 'kpi_recovery',      'month': 1, 'offset_days': 7},
            {'type': 'decision', 'subtype': 'recovery_plan',     'month': 0, 'offset_days': 14},
            {'type': 'decision', 'subtype': 'executive_qbr',     'month': 1, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'churn_averted',     'month': 2, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'revenue_protected', 'month': 2, 'offset_days': 14},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:1',                 'type': 'TRIGGERED', 'confidence': 0.9,  'lag_days': 7,  'label': 'KPI decline triggered escalation'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:churn_risk',          'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 14, 'label': 'Escalation surfaced churn risk'},
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:2',                 'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 10, 'label': 'Decline triggered retention plan'},
            {'phase': 'baseline',     'from': 'decision:2', 'to': 'outcome:engagement_decline', 'type': 'LED_TO',    'confidence': 0.8,  'lag_days': 21, 'label': 'Retention plan addressed engagement decline'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',                 'type': 'TRIGGERED', 'confidence': 0.9,  'lag_days': 7,  'label': 'Recovery signal triggered intervention plan'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:churn_averted',      'type': 'LED_TO',    'confidence': 0.9,  'lag_days': 21, 'label': 'Intervention plan averted churn'},
            {'phase': 'intervention', 'from': 'decision:2', 'to': 'outcome:revenue_protected',  'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 21, 'label': 'Executive QBR protected revenue'},
        ],
    },
    'expansion_champion': {  # was: proactive_growth
        'classification': 'healthy',
        'baseline': [
            {'type': 'signal',      'subtype': 'expansion_signal',      'month': 3, 'offset_days': 0},
            {'type': 'stakeholder', 'subtype': 'champion_engages',      'month': 3, 'offset_days': 7},
            {'type': 'decision',    'subtype': 'invest_expansion',      'month': 4, 'offset_days': 0},
            {'type': 'decision',    'subtype': 'upsell_proposal',       'month': 4, 'offset_days': 10},
            {'type': 'outcome',     'subtype': 'expansion_opportunity', 'month': 5, 'offset_days': 0},
            {'type': 'outcome',     'subtype': 'revenue_growth',        'month': 5, 'offset_days': 7},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'advocacy',           'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'expansion_proposal', 'month': 1, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'expansion_approved', 'month': 2, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'revenue_growth',     'month': 2, 'offset_days': 14},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:1',                    'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Expansion signal triggered investment'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:expansion_opportunity', 'type': 'LED_TO',    'confidence': 0.8,  'lag_days': 14, 'label': 'Investment identified expansion'},
            {'phase': 'baseline',     'from': 'decision:2', 'to': 'outcome:revenue_growth',        'type': 'LED_TO',    'confidence': 0.8,  'lag_days': 14, 'label': 'Upsell proposal drove revenue growth'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',                    'type': 'TRIGGERED', 'confidence': 0.9,  'lag_days': 7,  'label': 'Advocacy triggered expansion proposal'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:expansion_approved',   'type': 'LED_TO',    'confidence': 0.9,  'lag_days': 21, 'label': 'Proposal secured expansion approval'},
        ],
    },
    'crisis_recovery': {
        'classification': 'critical',
        'baseline': [
            {'type': 'signal',      'subtype': 'critical_incident',      'month': 2, 'offset_days': 0},
            {'type': 'signal',      'subtype': 'stakeholder_escalation', 'month': 2, 'offset_days': 3},
            {'type': 'decision',    'subtype': 'emergency_response',     'month': 2, 'offset_days': 10},
            {'type': 'stakeholder', 'subtype': 'exec_sponsor_engaged',   'month': 2, 'offset_days': 12},
            {'type': 'decision',    'subtype': 'recovery_plan',          'month': 3, 'offset_days': 0},
            {'type': 'outcome',     'subtype': 'partial_recovery',       'month': 4, 'offset_days': 0},
            {'type': 'outcome',     'subtype': 'revenue_protected',      'month': 4, 'offset_days': 14},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'kpi_recovery',      'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'recovery_plan',     'month': 0, 'offset_days': 14},
            {'type': 'decision', 'subtype': 'executive_qbr',     'month': 1, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'churn_averted',     'month': 1, 'offset_days': 21},
            {'type': 'outcome',  'subtype': 'revenue_protected', 'month': 2, 'offset_days': 0},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:1',              'type': 'TRIGGERED', 'confidence': 0.9,  'lag_days': 7,  'label': 'Critical incident triggered emergency response'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:partial_recovery', 'type': 'LED_TO',   'confidence': 0.85, 'lag_days': 14, 'label': 'Emergency response led to partial recovery'},
            {'phase': 'baseline',     'from': 'signal:2',   'to': 'decision:2',              'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 10, 'label': 'Escalation triggered recovery plan'},
            {'phase': 'baseline',     'from': 'decision:2', 'to': 'outcome:revenue_protected', 'type': 'LED_TO',  'confidence': 0.8,  'lag_days': 21, 'label': 'Recovery plan protected revenue'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',              'type': 'TRIGGERED', 'confidence': 0.9,  'lag_days': 7,  'label': 'KPI recovery signal triggered plan'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:churn_averted',   'type': 'LED_TO',    'confidence': 0.9,  'lag_days': 21, 'label': 'Recovery plan averted churn'},
            {'phase': 'intervention', 'from': 'decision:2', 'to': 'outcome:revenue_protected', 'type': 'LED_TO',  'confidence': 0.85, 'lag_days': 21, 'label': 'Executive QBR protected revenue'},
        ],
    },
    'expansion_champion': {
        'classification': 'healthy',
        'baseline': [
            {'type': 'signal',      'subtype': 'champion_advocacy', 'month': 2, 'offset_days': 0},
            {'type': 'stakeholder', 'subtype': 'champion_promotes', 'month': 2, 'offset_days': 5},
            {'type': 'signal',      'subtype': 'usage_spike',       'month': 3, 'offset_days': 0},
            {'type': 'decision',    'subtype': 'expand_contract',   'month': 3, 'offset_days': 14},
            {'type': 'outcome',     'subtype': 'expansion_closed',  'month': 4, 'offset_days': 0},
            {'type': 'outcome',     'subtype': 'revenue_growth',    'month': 4, 'offset_days': 7},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'advocacy',           'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'expansion_proposal', 'month': 0, 'offset_days': 14},
            {'type': 'outcome',  'subtype': 'expansion_approved', 'month': 1, 'offset_days': 21},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:1',              'type': 'TRIGGERED', 'confidence': 0.9,  'lag_days': 7,  'label': 'Champion advocacy triggered expansion'},
            {'phase': 'baseline',     'from': 'signal:2',   'to': 'decision:1',              'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Usage spike reinforced expansion decision'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:expansion_closed', 'type': 'LED_TO',  'confidence': 0.9,  'lag_days': 14, 'label': 'Contract expansion executed'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:revenue_growth',  'type': 'LED_TO',   'confidence': 0.85, 'lag_days': 21, 'label': 'Expansion drove revenue growth'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',              'type': 'TRIGGERED', 'confidence': 0.9,  'lag_days': 7,  'label': 'Advocacy triggered expansion proposal'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:expansion_approved', 'type': 'LED_TO', 'confidence': 0.9, 'lag_days': 21, 'label': 'Proposal secured approval'},
        ],
    },
    'seasonal_surge': {  # was: steady_performer (healthy stable accounts)
        'classification': 'healthy',
        'baseline': [
            {'type': 'signal',      'subtype': 'routine_review',    'month': 4, 'offset_days': 0},
            {'type': 'stakeholder', 'subtype': 'regular_qbr',       'month': 4, 'offset_days': 7},
            {'type': 'decision',    'subtype': 'renewal_confirmed', 'month': 5, 'offset_days': 0},
            {'type': 'outcome',     'subtype': 'renewal_secured',   'month': 5, 'offset_days': 14},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'advocacy',           'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'expansion_proposal', 'month': 1, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'expansion_approved', 'month': 2, 'offset_days': 0},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:1',              'type': 'TRIGGERED', 'confidence': 0.8,  'lag_days': 7,  'label': 'Routine review prompted renewal decision'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:renewal_secured', 'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 14, 'label': 'Renewal confirmed and secured'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',              'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Advocacy triggered expansion proposal'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:expansion_approved', 'type': 'LED_TO', 'confidence': 0.85, 'lag_days': 21, 'label': 'Proposal secured expansion'},
        ],
    },
    'competitive_displacement_budget': {  # budget-pressure variant of competitive_displacement
        'classification': 'at_risk',
        'baseline': [
            {'type': 'signal',   'subtype': 'kpi_decline',           'month': 2, 'offset_days': 0},
            {'type': 'signal',   'subtype': 'support_escalation',    'month': 2, 'offset_days': 7},
            {'type': 'decision', 'subtype': 'renewal_strategy',      'month': 3, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'feature_adoption_push', 'month': 3, 'offset_days': 14},
            {'type': 'outcome',  'subtype': 'renewal_uncertainty',   'month': 4, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'engagement_decline',    'month': 4, 'offset_days': 7},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'champion_reengagement', 'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'renewal_incentive',     'month': 0, 'offset_days': 14},
            {'type': 'outcome',  'subtype': 'renewal_secured',       'month': 1, 'offset_days': 21},
            {'type': 'outcome',  'subtype': 'revenue_protected',     'month': 2, 'offset_days': 0},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:1',                'type': 'TRIGGERED', 'confidence': 0.8,  'lag_days': 14, 'label': 'KPI decline triggered renewal review'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:renewal_uncertainty', 'type': 'LED_TO',  'confidence': 0.75, 'lag_days': 21, 'label': 'Review surfaced renewal uncertainty'},
            {'phase': 'baseline',     'from': 'signal:2',   'to': 'decision:2',                'type': 'TRIGGERED', 'confidence': 0.75, 'lag_days': 14, 'label': 'Escalation triggered adoption push'},
            {'phase': 'baseline',     'from': 'decision:2', 'to': 'outcome:engagement_decline', 'type': 'LED_TO',   'confidence': 0.7,  'lag_days': 21, 'label': 'Training surfaced engagement decline'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',                'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Re-engagement triggered incentive'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:renewal_secured',   'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 21, 'label': 'Incentive secured renewal'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:revenue_protected', 'type': 'LED_TO',    'confidence': 0.8,  'lag_days': 28, 'label': 'Renewal protected revenue'},
        ],
    },
    'stalled_deployment': {
        'classification': 'at_risk',
        'baseline': [
            {'type': 'signal',   'subtype': 'kpi_decline',            'month': 1, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'renewal_strategy',       'month': 2, 'offset_days': 7},
            {'type': 'decision', 'subtype': 'feature_adoption_push',  'month': 3, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'renewal_uncertainty',    'month': 4, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'partner_friction',       'month': 4, 'offset_days': 7},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'deployment_improvement', 'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'technical_remediation',  'month': 0, 'offset_days': 14},
            {'type': 'outcome',  'subtype': 'renewal_secured',        'month': 1, 'offset_days': 21},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:1',                'type': 'TRIGGERED', 'confidence': 0.8,  'lag_days': 14, 'label': 'KPI decline triggered renewal strategy'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:renewal_uncertainty', 'type': 'LED_TO',  'confidence': 0.75, 'lag_days': 21, 'label': 'Renewal review surfaced uncertainty'},
            {'phase': 'baseline',     'from': 'decision:2', 'to': 'outcome:partner_friction',   'type': 'LED_TO',   'confidence': 0.7,  'lag_days': 21, 'label': 'Adoption push revealed partner friction'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',                'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Improvement signal triggered remediation'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:renewal_secured',   'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 21, 'label': 'Remediation secured renewal'},
        ],
    },
    'competitive_displacement_eval': {  # competitor-eval variant
        'classification': 'at_risk',
        'baseline': [
            {'type': 'signal',   'subtype': 'support_escalation',  'month': 2, 'offset_days': 0},
            {'type': 'signal',   'subtype': 'kpi_decline',         'month': 2, 'offset_days': 7},
            {'type': 'decision', 'subtype': 'renewal_strategy',    'month': 3, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'renewal_uncertainty', 'month': 4, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'engagement_decline',  'month': 4, 'offset_days': 14},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'champion_reengagement', 'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'renewal_incentive',     'month': 1, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'renewal_secured',       'month': 2, 'offset_days': 0},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:1',                'type': 'TRIGGERED', 'confidence': 0.8,  'lag_days': 14, 'label': 'Escalation triggered renewal review'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:renewal_uncertainty', 'type': 'LED_TO',  'confidence': 0.75, 'lag_days': 21, 'label': 'Review surfaced renewal uncertainty'},
            {'phase': 'baseline',     'from': 'signal:2',   'to': 'outcome:engagement_decline', 'type': 'CAUSED_BY', 'confidence': 0.7, 'lag_days': 7,  'label': 'KPI decline causing engagement drop'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',                'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Re-engagement triggered incentive'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:renewal_secured',   'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 21, 'label': 'Incentive secured renewal'},
        ],
    },
    'exec_sponsor_change': {  # was: champion_loss
        'classification': 'critical',
        'baseline': [
            {'type': 'signal',   'subtype': 'stakeholder_escalation', 'month': 1, 'offset_days': 0},
            {'type': 'signal',   'subtype': 'kpi_decline',            'month': 2, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'escalation_to_exec',     'month': 2, 'offset_days': 7},
            {'type': 'decision', 'subtype': 'emergency_retention',    'month': 3, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'revenue_at_risk',        'month': 4, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'engagement_decline',     'month': 4, 'offset_days': 7},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'executive_engagement',  'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'recovery_plan',         'month': 0, 'offset_days': 14},
            {'type': 'decision', 'subtype': 'executive_qbr',         'month': 1, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'churn_averted',         'month': 1, 'offset_days': 21},
            {'type': 'outcome',  'subtype': 'revenue_protected',     'month': 2, 'offset_days': 7},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:1',                'type': 'TRIGGERED', 'confidence': 0.9,  'lag_days': 7,  'label': 'Stakeholder loss triggered escalation'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:revenue_at_risk',   'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 14, 'label': 'Escalation revealed revenue risk'},
            {'phase': 'baseline',     'from': 'signal:2',   'to': 'decision:2',                'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 10, 'label': 'KPI decline triggered retention plan'},
            {'phase': 'baseline',     'from': 'decision:2', 'to': 'outcome:engagement_decline', 'type': 'LED_TO',   'confidence': 0.8,  'lag_days': 21, 'label': 'Retention plan addressed engagement decline'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',                'type': 'TRIGGERED', 'confidence': 0.9,  'lag_days': 7,  'label': 'Exec engagement triggered recovery plan'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:churn_averted',     'type': 'LED_TO',    'confidence': 0.9,  'lag_days': 21, 'label': 'Recovery plan averted churn'},
            {'phase': 'intervention', 'from': 'decision:2', 'to': 'outcome:revenue_protected', 'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 21, 'label': 'Executive QBR protected revenue'},
        ],
    },
    'stalled_deployment_decay': {  # infrastructure-decay variant of stalled_deployment
        'classification': 'critical',
        'baseline': [
            {'type': 'signal',   'subtype': 'critical_incident',   'month': 1, 'offset_days': 0},
            {'type': 'signal',   'subtype': 'support_escalation',  'month': 1, 'offset_days': 7},
            {'type': 'decision', 'subtype': 'emergency_response',  'month': 2, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'emergency_retention', 'month': 3, 'offset_days': 7},
            {'type': 'outcome',  'subtype': 'revenue_at_risk',     'month': 4, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'capacity_constraint', 'month': 4, 'offset_days': 7},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'kpi_recovery',      'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'recovery_plan',     'month': 0, 'offset_days': 14},
            {'type': 'outcome',  'subtype': 'churn_averted',     'month': 1, 'offset_days': 21},
            {'type': 'outcome',  'subtype': 'revenue_protected', 'month': 2, 'offset_days': 0},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:1',              'type': 'TRIGGERED', 'confidence': 0.9,  'lag_days': 7,  'label': 'Critical incident triggered emergency response'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:revenue_at_risk', 'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 14, 'label': 'Response revealed revenue at risk'},
            {'phase': 'baseline',     'from': 'signal:2',   'to': 'decision:2',              'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 10, 'label': 'Escalation triggered retention plan'},
            {'phase': 'baseline',     'from': 'decision:2', 'to': 'outcome:capacity_constraint', 'type': 'LED_TO', 'confidence': 0.8, 'lag_days': 21, 'label': 'Retention surfaced capacity constraints'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',              'type': 'TRIGGERED', 'confidence': 0.9,  'lag_days': 7,  'label': 'KPI recovery triggered remediation plan'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:churn_averted',   'type': 'LED_TO',    'confidence': 0.9,  'lag_days': 21, 'label': 'Remediation averted churn'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:revenue_protected', 'type': 'LED_TO',  'confidence': 0.85, 'lag_days': 28, 'label': 'Remediation protected revenue'},
        ],
    },
    # Alias: engagement_decline falls back to budget_pressure topology
    'silent_churn_mild': {  # was: engagement_decline (mild variant of silent_churn)
        'classification': 'at_risk',
        'baseline': [
            {'type': 'signal',   'subtype': 'kpi_decline',        'month': 2, 'offset_days': 0},
            {'type': 'signal',   'subtype': 'support_escalation', 'month': 2, 'offset_days': 7},
            {'type': 'decision', 'subtype': 'renewal_strategy',   'month': 3, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'engagement_decline', 'month': 4, 'offset_days': 0},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'champion_reengagement', 'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'renewal_incentive',     'month': 0, 'offset_days': 14},
            {'type': 'outcome',  'subtype': 'renewal_secured',       'month': 1, 'offset_days': 21},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:1',                'type': 'TRIGGERED', 'confidence': 0.75, 'lag_days': 14, 'label': 'KPI decline triggered renewal review'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:engagement_decline', 'type': 'LED_TO',   'confidence': 0.7,  'lag_days': 21, 'label': 'Review surfaced engagement decline'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',                'type': 'TRIGGERED', 'confidence': 0.8,  'lag_days': 7,  'label': 'Re-engagement triggered incentive'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:renewal_secured',   'type': 'LED_TO',    'confidence': 0.8,  'lag_days': 21, 'label': 'Incentive secured renewal'},
        ],
    },
    # Alias: land_and_expand maps to expansion_champion topology
    'land_and_expand': {
        'classification': 'healthy',
        'baseline': [
            {'type': 'signal',      'subtype': 'expansion_signal',      'month': 2, 'offset_days': 0},
            {'type': 'stakeholder', 'subtype': 'champion_engages',      'month': 2, 'offset_days': 7},
            {'type': 'decision',    'subtype': 'invest_expansion',      'month': 3, 'offset_days': 0},
            {'type': 'outcome',     'subtype': 'expansion_opportunity', 'month': 4, 'offset_days': 0},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'advocacy',           'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'expansion_proposal', 'month': 0, 'offset_days': 14},
            {'type': 'outcome',  'subtype': 'expansion_approved', 'month': 1, 'offset_days': 21},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'decision:1',                    'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Expansion signal triggered investment'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:expansion_opportunity', 'type': 'LED_TO',    'confidence': 0.8,  'lag_days': 14, 'label': 'Investment identified expansion opportunity'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',                    'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Advocacy triggered expansion proposal'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:expansion_approved',   'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 21, 'label': 'Proposal secured expansion approval'},
        ],
    },

    # ── 4 additional arcs from JSON story arc manifests ──
    # These were missing, causing fallback to 'steady_performer' (only 2 edges).

    'competitive_displacement': {
        'classification': 'at_risk',
        'baseline': [
            {'type': 'signal',   'subtype': 'competitor_mention',      'month': 2, 'offset_days': 0},
            {'type': 'signal',   'subtype': 'budget_pressure',         'month': 3, 'offset_days': 0},
            {'type': 'signal',   'subtype': 'escalation',              'month': 3, 'offset_days': 14},
            {'type': 'decision', 'subtype': 'competitive_defense',     'month': 4, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'executive_engagement',    'month': 4, 'offset_days': 7},
            {'type': 'outcome',  'subtype': 'renewal_uncertainty',     'month': 5, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'engagement_decline',      'month': 5, 'offset_days': 7},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'value_defense',           'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'multi_year_commitment',   'month': 0, 'offset_days': 14},
            {'type': 'outcome',  'subtype': 'renewal_confirmed',       'month': 1, 'offset_days': 21},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'signal:2',                   'type': 'LED_TO',    'confidence': 0.75, 'lag_days': 14, 'label': 'Competitor threat led to budget pressure'},
            {'phase': 'baseline',     'from': 'signal:2',   'to': 'signal:3',                   'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 14, 'label': 'Budget pressure escalated retention risk'},
            {'phase': 'baseline',     'from': 'signal:3',   'to': 'decision:1',                 'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Escalation triggered competitive defense'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'decision:2',                 'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 7,  'label': 'Defense required executive engagement'},
            {'phase': 'baseline',     'from': 'decision:2', 'to': 'outcome:renewal_uncertainty', 'type': 'LED_TO',   'confidence': 0.70, 'lag_days': 14, 'label': 'Engagement surfaced renewal uncertainty'},
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'outcome:engagement_decline', 'type': 'CAUSED_BY', 'confidence': 0.75, 'lag_days': 30, 'label': 'Competitor threat caused engagement decline'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',                 'type': 'TRIGGERED', 'confidence': 0.90, 'lag_days': 7,  'label': 'Value defense triggered commitment discussion'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:renewal_confirmed',  'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 21, 'label': 'Multi-year commitment secured renewal'},
        ],
    },

    'silent_churn': {
        'classification': 'at_risk',
        'baseline': [
            {'type': 'signal',   'subtype': 'engagement_gap',       'month': 2, 'offset_days': 0},
            {'type': 'signal',   'subtype': 'nps_decline',          'month': 2, 'offset_days': 14},
            {'type': 'signal',   'subtype': 'usage_decline',        'month': 3, 'offset_days': 0},
            {'type': 'signal',   'subtype': 'competitor_mention',   'month': 4, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'exec_intervention',    'month': 4, 'offset_days': 7},
            {'type': 'outcome',  'subtype': 'churn_risk',           'month': 5, 'offset_days': 0},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'early_detection',      'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'reengagement_plan',    'month': 0, 'offset_days': 7},
            {'type': 'outcome',  'subtype': 'retention_secured',    'month': 1, 'offset_days': 21},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'signal:2',                'type': 'LED_TO',    'confidence': 0.70, 'lag_days': 14, 'label': 'Engagement gap led to NPS decline'},
            {'phase': 'baseline',     'from': 'signal:2',   'to': 'signal:3',                'type': 'LED_TO',    'confidence': 0.75, 'lag_days': 14, 'label': 'Dissatisfaction drove usage decline'},
            {'phase': 'baseline',     'from': 'signal:3',   'to': 'signal:4',                'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 21, 'label': 'Usage decline attracted competitor eval'},
            {'phase': 'baseline',     'from': 'signal:4',   'to': 'decision:1',              'type': 'TRIGGERED', 'confidence': 0.85, 'lag_days': 7,  'label': 'Competitor threat triggered exec intervention'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:churn_risk',      'type': 'LED_TO',    'confidence': 0.65, 'lag_days': 14, 'label': 'Late intervention revealed churn risk'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',              'type': 'TRIGGERED', 'confidence': 0.90, 'lag_days': 7,  'label': 'Early detection triggered re-engagement'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:retention_secured', 'type': 'LED_TO',  'confidence': 0.80, 'lag_days': 21, 'label': 'Re-engagement plan secured retention'},
        ],
    },

    'seasonal_surge': {
        'classification': 'healthy',
        'baseline': [
            {'type': 'signal',   'subtype': 'seasonal_pattern',     'month': 1, 'offset_days': 0},
            {'type': 'signal',   'subtype': 'capacity_constraint',  'month': 3, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'capacity_planning',    'month': 3, 'offset_days': 7},
            {'type': 'decision', 'subtype': 'expansion_proposal',   'month': 4, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'expansion_opportunity', 'month': 4, 'offset_days': 14},
            {'type': 'outcome',  'subtype': 'cost_avoidance',       'month': 5, 'offset_days': 0},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'proactive_planning',   'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'pre_surge_expansion',  'month': 0, 'offset_days': 14},
            {'type': 'outcome',  'subtype': 'expansion_captured',   'month': 1, 'offset_days': 14},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'signal:2',                    'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 30, 'label': 'Seasonal pattern led to capacity constraint'},
            {'phase': 'baseline',     'from': 'signal:2',   'to': 'decision:1',                  'type': 'TRIGGERED', 'confidence': 0.90, 'lag_days': 7,  'label': 'Capacity constraint triggered planning'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'decision:2',                  'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 14, 'label': 'Capacity planning led to expansion proposal'},
            {'phase': 'baseline',     'from': 'decision:2', 'to': 'outcome:expansion_opportunity', 'type': 'LED_TO',  'confidence': 0.80, 'lag_days': 14, 'label': 'Proposal identified expansion opportunity'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'outcome:cost_avoidance',      'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 30, 'label': 'Proactive planning avoided emergency costs'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',                  'type': 'TRIGGERED', 'confidence': 0.90, 'lag_days': 7,  'label': 'Proactive planning triggered pre-surge expansion'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:expansion_captured',  'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 14, 'label': 'Pre-surge expansion captured revenue'},
        ],
    },

    'exec_sponsor_change': {
        'classification': 'at_risk',
        'baseline': [
            {'type': 'signal',   'subtype': 'champion_departure',    'month': 2, 'offset_days': 0},
            {'type': 'signal',   'subtype': 'engagement_gap',        'month': 2, 'offset_days': 14},
            {'type': 'signal',   'subtype': 'usage_decline',         'month': 3, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'stakeholder_mapping',   'month': 3, 'offset_days': 7},
            {'type': 'decision', 'subtype': 'exec_reengagement',     'month': 4, 'offset_days': 0},
            {'type': 'outcome',  'subtype': 'relationship_reset',    'month': 4, 'offset_days': 14},
            {'type': 'outcome',  'subtype': 'renewal_uncertainty',   'month': 5, 'offset_days': 0},
        ],
        'intervention': [
            {'type': 'signal',   'subtype': 'new_champion_identified', 'month': 0, 'offset_days': 0},
            {'type': 'decision', 'subtype': 'onboarding_new_exec',     'month': 0, 'offset_days': 7},
            {'type': 'outcome',  'subtype': 'renewal_confirmed',       'month': 1, 'offset_days': 21},
        ],
        'edge_topology': [
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'signal:2',                   'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 14, 'label': 'Champion departure created engagement gap'},
            {'phase': 'baseline',     'from': 'signal:2',   'to': 'signal:3',                   'type': 'LED_TO',    'confidence': 0.75, 'lag_days': 14, 'label': 'Engagement gap led to usage decline'},
            {'phase': 'baseline',     'from': 'signal:3',   'to': 'decision:1',                 'type': 'TRIGGERED', 'confidence': 0.80, 'lag_days': 7,  'label': 'Usage decline triggered stakeholder mapping'},
            {'phase': 'baseline',     'from': 'decision:1', 'to': 'decision:2',                 'type': 'LED_TO',    'confidence': 0.80, 'lag_days': 14, 'label': 'Mapping led to exec re-engagement plan'},
            {'phase': 'baseline',     'from': 'decision:2', 'to': 'outcome:relationship_reset', 'type': 'LED_TO',    'confidence': 0.70, 'lag_days': 14, 'label': 'Re-engagement initiated relationship reset'},
            {'phase': 'baseline',     'from': 'signal:1',   'to': 'outcome:renewal_uncertainty', 'type': 'CAUSED_BY', 'confidence': 0.80, 'lag_days': 45, 'label': 'Champion departure caused renewal uncertainty'},
            {'phase': 'intervention', 'from': 'signal:1',   'to': 'decision:1',                 'type': 'TRIGGERED', 'confidence': 0.90, 'lag_days': 7,  'label': 'New champion identified triggered exec onboarding'},
            {'phase': 'intervention', 'from': 'decision:1', 'to': 'outcome:renewal_confirmed',  'type': 'LED_TO',    'confidence': 0.85, 'lag_days': 21, 'label': 'Exec onboarding secured renewal'},
        ],
    },
}

# Causal edge types that require temporal validation (from must precede to)
CAUSAL_EDGE_TYPES: frozenset[str] = frozenset({'LED_TO', 'TRIGGERED', 'CAUSED_BY'})


# ═══════════════════════════════════════════════════════════════════════════════
# InDBRefRegistry — resolves symbolic refs to real ContextNode IDs
# ═══════════════════════════════════════════════════════════════════════════════

class InDBRefRegistry:
    """
    Builds ref→node_id map from real ContextNode rows ordered by occurred_at.

    Symbolic ref formats:
      'signal:N'          → Nth SIGNAL node (1-indexed, ordered by occurred_at)
      'decision:N'        → Nth DECISION node (1-indexed, ordered by occurred_at)
      'outcome:type_name' → OUTCOME node where outcome_type matches
    """

    def __init__(self, account_id: int):
        self.account_id = account_id
        self._signals: list[tuple[int, Optional[datetime]]] = []
        self._decisions: list[tuple[int, Optional[datetime]]] = []
        self._outcomes: dict[str, tuple[int, Optional[datetime]]] = {}
        self._outcomes_by_idx: list[tuple[int, Optional[datetime]]] = []  # positional fallback
        self._build()

    def _build(self):
        from models import ContextNode
        from extensions import db

        nodes = (
            db.session.query(ContextNode)
            .filter_by(account_id=self.account_id)
            .order_by(ContextNode.occurred_at)
            .all()
        )

        for n in nodes:
            ts = n.occurred_at  # already a datetime or None
            if n.node_type == 'SIGNAL':
                self._signals.append((n.node_id, ts))
            elif n.node_type == 'DECISION':
                self._decisions.append((n.node_id, ts))
            elif n.node_type == 'OUTCOME':
                self._outcomes_by_idx.append((n.node_id, ts))
                # Register by node_subtype (outcome_type)
                if n.node_subtype:
                    otype = n.node_subtype.strip().lower()
                    self._outcomes[otype] = (n.node_id, ts)
                # Also check properties for explicit outcome_type field
                props = n.properties or {}
                outcome_type_from_props = str(props.get('outcome_type', '')).strip().lower()
                if outcome_type_from_props and outcome_type_from_props not in self._outcomes:
                    self._outcomes[outcome_type_from_props] = (n.node_id, ts)
                # Register by title (normalised) as additional fallback
                if n.title:
                    title_key = n.title.strip().lower().replace(' ', '_')
                    if title_key not in self._outcomes:
                        self._outcomes[title_key] = (n.node_id, ts)

    def resolve(self, symbolic: str) -> Optional[tuple[int, Optional[datetime]]]:
        """
        Resolve a symbolic reference to (node_id, occurred_at).
        Returns None if the reference cannot be resolved.
        """
        if not symbolic:
            return None

        if symbolic.startswith('signal:'):
            try:
                idx = int(symbolic.split(':', 1)[1]) - 1  # 1-indexed → 0-indexed
            except (ValueError, IndexError):
                return None
            return self._signals[idx] if 0 <= idx < len(self._signals) else None

        if symbolic.startswith('decision:'):
            try:
                idx = int(symbolic.split(':', 1)[1]) - 1
            except (ValueError, IndexError):
                return None
            return self._decisions[idx] if 0 <= idx < len(self._decisions) else None

        if symbolic.startswith('outcome:'):
            otype = symbolic.split(':', 1)[1].strip().lower()
            # 1. Exact subtype match
            hit = self._outcomes.get(otype)
            if hit:
                return hit
            # 2. Positional (outcome:1, outcome:2) — like signals/decisions
            try:
                idx = int(otype) - 1
                return self._outcomes_by_idx[idx] if 0 <= idx < len(self._outcomes_by_idx) else None
            except ValueError:
                pass
            # 3. Fuzzy: any outcome whose key contains the search term
            for key, val in self._outcomes.items():
                if otype in key or key in otype:
                    return val
            # 4. Last resort: return first outcome if only one exists
            if len(self._outcomes_by_idx) == 1:
                return self._outcomes_by_idx[0]
            return None

        return None


# ═══════════════════════════════════════════════════════════════════════════════
# generate_edges — main public function
# ═══════════════════════════════════════════════════════════════════════════════

def generate_edges(account_id: int, arc_type: str, phase: str = 'baseline') -> int:
    """
    Generate ContextEdge rows for account using arc edge_topology.

    Idempotent: deletes existing edges for this account (by joining through
    context_nodes) before inserting new ones.

    Returns count of edges created.
    """
    from models import ContextEdge, ContextNode
    from extensions import db

    # ── Arc type resolution ──
    # Canonical 8: crisis_recovery, exec_sponsor_change, competitive_displacement,
    #   silent_churn, stalled_deployment, land_and_expand, expansion_champion, seasonal_surge
    # Legacy aliases map old names to canonical + template variant keys.
    _ARC_ALIASES = {
        # Legacy classifier names → canonical
        'champion_loss': 'exec_sponsor_change',
        'competitor_evaluation': 'competitive_displacement',
        'ignored_churn': 'silent_churn',
        'proactive_growth': 'expansion_champion',
        'infrastructure_decay': 'stalled_deployment',
        'engagement_decline': 'silent_churn',
        'budget_pressure': 'competitive_displacement',
        'steady_performer': 'seasonal_surge',
        'crisis': 'crisis_recovery',
    }
    resolved_type = _ARC_ALIASES.get(arc_type, arc_type)

    # Look up template: try exact match first, then variants
    arc_def = ARC_TEMPLATES.get(resolved_type)
    if not arc_def:
        # Try variant templates (e.g., competitive_displacement_budget)
        for key in ARC_TEMPLATES:
            if key.startswith(resolved_type):
                arc_def = ARC_TEMPLATES[key]
                break
    if not arc_def:
        arc_def = ARC_TEMPLATES.get('seasonal_surge', {})  # safe fallback

    if resolved_type != arc_type:
        logger.info(f"arc_edge_generator: aliased '{arc_type}' → '{resolved_type}' for account {account_id}")

    # Filter topology to the requested phase
    topology = [
        e for e in arc_def.get('edge_topology', [])
        if e.get('phase', 'baseline') == phase
    ]

    if not topology:
        logger.warning(
            f"arc_edge_generator: no topology for arc={arc_type} phase={phase} "
            f"account={account_id}"
        )
        return 0

    # Delete existing edges for this account (idempotent re-run).
    # ContextEdge has no account_id column — identify via node membership.
    account_node_ids = (
        db.session.query(ContextNode.node_id)
        .filter_by(account_id=account_id)
        .subquery()
    )
    db.session.query(ContextEdge).filter(
        (ContextEdge.from_node_id.in_(account_node_ids))
        | (ContextEdge.to_node_id.in_(account_node_ids))
    ).delete(synchronize_session='fetch')

    registry = InDBRefRegistry(account_id)
    created = 0

    # Also need customer_id for ContextEdge.customer_id
    account_node = (
        db.session.query(ContextNode)
        .filter_by(account_id=account_id)
        .first()
    )
    customer_id = account_node.customer_id if account_node else None

    for edge_def in topology:
        from_resolved = registry.resolve(edge_def.get('from', ''))
        to_resolved   = registry.resolve(edge_def.get('to', ''))

        if from_resolved is None or to_resolved is None:
            logger.warning(
                f"arc_edge_generator: unresolved ref "
                f"acct={account_id} arc={arc_type} phase={phase} "
                f"from={edge_def.get('from')!r} -> {from_resolved} "
                f"to={edge_def.get('to')!r} -> {to_resolved}"
            )
            continue

        from_id, from_date = from_resolved
        to_id,   to_date   = to_resolved

        edge_type = edge_def.get('type', 'RELATES_TO')

        # Temporal validation for causal edges: from must precede to
        if (edge_type in CAUSAL_EDGE_TYPES
                and from_date is not None
                and to_date is not None
                and from_date >= to_date):
            logger.warning(
                f"arc_edge_generator: temporal violation skipped "
                f"acct={account_id} {edge_def.get('from')!r}({from_date}) "
                f"-> {edge_def.get('to')!r}({to_date}) type={edge_type}"
            )
            continue

        label = edge_def.get('label', '')
        confidence = edge_def.get('confidence', 0.7)
        lag_days = edge_def.get('lag_days', 0)

        edge = ContextEdge(
            customer_id  = customer_id,
            from_node_id = from_id,
            to_node_id   = to_id,
            edge_type    = edge_type,
            confidence   = confidence,
            lag_days     = lag_days,
            properties   = {'label': label, 'arc_type': arc_type, 'arc_phase': phase},
            source_platform = 'wizard_a',
            created_by   = 'arc_edge_generator',
        )
        db.session.add(edge)
        created += 1

    db.session.commit()
    logger.info(
        f"arc_edge_generator: created {created} edges "
        f"acct={account_id} arc={arc_type} phase={phase}"
    )
    return created
