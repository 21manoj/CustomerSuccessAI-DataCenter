#!/usr/bin/env python3
"""
KPI Reference Ranges API
Manages blood sample-like thresholds for KPI health scoring
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import KPIReferenceRange, Customer
import json

kpi_reference_ranges_api = Blueprint('kpi_reference_ranges_api', __name__)



@kpi_reference_ranges_api.route('/api/kpi-reference-ranges', methods=['GET'])
def get_kpi_reference_ranges():
    """
    Get all KPI reference ranges for the customer with fallback to system defaults.
    
    Strategy:
    1. Get customer-specific ranges (customer_id = X)
    2. Get system default ranges (customer_id = NULL)
    3. Merge: customer overrides take precedence over defaults
    """
    try:
        customer_id = get_current_customer_id()
        
        # Get customer-specific ranges
        customer_ranges = KPIReferenceRange.query.filter_by(customer_id=customer_id).all()
        
        # Get system default ranges (customer_id = NULL)
        system_ranges = KPIReferenceRange.query.filter_by(customer_id=None).all()
        
        # Create a dictionary to merge ranges (customer overrides take precedence)
        ranges_dict = {}
        
        # First, add all system defaults
        for ref_range in system_ranges:
            ranges_dict[ref_range.kpi_name] = {
                'range': ref_range,
                'is_custom': False,
                'source': 'System Default'
            }
        
        # Then, override with customer-specific ranges
        for ref_range in customer_ranges:
            ranges_dict[ref_range.kpi_name] = {
                'range': ref_range,
                'is_custom': True,
                'source': f'Custom Override'
            }
        
        # Build result list
        result = []
        for kpi_name, data in ranges_dict.items():
            ref_range = data['range']
            
            # Recalculate range strings from numeric values to ensure correctness
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
                'description': ref_range.description or '',
                'is_custom': data['is_custom'],
                'source': data['source'],
                'customer_id': ref_range.customer_id
            })
        
        # Sort by KPI name for consistency
        result.sort(key=lambda x: x['kpi_name'])
        
        # Count summary
        custom_count = sum(1 for r in result if r['is_custom'])
        system_count = len(result) - custom_count
        
        return jsonify({
            'status': 'success',
            'ranges': result,
            'total': len(result),
            'summary': {
                'custom_overrides': custom_count,
                'system_defaults': system_count,
                'customer_id': customer_id
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch KPI reference ranges: {str(e)}'
        }), 500

@kpi_reference_ranges_api.route('/api/kpi-reference-ranges/<int:range_id>', methods=['PUT'])
def update_kpi_reference_range(range_id):
    """
    Update a specific KPI reference range with copy-on-write behavior.
    
    If editing a system default (customer_id=NULL):
    - Creates a customer-specific override instead of modifying the system default
    
    If editing a customer override (customer_id=X):
    - Updates the existing customer override
    """
    try:
        customer_id = get_current_customer_id()
        data = request.json
        
        # Find the reference range
        ref_range = db.session.get(KPIReferenceRange, range_id)
        if not ref_range:
            return jsonify({
                'status': 'error',
                'message': 'KPI reference range not found'
            }), 404
        
        # COPY-ON-WRITE LOGIC
        # If this is a system default (customer_id=NULL), create a customer override
        if ref_range.customer_id is None:
            # Check if customer already has an override for this KPI
            existing_override = KPIReferenceRange.query.filter_by(
                customer_id=customer_id,
                kpi_name=ref_range.kpi_name
            ).first()
            
            if existing_override:
                # Customer already has an override, update it
                target_range = existing_override
                action = 'updated'
            else:
                # Create a new customer-specific override (copy-on-write)
                target_range = KPIReferenceRange(
                    customer_id=customer_id,
                    kpi_name=ref_range.kpi_name,
                    unit=ref_range.unit,
                    higher_is_better=ref_range.higher_is_better,
                    critical_min=ref_range.critical_min,
                    critical_max=ref_range.critical_max,
                    risk_min=ref_range.risk_min,
                    risk_max=ref_range.risk_max,
                    healthy_min=ref_range.healthy_min,
                    healthy_max=ref_range.healthy_max,
                    description=ref_range.description,
                    created_by=customer_id,
                    updated_by=customer_id
                )
                db.session.add(target_range)
                action = 'created'
        else:
            # This is already a customer override
            # Only allow the owner to update it
            if ref_range.customer_id != customer_id:
                return jsonify({
                    'status': 'error',
                    'message': 'Cannot update another customer\'s reference range'
                }), 403
            
            target_range = ref_range
            action = 'updated'
        
        # Apply updates to target range
        target_range.critical_min = float(data.get('critical_min', target_range.critical_min))
        target_range.critical_max = float(data.get('critical_max', target_range.critical_max))
        target_range.risk_min = float(data.get('risk_min', target_range.risk_min))
        target_range.risk_max = float(data.get('risk_max', target_range.risk_max))
        target_range.healthy_min = float(data.get('healthy_min', target_range.healthy_min))
        target_range.healthy_max = float(data.get('healthy_max', target_range.healthy_max))
        target_range.description = data.get('description', target_range.description)
        target_range.updated_by = customer_id
        
        # Update range strings
        target_range.critical_range = f"{target_range.critical_min}-{target_range.critical_max}"
        target_range.risk_range = f"{target_range.risk_min}-{target_range.risk_max}"
        target_range.healthy_range = f"{target_range.healthy_min}-{target_range.healthy_max}"
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'KPI reference range {action} successfully (customer override)',
            'action': action,
            'range': {
                'range_id': target_range.range_id,
                'kpi_name': target_range.kpi_name,
                'unit': target_range.unit,
                'higher_is_better': target_range.higher_is_better,
                'critical_range': target_range.critical_range,
                'risk_range': target_range.risk_range,
                'healthy_range': target_range.healthy_range,
                'critical_min': target_range.critical_min,
                'critical_max': target_range.critical_max,
                'risk_min': target_range.risk_min,
                'risk_max': target_range.risk_max,
                'healthy_min': target_range.healthy_min,
                'healthy_max': target_range.healthy_max,
                'description': target_range.description,
                'is_custom': True,
                'customer_id': target_range.customer_id
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
        customer_id = get_current_customer_id()
        data = request.json
        ranges = data.get('ranges', [])
        
        updated_count = 0
        for range_data in ranges:
            range_id = range_data.get('range_id')
            if not range_id:
                continue
                
            ref_range = db.session.get(KPIReferenceRange, range_id)
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
        customer_id = get_current_customer_id()
        
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
            
            # Map ranges by color (not by key name!)
            # Find which range has which color
            critical_range = None
            risk_range = None
            healthy_range = None
            
            for key, range_data in ranges.items():
                if range_data['color'] == 'red':
                    critical_range = range_data
                elif range_data['color'] == 'yellow':
                    risk_range = range_data
                elif range_data['color'] == 'green':
                    healthy_range = range_data
            
            # Assign based on color mapping
            critical_min = critical_range['min']
            critical_max = critical_range['max']
            risk_min = risk_range['min']
            risk_max = risk_range['max']
            healthy_min = healthy_range['min']
            healthy_max = healthy_range['max']
            
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
