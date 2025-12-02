#!/usr/bin/env python3
"""
Secure File API
Handles secure file uploads and downloads with transparent local/remote support
"""

from flask import Blueprint, request, jsonify, send_file, abort
from auth_middleware import get_current_customer_id, get_current_user_id
from secure_file_handler import get_secure_file_handler
import os
import io
from datetime import datetime
import mimetypes

secure_file_api = Blueprint('secure_file_api', __name__)

@secure_file_api.route('/api/secure-files/list', methods=['GET'])
def list_files():
    """
    List files in the customer's upload directory
    Supports directory browsing for file picker
    """
    try:
        customer_id = get_current_customer_id()
        subdirectory = request.args.get('subdirectory', None)
        
        handler = get_secure_file_handler(customer_id=customer_id)
        files = handler.list_files(subdirectory=subdirectory)
        
        # Format file info for frontend
        file_list = []
        for file_info in files:
            file_list.append({
                'name': file_info['name'],
                'size': file_info['size'],
                'size_formatted': _format_file_size(file_info['size']),
                'modified': datetime.fromtimestamp(file_info['modified']).isoformat(),
                'path': file_info['path']
            })
        
        return jsonify({
            'status': 'success',
            'files': file_list,
            'count': len(file_list)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@secure_file_api.route('/api/secure-files/directories', methods=['GET'])
def list_directories():
    """List subdirectories in the customer's upload directory"""
    try:
        customer_id = get_current_customer_id()
        handler = get_secure_file_handler(customer_id=customer_id)
        directories = handler.list_directories()
        
        return jsonify({
            'status': 'success',
            'directories': directories,
            'count': len(directories)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@secure_file_api.route('/api/secure-files/info/<path:filename>', methods=['GET'])
def get_file_info(filename):
    """Get file information (size, modified time, hash)"""
    try:
        customer_id = get_current_customer_id()
        handler = get_secure_file_handler(customer_id=customer_id)
        
        file_info = handler.get_file_info(filename)
        if not file_info:
            return jsonify({'error': 'File not found'}), 404
        
        return jsonify({
            'status': 'success',
            'file': {
                'name': file_info['name'],
                'size': file_info['size'],
                'size_formatted': _format_file_size(file_info['size']),
                'modified': datetime.fromtimestamp(file_info['modified']).isoformat(),
                'hash': file_info['hash']
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@secure_file_api.route('/api/secure-files/upload', methods=['POST'])
def upload_file():
    """
    Secure file upload endpoint
    Works transparently for both local and remote instances
    """
    try:
        customer_id = get_current_customer_id()
        user_id = get_current_user_id()
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get secure file handler
        handler = get_secure_file_handler(customer_id=customer_id)
        
        # Save file with all security checks
        file_path, error = handler.save_file(file, file.filename)
        
        if error:
            return jsonify({'error': error}), 400
        
        # Get file info
        filename = os.path.basename(file_path)
        file_info = handler.get_file_info(filename)
        
        return jsonify({
            'status': 'success',
            'message': 'File uploaded successfully',
            'file': {
                'name': file_info['name'] if file_info else filename,
                'path': file_info['path'] if file_info else file_path,
                'size': file_info['size'] if file_info else 0,
                'size_formatted': _format_file_size(file_info['size']) if file_info else '0 B'
            }
        })
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@secure_file_api.route('/api/secure-files/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """
    Secure file download endpoint
    Works transparently for both local and remote instances
    """
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

@secure_file_api.route('/api/secure-files/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a file"""
    try:
        customer_id = get_current_customer_id()
        handler = get_secure_file_handler(customer_id=customer_id)
        
        success, error = handler.delete_file(filename)
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'status': 'success',
            'message': 'File deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@secure_file_api.route('/api/secure-files/create-directory', methods=['POST'])
def create_directory():
    """Create a subdirectory for organizing files"""
    try:
        customer_id = get_current_customer_id()
        data = request.json
        
        if not data or 'name' not in data:
            return jsonify({'error': 'Directory name required'}), 400
        
        handler = get_secure_file_handler(customer_id=customer_id)
        success, error = handler.create_directory(data['name'])
        
        if not success:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'status': 'success',
            'message': 'Directory created successfully',
            'directory': data['name']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@secure_file_api.route('/api/secure-files/cleanup', methods=['POST'])
def cleanup_old_files():
    """Clean up old files (admin function)"""
    try:
        customer_id = get_current_customer_id()
        data = request.json or {}
        max_age_hours = data.get('max_age_hours', 24)
        
        handler = get_secure_file_handler(customer_id=customer_id)
        deleted_count = handler.cleanup_old_files(max_age_hours=max_age_hours)
        
        return jsonify({
            'status': 'success',
            'message': f'Cleaned up {deleted_count} old files',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024
        i += 1
    
    return f"{size:.2f} {size_names[i]}"

