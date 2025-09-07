from flask import Blueprint, request, jsonify, abort
from extensions import db
from models import KPI, KPIUpload, Account, CustomerConfig
from datetime import datetime

kpi_api = Blueprint('kpi_api', __name__)

def get_customer_id():
    """Extract and validate the X-Customer-ID header from the request."""
    cid = request.headers.get('X-Customer-ID')
    if not cid:
        abort(400, 'Missing X-Customer-ID header')
    try:
        return int(cid)
    except Exception:
        abort(400, 'Invalid X-Customer-ID header')

# Configuration Endpoints
@kpi_api.route('/api/config', methods=['GET'])
def get_customer_config():
    """Get customer configuration including KPI upload mode"""
    customer_id = get_customer_id()
    
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

@kpi_api.route('/api/config', methods=['PUT'])
def update_customer_config():
    """Update customer configuration"""
    customer_id = get_customer_id()
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

def _get_mode_description(mode):
    """Get description for upload mode"""
    descriptions = {
        'corporate': 'Upload corporate-level KPIs directly. Each upload represents the overall customer KPI sheet.',
        'account_rollup': 'Upload account-level KPIs and automatically roll up to corporate level using revenue-weighted averaging.'
    }
    return descriptions.get(mode, 'Unknown mode')

# Account Management Endpoints
@kpi_api.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Get all accounts for a customer"""
    customer_id = get_customer_id()
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    return jsonify([{
        'account_id': a.account_id,
        'account_name': a.account_name,
        'revenue': float(a.revenue),
        'industry': a.industry,
        'region': a.region,
        'account_status': a.account_status,
        'created_at': a.created_at.isoformat() if a.created_at else None
    } for a in accounts])

@kpi_api.route('/api/accounts', methods=['POST'])
def create_account():
    """Create a new account"""
    customer_id = get_customer_id()
    data = request.json
    
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
    })

@kpi_api.route('/api/accounts/<int:account_id>', methods=['PUT'])
def update_account(account_id):
    """Update an account"""
    customer_id = get_customer_id()
    account = Account.query.get_or_404(account_id)
    
    if account.customer_id != customer_id:
        abort(403, 'Forbidden: Account does not belong to your customer')
    
    data = request.json
    for field in ['account_name', 'revenue', 'industry', 'region', 'account_status']:
        if field in data:
            setattr(account, field, data[field])
    
    db.session.commit()
    return jsonify({'status': 'updated'})

@kpi_api.route('/api/accounts/<int:account_id>/kpis', methods=['GET'])
def get_account_kpis(account_id):
    """Get all KPIs for a specific account"""
    customer_id = get_customer_id()
    account = Account.query.get_or_404(account_id)
    
    if account.customer_id != customer_id:
        abort(403, 'Forbidden: Account does not belong to your customer')
    
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
        'last_edited_at': k.last_edited_at
    } for k in kpis])

@kpi_api.route('/api/kpi/<int:kpi_id>', methods=['PATCH'])
def edit_kpi(kpi_id):
    """Edit a single KPI entry by ID, enforcing customer ownership."""
    customer_id = get_customer_id()
    kpi = KPI.query.get_or_404(kpi_id)
    upload = KPIUpload.query.get_or_404(kpi.upload_id)
    if upload.customer_id != customer_id:
        abort(403, 'Forbidden: KPI does not belong to your customer')
    data = request.json
    for field in ['health_score_component', 'weight', 'data', 'source_review', 'kpi_parameter', 'impact_level', 'measurement_frequency', 'account_id']:
        if field in data:
            setattr(kpi, field, data[field])
    kpi.last_edited_by = data.get('user_id')
    kpi.last_edited_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'updated'})

@kpi_api.route('/api/kpis/customer/all', methods=['GET'])
def get_all_kpis():
    """Get all KPIs for a customer"""
    customer_id = get_customer_id()
    
    # Get KPIs with account information for this customer
    kpis = db.session.query(KPI, Account).join(
        KPIUpload, KPI.upload_id == KPIUpload.upload_id
    ).join(
        Account, KPI.account_id == Account.account_id, isouter=True
    ).filter(KPIUpload.customer_id == customer_id).all()
    
    return jsonify([{
        'kpi_id': kpi.kpi_id,
        'account_id': kpi.account_id,
        'account_name': account.account_name if account else 'Unknown Account',
        'account_revenue': float(account.revenue) if account else 0,
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
        'last_edited_at': kpi.last_edited_at
    } for kpi, account in kpis])

@kpi_api.route('/api/test-kpis', methods=['GET'])
def test_kpis():
    """Test endpoint for KPIs"""
    return jsonify({'message': 'KPI API is working'})

@kpi_api.route('/api/kpis/<int:upload_id>', methods=['GET'])
def get_kpis(upload_id):
    """Get all KPIs for a given upload, enforcing customer ownership."""
    customer_id = get_customer_id()
    upload = KPIUpload.query.get_or_404(upload_id)
    if upload.customer_id != customer_id:
        abort(403, 'Forbidden: Upload does not belong to your customer')
    
    # Get KPIs with account information
    kpis = db.session.query(KPI, Account).join(
        Account, KPI.account_id == Account.account_id, isouter=True
    ).filter(KPI.upload_id == upload_id).all()
    
    return jsonify([{
        'kpi_id': kpi.kpi_id,
        'account_id': kpi.account_id,
        'account_name': account.account_name if account else 'Unknown Account',
        'account_revenue': float(account.revenue) if account else 0,
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
        'last_edited_at': kpi.last_edited_at
    } for kpi, account in kpis]) 