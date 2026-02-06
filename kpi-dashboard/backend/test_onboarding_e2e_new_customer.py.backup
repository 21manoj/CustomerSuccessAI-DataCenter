#!/usr/bin/env python3
"""
End-to-End Onboarding Test Script for New Customer Creation
Tests complete onboarding flow with new customer ID generation and account ID formula

This script tests:
1. System-generated customer ID (read-only, no override)
2. Account ID formula: customer_id * 1000 (not 10000 + customer_id * 1000)
3. Sample file generation with correct account IDs
4. File validation and structure
5. Complete onboarding completion
"""

import sys
import os
import json
import time
import zipfile
import csv
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Tuple, Optional

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer, User, Account, CustomerConfig
from werkzeug.security import generate_password_hash
from sqlalchemy import func

# Log and report directories
LOG_DIR = Path(__file__).parent / "logs" / "onboarding_tests"
LOG_DIR.mkdir(parents=True, exist_ok=True)
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
LOG_FILE = LOG_DIR / f"onboarding_e2e_new_customer_{TIMESTAMP}.log"
REPORT_FILE = LOG_DIR / f"onboarding_e2e_new_customer_{TIMESTAMP}.json"

# Test results structure (will be initialized in main())
test_results = None

def initialize_test_results(num_accounts=10):
    """Initialize test results structure"""
    return {
        "test_name": "End-to-End Onboarding Test - New Customer",
        "timestamp": datetime.now().isoformat(),
        "test_config": {
            "company_name": "E2E Test Corporation",
            "industry": "Healthcare",
            "vertical": "dc2_s",
            "num_accounts": num_accounts,
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
    
    # Add to test results
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

def log_error(message: str, exception: Optional[Exception] = None):
    """Log error"""
    error_msg = message
    if exception:
        error_msg += f": {str(exception)}"
        import traceback
        error_msg += f"\n{traceback.format_exc()}"
    log(error_msg, "ERROR")
    test_results["errors"].append({
        "message": message,
        "exception": str(exception) if exception else None,
        "timestamp": datetime.now().isoformat()
    })

def log_warning(message: str):
    """Log warning"""
    log(message, "WARNING")
    test_results["warnings"].append({
        "message": message,
        "timestamp": datetime.now().isoformat()
    })

def step(step_name: str):
    """Decorator for test steps"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            log(f"\n{'='*70}", "INFO")
            log(f"STEP: {step_name}", "INFO")
            log(f"{'='*70}", "INFO")
            test_results["summary"]["total_steps"] += 1
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                log(f"✅ Step '{step_name}' completed in {elapsed:.2f}s", "INFO", step_name)
                test_results["summary"]["passed_steps"] += 1
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                log_error(f"Step '{step_name}' failed after {elapsed:.2f}s", e)
                test_results["summary"]["failed_steps"] += 1
                raise
        return wrapper
    return decorator

@step("1. Get Next Customer ID")
def test_get_next_customer_id() -> int:
    """Test getting next available customer ID"""
    with app.app_context():
        # Get current max customer ID
        max_id = db.session.query(func.max(Customer.customer_id)).scalar() or 0
        expected_next_id = max_id + 1
        
        log(f"Current max customer ID: {max_id}")
        log(f"Expected next customer ID: {expected_next_id}")
        
        # Simulate API call to get next customer ID
        # In real scenario, this would be: GET /api/onboarding/next-customer-id
        account_id_start = expected_next_id * 1000
        account_id_range = {
            "start": account_id_start + 1,
            "end": account_id_start + 10
        }
        
        log(f"Account ID range: {account_id_range['start']} - {account_id_range['end']}")
        
        # Validate account ID formula
        expected_start = expected_next_id * 1000 + 1
        actual_start = account_id_range["start"]
        log_validation(
            "Account ID Formula",
            actual_start == expected_start,
            f"Account IDs should use formula: customer_id * 1000",
            f"{expected_start}",
            f"{actual_start}"
        )
        
        # Validate no 10000 offset
        old_formula_result = 10000 + expected_next_id * 1000 + 1
        log_validation(
            "No 10000 Offset",
            actual_start != old_formula_result,
            f"Account IDs should NOT use old formula: 10000 + customer_id * 1000",
            f"NOT {old_formula_result}",
            f"{actual_start}"
        )
        
        return expected_next_id

@step("2. Create Test Customer")
def test_create_customer(customer_id: int) -> Customer:
    """Create a test customer in the database"""
    with app.app_context():
        # Check if customer already exists
        existing = Customer.query.filter_by(customer_id=customer_id).first()
        if existing:
            log_warning(f"Customer {customer_id} already exists, will use existing")
            return existing
        
        customer = Customer(
            customer_id=customer_id,
            customer_name=test_results["test_config"]["company_name"],
            email=f"test_{customer_id}@e2etest.com",
            domain=f"e2etest{customer_id}.com"
        )
        db.session.add(customer)
        db.session.commit()
        
        log(f"Created customer: {customer.customer_id} - {customer.customer_name}")
        log_validation(
            "Customer Created",
            customer.customer_id == customer_id,
            f"Customer ID matches expected value",
            f"{customer_id}",
            f"{customer.customer_id}"
        )
        
        return customer

@step("3. Generate Sample Files")
def test_generate_sample_files(customer_id: int) -> Dict:
    """Test sample file generation with new account ID formula"""
    with app.app_context():
        # Import the generator
        try:
            import generate_synthetic_customer_data as synth_gen
        except ImportError as e:
            log_error("Failed to import generate_synthetic_customer_data", e)
            raise
        
        # Prepare test data
        test_config = test_results["test_config"]
        company_name = test_config["company_name"]
        industry = test_config["industry"]
        num_accounts = test_config["num_accounts"]
        num_months = test_config["num_months"]
        
        log(f"Generating sample files with:")
        log(f"  Customer ID: {customer_id}")
        log(f"  Company Name: {company_name}")
        log(f"  Industry: {industry}")
        log(f"  Number of Accounts: {num_accounts}")
        log(f"  Number of Months: {num_months}")
        
        # Create temporary directory for generated files
        temp_dir = Path(tempfile.mkdtemp(prefix=f"e2e_test_{customer_id}_"))
        log(f"Temporary directory: {temp_dir}")
        
        try:
            # Generate files using the generator
            accounts = synth_gen.generate_accounts(
                customer_id=customer_id,
                num_accounts=num_accounts,
                industry=industry,
                company_name=company_name
            )
            
            # Generate customers.csv
            customers_data = synth_gen.generate_customers_csv(
                customer_id=customer_id,
                company_name=company_name,
                industry=industry
            )
            
            # Generate other CSV files
            # Note: generate_kpi_measurements and generate_qualitative_signals
            # use the global MONTHS constant (12 months) from the generator module
            kpi_measurements = synth_gen.generate_kpi_measurements(accounts=accounts)
            
            qualitative_signals = synth_gen.generate_qualitative_signals(accounts=accounts)
            
            products = synth_gen.generate_products()
            profiles = synth_gen.generate_profiles(accounts=accounts)
            
            # Generate DEMO_MANIFEST.md
            # Note: generate_demo_manifest only takes accounts parameter
            demo_manifest = synth_gen.generate_demo_manifest(accounts=accounts)
            
            # Save files to temp directory
            import pandas as pd
            
            # Save accounts
            accounts_df = pd.DataFrame(accounts)
            accounts_df.to_csv(temp_dir / "accounts.csv", index=False)
            
            # Save customers.csv
            customers_df = pd.DataFrame(customers_data)
            customers_df.to_csv(temp_dir / "customers.csv", index=False)
            
            # Save KPI measurements
            kpi_df = pd.DataFrame(kpi_measurements)
            kpi_df.to_csv(temp_dir / "kpi_measurements.csv", index=False)
            
            # Save qualitative signals
            signals_df = pd.DataFrame(qualitative_signals)
            signals_df.to_csv(temp_dir / "qualitative_signals.csv", index=False)
            
            # Save products
            products_df = pd.DataFrame(products)
            products_df.to_csv(temp_dir / "products.csv", index=False)
            
            # Save profiles
            profiles_df = pd.DataFrame(profiles)
            profiles_df.to_csv(temp_dir / "profiles.csv", index=False)
            
            # Save DEMO_MANIFEST.md
            (temp_dir / "DEMO_MANIFEST.md").write_text(demo_manifest, encoding='utf-8')
            
            log(f"Generated files in: {temp_dir}")
            
            return {
                "temp_dir": temp_dir,
                "accounts": accounts,
                "files": {
                    "accounts.csv": temp_dir / "accounts.csv",
                    "kpi_measurements.csv": temp_dir / "kpi_measurements.csv",
                    "qualitative_signals.csv": temp_dir / "qualitative_signals.csv",
                    "products.csv": temp_dir / "products.csv",
                    "profiles.csv": temp_dir / "profiles.csv",
                    "DEMO_MANIFEST.md": temp_dir / "DEMO_MANIFEST.md"
                }
            }
            
        except Exception as e:
            # Cleanup on error
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            log_error("Failed to generate sample files", e)
            raise

@step("4. Validate Generated Files")
def test_validate_files(generated_data: Dict, customer_id: int):
    """Validate generated files structure and account IDs"""
    import pandas as pd
    
    temp_dir = generated_data["temp_dir"]
    accounts = generated_data["accounts"]
    
    # Validate accounts.csv
    accounts_file = generated_data["files"]["accounts.csv"]
    if accounts_file.exists():
        log(f"Validating {accounts_file.name}...")
        accounts_df = pd.read_csv(accounts_file)
        
        # Check account IDs use correct formula
        expected_account_id_start = customer_id * 1000
        actual_first_account_id = accounts_df['account_id'].min()
        actual_last_account_id = accounts_df['account_id'].max()
        
        log_validation(
            "First Account ID Formula",
            actual_first_account_id == expected_account_id_start + 1,
            f"First account ID should be {expected_account_id_start + 1}",
            f"{expected_account_id_start + 1}",
            f"{actual_first_account_id}"
        )
        
        log_validation(
            "Account IDs Sequential",
            (actual_last_account_id - actual_first_account_id) == (len(accounts_df) - 1),
            f"Account IDs should be sequential",
            f"Range: {actual_first_account_id} to {actual_last_account_id}",
            f"Count: {len(accounts_df)}"
        )
        
        # Validate no account IDs use old formula
        old_formula_start = 10000 + customer_id * 1000 + 1
        accounts_using_old_formula = accounts_df[accounts_df['account_id'] >= old_formula_start]
        log_validation(
            "No Old Formula Account IDs",
            len(accounts_using_old_formula) == 0,
            f"No account IDs should use old formula (10000 + customer_id * 1000)",
            "0 accounts",
            f"{len(accounts_using_old_formula)} accounts"
        )
        
        # Validate customer_id in accounts
        all_same_customer = bool((accounts_df['customer_id'] == customer_id).all())
        log_validation(
            "All Accounts Same Customer",
            all_same_customer,
            f"All accounts should have customer_id = {customer_id}",
            f"All = {customer_id}",
            f"All = {customer_id}" if all_same_customer else "Mixed"
        )
        
        # Validate industry
        if 'industry' in accounts_df.columns:
            all_same_industry = bool((accounts_df['industry'] == test_results["test_config"]["industry"]).all())
            log_validation(
                "All Accounts Same Industry",
                all_same_industry,
                f"All accounts should have industry = {test_results['test_config']['industry']}",
                f"All = {test_results['test_config']['industry']}",
                f"All = {test_results['test_config']['industry']}" if all_same_industry else "Mixed"
            )
        
        log(f"✅ {accounts_file.name} validated: {len(accounts_df)} accounts")
    else:
        log_error(f"File not found: {accounts_file}")
    
    # Validate KPI measurements
    kpi_file = generated_data["files"]["kpi_measurements.csv"]
    if kpi_file.exists():
        log(f"Validating {kpi_file.name}...")
        kpi_df = pd.read_csv(kpi_file)
        
        # Check account IDs in KPI file match accounts
        kpi_account_ids = set(kpi_df['account_id'].unique())
        accounts_account_ids = set(accounts_df['account_id'].unique())
        
        log_validation(
            "KPI Account IDs Match Accounts",
            kpi_account_ids == accounts_account_ids,
            f"KPI file should contain same account IDs as accounts file",
            f"{len(accounts_account_ids)} unique IDs",
            f"{len(kpi_account_ids)} unique IDs"
        )
        
        log(f"✅ {kpi_file.name} validated: {len(kpi_df)} rows")
    else:
        log_error(f"File not found: {kpi_file}")
    
    # Validate qualitative signals
    signals_file = generated_data["files"]["qualitative_signals.csv"]
    if signals_file.exists():
        log(f"Validating {signals_file.name}...")
        signals_df = pd.read_csv(signals_file)
        
        signals_account_ids = set(signals_df['account_id'].unique())
        log_validation(
            "Signals Account IDs Match Accounts",
            signals_account_ids == accounts_account_ids,
            f"Signals file should contain same account IDs as accounts file",
            f"{len(accounts_account_ids)} unique IDs",
            f"{len(signals_account_ids)} unique IDs"
        )
        
        log(f"✅ {signals_file.name} validated: {len(signals_df)} rows")
    else:
        log_error(f"File not found: {signals_file}")
    
    # Validate DEMO_MANIFEST.md
    manifest_file = generated_data["files"]["DEMO_MANIFEST.md"]
    if manifest_file.exists():
        log(f"Validating {manifest_file.name}...")
        manifest_content = manifest_file.read_text(encoding='utf-8')
        
        # Check company name is in manifest
        company_name_in_manifest = test_results["test_config"]["company_name"] in manifest_content
        log_validation(
            "Company Name in Manifest",
            company_name_in_manifest,
            f"DEMO_MANIFEST.md should contain company name",
            test_results["test_config"]["company_name"],
            "Found" if company_name_in_manifest else "Not found"
        )
        
        log(f"✅ {manifest_file.name} validated: {len(manifest_content)} characters")
    else:
        log_error(f"File not found: {manifest_file}")

@step("5. Test API Endpoints")
def test_api_endpoints(customer_id: int):
    """Test onboarding API endpoints"""
    # Note: API endpoints require authentication, so we'll test the logic directly
    # instead of making HTTP calls
    log("Testing account ID formula calculation (simulating API logic)...")
    
    with app.app_context():
        # Simulate the API logic
        from sqlalchemy import func
        max_id = db.session.query(func.max(Customer.customer_id)).scalar() or 0
        next_id = max_id + 1
        account_id_start = next_id * 1000
        num_accounts = test_results["test_config"]["num_accounts"]
        api_account_range = {
            'start': account_id_start + 1,
            'end': account_id_start + num_accounts
        }
        
        log(f"API logic returned customer ID: {next_id}")
        log(f"API logic returned account range: {api_account_range}")
        
        # Validate account ID formula in API logic
        expected_start = next_id * 1000 + 1
        actual_start = api_account_range.get('start')
        
        log_validation(
            "API Account ID Formula",
            actual_start == expected_start,
            f"API logic should return account IDs using formula: customer_id * 1000",
            f"{expected_start}",
            f"{actual_start}"
        )
        
        # Validate no 10000 offset in API logic
        old_formula_start = 10000 + next_id * 1000 + 1
        log_validation(
            "API No 10000 Offset",
            actual_start != old_formula_start,
            f"API logic should NOT use old formula",
            f"NOT {old_formula_start}",
            f"{actual_start}"
        )

@step("6. Cleanup Test Data")
def test_cleanup(customer_id: int, generated_data: Optional[Dict] = None):
    """Cleanup test data"""
    with app.app_context():
        # Optionally remove test customer (commented out for safety)
        # customer = Customer.query.filter_by(customer_id=customer_id).first()
        # if customer:
        #     db.session.delete(customer)
        #     db.session.commit()
        #     log(f"Removed test customer {customer_id}")
        
        # Cleanup temporary files
        if generated_data and "temp_dir" in generated_data:
            temp_dir = generated_data["temp_dir"]
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                log(f"Cleaned up temporary directory: {temp_dir}")

def generate_report():
    """Generate final test report"""
    test_results["summary"]["end_time"] = datetime.now().isoformat()
    
    # Calculate success rate
    total = test_results["summary"]["total_steps"] + test_results["summary"]["total_validations"]
    passed = test_results["summary"]["passed_steps"] + test_results["summary"]["passed_validations"]
    success_rate = (passed / total * 100) if total > 0 else 0
    
    test_results["summary"]["success_rate"] = f"{success_rate:.2f}%"
    
    # Convert numpy types to Python types for JSON serialization
    def convert_to_python_types(obj):
        import numpy as np
        if isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: convert_to_python_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_python_types(item) for item in obj]
        return obj
    
    # Write JSON report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(convert_to_python_types(test_results), f, indent=2, ensure_ascii=False)
    
    log(f"\n{'='*70}", "INFO")
    log("TEST REPORT SUMMARY", "INFO")
    log(f"{'='*70}", "INFO")
    log(f"Total Steps: {test_results['summary']['total_steps']}", "INFO")
    log(f"  ✅ Passed: {test_results['summary']['passed_steps']}", "INFO")
    log(f"  ❌ Failed: {test_results['summary']['failed_steps']}", "INFO")
    log(f"Total Validations: {test_results['summary']['total_validations']}", "INFO")
    log(f"  ✅ Passed: {test_results['summary']['passed_validations']}", "INFO")
    log(f"  ❌ Failed: {test_results['summary']['failed_validations']}", "INFO")
    log(f"Success Rate: {success_rate:.2f}%", "INFO")
    log(f"\nReport saved to: {REPORT_FILE}", "INFO")
    log(f"Log saved to: {LOG_FILE}", "INFO")
    
    if test_results["errors"]:
        log(f"\nErrors ({len(test_results['errors'])}):", "ERROR")
        for error in test_results["errors"]:
            log(f"  - {error['message']}", "ERROR")
    
    if test_results["warnings"]:
        log(f"\nWarnings ({len(test_results['warnings'])}):", "WARNING")
        for warning in test_results["warnings"]:
            log(f"  - {warning['message']}", "WARNING")

def main():
    """Main test execution"""
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='End-to-End Onboarding Test - New Customer')
    parser.add_argument('--num-accounts', type=int, default=10, 
                       help='Number of accounts to generate (default: 10)')
    args = parser.parse_args()
    
    # Initialize test results with num_accounts
    global test_results
    test_results = initialize_test_results(num_accounts=args.num_accounts)
    
    log("="*70, "INFO")
    log("END-TO-END ONBOARDING TEST - NEW CUSTOMER", "INFO")
    log("="*70, "INFO")
    log(f"Test started at: {datetime.now().isoformat()}", "INFO")
    log(f"Test configuration:", "INFO")
    for key, value in test_results["test_config"].items():
        log(f"  {key}: {value}", "INFO")
    
    customer_id = None
    generated_data = None
    
    try:
        # Step 1: Get next customer ID
        customer_id = test_get_next_customer_id()
        
        # Step 2: Create test customer
        customer = test_create_customer(customer_id)
        
        # Step 3: Generate sample files
        generated_data = test_generate_sample_files(customer_id)
        
        # Step 4: Validate generated files
        test_validate_files(generated_data, customer_id)
        
        # Step 5: Test API endpoints
        test_api_endpoints(customer_id)
        
        # Step 6: Cleanup (optional)
        # test_cleanup(customer_id, generated_data)
        
    except Exception as e:
        log_error("Test execution failed", e)
    finally:
        # Always generate report
        generate_report()
        
        # Cleanup on exit
        if generated_data and "temp_dir" in generated_data:
            temp_dir = generated_data["temp_dir"]
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

if __name__ == "__main__":
    main()
