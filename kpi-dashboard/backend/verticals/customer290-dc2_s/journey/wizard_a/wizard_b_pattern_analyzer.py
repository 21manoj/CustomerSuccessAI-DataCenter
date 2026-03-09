#!/usr/bin/env python3
"""
Wizard B - Pattern Analyzer
============================

Analyzes customer journey patterns to identify:
1. Journey archetypes (crisis-recovery, churn, stable, expansion)
2. Common success/failure patterns
3. Risk indicators
4. Health trajectory patterns
5. Event impact analysis

This is a TRADITIONAL statistical analyzer (no AI/LLM).
Uses pattern recognition, statistical analysis, and rule-based classification.

Usage:
    python wizard_b_pattern_analyzer.py \
        --input-dir outputs/wizard_runs/run_001 \
        --output-dir outputs/wizard_runs/run_001/analysis

Input:
    - account_*_journey.json files from Wizard A
    - account_*_kpis.csv files (optional)

Output:
    - pattern_analysis_report.json - Overall pattern analysis
    - pattern_summary.csv - Per-account pattern classification
    - insights.md - Human-readable insights report
"""

import sys
import os
import json
import csv
import argparse
from glob import glob
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import List, Dict, Tuple
import statistics

# ============================================================================
# PATTERN DEFINITIONS
# ============================================================================

JOURNEY_ARCHETYPES = {
    'crisis_recovery': {
        'name': 'Crisis Recovery',
        'description': 'Starts low, recovers significantly',
        'health_pattern': 'low_start_high_end',
        'volatility': 'high',
        'risk_level': 'medium'
    },
    'churn_risk': {
        'name': 'Churn Risk',
        'description': 'Declining health, negative trajectory',
        'health_pattern': 'declining',
        'volatility': 'medium_high',
        'risk_level': 'high'
    },
    'stable_growth': {
        'name': 'Stable Growth',
        'description': 'Steady improvement, low volatility',
        'health_pattern': 'improving',
        'volatility': 'low',
        'risk_level': 'low'
    },
    'expansion_ready': {
        'name': 'Expansion Ready',
        'description': 'High health, strong engagement',
        'health_pattern': 'high_steady',
        'volatility': 'low',
        'risk_level': 'very_low'
    },
    'volatile_uncertain': {
        'name': 'Volatile/Uncertain',
        'description': 'Unstable, unpredictable swings',
        'health_pattern': 'volatile',
        'volatility': 'very_high',
        'risk_level': 'high'
    }
}

# ============================================================================
# PATTERN ANALYZER CLASS
# ============================================================================

class PatternAnalyzer:
    """Analyzes journey patterns using statistical methods"""
    
    def __init__(self):
        self.journeys = []
        self.patterns = []
        self.insights = {
            'total_journeys': 0,
            'pattern_distribution': {},
            'health_statistics': {},
            'event_patterns': {},
            'risk_indicators': {}
        }
    
    def load_journey(self, journey_file: str) -> Dict:
        """Load a journey JSON file"""
        with open(journey_file, 'r') as f:
            return json.load(f)
    
    def analyze_health_trajectory(self, journey: Dict) -> Dict:
        """
        Analyze health score trajectory
        
        Returns:
            - trajectory_type: improving, declining, stable, volatile
            - health_change: total change in health
            - volatility: standard deviation of health changes
            - turning_points: number of direction changes
        """
        events = journey.get('events', [])
        
        if not events:
            return {
                'trajectory_type': 'unknown',
                'health_change': 0,
                'volatility': 0,
                'turning_points': 0
            }
        
        # Extract health scores
        health_scores = []
        for event in events:
            score_before = event.get('health_score_before', 0)
            score_after = event.get('health_score_after', 0)
            health_scores.append(score_before)
        
        # Add final score
        if events:
            health_scores.append(events[-1].get('health_score_after', 0))
        
        # Calculate statistics
        if len(health_scores) < 2:
            return {
                'trajectory_type': 'insufficient_data',
                'health_change': 0,
                'volatility': 0,
                'turning_points': 0
            }
        
        # Health change
        health_change = health_scores[-1] - health_scores[0]
        
        # Volatility (standard deviation of week-to-week changes)
        changes = [health_scores[i+1] - health_scores[i] for i in range(len(health_scores)-1)]
        volatility = statistics.stdev(changes) if len(changes) > 1 else 0
        
        # Turning points (direction changes)
        turning_points = 0
        for i in range(1, len(changes)):
            if (changes[i] > 0 and changes[i-1] < 0) or (changes[i] < 0 and changes[i-1] > 0):
                turning_points += 1
        
        # Classify trajectory
        avg_health = statistics.mean(health_scores)
        
        if volatility > 5:
            trajectory_type = 'volatile'
        elif health_change > 20:
            trajectory_type = 'improving'
        elif health_change < -20:
            trajectory_type = 'declining'
        else:
            trajectory_type = 'stable'
        
        return {
            'trajectory_type': trajectory_type,
            'health_change': health_change,
            'volatility': volatility,
            'turning_points': turning_points,
            'avg_health': avg_health,
            'min_health': min(health_scores),
            'max_health': max(health_scores)
        }
    
    def classify_journey_archetype(self, journey: Dict, trajectory: Dict) -> str:
        """
        Classify journey into an archetype
        
        Logic:
        - Crisis Recovery: Low start (<50), high improvement (>30), medium-high volatility
        - Churn Risk: Declining trajectory, low end health (<40)
        - Stable Growth: Steady improvement, low volatility (<3)
        - Expansion Ready: High health (>80), low volatility, stable
        - Volatile/Uncertain: High volatility (>5)
        """
        starting_health = journey.get('starting_health', 0)
        ending_health = journey.get('ending_health', 0)
        health_change = trajectory['health_change']
        volatility = trajectory['volatility']
        
        # Volatile/Uncertain
        if volatility > 5:
            return 'volatile_uncertain'
        
        # Crisis Recovery
        if starting_health < 50 and health_change > 30:
            return 'crisis_recovery'
        
        # Churn Risk
        if health_change < -15 or ending_health < 40:
            return 'churn_risk'
        
        # Expansion Ready
        if ending_health > 80 and volatility < 3:
            return 'expansion_ready'
        
        # Stable Growth
        if health_change > 5 and volatility < 3:
            return 'stable_growth'
        
        # Default to stable if none match
        return 'stable_growth'
    
    def analyze_event_patterns(self, journey: Dict) -> Dict:
        """Analyze event patterns and frequencies"""
        events = journey.get('events', [])
        
        if not events:
            return {
                'total_events': 0,
                'event_types': {},
                'sentiment_distribution': {},
                'avg_impact': 0
            }
        
        # Count event types
        event_types = Counter([e.get('event_type', 'unknown') for e in events])
        
        # Sentiment distribution
        sentiments = Counter([e.get('sentiment', 'unknown') for e in events])
        
        # Average impact
        impacts = []
        for event in events:
            before = event.get('health_score_before', 0)
            after = event.get('health_score_after', 0)
            impacts.append(abs(after - before))
        
        avg_impact = statistics.mean(impacts) if impacts else 0
        
        return {
            'total_events': len(events),
            'event_types': dict(event_types),
            'sentiment_distribution': dict(sentiments),
            'avg_impact': avg_impact
        }
    
    def identify_risk_indicators(self, journey: Dict, trajectory: Dict, events: Dict) -> List[str]:
        """Identify risk indicators for this journey"""
        risks = []
        
        ending_health = journey.get('ending_health', 0)
        health_change = trajectory['health_change']
        volatility = trajectory['volatility']
        
        # Risk indicators
        if ending_health < 40:
            risks.append('critically_low_health')
        
        if health_change < -20:
            risks.append('significant_health_decline')
        
        if volatility > 7:
            risks.append('highly_volatile_health')
        
        if trajectory.get('turning_points', 0) > 8:
            risks.append('unstable_trajectory')
        
        # Event-based risks
        negative_events = events['sentiment_distribution'].get('negative', 0)
        total_events = events['total_events']
        
        if total_events > 0 and negative_events / total_events > 0.4:
            risks.append('high_negative_sentiment')
        
        if events['total_events'] < 10:
            risks.append('low_engagement')
        
        return risks
    
    def analyze_journey(self, journey: Dict) -> Dict:
        """Complete analysis of a single journey"""
        
        # Analyze trajectory
        trajectory = self.analyze_health_trajectory(journey)
        
        # Classify archetype
        archetype = self.classify_journey_archetype(journey, trajectory)
        
        # Analyze events
        event_patterns = self.analyze_event_patterns(journey)
        
        # Identify risks
        risks = self.identify_risk_indicators(journey, trajectory, event_patterns)
        
        return {
            'account_id': journey.get('account_id', 'unknown'),
            'account_name': journey.get('account_name', 'Unknown'),
            'archetype': archetype,
            'archetype_name': JOURNEY_ARCHETYPES[archetype]['name'],
            'trajectory': trajectory,
            'event_patterns': event_patterns,
            'risk_indicators': risks,
            'risk_level': JOURNEY_ARCHETYPES[archetype]['risk_level'],
            'starting_health': journey.get('starting_health', 0),
            'ending_health': journey.get('ending_health', 0)
        }
    
    def analyze_all_journeys(self, journey_files: List[str]) -> Dict:
        """Analyze all journeys and generate insights"""
        
        print("="*70)
        print("WIZARD B - PATTERN ANALYZER")
        print("="*70)
        print(f"Analyzing {len(journey_files)} journeys...")
        print()
        
        all_patterns = []
        
        for idx, journey_file in enumerate(journey_files):
            # Load journey
            journey = self.load_journey(journey_file)
            
            # Analyze
            pattern = self.analyze_journey(journey)
            all_patterns.append(pattern)
            
            # Progress
            print(f"✅ [{idx+1:3d}/{len(journey_files)}] {pattern['account_id']:10s} - "
                  f"{pattern['archetype_name']:20s} "
                  f"(Health: {pattern['starting_health']:.0f}→{pattern['ending_health']:.0f}, "
                  f"Risk: {pattern['risk_level']})")
        
        # Generate aggregate insights
        print()
        print("Generating insights...")
        
        insights = self.generate_insights(all_patterns)
        
        return {
            'patterns': all_patterns,
            'insights': insights
        }
    
    def generate_insights(self, patterns: List[Dict]) -> Dict:
        """Generate aggregate insights from all patterns"""
        
        # Pattern distribution
        archetypes = Counter([p['archetype'] for p in patterns])
        
        # Risk distribution
        risk_levels = Counter([p['risk_level'] for p in patterns])
        
        # Health statistics
        starting_healths = [p['starting_health'] for p in patterns]
        ending_healths = [p['ending_health'] for p in patterns]
        health_changes = [p['ending_health'] - p['starting_health'] for p in patterns]
        
        # Most common risks
        all_risks = []
        for p in patterns:
            all_risks.extend(p['risk_indicators'])
        common_risks = Counter(all_risks).most_common(10)
        
        # Trajectory types
        trajectories = Counter([p['trajectory']['trajectory_type'] for p in patterns])
        
        return {
            'total_journeys': len(patterns),
            'pattern_distribution': dict(archetypes),
            'risk_distribution': dict(risk_levels),
            'trajectory_distribution': dict(trajectories),
            'health_statistics': {
                'starting': {
                    'mean': statistics.mean(starting_healths),
                    'median': statistics.median(starting_healths),
                    'min': min(starting_healths),
                    'max': max(starting_healths)
                },
                'ending': {
                    'mean': statistics.mean(ending_healths),
                    'median': statistics.median(ending_healths),
                    'min': min(ending_healths),
                    'max': max(ending_healths)
                },
                'change': {
                    'mean': statistics.mean(health_changes),
                    'median': statistics.median(health_changes),
                    'positive_changes': sum(1 for c in health_changes if c > 0),
                    'negative_changes': sum(1 for c in health_changes if c < 0)
                }
            },
            'common_risk_indicators': [{'risk': r, 'count': c} for r, c in common_risks]
        }

# ============================================================================
# OUTPUT GENERATION
# ============================================================================

def save_pattern_summary_csv(patterns: List[Dict], output_file: str):
    """Save pattern summary as CSV"""
    
    fieldnames = [
        'account_id', 'account_name', 'archetype', 'archetype_name',
        'starting_health', 'ending_health', 'health_change',
        'trajectory_type', 'volatility', 'risk_level',
        'total_events', 'risk_indicators'
    ]
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for pattern in patterns:
            writer.writerow({
                'account_id': pattern['account_id'],
                'account_name': pattern['account_name'],
                'archetype': pattern['archetype'],
                'archetype_name': pattern['archetype_name'],
                'starting_health': pattern['starting_health'],
                'ending_health': pattern['ending_health'],
                'health_change': pattern['ending_health'] - pattern['starting_health'],
                'trajectory_type': pattern['trajectory']['trajectory_type'],
                'volatility': f"{pattern['trajectory']['volatility']:.2f}",
                'risk_level': pattern['risk_level'],
                'total_events': pattern['event_patterns']['total_events'],
                'risk_indicators': '; '.join(pattern['risk_indicators'])
            })

def save_insights_report(analysis: Dict, output_file: str):
    """Save human-readable insights report"""
    
    insights = analysis['insights']
    patterns = analysis['patterns']
    
    with open(output_file, 'w') as f:
        f.write("# Wizard B - Pattern Analysis Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("---\n\n")
        f.write("## Executive Summary\n\n")
        f.write(f"- **Total Journeys Analyzed:** {insights['total_journeys']}\n")
        f.write(f"- **Average Health Change:** {insights['health_statistics']['change']['mean']:.1f} points\n")
        f.write(f"- **Journeys Improving:** {insights['health_statistics']['change']['positive_changes']}\n")
        f.write(f"- **Journeys Declining:** {insights['health_statistics']['change']['negative_changes']}\n\n")
        
        f.write("---\n\n")
        f.write("## Pattern Distribution\n\n")
        
        for archetype, count in insights['pattern_distribution'].items():
            pct = (count / insights['total_journeys']) * 100
            archetype_info = JOURNEY_ARCHETYPES[archetype]
            f.write(f"### {archetype_info['name']} ({count} accounts, {pct:.1f}%)\n\n")
            f.write(f"- **Description:** {archetype_info['description']}\n")
            f.write(f"- **Risk Level:** {archetype_info['risk_level']}\n\n")
        
        f.write("---\n\n")
        f.write("## Health Statistics\n\n")
        
        health = insights['health_statistics']
        f.write("### Starting Health\n")
        f.write(f"- Mean: {health['starting']['mean']:.1f}\n")
        f.write(f"- Median: {health['starting']['median']:.1f}\n")
        f.write(f"- Range: {health['starting']['min']:.0f} - {health['starting']['max']:.0f}\n\n")
        
        f.write("### Ending Health\n")
        f.write(f"- Mean: {health['ending']['mean']:.1f}\n")
        f.write(f"- Median: {health['ending']['median']:.1f}\n")
        f.write(f"- Range: {health['ending']['min']:.0f} - {health['ending']['max']:.0f}\n\n")
        
        f.write("---\n\n")
        f.write("## Risk Analysis\n\n")
        
        f.write("### Common Risk Indicators\n\n")
        for risk_item in insights['common_risk_indicators'][:5]:
            risk = risk_item['risk']
            count = risk_item['count']
            pct = (count / insights['total_journeys']) * 100
            f.write(f"- **{risk.replace('_', ' ').title()}:** {count} accounts ({pct:.1f}%)\n")
        
        f.write("\n---\n\n")
        f.write("## High-Risk Accounts\n\n")
        
        high_risk = [p for p in patterns if p['risk_level'] in ['high', 'very_high']]
        f.write(f"**Total High-Risk Accounts:** {len(high_risk)}\n\n")
        
        for pattern in high_risk[:10]:
            f.write(f"### {pattern['account_name']} ({pattern['account_id']})\n")
            f.write(f"- **Pattern:** {pattern['archetype_name']}\n")
            f.write(f"- **Health:** {pattern['starting_health']:.0f} → {pattern['ending_health']:.0f}\n")
            f.write(f"- **Risks:** {', '.join(pattern['risk_indicators'])}\n\n")

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Wizard B - Analyze customer journey patterns'
    )
    parser.add_argument('--input-dir', required=True,
                       help='Directory containing journey JSON files')
    parser.add_argument('--output-dir', required=True,
                       help='Directory for analysis outputs')
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.exists(args.input_dir):
        print(f"❌ Input directory not found: {args.input_dir}")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Find journey files
    journey_files = sorted(glob(os.path.join(args.input_dir, "account_*_journey.json")))
    
    if not journey_files:
        print(f"❌ No journey files found in {args.input_dir}")
        sys.exit(1)
    
    # Analyze patterns
    analyzer = PatternAnalyzer()
    analysis = analyzer.analyze_all_journeys(journey_files)
    
    # Save outputs
    print()
    print("Saving outputs...")
    
    # JSON report
    json_file = os.path.join(args.output_dir, 'pattern_analysis_report.json')
    with open(json_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"  ✅ {json_file}")
    
    # CSV summary
    csv_file = os.path.join(args.output_dir, 'pattern_summary.csv')
    save_pattern_summary_csv(analysis['patterns'], csv_file)
    print(f"  ✅ {csv_file}")
    
    # Markdown report
    md_file = os.path.join(args.output_dir, 'insights.md')
    save_insights_report(analysis, md_file)
    print(f"  ✅ {md_file}")
    
    print()
    print("="*70)
    print("✅ PATTERN ANALYSIS COMPLETE!")
    print("="*70)
    print(f"Analyzed: {analysis['insights']['total_journeys']} journeys")
    print(f"Output: {args.output_dir}")
    print()

if __name__ == "__main__":
    main()
