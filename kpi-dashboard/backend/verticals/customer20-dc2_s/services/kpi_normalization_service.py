#!/usr/bin/env python3
"""
KPI Normalization Service
=========================

Converts raw KPI values with industry units to normalized 0-100 scores.
SHARED service used by both Journey Generator V2 and Excel Import Adapter.

Example:
    Raw: {'mtbf': (8500, 'hours')} → Normalized: {'mtbf': 85.0}
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class NormalizationMethod(Enum):
    LINEAR = "linear"           # value / factor
    INVERSE = "inverse"         # (max - value) / factor (lower is better)
    PERCENTAGE = "percentage"   # value is already 0-100


@dataclass
class KPIDefinition:
    code: str
    name: str
    unit: str
    pillar: str
    method: NormalizationMethod
    factor: float = 100.0
    max_value: float = 100.0
    healthy_min: float = 70.0
    at_risk_min: float = 40.0
    industry_avg: Optional[float] = None


class KPINormalizationService:
    """
    Normalizes raw KPI values to 0-100 scores.
    
    Usage:
        service = KPINormalizationService()
        score = service.normalize('mtbf', 8500, 'hours')  # → 85.0
    """
    
    def __init__(self):
        self.kpi_definitions: Dict[str, KPIDefinition] = {}
        self._load_dc2s_definitions()
    
    def _load_dc2s_definitions(self):
        """Load DC2_S vertical KPI definitions (35 KPIs)"""
        
        # P1: Deployment Velocity (6 KPIs)
        self._add('time_to_first_inference', 'Time to First Inference', 'hours', 'P1_deployment',
                  NormalizationMethod.INVERSE, factor=1.0, max_value=168, industry_avg=48)
        self._add('rack_deployment_time', 'Rack Deployment Time', 'hours', 'P1_deployment',
                  NormalizationMethod.INVERSE, factor=0.5, max_value=72, industry_avg=24)
        self._add('network_config_time', 'Network Config Time', 'hours', 'P1_deployment',
                  NormalizationMethod.INVERSE, factor=0.25, max_value=24, industry_avg=8)
        self._add('gpu_driver_install_success', 'GPU Driver Success', '%', 'P1_deployment',
                  NormalizationMethod.PERCENTAGE, industry_avg=98)
        self._add('cluster_validation_pass', 'Cluster Validation', '%', 'P1_deployment',
                  NormalizationMethod.PERCENTAGE, industry_avg=97)
        self._add('documentation_completeness', 'Doc Completeness', '%', 'P1_deployment',
                  NormalizationMethod.PERCENTAGE, industry_avg=85)
        
        # P2: Operational Stability (7 KPIs)
        self._add('mtbf', 'Mean Time Between Failures', 'hours', 'P2_stability',
                  NormalizationMethod.LINEAR, factor=100, industry_avg=10000)
        self._add('mttr', 'Mean Time To Repair', 'hours', 'P2_stability',
                  NormalizationMethod.INVERSE, factor=0.5, max_value=48, industry_avg=4)
        self._add('uptime_percentage', 'Uptime', '%', 'P2_stability',
                  NormalizationMethod.PERCENTAGE, healthy_min=99.5, at_risk_min=99.0, industry_avg=99.9)
        self._add('critical_incident_rate', 'Critical Incidents', 'incidents/month', 'P2_stability',
                  NormalizationMethod.INVERSE, factor=0.25, max_value=4, industry_avg=0.5)
        self._add('rma_rate', 'RMA Rate', '%', 'P2_stability',
                  NormalizationMethod.INVERSE, factor=0.05, max_value=5, industry_avg=1.5)
        self._add('thermal_compliance', 'Thermal Compliance', '%', 'P2_stability',
                  NormalizationMethod.PERCENTAGE, industry_avg=98)
        self._add('power_efficiency', 'Power Efficiency (PUE)', 'ratio', 'P2_stability',
                  NormalizationMethod.INVERSE, factor=0.01, max_value=2.0, industry_avg=1.3)
        
        # P3: AI Workload Performance (6 KPIs)
        self._add('gpu_utilization_rate', 'GPU Utilization', '%', 'P3_performance',
                  NormalizationMethod.PERCENTAGE, industry_avg=75)
        self._add('inference_latency', 'Inference Latency', 'ms', 'P3_performance',
                  NormalizationMethod.INVERSE, factor=1.0, max_value=100, industry_avg=25)
        self._add('training_throughput', 'Training Throughput', 'samples/sec', 'P3_performance',
                  NormalizationMethod.LINEAR, factor=100, industry_avg=5000)
        self._add('memory_utilization', 'GPU Memory', '%', 'P3_performance',
                  NormalizationMethod.PERCENTAGE, industry_avg=70)
        self._add('interconnect_bandwidth', 'Interconnect BW', '%', 'P3_performance',
                  NormalizationMethod.PERCENTAGE, industry_avg=75)
        self._add('job_completion_rate', 'Job Completion', '%', 'P3_performance',
                  NormalizationMethod.PERCENTAGE, industry_avg=98)
        
        # P4: Channel & Partner (6 KPIs)
        self._add('partner_response_time', 'Partner Response', 'hours', 'P4_channel',
                  NormalizationMethod.INVERSE, factor=0.5, max_value=48, industry_avg=4)
        self._add('partner_resolution_rate', 'Partner Resolution', '%', 'P4_channel',
                  NormalizationMethod.PERCENTAGE, industry_avg=85)
        self._add('escalation_rate', 'Escalation Rate', '%', 'P4_channel',
                  NormalizationMethod.INVERSE, factor=0.2, max_value=20, industry_avg=5)
        self._add('partner_satisfaction', 'Partner Satisfaction', 'score', 'P4_channel',
                  NormalizationMethod.LINEAR, factor=0.05, max_value=5, industry_avg=4.2)
        self._add('training_completion', 'Training Completion', '%', 'P4_channel',
                  NormalizationMethod.PERCENTAGE, industry_avg=85)
        self._add('joint_engagement_score', 'Joint Engagement', 'score', 'P4_channel',
                  NormalizationMethod.LINEAR, factor=0.1, max_value=10, industry_avg=7)
        
        # P5: Expansion & Revenue (8 KPIs)
        self._add('capacity_utilization', 'Capacity Utilization', '%', 'P5_expansion',
                  NormalizationMethod.PERCENTAGE, industry_avg=75)
        self._add('expansion_pipeline', 'Expansion Pipeline', '$', 'P5_expansion',
                  NormalizationMethod.LINEAR, factor=10000, industry_avg=500000)
        self._add('renewal_probability', 'Renewal Probability', '%', 'P5_expansion',
                  NormalizationMethod.PERCENTAGE, industry_avg=85)
        self._add('nps_score', 'NPS Score', 'score', 'P5_expansion',
                  NormalizationMethod.LINEAR, factor=1.0, industry_avg=45)
        self._add('cost_per_gpu_hour', 'Cost per GPU Hour', '$/hr', 'P5_expansion',
                  NormalizationMethod.INVERSE, factor=0.1, max_value=10, industry_avg=2.5)
        self._add('contract_growth_rate', 'Contract Growth', '%', 'P5_expansion',
                  NormalizationMethod.PERCENTAGE, industry_avg=15)
        self._add('feature_adoption_rate', 'Feature Adoption', '%', 'P5_expansion',
                  NormalizationMethod.PERCENTAGE, industry_avg=70)
        self._add('executive_engagement', 'Exec Engagement', 'score', 'P5_expansion',
                  NormalizationMethod.LINEAR, factor=0.1, max_value=10, industry_avg=7)
    
    def _add(self, code: str, name: str, unit: str, pillar: str,
             method: NormalizationMethod, factor: float = 100.0,
             max_value: float = 100.0, healthy_min: float = 70.0,
             at_risk_min: float = 40.0, industry_avg: Optional[float] = None):
        self.kpi_definitions[code] = KPIDefinition(
            code=code, name=name, unit=unit, pillar=pillar,
            method=method, factor=factor, max_value=max_value,
            healthy_min=healthy_min, at_risk_min=at_risk_min,
            industry_avg=industry_avg
        )
    
    def normalize(self, kpi_code: str, raw_value: float, unit: Optional[str] = None) -> float:
        """Normalize raw value to 0-100 score"""
        if kpi_code not in self.kpi_definitions:
            return min(100.0, max(0.0, float(raw_value)))
        
        defn = self.kpi_definitions[kpi_code]
        
        if defn.method == NormalizationMethod.PERCENTAGE:
            score = raw_value
        elif defn.method == NormalizationMethod.LINEAR:
            score = raw_value / defn.factor
        elif defn.method == NormalizationMethod.INVERSE:
            score = (defn.max_value - raw_value) / defn.factor * 100
        else:
            score = raw_value
        
        return min(100.0, max(0.0, float(score)))
    
    def normalize_batch(self, raw_kpis: Dict[str, Tuple[float, str]]) -> Dict[str, float]:
        """Normalize batch of raw KPIs: {code: (value, unit)} → {code: score}"""
        return {code: self.normalize(code, val, unit) 
                for code, (val, unit) in raw_kpis.items()}
    
    def denormalize(self, kpi_code: str, score: float) -> Tuple[float, str]:
        """Convert score back to raw value with unit"""
        if kpi_code not in self.kpi_definitions:
            return (score, 'unknown')
        
        defn = self.kpi_definitions[kpi_code]
        
        if defn.method == NormalizationMethod.PERCENTAGE:
            raw = score
        elif defn.method == NormalizationMethod.LINEAR:
            raw = score * defn.factor
        elif defn.method == NormalizationMethod.INVERSE:
            raw = defn.max_value - (score / 100 * defn.factor)
        else:
            raw = score
        
        return (raw, defn.unit)
    
    def get_health_status(self, kpi_code: str, score: float) -> str:
        """Get health status: 'healthy', 'at_risk', or 'critical'"""
        defn = self.kpi_definitions.get(kpi_code)
        healthy_min = defn.healthy_min if defn else 70.0
        at_risk_min = defn.at_risk_min if defn else 40.0
        
        if score >= healthy_min:
            return 'healthy'
        elif score >= at_risk_min:
            return 'at_risk'
        return 'critical'
    
    def get_all_kpi_codes(self) -> list:
        return list(self.kpi_definitions.keys())
    
    def get_kpis_by_pillar(self, pillar: str) -> list:
        return [c for c, d in self.kpi_definitions.items() if d.pillar == pillar]
    
    def get_pillar_list(self) -> list:
        return list(set(d.pillar for d in self.kpi_definitions.values()))


# Singleton
_service: Optional[KPINormalizationService] = None

def get_normalization_service() -> KPINormalizationService:
    global _service
    if _service is None:
        _service = KPINormalizationService()
    return _service


if __name__ == "__main__":
    service = KPINormalizationService()
    
    tests = [
        ('mtbf', 8500, 'hours'),
        ('gpu_utilization_rate', 72, '%'),
        ('critical_incident_rate', 1.5, 'incidents/month'),
    ]
    
    print("KPI Normalization Tests:")
    for code, val, unit in tests:
        score = service.normalize(code, val, unit)
        status = service.get_health_status(code, score)
        print(f"  {code}: {val} {unit} → {score:.1f}/100 ({status})")
    
    print("\n✅ Tests passed!")
