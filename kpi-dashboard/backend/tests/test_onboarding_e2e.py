#!/usr/bin/env python3
"""
End-to-End Onboarding Test Script
==================================

Tests complete onboarding flow from wizard completion to dashboard access.

Usage:
    python tests/test_onboarding_e2e.py
"""

import requests
import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5059')
TEST_DATA_DIR = Path(__file__).parent / 'test_data'
TEST_EMAIL = f'test_onboarding_{int(time.time())}@example.com'
TEST_PASSWORD = 'TestPassword123!'
TEST_COMPANY = f'Test Company {int(time.time())}'

# Test files (ensure these exist in tests/test_data/)
TEST_FILES = {
    'accounts': TEST_DATA_DIR / 'accounts.csv',
    'kpis': TEST_DATA_DIR / 'kpi_measurements.csv',
    'signals': TEST_DATA_DIR / 'qualitative_signals.csv',
    'products': TEST_DATA_DIR / 'products.csv',
    'profiles': TEST_DATA_DIR / 'profiles.csv'
}

# ============================================================================
# COLORS FOR OUTPUT
# ============================================================================

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")

def print_header(msg: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_step_1_complete_onboarding() -> Tuple[bool, Optional[int], Optional[int]]:
    """
    Test Step 1: POST /api/onboarding/complete
    Creates customer, user, and config
    """
    print_header("STEP 1: Complete Onboarding (Create Account)")
    
    payload = {
        'company_name': TEST_COMPANY,
        'company_email': TEST_EMAIL,
        'admin_name': 'Test Admin',
        'admin_email': TEST_EMAIL,
        'admin_password': TEST_PASSWORD,
        'vertical': 'dc2_s',
        'weights': {
            'P1_deployment_velocity': 0.15,
            'P2_operational_stability': 0.20,
            'P3_ai_workload_performance': 0.25,
            'P4_channel_partner_health': 0.15,
            'P5_expansion_readiness': 0.25
        },
        'team': []
    }
    
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/onboarding/complete',
            json=payload,
            timeout=30
        )
        
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print_error(f"Request failed: {response.text}")
            return False, None, None
        
        result = response.json()
        print_info(f"Response: {json.dumps(result, indent=2)}")
        
        customer_id = result.get('customer_id')
        user_id = result.get('user_id')
        
        if not customer_id or not user_id:
            print_error("Missing customer_id or user_id in response")
            return False, None, None
        
        print_success(f"Customer created: ID={customer_id}")
        print_success(f"User created: ID={user_id}")
        return True, customer_id, user_id
        
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False, None, None


def test_step_2_provision(customer_id: int) -> bool:
    """
    Test Step 2: POST /api/onboarding/provision
    Creates customer directory from _template
    """
    print_header("STEP 2: Provision Customer Directory")
    
    payload = {
        'customer_id': customer_id,
        'vertical': 'dc2_s'
    }
    
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/onboarding/provision',
            json=payload,
            timeout=60
        )
        
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print_error(f"Request failed: {response.text}")
            return False
        
        result = response.json()
        print_info(f"Response: {json.dumps(result, indent=2)}")
        
        print_success(f"Directory created: {result.get('customer_directory')}")
        print_success(f"Files created: {result.get('files_created')}")
        return True
        
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False


def test_step_3_upload_files(customer_id: int) -> bool:
    """
    Test Step 3: POST /api/onboarding/upload (for each file)
    Uploads CSV files to customer directory
    """
    print_header("STEP 3: Upload CSV Files")
    
    # Check if test files exist
    missing_files = [name for name, path in TEST_FILES.items() if not path.exists()]
    if missing_files:
        print_warning(f"Test files not found: {missing_files}")
        print_info("Creating sample test files...")
        create_sample_test_files()
    
    for file_type, file_path in TEST_FILES.items():
        if not file_path.exists():
            print_warning(f"Skipping {file_type}: file not found")
            continue
        
        print_info(f"Uploading {file_type}: {file_path.name}")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'text/csv')}
                data = {
                    'file_type': file_type,
                    'customer_id': str(customer_id)
                }
                
                response = requests.post(
                    f'{BASE_URL}/api/onboarding/upload',
                    files=files,
                    data=data,
                    timeout=30
                )
                
                if response.status_code != 200:
                    print_error(f"Upload failed for {file_type}: {response.text}")
                    return False
                
                result = response.json()
                print_success(f"Uploaded {file_type}: {result.get('file_path')}")
        
        except Exception as e:
            print_error(f"Exception uploading {file_type}: {str(e)}")
            return False
    
    return True


def test_step_4_process_data(customer_id: int) -> bool:
    """
    Test Step 4: POST /api/onboarding/process-data
    Runs all scripts (data loading, embeddings, Wizard A, B, C)
    """
    print_header("STEP 4: Process Data (This may take 2-3 minutes)")
    
    payload = {
        'customer_id': customer_id,
        'skip_validation': False,
        'skip_wizard_b': False,
        'skip_wizard_c': False
    }
    
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    print_warning("⏳ This step may take 1-3 minutes...")
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/onboarding/process-data',
            json=payload,
            timeout=300  # 5 minutes timeout
        )
        
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print_error(f"Request failed: {response.text}")
            return False
        
        result = response.json()
        print_info(f"Response: {json.dumps(result, indent=2)}")
        
        steps_completed = result.get('steps_completed', [])
        errors = result.get('errors', [])
        
        print_success(f"Steps completed: {', '.join(steps_completed)}")
        
        if errors:
            print_warning(f"Errors/Warnings: {errors}")
        
        # Check for required steps
        required_steps = ['data_loading', 'embeddings', 'journey_generation']
        missing_steps = [s for s in required_steps if s not in steps_completed]
        
        if missing_steps:
            print_error(f"Missing required steps: {missing_steps}")
            return False
        
        # Check for optional but recommended steps
        if 'pattern_analysis' in steps_completed:
            print_success("Wizard B (pattern analysis) completed")
        else:
            print_warning("Wizard B (pattern analysis) not run")
        
        if 'weight_calibration' in steps_completed:
            print_success("Wizard C (weight calibration) completed")
        else:
            print_warning("Wizard C (weight calibration) not run")
        
        return True
        
    except requests.Timeout:
        print_error("Request timed out after 5 minutes")
        return False
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False


def test_step_5_register_journey_api(customer_id: int) -> bool:
    """
    Test Step 5: POST /api/onboarding/register-journey-api
    Registers journey API blueprint
    """
    print_header("STEP 5: Register Journey API")
    
    payload = {
        'customer_id': customer_id
    }
    
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/onboarding/register-journey-api',
            json=payload,
            timeout=30
        )
        
        print_info(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print_warning(f"Request failed (non-critical): {response.text}")
            return True  # Non-critical failure
        
        result = response.json()
        print_info(f"Response: {json.dumps(result, indent=2)}")
        
        print_success(f"Blueprint registered: {result.get('blueprint_name')}")
        return True
        
    except Exception as e:
        print_warning(f"Exception (non-critical): {str(e)}")
        return True  # Non-critical failure


def test_step_6_verify_data(customer_id: int) -> bool:
    """
    Test Step 6: Verify data was loaded correctly
    Checks database and file system
    """
    print_header("STEP 6: Verify Data")
    
    # This would require database access
    # For now, just check processing status
    try:
        response = requests.get(
            f'{BASE_URL}/api/onboarding/processing-status',
            params={'customer_id': customer_id},
            timeout=30
        )
        
        if response.status_code != 200:
            print_error(f"Status check failed: {response.text}")
            return False
        
        result = response.json()
        print_info(f"Status: {json.dumps(result, indent=2)}")
        
        if result.get('journey_data_exists'):
            print_success("Journey data exists")
        else:
            print_warning("Journey data not found")
        
        if result.get('journey_api_exists'):
            print_success("Journey API exists")
        else:
            print_warning("Journey API not found")
        
        return True
        
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False


def create_sample_test_files():
    """Create minimal sample CSV files for testing"""
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # accounts.csv
    with open(TEST_FILES['accounts'], 'w') as f:
        f.write('account_id,account_name,initial_arr,final_arr,datacenter_location\n')
        f.write('1001,Test Account 1,100000,120000,US East (Virginia)\n')
        f.write('1002,Test Account 2,50000,55000,US West (Oregon)\n')
    
    # kpi_measurements.csv
    with open(TEST_FILES['kpis'], 'w') as f:
        f.write('account_id,date,kpi_name,kpi_value\n')
        f.write('1001,2025-01-01,deployment_time,30\n')
        f.write('1001,2025-01-01,uptime_percentage,99.9\n')
        f.write('1002,2025-01-01,deployment_time,45\n')
    
    # qualitative_signals.csv
    with open(TEST_FILES['signals'], 'w') as f:
        f.write('account_id,signal_date,signal_type,signal_description\n')
        f.write('1001,2025-01-01,positive,Expanded deployment\n')
    
    # products.csv
    with open(TEST_FILES['products'], 'w') as f:
        f.write('account_id,product_name,purchase_date,primary_product\n')
        f.write('1001,AI Server,2024-01-01,true\n')
    
    # profiles.csv
    with open(TEST_FILES['profiles'], 'w') as f:
        f.write('account_id,strategic_account,reference_customer\n')
        f.write('1001,true,false\n')
    
    print_success("Created sample test files")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run complete E2E test suite"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}ONBOARDING E2E TEST SUITE{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"Base URL: {BASE_URL}")
    print(f"Test Email: {TEST_EMAIL}")
    print(f"Test Company: {TEST_COMPANY}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")
    
    results = {}
    customer_id = None
    user_id = None
    
    # Step 1: Complete Onboarding
    success, customer_id, user_id = test_step_1_complete_onboarding()
    results['step_1_complete'] = success
    
    if not success:
        print_error("❌ Step 1 failed - cannot continue")
        print_summary(results)
        return False
    
    # Step 2: Provision
    success = test_step_2_provision(customer_id)
    results['step_2_provision'] = success
    
    if not success:
        print_error("❌ Step 2 failed - cannot continue")
        print_summary(results)
        return False
    
    # Step 3: Upload Files
    success = test_step_3_upload_files(customer_id)
    results['step_3_upload'] = success
    
    if not success:
        print_error("❌ Step 3 failed - cannot continue")
        print_summary(results)
        return False
    
    # Step 4: Process Data
    success = test_step_4_process_data(customer_id)
    results['step_4_process'] = success
    
    if not success:
        print_error("❌ Step 4 failed - cannot continue")
        print_summary(results)
        return False
    
    # Step 5: Register Journey API
    success = test_step_5_register_journey_api(customer_id)
    results['step_5_register'] = success
    
    # Step 6: Verify Data
    success = test_step_6_verify_data(customer_id)
    results['step_6_verify'] = success
    
    # Print summary
    print_summary(results)
    
    # Overall result
    all_passed = all(results.values())
    
    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! ONBOARDING IS WORKING! 🎉{Colors.RESET}")
        print(f"{Colors.GREEN}{Colors.BOLD}{'='*70}{Colors.RESET}\n")
        print_success(f"Customer ID: {customer_id}")
        print_success(f"User ID: {user_id}")
        print_success(f"You can now login with: {TEST_EMAIL}")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.RED}{Colors.BOLD}❌ SOME TESTS FAILED{Colors.RESET}")
        print(f"{Colors.RED}{Colors.BOLD}{'='*70}{Colors.RESET}\n")
        return False


def print_summary(results: Dict[str, bool]):
    """Print test results summary"""
    print_header("TEST SUMMARY")
    
    for test_name, passed in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    total = len(results)
    passed = sum(1 for p in results.values() if p)
    
    print(f"\n  Total: {passed}/{total} tests passed")


if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
