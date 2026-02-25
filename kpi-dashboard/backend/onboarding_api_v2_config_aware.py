"""
Updated Onboarding API - Config-Aware
======================================

UPDATES:
- Validates CSV uploads against CustomerConfig
- Filters disabled KPIs before processing
- Provides warnings for config mismatches
- Backward compatible with existing flow

Add to app_v3_minimal.py:
    from onboarding_api_v2_config_aware import onboarding_api
    app.register_blueprint(onboarding_api)
"""

from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
import subprocess
import pandas as pd
from datetime import datetime
import json
import os
import sys
import time
import uuid
from typing import Tuple, List, Dict, Optional
from werkzeug.utils import secure_filename

# Import db - avoid circular import with app_v3_minimal
from extensions import db
from flask import current_app
from models import Customer, CustomerConfig, Account, User
from utils.config_loader import ConfigLoader
from auth_middleware import get_current_user_id
from werkzeug.security import generate_password_hash
from id_generator import generate_id
from uuid_utils import ensure_uuid, ensure_customer_uuid_on_account

# File types supported for upload
FILE_TYPES = {
    'accounts': 'accounts.csv',
    'kpis': 'kpi_measurements.csv',
    'signals': 'qualitative_signals.csv',
    'products': 'products.csv',
    'profiles': 'profiles.csv'
}

onboarding_api = Blueprint('onboarding_v2', __name__)

# GAP 3.8: Progress tracking for long-running process-data (in-memory; per process)
_onboarding_progress = {}


# ============================================================================
# Helper Functions
# ============================================================================

def get_customer_directory(customer_id: int, vertical_slug: str = 'dc2_s') -> Path:
    """Get path to customer directory"""
    backend_dir = Path(__file__).parent
    verticals_dir = backend_dir / "verticals"
    return verticals_dir / f"customer{customer_id}-{vertical_slug}"


def execute_script(script_path: Path, customer_id: int, timeout: int = 300, 
                   additional_args: List[str] = None, env: dict = None) -> Tuple[bool, str, str]:
    """
    Execute a Python script synchronously
    
    Args:
        script_path: Path to script
        customer_id: Customer ID to pass as environment variable
        timeout: Execution timeout in seconds
        additional_args: Additional command-line arguments to pass to script
        env: Additional environment variables (merged with CUSTOMER_ID)
    
    Returns:
        (success, stdout, stderr)
    """
    try:
        # Change to script directory
        script_dir = script_path.parent
        script_name = script_path.name
        
        # Build command
        cmd = [sys.executable, script_name]
        if additional_args:
            cmd.extend(additional_args)
        
        # Build environment
        script_env = {**os.environ, 'CUSTOMER_ID': str(customer_id)}
        if env:
            script_env.update(env)
        
        # Run script
        result = subprocess.run(
            cmd,
            cwd=str(script_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=script_env
        )
        
        return (result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (False, "", f"Script execution timed out after {timeout} seconds")
    except Exception as e:
        return (False, "", str(e))


# Expected DC2_S pillar names for weight validation
DC2S_PILLAR_NAMES = {'AI', 'CH', 'DV', 'EX', 'OS'}


def validate_dc2s_pillar_weights(weights: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate custom pillar weights for /complete request.
    Checks: sum to 1.0, all pillars present, non-negative, valid pillar names.
    Returns (True, None) if valid, (False, error_message) otherwise.
    """
    if not weights:
        return (True, None)
    if not isinstance(weights, dict):
        return (False, "weights must be a dict")
    total = sum(float(v) for v in weights.values())
    if abs(total - 1.0) > 0.01:
        return (False, f"weights sum to {total:.4f}, expected 1.0")
    if set(weights.keys()) != DC2S_PILLAR_NAMES:
        missing = DC2S_PILLAR_NAMES - set(weights.keys())
        extra = set(weights.keys()) - DC2S_PILLAR_NAMES
        if missing or extra:
            return (False, f"weights must have exactly pillars {DC2S_PILLAR_NAMES}; missing: {missing or 'none'}; extra: {extra or 'none'}")
    if any(float(v) < 0 for v in weights.values()):
        return (False, "weights must be non-negative")
    return (True, None)


def generate_account_uuid() -> str:
    """
    Generate a UUID for a new account.

    Returns:
        UUID string like 'dc2s_acct_<uuid4>'
    """
    return f"dc2s_acct_{uuid.uuid4()}"


def calculate_account_id_range(customer_id: int) -> Tuple[int, int]:
    """
    DEPRECATED: Account IDs are now auto-incremented by the database.
    Use generate_account_uuid() for new account identification.

    Kept for backward compatibility with CSV validation that may still
    reference integer account IDs in legacy data files.

    Returns:
        (start_id, end_id) tuple
    """
    start_id = customer_id * 1000 + 1
    end_id = customer_id * 1000 + 999
    return (start_id, end_id)


def validate_account_ids_in_file(file_path: Path, customer_id: int, file_type: str) -> Tuple[bool, List[str]]:
    """
    Validate that account IDs in uploaded file match expected range
    
    Args:
        file_path: Path to uploaded file
        customer_id: Customer ID
        file_type: Type of file ('accounts', 'kpis', 'signals', 'products', 'profiles')
    
    Returns:
        (is_valid, errors) tuple
    """
    errors = []
    expected_start, expected_end = calculate_account_id_range(customer_id)
    
    try:
        # Read file based on type
        if file_path.suffix.lower() == '.csv':
            df = pd.read_csv(file_path, nrows=1000)  # Sample first 1000 rows for validation
        elif file_path.suffix.lower() in ['.xlsx', '.xls']:
            # For Excel, read first sheet
            try:
                df = pd.read_excel(file_path, nrows=1000, engine='openpyxl' if file_path.suffix.lower() == '.xlsx' else None)
            except ImportError:
                # Fallback if openpyxl not available
                df = pd.read_excel(file_path, nrows=1000)
        else:
            return (True, [])  # Skip validation for unknown file types
        
        if df.empty:
            return (True, [])  # Empty file, no validation needed
        
        # Determine account_id column name
        account_id_col = None
        possible_names = ['account_id', 'Account ID', 'AccountID', 'accountId', 'ACCOUNT_ID']
        for col in df.columns:
            if col.strip() in possible_names:
                account_id_col = col
                break
        
        if not account_id_col:
            # If no account_id column, skip validation (might be profiles or products)
            if file_type in ['profiles', 'products']:
                return (True, [])
            # For other types, warn but don't fail
            return (True, [f"Warning: No account_id column found in {file_type} file"])
        
        # Validate account IDs
        account_ids = df[account_id_col].dropna().unique()
        invalid_ids = []
        
        for account_id in account_ids:
            try:
                account_id_int = int(float(account_id))  # Handle float account IDs
                if account_id_int < expected_start or account_id_int > expected_end:
                    invalid_ids.append(account_id_int)
            except (ValueError, TypeError):
                # Skip non-numeric account IDs (might be strings like "NEW_ACCOUNT")
                continue
        
        if invalid_ids:
            errors.append(
                f"Invalid account IDs found: {sorted(set(invalid_ids))[:10]}. "
                f"Expected range: {expected_start}-{expected_end} for Customer {customer_id}. "
                f"Formula: (customer_id * 1000) + 1 to (customer_id * 1000) + 999"
            )
            return (False, errors)
        
        return (True, [])
        
    except Exception as e:
        # If validation fails due to file reading error, log but don't block upload
        current_app.logger.warning(f"Account ID validation error for {file_path}: {e}")
        return (True, [f"Warning: Could not validate account IDs: {str(e)}"])

# ============================================================================
# Config Validation Helper
# ============================================================================

def validate_csv_against_config(customer_id: int, csv_file: Path, strict_mode: bool = False) -> dict:
    """
    Validate CSV file against CustomerConfig
    
    Checks:
    - CSV contains valid columns
    - KPIs in CSV vs enabled in config
    - Provides warnings for disabled KPIs
    
    Args:
        customer_id: Customer ID
        csv_file: Path to CSV file
        strict_mode: If True, fail validation if disabled KPIs found
    
    Returns:
        {
            "valid": bool,
            "enabled_kpis": int,
            "csv_kpis": int,
            "disabled_kpis": list,
            "warnings": list,
            "will_filter": bool,
            "details": dict
        }
    """
    
    if not csv_file.exists():
        return {
            "valid": False,
            "error": f"File not found: {csv_file}"
        }
    
    try:
        # Read CSV
        df = pd.read_csv(csv_file)
        
        # Validate columns - match generator output (measured_at, target) or database schema (measurement_month, target_value)
        # Accept either format for flexibility
        required_cols_base = ['account_id', 'kpi_code', 'value']
        missing_base = [col for col in required_cols_base if col not in df.columns]
        
        if missing_base:
            return {
                "valid": False,
                "error": f"Missing required columns: {missing_base}"
            }
        
        # Check for date column (either measured_at or measurement_month)
        has_date_col = 'measured_at' in df.columns or 'measurement_month' in df.columns
        has_target_col = 'target' in df.columns or 'target_value' in df.columns
        
        if not has_date_col:
            return {
                "valid": False,
                "error": "Missing required date column: 'measured_at' or 'measurement_month'"
            }
        
        if not has_target_col:
            return {
                "valid": False,
                "error": "Missing required target column: 'target' or 'target_value'"
            }
        
        missing_cols = []  # All required columns present
        
        if missing_cols:
            return {
                "valid": False,
                "error": f"Missing required columns: {missing_cols}"
            }
        
        # Get enabled KPIs from config
        with current_app.app_context():
            loader = ConfigLoader(customer_id)
            enabled_kpis = set(loader.get_enabled_kpis())
            
            # Get KPIs in CSV
            csv_kpis = set(df['kpi_code'].unique())
            
            # Find disabled KPIs
            disabled_kpis = csv_kpis - enabled_kpis
            
            # Build warnings
            warnings = []
            if disabled_kpis:
                if strict_mode:
                    return {
                        "valid": False,
                        "error": f"CSV contains disabled KPIs in strict mode: {list(disabled_kpis)}",
                        "enabled_kpis": len(enabled_kpis),
                        "csv_kpis": len(csv_kpis),
                        "disabled_kpis": list(disabled_kpis)
                    }
                warnings.append(
                    f"CSV contains {len(disabled_kpis)} disabled KPIs that will be filtered out"
                )
                warnings.append(f"Disabled KPIs: {list(disabled_kpis)}")
            
            # Calculate stats
            total_records = len(df)
            enabled_records = len(df[df['kpi_code'].isin(enabled_kpis)])
            filtered_records = total_records - enabled_records
            
            return {
                "valid": True,
                "enabled_kpis": len(enabled_kpis),
                "csv_kpis": len(csv_kpis),
                "disabled_kpis": list(disabled_kpis),
                "warnings": warnings,
                "will_filter": len(disabled_kpis) > 0,
                "details": {
                    "total_records": total_records,
                    "enabled_records": enabled_records,
                    "filtered_records": filtered_records,
                    "filter_percentage": f"{(filtered_records/total_records*100):.1f}%" if total_records > 0 else "0%"
                }
            }
            
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


def validate_kpi_csv_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    GAP 2.2: Validate KPI CSV structure (required columns, types, date format).
    Returns (True, []) if valid, (False, list of errors) otherwise.
    """
    errors = []
    required_cols = ['account_id', 'kpi_code', 'value']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return (False, [f"Missing required columns: {missing}"])
    has_date = 'measured_at' in df.columns or 'measurement_month' in df.columns
    if not has_date:
        errors.append("Missing required date column: 'measured_at' or 'measurement_month'")
    has_target = 'target' in df.columns or 'target_value' in df.columns
    if not has_target:
        errors.append("Missing required target column: 'target' or 'target_value'")
    if errors:
        return (False, errors)
    try:
        if 'value' in df.columns:
            pd.to_numeric(df['value'], errors='raise')
        if 'target' in df.columns:
            pd.to_numeric(df['target'], errors='raise')
        elif 'target_value' in df.columns:
            pd.to_numeric(df['target_value'], errors='raise')
        date_col = 'measured_at' if 'measured_at' in df.columns else 'measurement_month'
        pd.to_datetime(df[date_col], errors='raise')
    except Exception as e:
        errors.append(f"Invalid data types or date format: {e}")
        return (False, errors)
    return (True, [])


def _get_dc2s_kpi_valid_ranges():
    """Return dict kpi_code -> {min, max, name, unit} from DC2_S KPI definitions (union of healthy/risk/critical)."""
    try:
        from verticals.dc2_s.kpi_definitions import DC2S_KPIS
    except ImportError:
        return {}
    out = {}
    for kpi_code, defn in DC2S_KPIS.items():
        ranges = defn.get('ranges') or {}
        mins, maxs = [], []
        for band in ('healthy', 'risk', 'critical'):
            r = ranges.get(band, {})
            if isinstance(r.get('min'), (int, float)):
                mins.append(float(r['min']))
            if isinstance(r.get('max'), (int, float)):
                maxs.append(float(r['max']))
        if mins and maxs:
            out[kpi_code] = {'min': min(mins), 'max': max(maxs), 'name': defn.get('name', kpi_code), 'unit': defn.get('unit', '')}
    return out


def _normalize_kpi_code_for_range(kpi_code, valid_codes):
    """Map AI/CH/DV/EX/OS to P1-P5 for range lookup."""
    if kpi_code in valid_codes:
        return kpi_code
    if '-' in str(kpi_code):
        parts = str(kpi_code).split('-', 1)
        if len(parts) == 2 and parts[0] in ('AI', 'CH', 'DV', 'EX', 'OS'):
            catalog = {'AI': 'P3', 'CH': 'P4', 'DV': 'P1', 'EX': 'P5', 'OS': 'P2'}
            lookup = catalog.get(parts[0], '') + '-' + parts[1]
            if lookup in valid_codes:
                return lookup
    return None


def validate_kpi_values_against_ranges(df_kpis: pd.DataFrame) -> Tuple[List[Dict], List[str]]:
    """
    Validate KPI values against DC2_S reference ranges.
    Returns (errors, warnings). Each error: {account_id, kpi_code, value, expected_min, expected_max, kpi_name, unit}.
    """
    errors = []
    warnings = []
    if df_kpis.empty or 'value' not in df_kpis.columns or 'kpi_code' not in df_kpis.columns:
        return (errors, warnings)
    ranges_map = _get_dc2s_kpi_valid_ranges()
    if not ranges_map:
        return (errors, warnings)
    for idx, row in df_kpis.iterrows():
        try:
            val = float(row['value'])
        except (TypeError, ValueError):
            errors.append({
                'row_index': int(idx),
                'account_id': int(row.get('account_id', 0)),
                'kpi_code': str(row.get('kpi_code', '')),
                'value': str(row.get('value', '')),
                'expected_min': None,
                'expected_max': None,
                'kpi_name': str(row.get('kpi_code', '')),
                'unit': '',
                'message': 'Invalid numeric value'
            })
            continue
        kpi_code = str(row.get('kpi_code', ''))
        lookup = _normalize_kpi_code_for_range(kpi_code, ranges_map) or kpi_code
        r = ranges_map.get(lookup)
        if not r:
            continue
        lo, hi = r['min'], r['max']
        if val < lo or val > hi:
            errors.append({
                'row_index': int(idx),
                'account_id': int(row.get('account_id', 0)),
                'kpi_code': kpi_code,
                'value': val,
                'expected_min': lo,
                'expected_max': hi,
                'kpi_name': r.get('name', kpi_code),
                'unit': r.get('unit', ''),
                'message': f'Value {val} outside allowed range [{lo}, {hi}] {r.get("unit", "")}'
            })
    return (errors, warnings)


def filter_kpi_csv_by_config(df: pd.DataFrame, customer_id: int, strict_mode: bool = False) -> Tuple[pd.DataFrame, List[str]]:
    """
    GAP 2.1: Filter KPI DataFrame by dc2s_enabled_kpis. Returns (filtered_df, warnings).
    If strict_mode and any disabled KPIs present, raises; otherwise filters and warns.
    """
    with current_app.app_context():
        loader = ConfigLoader(customer_id)
        enabled_kpis = set(loader.get_enabled_kpis())
    csv_kpis = set(df['kpi_code'].unique())
    disabled = csv_kpis - enabled_kpis
    warnings = []
    if disabled:
        if strict_mode:
            raise ValueError(f"CSV contains disabled KPIs: {list(disabled)}. Enable them in config or remove from CSV.")
        warnings.append(f"Filtered out {len(disabled)} disabled KPIs: {list(disabled)[:10]}{'...' if len(disabled) > 10 else ''}")
        df = df[df['kpi_code'].isin(enabled_kpis)].copy()
    return (df, warnings)

# ============================================================================
# Onboarding Endpoints
# ============================================================================

@onboarding_api.route('/complete', methods=['POST'])
def complete_onboarding():
    """
    Complete onboarding flow - ENHANCED V2
    
    Creates customer, admin user, config, accounts, provisions directory, and generates CSV files.
    
    Request:
        {
            "customer_id": 19,                    // Optional: explicit ID (auto-generated if not provided)
            "customer_name": "DC2_S Demo Enterprise",
            "domain": "dc2s-demo.example.com",    // Optional: customer domain
            "industry": "Data Center Infrastructure",
            "vertical": "dc2_s",
            "email": "admin@dc2s-demo.example.com",
            "username": "dc2s_admin",             // Optional: admin username
            "password": "DemoPass123!",           // Optional: admin password
            "first_name": "Demo",                  // Optional: admin first name
            "last_name": "Administrator",         // Optional: admin last name
            "num_accounts": 10,                   // Optional: number of accounts (default: 3)
            "weights": {                          // Optional: custom pillar weights
                "AI": 0.10,
                "CH": 0.30,
                "DV": 0.30,
                "EX": 0.05,
                "OS": 0.25
            }
        }
    
    Response:
        {
            "success": true,
            "customer_id": 19,
            "customer_name": "DC2_S Demo Enterprise",
            "domain": "dc2s-demo.example.com",
            "accounts": 10,
            "account_details": [...],
            "account_id_range": "19001 - 19010",
            "user": {
                "user_id": 123,
                "email": "admin@dc2s-demo.example.com",
                "username": "dc2s_admin",
                "role": "admin"
            },
            "config": {
                "enabled_kpis": 15,
                "pillars": 5,
                "weights": {...},
                "vertical": "dc2_s"
            },
            "directory_provisioned": true,
            "csv_files_generated": true,
            "message": "Onboarding complete! Customer, user, config, accounts, and CSV files created."
        }
    """
    
    data = request.get_json() or {}
    
    # Extract all fields
    customer_id_explicit = data.get('customer_id')  # Optional explicit ID
    customer_name = data.get('customer_name')
    domain = data.get('domain')
    industry = data.get('industry', 'Technology')
    vertical = data.get('vertical', 'dc2_s')
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    num_accounts = data.get('num_accounts', 3)  # Default: 3 accounts
    custom_weights = data.get('weights')  # Optional custom pillar weights
    idempotent = data.get('idempotent', False)  # If True, return existing customer on duplicate
    onboarding_mode = data.get('onboarding_mode', 'demo')  # 'demo' (synthetic data) or 'custom' (user uploads CSVs)
    showcase_pattern_mix = data.get('showcase_pattern_mix')  # Optional: custom journey pattern distribution for demo mode
    
    if not customer_name:
        return jsonify({"error": "customer_name required"}), 400
    
    # GAP 1.6: Validate custom weights before proceeding
    if custom_weights:
        ok, err = validate_dc2s_pillar_weights(custom_weights)
        if not ok:
            return jsonify({"error": f"Invalid weights: {err}"}), 400
    
    try:
        # Step 0: Provision customer directory structure (if not exists)
        customer_dir = get_customer_directory(customer_id_explicit if customer_id_explicit else 0, vertical)
        directory_provisioned = False
        
        # If customer_id is provided, check if directory exists, otherwise provision after customer creation
        if not customer_id_explicit:
            # Will provision after customer_id is known
            pass
        elif not customer_dir.exists():
            # Provision directory for explicit customer_id
            try:
                from verticals.provision_dc_customer import provision_customer, TEMPLATE_DIR, BASE_DIR
                
                # Debug logging
                current_app.logger.info(f"Provisioning customer {customer_id_explicit}")
                current_app.logger.info(f"BASE_DIR: {BASE_DIR}")
                current_app.logger.info(f"TEMPLATE_DIR: {TEMPLATE_DIR}")
                current_app.logger.info(f"TEMPLATE_DIR exists: {TEMPLATE_DIR.exists()}")
                
                provision_success = provision_customer(
                    customer_id=customer_id_explicit,
                    customer_name=customer_name,
                    vertical_slug=vertical,
                    force=True  # Skip confirmation
                )
                if provision_success:
                    directory_provisioned = True
                    current_app.logger.info(f"✅ Provisioned directory for customer {customer_id_explicit}")
                    
                    # Verify scripts were created
                    scripts_dir = customer_dir / "scripts"
                    if scripts_dir.exists():
                        py_files = list(scripts_dir.glob("*.py"))
                        current_app.logger.info(f"✅ Created {len(py_files)} Python scripts")
                    else:
                        current_app.logger.warning(f"⚠️  Scripts directory not created for customer {customer_id_explicit}")
                else:
                    current_app.logger.warning(f"⚠️  Directory provisioning returned False for customer {customer_id_explicit}")
            except Exception as e:
                import traceback
                current_app.logger.error(f"❌ Could not provision directory: {e}")
                current_app.logger.error(traceback.format_exc())
                # Don't fail silently - this is a critical step
                raise
        
        # Step 1: Create customer (GAP 1.4: idempotency - return existing if idempotent=True)
        if customer_id_explicit:
            existing = db.session.get(Customer, customer_id_explicit)
            if existing:
                if idempotent:
                    # Return existing customer (idempotent success)
                    customer_dir = get_customer_directory(customer_id_explicit, vertical)
                    config = CustomerConfig.query.filter_by(customer_id=customer_id_explicit).first()
                    accounts = Account.query.filter_by(customer_id=customer_id_explicit).all()
                    return jsonify({
                        "success": True,
                        "customer_id": existing.customer_id,
                        "customer_name": existing.customer_name,
                        "idempotent": True,
                        "message": "Customer already exists (idempotent). Returning existing customer.",
                        "accounts": len(accounts),
                        "account_details": [{"account_id": a.account_id, "account_name": a.account_name} for a in accounts],
                        "config": {
                            "enabled_kpis": len(config.dc2s_enabled_kpis or []) if config else 0,
                            "weights": (config.dc2s_pillar_weights if config else None) or custom_weights or {},
                            "vertical": getattr(config, "vertical", None) or vertical
                        },
                        "directory_provisioned": customer_dir.exists() if customer_dir else False,
                    })
                return jsonify({
                    "error": f"Customer with ID {customer_id_explicit} already exists",
                    "existing_customer": existing.customer_name,
                    "hint": "Send idempotent=true to return existing customer instead of error"
                }), 400
        
        customer = Customer(customer_name=customer_name)
        if domain:
            customer.domain = domain
        if email:
            customer.email = email
        if customer_id_explicit:
            # Try to set explicit ID (may fail if ID already in use)
            try:
                customer.customer_id = customer_id_explicit
            except Exception as e:
                current_app.logger.warning(f"Could not set explicit customer_id: {e}")

        # UUID generation — resolve vertical to valid prefix (dc2_s → dc)
        uuid_vertical = 'dc' if vertical.startswith('dc') else vertical
        if uuid_vertical not in ('dc', 'saas', 'msp'):
            uuid_vertical = 'dc'  # Default to dc for data center verticals
        ensure_uuid(customer, uuid_vertical)

        db.session.add(customer)
        db.session.flush()  # Get customer_id

        customer_id = customer.customer_id
        customer_uuid_value = customer.uuid  # Save before session detach
        current_app.logger.info(f"✅ Customer created: id={customer_id}, uuid={customer_uuid_value}")
        
        # Provision directory if not already done
        if not directory_provisioned:
            customer_dir = get_customer_directory(customer_id, vertical)
            if not customer_dir.exists():
                try:
                    from verticals.provision_dc_customer import provision_customer, TEMPLATE_DIR, BASE_DIR
                    
                    # Debug logging
                    current_app.logger.info(f"Provisioning customer {customer_id}")
                    current_app.logger.info(f"BASE_DIR: {BASE_DIR}")
                    current_app.logger.info(f"TEMPLATE_DIR: {TEMPLATE_DIR}")
                    current_app.logger.info(f"TEMPLATE_DIR exists: {TEMPLATE_DIR.exists()}")
                    
                    provision_success = provision_customer(
                        customer_id=customer_id,
                        customer_name=customer_name,
                        vertical_slug=vertical,
                        force=True
                    )
                    if provision_success:
                        directory_provisioned = True
                        current_app.logger.info(f"✅ Provisioned directory for customer {customer_id}")
                        
                        # Verify scripts were created
                        scripts_dir = customer_dir / "scripts"
                        if scripts_dir.exists():
                            py_files = list(scripts_dir.glob("*.py"))
                            current_app.logger.info(f"✅ Created {len(py_files)} Python scripts")
                        else:
                            current_app.logger.warning(f"⚠️  Scripts directory not created for customer {customer_id}")
                except Exception as e:
                    import traceback
                    current_app.logger.error(f"❌ Could not provision directory: {e}")
                    current_app.logger.error(traceback.format_exc())
                    # Don't fail silently - this is a critical step
                    raise
        
        # Step 2: Create User record (if email/username provided)
        user_created = None
        if email or username:
            # Generate username if not provided
            if not username:
                username = email.split('@')[0] if email else f"admin_{customer_id}"
            
            # Ensure email is provided (required field)
            if not email:
                email = f"admin@{domain or f'customer{customer_id}.example.com'}"
            
            # Check if user already exists (by email or username)
            existing_user = User.query.filter_by(email=email).first()
            if not existing_user:
                existing_user = User.query.filter_by(
                    customer_id=customer_id,
                    user_name=username
                ).first()
            
            if not existing_user:
                try:
                    user = User(
                        customer_id=customer_id,
                        user_name=username,
                        email=email,
                        password_hash=generate_password_hash(password) if password else None,
                        role='admin',
                        vertical=vertical
                    )
                    ensure_uuid(user, uuid_vertical)
                    if hasattr(user, 'customer_uuid') and customer.uuid:
                        user.customer_uuid = customer.uuid
                    # Note: first_name and last_name not in User model, stored in profile_metadata if needed
                    db.session.add(user)
                    db.session.flush()
                    user_created = {
                        "user_id": user.user_id,
                        "email": user.email,
                        "username": user.user_name,
                        "role": user.role,
                        "created": True
                    }
                    current_app.logger.info(f"✅ Created admin user: {username} ({email})")
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"❌ Failed to create user: {e}", exc_info=True)
                    # Don't fail entire onboarding if user creation fails
                    user_created = {
                        "error": "User creation failed. Please try again or contact support.",
                        "created": False
                    }
            else:
                user_created = {
                    "user_id": existing_user.user_id,
                    "email": existing_user.email,
                    "username": existing_user.user_name,
                    "role": existing_user.role,
                    "created": False
                }
                current_app.logger.info(f"ℹ️  User {username} already exists")
        
        # Step 3: Create or Update CustomerConfig with default or custom settings
        # Default: Enable first 15 KPIs (3 per pillar)
        default_enabled_kpis = [
            'AI-KPI1', 'AI-KPI2', 'AI-KPI3',
            'CH-KPI1', 'CH-KPI2', 'CH-KPI3',
            'DV-KPI1', 'DV-KPI2', 'DV-KPI3',
            'EX-KPI1', 'EX-KPI2', 'EX-KPI3',
            'OS-KPI1', 'OS-KPI2', 'OS-KPI3'
        ]
        
        # Use custom weights if provided, otherwise defaults
        pillar_weights = custom_weights if custom_weights else {
            'AI': 0.25,
            'CH': 0.20,
            'DV': 0.15,
            'EX': 0.20,
            'OS': 0.20
        }
        
        # Check if config already exists (for idempotency)
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        
        if config:
            # Update existing config
            config.vertical = vertical
            config.dc2s_enabled_kpis = default_enabled_kpis
            config.dc2s_pillar_weights = pillar_weights
            current_app.logger.info(f"✅ Updated CustomerConfig for customer {customer_id}")
        else:
            # Create new config
            config = CustomerConfig(
                customer_id=customer_id,
                vertical=vertical,
                dc2s_enabled_kpis=default_enabled_kpis,
                dc2s_pillar_weights=pillar_weights
            )
            db.session.add(config)
            current_app.logger.info(f"✅ Created CustomerConfig for customer {customer_id}")
        
        # Step 4: Create N accounts (configurable, default: 3)
        # Check existing accounts to avoid duplicates (idempotency)
        existing_accounts = Account.query.filter_by(customer_id=customer_id).all()
        existing_account_ids = {acc.account_id for acc in existing_accounts}
        
        accounts_created = []
        base_account_id = customer_id * 1000  # Calculate base account ID
        
        # Account name patterns (use environment names for first 3, then numbered)
        account_envs = ['Production', 'Staging', 'Development', 'Environment', 'Workspace', 'Cluster', 'Instance', 'Node', 'Server', 'System']
        
        for i in range(num_accounts):
            # Use environment name for first few, then numbered
            if i < len(account_envs):
                account_name = f"{customer_name}-{account_envs[i]}"
            else:
                account_name = f"{customer_name}-Account-{i+1}"
            
            # Account ID: (customer_id * 1000) + 1, +2, +3, etc.
            account_id = base_account_id + i + 1
            
            # Check if account already exists (idempotency)
            if account_id in existing_account_ids:
                # Account exists, update it
                account = db.session.get(Account, account_id)
                account.account_name = account_name
                account.industry = industry
                account.vertical = vertical
                current_app.logger.info(f"ℹ️  Updated existing account {account_id}")
            else:
                # Create new account with UUID
                account = Account(
                    account_id=account_id,
                    customer_id=customer_id,
                    account_name=account_name,
                    industry=industry,
                    vertical=vertical,
                    region='us-west-2',
                    account_status='active'
                )
                ensure_uuid(account, uuid_vertical)
                ensure_customer_uuid_on_account(account, customer)
                db.session.add(account)
                current_app.logger.info(f"✅ Created new account {account_id} (uuid={account.uuid})")
            
            db.session.flush()
            accounts_created.append({
                "account_id": account.account_id,
                "account_name": account.account_name
            })
        
        # ====================================================================
        # GAP 1.1 FIX: Config MUST be committed BEFORE CSV generation so the
        # generator (subprocess) can load CustomerConfig via ConfigLoader.
        # ====================================================================
        try:
            db.session.flush()
            current_app.logger.info("🔍 Flushed changes to database")
            
            # Query in same session before commit
            accounts_in_session = Account.query.filter_by(customer_id=customer_id).count()
            current_app.logger.info(f"  Accounts in current session (before commit): {accounts_in_session}")
            
            # Commit transaction
            db.session.commit()  # Commit transaction
            current_app.logger.info("✅ Transaction committed")
            
            # Force expire to clear cache
            db.session.expire_all()
            accounts_after_expire = Account.query.filter_by(customer_id=customer_id).count()
            current_app.logger.info(f"  Accounts after expire_all: {accounts_after_expire}")
            
            # Verify accounts are actually in database using raw SQL
            from sqlalchemy import text
            verification_count = db.session.execute(
                text("SELECT COUNT(*) FROM accounts WHERE customer_id = :cid"),
                {"cid": customer_id}
            ).scalar()
            current_app.logger.info(f"🔍 Verification (raw SQL): {verification_count} accounts in database")
            
            if verification_count != num_accounts:
                current_app.logger.error(f"❌ Expected {num_accounts} accounts, found {verification_count}")
                db.session.rollback()
                return jsonify({
                    "error": "Account creation verification failed",
                    "expected": num_accounts,
                    "found": verification_count
                }), 500
            
            # Remove session to force new queries in subsequent requests
            db.session.remove()
            current_app.logger.info("✅ Session removed - subsequent queries will use fresh connection")
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Commit failed: {e}")
            import traceback
            current_app.logger.error(traceback.format_exc())
            return jsonify({"error": "Transaction commit failed. Please try again or contact support."}), 500
        
        # Calculate account ID range
        if accounts_created:
            account_id_start = accounts_created[0]['account_id']
            account_id_end = accounts_created[-1]['account_id']
            account_id_range = f"{account_id_start} - {account_id_end}"
        else:
            account_id_range = "N/A"
        
        # Step 5: Generate config-aware CSV files (Demo mode only)
        # In 'custom' mode, user uploads their own CSVs via /upload endpoint
        csv_files_generated = False
        backend_dir = Path(__file__).parent

        if onboarding_mode == 'custom':
            current_app.logger.info(f"Custom mode: skipping CSV generation. User will upload CSVs via /api/onboarding/upload.")
            # Ensure data directory exists for later uploads
            data_dir = get_customer_directory(customer_id) / 'data'
            data_dir.mkdir(parents=True, exist_ok=True)

        # Try generate_synthetic_customer_data.py first (preferred)
        generator_script = backend_dir / 'scripts' / 'generate_synthetic_customer_data.py'

        # Fallback to generate_synthetic_dc2s_data.py if preferred doesn't exist
        if not generator_script.exists():
            generator_script = backend_dir / 'scripts' / 'generate_synthetic_dc2s_data.py'

        if onboarding_mode != 'custom' and generator_script.exists():
            # Build command for new config-aware generator
            data_dir = Path(f'verticals/customer{customer_id}-dc2_s/data')
            cmd = [
                'python3',
                str(generator_script),
                '--customer-id', str(customer_id),
                '--output-dir', str(data_dir),
                '--company-name', customer_name,
                '--num-accounts', str(num_accounts),
                '--num-months', '12'
            ]
            
            # Add journey-patterns if script supports it (check script name)
            if 'generate_synthetic_customer_data.py' in str(generator_script):
                cmd.extend(['--journey-patterns', 'DEMO_MANIFEST'])
            
            current_app.logger.info(f"Running generator: {' '.join(cmd)}")
            # Run from backend dir so output-dir verticals/... resolves correctly
            result = subprocess.run(
                cmd,
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                csv_files_generated = True
                current_app.logger.info(f"✅ Generated CSV files for customer {customer_id}")
                # Verify CSV files were created with correct account IDs
                data_dir = Path(f'verticals/customer{customer_id}-dc2_s/data')
                kpi_file = data_dir / 'kpi_measurements.csv'
                if kpi_file.exists():
                    import pandas as pd
                    df = pd.read_csv(kpi_file, nrows=100)  # Read more rows to verify account IDs
                    if 'account_id' in df.columns:
                        unique_account_ids = sorted(df['account_id'].unique())
                        current_app.logger.info(f"🔍 CSV verification: Found account IDs {unique_account_ids[:5]}... in kpi_measurements.csv")
                        # Verify against accounts_created
                        if accounts_created:
                            expected_ids = sorted([acc['account_id'] for acc in accounts_created])
                            found_ids = unique_account_ids[:len(expected_ids)]
                            if set(found_ids) != set(expected_ids):
                                current_app.logger.warning(f"⚠️  Account ID mismatch! Expected {expected_ids[:5]}..., found {found_ids[:5]}...")
                            else:
                                current_app.logger.info(f"✅ Account IDs verified: {len(expected_ids)} accounts match")
                else:
                    current_app.logger.warning(f"⚠️  kpi_measurements.csv not found after generation!")
            else:
                current_app.logger.warning(f"⚠️  Data generation had issues: {result.stderr}")
                current_app.logger.warning(f"⚠️  Generator stdout: {result.stdout}")
                # GAP 1.5: Partial success - customer/config/accounts created, CSVs not generated
        else:
            current_app.logger.warning(f"⚠️  Data generator script not found: {generator_script}")
        
        # Build enhanced response (GAP 1.5: partial success when csv_files_generated is False)
        if onboarding_mode == 'custom':
            message = "Customer, user, config, and accounts created. Upload your CSV files via /api/onboarding/upload, then call /api/onboarding/process-data."
        elif csv_files_generated:
            message = "Onboarding complete! Customer, user, config, accounts, and demo CSV files created."
        else:
            message = "Customer, user, config, and accounts created. CSV generation failed; upload CSVs via /api/onboarding/upload."

        # Enrich account_details with UUIDs (re-query since session was removed)
        enriched_accounts = []
        for acct_info in accounts_created:
            acct_obj = db.session.get(Account, acct_info['account_id'])
            entry = dict(acct_info)
            if acct_obj and getattr(acct_obj, 'uuid', None):
                entry['uuid'] = acct_obj.uuid
            enriched_accounts.append(entry)

        response_data = {
            "success": True,
            "customer_id": customer_id,
            "customer_uuid": customer_uuid_value,
            "customer_name": customer_name,
            "onboarding_mode": onboarding_mode,
            "accounts": len(accounts_created),
            "account_details": enriched_accounts,
            "account_id_range": account_id_range,
            "config": {
                "enabled_kpis": len(default_enabled_kpis),
                "pillars": 5,
                "weights": pillar_weights,
                "vertical": vertical
            },
            "directory_provisioned": directory_provisioned,
            "csv_files_generated": csv_files_generated,
            "message": message
        }
        if onboarding_mode == 'custom':
            response_data["next_step"] = "Upload CSVs via POST /api/onboarding/upload, then POST /api/onboarding/process-data"
        elif not csv_files_generated:
            response_data["warnings"] = ["CSV files were not generated; upload CSVs via /api/onboarding/upload and run process-data."]
        if showcase_pattern_mix:
            response_data["showcase_pattern_mix"] = showcase_pattern_mix
        
        # Add domain if provided
        if domain:
            response_data["domain"] = domain
        
        # Add user info if created
        if user_created:
            response_data["user"] = user_created
        
        return jsonify(response_data)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Onboarding complete failed: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Onboarding failed. Please try again or contact support."
        }), 500

@onboarding_api.route('/process-data', methods=['POST'])
def process_data():
    """
    Process uploaded CSV data - ENHANCED V2 with all steps
    
    Executes in order:
    1. Data Loading - Reads CSVs from customer data dir (saved by upload endpoint) and loads into PostgreSQL (dc2s_kpis, qualitative_signals). No 02_load/02_upload scripts.
    2. Embedding Generation (03_embed_*.py) - PostgreSQL → Qdrant
    3. Data Validation (04_validate_*.py) - Optional integrity checks
    4. Journey Generation (wizard_a_*.py) - Creates journey JSON files
    5. Pattern Analysis (wizard_b_*.py) - Optional pattern detection
    6. Weight Calibration (wizard_c_*.py) - Optional self-learning weights
    
    Request:
        {
            "customer_id": 123,
            "skip_validation": false,    // Optional: skip validation script
            "skip_wizard_b": true,       // Optional: skip Wizard B
            "skip_wizard_c": false,      // Optional: skip Wizard C (default: run it)
            "upload_mode": "incremental" // Optional: full_refresh, incremental, upsert, merge
        }
    
    Response:
        {
            "status": "success",
            "message": "Data processing completed successfully",
            "customer_id": 123,
            "steps_completed": [
                "data_loading",
                "embeddings",
                "validation",
                "journey_generation",
                "weight_calibration"
            ],
            "errors": [],
            "validation": {...}
        }
    """
    
    data = request.get_json() or {}
    customer_id = data.get('customer_id')
    
    if not customer_id:
        return jsonify({"status": "error", "message": "customer_id required"}), 400
    
    try:
        customer_id = int(customer_id)
        skip_validation = data.get('skip_validation', False)
        skip_wizard_b = data.get('skip_wizard_b', True)  # Default: skip Wizard B
        skip_wizard_c = data.get('skip_wizard_c', False)  # Default: run Wizard C
        upload_mode = data.get('upload_mode', 'incremental')
        strict_mode = data.get('strict_mode', False)  # P2: Strict CSV validation mode
        pattern_mix = data.get('pattern_mix')  # P1: Configurable pattern mix
        onboarding_mode = data.get('onboarding_mode', 'demo')  # 'demo' or 'custom'

        # Demo Showcase: use a pattern mix that demonstrates the core value prop
        # - crisis→recovery→expansion (proactive CSM saves the account)
        # - crisis→churn (what happens without intervention)
        # - stable accounts for baseline comparison
        DEMO_SHOWCASE_PATTERN_MIX = '{"crisis":0.30,"churn":0.20,"stable":0.25,"expansion":0.25}'
        if onboarding_mode == 'demo' and not pattern_mix:
            pattern_mix = data.get('showcase_pattern_mix', DEMO_SHOWCASE_PATTERN_MIX)
        
        # P0: Check customer exists in database
        # Refresh session to ensure we see committed data (important for test environments)
        db.session.expire_all()
        customer = db.session.get(Customer, customer_id)
        if not customer:
            return jsonify({
                "status": "error",
                "message": f"Customer {customer_id} not found in database"
            }), 404
        
        # Get customer directory
        customer_dir = get_customer_directory(customer_id)
        if not customer_dir.exists():
            return jsonify({
                "status": "error",
                "message": f"Customer directory not found. Please provision first: POST /api/onboarding/provision"
            }), 404
        
        # Check if data directory exists and has files
        data_dir = customer_dir / "data"
        if not data_dir.exists():
            return jsonify({
                "status": "error",
                "message": "Data directory not found. Please upload files first."
            }), 404
        
        # Check for required files
        required_files = ['accounts.csv', 'kpi_measurements.csv']
        missing_files = [f for f in required_files if not (data_dir / f).exists()]
        if missing_files:
            return jsonify({
                "status": "error",
                "message": f"Missing required files: {', '.join(missing_files)}"
            }), 400
        
        # Track execution state (GAP 3.5) and progress (GAP 3.8)
        execution_state = {
            'customer_id': customer_id,
            'steps_completed': [],
            'errors': [],
            'rollback_needed': False,
            'upload_mode': upload_mode
        }
        wizard_c_config_changes = None  # GAP 3.4: set when Wizard C updates pillar weights
        _onboarding_progress[customer_id] = {
            'in_progress': True,
            'current_step': 'starting',
            'steps_completed': [],
            'started_at': datetime.utcnow().isoformat() if hasattr(datetime, 'utcnow') else datetime.now().isoformat(),
        }
        
        # Validate KPI measurements against config
        kpi_file = data_dir / 'kpi_measurements.csv'
        validation_result = {"valid": True, "warnings": []}
        if kpi_file.exists():
            validation_result = validate_csv_against_config(customer_id, kpi_file, strict_mode=strict_mode)
            if not validation_result['valid']:
                return jsonify({
                    "status": "error",
                    "error": "CSV validation failed",
                    "validation": validation_result
                }), 400
        
        # ========================================================================
        # STEP 1: Data Loading - Direct CSV to Database (dc2s_kpis)
        # ========================================================================
        current_app.logger.info(f"Step 1: Loading CSV data directly into database for customer {customer_id}")
        
        # P2: Progress tracking (log step start for UI monitoring)
        current_app.logger.info(f"📊 PROCESS_DATA_START: customer_id={customer_id}, steps=[data_loading, embeddings, validation, journey_generation, pattern_analysis, weight_calibration]")
        
        script_start_time = time.time()
        
        try:
            import pandas as pd
            from sqlalchemy import create_engine, text
            from dotenv import load_dotenv
            import os
            
            load_dotenv()
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL not set")
            
            engine = create_engine(database_url)
            
            # ---------------------------------------------------------------------
            # Load accounts.csv → accounts (so ARR, revenue, profile can be populated)
            # ---------------------------------------------------------------------
            accounts_file = data_dir / 'accounts.csv'
            if accounts_file.exists():
                current_app.logger.info(f"Loading {accounts_file} into accounts table...")
                df_acc = pd.read_csv(accounts_file)
                df_acc['customer_id'] = customer_id  # tenant isolation
                if 'account_id' not in df_acc.columns or 'account_name' not in df_acc.columns:
                    current_app.logger.warning("accounts.csv missing account_id or account_name; skipping")
                else:
                    # Default vertical for DC onboarding so /api/dc2s/accounts returns these accounts
                    with current_app.app_context():
                        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
                        default_vertical = (getattr(config, 'vertical', None) or 'dc2_s') if config else 'dc2_s'
                    # Standard Account columns; extra columns (ARR, csm_name, champion_name) → profile_metadata JSON
                    standard = {'account_id', 'customer_id', 'account_name', 'revenue', 'account_status', 'industry', 'vertical', 'region', 'external_account_id'}
                    extra_cols = [c for c in df_acc.columns if c not in standard and c != 'created_at']
                    with engine.begin() as conn:
                        for _, row in df_acc.iterrows():
                            aid = int(row['account_id'])
                            profile_meta = None
                            if extra_cols:
                                profile_meta = {k: (float(row[k]) if isinstance(row.get(k), (int, float)) and pd.notna(row.get(k)) else str(row[k])) for k in extra_cols if k in row.index and pd.notna(row.get(k))}
                            existing = conn.execute(text("SELECT 1 FROM accounts WHERE account_id = :aid"), {"aid": aid}).scalar()
                            rev = float(row['revenue']) if 'revenue' in row and pd.notna(row.get('revenue')) else 0
                            vertical_val = str(row.get('vertical')) if (row.get('vertical') is not None and pd.notna(row.get('vertical'))) else default_vertical
                            if existing:
                                conn.execute(text("""
                                    UPDATE accounts SET customer_id=:cid, account_name=:name, revenue=:rev, account_status=COALESCE(:status,'active'),
                                    industry=:industry, vertical=:vertical, region=:region, external_account_id=:ext_id, profile_metadata=:meta
                                    WHERE account_id=:aid
                                """), {"cid": customer_id, "name": str(row.get('account_name', f'Account {aid}')), "rev": rev,
                                       "status": str(row.get('account_status')) if pd.notna(row.get('account_status')) else None,
                                       "industry": str(row.get('industry')) if pd.notna(row.get('industry')) else None,
                                       "vertical": vertical_val,
                                       "region": str(row.get('region')) if pd.notna(row.get('region')) else None,
                                       "ext_id": str(row['external_account_id']) if row.get('external_account_id') and pd.notna(row.get('external_account_id')) else None,
                                       "meta": json.dumps(profile_meta) if profile_meta else None, "aid": aid})
                            else:
                                conn.execute(text("""
                                    INSERT INTO accounts (account_id, customer_id, account_name, revenue, account_status, industry, vertical, region, external_account_id, profile_metadata)
                                    VALUES (:aid, :cid, :name, :rev, COALESCE(:status,'active'), :industry, :vertical, :region, :ext_id, :meta)
                                """), {"aid": aid, "cid": customer_id, "name": str(row.get('account_name', f'Account {aid}')), "rev": rev,
                                       "status": str(row.get('account_status')) if pd.notna(row.get('account_status')) else None,
                                       "industry": str(row.get('industry')) if pd.notna(row.get('industry')) else None,
                                       "vertical": vertical_val,
                                       "region": str(row.get('region')) if pd.notna(row.get('region')) else None,
                                       "ext_id": str(row['external_account_id']) if row.get('external_account_id') and pd.notna(row.get('external_account_id')) else None,
                                       "meta": json.dumps(profile_meta) if profile_meta else None})
                    current_app.logger.info(f"✅ Loaded/updated {len(df_acc)} account records (vertical={default_vertical})")
            
            # Load KPI measurements into dc2s_kpis table (GAP 3.1: filter by enabled_kpis)
            kpi_file = data_dir / 'kpi_measurements.csv'
            if kpi_file.exists():
                current_app.logger.info(f"Loading {kpi_file} into dc2s_kpis table...")
                df_kpis = pd.read_csv(kpi_file)
                current_app.logger.info(f"  Read {len(df_kpis)} rows from CSV")
                with current_app.app_context():
                    loader = ConfigLoader(customer_id)
                    enabled_kpis = set(loader.get_enabled_kpis())
                before_filter = len(df_kpis)
                df_kpis = df_kpis[df_kpis['kpi_code'].isin(enabled_kpis)]
                filtered_out = before_filter - len(df_kpis)
                if filtered_out:
                    current_app.logger.info(f"  Config-aware: filtered to enabled KPIs only; dropped {filtered_out} rows")
                # Validate KPI values against reference ranges (DC2_S); block load if out-of-range and strict
                strict_kpi_ranges = data.get('strict_kpi_ranges', True)
                kpi_range_errors, kpi_range_warnings = validate_kpi_values_against_ranges(df_kpis)
                if kpi_range_errors and strict_kpi_ranges:
                    current_app.logger.warning(f"  KPI range validation failed: {len(kpi_range_errors)} value(s) outside allowed ranges")
                    return jsonify({
                        "status": "validation_failed",
                        "error": "KPI values outside allowed reference ranges",
                        "message": "Some KPI values do not agree with defined ranges. Fix the data or set strict_kpi_ranges=false to load anyway.",
                        "customer_id": customer_id,
                        "kpi_range_errors": kpi_range_errors[:100],
                        "kpi_range_errors_count": len(kpi_range_errors)
                    }), 400
                if kpi_range_errors:
                    current_app.logger.info(f"  KPI range warnings (load allowed): {len(kpi_range_errors)} value(s) outside ranges")
                current_app.logger.info(f"  Loading {len(df_kpis)} KPI records (enabled KPIs only)")
                with engine.begin() as conn:
                    # Idempotent: delete existing dc2s_kpis for this customer's accounts
                    conn.execute(text("""
                        DELETE FROM dc2s_kpis WHERE account_id IN
                        (SELECT account_id FROM accounts WHERE customer_id = :cid)
                    """), {"cid": customer_id})
                    df_kpis.to_sql(
                        'dc2s_kpis',
                        conn,
                        if_exists='append',
                        index=False,
                        method='multi',
                        chunksize=1000
                    )
                current_app.logger.info(f"✅ Loaded {len(df_kpis)} KPI records into dc2s_kpis")
            
            # Load qualitative signals
            signals_file = data_dir / 'qualitative_signals.csv'
            if signals_file.exists():
                current_app.logger.info(f"Loading {signals_file} into qualitative_signals table...")
                df_signals = pd.read_csv(signals_file)
                current_app.logger.info(f"  Read {len(df_signals)} rows from CSV")
                with engine.begin() as conn:
                    # Idempotent: delete existing qualitative_signals for this customer's accounts
                    conn.execute(text("""
                        DELETE FROM qualitative_signals WHERE account_id IN
                        (SELECT account_id FROM accounts WHERE customer_id = :cid)
                    """), {"cid": customer_id})
                    df_signals.to_sql(
                        'qualitative_signals',
                        conn,
                        if_exists='append',
                        index=False,
                        method='multi',
                        chunksize=1000
                    )
                current_app.logger.info(f"✅ Loaded {len(df_signals)} signal records into qualitative_signals")
            
            # ---------------------------------------------------------------------
            # Load products.csv → products (product_name, product_sku, etc.)
            # ---------------------------------------------------------------------
            products_file = data_dir / 'products.csv'
            if products_file.exists():
                current_app.logger.info(f"Loading {products_file} into products table...")
                df_prod = pd.read_csv(products_file)
                df_prod['customer_id'] = customer_id
                if 'product_name' not in df_prod.columns:
                    current_app.logger.warning("products.csv missing product_name; skipping")
                else:
                    # Product model requires account_id; if missing, assign first account of customer
                    if 'account_id' not in df_prod.columns or df_prod['account_id'].isna().all():
                        with engine.begin() as conn:
                            first_acc = conn.execute(text("SELECT account_id FROM accounts WHERE customer_id = :cid ORDER BY account_id LIMIT 1"), {"cid": customer_id}).scalar()
                            if first_acc:
                                df_prod['account_id'] = first_acc
                                current_app.logger.info(f"  Assigned products to account_id={first_acc} (no account_id in CSV)")
                            else:
                                current_app.logger.warning("  No accounts for customer; skipping products load")
                                df_prod = pd.DataFrame()
                    if not df_prod.empty and 'account_id' in df_prod.columns:
                        cols = [c for c in df_prod.columns if c in ('product_id', 'account_id', 'customer_id', 'product_name', 'product_sku', 'product_type', 'revenue', 'status')]
                        df_prod = df_prod[cols] if cols else df_prod
                        with engine.begin() as conn:
                            # Idempotent: delete existing products for this customer to avoid duplicate key (product_id is global PK)
                            conn.execute(text("DELETE FROM products WHERE customer_id = :cid"), {"cid": customer_id})
                            df_prod.to_sql('products', conn, if_exists='append', index=False, method='multi', chunksize=500)
                        current_app.logger.info(f"✅ Loaded {len(df_prod)} product records")
            
            # ---------------------------------------------------------------------
            # Load profiles.csv or account_profiles.csv → account_profiles (ARR, CSM, Champion, etc.)
            # ---------------------------------------------------------------------
            profiles_file = data_dir / 'account_profiles.csv'
            if not profiles_file.exists():
                profiles_file = data_dir / 'profiles.csv'
            if profiles_file.exists():
                current_app.logger.info(f"Loading {profiles_file} into account_profiles table...")
                try:
                    df_prof = pd.read_csv(profiles_file)
                    df_prof['customer_id'] = customer_id
                    # Check if account_profiles table exists
                    with engine.begin() as conn:
                        has_table = conn.execute(text("""
                            SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'account_profiles'
                        """)).scalar()
                    if has_table:
                        df_prof.to_sql('account_profiles', engine, if_exists='append', index=False, method='multi', chunksize=500)
                        current_app.logger.info(f"✅ Loaded {len(df_prof)} account profile records (ARR, CSM, Champion, etc.)")
                    else:
                        # No account_profiles table: store key profile fields in accounts.profile_metadata
                        if 'account_id' in df_prof.columns:
                            profile_cols = [c for c in df_prof.columns if c not in ('account_id', 'customer_id')]
                            with engine.begin() as conn:
                                for _, row in df_prof.iterrows():
                                    aid = row.get('account_id')
                                    if pd.isna(aid):
                                        continue
                                    aid = int(aid)
                                    meta = {k: (float(row[k]) if isinstance(row.get(k), (int, float)) and pd.notna(row.get(k)) else str(row[k])) for k in profile_cols if k in row.index and pd.notna(row.get(k))}
                                    if meta:
                                        conn.execute(text("UPDATE accounts SET profile_metadata = :meta WHERE account_id = :aid"), {"meta": json.dumps(meta), "aid": aid})
                            current_app.logger.info(f"✅ Stored {len(df_prof)} account profiles in accounts.profile_metadata")
                except Exception as e:
                    current_app.logger.warning(f"Could not load profiles: {e}")
            
            script_duration = time.time() - script_start_time
            execution_state['steps_completed'].append('data_loading')
            if customer_id in _onboarding_progress:
                _onboarding_progress[customer_id]['current_step'] = 'data_loading'
                _onboarding_progress[customer_id]['steps_completed'] = list(execution_state['steps_completed'])
            current_app.logger.info(f"✅ Data loading completed in {script_duration:.2f}s")
            
        except Exception as e:
            if customer_id in _onboarding_progress:
                _onboarding_progress[customer_id]['in_progress'] = False
            script_duration = time.time() - script_start_time
            current_app.logger.error(f"Data loading failed: {str(e)}", exc_info=True)
            execution_state['errors'].append("Data loading failed")
            execution_state['rollback_needed'] = True
            return jsonify({
                "status": "error",
                "message": "Data loading failed. Please try again or contact support.",
                **execution_state
            }), 500
        
        # ========================================================================
        # STEP 2: Embedding Generation Script
        # ========================================================================
        current_app.logger.info(f"Step 2: Executing embedding script for customer {customer_id}")
        embed_script = customer_dir / "scripts" / f"03_embed_customer{customer_id}_OPENAI.py"
        
        if not embed_script.exists():
            # Try alternative location or use API-based embedding
            current_app.logger.warning(f"Embedding script not found: {embed_script}")
            current_app.logger.info("Attempting to build knowledge base via API...")
            
            # Use enhanced_rag_qdrant API to build knowledge base
            try:
                from enhanced_rag_qdrant import get_qdrant_rag_system
                with current_app.app_context():
                    rag_system = get_qdrant_rag_system()
                    if rag_system and not rag_system.qdrant_bypassed:
                        rag_system.customer_id = customer_id
                        rag_system.build_knowledge_base(customer_id)
                        execution_state['steps_completed'].append('embeddings')
                        current_app.logger.info("✅ Knowledge base built via API")
                    else:
                        execution_state['errors'].append("Qdrant not available - embedding step skipped")
                        current_app.logger.warning("⚠️  Qdrant not available, skipping embedding step")
            except Exception as e:
                execution_state['errors'].append("Embedding via API failed")
                current_app.logger.warning(f"⚠️  Embedding failed: {e}")
        else:
            script_start_time = time.time()
            # P2: Propagate upload_mode to embedding script if needed
            env_vars = {'UPLOAD_MODE': upload_mode} if upload_mode else {}
            success, stdout, stderr = execute_script(embed_script, customer_id, timeout=600, env=env_vars)
            script_duration = time.time() - script_start_time
            
            if not success:
                execution_state['errors'].append(f"Embedding failed: {stderr}")
                execution_state['rollback_needed'] = True
                return jsonify({
                    "status": "error",
                    "message": "Embedding script failed",
                    "error": stderr,
                    **execution_state
                }), 500
            
            execution_state['steps_completed'].append('embeddings')
            current_app.logger.info(f"✅ Embeddings created in {script_duration:.2f}s")
        
        # ========================================================================
        # STEP 3: Data Validation Script (Optional)
        # ========================================================================
        if not skip_validation:
            current_app.logger.info(f"Step 3: Executing validation script for customer {customer_id}")
            validate_script = customer_dir / "scripts" / "04_validate_data_integrity.py"
            
            if validate_script.exists():
                script_start_time = time.time()
                success, stdout, stderr = execute_script(validate_script, customer_id, timeout=300)
                script_duration = time.time() - script_start_time
                
                if not success:
                    execution_state['errors'].append(f"Validation warnings: {stderr}")
                    current_app.logger.warning(f"Validation script returned warnings: {stderr}")
                else:
                    execution_state['steps_completed'].append('validation')
                    current_app.logger.info(f"✅ Validation completed in {script_duration:.2f}s")
        
        # ========================================================================
        # STEP 4: Journey Generation (Wizard A)
        # ========================================================================
        current_app.logger.info(f"Step 4: Executing journey generator for customer {customer_id}")
        journey_script = customer_dir / "journey" / "wizard_a" / "wizard_journey_generator.py"
        
        if not journey_script.exists():
            journey_script = customer_dir / "journey" / "wizard_a" / "wizard_a_journey_generator.py"
        
        if not journey_script.exists():
            execution_state['errors'].append(f"Journey generator script not found")
            current_app.logger.warning(f"Journey generator script not found - skipping")
        else:
            # Get account count and start ID for Wizard A arguments
            # Check if account_ids were passed in request (for test environments)
            account_ids_from_request = data.get('account_ids')
            if account_ids_from_request:
                # Use account IDs from request (bypasses session isolation in tests)
                current_app.logger.info(f"Using account_ids from request: {len(account_ids_from_request)} accounts")
                accounts = Account.query.filter(Account.account_id.in_(account_ids_from_request)).all()
                account_count = len(accounts)
                if account_count == 0:
                    # Fallback: create minimal account objects from IDs
                    current_app.logger.warning("Account IDs provided but ORM query returned 0, using provided IDs")
                    accounts = [type('Account', (), {'account_id': aid})() for aid in account_ids_from_request]
                    account_count = len(accounts)
            else:
                # Normal flow: query accounts from database
                # Add small delay to ensure database transaction is fully committed (timing issue fix)
                time.sleep(0.5)  # Small delay for transaction propagation
                
                # Force session refresh to see committed data
                db.session.expire_all()
                db.session.commit()  # Ensure we're reading from committed state
                
                # Use raw SQL query to bypass SQLAlchemy session isolation (critical for Flask test client)
                from sqlalchemy import text
                try:
                    result = db.session.execute(
                        text("SELECT account_id, account_name FROM accounts WHERE customer_id = :customer_id"),
                        {"customer_id": customer_id}
                    )
                    account_rows = result.fetchall()
                    account_count = len(account_rows)
                    
                    # Convert to Account objects for compatibility
                    if account_count > 0:
                        account_ids = [row[0] for row in account_rows]
                        accounts = Account.query.filter(Account.account_id.in_(account_ids)).all()
                        # If ORM query fails, create minimal objects
                        if len(accounts) != account_count:
                            accounts = [type('Account', (), {'account_id': row[0], 'account_name': row[1]})() for row in account_rows]
                    else:
                        accounts = []
                except Exception as e:
                    current_app.logger.warning(f"Raw SQL query failed, falling back to ORM: {e}")
                    # Fallback to ORM query
                    db.session.expire_all()
                    accounts = Account.query.filter_by(customer_id=customer_id).all()
                    account_count = len(accounts)
            
            current_app.logger.info(f"Found {account_count} accounts for customer {customer_id}")
            if account_count > 0:
                current_app.logger.info(f"Account IDs: {[acc.account_id for acc in accounts[:5]]}")
            else:
                # Debug: Check if customer exists and verify account query
                customer = db.session.get(Customer, customer_id)
                if customer:
                    current_app.logger.warning(f"Customer {customer_id} exists but query found 0 accounts")
                    # Try querying all accounts to see if any exist
                    all_accounts = Account.query.all()
                    current_app.logger.warning(f"Total accounts in DB: {len(all_accounts)}")
                    if all_accounts:
                        sample_customer_ids = [acc.customer_id for acc in all_accounts[:10]]
                        current_app.logger.warning(f"Sample account customer_ids: {sample_customer_ids}")
                        # Check if any match our customer_id
                        matching = [cid for cid in sample_customer_ids if cid == customer_id]
                        if matching:
                            current_app.logger.error(f"⚠️ Found {len(matching)} accounts with customer_id={customer_id} but query returned 0!")
            
        wizard_a_output_dir = None  # Set when Wizard A runs; used as Wizard B run dir
        if account_count == 0:
            execution_state['errors'].append(f"No accounts found for customer {customer_id}. Cannot run Wizard A.")
            current_app.logger.warning("No accounts found - skipping journey generation")
        else:
            # Get first account ID as start_id
            start_id = accounts[0].account_id if accounts else customer_id * 1000 + 1
            
            # P1: Make pattern_mix configurable in request
            if not pattern_mix:
                pattern_mix = '{"crisis":0.2,"churn":0.15,"stable":0.4,"expansion":0.25}'
            
            # Output directory
            output_dir = str(journey_script.parent / "outputs")
            wizard_a_output_dir = output_dir
            
            # Build additional arguments for Wizard A
            additional_args = [
                '--accounts', str(account_count),
                '--start-id', str(start_id),
                '--pattern-mix', pattern_mix,
                '--output-dir', output_dir
            ]
            
            script_start_time = time.time()
            success, stdout, stderr = execute_script(journey_script, customer_id, timeout=600, additional_args=additional_args)
            script_duration = time.time() - script_start_time
            
            if not success:
                execution_state['errors'].append(f"Journey generation failed: {stderr}")
                current_app.logger.warning(f"Journey generation failed: {stderr}")
            else:
                execution_state['steps_completed'].append('journey_generation')
                current_app.logger.info(f"✅ Journey data generated in {script_duration:.2f}s")
        
        # ========================================================================
        # STEP 5: Pattern Analysis (Wizard B) - Optional
        # ========================================================================
        if not skip_wizard_b and wizard_a_output_dir:
            current_app.logger.info(f"Step 5: Executing pattern analyzer (Wizard B) for customer {customer_id}")
            # P1: Add script name variations for Wizard B
            wizard_b_script = customer_dir / "journey" / "wizard_b" / "wizard_b_pattern_analyzer.py"
            
            if not wizard_b_script.exists():
                wizard_b_script = customer_dir / "journey" / "wizard_b" / "pattern_analyzer.py"
            
            if wizard_b_script.exists():
                script_start_time = time.time()
                success, stdout, stderr = execute_script(
                    wizard_b_script, customer_id, timeout=300,
                    additional_args=[wizard_a_output_dir]
                )
                script_duration = time.time() - script_start_time
                
                if success:
                    execution_state['steps_completed'].append('pattern_analysis')
                    current_app.logger.info(f"✅ Pattern analysis completed in {script_duration:.2f}s")
                else:
                    execution_state['errors'].append(f"Pattern analysis warnings: {stderr}")
                    current_app.logger.warning(f"Pattern analysis returned warnings: {stderr}")
        
        # ========================================================================
        # STEP 6: Weight Calibration (Wizard C) - Optional but recommended
        # ========================================================================
        if not skip_wizard_c:
            current_app.logger.info(f"Step 6: Executing weight calibrator (Wizard C) for customer {customer_id}")
            wizard_c_script = customer_dir / "journey" / "wizard_c" / "wizard_c_weight_calibrator.py"
            
            if not wizard_c_script.exists():
                wizard_c_script = customer_dir / "journey" / "wizard_c" / "weight_calibrator.py"
            
            if wizard_c_script.exists():
                script_start_time = time.time()
                success, stdout, stderr = execute_script(wizard_c_script, customer_id, timeout=300)
                script_duration = time.time() - script_start_time
                
                if success:
                    execution_state['steps_completed'].append('weight_calibration')
                    current_app.logger.info(f"✅ Weight calibration completed in {script_duration:.2f}s")
                    
                    # P0: Improved Wizard C weight parsing - try file-based approach first, then robust regex
                    calibrated_weights = None
                    try:
                        # Try file-based approach first (more reliable)
                        weights_file = customer_dir / "journey" / "wizard_c" / "outputs" / f"customer_{customer_id}_calibrated_weights.json"
                        if weights_file.exists():
                            with open(weights_file, 'r') as f:
                                calibrated_weights = json.load(f)
                                current_app.logger.info(f"✅ Loaded calibrated weights from file: {weights_file}")
                        else:
                            # P0: Fallback to more robust regex parsing
                            import re
                            # Look for patterns like "Calibrated weights: {...}" or "Final weights: {...}"
                            json_match = re.search(
                                r'(?:calibrated|final).*?weights.*?(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',
                                stdout,
                                re.IGNORECASE | re.DOTALL
                            )
                            if not json_match:
                                # Fallback to simple JSON object match (original approach)
                                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', stdout, re.DOTALL)
                            
                            if json_match:
                                try:
                                    calibrated_weights = json.loads(json_match.group(1) if json_match.lastindex else json_match.group(0))
                                    current_app.logger.info(f"✅ Parsed calibrated weights from stdout")
                                except json.JSONDecodeError as e:
                                    current_app.logger.warning(f"⚠️  Could not parse weights JSON: {e}")
                    except Exception as e:
                        current_app.logger.warning(f"⚠️  Error parsing calibrated weights: {e}")
                    
                    # P0 & P1: Update CustomerConfig with transaction management and support KPI-level weights
                    if calibrated_weights:
                        try:
                            config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
                            if config:
                                # GAP 3.4: Capture old weights before update for response
                                old_pillar_weights = (config.dc2s_pillar_weights or {}).copy()
                                # P1: Support both pillar-level and KPI-level weight updates
                                pillar_keys = [k for k in calibrated_weights.keys() if k.startswith('P') or k in ['AI', 'CH', 'DV', 'EX', 'OS']]
                                kpi_keys = [k for k in calibrated_weights.keys() if '-' in k]  # e.g., 'AI-KPI1'
                                
                                if pillar_keys:
                                    # Update pillar weights
                                    new_pillar_weights = {k: calibrated_weights[k] for k in pillar_keys}
                                    config.dc2s_pillar_weights = new_pillar_weights
                                    current_app.logger.info(f"✅ Updated pillar weights: {list(new_pillar_weights.keys())}")
                                
                                if kpi_keys:
                                    # Update KPI-level weights
                                    kpi_weights = {k: calibrated_weights[k] for k in kpi_keys}
                                    # Check if dc2s_kpi_weights attribute exists
                                    if hasattr(config, 'dc2s_kpi_weights'):
                                        config.dc2s_kpi_weights = kpi_weights
                                        current_app.logger.info(f"✅ Updated KPI weights: {len(kpi_keys)} KPIs")
                                    else:
                                        current_app.logger.warning(f"⚠️  CustomerConfig model doesn't have dc2s_kpi_weights attribute")
                                
                                # P0: Transaction management with rollback on failure
                                db.session.commit()
                                current_app.logger.info(f"✅ Updated CustomerConfig with calibrated weights")
                                # GAP 3.4: Wizard C side effects - record for response so user knows scores may be stale
                                if pillar_keys:
                                    wizard_c_config_changes = {
                                        'pillar_weights_updated': True,
                                        'old_weights': old_pillar_weights,
                                        'new_weights': new_pillar_weights,
                                    }
                                current_app.logger.info(
                                    f"Wizard C config change: customer_id={customer_id} pillar_weights updated; "
                                    "health scores and embeddings may need recalculation (consider invalidating caches)."
                                )
                        except Exception as e:
                            # P0: Rollback on failure
                            db.session.rollback()
                            execution_state['errors'].append("Failed to update CustomerConfig")
                            current_app.logger.error(f"❌ Failed to update CustomerConfig: {e}", exc_info=True)
                    else:
                        current_app.logger.warning(f"⚠️  No calibrated weights found in Wizard C output")
                else:
                    execution_state['errors'].append(f"Weight calibration warnings: {stderr}")
                    current_app.logger.warning(f"Weight calibration returned warnings: {stderr}")
        
        # ========================================================================
        # STEP 7: Journey API Ready
        # ========================================================================
        current_app.logger.info(f"✅ Journey API ready (dynamic discovery enabled for customer {customer_id})")
        execution_state['steps_completed'].append('journey_api_ready')
        
        # GAP 3.7: Critical vs optional steps - fail if critical steps missing
        critical_steps = ['data_loading', 'embeddings']
        optional_steps = ['validation', 'pattern_analysis', 'weight_calibration']
        completed = set(execution_state['steps_completed'])
        missing_critical = [s for s in critical_steps if s not in completed]
        skipped_optional = [s for s in optional_steps if s not in completed]
        
        if missing_critical:
            if customer_id in _onboarding_progress:
                _onboarding_progress[customer_id]['in_progress'] = False
            return jsonify({
                "status": "error",
                "message": f"Critical step(s) failed or skipped: {missing_critical}. Process-data requires data_loading and embeddings.",
                "customer_id": customer_id,
                "steps_completed": execution_state['steps_completed'],
                "critical_steps_missing": missing_critical,
                "errors": execution_state['errors'],
                "execution_state": {
                    "data_loaded": 'data_loading' in completed,
                    "embeddings_created": 'embeddings' in completed,
                    "validation_run": 'validation' in completed,
                    "journey_generated": 'journey_generation' in completed,
                    "weight_calibrated": 'weight_calibration' in completed,
                }
            }), 500
        
        overall_status = 'success' if not execution_state['errors'] else 'warning'
        response_payload = {
            "status": overall_status,
            "message": "Data processing completed successfully" if overall_status == 'success' else "Data processing completed with warnings",
            "customer_id": customer_id,
            "steps_completed": execution_state['steps_completed'],
            "errors": execution_state['errors'],
            "validation": validation_result,
            "total_steps": len(execution_state['steps_completed']),
            "execution_state": {
                "data_loaded": True,
                "embeddings_created": 'embeddings' in completed,
                "validation_run": 'validation' in completed,
                "journey_generated": 'journey_generation' in completed,
                "weight_calibrated": 'weight_calibration' in completed,
            }
        }
        if skipped_optional:
            response_payload["optional_steps_skipped"] = skipped_optional
        # GAP 3.4: When Wizard C updated pillar weights, tell user health scores may be stale
        if wizard_c_config_changes:
            response_payload["config_changes"] = wizard_c_config_changes
            response_payload["action_required"] = [
                "Health scores should be recalculated (dashboard may show stale data until refresh).",
                "Consider refreshing account/dashboard views or re-running analysis.",
            ]
            warnings_list = response_payload.get("warnings") or []
            warnings_list.append({
                "type": "config_changed",
                "message": "Pillar weights updated by Wizard C. Health scores may be stale.",
                "action_required": "Recalculate health scores or refresh dashboards.",
            })
            response_payload["warnings"] = warnings_list
        if customer_id in _onboarding_progress:
            _onboarding_progress[customer_id]['in_progress'] = False
            _onboarding_progress[customer_id]['steps_completed'] = list(execution_state['steps_completed'])
        return jsonify(response_payload)
        
    except Exception as e:
        try:
            cid = (request.get_json() or {}).get('customer_id') or (request.form.get('customer_id', type=int))
            if cid is not None and cid in _onboarding_progress:
                _onboarding_progress.pop(cid, None)
        except Exception:
            pass
        current_app.logger.error(f"Error in process-data endpoint: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": "Data processing failed. Please try again or contact support."
        }), 500


@onboarding_api.route('/status/<int:customer_id>', methods=['GET'])
def onboarding_status(customer_id):
    """
    GAP 3.8: Progress endpoint for process-data.
    GET /api/onboarding/status/<customer_id>
    Returns in_progress, current_step, steps_completed, started_at (when in progress).
    """
    progress = _onboarding_progress.get(customer_id)
    if not progress:
        return jsonify({
            "customer_id": customer_id,
            "in_progress": False,
            "message": "No process-data in progress for this customer."
        })
    return jsonify({
        "customer_id": customer_id,
        "in_progress": progress.get("in_progress", True),
        "current_step": progress.get("current_step", "unknown"),
        "steps_completed": progress.get("steps_completed", []),
        "started_at": progress.get("started_at"),
    })


@onboarding_api.route('/upload', methods=['POST'])
def upload_onboarding_csv():
    """
    Upload CSV or Excel file to customer data directory
    
    Phase 2: Added to V2 - Config-aware upload with validation
    
    Files are saved to customer{N}-dc2_s/data/ directory.
    Loading to PostgreSQL is done by the process-data endpoint (reads these saved CSVs directly; no 02_load/02_upload scripts).
    
    Expected form data:
    - file: CSV or Excel file (.csv, .xlsx, .xls)
    - customer_id: int (required)
    - file_type: One of 'accounts', 'kpis', 'signals', 'products', 'profiles'
    - upload_mode: Optional - 'full_refresh', 'incremental', 'upsert', 'merge' (default: incremental)
    
    Returns:
    - status: success/error
    - file_path: Path where file was saved
    - message: Status message
    """
    try:
        # Get customer_id from form or request
        customer_id = request.form.get('customer_id', type=int)
        
        if not customer_id:
            # Try to get from authenticated user (if available)
            try:
                from auth_middleware import get_current_customer_id
                customer_id = get_current_customer_id()
            except:
                pass
        
        if not customer_id:
            return jsonify({'status': 'error', 'message': 'customer_id required'}), 400
        
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
        
        file = request.files['file']
        file_type = request.form.get('file_type', 'accounts')
        upload_mode = request.form.get('upload_mode', 'incremental')
        strict_mode = request.form.get('strict_mode', 'false').lower() == 'true'
        
        # Validate upload_mode
        valid_modes = ['full_refresh', 'incremental', 'upsert', 'merge']
        if upload_mode not in valid_modes:
            return jsonify({
                'status': 'error',
                'message': f'Invalid upload_mode: {upload_mode}. Valid modes: {", ".join(valid_modes)}'
            }), 400
        
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'Empty filename'}), 400
        
        customer_id = int(customer_id)
        
        # Get customer directory
        customer_dir = get_customer_directory(customer_id)
        data_dir = customer_dir / "data"
        
        # Check if customer directory exists
        if not customer_dir.exists():
            return jsonify({
                'status': 'error',
                'message': f'Customer directory not found. Please provision customer first: POST /api/onboarding/complete'
            }), 404
        
        # Create data directory if it doesn't exist
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Detect file type from extension
        filename = secure_filename(file.filename)
        file_ext = Path(filename).suffix.lower()
        is_excel = file_ext in ['.xlsx', '.xls']
        is_csv = file_ext == '.csv'
        
        if not (is_csv or is_excel):
            return jsonify({
                'status': 'error',
                'message': f'Unsupported file format: {file_ext}. Use .csv or .xlsx'
            }), 400
        
        # Determine target filename based on file_type
        if file_type in FILE_TYPES:
            # Map file_type to expected filename
            filename_map = {
                'accounts': 'accounts.csv',
                'kpis': 'kpi_measurements.csv',
                'signals': 'qualitative_signals.csv',
                'products': 'products.csv',
                'profiles': 'profiles.csv'
            }
            target_filename = filename_map.get(file_type, filename)
        else:
            target_filename = filename
        
        # Save file to customer data directory
        file_path = data_dir / target_filename
        
        try:
            upload_warnings = []
            # Save file temporarily first for validation
            temp_file_path = data_dir / f"temp_{target_filename}"
            file.save(str(temp_file_path))
            
            # GAP 2.2: For KPI files, validate schema (required columns, types, dates)
            if file_type == 'kpis':
                try:
                    df_check = pd.read_csv(temp_file_path, nrows=1000)
                except Exception as e:
                    temp_file_path.unlink(missing_ok=True)
                    return jsonify({'status': 'error', 'message': f'Invalid CSV: {e}'}), 400
                schema_ok, schema_errors = validate_kpi_csv_schema(df_check)
                if not schema_ok:
                    temp_file_path.unlink(missing_ok=True)
                    return jsonify({
                        'status': 'error',
                        'message': 'KPI CSV schema validation failed',
                        'errors': schema_errors
                    }), 400
            
            # GAP 2.1: For KPI files, validate/filter against config (enabled_kpis)
            if file_type == 'kpis':
                try:
                    df_full = pd.read_csv(temp_file_path)
                    df_filtered, config_warnings = filter_kpi_csv_by_config(df_full, customer_id, strict_mode=strict_mode)
                    upload_warnings.extend(config_warnings)
                    if len(df_filtered) < len(df_full):
                        df_filtered.to_csv(temp_file_path, index=False)
                except ValueError as e:
                    temp_file_path.unlink(missing_ok=True)
                    return jsonify({'status': 'error', 'message': str(e)}), 400
            
            # Validate account IDs before final save
            is_valid, validation_errors = validate_account_ids_in_file(temp_file_path, customer_id, file_type)
            
            if not is_valid:
                temp_file_path.unlink(missing_ok=True)
                return jsonify({
                    'status': 'error',
                    'message': 'Account ID validation failed',
                    'errors': validation_errors,
                    'expected_range': f"{calculate_account_id_range(customer_id)[0]}-{calculate_account_id_range(customer_id)[1]}"
                }), 400
            
            # Move temp file to final location
            if temp_file_path.exists():
                temp_file_path.rename(file_path)
            
            file_size = file_path.stat().st_size
            current_app.logger.info(f"✅ Saved file to {file_path} ({file_size} bytes)")
            
            # Store upload_mode in a metadata file for the data loading script
            upload_metadata = {
                'upload_mode': upload_mode,
                'uploaded_at': datetime.now().isoformat(),
                'file_type': file_type,
                'filename': target_filename
            }
            metadata_file = data_dir / f".upload_metadata_{file_type}.json"
            with open(metadata_file, 'w') as f:
                json.dump(upload_metadata, f, indent=2)
            
            # Log validation warnings if present
            if validation_errors:
                current_app.logger.warning(f"Account ID validation warnings: {validation_errors}")
                
        except Exception as e:
            current_app.logger.error(f"Error saving file: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': 'Failed to save file. Please try again or contact support.'
            }), 500
        
        resp = {
            'status': 'success',
            'message': 'File saved to customer directory',
            'file_type': file_type,
            'filename': target_filename,
            'file_path': str(file_path.relative_to(Path(__file__).parent)),
            'customer_id': customer_id,
            'upload_mode': upload_mode,
            'next_step': 'Run POST /api/onboarding/process-data to load data to database'
        }
        if upload_warnings:
            resp['warnings'] = upload_warnings
        return jsonify(resp)
            
    except Exception as e:
        current_app.logger.error(f"Error in onboarding upload: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred. Please try again or contact support.'
        }), 500

@onboarding_api.route('/validate-csv', methods=['POST'])
def validate_csv_endpoint():
    """
    NEW: Validate CSV file against CustomerConfig
    
    Allows users to check CSV before uploading
    
    Request:
        - file: CSV file (multipart/form-data)
        - customer_id: int
    
    Response:
        {
            "valid": true,
            "enabled_kpis": 15,
            "csv_kpis": 35,
            "disabled_kpis": [20 KPIs...],
            "warnings": [...],
            "details": {
                "total_records": 5400,
                "enabled_records": 1800,
                "filtered_records": 3600,
                "filter_percentage": "66.7%"
            }
        }
    """
    
    customer_id = request.form.get('customer_id', type=int)
    
    if not customer_id:
        return jsonify({"error": "customer_id required"}), 400
    
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    try:
        # Save temporarily
        import tempfile
        from werkzeug.utils import secure_filename
        
        temp_dir = Path(tempfile.mkdtemp())
        filename = secure_filename(file.filename)
        temp_file = temp_dir / filename
        file.save(temp_file)
        
        # Validate
        result = validate_csv_against_config(customer_id, temp_file)
        
        # Clean up
        temp_file.unlink()
        temp_dir.rmdir()
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error validating CSV: {str(e)}", exc_info=True)
        return jsonify({
            "error": "CSV validation failed. Please try again or contact support."
        }), 500

# ============================================================================
# Health Check
# ============================================================================

@onboarding_api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": "2.0",
        "features": ["config-aware", "validation", "filtering"]
    })

# ============================================================================
# Next Customer ID (DB query)
# ============================================================================

@onboarding_api.route('/next-customer-id', methods=['GET'])
def get_next_customer_id():
    """Get next available customer ID from database"""
    try:
        from sqlalchemy import func
        max_id = db.session.query(func.max(Customer.customer_id)).scalar() or 0
        next_id = max_id + 1
        account_id_start = next_id * 1000
        return jsonify({
            'next_customer_id': next_id,
            'account_id_range': {
                'start': account_id_start + 1,
                'end': account_id_start + 10
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error getting next customer ID: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# ============================================================================
# CSV Template Downloads
# ============================================================================

TEMPLATE_MAP = {
    'accounts': 'accounts.csv',
    'kpis': 'kpi_measurements.csv',
    'signals': 'qualitative_signals.csv',
    'products': 'products.csv',
    'profiles': 'account_profiles.csv',
    'customers': 'customers.csv'
}

@onboarding_api.route('/templates/<file_type>', methods=['GET'])
def download_template(file_type):
    """Download CSV template file for onboarding"""
    if file_type not in TEMPLATE_MAP:
        return jsonify({
            'status': 'error',
            'message': f'Invalid file type: {file_type}. Supported: {", ".join(TEMPLATE_MAP.keys())}'
        }), 400

    template_filename = TEMPLATE_MAP[file_type]
    template_path = Path(__file__).parent / "verticals" / "_template" / "templates" / template_filename

    if not template_path.exists():
        current_app.logger.error(f"Template file not found: {template_path}")
        return jsonify({
            'status': 'error',
            'message': f'Template file not found: {template_filename}'
        }), 404

    return send_file(
        str(template_path),
        as_attachment=True,
        download_name=template_filename,
        mimetype='text/csv'
    )

@onboarding_api.route('/templates', methods=['GET'])
def list_templates():
    """List all available template files with descriptions"""
    templates = [
        {'file_type': 'accounts', 'filename': 'accounts.csv',
         'description': 'Account master data with profile metadata', 'required': True},
        {'file_type': 'kpis', 'filename': 'kpi_measurements.csv',
         'description': 'KPI time-series measurements', 'required': True},
        {'file_type': 'signals', 'filename': 'qualitative_signals.csv',
         'description': 'Qualitative signals (emails, meetings, escalations)', 'required': False},
        {'file_type': 'products', 'filename': 'products.csv',
         'description': 'Product catalog', 'required': False},
        {'file_type': 'profiles', 'filename': 'account_profiles.csv',
         'description': 'Extended account profile attributes', 'required': False},
        {'file_type': 'customers', 'filename': 'customers.csv',
         'description': 'Customer/tenant-level data', 'required': False}
    ]
    return jsonify({
        'status': 'success',
        'templates': templates,
        'download_url': '/api/onboarding/templates/{file_type}'
    })

# ============================================================================
# DEPRECATED Filesystem Endpoints
# ============================================================================
# These endpoints relied on filesystem-based provisioning (customer directory
# structures, dynamic Python file loading, CSV file generation on disk).
# Journeys are now DB-based. Use /api/onboarding/complete which handles
# customer creation in the database. These stubs exist so the frontend
# gets an informative response instead of a 404.

@onboarding_api.route('/provision', methods=['POST'])
def provision_noop():
    """NO-OP: Provisioning is now handled inside /complete.
    Returns 200 so the frontend completion flow doesn't break."""
    return jsonify({
        'status': 'success',
        'message': 'Provisioning is handled by /api/onboarding/complete. No additional action needed.',
        'noop': True
    }), 200

@onboarding_api.route('/register-journey-api', methods=['POST'])
def register_journey_api_noop():
    """NO-OP: Journey data is now DB-based via /admin/wizard endpoints.
    Returns 200 so the frontend completion flow doesn't break."""
    return jsonify({
        'status': 'success',
        'message': 'Journey API is now DB-based. No registration needed.',
        'noop': True
    }), 200

@onboarding_api.route('/generate-sample-files', methods=['POST'])
def generate_sample_files_noop():
    """NO-OP: Sample data is generated inside /complete for demo mode.
    Returns 200 so the frontend doesn't break."""
    return jsonify({
        'status': 'success',
        'message': 'Sample data generation is handled by /api/onboarding/complete in demo mode.',
        'noop': True
    }), 200
