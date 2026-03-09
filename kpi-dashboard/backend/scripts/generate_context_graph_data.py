#!/usr/bin/env python3
"""
Context Graph 9-CSV Generator

Reads story arc manifests and generates the 9 additional CSVs needed for
context graph mode. This is SEPARATE from generate_synthetic_customer_data.py
(regular model, 6 CSVs).

The 9 CSVs generated:
  1. stakeholders.csv
  2. engagement_events.csv
  3. account_business_profiles.csv
  4. decisions.csv
  5. outcomes.csv
  6. signal_edges.csv
  7. decision_evidence.csv
  8. industry_benchmarks.csv
  9. enhanced_qualitative_signals.csv

Column names follow config/csv_schemas.json (shared with load driver).

Usage:
    # Single arc for all accounts (original mode):
    python generate_context_graph_data.py --customer-id 9 --arc arc_expansion_champion

    # All 8 arcs, one batch each:
    python generate_context_graph_data.py --customer-id 9 --all-arcs

    # Health-aware: assigns different arcs per account based on health scores:
    python generate_context_graph_data.py --customer-id 291 --health-aware

    # Programmatic:
    from scripts.generate_context_graph_data import ContextGraphGenerator
    gen = ContextGraphGenerator(customer_id=9, arc_id='arc_expansion_champion')
    gen.generate_all('/path/to/output/')

    # Per-account arc assignment:
    arc_map = {291001: 'arc_expansion_champion', 291007: 'arc_silent_churn'}
    gen = ContextGraphGenerator(customer_id=291, account_arc_map=arc_map)
    gen.generate_all('/path/to/output/')
"""

import csv
import io
import json
import logging
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from faker import Faker
    fake = Faker()
except ImportError:
    fake = None

from utils.story_arc_loader import load_arc, load_all_arcs, validate_arc, _get_phase_for_week

logger = logging.getLogger(__name__)

# Departments for stakeholders
DEPARTMENTS = ['Engineering', 'IT', 'Operations', 'Executive', 'Finance', 'Data Science']

TECH_STACKS = ['NVIDIA DGX + Kubernetes', 'AMD MI300X + Slurm', 'Custom GPU Cluster + Ray',
               'NVIDIA H100 + vSphere', 'Mixed GPU + OpenShift']

CLOUD_PROVIDERS = ['On-Premises Only', 'Hybrid (AWS + On-Prem)', 'Hybrid (Azure + On-Prem)',
                   'Hybrid (GCP + On-Prem)', 'Multi-Cloud Hybrid']

STRATEGIC_INITIATIVES = [
    'AI/ML model training at scale', 'Real-time inference deployment',
    'Data center modernization', 'Edge compute expansion',
    'Sustainability & power efficiency', 'Multi-cloud strategy',
    'Generative AI adoption', 'HPC workload migration',
]

# ─── Health-to-Arc Mapping ────────────────────────────────────────────────
# Maps health classification to appropriate story arc pools.
# Critical accounts get churn/crisis arcs, healthy accounts get expansion arcs.
# This ensures context graph data is consistent with health scores and
# Wizard B milestone logic (churn milestones for critical, expansion for healthy).

HEALTH_ARC_POOLS = {
    'critical': ['arc_silent_churn', 'arc_crisis_recovery'],
    'at_risk': ['arc_competitive_displacement', 'arc_stalled_deployment', 'arc_exec_sponsor_change'],
    'healthy': ['arc_expansion_champion', 'arc_land_and_expand', 'arc_seasonal_surge'],
}


def classify_health(score: float) -> str:
    """Classify health score into critical/at_risk/healthy.

    Uses the centralized thresholds: Critical <50, At-Risk 50-69, Healthy 70+.
    """
    if score < 50:
        return 'critical'
    elif score < 70:
        return 'at_risk'
    return 'healthy'


def build_health_arc_map(
    customer_id: int,
    num_accounts: int = 10,
    health_scores: Optional[Dict[int, float]] = None,
    seed: int = 42,
) -> Dict[int, str]:
    """Build per-account arc assignment based on health scores.

    Args:
        customer_id: Customer ID (accounts are customer_id*1000+1 through +num_accounts)
        num_accounts: Number of accounts
        health_scores: Optional dict of {account_id: health_score}. If not provided,
                       queries from DB using Flask app context.
        seed: Random seed for reproducible arc selection within each pool.

    Returns:
        Dict mapping account_id -> arc_id
    """
    rng = random.Random(seed)
    account_base = customer_id * 1000 + 1
    assignments = {}

    # If health_scores not provided, try to query from DB
    if health_scores is None:
        health_scores = _query_health_scores(customer_id, num_accounts)

    for i in range(num_accounts):
        account_id = account_base + i
        health = health_scores.get(account_id, 65.0)  # default to at-risk
        classification = classify_health(health)
        pool = HEALTH_ARC_POOLS[classification]
        arc_id = rng.choice(pool)
        assignments[account_id] = arc_id
        logger.info(
            f"Account {account_id}: health={health:.1f} ({classification}) -> {arc_id}"
        )

    return assignments


def _query_health_scores(customer_id: int, num_accounts: int = 10) -> Dict[int, float]:
    """Query account health scores from DB.

    Uses the same health calculation as /api/dc2s/accounts:
    reads trailing DC2S KPI values and applies config-aware weights.

    Requires Flask app context. Falls back to defaults if unavailable.
    """
    scores = {}

    try:
        from models import Account
        from verticals.dc2_s.api_routes import (
            calculate_kpi_health,
            _get_trailing_kpi_values,
        )

        accounts = Account.query.filter_by(
            customer_id=customer_id,
            vertical='dc2_s',
        ).all()

        for account in accounts:
            try:
                trailing_kpis = _get_trailing_kpi_values(account.account_id, days=30)
                if not trailing_kpis:
                    continue
                overall_health, _ = calculate_kpi_health(trailing_kpis, customer_id=customer_id)
                scores[account.account_id] = round(float(overall_health), 1)
            except Exception as e:
                logger.warning(f"Could not compute health for account {account.account_id}: {e}")

    except Exception as e:
        logger.warning(f"DB query failed, using default health scores: {e}")

    return scores


class ContextGraphGenerator:
    """
    Generates 9 context graph CSVs from story arc manifests.

    Each account in the customer gets assigned a story arc, and the generator
    produces CSV rows driven by the arc's phases, plot points, cast, decisions,
    outcomes, causal chains, and benchmarks.

    Supports two modes:
    - Single-arc mode (backward compatible): All accounts share one arc.
    - Per-account mode: Each account gets its own arc via account_arc_map.
    """

    def __init__(
        self,
        customer_id: int,
        arc_id: str = 'arc_expansion_champion',
        num_accounts: int = 10,
        seed: int = None,
        account_arc_map: Optional[Dict[int, str]] = None,
    ):
        self.customer_id = customer_id
        self.arc_id = arc_id
        self.num_accounts = num_accounts
        self.account_base = customer_id * 1000 + 1

        if seed is not None:
            random.seed(seed)
            if fake:
                Faker.seed(seed)

        # ── Per-account arc mode ──────────────────────────────────────
        self._account_arc_map = account_arc_map or {}

        if account_arc_map:
            # Load all unique arcs referenced in the map
            unique_arc_ids = set(account_arc_map.values())
            self._arc_cache: Dict[str, dict] = {}
            for aid in unique_arc_ids:
                arc = load_arc(aid)
                if not arc:
                    raise ValueError(f"Story arc '{aid}' not found")
                errors = validate_arc(arc)
                if errors:
                    logger.warning(f"Arc {aid} has validation issues: {errors}")
                self._arc_cache[aid] = arc

            # Default arc for backward compat (used in non-account-loop generators)
            self.arc = self._arc_cache.get(
                arc_id, list(self._arc_cache.values())[0]
            )
            # Account list from the map
            self.account_ids = sorted(account_arc_map.keys())
            self.num_accounts = len(self.account_ids)
        else:
            # Single-arc mode (backward compatible)
            self.arc = load_arc(arc_id)
            if not self.arc:
                raise ValueError(f"Story arc '{arc_id}' not found")
            errors = validate_arc(self.arc)
            if errors:
                logger.warning(f"Arc {arc_id} has validation issues: {errors}")
            self._arc_cache = {arc_id: self.arc}
            self.account_ids = [self.account_base + i for i in range(num_accounts)]

        # ── Pre-compute timing per arc ────────────────────────────────
        now = datetime.utcnow()
        self._arc_phase_starts: Dict[str, List[int]] = {}
        self._arc_total_weeks: Dict[str, int] = {}
        self._arc_base_dates: Dict[str, datetime] = {}

        for aid, arc in self._arc_cache.items():
            phase_starts = []
            cumulative = 0
            for phase in arc['phases']:
                phase_starts.append(cumulative)
                cumulative += phase.get('duration_weeks', 0)
            self._arc_phase_starts[aid] = phase_starts
            self._arc_total_weeks[aid] = cumulative
            # Each arc's timeline ends ~1 week before now
            self._arc_base_dates[aid] = now - timedelta(weeks=cumulative, days=7)

        # Backward-compatible instance vars (for default arc)
        default_aid = arc_id if arc_id in self._arc_cache else list(self._arc_cache.keys())[0]
        self.phase_starts = self._arc_phase_starts[default_aid]
        self.total_weeks = self._arc_total_weeks[default_aid]
        self.base_date = self._arc_base_dates[default_aid]

    # ─── Arc context helpers ──────────────────────────────────────────────

    def _get_arc_id(self, account_id: int) -> str:
        """Get the arc ID for a specific account."""
        return self._account_arc_map.get(account_id, self.arc_id)

    def _set_arc_context(self, account_id: int):
        """Switch self.arc / phase_starts / total_weeks / base_date to match
        the arc assigned to a specific account.

        This lets all generator methods use self.arc, self.phase_starts, etc.
        without modification — just call this at the top of each account loop.
        """
        aid = self._get_arc_id(account_id)
        self.arc = self._arc_cache.get(aid, self.arc)
        self.phase_starts = self._arc_phase_starts.get(aid, self.phase_starts)
        self.total_weeks = self._arc_total_weeks.get(aid, self.total_weeks)
        self.base_date = self._arc_base_dates.get(aid, self.base_date)

    def _unique_arcs(self) -> Dict[str, dict]:
        """Get all unique arcs in use (for non-account-loop generators)."""
        return self._arc_cache

    # ─── Existing helpers ─────────────────────────────────────────────────

    def _week_to_date(self, week: int) -> datetime:
        """Convert absolute week number to a date."""
        return self.base_date + timedelta(weeks=week - 1, days=random.randint(0, 4))

    def _make_name(self, prefix: str = '') -> str:
        if fake:
            return fake.name()
        return f"{prefix}-{random.randint(1000, 9999)}"

    def _make_email(self, name: str = '') -> str:
        if fake:
            return fake.email()
        clean = name.lower().replace(' ', '.') if name else f"user{random.randint(100,999)}"
        return f"{clean}@example.com"

    def _get_account_arr(self, account_id: int) -> float:
        """Get account ARR from DB, falling back to arc's arr_start.

        Used to scale revenue values proportionally per account.
        """
        try:
            from models import Account
            account = Account.query.filter_by(account_id=account_id).first()
            if account:
                if account.profile_metadata and isinstance(account.profile_metadata, dict):
                    arr = float(account.profile_metadata.get('arr', 0) or 0)
                    if arr > 0:
                        return arr
                if account.revenue:
                    return float(account.revenue)
        except Exception:
            pass
        # Fallback: use arc's base ARR (no scaling)
        return float(self.arc.get('revenue_narrative', {}).get('arr_start', 2400000))

    def generate_all(self, output_dir: str) -> Dict[str, str]:
        """Generate all 9 context graph CSVs to the specified directory."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        generators = [
            ('stakeholders.csv', self.generate_stakeholders_csv),
            ('engagement_events.csv', self.generate_engagement_events_csv),
            ('account_business_profiles.csv', self.generate_account_business_profiles_csv),
            ('decisions.csv', self.generate_decisions_csv),
            ('outcomes.csv', self.generate_outcomes_csv),
            ('signal_edges.csv', self.generate_signal_edges_csv),
            ('decision_evidence.csv', self.generate_decision_evidence_csv),
            ('industry_benchmarks.csv', self.generate_industry_benchmarks_csv),
            ('enhanced_qualitative_signals.csv', self.generate_enhanced_signals_csv),
        ]

        files = {}
        for filename, gen_func in generators:
            content = gen_func()
            filepath = output_path / filename
            filepath.write_text(content)
            files[filename] = str(filepath)

        logger.info(f"Generated {len(files)} context graph CSVs in {output_dir}")
        return files

    # ─── 1. Stakeholders ─────────────────────────────────────────────────

    def generate_stakeholders_csv(self) -> str:
        """Generate stakeholders.csv from arc cast definitions."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'account_id', 'stakeholder_name', 'title', 'role',
            'influence_score', 'email', 'engagement_frequency',
            'sentiment', 'department', 'is_active', 'source_platform',
            'first_observed_at'
        ])

        for account_id in self.account_ids:
            self._set_arc_context(account_id)
            cast = self.arc.get('cast', [])
            for member in cast:
                name = self._make_name(member.get('title', 'Contact'))
                # Use the final sentiment from the arc
                sentiment_arc = member.get('sentiment_arc', [0.5])
                final_sentiment = sentiment_arc[-1] if sentiment_arc else 0.5
                sentiment_label = 'positive' if final_sentiment > 0.3 else ('negative' if final_sentiment < -0.3 else 'neutral')

                # Determine earliest phase the stakeholder appears in
                appears_in = member.get('appears_in_phase', [0])
                earliest_phase = min(appears_in) if appears_in else 0
                first_week = self.phase_starts[earliest_phase] if earliest_phase < len(self.phase_starts) else 1
                first_observed = self._week_to_date(max(first_week, 1))

                writer.writerow([
                    account_id,
                    name,
                    member.get('title', 'Unknown'),
                    member.get('role', 'end_user'),
                    round(member.get('influence_score', 0.5), 2),
                    self._make_email(name),
                    member.get('engagement_frequency', 'monthly'),
                    sentiment_label,
                    random.choice(DEPARTMENTS),
                    'true',
                    'csv_import',
                    first_observed.strftime('%Y-%m-%d'),
                ])

        return output.getvalue()

    # ─── 2. Engagement Events ────────────────────────────────────────────

    def generate_engagement_events_csv(self) -> str:
        """Generate engagement_events.csv from arc plot points."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'account_id', 'event_date', 'event_type', 'description',
            'stakeholder_name', 'sentiment_shift', 'channel',
            'duration_minutes', 'outcome', 'source_platform'
        ])

        channels = ['video_call', 'in_person', 'email', 'slack', 'phone']

        for account_id in self.account_ids:
            self._set_arc_context(account_id)
            cast = self.arc.get('cast', [])
            for phase in self.arc.get('phases', []):
                phase_id = phase.get('phase_id', 0)
                phase_start = self.phase_starts[phase_id] if phase_id < len(self.phase_starts) else 0

                for pp in phase.get('plot_points', []):
                    abs_week = phase_start + pp.get('week_offset', 0)
                    event_date = self._week_to_date(abs_week)

                    # Pick a stakeholder from cast that appears in this phase
                    stakeholder_name = ''
                    for member in cast:
                        if phase_id in member.get('appears_in_phase', []):
                            stakeholder_name = member.get('title', '')
                            break

                    writer.writerow([
                        account_id,
                        event_date.strftime('%Y-%m-%d'),
                        pp.get('event_type', 'meeting'),
                        pp.get('description', ''),
                        stakeholder_name,
                        pp.get('sentiment_shift', 0),
                        random.choice(channels),
                        random.choice([30, 45, 60, 90]),
                        '',  # outcome filled later from outcomes.csv
                        'csv_import',
                    ])

        return output.getvalue()

    # ─── 3. Account Business Profiles ────────────────────────────────────

    def generate_account_business_profiles_csv(self) -> str:
        """Generate account_business_profiles.csv with business context."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'account_id', 'arr', 'industry', 'employee_count',
            'fiscal_year_end', 'tech_stack', 'cloud_provider',
            'competitive_landscape', 'strategic_initiatives', 'budget_cycle',
            'profile_date'
        ])

        industries = ['Technology', 'Financial Services', 'Healthcare',
                      'Manufacturing', 'Retail', 'Energy', 'Media']

        for account_id in self.account_ids:
            self._set_arc_context(account_id)
            rn = self.arc.get('revenue_narrative', {})
            arr_start = rn.get('arr_start', 2000000)
            # Vary ARR slightly per account
            arr = round(arr_start * random.uniform(0.7, 1.3), 2)

            # Profile date = arc start (week 1)
            profile_date = self._week_to_date(1)

            writer.writerow([
                account_id,
                arr,
                random.choice(industries),
                random.choice([500, 1000, 2500, 5000, 10000, 25000]),
                random.choice(['December', 'March', 'June', 'September']),
                random.choice(TECH_STACKS),
                random.choice(CLOUD_PROVIDERS),
                random.choice(['Dell PowerEdge', 'HPE ProLiant', 'Lenovo ThinkSystem', 'None identified']),
                json.dumps(random.sample(STRATEGIC_INITIATIVES, k=random.randint(2, 4))),
                random.choice(['Q1 (Jan-Mar)', 'Q2 (Apr-Jun)', 'Q3 (Jul-Sep)', 'Q4 (Oct-Dec)']),
                profile_date.strftime('%Y-%m-%d'),
            ])

        return output.getvalue()

    # ─── 4. Decisions ────────────────────────────────────────────────────

    def generate_decisions_csv(self) -> str:
        """Generate decisions.csv from arc decision points."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'account_id', 'decision_id', 'decision_date', 'title', 'decision_maker_role',
            'chosen_option', 'options_considered', 'revenue_impact',
            'risk_level', 'evidence_refs', 'outcome_description', 'confidence'
        ])

        for account_id in self.account_ids:
            self._set_arc_context(account_id)
            arc_arr_start = self.arc.get('revenue_narrative', {}).get('arr_start', 2400000)
            account_arr = self._get_account_arr(account_id)
            arr_scale = account_arr / arc_arr_start if arc_arr_start > 0 else 1.0

            for decision in self.arc.get('decisions', []):
                week = decision.get('week', 1)
                decision_date = self._week_to_date(week)

                options = decision.get('options', [])
                chosen_idx = decision.get('chosen_option', 0)
                chosen = options[chosen_idx]['option'] if chosen_idx < len(options) else ''

                # Determine risk level from options
                risk = options[chosen_idx].get('risk_level', 'medium') if chosen_idx < len(options) else 'medium'

                # Scale revenue to account ARR
                revenue_impact = decision.get('revenue_impact', 0) * arr_scale

                writer.writerow([
                    account_id,
                    decision.get('decision_id', ''),
                    decision_date.strftime('%Y-%m-%d'),
                    decision.get('title', ''),
                    decision.get('decision_maker_role', ''),
                    chosen,
                    json.dumps([o['option'] for o in options]),
                    round(revenue_impact, 2),
                    risk,
                    json.dumps(decision.get('evidence_refs', [])),
                    decision.get('outcome_description', ''),
                    round(random.uniform(0.7, 0.95), 2),
                ])

        return output.getvalue()

    # ─── 5. Outcomes ─────────────────────────────────────────────────────

    def generate_outcomes_csv(self) -> str:
        """Generate outcomes.csv from arc outcome definitions."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'account_id', 'outcome_id', 'outcome_date', 'title', 'outcome_type',
            'revenue_value', 'evidence', 'confidence',
            'related_decision_id', 'source_platform'
        ])

        for account_id in self.account_ids:
            self._set_arc_context(account_id)
            arc_arr_start = self.arc.get('revenue_narrative', {}).get('arr_start', 2400000)
            # Scale revenue proportional to account ARR vs arc base ARR
            account_arr = self._get_account_arr(account_id)
            arr_scale = account_arr / arc_arr_start if arc_arr_start > 0 else 1.0

            for outcome in self.arc.get('outcomes', []):
                week = outcome.get('realized_week', self.total_weeks)
                outcome_date = self._week_to_date(week)

                # Scale revenue to account ARR with slight variance
                revenue = outcome.get('revenue_value', 0) * arr_scale * random.uniform(0.85, 1.15)

                writer.writerow([
                    account_id,
                    outcome.get('outcome_id', ''),
                    outcome_date.strftime('%Y-%m-%d'),
                    outcome.get('title', ''),
                    outcome.get('outcome_type', 'retention'),
                    round(revenue, 2),
                    outcome.get('evidence', ''),
                    outcome.get('confidence', 0.8),
                    '',  # related_decision_id linked during ingestion
                    'csv_import',
                ])

        return output.getvalue()

    # ─── 6. Signal Edges ─────────────────────────────────────────────────

    def generate_signal_edges_csv(self) -> str:
        """Generate signal_edges.csv from arc causal chains and edges_template.

        In per-account mode, aggregates edges from all unique arcs in use.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'from_signal_ref', 'to_signal_ref', 'edge_type', 'weight',
            'confidence', 'lag_days', 'revenue_impact', 'evidence',
            'source_platform', 'created_by'
        ])

        seen_edges = set()

        for arc_id, arc in self._unique_arcs().items():
            # From causal chains
            for chain in arc.get('causal_chains', []):
                chain_revenue = chain.get('revenue_impact', 0)
                for link in chain.get('links', []):
                    edge_key = (link.get('from_event', ''), link.get('to_event', ''),
                                link.get('edge_type', 'CORRELATES_WITH'))
                    if edge_key in seen_edges:
                        continue
                    seen_edges.add(edge_key)

                    lag_weeks = link.get('lag_weeks', 0)
                    writer.writerow([
                        link.get('from_event', ''),
                        link.get('to_event', ''),
                        link.get('edge_type', 'CORRELATES_WITH'),
                        round(link.get('confidence', 0.8), 2),
                        round(link.get('confidence', 0.8), 2),
                        lag_weeks * 7,  # Convert weeks to days
                        chain_revenue,
                        f"Causal chain: {chain.get('name', '')}",
                        'csv_import',
                        'story_arc_generator',
                    ])

            # From edges_template
            for edge in arc.get('edges_template', []):
                edge_key = (edge.get('from_ref', ''), edge.get('to_ref', ''),
                            edge.get('edge_type', 'CORRELATES_WITH'))
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)

                props = edge.get('properties', {})
                writer.writerow([
                    edge.get('from_ref', ''),
                    edge.get('to_ref', ''),
                    edge.get('edge_type', 'CORRELATES_WITH'),
                    round(edge.get('weight', 0.8), 2),
                    round(props.get('confidence', 0.8), 2),
                    0,
                    props.get('revenue_impact', 0),
                    json.dumps(props) if props else '',
                    'csv_import',
                    'story_arc_generator',
                ])

        return output.getvalue()

    # ─── 7. Decision Evidence ────────────────────────────────────────────

    def generate_decision_evidence_csv(self) -> str:
        """Generate decision_evidence.csv linking decisions to supporting signals/KPIs.

        In per-account mode, aggregates evidence from all unique arcs.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'decision_ref', 'evidence_type', 'evidence_description',
            'kpi_code', 'kpi_value', 'signal_ref', 'timestamp', 'confidence'
        ])

        seen_decisions = set()

        for arc_id, arc in self._unique_arcs().items():
            # Use this arc's timing
            phase_starts = self._arc_phase_starts.get(arc_id, self.phase_starts)
            base_date = self._arc_base_dates.get(arc_id, self.base_date)

            for decision in arc.get('decisions', []):
                decision_id = decision.get('decision_id', '')
                if decision_id in seen_decisions:
                    continue
                seen_decisions.add(decision_id)

                week = decision.get('week', 1)
                evidence_date = base_date + timedelta(weeks=week - 1, days=random.randint(0, 4))

                # Generate evidence from evidence_refs
                for ref in decision.get('evidence_refs', []):
                    # Determine evidence type from ref pattern
                    if 'kpi' in ref.lower() or 'gpu' in ref.lower() or 'utilization' in ref.lower():
                        evidence_type = 'kpi_metric'
                    elif 'signal' in ref.lower() or 'alert' in ref.lower():
                        evidence_type = 'signal'
                    else:
                        evidence_type = 'observation'

                    writer.writerow([
                        decision_id,
                        evidence_type,
                        ref,
                        '',  # kpi_code filled if evidence_type is kpi_metric
                        '',
                        '',
                        evidence_date.strftime('%Y-%m-%d'),
                        round(random.uniform(0.7, 0.95), 2),
                    ])

                # Also generate KPI-based evidence from the phase's plot points
                phase_id = decision.get('phase_id', 0)
                if phase_id < len(arc.get('phases', [])):
                    phase = arc['phases'][phase_id]
                    for pp in phase.get('plot_points', []):
                        for impact in pp.get('kpi_impacts', []):
                            writer.writerow([
                                decision_id,
                                'kpi_metric',
                                f"{impact['kpi_code']} {impact['direction']} ({impact['magnitude']})",
                                impact['kpi_code'],
                                '',  # actual value generated by regular KPI generator
                                '',
                                evidence_date.strftime('%Y-%m-%d'),
                                round(random.uniform(0.75, 0.95), 2),
                            ])

        return output.getvalue()

    # ─── 8. Industry Benchmarks ──────────────────────────────────────────

    def generate_industry_benchmarks_csv(self) -> str:
        """Generate industry_benchmarks.csv from arc benchmark data.

        In per-account mode, aggregates benchmarks from all unique arcs,
        deduplicating by kpi_code.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'kpi_code', 'benchmark_source', 'industry_p50',
            'industry_p25', 'industry_p75', 'account_percentile',
            'sample_size', 'benchmark_date'
        ])

        seen_kpis = set()

        for arc_id, arc in self._unique_arcs().items():
            for bench in arc.get('industry_benchmarks', []):
                kpi_code = bench.get('kpi_code', '')
                if kpi_code in seen_kpis:
                    continue
                seen_kpis.add(kpi_code)

                writer.writerow([
                    kpi_code,
                    bench.get('benchmark_source', ''),
                    bench.get('industry_p50', 0),
                    bench.get('industry_p25', 0),
                    bench.get('industry_p75', 0),
                    bench.get('account_percentile', 50),
                    random.choice([150, 250, 500, 1000]),
                    datetime.now().strftime('%Y-%m-%d'),
                ])

        return output.getvalue()

    # ─── 9. Enhanced Qualitative Signals ─────────────────────────────────

    def generate_enhanced_signals_csv(self) -> str:
        """Generate enhanced_qualitative_signals.csv from arc plot points.

        This is the context-graph-enriched version of qualitative_signals.csv.
        Each signal carries stakeholder, causal chain, and revenue impact metadata.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'account_id', 'signal_ref', 'signal_date', 'signal_type', 'content', 'sentiment',
            'sentiment_score', 'stakeholder_name', 'stakeholder_title',
            'causal_chain_ref', 'revenue_impact', 'confidence', 'source_platform'
        ])

        for account_id in self.account_ids:
            self._set_arc_context(account_id)
            cast = self.arc.get('cast', [])
            chains = self.arc.get('causal_chains', [])
            arc_arr_start = self.arc.get('revenue_narrative', {}).get('arr_start', 2400000)
            account_arr = self._get_account_arr(account_id)
            arr_scale = account_arr / arc_arr_start if arc_arr_start > 0 else 1.0

            for phase in self.arc.get('phases', []):
                phase_id = phase.get('phase_id', 0)
                phase_start = self.phase_starts[phase_id] if phase_id < len(self.phase_starts) else 0

                for pp in phase.get('plot_points', []):
                    abs_week = phase_start + pp.get('week_offset', 0)
                    signal_date = self._week_to_date(abs_week)
                    signal_ref = f"phase{phase_id}:w{pp.get('week_offset', 0)}"

                    sentiment_shift = pp.get('sentiment_shift', 0)
                    if sentiment_shift > 0.2:
                        sentiment = 'positive'
                    elif sentiment_shift < -0.2:
                        sentiment = 'negative'
                    else:
                        sentiment = 'neutral'

                    # Find relevant stakeholder
                    stakeholder_name = ''
                    stakeholder_title = ''
                    for member in cast:
                        if phase_id in member.get('appears_in_phase', []):
                            stakeholder_name = member.get('title', '')
                            stakeholder_title = member.get('role', '')
                            break

                    # Find relevant causal chain
                    chain_ref = ''
                    for chain in chains:
                        for link in chain.get('links', []):
                            desc = pp.get('description', '').lower()
                            from_evt = link.get('from_event', '').lower()
                            if desc and from_evt and (desc[:20] in from_evt or from_evt[:20] in desc):
                                chain_ref = chain.get('chain_id', '')
                                break
                        if chain_ref:
                            break

                    # Scale revenue to account ARR
                    revenue_impact = pp.get('revenue_impact', 0) * arr_scale

                    writer.writerow([
                        account_id,
                        signal_ref,
                        signal_date.strftime('%Y-%m-%d'),
                        pp.get('event_type', 'signal'),
                        pp.get('description', ''),
                        sentiment,
                        round(sentiment_shift, 2),
                        stakeholder_name,
                        stakeholder_title,
                        chain_ref,
                        round(revenue_impact, 2),
                        round(random.uniform(0.7, 0.95), 2),
                        'csv_import',
                    ])

        return output.getvalue()


def main():
    """CLI entry point."""
    import argparse

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    parser = argparse.ArgumentParser(
        description='Generate context graph 9-CSV data from story arc manifests'
    )
    parser.add_argument('--customer-id', type=int, default=9,
                        help='Customer ID (default: 9)')
    parser.add_argument('--num-accounts', type=int, default=10,
                        help='Number of accounts (default: 10)')
    parser.add_argument('--arc', type=str, default='arc_expansion_champion',
                        help='Story arc ID (default: arc_expansion_champion)')
    parser.add_argument('--all-arcs', action='store_true',
                        help='Generate data for ALL 8 story arcs')
    parser.add_argument('--health-aware', action='store_true',
                        help='Assign different arcs per account based on health scores')
    parser.add_argument('--health-scores', type=str, default=None,
                        help='JSON file with health scores: {"291001": 77.9, ...}')
    parser.add_argument('--output-dir', default=None,
                        help='Output directory (default: verticals/customer{id}-dc2_s/context_graph/)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility')
    parser.add_argument('--validate', action='store_true',
                        help='Run post-generation validation (requires DB access)')

    args = parser.parse_args()

    if args.health_aware:
        # ── Health-aware mode: per-account arc assignment ─────────────
        print(f"\nHealth-aware context graph generation for customer {args.customer_id}")
        print("=" * 60)

        # Load health scores
        health_scores = None
        if args.health_scores:
            with open(args.health_scores) as f:
                raw = json.load(f)
                health_scores = {int(k): float(v) for k, v in raw.items()}
            print(f"Loaded health scores from {args.health_scores}")
        else:
            # Try to query from DB via Flask app context
            try:
                from app_v3_minimal import app
                with app.app_context():
                    health_scores = _query_health_scores(args.customer_id, args.num_accounts)
                    if health_scores:
                        print(f"Queried {len(health_scores)} health scores from DB")
                    else:
                        print("WARNING: No health scores from DB, using defaults (at-risk)")
            except Exception as e:
                print(f"WARNING: Could not query DB ({e}), using defaults (at-risk)")

        # Build per-account arc map
        arc_map = build_health_arc_map(
            customer_id=args.customer_id,
            num_accounts=args.num_accounts,
            health_scores=health_scores,
            seed=args.seed,
        )

        # Print assignment table
        print(f"\nArc assignments ({len(arc_map)} accounts):")
        for acct_id in sorted(arc_map.keys()):
            health = (health_scores or {}).get(acct_id, 65.0)
            cls = classify_health(health)
            print(f"  {acct_id}: health={health:5.1f} ({cls:>8}) -> {arc_map[acct_id]}")

        # Output directory
        output_dir = args.output_dir or str(
            Path(__file__).parent.parent / 'verticals' /
            f'customer{args.customer_id}-dc2_s' / 'context_graph' / 'health_aware'
        )

        gen = ContextGraphGenerator(
            customer_id=args.customer_id,
            num_accounts=args.num_accounts,
            seed=args.seed,
            account_arc_map=arc_map,
        )
        files = gen.generate_all(output_dir)

        print(f"\nGenerated {len(files)} context graph CSV files:")
        for name, path in files.items():
            print(f"  {name}: {path}")

    elif args.all_arcs:
        arcs = load_all_arcs()
        print(f"\nGenerating context graph CSVs for {len(arcs)} story arcs...")

        for arc_id in sorted(arcs.keys()):
            if args.output_dir:
                output_dir = str(Path(args.output_dir) / arc_id)
            else:
                output_dir = str(
                    Path(__file__).parent.parent / 'verticals' /
                    f'customer{args.customer_id}-dc2_s' / 'context_graph' / arc_id
                )
            gen = ContextGraphGenerator(
                customer_id=args.customer_id,
                arc_id=arc_id,
                num_accounts=args.num_accounts,
                seed=args.seed,
            )
            files = gen.generate_all(output_dir)
            print(f"  {arc_id}: {len(files)} files -> {output_dir}")
    else:
        output_dir = args.output_dir or str(
            Path(__file__).parent.parent / 'verticals' /
            f'customer{args.customer_id}-dc2_s' / 'context_graph' / args.arc
        )
        gen = ContextGraphGenerator(
            customer_id=args.customer_id,
            arc_id=args.arc,
            num_accounts=args.num_accounts,
            seed=args.seed,
        )
        files = gen.generate_all(output_dir)

        print(f"\nGenerated {len(files)} context graph CSV files:")
        for name, path in files.items():
            print(f"  {name}: {path}")

    # Post-generation validation (requires data to be loaded into DB first)
    if args.validate:
        print("\n" + "=" * 60)
        print("Post-Generation Validation")
        print("=" * 60)
        print("NOTE: Validation requires context graph CSVs to be loaded")
        print("into the database first (via onboarding API process-data).")
        print(f"Run: python scripts/validate_context_graph.py {args.customer_id}")
        print("=" * 60)


if __name__ == '__main__':
    main()
