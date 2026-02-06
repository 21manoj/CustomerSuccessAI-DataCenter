"""
Multi-File-Type Upload API V3 - IMPROVED DUPLICATE HANDLING
============================================================

Handles duplicates properly across all upload modes:
- incremental: Skip duplicates with optional error/ignore
- upsert: Bulk upsert using database ON CONFLICT
- merge: Smart merge with conflict resolution
- full_refresh: Delete old data first

Add to app_v3_minimal.py:
    from upload_api_v3_improved_duplicates import upload_api_v3_improved
    app.register_blueprint(upload_api_v3_improved, url_prefix='/api')
"""

from flask import Blueprint, request, jsonify
from extensions import db
from models import DC2SKPI, Account, Customer, CustomerConfig
from utils.config_loader import ConfigLoader
from datetime import datetime
import pandas as pd
from io import StringIO
from sqlalchemy.dialects.postgresql import insert

# Import QualitativeSignal (now available in models.py)
from models import QualitativeSignal
HAS_QUALITATIVE_SIGNAL = True

# Profile is stored in Account.profile_metadata (JSON), not a separate table
# So we'll handle profiles differently

upload_api_v3_improved = Blueprint('upload_api_v3_improved', __name__)

# ============================================================================
# Duplicate Handling Strategies
# ============================================================================

DUPLICATE_STRATEGIES = {
    'skip': 'Skip duplicate records (ignore)',
    'error': 'Fail on first duplicate',
    'update': 'Update existing records (upsert)',
    'replace': 'Delete old, insert new'
}

# ============================================================================
# File Type Configurations with Unique Keys
# ============================================================================

FILE_TYPE_CONFIG = {
    'kpis': {
        'model': DC2SKPI,
        'table_name': 'dc2s_kpis',
        'required_columns': ['account_id', 'kpi_code', 'measured_at', 'value', 'target', 'pillar'],
        'unique_key': ['account_id', 'kpi_code', 'measured_at'],  # Natural key
        'config_aware': True
    },
    'signals': {
        'model': QualitativeSignal,
        'table_name': 'qualitative_signals',
        'required_columns': ['account_id', 'signal_date', 'signal_type', 'signal_text'],  # signal_text will map to content
        'unique_key': ['signal_id'],  # Use primary key (signal_id is VARCHAR(50) in existing table)
        'config_aware': False
    },
    'accounts': {
        'model': Account,
        'table_name': 'accounts',
        'required_columns': ['account_id', 'customer_id', 'account_name'],
        'unique_key': ['account_id'],  # Primary key
        'config_aware': False
    },
    'products': {
        'model': None,  # Will import Product model when needed
        'table_name': 'products',
        'required_columns': ['customer_id', 'product_id', 'product_name'],
        'unique_key': ['customer_id', 'product_id'],  # Unique constraint: uk_products
        'config_aware': False
    },
    'profiles': {
        'model': Account,  # Profiles stored in Account.profile_metadata
        'table_name': 'accounts',
        'required_columns': ['account_id', 'profile_metadata'],
        'unique_key': ['account_id'],  # Update account's profile_metadata
        'config_aware': False
    },
    'customers': {
        'model': Customer,
        'table_name': 'customers',
        'required_columns': ['customer_id', 'customer_name'],
        'unique_key': ['customer_id'],  # Primary key
        'config_aware': False
    }
}

# ============================================================================
# Main Upload Endpoint
# ============================================================================

@upload_api_v3_improved.route('/upload', methods=['POST'])
def upload_csv():
    """
    Upload CSV file with proper duplicate handling
    
    Form Parameters:
        file: CSV file
        customer_id: Customer ID
        file_type: Type of file (kpis, signals, accounts, products, profiles, customers)
        upload_mode: Upload mode (incremental, full_refresh, upsert, merge)
        duplicate_strategy: How to handle duplicates (skip, error, update, replace)
            - Default varies by upload_mode:
              - incremental: skip (default)
              - upsert: update
              - merge: update with smart merge
              - full_refresh: replace
    """
    
    # Validate request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    customer_id = request.form.get('customer_id')
    file_type = request.form.get('file_type', 'kpis')
    upload_mode = request.form.get('upload_mode', 'incremental')
    duplicate_strategy = request.form.get('duplicate_strategy')
    
    if not customer_id:
        return jsonify({'error': 'customer_id required'}), 400
    
    if file_type not in FILE_TYPE_CONFIG:
        return jsonify({
            'error': f'Invalid file_type: {file_type}',
            'supported_types': list(FILE_TYPE_CONFIG.keys())
        }), 400
    
    # Set default duplicate strategy based on upload mode
    if not duplicate_strategy:
        duplicate_strategy = {
            'incremental': 'skip',
            'upsert': 'update',
            'merge': 'update',
            'full_refresh': 'replace'
        }.get(upload_mode, 'skip')
    
    try:
        customer_id = int(customer_id)
    except ValueError:
        return jsonify({'error': 'customer_id must be an integer'}), 400
    
    # Read CSV
    try:
        csv_content = file.read().decode('utf-8')
        df = pd.read_csv(StringIO(csv_content))
    except Exception as e:
        return jsonify({'error': f'Failed to read CSV: {str(e)}'}), 400
    
    # Get file type config
    config = FILE_TYPE_CONFIG[file_type]
    
        # Check if model is available (products imports Product when needed)
    if config['model'] is None and file_type not in ['profiles', 'products']:
        return jsonify({
            'error': f'Model not available for file_type: {file_type}',
            'message': 'This file type requires additional model definitions'
        }), 501
    
    # Validate columns
    missing_columns = set(config['required_columns']) - set(df.columns)
    if missing_columns:
        return jsonify({
            'error': f'Missing required columns for {file_type}',
            'missing': list(missing_columns),
            'required': config['required_columns']
        }), 400
    
    # Process based on file type
    try:
        if file_type == 'kpis':
            result = process_kpi_upload_improved(df, customer_id, upload_mode, duplicate_strategy)
        elif file_type == 'signals':
            result = process_signals_upload(df, customer_id, upload_mode, duplicate_strategy)
        elif file_type == 'accounts':
            result = process_accounts_upload(df, customer_id, upload_mode, duplicate_strategy)
        elif file_type == 'products':
            result = process_products_upload(df, customer_id, upload_mode, duplicate_strategy)
        elif file_type == 'profiles':
            result = process_profiles_upload(df, customer_id, upload_mode, duplicate_strategy)
        elif file_type == 'customers':
            result = process_customers_upload(df, customer_id, upload_mode, duplicate_strategy)
        else:
            return jsonify({'error': f'File type {file_type} not implemented'}), 501
        
        return jsonify(result), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'error': f'Upload failed: {str(e)}',
            'file_type': file_type,
            'upload_mode': upload_mode,
            'traceback': traceback.format_exc()
        }), 500

# ============================================================================
# KPI Upload (Config-Aware)
# ============================================================================

def process_kpi_upload_improved(df, customer_id, upload_mode, duplicate_strategy):
    """Process KPI upload with config-aware filtering and duplicate handling"""
    
    # Load config
    loader = ConfigLoader(customer_id)
    enabled_kpis = set(loader.get_enabled_kpis())
    
    records_in_csv = len(df)
    csv_kpis = set(df['kpi_code'].unique())
    
    # Filter to enabled KPIs only
    df_filtered = df[df['kpi_code'].isin(enabled_kpis)].copy()
    records_after_filter = len(df_filtered)
    records_filtered = records_in_csv - records_after_filter
    disabled_kpis = list(csv_kpis - enabled_kpis)
    
    if len(df_filtered) == 0:
        return {
            'status': 'warning',
            'message': 'No records to process after filtering',
            'records_in_csv': records_in_csv,
            'records_filtered': records_filtered,
            'enabled_kpis': len(enabled_kpis)
        }
    
    # Get account IDs for full_refresh
    account_ids = df_filtered['account_id'].unique().tolist()
    
    # Handle full_refresh mode
    # Note: DC2SKPI doesn't have customer_id column, filter by account_id only
    # We need to get account_ids that belong to this customer first
    if upload_mode == 'full_refresh' or duplicate_strategy == 'replace':
        # Get account_ids that belong to this customer
        from models import Account
        customer_account_ids = Account.query.filter_by(customer_id=customer_id).with_entities(Account.account_id).all()
        customer_account_ids = [a[0] for a in customer_account_ids]
        
        # Only delete KPIs for accounts that are in both lists (safety check)
        account_ids_to_delete = [aid for aid in account_ids if aid in customer_account_ids]
        
        if account_ids_to_delete:
            deleted = DC2SKPI.query.filter(
                DC2SKPI.account_id.in_(account_ids_to_delete)
            ).delete(synchronize_session=False)
            db.session.commit()
    
    # Prepare data for insertion
    df_filtered['measured_at'] = pd.to_datetime(df_filtered['measured_at'])
    
    # Note: DC2SKPI doesn't have customer_id column - it's derived from Account
    # Don't add customer_id to records
    
    # Handle duplicates based on strategy
    if duplicate_strategy == 'update' or upload_mode in ['upsert', 'merge']:
        # Use PostgreSQL UPSERT (ON CONFLICT UPDATE)
        records_processed = bulk_upsert_kpis(df_filtered)
        duplicates_skipped = 0
        duplicates_updated = records_after_filter
        
    elif duplicate_strategy == 'skip' or upload_mode == 'incremental':
        # Skip duplicates (INSERT IGNORE style)
        records_processed, duplicates_skipped = bulk_insert_skip_duplicates_kpis(df_filtered)
        duplicates_updated = 0
        
    elif duplicate_strategy == 'error':
        # Fail on first duplicate
        records_processed = bulk_insert_fail_on_duplicate_kpis(df_filtered)
        duplicates_skipped = 0
        duplicates_updated = 0
        
    else:
        # Default: skip
        records_processed, duplicates_skipped = bulk_insert_skip_duplicates_kpis(df_filtered)
        duplicates_updated = 0
    
    return {
        'status': 'success',
        'file_type': 'kpis',
        'upload_mode': upload_mode,
        'duplicate_strategy': duplicate_strategy,
        'records_in_csv': records_in_csv,
        'records_filtered': records_filtered,
        'records_processed': records_processed,
        'duplicates_skipped': duplicates_skipped,
        'duplicates_updated': duplicates_updated,
        'enabled_kpis': len(enabled_kpis),
        'csv_kpis': len(csv_kpis),
        'disabled_kpis': disabled_kpis,
        'filter_percentage': f"{(records_filtered/records_in_csv*100):.1f}%" if records_in_csv > 0 else "0%"
    }

# ============================================================================
# Bulk Operations for KPIs
# ============================================================================

def bulk_upsert_kpis(df):
    """Bulk upsert using PostgreSQL ON CONFLICT UPDATE"""
    records = df.to_dict('records')
    
    if not records:
        return 0
    
    # Convert datetime and remove customer_id (DC2SKPI doesn't have this column)
    for record in records:
        if 'measured_at' in record and pd.notna(record['measured_at']):
            if isinstance(record['measured_at'], pd.Timestamp):
                record['measured_at'] = record['measured_at'].to_pydatetime()
        # Remove customer_id if present (DC2SKPI doesn't have this column)
        if 'customer_id' in record:
            del record['customer_id']
    
    # PostgreSQL UPSERT
    stmt = insert(DC2SKPI).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=['account_id', 'kpi_code', 'measured_at'],
        set_={
            'value': stmt.excluded.value,
            'target': stmt.excluded.target,
            'pillar': stmt.excluded.pillar
        }
    )
    
    db.session.execute(stmt)
    db.session.commit()
    
    return len(records)

def bulk_insert_skip_duplicates_kpis(df):
    """Bulk insert, skip duplicates (ON CONFLICT DO NOTHING)"""
    records = df.to_dict('records')
    
    if not records:
        return 0, 0
    
    # Convert datetime and remove customer_id (DC2SKPI doesn't have this column)
    for record in records:
        if 'measured_at' in record and pd.notna(record['measured_at']):
            if isinstance(record['measured_at'], pd.Timestamp):
                record['measured_at'] = record['measured_at'].to_pydatetime()
        # Remove customer_id if present (DC2SKPI doesn't have this column)
        if 'customer_id' in record:
            del record['customer_id']
    
    # Get count before
    count_before = db.session.query(DC2SKPI).count()
    
    # PostgreSQL INSERT ... ON CONFLICT DO NOTHING
    stmt = insert(DC2SKPI).values(records)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=['account_id', 'kpi_code', 'measured_at']
    )
    
    db.session.execute(stmt)
    db.session.commit()
    
    # Get count after
    count_after = db.session.query(DC2SKPI).count()
    
    inserted = count_after - count_before
    skipped = len(records) - inserted
    
    return inserted, skipped

def bulk_insert_fail_on_duplicate_kpis(df):
    """Bulk insert, fail on first duplicate"""
    records = df.to_dict('records')
    
    if not records:
        return 0
    
    # Convert datetime and remove customer_id (DC2SKPI doesn't have this column)
    for record in records:
        if 'measured_at' in record and pd.notna(record['measured_at']):
            if isinstance(record['measured_at'], pd.Timestamp):
                record['measured_at'] = record['measured_at'].to_pydatetime()
        # Remove customer_id if present (DC2SKPI doesn't have this column)
        if 'customer_id' in record:
            del record['customer_id']
    
    # This will raise IntegrityError if duplicate exists
    db.session.bulk_insert_mappings(DC2SKPI, records)
    db.session.commit()
    
    return len(records)

# ============================================================================
# Signals Upload
# ============================================================================

def process_signals_upload(df, customer_id, upload_mode, duplicate_strategy):
    """Process signals upload"""
    records_in_csv = len(df)
    
    if len(df) == 0:
        return {
            'status': 'warning',
            'message': 'No records in CSV',
            'records_in_csv': 0
        }
    
    # Convert signal_date to date
    df['signal_date'] = pd.to_datetime(df['signal_date']).dt.date
    
    # Map signal_text to content (existing table column name is 'content', not 'signal_text')
    if 'signal_text' in df.columns and 'content' not in df.columns:
        df['content'] = df['signal_text']
        # Drop signal_text column to avoid confusion
        df = df.drop(columns=['signal_text'])
    
    # Generate signal_id if not provided (existing table uses VARCHAR(50), not auto-increment)
    if 'signal_id' not in df.columns:
        import uuid
        df['signal_id'] = [str(uuid.uuid4())[:50] for _ in range(len(df))]  # Limit to 50 chars
    
    # Handle full_refresh mode
    if upload_mode == 'full_refresh' or duplicate_strategy == 'replace':
        if 'account_id' in df.columns:
            account_ids = df['account_id'].unique().tolist()
            # Get account_ids that belong to this customer
            from models import Account
            customer_account_ids = Account.query.filter_by(customer_id=customer_id).with_entities(Account.account_id).all()
            customer_account_ids = [a[0] for a in customer_account_ids]
            account_ids_to_delete = [aid for aid in account_ids if aid in customer_account_ids]
            
            if account_ids_to_delete:
                QualitativeSignal.query.filter(
                    QualitativeSignal.account_id.in_(account_ids_to_delete)
                ).delete(synchronize_session=False)
        db.session.commit()
    
    records = df.to_dict('records')
    
    # Handle duplicates
    if duplicate_strategy == 'update' or upload_mode in ['upsert', 'merge']:
        records_processed = bulk_upsert_signals(records)
        duplicates_skipped = 0
        duplicates_updated = records_in_csv
    elif duplicate_strategy == 'skip' or upload_mode == 'incremental':
        records_processed, duplicates_skipped = bulk_insert_skip_duplicates_signals(records)
        duplicates_updated = 0
    elif duplicate_strategy == 'error':
        db.session.bulk_insert_mappings(QualitativeSignal, records)
        db.session.commit()
        records_processed = len(records)
        duplicates_skipped = 0
        duplicates_updated = 0
    else:
        records_processed, duplicates_skipped = bulk_insert_skip_duplicates_signals(records)
        duplicates_updated = 0
    
    return {
        'status': 'success',
        'file_type': 'signals',
        'upload_mode': upload_mode,
        'duplicate_strategy': duplicate_strategy,
        'records_in_csv': records_in_csv,
        'records_processed': records_processed,
        'duplicates_skipped': duplicates_skipped,
        'duplicates_updated': duplicates_updated
    }

def bulk_upsert_signals(records):
    """Bulk upsert signals"""
    if not records:
        return 0
    
    # Map signal_text to content for existing table schema
    for record in records:
        if 'signal_text' in record and 'content' not in record:
            record['content'] = record.pop('signal_text')
    
    stmt = insert(QualitativeSignal).values(records)
    # Use signal_id as conflict target (primary key) since unique constraint may not exist
    stmt = stmt.on_conflict_do_update(
        index_elements=['signal_id'],
        set_={
            'content': stmt.excluded.content,
            'sentiment': stmt.excluded.sentiment,
            'signal_type': stmt.excluded.signal_type
        }
    )
    
    db.session.execute(stmt)
    db.session.commit()
    
    return len(records)

def bulk_insert_skip_duplicates_signals(records):
    """Bulk insert signals, skip duplicates"""
    if not records:
        return 0, 0
    
    # Map signal_text to content for existing table schema
    for record in records:
        if 'signal_text' in record and 'content' not in record:
            record['content'] = record.pop('signal_text')
    
    count_before = db.session.query(QualitativeSignal).count()
    
    stmt = insert(QualitativeSignal).values(records)
    # Use signal_id as conflict target (primary key)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=['signal_id']
    )
    
    db.session.execute(stmt)
    db.session.commit()
    
    count_after = db.session.query(QualitativeSignal).count()
    inserted = count_after - count_before
    skipped = len(records) - inserted
    
    return inserted, skipped

# ============================================================================
# Generic Upload (Other File Types)
# ============================================================================

def process_accounts_upload(df, customer_id, upload_mode, duplicate_strategy):
    """Process accounts upload"""
    records_in_csv = len(df)
    
    if len(df) == 0:
        return {
            'status': 'warning',
            'message': 'No records in CSV',
            'records_in_csv': 0
        }
    
    # Ensure customer_id is set
    df['customer_id'] = customer_id
    
    # Handle full_refresh mode
    if upload_mode == 'full_refresh' or duplicate_strategy == 'replace':
        account_ids = df['account_id'].unique().tolist()
        Account.query.filter(
            Account.account_id.in_(account_ids),
            Account.customer_id == customer_id
        ).delete(synchronize_session=False)
        db.session.commit()
    
    records = df.to_dict('records')
    
    # Handle duplicates
    if duplicate_strategy == 'update' or upload_mode in ['upsert', 'merge']:
        records_processed = bulk_upsert_accounts(records)
        duplicates_skipped = 0
        duplicates_updated = records_in_csv
    elif duplicate_strategy == 'skip' or upload_mode == 'incremental':
        records_processed, duplicates_skipped = bulk_insert_skip_duplicates_accounts(records)
        duplicates_updated = 0
    elif duplicate_strategy == 'error':
        db.session.bulk_insert_mappings(Account, records)
        db.session.commit()
        records_processed = len(records)
        duplicates_skipped = 0
        duplicates_updated = 0
    else:
        records_processed, duplicates_skipped = bulk_insert_skip_duplicates_accounts(records)
        duplicates_updated = 0
    
    return {
        'status': 'success',
        'file_type': 'accounts',
        'upload_mode': upload_mode,
        'duplicate_strategy': duplicate_strategy,
        'records_in_csv': records_in_csv,
        'records_processed': records_processed,
        'duplicates_skipped': duplicates_skipped,
        'duplicates_updated': duplicates_updated
    }

def process_products_upload(df, customer_id, upload_mode, duplicate_strategy):
    """Process products upload"""
    from models import Product
    
    records_in_csv = len(df)
    
    if len(df) == 0:
        return {
            'status': 'warning',
            'message': 'No records in CSV',
            'records_in_csv': 0
        }
    
    # Ensure customer_id is set
    df['customer_id'] = customer_id
    
    # Product_id is required for unique constraint (customer_id, product_id)
    if 'product_id' not in df.columns:
        return {
            'status': 'error',
            'message': 'product_id is required for products upload',
            'records_in_csv': records_in_csv
        }
    
    # Handle full_refresh mode
    if upload_mode == 'full_refresh' or duplicate_strategy == 'replace':
        # Delete products for this customer
        Product.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        db.session.commit()
    
    records = df.to_dict('records')
    
    # Remove columns that don't exist in Product model
    for record in records:
        if 'category' in record:
            # Map category to product_type if product_type not present
            if 'product_type' not in record:
                record['product_type'] = record.get('category', 'Unknown')
            del record['category']
    
    # Handle duplicates
    if duplicate_strategy == 'update' or upload_mode in ['upsert', 'merge']:
        records_processed = bulk_upsert_products(records)
        duplicates_skipped = 0
        duplicates_updated = records_in_csv
    elif duplicate_strategy == 'skip' or upload_mode == 'incremental':
        records_processed, duplicates_skipped = bulk_insert_skip_duplicates_products(records)
        duplicates_updated = 0
    elif duplicate_strategy == 'error':
        db.session.bulk_insert_mappings(Product, records)
        db.session.commit()
        records_processed = len(records)
        duplicates_skipped = 0
        duplicates_updated = 0
    else:
        records_processed, duplicates_skipped = bulk_insert_skip_duplicates_products(records)
        duplicates_updated = 0
    
    return {
        'status': 'success',
        'file_type': 'products',
        'upload_mode': upload_mode,
        'duplicate_strategy': duplicate_strategy,
        'records_in_csv': records_in_csv,
        'records_processed': records_processed,
        'duplicates_skipped': duplicates_skipped,
        'duplicates_updated': duplicates_updated
    }

def process_profiles_upload(df, customer_id, upload_mode, duplicate_strategy):
    """Process profiles upload (stored in Account.profile_metadata)"""
    records_in_csv = len(df)
    
    if len(df) == 0:
        return {
            'status': 'warning',
            'message': 'No records in CSV',
            'records_in_csv': 0
        }
    
    # Profiles are stored as JSON in Account.profile_metadata
    # CSV should have account_id and profile_metadata (JSON string)
    records_processed = 0
    
    for _, row in df.iterrows():
        account_id = int(row['account_id'])
        profile_metadata = row.get('profile_metadata', '{}')
        
        # Parse JSON if it's a string
        import json
        if isinstance(profile_metadata, str):
            try:
                profile_metadata = json.loads(profile_metadata)
            except:
                profile_metadata = {}
        
        # Update account
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).first()
        
        if account:
            account.profile_metadata = profile_metadata
            records_processed += 1
    
    db.session.commit()
    
    return {
        'status': 'success',
        'file_type': 'profiles',
        'upload_mode': upload_mode,
        'duplicate_strategy': duplicate_strategy,
        'records_in_csv': records_in_csv,
        'records_processed': records_processed,
        'duplicates_skipped': 0,
        'duplicates_updated': records_processed
    }

def process_customers_upload(df, customer_id, upload_mode, duplicate_strategy):
    """Process customers upload"""
    records_in_csv = len(df)
    
    if len(df) == 0:
        return {
            'status': 'warning',
            'message': 'No records in CSV',
            'records_in_csv': 0
        }
    
    # Handle full_refresh mode
    # Note: Can't delete customer if it has accounts (foreign key constraint)
    # So we skip deletion for customers in full_refresh mode
    if upload_mode == 'full_refresh' or duplicate_strategy == 'replace':
        # Don't delete customer - it has foreign key constraints
        # Just update existing customer record instead
        pass
    
    records = df.to_dict('records')
    
    # Handle duplicates
    if duplicate_strategy == 'update' or upload_mode in ['upsert', 'merge']:
        records_processed = bulk_upsert_customers(records)
        duplicates_skipped = 0
        duplicates_updated = records_in_csv
    elif duplicate_strategy == 'skip' or upload_mode == 'incremental':
        records_processed, duplicates_skipped = bulk_insert_skip_duplicates_customers(records)
        duplicates_updated = 0
    elif duplicate_strategy == 'error':
        db.session.bulk_insert_mappings(Customer, records)
        db.session.commit()
        records_processed = len(records)
        duplicates_skipped = 0
        duplicates_updated = 0
    else:
        records_processed, duplicates_skipped = bulk_insert_skip_duplicates_customers(records)
        duplicates_updated = 0
    
    return {
        'status': 'success',
        'file_type': 'customers',
        'upload_mode': upload_mode,
        'duplicate_strategy': duplicate_strategy,
        'records_in_csv': records_in_csv,
        'records_processed': records_processed,
        'duplicates_skipped': duplicates_skipped,
        'duplicates_updated': duplicates_updated
    }

def process_generic_upload(df, customer_id, upload_mode, duplicate_strategy, config):
    """Generic upload processor for non-KPI file types"""
    
    records_in_csv = len(df)
    model = config['model']
    unique_key = config['unique_key']
    
    if len(df) == 0:
        return {
            'status': 'warning',
            'message': 'No records in CSV',
            'records_in_csv': 0
        }
    
    # Handle full_refresh mode
    if upload_mode == 'full_refresh' or duplicate_strategy == 'replace':
        if 'customer_id' in df.columns:
            model.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        elif 'account_id' in df.columns:
            account_ids = df['account_id'].unique().tolist()
            model.query.filter(model.account_id.in_(account_ids)).delete(synchronize_session=False)
        db.session.commit()
    
    # Convert to records
    records = df.to_dict('records')
    
    # Handle duplicates
    if duplicate_strategy == 'update' or upload_mode in ['upsert', 'merge']:
        # Use bulk upsert
        records_processed = bulk_upsert_generic(model, records, unique_key)
        duplicates_skipped = 0
        duplicates_updated = records_in_csv
        
    elif duplicate_strategy == 'skip' or upload_mode == 'incremental':
        # Skip duplicates
        records_processed, duplicates_skipped = bulk_insert_skip_duplicates_generic(model, records, unique_key)
        duplicates_updated = 0
        
    elif duplicate_strategy == 'error':
        # Fail on duplicate
        db.session.bulk_insert_mappings(model, records)
        db.session.commit()
        records_processed = len(records)
        duplicates_skipped = 0
        duplicates_updated = 0
        
    else:
        # Default: skip
        records_processed, duplicates_skipped = bulk_insert_skip_duplicates_generic(model, records, unique_key)
        duplicates_updated = 0
    
    return {
        'status': 'success',
        'file_type': config['table_name'],
        'upload_mode': upload_mode,
        'duplicate_strategy': duplicate_strategy,
        'records_in_csv': records_in_csv,
        'records_processed': records_processed,
        'duplicates_skipped': duplicates_skipped,
        'duplicates_updated': duplicates_updated
    }

# ============================================================================
# Bulk Operations
# ============================================================================

def bulk_upsert_accounts(records):
    """Bulk upsert accounts"""
    if not records:
        return 0
    
    stmt = insert(Account).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=['account_id'],
        set_={
            'account_name': stmt.excluded.account_name,
            'customer_id': stmt.excluded.customer_id,
            'updated_at': datetime.utcnow()
        }
    )
    
    db.session.execute(stmt)
    db.session.commit()
    
    return len(records)

def bulk_insert_skip_duplicates_accounts(records):
    """Bulk insert accounts, skip duplicates"""
    if not records:
        return 0, 0
    
    count_before = db.session.query(Account).count()
    
    stmt = insert(Account).values(records)
    stmt = stmt.on_conflict_do_nothing(index_elements=['account_id'])
    
    db.session.execute(stmt)
    db.session.commit()
    
    count_after = db.session.query(Account).count()
    inserted = count_after - count_before
    skipped = len(records) - inserted
    
    return inserted, skipped

def bulk_upsert_products(records):
    """Bulk upsert products"""
    from models import Product
    
    if not records:
        return 0
    
    # Remove columns that don't exist in Product model
    for record in records:
        if 'category' in record:
            del record['category']
    
    stmt = insert(Product).values(records)
    # Products have unique constraint uk_products on (customer_id, product_id)
    stmt = stmt.on_conflict_do_update(
        constraint='uk_products',
        set_={
            'product_name': stmt.excluded.product_name,
            'product_sku': stmt.excluded.product_sku,
            'product_type': stmt.excluded.product_type,
            'revenue': stmt.excluded.revenue,
            'status': stmt.excluded.status,
            'account_id': stmt.excluded.account_id
        }
    )
    
    db.session.execute(stmt)
    db.session.commit()
    
    return len(records)

def bulk_insert_skip_duplicates_products(records):
    """Bulk insert products, skip duplicates"""
    from models import Product
    
    if not records:
        return 0, 0
    
    # Remove columns that don't exist in Product model
    for record in records:
        if 'category' in record:
            del record['category']
    
    count_before = db.session.query(Product).count()
    
    stmt = insert(Product).values(records)
    # Products have unique constraint uk_products on (customer_id, product_id)
    stmt = stmt.on_conflict_do_nothing(constraint='uk_products')
    
    db.session.execute(stmt)
    db.session.commit()
    
    count_after = db.session.query(Product).count()
    inserted = count_after - count_before
    skipped = len(records) - inserted
    
    return inserted, skipped

def bulk_upsert_customers(records):
    """Bulk upsert customers"""
    if not records:
        return 0
    
    # Remove columns that don't exist in Customer model
    for record in records:
        # Customer model doesn't have 'vertical' or 'created_at' columns
        if 'vertical' in record:
            del record['vertical']
        if 'created_at' in record:
            del record['created_at']
    
    stmt = insert(Customer).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=['customer_id'],
        set_={
            'customer_name': stmt.excluded.customer_name
        }
    )
    
    db.session.execute(stmt)
    db.session.commit()
    
    return len(records)

def bulk_insert_skip_duplicates_customers(records):
    """Bulk insert customers, skip duplicates"""
    if not records:
        return 0, 0
    
    # Remove columns that don't exist in Customer model
    for record in records:
        if 'vertical' in record:
            del record['vertical']
        if 'created_at' in record:
            del record['created_at']
    
    count_before = db.session.query(Customer).count()
    
    stmt = insert(Customer).values(records)
    stmt = stmt.on_conflict_do_nothing(index_elements=['customer_id'])
    
    db.session.execute(stmt)
    db.session.commit()
    
    count_after = db.session.query(Customer).count()
    inserted = count_after - count_before
    skipped = len(records) - inserted
    
    return inserted, skipped

def bulk_upsert_generic(model, records, unique_key):
    """Bulk upsert for any model"""
    if not records:
        return 0
    
    stmt = insert(model).values(records)
    
    # Build update dict (all columns except unique key)
    all_columns = records[0].keys()
    update_dict = {
        col: getattr(stmt.excluded, col)
        for col in all_columns
        if col not in unique_key
    }
    
    stmt = stmt.on_conflict_do_update(
        index_elements=unique_key,
        set_=update_dict
    )
    
    db.session.execute(stmt)
    db.session.commit()
    
    return len(records)

def bulk_insert_skip_duplicates_generic(model, records, unique_key):
    """Bulk insert with skip duplicates for any model"""
    if not records:
        return 0, 0
    
    count_before = db.session.query(model).count()
    
    stmt = insert(model).values(records)
    stmt = stmt.on_conflict_do_nothing(index_elements=unique_key)
    
    db.session.execute(stmt)
    db.session.commit()
    
    count_after = db.session.query(model).count()
    
    inserted = count_after - count_before
    skipped = len(records) - inserted
    
    return inserted, skipped

# ============================================================================
# Health Check
# ============================================================================

@upload_api_v3_improved.route('/upload/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '3.0',
        'supported_file_types': list(FILE_TYPE_CONFIG.keys()),
        'supported_upload_modes': ['incremental', 'full_refresh', 'upsert', 'merge'],
        'supported_duplicate_strategies': list(DUPLICATE_STRATEGIES.keys())
    }), 200
