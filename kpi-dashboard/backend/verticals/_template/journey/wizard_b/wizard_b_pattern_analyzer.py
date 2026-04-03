#!/usr/bin/env python3
"""
Wizard B - Pattern Analyzer (Phase 1)
=====================================

Analyzes journey data from Wizard A to extract pattern insights.

Supports two modes:
  1. **Database mode** (preferred): ``run_wizard_b(customer_id)`` reads from
     ``JourneyData`` table and writes to ``WizardLearning``/``WizardRun`` tables.
  2. **File mode** (legacy/CLI): ``main()`` reads/writes to filesystem.

Input: Wizard A generated journey data (DB or file)
Output: Pattern definitions, early warning rules, transition probabilities
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import warnings
warnings.filterwarnings('ignore')

# Try to import advanced libraries (optional)
try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from scipy.spatial.distance import euclidean
    from fastdtw import fastdtw
    ADVANCED_CLUSTERING = True
except ImportError:
    print("⚠️  Advanced clustering libraries not available. Using basic analysis.")
    ADVANCED_CLUSTERING = False


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class PatternProfile:
    """Statistical profile of a journey pattern"""
    pattern_type: str
    n_accounts: int
    avg_starting_health: float
    avg_ending_health: float
    health_change: float
    avg_lowest_health: float
    avg_highest_health: float
    avg_duration_weeks: float
    avg_total_events: float
    common_phases: List[str]
    phase_distribution: Dict[str, float]
    avg_csm_investment: float
    financial_impact: str
    early_warning_signals: List[Dict]
    success_factors: List[str]
    # ── NRR Intelligence (Step 1) ──
    avg_nrr_impact: float = 1.0           # avg NRR contribution (1.0 = flat, 0.87 = 13% contraction)
    total_arr_exposed: float = 0.0        # total ARR across accounts in this pattern
    avg_revenue_protected: float = 0.0    # avg $ protected per account
    avg_revenue_lost: float = 0.0         # avg $ lost per account
    avg_revenue_expanded: float = 0.0     # avg $ expanded per account
    intervention_success_rate: float = 0.0  # % of accounts where health improved post-intervention


@dataclass
class TransitionProbability:
    """Phase transition probability"""
    from_phase: str
    to_phase: str
    probability: float
    avg_weeks_between: float
    sample_size: int


@dataclass
class EarlyWarningRule:
    """Early warning detection rule"""
    rule_id: str
    description: str
    condition: str
    predicted_outcome: str
    lead_time_weeks: int
    confidence: float
    sample_size: int


# ============================================================================
# PATTERN ANALYZER
# ============================================================================

class PatternAnalyzer:
    """
    Analyzes journey patterns from Wizard A data.

    Supports two construction paths:
      * ``PatternAnalyzer(run_dir)`` — file-based (legacy CLI)
      * ``PatternAnalyzer.from_database(customer_id)`` — DB-based (preferred)
    """

    def __init__(self, wizard_run_dir: Optional[Path] = None):
        """
        Initialize analyzer.

        Args:
            wizard_run_dir: Path to wizard run output (optional, not needed for DB mode).
        """
        self.run_dir = Path(wizard_run_dir) if wizard_run_dir else None
        self.customer_id: Optional[int] = None
        self.journeys: List[Dict] = []
        self.kpis = pd.DataFrame()
        self.milestones: list = []

        # Outputs
        self.pattern_profiles: Dict[str, PatternProfile] = {}
        self.transition_matrix: Dict[str, TransitionProbability] = {}
        self.early_warning_rules: List[EarlyWarningRule] = []
        self.nrr_correlations: Dict[str, Dict] = {}  # pattern → NRR metrics
        self.portfolio_nrr_forecast: Optional[Dict] = None

        if self.run_dir:
            print(f"🔍 Pattern Analyzer initialized for: {self.run_dir.name}")

    # ------------------------------------------------------------------
    # DATABASE CONSTRUCTION (preferred)
    # ------------------------------------------------------------------

    @classmethod
    def from_database(cls, customer_id: int) -> 'PatternAnalyzer':
        """
        Create a PatternAnalyzer by loading journey data from the JourneyData table.

        Args:
            customer_id: The customer whose journey data to analyse.

        Returns:
            Populated ``PatternAnalyzer`` instance ready for ``analyze_patterns()``.

        Raises:
            ValueError: If no journey data exists for the customer.
        """
        from models import JourneyData  # deferred to avoid circular import

        rows = JourneyData.query.filter_by(customer_id=customer_id).all()
        if not rows:
            raise ValueError(
                f"No journey data found for customer_id={customer_id}. "
                "Run Wizard A (process-data) first."
            )

        analyzer = cls()
        analyzer.customer_id = customer_id
        for row in rows:
            journey = row.journey_json
            # Normalise the field name: DB may store 'pattern' while
            # analyzer code expects 'pattern_type'.
            if 'pattern_type' not in journey and 'pattern' in journey:
                journey['pattern_type'] = journey['pattern']
            analyzer.journeys.append(journey)

        print(f"🔍 Pattern Analyzer loaded {len(analyzer.journeys)} journeys "
              f"from DB for customer {customer_id}")
        return analyzer
    
    # ========================================================================
    # DATA LOADING
    # ========================================================================
    
    def load_data(self):
        """Load all journey data from the run directory"""
        
        print("📂 Loading journey data...")
        
        # Load journey JSON files
        journey_files = list(self.run_dir.glob('account_*_journey.json'))
        for journey_file in journey_files:
            with open(journey_file, 'r') as f:
                journey = json.load(f)
                self.journeys.append(journey)
        
        print(f"   ✅ Loaded {len(self.journeys)} journeys")
        
        # Load KPI data
        kpi_file = self.run_dir / 'all_accounts_kpis.csv'
        if kpi_file.exists():
            self.kpis = pd.read_csv(kpi_file)
            print(f"   ✅ Loaded {len(self.kpis)} KPI records")
        
        # Load milestones
        milestone_file = self.run_dir.parent.parent / 'processed/wizard' / self.run_dir.name / 'all_milestones.json'
        if milestone_file.exists():
            with open(milestone_file, 'r') as f:
                self.milestones = json.load(f)
            print(f"   ✅ Loaded {len(self.milestones)} milestones")
        
        return self
    
    # ========================================================================
    # FEATURE FLAG CHECK
    # ========================================================================

    def _is_nrr_intelligence_enabled(self) -> bool:
        """Check if 'nrr_intelligence' per-customer feature flag is enabled.

        Default: ON (enabled unless explicitly disabled via feature toggle).
        To disable: enable_features(customer_id, ['nrr_intelligence']) then
        set enabled=False via the admin API.
        """
        if not self.customer_id:
            return False
        try:
            from models import FeatureToggle as FTModel
            toggle = FTModel.query.filter_by(
                customer_id=self.customer_id,
                feature_name='nrr_intelligence',
            ).first()
            # Default ON: if no toggle row exists, feature is enabled
            return toggle.enabled if toggle else True
        except Exception:
            return True

    # ========================================================================
    # PATTERN PROFILING
    # ========================================================================

    def analyze_patterns(self, auto_save: bool = False):
        """
        Main analysis pipeline.

        Args:
            auto_save: If True, call ``save_results()`` to write files (legacy).
                       Default False — caller decides where to persist.
        """

        print("\n" + "="*70)
        print("🧙 WIZARD B - PATTERN ANALYSIS")
        print("="*70)

        # 1. Profile each pattern type
        print("\n1️⃣  Profiling pattern types...")
        self.profile_patterns()

        # 2. Analyze phase transitions
        print("\n2️⃣  Analyzing phase transitions...")
        self.analyze_transitions()

        # 3. Identify early warning signals
        print("\n3️⃣  Identifying early warning signals...")
        self.identify_early_warnings()

        # 4. Extract success factors
        print("\n4️⃣  Extracting success factors...")
        self.extract_success_factors()

        # 5. NRR correlation (requires DB context + feature flag)
        if self.customer_id is not None and self._is_nrr_intelligence_enabled():
            print("\n5️⃣  Correlating patterns to NRR impact...")
            self.correlate_nrr_impact()

            # 6. Portfolio NRR forecast
            print("\n6️⃣  Forecasting portfolio NRR...")
            self.forecast_portfolio_nrr()
        elif self.customer_id is None:
            print("\n5️⃣  Skipping NRR correlation (no customer_id — filesystem mode)")
        else:
            print("\n5️⃣  Skipping NRR correlation (nrr_intelligence feature not enabled)")

        # 7. Optionally save to filesystem (legacy CLI mode)
        if auto_save and self.run_dir:
            print("\n7️⃣  Generating outputs...")
            self.save_results()

        print("\n" + "="*70)
        print("✅ PATTERN ANALYSIS COMPLETE!")
        print("="*70 + "\n")

        return self
    
    def profile_patterns(self):
        """Create statistical profiles for each pattern type"""
        
        # Group journeys by pattern
        patterns = defaultdict(list)
        for journey in self.journeys:
            patterns[journey['pattern_type']].append(journey)
        
        # Analyze each pattern
        for pattern_type, pattern_journeys in patterns.items():
            print(f"\n   Analyzing {pattern_type} pattern ({len(pattern_journeys)} accounts)...")
            
            # Extract statistics (filter out None health values)
            _sh = [j['starting_health'] for j in pattern_journeys if j.get('starting_health') is not None]
            _eh = [j['ending_health'] for j in pattern_journeys if j.get('ending_health') is not None]
            _hc = [j['ending_health'] - j['starting_health'] for j in pattern_journeys
                   if j.get('ending_health') is not None and j.get('starting_health') is not None]
            _lh = [j['lowest_health'] for j in pattern_journeys if j.get('lowest_health') is not None]
            _hh = [j['highest_health'] for j in pattern_journeys if j.get('highest_health') is not None]
            profile = PatternProfile(
                pattern_type=pattern_type,
                n_accounts=len(pattern_journeys),
                avg_starting_health=np.mean(_sh) if _sh else 0.0,
                avg_ending_health=np.mean(_eh) if _eh else 0.0,
                health_change=np.mean(_hc) if _hc else 0.0,
                avg_lowest_health=np.mean(_lh) if _lh else 0.0,
                avg_highest_health=np.mean(_hh) if _hh else 0.0,
                avg_duration_weeks=np.mean([j['total_weeks'] for j in pattern_journeys]),
                avg_total_events=np.mean([j['summary']['total_events'] for j in pattern_journeys]),
                common_phases=self._extract_common_phases(pattern_journeys),
                phase_distribution=self._compute_phase_distribution(pattern_journeys),
                avg_csm_investment=np.mean([j['summary'].get('total_csm_investment', 0) for j in pattern_journeys]),
                financial_impact=pattern_journeys[0]['summary'].get('financial_impact', 'N/A'),
                early_warning_signals=[],  # Will fill in later
                success_factors=[]  # Will fill in later
            )
            
            self.pattern_profiles[pattern_type] = profile
            
            # Print summary
            print(f"      Health: {profile.avg_starting_health:.1f} → {profile.avg_ending_health:.1f} (Δ {profile.health_change:+.1f})")
            print(f"      Events: {profile.avg_total_events:.0f} avg")
            print(f"      CSM Investment: ${profile.avg_csm_investment:,.0f}")
            print(f"      Financial Impact: {profile.financial_impact}")
    
    def _extract_common_phases(self, journeys: List[Dict]) -> List[str]:
        """Extract most common phases across journeys"""
        all_phases = []
        for journey in journeys:
            phases = [event['phase'] for event in journey['events']]
            all_phases.extend(phases)
        
        # Get top 5 most common
        phase_counts = Counter(all_phases)
        return [phase for phase, _ in phase_counts.most_common(5)]
    
    def _compute_phase_distribution(self, journeys: List[Dict]) -> Dict[str, float]:
        """Compute percentage of time spent in each phase"""
        phase_weeks = defaultdict(int)
        total_weeks = 0
        
        for journey in journeys:
            for event in journey['events']:
                phase_weeks[event['phase']] += 1
                total_weeks += 1
        
        return {phase: (count / total_weeks) * 100 for phase, count in phase_weeks.items()}
    
    # ========================================================================
    # TRANSITION ANALYSIS
    # ========================================================================
    
    def analyze_transitions(self):
        """Analyze phase-to-phase transitions"""
        
        transitions = defaultdict(lambda: {'count': 0, 'total_weeks': 0})
        
        for journey in self.journeys:
            events = journey['events']
            for i in range(len(events) - 1):
                from_phase = events[i]['phase']
                to_phase = events[i+1]['phase']
                
                if from_phase != to_phase:
                    key = f"{from_phase}→{to_phase}"
                    transitions[key]['count'] += 1
                    transitions[key]['total_weeks'] += (events[i+1].get('week_number', events[i+1].get('week', 0)) - events[i].get('week_number', events[i].get('week', 0)))
        
        # Convert to probabilities
        phase_counts = defaultdict(int)
        for journey in self.journeys:
            for event in journey['events']:
                phase_counts[event['phase']] += 1
        
        self.transition_matrix = {}
        for transition, data in transitions.items():
            from_phase, to_phase = transition.split('→')
            probability = data['count'] / phase_counts[from_phase] if phase_counts[from_phase] > 0 else 0
            avg_weeks = data['total_weeks'] / data['count'] if data['count'] > 0 else 0
            
            self.transition_matrix[transition] = TransitionProbability(
                from_phase=from_phase,
                to_phase=to_phase,
                probability=probability,
                avg_weeks_between=avg_weeks,
                sample_size=data['count']
            )
            
            if data['count'] >= 5:  # Only show significant transitions
                print(f"   {transition}: {probability:.1%} probability (n={data['count']})")
    
    # ========================================================================
    # EARLY WARNING DETECTION
    # ========================================================================
    
    def identify_early_warnings(self):
        """Identify signals that predict negative outcomes"""
        
        # Analyze churned accounts
        churned = [j for j in self.journeys if j['pattern_type'] in ['ignored_churn', 'churn']]
        
        if len(churned) >= 3:
            print(f"\n   Analyzing {len(churned)} churned accounts...")
            
            # Rule 1: Health drops below 50 within first 20 weeks
            early_low_health = 0
            for journey in churned:
                for event in journey['events'][:20]:  # First 20 weeks
                    if event.get('health_score_after') is not None and event['health_score_after'] < 50:
                        early_low_health += 1
                        break
            
            if early_low_health >= 2:
                rule = EarlyWarningRule(
                    rule_id='EW001',
                    description='Health drops below 50 in first 20 weeks',
                    condition='health_score < 50 AND week_number <= 20',
                    predicted_outcome='churn',
                    lead_time_weeks=20,
                    confidence=early_low_health / len(churned),
                    sample_size=len(churned)
                )
                self.early_warning_rules.append(rule)
                print(f"   ✅ Rule EW001: {rule.description} (confidence: {rule.confidence:.1%})")
            
            # Rule 2: Sustained negative sentiment
            neg_sentiment = 0
            for journey in churned:
                neg_events = sum(1 for e in journey['events'] if e.get('sentiment_value') is not None and e['sentiment_value'] < 0)
                if neg_events / len(journey['events']) > 0.6:  # More than 60% negative
                    neg_sentiment += 1
            
            if neg_sentiment >= 2:
                rule = EarlyWarningRule(
                    rule_id='EW002',
                    description='Sustained negative sentiment (>60% of events)',
                    condition='negative_sentiment_ratio > 0.60',
                    predicted_outcome='churn',
                    lead_time_weeks=10,
                    confidence=neg_sentiment / len(churned),
                    sample_size=len(churned)
                )
                self.early_warning_rules.append(rule)
                print(f"   ✅ Rule EW002: {rule.description} (confidence: {rule.confidence:.1%})")
    
    # ========================================================================
    # SUCCESS FACTOR EXTRACTION
    # ========================================================================
    
    def extract_success_factors(self):
        """Extract factors that lead to successful outcomes"""
        
        # Analyze expansion accounts
        expanded = [j for j in self.journeys if j['pattern_type'] in ['proactive_growth', 'expansion']]
        
        if len(expanded) >= 3:
            print(f"\n   Analyzing {len(expanded)} expansion accounts...")
            
            success_factors = []
            
            # Factor 1: High CSM investment
            avg_investment = np.mean([j['summary'].get('total_csm_investment', 0) for j in expanded])
            success_factors.append(f"Average CSM investment: ${avg_investment:,.0f}")
            
            # Factor 2: Regular positive events
            avg_events = np.mean([j['summary']['total_events'] for j in expanded])
            success_factors.append(f"High engagement: {avg_events:.0f} events/account")
            
            # Factor 3: Early health score improvement
            early_improvers = sum(1 for j in expanded if len(j.get('events', [])) > 10 and j['events'][10].get('health_score_after') is not None and j.get('starting_health') is not None and j['events'][10]['health_score_after'] > j['starting_health'])
            if early_improvers >= 2:
                success_factors.append(f"Early health improvement: {early_improvers}/{len(expanded)} accounts")
            
            # Store in pattern profiles
            for pattern in ['proactive_growth', 'expansion']:
                if pattern in self.pattern_profiles:
                    self.pattern_profiles[pattern].success_factors = success_factors
            
            for factor in success_factors:
                print(f"   ✅ {factor}")
    
    # ========================================================================
    # NRR INTELLIGENCE (Steps 1-2)
    # ========================================================================

    def correlate_nrr_impact(self):
        """
        Step 1: Correlate each arc pattern with its NRR impact.

        For each pattern group, joins account ARR + context graph OUTCOME
        revenue to compute what NRR contribution that pattern produces.

        Populates:
          - self.nrr_correlations  (dict: pattern → NRR metrics)
          - PatternProfile NRR fields on each profile
        """
        from models import Account, ContextNode
        from extensions import db

        if not self.customer_id:
            return

        # Load account ARR map: account_id → revenue (float)
        accounts = Account.query.filter_by(customer_id=self.customer_id).all()
        arr_map = {a.account_id: float(a.revenue or 0) for a in accounts}

        # Load OUTCOME revenue per account: account_id → {protected, expansion, lost}
        outcome_nodes = (
            ContextNode.query
            .filter(
                ContextNode.customer_id == self.customer_id,
                ContextNode.node_type == 'OUTCOME',
                ContextNode.revenue_impact.isnot(None),
            )
            .all()
        )
        revenue_by_account: Dict[int, Dict[str, float]] = defaultdict(
            lambda: {'protected': 0.0, 'expansion': 0.0, 'lost': 0.0}
        )
        for n in outcome_nodes:
            impact = abs(float(n.revenue_impact or 0)) * float(n.confidence or 1.0)
            bucket = n.revenue_impact_type or 'expansion'
            if bucket in ('protected', 'expansion', 'lost'):
                revenue_by_account[n.account_id][bucket] += impact

        # Group journeys by pattern and compute NRR per group
        patterns = defaultdict(list)
        for journey in self.journeys:
            patterns[journey['pattern_type']].append(journey)

        for pattern_type, journeys in patterns.items():
            total_arr = 0.0
            total_protected = 0.0
            total_expansion = 0.0
            total_lost = 0.0
            intervention_successes = 0

            for j in journeys:
                aid = j.get('account_id', 0)
                arr = arr_map.get(aid, 0)
                total_arr += arr

                rev = revenue_by_account.get(aid, {})
                total_protected += rev.get('protected', 0)
                total_expansion += rev.get('expansion', 0)
                total_lost += rev.get('lost', 0)

                # Intervention success: health improved from lowest to ending
                if j.get('ending_health') is not None and j.get('lowest_health') is not None and j['ending_health'] > j['lowest_health'] + 5:
                    intervention_successes += 1

            n = len(journeys)
            # NRR = (retained ARR + expansion - contraction) / starting ARR
            if total_arr > 0:
                net_revenue = total_arr + total_expansion + total_protected - total_lost
                avg_nrr = net_revenue / total_arr
            else:
                avg_nrr = 1.0

            nrr_data = {
                'avg_nrr': round(avg_nrr, 4),
                'total_arr_exposed': round(total_arr, 2),
                'avg_revenue_protected': round(total_protected / n, 2) if n else 0,
                'avg_revenue_lost': round(total_lost / n, 2) if n else 0,
                'avg_revenue_expanded': round(total_expansion / n, 2) if n else 0,
                'intervention_success_rate': round(intervention_successes / n, 4) if n else 0,
                'n_accounts': n,
            }
            self.nrr_correlations[pattern_type] = nrr_data

            # Update PatternProfile with NRR fields
            if pattern_type in self.pattern_profiles:
                p = self.pattern_profiles[pattern_type]
                p.avg_nrr_impact = nrr_data['avg_nrr']
                p.total_arr_exposed = nrr_data['total_arr_exposed']
                p.avg_revenue_protected = nrr_data['avg_revenue_protected']
                p.avg_revenue_lost = nrr_data['avg_revenue_lost']
                p.avg_revenue_expanded = nrr_data['avg_revenue_expanded']
                p.intervention_success_rate = nrr_data['intervention_success_rate']

            # Log
            nrr_pct = f"{avg_nrr * 100:.1f}%"
            print(f"   {pattern_type:25s}  NRR={nrr_pct:>7s}  ARR=${total_arr:>12,.0f}  "
                  f"protected=${total_protected:>10,.0f}  lost=${total_lost:>10,.0f}  "
                  f"expansion=${total_expansion:>10,.0f}")

    # ------------------------------------------------------------------
    # Health extrapolation helper (used by forecast_portfolio_nrr)
    # ------------------------------------------------------------------

    @staticmethod
    def _extrapolate_health(health_now: float, slope_pts_per_month: float,
                            months: int, deceleration: float = 0.85) -> list:
        """Project health forward with diminishing slope.

        Returns list of dicts, one per month:
          [{'month': 1, 'projected_health': 72.3, 'threshold_crossing': None}, ...]
        Threshold crossings: 'healthy_to_at_risk', 'at_risk_to_critical', or None.
        """
        trajectory = []
        h = health_now
        prev_h = health_now
        for m in range(1, months + 1):
            effective_slope = slope_pts_per_month * (deceleration ** (m - 1))
            h = max(0.0, min(100.0, h + effective_slope))
            crossing = None
            if prev_h >= 70 and h < 70:
                crossing = 'healthy_to_at_risk'
            elif prev_h >= 50 and h < 50:
                crossing = 'at_risk_to_critical'
            elif prev_h < 50 and h >= 50:
                crossing = 'critical_to_at_risk'
            elif prev_h < 70 and h >= 70:
                crossing = 'at_risk_to_healthy'
            trajectory.append({
                'month': m,
                'projected_health': round(h, 1),
                'threshold_crossing': crossing,
            })
            prev_h = h
        return trajectory

    def forecast_portfolio_nrr(self, forecast_horizon_days: int = 90):
        """
        Step 2: Revenue-weighted NRR forecast for the entire portfolio.

        Uses the per-pattern NRR correlations (from Step 1) to project
        portfolio-level NRR, plus a what-if simulation showing the impact
        of executing playbooks on at-risk accounts.

        Enhanced with:
          - T+30/60/90 trajectory with health extrapolation
          - Renewal risk overlay
          - Per-intervention playbook cost and ROI

        Populates self.portfolio_nrr_forecast dict.
        """
        if not self.nrr_correlations:
            return

        from models import Account, HealthScore
        from datetime import datetime, timedelta, date

        accounts_db = Account.query.filter_by(customer_id=self.customer_id).all()
        arr_map = {a.account_id: float(a.revenue or 0) for a in accounts_db}
        arc_map = {a.account_id: a.arc_type for a in accounts_db}

        # Renewal dates from profile_metadata
        renewal_map = {}
        for a in accounts_db:
            meta = a.profile_metadata or {}
            rd_raw = meta.get('renewal_date') or meta.get('contract_renewal_date')
            if rd_raw:
                try:
                    renewal_map[a.account_id] = datetime.strptime(
                        str(rd_raw)[:10], '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass

        # Health slopes per account (simplified: use last 2 health scores)
        slope_map = {}
        for a in accounts_db:
            scores = (
                HealthScore.query
                .filter_by(account_id=a.account_id)
                .order_by(HealthScore.measurement_month.desc())
                .limit(3)
                .all()
            )
            if len(scores) >= 2:
                latest = float(scores[0].health_score or 0)
                prev = float(scores[1].health_score or 0)
                d0 = scores[1].measurement_month
                d1 = scores[0].measurement_month
                delta_days = (d1 - d0).days if hasattr(d1, 'year') else 30
                if delta_days > 0:
                    slope_map[a.account_id] = (latest - prev) / delta_days * 30
                else:
                    slope_map[a.account_id] = 0.0
            else:
                slope_map[a.account_id] = 0.0

        # Arc→playbook mapping
        arc_playbook_map = {}
        try:
            import json as _json
            from pathlib import Path
            _map_path = Path(__file__).parent.parent.parent.parent.parent / 'config' / 'arc_playbook_map.json'
            if _map_path.exists():
                with open(_map_path) as _f:
                    _raw = _json.load(_f)
                arc_playbook_map = {k: v for k, v in _raw.items() if not k.startswith('_')}
        except Exception:
            pass

        # Playbook cost lookup (lazy, cached)
        _cost_cache = {}
        def _get_playbook_cost(playbook_id: str, acct_arr: float) -> float:
            if playbook_id not in _cost_cache:
                try:
                    from playbook_cost_bridge import calculate_cost_bridge
                    bridge = calculate_cost_bridge(account_arr=acct_arr)
                    for pid, econ in bridge.playbooks.items():
                        _cost_cache[pid] = econ.manual_cost
                except Exception:
                    pass
            return _cost_cache.get(playbook_id, 0)

        # Build per-account forecast
        account_forecasts = []
        total_arr = 0.0
        weighted_nrr_sum = 0.0

        patterns = defaultdict(list)
        for j in self.journeys:
            patterns[j['pattern_type']].append(j)

        forecast_months = max(1, forecast_horizon_days // 30)

        for pattern_type, journeys in patterns.items():
            corr = self.nrr_correlations.get(pattern_type, {})
            pattern_nrr = corr.get('avg_nrr', 1.0)
            intervention_rate = corr.get('intervention_success_rate', 0.0)

            for j in journeys:
                aid = j.get('account_id', 0)
                arr = arr_map.get(aid, 0)
                total_arr += arr
                weighted_nrr_sum += arr * pattern_nrr

                health_end = j.get('ending_health', 0)
                slope = slope_map.get(aid, 0.0)
                health_traj = self._extrapolate_health(health_end, slope, forecast_months)

                # Renewal urgency
                renewal_date = renewal_map.get(aid)
                renewal_urgency = None
                days_to_renewal = None
                if renewal_date:
                    days_to_renewal = (renewal_date - date.today()).days
                    projected_at_renewal = health_traj[-1]['projected_health'] if health_traj else health_end
                    if days_to_renewal <= 30 and projected_at_renewal < 50:
                        renewal_urgency = 'urgent'
                    elif days_to_renewal <= 60 and projected_at_renewal < 60:
                        renewal_urgency = 'warning'
                    elif days_to_renewal <= 90 and slope < -1:
                        renewal_urgency = 'watch'

                account_forecasts.append({
                    'account_id': aid,
                    'account_name': j.get('account_name', f'Account {aid}'),
                    'arr': arr,
                    'pattern': pattern_type,
                    'current_nrr': pattern_nrr,
                    'health_start': j.get('starting_health', 0),
                    'health_end': health_end,
                    'health_slope_30d': round(slope, 2),
                    'health_trajectory': health_traj,
                    'intervention_success_rate': intervention_rate,
                    'renewal_date': str(renewal_date) if renewal_date else None,
                    'days_to_renewal': days_to_renewal,
                    'renewal_urgency': renewal_urgency,
                })

        # Current portfolio NRR (revenue-weighted)
        current_nrr = weighted_nrr_sum / total_arr if total_arr > 0 else 1.0

        # ── Trajectory: portfolio NRR at T+30/60/90 ────────────────────
        # Use health-to-churn mapping to project NRR at each horizon
        def _health_to_churn_90d(h, arc):
            """Map projected health to 90-day churn probability."""
            base = 0.12 if h < 50 else (0.054 if h < 70 else 0.013)
            arc_mult = {'crisis_recovery': 1.5, 'silent_churn': 1.3,
                        'competitive_displacement': 1.4, 'expansion_champion': 0.3
                        }.get(arc, 1.0)
            return min(base * arc_mult, 0.5)

        trajectory = {}
        for t_months in range(1, forecast_months + 1):
            t_key = f't{t_months * 30}'
            weighted_nrr_t = 0.0
            crossings = []
            for acct in account_forecasts:
                proj_h = acct['health_trajectory'][t_months - 1]['projected_health'] if t_months <= len(acct['health_trajectory']) else acct['health_end']
                churn = _health_to_churn_90d(proj_h, acct['pattern']) * (t_months / 3)
                acct_nrr_t = 1.0 - churn
                weighted_nrr_t += acct['arr'] * acct_nrr_t
                cx = acct['health_trajectory'][t_months - 1].get('threshold_crossing') if t_months <= len(acct['health_trajectory']) else None
                if cx:
                    crossings.append({'account_id': acct['account_id'],
                                      'account_name': acct['account_name'],
                                      'crossing': cx})
            nrr_t = weighted_nrr_t / total_arr if total_arr > 0 else 1.0
            trajectory[t_key] = {
                'nrr_pct': round(nrr_t * 100, 2),
                'threshold_crossings': crossings,
            }

        # ── What-if simulation + playbook cost/ROI ─────────────────────
        intervention_nrr_sum = 0.0
        total_intervention_arr = 0.0
        top_interventions = []

        for acct in account_forecasts:
            if acct['current_nrr'] < 1.0:
                success_rate = acct['intervention_success_rate']
                intervened_nrr = (success_rate * 1.0) + ((1 - success_rate) * acct['current_nrr'])
                intervention_nrr_sum += acct['arr'] * intervened_nrr
                total_intervention_arr += acct['arr']

                projected_save = acct['arr'] * (intervened_nrr - acct['current_nrr'])

                # Playbook cost from arc mapping
                arc = acct['pattern']
                playbooks = arc_playbook_map.get(arc, [])
                primary_pb = playbooks[0] if playbooks else None
                pb_cost = _get_playbook_cost(primary_pb, acct['arr']) if primary_pb else 0
                roi = round(projected_save / pb_cost, 1) if pb_cost > 0 else None

                # Intervention deadline
                dtr = acct.get('days_to_renewal')
                if dtr and dtr < 30:
                    deadline = 'Act within 7 days'
                elif dtr and dtr < 60:
                    deadline = 'Act within 14 days'
                elif acct['health_end'] < 50:
                    deadline = 'Act within 21 days'
                else:
                    deadline = 'Act within 30 days'

                top_interventions.append({
                    'account_id': acct['account_id'],
                    'account_name': acct['account_name'],
                    'arr': acct['arr'],
                    'pattern': arc,
                    'current_nrr': round(acct['current_nrr'] * 100, 1),
                    'projected_nrr': round(intervened_nrr * 100, 1),
                    'projected_save': round(projected_save, 2),
                    'playbook': primary_pb,
                    'playbook_cost': round(pb_cost, 2),
                    'roi': roi,
                    'deadline': deadline,
                    'renewal_date': acct.get('renewal_date'),
                    'renewal_urgency': acct.get('renewal_urgency'),
                })
            else:
                intervention_nrr_sum += acct['arr'] * acct['current_nrr']

        with_interventions_nrr = intervention_nrr_sum / total_arr if total_arr > 0 else 1.0
        delta_arr = (with_interventions_nrr - current_nrr) * total_arr

        # Sort top interventions by projected save (descending)
        top_interventions.sort(key=lambda x: x['projected_save'], reverse=True)

        # Renewals at risk
        renewals_at_risk = [
            {
                'account_id': a['account_id'],
                'account_name': a['account_name'],
                'renewal_date': a['renewal_date'],
                'days_until': a['days_to_renewal'],
                'health': round(a['health_end'], 1),
                'projected_health_at_renewal': a['health_trajectory'][-1]['projected_health'] if a['health_trajectory'] else a['health_end'],
                'arr': a['arr'],
                'renewal_urgency': a['renewal_urgency'],
            }
            for a in account_forecasts
            if a.get('renewal_urgency')
        ]
        renewals_at_risk.sort(key=lambda x: x.get('days_until') or 999)

        # Pattern breakdown (aggregated)
        pattern_breakdown = []
        for pattern_type, corr in self.nrr_correlations.items():
            pattern_breakdown.append({
                'pattern': pattern_type,
                'accounts': corr['n_accounts'],
                'arr': corr['total_arr_exposed'],
                'nrr_pct': round(corr['avg_nrr'] * 100, 1),
                'intervention_success_rate': round(corr['intervention_success_rate'] * 100, 1),
            })
        pattern_breakdown.sort(key=lambda x: x['nrr_pct'])

        self.portfolio_nrr_forecast = {
            'current_nrr_pct': round(current_nrr * 100, 2),
            'with_interventions_nrr_pct': round(with_interventions_nrr * 100, 2),
            'delta_arr': round(delta_arr, 2),
            'total_arr': round(total_arr, 2),
            'total_accounts': len(account_forecasts),
            'at_risk_accounts': len(top_interventions),
            'at_risk_arr': round(total_intervention_arr, 2),
            'trajectory': trajectory,
            'renewals_at_risk': renewals_at_risk,
            'pattern_breakdown': pattern_breakdown,
            'top_interventions': top_interventions[:10],
        }

        print(f"\n   Portfolio NRR: {current_nrr * 100:.1f}% → {with_interventions_nrr * 100:.1f}% "
              f"(+${delta_arr:,.0f} if interventions succeed)")
        print(f"   At-risk accounts: {len(top_interventions)} / {len(account_forecasts)} "
              f"(${total_intervention_arr:,.0f} ARR)")
        if renewals_at_risk:
            print(f"   Renewals at risk: {len(renewals_at_risk)}")

    # ========================================================================
    # OUTPUT GENERATION
    # ========================================================================

    def save_results(self):
        """Save analysis results to JSON files"""
        
        output_dir = self.run_dir.parent.parent / 'learnings' / self.run_dir.name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Pattern profiles
        profiles_file = output_dir / 'pattern_profiles.json'
        with open(profiles_file, 'w') as f:
            profiles_dict = {k: asdict(v) for k, v in self.pattern_profiles.items()}
            json.dump(profiles_dict, f, indent=2)
        print(f"   ✅ Saved pattern profiles: {profiles_file}")
        
        # 2. Transition matrix
        transitions_file = output_dir / 'phase_transitions.json'
        with open(transitions_file, 'w') as f:
            transitions_dict = {k: asdict(v) for k, v in self.transition_matrix.items()}
            json.dump(transitions_dict, f, indent=2)
        print(f"   ✅ Saved transition matrix: {transitions_file}")
        
        # 3. Early warning rules
        warnings_file = output_dir / 'early_warning_rules.json'
        with open(warnings_file, 'w') as f:
            warnings_dict = [asdict(rule) for rule in self.early_warning_rules]
            json.dump(warnings_dict, f, indent=2)
        print(f"   ✅ Saved early warning rules: {warnings_file}")
        
        # 4. Summary report
        self._generate_summary_report(output_dir)
        
        return output_dir
    
    def _generate_summary_report(self, output_dir: Path):
        """Generate human-readable summary report"""
        
        report_file = output_dir / 'ANALYSIS_REPORT.md'
        
        with open(report_file, 'w') as f:
            f.write("# Wizard B - Pattern Analysis Report\n\n")
            f.write(f"**Run ID:** {self.run_dir.name}\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Total Accounts Analyzed:** {len(self.journeys)}\n")
            f.write(f"- **Patterns Identified:** {len(self.pattern_profiles)}\n")
            f.write(f"- **Phase Transitions:** {len(self.transition_matrix)}\n")
            f.write(f"- **Early Warning Rules:** {len(self.early_warning_rules)}\n\n")
            
            f.write("## Pattern Profiles\n\n")
            for pattern_type, profile in self.pattern_profiles.items():
                f.write(f"### {pattern_type.upper()}\n\n")
                f.write(f"- **Accounts:** {profile.n_accounts}\n")
                f.write(f"- **Health Trajectory:** {profile.avg_starting_health:.1f} → {profile.avg_ending_health:.1f}\n")
                f.write(f"- **Average Events:** {profile.avg_total_events:.0f}\n")
                f.write(f"- **CSM Investment:** ${profile.avg_csm_investment:,.0f}\n")
                f.write(f"- **Financial Impact:** {profile.financial_impact}\n\n")
                
                if profile.success_factors:
                    f.write("**Success Factors:**\n")
                    for factor in profile.success_factors:
                        f.write(f"- {factor}\n")
                    f.write("\n")
            
            f.write("## Early Warning Rules\n\n")
            for rule in self.early_warning_rules:
                f.write(f"### {rule.rule_id}: {rule.description}\n\n")
                f.write(f"- **Condition:** `{rule.condition}`\n")
                f.write(f"- **Predicted Outcome:** {rule.predicted_outcome}\n")
                f.write(f"- **Lead Time:** {rule.lead_time_weeks} weeks\n")
                f.write(f"- **Confidence:** {rule.confidence:.1%}\n\n")
        
        print(f"   ✅ Saved summary report: {report_file}")

    # ========================================================================
    # DATABASE PERSISTENCE
    # ========================================================================

    def save_to_database(self, customer_id: int):
        """
        Persist analysis results to WizardRun + WizardLearning DB tables.

        Args:
            customer_id: Customer that owns this analysis.

        Returns:
            The created ``WizardLearning`` instance.
        """
        from models import WizardRun, WizardLearning, db

        # 1. Create WizardRun record
        run = WizardRun(
            customer_id=customer_id,
            status='completed',
            current_phase='pattern_analysis',
            config={'type': 'wizard_b', 'customer_id': customer_id},
            results={
                'total_patterns': len(self.pattern_profiles),
                'total_transitions': len(self.transition_matrix),
                'total_warnings': len(self.early_warning_rules),
                'total_journeys': len(self.journeys),
            },
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.flush()  # get run.run_id

        # 2. Build structured learnings blob
        learnings_blob = {
            'pattern_profiles': {
                k: asdict(v) for k, v in self.pattern_profiles.items()
            },
            'phase_transitions': {
                k: asdict(v) for k, v in self.transition_matrix.items()
            },
            'early_warning_rules': [
                asdict(r) for r in self.early_warning_rules
            ],
            'nrr_correlations': self.nrr_correlations or {},
            'portfolio_nrr_forecast': self.portfolio_nrr_forecast or {},
        }

        # 3. Build validation_rules (early warning rules in usable form)
        validation_rules = [asdict(r) for r in self.early_warning_rules]

        # 4. Generate markdown report
        report_text = self._generate_report_text(run.run_id)

        # 5. Create WizardLearning record
        learning = WizardLearning(
            customer_id=customer_id,
            run_id=run.run_id,
            source_runs=[run.run_id],
            learnings=learnings_blob,
            validation_rules=validation_rules,
            analysis_report=report_text,
            total_accounts_tested=len(self.journeys),
        )
        db.session.add(learning)
        db.session.flush()

        # 6. Activate this learning (deactivates previous ones for same customer)
        learning.activate()

        db.session.commit()
        print(f"   ✅ Saved to DB: WizardRun={run.run_id}, "
              f"WizardLearning v{learning.version} (active)")

        return learning

    def _generate_report_text(self, run_id: str = '') -> str:
        """
        Generate a markdown analysis report as a string.

        Args:
            run_id: Optional run identifier for the header.

        Returns:
            Markdown report text.
        """
        lines = []
        lines.append("# Wizard B - Pattern Analysis Report\n")
        lines.append(f"**Run ID:** {run_id}")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        lines.append("## Summary\n")
        lines.append(f"- **Total Accounts Analyzed:** {len(self.journeys)}")
        lines.append(f"- **Patterns Identified:** {len(self.pattern_profiles)}")
        lines.append(f"- **Phase Transitions:** {len(self.transition_matrix)}")
        lines.append(f"- **Early Warning Rules:** {len(self.early_warning_rules)}\n")

        lines.append("## Pattern Profiles\n")
        for pattern_type, profile in self.pattern_profiles.items():
            lines.append(f"### {pattern_type.upper()}\n")
            lines.append(f"- **Accounts:** {profile.n_accounts}")
            lines.append(f"- **Health Trajectory:** {profile.avg_starting_health:.1f} → {profile.avg_ending_health:.1f}")
            lines.append(f"- **Average Events:** {profile.avg_total_events:.0f}")
            lines.append(f"- **CSM Investment:** ${profile.avg_csm_investment:,.0f}")
            lines.append(f"- **Financial Impact:** {profile.financial_impact}\n")

            if profile.success_factors:
                lines.append("**Success Factors:**")
                for factor in profile.success_factors:
                    lines.append(f"- {factor}")
                lines.append("")

        lines.append("## Early Warning Rules\n")
        for rule in self.early_warning_rules:
            lines.append(f"### {rule.rule_id}: {rule.description}\n")
            lines.append(f"- **Condition:** `{rule.condition}`")
            lines.append(f"- **Predicted Outcome:** {rule.predicted_outcome}")
            lines.append(f"- **Lead Time:** {rule.lead_time_weeks} weeks")
            lines.append(f"- **Confidence:** {rule.confidence:.1%}\n")

        # NRR Intelligence section
        if self.nrr_correlations:
            lines.append("## NRR Intelligence\n")
            lines.append("### Pattern-to-NRR Correlations\n")
            lines.append("| Pattern | NRR | ARR Exposed | Protected | Lost | Intervention Rate |")
            lines.append("|---------|-----|-------------|-----------|------|-------------------|")
            for pattern, data in sorted(self.nrr_correlations.items(),
                                         key=lambda x: x[1].get('avg_nrr', 1)):
                nrr = f"{data.get('avg_nrr', 1) * 100:.1f}%"
                arr = f"${data.get('total_arr_exposed', 0):,.0f}"
                prot = f"${data.get('avg_revenue_protected', 0):,.0f}"
                lost = f"${data.get('avg_revenue_lost', 0):,.0f}"
                intv = f"{data.get('intervention_success_rate', 0) * 100:.0f}%"
                lines.append(f"| {pattern} | {nrr} | {arr} | {prot} | {lost} | {intv} |")
            lines.append("")

        if self.portfolio_nrr_forecast:
            f = self.portfolio_nrr_forecast
            lines.append("### Portfolio NRR Forecast\n")
            lines.append(f"- **Current Projected NRR:** {f.get('current_nrr_pct', 0):.1f}%")
            lines.append(f"- **With Interventions:** {f.get('with_interventions_nrr_pct', 0):.1f}%")
            lines.append(f"- **Delta ARR:** ${f.get('delta_arr', 0):,.0f}")
            lines.append(f"- **At-Risk Accounts:** {f.get('at_risk_accounts', 0)} / {f.get('total_accounts', 0)}")
            lines.append(f"- **At-Risk ARR:** ${f.get('at_risk_arr', 0):,.0f}\n")

            if f.get('top_interventions'):
                lines.append("### Top Intervention Opportunities\n")
                lines.append("| Account | ARR | Pattern | Current NRR | Projected NRR | Projected Save |")
                lines.append("|---------|-----|---------|-------------|---------------|----------------|")
                for t in f['top_interventions'][:5]:
                    lines.append(
                        f"| {t['account_name']} | ${t['arr']:,.0f} | {t['pattern']} | "
                        f"{t['current_nrr']}% | {t['projected_nrr']}% | ${t['projected_save']:,.0f} |"
                    )
                lines.append("")

        return "\n".join(lines)


# ============================================================================
# DATABASE ENTRYPOINT
# ============================================================================

def run_wizard_b(customer_id: int) -> dict:
    """
    Top-level entrypoint for running Wizard B from within a Flask request
    context (no subprocess, no filesystem).

    Args:
        customer_id: Customer to analyze.

    Returns:
        dict with ``success``, ``run_id``, ``version``, ``total_patterns``, etc.

    Raises:
        ValueError: If no journey data exists for this customer.
    """
    analyzer = PatternAnalyzer.from_database(customer_id)
    analyzer.analyze_patterns()
    learning = analyzer.save_to_database(customer_id)

    return {
        'success': True,
        'run_id': learning.run_id,
        'version': learning.version,
        'total_patterns': len(analyzer.pattern_profiles),
        'total_transitions': len(analyzer.transition_matrix),
        'total_warnings': len(analyzer.early_warning_rules),
        'total_journeys': len(analyzer.journeys),
    }


# ============================================================================
# CLI INTERFACE (legacy filesystem mode)
# ============================================================================

def main():
    """Run pattern analyzer from command line"""
    
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python wizard_b_pattern_analyzer.py <wizard_run_dir>")
        print("Example: python wizard_b_pattern_analyzer.py data/wizard/wizard_20260109_101218")
        sys.exit(1)
    
    run_dir = Path(sys.argv[1])
    
    if not run_dir.exists():
        print(f"❌ Error: Directory not found: {run_dir}")
        sys.exit(1)
    
    # Run analysis (file mode: auto-save to filesystem)
    analyzer = PatternAnalyzer(run_dir)
    analyzer.load_data()
    analyzer.analyze_patterns(auto_save=True)
    
    print("\n🎉 Analysis complete! Check the learnings/ directory for results.")


if __name__ == '__main__':
    main()
