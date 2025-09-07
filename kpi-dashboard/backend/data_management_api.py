from flask import Blueprint, request, jsonify, abort
from extensions import db
from models import KPI, KPIUpload, Account, CustomerConfig
from datetime import datetime

data_management_api = Blueprint('data_management_api', __name__)

def get_customer_id():
    """Extract and validate the X-Customer-ID header from the request."""
    cid = request.headers.get('X-Customer-ID')
    if not cid:
        abort(400, 'Missing X-Customer-ID header')
    try:
        return int(cid)
    except Exception:
        abort(400, 'Invalid X-Customer-ID header')

@data_management_api.route('/api/data/status', methods=['GET'])
def get_data_status():
    """Get current data status for a customer"""
    customer_id = get_customer_id()
    
    # Count KPIs
    kpi_count = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).count()
    
    # Count uploads
    upload_count = KPIUpload.query.filter_by(customer_id=customer_id).count()
    
    # Count accounts
    account_count = Account.query.filter_by(customer_id=customer_id).count()
    
    # Get upload details
    uploads = KPIUpload.query.filter_by(customer_id=customer_id).order_by(KPIUpload.uploaded_at.desc()).all()
    upload_details = [{
        'upload_id': upload.upload_id,
        'original_filename': upload.original_filename,
        'uploaded_at': upload.uploaded_at.isoformat(),
        'version': upload.version,
        'kpi_count': KPI.query.filter_by(upload_id=upload.upload_id).count()
    } for upload in uploads]
    
    return jsonify({
        'customer_id': customer_id,
        'total_kpis': kpi_count,
        'total_uploads': upload_count,
        'total_accounts': account_count,
        'uploads': upload_details
    })

@data_management_api.route('/api/data/clear', methods=['POST'])
def clear_all_data():
    """Clear all data for a customer"""
    customer_id = get_customer_id()
    
    try:
        # Get upload IDs for this customer
        upload_ids = [u.upload_id for u in KPIUpload.query.filter_by(customer_id=customer_id).all()]
        
        # Delete all KPIs for this customer's uploads
        kpis_deleted = 0
        if upload_ids:
            kpis_deleted = KPI.query.filter(KPI.upload_id.in_(upload_ids)).delete(synchronize_session=False)
        
        # Delete all uploads for this customer
        uploads_deleted = KPIUpload.query.filter_by(customer_id=customer_id).delete()
        
        # Delete all accounts for this customer
        accounts_deleted = Account.query.filter_by(customer_id=customer_id).delete()
        
        # Delete customer config
        config_deleted = CustomerConfig.query.filter_by(customer_id=customer_id).delete()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'All data cleared successfully',
            'deleted': {
                'kpis': kpis_deleted,
                'uploads': uploads_deleted,
                'accounts': accounts_deleted,
                'config': config_deleted
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to clear data: {str(e)}'
        }), 500

@data_management_api.route('/api/data/clear-uploads', methods=['POST'])
def clear_uploads():
    """Clear specific uploads"""
    customer_id = get_customer_id()
    data = request.json
    upload_ids = data.get('upload_ids', [])
    
    if not upload_ids:
        return jsonify({
            'status': 'error',
            'message': 'No upload IDs provided'
        }), 400
    
    try:
        # Verify uploads belong to customer
        uploads = KPIUpload.query.filter(
            KPIUpload.upload_id.in_(upload_ids),
            KPIUpload.customer_id == customer_id
        ).all()
        
        if len(uploads) != len(upload_ids):
            return jsonify({
                'status': 'error',
                'message': 'Some upload IDs not found or do not belong to customer'
            }), 400
        
        # Delete KPIs for these uploads
        kpis_deleted = db.session.query(KPI).filter(
            KPI.upload_id.in_(upload_ids)
        ).delete(synchronize_session=False)
        
        # Delete uploads
        uploads_deleted = KPIUpload.query.filter(
            KPIUpload.upload_id.in_(upload_ids)
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Cleared {len(upload_ids)} upload(s)',
            'deleted': {
                'kpis': kpis_deleted,
                'uploads': uploads_deleted
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to clear uploads: {str(e)}'
        }), 500

@data_management_api.route('/api/data/clear-accounts', methods=['POST'])
def clear_accounts():
    """Clear all accounts for a customer"""
    customer_id = get_customer_id()
    
    try:
        # Delete all accounts for this customer
        accounts_deleted = Account.query.filter_by(customer_id=customer_id).delete()
        
        # Reset account_id for all KPIs
        kpis_updated = db.session.query(KPI).join(KPIUpload).filter(
            KPIUpload.customer_id == customer_id
        ).update({'account_id': None}, synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'All accounts cleared successfully',
            'deleted': {
                'accounts': accounts_deleted,
                'kpis_reset': kpis_updated
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to clear accounts: {str(e)}'
        }), 500 