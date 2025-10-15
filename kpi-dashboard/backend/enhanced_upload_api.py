#!/usr/bin/env python3
"""
Enhanced Upload API with Format Detection and Event-Driven RAG Rebuilds
Supports multiple file formats and automatic knowledge base updates
"""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
from extensions import db
from models import KPIUpload, KPI, CustomerConfig, Account
import io
from datetime import datetime
import os
import sys

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from format_detection import FormatDetector, FormatAdapterFactory
from event_system import event_manager

enhanced_upload_api = Blueprint('enhanced_upload_api', __name__)

@enhanced_upload_api.route('/api/upload-enhanced', methods=['POST'])
def upload_excel_enhanced():
    """Enhanced upload with format detection and automatic RAG rebuild"""
    file = request.files.get('file')
    customer_id = request.headers.get('X-Customer-ID')
    user_id = request.headers.get('X-User-ID')
    account_name = request.form.get('account_name')
    
    if not file:
        return jsonify({'error': 'Missing file'}), 400
    if not customer_id:
        return jsonify({'error': 'Missing X-Customer-ID header'}), 400
    if not user_id:
        return jsonify({'error': 'Missing X-User-ID header'}), 400
    if not account_name:
        return jsonify({'error': 'Account name is required'}), 400
    
    customer_id = int(customer_id)
    user_id = int(user_id)
    
    try:
        # Save file temporarily for format detection
        filename = secure_filename(file.filename)
        temp_path = f"/tmp/{filename}"
        file.save(temp_path)
        
        # Detect file format
        format_detector = FormatDetector()
        format_info = format_detector.detect_format(temp_path)
        
        if format_info.format_type == 'unknown' or format_info.confidence < 0.5:
            os.remove(temp_path)
            return jsonify({
                'error': 'Unsupported file format',
                'detected_format': format_info.format_type,
                'confidence': format_info.confidence,
                'supported_formats': ['excel_standard', 'excel_simple', 'csv_standard', 'csv_basic']
            }), 400
        
        # Validate format
        is_valid, validation_errors = format_detector.validate_format(temp_path, format_info)
        if not is_valid:
            os.remove(temp_path)
            return jsonify({
                'error': 'File format validation failed',
                'errors': validation_errors,
                'detected_format': format_info.format_type
            }), 400
        
        # Get appropriate adapter
        adapter = FormatAdapterFactory.create_adapter(format_info.format_type)
        
        # Process file with adapter
        kpi_data = adapter.process(temp_path, customer_id, account_name)
        
        if not kpi_data:
            os.remove(temp_path)
            return jsonify({'error': 'No valid KPI data found in file'}), 400
        
        # Clean up temp file
        os.remove(temp_path)
        
        # Get or create customer configuration
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            config = CustomerConfig(customer_id=customer_id, kpi_upload_mode='account_rollup')
            db.session.add(config)
            db.session.commit()
        
        # Handle account creation/validation
        existing_account = Account.query.filter_by(
            account_name=account_name, 
            customer_id=customer_id
        ).first()
        
        if existing_account:
            return jsonify({'error': f'Account "{account_name}" already exists for this customer'}), 400
        
        # Create new account
        account = Account(
            customer_id=customer_id,
            account_name=account_name,
            revenue=0,
            industry='Unknown',
            region='Unknown',
            account_status='active'
        )
        db.session.add(account)
        db.session.flush()
        account_id = account.account_id
        
        # Create new upload record
        latest_upload = KPIUpload.query.filter_by(customer_id=customer_id).order_by(KPIUpload.version.desc()).first()
        new_version = (latest_upload.version + 1) if latest_upload else 1
        
        # Read file content for storage
        file.seek(0)
        raw_excel = file.read()
        
        upload = KPIUpload(
            customer_id=customer_id,
            user_id=user_id,
            version=new_version,
            original_filename=filename,
            raw_excel=raw_excel,
            account_id=account_id
        )
        
        db.session.add(upload)
        db.session.flush()
        upload_id = upload.upload_id
        
        # Store KPIs
        for kpi_row in kpi_data:
            kpi = KPI(
                upload_id=upload_id,
                account_id=account_id,
                category=kpi_row['category'],
                row_index=kpi_row.get('row_index', '0'),
                health_score_component=kpi_row['health_score_component'],
                weight=kpi_row['weight'],
                data=kpi_row['data'],
                source_review=kpi_row.get('source_review', ''),
                kpi_parameter=kpi_row['kpi_parameter'],
                impact_level=kpi_row.get('impact_level', 'Medium'),
                measurement_frequency=kpi_row.get('measurement_frequency', 'Monthly')
            )
            db.session.add(kpi)
        
        db.session.commit()
        
        # Publish event for automatic RAG rebuild
        event_manager.publish_kpi_upload(customer_id, upload_id, len(kpi_data))
        
        return jsonify({
            'upload_id': upload_id,
            'version': new_version,
            'filename': filename,
            'kpi_count': len(kpi_data),
            'format_detected': format_info.format_type,
            'format_confidence': format_info.confidence,
            'account_id': account_id,
            'account_name': account_name,
            'rag_rebuild_triggered': True,
            'status': 'success'
        })
        
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        
        return jsonify({
            'error': f'Upload failed: {str(e)}',
            'status': 'error'
        }), 500

@enhanced_upload_api.route('/api/upload-formats', methods=['GET'])
def get_supported_formats():
    """Get list of supported file formats"""
    return jsonify({
        'supported_formats': [
            {
                'format_type': 'excel_standard',
                'description': 'Standard KPI Dashboard format',
                'required_sheets': ['Account Info', 'KPI Data', 'Summary'],
                'required_columns': ['Health Score Component', 'KPI/Parameter', 'Data'],
                'example_file': 'template_standard.xlsx'
            },
            {
                'format_type': 'excel_simple',
                'description': 'Simple KPI list format',
                'required_sheets': ['KPIs'],
                'required_columns': ['KPI Name', 'Value', 'Category'],
                'example_file': 'template_simple.xlsx'
            },
            {
                'format_type': 'csv_standard',
                'description': 'Standard CSV format',
                'required_columns': ['kpi_parameter', 'data', 'category'],
                'example_file': 'template_standard.csv'
            },
            {
                'format_type': 'csv_basic',
                'description': 'Basic CSV format',
                'required_columns': ['kpi_name', 'value', 'category'],
                'example_file': 'template_basic.csv'
            }
        ],
        'format_detection': {
            'auto_detection': True,
            'validation': True,
            'confidence_threshold': 0.5
        }
    })

@enhanced_upload_api.route('/api/upload-template/<format_type>', methods=['GET'])
def get_upload_template(format_type):
    """Get upload template for specific format"""
    templates = {
        'excel_standard': {
            'description': 'Standard KPI Dashboard Excel format',
            'structure': {
                'sheets': ['Account Info', 'KPI Data', 'Summary'],
                'kpi_data_columns': [
                    'Health Score Component',
                    'KPI/Parameter', 
                    'Data',
                    'Weight (%)',
                    'Impact Level',
                    'Source Review',
                    'Measurement Frequency'
                ]
            },
            'sample_data': [
                {
                    'Health Score Component': 'Customer Sentiment',
                    'KPI/Parameter': 'Customer Satisfaction Score',
                    'Data': '85',
                    'Weight (%)': '25',
                    'Impact Level': 'High',
                    'Source Review': 'Quarterly survey',
                    'Measurement Frequency': 'Monthly'
                }
            ]
        },
        'excel_simple': {
            'description': 'Simple KPI list Excel format',
            'structure': {
                'sheets': ['KPIs'],
                'columns': ['KPI Name', 'Value', 'Category', 'Weight', 'Impact Level']
            },
            'sample_data': [
                {
                    'KPI Name': 'Customer Satisfaction Score',
                    'Value': '85',
                    'Category': 'Customer Sentiment',
                    'Weight': '25',
                    'Impact Level': 'High'
                }
            ]
        },
        'csv_standard': {
            'description': 'Standard CSV format',
            'structure': {
                'columns': ['kpi_parameter', 'data', 'category', 'weight', 'impact_level']
            },
            'sample_data': [
                {
                    'kpi_parameter': 'Customer Satisfaction Score',
                    'data': '85',
                    'category': 'Customer Sentiment',
                    'weight': '25',
                    'impact_level': 'High'
                }
            ]
        },
        'csv_basic': {
            'description': 'Basic CSV format',
            'structure': {
                'columns': ['kpi_name', 'value', 'category']
            },
            'sample_data': [
                {
                    'kpi_name': 'Customer Satisfaction Score',
                    'value': '85',
                    'category': 'Customer Sentiment'
                }
            ]
        }
    }
    
    if format_type not in templates:
        return jsonify({'error': 'Unsupported format type'}), 400
    
    return jsonify(templates[format_type])

@enhanced_upload_api.route('/api/upload-status/<int:upload_id>', methods=['GET'])
def get_upload_status(upload_id):
    """Get status of upload and RAG rebuild"""
    upload = KPIUpload.query.get_or_404(upload_id)
    
    # Check RAG knowledge base status
    from models import RAGKnowledgeBase
    kb_status = RAGKnowledgeBase.query.filter_by(customer_id=upload.customer_id).first()
    
    return jsonify({
        'upload_id': upload_id,
        'version': upload.version,
        'filename': upload.original_filename,
        'uploaded_at': upload.uploaded_at.isoformat(),
        'kpi_count': KPI.query.filter_by(upload_id=upload_id).count(),
        'rag_status': kb_status.status if kb_status else 'not_built',
        'rag_last_updated': kb_status.last_updated.isoformat() if kb_status and kb_status.last_updated else None
    })

@enhanced_upload_api.route('/api/upload-validate', methods=['POST'])
def validate_file_format():
    """Validate file format before upload"""
    file = request.files.get('file')
    
    if not file:
        return jsonify({'error': 'Missing file'}), 400
    
    try:
        # Save file temporarily for validation
        filename = secure_filename(file.filename)
        temp_path = f"/tmp/validate_{filename}"
        file.save(temp_path)
        
        # Detect format
        format_detector = FormatDetector()
        format_info = format_detector.detect_format(temp_path)
        
        # Validate format
        is_valid, validation_errors = format_detector.validate_format(temp_path, format_info)
        
        # Clean up temp file
        os.remove(temp_path)
        
        return jsonify({
            'format_detected': format_info.format_type,
            'confidence': format_info.confidence,
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'required_fields': format_info.required_fields,
            'optional_fields': format_info.optional_fields
        })
        
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        
        return jsonify({
            'error': f'Validation failed: {str(e)}',
            'is_valid': False
        }), 500

# Example usage
if __name__ == "__main__":
    print("Enhanced Upload API with Format Detection and Event-Driven RAG Rebuilds")
    print("Supported formats:")
    print("- excel_standard: Standard KPI Dashboard format")
    print("- excel_simple: Simple KPI list format")
    print("- csv_standard: Standard CSV format")
    print("- csv_basic: Basic CSV format")
    print("\nFeatures:")
    print("- Automatic format detection")
    print("- Format validation")
    print("- Event-driven RAG rebuilds")
    print("- Multiple format support")
