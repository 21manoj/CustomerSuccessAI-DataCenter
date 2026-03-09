"""
Updated Upload API - Config-Aware Runtime Uploads
==================================================

UPDATES:
- Runtime CSV uploads now respect CustomerConfig
- Filters out disabled KPIs automatically
- Supports incremental and replace modes
- Provides detailed feedback on filtering

Add to app_v3_minimal.py:
    from upload_api_v2_config_aware import upload_api
    app.register_blueprint(upload_api)
"""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import tempfile
import pandas as pd
from datetime import datetime

from flask import current_app
from extensions import db
from models import DC2SKPI, Account, Customer, CustomerConfig
from utils.config_loader import ConfigLoader
from utils.score_calculator import ScoreCalculator
# Note: Authentication handled by auth_middleware automatically for /api/* routes
from sqlalchemy import func

upload_api = Blueprint('upload_v2', __name__)

# ============================================================================
# Runtime Upload Endpoint - Config-Aware
# ============================================================================

@upload_api.route('/upload', methods=['POST'])
def upload_kpi_csv():
    """
    Upload KPI CSV at runtime
    
    V2 UPDATE: Config-aware filtering
    - Only loads enabled KPIs from CustomerConfig
    - Automatically filters out disabled KPIs
    - Provides detailed feedback
    
    Supports two modes:
    1. incremental (default): Add new + update existing
    2. replace: Delete existing + load new
    
    Request (multipart/form-data):
        - file: CSV file
        - customer_id: int
        - mode: 'incremental' or 'replace' (default: incremental)
        - date_range: optional for replace mode (e.g., '2024-12-01,2024-12-31')
    
    Response:
        {
            "success": true,
            "mode": "incremental",
            "records_in_csv": 5400,
            "records_filtered": 3600,
            "records_processed": 1800,
            "enabled_kpis": 15,
            "csv_kpis": 35,
            "disabled_kpis": [20 KPIs...],
            "details": {
                "added": 1500,
                "updated": 300,
                "deleted": 0
            }
        }
    """
    
    # Get parameters
    customer_id = request.form.get('customer_id', type=int)
    mode = request.form.get('mode', 'incremental')
    date_range = request.form.get('date_range')
    
    if not customer_id:
        return jsonify({"error": "customer_id required"}), 400
    
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    try:
        # Save uploaded file temporarily
        temp_dir = Path(tempfile.mkdtemp())
        filename = secure_filename(file.filename)
        temp_file = temp_dir / filename
        file.save(temp_file)
        
        # Read CSV
        df = pd.read_csv(temp_file)
        
        # Validate columns
        required_cols = ['account_id', 'kpi_code', 'measured_at', 'value', 'target', 'pillar']
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            return jsonify({"error": f"Missing columns: {missing}"}), 400
        
        # V2 UPDATE: Filter based on CustomerConfig
        loader = ConfigLoader(customer_id)
        enabled_kpis = set(loader.get_enabled_kpis())
        
        # Get CSV stats
        csv_kpis = set(df['kpi_code'].unique())
        disabled_kpis = csv_kpis - enabled_kpis
        
        records_before = len(df)
        
        # Filter to only enabled KPIs
        df_filtered = df[df['kpi_code'].isin(enabled_kpis)]
        
        records_after = len(df_filtered)
        records_filtered = records_before - records_after
        
        print(f"Config-aware filtering:")
        print(f"  Total in CSV: {records_before}")
        print(f"  Enabled KPIs: {len(enabled_kpis)}")
        print(f"  Filtered out: {records_filtered}")
        print(f"  To process: {records_after}")
        
        if disabled_kpis:
            print(f"  Disabled KPIs in CSV: {disabled_kpis}")
        
        # Process based on mode
        if mode == 'replace':
            result = _process_replace_mode(customer_id, df_filtered, date_range)
        else:  # incremental
            result = _process_incremental_mode(customer_id, df_filtered)
        
        # Clean up
        temp_file.unlink()
        temp_dir.rmdir()
        
        return jsonify({
            "success": True,
            "mode": mode,
            "records_in_csv": records_before,
            "records_filtered": records_filtered,
            "records_processed": records_after,
            "enabled_kpis": len(enabled_kpis),
            "csv_kpis": len(csv_kpis),
            "disabled_kpis": list(disabled_kpis),
            "filter_percentage": f"{(records_filtered/records_before*100):.1f}%" if records_before > 0 else "0%",
            "details": result
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

# ============================================================================
# Processing Functions
# ============================================================================

def _process_incremental_mode(customer_id: int, df: pd.DataFrame) -> dict:
    """
    Incremental mode: Add new + Update existing
    
    Logic:
    - Check if record exists (account_id + kpi_code + measured_at)
    - If exists: UPDATE value and target
    - If not exists: INSERT new record
    - Never DELETE anything
    """
    
    added = 0
    updated = 0
    
    for _, row in df.iterrows():
        # Check if record exists
        existing = DC2SKPI.query.filter_by(
            account_id=row['account_id'],
            kpi_code=row['kpi_code'],
            measured_at=pd.to_datetime(row['measured_at'])
        ).first()
        
        if existing:
            # UPDATE
            existing.value = float(row['value'])
            existing.target = float(row['target'])
            existing.pillar = row['pillar']
            updated += 1
        else:
            # INSERT
            new_record = DC2SKPI(
                account_id=row['account_id'],
                kpi_code=row['kpi_code'],
                measured_at=pd.to_datetime(row['measured_at']),
                value=float(row['value']),
                target=float(row['target']),
                pillar=row['pillar']
            )
            db.session.add(new_record)
            added += 1
    
    db.session.commit()
    
    return {
        "added": added,
        "updated": updated,
        "deleted": 0,
        "message": f"Incremental update: {added} added, {updated} updated"
    }

def _process_replace_mode(customer_id: int, df: pd.DataFrame, date_range: str = None) -> dict:
    """
    Replace mode: Delete existing + Load new
    
    Logic:
    - DELETE existing records (optionally filtered by date_range)
    - INSERT all new records from CSV
    
    If date_range provided: Only replace that date range
    If no date_range: Replace ALL data for this customer
    """
    
    # Get account IDs for this customer
    account_ids = [a.account_id for a in Account.query.filter_by(customer_id=customer_id).all()]
    
    # Build delete query
    delete_query = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids))
    
    # Apply date range filter if provided
    if date_range:
        try:
            start_date, end_date = date_range.split(',')
            delete_query = delete_query.filter(
                DC2SKPI.measured_at >= pd.to_datetime(start_date),
                DC2SKPI.measured_at <= pd.to_datetime(end_date)
            )
            print(f"  Replacing date range: {start_date} to {end_date}")
        except:
            raise ValueError("date_range must be 'YYYY-MM-DD,YYYY-MM-DD'")
    else:
        print(f"  Replacing ALL data for customer {customer_id}")
    
    # DELETE existing
    deleted = delete_query.delete(synchronize_session=False)
    
    # INSERT new
    added = 0
    for _, row in df.iterrows():
        new_record = DC2SKPI(
            account_id=row['account_id'],
            kpi_code=row['kpi_code'],
            measured_at=pd.to_datetime(row['measured_at']),
            value=float(row['value']),
            target=float(row['target']),
            pillar=row['pillar']
        )
        db.session.add(new_record)
        added += 1
    
    db.session.commit()
    
    return {
        "added": added,
        "updated": 0,
        "deleted": deleted,
        "message": f"Complete refresh: {deleted} deleted, {added} added",
        "date_range": date_range if date_range else "all"
    }

# ============================================================================
# Score Recalculation
# ============================================================================

@upload_api.route('/upload/recalculate-scores', methods=['POST'])
def recalculate_scores():
    """
    Recalculate health scores after CSV upload
    
    Should be called after uploading new KPI data
    
    Request:
        {
            "customer_id": 123,
            "month": "2024-12-01"  // Optional, defaults to latest month with data
        }
    
    Response:
        {
            "success": true,
            "customer_id": 123,
            "measurement_month": "2024-12-01",
            "accounts_scored": 3,
            "results": [
                {
                    "account_id": 10021,
                    "account_name": "Account-1",
                    "health_score": 88.3,
                    "health_status": "excellent"
                },
                ...
            ]
        }
    """
    
    data = request.get_json()
    customer_id = data.get('customer_id')
    month = data.get('month')
    
    if not customer_id:
        return jsonify({"error": "customer_id required"}), 400
    
    try:
        calculator = ScoreCalculator(customer_id)
        
        # Determine measurement month
        if month:
            measurement_date = pd.to_datetime(month).date()
        else:
            # Get latest month with data
            latest = db.session.query(
                func.max(func.date_trunc('month', DC2SKPI.measured_at))
            ).filter(
                DC2SKPI.account_id.in_([
                    a.account_id for a in Account.query.filter_by(customer_id=customer_id).all()
                ])
            ).scalar()
            
            if not latest:
                return jsonify({"error": "No KPI data found"}), 404
            
            measurement_date = latest.date()
        
        # Calculate scores for all accounts
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        results = []
        
        for account in accounts:
            score_result = calculator.calculate_scores_for_account(
                account.account_id,
                measurement_date
            )
            
            if score_result and 'health_score' in score_result:
                results.append({
                    "account_id": account.account_id,
                    "account_name": account.account_name,
                    "health_score": score_result['health_score']['health_score'],
                    "health_status": score_result['health_score']['health_status']
                })
        
        return jsonify({
            "success": True,
            "customer_id": customer_id,
            "measurement_month": str(measurement_date),
            "accounts_scored": len(results),
            "results": results
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

# ============================================================================
# Validation Endpoint
# ============================================================================

@upload_api.route('/upload/validate', methods=['POST'])
def validate_upload():
    """
    Validate CSV before uploading
    
    Shows what will happen without actually uploading
    
    Request (multipart/form-data):
        - file: CSV file
        - customer_id: int
    
    Response:
        {
            "valid": true,
            "enabled_kpis": 15,
            "csv_kpis": 35,
            "disabled_kpis": [20 KPIs...],
            "records_in_csv": 5400,
            "records_will_load": 1800,
            "records_will_filter": 3600,
            "warnings": [...]
        }
    """
    
    customer_id = request.form.get('customer_id', type=int)
    
    if not customer_id:
        return jsonify({"error": "customer_id required"}), 400
    
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    
    try:
        # Save temporarily
        temp_dir = Path(tempfile.mkdtemp())
        filename = secure_filename(file.filename)
        temp_file = temp_dir / filename
        file.save(temp_file)
        
        # Read CSV
        df = pd.read_csv(temp_file)
        
        # Validate columns
        required_cols = ['account_id', 'kpi_code', 'measured_at', 'value', 'target', 'pillar']
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            return jsonify({
                "valid": False,
                "error": f"Missing columns: {missing}"
            }), 400
        
        # Check against config
        loader = ConfigLoader(customer_id)
        enabled_kpis = set(loader.get_enabled_kpis())
        csv_kpis = set(df['kpi_code'].unique())
        disabled_kpis = csv_kpis - enabled_kpis
        
        records_total = len(df)
        records_enabled = len(df[df['kpi_code'].isin(enabled_kpis)])
        records_filtered = records_total - records_enabled
        
        warnings = []
        if disabled_kpis:
            warnings.append(f"{len(disabled_kpis)} disabled KPIs will be filtered out")
            warnings.append(f"Disabled KPIs: {list(disabled_kpis)}")
        
        # Clean up
        temp_file.unlink()
        temp_dir.rmdir()
        
        return jsonify({
            "valid": True,
            "enabled_kpis": len(enabled_kpis),
            "csv_kpis": len(csv_kpis),
            "disabled_kpis": list(disabled_kpis),
            "records_in_csv": records_total,
            "records_will_load": records_enabled,
            "records_will_filter": records_filtered,
            "filter_percentage": f"{(records_filtered/records_total*100):.1f}%" if records_total > 0 else "0%",
            "warnings": warnings
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

# ============================================================================
# Health Check
# ============================================================================

@upload_api.route('/upload/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": "2.0",
        "features": [
            "config-aware-filtering",
            "incremental-mode",
            "replace-mode",
            "date-range-replace",
            "validation",
            "score-recalculation"
        ]
    })

# ============================================================================
# Onboarding Upload Endpoint (Public - for UI compatibility)
# ============================================================================

# Note: /api/onboarding/upload is handled by onboarding_api_v2
# This route removed to avoid duplication
    """
    Public upload endpoint for onboarding UI
    Saves files to customer directory (scripts handle DB loading)
    
    This endpoint is public (no auth required) to match UI expectations.
    Files are saved to customer{N}-dc2_s/data/ directory.
    
    Expected form data:
    - file: CSV or Excel file (.csv, .xlsx, .xls)
    - file_type: One of 'accounts', 'kpis', 'signals', 'products', 'profiles', 'customers'
    - upload_mode: One of 'full_refresh', 'incremental', 'upsert', 'merge'
    
    Returns:
    - status: success/error
    - file_path: Path where file was saved
    - message: Status message
    """
    try:
        # Get customer_id from form or headers (for public endpoint)
        customer_id = request.form.get('customer_id', type=int)
        if not customer_id:
            # Try to get from headers
            customer_id = request.headers.get('X-Customer-ID', type=int)
        
        if not customer_id:
            return jsonify({
                'status': 'error',
                'message': 'customer_id required (in form data or X-Customer-ID header)'
            }), 400
        
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
        
        file = request.files['file']
        file_type = request.form.get('file_type', 'accounts')
        upload_mode = request.form.get('upload_mode', 'incremental')
        
        # Validate upload_mode
        valid_modes = ['full_refresh', 'incremental', 'upsert', 'merge']
        if upload_mode not in valid_modes:
            return jsonify({
                'status': 'error',
                'message': f'Invalid upload_mode: {upload_mode}. Valid modes: {", ".join(valid_modes)}'
            }), 400
        
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'Empty filename'}), 400
        
        # Get customer directory
        backend_dir = Path(__file__).parent
        customer_dir = backend_dir / f"verticals/customer{customer_id}-dc2_s"
        data_dir = customer_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        filename = secure_filename(file.filename)
        file_path = data_dir / filename
        file.save(str(file_path))
        
        # Save upload metadata (for loader scripts)
        metadata = {
            'customer_id': customer_id,
            'file_type': file_type,
            'upload_mode': upload_mode,
            'uploaded_at': datetime.now().isoformat(),
            'filename': filename
        }
        metadata_file = data_dir / f".upload_metadata_{file_type}.json"
        import json
        metadata_file.write_text(json.dumps(metadata, indent=2))
        
        # Activity log: high-value upload event (low volume)
        try:
            from activity_logging import activity_logger
            from auth_middleware import get_current_user_id
            user_id = get_current_user_id()
            activity_logger.log_upload(
                customer_id=customer_id,
                user_id=user_id,
                upload_type=file_type,
                filename=filename,
                upload_id=None,
                status="success",
            )
        except Exception:
            pass
        
        return jsonify({
            'status': 'success',
            'message': f'File uploaded successfully',
            'file_path': str(file_path),
            'file_type': file_type,
            'upload_mode': upload_mode,
            'customer_id': customer_id
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Upload failed: {str(e)}'
        }), 500
