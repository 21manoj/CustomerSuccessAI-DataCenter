#!/usr/bin/env python3
"""
Scenario: Manifest-Driven Data Load (V3)

Reads a JSON manifest and generates deterministic CSV data for accounts,
KPI measurements, signals, stakeholders, engagement events, profiles,
products, outcomes, decisions, and signal edges.

Key V3 additions:
- NarrativeTimelinePlanner: causally-ordered event timelines per account
  (signals before decisions before outcomes)
- Phase/intervention support merged from V2
- Post-process validation merged from V2
- _header_use_account_id merged from V2

Usage as scenario:
    ScenarioManifest(client, args).run()

Usage standalone:
    gen = ManifestCSVGenerator("manifests/novastar_dc2s.json")
    gen.generate_all("/tmp/novastar/")
"""

import csv
import io
import json
import logging
import math
import random
import time
import uuid as uuid_mod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseScenario

logger = logging.getLogger(__name__)

# ── Catalog loader (for KPI metadata) ──
try:
    import sys
    _ld_root = str(Path(__file__).resolve().parent.parent)
    if _ld_root not in sys.path:
        sys.path.insert(0, _ld_root)
    from catalog_loader import get_kpis, get_kpi_target
    _catalog_available = True
except ImportError:
    _catalog_available = False
    logger.warning("catalog_loader not available — using manifest KPI codes only")


# ═══════════════════════════════════════════════════════════════════════
# NarrativeTimelinePlanner — causally-ordered event timelines
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class PlannedEvent:
    """A single event in a narrative timeline with a concrete date."""
    account_id: int
    phase: str
    event_type: str       # signal, decision, outcome, stakeholder
    event_subtype: str    # kpi_decline, escalation_to_exec, churn_risk, etc.
    date: datetime
    offset_days: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def date_str(self) -> str:
        return self.date.strftime('%Y-%m-%d')


class NarrativeTimelinePlanner:
    """
    Generates a causally-ordered event timeline per account.

    For each account, reads the arc_type from the manifest and produces
    a spine of events where:
    - signal.date < decision.date (decisions reference signals)
    - decision.date < outcome.date (outcomes reference decisions)
    - stakeholder engagement aligns with referenced decisions

    Generators pull dates FROM this spine instead of using random offsets,
    ensuring causal ordering across all CSV files.
    """

    # Arc templates define phases with ordered events.
    # 'month' is relative to data start (0-indexed).
    # 'offset_days' is relative to the phase month start.
    ARC_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
        'ignored_churn': [
            {'phase': 'baseline', 'months': (0, 2), 'events': []},
            {'phase': 'warning', 'month': 3, 'events': [
                {'type': 'signal', 'subtype': 'kpi_decline', 'offset_days': 0},
                {'type': 'signal', 'subtype': 'support_escalation', 'offset_days': 7},
                {'type': 'stakeholder', 'subtype': 'champion_disengagement', 'offset_days': 14},
            ]},
            {'phase': 'crisis', 'month': 4, 'events': [
                {'type': 'decision', 'subtype': 'escalation_to_exec', 'offset_days': 0},
                {'type': 'decision', 'subtype': 'emergency_retention', 'offset_days': 7},
            ]},
            {'phase': 'outcome', 'month': 5, 'events': [
                {'type': 'outcome', 'subtype': 'churn_risk', 'offset_days': 0},
                {'type': 'outcome', 'subtype': 'engagement_decline', 'offset_days': 3},
            ]},
        ],
        'proactive_growth': [
            {'phase': 'baseline', 'months': (0, 2), 'events': []},
            {'phase': 'expansion', 'month': 3, 'events': [
                {'type': 'signal', 'subtype': 'expansion_signal', 'offset_days': 0},
                {'type': 'stakeholder', 'subtype': 'champion_engages', 'offset_days': 7},
            ]},
            {'phase': 'invest', 'month': 4, 'events': [
                {'type': 'decision', 'subtype': 'invest_expansion', 'offset_days': 0},
                {'type': 'decision', 'subtype': 'upsell_proposal', 'offset_days': 10},
            ]},
            {'phase': 'outcome', 'month': 5, 'events': [
                {'type': 'outcome', 'subtype': 'expansion_opportunity', 'offset_days': 0},
                {'type': 'outcome', 'subtype': 'revenue_growth', 'offset_days': 7},
            ]},
        ],
        'crisis_recovery': [
            {'phase': 'baseline', 'months': (0, 1), 'events': []},
            {'phase': 'crisis', 'month': 2, 'events': [
                {'type': 'signal', 'subtype': 'critical_incident', 'offset_days': 0},
                {'type': 'signal', 'subtype': 'stakeholder_escalation', 'offset_days': 3},
            ]},
            {'phase': 'response', 'month': 2, 'events': [
                {'type': 'decision', 'subtype': 'emergency_response', 'offset_days': 10},
                {'type': 'stakeholder', 'subtype': 'exec_sponsor_engaged', 'offset_days': 12},
            ]},
            {'phase': 'recovery', 'month': 3, 'events': [
                {'type': 'decision', 'subtype': 'recovery_plan', 'offset_days': 0},
            ]},
            {'phase': 'outcome', 'month': 4, 'events': [
                {'type': 'outcome', 'subtype': 'partial_recovery', 'offset_days': 0},
                {'type': 'outcome', 'subtype': 'revenue_protected', 'offset_days': 14},
            ]},
        ],
        'expansion_champion': [
            {'phase': 'baseline', 'months': (0, 1), 'events': []},
            {'phase': 'champion_active', 'month': 2, 'events': [
                {'type': 'signal', 'subtype': 'champion_advocacy', 'offset_days': 0},
                {'type': 'stakeholder', 'subtype': 'champion_promotes', 'offset_days': 5},
            ]},
            {'phase': 'expansion', 'month': 3, 'events': [
                {'type': 'signal', 'subtype': 'usage_spike', 'offset_days': 0},
                {'type': 'decision', 'subtype': 'expand_contract', 'offset_days': 14},
            ]},
            {'phase': 'outcome', 'month': 4, 'events': [
                {'type': 'outcome', 'subtype': 'expansion_closed', 'offset_days': 0},
                {'type': 'outcome', 'subtype': 'revenue_growth', 'offset_days': 7},
            ]},
        ],
        'steady_performer': [
            {'phase': 'baseline', 'months': (0, 3), 'events': []},
            {'phase': 'review', 'month': 4, 'events': [
                {'type': 'signal', 'subtype': 'routine_review', 'offset_days': 0},
                {'type': 'stakeholder', 'subtype': 'regular_qbr', 'offset_days': 7},
            ]},
            {'phase': 'outcome', 'month': 5, 'events': [
                {'type': 'decision', 'subtype': 'renewal_confirmed', 'offset_days': 0},
                {'type': 'outcome', 'subtype': 'renewal_secured', 'offset_days': 14},
            ]},
        ],
    }

    # Fallback: maps classification to a default arc
    CLASSIFICATION_TO_ARC = {
        'critical': 'ignored_churn',
        'at_risk': 'crisis_recovery',
        'healthy': 'steady_performer',
    }

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self._plans: Dict[int, List[PlannedEvent]] = {}

    def plan(
        self,
        account_id: int,
        arc_type: str,
        start_date: datetime,
        total_months: int = 6,
        classification: str = 'healthy',
    ) -> List[PlannedEvent]:
        """
        Generate ordered events with concrete dates for one account.

        Args:
            account_id: The account's numeric ID
            arc_type: Story arc key (e.g. 'ignored_churn')
            start_date: First date of the data range
            total_months: Total months of data
            classification: Account classification fallback

        Returns:
            Chronologically sorted list of PlannedEvent
        """
        # Resolve arc template
        template = self.ARC_TEMPLATES.get(arc_type)
        if not template:
            # Fall back to classification-based arc
            fallback = self.CLASSIFICATION_TO_ARC.get(classification, 'steady_performer')
            template = self.ARC_TEMPLATES.get(fallback, self.ARC_TEMPLATES['steady_performer'])

        events: List[PlannedEvent] = []

        for phase_def in template:
            phase_name = phase_def['phase']
            phase_events = phase_def.get('events', [])

            if not phase_events:
                continue

            # Determine the month for this phase
            month = phase_def.get('month')
            if month is None:
                months_range = phase_def.get('months', (0, 0))
                month = months_range[1]  # end of range

            # Cap month to total_months - 1
            month = min(month, max(total_months - 1, 0))
            phase_start = start_date + timedelta(days=month * 30)

            for evt_def in phase_events:
                evt_date = phase_start + timedelta(days=evt_def.get('offset_days', 0))
                events.append(PlannedEvent(
                    account_id=account_id,
                    phase=phase_name,
                    event_type=evt_def['type'],
                    event_subtype=evt_def['subtype'],
                    date=evt_date,
                    offset_days=evt_def.get('offset_days', 0),
                ))

        # Sort by date to enforce causal ordering
        events.sort(key=lambda e: e.date)

        # Cache the plan
        self._plans[account_id] = events
        return events

    def get_events(
        self,
        account_id: int,
        event_type: Optional[str] = None,
    ) -> List[PlannedEvent]:
        """
        Retrieve planned events for an account, optionally filtered by type.

        Args:
            account_id: The account ID
            event_type: Optional filter ('signal', 'decision', 'outcome', 'stakeholder')

        Returns:
            List of PlannedEvent (may be empty if no plan exists)
        """
        events = self._plans.get(account_id, [])
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events

    def get_plan(self, account_id: int) -> List[PlannedEvent]:
        """Get the full plan for an account."""
        return self._plans.get(account_id, [])

    def has_plan(self, account_id: int) -> bool:
        """Check if a plan exists for this account."""
        return account_id in self._plans


# ═══════════════════════════════════════════════════════════════════════
# ManifestCSVGenerator — the core engine (V3: merged V2 extensions)
# ═══════════════════════════════════════════════════════════════════════

class ManifestCSVGenerator:
    """
    Generates all CSV files from a curated manifest JSON.

    The manifest specifies exact account names, ARR, health targets,
    trajectories, stakeholders, and signals — producing deterministic
    data suitable for gold-reference demos.

    V3 additions (merged from V2):
    - Phase windowing (baseline / intervention)
    - Intervention narratives (recovery signals, CSM actions, revenue outcomes)
    - NarrativeTimelinePlanner integration for causal ordering
    - decisions.csv and signal_edges.csv generation
    - _header_use_account_id static method

    V3.1 enrichments:
    - Diverse stakeholders (5-6 per account with seeded selection)
    - Diverse engagement events (8-12 per account, multiple types)
    - Richer products (3-5 per account based on ARR tier)
    - Richer outcomes (3-4 critical, 2-3 at_risk, 1-2 healthy)
    - Phase 2 (intervention) recovery signals, outcomes, decisions
    - Phase 2 KPI improvement boost for critical/at_risk accounts
    """

    # ── Enrichment templates (V3.1) ──

    STAKEHOLDER_TEMPLATES = [
        {"role": "champion", "title": "VP of Engineering", "department": "Engineering",
         "names": ["Sarah Chen", "Michael Torres", "Priya Sharma", "James Wilson"]},
        {"role": "economic_buyer", "title": "VP of Finance", "department": "Finance",
         "names": ["George Martinez", "Amanda Foster", "Robert Kim", "Lisa Wang"]},
        {"role": "technical_lead", "title": "Sr. Systems Engineer", "department": "Engineering",
         "names": ["Kevin Wright", "Nina Kowalski", "David Park", "Elena Rossi"]},
        {"role": "executive_sponsor", "title": "CTO", "department": "Executive",
         "names": ["Thomas Anderson", "Jennifer Brooks", "Raj Patel", "Maria Santos"]},
        {"role": "csm", "title": "Customer Success Manager", "department": "Customer Success",
         "names": ["Alex Thompson", "Rachel Kim", "Chris Davis", "Maya Johnson"]},
        {"role": "procurement", "title": "Director of Procurement", "department": "Operations",
         "names": ["Brian Foster", "Samantha Lee", "Marcus Chen", "Diana Walsh"]},
    ]

    ENGAGEMENT_EVENT_TEMPLATES = [
        {"type": "qbr", "title": "Quarterly Business Review", "cadence": "quarterly"},
        {"type": "executive_briefing", "title": "Executive Sponsor Check-in", "cadence": "monthly"},
        {"type": "technical_review", "title": "Technical Architecture Review", "cadence": "monthly"},
        {"type": "training", "title": "Platform Training Session", "cadence": "quarterly"},
        {"type": "incident_review", "title": "Post-Incident Review", "cadence": "as_needed"},
        {"type": "roadmap_session", "title": "Product Roadmap Preview", "cadence": "quarterly"},
        {"type": "health_check", "title": "System Health Assessment", "cadence": "monthly"},
        {"type": "expansion_discussion", "title": "Capacity Planning & Expansion", "cadence": "quarterly"},
    ]

    DC_PRODUCTS = [
        {"name": "GPU Compute Cluster", "category": "compute", "tier": "enterprise"},
        {"name": "High-Performance Storage", "category": "storage", "tier": "premium"},
        {"name": "Network Fabric", "category": "networking", "tier": "standard"},
        {"name": "Managed Kubernetes", "category": "platform", "tier": "enterprise"},
        {"name": "AI Training Pipeline", "category": "ml_ops", "tier": "premium"},
        {"name": "Edge Computing Nodes", "category": "edge", "tier": "standard"},
        {"name": "Disaster Recovery", "category": "resilience", "tier": "enterprise"},
        {"name": "Monitoring & Observability", "category": "ops", "tier": "standard"},
    ]

    RECOVERY_SIGNAL_TEMPLATES = {
        'critical': [
            {"type": "csm_intervention", "content": "New CSM {csm_name} assigned. First QBR scheduled for next week.", "sentiment": "positive"},
            {"type": "kpi_recovery", "content": "GPU utilization recovering: 48% -> 67% after PB-03 optimization playbook.", "sentiment": "positive"},
            {"type": "executive_engagement", "content": "Executive sponsor engagement: VP Finance joined monthly review cadence.", "sentiment": "positive"},
            {"type": "churn_averted", "content": "Churn risk mitigated. Retention plan approved with 12-month commitment.", "sentiment": "very_positive"},
        ],
        'at_risk': [
            {"type": "deployment_improvement", "content": "Deployment velocity improved 30% after PB-01 acceleration playbook.", "sentiment": "positive"},
            {"type": "champion_reengagement", "content": "Champion {champion_name} re-engaged. Quarterly roadmap session completed.", "sentiment": "positive"},
            {"type": "health_improvement", "content": "Account health trending upward: +12 points over 4 weeks.", "sentiment": "positive"},
        ],
        'healthy': [
            {"type": "expansion_signal", "content": "Account expanding GPU cluster capacity by 40%. New PO in procurement.", "sentiment": "very_positive"},
            {"type": "advocacy", "content": "Customer agreed to co-present at annual user conference.", "sentiment": "positive"},
        ],
    }

    RECOVERY_OUTCOME_TEMPLATES = {
        'critical': [
            ("churn_averted", "Churn Risk Averted", "Retention plan executed successfully. Account committed to 12-month renewal.", "resolved"),
            ("revenue_protected", "Revenue Protected", "Intervention protected ARR through executive engagement and service improvements.", "resolved"),
            ("engagement_recovery", "Engagement Recovery", "Stakeholder engagement restored to healthy levels after CSM intervention.", "resolved"),
        ],
        'at_risk': [
            ("engagement_recovery", "Engagement Recovery", "Regular QBR cadence re-established with key stakeholders.", "resolved"),
            ("revenue_protected", "Revenue Protected", "Renewal secured after addressing platform concerns.", "resolved"),
            ("renewal_secured", "Renewal Confirmed", "Account renewed with expanded scope after successful intervention.", "resolved"),
        ],
        'healthy': [
            ("expansion_approved", "Expansion Approved", "Account approved additional capacity and new product modules.", "in_progress"),
            ("revenue_growth", "Revenue Growth", "Upsell opportunity converted. New workload onboarded.", "resolved"),
        ],
    }

    RECOVERY_DECISION_TEMPLATES = {
        'critical': [
            ("CSM resource allocation approved", "executive_sponsor", "Assign dedicated senior CSM", "Resource reallocation approved", "high"),
            ("Executive QBR cadence established", "executive_sponsor", "Weekly executive check-ins for 90 days", "Cadence approved", "high"),
            ("GPU optimization playbook initiated", "technical_lead", "Deploy PB-03 optimization playbook", "Playbook execution started", "medium"),
        ],
        'at_risk': [
            ("Renewal incentive package approved", "economic_buyer", "Offer multi-year discount", "Incentive approved", "medium"),
            ("Technical remediation plan", "technical_lead", "Address top 3 platform concerns", "Remediation in progress", "medium"),
        ],
        'healthy': [
            ("Expansion proposal submitted", "champion", "Propose additional capacity", "Expansion under review", "low"),
        ],
    }

    PHASE1_OUTCOME_TEMPLATES = {
        'critical': [
            ('revenue_at_risk', 'Churn risk identified', 'Account showing signs of churn. ARR at risk.', -0.5, 'open'),
            ('engagement_decline', 'Engagement declining', 'Stakeholder engagement dropped significantly.', -0.1, 'in_progress'),
            ('renewal_uncertainty', 'Renewal at risk', 'Renewal timeline uncertain due to unresolved issues.', -0.3, 'open'),
            ('capacity_constraint', 'Capacity issues', 'Infrastructure capacity constraints impacting service quality.', -0.15, 'in_progress'),
        ],
        'at_risk': [
            ('renewal_uncertainty', 'Renewal discussion stalled', 'Renewal discussion delayed pending resolution of concerns.', -0.2, 'in_progress'),
            ('engagement_decline', 'Engagement cooling', 'Key stakeholder engagement frequency declining.', -0.1, 'open'),
            ('partner_friction', 'Integration friction', 'P4 partner integration issues causing workflow disruption.', -0.08, 'in_progress'),
        ],
        'healthy': [
            ('expansion_opportunity', 'Expansion potential identified', 'Account showing strong expansion signals.', 0.15, 'open'),
            ('renewal_secured', 'Renewal on track', 'Renewal discussion progressing positively.', 0.05, 'in_progress'),
        ],
    }

    def __init__(
        self,
        manifest_path: str,
        customer_id: int = 0,
        seed: int = 42,
        phase: Optional[str] = None,
    ):
        """
        Args:
            manifest_path: Path to the manifest JSON file
            customer_id: Assigned customer_id (overrides manifest if >0)
            seed: Random seed for reproducible noise
            phase: 'baseline', 'intervention', or None (full range)
        """
        with open(manifest_path, 'r') as f:
            self.manifest = json.load(f)

        self.customer_info = self.manifest['customer']
        self.time_range = self.manifest['time_range']
        self.kpi_codes = self.manifest['kpis']['codes']
        self.context_graph_cfg = self.manifest.get('context_graph', {})
        self.accounts = self.manifest['accounts']

        self.customer_id = customer_id
        self.seed = seed
        self.phase = phase
        self.vertical = self.customer_info.get('vertical', 'dc2_s')
        random.seed(seed)

        # Set vertical in catalog loader so KPI ranges match the vertical
        if _catalog_available:
            from catalog_loader import set_vertical
            set_vertical(self.vertical)
            logger.info("  Catalog vertical set to '%s'", self.vertical)

        # Parse time range
        raw_dp = int(self.time_range.get('data_points_per_kpi', 26))
        self.start_date = datetime.strptime(self.time_range['start'], '%Y-%m-%d')
        self.end_date = datetime.strptime(self.time_range['end'], '%Y-%m-%d')
        self.frequency = self.time_range.get('frequency', 'weekly')

        # Phase windowing (from V2)
        if phase == 'baseline':
            self.data_points = int(raw_dp * 2 / 3)
            logger.info("  Phase=baseline: generating %s data points", self.data_points)
        elif phase == 'intervention':
            baseline_points = int(raw_dp * 2 / 3)
            self.data_points = raw_dp - baseline_points
            if self.frequency == 'weekly':
                self.start_date += timedelta(weeks=baseline_points)
            elif self.frequency == 'daily':
                self.start_date += timedelta(days=baseline_points)
            else:
                self.start_date += timedelta(days=baseline_points * 30)
            logger.info(
                "  Phase=intervention: generating %s data points from %s",
                self.data_points, self.start_date.strftime('%Y-%m-%d'),
            )
        else:
            self.data_points = raw_dp

        # Build measurement dates
        self.dates = self._build_dates()

        # Load KPI catalog metadata (now vertical-aware via set_vertical above)
        self.kpi_catalog = {}
        if _catalog_available:
            full_catalog = get_kpis()
            for code in self.kpi_codes:
                if code in full_catalog:
                    self.kpi_catalog[code] = full_catalog[code]

        # Account ID base: customer_id * 1000 + 1
        self.account_id_base = (self.customer_id or 1) * 1000 + 1

        # Build narrative timeline plans for all accounts
        self.planner = NarrativeTimelinePlanner(seed=seed)
        self._build_narrative_plans()

    def _build_narrative_plans(self):
        """Create narrative timeline plans for all accounts."""
        total_months = max(1, int((self.end_date - self.start_date).days / 30))
        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            arc_type = acct.get('story_arc', '')
            classification = acct.get('classification', 'healthy')
            self.planner.plan(
                account_id=aid,
                arc_type=arc_type,
                start_date=self.start_date,
                total_months=total_months,
                classification=classification,
            )

    def _build_dates(self) -> List[str]:
        """Build list of measurement date strings based on frequency."""
        dates = []
        if self.frequency == 'weekly':
            delta = timedelta(weeks=1)
        elif self.frequency == 'daily':
            delta = timedelta(days=1)
        else:  # monthly
            delta = timedelta(days=30)

        current = self.start_date
        for _ in range(self.data_points):
            dates.append(current.strftime('%Y-%m-%d'))
            current += delta
        return dates

    def _account_id(self, idx: int) -> int:
        """Deterministic account_id from index."""
        return self.account_id_base + idx

    @staticmethod
    def _header_use_account_id(csv_content: str) -> str:
        """Replace source_account_id with account_id in CSV header."""
        if not csv_content:
            return csv_content
        first_nl = csv_content.find('\n')
        if first_nl == -1:
            header, rest = csv_content, ''
        else:
            header, rest = csv_content[:first_nl], csv_content[first_nl:]
        header = header.replace('source_account_id', 'account_id')
        return header + rest

    # ── KPI value generation with trajectories ──

    @staticmethod
    def _health_to_kpi_value(
        target_health: float,
        target_val: float,
        ranges: dict,
        higher_is_better: bool,
    ) -> float:
        """
        Reverse-engineer a KPI value that will score approximately target_health
        through the scoring engine.
        """
        healthy = ranges.get('healthy', {})
        risk = ranges.get('risk', {})
        critical = ranges.get('critical', {})

        if not healthy or not risk:
            factor = 0.4 + 0.6 * (target_health / 100.0) ** 0.7
            if not higher_is_better:
                factor = 1.0 / factor
            return target_val * factor

        if higher_is_better:
            h_min = healthy.get('min', target_val * 0.8)
            h_max = healthy.get('max', target_val * 1.2)
            r_min = risk.get('min', target_val * 0.5)
            r_max = risk.get('max', h_min)
            c_min = critical.get('min', 0)
            c_max = critical.get('max', r_min)

            if target_health >= 70:
                t = (target_health - 70) / 30.0
                return h_min + t * (h_max - h_min)
            elif target_health >= 50:
                t = (target_health - 50) / 20.0
                return r_min + t * (r_max - r_min)
            else:
                t = target_health / 50.0
                return c_min + t * (c_max - c_min)
        else:
            h_min = healthy.get('min', target_val * 0.5)
            h_max = healthy.get('max', target_val)
            r_min = risk.get('min', h_max)
            r_max = risk.get('max', target_val * 1.5)
            c_min = critical.get('min', r_max)
            c_max = critical.get('max', target_val * 3.0)

            if target_health >= 70:
                t = (target_health - 70) / 30.0
                return h_max - t * (h_max - h_min)
            elif target_health >= 50:
                t = (target_health - 50) / 20.0
                return r_max - t * (r_max - r_min)
            else:
                t = target_health / 50.0
                return c_max - t * (c_max - c_min)

    def _generate_kpi_series(
        self,
        target_health: float,
        trajectory: str,
        decline_start_month: Optional[int],
        kpi_code: str,
        classification: str = 'healthy',
    ) -> List[float]:
        """
        Generate a time-series of KPI values for one account+KPI.

        Uses the account's target_health (0-100) to set the baseline,
        then applies trajectory with realistic noise.

        V3: intervention phase flips declining trajectories to improving.
        V3.1: adds recovery_boost for critical/at_risk accounts in intervention phase.
        """
        # V2 phase logic: intervention flips declining to improving
        if self.phase == 'intervention' and trajectory in ('declining', 'slow_decline'):
            target_health = min(target_health + 15, 95)
            trajectory = 'improving'

        # V3.1: Additional recovery boost for intervention phase
        recovery_boost_pct = 0.0
        if self.phase == 'intervention':
            rng = random.Random(self.seed + hash(kpi_code))
            if classification == 'critical':
                recovery_boost_pct = rng.uniform(0.05, 0.15)
            elif classification == 'at_risk':
                recovery_boost_pct = rng.uniform(0.03, 0.08)

        n = len(self.dates)

        meta = self.kpi_catalog.get(kpi_code, {})
        higher_is_better = meta.get('higher_is_better', True)
        target_val = meta.get('target', {})
        if isinstance(target_val, dict):
            target_val = target_val.get('value', 85.0)
        elif target_val is None:
            target_val = 85.0

        ranges = meta.get('ranges', {})
        base = self._health_to_kpi_value(
            target_health, target_val, ranges, higher_is_better
        )

        values = []
        for i in range(n):
            t = i / max(n - 1, 1)

            if trajectory == 'declining':
                start_month = decline_start_month or 3
                start_idx = int(start_month * (n / 6))
                if i >= start_idx:
                    decay = (i - start_idx) / max(n - start_idx, 1)
                    if higher_is_better:
                        modifier = 1.0 - 0.35 * decay
                    else:
                        modifier = 1.0 + 0.5 * decay
                else:
                    modifier = 1.0
            elif trajectory == 'slow_decline':
                modifier = 1.0 - 0.15 * t if higher_is_better else 1.0 + 0.15 * t
            elif trajectory == 'improving':
                modifier = 1.0 + 0.15 * t if higher_is_better else 1.0 - 0.15 * t
            elif trajectory == 'recovering':
                if t < 0.4:
                    m = 1.0 - 0.25 * (t / 0.4)
                else:
                    m = 0.75 + 0.30 * ((t - 0.4) / 0.6)
                modifier = m if higher_is_better else (2.0 - m)
            elif trajectory == 'ramping_up':
                modifier = 0.7 + 0.35 * t if higher_is_better else 1.3 - 0.35 * t
            elif trajectory == 'stable_high':
                modifier = 1.0 + 0.02 * random.gauss(0, 1)
            elif trajectory == 'flat_high_risk':
                modifier = 1.0
            else:  # stable
                modifier = 1.0 + 0.01 * random.gauss(0, 1)

            noise = 1.0 + random.gauss(0, 0.03)
            val = base * modifier * noise

            # V3.1: Apply recovery boost for intervention phase (progressive)
            if recovery_boost_pct > 0:
                # Progressive boost: increases through the intervention window
                progress = (i + 1) / max(n, 1)
                boost_range = target_val * recovery_boost_pct * progress
                if higher_is_better:
                    val += boost_range
                else:
                    val -= boost_range

            if higher_is_better:
                val = max(0, min(target_val * 1.2, val))
            else:
                val = max(target_val * 0.5, val)

            values.append(round(val, 2))

        return values

    def _classify_status(self, kpi_code: str, value: float) -> str:
        """Classify KPI value as healthy/risk/critical."""
        meta = self.kpi_catalog.get(kpi_code, {})
        ranges = meta.get('ranges', {})
        higher_is_better = meta.get('higher_is_better', True)

        if ranges:
            healthy = ranges.get('healthy', {})
            risk = ranges.get('risk', {})

            if higher_is_better:
                if healthy and value >= healthy.get('min', 0):
                    return 'healthy'
                elif risk and value >= risk.get('min', 0):
                    return 'risk'
                return 'critical'
            else:
                if healthy and value <= healthy.get('max', float('inf')):
                    return 'healthy'
                elif risk and value <= risk.get('max', float('inf')):
                    return 'risk'
                return 'critical'

        target_val = meta.get('target', {})
        if isinstance(target_val, dict):
            target_val = target_val.get('value', 85.0)
        elif target_val is None:
            target_val = 85.0

        if higher_is_better:
            score = min(100, (value / target_val) * 100) if target_val else 50
        else:
            score = min(100, (target_val / value) * 100) if value else 50

        if score >= 70:
            return 'healthy'
        elif score >= 50:
            return 'risk'
        return 'critical'

    # ═══════════════════════════════════════════════════════════════════
    # CSV Generators
    # ═══════════════════════════════════════════════════════════════════

    def generate_all(self, output_dir: str) -> Dict[str, str]:
        """Generate all CSV files to output_dir. Returns {filename: path}."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files = {}
        generators = {
            'accounts.csv': self.generate_accounts_csv,
            'kpi_measurements.csv': self.generate_kpi_measurements_csv,
            'enhanced_qualitative_signals.csv': self.generate_signals_csv,
            'products.csv': self.generate_products_csv,
            'stakeholders.csv': self.generate_stakeholders_csv,
            'engagement_events.csv': self.generate_engagement_events_csv,
            'account_business_profiles.csv': self.generate_profiles_csv,
            'outcomes.csv': self.generate_outcomes_csv,
            'decisions.csv': self.generate_decisions_csv,
            'signal_edges.csv': self.generate_signal_edges_csv,
        }

        for filename, gen_fn in generators.items():
            content = gen_fn()
            fpath = output_path / filename
            fpath.write_text(content)
            files[filename] = str(fpath)
            lines = content.count('\n')
            logger.info(f"  {filename}: {lines} lines")

        return files

    def generate_accounts_csv(self) -> str:
        """Generate accounts.csv from manifest accounts."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'customer_id', 'account_name', 'industry', 'region',
            'vertical', 'tier', 'arr', 'revenue', 'contract_start', 'contract_end',
            'renewal_date', 'csm_name', 'csm_email', 'account_status', 'uuid',
            'csm_manager', 'executive_sponsor',
            'primary_champion_name', 'primary_champion_title',
            'primary_champion_email', 'primary_champion_engagement_score',
        ])

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            arr = acct['arr']

            if arr >= 5_000_000:
                tier = 'Enterprise'
            elif arr >= 1_000_000:
                tier = 'Mid-Market'
            else:
                tier = 'SMB'

            cls = acct.get('classification', 'healthy')
            status = 'at_risk' if cls in ('critical', 'at_risk') else 'active'

            champion = None
            exec_sponsor = None
            for sh in acct.get('stakeholders', []):
                role = sh.get('role', '')
                if role in ('champion', 'economic_buyer') and not champion:
                    champion = sh
                if role == 'executive_sponsor' and not exec_sponsor:
                    exec_sponsor = sh

            champion = champion or (acct.get('stakeholders', [{}])[0] if acct.get('stakeholders') else {})
            exec_sponsor_name = exec_sponsor['name'] if exec_sponsor else ''

            renewal = acct.get('renewal_date', '2026-09-01')
            renewal_dt = datetime.strptime(renewal, '%Y-%m-%d')
            contract_start = (renewal_dt - timedelta(days=365)).strftime('%Y-%m-%d')

            csm_names = ['Sarah Rivera', 'Alex Chen', 'Jordan Blake', 'Morgan Lee', 'Taylor Kim']
            csm = csm_names[idx % len(csm_names)]
            csm_email = csm.lower().replace(' ', '.') + '@novastar-dc.com'

            w.writerow([
                aid,
                self.customer_id,
                acct['name'],
                random.choice(['Technology', 'Financial Services', 'Healthcare', 'Manufacturing', 'Energy']),
                random.choice(['North America', 'EMEA', 'APAC']),
                self.customer_info.get('vertical', 'dc2_s'),
                tier,
                arr,
                arr,
                contract_start,
                renewal,
                renewal,
                csm,
                csm_email,
                status,
                f'dc_acct_{uuid_mod.uuid4().hex[:12]}',
                'Sam Rivera',
                exec_sponsor_name,
                champion.get('name', '') if isinstance(champion, dict) else '',
                champion.get('title', '') if isinstance(champion, dict) else '',
                (champion.get('name', '').lower().replace(' ', '.') + '@' + acct['name'].lower().replace(' ', '') + '.com') if isinstance(champion, dict) and champion.get('name') else '',
                random.randint(40, 95) if isinstance(champion, dict) else 70,
            ])

        return out.getvalue()

    def generate_kpi_measurements_csv(self) -> str:
        """Generate kpi_measurements.csv — KPIs x accounts x time points."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'kpi_code', 'kpi_name', 'pillar',
            'measured_at', 'value', 'target', 'weight', 'unit', 'status',
        ])

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            target_health = acct['target_health']
            trajectory = acct.get('kpi_trajectory', 'stable')
            decline_start = acct.get('decline_start_month')
            classification = acct.get('classification', 'healthy')

            for kpi_code in self.kpi_codes:
                meta = self.kpi_catalog.get(kpi_code, {})
                kpi_name = meta.get('name', kpi_code)
                pillar = meta.get('pillar', kpi_code.split('-')[0])
                weight = meta.get('weight_l1', 0.25)
                unit = meta.get('unit', '%')
                target_val = meta.get('target', {})
                if isinstance(target_val, dict):
                    target_val = target_val.get('value', 85.0)
                elif target_val is None:
                    target_val = 85.0

                series = self._generate_kpi_series(
                    target_health, trajectory, decline_start, kpi_code,
                    classification=classification,
                )

                for i, date_str in enumerate(self.dates):
                    val = series[i] if i < len(series) else series[-1]
                    status = self._classify_status(kpi_code, val)

                    w.writerow([
                        aid, kpi_code, kpi_name, pillar,
                        date_str, val, target_val, weight, unit, status,
                    ])

        return out.getvalue()

    def generate_signals_csv(self) -> str:
        """Generate enhanced_qualitative_signals.csv with narrative timeline dates."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'signal_id', 'source_account_id', 'signal_date', 'signal_type',
            'content', 'sentiment', 'sentiment_score',
            'arc_id', 'story_phase', 'linked_node_id', 'signal_ref',
        ])

        phase_prefix = f'{self.phase}_' if self.phase else ''
        counter = 0
        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            arc = acct.get('story_arc', '')

            # Get planned signal events for narrative-aligned dates
            planned_signals = self.planner.get_events(aid, 'signal')

            # Manifest-defined signals (curated)
            for sig in acct.get('key_signals', []):
                counter += 1
                sentiment = sig.get('sentiment', 'neutral')
                score_map = {
                    'very_positive': 0.9, 'positive': 0.7,
                    'neutral': 0.1,
                    'negative': -0.6, 'very_negative': -0.9,
                }
                sig_ref = f'{phase_prefix}sig_{aid}_{counter}'
                w.writerow([
                    sig_ref,
                    aid,
                    sig.get('date', '2026-01-01'),
                    sig.get('type', 'observation'),
                    sig.get('content', ''),
                    sentiment.replace('very_', ''),
                    score_map.get(sentiment, 0.0),
                    arc,
                    '',
                    '',
                    sig_ref,
                ])

            # Narrative-planned signals (from NarrativeTimelinePlanner)
            for pe in planned_signals:
                counter += 1
                sig_ref = f'{phase_prefix}narrative_sig_{aid}_{counter}'
                sentiment = 'negative' if pe.event_subtype in (
                    'kpi_decline', 'support_escalation', 'critical_incident',
                    'stakeholder_escalation',
                ) else 'positive'
                score = -0.6 if sentiment == 'negative' else 0.7
                content_map = {
                    'kpi_decline': 'KPI metrics declining below threshold',
                    'support_escalation': 'Support ticket escalated to management',
                    'expansion_signal': 'Account showing expansion readiness',
                    'critical_incident': 'Critical service incident reported',
                    'stakeholder_escalation': 'Stakeholder escalated concerns',
                    'champion_advocacy': 'Champion actively advocating for platform',
                    'usage_spike': 'Significant usage increase detected',
                    'routine_review': 'Routine quarterly review completed',
                }
                w.writerow([
                    sig_ref,
                    aid,
                    pe.date_str,
                    pe.event_subtype,
                    content_map.get(pe.event_subtype, f'Signal: {pe.event_subtype}'),
                    sentiment,
                    round(score + random.gauss(0, 0.1), 2),
                    arc,
                    pe.phase,
                    '',
                    sig_ref,
                ])

            # Auto-generated filler signals (2 per month for 6 months)
            cls = acct.get('classification', 'healthy')
            for month in range(6):
                for _ in range(2):
                    counter += 1
                    date = self.start_date + timedelta(days=30 * month + random.randint(0, 29))

                    if cls == 'critical':
                        templates = [
                            'Escalation review meeting conducted',
                            'Support ticket volume above normal',
                            'Performance metrics under review',
                            'Stakeholder alignment meeting scheduled',
                        ]
                        sentiment = random.choice(['negative', 'neutral'])
                    elif cls == 'at_risk':
                        templates = [
                            'Quarterly check-in completed',
                            'Usage patterns reviewed with team',
                            'Renewal discussion in progress',
                            'Technical review session held',
                        ]
                        sentiment = random.choice(['neutral', 'negative', 'neutral'])
                    else:
                        templates = [
                            'Regular QBR completed successfully',
                            'Product adoption metrics trending well',
                            'Champion engagement remains strong',
                            'Expansion discussion in early stages',
                        ]
                        sentiment = random.choice(['positive', 'neutral', 'positive'])

                    score = {'positive': 0.6, 'neutral': 0.1, 'negative': -0.5}[sentiment]
                    sig_ref = f'{phase_prefix}sig_{aid}_{counter}'
                    w.writerow([
                        sig_ref,
                        aid,
                        date.strftime('%Y-%m-%d'),
                        random.choice(['meeting', 'health_check', 'observation', 'customer_feedback']),
                        random.choice(templates),
                        sentiment,
                        round(score + random.gauss(0, 0.1), 2),
                        arc,
                        '',
                        '',
                        sig_ref,
                    ])

            # Intervention-phase recovery signals (from V2 — manifest-defined)
            intervention = acct.get('intervention', {})
            if self.phase == 'intervention' and intervention.get('recovery_signals'):
                for rs in intervention['recovery_signals']:
                    counter += 1
                    sig_ref = f'{phase_prefix}recovery_{aid}_{counter}'
                    w.writerow([
                        sig_ref,
                        aid,
                        rs.get('date', '2026-03-01'),
                        rs.get('type', 'recovery_signal'),
                        rs.get('content', ''),
                        rs.get('sentiment', 'positive'),
                        0.7 if rs.get('sentiment') == 'positive' else 0.1,
                        arc,
                        'recovery',
                        '',
                        sig_ref,
                    ])

            if self.phase == 'intervention' and intervention.get('csm_actions'):
                for ca in intervention['csm_actions']:
                    counter += 1
                    sig_ref = f'{phase_prefix}csm_action_{aid}_{counter}'
                    w.writerow([
                        sig_ref,
                        aid,
                        ca.get('date', '2026-02-01'),
                        'csm_action',
                        f'{ca["action"]} -> {ca["outcome"]}',
                        'positive',
                        0.8,
                        arc,
                        'intervention',
                        '',
                        sig_ref,
                    ])

            # V3.1: Auto-generated recovery signals for intervention phase
            if self.phase == 'intervention':
                recovery_templates = self.RECOVERY_SIGNAL_TEMPLATES.get(cls, [])
                acct_rng = random.Random(self.seed + aid + 7000)
                # Determine how many recovery signals
                if cls == 'critical':
                    n_recovery = acct_rng.randint(3, 4)
                elif cls == 'at_risk':
                    n_recovery = acct_rng.randint(2, 3)
                else:
                    n_recovery = acct_rng.randint(1, 2)
                n_recovery = min(n_recovery, len(recovery_templates))

                # Pick a CSM name and champion name for template interpolation
                stakeholders = acct.get('stakeholders', [])
                csm_name = 'Sarah Rivera'
                champion_name = 'the champion'
                for sh in stakeholders:
                    if sh.get('role') == 'csm':
                        csm_name = sh['name']
                    if sh.get('role') == 'champion':
                        champion_name = sh['name']

                selected_recovery = acct_rng.sample(recovery_templates, n_recovery)
                total_days = max(1, (self.end_date - self.start_date).days)
                for ri, rtpl in enumerate(selected_recovery):
                    counter += 1
                    # Spread recovery signals across the intervention window
                    day_offset = int(total_days * (ri + 1) / (n_recovery + 1))
                    sig_date = self.start_date + timedelta(days=day_offset)
                    content = rtpl['content'].format(
                        csm_name=csm_name,
                        champion_name=champion_name,
                    )
                    sentiment = rtpl.get('sentiment', 'positive')
                    score_map = {
                        'very_positive': 0.9, 'positive': 0.7,
                        'neutral': 0.1, 'negative': -0.6,
                    }
                    sig_ref = f'{phase_prefix}auto_recovery_{aid}_{counter}'
                    w.writerow([
                        sig_ref,
                        aid,
                        sig_date.strftime('%Y-%m-%d'),
                        rtpl.get('type', 'recovery_signal'),
                        content,
                        sentiment.replace('very_', ''),
                        round(score_map.get(sentiment, 0.7) + acct_rng.gauss(0, 0.05), 2),
                        arc,
                        'recovery',
                        '',
                        sig_ref,
                    ])

        return out.getvalue()

    def generate_products_csv(self) -> str:
        """Generate products.csv — 3-5 products per account based on ARR tier."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'product_name', 'product_category',
            'quantity', 'unit_price', 'deployment_date', 'status',
        ])

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            arr = acct.get('arr', 1_000_000)
            acct_rng = random.Random(self.seed + idx + 3000)

            # Higher ARR = more products (3-5)
            if arr >= 5_000_000:
                n_products = acct_rng.randint(4, 5)
            elif arr >= 2_000_000:
                n_products = acct_rng.randint(3, 5)
            else:
                n_products = acct_rng.randint(3, 4)

            n_products = min(n_products, len(self.DC_PRODUCTS))
            selected = acct_rng.sample(self.DC_PRODUCTS, n_products)

            for prod in selected:
                deploy_date = self.start_date - timedelta(days=acct_rng.randint(30, 365))
                # Scale quantity and price by ARR tier
                base_qty = acct_rng.randint(5, 50)
                qty_multiplier = max(1, int(arr / 2_000_000))
                quantity = base_qty * qty_multiplier
                unit_price = round(acct_rng.uniform(5000, 100000), 2)

                w.writerow([
                    aid,
                    prod['name'],
                    prod['category'],
                    quantity,
                    unit_price,
                    deploy_date.strftime('%Y-%m-%d'),
                    'active',
                ])

        return out.getvalue()

    def generate_stakeholders_csv(self) -> str:
        """Generate stakeholders.csv with 5-6 diverse stakeholders per account."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'stakeholder_name', 'role', 'title',
            'department', 'email', 'influence_score', 'sentiment',
            'engagement_frequency', 'last_contact_date',
        ])

        freq_by_role = {
            'champion': 'weekly',
            'economic_buyer': 'monthly',
            'technical_lead': 'weekly',
            'executive_sponsor': 'monthly',
            'csm': 'daily',
            'procurement': 'quarterly',
        }
        influence_by_role = {
            'champion': 8,
            'economic_buyer': 9,
            'technical_lead': 7,
            'executive_sponsor': 10,
            'csm': 6,
            'procurement': 5,
        }

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            domain = acct['name'].lower().replace(' ', '') + '.com'
            cls = acct.get('classification', 'healthy')
            acct_rng = random.Random(self.seed + aid + 5000)

            # Get planned stakeholder events to align dates
            planned_stakeholder_events = self.planner.get_events(aid, 'stakeholder')

            # Start with manifest-defined stakeholders
            manifest_stakeholders = acct.get('stakeholders', [])
            existing_roles = {sh.get('role', 'contact') for sh in manifest_stakeholders}
            all_stakeholders = list(manifest_stakeholders)

            # Fill from templates to reach 5-6 total
            target_count = acct_rng.randint(5, 6)
            for tpl in self.STAKEHOLDER_TEMPLATES:
                if len(all_stakeholders) >= target_count:
                    break
                if tpl['role'] in existing_roles:
                    continue
                # Pick a deterministic name from the pool
                name = tpl['names'][aid % len(tpl['names'])]
                all_stakeholders.append({
                    'name': name,
                    'role': tpl['role'],
                    'title': tpl['title'],
                    'department': tpl['department'],
                    'engagement_frequency': freq_by_role.get(tpl['role'], 'monthly'),
                    'influence_score': influence_by_role.get(tpl['role'], 5),
                    'sentiment': 'positive' if cls == 'healthy' else ('neutral' if cls == 'at_risk' else 'negative'),
                })
                existing_roles.add(tpl['role'])

            for si, sh in enumerate(all_stakeholders):
                email = sh['name'].lower().replace(' ', '.') + '@' + domain
                freq = sh.get('engagement_frequency', 'monthly')

                # Use narrative planner date if available for this stakeholder
                if si < len(planned_stakeholder_events):
                    last_contact = planned_stakeholder_events[si].date_str
                elif freq in ('none', 'none_recent'):
                    last_contact = (self.end_date - timedelta(days=acct_rng.randint(90, 180))).strftime('%Y-%m-%d')
                elif freq == 'daily':
                    last_contact = (self.end_date - timedelta(days=acct_rng.randint(0, 3))).strftime('%Y-%m-%d')
                elif freq == 'weekly':
                    last_contact = (self.end_date - timedelta(days=acct_rng.randint(0, 10))).strftime('%Y-%m-%d')
                elif freq == 'biweekly':
                    last_contact = (self.end_date - timedelta(days=acct_rng.randint(0, 18))).strftime('%Y-%m-%d')
                elif freq == 'quarterly':
                    last_contact = (self.end_date - timedelta(days=acct_rng.randint(30, 95))).strftime('%Y-%m-%d')
                else:  # monthly
                    last_contact = (self.end_date - timedelta(days=acct_rng.randint(0, 35))).strftime('%Y-%m-%d')

                w.writerow([
                    aid,
                    sh['name'],
                    sh.get('role', 'contact'),
                    sh.get('title', ''),
                    sh.get('department', ''),
                    email,
                    sh.get('influence_score', 5),
                    sh.get('sentiment', 'neutral'),
                    freq,
                    last_contact,
                ])

        return out.getvalue()

    def generate_engagement_events_csv(self) -> str:
        """Generate engagement_events.csv — 8-12 diverse events per account."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'event_date', 'event_type', 'title',
            'participants', 'outcome', 'sentiment', 'notes',
        ])

        outcome_by_cls = {
            'critical': ['action_items_assigned', 'escalated', 'follow_up_needed', 'partially_resolved', 'risk_identified'],
            'at_risk': ['follow_up_needed', 'positive_engagement', 'action_items_assigned', 'improvement_noted'],
            'healthy': ['positive_engagement', 'expansion_discussed', 'renewal_confirmed', 'best_practices_shared'],
        }
        sentiment_by_cls = {
            'critical': ['negative', 'neutral', 'negative', 'neutral'],
            'at_risk': ['neutral', 'negative', 'neutral', 'positive'],
            'healthy': ['positive', 'neutral', 'positive', 'positive'],
        }

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            cls = acct.get('classification', 'healthy')
            acct_rng = random.Random(self.seed + aid + 6000)

            # Build participant pool from manifest stakeholders + generated
            stakeholders = acct.get('stakeholders', [])
            participant_pool = [s['name'] for s in stakeholders[:4]]
            if len(participant_pool) < 2:
                participant_pool = ['Sarah Chen', 'Alex Thompson']

            # Determine event count: 8-12 per account
            ev_cfg = self.context_graph_cfg.get('events_per_account')
            if isinstance(ev_cfg, (list, tuple)) and len(ev_cfg) >= 2:
                lo, hi = int(ev_cfg[0]), int(ev_cfg[1])
                n_events = acct_rng.randint(max(lo, 8), max(hi, 12))
            else:
                n_events = acct_rng.randint(8, 12)

            total_days = max(1, (self.end_date - self.start_date).days)

            # Pick diverse event types (cycle through templates to ensure variety)
            event_types_for_account = []
            shuffled_templates = list(self.ENGAGEMENT_EVENT_TEMPLATES)
            acct_rng.shuffle(shuffled_templates)
            while len(event_types_for_account) < n_events:
                event_types_for_account.extend(shuffled_templates)
            event_types_for_account = event_types_for_account[:n_events]

            for i, evt_tpl in enumerate(event_types_for_account):
                # Spread events evenly across the time range
                event_date = self.start_date + timedelta(
                    days=int(total_days * i / max(n_events - 1, 1))
                )

                etype = evt_tpl['type']
                title = f"{evt_tpl['title']} — {acct['name']}"
                sentiment = acct_rng.choice(sentiment_by_cls.get(cls, ['neutral']))
                outcome = acct_rng.choice(outcome_by_cls.get(cls, ['follow_up_needed']))

                n_participants = acct_rng.randint(2, min(4, len(participant_pool)))
                participants = ', '.join(acct_rng.sample(participant_pool, n_participants))

                # Richer notes based on event type
                notes_map = {
                    'qbr': f"Quarterly review covered health metrics, roadmap alignment, and renewal timeline for {acct['name']}.",
                    'executive_briefing': f"Executive sponsor briefed on account status and strategic priorities.",
                    'technical_review': f"Technical deep-dive on infrastructure performance and optimization opportunities.",
                    'training': f"Hands-on training session on new platform features and best practices.",
                    'incident_review': f"Post-incident review: root cause analysis and prevention measures discussed.",
                    'roadmap_session': f"Product roadmap preview with feedback collection on upcoming features.",
                    'health_check': f"System health assessment completed. Key metrics reviewed with recommendations.",
                    'expansion_discussion': f"Capacity planning discussion. Growth projections and expansion options reviewed.",
                }
                notes = notes_map.get(etype, f"Engagement with {acct['name']}: {outcome.replace('_', ' ')}")

                w.writerow([
                    aid,
                    event_date.strftime('%Y-%m-%d'),
                    etype,
                    title,
                    participants,
                    outcome,
                    sentiment,
                    notes,
                ])

            # V3.1: Additional recovery engagement events for intervention phase
            if self.phase == 'intervention' and cls in ('critical', 'at_risk'):
                recovery_events = [
                    ('executive_briefing', 'Emergency Executive Review', 'positive', 'risk_mitigation_discussed'),
                    ('health_check', 'Intervention Health Assessment', 'positive', 'improvement_noted'),
                    ('technical_review', 'Remediation Progress Review', 'positive', 'action_items_assigned'),
                ]
                for ri, (re_type, re_title, re_sent, re_outcome) in enumerate(recovery_events[:2 if cls == 'at_risk' else 3]):
                    day_offset = int(total_days * (ri + 1) / 4)
                    event_date = self.start_date + timedelta(days=day_offset)
                    n_participants = acct_rng.randint(2, min(3, len(participant_pool)))
                    participants = ', '.join(acct_rng.sample(participant_pool, n_participants))
                    w.writerow([
                        aid,
                        event_date.strftime('%Y-%m-%d'),
                        re_type,
                        f"{re_title} — {acct['name']}",
                        participants,
                        re_outcome,
                        re_sent,
                        f"Recovery intervention: {re_title.lower()} for {acct['name']}.",
                    ])

        return out.getvalue()

    def generate_profiles_csv(self) -> str:
        """Generate account_business_profiles.csv — firmographic data per account."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'company_name', 'industry', 'employee_count',
            'annual_revenue', 'founded_year', 'headquarters', 'website',
            'description',
        ])

        industries = ['Technology', 'Financial Services', 'Healthcare',
                       'Cloud Infrastructure', 'AI/ML', 'Telecommunications']
        cities = ['San Francisco, CA', 'New York, NY', 'Austin, TX',
                  'Seattle, WA', 'Boston, MA', 'Denver, CO', 'Chicago, IL']

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            domain = acct['name'].lower().replace(' ', '') + '.com'
            emp = random.randint(100, 5000)

            w.writerow([
                aid,
                acct['name'],
                random.choice(industries),
                emp,
                acct['arr'] * random.uniform(5, 20),
                random.randint(2005, 2022),
                random.choice(cities),
                f'https://www.{domain}',
                acct.get('narrative', f'{acct["name"]} is a customer account.'),
            ])

        return out.getvalue()

    def generate_outcomes_csv(self) -> str:
        """Generate outcomes.csv with narrative-aligned dates (V3.1: richer outcomes + Phase 2 recovery)."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'outcome_date', 'outcome_type', 'title',
            'description', 'revenue_impact', 'status', 'linked_signal_id',
        ])

        phase_prefix = f'{self.phase}_' if self.phase else ''
        counter = 0
        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            cls = acct.get('classification', 'healthy')
            arr = acct['arr']
            acct_rng = random.Random(self.seed + aid + 8000)

            # Get planned outcome events for narrative-aligned dates
            planned_outcomes = self.planner.get_events(aid, 'outcome')

            # V3.1: Use richer outcome templates
            outcome_templates = self.PHASE1_OUTCOME_TEMPLATES.get(cls, self.PHASE1_OUTCOME_TEMPLATES['healthy'])
            # Determine how many outcomes: 3-4 critical, 2-3 at_risk, 1-2 healthy
            if cls == 'critical':
                n_outcomes = acct_rng.randint(3, min(4, len(outcome_templates)))
            elif cls == 'at_risk':
                n_outcomes = acct_rng.randint(2, min(3, len(outcome_templates)))
            else:
                n_outcomes = acct_rng.randint(1, min(2, len(outcome_templates)))

            selected_outcomes = outcome_templates[:n_outcomes]
            total_days = max(1, (self.end_date - self.start_date).days)

            for oi, (otype, title_tpl, desc_tpl, impact_pct, status) in enumerate(selected_outcomes):
                counter += 1
                impact = arr * impact_pct
                title = f'{title_tpl} — {acct["name"]}'
                desc = desc_tpl

                # Use narrative-planned date if available, else spread across range
                if oi < len(planned_outcomes):
                    outcome_date = planned_outcomes[oi].date_str
                else:
                    # Spread outcomes across the latter half of the time range
                    day_offset = int(total_days * 0.5) + acct_rng.randint(0, int(total_days * 0.5))
                    outcome_date = (self.start_date + timedelta(days=day_offset)).strftime('%Y-%m-%d')

                w.writerow([
                    aid,
                    outcome_date,
                    otype,
                    title,
                    desc,
                    round(impact, 2),
                    status,
                    f'{phase_prefix}sig_{aid}_1',
                ])

            # Intervention revenue outcome (from V2 — manifest-defined)
            intervention = acct.get('intervention', {})
            if self.phase == 'intervention' and intervention.get('revenue_outcome'):
                ro = intervention['revenue_outcome']
                counter += 1
                w.writerow([
                    aid,
                    self.end_date.strftime('%Y-%m-%d'),
                    ro['type'],
                    f'{ro["type"].replace("_", " ").title()} — {acct["name"]}',
                    ro.get('description', ''),
                    round(ro['amount'], 2),
                    'resolved',
                    f'{phase_prefix}sig_{aid}_1',
                ])

            # V3.1: Auto-generated recovery outcomes for intervention phase
            if self.phase == 'intervention':
                recovery_outcome_templates = self.RECOVERY_OUTCOME_TEMPLATES.get(cls, [])
                # Pick 2-3 for critical, 2 for at_risk, 1 for healthy
                if cls == 'critical':
                    n_recovery_outcomes = acct_rng.randint(2, min(3, len(recovery_outcome_templates)))
                elif cls == 'at_risk':
                    n_recovery_outcomes = min(2, len(recovery_outcome_templates))
                else:
                    n_recovery_outcomes = min(1, len(recovery_outcome_templates))

                selected_recovery = acct_rng.sample(
                    recovery_outcome_templates,
                    min(n_recovery_outcomes, len(recovery_outcome_templates)),
                )

                for ri, (ro_type, ro_title, ro_desc, ro_status) in enumerate(selected_recovery):
                    counter += 1
                    # Positive revenue impact for recovery outcomes
                    if ro_type == 'churn_averted':
                        rev_impact = arr * acct_rng.uniform(0.3, 0.5)
                    elif ro_type in ('revenue_protected', 'renewal_secured'):
                        rev_impact = arr * acct_rng.uniform(0.1, 0.25)
                    elif ro_type == 'expansion_approved':
                        rev_impact = arr * acct_rng.uniform(0.15, 0.3)
                    elif ro_type == 'revenue_growth':
                        rev_impact = arr * acct_rng.uniform(0.1, 0.2)
                    else:
                        rev_impact = arr * acct_rng.uniform(0.05, 0.1)

                    # Spread recovery outcomes across the intervention window
                    day_offset = int(total_days * (ri + 1) / (n_recovery_outcomes + 1))
                    outcome_date = (self.start_date + timedelta(days=day_offset)).strftime('%Y-%m-%d')

                    w.writerow([
                        aid,
                        outcome_date,
                        ro_type,
                        f'{ro_title} — {acct["name"]}',
                        ro_desc,
                        round(rev_impact, 2),
                        ro_status,
                        f'{phase_prefix}auto_recovery_{aid}_1',
                    ])

        return out.getvalue()

    def generate_decisions_csv(self) -> str:
        """Generate decisions.csv with narrative-aligned dates."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'decision_date', 'decision_id', 'title',
            'decision_maker_role', 'chosen_option', 'outcome_description',
            'risk_level', 'revenue_impact',
        ])

        phase_prefix = f'{self.phase}_' if self.phase else ''

        decision_templates = {
            'critical': [
                ('Escalation to executive sponsor', 'executive_sponsor', 'Escalate account risk', 'Risk review initiated', 'high'),
                ('Emergency retention plan', 'champion', 'Launch retention playbook', 'Retention plan in progress', 'critical'),
            ],
            'at_risk': [
                ('Renewal strategy review', 'executive_sponsor', 'Adjust contract terms', 'Renewal discussion underway', 'medium'),
                ('Feature adoption push', 'champion', 'Schedule training sessions', 'Training plan approved', 'medium'),
            ],
            'healthy': [
                ('Expansion discussion', 'champion', 'Propose upsell package', 'Expansion opportunity identified', 'low'),
            ],
        }

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            cls = acct.get('classification', 'healthy')
            arr = acct['arr']
            templates = decision_templates.get(cls, decision_templates['healthy'])

            # Get planned decision events for narrative-aligned dates
            planned_decisions = self.planner.get_events(aid, 'decision')

            for di, (title, role, chosen, outcome_desc, risk) in enumerate(templates):
                # Use narrative-planned date if available
                if di < len(planned_decisions):
                    decision_date = planned_decisions[di].date_str
                else:
                    decision_date = (self.end_date - timedelta(days=random.randint(10, 45))).strftime('%Y-%m-%d')
                rev_impact = -arr * 0.1 if cls == 'critical' else (-arr * 0.05 if cls == 'at_risk' else arr * 0.1)
                w.writerow([
                    aid,
                    decision_date,
                    f'{phase_prefix}dec_{aid}_{di+1}',
                    f'{title} — {acct["name"]}',
                    role,
                    chosen,
                    outcome_desc,
                    risk,
                    round(rev_impact, 2),
                ])

            # Intervention decisions (from V2 — manifest-defined)
            intervention = acct.get('intervention', {})
            if self.phase == 'intervention' and intervention.get('decisions'):
                for di, dec in enumerate(intervention['decisions']):
                    w.writerow([
                        aid,
                        dec['date'],
                        f'int_dec_{aid}_{di+1}',
                        dec['title'],
                        dec.get('decision_maker', 'executive_sponsor'),
                        dec.get('rationale', ''),
                        f'Intervention: {dec["title"]}',
                        dec.get('impact', 'high'),
                        round(arr * 0.1, 2),
                    ])

            # V3.1: Auto-generated recovery decisions for intervention phase
            if self.phase == 'intervention':
                acct_rng = random.Random(self.seed + aid + 9000)
                recovery_decision_templates = self.RECOVERY_DECISION_TEMPLATES.get(cls, [])
                total_days = max(1, (self.end_date - self.start_date).days)

                for rdi, (rd_title, rd_role, rd_chosen, rd_outcome, rd_risk) in enumerate(recovery_decision_templates):
                    day_offset = int(total_days * (rdi + 1) / (len(recovery_decision_templates) + 1))
                    decision_date = (self.start_date + timedelta(days=day_offset)).strftime('%Y-%m-%d')
                    rev_impact = arr * acct_rng.uniform(0.05, 0.15)
                    w.writerow([
                        aid,
                        decision_date,
                        f'{phase_prefix}auto_dec_{aid}_{rdi+1}',
                        f'{rd_title} — {acct["name"]}',
                        rd_role,
                        rd_chosen,
                        rd_outcome,
                        rd_risk,
                        round(rev_impact, 2),
                    ])

        return out.getvalue()

    def generate_signal_edges_csv(self) -> str:
        """Generate signal_edges.csv — causal links between signals, decisions, outcomes."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'from_signal_ref', 'to_signal_ref',
            'edge_type', 'label', 'confidence', 'lag_days',
        ])

        phase_prefix = f'{self.phase}_' if self.phase else ''

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            cls = acct.get('classification', 'healthy')

            if cls == 'critical':
                edges = [
                    (f'sig_{aid}_1', f'decision:dec_{aid}_1', 'TRIGGERED', 'Signal triggered escalation', 0.9, 7),
                    (f'decision:dec_{aid}_1', 'outcome:revenue_at_risk', 'LED_TO', 'Escalation revealed risk', 0.85, 14),
                    (f'sig_{aid}_1', f'decision:dec_{aid}_2', 'TRIGGERED', 'Signal triggered retention plan', 0.85, 10),
                    (f'decision:dec_{aid}_2', 'outcome:engagement_decline', 'LED_TO', 'Retention plan in response to decline', 0.8, 21),
                ]
            elif cls == 'at_risk':
                edges = [
                    (f'sig_{aid}_1', f'decision:dec_{aid}_1', 'TRIGGERED', 'Signal triggered renewal review', 0.8, 14),
                    (f'decision:dec_{aid}_1', 'outcome:renewal_risk', 'LED_TO', 'Review surfaced renewal risk', 0.75, 21),
                ]
            else:
                edges = [
                    (f'sig_{aid}_1', f'decision:dec_{aid}_1', 'TRIGGERED', 'Positive signal prompted expansion', 0.85, 7),
                    (f'decision:dec_{aid}_1', 'outcome:expansion_opportunity', 'LED_TO', 'Discussion identified expansion', 0.8, 14),
                ]

            for from_ref, to_ref, etype, label, conf, lag in edges:
                w.writerow([aid, from_ref, to_ref, etype, label, conf, lag])

            # Intervention edges (from V2)
            intervention = acct.get('intervention', {})
            if self.phase == 'intervention' and intervention.get('decisions'):
                n_decisions = len(intervention['decisions'])
                n_recovery = len(intervention.get('recovery_signals', []))

                for di in range(min(n_decisions, n_recovery)):
                    w.writerow([
                        aid,
                        f'decision:int_dec_{aid}_{di+1}',
                        f'intervention_recovery_{aid}_{di+100}',
                        'LED_TO',
                        f'Intervention: {intervention["decisions"][di]["title"]}',
                        0.9,
                        14,
                    ])

                if intervention.get('revenue_outcome'):
                    amt = intervention['revenue_outcome']['amount']
                    w.writerow([
                        aid,
                        f'decision:int_dec_{aid}_{n_decisions}',
                        'outcome:revenue_protected',
                        'LED_TO',
                        f'Intervention protected ${amt/1e6:.1f}M ARR',
                        0.95,
                        30,
                    ])

            # V3.1: Auto-generated recovery edges for intervention phase
            if self.phase == 'intervention':
                recovery_decision_templates = self.RECOVERY_DECISION_TEMPLATES.get(cls, [])
                recovery_outcome_templates = self.RECOVERY_OUTCOME_TEMPLATES.get(cls, [])

                # Link recovery signals -> recovery decisions
                for rdi in range(len(recovery_decision_templates)):
                    w.writerow([
                        aid,
                        f'{phase_prefix}auto_recovery_{aid}_1',
                        f'decision:{phase_prefix}auto_dec_{aid}_{rdi+1}',
                        'TRIGGERED',
                        f'Recovery signal triggered intervention decision',
                        0.85,
                        7,
                    ])

                # Link recovery decisions -> recovery outcomes
                n_dec = len(recovery_decision_templates)
                n_out = min(len(recovery_outcome_templates), 3 if cls == 'critical' else (2 if cls == 'at_risk' else 1))
                for roi in range(n_out):
                    dec_idx = min(roi, n_dec - 1) if n_dec > 0 else 0
                    if n_dec > 0:
                        ro_type = recovery_outcome_templates[roi][0] if roi < len(recovery_outcome_templates) else 'revenue_protected'
                        w.writerow([
                            aid,
                            f'decision:{phase_prefix}auto_dec_{aid}_{dec_idx+1}',
                            f'outcome:{ro_type}',
                            'LED_TO',
                            f'Intervention led to {ro_type.replace("_", " ")}',
                            0.9,
                            21,
                        ])

        return out.getvalue()

    def generate_industry_benchmarks_csv(self) -> str:
        """Generate industry_benchmarks.csv — one row per manifest KPI."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'kpi_code', 'benchmark_source', 'industry_p50',
            'industry_p25', 'industry_p75', 'account_percentile',
            'sample_size', 'benchmark_date',
        ])
        bench_date = self.end_date.strftime('%Y-%m-%d')
        for code in self.kpi_codes:
            meta = self.kpi_catalog.get(code, {})
            tv = meta.get('target', 85.0)
            if isinstance(tv, dict):
                p50 = float(tv.get('value', 85.0))
            else:
                try:
                    p50 = float(tv)
                except (TypeError, ValueError):
                    p50 = 85.0
            p25 = round(p50 * 0.85, 2)
            p75 = round(p50 * 1.15, 2)
            w.writerow([
                code,
                'DC2_S Industry Peer Index',
                p50,
                p25,
                p75,
                random.randint(35, 75),
                random.choice([200, 350, 500, 750, 1000]),
                bench_date,
            ])
        return out.getvalue()

    def get_upload_file_map(self) -> Dict[str, str]:
        """
        Generate all CSVs in memory and return {file_type: csv_content}.
        Headers are normalized with account_id (not source_account_id).
        """
        return {
            'accounts': self._header_use_account_id(self.generate_accounts_csv()),
            'kpi_measurements': self._header_use_account_id(self.generate_kpi_measurements_csv()),
            'enhanced_signals': self._header_use_account_id(self.generate_signals_csv()),
            'products': self._header_use_account_id(self.generate_products_csv()),
            'stakeholders': self._header_use_account_id(self.generate_stakeholders_csv()),
            'engagement_events': self._header_use_account_id(self.generate_engagement_events_csv()),
            'account_business_profiles': self._header_use_account_id(self.generate_profiles_csv()),
            'outcomes': self._header_use_account_id(self.generate_outcomes_csv()),
            'decisions': self._header_use_account_id(self.generate_decisions_csv()),
            'signal_edges': self._header_use_account_id(self.generate_signal_edges_csv()),
        }


# ═══════════════════════════════════════════════════════════════════════
# ScenarioManifest (V3: merged V2 validation)
# ═══════════════════════════════════════════════════════════════════════

class ScenarioManifest(BaseScenario):
    """
    Manifest-driven data load scenario with post-process validation.

    Reads a manifest JSON, generates all CSVs, uploads them via
    the onboarding API, triggers process-data, and validates results.

    V3: merged V2 validation logic (health score checks, distribution,
    KPI cardinality) directly into this class.
    """

    # ── Validation helpers (merged from ScenarioManifestV2) ──

    def _expected_distribution(self, accounts: List[Dict[str, Any]]) -> Dict[str, int]:
        out = {'critical': 0, 'at_risk': 0, 'healthy': 0}
        for acct in accounts:
            cls = str(acct.get('classification', 'healthy')).lower()
            if cls in out:
                out[cls] += 1
            else:
                out['healthy'] += 1
        return out

    @staticmethod
    def _manifest_class_for_account(acct: Dict[str, Any]) -> str:
        cls = str(acct.get('classification', 'healthy')).lower()
        if cls in ('critical', 'at_risk', 'healthy'):
            return cls
        return 'healthy'

    def _expected_account_ids(self, customer_id: int, n_accounts: int) -> List[int]:
        base = customer_id * 1000 + 1
        return [base + i for i in range(n_accounts)]

    def _status_from_score(self, score: float) -> str:
        if score >= 70:
            return 'healthy'
        if score >= 50:
            return 'at_risk'
        return 'critical'

    def _extract_score_and_status(self, payload: Dict[str, Any]) -> Tuple[float, str]:
        if not payload:
            return 0.0, 'critical'

        if payload.get('overall_score') is not None:
            try:
                score_f = float(payload['overall_score'])
            except Exception:
                score_f = 0.0
            status = str(payload.get('health_status') or '').lower()
            if status == 'risk':
                status = 'at_risk'
            if status not in ('critical', 'at_risk', 'healthy'):
                status = self._status_from_score(score_f)
            return score_f, status

        hs = payload.get('health_score')
        if isinstance(hs, dict):
            score = hs.get('health_score')
            status_raw = hs.get('health_status')
        else:
            score = hs
            status_raw = payload.get('health_status')

        if score is None and isinstance(payload.get('health'), dict):
            score = payload['health'].get('score')
        if score is None and isinstance(payload.get('data'), dict):
            score = payload['data'].get('health_score')
        try:
            score_f = float(score) if score is not None else 0.0
        except Exception:
            score_f = 0.0

        def _norm(s: Any) -> str:
            r = str(s or '').lower().strip()
            if r in ('excellent', 'good', 'healthy'):
                return 'healthy'
            if r in ('warning', 'at_risk', 'risk'):
                return 'at_risk'
            if r == 'critical':
                return 'critical'
            return ''

        status = _norm(status_raw)
        if not status:
            status = _norm(payload.get('health_status'))
        if not status:
            st = payload.get('status')
            if st not in ('success', 'warning', 'error', None):
                status = _norm(st)
        if not status:
            status = self._status_from_score(score_f)
        if status not in ('critical', 'at_risk', 'healthy'):
            status = self._status_from_score(score_f)
        return score_f, status

    def _extract_kpi_count(self, payload: Dict[str, Any]) -> int:
        if not payload:
            return 0
        kc = payload.get('kpi_count')
        if kc is not None:
            try:
                return int(kc)
            except Exception:
                pass
        for key in ('kpi_scores', 'kpis', 'kpi_data'):
            v = payload.get(key)
            if isinstance(v, list):
                return len(v)
            if isinstance(v, dict):
                return len(v)
        if isinstance(payload.get('pillars'), list):
            total = 0
            for p in payload['pillars']:
                if isinstance(p, dict):
                    k = p.get('kpis')
                    if isinstance(k, list):
                        total += len(k)
            if total > 0:
                return total
        return 0

    def _validate_post_process(
        self,
        customer_id: int,
        expected_account_ids: List[int],
        manifest_accounts: List[Dict[str, Any]],
        expected_kpi_count: int,
        expected_distribution: Dict[str, int],
        sample_size: int,
        health_tolerance: int,
        strict: bool,
    ) -> Dict[str, Any]:
        checks: Dict[str, Any] = {'passed': True, 'errors': [], 'metrics': {}}

        accounts_resp = self.client.get_accounts() or []
        actual_ids = []
        for row in accounts_resp:
            if not isinstance(row, dict):
                continue
            aid = row.get('account_id') or row.get('source_account_id') or row.get('id')
            if aid is None:
                continue
            try:
                actual_ids.append(int(aid))
            except Exception:
                continue

        exp_set = set(expected_account_ids)
        act_set = set(actual_ids)
        missing_ids = sorted(exp_set - act_set)
        checks['metrics']['accounts_expected'] = len(expected_account_ids)
        checks['metrics']['accounts_found'] = len(act_set)
        checks['metrics']['missing_account_ids'] = missing_ids[:20]
        if missing_ids:
            checks['passed'] = False
            checks['errors'].append(f'Missing expected account IDs: {missing_ids[:10]}')

        sample_ids = expected_account_ids[:max(1, min(sample_size, len(expected_account_ids)))]
        id_to_manifest: Dict[int, str] = {}
        for i, aid in enumerate(expected_account_ids):
            if i < len(manifest_accounts):
                id_to_manifest[aid] = self._manifest_class_for_account(manifest_accounts[i])
            else:
                id_to_manifest[aid] = 'healthy'
        expected_sample_manifest = {'critical': 0, 'at_risk': 0, 'healthy': 0}
        for aid in sample_ids:
            c = id_to_manifest.get(aid, 'healthy')
            expected_sample_manifest[c] += 1

        endpoint_failures = []
        actual_distribution = {'critical': 0, 'at_risk': 0, 'healthy': 0}
        kpi_count_failures = []
        validation_call_seconds: Dict[str, float] = {}
        for aid in sample_ids:
            t_call = time.time()
            payload = self.client.get_dc2s_health_score(aid)
            validation_call_seconds[str(aid)] = round(time.time() - t_call, 3)
            if not payload:
                endpoint_failures.append(aid)
                continue
            score, status = self._extract_score_and_status(payload)
            actual_distribution[status] += 1
            kpi_count = self._extract_kpi_count(payload)
            if strict and kpi_count < expected_kpi_count:
                kpi_count_failures.append((aid, kpi_count))
            if kpi_count == 0 or payload.get('error'):
                endpoint_failures.append(aid)
            checks['metrics'].setdefault('sample_scores', {})[str(aid)] = {
                'health_score': round(score, 2),
                'status': status,
                'kpi_count': kpi_count,
            }

        checks['metrics']['sample_size'] = len(sample_ids)
        checks['metrics']['endpoint_failures'] = endpoint_failures
        checks['metrics']['validation_call_seconds'] = validation_call_seconds
        if validation_call_seconds:
            vals = list(validation_call_seconds.values())
            checks['metrics']['validation_latency_summary_s'] = {
                'min': round(min(vals), 3),
                'max': round(max(vals), 3),
                'avg': round(sum(vals) / len(vals), 3),
            }
        if endpoint_failures:
            checks['passed'] = False
            checks['errors'].append(f'Account score endpoint failed/empty for IDs: {endpoint_failures[:10]}')

        checks['metrics']['sample_distribution_actual'] = actual_distribution
        checks['metrics']['sample_distribution_expected'] = dict(expected_sample_manifest)
        phase = getattr(self.args, 'phase', None)
        skip_dist = (not strict) or (phase == 'intervention')
        if skip_dist and phase == 'intervention':
            logger.info(
                '    Distribution drift check skipped (intervention phase — tiers expected to shift)'
            )
        for cls in ('critical', 'at_risk', 'healthy'):
            if skip_dist:
                continue
            expected_sample = expected_sample_manifest[cls]
            if abs(actual_distribution[cls] - expected_sample) > health_tolerance:
                checks['passed'] = False
                checks['errors'].append(
                    f'Health distribution drift for {cls}: actual={actual_distribution[cls]} '
                    f'expected~={expected_sample} tolerance={health_tolerance}'
                )

        checks['metrics']['kpi_count_failures'] = kpi_count_failures[:10]
        if kpi_count_failures:
            checks['passed'] = False
            checks['errors'].append(f'KPI cardinality shortfall in sample accounts: {kpi_count_failures[:5]}')

        # ── Health summary validation ──
        try:
            health_resp = self.client.get('/api/dc2s/health-summary')
            if health_resp:
                total = health_resp.get('total_accounts', 0)
                avg_health = health_resp.get('average_health', 0)
                checks['metrics']['health_summary'] = {
                    'total_accounts': total,
                    'average_health': avg_health,
                }
                if total == 0:
                    checks['errors'].append('No health scores computed after process-data')
                    checks['passed'] = False
                elif avg_health == 0:
                    checks['errors'].append(f'Health scores all zero ({total} accounts)')
                    checks['passed'] = False
                else:
                    logger.info(f'    Health: avg={avg_health:.1f} across {total} accounts')
            else:
                logger.warning('    Health summary endpoint returned None (non-fatal)')
        except Exception as e:
            logger.warning(f'    Health summary check failed (non-fatal): {e}')

        # ── Context graph validation (if CG was enabled) ──
        try:
            if self.client.is_context_graph_enabled(customer_id):
                cg_found = False
                for sample_aid in expected_account_ids[:3]:
                    graph = self.client.get_context_graph_summary(sample_aid)
                    if graph and graph.get('total_nodes', 0) > 0:
                        total_nodes = graph['total_nodes']
                        logger.info(f'    CG: account {sample_aid} has {total_nodes} nodes')
                        checks['metrics']['context_graph_sample'] = {
                            'account_id': sample_aid,
                            'total_nodes': total_nodes,
                        }
                        cg_found = True
                        break
                if not cg_found:
                    checks['metrics']['context_graph_warning'] = (
                        'Context graph enabled but no nodes found for sample accounts'
                    )
                    logger.warning('    Context graph enabled but no nodes found for sample accounts')
        except Exception as e:
            logger.warning(f'    Context graph validation failed (non-fatal): {e}')

        return checks

    # ── Main run method ──

    def run(self) -> Dict[str, Any]:
        self.start_timer()
        logger.info('=== Scenario: Manifest-Driven Load V3 ===')

        api_calls = 0
        errors: List[str] = []
        results: Dict[str, Any] = {}

        manifest_path = getattr(self.args, 'manifest', None)
        if not manifest_path:
            return self.failure('--manifest path required')
        manifest_path = Path(manifest_path)
        if not manifest_path.exists():
            return self.failure(f'Manifest not found: {manifest_path}')

        customer_id = getattr(self.args, 'customer_id', None) or \
                      getattr(self.client, 'customer_id', None)
        if not customer_id:
            return self.failure('--customer-id required for manifest scenario')
        seed = getattr(self.args, 'seed', None) or 42
        phase = getattr(self.args, 'phase', None)

        strict = bool(getattr(self.args, 'validate_strict', True))
        sample_size = int(getattr(self.args, 'validate_sample_size', 5))
        health_tolerance = int(getattr(self.args, 'health_tolerance', 1))

        try:
            gen = ManifestCSVGenerator(
                manifest_path=str(manifest_path),
                customer_id=int(customer_id),
                seed=seed,
                phase=phase,
            )

            expected_ids = self._expected_account_ids(int(customer_id), len(gen.accounts))
            expected_kpi_count = len(gen.kpi_codes)
            expected_distribution = self._expected_distribution(gen.accounts)

            results['manifest'] = str(manifest_path)
            results['customer_id'] = int(customer_id)
            results['customer_name'] = gen.customer_info['name']
            results['phase'] = phase
            results['num_accounts'] = len(gen.accounts)
            results['num_kpis'] = len(gen.kpi_codes)
            results['time_range'] = gen.time_range
            results['expected'] = {
                'accounts': len(gen.accounts),
                'kpi_count_per_account': expected_kpi_count,
                'expected_account_ids_preview': expected_ids[:5],
                'expected_distribution': expected_distribution,
            }
            logger.info(f'    {gen.customer_info["name"]}: '
                        f'{len(gen.accounts)} accounts, {len(gen.kpi_codes)} KPIs, '
                        f'{gen.data_points} data points')

            # Step 1: Generate + upload CSVs (streamed per file)
            logger.info('  Step 1/2: Generate + upload CSVs')
            filename_map = {
                'accounts': 'accounts.csv',
                'kpi_measurements': 'kpi_measurements.csv',
                'enhanced_signals': 'enhanced_qualitative_signals.csv',
                'products': 'products.csv',
                'stakeholders': 'stakeholders.csv',
                'engagement_events': 'engagement_events.csv',
                'account_business_profiles': 'account_business_profiles.csv',
                'outcomes': 'outcomes.csv',
                'decisions': 'decisions.csv',
                'signal_edges': 'signal_edges.csv',
                'industry_benchmarks': 'industry_benchmarks.csv',
            }
            generators = {
                'accounts': gen.generate_accounts_csv,
                'kpi_measurements': gen.generate_kpi_measurements_csv,
                'enhanced_signals': gen.generate_signals_csv,
                'products': gen.generate_products_csv,
                'stakeholders': gen.generate_stakeholders_csv,
                'engagement_events': gen.generate_engagement_events_csv,
                'account_business_profiles': gen.generate_profiles_csv,
                'outcomes': gen.generate_outcomes_csv,
                'decisions': gen.generate_decisions_csv,
                'signal_edges': gen.generate_signal_edges_csv,
                'industry_benchmarks': gen.generate_industry_benchmarks_csv,
            }
            upload_results = {}
            endpoint_metrics = {
                'generate_seconds': {},
                'upload_seconds': {},
                'upload_bytes': {},
                'upload_status': {},
            }
            t_step12 = time.time()
            for file_type, gen_fn in generators.items():
                t_gen = time.time()
                csv_content = ManifestCSVGenerator._header_use_account_id(gen_fn())
                endpoint_metrics['generate_seconds'][file_type] = round(time.time() - t_gen, 3)
                endpoint_metrics['upload_bytes'][file_type] = len(csv_content.encode('utf-8'))

                t_up = time.time()
                resp = self.client.upload_csv(
                    customer_id=int(customer_id),
                    file_type=file_type,
                    csv_content=csv_content,
                    filename=filename_map.get(file_type, f'{file_type}.csv'),
                )
                endpoint_metrics['upload_seconds'][file_type] = round(time.time() - t_up, 3)
                api_calls += 1
                ok = bool(resp and resp.get('status') == 'success')
                upload_results[file_type] = 'success' if ok else f'failed: {str(resp)[:80]}'
                endpoint_metrics['upload_status'][file_type] = 'success' if ok else 'failed'
                if not ok:
                    errors.append(f'Upload failed: {file_type}')
                else:
                    logger.info(f'    {file_type}: uploaded')

            results['upload_results'] = upload_results
            total_upload_bytes = sum(endpoint_metrics['upload_bytes'].values())
            total_upload_s = sum(endpoint_metrics['upload_seconds'].values())
            endpoint_metrics['upload_throughput_bytes_per_s'] = round(
                total_upload_bytes / max(total_upload_s, 0.001), 2
            )
            endpoint_metrics['step12_duration_s'] = round(time.time() - t_step12, 2)
            results['endpoint_metrics'] = endpoint_metrics
            results['generation_duration_s'] = round(
                sum(endpoint_metrics['generate_seconds'].values()), 2
            )
            results['upload_duration_s'] = round(total_upload_s, 2)

            successes = sum(1 for v in upload_results.values() if v == 'success')
            logger.info(f'    Uploaded {successes}/{len(generators)} files')

            if successes == 0:
                return self.failure(
                    'All CSV uploads failed',
                    api_calls=api_calls, errors=errors, details=results,
                )

            # Step 2: Process data
            logger.info('  Step 3: process-data')
            original_timeout = self.client.timeout
            self.client.timeout = 300
            t1 = time.time()
            process_resp = self.client.process_data(
                customer_id=int(customer_id),
                skip_wizard_b=True,
                skip_wizard_c=False,
                strict_kpi_ranges=False,
            )
            self.client.timeout = original_timeout
            api_calls += 1
            results['process_duration_s'] = round(time.time() - t1, 2)
            results['process_response'] = process_resp or {}
            results.setdefault('endpoint_metrics', {})['process_data_seconds'] = round(
                time.time() - t1, 3
            )
            results['endpoint_metrics']['process_data_status'] = (
                process_resp.get('status') if process_resp else 'failed'
            )

            if not (process_resp and process_resp.get('status') in ('success', 'warning')):
                return self.failure(
                    f'process-data failed: {str(process_resp)[:150]}',
                    api_calls=api_calls, errors=errors, details=results,
                )

            # Step 3: Post-process validations
            logger.info('  Step 4: post-process validations')
            validation = self._validate_post_process(
                customer_id=int(customer_id),
                expected_account_ids=expected_ids,
                manifest_accounts=gen.accounts,
                expected_kpi_count=expected_kpi_count,
                expected_distribution=expected_distribution,
                sample_size=sample_size,
                health_tolerance=health_tolerance,
                strict=strict,
            )
            results['validation'] = validation
            if not validation['passed']:
                return self.failure(
                    'Manifest ingest completed but validation checks failed',
                    api_calls=api_calls,
                    errors=errors + validation.get('errors', []),
                    details=results,
                )

        except Exception as e:
            logger.error(f'Manifest V3 scenario error: {e}', exc_info=True)
            return self.failure(
                f'Manifest V3 scenario failed: {str(e)}',
                api_calls=api_calls, errors=errors, details=results,
            )

        return self.success(
            f'Manifest V3 loaded + validated: {results["customer_name"]} '
            f'({results["expected"]["accounts"]} accounts, '
            f'{results["num_kpis"]} KPIs, {gen.data_points} data points)',
            api_calls=api_calls,
            errors=errors,
            details=results,
        )
