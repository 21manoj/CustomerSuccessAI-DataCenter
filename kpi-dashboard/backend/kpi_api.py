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
        
        # DEBUG: Log customer_id to help troubleshoot
        logger.info(f"[DEBUG /api/accounts] customer_id from get_current_customer_id(): {customer_id}")
        
        if not customer_id:
            logger.error("[DEBUG /api/accounts] No customer_id found! User might not be authenticated correctly.")
            return jsonify({'error': 'Customer ID not found. Please log in again.'}), 401
        
        # Get user's vertical for additional filtering (prevents cross-vertical data leakage)
        from flask_login import current_user
        user_vertical = getattr(current_user, 'vertical', None)
        logger.info(f"[DEBUG /api/accounts] user_vertical: {user_vertical}")
        logger.info(f"[DEBUG /api/accounts] current_user.customer_id: {getattr(current_user, 'customer_id', 'N/A')}")
        
        # Build query - filter by customer_id first
        query = Account.query.filter(Account.customer_id == customer_id)
        logger.info(f"[DEBUG /api/accounts] Query filter: Account.customer_id == {customer_id}")
        
        # Additional security: Filter by vertical to prevent cross-vertical data leakage
        # DC users (vertical='dc2_s') should see ALL accounts for their customer (DC accounts may have various vertical values)
        # SaaS users (vertical='saas' or None) should only see SaaS accounts
        if user_vertical == 'dc2_s':
            # DC users: Show ALL accounts for Customer 9 (DC accounts may have vertical='dc2_s' or other journey states)
            # Don't filter by vertical - Customer 9 accounts have various vertical values (Success Story, Churned, etc.)
            # All accounts belong to Customer 9, so they should all be visible
            pass  # No additional filtering needed - already filtered by customer_id
        elif user_vertical == 'saas' or user_vertical is None:
            # SaaS users see accounts with vertical='saas' or vertical=None (legacy)
            query = query.filter((Account.vertical == 'saas') | (Account.vertical.is_(None)))
        else:
            # For other verticals, filter by that specific vertical
            query = query.filter(Account.vertical == user_vertical)
        
        accounts = query.all()
        logger.info(f"[DEBUG /api/accounts] Query returned {len(accounts)} accounts")
        
        # Import models needed for health score calculation
        from models import HealthTrend
        from playbook_recommendations_api import calculate_health_score_proxy
        
        result = []
        for a in accounts:
            logger.info(f"[DEBUG /api/accounts] Processing account: {a.account_id} (customer_id: {a.customer_id})")
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
                # Calculate health score on-the-fly from KPIs (kpis table)
                health_score = calculate_health_score_proxy(a.account_id)
                # DC2_S: If no data in kpis/health_trends, use onboarding data in dc2s_kpis
                if user_vertical == 'dc2_s' and (health_score is None or health_score == 50.0):
                    try:
                        from models import DC2SKPI
                        from verticals.dc2_s.api_routes import calculate_kpi_health
                        dc2s_kpis = DC2SKPI.query.filter_by(account_id=a.account_id).order_by(
                            DC2SKPI.measured_at.desc()
                        ).all()
                        if dc2s_kpis:
                            latest_time = dc2s_kpis[0].measured_at
                            latest_kpis = {
                                k.kpi_code: float(k.value)
                                for k in dc2s_kpis
                                if k.measured_at == latest_time
                            }
                            if latest_kpis:
                                overall_health, _ = calculate_kpi_health(latest_kpis, customer_id=customer_id)
                                health_score = round(overall_health, 1)
                                logger.info(f"[DEBUG /api/accounts] Using dc2s_kpis health (config-aware) for account {a.account_id}: {health_score}")
                    except Exception as e:
                        logger.debug(f"DC2_S health fallback skipped for account {a.account_id}: {e}")
            
            # Get products for this account
            products = Product.query.filter_by(account_id=a.account_id).all()
            products_list = [p.product_name for p in products] if products else []
            
            # Get products_used from profile_metadata if not found in Product table
            if not products_list and hasattr(a, 'profile_metadata') and a.profile_metadata:
                products_used_meta = a.profile_metadata.get('products_used')
                if products_used_meta:
                    # Handle both list and string formats
                    if isinstance(products_used_meta, list):
                        products_list = products_used_meta
                    elif isinstance(products_used_meta, str):
                        products_list = [p.strip() for p in products_used_meta.split(',') if p.strip()]
            
            result.append({
                'account_id': a.account_id,
                'uuid': getattr(a, 'uuid', None),
                'customer_id': a.customer_id,
                'customer_uuid': getattr(a, 'customer_uuid', None),
                'account_name': a.account_name,
                'revenue': float(a.revenue) if a.revenue else 0,
                'status': a.account_status,
                'industry': a.industry,
                'region': a.region,
                'health_score': health_score,
                'account_status': a.account_status,
                'created_at': a.created_at.isoformat() if a.created_at else None,
                'profile_metadata': a.profile_metadata if hasattr(a, 'profile_metadata') and a.profile_metadata else None,
                'products_used': products_list
            })
        
        return jsonify({
            'status': 'success',
            'accounts': result,
            'total': len(result)
        })
        
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
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

@kpi_api.route('/api/accounts/<int:account_id>/products', methods=['GET'])
def get_account_products(account_id):
    """Get all products for a specific account"""
    try:
        customer_id = get_current_customer_id()
        
        # Verify account belongs to customer
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Get products for this account
        products = Product.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).all()
        
        result = []
        for product in products:
            result.append({
                'product_id': product.product_id,
                'account_id': product.account_id,
                'customer_id': product.customer_id,
                'product_name': product.product_name,
                'product_sku': product.product_sku,
                'product_type': product.product_type,
                'revenue': float(product.revenue) if product.revenue else 0,
                'status': product.status,
                'created_at': product.created_at.isoformat() if product.created_at else None,
                'updated_at': product.updated_at.isoformat() if product.updated_at else None
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting products for account {account_id}: {e}", exc_info=True)
        return jsonify({'error': 'Failed to get products'}), 500

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
    # Ensure we start with a clean transaction state
    try:
        db.session.rollback()
    except:
        pass
    
    try:
        # Get customer_id directly from current_user to avoid session transaction issues
        from flask_login import current_user
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        customer_id = current_user.customer_id
        if not customer_id:
            return jsonify({'error': 'Customer ID not found'}), 400
        
        # Use KPI.query instead of db.session.query to avoid transaction issues
        # Simplified query: Get KPIs and join accounts separately
        # This avoids complex joins that might cause transaction issues
        kpis_list = KPI.query.join(
            Account, KPI.account_id == Account.account_id
        ).filter(
            Account.customer_id == customer_id
        ).all()
        
        if not kpis_list:
            return jsonify([])  # Return empty list if no KPIs
        
        # Build account lookup
        account_ids = list(set(kpi.account_id for kpi in kpis_list))
        accounts_list = Account.query.filter(
            Account.account_id.in_(account_ids),
            Account.customer_id == customer_id
        ).all()
        accounts = {acc.account_id: acc for acc in accounts_list}
        
        # Build upload lookup
        upload_ids = [kpi.upload_id for kpi in kpis_list if kpi.upload_id]
        uploads = {}
        if upload_ids:
            uploads_list = KPIUpload.query.filter(
                KPIUpload.upload_id.in_(upload_ids)
            ).all()
            uploads = {upl.upload_id: upl for upl in uploads_list}
        
        result = []
        for kpi in kpis_list:
            account = accounts.get(kpi.account_id)
            upload = uploads.get(kpi.upload_id) if kpi.upload_id else None
            
            result.append({
                'kpi_id': kpi.kpi_id,
                'account_id': kpi.account_id,
                'account_name': account.account_name if account else 'Unknown Account',
                'account_revenue': float(account.revenue) if account and account.revenue else 0,
                'account_industry': account.industry if account else 'Unknown',
                'account_region': account.region if account else 'Unknown',
                'product_id': kpi.product_id,
                'product_name': None,  # Product lookup skipped due to schema mismatch
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
                'last_edited_at': kpi.last_edited_at.isoformat() if kpi.last_edited_at else None,
                'upload_id': kpi.upload_id,
                'upload_filename': upload.original_filename if upload else None
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting all KPIs: {e}", exc_info=True)
        db.session.rollback()  # Ensure transaction is cleared
        return jsonify({'error': 'Failed to get KPIs. Please try again or contact support.'}), 500

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
