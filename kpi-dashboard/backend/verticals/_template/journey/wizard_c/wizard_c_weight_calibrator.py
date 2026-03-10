#!/usr/bin/env python3
"""
Wizard C - Weight Calibrator
=============================

Calibrates KPI weights based on journey outcomes to optimize health scoring.

Uses statistical optimization to determine optimal weights for:
1. Individual KPIs
2. KPI categories (Performance, Cost, Scalability, Support, Business Value)
3. Event types (positive, neutral, negative)

This is a TRADITIONAL statistical optimizer (no AI/LLM).
Uses correlation analysis, linear regression, and optimization algorithms.

Usage:
    python wizard_c_weight_calibrator.py \
        --input-dir outputs/wizard_runs/run_001 \
        --pattern-file outputs/wizard_runs/run_001/analysis/pattern_summary.csv \
        --output-dir outputs/wizard_runs/run_001/weights

Input:
    - account_*_journey.json files from Wizard A
    - account_*_kpis.csv files from KPI generator
    - pattern_summary.csv from Wizard B (optional but recommended)

Output:
    - optimized_weights.json - Calibrated weights for KPIs
    - weight_analysis.csv - Weight impact analysis
    - calibration_report.md - Human-readable report
"""

import sys
import os
import json
import csv
import argparse
from glob import glob
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple
import statistics

# ============================================================================
# DEFAULT WEIGHTS (Baseline)
# ============================================================================

DEFAULT_KPI_WEIGHTS = {
    # Performance & Utilization (8 KPIs)
    'DC2S_PERF_CPU_UTIL': 0.08,
    'DC2S_PERF_GPU_UTIL': 0.10,
    'DC2S_PERF_MEM_UTIL': 0.07,
    'DC2S_PERF_STORAGE_UTIL': 0.06,
    'DC2S_PERF_NETWORK_UTIL': 0.06,
    'DC2S_PERF_THROUGHPUT': 0.08,
    'DC2S_PERF_LATENCY': 0.07,
    'DC2S_PERF_IOPS': 0.06,
    
    # Cost Efficiency (7 KPIs)
    'DC2S_COST_TOTAL_MONTHLY': 0.09,
    'DC2S_COST_PER_WORKLOAD': 0.06,
    'DC2S_COST_POWER_EFFICIENCY': 0.07,
    'DC2S_COST_COOLING_EFFICIENCY': 0.06,
    'DC2S_COST_OPTIMIZATION_SCORE': 0.07,
    'DC2S_COST_CAPEX_UTILIZATION': 0.05,
    'DC2S_COST_OPEX_RATIO': 0.05,
    
    # Scalability & Growth (7 KPIs)
    'DC2S_SCALE_CAPACITY_HEADROOM': 0.07,
    'DC2S_SCALE_WORKLOAD_GROWTH': 0.06,
    'DC2S_SCALE_CLUSTER_EXPANSION': 0.05,
    'DC2S_SCALE_STORAGE_GROWTH': 0.05,
    'DC2S_SCALE_DEPLOYMENT_VELOCITY': 0.06,
    'DC2S_SCALE_AUTO_SCALING_SCORE': 0.06,
    'DC2S_SCALE_ELASTICITY_SCORE': 0.06,
    
    # Support & Reliability (6 KPIs)
    'DC2S_SUP_UPTIME_PCT': 0.10,
    'DC2S_SUP_MTBF': 0.07,
    'DC2S_SUP_MTTR': 0.07,
    'DC2S_SUP_TICKET_RESOLUTION_TIME': 0.06,
    'DC2S_SUP_CUSTOMER_SATISFACTION': 0.08,
    'DC2S_SUP_SLA_COMPLIANCE': 0.09,
    
    # Business Value (7 KPIs)
    'DC2S_BIZ_ROI': 0.08,
    'DC2S_BIZ_TIME_TO_VALUE': 0.06,
    'DC2S_BIZ_FEATURE_ADOPTION': 0.06,
    'DC2S_BIZ_INNOVATION_SCORE': 0.05,
    'DC2S_BIZ_COMPETITIVE_ADVANTAGE': 0.06,
    'DC2S_BIZ_REVENUE_IMPACT': 0.07,
    'DC2S_BIZ_STRATEGIC_ALIGNMENT': 0.06
}

KPI_CATEGORIES = {
    'Performance & Utilization': [
        'DC2S_PERF_CPU_UTIL', 'DC2S_PERF_GPU_UTIL', 'DC2S_PERF_MEM_UTIL',
        'DC2S_PERF_STORAGE_UTIL', 'DC2S_PERF_NETWORK_UTIL', 'DC2S_PERF_THROUGHPUT',
        'DC2S_PERF_LATENCY', 'DC2S_PERF_IOPS'
    ],
    'Cost Efficiency': [
        'DC2S_COST_TOTAL_MONTHLY', 'DC2S_COST_PER_WORKLOAD', 'DC2S_COST_POWER_EFFICIENCY',
        'DC2S_COST_COOLING_EFFICIENCY', 'DC2S_COST_OPTIMIZATION_SCORE',
        'DC2S_COST_CAPEX_UTILIZATION', 'DC2S_COST_OPEX_RATIO'
    ],
    'Scalability & Growth': [
        'DC2S_SCALE_CAPACITY_HEADROOM', 'DC2S_SCALE_WORKLOAD_GROWTH', 'DC2S_SCALE_CLUSTER_EXPANSION',
        'DC2S_SCALE_STORAGE_GROWTH', 'DC2S_SCALE_DEPLOYMENT_VELOCITY',
        'DC2S_SCALE_AUTO_SCALING_SCORE', 'DC2S_SCALE_ELASTICITY_SCORE'
    ],
    'Support & Reliability': [
        'DC2S_SUP_UPTIME_PCT', 'DC2S_SUP_MTBF', 'DC2S_SUP_MTTR',
        'DC2S_SUP_TICKET_RESOLUTION_TIME', 'DC2S_SUP_CUSTOMER_SATISFACTION',
        'DC2S_SUP_SLA_COMPLIANCE'
    ],
    'Business Value': [
        'DC2S_BIZ_ROI', 'DC2S_BIZ_TIME_TO_VALUE', 'DC2S_BIZ_FEATURE_ADOPTION',
        'DC2S_BIZ_INNOVATION_SCORE', 'DC2S_BIZ_COMPETITIVE_ADVANTAGE',
        'DC2S_BIZ_REVENUE_IMPACT', 'DC2S_BIZ_STRATEGIC_ALIGNMENT'
    ]
}

# ============================================================================
# DC2S -> P-FORMAT TRANSLATION
# ============================================================================
# The canonical KPI system uses P-format codes (P1-KPI1 through P5-KPI8).
# Wizard C internally uses DC2S_* codes for calibration. This mapping bridges
# the two systems so calibrated weights can be saved in canonical format.

DC2S_TO_P_FORMAT = {
    # Performance & Utilization -> P1 (Deployment Velocity) + P3 (AI Workload)
    'DC2S_PERF_CPU_UTIL': 'P1-KPI3',        # Configuration Accuracy (CPU config)
    'DC2S_PERF_GPU_UTIL': 'P3-KPI1',        # GPU Utilization Rate
    'DC2S_PERF_MEM_UTIL': 'P3-KPI5',        # GPU Memory Efficiency
    'DC2S_PERF_STORAGE_UTIL': 'P3-KPI6',    # Distributed Training Efficiency
    'DC2S_PERF_NETWORK_UTIL': 'P1-KPI6',    # Network Readiness Score
    'DC2S_PERF_THROUGHPUT': 'P3-KPI8',      # Batch Processing Throughput
    'DC2S_PERF_LATENCY': 'P3-KPI3',         # Inference Latency (P95)
    'DC2S_PERF_IOPS': 'P3-KPI4',            # Model Training Time
    # Cost Efficiency -> P2 (Operational Stability)
    'DC2S_COST_TOTAL_MONTHLY': 'P2-KPI4',   # System Uptime Percentage
    'DC2S_COST_PER_WORKLOAD': 'P2-KPI6',    # Power Efficiency (PUE)
    'DC2S_COST_POWER_EFFICIENCY': 'P2-KPI6',  # Power Efficiency (PUE)
    'DC2S_COST_COOLING_EFFICIENCY': 'P2-KPI5',  # Thermal Management Score
    'DC2S_COST_OPTIMIZATION_SCORE': 'P2-KPI8',  # Preventive Maintenance Compliance
    'DC2S_COST_CAPEX_UTILIZATION': 'P5-KPI5',   # Budget Availability Signals
    'DC2S_COST_OPEX_RATIO': 'P2-KPI7',      # Mean Time To Repair (MTTR)
    # Scalability & Growth -> P5 (Expansion Readiness)
    'DC2S_SCALE_CAPACITY_HEADROOM': 'P5-KPI1',  # Capacity Utilization Rate
    'DC2S_SCALE_WORKLOAD_GROWTH': 'P5-KPI3',    # Workload Growth Velocity
    'DC2S_SCALE_CLUSTER_EXPANSION': 'P5-KPI4',  # Compute Hour Consumption Trend
    'DC2S_SCALE_STORAGE_GROWTH': 'P5-KPI2',     # Capacity Utilization Trajectory
    'DC2S_SCALE_DEPLOYMENT_VELOCITY': 'P1-KPI4', # Deployment Cycle Time
    'DC2S_SCALE_AUTO_SCALING_SCORE': 'P5-KPI7',  # Expansion Probability (90d)
    'DC2S_SCALE_ELASTICITY_SCORE': 'P5-KPI6',   # New Use Case Adoption
    # Support & Reliability -> P2 (Operational Stability)
    'DC2S_SUP_UPTIME_PCT': 'P2-KPI4',       # System Uptime Percentage
    'DC2S_SUP_MTBF': 'P2-KPI2',             # MTBF
    'DC2S_SUP_MTTR': 'P2-KPI7',             # Mean Time To Repair
    'DC2S_SUP_TICKET_RESOLUTION_TIME': 'P2-KPI3',  # Critical Incidents (30d)
    'DC2S_SUP_CUSTOMER_SATISFACTION': 'P4-KPI6',    # Partner NPS
    'DC2S_SUP_SLA_COMPLIANCE': 'P2-KPI1',   # RMA Frequency Rate
    # Business Value -> P4 (Channel & Partner) + P5 (Expansion)
    'DC2S_BIZ_ROI': 'P5-KPI5',              # Budget Availability Signals
    'DC2S_BIZ_TIME_TO_VALUE': 'P1-KPI1',    # Time-to-First-Workload
    'DC2S_BIZ_FEATURE_ADOPTION': 'P5-KPI6', # New Use Case Adoption
    'DC2S_BIZ_INNOVATION_SCORE': 'P3-KPI7', # Workload Diversity Score
    'DC2S_BIZ_COMPETITIVE_ADVANTAGE': 'P4-KPI4',  # Channel Conflict Score
    'DC2S_BIZ_REVENUE_IMPACT': 'P4-KPI5',   # Co-selling Opportunities
    'DC2S_BIZ_STRATEGIC_ALIGNMENT': 'P4-KPI1',  # Partner Engagement Score
}

DC2S_CATEGORY_TO_PILLAR = {
    'Performance & Utilization': 'P3',   # AI Workload Performance
    'Cost Efficiency': 'P2',             # Operational Stability
    'Scalability & Growth': 'P5',        # Expansion Readiness
    'Support & Reliability': 'P2',       # Operational Stability
    'Business Value': 'P4',              # Channel & Partner Health
}


def translate_to_p_format(dc2s_weights: Dict) -> Dict:
    """
    Translate DC2S_* keyed weights to P-format keyed weights.

    If a DC2S code maps to a P-format KPI that already has a weight
    (from a previous mapping), the weights are averaged.
    """
    p_weights = defaultdict(list)
    for dc2s_code, weight in dc2s_weights.items():
        p_code = DC2S_TO_P_FORMAT.get(dc2s_code)
        if p_code:
            p_weights[p_code].append(weight)
    # Average if multiple DC2S codes map to same P-format code
    return {code: statistics.mean(weights) for code, weights in p_weights.items()}


# ============================================================================
# WEIGHT CALIBRATOR CLASS
# ============================================================================

class WeightCalibrator:
    """Calibrates KPI weights based on journey outcomes"""
    
    def __init__(self):
        self.journeys = []
        self.kpis = {}
        self.patterns = {}
        self.weights = DEFAULT_KPI_WEIGHTS.copy()
        self.category_weights = {}
    
    def load_journey(self, journey_file: str) -> Dict:
        """Load journey JSON file"""
        with open(journey_file, 'r') as f:
            return json.load(f)
    
    def load_kpis(self, kpi_file: str) -> List[Dict]:
        """Load KPI CSV file"""
        kpis = []
        with open(kpi_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                kpis.append(row)
        return kpis
    
    def load_patterns(self, pattern_file: str) -> Dict:
        """Load pattern summary from Wizard B"""
        patterns = {}
        with open(pattern_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                account_id = row['account_id']
                patterns[account_id] = row
        return patterns
    
    def calculate_kpi_correlation(self, kpis: List[Dict], outcome: str) -> Dict:
        """
        Calculate correlation between KPI values and journey outcomes
        
        Uses simple correlation: KPIs that are consistently high in successful
        journeys (expansion_ready, stable_growth) should have higher weights.
        """
        
        # Aggregate KPI values by account
        kpi_by_account = defaultdict(lambda: defaultdict(list))
        
        for kpi in kpis:
            account_id = kpi.get('account_id', '')
            kpi_code = kpi.get('kpi_code', '')
            
            try:
                value = float(kpi.get('value', 0))
                kpi_by_account[account_id][kpi_code].append(value)
            except ValueError:
                continue
        
        # Calculate average KPI values per account
        kpi_averages = {}
        for account_id, kpi_values in kpi_by_account.items():
            kpi_averages[account_id] = {
                kpi_code: statistics.mean(values)
                for kpi_code, values in kpi_values.items()
            }
        
        # Calculate correlations
        correlations = {}
        
        for kpi_code in DEFAULT_KPI_WEIGHTS.keys():
            # Get KPI values for successful vs unsuccessful accounts
            successful_values = []
            unsuccessful_values = []
            
            for account_id, avg_kpis in kpi_averages.items():
                pattern = self.patterns.get(account_id, {})
                archetype = pattern.get('archetype', '')
                
                if kpi_code in avg_kpis:
                    value = avg_kpis[kpi_code]
                    
                    if archetype in ['expansion_ready', 'stable_growth']:
                        successful_values.append(value)
                    elif archetype in ['churn_risk', 'volatile_uncertain']:
                        unsuccessful_values.append(value)
            
            # Simple correlation: difference in means
            if successful_values and unsuccessful_values:
                success_mean = statistics.mean(successful_values)
                unsuccess_mean = statistics.mean(unsuccessful_values)
                
                # Normalize to 0-1 scale
                correlation = abs(success_mean - unsuccess_mean) / 100
                correlations[kpi_code] = min(correlation, 1.0)
            else:
                correlations[kpi_code] = 0.5  # Neutral
        
        return correlations
    
    def optimize_weights(self, correlations: Dict) -> Dict:
        """
        Optimize weights based on correlations
        
        Higher correlation = higher importance = higher weight
        Ensures weights sum to 1.0
        """
        
        optimized_weights = {}
        
        # Adjust weights based on correlation
        for kpi_code, base_weight in DEFAULT_KPI_WEIGHTS.items():
            correlation = correlations.get(kpi_code, 0.5)
            
            # Adjust weight: multiply base weight by correlation factor
            # Factor ranges from 0.5 (low correlation) to 1.5 (high correlation)
            factor = 0.5 + correlation
            optimized_weights[kpi_code] = base_weight * factor
        
        # Normalize to sum to 1.0
        total = sum(optimized_weights.values())
        optimized_weights = {
            kpi: weight / total
            for kpi, weight in optimized_weights.items()
        }
        
        return optimized_weights
    
    def calculate_category_weights(self, kpi_weights: Dict) -> Dict:
        """Calculate aggregate weights for KPI categories"""
        
        category_weights = {}
        
        for category, kpi_list in KPI_CATEGORIES.items():
            total_weight = sum(
                kpi_weights.get(kpi_code, 0)
                for kpi_code in kpi_list
            )
            category_weights[category] = total_weight
        
        return category_weights
    
    def calibrate(self, journey_files: List[str], kpi_files: List[str], 
                  pattern_file: str = None) -> Dict:
        """
        Main calibration process
        
        Steps:
        1. Load all data (journeys, KPIs, patterns)
        2. Calculate KPI correlations with outcomes
        3. Optimize weights based on correlations
        4. Calculate category weights
        5. Generate calibration report
        """
        
        print("="*70)
        print("WIZARD C - WEIGHT CALIBRATOR")
        print("="*70)
        print(f"Journeys: {len(journey_files)}")
        print(f"KPI files: {len(kpi_files)}")
        print()
        
        # Load patterns if available
        if pattern_file and os.path.exists(pattern_file):
            print("Loading pattern analysis...")
            self.patterns = self.load_patterns(pattern_file)
            print(f"  ✅ Loaded {len(self.patterns)} pattern classifications")
        else:
            print("⚠️  No pattern file provided, using default optimization")
        
        # Load KPIs
        print("\nLoading KPI data...")
        all_kpis = []
        for kpi_file in kpi_files:
            kpis = self.load_kpis(kpi_file)
            all_kpis.extend(kpis)
        print(f"  ✅ Loaded {len(all_kpis)} KPI records")
        
        # Calculate correlations
        print("\nCalculating KPI correlations...")
        correlations = self.calculate_kpi_correlation(all_kpis, 'success')
        print(f"  ✅ Calculated correlations for {len(correlations)} KPIs")
        
        # Optimize weights
        print("\nOptimizing weights...")
        optimized_weights = self.optimize_weights(correlations)
        print(f"  ✅ Optimized {len(optimized_weights)} KPI weights")
        
        # Calculate category weights
        print("\nCalculating category weights...")
        category_weights = self.calculate_category_weights(optimized_weights)
        print(f"  ✅ Calculated {len(category_weights)} category weights")
        
        # Compare with defaults
        print("\nWeight changes:")
        significant_changes = []
        for kpi_code in sorted(DEFAULT_KPI_WEIGHTS.keys())[:10]:  # Show first 10
            old = DEFAULT_KPI_WEIGHTS[kpi_code]
            new = optimized_weights[kpi_code]
            change = ((new - old) / old) * 100
            
            if abs(change) > 10:
                significant_changes.append((kpi_code, old, new, change))
                print(f"  {kpi_code:30s}: {old:.4f} → {new:.4f} ({change:+.1f}%)")
        
        return {
            'kpi_weights': optimized_weights,
            'category_weights': category_weights,
            'correlations': correlations,
            'significant_changes': significant_changes,
            'default_weights': DEFAULT_KPI_WEIGHTS,
            'calibration_date': datetime.now().isoformat()
        }

# ============================================================================
# OUTPUT GENERATION
# ============================================================================

def save_weights_json(calibration: Dict, output_file: str):
    """Save optimized weights as JSON"""
    with open(output_file, 'w') as f:
        json.dump(calibration, f, indent=2)

def save_weight_analysis_csv(calibration: Dict, output_file: str):
    """Save weight analysis as CSV"""
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'kpi_code', 'default_weight', 'optimized_weight',
            'weight_change_pct', 'correlation', 'category'
        ])
        
        # Find category for each KPI
        kpi_to_category = {}
        for category, kpi_list in KPI_CATEGORIES.items():
            for kpi in kpi_list:
                kpi_to_category[kpi] = category
        
        for kpi_code in sorted(calibration['kpi_weights'].keys()):
            default = calibration['default_weights'][kpi_code]
            optimized = calibration['kpi_weights'][kpi_code]
            change = ((optimized - default) / default) * 100
            correlation = calibration['correlations'].get(kpi_code, 0)
            category = kpi_to_category.get(kpi_code, 'Unknown')
            
            writer.writerow([
                kpi_code, f"{default:.6f}", f"{optimized:.6f}",
                f"{change:.2f}", f"{correlation:.4f}", category
            ])

def save_calibration_report(calibration: Dict, output_file: str):
    """Save human-readable calibration report"""
    
    with open(output_file, 'w') as f:
        f.write("# Wizard C - Weight Calibration Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("---\n\n")
        f.write("## Summary\n\n")
        f.write("This report shows the optimized KPI weights based on journey outcome analysis.\n\n")
        f.write("**Methodology:**\n")
        f.write("1. Analyzed correlations between KPI values and journey success\n")
        f.write("2. Adjusted weights based on predictive power\n")
        f.write("3. Normalized weights to sum to 1.0\n\n")
        
        f.write("---\n\n")
        f.write("## Category Weights\n\n")
        
        category_weights = calibration['category_weights']
        for category in sorted(category_weights.keys(), key=lambda x: category_weights[x], reverse=True):
            weight = category_weights[category]
            pct = weight * 100
            f.write(f"### {category}\n")
            f.write(f"- **Total Weight:** {weight:.4f} ({pct:.2f}%)\n")
            f.write(f"- **KPIs:** {len(KPI_CATEGORIES[category])}\n\n")
        
        f.write("---\n\n")
        f.write("## Significant Weight Changes\n\n")
        f.write("KPIs with weight changes >10%:\n\n")
        
        significant = calibration['significant_changes']
        if significant:
            for kpi_code, old, new, change in significant[:20]:
                f.write(f"### {kpi_code}\n")
                f.write(f"- **Default:** {old:.6f}\n")
                f.write(f"- **Optimized:** {new:.6f}\n")
                f.write(f"- **Change:** {change:+.1f}%\n\n")
        else:
            f.write("*No significant changes (all weights within ±10%)*\n\n")
        
        f.write("---\n\n")
        f.write("## Top 10 Most Important KPIs\n\n")
        
        top_kpis = sorted(
            calibration['kpi_weights'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        for idx, (kpi_code, weight) in enumerate(top_kpis, 1):
            pct = weight * 100
            f.write(f"{idx}. **{kpi_code}** - {pct:.2f}%\n")

# ============================================================================
# MAIN
# ============================================================================

def save_optimized_weights_to_config(customer_id, optimized_weights, pillar_weights, kpi_weights):
    """
    Save optimized weights back to CustomerConfig
    
    Args:
        customer_id: Customer ID
        optimized_weights: Optimized weights dict
        pillar_weights: Calibrated pillar weights
        kpi_weights: Calibrated KPI weights by pillar
    """
    
    try:
        # Import here to avoid circular dependencies
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent.parent.parent.parent
        sys.path.insert(0, str(backend_path))
        
        from app_v3_minimal import app
        from models import db, CustomerConfig
        
        with app.app_context():
            print()
            print("="*70)
            print("SAVING OPTIMIZED WEIGHTS TO CUSTOMER CONFIG")
            print("="*70)
            
            config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
            
            if not config:
                print(f"❌ No config found for customer {customer_id}")
                return False
            
            # Update pillar weights
            config.dc2s_pillar_weights = pillar_weights
            
            # Update KPI weights
            config.dc2s_kpi_weights = kpi_weights
            
            # Save
            try:
                db.session.commit()
                
                print("✅ Weights saved to database")
                print()
                print("Updated Pillar Weights:")
                for pillar, weight in pillar_weights.items():
                    print(f"  {pillar}: {weight:.3f} ({weight*100:.1f}%)")
                
                print()
                print("Updated KPI Weights by Pillar:")
                for pillar, kpis in kpi_weights.items():
                    print(f"  {pillar}:")
                    for kpi_code, weight in list(kpis.items())[:3]:  # Show first 3
                        print(f"    {kpi_code}: {weight:.3f}")
                    if len(kpis) > 3:
                        print(f"    ... and {len(kpis) - 3} more")
                
                print()
                print("="*70)
                
                return True
            
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error saving weights: {e}")
                return False
    except Exception as e:
        print(f"❌ Error accessing database: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Wizard C - Calibrate KPI weights based on journey outcomes'
    )
    parser.add_argument('--input-dir', required=True,
                       help='Directory containing journey and KPI files')
    parser.add_argument('--pattern-file',
                       help='Pattern summary CSV from Wizard B (optional)')
    parser.add_argument('--output-dir', required=True,
                       help='Directory for calibration outputs')
    parser.add_argument('--customer-id', type=int, default=9,
                       help='Customer ID for saving to config (default: 9)')
    parser.add_argument('--save-to-config', action='store_true',
                       help='Save optimized weights to CustomerConfig')
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.exists(args.input_dir):
        print(f"❌ Input directory not found: {args.input_dir}")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Find journey files
    journey_files = sorted(glob(os.path.join(args.input_dir, "account_*_journey.json")))
    
    # Find KPI files
    kpi_files = sorted(glob(os.path.join(args.input_dir, "account_*_kpis.csv")))
    
    if not journey_files:
        print(f"❌ No journey files found in {args.input_dir}")
        sys.exit(1)
    
    if not kpi_files:
        print(f"⚠️  Warning: No KPI files found, using default weights")
    
    # Calibrate weights
    calibrator = WeightCalibrator()
    calibration = calibrator.calibrate(
        journey_files=journey_files,
        kpi_files=kpi_files,
        pattern_file=args.pattern_file
    )
    
    # Save outputs
    print()
    print("Saving outputs...")
    
    # JSON weights
    json_file = os.path.join(args.output_dir, 'optimized_weights.json')
    save_weights_json(calibration, json_file)
    print(f"  ✅ {json_file}")
    
    # CSV analysis
    csv_file = os.path.join(args.output_dir, 'weight_analysis.csv')
    save_weight_analysis_csv(calibration, csv_file)
    print(f"  ✅ {csv_file}")
    
    # Markdown report
    md_file = os.path.join(args.output_dir, 'calibration_report.md')
    save_calibration_report(calibration, md_file)
    print(f"  ✅ {md_file}")
    
    print()
    print("="*70)
    print("✅ WEIGHT CALIBRATION COMPLETE!")
    print("="*70)
    print(f"KPIs calibrated: {len(calibration['kpi_weights'])}")
    print(f"Significant changes: {len(calibration['significant_changes'])}")
    print(f"Output: {args.output_dir}")
    print()
    
    # Save to CustomerConfig if requested
    if args.save_to_config:
        print()
        print("Saving weights to CustomerConfig...")

        # Translate DC2S_* KPI codes to P-format before saving
        p_format_kpi_weights = translate_to_p_format(calibration['kpi_weights'])
        print(f"  Translated {len(calibration['kpi_weights'])} DC2S codes -> {len(p_format_kpi_weights)} P-format codes")

        # Use calibrated category weights mapped to pillars (P-format)
        cat_weights = calibration.get('category_weights', {})
        pillar_weights = {}
        for category, pillar in DC2S_CATEGORY_TO_PILLAR.items():
            cat_w = cat_weights.get(category, 0)
            # Categories may map to same pillar (e.g. Cost + Support -> P2), accumulate
            pillar_weights[pillar] = pillar_weights.get(pillar, 0) + cat_w
        # Ensure all 5 pillars present
        for p in ('P1', 'P2', 'P3', 'P4', 'P5'):
            if p not in pillar_weights:
                pillar_weights[p] = 0.20
        # Normalize so they sum to 1.0
        total = sum(pillar_weights.values())
        if total > 0:
            pillar_weights = {k: v / total for k, v in pillar_weights.items()}

        # Group P-format KPI weights by pillar
        kpi_weights_by_pillar = {'P1': {}, 'P2': {}, 'P3': {}, 'P4': {}, 'P5': {}}
        for kpi_code, weight in p_format_kpi_weights.items():
            pillar = kpi_code.split('-')[0]  # "P3-KPI1" -> "P3"
            if pillar in kpi_weights_by_pillar:
                kpi_weights_by_pillar[pillar][kpi_code] = weight

        # Normalize KPI weights within each pillar to sum to 1.0
        for pillar, kpis in kpi_weights_by_pillar.items():
            if kpis:
                total_w = sum(kpis.values())
                if total_w > 0:
                    kpi_weights_by_pillar[pillar] = {k: v / total_w for k, v in kpis.items()}

        success = save_optimized_weights_to_config(
            customer_id=args.customer_id,
            optimized_weights=p_format_kpi_weights,
            pillar_weights=pillar_weights,
            kpi_weights=kpi_weights_by_pillar
        )

        if success:
            print("Weights saved to customer configuration (P-format)")
            print("   These weights will be used for future calculations")
        else:
            print("Failed to save weights to config")
        print()

if __name__ == "__main__":
    main()
