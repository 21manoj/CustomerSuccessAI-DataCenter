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
    Trigger Wizard A (Journey Generator) to regenerate journey timelines
    
    This endpoint runs the wizard_a_journey_generator.py script for the current customer
    to regenerate journey JSON files from the latest account and KPI data.
    """
    try:
        customer_id = get_current_customer_id()
        
        # Determine customer directory (check for dc2_s vertical)
        # Path(__file__) = backend/data_management_api.py
        # Path(__file__).parent = backend/
        # So backend_dir = backend/, and customer_dir = backend/verticals/customer{N}-dc2_s
        backend_dir = Path(__file__).parent
        customer_dir = backend_dir / "verticals" / f"customer{customer_id}-dc2_s"
        
        current_app.logger.info(f"Looking for customer directory: {customer_dir}")
        current_app.logger.info(f"Directory exists: {customer_dir.exists()}")
        
        if not customer_dir.exists():
            return jsonify({
                'status': 'error',
                'message': f'Customer directory not found: {customer_dir}'
            }), 404
        
        # Find Wizard A script
        journey_script = customer_dir / "journey" / "wizard_a" / "wizard_journey_generator.py"
        
        if not journey_script.exists():
            # Try alternative name
            journey_script = customer_dir / "journey" / "wizard_a" / "wizard_a_journey_generator.py"
        
        if not journey_script.exists():
            return jsonify({
                'status': 'error',
                'message': f'Journey generator script not found in {customer_dir / "journey" / "wizard_a"}'
            }), 404
        
        # Get account count for this customer to determine script arguments
        from models import Account
        account_count = Account.query.filter_by(customer_id=customer_id).count()
        
        if account_count == 0:
            return jsonify({
                'status': 'error',
                'message': 'No accounts found for this customer. Please upload account data first.'
            }), 400
        
        # Determine starting account ID (use lowest account_id for this customer)
        first_account = Account.query.filter_by(customer_id=customer_id).order_by(Account.account_id.asc()).first()
        start_id = first_account.account_id if first_account else 10001
        
        # Default pattern mix (can be made configurable later)
        pattern_mix = '{"crisis":0.15,"churn":0.15,"stable":0.5,"expansion":0.2}'
        
        # Generate output directory with timestamp
        # Script runs from journey/wizard_a/ directory, so output_dir should be relative to that
        script_dir = journey_script.parent  # journey/wizard_a/
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir_name = f"test_run_{timestamp}"
        output_dir = script_dir / output_dir_name  # journey/wizard_a/test_run_.../
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        current_app.logger.info(f"Triggering Wizard A (Journey Generator) for customer {customer_id}")
        current_app.logger.info(f"Script: {journey_script}")
        current_app.logger.info(f"Accounts: {account_count}, Start ID: {start_id}, Output: {output_dir_name}")
        
        # Build script arguments (output-dir is relative to script directory)
        script_args = [
            '--accounts', str(account_count),
            '--start-id', str(start_id),
            '--pattern-mix', pattern_mix,
            '--output-dir', output_dir_name  # Relative to script directory (journey/wizard_a/)
        ]
        
        # Execute Wizard A script
        script_start_time = time.time()
        success, stdout, stderr = execute_script(journey_script, customer_id, timeout=600, additional_args=script_args)
        script_duration = time.time() - script_start_time
        
        if not success:
            current_app.logger.error(f"Wizard A execution failed: {stderr}")
            return jsonify({
                'status': 'error',
                'message': 'Journey generation script failed',
                'error': stderr,
                'duration_seconds': round(script_duration, 2)
            }), 500
        
        current_app.logger.info(f"✅ Wizard A completed successfully in {script_duration:.2f} seconds")
        
        return jsonify({
            'status': 'success',
            'message': 'Journey timelines regenerated successfully',
            'customer_id': customer_id,
            'script_path': str(journey_script),
            'duration_seconds': round(script_duration, 2),
            'output': stdout[:500] if stdout else None  # First 500 chars of output
        })
        
    except Exception as e:
        current_app.logger.error(f"Error triggering Wizard A: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to trigger Wizard A: {str(e)}'
        }), 500

@data_management_api.route('/api/data/trigger-wizard-b', methods=['POST'])
def trigger_wizard_b():
    """
    Trigger Wizard B (Pattern Analysis) to analyze journey patterns
    
    This endpoint runs the wizard_b_pattern_analyzer.py script for the current customer
    using the latest Wizard A output (test_run directory).
    """
    try:
        customer_id = get_current_customer_id()
        
        # Determine customer directory
        backend_dir = Path(__file__).parent
        customer_dir = backend_dir / "verticals" / f"customer{customer_id}-dc2_s"
        
        if not customer_dir.exists():
            return jsonify({
                'status': 'error',
                'message': f'Customer directory not found: {customer_dir}'
            }), 404
        
        # Find Wizard B script
        wizard_b_script = customer_dir / "journey" / "wizard_b" / "wizard_b_pattern_analyzer.py"
        
        if not wizard_b_script.exists():
            return jsonify({
                'status': 'error',
                'message': f'Wizard B script not found: {wizard_b_script}'
            }), 404
        
        # Find latest Wizard A test_run directory
        wizard_a_dir = customer_dir / "journey" / "wizard_a"
        if not wizard_a_dir.exists():
            return jsonify({
                'status': 'error',
                'message': 'Wizard A output directory not found. Please run Wizard A first.'
            }), 404
        
        # Find the most recent test_run directory
        test_runs = [d for d in wizard_a_dir.iterdir() if d.is_dir() and d.name.startswith('test_run_')]
        
        if not test_runs:
            return jsonify({
                'status': 'error',
                'message': 'No Wizard A test_run directories found. Please run Wizard A first.'
            }), 404
        
        # Get the most recent test_run
        latest_test_run = max(test_runs, key=lambda x: x.stat().st_mtime)
        
        current_app.logger.info(f"Triggering Wizard B (Pattern Analysis) for customer {customer_id}")
        current_app.logger.info(f"Script: {wizard_b_script}")
        current_app.logger.info(f"Using Wizard A output: {latest_test_run.name}")
        
        # Wizard B script takes the test_run directory as argument
        # The script expects a relative path from the wizard_b directory, or absolute path
        # Since we're running from wizard_b directory, we need to pass relative path
        # Or we can pass absolute path - let's use absolute path for clarity
        script_args = [str(latest_test_run.resolve())]
        
        # Execute Wizard B script
        script_start_time = time.time()
        success, stdout, stderr = execute_script(wizard_b_script, customer_id, timeout=600, additional_args=script_args)
        script_duration = time.time() - script_start_time
        
        if not success:
            current_app.logger.error(f"Wizard B execution failed: {stderr}")
            return jsonify({
                'status': 'error',
                'message': 'Pattern analysis script failed',
                'error': stderr,
                'duration_seconds': round(script_duration, 2)
            }), 500
        
        current_app.logger.info(f"✅ Wizard B completed successfully in {script_duration:.2f} seconds")
        
        return jsonify({
            'status': 'success',
            'message': 'Pattern analysis completed successfully',
            'customer_id': customer_id,
            'script_path': str(wizard_b_script),
            'wizard_a_run': latest_test_run.name,
            'duration_seconds': round(script_duration, 2),
            'output': stdout[:500] if stdout else None
        })
        
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