#!/usr/bin/env python3
"""
KPI API - Handles KPI configuration, accounts, and KPI data management

FIXED: Line 150 - Improved query security with customer_id filtering in query
FIXED: SQLAlchemy 2.0 compatibility - Replaced .query.get() with db.session.get()
FIXED: Replaced .query.get_or_404() with proper filtering + first_or_404()
"""

from flask import Blueprint, request, jsonify, abort
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import KPI, KPIUpload, Account, CustomerConfig, Product
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

kpi_api = Blueprint('kpi_api', __name__)

# Use get_current_customer_id from auth_middleware (imported above)
# No need to redefine it here

# ========================================
# CONFIGURATION ENDPOINTS
# ========================================

@kpi_api.route('/api/config', methods=['GET'])
def get_customer_config():
    """Get customer configuration including KPI upload mode"""
    try:
        customer_id = get_current_customer_id()
        
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            # Create default config
            config = CustomerConfig(
                customer_id=customer_id,
                kpi_upload_mode='corporate'  # Default to corporate mode
            )
            db.session.add(config)
            db.session.commit()
        
        return jsonify({
            'kpi_upload_mode': config.kpi_upload_mode,
            'description': _get_mode_description(config.kpi_upload_mode)
        })
        
    except Exception as e:
        logger.error(f"Error getting customer config: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to get configuration'}), 500

@kpi_api.route('/api/config', methods=['PUT'])
def update_customer_config():
    """Update customer configuration"""
    try:
        customer_id = get_current_customer_id()
        data = request.json
        
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            config = CustomerConfig(customer_id=customer_id)
            db.session.add(config)
        
        if 'kpi_upload_mode' in data:
            if data['kpi_upload_mode'] not in ['corporate', 'account_rollup']:
                abort(400, 'Invalid kpi_upload_mode. Must be "corporate" or "account_rollup"')
            config.kpi_upload_mode = data['kpi_upload_mode']
        
        db.session.commit()
        
        return jsonify({
            'status': 'updated',
            'kpi_upload_mode': config.kpi_upload_mode,
            'description': _get_mode_description(config.kpi_upload_mode)
        })
        
    except Exception as e:
        logger.error(f"Error updating customer config: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to update configuration'}), 500

def _get_mode_description(mode):
    """Get description for upload mode"""
    descriptions = {
        'corporate': 'Upload corporate-level KPIs directly. Each upload represents the overall customer KPI sheet.',
        'account_rollup': 'Upload account-level KPIs and automatically roll up to corporate level using revenue-weighted averaging.'
    }
    return descriptions.get(mode, 'Unknown mode')

# ========================================
# ACCOUNT MANAGEMENT ENDPOINTS
# ========================================

@kpi_api.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Get all accounts for a customer"""
    try:
        customer_id = get_current_customer_id()
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        # Import models needed for health score calculation
        from models import HealthTrend
        from playbook_recommendations_api import calculate_health_score_proxy
        
        result = []
        for a in accounts:
            # First try to get health score from health_trends table
            latest_trend = HealthTrend.query.filter_by(
                account_id=a.account_id,
                customer_id=customer_id
            ).order_by(
                HealthTrend.year.desc(),
                HealthTrend.month.desc()
            ).first()
            
            health_score = None
            if latest_trend and latest_trend.overall_health_score:
                health_score = float(latest_trend.overall_health_score)
            else:
                # Calculate health score on-the-fly from KPIs
                health_score = calculate_health_score_proxy(a.account_id)
            
            # Get products for this account
            products = Product.query.filter_by(account_id=a.account_id).all()
            products_list = [p.product_name for p in products] if products else []
            
            result.append({
                'account_id': a.account_id,
                'customer_id': a.customer_id,
                'account_name': a.account_name,
                'revenue': float(a.revenue) if a.revenue else 0,
                'status': a.account_status,
                'industry': a.industry,
                'region': a.region,
                'health_score': health_score,
                'account_status': a.account_status,
                'created_at': a.created_at.isoformat() if a.created_at else None,
                'profile_metadata': a.profile_metadata if hasattr(a, 'profile_metadata') and a.profile_metadata else None,
                'products_used': products_list if products_list else (a.profile_metadata.get('products_used', '').split(',') if (hasattr(a, 'profile_metadata') and a.profile_metadata and a.profile_metadata.get('products_used')) else [])
            })
        
        return jsonify({
            'status': 'success',
            'accounts': result,
            'total': len(result)
        })
        
    except Exception as e:
        logger.error(f"Error getting accounts: {e}", exc_info=True)
        return jsonify({'error': 'Failed to get accounts'}), 500

@kpi_api.route('/api/accounts', methods=['POST'])
def create_account():
    """Create a new account"""
    try:
        customer_id = get_current_customer_id()
        data = request.json
        
        if not data.get('account_name'):
            return jsonify({'error': 'account_name is required'}), 400
        
        account = Account(
            customer_id=customer_id,
            account_name=data['account_name'],
            revenue=data.get('revenue', 0),
            industry=data.get('industry'),
            region=data.get('region'),
            account_status=data.get('account_status', 'active')
        )
        
        db.session.add(account)
        db.session.commit()
        
        return jsonify({
            'account_id': account.account_id,
            'status': 'created'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating account: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to create account'}), 500

@kpi_api.route('/api/accounts/<int:account_id>', methods=['PUT'])
def update_account(account_id):
    """Update an account"""
    try:
        customer_id = get_current_customer_id()
        
        # ✅ FIXED: Use db.session.get() instead of deprecated .query.get()
        account = db.session.get(Account, account_id)
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Validate customer ownership
        if account.customer_id != customer_id:
            abort(403, 'Forbidden: Account does not belong to your customer')
        
        data = request.json
        for field in ['account_name', 'revenue', 'industry', 'region', 'account_status']:
            if field in data:
                setattr(account, field, data[field])
        
        db.session.commit()
        return jsonify({'status': 'updated'})
        
    except Exception as e:
        logger.error(f"Error updating account {account_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to update account'}), 500

@kpi_api.route('/api/accounts/<int:account_id>/kpis', methods=['GET'])
def get_account_kpis(account_id):
    """Get all KPIs for a specific account"""
    try:
        customer_id = get_current_customer_id()
        
        # ✅ FIXED: Validate account ownership using filter instead of get()
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found or access denied'}), 404
        
        kpis = KPI.query.filter_by(account_id=account_id).all()
        
        return jsonify([{
            'kpi_id': k.kpi_id,
            'account_id': k.account_id,
            'category': k.category,
            'row_index': k.row_index,
            'health_score_component': k.health_score_component,
            'weight': k.weight,
            'data': k.data,
            'source_review': k.source_review,
            'kpi_parameter': k.kpi_parameter,
            'impact_level': k.impact_level,
            'measurement_frequency': k.measurement_frequency,
            'last_edited_by': k.last_edited_by,
            'last_edited_at': k.last_edited_at.isoformat() if k.last_edited_at else None
        } for k in kpis])
        
    except Exception as e:
        logger.error(f"Error getting KPIs for account {account_id}: {e}", exc_info=True)
        return jsonify({'error': 'Failed to get KPIs'}), 500

# ========================================
# KPI MANAGEMENT ENDPOINTS
# ========================================

@kpi_api.route('/api/kpi/<int:kpi_id>', methods=['PATCH'])
def edit_kpi(kpi_id):
    """
    Edit a single KPI entry by ID, enforcing customer ownership.
    
    ✅ FIXED: Now filters by customer_id in the query itself (not after fetching)
    ✅ FIXED: SQLAlchemy 2.0 compatible (no deprecated .query.get())
    """
    try:
        customer_id = get_current_customer_id()
        
        # ✅ FIXED: Join with KPIUpload to filter by customer_id in the query
        kpi = db.session.query(KPI).join(
            KPIUpload, KPI.upload_id == KPIUpload.upload_id
        ).filter(
            KPI.kpi_id == kpi_id,
            KPIUpload.customer_id == customer_id
        ).first()
        
        if not kpi:
            return jsonify({'error': 'KPI not found or access denied'}), 404
        
        # Update KPI fields
        data = request.json
        for field in ['health_score_component', 'weight', 'data', 'source_review', 
                      'kpi_parameter', 'impact_level', 'measurement_frequency', 'account_id']:
            if field in data:
                setattr(kpi, field, data[field])
        
        # Update metadata
        kpi.last_edited_by = get_current_user_id()
        kpi.last_edited_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'status': 'updated',
            'kpi_id': kpi.kpi_id
        })
        
    except Exception as e:
        logger.error(f"Error editing KPI {kpi_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to update KPI'}), 500

@kpi_api.route('/api/kpis/customer/all', methods=['GET'])
def get_all_kpis():
    """Get all KPIs for a customer with account and product information"""
    try:
        customer_id = get_current_customer_id()
        
        # Get KPIs with account and product information for this customer
        kpis = db.session.query(KPI, Account, Product).join(
            KPIUpload, KPI.upload_id == KPIUpload.upload_id
        ).join(
            Account, KPI.account_id == Account.account_id, isouter=True
        ).outerjoin(
            Product, KPI.product_id == Product.product_id
        ).filter(
            KPIUpload.customer_id == customer_id
        ).all()
        
        result = []
        for kpi, account, product in kpis:
            result.append({
                'kpi_id': kpi.kpi_id,
                'account_id': kpi.account_id,
                'account_name': account.account_name if account else 'Unknown Account',
                'account_revenue': float(account.revenue) if account and account.revenue else 0,
                'account_industry': account.industry if account else 'Unknown',
                'account_region': account.region if account else 'Unknown',
                'product_id': kpi.product_id,
                'product_name': product.product_name if product else None,
                'aggregation_type': kpi.aggregation_type,
                'category': kpi.category,
                'row_index': kpi.row_index,
                'health_score_component': kpi.health_score_component,
                'weight': kpi.weight,
                'data': kpi.data,
                'source_review': kpi.source_review,
                'kpi_parameter': kpi.kpi_parameter,
                'impact_level': kpi.impact_level,
                'measurement_frequency': kpi.measurement_frequency,
                'last_edited_by': kpi.last_edited_by,
                'last_edited_at': kpi.last_edited_at.isoformat() if kpi.last_edited_at else None
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting all KPIs: {e}", exc_info=True)
        return jsonify({'error': 'Failed to get KPIs'}), 500

@kpi_api.route('/api/test-kpis', methods=['GET'])
def test_kpis():
    """Test endpoint for KPIs"""
    return jsonify({'message': 'KPI API is working'})

@kpi_api.route('/api/kpis/<int:upload_id>', methods=['GET'])
def get_kpis(upload_id):
    """Get all KPIs for a given upload, enforcing customer ownership."""
    try:
        customer_id = get_current_customer_id()
        
        # ✅ FIXED: Use filter instead of deprecated .query.get_or_404()
        upload = KPIUpload.query.filter_by(
            upload_id=upload_id,
            customer_id=customer_id
        ).first()
        
        if not upload:
            return jsonify({'error': 'Upload not found or access denied'}), 404
        
        # Get KPIs with account information
        kpis = db.session.query(KPI, Account).join(
            Account, KPI.account_id == Account.account_id, isouter=True
        ).filter(
            KPI.upload_id == upload_id
        ).all()
        
        result = []
        for kpi, account in kpis:
            result.append({
                'kpi_id': kpi.kpi_id,
                'account_id': kpi.account_id,
                'account_name': account.account_name if account else 'Unknown Account',
                'account_revenue': float(account.revenue) if account and account.revenue else 0,
                'account_industry': account.industry if account else 'Unknown',
                'account_region': account.region if account else 'Unknown',
                'category': kpi.category,
                'row_index': kpi.row_index,
                'health_score_component': kpi.health_score_component,
                'weight': kpi.weight,
                'data': kpi.data,
                'source_review': kpi.source_review,
                'kpi_parameter': kpi.kpi_parameter,
                'impact_level': kpi.impact_level,
                'measurement_frequency': kpi.measurement_frequency,
                'last_edited_by': kpi.last_edited_by,
                'last_edited_at': kpi.last_edited_at.isoformat() if kpi.last_edited_at else None
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting KPIs for upload {upload_id}: {e}", exc_info=True)
        return jsonify({'error': 'Failed to get KPIs'}), 500