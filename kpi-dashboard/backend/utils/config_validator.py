#!/usr/bin/env python3
"""
Configuration Validator for DC2_S
Validates customer configurations including custom KPIs
"""

import re
from typing import Dict, List, Tuple

class ConfigValidator:
    """Validates DC2_S customer configurations"""
    
    VALID_PILLARS = ['AI', 'CH', 'DV', 'EX', 'OS']
    VALID_OPERATORS = ['>', '<', '>=', '<=', '=']
    CUSTOM_KPI_PATTERN = r'^CUSTOM-[A-Z0-9-]+$'
    CATALOG_KPI_PATTERN = r'^(AI|CH|DV|EX|OS)-KPI[0-9]+$'
    
    def validate_pillar_weights(self, weights: Dict[str, float]) -> Tuple[bool, List[str]]:
        """Validate pillar weights sum to 1.0"""
        errors = []
        
        # Check all pillars present
        for pillar in self.VALID_PILLARS:
            if pillar not in weights:
                errors.append(f"Missing weight for pillar '{pillar}'")
        
        # Check sum to 1.0
        total = sum(weights.values())
        if abs(total - 1.0) > 0.001:
            errors.append(f"Pillar weights must sum to 1.0, got {total:.4f}")
        
        # Check each weight is positive
        for pillar, weight in weights.items():
            if weight < 0 or weight > 1:
                errors.append(f"Weight for '{pillar}' must be between 0 and 1, got {weight}")
        
        return len(errors) == 0, errors
    
    def validate_kpi_code(self, kpi_code: str) -> Tuple[bool, List[str]]:
        """Validate KPI code format"""
        errors = []
        
        # Check if catalog or custom
        is_catalog = re.match(self.CATALOG_KPI_PATTERN, kpi_code)
        is_custom = re.match(self.CUSTOM_KPI_PATTERN, kpi_code)
        
        if not (is_catalog or is_custom):
            errors.append(
                f"Invalid KPI code '{kpi_code}'. "
                f"Must match {self.CATALOG_KPI_PATTERN} or {self.CUSTOM_KPI_PATTERN}"
            )
        
        return len(errors) == 0, errors
    
    def validate_custom_kpi(self, kpi_code: str, kpi_definition: Dict) -> Tuple[bool, List[str]]:
        """Validate a custom KPI definition"""
        errors = []
        
        # 1. Validate KPI code format
        if not re.match(self.CUSTOM_KPI_PATTERN, kpi_code):
            errors.append(
                f"Custom KPI code must match pattern {self.CUSTOM_KPI_PATTERN}, "
                f"got '{kpi_code}'"
            )
        
        # 2. Required fields
        required_fields = ['pillar', 'name', 'unit', 'target', 'operator', 'range']
        for field in required_fields:
            if field not in kpi_definition:
                errors.append(f"Custom KPI '{kpi_code}' missing required field '{field}'")
        
        # If required fields missing, return early
        if errors:
            return False, errors
        
        # 3. Validate pillar
        if kpi_definition['pillar'] not in self.VALID_PILLARS:
            errors.append(
                f"Invalid pillar '{kpi_definition['pillar']}' for KPI '{kpi_code}'. "
                f"Must be one of: {', '.join(self.VALID_PILLARS)}"
            )
        
        # 4. Validate operator
        if kpi_definition['operator'] not in self.VALID_OPERATORS:
            errors.append(
                f"Invalid operator '{kpi_definition['operator']}' for KPI '{kpi_code}'. "
                f"Must be one of: {', '.join(self.VALID_OPERATORS)}"
            )
        
        # 5. Validate range
        range_val = kpi_definition['range']
        if not isinstance(range_val, list) or len(range_val) != 2:
            errors.append(f"Range for KPI '{kpi_code}' must be [min, max], got {range_val}")
        elif range_val[0] >= range_val[1]:
            errors.append(f"Range min must be less than max for KPI '{kpi_code}'")
        
        # 6. Validate target is within range
        target = kpi_definition['target']
        range_min, range_max = range_val
        if not (range_min <= target <= range_max):
            errors.append(
                f"Target {target} for KPI '{kpi_code}' must be within range [{range_min}, {range_max}]"
            )
        
        # 7. Validate thresholds if present
        if 'thresholds' in kpi_definition:
            thresholds = kpi_definition['thresholds']
            required_threshold_keys = ['excellent', 'good', 'warning', 'critical']
            for key in required_threshold_keys:
                if key not in thresholds:
                    errors.append(f"Missing threshold '{key}' for KPI '{kpi_code}'")
        
        return len(errors) == 0, errors
    
    def validate_kpi_weights(self, pillar: str, kpi_codes: List[str], weights: Dict[str, float]) -> Tuple[bool, List[str]]:
        """Validate KPI weights within a pillar sum to 1.0"""
        errors = []
        
        # Check all KPIs have weights
        for kpi_code in kpi_codes:
            if kpi_code not in weights:
                errors.append(f"Missing weight for KPI '{kpi_code}' in pillar '{pillar}'")
        
        # Check weights sum to 1.0
        total = sum(weights.values())
        if abs(total - 1.0) > 0.001:
            errors.append(
                f"KPI weights in pillar '{pillar}' must sum to 1.0, got {total:.4f}"
            )
        
        # Check each weight is positive
        for kpi_code, weight in weights.items():
            if weight < 0 or weight > 1:
                errors.append(
                    f"Weight for KPI '{kpi_code}' in pillar '{pillar}' "
                    f"must be between 0 and 1, got {weight}"
                )
        
        return len(errors) == 0, errors
    
    def validate_full_config(self, config: Dict) -> Tuple[bool, List[str]]:
        """Validate entire configuration"""
        all_errors = []
        
        # 1. Validate pillar weights
        if 'pillar_weights' in config:
            is_valid, errors = self.validate_pillar_weights(config['pillar_weights'])
            all_errors.extend(errors)
        
        # 2. Validate enabled KPIs
        if 'enabled_kpis' in config:
            for kpi_code in config['enabled_kpis']:
                is_valid, errors = self.validate_kpi_code(kpi_code)
                all_errors.extend(errors)
        
        # 3. Validate custom KPI definitions
        if 'kpi_definitions' in config:
            for kpi_code, kpi_def in config['kpi_definitions'].items():
                is_valid, errors = self.validate_custom_kpi(kpi_code, kpi_def)
                all_errors.extend(errors)
        
        # 4. Validate KPI weights within pillars
        if 'kpi_weights' in config and 'enabled_kpis' in config:
            # Group KPIs by pillar
            kpis_by_pillar = {}
            for kpi_code in config['enabled_kpis']:
                # Extract pillar from KPI code
                if kpi_code.startswith('CUSTOM-'):
                    # Get pillar from custom definition
                    if 'kpi_definitions' in config and kpi_code in config['kpi_definitions']:
                        pillar = config['kpi_definitions'][kpi_code]['pillar']
                    else:
                        continue
                else:
                    # Extract from catalog KPI code (e.g., "AI-KPI1" -> "AI")
                    pillar = kpi_code.split('-')[0]
                
                if pillar not in kpis_by_pillar:
                    kpis_by_pillar[pillar] = []
                kpis_by_pillar[pillar].append(kpi_code)
            
            # Validate weights for each pillar
            for pillar, kpi_codes in kpis_by_pillar.items():
                if pillar in config['kpi_weights']:
                    is_valid, errors = self.validate_kpi_weights(
                        pillar, kpi_codes, config['kpi_weights'][pillar]
                    )
                    all_errors.extend(errors)
        
        return len(all_errors) == 0, all_errors
