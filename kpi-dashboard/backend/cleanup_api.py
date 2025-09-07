from flask import Blueprint, request, jsonify
import os
import pandas as pd
from extensions import db
from models import KPIUpload, KPI, Account, CustomerConfig
from werkzeug.utils import secure_filename
import io
from datetime import datetime
import glob

cleanup_api = Blueprint('cleanup_api', __name__)

@cleanup_api.route('/api/cleanup/bulk-upload', methods=['POST'])
def bulk_cleanup_and_upload():
    """Clean up all existing data and re-upload from a directory of KPI files."""
    customer_id = request.headers.get('X-Customer-ID')
    user_id = request.headers.get('X-User-ID')
    directory_path = request.json.get('directory_path')
    
    if not customer_id:
        return jsonify({'error': 'Missing X-Customer-ID header'}), 400
    if not user_id:
        return jsonify({'error': 'Missing X-User-ID header'}), 400
    if not directory_path:
        return jsonify({'error': 'Missing directory_path'}), 400
    
    customer_id = int(customer_id)
    user_id = int(user_id)
    
    try:
        # Step 1: Clean up existing data
        cleanup_result = cleanup_existing_data(customer_id)
        
        # Step 2: Process all KPI files in directory
        upload_result = process_directory_files(directory_path, customer_id, user_id)
        
        return jsonify({
            'success': True,
            'cleanup_result': cleanup_result,
            'upload_result': upload_result,
            'message': 'Bulk cleanup and upload completed successfully'
        })
        
    except Exception as e:
        return jsonify({'error': f'Bulk cleanup failed: {str(e)}'}), 500

def cleanup_existing_data(customer_id):
    """Remove all existing KPI data for the customer."""
    try:
        # Get counts first
        kpi_count = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).count()
        upload_count = KPIUpload.query.filter_by(customer_id=customer_id).count()
        account_count = Account.query.filter_by(customer_id=customer_id).count()
        
        # Delete KPIs using a subquery approach
        kpi_upload_ids = db.session.query(KPIUpload.upload_id).filter(KPIUpload.customer_id == customer_id).subquery()
        KPI.query.filter(KPI.upload_id.in_(kpi_upload_ids)).delete(synchronize_session=False)
        
        # Delete all upload records for this customer
        KPIUpload.query.filter_by(customer_id=customer_id).delete()
        
        # Delete all accounts for this customer
        Account.query.filter_by(customer_id=customer_id).delete()
        
        db.session.commit()
        
        return {
            'deleted_kpis': kpi_count,
            'deleted_uploads': upload_count,
            'deleted_accounts': account_count
        }
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f'Failed to cleanup existing data: {str(e)}')

def process_directory_files(directory_path, customer_id, user_id):
    """Process all Excel files in the specified directory."""
    if not os.path.exists(directory_path):
        raise Exception(f'Directory not found: {directory_path}')
    
    # Find all Excel files
    excel_files = []
    for ext in ['*.xlsx', '*.xls']:
        excel_files.extend(glob.glob(os.path.join(directory_path, ext)))
    
    if not excel_files:
        raise Exception(f'No Excel files found in directory: {directory_path}')
    
    results = {
        'total_files': len(excel_files),
        'processed_files': 0,
        'successful_uploads': 0,
        'failed_uploads': 0,
        'total_kpis_created': 0,
        'accounts_created': 0,
        'errors': []
    }
    
    for file_path in excel_files:
        try:
            # Extract account name from filename (remove extension and common suffixes)
            filename = os.path.basename(file_path)
            account_name = filename.replace('.xlsx', '').replace('.xls', '').replace('_kpis', '').replace('_KPIs', '')
            
            # Process the file
            file_result = process_single_file(file_path, account_name, customer_id, user_id)
            
            results['processed_files'] += 1
            results['successful_uploads'] += 1
            results['total_kpis_created'] += file_result['kpi_count']
            results['accounts_created'] += 1
            
        except Exception as e:
            results['failed_uploads'] += 1
            results['errors'].append({
                'file': os.path.basename(file_path),
                'error': str(e)
            })
    
    return results

def process_single_file(file_path, account_name, customer_id, user_id):
    """Process a single Excel file and create account + KPIs."""
    try:
        # Create account
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
        
        # Read and parse Excel file
        with open(file_path, 'rb') as f:
            raw_excel = f.read()
        
        xls = pd.ExcelFile(io.BytesIO(raw_excel))
        kpi_data = []
        
        # Process KPI sheets (skip first and last)
        kpi_sheets = xls.sheet_names[1:-1] if len(xls.sheet_names) > 2 else xls.sheet_names
        
        for sheet_name in kpi_sheets:
            try:
                df = pd.read_excel(xls, sheet_name, header=None)
                
                # Find header row
                header_row_idx = df[df.iloc[:,0] == 'Health Score Component'].index
                if len(header_row_idx) == 0:
                    continue
                header_row_idx = header_row_idx[0]
                
                df.columns = df.iloc[header_row_idx]
                df = df.iloc[header_row_idx+1:]
                df = df.dropna(subset=['Health Score Component'])
                
                # Process each KPI row
                for idx, row in df.iterrows():
                    if pd.isna(row.get('Health Score Component')):
                        continue
                    
                    # Extract weight and impact level
                    weight_value = None
                    if 'weight' in str(row.get('Weight', '')).lower():
                        weight_value = 1.0
                    elif 'medium' in str(row.get('Weight', '')).lower():
                        weight_value = 0.5
                    elif 'low' in str(row.get('Weight', '')).lower():
                        weight_value = 0.25
                    
                    impact_value = None
                    if 'high' in str(row.get('Impact Level', '')).lower():
                        impact_value = 'High'
                    elif 'medium' in str(row.get('Impact Level', '')).lower():
                        impact_value = 'Medium'
                    elif 'low' in str(row.get('Impact Level', '')).lower():
                        impact_value = 'Low'
                    
                    kpi_row = {
                        'category': sheet_name,
                        'row_index': str(idx),
                        'health_score_component': row.get('Health Score Component'),
                        'weight': weight_value,
                        'data': row.get('Data'),
                        'source_review': row.get('Source Review'),
                        'kpi_parameter': row.get('KPI/Parameter'),
                        'impact_level': impact_value,
                        'measurement_frequency': row.get('Measurement Frequency'),
                    }
                    
                    # Convert NaN to None
                    for key, value in kpi_row.items():
                        if pd.isna(value):
                            kpi_row[key] = None
                    
                    kpi_data.append(kpi_row)
                    
            except Exception as e:
                print(f"Error processing sheet {sheet_name}: {str(e)}")
                continue
        
        if not kpi_data:
            raise Exception(f'No valid KPI data found in {os.path.basename(file_path)}')
        
        # Create upload record
        upload = KPIUpload(
            customer_id=customer_id,
            user_id=user_id,
            version=1,  # Fresh start
            original_filename=os.path.basename(file_path),
            raw_excel=raw_excel,
            account_id=account_id
        )
        db.session.add(upload)
        db.session.flush()
        
        # Create KPI records
        for kpi_row in kpi_data:
            kpi = KPI(
                upload_id=upload.upload_id,
                account_id=account_id,
                category=kpi_row['category'],
                row_index=kpi_row['row_index'],
                health_score_component=kpi_row['health_score_component'],
                weight=kpi_row['weight'],
                data=kpi_row['data'],
                source_review=kpi_row['source_review'],
                kpi_parameter=kpi_row['kpi_parameter'],
                impact_level=kpi_row['impact_level'],
                measurement_frequency=kpi_row['measurement_frequency']
            )
            db.session.add(kpi)
        
        db.session.commit()
        
        return {
            'account_name': account_name,
            'kpi_count': len(kpi_data),
            'upload_id': upload.upload_id
        }
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f'Failed to process {os.path.basename(file_path)}: {str(e)}')

@cleanup_api.route('/api/cleanup/status', methods=['GET'])
def get_cleanup_status():
    """Get current data status for the customer."""
    customer_id = request.headers.get('X-Customer-ID')
    if not customer_id:
        return jsonify({'error': 'Missing X-Customer-ID header'}), 400
    
    customer_id = int(customer_id)
    
    try:
        # Count current data
        account_count = Account.query.filter_by(customer_id=customer_id).count()
        upload_count = KPIUpload.query.filter_by(customer_id=customer_id).count()
        kpi_count = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).count()
        
        return jsonify({
            'customer_id': customer_id,
            'accounts': account_count,
            'uploads': upload_count,
            'kpis': kpi_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get status: {str(e)}'}), 500
