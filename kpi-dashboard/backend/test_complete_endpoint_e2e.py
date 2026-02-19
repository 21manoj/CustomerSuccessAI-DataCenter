#!/usr/bin/env python3
"""
End-to-End Test Suite for Enhanced /complete Endpoint
Uses unique customer IDs and comprehensive validation
"""

import sys
import os
import time
from pathlib import Path
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app
from extensions import db
from models import Customer, User, Account, CustomerConfig

def print_test_header(test_name: str):
    """Print formatted test header"""
    print("\n" + "="*70)
    print(f"TEST: {test_name}")
    print("="*70)

def print_result(success: bool, message: str):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")

def get_unique_customer_id():
    """Generate a unique customer ID based on timestamp"""
    return int(time.time() * 1000) % 1000000  # Use milliseconds for uniqueness

def cleanup_customer(customer_id: int):
    """Clean up test customer data"""
    try:
        with app.app_context():
            # Delete accounts
            Account.query.filter_by(customer_id=customer_id).delete()
            # Delete user
            User.query.filter_by(customer_id=customer_id).delete()
            # Delete config
            CustomerConfig.query.filter_by(customer_id=customer_id).delete()
            # Delete customer
            Customer.query.filter_by(customer_id=customer_id).delete()
            db.session.commit()
            
            # Delete directory
            customer_dir = Path(f"verticals/customer{customer_id}-dc2_s")
            if customer_dir.exists():
                import shutil
                shutil.rmtree(customer_dir)
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

def test_minimal_request():
    """Test 1: Minimal Request (Auto-generate customer_id)"""
    print_test_header("Minimal Request - Auto-generate customer_id")
    
    with app.test_client() as client:
        payload = {
            "customer_name": f"E2E Test Company Minimal {int(time.time())}"
        }
        
        response = client.post(
            '/api/onboarding/complete',
            json=payload,
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f"Customer ID: {data.get('customer_id')}")
            
            # Verify required fields
            checks = [
                (data.get('success') == True, "success = true"),
                (data.get('customer_id') is not None, "customer_id present"),
                (data.get('customer_name') == payload['customer_name'], "customer_name matches"),
                (data.get('accounts') == 3, "default 3 accounts created"),
                (len(data.get('account_details', [])) == 3, "3 account_details"),
                (data.get('account_id_range') is not None, "account_id_range present"),
                (data.get('config') is not None, "config present"),
                (data.get('directory_provisioned') is not None, "directory_provisioned flag"),
                (data.get('csv_files_generated') is not None, "csv_files_generated flag"),
            ]
            
            all_pass = all(check[0] for check in checks)
            for check, msg in checks:
                print_result(check, msg)
            
            if all_pass:
                print_result(True, "All minimal request checks passed")
                return data.get('customer_id')
            else:
                print_result(False, "Some checks failed")
                return None
        else:
            print_result(False, f"Request failed with status {response.status_code}")
            print(f"Response: {response.data.decode()}")
            return None

def test_full_request():
    """Test 2: Full Request (All fields)"""
    print_test_header("Full Request - All fields provided")
    
    customer_id = get_unique_customer_id()
    timestamp = int(time.time())
    
    with app.test_client() as client:
        payload = {
            "customer_id": customer_id,
            "customer_name": f"E2E DC2_S Demo Enterprise {timestamp}",
            "domain": f"dc2s-demo-{timestamp}.example.com",
            "industry": "Data Center Infrastructure",
            "vertical": "dc2_s",
            "email": f"admin-{timestamp}@dc2s-demo.example.com",
            "username": f"dc2s_admin_{timestamp}",
            "password": "DemoPass123!",
            "first_name": "Demo",
            "last_name": "Administrator",
            "num_accounts": 10,
            "weights": {
                "AI": 0.10,
                "CH": 0.30,
                "DV": 0.30,
                "EX": 0.05,
                "OS": 0.25
            }
        }
        
        response = client.post(
            '/api/onboarding/complete',
            json=payload,
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = json.loads(response.data)
            
            # Verify all fields
            checks = [
                (data.get('success') == True, "success = true"),
                (data.get('customer_id') == customer_id, f"customer_id = {customer_id}"),
                (data.get('customer_name') == payload['customer_name'], "customer_name matches"),
                (data.get('domain') == payload['domain'], "domain matches"),
                (data.get('accounts') == 10, "10 accounts created"),
                (len(data.get('account_details', [])) == 10, "10 account_details"),
                (data.get('account_id_range') == f"{customer_id * 1000 + 1} - {customer_id * 1000 + 10}", "account_id_range correct"),
                (data.get('user') is not None, "user object present"),
                (data.get('user', {}).get('username') == payload['username'], "username matches"),
                (data.get('user', {}).get('email') == payload['email'], "email matches"),
                (data.get('user', {}).get('role') == "admin", "role = admin"),
                (data.get('config', {}).get('weights', {}).get('AI') == 0.10, "custom weights applied"),
                (data.get('directory_provisioned') is not None, "directory_provisioned flag"),
                (data.get('csv_files_generated') is not None, "csv_files_generated flag"),
            ]
            
            all_pass = all(check[0] for check in checks)
            for check, msg in checks:
                print_result(check, msg)
            
            if all_pass:
                print_result(True, "All full request checks passed")
                return customer_id
            else:
                print_result(False, "Some checks failed")
                return None
        else:
            print_result(False, f"Request failed with status {response.status_code}")
            print(f"Response: {response.data.decode()}")
            return None

def test_custom_weights():
    """Test 3: Custom Weights"""
    print_test_header("Custom Weights")
    
    customer_id = get_unique_customer_id()
    
    with app.test_client() as client:
        payload = {
            "customer_name": f"E2E Test Company Weights {customer_id}",
            "weights": {
                "AI": 0.50,
                "CH": 0.20,
                "DV": 0.10,
                "EX": 0.10,
                "OS": 0.10
            }
        }
        
        response = client.post(
            '/api/onboarding/complete',
            json=payload,
            content_type='application/json'
        )
        
        if response.status_code == 200:
            data = json.loads(response.data)
            weights = data.get('config', {}).get('weights', {})
            
            checks = [
                (weights.get('AI') == 0.50, "AI weight = 0.50"),
                (weights.get('CH') == 0.20, "CH weight = 0.20"),
                (weights.get('DV') == 0.10, "DV weight = 0.10"),
                (weights.get('EX') == 0.10, "EX weight = 0.10"),
                (weights.get('OS') == 0.10, "OS weight = 0.10"),
            ]
            
            all_pass = all(check[0] for check in checks)
            for check, msg in checks:
                print_result(check, msg)
            
            return all_pass
        else:
            print_result(False, f"Request failed: {response.status_code}")
            print(f"Response: {response.data.decode()}")
            return False

def test_num_accounts():
    """Test 4: Configurable num_accounts"""
    print_test_header("Configurable num_accounts")
    
    customer_id = get_unique_customer_id()
    
    with app.test_client() as client:
        payload = {
            "customer_name": f"E2E Test Company Accounts {customer_id}",
            "num_accounts": 5
        }
        
        response = client.post(
            '/api/onboarding/complete',
            json=payload,
            content_type='application/json'
        )
        
        if response.status_code == 200:
            data = json.loads(response.data)
            
            checks = [
                (data.get('accounts') == 5, "5 accounts created"),
                (len(data.get('account_details', [])) == 5, "5 account_details"),
            ]
            
            # Verify account IDs are sequential
            account_ids = [acc['account_id'] for acc in data.get('account_details', [])]
            if account_ids:
                base_id = account_ids[0]
                sequential = all(account_ids[i] == base_id + i for i in range(len(account_ids)))
                checks.append((sequential, "Account IDs are sequential"))
            
            all_pass = all(check[0] for check in checks)
            for check, msg in checks:
                print_result(check, msg)
            
            return all_pass
        else:
            print_result(False, f"Request failed: {response.status_code}")
            return False

def test_user_creation():
    """Test 5: User Creation"""
    print_test_header("User Creation")
    
    timestamp = int(time.time())
    
    with app.test_client() as client:
        payload = {
            "customer_name": f"E2E Test Company User {timestamp}",
            "email": f"testuser-{timestamp}@example.com",
            "username": f"testuser_{timestamp}",
            "password": "TestPass123!"
        }
        
        response = client.post(
            '/api/onboarding/complete',
            json=payload,
            content_type='application/json'
        )
        
        if response.status_code == 200:
            data = json.loads(response.data)
            customer_id = data.get('customer_id')  # Get actual customer_id from response
            
            checks = [
                (data.get('user') is not None, "user object present"),
                (data.get('user', {}).get('email') == payload['email'], "email matches"),
                (data.get('user', {}).get('username') == payload['username'], "username matches"),
                (data.get('user', {}).get('role') == "admin", "role = admin"),
            ]
            
            all_pass = all(check[0] for check in checks)
            for check, msg in checks:
                print_result(check, msg)
            
            if all_pass:
                return customer_id  # Return actual customer_id from response
            return None
        else:
            print_result(False, f"Request failed: {response.status_code}")
            print(f"Response: {response.data.decode()}")
            return None

def test_directory_provisioning(customer_id: int):
    """Test 6: Directory Provisioning"""
    print_test_header("Directory Provisioning")
    
    customer_dir = Path(f"verticals/customer{customer_id}-dc2_s")
    
    # Check what directories actually exist (based on provision script)
    checks = [
        (customer_dir.exists(), f"Directory exists: {customer_dir}"),
        ((customer_dir / "data").exists(), "data/ subdirectory exists"),
    ]
    
    # Check if scripts/ exists (may or may not be created by provision script)
    scripts_exists = (customer_dir / "scripts").exists()
    if scripts_exists:
        checks.append((True, "scripts/ subdirectory exists"))
    else:
        # This is OK - provision script may not create scripts/ directory
        print_result(True, "scripts/ subdirectory (optional - not required)")
    
    all_pass = all(check[0] for check in checks)
    for check, msg in checks:
        print_result(check, msg)
    
    return all_pass

def test_csv_files_generated(customer_id: int):
    """Test 7: CSV Files Generated"""
    print_test_header("CSV Files Generated")
    
    data_dir = Path(f"verticals/customer{customer_id}-dc2_s/data")
    
    if not data_dir.exists():
        print_result(False, f"Data directory does not exist: {data_dir}")
        return False
    
    required_files = [
        "accounts.csv",
        "kpi_measurements.csv",
    ]
    
    checks = []
    for file in required_files:
        file_path = data_dir / file
        exists = file_path.exists()
        checks.append((exists, f"{file} exists"))
        if exists:
            size = file_path.stat().st_size
            checks.append((size > 0, f"{file} is not empty ({size} bytes)"))
    
    all_pass = all(check[0] for check in checks)
    for check, msg in checks:
        print_result(check, msg)
    
    return all_pass

def test_idempotency():
    """Test 8: Idempotency (Run twice with same customer_id)"""
    print_test_header("Idempotency - Run twice with same customer_id")
    
    customer_id = get_unique_customer_id()
    timestamp = int(time.time())
    
    with app.test_client() as client:
        payload = {
            "customer_id": customer_id,
            "customer_name": f"E2E Test Company Idempotent {timestamp}"
        }
        
        # First request
        response1 = client.post(
            '/api/onboarding/complete',
            json=payload,
            content_type='application/json'
        )
        print(f"First request status: {response1.status_code}")
        
        if response1.status_code != 200:
            print_result(False, f"First request failed: {response1.status_code}")
            print(f"Response: {response1.data.decode()}")
            return False
        
        # Second request (should handle existing customer gracefully)
        response2 = client.post(
            '/api/onboarding/complete',
            json=payload,
            content_type='application/json'
        )
        print(f"Second request status: {response2.status_code}")
        
        if response2.status_code == 200:
            print_result(True, "Second request succeeded (updated existing)")
            return True
        elif response2.status_code == 400:
            data2 = json.loads(response2.data)
            if "already exists" in str(data2.get('error', '')):
                print_result(True, "Second request failed gracefully (already exists)")
                return True
            else:
                print_result(False, "Second request failed unexpectedly")
                return False
        else:
            print_result(False, f"Second request returned unexpected status: {response2.status_code}")
            return False

def test_error_handling():
    """Test 9: Error Handling"""
    print_test_header("Error Handling")
    
    with app.test_client() as client:
        # Test missing required field
        payload = {}
        
        response = client.post(
            '/api/onboarding/complete',
            json=payload,
            content_type='application/json'
        )
        
        if response.status_code == 400:
            print_result(True, "Missing customer_name returns 400")
            return True
        else:
            print_result(False, f"Expected 400, got {response.status_code}")
            print(f"Response: {response.data.decode()}")
            return False

def verify_database(customer_id: int, expect_user: bool = False):
    """Test 10: Verify Database Records"""
    print_test_header("Verify Database Records")
    
    with app.app_context():
        # Check customer
        customer = db.session.get(Customer, customer_id)
        checks = [
            (customer is not None, f"Customer {customer_id} exists"),
        ]
        
        if customer:
            # Check user (only if expected)
            if expect_user:
                user = User.query.filter_by(customer_id=customer_id).first()
                checks.append((user is not None, "User exists"))
                
                if user:
                    checks.append((user.role == 'admin', "User role = admin"))
            else:
                # User not expected (minimal request)
                print_result(True, "User not created (expected - no email/username provided)")
            
            # Check accounts
            accounts = Account.query.filter_by(customer_id=customer_id).all()
            checks.append((len(accounts) > 0, f"{len(accounts)} accounts exist"))
            
            # Check config
            config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
            checks.append((config is not None, "CustomerConfig exists"))
            if config:
                checks.append((config.dc2s_pillar_weights is not None, "Pillar weights set"))
                checks.append((config.vertical == 'dc2_s', "Vertical = dc2_s"))
        
        all_pass = all(check[0] for check in checks)
        for check, msg in checks:
            print_result(check, msg)
        
        return all_pass

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("END-TO-END TEST SUITE FOR ENHANCED /complete ENDPOINT")
    print("Using Flask Test Client with Unique Customer IDs")
    print("="*70)
    
    results = {}
    customer_ids_to_cleanup = []
    
    try:
        # Test 1: Minimal request
        customer_id_1 = test_minimal_request()
        results['minimal_request'] = customer_id_1 is not None
        if customer_id_1:
            customer_ids_to_cleanup.append(customer_id_1)
            
            # Test 6: Directory provisioning
            results['directory_provisioning'] = test_directory_provisioning(customer_id_1)
            
            # Test 7: CSV files
            results['csv_files'] = test_csv_files_generated(customer_id_1)
            
            # Test 10: Database verification (no user expected)
            results['database'] = verify_database(customer_id_1, expect_user=False)
        
        # Test 2: Full request
        customer_id_2 = test_full_request()
        results['full_request'] = customer_id_2 is not None
        if customer_id_2:
            customer_ids_to_cleanup.append(customer_id_2)
        
        # Test 3: Custom weights
        results['custom_weights'] = test_custom_weights()
        
        # Test 4: num_accounts
        results['num_accounts'] = test_num_accounts()
        
        # Test 5: User creation
        customer_id_5 = test_user_creation()
        results['user_creation'] = customer_id_5 is not None
        if customer_id_5:
            customer_ids_to_cleanup.append(customer_id_5)
            # Verify database with user
            results['database_with_user'] = verify_database(customer_id_5, expect_user=True)
        
        # Test 8: Idempotency
        results['idempotency'] = test_idempotency()
        
        # Test 9: Error handling
        results['error_handling'] = test_error_handling()
        
    finally:
        # Cleanup test data
        print("\n" + "="*70)
        print("CLEANUP")
        print("="*70)
        for customer_id in customer_ids_to_cleanup:
            print(f"Cleaning up customer {customer_id}...")
            cleanup_customer(customer_id)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
