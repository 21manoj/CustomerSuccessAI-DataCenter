#!/usr/bin/env python3
"""
Customer 19 End-to-End Onboarding Test
Executes complete onboarding flow including all scripts
CORRECTED ORDER: Provision FIRST, then generate data directly into provisioned directory
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
import subprocess

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer, User, Account, CustomerConfig, KPIUpload
from onboarding_api import (
    get_customer_directory,
    calculate_account_id_range,
    execute_script
)
from onboarding_logger import get_onboarding_logger, close_onboarding_session

# Test configuration
CUSTOMER_ID = 19
CUSTOMER_NAME = "Synthetic Data Corp"

# Log file
LOG_DIR = Path(__file__).parent / "logs" / "onboarding_tests"
LOG_DIR.mkdir(parents=True, exist_ok=True)
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
LOG_FILE = LOG_DIR / f"customer19_e2e_test_{TIMESTAMP}.log"
REPORT_FILE = LOG_DIR / f"customer19_e2e_report_{TIMESTAMP}.json"

def log(message, level="INFO"):
    """Log message to file and console"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] [{level}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + '\n')

def test_customer_19_e2e():
    """Test Customer 19 complete end-to-end onboarding"""
    log("=" * 70)
    log("CUSTOMER 19 END-TO-END ONBOARDING TEST")
    log("=" * 70)
    log(f"Customer ID: {CUSTOMER_ID}")
    log(f"Customer Name: {CUSTOMER_NAME}")
    log(f"Log file: {LOG_FILE}")
    log(f"Report file: {REPORT_FILE}")
    log("=" * 70)
    
    results = {
        "customer_id": CUSTOMER_ID,
        "steps": [],
        "errors": [],
        "warnings": [],
        "start_time": datetime.now().isoformat()
    }
    
    # Initialize onboarding logger
    onboarding_logger = get_onboarding_logger(CUSTOMER_ID, CUSTOMER_NAME)
    
    with app.app_context():
        # STEP 0: Provision customer directory FIRST
        log("\n[0/8] Provisioning customer directory structure...")
        try:
            verticals_dir = Path(__file__).parent / "verticals"
            customer_dir = verticals_dir / f"customer{CUSTOMER_ID}-dc2_s"
            
            # Check if already provisioned
            if customer_dir.exists():
                log(f"⚠️  Customer directory already exists: {customer_dir}", "WARNING")
                log("   Removing and re-provisioning...")
                import shutil
                shutil.rmtree(customer_dir)
            
            # Run provisioning script
            provision_script = verticals_dir / "provision_dc_customer.py"
            if not provision_script.exists():
                log(f"❌ Provisioning script not found: {provision_script}", "ERROR")
                results["errors"].append(f"Provisioning script not found: {provision_script}")
                return results
            
            log(f"✅ Found provisioning script: {provision_script}")
            log(f"   Running: python3 {provision_script.name} --customer-id {CUSTOMER_ID} --customer-name '{CUSTOMER_NAME}' --force")
            
            provision_result = subprocess.run(
                [sys.executable, str(provision_script), 
                 "--customer-id", str(CUSTOMER_ID),
                 "--customer-name", CUSTOMER_NAME,
                 "--force"],
                cwd=str(verticals_dir),
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if provision_result.returncode != 0:
                log(f"❌ Provisioning failed: {provision_result.stderr}", "ERROR")
                results["errors"].append(f"Provisioning failed: {provision_result.stderr}")
                return results
            
            log("✅ Provisioning completed successfully")
            log(f"   Created directory: {customer_dir}")
            results["steps"].append({
                "step": "provision",
                "status": "success",
                "directory": str(customer_dir)
            })
            
        except Exception as e:
            log(f"❌ Provisioning error: {e}", "ERROR")
            results["errors"].append(f"Provisioning error: {str(e)}")
            return results
        
        # STEP 0.5: Generate synthetic data DIRECTLY into provisioned directory
        log("\n[0.5/8] Generating synthetic data directly into provisioned directory...")
        try:
            data_dir = customer_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            
            generate_script = Path(__file__).parent / "generate_synthetic_customer_data.py"
            if not generate_script.exists():
                log(f"❌ Generate script not found: {generate_script}", "ERROR")
                results["errors"].append(f"Generate script not found: {generate_script}")
                return results
            
            log(f"✅ Found generate script: {generate_script}")
            log(f"   Running: python3 {generate_script.name} --customer-id {CUSTOMER_ID} --num-accounts 20 --output-dir {data_dir}")
            
            generate_result = subprocess.run(
                [sys.executable, str(generate_script),
                 "--customer-id", str(CUSTOMER_ID),
                 "--num-accounts", "20",
                 "--output-dir", str(data_dir)],
                cwd=str(Path(__file__).parent),
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if generate_result.returncode != 0:
                log(f"❌ Data generation failed: {generate_result.stderr}", "ERROR")
                results["errors"].append(f"Data generation failed: {generate_result.stderr}")
                return results
            
            log("✅ Synthetic data generated successfully")
            log(f"   Output directory: {data_dir}")
            results["steps"].append({
                "step": "generate_data",
                "status": "success",
                "output_directory": str(data_dir)
            })
            
        except Exception as e:
            log(f"❌ Data generation error: {e}", "ERROR")
            results["errors"].append(f"Data generation error: {str(e)}")
            return results
        
        # Step 1: Verify directory and files
        log("\n[1/8] Verifying customer directory and data files...")
        try:
            if not customer_dir.exists():
                log(f"❌ Customer directory not found: {customer_dir}", "ERROR")
                results["errors"].append(f"Directory not found: {customer_dir}")
                return results
            
            log(f"✅ Customer directory exists: {customer_dir}")
            
            # Check required files
            required_files = ["accounts.csv", "kpi_measurements.csv"]
            missing_files = [f for f in required_files if not (data_dir / f).exists()]
            
            if missing_files:
                log(f"❌ Missing required files: {missing_files}", "ERROR")
                results["errors"].append(f"Missing files: {missing_files}")
                return results
            
            log(f"✅ All required files present in {data_dir}")
            results["steps"].append({
                "step": "verify_files",
                "status": "success",
                "data_directory": str(data_dir)
            })
            
        except Exception as e:
            log(f"❌ Verification error: {e}", "ERROR")
            results["errors"].append(f"Verification error: {str(e)}")
            return results
        
        # Step 2: Verify customer in database
        log("\n[2/8] Verifying customer in database...")
        try:
            customer = Customer.query.filter(
                (Customer.email == "admin@synthetic-data.com") |
                (Customer.domain == "synthetic-data.com")
            ).first()
            
            if not customer:
                log("⚠️  Customer not found in database (will be created by complete endpoint)", "WARNING")
                results["warnings"].append("Customer not in database")
            else:
                log(f"✅ Customer found: ID {customer.customer_id}, Name: {customer.customer_name}")
                results["steps"].append({
                    "step": "verify_customer",
                    "status": "exists",
                    "customer_id": customer.customer_id
                })
        except Exception as e:
            log(f"⚠️  Database check error: {e}", "WARNING")
            results["warnings"].append(f"Database check: {str(e)}")
        
        # Step 3: Execute data loading script
        log("\n[3/8] Executing data loading script...")
        try:
            load_script = customer_dir / "scripts" / f"02_load_customer{CUSTOMER_ID}_data_SMART.py"
            
            if not load_script.exists():
                # Try alternative location
                alt_script = customer_dir.parent / "_template" / "scripts" / f"02_load_customer{CUSTOMER_ID}_data_SMART.py"
                if alt_script.exists():
                    load_script = alt_script
                else:
                    log(f"❌ Data loading script not found", "ERROR")
                    results["errors"].append("Data loading script not found")
            else:
                log(f"✅ Found script: {load_script}")
                onboarding_logger.log_script_start('02_load_data', str(load_script))
                
                script_start = time.time()
                success, stdout, stderr = execute_script(load_script, CUSTOMER_ID, timeout=600)
                script_duration = time.time() - script_start
                
                if success:
                    log(f"✅ Data loading completed in {script_duration:.2f}s")
                    log(f"   Output preview: {stdout[:200]}")
                    onboarding_logger.log_script_success('02_load_data', stdout, script_duration)
                    results["steps"].append({
                        "step": "load_data",
                        "status": "success",
                        "duration_seconds": round(script_duration, 2)
                    })
                else:
                    log(f"❌ Data loading failed: {stderr[:500]}", "ERROR")
                    onboarding_logger.log_script_error('02_load_data', stderr, script_duration)
                    results["errors"].append(f"Data loading failed: {stderr[:200]}")
                    
        except Exception as e:
            log(f"❌ Data loading error: {e}", "ERROR")
            onboarding_logger.log_script_error('02_load_data', str(e), 0)
            results["errors"].append(f"Data loading error: {str(e)}")
        
        # Step 4: Execute embedding script
        log("\n[4/8] Executing embedding script...")
        try:
            embed_script = customer_dir / "scripts" / f"03_embed_customer{CUSTOMER_ID}_OPENAI.py"
            
            if not embed_script.exists():
                log(f"⚠️  Embedding script not found (optional): {embed_script}", "WARNING")
                results["warnings"].append("Embedding script not found")
            else:
                log(f"✅ Found script: {embed_script}")
                onboarding_logger.log_script_start('03_embed_data', str(embed_script))
                
                script_start = time.time()
                success, stdout, stderr = execute_script(embed_script, CUSTOMER_ID, timeout=600)
                script_duration = time.time() - script_start
                
                if success:
                    log(f"✅ Embedding completed in {script_duration:.2f}s")
                    onboarding_logger.log_script_success('03_embed_data', stdout, script_duration)
                    results["steps"].append({
                        "step": "embed_data",
                        "status": "success",
                        "duration_seconds": round(script_duration, 2)
                    })
                else:
                    log(f"⚠️  Embedding warnings: {stderr[:200]}", "WARNING")
                    onboarding_logger.log_script_error('03_embed_data', stderr, script_duration)
                    results["warnings"].append(f"Embedding warnings: {stderr[:200]}")
                    
        except Exception as e:
            log(f"⚠️  Embedding error: {e}", "WARNING")
            results["warnings"].append(f"Embedding error: {str(e)}")
        
        # Step 5: Execute validation script
        log("\n[5/8] Executing validation script...")
        try:
            validate_script = customer_dir / "scripts" / f"04_validate_data_integrity.py"
            
            if not validate_script.exists():
                log(f"⚠️  Validation script not found (optional): {validate_script}", "WARNING")
                results["warnings"].append("Validation script not found")
            else:
                log(f"✅ Found script: {validate_script}")
                onboarding_logger.log_script_start('04_validate_data', str(validate_script))
                
                script_start = time.time()
                success, stdout, stderr = execute_script(validate_script, CUSTOMER_ID, timeout=300)
                script_duration = time.time() - script_start
                
                if success:
                    log(f"✅ Validation completed in {script_duration:.2f}s")
                    onboarding_logger.log_script_success('04_validate_data', stdout, script_duration)
                    results["steps"].append({
                        "step": "validate_data",
                        "status": "success",
                        "duration_seconds": round(script_duration, 2)
                    })
                else:
                    log(f"⚠️  Validation warnings: {stderr[:200]}", "WARNING")
                    onboarding_logger.log_script_error('04_validate_data', stderr, script_duration)
                    results["warnings"].append(f"Validation warnings: {stderr[:200]}")
                    
        except Exception as e:
            log(f"⚠️  Validation error: {e}", "WARNING")
            results["warnings"].append(f"Validation error: {str(e)}")
        
        # Step 6: Execute journey generator (Wizard A)
        log("\n[6/8] Executing journey generator (Wizard A)...")
        try:
            journey_script = customer_dir / "journey" / "wizard_a" / "wizard_a_journey_generator.py"
            
            if not journey_script.exists():
                # Try alternative name
                journey_script = customer_dir / "journey" / "wizard_a" / "wizard_journey_generator.py"
            
            if not journey_script.exists():
                log(f"❌ Journey generator script not found", "ERROR")
                results["errors"].append("Journey generator script not found")
            else:
                log(f"✅ Found script: {journey_script}")
                onboarding_logger.log_script_start('wizard_a_journey', str(journey_script))
                
                # Calculate account ID range
                account_id_start = 10000 + CUSTOMER_ID * 1000
                
                script_start = time.time()
                success, stdout, stderr = execute_script(
                    journey_script, 
                    CUSTOMER_ID, 
                    timeout=600,
                    additional_args=[
                        "--accounts", "20",
                        "--start-id", str(account_id_start),
                        "--pattern-mix", '{"crisis":0.2,"churn":0.15,"stable":0.4,"expansion":0.25}',
                        "--output-dir", f"test_run_{TIMESTAMP}"
                    ],
                    env={**os.environ, 'CUSTOMER_ID': str(CUSTOMER_ID)}
                )
                script_duration = time.time() - script_start
                
                if success:
                    log(f"✅ Journey generation completed in {script_duration:.2f}s")
                    log(f"   Output preview: {stdout[:200]}")
                    onboarding_logger.log_script_success('wizard_a_journey', stdout, script_duration)
                    
                    # Find generated journey files
                    journey_dir = customer_dir / "journey" / "wizard_a"
                    if journey_dir.exists():
                        test_runs = sorted([d for d in journey_dir.iterdir() if d.is_dir() and d.name.startswith("test_run_")], 
                                          key=lambda x: x.stat().st_mtime, reverse=True)
                        if test_runs:
                            latest_run = test_runs[0]
                            log(f"✅ Journey data generated in: {latest_run.name}")
                            results["steps"].append({
                                "step": "journey_generation",
                                "status": "success",
                                "duration_seconds": round(script_duration, 2),
                                "test_run": latest_run.name
                            })
                    
                    results["steps"].append({
                        "step": "journey_generation",
                        "status": "success",
                        "duration_seconds": round(script_duration, 2)
                    })
                else:
                    log(f"❌ Journey generation failed: {stderr[:500]}", "ERROR")
                    onboarding_logger.log_script_error('wizard_a_journey', stderr, script_duration)
                    results["errors"].append(f"Journey generation failed: {stderr[:200]}")
                    
        except Exception as e:
            log(f"❌ Journey generation error: {e}", "ERROR")
            onboarding_logger.log_script_error('wizard_a_journey', str(e), 0)
            results["errors"].append(f"Journey generation error: {str(e)}")
        
        # Step 7: Verify database records
        log("\n[7/8] Verifying database records...")
        try:
            # Check accounts
            accounts = Account.query.filter_by(customer_id=CUSTOMER_ID).all()
            log(f"✅ Found {len(accounts)} accounts in database")
            
            # Check KPI uploads
            kpi_uploads = KPIUpload.query.filter_by(customer_id=CUSTOMER_ID).all()
            log(f"✅ Found {len(kpi_uploads)} KPI upload records")
            
            results["steps"].append({
                "step": "verify_database",
                "status": "success",
                "accounts_count": len(accounts),
                "kpi_uploads_count": len(kpi_uploads)
            })
            
        except Exception as e:
            log(f"⚠️  Database verification error: {e}", "WARNING")
            results["warnings"].append(f"Database verification: {str(e)}")
        
        # Close onboarding logger
        close_onboarding_session(
            CUSTOMER_ID,
            "SUCCESS" if len(results["errors"]) == 0 else "PARTIAL",
            len(results["steps"]),
            len(results["errors"]),
            len(results["warnings"])
        )
        
        # Final summary
        results["end_time"] = datetime.now().isoformat()
        results["success"] = len(results["errors"]) == 0
        
        log("\n" + "=" * 70)
        log("TEST SUMMARY")
        log("=" * 70)
        log(f"Status: {'✅ PASSED' if results['success'] else '❌ FAILED'}")
        log(f"Steps Completed: {len(results['steps'])}")
        log(f"Errors: {len(results['errors'])}")
        log(f"Warnings: {len(results['warnings'])}")
        
        if results["warnings"]:
            log("\nWarnings:")
            for warning in results["warnings"]:
                log(f"  ⚠️  {warning}")
        
        if results["errors"]:
            log("\nErrors:")
            for error in results["errors"]:
                log(f"  ❌ {error}")
        
        log(f"\n📊 Report file: {REPORT_FILE}")
        log("=" * 70)
        
        # Save report
        with open(REPORT_FILE, 'w') as f:
            json.dump(results, f, indent=2)
        
        return results

if __name__ == '__main__':
    results = test_customer_19_e2e()
    sys.exit(0 if results.get("success") else 1)
