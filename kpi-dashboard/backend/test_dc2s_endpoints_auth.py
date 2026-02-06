#!/usr/bin/env python3
"""
DC2S Endpoint Validation Script with Authentication
Run this BEFORE Week 1 production hardening
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5059"  # Your backend URL
ACCOUNT_ID = 372  # DC2S account for customer 5 (dc_super1@supermicro.com)
CUSTOMER_ID = 5

# AUTHENTICATION
EMAIL = "dc_super1@supermicro.com"
PASSWORD = "dc_super321"
LOGIN_ENDPOINT = "/api/login"  # Your login endpoint

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class AuthenticatedTester:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.tests_skipped = 0
        self.results = []
        self.session = requests.Session()
        self.authenticated = False
    
    def login(self):
        """Authenticate with the API"""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}AUTHENTICATION{RESET}")
        print(f"{BLUE}{'='*70}{RESET}")
        
        login_url = f"{BASE_URL}{LOGIN_ENDPOINT}"
        
        try:
            # Try JSON body login with email
            response = self.session.post(
                login_url,
                json={"email": EMAIL, "password": PASSWORD},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"{GREEN}✅ Logged in successfully as {EMAIL}{RESET}")
                self.authenticated = True
                return True
            
            # Try with username field
            response = self.session.post(
                login_url,
                json={"username": EMAIL, "password": PASSWORD},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"{GREEN}✅ Logged in successfully as {EMAIL}{RESET}")
                self.authenticated = True
                return True
            
            print(f"{RED}❌ Login failed: Status {response.status_code}{RESET}")
            print(f"   Response: {response.text[:200]}")
            return False
        
        except Exception as e:
            print(f"{RED}❌ Login error: {e}{RESET}")
            return False
    
    def test_endpoint(self, name, method, endpoint, data=None, 
                     expected_status=200, required=True, timeout=60):
        """Test a single endpoint"""
        url = f"{BASE_URL}{endpoint}"
        
        print(f"\n{'='*70}")
        print(f"Testing: {name}")
        print(f"  {method} {endpoint}")
        print(f"{'='*70}")
        
        try:
            # Make request using session (which has auth cookies)
            if method == "GET":
                response = self.session.get(url, timeout=timeout)
            elif method == "POST":
                response = self.session.post(url, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Check status
            if response.status_code == expected_status:
                print(f"{GREEN}✅ Status: {response.status_code}{RESET}")
                
                # Try to parse JSON
                try:
                    json_data = response.json()
                    print(f"{GREEN}✅ Valid JSON response{RESET}")
                    
                    # Show sample of response
                    if isinstance(json_data, dict):
                        print(f"   Response keys: {list(json_data.keys())[:5]}")
                    
                    self.tests_passed += 1
                    self.results.append({
                        'name': name,
                        'status': 'PASS',
                        'required': required
                    })
                    return json_data
                
                except json.JSONDecodeError:
                    print(f"{YELLOW}⚠️  Response is not JSON{RESET}")
                    if required:
                        self.tests_failed += 1
                    else:
                        self.tests_skipped += 1
                    return None
            
            else:
                print(f"{RED}❌ Status: {response.status_code} (Expected: {expected_status}){RESET}")
                print(f"   Response: {response.text[:200]}")
                
                if required:
                    self.tests_failed += 1
                else:
                    self.tests_skipped += 1
                
                self.results.append({
                    'name': name,
                    'status': 'FAIL' if required else 'SKIP',
                    'required': required,
                    'reason': f'Status {response.status_code}'
                })
                return None
        
        except requests.exceptions.ConnectionError:
            print(f"{RED}❌ Connection Error: Cannot reach {BASE_URL}{RESET}")
            print(f"   Is the server running on port 5059?")
            if required:
                self.tests_failed += 1
            else:
                self.tests_skipped += 1
            return None
        
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}")
            if required:
                self.tests_failed += 1
            else:
                self.tests_skipped += 1
            return None
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        print(f"\n{GREEN}✅ Passed: {self.tests_passed}{RESET}")
        print(f"{RED}❌ Failed: {self.tests_failed}{RESET}")
        print(f"{YELLOW}⚠️  Skipped: {self.tests_skipped}{RESET}")
        
        print(f"\nTotal: {self.tests_passed + self.tests_failed + self.tests_skipped}")
        
        # Show failed tests
        if self.tests_failed > 0:
            print(f"\n{RED}FAILED TESTS:{RESET}")
            for result in self.results:
                if result['status'] == 'FAIL':
                    print(f"  ❌ {result['name']}")
                    if 'reason' in result:
                        print(f"     Reason: {result['reason']}")
        
        # Show skipped tests
        if self.tests_skipped > 0:
            print(f"\n{YELLOW}SKIPPED TESTS (Optional endpoints):{RESET}")
            for result in self.results:
                if result['status'] == 'SKIP':
                    print(f"  ⚠️  {result['name']}")
        
        print("\n" + "="*70)
        
        # Final decision
        required_failures = sum(1 for r in self.results if r['status'] == 'FAIL' and r.get('required', True))
        
        if required_failures == 0:
            print(f"{GREEN}✅ ALL REQUIRED ENDPOINTS WORKING!{RESET}")
            print(f"{GREEN}✅ READY TO PROCEED WITH WEEK 1 PRODUCTION HARDENING{RESET}")
            return True
        else:
            print(f"{RED}❌ {required_failures} REQUIRED ENDPOINT(S) FAILING{RESET}")
            print(f"{RED}❌ FIX ISSUES BEFORE PROCEEDING WITH WEEK 1{RESET}")
            return False


def main():
    print("="*70)
    print("DC2S ENDPOINT VALIDATION")
    print(f"Base URL: {BASE_URL}")
    print(f"Account ID: {ACCOUNT_ID}")
    print(f"Customer ID: {CUSTOMER_ID}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*70)
    
    tester = AuthenticatedTester()
    
    # Step 1: Login
    if not tester.login():
        print(f"\n{RED}❌ Authentication failed!{RESET}")
        print(f"\n{YELLOW}Please update EMAIL and PASSWORD in the script:{RESET}")
        print(f"   nano test_dc2s_endpoints_auth.py")
        print(f"   # Update lines 13-14:")
        print(f"   EMAIL = \"your_email@example.com\"")
        print(f"   PASSWORD = \"your_password\"")
        sys.exit(1)
    
    # Step 2: Test critical endpoints
    print(f"\n{'='*70}")
    print("TESTING CRITICAL ENDPOINTS")
    print("="*70)
    
    tester.test_endpoint(
        name="Get All Accounts",
        method="GET",
        endpoint="/api/dc2s/accounts",
        required=True
    )
    
    tester.test_endpoint(
        name="Get Account Details",
        method="GET",
        endpoint=f"/api/dc2s/accounts/{ACCOUNT_ID}",
        required=True
    )
    
    tester.test_endpoint(
        name="Get Account KPIs",
        method="GET",
        endpoint=f"/api/dc2s/accounts/{ACCOUNT_ID}/kpis",
        required=True
    )
    
    # Signal Analyst endpoints are under /api/signal-analyst, not /api/dc2s/signal-analyst
    # Use longer timeout for signal analyst as it may take time
    result = tester.test_endpoint(
        name="Run Signal Analyst",
        method="POST",
        endpoint="/api/signal-analyst/analyze",
        data={
            "account_id": ACCOUNT_ID,
            "analysis_type": "comprehensive",
            "time_horizon_days": 60
        },
        required=True,
        timeout=120  # Signal analyst may take longer
    )
    
    if result:
        print(f"\n{GREEN}Signal Analyst Response Preview:{RESET}")
        if 'analysis' in result:
            print(f"  Health Status: {result.get('analysis', {}).get('health_status', 'N/A')}")
        if 'cost' in result:
            print(f"  Total Cost: ${result.get('cost', {}).get('total_cost', 0):.6f}")
    
    # Step 3: Test optional endpoints
    print(f"\n{'='*70}")
    print("TESTING OPTIONAL ENDPOINTS")
    print("="*70)
    
    tester.test_endpoint(
        name="Get All KPIs",
        method="GET",
        endpoint="/api/dc2s/kpis/all",
        required=False
    )
    
    tester.test_endpoint(
        name="Get KPI Definitions",
        method="GET",
        endpoint="/api/dc2s/kpis",
        required=False
    )
    
    tester.test_endpoint(
        name="Get Account Health Score",
        method="GET",
        endpoint=f"/api/dc2s/health-score/{ACCOUNT_ID}",
        required=False
    )
    
    tester.test_endpoint(
        name="Get Account Recommendations",
        method="GET",
        endpoint=f"/api/dc2s/recommendations/{ACCOUNT_ID}",
        required=False
    )
    
    # Print summary
    ready = tester.print_summary()
    
    # Exit code
    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Test interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{RED}Fatal error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


