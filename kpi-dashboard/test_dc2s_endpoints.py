#!/usr/bin/env python3
"""
DC2S Endpoint Validation Script
Run this BEFORE Week 1 production hardening to ensure all client-facing endpoints work
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5059"  # Update if different
ACCOUNT_ID = 1007  # Syntara account
CUSTOMER_ID = 1

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

class EndpointTester:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.tests_skipped = 0
        self.results = []
    
    def test_endpoint(self, name, method, endpoint, data=None, 
                     expected_status=200, required=True):
        """Test a single endpoint"""
        url = f"{BASE_URL}{endpoint}"
        
        print(f"\n{'='*70}")
        print(f"Testing: {name}")
        print(f"  {method} {endpoint}")
        print(f"{'='*70}")
        
        try:
            # Make request
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=10)
            elif method == "PUT":
                response = requests.put(url, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Check status
            if response.status_code == expected_status:
                print(f"{GREEN}✅ Status: {response.status_code} (Expected: {expected_status}){RESET}")
                
                # Try to parse JSON
                try:
                    json_data = response.json()
                    print(f"{GREEN}✅ Valid JSON response{RESET}")
                    print(f"   Response keys: {list(json_data.keys())}")
                    
                    self.tests_passed += 1
                    self.results.append({
                        'name': name,
                        'status': 'PASS',
                        'http_status': response.status_code,
                        'required': required
                    })
                    return json_data
                
                except json.JSONDecodeError:
                    print(f"{YELLOW}⚠️  Response is not JSON{RESET}")
                    if required:
                        self.tests_failed += 1
                        self.results.append({
                            'name': name,
                            'status': 'FAIL',
                            'reason': 'Invalid JSON',
                            'required': required
                        })
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
                    'http_status': response.status_code,
                    'reason': f'Expected {expected_status}',
                    'required': required
                })
                return None
        
        except requests.exceptions.ConnectionError:
            print(f"{RED}❌ Connection Error: Cannot reach {BASE_URL}{RESET}")
            print(f"   Is the server running?")
            if required:
                self.tests_failed += 1
            else:
                self.tests_skipped += 1
            self.results.append({
                'name': name,
                'status': 'FAIL' if required else 'SKIP',
                'reason': 'Connection error',
                'required': required
            })
            return None
        
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}")
            if required:
                self.tests_failed += 1
            else:
                self.tests_skipped += 1
            self.results.append({
                'name': name,
                'status': 'FAIL' if required else 'SKIP',
                'reason': str(e),
                'required': required
            })
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
    
    tester = EndpointTester()
    
    # ==========================================================================
    # CRITICAL ENDPOINTS (Must work)
    # ==========================================================================
    
    print("\n" + "="*70)
    print("TESTING CRITICAL ENDPOINTS")
    print("="*70)
    
    # 1. KPI Endpoints
    tester.test_endpoint(
        name="Get Account KPIs",
        method="GET",
        endpoint=f"/api/dc2s/kpis/{ACCOUNT_ID}",
        required=True
    )
    
    # 2. Account Endpoints
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
    
    # 3. Signals Endpoints
    tester.test_endpoint(
        name="Get Account Signals",
        method="GET",
        endpoint=f"/api/dc2s/signals/{ACCOUNT_ID}",
        required=True
    )
    
    # 4. Signal Analyst Endpoint
    result = tester.test_endpoint(
        name="Run Signal Analyst",
        method="POST",
        endpoint="/api/dc2s/signal-analyst/analyze",
        data={
            "account_id": ACCOUNT_ID,
            "customer_id": CUSTOMER_ID
        },
        required=True
    )
    
    if result:
        print(f"\n{GREEN}Signal Analyst Response Preview:{RESET}")
        print(f"  Health Status: {result.get('analysis', {}).get('health_status', 'N/A')}")
        print(f"  Total Cost: ${result.get('cost', {}).get('total_cost', 0):.6f}")
    
    # ==========================================================================
    # OPTIONAL ENDPOINTS (Nice to have)
    # ==========================================================================
    
    print("\n" + "="*70)
    print("TESTING OPTIONAL ENDPOINTS")
    print("="*70)
    
    # KPI Trends
    tester.test_endpoint(
        name="Get KPI Trends",
        method="GET",
        endpoint=f"/api/dc2s/kpis/{ACCOUNT_ID}/trend?kpi_code=P1-KPI1",
        required=False
    )
    
    # Analysis History
    tester.test_endpoint(
        name="Get Analysis History",
        method="GET",
        endpoint=f"/api/dc2s/signal-analyst/history/{ACCOUNT_ID}",
        required=False
    )
    
    # Embedding Status
    tester.test_endpoint(
        name="Get Embedding Status",
        method="GET",
        endpoint=f"/api/dc2s/embeddings/status?customer_id={CUSTOMER_ID}",
        required=False
    )
    
    # Add Signal
    tester.test_endpoint(
        name="Add New Signal",
        method="POST",
        endpoint="/api/dc2s/signals/add",
        data={
            "account_id": ACCOUNT_ID,
            "signal_type": "test",
            "subject": "Endpoint Test Signal",
            "summary": "This is a test signal from automated endpoint validation",
            "sentiment": "neutral",
            "priority": "low"
        },
        required=False
    )
    
    # ==========================================================================
    # PRINT SUMMARY
    # ==========================================================================
    
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
        sys.exit(1)
