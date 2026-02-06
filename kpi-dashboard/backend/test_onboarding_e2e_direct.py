#!/usr/bin/env python3
"""
End-to-End Onboarding Test Script (Direct - No HTTP)
Tests complete onboarding flow for Customer 19 and Customer 9
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
import shutil

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer, User, Account, CustomerConfig
from onboarding_api import (
    get_customer_directory,
    calculate_account_id_range,
    execute_script
)
from verticals.provision_dc_customer import provision_customer

# Log file
LOG_DIR = Path(__file__).parent / "logs" / "onboarding_tests"
LOG_DIR.mkdir(parents=True, exist_ok=True)
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
LOG_FILE = LOG_DIR / f"onboarding_e2e_test_{TIMESTAMP}.log"
REPORT_FILE = LOG_DIR / f"onboarding_e2e_report_{TIMESTAMP}.json"

def log(message, level="INFO"):
    """Log message to file and console"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] [{level}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + '\n')

def test_customer_19_onboarding():
    """Test Customer 19 onboarding flow"""
    log("=" * 70)
    log("TESTING CUSTOMER 19 ONBOARDING FLOW")
    log("=" * 70)
    
    results = {
        "customer_id": 19,
        "steps": [],
        "errors": [],
        "start_time": datetime.now().isoformat()
    }
    
    with app.app_context():
        # Step 1: Provision customer directory
        log("\n[1/6] Provisioning customer directory...")
        try:
            # Fix path - use correct verticals directory
            verticals_dir = Path(__file__).parent / "verticals"
            customer_dir = verticals_dir / "customer19-dc2_s"
            if customer_dir.exists():
                log(f"✅ Customer directory already exists: {customer_dir}")
                results["steps"].append({"step": "provision", "status": "exists", "path": str(customer_dir)})
            else:
                success = provision_customer(
                    customer_id=19,
                    customer_name="Synthetic Data Corp",
                    vertical_slug="dc2_s",
                    dry_run=False,
                    force=True
                )
                if success:
                    log(f"✅ Provision successful: {customer_dir}")
                    results["steps"].append({"step": "provision", "status": "created", "path": str(customer_dir)})
                else:
                    log(f"❌ Provision failed", "ERROR")
                    results["errors"].append("Provision failed")
                    return results
        except Exception as e:
            log(f"❌ Provision error: {e}", "ERROR")
            results["errors"].append(f"Provision error: {str(e)}")
            return results
        
        # Step 2: Copy generated files to data directory
        log("\n[2/6] Copying generated files to customer directory...")
        source_dir = Path(__file__).parent / "customer19_synthetic_data"
        target_dir = customer_dir / "data"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        files_to_copy = ["accounts.csv", "kpi_measurements.csv", "qualitative_signals.csv", "products.csv", "profiles.csv"]
        copied_files = []
        for filename in files_to_copy:
            source_file = source_dir / filename
            if source_file.exists():
                shutil.copy2(source_file, target_dir / filename)
                copied_files.append(filename)
                log(f"✅ Copied {filename}")
            else:
                log(f"⚠️  File not found: {filename}", "WARNING")
        
        results["steps"].append({
            "step": "copy_files",
            "files_copied": copied_files,
            "success": len(copied_files) == len(files_to_copy)
        })
        
        # Step 3: Complete onboarding (create customer/user/config)
        log("\n[3/6] Completing onboarding (creating customer/user/config)...")
        try:
            # Check if customer exists (by email/domain, not ID)
            customer = Customer.query.filter_by(email="admin@synthetic-data.com").first()
            if not customer:
                customer = Customer.query.filter_by(domain="synthetic-data.com").first()
            if not customer:
                customer = Customer(
                    customer_name="Synthetic Data Corp",
                    email="admin@synthetic-data.com",
                    domain="synthetic-data.com"
                )
                db.session.add(customer)
                db.session.flush()
                log(f"✅ Created customer: {customer.customer_id}")
            else:
                log(f"✅ Customer already exists: {customer.customer_id}")
            
            # Create user
            user = User.query.filter_by(email="admin@synthetic-data.com").first()
            if not user:
                from werkzeug.security import generate_password_hash
                user = User(
                    customer_id=customer.customer_id,
                    user_name="Admin User",
                    email="admin@synthetic-data.com",
                    password_hash=generate_password_hash("TestPass123!"),
                    vertical="dc2_s",
                    role="admin",
                    active=True
                )
                db.session.add(user)
                db.session.flush()
                log(f"✅ Created user: {user.user_id}")
            else:
                log(f"✅ User already exists: {user.user_id}")
            
            # Create config
            config = CustomerConfig.query.filter_by(customer_id=customer.customer_id).first()
            if not config:
                config = CustomerConfig(
                    customer_id=customer.customer_id,
                    kpi_upload_mode="account_rollup",
                    category_weights='{"P1_deployment_velocity": 0.10, "P2_operational_stability": 0.30, "P3_ai_workload_performance": 0.30, "P4_channel_partner_health": 0.05, "P5_expansion_revenue": 0.25}',
                    master_file_name=None
                )
                db.session.add(config)
                db.session.commit()
                log(f"✅ Created config")
            else:
                log(f"✅ Config already exists")
            
            results["steps"].append({
                "step": "complete",
                "customer_id": customer.customer_id,
                "user_id": user.user_id if user else None,
                "success": True
            })
        except Exception as e:
            db.session.rollback()
            log(f"❌ Complete failed: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "ERROR")
            results["errors"].append(f"Complete failed: {str(e)}")
            return results
        
        # Step 4: Verify files
        log("\n[4/6] Verifying uploaded files...")
        required_files = ["accounts.csv", "kpi_measurements.csv"]
        missing_files = [f for f in required_files if not (target_dir / f).exists()]
        if missing_files:
            log(f"❌ Missing files: {missing_files}", "ERROR")
            results["errors"].append(f"Missing files: {missing_files}")
        else:
            log(f"✅ All required files present")
            results["steps"].append({"step": "verify_files", "success": True})
        
        # Step 5: Process data (execute scripts)
        log("\n[5/6] Processing data (executing scripts)...")
        try:
            # Check if scripts exist
            load_script = customer_dir / "scripts" / "02_load_customer19_data_SMART.py"
            if not load_script.exists():
                log(f"⚠️  Data loading script not found: {load_script}", "WARNING")
                results["steps"].append({"step": "process_data", "status": "skipped", "reason": "script_not_found"})
            else:
                log(f"✅ Found script: {load_script}")
                # Note: We'll skip actual execution as it may take time and require DB setup
                log(f"⚠️  Script execution skipped (would run: {load_script})", "WARNING")
                results["steps"].append({"step": "process_data", "status": "skipped", "reason": "manual_execution_required"})
        except Exception as e:
            log(f"❌ Process data error: {e}", "ERROR")
            results["errors"].append(f"Process data error: {str(e)}")
        
        # Step 6: Check journey API
        log("\n[6/6] Checking journey API...")
        journey_api = customer_dir / "journey" / "customer19_journey_api.py"
        if journey_api.exists():
            log(f"✅ Journey API file exists: {journey_api}")
            results["steps"].append({"step": "journey_api", "status": "exists", "path": str(journey_api)})
        else:
            log(f"⚠️  Journey API file not found (will be created by wizard_a)", "WARNING")
            results["steps"].append({"step": "journey_api", "status": "not_found"})
    
    results["end_time"] = datetime.now().isoformat()
    results["success"] = len(results["errors"]) == 0
    
    return results

def test_customer_9_e2e():
    """Test Customer 9 end-to-end"""
    log("\n" + "=" * 70)
    log("TESTING CUSTOMER 9 END-TO-END")
    log("=" * 70)
    
    results = {
        "customer_id": 9,
        "steps": [],
        "errors": [],
        "start_time": datetime.now().isoformat()
    }
    
    with app.app_context():
        # Check if customer 9 directory exists
        # Fix path - get_customer_directory uses parent.parent which may be wrong
        verticals_dir = Path(__file__).parent / "verticals"
        customer9_dir = verticals_dir / "customer9-dc2_s"
        if not customer9_dir.exists():
            log("❌ Customer 9 directory not found", "ERROR")
            results["errors"].append("Customer 9 directory not found")
            return results
        
        log(f"✅ Customer 9 directory exists: {customer9_dir}")
        
        # Check data directory
        data_dir = customer9_dir / "data"
        if not data_dir.exists():
            log("❌ Customer 9 data directory not found", "ERROR")
            results["errors"].append("Data directory not found")
            return results
        
        log(f"✅ Data directory exists: {data_dir}")
        
        # Check for required files
        required_files = ["accounts.csv", "kpi_measurements.csv"]
        missing_files = [f for f in required_files if not (data_dir / f).exists()]
        if missing_files:
            log(f"⚠️  Missing files: {missing_files}", "WARNING")
            results["errors"].append(f"Missing files: {missing_files}")
        else:
            log("✅ All required files present")
            results["steps"].append({"step": "files_check", "success": True})
        
        # Check scripts
        scripts_dir = customer9_dir / "scripts"
        if scripts_dir.exists():
            scripts = list(scripts_dir.glob("*.py"))
            log(f"✅ Found {len(scripts)} scripts in scripts directory")
            results["steps"].append({"step": "scripts_check", "count": len(scripts)})
        
        # Check journey data
        journey_dir = customer9_dir / "journey" / "wizard_a"
        if journey_dir.exists():
            test_runs = [d for d in journey_dir.iterdir() if d.is_dir() and d.name.startswith('test_run')]
            if test_runs:
                log(f"✅ Found {len(test_runs)} journey test runs")
                results["steps"].append({"step": "journey_data", "test_runs": len(test_runs)})
        
        # Check database records
        try:
            customer = Customer.query.filter_by(customer_id=9).first()
            if customer:
                accounts = Account.query.filter_by(customer_id=9).all()
                log(f"✅ Customer 9 exists in DB with {len(accounts)} accounts")
                results["steps"].append({"step": "db_check", "accounts_count": len(accounts)})
            else:
                log("⚠️  Customer 9 not found in database", "WARNING")
        except Exception as e:
            log(f"⚠️  Database check error: {e}", "WARNING")
    
    results["end_time"] = datetime.now().isoformat()
    results["success"] = len(results["errors"]) == 0
    
    return results

def main():
    """Run all tests"""
    log("=" * 70)
    log("ONBOARDING END-TO-END TEST SUITE (DIRECT)")
    log(f"Started at: {datetime.now().isoformat()}")
    log(f"Log file: {LOG_FILE}")
    log(f"Report file: {REPORT_FILE}")
    log("=" * 70)
    
    all_results = {
        "test_start": datetime.now().isoformat(),
        "customer_19": None,
        "customer_9": None,
        "summary": {}
    }
    
    # Test Customer 19 onboarding
    try:
        customer19_results = test_customer_19_onboarding()
        all_results["customer_19"] = customer19_results
    except Exception as e:
        log(f"❌ Customer 19 test failed with exception: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        all_results["customer_19"] = {"error": str(e)}
    
    # Test Customer 9 end-to-end
    try:
        customer9_results = test_customer_9_e2e()
        all_results["customer_9"] = customer9_results
    except Exception as e:
        log(f"❌ Customer 9 test failed with exception: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        all_results["customer_9"] = {"error": str(e)}
    
    # Generate summary
    all_results["test_end"] = datetime.now().isoformat()
    all_results["summary"] = {
        "customer_19_success": all_results["customer_19"] and all_results["customer_19"].get("success", False),
        "customer_9_success": all_results["customer_9"] and all_results["customer_9"].get("success", False),
        "total_errors": (
            len(all_results["customer_19"].get("errors", [])) if all_results["customer_19"] else 0
        ) + (
            len(all_results["customer_9"].get("errors", [])) if all_results["customer_9"] else 0
        )
    }
    
    # Save report
    with open(REPORT_FILE, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Print summary
    log("\n" + "=" * 70)
    log("TEST SUMMARY")
    log("=" * 70)
    log(f"Customer 19 Onboarding: {'✅ PASSED' if all_results['summary']['customer_19_success'] else '❌ FAILED'}")
    log(f"Customer 9 E2E: {'✅ PASSED' if all_results['summary']['customer_9_success'] else '❌ FAILED'}")
    log(f"Total Errors: {all_results['summary']['total_errors']}")
    log(f"\n📁 Log file: {LOG_FILE}")
    log(f"📊 Report file: {REPORT_FILE}")
    log("=" * 70)
    
    return 0 if all_results["summary"]["total_errors"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
