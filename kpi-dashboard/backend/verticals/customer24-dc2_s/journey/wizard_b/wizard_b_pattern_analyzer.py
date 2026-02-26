#!/usr/bin/env python3
"""
Wizard B - Pattern Analyzer (Phase 1)
=====================================

Analyzes journey data from Wizard A to extract pattern insights.

Input: Wizard A generated journey data
Output: Pattern definitions, early warning rules, transition probabilities
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
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
    Analyzes journey patterns from Wizard A data
    """
    
    def __init__(self, wizard_run_dir: Path):
        """
        Initialize analyzer with Wizard A output directory
        
        Args:
            wizard_run_dir: Path to wizard run output (e.g., data/wizard/wizard_20260109_101218/)
        """
        self.run_dir = Path(wizard_run_dir)
        self.journeys = []
        self.kpis = pd.DataFrame()
        self.milestones = []
        
        # Outputs
        self.pattern_profiles = {}
        self.transition_matrix = {}
        self.early_warning_rules = []
        
        print(f"🔍 Pattern Analyzer initialized for: {self.run_dir.name}")
    
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
    # PATTERN PROFILING
    # ========================================================================
    
    def analyze_patterns(self):
        """Main analysis pipeline"""
        
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
        
        # 5. Generate outputs
        print("\n5️⃣  Generating outputs...")
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
            
            # Extract statistics
            profile = PatternProfile(
                pattern_type=pattern_type,
                n_accounts=len(pattern_journeys),
                avg_starting_health=np.mean([j['starting_health'] for j in pattern_journeys]),
                avg_ending_health=np.mean([j['ending_health'] for j in pattern_journeys]),
                health_change=np.mean([j['ending_health'] - j['starting_health'] for j in pattern_journeys]),
                avg_lowest_health=np.mean([j['lowest_health'] for j in pattern_journeys]),
                avg_highest_health=np.mean([j['highest_health'] for j in pattern_journeys]),
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
                    transitions[key]['total_weeks'] += (events[i+1]['week_number'] - events[i]['week_number'])
        
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
                    if event['health_score_after'] < 50:
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
                neg_events = sum(1 for e in journey['events'] if e['sentiment_value'] < 0)
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
            early_improvers = sum(1 for j in expanded if j['events'][10]['health_score_after'] > j['starting_health'])
            if early_improvers >= 2:
                success_factors.append(f"Early health improvement: {early_improvers}/{len(expanded)} accounts")
            
            # Store in pattern profiles
            for pattern in ['proactive_growth', 'expansion']:
                if pattern in self.pattern_profiles:
                    self.pattern_profiles[pattern].success_factors = success_factors
            
            for factor in success_factors:
                print(f"   ✅ {factor}")
    
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


# ============================================================================
# CLI INTERFACE
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
    
    # Run analysis
    analyzer = PatternAnalyzer(run_dir)
    analyzer.load_data()
    analyzer.analyze_patterns()
    
    print("\n🎉 Analysis complete! Check the learnings/ directory for results.")


if __name__ == '__main__':
    main()
