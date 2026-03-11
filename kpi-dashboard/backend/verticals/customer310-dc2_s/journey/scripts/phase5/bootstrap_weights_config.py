#!/usr/bin/env python3
"""
Bootstrap Weights Configuration Loader
======================================

Loads the Supermicro simulation-derived weights for the Signal Analyst.
Starting accuracy: 70% | Target: 85% | Convergence: ~150 iterations

Usage:
    from bootstrap_weights_config import BootstrapWeights
    
    weights = BootstrapWeights()
    health_score = weights.calculate_health(account_kpis)
"""

import json
import os
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class WeightConfig:
    """Configuration for bootstrap weights"""
    version: str
    source: str
    baseline_accuracy: float
    target_accuracy: float
    convergence_iterations: int
    pillar_weights: Dict[str, float]
    kpi_weights: Dict[str, Dict[str, float]]
    effective_weights: Dict[str, float]
    
    def get_pillar_weight(self, pillar: str) -> float:
        """Get weight for a specific pillar"""
        return self.pillar_weights.get(pillar, 0.0)
    
    def get_kpi_weight(self, pillar: str, kpi: str) -> float:
        """Get weight for a specific KPI within a pillar"""
        return self.kpi_weights.get(pillar, {}).get(kpi, 0.0)
    
    def get_effective_weight(self, pillar: str, kpi: str) -> float:
        """Calculate effective weight (L2 × L1)"""
        return self.get_pillar_weight(pillar) * self.get_kpi_weight(pillar, kpi)


class BootstrapWeights:
    """
    Bootstrap weights loader and calculator
    
    Loads simulation-derived weights and provides methods to calculate
    health scores, pillar scores, and make predictions.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize with bootstrap weights
        
        Args:
            config_path: Path to JSON config file. If None, uses default.
        """
        if config_path is None:
            # Default to same directory as this file
            config_path = os.path.join(
                os.path.dirname(__file__), 
                'bootstrap_weights_config.json'
            )
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        self.config = WeightConfig(
            version=config_data['config_version'],
            source=config_data['source'],
            baseline_accuracy=config_data['baseline_accuracy'],
            target_accuracy=config_data['target_accuracy'],
            convergence_iterations=config_data['convergence_iterations'],
            pillar_weights=config_data['pillar_weights_L2'],
            kpi_weights=config_data['kpi_weights_L1'],
            effective_weights=config_data['effective_weights_top_10']
        )
        
        self.validation_thresholds = config_data['validation_thresholds']
        self.learning_params = config_data['learning_parameters']
    
    def calculate_pillar_scores(self, account_kpis: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate pillar scores from KPI values (L1 aggregation)
        
        Args:
            account_kpis: Dict mapping KPI names to values (0-100)
        
        Returns:
            Dict mapping pillar names to scores (0-100)
        
        Example:
            account_kpis = {
                'gpu_utilization_rate': 85.0,
                'training_job_completion': 78.0,
                'inference_latency': 92.0,
                # ... other KPIs
            }
            pillar_scores = weights.calculate_pillar_scores(account_kpis)
            # {'P3_ai_workload_performance': 84.2, ...}
        """
        pillar_scores = {}
        
        for pillar, kpi_weights in self.config.kpi_weights.items():
            total = 0.0
            for kpi, weight in kpi_weights.items():
                kpi_value = account_kpis.get(kpi, 50.0)  # Default to 50 if missing
                total += kpi_value * weight
            
            pillar_scores[pillar] = round(total, 2)
        
        return pillar_scores
    
    def calculate_health_score(self, pillar_scores: Dict[str, float]) -> float:
        """
        Calculate overall health score from pillar scores (L2 aggregation)
        
        Args:
            pillar_scores: Dict mapping pillar names to scores (0-100)
        
        Returns:
            Overall health score (0-100)
        
        Example:
            pillar_scores = {
                'P1_deployment_velocity': 75.0,
                'P2_operational_stability': 82.0,
                'P3_ai_workload_performance': 88.0,
                'P4_channel_partner_health': 70.0,
                'P5_expansion_readiness': 85.0
            }
            health = weights.calculate_health_score(pillar_scores)
            # 82.25
        """
        total = sum(
            pillar_scores.get(pillar, 50.0) * weight
            for pillar, weight in self.config.pillar_weights.items()
        )
        
        return round(total, 2)
    
    def calculate_health_from_kpis(self, account_kpis: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
        """
        Calculate health score directly from KPIs (combined L1 + L2)
        
        Args:
            account_kpis: Dict mapping KPI names to values (0-100)
        
        Returns:
            Tuple of (health_score, pillar_scores)
        
        Example:
            health, pillars = weights.calculate_health_from_kpis(account_kpis)
            print(f"Health: {health}, P3: {pillars['P3_ai_workload_performance']}")
        """
        pillar_scores = self.calculate_pillar_scores(account_kpis)
        health_score = self.calculate_health_score(pillar_scores)
        return health_score, pillar_scores
    
    def predict_churn_risk(self, health_score: float) -> Tuple[str, float]:
        """
        Predict churn risk category based on health score
        
        Args:
            health_score: Overall health score (0-100)
        
        Returns:
            Tuple of (risk_category, risk_probability)
        
        Categories:
            - 'critical': Health < 40, 90% churn risk
            - 'high': Health 40-70, 60% churn risk
            - 'medium': Health 70-85, 30% churn risk
            - 'low': Health > 85, 10% churn risk
        """
        if health_score < self.validation_thresholds['health_critical']:
            return 'critical', 0.90
        elif health_score < self.validation_thresholds['health_at_risk']:
            return 'high', 0.60
        elif health_score < 85:
            return 'medium', 0.30
        else:
            return 'low', 0.10
    
    def predict_expansion_probability(self, 
                                     health_score: float,
                                     pillar_scores: Dict[str, float]) -> float:
        """
        Predict expansion probability based on health and P5 pillar
        
        Args:
            health_score: Overall health score (0-100)
            pillar_scores: Dict with pillar scores
        
        Returns:
            Expansion probability (0.0 to 1.0)
        
        Logic:
            - P5 (Expansion Readiness) is primary driver
            - Overall health must be > 70 for expansion consideration
            - Combines both factors with weights
        """
        if health_score < 70:
            return 0.0  # Too risky for expansion
        
        p5_score = pillar_scores.get('P5_expansion_readiness', 50.0)
        
        # Weighted combination: 70% P5, 30% overall health
        expansion_signal = (p5_score * 0.7) + (health_score * 0.3)
        
        # Convert to probability (0-1)
        if expansion_signal > 85:
            return 0.80  # High probability
        elif expansion_signal > 70:
            return 0.50  # Medium probability
        else:
            return 0.20  # Low probability
    
    def get_top_kpis(self, n: int = 10) -> List[Tuple[str, float]]:
        """
        Get top N KPIs by effective weight
        
        Args:
            n: Number of top KPIs to return
        
        Returns:
            List of (kpi_name, effective_weight) tuples, sorted by weight
        """
        sorted_kpis = sorted(
            self.config.effective_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_kpis[:n]
    
    def get_pillar_summary(self) -> Dict[str, any]:
        """
        Get summary of pillar weights
        
        Returns:
            Dict with pillar weights, sorted by importance
        """
        sorted_pillars = sorted(
            self.config.pillar_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            'pillars': sorted_pillars,
            'highest': sorted_pillars[0],
            'total': sum(self.config.pillar_weights.values())
        }
    
    def validate_weights(self) -> Dict[str, bool]:
        """
        Validate that weights are properly configured
        
        Returns:
            Dict with validation results
        """
        validations = {}
        
        # Check L2 weights sum to 1.0
        l2_sum = sum(self.config.pillar_weights.values())
        validations['l2_sum_valid'] = abs(l2_sum - 1.0) < 0.001
        
        # Check each pillar's L1 weights sum to 1.0
        for pillar, kpi_weights in self.config.kpi_weights.items():
            l1_sum = sum(kpi_weights.values())
            validations[f'{pillar}_l1_sum_valid'] = abs(l1_sum - 1.0) < 0.001
        
        # Check effective weights are correctly calculated
        for kpi, eff_weight in self.config.effective_weights.items():
            # Find which pillar this KPI belongs to
            for pillar, kpis in self.config.kpi_weights.items():
                if kpi in kpis:
                    expected = self.config.pillar_weights[pillar] * kpis[kpi]
                    validations[f'{kpi}_effective_weight_valid'] = abs(eff_weight - expected) < 0.001
                    break
        
        validations['all_valid'] = all(validations.values())
        return validations
    
    def export_for_signal_analyst(self) -> Dict:
        """
        Export config in format suitable for Signal Analyst agent
        
        Returns:
            Dict with weights in Signal Analyst format
        """
        return {
            'bootstrap_mode': True,
            'baseline_accuracy': self.config.baseline_accuracy,
            'weights': {
                'L2': self.config.pillar_weights,
                'L1': self.config.kpi_weights
            },
            'learning_params': self.learning_params,
            'version': self.config.version
        }


# Example usage
if __name__ == "__main__":
    print("="*70)
    print("BOOTSTRAP WEIGHTS CONFIGURATION")
    print("="*70)
    print()
    
    # Load weights
    weights = BootstrapWeights()
    
    print(f"✅ Configuration loaded successfully")
    print(f"   Source: {weights.config.source}")
    print(f"   Version: {weights.config.version}")
    print(f"   Baseline Accuracy: {weights.config.baseline_accuracy * 100}%")
    print(f"   Target Accuracy: {weights.config.target_accuracy * 100}%")
    print()
    
    # Show pillar summary
    summary = weights.get_pillar_summary()
    print("📊 Pillar Weights (L2):")
    for pillar, weight in summary['pillars']:
        print(f"   {pillar}: {weight * 100:.1f}%")
    print()
    
    # Show top KPIs
    print("🏆 Top 10 KPIs by Effective Weight:")
    for idx, (kpi, weight) in enumerate(weights.get_top_kpis(10), 1):
        print(f"   {idx}. {kpi}: {weight * 100:.1f}%")
    print()
    
    # Validate weights
    validation = weights.validate_weights()
    print("✅ Weight Validation:")
    print(f"   All weights valid: {validation['all_valid']}")
    print(f"   L2 sum valid: {validation['l2_sum_valid']}")
    print()
    
    # Example calculation
    print("📈 Example Calculation:")
    example_kpis = {
        'gpu_utilization_rate': 85.0,
        'training_job_completion': 78.0,
        'inference_latency': 92.0,
        'storage_io_efficiency': 88.0,
        'network_fabric_health': 90.0,
        'workload_density_trend': 75.0,
        # Add more KPIs as needed...
    }
    
    health, pillars = weights.calculate_health_from_kpis(example_kpis)
    risk_category, risk_prob = weights.predict_churn_risk(health)
    expansion_prob = weights.predict_expansion_probability(health, pillars)
    
    print(f"   Input: {len(example_kpis)} KPI values")
    print(f"   Health Score: {health}")
    print(f"   Churn Risk: {risk_category} ({risk_prob * 100}%)")
    print(f"   Expansion Probability: {expansion_prob * 100:.1f}%")
    print()
    
    print("="*70)
    print("Ready to integrate with Signal Analyst!")
    print("="*70)
