#!/usr/bin/env python3
"""
KPI Reference Ranges API
Provides reference ranges for KPI calculations
"""

from flask import Blueprint, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from health_score_config import KPI_REFERENCE_RANGES

kpi_reference_api = Blueprint('kpi_reference_api', __name__)

@kpi_reference_api.route('/api/kpi-reference-ranges', methods=['GET'])
def get_kpi_reference_ranges():
    """
    Get all KPI reference ranges and calculation details
    """
    reference_ranges = []
    for kpi_name, config in KPI_REFERENCE_RANGES.items():
        reference_ranges.append({
            "kpi_name": kpi_name,
            "ranges": config['ranges'],
            "unit": config['unit'],
            "higher_is_better": config['higher_is_better'],
            "critical_range": f"{config['ranges']['low']['min']}-{config['ranges']['low']['max']} {config['unit']}",
            "risk_range": f"{config['ranges']['medium']['min']}-{config['ranges']['medium']['max']} {config['unit']}",
            "healthy_range": f"{config['ranges']['high']['min']}-{config['ranges']['high']['max']} {config['unit']}"
        })
    
    return jsonify({"reference_ranges": reference_ranges}), 200
