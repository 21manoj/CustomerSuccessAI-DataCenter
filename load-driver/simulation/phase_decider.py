"""
PhaseDecider — rule-based trajectory decisions per account per phase.

Pure logic, no I/O. Evaluates rules top-to-bottom against an AccountState.
First match wins. Falls back to 'stable' if no rules match.
"""

import logging
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from simulation.state_reader import AccountState

logger = logging.getLogger(__name__)


@dataclass
class PhaseDecision:
    """What should happen to this account in the next phase."""
    trajectory: str                          # KPI trajectory for _generate_kpi_series()
    target_health_delta: float              # Health shift: -8 for decline, +15 for recovery
    signals_to_inject: List[Dict] = field(default_factory=list)
    outcomes_to_inject: List[Dict] = field(default_factory=list)
    decisions_to_inject: List[Dict] = field(default_factory=list)
    narrative_phase: str = 'baseline'       # baseline | deterioration | intervention | resolution
    explanation: str = ''


# ── Signal templates ──────────────────────────────────────────────────

_SIGNAL_TEMPLATES = {
    'usage_decline': {
        'subtype': 'usage_decline',
        'sentiment': 'negative',
        'content': 'Product usage declining — DAU dropped {pct}% in the last 2 weeks',
    },
    'nps_decline': {
        'subtype': 'nps_decline',
        'sentiment': 'negative',
        'content': 'NPS score declined from {before} to {after} — moving into detractor territory',
    },
    'champion_departure': {
        'subtype': 'champion_departure',
        'sentiment': 'negative',
        'content': 'Key champion {name} has departed — executive sponsor gap created',
    },
    'competitor_mention': {
        'subtype': 'competitor_mention',
        'sentiment': 'negative',
        'content': 'Account mentioned evaluating competitor {competitor} during recent call',
    },
    'support_escalation': {
        'subtype': 'support_escalation',
        'sentiment': 'negative',
        'content': 'Multiple P1 tickets escalated — resolution time exceeding SLA',
    },
    'executive_escalation': {
        'subtype': 'executive_escalation',
        'sentiment': 'negative',
        'content': 'Executive sponsor escalated to leadership — demanding remediation plan',
    },
    'csm_intervention': {
        'subtype': 'csm_intervention',
        'sentiment': 'positive',
        'content': 'CSM intervention initiated — dedicated support pod assigned',
    },
    'kpi_recovery': {
        'subtype': 'kpi_recovery',
        'sentiment': 'positive',
        'content': 'Key metrics showing recovery — adoption rate improving week-over-week',
    },
    'champion_reengagement': {
        'subtype': 'champion_reengagement',
        'sentiment': 'positive',
        'content': 'New champion identified and engaged — exec sponsor meeting scheduled',
    },
    'expansion_signal': {
        'subtype': 'expansion_discussion',
        'sentiment': 'positive',
        'content': 'Account exploring expansion to additional business units',
    },
    'deployment_improvement': {
        'subtype': 'deployment_improvement',
        'sentiment': 'positive',
        'content': 'Deployment milestones hit — platform fully operational across all teams',
    },
    'routine_review': {
        'subtype': 'routine_review',
        'sentiment': 'neutral',
        'content': 'Quarterly business review completed — account stable, no action needed',
    },
    'engagement_gap': {
        'subtype': 'engagement_gap',
        'sentiment': 'negative',
        'content': 'No executive touchpoint in 45+ days — engagement cadence broken',
    },
    'critical_incident': {
        'subtype': 'critical_incident',
        'sentiment': 'negative',
        'content': 'Critical platform incident — service degradation affecting all users',
    },
}

# ── Outcome templates ─────────────────────────────────────────────────

_OUTCOME_TEMPLATES = {
    'revenue_at_risk': {
        'subtype': 'renewal_at_risk',
        'revenue_impact_type': 'at_risk',
        'revenue_pct': -0.15,  # 15% of ARR at risk
        'title': 'Renewal at Risk — {account_name}',
    },
    'revenue_protected': {
        'subtype': 'churn_averted',
        'revenue_impact_type': 'revenue_protected',
        'revenue_pct': 0.10,
        'title': 'Revenue Protected — {account_name}',
    },
    'expansion_opportunity': {
        'subtype': 'expansion_opportunity',
        'revenue_impact_type': 'expansion_opportunity',
        'revenue_pct': 0.15,
        'title': 'Expansion Potential — {account_name}',
    },
}


# ── Rule table ────────────────────────────────────────────────────────

RULES = [
    # Critical accounts — no playbook → keep declining
    {
        'name': 'critical_declining_no_pb',
        'conditions': {'health_band': 'critical', 'active_playbook': False,
                       'closed_resolved': False, 'slope': 'declining'},
        'decision': {
            'trajectory': 'declining', 'target_health_delta': -8,
            'signals': ['usage_decline', 'nps_decline'],
            'outcomes': ['revenue_at_risk'],
            'narrative_phase': 'deterioration',
        },
    },
    # Critical + flat → slowly worsening
    {
        'name': 'critical_flat_no_pb',
        'conditions': {'health_band': 'critical', 'active_playbook': False,
                       'closed_resolved': False, 'slope': 'flat'},
        'decision': {
            'trajectory': 'slow_decline', 'target_health_delta': -3,
            'signals': ['support_escalation'],
            'outcomes': ['revenue_at_risk'],
            'narrative_phase': 'baseline',
        },
    },
    # Critical + active playbook → strong recovery (must punch through to at-risk)
    {
        'name': 'critical_pb_active',
        'conditions': {'health_band': 'critical', 'active_playbook': True},
        'decision': {
            'trajectory': 'recovering', 'target_health_delta': 10,
            'signals': ['csm_intervention', 'kpi_recovery'],
            'narrative_phase': 'intervention',
        },
    },
    # Critical + resolved playbook → strong recovery
    {
        'name': 'critical_pb_resolved',
        'conditions': {'health_band': 'critical', 'closed_resolved': True},
        'decision': {
            'trajectory': 'improving', 'target_health_delta': 15,
            'signals': ['kpi_recovery', 'champion_reengagement'],
            'outcomes': ['revenue_protected'],
            'narrative_phase': 'resolution',
        },
    },
    # At-risk + declining → inject warning signals (gradual, not cliff)
    {
        'name': 'at_risk_declining_no_pb',
        'conditions': {'health_band': 'at_risk', 'active_playbook': False, 'slope': 'declining'},
        'decision': {
            'trajectory': 'slow_decline', 'target_health_delta': -5,
            'signals': ['competitor_mention', 'usage_decline'],
            'outcomes': ['revenue_at_risk'],
            'narrative_phase': 'deterioration',
        },
    },
    # At-risk + flat → silent churn pattern
    {
        'name': 'at_risk_flat_no_pb',
        'conditions': {'health_band': 'at_risk', 'active_playbook': False, 'slope': 'flat'},
        'decision': {
            'trajectory': 'slow_decline', 'target_health_delta': -5,
            'signals': ['usage_decline'],
            'narrative_phase': 'baseline',
        },
    },
    # At-risk + active playbook → sustained recovery (push toward healthy ≥70)
    {
        'name': 'at_risk_pb_active',
        'conditions': {'health_band': 'at_risk', 'active_playbook': True},
        'decision': {
            'trajectory': 'improving', 'target_health_delta': 7,
            'signals': ['kpi_recovery', 'champion_reengagement'],
            'narrative_phase': 'intervention',
        },
    },
    # At-risk + resolved playbook → recovery
    {
        'name': 'at_risk_pb_resolved',
        'conditions': {'health_band': 'at_risk', 'closed_resolved': True},
        'decision': {
            'trajectory': 'improving', 'target_health_delta': 10,
            'signals': ['deployment_improvement'],
            'outcomes': ['revenue_protected'],
            'narrative_phase': 'resolution',
        },
    },
    # Healthy + active playbook → sustain and expand (just crossed threshold)
    {
        'name': 'healthy_pb_active',
        'conditions': {'health_band': 'healthy', 'active_playbook': True},
        'decision': {
            'trajectory': 'improving', 'target_health_delta': 5,
            'signals': ['deployment_improvement', 'expansion_signal'],
            'outcomes': ['revenue_protected', 'expansion_opportunity'],
            'narrative_phase': 'resolution',
        },
    },
    # Healthy + improving (no playbook) → expansion signals
    {
        'name': 'healthy_improving',
        'conditions': {'health_band': 'healthy', 'slope': 'improving'},
        'decision': {
            'trajectory': 'improving', 'target_health_delta': 3,
            'signals': ['expansion_signal'],
            'outcomes': ['expansion_opportunity'],
            'narrative_phase': 'baseline',
        },
    },
    # Healthy + declining + no playbook → early warning before crossing at-risk
    {
        'name': 'healthy_declining_no_pb',
        'conditions': {'health_band': 'healthy', 'active_playbook': False, 'slope': 'declining'},
        'decision': {
            'trajectory': 'slow_decline', 'target_health_delta': -3,
            'signals': ['usage_decline', 'engagement_gap'],
            'outcomes': ['revenue_at_risk'],
            'narrative_phase': 'deterioration',
        },
    },
    # Healthy + stable → business as usual
    {
        'name': 'healthy_stable',
        'conditions': {'health_band': 'healthy'},
        'decision': {
            'trajectory': 'stable', 'target_health_delta': 3,
            'signals': ['routine_review'],
            'narrative_phase': 'baseline',
        },
    },
]

# Sudden swing rule — applied to 1-2 healthy accounts at mid-cycle
_SUDDEN_SWING = {
    'name': 'sudden_swing',
    'decision': {
        'trajectory': 'declining', 'target_health_delta': -20,
        'signals': ['champion_departure', 'usage_decline', 'executive_escalation'],
        'outcomes': ['revenue_at_risk'],
        'narrative_phase': 'deterioration',
    },
}


class PhaseDecider:
    """Decide what happens next for each account based on current state."""

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def decide(self, state: AccountState, phase_number: int, total_phases: int) -> PhaseDecision:
        """Evaluate rules for one account. First match wins."""

        # Sudden swing: at mid-cycle, 1 healthy account gets hit
        # (selection happens in decide_all, not here)

        for rule in RULES:
            if self._match_rule(state, rule['conditions']):
                return self._build_decision(state, rule)

        # Fallback: stable
        return PhaseDecision(
            trajectory='stable',
            target_health_delta=0,
            signals_to_inject=[],
            narrative_phase='baseline',
            explanation=f'No rule matched — defaulting to stable',
        )

    def decide_all(
        self,
        states: List[AccountState],
        phase_number: int,
        total_phases: int,
    ) -> List[tuple]:
        """Decide for all accounts. Returns [(state, decision), ...]

        Applies sudden swing to 1 healthy account at mid-cycle.
        """
        decisions = []
        swing_applied = False

        for state in states:
            # Sudden swing at mid-cycle for 1 healthy account
            if (phase_number == total_phases // 2
                    and state.health_band == 'healthy'
                    and not swing_applied
                    and self._rng.random() < 0.5):
                decision = self._build_decision(state, _SUDDEN_SWING)
                decision.explanation = (
                    f'SUDDEN SWING: champion departure at mid-cycle '
                    f'(phase {phase_number}/{total_phases})'
                )
                swing_applied = True
                logger.info(
                    f"  SUDDEN SWING: {state.account_name} "
                    f"({state.health_score:.0f} → {state.health_score + decision.target_health_delta:.0f})"
                )
            else:
                decision = self.decide(state, phase_number, total_phases)

            decisions.append((state, decision))

        return decisions

    def _match_rule(self, state: AccountState, conditions: Dict) -> bool:
        """Check if all conditions match."""
        if 'health_band' in conditions:
            if state.health_band != conditions['health_band']:
                return False

        if 'active_playbook' in conditions:
            has_active = len(state.active_playbooks) > 0
            if conditions['active_playbook'] != has_active:
                return False

        if 'closed_resolved' in conditions:
            has_resolved = any(
                p.get('outcome') == 'resolved'
                for p in state.closed_playbooks
            )
            if conditions['closed_resolved'] != has_resolved:
                return False

        if 'slope' in conditions:
            if state.health_slope != conditions['slope']:
                return False

        return True

    def _build_decision(self, state: AccountState, rule: Dict) -> PhaseDecision:
        """Build PhaseDecision from a matched rule."""
        d = rule['decision']

        # Build signal list from templates
        signals = []
        for sig_key in d.get('signals', []):
            tmpl = _SIGNAL_TEMPLATES.get(sig_key, {})
            if tmpl:
                content = tmpl['content'].format(
                    pct=self._rng.randint(15, 35),
                    before=self._rng.randint(35, 50),
                    after=self._rng.randint(10, 25),
                    name=f'VP of {self._rng.choice(["Engineering", "Product", "Operations"])}',
                    competitor=self._rng.choice(['Competitor A', 'Competitor B', 'Salesforce', 'ServiceNow']),
                )
                signals.append({
                    'signal_type': tmpl['subtype'],
                    'sentiment': tmpl['sentiment'],
                    'content': content,
                })

        # Build outcome list
        outcomes = []
        for out_key in d.get('outcomes', []):
            tmpl = _OUTCOME_TEMPLATES.get(out_key, {})
            if tmpl:
                outcomes.append({
                    'subtype': tmpl['subtype'],
                    'revenue_impact_type': tmpl['revenue_impact_type'],
                    'revenue_impact': round(state.arr * tmpl['revenue_pct']),
                    'title': tmpl['title'].format(account_name=state.account_name),
                })

        return PhaseDecision(
            trajectory=d['trajectory'],
            target_health_delta=d['target_health_delta'],
            signals_to_inject=signals,
            outcomes_to_inject=outcomes,
            narrative_phase=d.get('narrative_phase', 'baseline'),
            explanation=f"Rule '{rule['name']}': {d['trajectory']} (delta={d['target_health_delta']:+.0f})",
        )
