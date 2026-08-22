#!/usr/bin/env python3
"""
Bootstrap Weights Loader (FIXED)
================================

Loads and manages bootstrap weights for the Signal Analyst.
Bootstrap weights provide initial prediction accuracy (~70%) before
the system learns from actual data.

FIX: Now handles both 'pillar_weights' and 'pillar_weights_L2' keys
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

# Vertical-agnostic fallback pillar weights.
#
# IMPORTANT: this module is the shared PROVISIONING TEMPLATE
# (verticals/_template/services/bootstrap_weights_loader.py) — it gets
# copied verbatim into every newly-provisioned customer directory
# regardless of vertical (see verticals/provision_dc_customer.py, invoked
# with vertical_slug=<the customer's actual vertical> from both
# mcp_server/cs_pulse_onboarding.py::create_customer and
# onboarding_api_v2_config_aware.py). Hardcoding dc2_s's pillar weights
# here would make every new saas_premium/datacenter_v1/etc. customer
# silently inherit dc2_s's canonical weights as its "single source of
# truth" default — the exact bug class this refactor exists to prevent.
#
# Real per-vertical weights are resolved lazily by
# _canonical_pillar_weights_for(vertical) once the vertical is known (from
# the loaded bootstrap_weights_config.json). The module-level constants
# below are only the last-resort default before any config has been
# loaded, or when the vertical genuinely can't be resolved.
_GENERIC_FALLBACK_PILLAR_WEIGHTS = {'P1': 0.20, 'P2': 0.20, 'P3': 0.20, 'P4': 0.20, 'P5': 0.20}


def _canonical_pillar_weights_for(vertical: str) -> Dict[str, float]:
    """Resolve default L2 pillar weights for a vertical via the registry.

    Routes through utils.vertical_registry.get_default_pillar_weights so
    each vertical (dc2_s, saas_premium, datacenter_v1, or any future
    JSON-catalog vertical) gets its OWN canonical weights instead of
    silently inheriting dc2_s's. Falls back to an equal-weight generic
    default only if the registry can't resolve the vertical at all (e.g.
    vertical is 'unknown', or the registry import fails) — this must not
    hard-crash a brand-new customer's onboarding just because weights
    aren't resolvable yet.
    """
    try:
        from utils.vertical_registry import get_default_pillar_weights
        weights = get_default_pillar_weights(vertical)
        if weights:
            return weights
    except Exception:
        pass
    return dict(_GENERIC_FALLBACK_PILLAR_WEIGHTS)


# Load health thresholds from centralized config
try:
    import utils.health_thresholds as _ht
    _HEALTHY_MIN = _ht.healthy_min()
    _AT_RISK_MIN = _ht.at_risk_min()
except ImportError:
    _HEALTHY_MIN = 70
    _AT_RISK_MIN = 50

_CANONICAL_PILLAR_WEIGHTS = dict(_GENERIC_FALLBACK_PILLAR_WEIGHTS)
_DEFAULT_PILLAR_WEIGHT = sum(_CANONICAL_PILLAR_WEIGHTS.values()) / len(_CANONICAL_PILLAR_WEIGHTS)


@dataclass
class KPIWeight:
    """Individual KPI weight configuration"""
    kpi_id: str
    name: str
    pillar: str
    weight: float
    importance_rank: int
    description: str = ""


@dataclass
class PillarWeight:
    """Pillar-level weight configuration"""
    pillar_id: str
    name: str
    weight: float
    kpis: List[KPIWeight] = field(default_factory=list)


@dataclass
class BootstrapConfig:
    """Complete bootstrap weights configuration"""
    version: str
    vertical: str
    pillars: Dict[str, PillarWeight] = field(default_factory=dict)
    scenario_adjustments: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    @property
    def total_kpis(self) -> int:
        return sum(len(p.kpis) for p in self.pillars.values())


class BootstrapWeightsLoader:
    """
    Loads and manages bootstrap weights from configuration files.
    
    Usage:
        loader = BootstrapWeightsLoader()
        loader.load_config('/path/to/bootstrap_weights_config.json')
        
        # Get weight for specific KPI
        weight = loader.get_kpi_weight('GPU_UTILIZATION')
        
        # Calculate weighted health score
        score = loader.calculate_weighted_health(kpi_values)
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config: Optional[BootstrapConfig] = None
        self.kpi_weights: Dict[str, float] = {}
        self.pillar_weights: Dict[str, float] = {}
        self.kpi_to_pillar: Dict[str, str] = {}
        # Vertical-resolved canonical weights (see _canonical_pillar_weights_for).
        # Start with the generic equal-weight fallback; load_config() will
        # re-resolve these once the config's 'vertical' field is known.
        self._canonical_pillar_weights: Dict[str, float] = dict(_CANONICAL_PILLAR_WEIGHTS)
        self._default_pillar_weight: float = _DEFAULT_PILLAR_WEIGHT

        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> bool:
        """
        Load bootstrap weights from JSON configuration file.
        
        Args:
            config_path: Path to bootstrap_weights_config.json
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            # Extract version and vertical
            version = data.get('version', '1.0')
            vertical = data.get('vertical', 'unknown')

            # Re-resolve canonical pillar weights for THIS vertical now that
            # it's known (routes through utils.vertical_registry — see
            # _canonical_pillar_weights_for() above).
            self._canonical_pillar_weights = _canonical_pillar_weights_for(vertical)
            self._default_pillar_weight = (
                sum(self._canonical_pillar_weights.values()) / len(self._canonical_pillar_weights)
                if self._canonical_pillar_weights else _DEFAULT_PILLAR_WEIGHT
            )

            # FIX: Handle both 'pillar_weights' and 'pillar_weights_L2' keys
            pillar_data = data.get('pillar_weights') or data.get('pillar_weights_L2') or {}
            
            # FIX: Handle both 'kpi_weights' and 'kpi_weights_L1' keys
            kpi_weights_data = data.get('kpi_weights') or data.get('kpi_weights_L1') or {}
            
            if not pillar_data:
                print(f"Warning: No pillar weights found in config. Checked keys: pillar_weights, pillar_weights_L2")
                print(f"Available keys in config: {list(data.keys())}")
            
            # Parse pillars
            pillars = {}
            for pillar_id, pillar_info in pillar_data.items():
                # Handle different config formats
                if isinstance(pillar_info, dict):
                    pillar_weight = pillar_info.get('weight', pillar_info.get('pillar_weight', self._canonical_pillar_weights.get(pillar_id, self._default_pillar_weight)))
                    pillar_name = pillar_info.get('name', pillar_id)
                    kpi_list = pillar_info.get('kpis', pillar_info.get('kpi_weights', []))
                else:
                    # Simple format: just a weight value
                    pillar_weight = float(pillar_info)
                    pillar_name = pillar_id
                    kpi_list = []
                
                # FIX: If kpi_list is empty, try to get KPIs from kpi_weights_L1
                if not kpi_list and pillar_id in kpi_weights_data:
                    kpi_list = kpi_weights_data[pillar_id]
                
                # Parse KPIs within pillar
                kpis = []
                if isinstance(kpi_list, dict):
                    # Dict format: {kpi_id: weight}
                    for kpi_id, kpi_weight in kpi_list.items():
                        kpi = KPIWeight(
                            kpi_id=kpi_id,
                            name=kpi_id.replace('_', ' ').title(),
                            pillar=pillar_id,
                            weight=float(kpi_weight) if not isinstance(kpi_weight, dict) else kpi_weight.get('weight', 0.1),
                            importance_rank=0
                        )
                        kpis.append(kpi)
                        self.kpi_weights[kpi_id] = kpi.weight
                        self.kpi_to_pillar[kpi_id] = pillar_id
                elif isinstance(kpi_list, list):
                    # List format: [{kpi_id, weight, ...}, ...]
                    for idx, kpi_info in enumerate(kpi_list):
                        if isinstance(kpi_info, dict):
                            kpi_id = kpi_info.get('kpi_id', kpi_info.get('id', f'kpi_{idx}'))
                            kpi = KPIWeight(
                                kpi_id=kpi_id,
                                name=kpi_info.get('name', kpi_id.replace('_', ' ').title()),
                                pillar=pillar_id,
                                weight=kpi_info.get('weight', 0.1),
                                importance_rank=kpi_info.get('importance_rank', idx + 1),
                                description=kpi_info.get('description', '')
                            )
                            kpis.append(kpi)
                            self.kpi_weights[kpi_id] = kpi.weight
                            self.kpi_to_pillar[kpi_id] = pillar_id
                
                pillars[pillar_id] = PillarWeight(
                    pillar_id=pillar_id,
                    name=pillar_name,
                    weight=pillar_weight,
                    kpis=kpis
                )
                self.pillar_weights[pillar_id] = pillar_weight
            
            # Parse scenario adjustments if present
            scenario_adjustments = data.get('scenario_adjustments', {})
            
            self.config = BootstrapConfig(
                version=version,
                vertical=vertical,
                pillars=pillars,
                scenario_adjustments=scenario_adjustments
            )
            
            print(f"✅ Loaded bootstrap config v{version} for {vertical}")
            print(f"   Pillars: {len(pillars)}")
            print(f"   Total KPIs: {self.config.total_kpis}")
            
            return True
            
        except FileNotFoundError:
            print(f"❌ Config file not found: {config_path}")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in config file: {e}")
            return False
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return False
    
    def get_kpi_weight(self, kpi_id: str, default: float = 0.1) -> float:
        """Get weight for a specific KPI"""
        return self.kpi_weights.get(kpi_id, default)
    
    def get_pillar_weight(self, pillar_id: str, default: float = None) -> float:
        """Get weight for a specific pillar"""
        if default is None:
            default = self._canonical_pillar_weights.get(pillar_id, self._default_pillar_weight)
        return self.pillar_weights.get(pillar_id, default)
    
    def get_kpi_pillar(self, kpi_id: str) -> Optional[str]:
        """Get the pillar that a KPI belongs to"""
        return self.kpi_to_pillar.get(kpi_id)
    
    @property
    def is_loaded(self) -> bool:
        """Check if config is loaded"""
        return self.config is not None
    
    def get_pillar_weights(self) -> Dict[str, float]:
        """Get all pillar weights (for test compatibility)"""
        return self.pillar_weights.copy()
    
    def get_thresholds(self) -> Dict[str, Dict[str, int]]:
        """Get health score thresholds (from centralized config)"""
        return {
            'healthy': {'min': _HEALTHY_MIN, 'max': 100},
            'at_risk': {'min': _AT_RISK_MIN, 'max': _HEALTHY_MIN - 1},
            'crisis': {'min': 0, 'max': _AT_RISK_MIN - 1}
        }
    
    def get_critical_kpis(self) -> List[str]:
        """Get list of critical KPIs"""
        # Return top weighted KPIs as critical
        top_kpis = self.get_top_weighted_kpis(5)
        return [kpi['kpi_id'] for kpi in top_kpis]
    
    def classify_health(self, score: float) -> str:
        """
        Classify health score into category.
        
        Args:
            score: Health score (0-100)
            
        Returns:
            'healthy', 'at_risk', or 'crisis'
        """
        thresholds = self.get_thresholds()
        
        if score >= thresholds['healthy']['min']:
            return 'healthy'
        elif score >= thresholds['at_risk']['min']:
            return 'at_risk'
        else:
            return 'crisis'
    
    def get_all_kpi_weights(self) -> Dict[str, Dict[str, float]]:
        """
        Get all KPI weights organized by pillar (for test compatibility).
        
        Returns:
            Dict of {pillar_id: {kpi_id: weight}}
        """
        result = {}
        if not self.config:
            return result
        
        for pillar_id, pillar in self.config.pillars.items():
            result[pillar_id] = {}
            for kpi in pillar.kpis:
                result[pillar_id][kpi.kpi_id] = kpi.weight
        
        return result
    
    def calculate_weighted_health(
        self, 
        kpi_values: Dict[str, float],
        scenario: str = 'normal'
    ) -> float:
        """
        Calculate weighted health score from KPI values or pillar scores.
        
        Args:
            kpi_values: Dict of {kpi_id: normalized_value (0-100)} OR {pillar_id: score (0-100)}
            scenario: 'normal', 'crisis', or 'expansion'
            
        Returns:
            Health score (0-100) as float, or dict if called with full signature
        """
        if not self.config:
            return 50.0
        
        # Check if input is pillar scores (keys start with 'P' and have underscore)
        is_pillar_scores = all(key.startswith('P') and '_' in key for key in kpi_values.keys())
        
        if is_pillar_scores:
            # Direct pillar scores - just calculate weighted average
            total_weight = sum(self.pillar_weights.get(p, self._canonical_pillar_weights.get(p, self._default_pillar_weight)) for p in kpi_values.keys())
            if total_weight > 0:
                health_score = sum(
                    score * self.pillar_weights.get(pillar, self._canonical_pillar_weights.get(pillar, self._default_pillar_weight))
                    for pillar, score in kpi_values.items()
                ) / total_weight
            else:
                health_score = sum(kpi_values.values()) / len(kpi_values) if kpi_values else 50.0
            return health_score
        
        # Get scenario adjustments
        adjustments = self.config.scenario_adjustments.get(scenario, {})
        
        # Calculate pillar scores
        pillar_scores = {}
        for pillar_id, pillar in self.config.pillars.items():
            pillar_kpi_values = []
            pillar_kpi_weights = []
            
            for kpi in pillar.kpis:
                if kpi.kpi_id in kpi_values:
                    value = kpi_values[kpi.kpi_id]
                    weight = kpi.weight
                    
                    # Apply scenario adjustment if exists
                    if kpi.kpi_id in adjustments:
                        weight *= adjustments[kpi.kpi_id]
                    
                    pillar_kpi_values.append(value)
                    pillar_kpi_weights.append(weight)
            
            if pillar_kpi_values:
                # Weighted average within pillar
                total_weight = sum(pillar_kpi_weights)
                if total_weight > 0:
                    pillar_score = sum(v * w for v, w in zip(pillar_kpi_values, pillar_kpi_weights)) / total_weight
                else:
                    pillar_score = sum(pillar_kpi_values) / len(pillar_kpi_values)
                pillar_scores[pillar_id] = pillar_score
        
        # Calculate overall health score (weighted by pillar weights)
        if pillar_scores:
            total_pillar_weight = sum(self.pillar_weights.get(p, self._canonical_pillar_weights.get(p, self._default_pillar_weight)) for p in pillar_scores)
            if total_pillar_weight > 0:
                health_score = sum(
                    score * self.pillar_weights.get(pillar, self._canonical_pillar_weights.get(pillar, self._default_pillar_weight))
                    for pillar, score in pillar_scores.items()
                ) / total_pillar_weight
            else:
                health_score = sum(pillar_scores.values()) / len(pillar_scores)
        else:
            # Fallback: simple average of all KPIs
            if kpi_values:
                health_score = sum(kpi_values.values()) / len(kpi_values)
            else:
                health_score = 50.0
        
        # Classify health (using centralized thresholds)
        if health_score >= _HEALTHY_MIN:
            classification = 'healthy'
        elif health_score >= _AT_RISK_MIN:
            classification = 'at_risk'
        else:
            classification = 'crisis'
        
        return {
            'health_score': round(health_score, 1),
            'classification': classification,
            'pillar_scores': {k: round(v, 1) for k, v in pillar_scores.items()},
            'kpis_used': len(kpi_values),
            'scenario': scenario
        }
    
    def get_top_weighted_kpis(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get the top N KPIs by weight"""
        sorted_kpis = sorted(
            self.kpi_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n]
        
        return [
            {
                'kpi_id': kpi_id,
                'weight': weight,
                'pillar': self.kpi_to_pillar.get(kpi_id, 'unknown')
            }
            for kpi_id, weight in sorted_kpis
        ]
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate the loaded configuration"""
        issues = []
        
        if not self.config:
            return {'valid': False, 'issues': ['No config loaded']}
        
        # Check pillar weights sum to ~1.0
        pillar_sum = sum(self.pillar_weights.values())
        if abs(pillar_sum - 1.0) > 0.01:
            issues.append(f"Pillar weights sum to {pillar_sum:.2f}, expected ~1.0")
        
        # Check each pillar has KPIs
        for pillar_id, pillar in self.config.pillars.items():
            if not pillar.kpis:
                issues.append(f"Pillar '{pillar_id}' has no KPIs defined")
        
        # Check KPI weights within pillars
        for pillar_id, pillar in self.config.pillars.items():
            if pillar.kpis:
                kpi_sum = sum(k.weight for k in pillar.kpis)
                if abs(kpi_sum - 1.0) > 0.1:
                    issues.append(f"KPI weights in '{pillar_id}' sum to {kpi_sum:.2f}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'stats': {
                'pillars': len(self.config.pillars),
                'total_kpis': self.config.total_kpis,
                'pillar_weight_sum': round(pillar_sum, 2)
            }
        }


# ============================================================
# Convenience Functions
# ============================================================

# Singleton instance for compatibility
_bootstrap_loader_instance: Optional[BootstrapWeightsLoader] = None

def get_bootstrap_weights(config_dir: str = None) -> BootstrapWeightsLoader:
    """
    Get bootstrap weights loader singleton (for test compatibility).
    
    Args:
        config_dir: Directory containing bootstrap_weights_config.json
    
    Returns:
        BootstrapWeightsLoader instance
    """
    global _bootstrap_loader_instance
    if _bootstrap_loader_instance is None:
        _bootstrap_loader_instance = load_bootstrap_weights(config_dir)
    return _bootstrap_loader_instance

def reset_bootstrap_weights():
    """Reset the singleton (for testing)"""
    global _bootstrap_loader_instance
    _bootstrap_loader_instance = None

def load_bootstrap_weights(config_dir: str = None) -> BootstrapWeightsLoader:
    """
    Load bootstrap weights from default or specified directory.
    
    Args:
        config_dir: Directory containing bootstrap_weights_config.json
                   Defaults to ./config or ./journey/config
    
    Returns:
        Initialized BootstrapWeightsLoader
    """
    loader = BootstrapWeightsLoader()
    
    # Try common config locations
    search_paths = [
        config_dir,
        './config',
        './journey/config',
        '../config',
        './data/bootstrap',
        os.path.join(os.path.dirname(__file__), 'config'),
    ]
    
    config_file = 'bootstrap_weights_config.json'
    
    for path in search_paths:
        if path:
            full_path = os.path.join(path, config_file)
            if os.path.exists(full_path):
                loader.load_config(full_path)
                break
    
    return loader


# ============================================================
# Test / Demo
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Bootstrap Weights Loader Test")
    print("=" * 60)
    
    # Try to load config
    loader = load_bootstrap_weights()
    
    if loader.config:
        # Validate
        validation = loader.validate_config()
        print(f"\nValidation: {'✅ PASS' if validation['valid'] else '❌ FAIL'}")
        for issue in validation.get('issues', []):
            print(f"  - {issue}")
        
        # Show top KPIs
        print("\nTop 5 Weighted KPIs:")
        for kpi in loader.get_top_weighted_kpis(5):
            print(f"  {kpi['kpi_id']}: {kpi['weight']:.3f} ({kpi['pillar']})")
        
        # Test health calculation
        print("\nTest Health Calculations:")
        
        # Healthy scenario
        healthy_kpis = {kpi: 85.0 for kpi in list(loader.kpi_weights.keys())[:10]}
        result = loader.calculate_weighted_health(healthy_kpis)
        print(f"  Healthy case: score={result['health_score']}, class={result['classification']}")
        
        # At-risk scenario
        atrisk_kpis = {kpi: 55.0 for kpi in list(loader.kpi_weights.keys())[:10]}
        result = loader.calculate_weighted_health(atrisk_kpis)
        print(f"  At-risk case: score={result['health_score']}, class={result['classification']}")
        
        # Crisis scenario
        crisis_kpis = {kpi: 25.0 for kpi in list(loader.kpi_weights.keys())[:10]}
        result = loader.calculate_weighted_health(crisis_kpis)
        print(f"  Crisis case:  score={result['health_score']}, class={result['classification']}")
    else:
        print("\n❌ No config file found. Please specify config directory.")
        print("   Usage: loader = BootstrapWeightsLoader('/path/to/config/bootstrap_weights_config.json')")
