from flask import Blueprint, send_file, abort
from auth_middleware import get_current_customer_id, get_current_user_id
from models import KPIUpload
import io


download_api = Blueprint('download_api', __name__)

@download_api.route('/api/download/<int:upload_id>', methods=['GET'])
def download_excel(upload_id):
    upload = KPIUpload.query.get_or_404(upload_id)
    if not upload.raw_excel:
        abort(404, description='No file found for this upload')
    return send_file(
        io.BytesIO(upload.raw_excel),
        download_name=upload.original_filename or f'kpi_upload_{upload_id}.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ) 