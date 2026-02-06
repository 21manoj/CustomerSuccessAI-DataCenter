#!/usr/bin/env python3
"""
DC2_S Vertical Loader
====================

Provides DC2SVertical class for easy access to DC2_S KPI definitions.
Used by onboarding scripts to get KPI lists.
"""

from .kpi_definitions import DC2S_KPIS, DC2S_PILLARS
from typing import List, Dict, Any

class DC2SVertical:
    """DC2_S Vertical Loader - Provides access to KPI definitions"""
    
    # Pillar mapping: P1-P5 to AI/CH/DV/EX/OS
    PILLAR_MAP = {
        'P1': 'DV',  # Deployment Velocity
        'P2': 'OS',  # Operational Stability
        'P3': 'AI',  # AI Workload Performance
        'P4': 'CH',  # Channel & Partner Health
        'P5': 'EX'   # Expansion Readiness
    }
    
    def __init__(self):
        """Initialize vertical loader"""
        self._kpis = None
        self._pillars = None
    
    @property
    def kpis(self) -> List[Dict[str, Any]]:
        """Get all KPIs as a list of dictionaries with mapped pillar codes"""
        if self._kpis is None:
            self._kpis = []
            for kpi_code, kpi_def in DC2S_KPIS.items():
                original_pillar = kpi_def.get('pillar', 'Unknown')
                # Map P1-P5 to AI/CH/DV/EX/OS
                mapped_pillar = self.PILLAR_MAP.get(original_pillar, original_pillar)
                
                # Create KPI dict with mapped pillar (must override after **kpi_def)
                kpi_dict = {
                    'code': kpi_code,
                    'name': kpi_def.get('name', kpi_code),
                    'description': kpi_def.get('description', ''),
                    'target': kpi_def.get('target', {}),
                    'unit': kpi_def.get('unit', ''),
                    **kpi_def  # Include all original fields
                }
                # Override pillar with mapped version
                kpi_dict['pillar'] = mapped_pillar
                kpi_dict['original_pillar'] = original_pillar  # Keep original for reference
                
                self._kpis.append(kpi_dict)
        return self._kpis
    
    @property
    def pillars(self) -> Dict[str, Dict[str, Any]]:
        """Get all pillars"""
        if self._pillars is None:
            self._pillars = DC2S_PILLARS.copy()
        return self._pillars
    
    def get_kpi_by_code(self, kpi_code: str) -> Dict[str, Any]:
        """Get KPI definition by code"""
        return DC2S_KPIS.get(kpi_code, {})
    
    def get_kpis_by_pillar(self, pillar: str) -> List[Dict[str, Any]]:
        """Get all KPIs for a specific pillar"""
        return [kpi for kpi in self.kpis if kpi['pillar'] == pillar]
    
    def get_all_kpi_codes(self) -> List[str]:
        """Get list of all KPI codes"""
        return list(DC2S_KPIS.keys())
    
    def get_pillar_kpi_codes(self, pillar: str) -> List[str]:
        """Get KPI codes for a specific pillar"""
        return [kpi['code'] for kpi in self.kpis if kpi['pillar'] == pillar]
