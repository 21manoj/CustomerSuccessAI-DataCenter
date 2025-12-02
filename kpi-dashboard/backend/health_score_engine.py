#!/usr/bin/env python3
"""
Health Score Engine
Implements medical report-style health scoring for KPIs
"""

import re
from typing import Dict, List, Tuple, Optional
from health_score_config import get_kpi_reference_range, get_category_weight, get_impact_weight
from extensions import db
from models import KPIReferenceRange

class HealthScoreEngine:
    """Engine for calculating health scores based on reference ranges"""
    
    @staticmethod
    def get_kpi_reference_range_from_db(kpi_name: str) -> Optional[Dict]:
        """
        Get KPI reference range from database, fallback to config if not found
        Returns the same format as health_score_config for compatibility
        """
        try:
            ref_range = KPIReferenceRange.query.filter_by(kpi_name=kpi_name).first()
            if ref_range:
                return {
                    'unit': ref_range.unit,
                    'higher_is_better': ref_range.higher_is_better,
                    'ranges': {
                        'low': {
                            'min': float(ref_range.critical_min),
                            'max': float(ref_range.critical_max),
                            'color': 'red'
                        },
                        'medium': {
                            'min': float(ref_range.risk_min),
                            'max': float(ref_range.risk_max),
                            'color': 'yellow'
                        },
                        'high': {
                            'min': float(ref_range.healthy_min),
                            'max': float(ref_range.healthy_max),
                            'color': 'green'
                        }
                    }
                }
        except Exception as e:
            print(f"Error getting reference range from DB for {kpi_name}: {e}")
        
        # Fallback to config file
        return get_kpi_reference_range(kpi_name)
    
    @staticmethod
    def parse_kpi_value(data_str: str, kpi_name: str = None) -> Optional[float]:
        """
        Parse KPI data value from various formats with unit conversion
        Returns normalized numeric value or None if invalid
        """
        if not data_str or data_str == 'None':
            return None
            
        data_str = str(data_str).strip()
        original_data_str = data_str
        
        # Handle percentage values
        if '%' in data_str:
            data_str = data_str.replace('%', '')
            try:
                return float(data_str)
            except ValueError:
                return None
        
        # Handle currency values
        if '$' in data_str:
            data_str = data_str.replace('$', '').replace(',', '')
            # Handle K/M suffixes for currency
            if 'k' in data_str.lower():
                # Handle decimal values like 2.5K -> 2500
                if '.' in data_str:
                    base_value = float(data_str.lower().replace('k', ''))
                    data_str = str(base_value * 1000)
                else:
                    data_str = data_str.lower().replace('k', '000')
            elif 'm' in data_str.lower():
                # Handle decimal values like 2.5M -> 2500000
                if '.' in data_str:
                    base_value = float(data_str.lower().replace('m', ''))
                    data_str = str(base_value * 1000000)
                else:
                    data_str = data_str.lower().replace('m', '000000')
            try:
                return float(data_str)
            except ValueError:
                return None
        
        # Handle time values with unit conversion
        if 'hours' in data_str.lower():
            data_str = data_str.lower().replace('hours', '').strip()
            try:
                hours_value = float(data_str)
                
                # Unit conversion based on KPI name and expected reference unit
                if kpi_name:
                    config = HealthScoreEngine.get_kpi_reference_range_from_db(kpi_name)
                    expected_unit = config.get('unit', '')
                    
                    # Convert hours to days for KPIs that expect days
                    if expected_unit == 'days':
                        return hours_value / 24.0  # Convert hours to days
                    elif expected_unit == 'hours':
                        return hours_value  # Keep as hours
                    else:
                        # For other units, return hours (might need further conversion)
                        return hours_value
                else:
                    return hours_value
            except ValueError:
                return None
        
        if 'days' in data_str.lower():
            data_str = data_str.lower().replace('days', '').strip()
            try:
                days_value = float(data_str)
                
                # Unit conversion based on KPI name and expected reference unit
                if kpi_name:
                    config = HealthScoreEngine.get_kpi_reference_range_from_db(kpi_name)
                    expected_unit = config.get('unit', '')
                    
                    # Convert days to hours for KPIs that expect hours
                    if expected_unit == 'hours':
                        return days_value * 24.0  # Convert days to hours
                    elif expected_unit == 'days':
                        return days_value  # Keep as days
                    else:
                        # For other units, return days (might need further conversion)
                        return days_value
                else:
                    return days_value
            except ValueError:
                return None
        
        # Handle K/M suffixes
        if 'k' in data_str.lower():
            data_str = data_str.lower().replace('k', '000')
        elif 'm' in data_str.lower():
            data_str = data_str.lower().replace('m', '000000')
        
        # Try to parse as float
        try:
            return float(data_str)
        except ValueError:
            return None
    
    @staticmethod
    def calculate_health_status(value: float, kpi_name: str) -> Dict:
        """
        Calculate health status based on reference ranges
        Returns: {'status': 'low/medium/high', 'score': 0-100, 'color': 'red/yellow/green'}
        """
        if value is None:
            return {
                'status': 'unknown', 
                'score': 0, 
                'color': 'gray',
                'value': None,
                'reference_range': 'N/A'
            }
        
        config = HealthScoreEngine.get_kpi_reference_range_from_db(kpi_name)
        ranges = config['ranges']
        higher_is_better = config['higher_is_better']
        
        # Determine which range the value falls into
        # For higher_is_better=True: low < medium < high
        # For higher_is_better=False: high < medium < low (lower values are better)
        if higher_is_better:
            # Higher values are better: low < medium < high
            # Check ranges in order: low, medium, high
            if ranges['low']['min'] <= value <= ranges['low']['max']:
                status = 'low'
                color = ranges['low']['color']
            elif ranges['medium']['min'] <= value <= ranges['medium']['max']:
                status = 'medium'
                color = ranges['medium']['color']
            elif ranges['high']['min'] <= value <= ranges['high']['max']:
                status = 'high'
                color = ranges['high']['color']
            else:
                # Value outside all ranges - determine closest range
                if value < ranges['low']['min']:
                    status = 'low'
                    color = ranges['low']['color']
                elif value > ranges['high']['max']:
                    status = 'high'
                    color = ranges['high']['color']
                else:
                    # Fallback to medium if somehow in between
                    status = 'medium'
                    color = ranges['medium']['color']
        else:
            # Lower values are better: high < medium < low
            # Check ranges in order: high, medium, low
            if ranges['high']['min'] <= value <= ranges['high']['max']:
                status = 'high'
                color = ranges['high']['color']
            elif ranges['medium']['min'] <= value <= ranges['medium']['max']:
                status = 'medium'
                color = ranges['medium']['color']
            elif ranges['low']['min'] <= value <= ranges['low']['max']:
                status = 'low'
                color = ranges['low']['color']
            else:
                # Value outside all ranges - determine closest range
                if value < ranges['high']['min']:
                    status = 'high'
                    color = ranges['high']['color']
                elif value > ranges['low']['max']:
                    status = 'low'
                    color = ranges['low']['color']
                else:
                    # Fallback to medium if somehow in between
                    status = 'medium'
                    color = ranges['medium']['color']
        
        # Calculate score (0-100) based on position within the range
        if status == 'low':
            if higher_is_better:
                # Lower values are worse
                score = max(0, min(33, (value - ranges['low']['min']) / (ranges['low']['max'] - ranges['low']['min']) * 33))
            else:
                # Lower values are better
                score = max(0, min(33, (ranges['low']['max'] - value) / (ranges['low']['max'] - ranges['low']['min']) * 33))
        elif status == 'medium':
            if higher_is_better:
                score = 34 + ((value - ranges['medium']['min']) / (ranges['medium']['max'] - ranges['medium']['min']) * 32)
            else:
                score = 34 + ((ranges['medium']['max'] - value) / (ranges['medium']['max'] - ranges['medium']['min']) * 32)
        else:  # high
            if higher_is_better:
                score = 67 + ((value - ranges['high']['min']) / (ranges['high']['max'] - ranges['high']['min']) * 33)
            else:
                score = 67 + ((ranges['high']['max'] - value) / (ranges['high']['max'] - ranges['high']['min']) * 33)
        
        return {
            'status': status,
            'score': min(100, max(0, score)),
            'color': color,
            'value': value,
            'reference_range': f"{ranges['low']['min']}-{ranges['high']['max']} {config['unit']}"
        }
    
    @staticmethod
    def calculate_kpi_health_score(kpi_data: Dict) -> Dict:
        """
        Calculate health score for a single KPI
        Returns enhanced KPI data with health information
        """
        kpi_name = kpi_data.get('kpi_parameter', '')
        data_value = kpi_data.get('data', '')
        impact_level = kpi_data.get('impact_level', 'Medium')
        
        # Parse the value
        parsed_value = HealthScoreEngine.parse_kpi_value(data_value, kpi_name)
        
        # Calculate health status
        health_info = HealthScoreEngine.calculate_health_status(parsed_value, kpi_name)
        
        # Get impact weight
        impact_weight = get_impact_weight(impact_level)
        
        # Calculate weighted score
        weighted_score = health_info['score'] * impact_weight
        
        return {
            **kpi_data,
            'parsed_value': parsed_value,
            'health_status': health_info['status'],
            'health_score': health_info['score'],
            'health_color': health_info['color'],
            'reference_range': health_info['reference_range'],
            'impact_weight': impact_weight,
            'weighted_score': weighted_score
        }
    
    @staticmethod
    def calculate_category_health_score(kpis: List[Dict], category: str, customer_id: int = None) -> Dict:
        """
        Calculate health score for a category of KPIs with proper normalization
        Each category is normalized to 100 units before applying category weight
        Returns category health information
        """
        if not kpis:
            return {
                'category': category,
                'total_score': 0,
                'average_score': 0,
                'health_status': 'unknown',
                'color': 'gray',
                'kpi_count': 0,
                'valid_kpi_count': 0,
                'category_weight': get_category_weight(category, customer_id),
                'normalized_score': 0
            }
        
        # Calculate health scores for all KPIs
        enhanced_kpis = []
        category_total_units = 0  # Total impact weight units in this category
        category_total_score = 0   # Total weighted score in this category
        valid_kpis = 0
        
        for kpi in kpis:
            enhanced_kpi = HealthScoreEngine.calculate_kpi_health_score(kpi)
            enhanced_kpis.append(enhanced_kpi)
            
            if enhanced_kpi['parsed_value'] is not None:
                # Add to category totals
                category_total_units += enhanced_kpi['impact_weight']
                category_total_score += enhanced_kpi['weighted_score']
                valid_kpis += 1
        
        # NORMALIZATION: Calculate normalized category score (0-100)
        # This ensures each category contributes equally regardless of KPI count
        normalized_category_score = 0
        if category_total_units > 0:
            # Average score within the category
            avg_score_in_category = category_total_score / category_total_units
            # This is already 0-100, so we use it directly as normalized score
            normalized_category_score = avg_score_in_category
        
        # Apply category weight to get final weighted score
        category_weight = get_category_weight(category, customer_id)
        print(f"DEBUG: Category '{category}', customer_id={customer_id}, weight={category_weight}")
        weighted_category_score = normalized_category_score * category_weight
        
        # Determine category health status based on normalized score
        if normalized_category_score >= 67:
            status = 'high'
            color = 'green'
        elif normalized_category_score >= 34:
            status = 'medium'
            color = 'yellow'
        else:
            status = 'low'
            color = 'red'
        
        return {
            'category': category,
            'total_score': category_total_score,
            'total_units': category_total_units,
            'average_score': normalized_category_score,  # This is the normalized score
            'weighted_category_score': weighted_category_score,
            'health_status': status,
            'color': color,
            'kpi_count': len(kpis),
            'valid_kpi_count': valid_kpis,
            'category_weight': category_weight,
            'normalized_score': normalized_category_score,
            'enhanced_kpis': enhanced_kpis
        }
    
    @staticmethod
    def calculate_overall_health_score(category_scores: List[Dict]) -> Dict:
        """
        Calculate overall health score from normalized category scores
        Each category is already normalized to 0-100, then weighted by category weight
        Returns overall health information
        """
        if not category_scores:
            return {
                'overall_score': 0,
                'health_status': 'unknown',
                'color': 'gray',
                'category_breakdown': []
            }
        
        total_weighted_score = 0
        total_category_weights = 0
        
        for category_score in category_scores:
            # Each category score is already normalized (0-100)
            # Apply category weight to get weighted contribution
            weighted_contribution = category_score['normalized_score'] * category_score['category_weight']
            total_weighted_score += weighted_contribution
            total_category_weights += category_score['category_weight']
        
        # Calculate overall score (weighted average of normalized category scores)
        overall_score = total_weighted_score / total_category_weights if total_category_weights > 0 else 0
        
        # Determine overall health status
        if overall_score >= 67:
            status = 'high'
            color = 'green'
        elif overall_score >= 34:
            status = 'medium'
            color = 'yellow'
        else:
            status = 'low'
            color = 'red'
        
        return {
            'overall_score': overall_score,
            'health_status': status,
            'color': color,
            'category_breakdown': category_scores
        }
    
    @staticmethod
    def format_health_score(score: float) -> str:
        """Format health score as percentage"""
        return f"{score:.1f}%"
    
    @staticmethod
    def get_health_color_class(color: str) -> str:
        """Get Tailwind CSS class for health color"""
        color_map = {
            'green': 'text-green-600 bg-green-100',
            'yellow': 'text-yellow-600 bg-yellow-100',
            'red': 'text-red-600 bg-red-100',
            'gray': 'text-gray-600 bg-gray-100'
        }
        return color_map.get(color, 'text-gray-600 bg-gray-100') 