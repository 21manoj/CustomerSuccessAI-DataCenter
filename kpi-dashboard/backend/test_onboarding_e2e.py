#!/usr/bin/env python3
"""
End-to-End Onboarding Test Script
Tests complete onboarding flow for Customer 19 and Customer 9
"""

import sys
import os
import json
import requests
import time
from pathlib import Path
from datetime import datetime
import shutil

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_CUSTOMER_19 = {
    "customer_id": 19,
    "company_name": "Synthetic Data Corp",
    "company_email": "admin@synthetic-data.com",
    "admin_name": "Admin User",
    "admin_email": "admin@synthetic-data.com",
    "admin_password": "TestPass123!",
    "vertical": "dc2_s"
}

TEST_CUSTOMER_9 = {
    "customer_id": 9,
    "company_name": "Customer 9 Test",
    "company_email": "admin@customer9.com",
    "admin_name": "Admin User",
    "admin_email": "admin@customer9.com",
    "admin_password": "TestPass123!",
    "vertical": "dc2_s"
}

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

def make_request(method, endpoint, data=None, files=None, headers=None):
    """Make HTTP request and return response"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            if files:
                response = requests.post(url, data=data, files=files, headers=headers, timeout=60)
            else:
                response = requests.post(url, json=data, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return {
            "status_code": response.status_code,
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            "success": response.status_code < 400
        }
    except Exception as e:
        return {
            "status_code": 0,
            "data": {"error": str(e)},
            "success": False
        }

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
    
    # Step 1: Provision customer directory
    log("\n[1/6] Provisioning customer directory...")
    provision_data = {
        "customer_id": 19,
        "customer_name": TEST_CUSTOMER_19["company_name"],
        "vertical_slug": "dc2_s"
    }
    response = make_request("POST", "/api/onboarding/provision", data=provision_data)
    results["steps"].append({"step": "provision", **response})
    if response["success"]:
        log(f"✅ Provision successful: {response['data']}")
    else:
        log(f"❌ Provision failed: {response['data']}", "ERROR")
        results["errors"].append("Provision failed")
        return results
    
    # Step 2: Copy generated files to data directory
    log("\n[2/6] Copying generated files to customer directory...")
    source_dir = Path(__file__).parent / "customer19_synthetic_data"
    target_dir = Path(__file__).parent / "verticals" / "customer19-dc2_s" / "data"
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
    response = make_request("POST", "/api/onboarding/complete", data=TEST_CUSTOMER_19)
    results["steps"].append({"step": "complete", **response})
    if response["success"]:
        log(f"✅ Complete successful: Customer ID {response['data'].get('customer_id')}")
        customer_id = response['data'].get('customer_id', 19)
    else:
        log(f"❌ Complete failed: {response['data']}", "ERROR")
        results["errors"].append("Complete failed")
        customer_id = 19  # Continue with expected ID
    
    # Step 4: Upload files (verify they're in place)
    log("\n[4/6] Checking uploaded files...")
    # Files are already copied, so we'll just verify
    upload_status = make_request("GET", "/api/onboarding/upload-status")
    results["steps"].append({"step": "upload_status", **upload_status})
    if upload_status["success"]:
        log(f"✅ Upload status: {upload_status['data']}")
    
    # Step 5: Process data (execute scripts)
    log("\n[5/6] Processing data (executing scripts)...")
    process_data = {
        "customer_id": customer_id,
        "skip_validation": False,
        "skip_wizard_b": True
    }
    response = make_request("POST", "/api/onboarding/process-data", data=process_data)
    results["steps"].append({"step": "process_data", **response})
    if response["success"]:
        log(f"✅ Process data successful: {response['data']}")
    else:
        log(f"❌ Process data failed: {response['data']}", "ERROR")
        results["errors"].append("Process data failed")
    
    # Step 6: Register journey API
    log("\n[6/6] Registering journey API...")
    register_data = {"customer_id": customer_id}
    response = make_request("POST", "/api/onboarding/register-journey-api", data=register_data)
    results["steps"].append({"step": "register_journey_api", **response})
    if response["success"]:
        log(f"✅ Journey API registered: {response['data']}")
    else:
        log(f"⚠️  Journey API registration: {response['data']}", "WARNING")
    
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
    
    # Check if customer 9 directory exists
    customer9_dir = Path(__file__).parent / "verticals" / "customer9-dc2_s"
    if not customer9_dir.exists():
        log("❌ Customer 9 directory not found", "ERROR")
        results["errors"].append("Customer 9 directory not found")
        return results
    
    # Check data directory
    data_dir = customer9_dir / "data"
    if not data_dir.exists():
        log("❌ Customer 9 data directory not found", "ERROR")
        results["errors"].append("Data directory not found")
        return results
    
    # Check for required files
    required_files = ["accounts.csv", "kpi_measurements.csv"]
    missing_files = [f for f in required_files if not (data_dir / f).exists()]
    if missing_files:
        log(f"⚠️  Missing files: {missing_files}", "WARNING")
        results["errors"].append(f"Missing files: {missing_files}")
    else:
        log("✅ All required files present")
    
    # Check processing status
    log("\n[1/3] Checking processing status...")
    status_data = {"customer_id": 9}
    response = make_request("GET", "/api/onboarding/processing-status", data=status_data)
    results["steps"].append({"step": "processing_status", **response})
    if response["success"]:
        log(f"✅ Processing status: {json.dumps(response['data'], indent=2)}")
    
    # Test journey API (if available)
    log("\n[2/3] Testing journey API...")
    # Try to access a journey endpoint
    journey_response = make_request("GET", "/api/journey/29001")  # Customer 9 account
    results["steps"].append({"step": "journey_api", **journey_response})
    if journey_response["success"]:
        log("✅ Journey API accessible")
    else:
        log(f"⚠️  Journey API: {journey_response['data']}", "WARNING")
    
    # Check dashboard data
    log("\n[3/3] Checking dashboard data...")
    accounts_response = make_request("GET", "/api/accounts")
    results["steps"].append({"step": "accounts_api", **accounts_response})
    if accounts_response["success"]:
        accounts = accounts_response.get("data", {}).get("accounts", [])
        customer9_accounts = [a for a in accounts if a.get("customer_id") == 9]
        log(f"✅ Found {len(customer9_accounts)} accounts for Customer 9")
    
    results["end_time"] = datetime.now().isoformat()
    results["success"] = len(results["errors"]) == 0
    
    return results

def main():
    """Run all tests"""
    log("=" * 70)
    log("ONBOARDING END-TO-END TEST SUITE")
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
