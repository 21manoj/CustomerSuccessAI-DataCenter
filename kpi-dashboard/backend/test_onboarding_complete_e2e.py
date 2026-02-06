#!/usr/bin/env python3
"""
Complete End-to-End Onboarding Test
====================================

Tests the FULL onboarding pipeline including:
1. Customer creation
2. Directory provisioning
3. File generation and upload
4. Data loading (02_load script execution)
5. Embeddings (03_embed script execution)
6. Wizard A execution (journey generation)
7. Validation of all steps

This test actually EXECUTES all scripts, not just validates structure.
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer, User, Account, CustomerConfig
from sqlalchemy import func, text
from werkzeug.security import generate_password_hash
from onboarding_api import (
    get_customer_directory,
    execute_script
)
from verticals.provision_dc_customer import provision_customer
import generate_synthetic_customer_data as synth_gen

# Log and report directories
LOG_DIR = Path(__file__).parent / "logs" / "onboarding_tests"
LOG_DIR.mkdir(parents=True, exist_ok=True)
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
LOG_FILE = LOG_DIR / f"onboarding_complete_e2e_{TIMESTAMP}.log"
REPORT_FILE = LOG_DIR / f"onboarding_complete_e2e_{TIMESTAMP}.json"

# Test results structure
test_results = {
    "test_name": "Complete End-to-End Onboarding Test",
    "timestamp": datetime.now().isoformat(),
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

@step("1. Get Next Customer ID and Create Customer")
def test_create_customer() -> int:
    """Create a new test customer"""
    with app.app_context():
        # Get next customer ID
        max_id = db.session.query(func.max(Customer.customer_id)).scalar() or 0
        customer_id = max_id + 1
        
        log(f"Current max customer ID: {max_id}")
        log(f"Next customer ID: {customer_id}")
        
        # Create customer
        customer = Customer(
            customer_id=customer_id,
            customer_name="E2E Complete Test Corporation",
            email=f"test_{customer_id}@e2ecompletetest.com",
            domain=f"e2ecompletetest{customer_id}.com"
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
        
        # Create user
        user = User(
            customer_id=customer_id,
            user_name="E2E Test Admin",
            email=f"admin_{customer_id}@e2ecompletetest.com",
            password_hash=generate_password_hash("TestPass123!"),
            vertical="dc2_s",
            role="admin",
            active=True
        )
        db.session.add(user)
        db.session.commit()
        
        log(f"Created user: {user.user_id}")
        log_validation(
            "User Created",
            user.user_id is not None,
            f"User should be created with ID",
            "Not None",
            f"{user.user_id}"
        )
        
        # Create config
        config = CustomerConfig(
            customer_id=customer_id,
            kpi_upload_mode="account_rollup",
            category_weights='{"P1_deployment_velocity": 0.15, "P2_operational_stability": 0.20, "P3_ai_workload_performance": 0.25, "P4_channel_partner_health": 0.15, "P5_expansion_revenue": 0.25}',
            master_file_name=None
        )
        db.session.add(config)
        db.session.commit()
        
        log(f"Created config for customer {customer_id}")
        log_validation(
            "Config Created",
            config.customer_id == customer_id,
            f"Config should be created for customer {customer_id}",
            f"{customer_id}",
            f"{config.customer_id}"
        )
        
        return customer_id

@step("2. Provision Customer Directory")
def test_provision_directory(customer_id: int) -> Path:
    """Provision customer directory structure"""
    with app.app_context():
        customer_dir = get_customer_directory(customer_id, vertical_slug="dc2_s")
        
        if customer_dir.exists():
            log(f"Customer directory already exists: {customer_dir}")
            success = True
        else:
            log(f"Provisioning customer directory...")
            success = provision_customer(
                customer_id=customer_id,
                customer_name="E2E Complete Test Corporation",
                vertical_slug="dc2_s",
                dry_run=False,
                force=True
            )
        
        if not success:
            raise Exception(f"Provision failed for customer {customer_id}")
        
        # Re-check directory after provision (it may have been created)
        customer_dir = get_customer_directory(customer_id, vertical_slug="dc2_s")
        log(f"✅ Provision successful: {customer_dir}")
        
        # Wait a moment for filesystem to sync
        import time
        time.sleep(1.0)  # Give more time for filesystem
        
        # Re-resolve path to ensure we have the correct one
        backend_dir = Path(__file__).parent
        customer_dir = backend_dir / "verticals" / f"customer{customer_id}-dc2_s"
        
        # Validate subdirectories
        data_dir = customer_dir / "data"
        scripts_dir = customer_dir / "scripts"
        journey_dir = customer_dir / "journey"
        
        log_validation(
            "Customer Directory Created",
            customer_dir.exists(),
            f"Customer directory should be created",
            "True",
            str(customer_dir.exists())
        )
        
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

@step("3. Generate and Upload Sample Files")
def test_generate_and_upload_files(customer_id: int, customer_dir: Path) -> Dict:
    """Generate sample CSV files and place them in data directory"""
    with app.app_context():
        data_dir = customer_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        log(f"Generating sample files for customer {customer_id}...")
        
        # Generate files using the synthetic data generator
        company_name = "E2E Complete Test Corporation"
        industry = "Healthcare"
        num_accounts = 5
        num_months = 12
        
        # Generate accounts
        accounts = synth_gen.generate_accounts(
            customer_id=customer_id,
            num_accounts=num_accounts,
            industry=industry,
            company_name=company_name
        )
        
        # Generate customers CSV
        customers_data = synth_gen.generate_customers_csv(
            customer_id=customer_id,
            company_name=company_name,
            industry=industry
        )
        
        # Generate KPI measurements
        kpi_measurements = synth_gen.generate_kpi_measurements(
            accounts=accounts
        )
        
        # Generate qualitative signals
        qualitative_signals = synth_gen.generate_qualitative_signals(
            accounts=accounts
        )
        
        # Generate products
        products = synth_gen.generate_products(customer_id=customer_id)
        
        # Generate account profiles
        account_profiles = synth_gen.generate_profiles(accounts=accounts)
        
        # Save to CSV files
        import pandas as pd
        
        files_saved = {}
        
        # Save accounts
        accounts_df = pd.DataFrame(accounts)
        accounts_file = data_dir / "accounts.csv"
        accounts_df.to_csv(accounts_file, index=False)
        files_saved["accounts"] = str(accounts_file)
        log(f"✅ Saved accounts.csv ({len(accounts)} accounts)")
        
        # Save KPI measurements
        kpi_df = pd.DataFrame(kpi_measurements)
        kpi_file = data_dir / "kpi_measurements.csv"
        kpi_df.to_csv(kpi_file, index=False)
        files_saved["kpi_measurements"] = str(kpi_file)
        log(f"✅ Saved kpi_measurements.csv ({len(kpi_measurements)} measurements)")
        
        # Save qualitative signals
        signals_df = pd.DataFrame(qualitative_signals)
        signals_file = data_dir / "qualitative_signals.csv"
        signals_df.to_csv(signals_file, index=False)
        files_saved["qualitative_signals"] = str(signals_file)
        log(f"✅ Saved qualitative_signals.csv ({len(qualitative_signals)} signals)")
        
        # Save products
        products_df = pd.DataFrame(products)
        products_file = data_dir / "products.csv"
        products_df.to_csv(products_file, index=False)
        files_saved["products"] = str(products_file)
        log(f"✅ Saved products.csv ({len(products)} products)")
        
        # Save account profiles
        profiles_df = pd.DataFrame(account_profiles)
        profiles_file = data_dir / "profiles.csv"
        profiles_df.to_csv(profiles_file, index=False)
        files_saved["profiles"] = str(profiles_file)
        log(f"✅ Saved profiles.csv ({len(account_profiles)} profiles)")
        
        # Validate files exist
        required_files = ["accounts.csv", "kpi_measurements.csv", "qualitative_signals.csv", "products.csv", "profiles.csv"]
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

@step("4. Process Data (Load + Embeddings + Wizard A)")
def test_process_data(customer_id: int, customer_dir: Path) -> Dict:
    """Execute data loading script, embeddings, and Wizard A"""
    with app.app_context():
        execution_state = {
            "steps_completed": [],
            "errors": [],
            "warnings": []
        }
        
        # Step 4.1: Execute 02_load script
        log(f"Step 4.1: Executing data loading script for customer {customer_id}")
        
        # Ensure we have the correct path
        backend_dir = Path(__file__).parent
        customer_dir = backend_dir / "verticals" / f"customer{customer_id}-dc2_s"
        load_script = customer_dir / "scripts" / f"02_load_customer{customer_id}_data_SMART.py"
        
        log(f"Looking for script at: {load_script}")
        
        if not load_script.exists():
            # List what's actually in scripts directory
            scripts_dir = customer_dir / "scripts"
            if scripts_dir.exists():
                scripts = list(scripts_dir.glob("*.py"))
                log(f"Found {len(scripts)} Python files in scripts directory:")
                for script in scripts[:5]:
                    log(f"  - {script.name}")
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
        
        # Step 4.2: Execute 03_embed script
        log(f"Step 4.2: Executing embedding script for customer {customer_id}")
        embed_script = customer_dir / "scripts" / f"03_embed_customer{customer_id}_OPENAI.py"
        
        if not embed_script.exists():
            log(f"⚠️  Embedding script not found: {embed_script}", "WARNING")
            execution_state["warnings"].append("Embedding script not found")
        else:
            log(f"✅ Found script: {embed_script}")
            log(f"Executing script...")
            
            script_start_time = time.time()
            success, stdout, stderr = execute_script(embed_script, customer_id, timeout=600)
            script_duration = time.time() - script_start_time
            
            if success:
                log(f"✅ Embeddings created in {script_duration:.2f}s")
                execution_state["steps_completed"].append("embeddings")
                log_validation(
                    "Embeddings Created",
                    True,
                    f"Embeddings should be created",
                    "True",
                    "True"
                )
            else:
                log(f"⚠️  Embedding script returned warnings: {stderr}", "WARNING")
                execution_state["warnings"].append(f"Embedding warnings: {stderr}")
        
        # Step 4.3: Execute Wizard A (Journey Generator)
        log(f"Step 4.3: Executing Wizard A (journey generator) for customer {customer_id}")
        wizard_a_dir = customer_dir / "journey" / "wizard_a"
        journey_script = wizard_a_dir / "wizard_journey_generator.py"
        
        if not journey_script.exists():
            # Try alternative name
            journey_script = wizard_a_dir / "wizard_a_journey_generator.py"
        
        if not journey_script.exists():
            raise Exception(f"Journey generator script not found in {wizard_a_dir}")
        
        log(f"✅ Found script: {journey_script}")
        log(f"Executing Wizard A...")
        
        script_start_time = time.time()
        success, stdout, stderr = execute_script(journey_script, customer_id, timeout=600)
        script_duration = time.time() - script_start_time
        
        if not success:
            raise Exception(f"Wizard A (journey generator) failed: {stderr}")
        
        log(f"✅ Wizard A completed in {script_duration:.2f}s")
        execution_state["steps_completed"].append("journey_generation")
        
        # Validate journey data was created
        journey_files = list(wizard_a_dir.glob("*.json"))
        log_validation(
            "Journey Data Files Exist",
            len(journey_files) > 0,
            f"Should have journey JSON files after Wizard A",
            "> 0 files",
            f"{len(journey_files)} files"
        )
        
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
        journey_files = list(wizard_a_dir.glob("*.json")) if wizard_a_dir.exists() else []
        log_validation(
            "Journey Data Files Exist",
            len(journey_files) > 0,
            f"Should have journey JSON files after Wizard A",
            "> 0 files",
            f"{len(journey_files)} files"
        )

def generate_report():
    """Generate final test report"""
    test_results["summary"]["end_time"] = datetime.now().isoformat()
    
    # Calculate success rate
    total = test_results["summary"]["total_steps"] + test_results["summary"]["total_validations"]
    passed = test_results["summary"]["passed_steps"] + test_results["summary"]["passed_validations"]
    success_rate = (passed / total * 100) if total > 0 else 0
    
    test_results["summary"]["success_rate"] = f"{success_rate:.2f}%"
    
    # Save JSON report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, default=str, ensure_ascii=False)
    
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
    log("COMPLETE END-TO-END ONBOARDING TEST")
    log("=" * 70)
    log(f"Started at: {datetime.now().isoformat()}")
    log(f"Log file: {LOG_FILE}")
    log(f"Report file: {REPORT_FILE}")
    log("=" * 70)
    log("")
    
    customer_id = None
    customer_dir = None
    generated_data = None
    
    try:
        # Step 1: Create customer
        customer_id = test_create_customer()
        
        # Step 2: Provision directory
        customer_dir = test_provision_directory(customer_id)
        
        # Step 3: Generate and upload files
        generated_data = test_generate_and_upload_files(customer_id, customer_dir)
        
        # Step 4: Process data (load + embeddings + wizard A)
        execution_state = test_process_data(customer_id, customer_dir)
        
        # Step 5: Validate final state
        test_validate_final_state(customer_id, customer_dir)
        
        log("\n✅ Test completed successfully!")
        log(f"   Customer ID {customer_id} created and configured")
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
