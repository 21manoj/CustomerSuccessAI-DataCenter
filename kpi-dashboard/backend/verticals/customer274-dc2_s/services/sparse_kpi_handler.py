#!/usr/bin/env python3
"""
Sparse KPI Handler - Handles accounts with incomplete KPI data (10-15 KPIs instead of 35).
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

PILLAR_WEIGHTS = {
    'P1_deployment_velocity': 10,
    'P2_operational_stability': 30,
    'P3_ai_workload_performance': 30,
    'P4_channel_partner_health': 5,
    'P5_expansion_revenue': 25,
}

KPI_PILLAR_MAP = {
    'p1_time_to_first_gpu': 'P1_deployment_velocity',
    'p1_rack_deployment_rate': 'P1_deployment_velocity',
    'p1_config_accuracy': 'P1_deployment_velocity',
    'p1_provisioning_success': 'P1_deployment_velocity',
    'p1_deployment_checklist': 'P1_deployment_velocity',
    'p1_initial_validation': 'P1_deployment_velocity',
    'p2_mtbf': 'P2_operational_stability',
    'p2_mttr': 'P2_operational_stability',
    'p2_critical_incident_rate': 'P2_operational_stability',
    'p2_rma_rate': 'P2_operational_stability',
    'p2_uptime': 'P2_operational_stability',
    'p2_thermal_compliance': 'P2_operational_stability',
    'p2_power_efficiency': 'P2_operational_stability',
    'p3_gpu_utilization': 'P3_ai_workload_performance',
    'p3_inference_latency': 'P3_ai_workload_performance',
    'p3_training_throughput': 'P3_ai_workload_performance',
    'p3_model_accuracy': 'P3_ai_workload_performance',
    'p3_gpu_memory_utilization': 'P3_ai_workload_performance',
    'p3_job_completion_rate': 'P3_ai_workload_performance',
    'p4_partner_nps': 'P4_channel_partner_health',
    'p4_support_ticket_resolution': 'P4_channel_partner_health',
    'p4_partner_certification': 'P4_channel_partner_health',
    'p4_joint_engagement': 'P4_channel_partner_health',
    'p4_escalation_rate': 'P4_channel_partner_health',
    'p4_communication_score': 'P4_channel_partner_health',
    'p5_capacity_utilization': 'P5_expansion_revenue',
    'p5_expansion_pipeline': 'P5_expansion_revenue',
    'p5_contract_renewal_likelihood': 'P5_expansion_revenue',
    'p5_upsell_conversion': 'P5_expansion_revenue',
    'p5_gpu_growth_rate': 'P5_expansion_revenue',
    'p5_budget_utilization': 'P5_expansion_revenue',
    'p5_roi_achievement': 'P5_expansion_revenue',
    'p5_strategic_alignment': 'P5_expansion_revenue',
}

KPI_ALIASES = {
    'mtbf': 'p2_mtbf', 'mttr': 'p2_mttr',
    'gpu_utilization': 'p3_gpu_utilization',
    'gpu_utilization_rate': 'p3_gpu_utilization',
    'critical_incident_rate': 'p2_critical_incident_rate',
    'rma_rate': 'p2_rma_rate', 'uptime': 'p2_uptime',
    'inference_latency': 'p3_inference_latency',
    'capacity_utilization': 'p5_capacity_utilization',
    'expansion_pipeline': 'p5_expansion_pipeline',
}

class DataQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    LOW = "low"
    CRITICAL = "critical"

@dataclass
class SparseKPIResult:
    health_score: float
    pillar_scores: Dict[str, float]
    pillar_weights_used: Dict[str, float]
    available_kpis: List[str]
    missing_kpis: List[str]
    coverage_pct: float
    data_quality: DataQuality
    pillars_with_data: List[str]
    pillars_without_data: List[str]
    confidence: float

@dataclass
class KPICoverage:
    account_id: str
    available_kpis: Set[str] = field(default_factory=set)
    kpi_values: Dict[str, float] = field(default_factory=dict)
    raw_values: Dict[str, Tuple[float, str]] = field(default_factory=dict)
    
    @property
    def total_kpis(self) -> int: return len(KPI_PILLAR_MAP)
    @property
    def coverage_count(self) -> int: return len(self.available_kpis)
    @property
    def coverage_pct(self) -> float: return (self.coverage_count / self.total_kpis) * 100

class SparseKPIHandler:
    def __init__(self): self.accounts: Dict[str, KPICoverage] = {}
    
    def _resolve_kpi_code(self, kpi_code: str) -> str:
        code = kpi_code.lower().strip()
        return KPI_ALIASES.get(code, code)
    
    def _get_or_create_account(self, account_id: str) -> KPICoverage:
        if account_id not in self.accounts:
            self.accounts[account_id] = KPICoverage(account_id=account_id)
        return self.accounts[account_id]
    
    def set_kpi(self, account_id: str, kpi_code: str, normalized_value: float, raw_value: Optional[Tuple[float, str]] = None):
        code = self._resolve_kpi_code(kpi_code)
        account = self._get_or_create_account(account_id)
        account.available_kpis.add(code)
        account.kpi_values[code] = normalized_value
        if raw_value: account.raw_values[code] = raw_value
    
    def set_kpis_batch(self, account_id: str, kpis: Dict[str, float], raw_kpis: Optional[Dict[str, Tuple[float, str]]] = None):
        for kpi_code, value in kpis.items():
            raw = raw_kpis.get(kpi_code) if raw_kpis else None
            self.set_kpi(account_id, kpi_code, value, raw)
    
    def calculate_health(self, account_id: str) -> SparseKPIResult:
        account = self._get_or_create_account(account_id)
        pillar_kpis: Dict[str, List[Tuple[str, float]]] = {p: [] for p in PILLAR_WEIGHTS.keys()}
        
        for kpi_code in account.available_kpis:
            if kpi_code in KPI_PILLAR_MAP:
                pillar = KPI_PILLAR_MAP[kpi_code]
                value = account.kpi_values.get(kpi_code, 0)
                pillar_kpis[pillar].append((kpi_code, value))
        
        pillar_scores: Dict[str, float] = {}
        pillars_with_data, pillars_without_data = [], []
        
        for pillar, kpis in pillar_kpis.items():
            if kpis:
                pillar_scores[pillar] = sum(v for _, v in kpis) / len(kpis)
                pillars_with_data.append(pillar)
            else:
                pillar_scores[pillar] = 0
                pillars_without_data.append(pillar)
        
        total_available_weight = sum(PILLAR_WEIGHTS[p] for p in pillars_with_data)
        if total_available_weight > 0:
            renormalized_weights = {p: (PILLAR_WEIGHTS[p] / total_available_weight) * 100 for p in pillars_with_data}
            for p in pillars_without_data: renormalized_weights[p] = 0
        else:
            renormalized_weights = {p: 0 for p in PILLAR_WEIGHTS.keys()}
        
        health_score = sum(pillar_scores[p] * (renormalized_weights[p] / 100) for p in PILLAR_WEIGHTS.keys())
        all_kpis = set(KPI_PILLAR_MAP.keys())
        missing_kpis = list(all_kpis - account.available_kpis)
        coverage_pct = account.coverage_pct
        
        if coverage_pct >= 70: data_quality = DataQuality.EXCELLENT
        elif coverage_pct >= 40: data_quality = DataQuality.GOOD
        elif coverage_pct >= 20: data_quality = DataQuality.LOW
        else: data_quality = DataQuality.CRITICAL
        
        confidence = min(1.0, coverage_pct / 50)
        
        return SparseKPIResult(
            health_score=round(health_score, 1), pillar_scores={p: round(s, 1) for p, s in pillar_scores.items()},
            pillar_weights_used=renormalized_weights, available_kpis=list(account.available_kpis),
            missing_kpis=missing_kpis, coverage_pct=round(coverage_pct, 1), data_quality=data_quality,
            pillars_with_data=pillars_with_data, pillars_without_data=pillars_without_data, confidence=round(confidence, 2)
        )
    
    def clear_account(self, account_id: str):
        if account_id in self.accounts: del self.accounts[account_id]
    
    def select_sparse_kpis(self, pattern: str = 'typical', required_kpis: Optional[List[str]] = None) -> List[str]:
        """Select a subset of KPIs based on pattern for sparse data scenarios."""
        import random
        
        all_kpis = list(KPI_PILLAR_MAP.keys())
        required = set([self._resolve_kpi_code(k) for k in (required_kpis or [])])
        
        # Pattern-based selection
        if pattern == 'typical':
            # Select 10-20 KPIs, ensuring at least 1 per pillar
            target_count = random.randint(10, 20)
            
            # Start with required KPIs
            selected = set(required)
            
            # Ensure at least one KPI per pillar
            pillars_covered = set()
            for kpi in all_kpis:
                if kpi in KPI_PILLAR_MAP:
                    pillar = KPI_PILLAR_MAP[kpi]
                    if pillar not in pillars_covered:
                        selected.add(kpi)
                        pillars_covered.add(pillar)
            
            # Add more KPIs from each pillar proportionally
            pillar_kpis = {p: [k for k in all_kpis if KPI_PILLAR_MAP.get(k) == p] 
                          for p in PILLAR_WEIGHTS.keys()}
            
            remaining = target_count - len(selected)
            if remaining > 0:
                # Distribute remaining KPIs based on pillar weights
                available = [k for k in all_kpis if k not in selected]
                random.shuffle(available)
                selected.update(available[:remaining])
        
        elif pattern == 'minimal':
            # Minimal: 5-10 KPIs, ensure critical ones
            target_count = random.randint(5, 10)
            critical = ['p2_mtbf', 'p2_uptime', 'p3_gpu_utilization', 
                       'p5_capacity_utilization', 'p5_expansion_pipeline']
            selected = set([self._resolve_kpi_code(k) for k in critical])
            available = [k for k in all_kpis if k not in selected]
            random.shuffle(available)
            selected.update(available[:target_count - len(selected)])
        
        elif pattern == 'comprehensive':
            # Comprehensive: 25-33 KPIs (most KPIs)
            target_count = random.randint(25, len(all_kpis))
            selected = set(required)
            available = [k for k in all_kpis if k not in selected]
            random.shuffle(available)
            selected.update(available[:target_count - len(selected)])
        
        else:
            # Default: return all KPIs
            selected = set(all_kpis)
        
        # Ensure required KPIs are included
        selected.update(required)
        
        return sorted(list(selected))

_handler_instance = None
def get_sparse_handler() -> SparseKPIHandler:
    global _handler_instance
    if _handler_instance is None: _handler_instance = SparseKPIHandler()
    return _handler_instance
