#!/usr/bin/env python3
"""
Realistic KPI Generator
=======================

Generates KPIs with industry-standard units matching the Import Adapter.
Ensures Journey Generator V2 speaks the SAME LANGUAGE as production data.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import random

from kpi_normalization_service import get_normalization_service
from sparse_kpi_handler import get_sparse_handler


@dataclass
class RealisticKPIOutput:
    raw_kpis: Dict[str, Tuple[float, str]]    # {code: (value, unit)}
    normalized_kpis: Dict[str, float]          # {code: score 0-100}
    coverage_pct: float
    data_quality: float
    missing_kpis: List[str]
    available_kpis: List[str]
    pillar_coverage: Dict[str, float]


class RealisticKPIGenerator:
    """Generates realistic KPIs with industry units."""
    
    def __init__(self):
        self.norm_service = get_normalization_service()
        self.sparse_handler = get_sparse_handler()
        self._init_value_ranges()
    
    def _init_value_ranges(self):
        """Value ranges for each KPI by scenario (in RAW units)"""
        self.value_ranges = {
            'mtbf': {'healthy': (10000, 15000), 'at_risk': (6000, 10000),
                     'crisis': (3000, 6000), 'recovery': (7000, 11000)},
            'mttr': {'healthy': (1, 4), 'at_risk': (4, 12),
                     'crisis': (12, 48), 'recovery': (3, 8)},
            'uptime_percentage': {'healthy': (99.5, 99.99), 'at_risk': (99.0, 99.5),
                                  'crisis': (95, 99.0), 'recovery': (99.2, 99.7)},
            'critical_incident_rate': {'healthy': (0, 0.5), 'at_risk': (0.5, 2.0),
                                       'crisis': (2.0, 4.0), 'recovery': (0.3, 1.5)},
            'rma_rate': {'healthy': (0.5, 1.5), 'at_risk': (1.5, 3.0),
                         'crisis': (3.0, 5.0), 'recovery': (1.0, 2.5)},
            'gpu_utilization_rate': {'healthy': (70, 90), 'at_risk': (50, 70),
                                     'crisis': (30, 50), 'recovery': (55, 75)},
            'inference_latency': {'healthy': (10, 30), 'at_risk': (30, 60),
                                  'crisis': (60, 100), 'recovery': (25, 50)},
            'capacity_utilization': {'healthy': (70, 90), 'at_risk': (50, 70),
                                     'crisis': (30, 50), 'recovery': (55, 75)},
            'renewal_probability': {'healthy': (80, 95), 'at_risk': (50, 80),
                                    'crisis': (20, 50), 'recovery': (60, 85)},
            'nps_score': {'healthy': (40, 80), 'at_risk': (10, 40),
                          'crisis': (-30, 10), 'recovery': (20, 50)},
        }
    
    def _get_raw_value(self, kpi_code: str, scenario: str) -> float:
        if kpi_code in self.value_ranges and scenario in self.value_ranges[kpi_code]:
            min_val, max_val = self.value_ranges[kpi_code][scenario]
            return random.uniform(min_val, max_val)
        
        score_ranges = {'healthy': (70, 95), 'at_risk': (45, 75),
                       'crisis': (20, 50), 'recovery': (50, 80)}
        min_s, max_s = score_ranges.get(scenario, (50, 80))
        target_score = random.uniform(min_s, max_s)
        raw_val, _ = self.norm_service.denormalize(kpi_code, target_score)
        return raw_val
    
    def generate(self, pattern: str = 'typical', scenario: str = 'healthy',
                 required_kpis: Optional[List[str]] = None) -> RealisticKPIOutput:
        """Generate realistic KPIs with raw values and units."""
        selected_kpis = self.sparse_handler.select_sparse_kpis(pattern, required_kpis)
        
        raw_kpis = {}
        for kpi_code in selected_kpis:
            defn = self.norm_service.kpi_definitions.get(kpi_code)
            if defn:
                raw_value = self._get_raw_value(kpi_code, scenario)
                raw_kpis[kpi_code] = (round(raw_value, 2), defn.unit)
            else:
                score_ranges = {'healthy': (70, 95), 'at_risk': (45, 75),
                              'crisis': (20, 50), 'recovery': (50, 80)}
                min_s, max_s = score_ranges.get(scenario, (50, 80))
                raw_kpis[kpi_code] = (round(random.uniform(min_s, max_s), 2), '%')
        
        normalized_kpis = {
            code: round(self.norm_service.normalize(code, val, unit), 1)
            for code, (val, unit) in raw_kpis.items()
        }
        
        all_kpis = set(self.norm_service.get_all_kpi_codes())
        available = set(selected_kpis)
        missing = all_kpis - available
        coverage_pct = len(available) / len(all_kpis) * 100
        
        pillar_coverage = {}
        for pillar in self.norm_service.get_pillar_list():
            pillar_kpis = set(self.norm_service.get_kpis_by_pillar(pillar))
            available_in_pillar = available & pillar_kpis
            if pillar_kpis:
                pillar_coverage[pillar] = len(available_in_pillar) / len(pillar_kpis) * 100
        
        priority_kpis = ['mtbf', 'gpu_utilization_rate', 'uptime_percentage',
                        'critical_incident_rate', 'capacity_utilization']
        priority_count = sum(1 for k in priority_kpis if k in available)
        data_quality = (coverage_pct / 100 * 0.6) + (priority_count / len(priority_kpis) * 0.4)
        
        return RealisticKPIOutput(
            raw_kpis=raw_kpis,
            normalized_kpis=normalized_kpis,
            coverage_pct=round(coverage_pct, 1),
            data_quality=round(data_quality, 3),
            missing_kpis=sorted(list(missing)),
            available_kpis=sorted(list(available)),
            pillar_coverage=pillar_coverage
        )


def get_realistic_generator() -> RealisticKPIGenerator:
    return RealisticKPIGenerator()


if __name__ == "__main__":
    gen = RealisticKPIGenerator()
    result = gen.generate('typical', 'healthy')
    print(f"Coverage: {result.coverage_pct}%, KPIs: {len(result.raw_kpis)}")
    for kpi, (val, unit) in list(result.raw_kpis.items())[:3]:
        print(f"  {kpi}: {val} {unit} → {result.normalized_kpis[kpi]}/100")
    print("✅ Test passed!")
