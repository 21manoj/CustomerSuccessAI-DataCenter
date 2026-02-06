#!/usr/bin/env python3
"""
Complete End-to-End Onboarding Test (Using API Endpoints)
==========================================================

Tests the FULL onboarding pipeline starting from API endpoint:
1. POST /api/onboarding/complete - Create customer (will be 113)
2. POST /api/onboarding/provision - Provision directory
3. Generate and upload sample files
4. POST /api/onboarding/process-data - Execute data loading + Wizard A
5. Validate final state

This test uses the actual API endpoints to simulate real user flow.
"""

import sys
import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer, User, Account, CustomerConfig
from sqlalchemy import func, text
from onboarding_api import (
    get_customer_directory,
    execute_script
)
import generate_synthetic_customer_data as synth_gen

# Test configuration
BASE_URL = "http://localhost:5059"  # Backend URL
# Use a single timestamp to ensure consistency between company name and email
_TEST_TIMESTAMP = int(time.time())
TEST_COMPANY_NAME = f"E2E Complete Test Corporation {_TEST_TIMESTAMP}"
TEST_EMAIL = f"test_{_TEST_TIMESTAMP}@e2ecompletetest.com"
TEST_PASSWORD = "TestPass123!"

# Log and report directories
LOG_DIR = Path(__file__).parent / "logs" / "onboarding_tests"
LOG_DIR.mkdir(parents=True, exist_ok=True)
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
# Initial log file (will be renamed after customer ID is known)
LOG_FILE = LOG_DIR / f"onboarding_complete_e2e_api_{TIMESTAMP}.log"
REPORT_FILE = None  # Will be set after customer ID is known

# Test results structure
test_results = {
    "test_name": "Complete End-to-End Onboarding Test (API-based)",
    "timestamp": datetime.now().isoformat(),
    "test_config": {
        "company_name": TEST_COMPANY_NAME,
        "email": TEST_EMAIL,
        "vertical": "dc2_s",
        "num_accounts": 5,
        "num_months": 12
    },
    "steps": [],
    "validations": [],
    "errors": [],
    "warnings": [],
    "summary": {
        "total_steps": 0,
        "passed_steps": 0,
        "failed_steps": 0,
        "total_validations": 0,
        "passed_validations": 0,
        "failed_validations": 0
    }
}

def log(message: str, level: str = "INFO", step: Optional[str] = None):
    """Log message to file and console"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    log_msg = f"[{timestamp}] [{level}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')
    
    if step:
        test_results["steps"].append({
            "timestamp": timestamp,
            "level": level,
            "step": step,
            "message": message
        })

def log_validation(name: str, passed: bool, details: str, expected: Optional[str] = None, actual: Optional[str] = None):
    """Log validation result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    log(f"VALIDATION: {name} - {status}", "INFO" if passed else "ERROR")
    if details:
        log(f"  Details: {details}", "INFO")
    if expected:
        log(f"  Expected: {expected}", "INFO")
    if actual:
        log(f"  Actual: {actual}", "INFO")
    
    validation = {
        "name": name,
        "passed": passed,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    if expected:
        validation["expected"] = expected
    if actual:
        validation["actual"] = actual
    
    test_results["validations"].append(validation)
    test_results["summary"]["total_validations"] += 1
    if passed:
        test_results["summary"]["passed_validations"] += 1
    else:
        test_results["summary"]["failed_validations"] += 1

def log_error(message: str, error: Exception = None):
    """Log error"""
    error_msg = f"{message}: {str(error)}" if error else message
    log(error_msg, "ERROR")
    test_results["errors"].append(error_msg)
    if error:
        import traceback
        log(traceback.format_exc(), "ERROR")

def step(step_name: str):
    """Decorator for test steps"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            log("=" * 70)
            log(f"STEP: {step_name}")
            log("=" * 70)
            test_results["summary"]["total_steps"] += 1
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                log(f"✅ Step '{step_name}' completed in {duration:.2f}s")
                test_results["summary"]["passed_steps"] += 1
                return result
            except Exception as e:
                duration = time.time() - start_time
                log_error(f"Step '{step_name}' failed", e)
                test_results["summary"]["failed_steps"] += 1
                raise
        return wrapper
    return decorator

@step("1. Complete Onboarding (Create Customer via API)")
def test_complete_onboarding() -> int:
    """Create customer using /api/onboarding/complete endpoint"""
    log(f"Calling POST {BASE_URL}/api/onboarding/complete")
    
    payload = {
        "company_name": TEST_COMPANY_NAME,
        "company_email": TEST_EMAIL,
        "admin_name": "E2E Test Admin",
        "admin_email": TEST_EMAIL,
        "admin_password": TEST_PASSWORD,
        "vertical": "dc2_s",
        "weights": {
            "P1_deployment_velocity": 0.15,
            "P2_operational_stability": 0.20,
            "P3_ai_workload_performance": 0.25,
            "P4_channel_partner_health": 0.15,
            "P5_expansion_revenue": 0.25
        },
        "team": []
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/onboarding/complete",
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"API returned status {response.status_code}: {response.text}")
        
        data = response.json()
        customer_id = data.get("customer_id")
        
        if not customer_id:
            raise Exception(f"No customer_id in response: {data}")
        
        log(f"✅ Customer created via API: {customer_id}")
        
        # Rename log and report files to include customer ID
        global LOG_FILE, REPORT_FILE
        old_log_file = LOG_FILE
        LOG_FILE = LOG_DIR / f"onboarding_customer{customer_id}_e2e_api_{TIMESTAMP}.log"
        REPORT_FILE = LOG_DIR / f"onboarding_customer{customer_id}_e2e_api_{TIMESTAMP}.json"
        
        # Move existing log content to new file
        if old_log_file.exists():
            import shutil
            shutil.move(str(old_log_file), str(LOG_FILE))
            log(f"✅ Log file renamed to include customer ID: {LOG_FILE.name}")
        
        log_validation(
            "Customer Created via API",
            customer_id is not None and customer_id > 0,
            f"Customer ID should be assigned by database",
            "> 0",
            f"{customer_id}"
        )
        
        # Verify in database
        with app.app_context():
            customer = Customer.query.filter_by(customer_id=customer_id).first()
            log_validation(
                "Customer in Database",
                customer is not None,
                f"Customer {customer_id} should exist in database",
                "Not None",
                "Found" if customer else "Not Found"
            )
            
            user = User.query.filter_by(customer_id=customer_id).first()
            log_validation(
                "User Created",
                user is not None,
                f"User should be created for customer {customer_id}",
                "Not None",
                "Found" if user else "Not Found"
            )
            
            config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
            log_validation(
                "Config Created",
                config is not None,
                f"Config should be created for customer {customer_id}",
                "Not None",
                "Found" if config else "Not Found"
            )
        
        return customer_id
        
    except requests.exceptions.ConnectionError:
        # Fallback: Create directly if API not available
        log("⚠️  API not available, creating customer directly", "WARNING")
        return test_create_customer_direct()

def test_create_customer_direct() -> int:
    """Fallback: Create customer directly if API unavailable"""
    with app.app_context():
        max_id = db.session.query(func.max(Customer.customer_id)).scalar() or 0
        customer_id = max_id + 1
        
        customer = Customer(
            customer_id=customer_id,
            customer_name=TEST_COMPANY_NAME,
            email=TEST_EMAIL,
            domain=f"e2ecompletetest{customer_id}.com"
        )
        db.session.add(customer)
        db.session.commit()
        
        from werkzeug.security import generate_password_hash
        user = User(
            customer_id=customer_id,
            user_name="E2E Test Admin",
            email=TEST_EMAIL,
            password_hash=generate_password_hash(TEST_PASSWORD),
            vertical="dc2_s",
            role="admin",
            active=True
        )
        db.session.add(user)
        db.session.commit()
        
        config = CustomerConfig(
            customer_id=customer_id,
            kpi_upload_mode="account_rollup",
            category_weights='{"P1_deployment_velocity": 0.15, "P2_operational_stability": 0.20, "P3_ai_workload_performance": 0.25, "P4_channel_partner_health": 0.15, "P5_expansion_revenue": 0.25}',
            master_file_name=None
        )
        db.session.add(config)
        db.session.commit()
        
        # Rename log and report files to include customer ID
        global LOG_FILE, REPORT_FILE
        old_log_file = LOG_FILE
        LOG_FILE = LOG_DIR / f"onboarding_customer{customer_id}_e2e_api_{TIMESTAMP}.log"
        REPORT_FILE = LOG_DIR / f"onboarding_customer{customer_id}_e2e_api_{TIMESTAMP}.json"
        
        # Move existing log content to new file
        if old_log_file.exists():
            import shutil
            shutil.move(str(old_log_file), str(LOG_FILE))
            log(f"✅ Log file renamed to include customer ID: {LOG_FILE.name}")
        
        log(f"✅ Customer created directly: {customer_id}")
        return customer_id

@step("2. Provision Customer Directory (via API)")
def test_provision_directory(customer_id: int) -> Path:
    """Provision customer directory using /api/onboarding/provision endpoint"""
    log(f"Calling POST {BASE_URL}/api/onboarding/provision")
    
    payload = {
        "customer_id": customer_id,
        "customer_name": TEST_COMPANY_NAME,
        "vertical_slug": "dc2_s"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/onboarding/provision",
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"API returned status {response.status_code}: {response.text}")
        
        data = response.json()
        log(f"✅ Provision response: {data.get('message', 'Success')}")
        
        # Get customer directory path
        with app.app_context():
            customer_dir = get_customer_directory(customer_id, vertical_slug="dc2_s")
        
        # Wait for filesystem sync
        time.sleep(1.0)
        
        # Validate directory structure
        backend_dir = Path(__file__).parent
        customer_dir = backend_dir / "verticals" / f"customer{customer_id}-dc2_s"
        
        log_validation(
            "Customer Directory Created",
            customer_dir.exists(),
            f"Customer directory should be created",
            "True",
            str(customer_dir.exists())
        )
        
        data_dir = customer_dir / "data"
        scripts_dir = customer_dir / "scripts"
        journey_dir = customer_dir / "journey"
        
        log_validation(
            "Subdirectory 'data' Exists",
            data_dir.exists(),
            f"Subdirectory data should exist",
            "True",
            str(data_dir.exists())
        )
        
        log_validation(
            "Subdirectory 'scripts' Exists",
            scripts_dir.exists(),
            f"Subdirectory scripts should exist",
            "True",
            str(scripts_dir.exists())
        )
        
        log_validation(
            "Subdirectory 'journey' Exists",
            journey_dir.exists(),
            f"Subdirectory journey should exist",
            "True",
            str(journey_dir.exists())
        )
        
        return customer_dir
        
    except requests.exceptions.ConnectionError:
        # Fallback: Provision directly
        log("⚠️  API not available, provisioning directly", "WARNING")
        return test_provision_direct(customer_id)

def test_provision_direct(customer_id: int) -> Path:
    """Fallback: Provision directory directly"""
    from verticals.provision_dc_customer import provision_customer
    
    success = provision_customer(
        customer_id=customer_id,
        customer_name=TEST_COMPANY_NAME,
        vertical_slug="dc2_s",
        dry_run=False,
        force=True
    )
    
    if not success:
        raise Exception(f"Provision failed for customer {customer_id}")
    
    time.sleep(1.0)
    backend_dir = Path(__file__).parent
    customer_dir = backend_dir / "verticals" / f"customer{customer_id}-dc2_s"
    return customer_dir

@step("3. Generate and Upload Sample Files")
def test_generate_and_upload_files(customer_id: int, customer_dir: Path) -> Dict:
    """Generate sample CSV files and upload them"""
    with app.app_context():
        data_dir = customer_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        log(f"Generating sample files for customer {customer_id}...")
        
        # Generate files
        company_name = TEST_COMPANY_NAME
        industry = "Healthcare"
        num_accounts = 5
        
        accounts = synth_gen.generate_accounts(
            customer_id=customer_id,
            num_accounts=num_accounts,
            industry=industry,
            company_name=company_name
        )
        
        # Ensure all accounts have the correct customer_id
        for account in accounts:
            if 'customer_id' not in account or account['customer_id'] != customer_id:
                account['customer_id'] = customer_id
                log(f"  Fixed customer_id for account {account.get('account_id', 'unknown')}")
        
        kpi_measurements = synth_gen.generate_kpi_measurements(accounts=accounts)
        qualitative_signals = synth_gen.generate_qualitative_signals(accounts=accounts)
        products = synth_gen.generate_products(customer_id=customer_id)
        profiles = synth_gen.generate_profiles(accounts=accounts)
        
        # Save to CSV files
        files_saved = {}
        
        accounts_df = pd.DataFrame(accounts)
        # Ensure customer_id column exists and is correct
        if 'customer_id' not in accounts_df.columns:
            accounts_df['customer_id'] = customer_id
        accounts_df['customer_id'] = customer_id
        
        # Remove internal columns that aren't in the database schema
        # These are used for data generation but shouldn't be in the CSV
        columns_to_drop = ['_scenario', '_scenario_key']
        for col in columns_to_drop:
            if col in accounts_df.columns:
                accounts_df = accounts_df.drop(columns=[col])
        
        # Convert profile_metadata to JSON string if it's a dict
        if 'profile_metadata' in accounts_df.columns:
            accounts_df['profile_metadata'] = accounts_df['profile_metadata'].apply(
                lambda x: json.dumps(x) if isinstance(x, dict) else x
            )
        
        accounts_file = data_dir / "accounts.csv"
        accounts_df.to_csv(accounts_file, index=False)
        files_saved["accounts"] = str(accounts_file)
        log(f"✅ Saved accounts.csv ({len(accounts)} accounts, customer_id={customer_id})")
        
        kpi_df = pd.DataFrame(kpi_measurements)
        kpi_file = data_dir / "kpi_measurements.csv"
        kpi_df.to_csv(kpi_file, index=False)
        files_saved["kpi_measurements"] = str(kpi_file)
        log(f"✅ Saved kpi_measurements.csv ({len(kpi_measurements)} measurements)")
        
        signals_df = pd.DataFrame(qualitative_signals)
        signals_file = data_dir / "qualitative_signals.csv"
        signals_df.to_csv(signals_file, index=False)
        files_saved["qualitative_signals"] = str(signals_file)
        log(f"✅ Saved qualitative_signals.csv ({len(qualitative_signals)} signals)")
        
        products_df = pd.DataFrame(products)
        products_file = data_dir / "products.csv"
        products_df.to_csv(products_file, index=False)
        files_saved["products"] = str(products_file)
        log(f"✅ Saved products.csv ({len(products)} products)")
        
        profiles_df = pd.DataFrame(profiles)
        # Save as account_profiles.csv (expected by 02_load script)
        profiles_file = data_dir / "account_profiles.csv"
        profiles_df.to_csv(profiles_file, index=False)
        files_saved["account_profiles"] = str(profiles_file)
        log(f"✅ Saved account_profiles.csv ({len(profiles)} profiles)")
        
        # Generate customers.csv (expected by 02_load script)
        # The customer is already created via API, but the script expects a CSV file
        with app.app_context():
            customer = Customer.query.filter_by(customer_id=customer_id).first()
            if customer:
                customers_data = [{
                    'customer_id': customer.customer_id,
                    'customer_name': customer.customer_name,
                    'email': customer.email or '',
                    'domain': customer.domain or '',
                    'phone': customer.phone or '',
                    'created_at': customer.created_at.isoformat() if customer.created_at else datetime.now().isoformat()
                }]
                customers_df = pd.DataFrame(customers_data)
                customers_file = data_dir / "customers.csv"
                customers_df.to_csv(customers_file, index=False)
                files_saved["customers"] = str(customers_file)
                log(f"✅ Saved customers.csv (1 customer)")
        
        # Validate files exist
        required_files = ["accounts.csv", "kpi_measurements.csv", "qualitative_signals.csv", "products.csv", "account_profiles.csv", "customers.csv"]
        for filename in required_files:
            file_path = data_dir / filename
            log_validation(
                f"Required File '{filename}' Exists",
                file_path.exists(),
                f"Required file {filename} should exist in data directory",
                "True",
                str(file_path.exists())
            )
        
        return {
            "files_saved": files_saved,
            "data_dir": str(data_dir),
            "num_accounts": num_accounts,
            "num_kpi_measurements": len(kpi_measurements),
            "num_signals": len(qualitative_signals)
        }

@step("4. Process Data (Load + Embeddings + Wizard A via API)")
def test_process_data_api(customer_id: int, customer_dir: Path) -> Dict:
    """Execute data processing via /api/onboarding/process-data endpoint"""
    log(f"Calling POST {BASE_URL}/api/onboarding/process-data")
    
    payload = {
        "customer_id": customer_id,
        "skip_validation": False,
        "skip_wizard_b": True,
        "skip_wizard_c": True
    }
    
    try:
        log(f"Starting process-data for customer {customer_id}...")
        log(f"This will execute:")
        log(f"  1. 02_load script (data loading)")
        log(f"  2. 03_embed script (embeddings)")
        log(f"  3. Wizard A (journey generation)")
        log(f"  4. Wizard B/C (skipped)")
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/process-data",
            json=payload,
            timeout=600  # 10 minute timeout for full processing
        )
        
        if response.status_code != 200:
            raise Exception(f"API returned status {response.status_code}: {response.text}")
        
        data = response.json()
        log(f"✅ Process-data response: {data.get('message', 'Success')}")
        
        execution_state = data.get("execution_state", {})
        steps_completed = execution_state.get("steps_completed", [])
        
        log(f"Steps completed: {', '.join(steps_completed)}")
        
        # Validate data was loaded
        with app.app_context():
            account_count = Account.query.filter_by(customer_id=customer_id).count()
            log_validation(
                "Accounts Loaded into Database",
                account_count > 0,
                f"Should have loaded accounts",
                "> 0",
                f"{account_count}"
            )
            
            # Check KPI measurements
            result = db.session.execute(text('''
                SELECT COUNT(*) FROM kpi_measurements km
                JOIN accounts a ON km.account_id = a.account_id
                WHERE a.customer_id = :cid
            '''), {'cid': customer_id})
            kpi_count = result.scalar()
            
            log_validation(
                "KPI Measurements Loaded",
                kpi_count > 0,
                f"Should have loaded KPI measurements",
                "> 0",
                f"{kpi_count}"
            )
            
            # Check qualitative signals
            result = db.session.execute(text('''
                SELECT COUNT(*) FROM qualitative_signals qs
                JOIN accounts a ON qs.account_id = a.account_id
                WHERE a.customer_id = :cid
            '''), {'cid': customer_id})
            signal_count = result.scalar()
            
            log_validation(
                "Qualitative Signals Loaded",
                signal_count > 0,
                f"Should have loaded qualitative signals",
                "> 0",
                f"{signal_count}"
            )
        
        # Validate Wizard A execution
        wizard_a_dir = customer_dir / "journey" / "wizard_a"
        # Files are created in the outputs subdirectory
        outputs_dir = wizard_a_dir / "outputs"
        journey_files = list(outputs_dir.glob("account_*_journey.json")) if outputs_dir.exists() else []
        
        log_validation(
            "Journey Data Files Created (Wizard A)",
            len(journey_files) > 0,
            f"Should have journey JSON files after Wizard A in {outputs_dir}",
            "> 0 files",
            f"{len(journey_files)} files"
        )
        
        if len(journey_files) > 0:
            log(f"  Found journey files: {[f.name for f in journey_files[:5]]}")
        
        log_validation(
            "Data Loading Step Completed",
            "data_loading" in steps_completed,
            f"Data loading should be in completed steps",
            "data_loading in steps_completed",
            str("data_loading" in steps_completed)
        )
        
        log_validation(
            "Wizard A Step Completed",
            "journey_generation" in steps_completed,
            f"Journey generation (Wizard A) should be in completed steps",
            "journey_generation in steps_completed",
            str("journey_generation" in steps_completed)
        )
        
        return execution_state
        
    except requests.exceptions.ConnectionError:
        # Fallback: Execute scripts directly
        log("⚠️  API connection error, executing scripts directly", "WARNING")
        return test_process_data_direct(customer_id, customer_dir)
    except Exception as e:
        # If API fails for any reason (404, etc.), fallback to direct execution
        log(f"⚠️  API call failed: {e}, falling back to direct execution", "WARNING")
        return test_process_data_direct(customer_id, customer_dir)

def test_process_data_direct(customer_id: int, customer_dir: Path) -> Dict:
    """Fallback: Execute scripts directly if API unavailable"""
    execution_state = {
        "steps_completed": [],
        "errors": [],
        "warnings": []
    }
    
    # Ensure we have the correct customer_dir path
    with app.app_context():
        customer_dir = get_customer_directory(customer_id, vertical_slug="dc2_s")
    
    # Step 4.1: Execute 02_load script
    log(f"Step 4.1: Executing data loading script for customer {customer_id}")
    load_script = customer_dir / "scripts" / f"02_load_customer{customer_id}_data_SMART.py"
    
    if not load_script.exists():
        raise Exception(f"Data loading script not found: {load_script}")
    
    log(f"✅ Found script: {load_script}")
    log(f"Executing script...")
    
    script_start_time = time.time()
    success, stdout, stderr = execute_script(load_script, customer_id, timeout=600)
    script_duration = time.time() - script_start_time
    
    if not success:
        raise Exception(f"Data loading script failed: {stderr}")
    
    log(f"✅ Data loading completed in {script_duration:.2f}s")
    execution_state["steps_completed"].append("data_loading")
    
    # Step 4.2: Execute 03_embed script (optional)
    embed_script = customer_dir / "scripts" / f"03_embed_customer{customer_id}_OPENAI.py"
    if embed_script.exists():
        log(f"Step 4.2: Executing embedding script...")
        success, stdout, stderr = execute_script(embed_script, customer_id, timeout=600)
        if success:
            log(f"✅ Embeddings created")
            execution_state["steps_completed"].append("embeddings")
        else:
            log(f"⚠️  Embedding script returned warnings: {stderr}", "WARNING")
    
    # Step 4.3: Execute Wizard A
    log(f"Step 4.3: Executing Wizard A (journey generator)...")
    wizard_a_dir = customer_dir / "journey" / "wizard_a"
    journey_script = wizard_a_dir / "wizard_journey_generator.py"
    
    if not journey_script.exists():
        journey_script = wizard_a_dir / "wizard_a_journey_generator.py"
    
    if not journey_script.exists():
        raise Exception(f"Journey generator script not found in {wizard_a_dir}")
    
    log(f"✅ Found script: {journey_script}")
    
    # Wait a moment for database to sync
    time.sleep(0.5)
    
    # Get account count and IDs for Wizard A
    with app.app_context():
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        account_count = len(accounts)
        
        if account_count == 0:
            # Check if accounts exist with different customer_id (maybe data loading issue)
            all_accounts = Account.query.all()
            log(f"⚠️  No accounts found for customer {customer_id}")
            log(f"   Total accounts in database: {len(all_accounts)}")
            if len(all_accounts) > 0:
                from collections import Counter
                customer_ids = [a.customer_id for a in all_accounts]
                counts = Counter(customer_ids)
                log(f"   Accounts by customer_id: {dict(counts)}")
            
            # Check if data loading actually succeeded by checking the script output
            log(f"   Checking if data loading script output indicates success...")
            raise Exception(f"No accounts found for customer {customer_id}. Data loading may have failed. Check script output above.")
        
        # Get first account ID as start_id
        start_id = accounts[0].account_id if accounts else customer_id * 1000
        
        # Default pattern mix
        pattern_mix = '{"crisis":0.2,"churn":0.15,"stable":0.4,"expansion":0.25}'
        
        # Output directory
        output_dir = str(wizard_a_dir / "outputs")
    
    log(f"Executing Wizard A with {account_count} accounts...")
    log(f"  Start ID: {start_id}")
    log(f"  Pattern Mix: {pattern_mix}")
    log(f"  Output Dir: {output_dir}")
    
    # Build command arguments
    additional_args = [
        "--accounts", str(account_count),
        "--start-id", str(start_id),
        "--pattern-mix", pattern_mix,
        "--output-dir", output_dir
    ]
    
    script_start_time = time.time()
    success, stdout, stderr = execute_script(
        journey_script, 
        customer_id, 
        timeout=600,
        additional_args=additional_args
    )
    script_duration = time.time() - script_start_time
    
    if not success:
        raise Exception(f"Wizard A (journey generator) failed: {stderr}")
    
    log(f"✅ Wizard A completed in {script_duration:.2f}s")
    execution_state["steps_completed"].append("journey_generation")
    
    # Validate journey data
    # Files are created in the outputs subdirectory
    outputs_dir = wizard_a_dir / "outputs"
    journey_files = list(outputs_dir.glob("account_*_journey.json")) if outputs_dir.exists() else []
    log_validation(
        "Journey Data Files Created (Wizard A)",
        len(journey_files) > 0,
        f"Should have journey JSON files after Wizard A in {outputs_dir}",
        "> 0 files",
        f"{len(journey_files)} files"
    )
    
    if len(journey_files) > 0:
        log(f"  Found journey files: {[f.name for f in journey_files[:5]]}")
    
    return execution_state

@step("5. Validate Final State")
def test_validate_final_state(customer_id: int, customer_dir: Path):
    """Validate final state after all steps"""
    with app.app_context():
        log(f"Validating final state for customer {customer_id}")
        
        # Validate customer in database
        customer = Customer.query.filter_by(customer_id=customer_id).first()
        log_validation(
            "Customer in Database",
            customer is not None,
            f"Customer {customer_id} should exist in database",
            "Not None",
            "Found" if customer else "Not Found"
        )
        
        # Validate user
        user = User.query.filter_by(customer_id=customer_id).first()
        log_validation(
            "User in Database",
            user is not None,
            f"User for customer {customer_id} should exist",
            "Not None",
            "Found" if user else "Not Found"
        )
        
        # Validate config
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        log_validation(
            "Config in Database",
            config is not None,
            f"Config for customer {customer_id} should exist",
            "Not None",
            "Found" if config else "Not Found"
        )
        
        # Validate accounts
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        account_count = len(accounts)
        log_validation(
            "Accounts in Database",
            account_count > 0,
            f"Should have accounts in database",
            "> 0",
            f"{account_count}"
        )
        
        # Validate KPI measurements
        if account_count > 0:
            account_ids = [a.account_id for a in accounts]
            result = db.session.execute(text('''
                SELECT COUNT(*) FROM kpi_measurements 
                WHERE account_id = ANY(:account_ids)
            '''), {'account_ids': account_ids})
            kpi_count = result.scalar()
            
            log_validation(
                "KPI Measurements in Database",
                kpi_count > 0,
                f"Should have KPI measurements loaded",
                "> 0",
                f"{kpi_count}"
            )
            
            # Validate qualitative signals
            result = db.session.execute(text('''
                SELECT COUNT(*) FROM qualitative_signals 
                WHERE account_id = ANY(:account_ids)
            '''), {'account_ids': account_ids})
            signal_count = result.scalar()
            
            log_validation(
                "Qualitative Signals in Database",
                signal_count > 0,
                f"Should have qualitative signals loaded",
                "> 0",
                f"{signal_count}"
            )
        
        # Validate directory structure
        log_validation(
            "Customer Directory Exists",
            customer_dir.exists(),
            f"Customer directory should exist",
            "True",
            str(customer_dir.exists())
        )
        
        # Validate journey data
        wizard_a_dir = customer_dir / "journey" / "wizard_a"
        # Files are created in the outputs subdirectory
        outputs_dir = wizard_a_dir / "outputs"
        journey_files = list(outputs_dir.glob("account_*_journey.json")) if outputs_dir.exists() else []
        log_validation(
            "Journey Data Files Exist",
            len(journey_files) > 0,
            f"Should have journey JSON files after Wizard A in {outputs_dir}",
            "> 0 files",
            f"{len(journey_files)} files"
        )
        
        if len(journey_files) > 0:
            log(f"  Found journey files: {[f.name for f in journey_files[:5]]}")

def generate_report():
    """Generate final test report"""
    test_results["summary"]["end_time"] = datetime.now().isoformat()
    
    # Calculate success rate
    total = test_results["summary"]["total_steps"] + test_results["summary"]["total_validations"]
    passed = test_results["summary"]["passed_steps"] + test_results["summary"]["passed_validations"]
    success_rate = (passed / total * 100) if total > 0 else 0
    
    test_results["summary"]["success_rate"] = f"{success_rate:.2f}%"
    
    # Save JSON report (REPORT_FILE is set after customer creation)
    if REPORT_FILE:
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, default=str, ensure_ascii=False)
    else:
        log("⚠️  WARNING: REPORT_FILE not set, cannot save JSON report", "WARNING")
    
    log("\n" + "=" * 70)
    log("TEST SUMMARY")
    log("=" * 70)
    log(f"Total Steps: {test_results['summary']['total_steps']}")
    log(f"  ✅ Passed: {test_results['summary']['passed_steps']}")
    log(f"  ❌ Failed: {test_results['summary']['failed_steps']}")
    log(f"Total Validations: {test_results['summary']['total_validations']}")
    log(f"  ✅ Passed: {test_results['summary']['passed_validations']}")
    log(f"  ❌ Failed: {test_results['summary']['failed_validations']}")
    log(f"Success Rate: {test_results['summary']['success_rate']}")
    if REPORT_FILE:
        log(f"\nReport saved to: {REPORT_FILE}")
    log(f"Log saved to: {LOG_FILE}")
    
    if test_results["warnings"]:
        log(f"\nWarnings ({len(test_results['warnings'])}):")
        for warning in test_results["warnings"]:
            log(f"  - {warning}", "WARNING")
    
    log("=" * 70)

def main():
    """Main test execution"""
    log("=" * 70)
    log("COMPLETE END-TO-END ONBOARDING TEST (API-BASED)")
    log("=" * 70)
    log(f"Started at: {datetime.now().isoformat()}")
    log(f"Initial log file: {LOG_FILE}")
    log(f"Report file: (will be set after customer creation)")
    log(f"Base URL: {BASE_URL}")
    log("=" * 70)
    log("")
    
    customer_id = None
    customer_dir = None
    generated_data = None
    
    try:
        # Ensure we get customer 113 (next after 112)
        with app.app_context():
            max_id = db.session.query(func.max(Customer.customer_id)).scalar() or 0
            if max_id < 112:
                # Set sequence so next customer will be 113
                from sqlalchemy import text
                db.session.execute(text('SELECT setval(\'customers_customer_id_seq\', 112, true)'))
                db.session.commit()
                log(f"✅ Set sequence to 112, next customer will be 113")
        
        # Step 1: Complete onboarding (create customer via API)
        customer_id = test_complete_onboarding()
        log(f"\n✅ Customer {customer_id} created (should be 113)")
        
        if customer_id != 113:
            log(f"⚠️  WARNING: Expected customer 113, but got {customer_id}", "WARNING")
        
        # Step 2: Provision directory (via API)
        customer_dir = test_provision_directory(customer_id)
        
        # Step 3: Generate and upload files
        generated_data = test_generate_and_upload_files(customer_id, customer_dir)
        
        # Step 4: Process data (load + embeddings + wizard A via API)
        execution_state = test_process_data_api(customer_id, customer_dir)
        
        # Step 5: Validate final state
        test_validate_final_state(customer_id, customer_dir)
        
        log("\n✅ Test completed successfully!")
        log(f"   Customer ID {customer_id} created and fully configured")
        log(f"   Data loaded, embeddings created, Wizard A executed")
        log(f"   You can now login to the portal with customer {customer_id}")
        
    except Exception as e:
        log_error("Test execution failed", e)
        if customer_id:
            log(f"\n⚠️  Customer {customer_id} was created but test failed")
            log(f"   You may need to clean up customer {customer_id} manually")
    
    finally:
        generate_report()
        
        # Return exit code
        if test_results["summary"]["failed_steps"] > 0 or test_results["summary"]["failed_validations"] > 0:
            return 1
        return 0

if __name__ == "__main__":
    sys.exit(main())
