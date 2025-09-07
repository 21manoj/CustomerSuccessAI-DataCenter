from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
from extensions import db
from models import KPIUpload, KPI, CustomerConfig, Account
import io
from datetime import datetime

upload_api = Blueprint('upload_api', __name__)

@upload_api.route('/api/upload', methods=['POST'])
def upload_excel():
    """Upload and parse a KPI Excel file, create a new versioned upload, and store KPIs."""
    file = request.files.get('file')
    customer_id = request.headers.get('X-Customer-ID')
    user_id = request.headers.get('X-User-ID')
    account_name = request.form.get('account_name')  # Account name from frontend
    account_id = None
    
    if not file:
        return jsonify({'error': 'Missing file'}), 400
    if not customer_id:
        return jsonify({'error': 'Missing X-Customer-ID header'}), 400
    if not user_id:
        return jsonify({'error': 'Missing X-User-ID header'}), 400
    
    customer_id = int(customer_id)
    user_id = int(user_id)
    
    # Get customer configuration
    config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
    if not config:
        config = CustomerConfig(customer_id=customer_id, kpi_upload_mode='account_rollup')  # Changed to account_rollup
        db.session.add(config)
        db.session.commit()
    
    # Handle account creation/validation
    if account_name:
        # Check for duplicate account name
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
            revenue=0,  # Default revenue
            industry='Unknown',
            region='Unknown',
            account_status='active'
        )
        db.session.add(account)
        db.session.flush()  # Get the account_id
        account_id = account.account_id
    else:
        return jsonify({'error': 'Account name is required'}), 400

    filename = secure_filename(file.filename)
    raw_excel = file.read()
    file.seek(0)

    # Parse Excel
    xls = pd.ExcelFile(io.BytesIO(raw_excel))
    kpi_data = []
    
    # Skip first sheet, process middle sheets (KPI tabs), skip last sheet (rollup)
    kpi_sheets = xls.sheet_names[1:-1]
    print(f"Processing sheets: {kpi_sheets}")
    
    for sheet_name in kpi_sheets:
        try:
            print(f"\n--- Processing sheet: {sheet_name} ---")
            df = pd.read_excel(xls, sheet_name, header=None)
            print(f"Sheet shape: {df.shape}")
            print(f"First few rows:")
            print(df.head())
            
            # Find header row
            header_row_idx = df[df.iloc[:,0] == 'Health Score Component'].index
            if len(header_row_idx) == 0:
                print(f"No header row found in {sheet_name}")
                continue
            header_row_idx = header_row_idx[0]
            print(f"Header row found at index: {header_row_idx}")
            
            # Get the actual header row and print column names
            header_row = df.iloc[header_row_idx]
            print(f"Header row values: {list(header_row)}")
            
            df.columns = df.iloc[header_row_idx]
            df = df.iloc[header_row_idx+1:]
            df = df.dropna(subset=['Health Score Component'])
            
            print(f"Available columns: {list(df.columns)}")
            print(f"Data rows after processing:")
            print(df.head())
            
            for idx, row in df.iterrows():
                # Try different possible column names for each field
                weight_value = row.get('Weight (%)')
                if weight_value is None:
                    weight_value = row.get('Weight') or row.get('weight') or row.get('WEIGHT') or row.get('WEIGHT (%)')
                
                impact_value = (
                    row.get('Impact level') or 
                    row.get('Impact Level') or 
                    row.get('Impact') or
                    row.get('impact level') or
                    row.get('IMPACT LEVEL') or
                    None
                )
                
                # Convert NaN values to None for JSON compatibility
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
                
                # Convert any NaN values to None, but preserve weight values
                for key, value in kpi_row.items():
                    if pd.isna(value):
                        kpi_row[key] = None
                    elif key == 'weight' and value is not None:
                        # Convert weight to string to preserve the value
                        kpi_row[key] = str(value)
                
                print(f"KPI row: {kpi_row}")
                kpi_data.append(kpi_row)
                
        except Exception as e:
            print(f"Error processing sheet {sheet_name}: {str(e)}")
            continue

    print(f"Total KPIs parsed: {len(kpi_data)}")
    
    if not kpi_data:
        return jsonify({'error': 'No valid KPI data found in Excel file'}), 400

    # Create new upload record
    latest_upload = KPIUpload.query.filter_by(customer_id=customer_id).order_by(KPIUpload.version.desc()).first()
    new_version = (latest_upload.version + 1) if latest_upload else 1
    
    upload = KPIUpload(
        customer_id=customer_id,
        user_id=user_id,
        version=new_version,
        original_filename=filename,
        raw_excel=raw_excel,
        account_id=account_id  # Always use account_id now
    )
    
    db.session.add(upload)
    db.session.flush()  # Get the upload_id
    
    # Store KPIs
    for kpi_row in kpi_data:
        kpi = KPI(
            upload_id=upload.upload_id,
            account_id=account_id,  # Always use account_id now
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
    
    return jsonify({
        'upload_id': upload.upload_id,
        'version': upload.version,
        'filename': filename,
        'kpi_count': len(kpi_data),
        'upload_mode': 'account_rollup',
        'account_id': account_id,
        'account_name': account_name
    })

@upload_api.route('/api/uploads', methods=['GET'])
def get_upload_history():
    """Get all uploads for versioning history for the current customer."""
    customer_id = request.headers.get('X-Customer-ID')
    if not customer_id:
        return jsonify({'error': 'Missing X-Customer-ID header'}), 400
    uploads = KPIUpload.query.filter_by(customer_id=customer_id).order_by(KPIUpload.version.desc()).all()
    return jsonify([{
        'upload_id': upload.upload_id,
        'version': upload.version,
        'uploaded_at': upload.uploaded_at.isoformat(),
        'original_filename': upload.original_filename,
        'kpi_count': KPI.query.filter_by(upload_id=upload.upload_id).count()
    } for upload in uploads])

@upload_api.route('/api/upload/<int:upload_id>', methods=['GET'])
def get_upload_details(upload_id):
    """Get details of a specific upload version by upload_id."""
    upload = KPIUpload.query.get_or_404(upload_id)
    return jsonify({
        'upload_id': upload.upload_id,
        'version': upload.version,
        'uploaded_at': upload.uploaded_at.isoformat(),
        'original_filename': upload.original_filename,
        'kpi_count': KPI.query.filter_by(upload_id=upload.upload_id).count()
    }) 