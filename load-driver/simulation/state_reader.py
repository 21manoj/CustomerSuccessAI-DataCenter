"""
StateReader — reads current account state from CS Pulse via REST API.

No direct DB access; works entirely over HTTP so it can run from a laptop
against a remote EC2 instance.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AccountState:
    """Snapshot of one account's current state, used by PhaseDecider."""
    account_id: int
    account_name: str
    health_score: float                     # 0-100
    health_band: str                        # 'critical' | 'at_risk' | 'healthy'
    arr: float
    pillar_scores: Dict[str, float] = field(default_factory=dict)
    arc_type: str = ''                      # Wizard A classification
    arc_phase: str = ''                     # baseline | deterioration | intervention | resolution
    arc_confidence: float = 0.0
    health_slope: str = 'flat'              # 'improving' | 'declining' | 'flat'
    slope_value: float = 0.0               # numeric pts/month
    active_playbooks: List[Dict] = field(default_factory=list)
    closed_playbooks: List[Dict] = field(default_factory=list)
    recent_signal_types: List[str] = field(default_factory=list)
    renewal_date: Optional[str] = None
    last_kpi_date: Optional[str] = None     # latest measured_at — for date chaining


def _classify_health(score: float) -> str:
    if score < 50:
        return 'critical'
    if score < 70:
        return 'at_risk'
    return 'healthy'


def _compute_slope(monthly_scores: List[Dict]) -> Tuple[str, float]:
    """Compute health slope from monthly snapshots.

    Returns (label, value) where value is pts/month.
    """
    if len(monthly_scores) < 2:
        return ('flat', 0.0)

    # Use last 3 months for slope
    recent = monthly_scores[-3:] if len(monthly_scores) >= 3 else monthly_scores
    scores = [m.get('health_score', 0) for m in recent if m.get('health_score') is not None]
    if len(scores) < 2:
        return ('flat', 0.0)

    # Simple linear: (last - first) / months
    delta = scores[-1] - scores[0]
    months = max(1, len(scores) - 1)
    slope = delta / months

    if slope > 1.5:
        return ('improving', round(slope, 2))
    elif slope < -1.5:
        return ('declining', round(slope, 2))
    return ('flat', round(slope, 2))


class StateReader:
    """Reads current account state from CS Pulse REST API."""

    def __init__(self, client, customer_id: int):
        self.client = client
        self.customer_id = customer_id

    def read_all(self) -> List[AccountState]:
        """Read state for all accounts. Returns list of AccountState."""
        accounts = self._read_accounts()
        if not accounts:
            logger.warning(f"No accounts found for customer {self.customer_id}")
            return []

        # Read active/completed playbooks
        active_pbs = self._read_playbooks('active')
        completed_pbs = self._read_playbooks('completed')

        # Build playbook lookup by account_id
        active_by_acct = {}
        for pb in active_pbs:
            aid = pb.get('account_id')
            active_by_acct.setdefault(aid, []).append(pb)

        completed_by_acct = {}
        for pb in completed_pbs:
            aid = pb.get('account_id')
            completed_by_acct.setdefault(aid, []).append(pb)

        states = []
        for acct in accounts:
            aid = acct.get('account_id')
            health = float(acct.get('health_score') or 0)

            # Health history for slope
            history = self._read_health_history(aid)
            slope_label, slope_val = _compute_slope(history)

            # Recent signals
            signals = self._read_recent_signals(aid)

            # Renewal date from profile_metadata
            meta = acct.get('profile_metadata') or {}
            renewal = meta.get('renewal_date') or meta.get('contract_renewal_date')

            # Last KPI date
            last_kpi = acct.get('last_data_at') or acct.get('updated_at')

            state = AccountState(
                account_id=aid,
                account_name=acct.get('account_name', f'Account {aid}'),
                health_score=health,
                health_band=_classify_health(health),
                arr=float(acct.get('revenue') or acct.get('arr') or 0),
                pillar_scores=acct.get('pillar_scores') or acct.get('contributing_pillars') or {},
                arc_type=acct.get('arc_type', ''),
                arc_phase=acct.get('arc_phase', ''),
                arc_confidence=float(acct.get('arc_confidence') or 0),
                health_slope=slope_label,
                slope_value=slope_val,
                active_playbooks=active_by_acct.get(aid, []),
                closed_playbooks=completed_by_acct.get(aid, []),
                recent_signal_types=[s.get('node_subtype', '') for s in signals],
                renewal_date=str(renewal) if renewal else None,
                last_kpi_date=str(last_kpi)[:10] if last_kpi else None,
            )
            states.append(state)

        logger.info(
            f"StateReader: {len(states)} accounts — "
            f"{sum(1 for s in states if s.health_band == 'critical')} critical, "
            f"{sum(1 for s in states if s.health_band == 'at_risk')} at_risk, "
            f"{sum(1 for s in states if s.health_band == 'healthy')} healthy"
        )
        return states

    def _read_accounts(self) -> List[Dict]:
        """Fetch accounts via REST. Returns raw account dicts."""
        try:
            resp = self.client.get(f'/api/accounts')
            if isinstance(resp, dict):
                return resp.get('accounts', [])
            if isinstance(resp, list):
                return resp
        except Exception as e:
            logger.error(f"Failed to read accounts: {e}")
        return []

    def _read_health_history(self, account_id: int) -> List[Dict]:
        """Fetch monthly health scores for slope computation."""
        try:
            resp = self.client.get(f'/api/health-scores', params={
                'customer_id': self.customer_id,
                'months': 6,
            })
            if isinstance(resp, dict):
                all_scores = resp.get('health_scores', [])
                # Filter to this account
                return [s for s in all_scores if s.get('account_id') == account_id]
        except Exception as e:
            logger.debug(f"Health history unavailable for account {account_id}: {e}")
        return []

    def _read_playbooks(self, status: str) -> List[Dict]:
        """Fetch active or completed playbooks."""
        try:
            resp = self.client.get(f'/api/playbooks/{status}')
            if isinstance(resp, dict):
                return resp.get(f'{status}_playbooks', [])
        except Exception as e:
            logger.debug(f"Playbooks ({status}) unavailable: {e}")
        return []

    def _read_recent_signals(self, account_id: int) -> List[Dict]:
        """Fetch recent context graph signals for this account."""
        try:
            resp = self.client.get(f'/api/context-graph/nodes', params={
                'account_id': account_id,
                'node_type': 'SIGNAL',
                'limit': 20,
            })
            if isinstance(resp, dict):
                return resp.get('nodes', [])
        except Exception:
            pass
        return []
