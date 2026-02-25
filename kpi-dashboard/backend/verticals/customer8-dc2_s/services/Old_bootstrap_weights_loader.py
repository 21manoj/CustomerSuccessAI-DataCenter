#!/usr/bin/env python3
"""
Bootstrap Weights Loader
========================

Loads and manages bootstrap weights for the Signal Analyst.
Bootstrap weights provide initial prediction accuracy (~70%) before
the system learns from actual data.

Files loaded:
- bootstrap_weights_config.json: Pillar and KPI weights for health scoring
- kpi_mapping_config.json: KPI code mappings and metadata

Usage:
    from bootstrap_weights_loader import get_bootstrap_weights, BootstrapWeightsManager
    
    weights = get_bootstrap_weights()
    pillar_weights = weights.get_pillar_weights()
    kpi_weights = weights.get_kpi_weights('P2_stability')
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PillarWeight:
    """Weight configuration for a pillar"""
    pillar_id: str
    pillar_name: str
    weight: float
    kpi_weights: Dict[str, float]


@dataclass 
class BootstrapConfig:
    """Complete bootstrap configuration"""
    version: str
    pillar_weights: Dict[str, PillarWeight]
    kpi_mappings: Dict[str, Any]
    threshold_config: Dict[str, Any]
    scenario_patterns: Dict[str, Any]


class BootstrapWeightsManager:
    """
    Manages bootstrap weights for Signal Analyst predictions.
    
    Bootstrap weights provide:
    - Pillar importance weights (how much each pillar affects overall health)
    - KPI weights within pillars (which KPIs matter most)
    - Threshold configurations (when to trigger alerts)
    - Scenario patterns (characteristic patterns for healthy/at_risk/crisis)
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize with config directory.
        
        Args:
            config_dir: Path to config directory containing JSON files.
                       Defaults to journey/config/ relative to BASE_DIR
        """
        self.config_dir = self._resolve_config_dir(config_dir)
        self.weights_config: Dict = {}
        self.kpi_mapping: Dict = {}
        self.is_loaded = False
        
        # Load on init
        self.load()
    
    def _resolve_config_dir(self, config_dir: Optional[str]) -> Path:
        """Resolve config directory path"""
        if config_dir:
            return Path(config_dir)
        
        # Try environment variable
        base_dir = os.environ.get('BASE_DIR', '')
        if base_dir:
            return Path(base_dir).expanduser() / 'journey' / 'config'
        
        # Try relative to this file
        this_file = Path(__file__).resolve()
        possible_paths = [
            this_file.parent.parent / 'journey' / 'config',  # From services/
            this_file.parent / 'journey' / 'config',          # From root
            Path.home() / 'CustomerSuccessAI-DataCenter' / 'kpi-dashboard' / 
                'backend' / 'verticals' / 'customer8-dc2_s' / 'journey' / 'config',
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # Default
        return possible_paths[0]
    
    def load(self) -> bool:
        """Load bootstrap weights from config files"""
        print(f"Loading bootstrap weights from: {self.config_dir}")
        
        # Load weights config
        weights_file = self.config_dir / 'bootstrap_weights_config.json'
        if weights_file.exists():
            with open(weights_file, 'r') as f:
                self.weights_config = json.load(f)
            print(f"  ✅ Loaded: bootstrap_weights_config.json")
        else:
            print(f"  ⚠️  Not found: {weights_file}")
            self._create_default_weights()
        
        # Load KPI mapping
        mapping_file = self.config_dir / 'kpi_mapping_config.json'
        if mapping_file.exists():
            with open(mapping_file, 'r') as f:
                self.kpi_mapping = json.load(f)
            print(f"  ✅ Loaded: kpi_mapping_config.json")
        else:
            print(f"  ⚠️  Not found: {mapping_file}")
            self._create_default_mapping()
        
        self.is_loaded = True
        return True
    
    def _create_default_weights(self):
        """Create default bootstrap weights if config not found"""
        self.weights_config = {
            "version": "1.0.0",
            "description": "Default bootstrap weights for DC2_S Signal Analyst",
            "pillar_weights": {
                "P1_deployment": 0.15,
                "P2_stability": 0.30,
                "P3_performance": 0.25,
                "P4_channel": 0.10,
                "P5_expansion": 0.20
            },
            "kpi_weights": {
                "P1_deployment": {
                    "time_to_first_inference": 0.25,
                    "rack_deployment_time": 0.20,
                    "gpu_driver_install_success": 0.20,
                    "cluster_validation_pass": 0.20,
                    "documentation_completeness": 0.15
                },
                "P2_stability": {
                    "mtbf": 0.25,
                    "mttr": 0.15,
                    "uptime_percentage": 0.25,
                    "critical_incident_rate": 0.20,
                    "rma_rate": 0.15
                },
                "P3_performance": {
                    "gpu_utilization_rate": 0.30,
                    "inference_latency": 0.25,
                    "training_throughput": 0.20,
                    "job_completion_rate": 0.25
                },
                "P4_channel": {
                    "partner_response_time": 0.25,
                    "partner_resolution_rate": 0.25,
                    "escalation_rate": 0.25,
                    "partner_satisfaction": 0.25
                },
                "P5_expansion": {
                    "capacity_utilization": 0.20,
                    "expansion_pipeline": 0.20,
                    "renewal_probability": 0.30,
                    "nps_score": 0.15,
                    "contract_growth_rate": 0.15
                }
            },
            "thresholds": {
                "healthy": {"min": 70, "max": 100},
                "at_risk": {"min": 40, "max": 69},
                "crisis": {"min": 0, "max": 39}
            },
            "scenario_patterns": {
                "healthy": {
                    "avg_health": [75, 95],
                    "trend": "stable_or_improving",
                    "event_sentiment": [0.3, 1.0],
                    "critical_incidents": [0, 1]
                },
                "at_risk": {
                    "avg_health": [45, 74],
                    "trend": "declining",
                    "event_sentiment": [-0.2, 0.5],
                    "critical_incidents": [1, 3]
                },
                "crisis": {
                    "avg_health": [20, 50],
                    "trend": "sharply_declining",
                    "event_sentiment": [-1.0, 0.0],
                    "critical_incidents": [2, 10]
                }
            }
        }
        print("  ℹ️  Using default weights")
    
    def _create_default_mapping(self):
        """Create default KPI mapping if config not found"""
        self.kpi_mapping = {
            "version": "1.0.0",
            "pillars": {
                "P1_deployment": {"name": "Deployment Velocity", "kpi_count": 6},
                "P2_stability": {"name": "Operational Stability", "kpi_count": 7},
                "P3_performance": {"name": "AI Workload Performance", "kpi_count": 6},
                "P4_channel": {"name": "Channel & Partner Health", "kpi_count": 6},
                "P5_expansion": {"name": "Expansion & Revenue", "kpi_count": 8}
            },
            "critical_kpis": [
                "mtbf", "uptime_percentage", "gpu_utilization_rate",
                "critical_incident_rate", "renewal_probability"
            ],
            "early_warning_kpis": [
                "critical_incident_rate", "rma_rate", "escalation_rate",
                "partner_satisfaction", "nps_score"
            ]
        }
        print("  ℹ️  Using default KPI mapping")
    
    def get_pillar_weights(self) -> Dict[str, float]:
        """Get pillar importance weights (sum to 1.0)"""
        return self.weights_config.get('pillar_weights', {})
    
    def get_kpi_weights(self, pillar: str) -> Dict[str, float]:
        """Get KPI weights within a pillar (sum to 1.0)"""
        return self.weights_config.get('kpi_weights', {}).get(pillar, {})
    
    def get_all_kpi_weights(self) -> Dict[str, Dict[str, float]]:
        """Get all KPI weights organized by pillar"""
        return self.weights_config.get('kpi_weights', {})
    
    def get_thresholds(self) -> Dict[str, Dict[str, int]]:
        """Get health score thresholds"""
        return self.weights_config.get('thresholds', {
            'healthy': {'min': 70, 'max': 100},
            'at_risk': {'min': 40, 'max': 69},
            'crisis': {'min': 0, 'max': 39}
        })
    
    def get_scenario_patterns(self) -> Dict[str, Any]:
        """Get characteristic patterns for each scenario"""
        return self.weights_config.get('scenario_patterns', {})
    
    def get_critical_kpis(self) -> List[str]:
        """Get list of critical KPIs that heavily influence predictions"""
        return self.kpi_mapping.get('critical_kpis', [])
    
    def get_early_warning_kpis(self) -> List[str]:
        """Get list of KPIs that serve as early warning indicators"""
        return self.kpi_mapping.get('early_warning_kpis', [])
    
    def calculate_weighted_health(self, pillar_scores: Dict[str, float]) -> float:
        """
        Calculate overall health using bootstrap weights.
        
        Args:
            pillar_scores: Dict of {pillar_id: score}
        
        Returns:
            Weighted health score 0-100
        """
        pillar_weights = self.get_pillar_weights()
        
        total_weight = 0
        weighted_sum = 0
        
        for pillar, score in pillar_scores.items():
            weight = pillar_weights.get(pillar, 0.2)  # Default equal weight
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 50.0  # Default neutral score
        
        return weighted_sum / total_weight
    
    def classify_health(self, score: float) -> str:
        """
        Classify health score into category.
        
        Returns: 'healthy', 'at_risk', or 'crisis'
        """
        thresholds = self.get_thresholds()
        
        if score >= thresholds['healthy']['min']:
            return 'healthy'
        elif score >= thresholds['at_risk']['min']:
            return 'at_risk'
        else:
            return 'crisis'
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of loaded configuration"""
        return {
            'config_dir': str(self.config_dir),
            'is_loaded': self.is_loaded,
            'weights_version': self.weights_config.get('version', 'unknown'),
            'mapping_version': self.kpi_mapping.get('version', 'unknown'),
            'pillar_count': len(self.get_pillar_weights()),
            'critical_kpis': len(self.get_critical_kpis()),
            'thresholds': self.get_thresholds()
        }
    
    def save_weights(self, filepath: Optional[str] = None):
        """Save current weights to file"""
        if filepath is None:
            filepath = self.config_dir / 'bootstrap_weights_config.json'
        
        with open(filepath, 'w') as f:
            json.dump(self.weights_config, f, indent=2)
        print(f"Saved weights to: {filepath}")
    
    def update_weights_from_learning(self, learned_weights: Dict[str, Any]):
        """
        Update bootstrap weights with learned weights from Wizard B.
        
        Args:
            learned_weights: New weights learned from outcome data
        """
        if 'pillar_weights' in learned_weights:
            self.weights_config['pillar_weights'].update(learned_weights['pillar_weights'])
        
        if 'kpi_weights' in learned_weights:
            for pillar, kpi_weights in learned_weights['kpi_weights'].items():
                if pillar in self.weights_config['kpi_weights']:
                    self.weights_config['kpi_weights'][pillar].update(kpi_weights)
        
        print("Updated weights from learning")


# Singleton instance
_bootstrap_manager: Optional[BootstrapWeightsManager] = None


def get_bootstrap_weights(config_dir: Optional[str] = None) -> BootstrapWeightsManager:
    """Get the bootstrap weights manager singleton"""
    global _bootstrap_manager
    if _bootstrap_manager is None:
        _bootstrap_manager = BootstrapWeightsManager(config_dir)
    return _bootstrap_manager


def reset_bootstrap_weights():
    """Reset the singleton (useful for testing)"""
    global _bootstrap_manager
    _bootstrap_manager = None


# ============================================================
# CLI for testing and verification
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Bootstrap Weights Manager')
    parser.add_argument('--config-dir', type=str, help='Path to config directory')
    parser.add_argument('--verify', action='store_true', help='Verify weights are loaded')
    parser.add_argument('--show', action='store_true', help='Show loaded weights')
    parser.add_argument('--test', action='store_true', help='Run test calculations')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Bootstrap Weights Manager")
    print("=" * 60)
    
    # Load weights
    manager = BootstrapWeightsManager(args.config_dir)
    
    if args.verify or args.show:
        print("\n📋 Configuration Summary:")
        summary = manager.get_config_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")
    
    if args.show:
        print("\n📊 Pillar Weights:")
        for pillar, weight in manager.get_pillar_weights().items():
            print(f"  {pillar}: {weight:.2f}")
        
        print("\n🎯 Critical KPIs:")
        for kpi in manager.get_critical_kpis():
            print(f"  - {kpi}")
        
        print("\n⚠️  Early Warning KPIs:")
        for kpi in manager.get_early_warning_kpis():
            print(f"  - {kpi}")
        
        print("\n📈 Thresholds:")
        for category, bounds in manager.get_thresholds().items():
            print(f"  {category}: {bounds['min']}-{bounds['max']}")
    
    if args.test:
        print("\n🧪 Test Calculations:")
        
        # Test weighted health calculation
        test_scores = {
            'P1_deployment': 85,
            'P2_stability': 72,
            'P3_performance': 68,
            'P4_channel': 90,
            'P5_expansion': 75
        }
        
        health = manager.calculate_weighted_health(test_scores)
        classification = manager.classify_health(health)
        
        print(f"\n  Input pillar scores: {test_scores}")
        print(f"  Weighted health: {health:.1f}")
        print(f"  Classification: {classification}")
    
    print("\n✅ Bootstrap weights loaded successfully!")
