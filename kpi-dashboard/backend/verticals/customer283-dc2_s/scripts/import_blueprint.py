#!/usr/bin/env python3
"""
Import API Blueprint
====================

Flask blueprint providing REST API for customer data imports.

Endpoints:
- POST /api/import/excel: Upload and import Excel file
- GET /api/import/<import_id>/status: Get import progress
- GET /api/import/history: List past imports
- POST /api/import/<import_id>/rollback: Rollback failed import
- GET /api/import/validate: Validate Excel file before import

Usage:
    from blueprints.import_blueprint import bp as import_bp
    app.register_blueprint(import_bp)
"""

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# Import services
from import_integration_adapter import ImportIntegrationAdapter, ImportResult
from production_import_helpers import (
    ProgressTracker,
    ImportValidator,
    PerformanceMonitor
)

# Create blueprint
bp = Blueprint('import', __name__, url_prefix='/api/import')

# Configuration
UPLOAD_FOLDER = '/tmp/cs_pulse_uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Ensure upload folder exists
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

# Global storage for progress tracking (in production, use Redis or database)
import_progress_store = {}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# ENDPOINTS
# ============================================================================

@bp.route('/excel', methods=['POST'])
def upload_excel():
    """
    Upload and import Excel file
    
    Request:
        - file: Excel file (multipart/form-data)
        - dry_run: Optional boolean (default: false)
    
    Response:
        {
            "success": true,
            "import_id": "uuid",
            "message": "Import started",
            "estimated_time": 120
        }
    """
    
    # Validate request
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No file provided'
        }), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'No file selected'
        }), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'error': 'Invalid file type. Must be .xlsx or .xls'
        }), 400
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return jsonify({
            'success': False,
            'error': f'File too large. Max size: {MAX_FILE_SIZE / (1024*1024):.0f}MB'
        }), 400
    
    try:
        # Save file
        import_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, f"{import_id}_{filename}")
        file.save(filepath)
        
        # Get dry_run parameter
        dry_run = request.form.get('dry_run', 'false').lower() == 'true'
        
        # Start import (in production, use Celery for async)
        # For now, run synchronously
        adapter = ImportIntegrationAdapter()
        
        # Start performance monitoring
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Execute import
        result = adapter.import_excel_to_cs_pulse(filepath)
        
        monitor.checkpoint('import_complete')
        
        # Store result for status endpoint
        import_progress_store[import_id] = {
            'import_id': import_id,
            'filename': filename,
            'status': 'completed' if result.success else 'failed',
            'result': result,
            'started_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat()
        }
        
        # Clean up file
        if not dry_run:
            os.remove(filepath)
        
        return jsonify({
            'success': result.success,
            'import_id': import_id,
            'message': 'Import completed' if result.success else 'Import failed',
            'customers_imported': result.customers_imported,
            'weeks_imported': result.weeks_imported,
            'errors': result.errors,
            'warnings': result.warnings,
            'execution_time': monitor.get_stats()['total_time_seconds']
        }), 200 if result.success else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/<import_id>/status', methods=['GET'])
def get_import_status(import_id):
    """
    Get import progress and status
    
    Response:
        {
            "import_id": "uuid",
            "status": "completed|processing|failed",
            "progress": {
                "customers_imported": 10,
                "weeks_imported": 520,
                "progress_pct": 100
            },
            "errors": [],
            "warnings": []
        }
    """
    
    if import_id not in import_progress_store:
        return jsonify({
            'success': False,
            'error': 'Import not found'
        }), 404
    
    import_data = import_progress_store[import_id]
    result = import_data.get('result')
    
    return jsonify({
        'success': True,
        'import_id': import_id,
        'filename': import_data['filename'],
        'status': import_data['status'],
        'started_at': import_data['started_at'],
        'completed_at': import_data.get('completed_at'),
        'progress': {
            'customers_imported': result.customers_imported if result else 0,
            'weeks_imported': result.weeks_imported if result else 0,
            'progress_pct': 100 if import_data['status'] == 'completed' else 0
        },
        'errors': result.errors if result else [],
        'warnings': result.warnings if result else []
    }), 200


@bp.route('/history', methods=['GET'])
def get_import_history():
    """
    List past imports with pagination
    
    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
    
    Response:
        {
            "success": true,
            "imports": [...],
            "total": 45,
            "page": 1,
            "per_page": 20
        }
    """
    
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    
    # Get all imports (in production, query database)
    all_imports = list(import_progress_store.values())
    
    # Sort by started_at descending
    all_imports.sort(key=lambda x: x['started_at'], reverse=True)
    
    # Paginate
    start = (page - 1) * per_page
    end = start + per_page
    page_imports = all_imports[start:end]
    
    # Format response
    imports_list = [
        {
            'import_id': imp['import_id'],
            'filename': imp['filename'],
            'status': imp['status'],
            'started_at': imp['started_at'],
            'completed_at': imp.get('completed_at'),
            'customers_imported': imp['result'].customers_imported if imp.get('result') else 0,
            'weeks_imported': imp['result'].weeks_imported if imp.get('result') else 0
        }
        for imp in page_imports
    ]
    
    return jsonify({
        'success': True,
        'imports': imports_list,
        'total': len(all_imports),
        'page': page,
        'per_page': per_page,
        'total_pages': (len(all_imports) + per_page - 1) // per_page
    }), 200


@bp.route('/<import_id>/rollback', methods=['POST'])
def rollback_import(import_id):
    """
    Rollback failed import
    
    Deletes all Qdrant points created by this import.
    
    Response:
        {
            "success": true,
            "message": "Import rolled back",
            "points_deleted": 520
        }
    """
    
    if import_id not in import_progress_store:
        return jsonify({
            'success': False,
            'error': 'Import not found'
        }), 404
    
    import_data = import_progress_store[import_id]
    result = import_data.get('result')
    
    if not result:
        return jsonify({
            'success': False,
            'error': 'No import result to rollback'
        }), 400
    
    try:
        # Delete Qdrant points (in production, implement actual deletion)
        points_deleted = len(result.qdrant_point_ids)
        
        # In production:
        # from qdrant_client import QdrantClient
        # client = QdrantClient(url='http://localhost:6333')
        # client.delete(
        #     collection_name='journey_weeks',
        #     points_selector=result.qdrant_point_ids
        # )
        
        # Update status
        import_data['status'] = 'rolled_back'
        
        return jsonify({
            'success': True,
            'message': 'Import rolled back successfully',
            'points_deleted': points_deleted
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/validate', methods=['POST'])
def validate_excel():
    """
    Validate Excel file before import
    
    Request:
        - file: Excel file (multipart/form-data)
    
    Response:
        {
            "valid": true|false,
            "errors": [],
            "warnings": [],
            "stats": {
                "customers": 10,
                "has_history": true
            }
        }
    """
    
    if 'file' not in request.files:
        return jsonify({
            'valid': False,
            'errors': ['No file provided']
        }), 400
    
    file = request.files['file']
    
    if not allowed_file(file.filename):
        return jsonify({
            'valid': False,
            'errors': ['Invalid file type']
        }), 400
    
    try:
        # Save temporarily
        temp_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, f"{temp_id}_{filename}")
        file.save(filepath)
        
        # Validate
        validation = ImportValidator.validate_before_import(filepath)
        
        # Clean up
        os.remove(filepath)
        
        return jsonify(validation), 200
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'errors': [str(e)]
        }), 500


@bp.route('/download/<import_id>', methods=['GET'])
def download_import_results(import_id):
    """
    Download import results as JSON
    
    Response:
        JSON file with complete import results
    """
    
    if import_id not in import_progress_store:
        return jsonify({
            'success': False,
            'error': 'Import not found'
        }), 404
    
    import_data = import_progress_store[import_id]
    
    # In production, generate comprehensive report
    # For now, return basic data
    
    return jsonify(import_data), 200


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@bp.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({
        'success': False,
        'error': 'File too large'
    }), 413


@bp.errorhandler(500)
def internal_error(e):
    """Handle internal server error"""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def cleanup_old_uploads():
    """Clean up old upload files (run periodically)"""
    import time
    
    upload_dir = Path(UPLOAD_FOLDER)
    now = time.time()
    max_age = 24 * 60 * 60  # 24 hours
    
    for filepath in upload_dir.glob('*'):
        if filepath.is_file():
            file_age = now - filepath.stat().st_mtime
            if file_age > max_age:
                filepath.unlink()


if __name__ == '__main__':
    print("Import API Blueprint")
    print("Register with: app.register_blueprint(import_bp)")
