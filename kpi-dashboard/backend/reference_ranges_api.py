#!/usr/bin/env python3
"""
API for managing KPI reference ranges
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import KPIReferenceRange
from decimal import Decimal

reference_ranges_api = Blueprint('reference_ranges_api', __name__)

@reference_ranges_api.route('/api/reference-ranges', methods=['GET'])
def get_all_reference_ranges():
    """Get all KPI reference ranges"""
    try:
        ranges = KPIReferenceRange.query.all()
        
        reference_ranges = []
        for range_obj in ranges:
            reference_ranges.append({
                'range_id': range_obj.range_id,
                'kpi_name': range_obj.kpi_name,
                'unit': range_obj.unit,
                'higher_is_better': range_obj.higher_is_better,
                'critical_range': f"{range_obj.critical_min}-{range_obj.critical_max} {range_obj.unit}",
                'risk_range': f"{range_obj.risk_min}-{range_obj.risk_max} {range_obj.unit}",
                'healthy_range': f"{range_obj.healthy_min}-{range_obj.healthy_max} {range_obj.unit}",
                'critical_min': float(range_obj.critical_min),
                'critical_max': float(range_obj.critical_max),
                'risk_min': float(range_obj.risk_min),
                'risk_max': float(range_obj.risk_max),
                'healthy_min': float(range_obj.healthy_min),
                'healthy_max': float(range_obj.healthy_max),
                'created_at': range_obj.created_at.isoformat() if range_obj.created_at else None,
                'updated_at': range_obj.updated_at.isoformat() if range_obj.updated_at else None
            })
        
        return jsonify({
            'success': True,
            'reference_ranges': reference_ranges,
            'total_count': len(reference_ranges)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch reference ranges: {str(e)}'
        }), 500

@reference_ranges_api.route('/api/reference-ranges/<int:range_id>', methods=['PUT'])
def update_reference_range(range_id):
    """Update a specific KPI reference range"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Find the reference range
        ref_range = KPIReferenceRange.query.get(range_id)
        if not ref_range:
            return jsonify({
                'success': False,
                'error': 'Reference range not found'
            }), 404
        
        # Update the fields
        if 'critical_min' in data:
            ref_range.critical_min = Decimal(str(data['critical_min']))
        if 'critical_max' in data:
            ref_range.critical_max = Decimal(str(data['critical_max']))
        if 'risk_min' in data:
            ref_range.risk_min = Decimal(str(data['risk_min']))
        if 'risk_max' in data:
            ref_range.risk_max = Decimal(str(data['risk_max']))
        if 'healthy_min' in data:
            ref_range.healthy_min = Decimal(str(data['healthy_min']))
        if 'healthy_max' in data:
            ref_range.healthy_max = Decimal(str(data['healthy_max']))
        if 'higher_is_better' in data:
            ref_range.higher_is_better = bool(data['higher_is_better'])
        
        # Save changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reference range updated successfully',
            'reference_range': {
                'range_id': ref_range.range_id,
                'kpi_name': ref_range.kpi_name,
                'unit': ref_range.unit,
                'higher_is_better': ref_range.higher_is_better,
                'critical_range': f"{ref_range.critical_min}-{ref_range.critical_max} {ref_range.unit}",
                'risk_range': f"{ref_range.risk_min}-{ref_range.risk_max} {ref_range.unit}",
                'healthy_range': f"{ref_range.healthy_min}-{ref_range.healthy_max} {ref_range.unit}",
                'updated_at': ref_range.updated_at.isoformat() if ref_range.updated_at else None
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to update reference range: {str(e)}'
        }), 500

@reference_ranges_api.route('/api/reference-ranges/bulk-update', methods=['PUT'])
def bulk_update_reference_ranges():
    """Update multiple KPI reference ranges at once"""
    try:
        data = request.get_json()
        
        if not data or 'ranges' not in data:
            return jsonify({
                'success': False,
                'error': 'No ranges data provided'
            }), 400
        
        updated_count = 0
        errors = []
        
        for range_data in data['ranges']:
            try:
                range_id = range_data.get('range_id')
                if not range_id:
                    errors.append(f"Missing range_id for range: {range_data}")
                    continue
                
                ref_range = KPIReferenceRange.query.get(range_id)
                if not ref_range:
                    errors.append(f"Reference range not found for ID: {range_id}")
                    continue
                
                # Update the fields
                if 'critical_min' in range_data:
                    ref_range.critical_min = Decimal(str(range_data['critical_min']))
                if 'critical_max' in range_data:
                    ref_range.critical_max = Decimal(str(range_data['critical_max']))
                if 'risk_min' in range_data:
                    ref_range.risk_min = Decimal(str(range_data['risk_min']))
                if 'risk_max' in range_data:
                    ref_range.risk_max = Decimal(str(range_data['risk_max']))
                if 'healthy_min' in range_data:
                    ref_range.healthy_min = Decimal(str(range_data['healthy_min']))
                if 'healthy_max' in range_data:
                    ref_range.healthy_max = Decimal(str(range_data['healthy_max']))
                if 'higher_is_better' in range_data:
                    ref_range.higher_is_better = bool(range_data['higher_is_better'])
                
                updated_count += 1
                
            except Exception as e:
                errors.append(f"Error updating range {range_data.get('range_id', 'unknown')}: {str(e)}")
        
        # Save all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} reference ranges',
            'updated_count': updated_count,
            'errors': errors if errors else None
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to bulk update reference ranges: {str(e)}'
        }), 500