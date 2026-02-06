#!/usr/bin/env python3
"""
DC2_S Vertical - Pillar Weights Configuration
Manages L1 (KPI → Pillar) and L2 (Pillar → Overall) weight configurations

Supports:
- Bootstrap weights from simulation
- Dynamic weight adjustment (learning loop)
- Weight history tracking
- Customer-specific weight overrides
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# ============================================================
# L2 WEIGHTS (Pillar → Overall Revenue Health Index)
# ============================================================

# Bootstrap weights from 100-account, 12-month simulation
BOOTSTRAP_L2_WEIGHTS = {
    "P1_deployment_velocity": 0.15,      # 15% - Important but not highest
    "P2_operational_stability": 0.20,    # 20% - Critical for retention
    "P3_ai_workload_performance": 0.25,  # 25% ⭐ HIGHEST - Top predictor
    "P4_channel_partner_health": 0.15,   # 15% - Important for indirect sales
    "P5_expansion_readiness": 0.25       # 25% ⭐ HIGHEST - Expansion driver
}

# Current active weights (start with bootstrap, updated by learning loop)
CURRENT_L2_WEIGHTS = BOOTSTRAP_L2_WEIGHTS.copy()

# ============================================================
# L1 WEIGHTS (KPI → Pillar Score)
# ============================================================

# Defined in kpi_definitions.py as weight_l1 for each KPI
# This module provides functions to retrieve and update them

# ============================================================
# WEIGHT CONFIGURATION
# ============================================================

class WeightConfig:
    """Manages weight configurations and updates"""
    
    def __init__(self, customer_id: Optional[int] = None):
        """
        Initialize weight configuration
        
        Args:
            customer_id: Optional customer ID for customer-specific weights
        """
        self.customer_id = customer_id
        self.l2_weights = BOOTSTRAP_L2_WEIGHTS.copy()
        self.l1_weight_overrides = {}  # Custom L1 weights per customer
        self.weight_history = []
        
    def get_l2_weight(self, pillar: str) -> float:
        """
        Get L2 weight for a pillar
        
        Args:
            pillar: Pillar key (e.g., 'P1_deployment_velocity')
            
        Returns:
            Weight value (0.0-1.0)
        """
        return self.l2_weights.get(pillar, 0.0)
    
    def get_l1_weight(self, kpi_code: str, pillar: str) -> float:
        """
        Get L1 weight for a KPI within its pillar
        
        Args:
            kpi_code: KPI code (e.g., 'P1-KPI1')
            pillar: Pillar the KPI belongs to
            
        Returns:
            Weight value (0.0-1.0)
        """
        # Check for customer-specific override first
        if kpi_code in self.l1_weight_overrides:
            return self.l1_weight_overrides[kpi_code]
        
        # Otherwise use default from kpi_definitions
        from .kpi_definitions import get_kpi_by_code
        kpi = get_kpi_by_code(kpi_code)
        return kpi.get('weight_l1', 0.0) if kpi else 0.0
    
    def update_l2_weights(self, new_weights: Dict[str, float], reason: str = ""):
        """
        Update L2 weights (learning loop adjustment)
        
        Args:
            new_weights: New pillar weights
            reason: Reason for update (for audit trail)
        """
        # Validate weights sum to ~1.0
        total = sum(new_weights.values())
        if not (0.95 <= total <= 1.05):
            raise ValueError(f"Weights must sum to ~1.0, got {total}")
        
        # Record in history
        self.weight_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "L2",
            "old_weights": self.l2_weights.copy(),
            "new_weights": new_weights.copy(),
            "reason": reason,
            "customer_id": self.customer_id
        })
        
        # Update weights
        self.l2_weights = new_weights.copy()
    
    def update_l1_weight(self, kpi_code: str, new_weight: float, reason: str = ""):
        """
        Update L1 weight for a specific KPI
        
        Args:
            kpi_code: KPI code to update
            new_weight: New weight value
            reason: Reason for update
        """
        old_weight = self.get_l1_weight(kpi_code, "")
        
        # Record in history
        self.weight_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "L1",
            "kpi_code": kpi_code,
            "old_weight": old_weight,
            "new_weight": new_weight,
            "reason": reason,
            "customer_id": self.customer_id
        })
        
        # Update weight
        self.l1_weight_overrides[kpi_code] = new_weight
    
    def reset_to_bootstrap(self):
        """Reset all weights to bootstrap values"""
        self.l2_weights = BOOTSTRAP_L2_WEIGHTS.copy()
        self.l1_weight_overrides = {}
        
        self.weight_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "RESET",
            "reason": "Reset to bootstrap weights",
            "customer_id": self.customer_id
        })
    
    def get_weight_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get weight update history
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of weight update records
        """
        return self.weight_history[-limit:]
    
    def export_config(self) -> Dict[str, Any]:
        """Export current weight configuration"""
        return {
            "customer_id": self.customer_id,
            "l2_weights": self.l2_weights,
            "l1_weight_overrides": self.l1_weight_overrides,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def import_config(self, config: Dict[str, Any]):
        """Import weight configuration"""
        self.customer_id = config.get("customer_id")
        self.l2_weights = config.get("l2_weights", BOOTSTRAP_L2_WEIGHTS.copy())
        self.l1_weight_overrides = config.get("l1_weight_overrides", {})

# ============================================================
# WEIGHT ADJUSTMENT STRATEGIES
# ============================================================

class WeightAdjuster:
    """Strategies for adjusting weights based on learning loop feedback"""
    
    @staticmethod
    def gradient_descent_adjustment(
        current_weights: Dict[str, float],
        gradients: Dict[str, float],
        learning_rate: float = 0.01
    ) -> Dict[str, float]:
        """
        Adjust weights using gradient descent
        
        Args:
            current_weights: Current weight values
            gradients: Gradient for each weight
            learning_rate: Learning rate (default 0.01)
            
        Returns:
            Adjusted weights (normalized to sum to 1.0)
        """
        adjusted = {}
        
        for key, weight in current_weights.items():
            gradient = gradients.get(key, 0.0)
            new_weight = weight - (learning_rate * gradient)
            # Clamp to reasonable range
            adjusted[key] = max(0.05, min(0.50, new_weight))
        
        # Normalize to sum to 1.0
        total = sum(adjusted.values())
        return {k: v / total for k, v in adjusted.items()}
    
    @staticmethod
    def performance_based_adjustment(
        current_weights: Dict[str, float],
        kpi_performance: Dict[str, float],
        adjustment_factor: float = 0.05
    ) -> Dict[str, float]:
        """
        Adjust weights based on KPI predictive performance
        
        Args:
            current_weights: Current weight values
            kpi_performance: Performance score for each KPI (0-1)
            adjustment_factor: How much to adjust (default 0.05)
            
        Returns:
            Adjusted weights
        """
        adjusted = {}
        
        for key, weight in current_weights.items():
            performance = kpi_performance.get(key, 0.5)
            
            # Increase weight if performance > 0.7, decrease if < 0.5
            if performance > 0.7:
                adjusted[key] = weight * (1 + adjustment_factor)
            elif performance < 0.5:
                adjusted[key] = weight * (1 - adjustment_factor)
            else:
                adjusted[key] = weight
            
            # Clamp
            adjusted[key] = max(0.05, min(0.50, adjusted[key]))
        
        # Normalize
        total = sum(adjusted.values())
        return {k: v / total for k, v in adjusted.items()}
    
    @staticmethod
    def transfer_learning_weights(
        source_weights: Dict[str, float],
        target_initial_weights: Dict[str, float],
        similarity_score: float = 0.8
    ) -> Dict[str, float]:
        """
        Transfer weights from source account to target account
        
        Args:
            source_weights: Learned weights from source account
            target_initial_weights: Initial weights for target
            similarity_score: How similar accounts are (0-1)
            
        Returns:
            Blended weights for target account
        """
        blended = {}
        
        for key in target_initial_weights.keys():
            source_val = source_weights.get(key, target_initial_weights[key])
            target_val = target_initial_weights[key]
            
            # Blend based on similarity
            blended[key] = (source_val * similarity_score) + (target_val * (1 - similarity_score))
        
        # Normalize
        total = sum(blended.values())
        return {k: v / total for k, v in blended.items()}

# ============================================================
# CONVERGENCE TRACKING
# ============================================================

class ConvergenceTracker:
    """Tracks weight convergence over time"""
    
    def __init__(self):
        self.convergence_history = []
        self.target_accuracy = 0.85  # 85% target from requirements
    
    def record_iteration(
        self,
        iteration: int,
        month: int,
        accuracy: float,
        weights: Dict[str, float],
        account_id: Optional[int] = None
    ):
        """
        Record a learning iteration
        
        Args:
            iteration: Iteration number
            month: Month number (1-12)
            accuracy: Prediction accuracy (0-1)
            weights: Current weights
            account_id: Optional account ID
        """
        self.convergence_history.append({
            "iteration": iteration,
            "month": month,
            "accuracy": accuracy,
            "weights": weights.copy(),
            "account_id": account_id,
            "timestamp": datetime.utcnow().isoformat(),
            "converged": accuracy >= self.target_accuracy
        })
    
    def get_current_accuracy(self) -> float:
        """Get most recent accuracy score"""
        if not self.convergence_history:
            return 0.0
        return self.convergence_history[-1].get("accuracy", 0.0)
    
    def is_converged(self) -> bool:
        """Check if weights have converged to target"""
        return self.get_current_accuracy() >= self.target_accuracy
    
    def get_convergence_month(self) -> Optional[int]:
        """Get the month when convergence was reached"""
        for record in self.convergence_history:
            if record.get("converged", False):
                return record.get("month")
        return None
    
    def get_convergence_stats(self) -> Dict[str, Any]:
        """Get convergence statistics"""
        if not self.convergence_history:
            return {
                "total_iterations": 0,
                "current_accuracy": 0.0,
                "converged": False
            }
        
        return {
            "total_iterations": len(self.convergence_history),
            "current_accuracy": self.get_current_accuracy(),
            "converged": self.is_converged(),
            "convergence_month": self.get_convergence_month(),
            "target_accuracy": self.target_accuracy,
            "starting_accuracy": self.convergence_history[0].get("accuracy", 0.0)
        }
    
    def export_history(self) -> List[Dict[str, Any]]:
        """Export full convergence history"""
        return self.convergence_history.copy()

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_bootstrap_weights() -> Dict[str, float]:
    """Get bootstrap L2 weights from simulation"""
    return BOOTSTRAP_L2_WEIGHTS.copy()

# Short pillar codes used in DC2S_KPIS (kpi_definitions) and in health calculation
PILLAR_SHORT = ("P1", "P2", "P3", "P4", "P5")
# Long keys in BOOTSTRAP_L2_WEIGHTS
PILLAR_LONG_TO_SHORT = {
    "P1_deployment_velocity": "P1",
    "P2_operational_stability": "P2",
    "P3_ai_workload_performance": "P3",
    "P4_channel_partner_health": "P4",
    "P5_expansion_readiness": "P5",
}
# DB config (CustomerConfig.dc2s_pillar_weights) uses AI, CH, DV, EX, OS
PILLAR_SHORT_TO_DB = {"P1": "DV", "P2": "OS", "P3": "AI", "P4": "CH", "P5": "EX"}
PILLAR_DB_TO_SHORT = {v: k for k, v in PILLAR_SHORT_TO_DB.items()}


def get_current_weights() -> Dict[str, Any]:
    """Get current active L2 weights in format expected by calculate_kpi_health: {P1: {weight: w}, ...}"""
    return {
        PILLAR_LONG_TO_SHORT.get(k, k): {"weight": v}
        for k, v in CURRENT_L2_WEIGHTS.items()
    }


def get_weights_for_customer(customer_id: Optional[int]) -> Dict[str, Any]:
    """
    Get L2 pillar weights for a customer from DB (CustomerConfig) when available.
    Returns format: {P1: {weight: w}, P2: {weight: w}, ...}.
    Falls back to code bootstrap weights and logs explicitly.
    """
    import logging
    log = logging.getLogger(__name__)
    if not customer_id:
        log.debug("FALLBACK: No customer_id provided; using code default L2 weights (get_current_weights)")
        return get_current_weights()
    try:
        from models import CustomerConfig
        config = CustomerConfig.query.filter_by(customer_id=int(customer_id)).first()
        if not config or config.vertical != "dc2_s":
            log.info(
                "FALLBACK: Using code default L2 weights (no CustomerConfig or vertical != dc2_s). "
                "customer_id=%s, config_exists=%s, vertical=%s",
                customer_id, config is not None, getattr(config, "vertical", None)
            )
            return get_current_weights()
        db_weights = config.dc2s_pillar_weights or {}
        if not db_weights:
            log.info(
                "FALLBACK: Using code default L2 weights (CustomerConfig.dc2s_pillar_weights empty). customer_id=%s",
                customer_id
            )
            return get_current_weights()
        # Map DB keys (AI, CH, DV, EX, OS) to short (P1-P5) for calculate_kpi_health
        out = {}
        for short, db_key in PILLAR_SHORT_TO_DB.items():
            w = db_weights.get(db_key)
            if w is not None:
                out[short] = {"weight": float(w)}
            else:
                out[short] = {"weight": 0.2}
        log.info(
            "Config-aware: Using CustomerConfig.dc2s_pillar_weights for customer_id=%s (L2 weights from DB)",
            customer_id
        )
        return out
    except Exception as e:
        log.warning(
            "FALLBACK: Using code default L2 weights after error loading CustomerConfig. customer_id=%s, error=%s",
            customer_id, e
        )
        return get_current_weights()

def calculate_weight_drift(
    old_weights: Dict[str, float],
    new_weights: Dict[str, float]
) -> float:
    """
    Calculate total drift between two weight configurations
    
    Args:
        old_weights: Previous weights
        new_weights: New weights
        
    Returns:
        Total absolute drift
    """
    drift = 0.0
    for key in old_weights.keys():
        old_val = old_weights.get(key, 0.0)
        new_val = new_weights.get(key, 0.0)
        drift += abs(new_val - old_val)
    
    return drift

def validate_weights(weights: Dict[str, float]) -> bool:
    """
    Validate weight configuration
    
    Args:
        weights: Weight dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Check sum is approximately 1.0
    total = sum(weights.values())
    if not (0.95 <= total <= 1.05):
        return False
    
    # Check all values are positive and reasonable
    for value in weights.values():
        if not (0.0 <= value <= 1.0):
            return False
    
    return True

# ============================================================
# METADATA
# ============================================================

WEIGHT_METADATA = {
    "bootstrap_source": "100-account, 12-month simulation",
    "bootstrap_accuracy": 0.88,  # Final simulation accuracy
    "convergence_month": 6,  # Month 6-7 in simulation
    "target_accuracy": 0.85,
    "learning_rate_default": 0.01,
    "adjustment_strategies": ["gradient_descent", "performance_based", "transfer_learning"],
    "version": "1.0.0"
}
