#!/usr/bin/env python3
"""
Configuration Loader for DC2_S Wizards
Loads and resolves customer configuration (catalog + custom KPIs)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from models import db, CustomerConfig

class ConfigLoader:
    """
    Loads DC2_S configuration for wizards
    Merges catalog KPIs with customer customizations
    """
    
    def __init__(self, customer_id: int):
        self.customer_id = customer_id
        self._vertical_definition = None
        self._customer_config = None
    
    @property
    def vertical_definition(self) -> Dict:
        """Load vertical definition (catalog) once"""
        if self._vertical_definition is None:
            # Try multiple possible paths
            possible_paths = [
                Path(__file__).parent.parent / 'verticals/_template/config/dc2s_vertical_definition.json',
                Path(__file__).parent.parent / 'verticals/dc2_s/kpi_definitions.py',
            ]
            
            # For now, we'll use the kpi_definitions.py approach
            # Import the DC2_S KPI definitions
            try:
                from verticals.dc2_s.kpi_definitions import DC2S_KPIS, DC2S_PILLARS
                
                # Convert to expected format
                self._vertical_definition = {
                    'pillars': [
                        {
                            'code': pillar_code,
                            'name': pillar_info['name'],
                            'default_weight': pillar_info.get('weight_l2', 0.20)
                        }
                        for pillar_code, pillar_info in DC2S_PILLARS.items()
                    ],
                    'default_kpis': [
                        {
                            'code': kpi_code,
                            'name': kpi_info['name'],
                            'pillar': kpi_info['pillar'],
                            'target': kpi_info.get('target', {}).get('value', 85.0),
                            'operator': kpi_info.get('target', {}).get('operator', '>'),
                            'range': [
                                kpi_info.get('ranges', {}).get('critical', {}).get('min', 0),
                                kpi_info.get('ranges', {}).get('healthy', {}).get('max', 100)
                            ],
                            'unit': kpi_info.get('unit', '%')
                        }
                        for kpi_code, kpi_info in DC2S_KPIS.items()
                    ]
                }
            except ImportError:
                # Fallback to defaults if import fails
                self._vertical_definition = {
                    'pillars': [
                        {'code': 'AI', 'name': 'AI Workload Performance', 'default_weight': 0.25},
                        {'code': 'CH', 'name': 'Customer Health', 'default_weight': 0.20},
                        {'code': 'DV', 'name': 'Deployment Velocity', 'default_weight': 0.15},
                        {'code': 'EX', 'name': 'Expansion & Growth', 'default_weight': 0.20},
                        {'code': 'OS', 'name': 'Operational Stability', 'default_weight': 0.20}
                    ],
                    'default_kpis': []
                }
        
        return self._vertical_definition
    
    @property
    def customer_config(self) -> Optional[Dict]:
        """Load customer config once"""
        if self._customer_config is None:
            config = CustomerConfig.query.filter_by(customer_id=self.customer_id).first()
            
            if config and config.vertical == 'dc2_s':
                self._customer_config = {
                    'pillar_weights': config.dc2s_pillar_weights or self._get_default_pillar_weights(),
                    'enabled_kpis': config.dc2s_enabled_kpis or self._get_default_enabled_kpis(),
                    'kpi_definitions': config.dc2s_kpi_definitions or {},
                    'kpi_overrides': config.dc2s_kpi_overrides or {},
                    'kpi_weights': config.dc2s_kpi_weights or self._get_default_kpi_weights()
                }
            else:
                # No config - use defaults
                self._customer_config = {
                    'pillar_weights': self._get_default_pillar_weights(),
                    'enabled_kpis': self._get_default_enabled_kpis(),
                    'kpi_definitions': {},
                    'kpi_overrides': {},
                    'kpi_weights': self._get_default_kpi_weights()
                }
        
        return self._customer_config
    
    def _get_default_pillar_weights(self) -> Dict[str, float]:
        """Get default pillar weights from vertical definition"""
        pillars = self.vertical_definition.get('pillars', [])
        weights = {}
        
        for pillar in pillars:
            code = pillar.get('code')
            if code:
                # Map P1-P5 to AI, CH, DV, EX, OS if needed
                pillar_map = {
                    'P1': 'DV', 'P2': 'OS', 'P3': 'AI', 'P4': 'CH', 'P5': 'EX'
                }
                mapped_code = pillar_map.get(code, code)
                weights[mapped_code] = pillar.get('default_weight', 0.20)
        
        # Ensure all 5 pillars are present
        if len(weights) < 5:
            weights = {
                'AI': 0.25, 'CH': 0.20, 'DV': 0.15, 'EX': 0.20, 'OS': 0.20
            }
        
        return weights
    
    def _get_default_enabled_kpis(self) -> List[str]:
        """Get all catalog KPI codes"""
        kpis = self.vertical_definition.get('default_kpis', [])
        return [kpi.get('code') for kpi in kpis if kpi.get('code')]
    
    def _get_default_kpi_weights(self) -> Dict[str, Dict[str, float]]:
        """Get default KPI weights grouped by pillar"""
        weights = {}
        
        # Group KPIs by pillar
        kpis_by_pillar = {}
        for kpi in self.vertical_definition.get('default_kpis', []):
            pillar = kpi.get('pillar')
            if pillar:
                # Map P1-P5 to AI, CH, DV, EX, OS if needed
                pillar_map = {
                    'P1': 'DV', 'P2': 'OS', 'P3': 'AI', 'P4': 'CH', 'P5': 'EX'
                }
                mapped_pillar = pillar_map.get(pillar, pillar)
                
                if mapped_pillar not in kpis_by_pillar:
                    kpis_by_pillar[mapped_pillar] = []
                kpis_by_pillar[mapped_pillar].append(kpi.get('code'))
        
        # Calculate equal weights
        for pillar, kpi_codes in kpis_by_pillar.items():
            if kpi_codes:
                equal_weight = 1.0 / len(kpi_codes)
                weights[pillar] = {
                    code: equal_weight
                    for code in kpi_codes if code
                }
        
        return weights
    
    def get_enabled_kpis(self) -> List[str]:
        """Get list of enabled KPI codes"""
        return self.customer_config['enabled_kpis']
    
    def get_kpi_definition(self, kpi_code: str) -> Optional[Dict]:
        """
        Get KPI definition (catalog or custom)
        
        Returns:
            KPI definition dict or None
        """
        # Check if custom KPI
        if kpi_code.startswith('CUSTOM-'):
            return self.customer_config['kpi_definitions'].get(kpi_code)
        
        # Check catalog - handle both P1-KPI1 and AI-KPI1 formats
        for kpi in self.vertical_definition.get('default_kpis', []):
            if kpi.get('code') == kpi_code:
                # Apply overrides
                kpi_def = kpi.copy()
                override = self.customer_config['kpi_overrides'].get(kpi_code, {})
                kpi_def.update(override)
                return kpi_def
        
        # Also check if it's a catalog-style KPI (AI-KPI1, CH-KPI4, etc.)
        if '-' in kpi_code:
            pillar = kpi_code.split('-')[0]
            if pillar in ['AI', 'CH', 'DV', 'EX', 'OS']:
                # Create a default definition for catalog KPIs
                override = self.customer_config['kpi_overrides'].get(kpi_code, {})
                
                kpi_def = {
                    'code': kpi_code,
                    'pillar': pillar,
                    'name': kpi_code,
                    'target': override.get('target', 85.0),
                    'operator': override.get('operator', '>'),
                    'range': override.get('range', [0.0, 100.0]),
                    'unit': override.get('unit', '%')
                }
                return kpi_def
        
        return None
    
    def get_all_kpi_definitions(self) -> List[Dict]:
        """
        Get all enabled KPI definitions with overrides applied
        
        Returns:
            List of KPI definition dicts
        """
        kpis = []
        
        for kpi_code in self.get_enabled_kpis():
            kpi_def = self.get_kpi_definition(kpi_code)
            if kpi_def:
                kpis.append({
                    'code': kpi_code,
                    **kpi_def
                })
        
        return kpis
    
    def get_pillar_weights(self) -> Dict[str, float]:
        """Get pillar weights"""
        return self.customer_config['pillar_weights']
    
    def get_kpi_weights(self, pillar_code: str) -> Dict[str, float]:
        """Get KPI weights for a specific pillar"""
        return self.customer_config['kpi_weights'].get(pillar_code, {})
    
    def get_kpis_by_pillar(self) -> Dict[str, List[str]]:
        """Group enabled KPIs by pillar"""
        kpis_by_pillar = {'AI': [], 'CH': [], 'DV': [], 'EX': [], 'OS': []}
        
        for kpi_code in self.get_enabled_kpis():
            kpi_def = self.get_kpi_definition(kpi_code)
            if kpi_def:
                pillar = kpi_def.get('pillar')
                # Map P1-P5 to AI, CH, DV, EX, OS if needed
                pillar_map = {
                    'P1': 'DV', 'P2': 'OS', 'P3': 'AI', 'P4': 'CH', 'P5': 'EX'
                }
                mapped_pillar = pillar_map.get(pillar, pillar)
                if mapped_pillar in kpis_by_pillar:
                    kpis_by_pillar[mapped_pillar].append(kpi_code)
        
        return kpis_by_pillar
