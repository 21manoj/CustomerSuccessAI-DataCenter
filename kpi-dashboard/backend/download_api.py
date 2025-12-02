from flask import Blueprint, send_file, abort, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from models import KPIUpload
from secure_file_handler import get_secure_file_handler
import io


download_api = Blueprint('download_api', __name__)

@download_api.route('/api/download/<int:upload_id>', methods=['GET'])
def download_excel(upload_id):
    """Download KPI upload file (legacy endpoint - uses database storage)"""
    customer_id = get_current_customer_id()
    upload = KPIUpload.query.get_or_404(upload_id)
    
    # Verify customer owns this upload
    if upload.customer_id != customer_id:
        abort(403, description='Access denied')
    
    if not upload.raw_excel:
        abort(404, description='No file found for this upload')
    return send_file(
        io.BytesIO(upload.raw_excel),
        download_name=upload.original_filename or f'kpi_upload_{upload_id}.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@download_api.route('/api/download/secure/<path:filename>', methods=['GET'])
def download_secure_file(filename):
    """Download file from secure file storage (new secure endpoint)"""
    try:
        customer_id = get_current_customer_id()
        handler = get_secure_file_handler(customer_id=customer_id)
        
        # Read file safely
        file_content, error = handler.read_file(filename)
        
        if error:
            return jsonify({'error': error}), 404
        
        # Get file info for proper MIME type
        file_info = handler.get_file_info(filename)
        if not file_info:
            return jsonify({'error': 'File not found'}), 404
        
        # Determine MIME type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        # Return file
        return send_file(
            io.BytesIO(file_content),
            download_name=file_info['name'],
            as_attachment=True,
            mimetype=mime_type
        )
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500 