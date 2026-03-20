#!/usr/bin/env python3
"""
Scenario: Manifest-Driven Data Load

Reads a JSON manifest (e.g. manifests/novastar_dc2s.json) and generates
deterministic CSV data for accounts, KPI measurements, signals,
stakeholders, engagement events, profiles, products, and outcomes.

Unlike the random CSVGenerator, this produces data that matches a
curated narrative — specific account names, ARR values, health
trajectories, story arcs, and named stakeholders.

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
# ManifestCSVGenerator — the core engine
# ═══════════════════════════════════════════════════════════════════════

class ManifestCSVGenerator:
    """
    Generates all CSV files from a curated manifest JSON.

    The manifest specifies exact account names, ARR, health targets,
    trajectories, stakeholders, and signals — producing deterministic
    data suitable for gold-reference demos.
    """

    def __init__(self, manifest_path: str, customer_id: int = 0, seed: int = 42):
        """
        Args:
            manifest_path: Path to the manifest JSON file
            customer_id: Assigned customer_id (overrides manifest if >0)
            seed: Random seed for reproducible noise
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
        random.seed(seed)

        # Parse time range
        self.start_date = datetime.strptime(self.time_range['start'], '%Y-%m-%d')
        self.end_date = datetime.strptime(self.time_range['end'], '%Y-%m-%d')
        self.frequency = self.time_range.get('frequency', 'weekly')
        self.data_points = self.time_range.get('data_points_per_kpi', 26)

        # Build measurement dates
        self.dates = self._build_dates()

        # Load KPI catalog metadata
        self.kpi_catalog = {}
        if _catalog_available:
            full_catalog = get_kpis()
            for code in self.kpi_codes:
                if code in full_catalog:
                    self.kpi_catalog[code] = full_catalog[code]

        # Account ID base: customer_id * 1000 + 1
        self.account_id_base = (self.customer_id or 1) * 1000 + 1

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

        The scoring engine maps KPI values → 0-100 scores using ranges:
          - In "healthy" range → scores 70-100
          - In "risk" range → scores 50-69
          - In "critical" range → scores 0-49

        We interpolate within the appropriate range band to produce a value
        that the engine will score close to target_health.
        """
        healthy = ranges.get('healthy', {})
        risk = ranges.get('risk', {})
        critical = ranges.get('critical', {})

        if not healthy or not risk:
            # No ranges — fall back to linear mapping but more generous
            # Use power curve: health=90 → 95% of target, health=50 → 70%, health=30 → 50%
            factor = 0.4 + 0.6 * (target_health / 100.0) ** 0.7
            if not higher_is_better:
                factor = 1.0 / factor
            return target_val * factor

        if higher_is_better:
            # healthy: [h_min, h_max], risk: [r_min, r_max], critical: [c_min, c_max]
            h_min = healthy.get('min', target_val * 0.8)
            h_max = healthy.get('max', target_val * 1.2)
            r_min = risk.get('min', target_val * 0.5)
            r_max = risk.get('max', h_min)
            c_min = critical.get('min', 0)
            c_max = critical.get('max', r_min)

            if target_health >= 70:
                # Healthy band: score 70-100 maps to [h_min, h_max]
                t = (target_health - 70) / 30.0
                return h_min + t * (h_max - h_min)
            elif target_health >= 50:
                # Risk band: score 50-69 maps to [r_min, r_max]
                t = (target_health - 50) / 20.0
                return r_min + t * (r_max - r_min)
            else:
                # Critical band: score 0-49 maps to [c_min, c_max]
                t = target_health / 50.0
                return c_min + t * (c_max - c_min)
        else:
            # Lower-is-better: healthy has LOW values, critical has HIGH values
            h_min = healthy.get('min', target_val * 0.5)
            h_max = healthy.get('max', target_val)
            r_min = risk.get('min', h_max)
            r_max = risk.get('max', target_val * 1.5)
            c_min = critical.get('min', r_max)
            c_max = critical.get('max', target_val * 3.0)

            if target_health >= 70:
                # Healthy: lower values are better
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
    ) -> List[float]:
        """
        Generate a time-series of KPI values for one account+KPI.

        Uses the account's target_health (0-100) to set the baseline,
        then applies trajectory (stable, declining, improving, etc.)
        with realistic noise.
        """
        n = len(self.dates)

        # Get KPI metadata
        meta = self.kpi_catalog.get(kpi_code, {})
        higher_is_better = meta.get('higher_is_better', True)
        target_val = meta.get('target', {})
        if isinstance(target_val, dict):
            target_val = target_val.get('value', 85.0)
        elif target_val is None:
            target_val = 85.0

        # Base value: use KPI ranges to reverse-engineer a value that will
        # produce roughly the desired health score through the scoring engine.
        # The scoring engine maps: healthy range → 70-100, risk → 50-69, critical → 0-49
        ranges = meta.get('ranges', {})
        base = self._health_to_kpi_value(
            target_health, target_val, ranges, higher_is_better
        )

        values = []
        for i in range(n):
            t = i / max(n - 1, 1)  # 0.0 to 1.0

            # Apply trajectory
            if trajectory == 'declining':
                start_month = decline_start_month or 3
                start_idx = int(start_month * (n / 6))  # convert months to index
                if i >= start_idx:
                    decay = (i - start_idx) / max(n - start_idx, 1)
                    if higher_is_better:
                        modifier = 1.0 - 0.35 * decay  # drop up to 35%
                    else:
                        modifier = 1.0 + 0.5 * decay  # increase (worse) up to 50%
                else:
                    modifier = 1.0
            elif trajectory == 'slow_decline':
                modifier = 1.0 - 0.15 * t if higher_is_better else 1.0 + 0.15 * t
            elif trajectory == 'improving':
                modifier = 1.0 + 0.15 * t if higher_is_better else 1.0 - 0.15 * t
            elif trajectory == 'recovering':
                # V-shape: decline first half, recover second half
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

            # Apply noise (±3%)
            noise = 1.0 + random.gauss(0, 0.03)
            val = base * modifier * noise

            # Clamp to reasonable bounds
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
            critical = ranges.get('critical', {})

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

        # Fallback: normalize to 0-100
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

            # Tier from ARR
            if arr >= 5_000_000:
                tier = 'Enterprise'
            elif arr >= 1_000_000:
                tier = 'Mid-Market'
            else:
                tier = 'SMB'

            # Classification → status
            cls = acct.get('classification', 'healthy')
            status = 'at_risk' if cls in ('critical', 'at_risk') else 'active'

            # Champion = first stakeholder with champion/executive_sponsor role
            champion = None
            exec_sponsor = None
            for sh in acct.get('stakeholders', []):
                role = sh.get('role', '')
                if role in ('champion', 'economic_buyer') and not champion:
                    champion = sh
                if role == 'executive_sponsor' and not exec_sponsor:
                    exec_sponsor = sh

            champion = champion or acct.get('stakeholders', [{}])[0] if acct.get('stakeholders') else {}
            exec_sponsor_name = exec_sponsor['name'] if exec_sponsor else ''

            # Dates
            renewal = acct.get('renewal_date', '2026-09-01')
            renewal_dt = datetime.strptime(renewal, '%Y-%m-%d')
            contract_start = (renewal_dt - timedelta(days=365)).strftime('%Y-%m-%d')

            # CSM names
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

                # Generate full time series
                series = self._generate_kpi_series(
                    target_health, trajectory, decline_start, kpi_code
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
        """Generate enhanced_qualitative_signals.csv from manifest key_signals + auto-generated."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'signal_id', 'source_account_id', 'signal_date', 'signal_type',
            'content', 'sentiment', 'sentiment_score',
            'arc_id', 'story_phase', 'linked_node_id',
        ])

        counter = 0
        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            arc = acct.get('story_arc', '')

            # Manifest-defined signals (curated)
            for sig in acct.get('key_signals', []):
                counter += 1
                sentiment = sig.get('sentiment', 'neutral')
                score_map = {
                    'very_positive': 0.9, 'positive': 0.7,
                    'neutral': 0.1,
                    'negative': -0.6, 'very_negative': -0.9,
                }
                w.writerow([
                    f'sig_{aid}_{counter}',
                    aid,
                    sig.get('date', '2026-01-01'),
                    sig.get('type', 'observation'),
                    sig.get('content', ''),
                    sentiment.replace('very_', ''),  # normalize to positive/negative/neutral
                    score_map.get(sentiment, 0.0),
                    arc,
                    '',  # story_phase
                    '',  # linked_node_id
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
                    w.writerow([
                        f'sig_{aid}_{counter}',
                        aid,
                        date.strftime('%Y-%m-%d'),
                        random.choice(['meeting', 'health_check', 'observation', 'customer_feedback']),
                        random.choice(templates),
                        sentiment,
                        round(score + random.gauss(0, 0.1), 2),
                        arc,
                        '',
                        '',
                    ])

        return out.getvalue()

    def generate_products_csv(self) -> str:
        """Generate products.csv — 1-3 products per account."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'product_name', 'product_category',
            'quantity', 'unit_price', 'deployment_date', 'status',
        ])

        products = [
            ('GPU Compute Cluster', 'Compute'),
            ('AI Training Platform', 'AI/ML'),
            ('Inference Engine', 'AI/ML'),
            ('Data Lake Storage', 'Storage'),
            ('Network Fabric Controller', 'Networking'),
            ('Cooling Management System', 'Facilities'),
            ('Power Distribution Unit', 'Facilities'),
            ('Monitoring Dashboard', 'Observability'),
        ]

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            random.seed(self.seed + idx)  # deterministic per account
            n_products = random.randint(1, 3)
            selected = random.sample(products, min(n_products, len(products)))

            for prod_name, category in selected:
                deploy_date = self.start_date - timedelta(days=random.randint(30, 365))
                w.writerow([
                    aid,
                    prod_name,
                    category,
                    random.randint(5, 200),
                    round(random.uniform(5000, 100000), 2),
                    deploy_date.strftime('%Y-%m-%d'),
                    'active',
                ])

        random.seed(self.seed)  # reset
        return out.getvalue()

    def generate_stakeholders_csv(self) -> str:
        """Generate stakeholders.csv from manifest stakeholder data."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'stakeholder_name', 'role', 'title',
            'department', 'email', 'influence_score', 'sentiment',
            'engagement_frequency', 'last_contact_date',
        ])

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            domain = acct['name'].lower().replace(' ', '') + '.com'

            for sh in acct.get('stakeholders', []):
                email = sh['name'].lower().replace(' ', '.') + '@' + domain
                # Last contact based on engagement frequency
                freq = sh.get('engagement_frequency', 'monthly')
                if freq in ('none', 'none_recent'):
                    last_contact = (self.end_date - timedelta(days=random.randint(90, 180))).strftime('%Y-%m-%d')
                elif freq == 'daily':
                    last_contact = (self.end_date - timedelta(days=random.randint(0, 3))).strftime('%Y-%m-%d')
                elif freq == 'weekly':
                    last_contact = (self.end_date - timedelta(days=random.randint(0, 10))).strftime('%Y-%m-%d')
                elif freq == 'biweekly':
                    last_contact = (self.end_date - timedelta(days=random.randint(0, 18))).strftime('%Y-%m-%d')
                elif freq == 'quarterly':
                    last_contact = (self.end_date - timedelta(days=random.randint(30, 95))).strftime('%Y-%m-%d')
                else:  # monthly
                    last_contact = (self.end_date - timedelta(days=random.randint(0, 35))).strftime('%Y-%m-%d')

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
        """Generate engagement_events.csv — meetings, QBRs, calls per account."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'event_date', 'event_type', 'title',
            'participants', 'outcome', 'sentiment', 'notes',
        ])

        event_types = ['QBR', 'check_in', 'technical_review', 'executive_briefing',
                       'support_escalation', 'onboarding_session', 'renewal_discussion']

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            cls = acct.get('classification', 'healthy')
            stakeholders = acct.get('stakeholders', [])
            participant_names = [s['name'] for s in stakeholders[:3]]

            # Number of events based on health: critical=more escalation, healthy=regular
            n_events = {'critical': 10, 'at_risk': 8, 'healthy': 6}.get(cls, 6)

            for i in range(n_events):
                event_date = self.start_date + timedelta(
                    days=int((self.end_date - self.start_date).days * i / max(n_events - 1, 1))
                )

                if cls == 'critical':
                    etype = random.choice(['support_escalation', 'check_in', 'executive_briefing', 'check_in'])
                    sentiment = random.choice(['negative', 'neutral', 'negative'])
                    outcome = random.choice(['action_items_assigned', 'escalated', 'follow_up_needed', 'partially_resolved'])
                elif cls == 'at_risk':
                    etype = random.choice(['check_in', 'QBR', 'technical_review', 'renewal_discussion'])
                    sentiment = random.choice(['neutral', 'negative', 'neutral', 'positive'])
                    outcome = random.choice(['follow_up_needed', 'positive_engagement', 'action_items_assigned'])
                else:
                    etype = random.choice(['QBR', 'check_in', 'technical_review'])
                    sentiment = random.choice(['positive', 'neutral', 'positive'])
                    outcome = random.choice(['positive_engagement', 'expansion_discussed', 'renewal_confirmed'])

                participants = ', '.join(random.sample(participant_names, min(2, len(participant_names))))
                title = f"{etype.replace('_', ' ').title()} — {acct['name']}"

                w.writerow([
                    aid,
                    event_date.strftime('%Y-%m-%d'),
                    etype,
                    title,
                    participants,
                    outcome,
                    sentiment,
                    f"Engagement with {acct['name']}: {outcome.replace('_', ' ')}",
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
                acct['arr'] * random.uniform(5, 20),  # company revenue >> arr to us
                random.randint(2005, 2022),
                random.choice(cities),
                f'https://www.{domain}',
                acct.get('narrative', f'{acct["name"]} is a customer account.'),
            ])

        return out.getvalue()

    def generate_outcomes_csv(self) -> str:
        """Generate outcomes.csv — resolved/in-progress outcomes linked to story arcs."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([
            'source_account_id', 'outcome_date', 'outcome_type', 'title',
            'description', 'revenue_impact', 'status', 'linked_signal_id',
        ])

        counter = 0
        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            cls = acct.get('classification', 'healthy')
            arc = acct.get('story_arc', '')
            arr = acct['arr']

            if cls == 'critical':
                # At-risk revenue outcomes
                outcomes = [
                    ('revenue_at_risk', f'Churn risk — {acct["name"]}',
                     f'Account showing signs of churn. ARR at risk: ${arr:,.0f}',
                     -arr * 0.5, 'open'),
                    ('engagement_decline', f'Engagement decline — {acct["name"]}',
                     'Stakeholder engagement dropped significantly',
                     -arr * 0.1, 'in_progress'),
                ]
            elif cls == 'at_risk':
                outcomes = [
                    ('renewal_risk', f'Renewal uncertainty — {acct["name"]}',
                     'Renewal discussion stalled or delayed',
                     -arr * 0.2, 'in_progress'),
                ]
            else:
                outcomes = [
                    ('expansion_opportunity', f'Expansion potential — {acct["name"]}',
                     'Account showing expansion signals',
                     arr * 0.15, 'open'),
                ]

            for otype, title, desc, impact, status in outcomes:
                counter += 1
                outcome_date = (self.end_date - timedelta(days=random.randint(0, 60))).strftime('%Y-%m-%d')
                w.writerow([
                    aid,
                    outcome_date,
                    otype,
                    title,
                    desc,
                    round(impact, 2),
                    status,
                    f'sig_{aid}_1',  # link to first signal
                ])

        return out.getvalue()

    def get_upload_file_map(self) -> Dict[str, str]:
        """
        Generate all CSVs in memory and return {file_type: csv_content}.
        file_type keys match the onboarding API expectations.
        """
        return {
            'accounts': self.generate_accounts_csv(),
            'kpi_measurements': self.generate_kpi_measurements_csv(),
            'enhanced_signals': self.generate_signals_csv(),
            'products': self.generate_products_csv(),
            'stakeholders': self.generate_stakeholders_csv(),
            'engagement_events': self.generate_engagement_events_csv(),
            'account_business_profiles': self.generate_profiles_csv(),
            'outcomes': self.generate_outcomes_csv(),
        }


# ═══════════════════════════════════════════════════════════════════════
# Scenario class (for use with LoadDriver)
# ═══════════════════════════════════════════════════════════════════════

class ScenarioManifest(BaseScenario):
    """
    Manifest-driven data load scenario.

    Reads a manifest JSON, generates all CSVs, uploads them via
    the onboarding API, and triggers process-data.

    Required args:
        --manifest: Path to manifest JSON file
        --customer-id: Target customer ID (if loading into existing customer)
    """

    def run(self) -> Dict[str, Any]:
        self.start_timer()
        logger.info("=== Scenario: Manifest-Driven Load ===")

        api_calls = 0
        errors = []
        results = {}

        manifest_path = getattr(self.args, 'manifest', None)
        if not manifest_path:
            return self.failure("--manifest path required")

        manifest_path = Path(manifest_path)
        if not manifest_path.exists():
            return self.failure(f"Manifest not found: {manifest_path}")

        customer_id = getattr(self.args, 'customer_id', None) or \
                      getattr(self.client, 'customer_id', None)
        seed = getattr(self.args, 'seed', None) or 42

        results['manifest'] = str(manifest_path)
        results['customer_id'] = customer_id

        try:
            # Step 1: Parse manifest
            logger.info(f"  Step 1: Loading manifest: {manifest_path}")
            gen = ManifestCSVGenerator(
                manifest_path=str(manifest_path),
                customer_id=customer_id or 0,
                seed=seed,
            )
            results['customer_name'] = gen.customer_info['name']
            results['num_accounts'] = len(gen.accounts)
            results['num_kpis'] = len(gen.kpi_codes)
            results['time_range'] = gen.time_range
            logger.info(f"    {gen.customer_info['name']}: "
                        f"{len(gen.accounts)} accounts, {len(gen.kpi_codes)} KPIs, "
                        f"{gen.data_points} data points")

            # Step 2: Generate CSVs in memory
            logger.info("  Step 2: Generating CSVs from manifest")
            gen_start = time.time()
            file_map = gen.get_upload_file_map()
            gen_duration = time.time() - gen_start
            results['generation_duration_s'] = round(gen_duration, 2)
            results['files_generated'] = list(file_map.keys())
            logger.info(f"    Generated {len(file_map)} files in {gen_duration:.1f}s")

            # Step 3: Upload CSVs
            logger.info("  Step 3: Uploading CSVs to onboarding API")
            upload_start = time.time()
            upload_results = {}

            # File type → filename mapping for upload
            filename_map = {
                'accounts': 'accounts.csv',
                'kpi_measurements': 'kpi_measurements.csv',
                'enhanced_signals': 'enhanced_qualitative_signals.csv',
                'products': 'products.csv',
                'stakeholders': 'stakeholders.csv',
                'engagement_events': 'engagement_events.csv',
                'account_business_profiles': 'account_business_profiles.csv',
                'outcomes': 'outcomes.csv',
            }

            for file_type, csv_content in file_map.items():
                filename = filename_map.get(file_type, f'{file_type}.csv')
                resp = self.client.upload_csv(
                    customer_id=customer_id,
                    file_type=file_type,
                    csv_content=csv_content,
                    filename=filename,
                )
                api_calls += 1

                if resp and resp.get('status') == 'success':
                    upload_results[file_type] = 'success'
                    logger.info(f"    {file_type}: uploaded")
                else:
                    upload_results[file_type] = f"failed: {str(resp)[:80]}"
                    errors.append(f"Upload {file_type} failed")
                    logger.warning(f"    {file_type}: FAILED — {str(resp)[:80]}")

            upload_duration = time.time() - upload_start
            results['upload_duration_s'] = round(upload_duration, 2)
            results['upload_results'] = upload_results

            successes = sum(1 for v in upload_results.values() if v == 'success')
            logger.info(f"    Uploaded {successes}/{len(file_map)} files in {upload_duration:.1f}s")

            if successes == 0:
                return self.failure(
                    "All CSV uploads failed",
                    api_calls=api_calls, errors=errors, details=results,
                )

            # Step 4: Process data
            logger.info("  Step 4: Processing data (health scores + ingestion)")
            process_start = time.time()

            original_timeout = self.client.timeout
            self.client.timeout = 300
            process_resp = self.client.process_data(
                customer_id=customer_id,
                skip_wizard_b=True,
                skip_wizard_c=False,
                strict_kpi_ranges=False,
            )
            self.client.timeout = original_timeout
            api_calls += 1

            process_duration = time.time() - process_start
            results['process_duration_s'] = round(process_duration, 2)

            if process_resp and process_resp.get('status') in ('success', 'warning'):
                logger.info(f"    OK: Process-data completed in {process_duration:.1f}s")
                results['process_status'] = 'success'
            else:
                err = str(process_resp)[:150] if process_resp else "No response"
                logger.warning(f"    WARN: process-data: {err}")
                results['process_status'] = f"failed: {err}"
                errors.append(f"process-data: {err[:80]}")

        except Exception as e:
            logger.error(f"Manifest scenario error: {e}", exc_info=True)
            return self.failure(
                f"Manifest scenario failed: {str(e)}",
                api_calls=api_calls, errors=errors, details=results,
            )

        if errors:
            return self.success(
                f"Manifest loaded with {len(errors)} warnings: "
                f"{results.get('num_accounts', 0)} accounts, {successes} files",
                api_calls=api_calls, errors=errors, details=results,
            )

        return self.success(
            f"Manifest loaded: {gen.customer_info['name']} — "
            f"{results.get('num_accounts', 0)} accounts, "
            f"{len(gen.kpi_codes)} KPIs, {gen.data_points} data points",
            api_calls=api_calls, details=results,
        )
