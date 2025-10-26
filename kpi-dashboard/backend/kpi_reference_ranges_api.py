#!/usr/bin/env python3
"""
KPI Reference Ranges API
Manages blood sample-like thresholds for KPI health scoring
"""

from flask import Blueprint, request, jsonify
from extensions import db
from models import KPIReferenceRange, Customer
import json

kpi_reference_ranges_api = Blueprint('kpi_reference_ranges_api', __name__)

def get_customer_id():
    """Get customer ID from request headers"""
    return request.headers.get('X-Customer-ID', type=int, default=1)

@kpi_reference_ranges_api.route('/api/kpi-reference-ranges', methods=['GET'])
def get_kpi_reference_ranges():
    """Get all KPI reference ranges for the customer"""
    try:
        customer_id = get_customer_id()
        
        # Get all reference ranges
        ranges = KPIReferenceRange.query.all()
        
        result = []
        for ref_range in ranges:
            # Recalculate range strings from numeric values to ensure correctness
            # Don't trust the string fields which may be stale
            critical_range_str = f"{ref_range.critical_min}-{ref_range.critical_max} {ref_range.unit}"
            risk_range_str = f"{ref_range.risk_min}-{ref_range.risk_max} {ref_range.unit}"
            healthy_range_str = f"{ref_range.healthy_min}-{ref_range.healthy_max} {ref_range.unit}"
            
            result.append({
                'range_id': ref_range.range_id,
                'kpi_name': ref_range.kpi_name,
                'unit': ref_range.unit,
                'higher_is_better': ref_range.higher_is_better,
                'critical_range': critical_range_str,
                'risk_range': risk_range_str,
                'healthy_range': healthy_range_str,
                'critical_min': ref_range.critical_min,
                'critical_max': ref_range.critical_max,
                'risk_min': ref_range.risk_min,
                'risk_max': ref_range.risk_max,
                'healthy_min': ref_range.healthy_min,
                'healthy_max': ref_range.healthy_max,
                'description': ref_range.description or ''
            })
        
        return jsonify({
            'status': 'success',
            'ranges': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch KPI reference ranges: {str(e)}'
        }), 500

@kpi_reference_ranges_api.route('/api/kpi-reference-ranges/<int:range_id>', methods=['PUT'])
def update_kpi_reference_range(range_id):
    """Update a specific KPI reference range"""
    try:
        customer_id = get_customer_id()
        data = request.json
        
        # Find the reference range
        ref_range = KPIReferenceRange.query.get(range_id)
        if not ref_range:
            return jsonify({
                'status': 'error',
                'message': 'KPI reference range not found'
            }), 404
        
        # Update the range
        ref_range.critical_min = float(data.get('critical_min', ref_range.critical_min))
        ref_range.critical_max = float(data.get('critical_max', ref_range.critical_max))
        ref_range.risk_min = float(data.get('risk_min', ref_range.risk_min))
        ref_range.risk_max = float(data.get('risk_max', ref_range.risk_max))
        ref_range.healthy_min = float(data.get('healthy_min', ref_range.healthy_min))
        ref_range.healthy_max = float(data.get('healthy_max', ref_range.healthy_max))
        ref_range.description = data.get('description', ref_range.description)
        
        # Update range strings
        ref_range.critical_range = f"{ref_range.critical_min}-{ref_range.critical_max}"
        ref_range.risk_range = f"{ref_range.risk_min}-{ref_range.risk_max}"
        ref_range.healthy_range = f"{ref_range.healthy_min}-{ref_range.healthy_max}"
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'KPI reference range updated successfully',
            'range': {
                'range_id': ref_range.range_id,
                'kpi_name': ref_range.kpi_name,
                'unit': ref_range.unit,
                'higher_is_better': ref_range.higher_is_better,
                'critical_range': ref_range.critical_range,
                'risk_range': ref_range.risk_range,
                'healthy_range': ref_range.healthy_range,
                'critical_min': ref_range.critical_min,
                'critical_max': ref_range.critical_max,
                'risk_min': ref_range.risk_min,
                'risk_max': ref_range.risk_max,
                'healthy_min': ref_range.healthy_min,
                'healthy_max': ref_range.healthy_max,
                'description': ref_range.description
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to update KPI reference range: {str(e)}'
        }), 500

@kpi_reference_ranges_api.route('/api/kpi-reference-ranges/bulk-update', methods=['POST'])
def bulk_update_kpi_reference_ranges():
    """Bulk update multiple KPI reference ranges"""
    try:
        customer_id = get_customer_id()
        data = request.json
        ranges = data.get('ranges', [])
        
        updated_count = 0
        for range_data in ranges:
            range_id = range_data.get('range_id')
            if not range_id:
                continue
                
            ref_range = KPIReferenceRange.query.get(range_id)
            if not ref_range:
                continue
            
            # Update the range
            ref_range.critical_min = float(range_data.get('critical_min', ref_range.critical_min))
            ref_range.critical_max = float(range_data.get('critical_max', ref_range.critical_max))
            ref_range.risk_min = float(range_data.get('risk_min', ref_range.risk_min))
            ref_range.risk_max = float(range_data.get('risk_max', ref_range.risk_max))
            ref_range.healthy_min = float(range_data.get('healthy_min', ref_range.healthy_min))
            ref_range.healthy_max = float(range_data.get('healthy_max', ref_range.healthy_max))
            ref_range.description = range_data.get('description', ref_range.description)
            
            # Update range strings
            ref_range.critical_range = f"{ref_range.critical_min}-{ref_range.critical_max}"
            ref_range.risk_range = f"{ref_range.risk_min}-{ref_range.risk_max}"
            ref_range.healthy_range = f"{ref_range.healthy_min}-{ref_range.healthy_max}"
            
            updated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully updated {updated_count} KPI reference ranges',
            'updated_count': updated_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to bulk update KPI reference ranges: {str(e)}'
        }), 500

@kpi_reference_ranges_api.route('/api/kpi-reference-ranges/reset', methods=['POST'])
def reset_kpi_reference_ranges():
    """Reset KPI reference ranges to default values"""
    try:
        customer_id = get_customer_id()
        
        # Import the default configuration
        from health_score_config import KPI_REFERENCE_RANGES
        
        # Clear existing ranges
        KPIReferenceRange.query.delete()
        
        # Insert default ranges
        for kpi_name, config in KPI_REFERENCE_RANGES.items():
            ranges = config['ranges']
            
            # For higher_is_better: True, low color = red (critical), high color = green (healthy)
            # For higher_is_better: False, low value = good (healthy), high value = bad (critical)
            
            higher_is_better = config['higher_is_better']
            
            if higher_is_better:
                # Higher is better: low range = red (critical), high range = green (healthy)
                critical_min = ranges['low']['min']
                critical_max = ranges['low']['max']
                risk_min = ranges['medium']['min']
                risk_max = ranges['medium']['max']
                healthy_min = ranges['high']['min']
                healthy_max = ranges['high']['max']
            else:
                # Lower is better: low range = green (healthy), high range = red (critical)
                # Need to reverse the mapping
                healthy_min = ranges['low']['min']  # Low values are healthy (green)
                healthy_max = ranges['low']['max']
                risk_min = ranges['medium']['min']
                risk_max = ranges['medium']['max']
                critical_min = ranges['high']['min']  # High values are critical (red)
                critical_max = ranges['high']['max']
            
            ref_range = KPIReferenceRange(
                kpi_name=kpi_name,
                unit=config['unit'],
                higher_is_better=config['higher_is_better'],
                critical_min=critical_min,
                critical_max=critical_max,
                risk_min=risk_min,
                risk_max=risk_max,
                healthy_min=healthy_min,
                healthy_max=healthy_max,
                critical_range=f"{critical_min}-{critical_max} {config['unit']}",
                risk_range=f"{risk_min}-{risk_max} {config['unit']}",
                healthy_range=f"{healthy_min}-{healthy_max} {config['unit']}",
                description=f"Default reference range for {kpi_name}"
            )
            db.session.add(ref_range)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'KPI reference ranges reset to default values',
            'total_ranges': len(KPI_REFERENCE_RANGES)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to reset KPI reference ranges: {str(e)}'
        }), 500

@kpi_reference_ranges_api.route('/api/kpi-reference-ranges/health-status', methods=['POST'])
def calculate_health_status():
    """Calculate health status for a given KPI value"""
    try:
        data = request.json
        kpi_name = data.get('kpi_name')
        value = float(data.get('value', 0))
        
        if not kpi_name:
            return jsonify({
                'status': 'error',
                'message': 'KPI name is required'
            }), 400
        
        # Get reference range
        ref_range = KPIReferenceRange.query.filter_by(kpi_name=kpi_name).first()
        if not ref_range:
            return jsonify({
                'status': 'error',
                'message': f'No reference range found for KPI: {kpi_name}'
            }), 404
        
        # Calculate health status
        from health_score_engine import HealthScoreEngine
        health_status = HealthScoreEngine.calculate_health_status(value, kpi_name)
        
        return jsonify({
            'status': 'success',
            'kpi_name': kpi_name,
            'value': value,
            'unit': ref_range.unit,
            'health_status': health_status,
            'reference_range': {
                'critical': ref_range.critical_range,
                'risk': ref_range.risk_range,
                'healthy': ref_range.healthy_range
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to calculate health status: {str(e)}'
        }), 500
