#!/usr/bin/env python3
"""
Google Sheets Simulator for CS Pulse Load Testing (Ring 3)

Generates realistic Google Sheets-format KPI data, qualitative signals,
and contact/champion updates. Output matches the schemas expected by
the /api/data-ingestion/* endpoints, so the full pipeline can be tested
without an actual Google Sheets integration.
"""

import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DC2_S KPI definitions — codes, display names, units, and realistic ranges
# ---------------------------------------------------------------------------
KPI_DEFINITIONS = {
    'nrr': {
        'display_name': 'Net Revenue Retention',
        'unit': 'percent',
        'min': 85.0,
        'max': 130.0,
        'target': 105.0,
        'pillar': 'EX',
    },
    'logo_retention': {
        'display_name': 'Logo Retention Rate',
        'unit': 'percent',
        'min': 80.0,
        'max': 100.0,
        'target': 95.0,
        'pillar': 'CH',
    },
    'support_ticket_volume': {
        'display_name': 'Support Ticket Volume',
        'unit': 'count',
        'min': 0,
        'max': 120,
        'target': 25,
        'pillar': 'OS',
        'lower_is_better': True,
    },
    'p1_mttr': {
        'display_name': 'P1 Mean Time to Resolve',
        'unit': 'hours',
        'min': 0.5,
        'max': 72.0,
        'target': 4.0,
        'pillar': 'OS',
        'lower_is_better': True,
    },
    'adoption_rate': {
        'display_name': 'Product Adoption Rate',
        'unit': 'percent',
        'min': 10.0,
        'max': 100.0,
        'target': 75.0,
        'pillar': 'DV',
    },
    'expansion_revenue': {
        'display_name': 'Expansion Revenue',
        'unit': 'usd',
        'min': 0,
        'max': 500000,
        'target': 50000,
        'pillar': 'EX',
    },
    'csat': {
        'display_name': 'Customer Satisfaction Score',
        'unit': 'score',
        'min': 1.0,
        'max': 5.0,
        'target': 4.2,
        'pillar': 'CH',
    },
    'login_frequency': {
        'display_name': 'Login Frequency (30d)',
        'unit': 'count',
        'min': 0,
        'max': 500,
        'target': 120,
        'pillar': 'DV',
    },
    'feature_adoption': {
        'display_name': 'Feature Adoption Breadth',
        'unit': 'percent',
        'min': 5.0,
        'max': 100.0,
        'target': 60.0,
        'pillar': 'DV',
    },
    'gpu_utilization': {
        'display_name': 'GPU Utilization',
        'unit': 'percent',
        'min': 0.0,
        'max': 100.0,
        'target': 70.0,
        'pillar': 'AI',
    },
}

ALL_KPI_CODES = list(KPI_DEFINITIONS.keys())

# ---------------------------------------------------------------------------
# Signal types for qualitative signal generation
# ---------------------------------------------------------------------------
SIGNAL_TYPES = [
    {
        'type': 'champion_change',
        'severity': 'high',
        'messages': [
            'Primary champion {name} left the organization',
            'New VP of Engineering onboarded — champion risk',
            'Key stakeholder {name} moved to different department',
        ],
    },
    {
        'type': 'support_escalation',
        'severity': 'high',
        'messages': [
            'P1 ticket escalated to engineering — SLA breach risk',
            'Multiple P2 tickets opened in past 48h',
            'Customer requested executive escalation on ticket #{ticket}',
        ],
    },
    {
        'type': 'usage_decline',
        'severity': 'medium',
        'messages': [
            'Login frequency dropped 40% month-over-month',
            'API call volume decreased 25% in last 2 weeks',
            'Feature adoption breadth declined from 65% to 42%',
        ],
    },
    {
        'type': 'expansion_signal',
        'severity': 'low',
        'messages': [
            'Customer inquired about enterprise tier pricing',
            'New team onboarded — 15 additional seats requested',
            'Customer asked about GPU cluster expansion options',
        ],
    },
    {
        'type': 'renewal_risk',
        'severity': 'high',
        'messages': [
            'Renewal conversation stalled — no response in 14 days',
            'Customer benchmarking competitors ahead of renewal',
            'Budget holder flagged cost concerns in QBR',
        ],
    },
]

# ---------------------------------------------------------------------------
# Contact/champion names for realistic updates
# ---------------------------------------------------------------------------
FIRST_NAMES = [
    'Sarah', 'James', 'Maria', 'David', 'Emily', 'Michael', 'Jessica',
    'Robert', 'Amanda', 'Daniel', 'Lisa', 'Kevin', 'Rachel', 'Thomas',
    'Olivia', 'Andrew', 'Sophia', 'Benjamin', 'Chloe', 'Nathan',
]
LAST_NAMES = [
    'Chen', 'Patel', 'Williams', 'Garcia', 'Johnson', 'Kim', 'Martinez',
    'Anderson', 'Taylor', 'Brown', 'Lee', 'Wilson', 'Nguyen', 'Jackson',
    'Thompson', 'White', 'Harris', 'Clark', 'Lewis', 'Robinson',
]
TITLES = [
    'VP of Engineering', 'Director of IT', 'CTO', 'Head of Data',
    'Senior Architect', 'Platform Lead', 'DevOps Manager',
    'Head of Infrastructure', 'Chief Data Officer', 'IT Director',
]


class GoogleSheetsSimulator:
    """
    Generates realistic Google Sheets-format data payloads for the
    CS Pulse data-ingestion API endpoints.

    All generated data matches the schemas expected by:
      - POST /api/data-ingestion/kpis
      - POST /api/data-ingestion/signals
      - POST /api/data-ingestion/contacts
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Args:
            seed: Optional random seed for reproducible output.
        """
        self.rng = random.Random(seed)
        if seed is not None:
            logger.debug(f"GoogleSheetsSimulator initialized with seed={seed}")

    # ------------------------------------------------------------------
    # KPI delta generation
    # ------------------------------------------------------------------

    def generate_kpi_delta(
        self,
        accounts: List[Dict[str, Any]],
        num_kpis: int = 10,
        measurement_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate a batch of KPI measurements as JSON, matching the
        /api/data-ingestion/kpis schema.

        Each record represents one KPI measurement for one account,
        as if a Google Sheet row was updated and pushed via n8n.

        Args:
            accounts: List of account dicts (must contain 'account_id').
            num_kpis: Number of distinct KPI codes to include per account
                      (max 10, will be clamped).
            measurement_date: ISO date string (default: today).

        Returns:
            List of KPI measurement dicts ready to POST.
        """
        num_kpis = min(num_kpis, len(ALL_KPI_CODES))
        selected_codes = self.rng.sample(ALL_KPI_CODES, num_kpis)
        measurement_date = measurement_date or datetime.utcnow().strftime('%Y-%m-%d')

        measurements = []
        for account in accounts:
            account_id = account.get('account_id')
            account_name = account.get('account_name', f'Account-{account_id}')

            for code in selected_codes:
                defn = KPI_DEFINITIONS[code]
                value = self._random_kpi_value(defn)
                measurements.append({
                    'account_id': account_id,
                    'account_name': account_name,
                    'kpi_code': code,
                    'kpi_name': defn['display_name'],
                    'value': value,
                    'unit': defn['unit'],
                    'measured_at': measurement_date,
                    'source': 'google_sheets_simulator',
                    'pillar': defn['pillar'],
                })

        logger.info(
            f"Generated {len(measurements)} KPI measurements "
            f"({num_kpis} KPIs x {len(accounts)} accounts)"
        )
        return measurements

    def _random_kpi_value(self, defn: Dict[str, Any]) -> float:
        """Generate a random KPI value within realistic bounds."""
        lo, hi = defn['min'], defn['max']
        target = defn['target']

        # Bias toward the target with some variance
        # 70% of the time, cluster near the target; 30% wider spread
        if self.rng.random() < 0.7:
            spread = (hi - lo) * 0.15
            value = self.rng.gauss(target, spread)
        else:
            value = self.rng.uniform(lo, hi)

        # Clamp and round
        value = max(lo, min(hi, value))
        if defn['unit'] == 'count':
            return round(value)
        elif defn['unit'] == 'usd':
            return round(value, 2)
        else:
            return round(value, 2)

    # ------------------------------------------------------------------
    # Signal batch generation
    # ------------------------------------------------------------------

    def generate_signal_batch(
        self,
        accounts: List[Dict[str, Any]],
        num_signals: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate qualitative signals as JSON, matching the
        /api/data-ingestion/signals schema.

        Signals represent events like champion changes, support
        escalations, usage declines, etc.

        Args:
            accounts: List of account dicts.
            num_signals: Number of signals to generate (spread across
                         accounts).

        Returns:
            List of signal dicts ready to POST.
        """
        signals = []
        now = datetime.utcnow()

        for i in range(num_signals):
            account = self.rng.choice(accounts)
            account_id = account.get('account_id')
            account_name = account.get('account_name', f'Account-{account_id}')

            signal_def = self.rng.choice(SIGNAL_TYPES)
            message_template = self.rng.choice(signal_def['messages'])
            message = message_template.format(
                name=f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}",
                ticket=self.rng.randint(10000, 99999),
            )

            detected_at = (now - timedelta(hours=self.rng.randint(0, 72))).isoformat() + 'Z'

            signals.append({
                'signal_id': str(uuid.uuid4()),
                'account_id': account_id,
                'account_name': account_name,
                'signal_type': signal_def['type'],
                'severity': signal_def['severity'],
                'message': message,
                'detected_at': detected_at,
                'source': 'google_sheets_simulator',
                'metadata': {
                    'simulator_version': '1.0',
                    'batch_index': i,
                },
            })

        logger.info(f"Generated {len(signals)} qualitative signals across {len(accounts)} accounts")
        return signals

    # ------------------------------------------------------------------
    # Contact / champion update generation
    # ------------------------------------------------------------------

    def generate_contact_updates(
        self,
        accounts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Generate contact and champion update records, matching the
        /api/data-ingestion/contacts schema.

        Simulates what happens when a Google Sheet of customer contacts
        is refreshed — some contacts are new, some have updated roles,
        and some are flagged as departed (champion risk).

        Args:
            accounts: List of account dicts.

        Returns:
            List of contact update dicts ready to POST.
        """
        updates = []
        for account in accounts:
            account_id = account.get('account_id')
            account_name = account.get('account_name', f'Account-{account_id}')

            # Each account gets 1-3 contact updates
            num_contacts = self.rng.randint(1, 3)
            for _ in range(num_contacts):
                first = self.rng.choice(FIRST_NAMES)
                last = self.rng.choice(LAST_NAMES)
                title = self.rng.choice(TITLES)
                is_champion = self.rng.random() < 0.3
                is_departed = self.rng.random() < 0.1

                status = 'departed' if is_departed else 'active'

                updates.append({
                    'account_id': account_id,
                    'account_name': account_name,
                    'contact_name': f'{first} {last}',
                    'contact_email': f'{first.lower()}.{last.lower()}@{account_name.lower().replace(" ", "")}.com',
                    'title': title,
                    'is_champion': is_champion,
                    'status': status,
                    'updated_at': datetime.utcnow().isoformat() + 'Z',
                    'source': 'google_sheets_simulator',
                })

        active_count = sum(1 for u in updates if u['status'] == 'active')
        departed_count = sum(1 for u in updates if u['status'] == 'departed')
        champion_count = sum(1 for u in updates if u['is_champion'])
        logger.info(
            f"Generated {len(updates)} contact updates "
            f"(active={active_count}, departed={departed_count}, champions={champion_count})"
        )
        return updates
