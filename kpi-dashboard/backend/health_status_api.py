#!/usr/bin/env python3
"""
Health Status API
Provides health status (Healthy/Risk/Critical) for individual KPIs
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import KPI, Account, Customer
from health_score_engine import HealthScoreEngine
import json

health_status_api = Blueprint('health_status_api', __name__)

@health_status_api.route('/api/health-status/kpis', methods=['GET'])
def get_kpi_health_status():
    """
    Get health status for all KPIs of a customer
    """
    customer_id = get_current_customer_id()
    account_id = request.args.get('account_id')
    
    if not customer_id:
        return jsonify({"error": "X-Customer-ID header is required"}), 400
    
    try:
        customer_id = int(customer_id)
    except ValueError:
        return jsonify({"error": "Invalid X-Customer-ID"}), 400
    
    # Build query
    query = KPI.query.join(Account).filter(Account.customer_id == customer_id)
    
    if account_id:
        try:
            account_id = int(account_id)
            query = query.filter(KPI.account_id == account_id)
        except ValueError:
            return jsonify({"error": "Invalid account_id"}), 400
    
    kpis = query.all()
    
    health_statuses = []
    for kpi in kpis:
        # Debug logging for TTFV
        if kpi.kpi_parameter == 'Time to First Value (TTFV)' and '21 hours' in kpi.data:
            print(f"DEBUG TTFV 21 hours: kpi_id={kpi.kpi_id}, data='{kpi.data}'")
            parsed_value = HealthScoreEngine.parse_kpi_value(kpi.data, kpi.kpi_parameter)
            print(f"DEBUG TTFV 21 hours: parsed_value={parsed_value}")
            health_info = HealthScoreEngine.calculate_health_status(parsed_value, kpi.kpi_parameter)
            print(f"DEBUG TTFV 21 hours: health_info={health_info}")
        else:
            # Calculate health status using the health score engine
            health_info = HealthScoreEngine.calculate_health_status(
                HealthScoreEngine.parse_kpi_value(kpi.data, kpi.kpi_parameter), 
                kpi.kpi_parameter
            )
        
        # Convert to medical blood test terminology
        status_mapping = {
            'low': 'Critical',
            'medium': 'Risk', 
            'high': 'Healthy',
            'unknown': 'Unknown'
        }
        
        health_statuses.append({
            "kpi_id": kpi.kpi_id,
            "account_id": kpi.account_id,
            "category": kpi.category,
            "kpi_parameter": kpi.kpi_parameter,
            "data": kpi.data,
            "health_status": status_mapping.get(health_info['status'], 'Unknown'),
            "health_score": health_info['score'],
            "health_color": health_info['color'],
            "reference_range": health_info['reference_range']
        })
    
    return jsonify({"health_statuses": health_statuses}), 200

@health_status_api.route('/api/health-status/summary', methods=['GET'])
def get_health_status_summary():
    """
    Get health status summary for a customer or account
    """
    customer_id = get_current_customer_id()
    account_id = request.args.get('account_id')
    
    if not customer_id:
        return jsonify({"error": "X-Customer-ID header is required"}), 400
    
    try:
        customer_id = int(customer_id)
    except ValueError:
        return jsonify({"error": "Invalid X-Customer-ID"}), 400
    
    # Build query
    query = KPI.query.join(Account).filter(Account.customer_id == customer_id)
    
    if account_id:
        try:
            account_id = int(account_id)
            query = query.filter(KPI.account_id == account_id)
        except ValueError:
            return jsonify({"error": "Invalid account_id"}), 400
    
    kpis = query.all()
    
    # Count health statuses
    status_counts = {'Healthy': 0, 'Risk': 0, 'Critical': 0, 'Unknown': 0}
    category_breakdown = {}
    
    for kpi in kpis:
        health_info = HealthScoreEngine.calculate_health_status(
            HealthScoreEngine.parse_kpi_value(kpi.data, kpi.kpi_parameter), 
            kpi.kpi_parameter
        )
        
        status_mapping = {
            'low': 'Critical',
            'medium': 'Risk', 
            'high': 'Healthy',
            'unknown': 'Unknown'
        }
        
        status = status_mapping.get(health_info['status'], 'Unknown')
        status_counts[status] += 1
        
        # Category breakdown
        if kpi.category not in category_breakdown:
            category_breakdown[kpi.category] = {'Healthy': 0, 'Risk': 0, 'Critical': 0, 'Unknown': 0}
        category_breakdown[kpi.category][status] += 1
    
    # Also include reference ranges from the actual config
    from health_score_config import KPI_REFERENCE_RANGES
    reference_ranges = []
    for kpi_name, config in KPI_REFERENCE_RANGES.items():
        # Get the actual ranges from the config
        low_range = config['ranges']['low']
        medium_range = config['ranges']['medium'] 
        high_range = config['ranges']['high']
        
        # Format ranges properly based on higher_is_better
        if config['higher_is_better']:
            critical_range = f"{low_range['min']}-{low_range['max']} {config['unit']}"
            risk_range = f"{medium_range['min']}-{medium_range['max']} {config['unit']}"
            healthy_range = f"{high_range['min']}-{high_range['max']} {config['unit']}"
        else:  # Lower is better (like TTFV)
            critical_range = f"{high_range['min']}-{high_range['max']} {config['unit']}"
            risk_range = f"{medium_range['min']}-{medium_range['max']} {config['unit']}"
            healthy_range = f"{low_range['min']}-{low_range['max']} {config['unit']}"
        
        reference_ranges.append({
            "kpi_name": kpi_name,
            "ranges": config['ranges'],
            "unit": config['unit'],
            "higher_is_better": config['higher_is_better'],
            "critical_range": critical_range,
            "risk_range": risk_range,
            "healthy_range": healthy_range
        })

    return jsonify({
        "total_kpis": len(kpis),
        "status_counts": status_counts,
        "category_breakdown": category_breakdown,
        "reference_ranges": reference_ranges
    }), 200

@health_status_api.route('/api/health-status/test', methods=['GET'])
def test_endpoint():
    """
    Test endpoint to verify the updated code is loading
    """
    return jsonify({"message": "Updated health status API is working!", "timestamp": "2025-09-03"}), 200

@health_status_api.route('/api/health-status/reference-ranges', methods=['GET'])
def get_reference_ranges():
    """
    Get all KPI reference ranges and calculation details
    """
    from health_score_config import KPI_REFERENCE_RANGES
    
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
