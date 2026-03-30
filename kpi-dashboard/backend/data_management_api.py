from flask import Blueprint, request, jsonify, abort, current_app
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import KPI, KPIUpload, Account, CustomerConfig
from datetime import datetime
from pathlib import Path
import sys
import os
import subprocess
import time

data_management_api = Blueprint('data_management_api', __name__)

def execute_script(script_path: Path, customer_id: int, timeout: int = 600, additional_args: list = None) -> tuple:
    """
    Execute a Python script synchronously (reused from onboarding_api.py)
    
    Args:
        script_path: Path to script
        customer_id: Customer ID to pass as environment variable
        timeout: Execution timeout in seconds
        additional_args: Additional command-line arguments to pass to script
    
    Returns:
        (success: bool, stdout: str, stderr: str)
    """
    try:
        script_dir = script_path.parent
        script_name = script_path.name
        cmd = [sys.executable, script_name]
        
        # Add additional arguments if provided
        if additional_args:
            cmd.extend(additional_args)
        
        script_env = {**os.environ, 'CUSTOMER_ID': str(customer_id)}
        
        result = subprocess.run(
            cmd,
            cwd=str(script_dir),
            env=script_env,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return (result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (False, '', f'Script execution timed out after {timeout} seconds')
    except Exception as e:
        return (False, '', str(e))

@data_management_api.route('/api/data/trigger-wizard-a', methods=['POST'])
def trigger_wizard_a():
    """
    Trigger Wizard A (Arc Intelligence) to classify accounts and generate
    causal edges.  DB-native — no subprocess, no filesystem.
    """
    try:
        customer_id = get_current_customer_id()

        from models import Account
        account_count = Account.query.filter_by(customer_id=customer_id).count()
        if account_count == 0:
            return jsonify({
                'status': 'error',
                'message': 'No accounts found for this customer. Please upload account data first.'
            }), 400

        current_app.logger.info(
            f"Triggering Wizard A (Arc Intelligence) for customer {customer_id} — DB mode"
        )

        from wizards.wizard_a_journey_db import run_wizard_a

        script_start_time = time.time()
        result = run_wizard_a(customer_id)
        script_duration = time.time() - script_start_time

        current_app.logger.info(
            f"✅ Wizard A completed in {script_duration:.2f}s — "
            f"accounts={result.get('accounts_processed')}"
        )

        return jsonify({
            'status': 'success',
            'message': 'Arc intelligence completed successfully',
            'customer_id': customer_id,
            'accounts_processed': result.get('accounts_processed', 0),
            'arcs_classified': result.get('arcs_classified', 0),
            'edges_generated': result.get('edges_generated', 0),
            'duration_seconds': round(script_duration, 2),
            'source': 'database',
        })

    except ValueError as ve:
        current_app.logger.warning(f"Wizard A: {ve}")
        return jsonify({'status': 'error', 'message': str(ve)}), 404

    except Exception as e:
        current_app.logger.error(f"Error triggering Wizard A: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to trigger Wizard A: {str(e)}'
        }), 500

@data_management_api.route('/api/data/trigger-wizard-b', methods=['POST'])
def trigger_wizard_b():
    """
    Trigger Wizard B (Pattern Analysis) to analyze journey patterns.

    Reads journey data from the JourneyData DB table (populated by Wizard A /
    process-data step 4.5) and writes results to WizardRun + WizardLearning
    tables.  No subprocess, no filesystem.
    """
    try:
        customer_id = get_current_customer_id()

        current_app.logger.info(
            f"Triggering Wizard B (Pattern Analysis) for customer {customer_id} — DB mode"
        )

        import sys as _sys
        _wizard_b_dir = str(Path(__file__).parent / 'verticals' / '_template' / 'journey' / 'wizard_b')
        if _wizard_b_dir not in _sys.path:
            _sys.path.insert(0, _wizard_b_dir)
        from wizard_b_pattern_analyzer import run_wizard_b

        script_start_time = time.time()
        result = run_wizard_b(customer_id)
        script_duration = time.time() - script_start_time

        current_app.logger.info(
            f"✅ Wizard B completed in {script_duration:.2f}s — "
            f"run_id={result.get('run_id')}, patterns={result.get('total_patterns')}"
        )

        return jsonify({
            'status': 'success',
            'message': 'Pattern analysis completed successfully',
            'customer_id': customer_id,
            'run_id': result.get('run_id'),
            'version': result.get('version'),
            'total_patterns': result.get('total_patterns'),
            'total_transitions': result.get('total_transitions'),
            'total_warnings': result.get('total_warnings'),
            'total_journeys': result.get('total_journeys'),
            'duration_seconds': round(script_duration, 2),
            'source': 'database'
        })

    except ValueError as ve:
        # No journey data — return 404
        current_app.logger.warning(f"Wizard B: {ve}")
        return jsonify({
            'status': 'error',
            'message': str(ve)
        }), 404

    except Exception as e:
        current_app.logger.error(f"Error triggering Wizard B: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to trigger Wizard B: {str(e)}'
        }), 500

@data_management_api.route('/api/data/status', methods=['GET'])
def get_data_status():
    """Get current data status for a customer"""
    customer_id = get_current_customer_id()
    
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
    customer_id = get_current_customer_id()
    
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
    customer_id = get_current_customer_id()
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
    customer_id = get_current_customer_id()
    
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