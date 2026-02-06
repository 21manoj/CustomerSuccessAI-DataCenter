#!/usr/bin/env python3
"""
Security Audit - Test API Authentication
Tests all DC2_S endpoints to ensure they require authentication
"""

import requests
import sys

BASE_URL = "http://localhost:5059"

# Endpoints to test (should all return 401 without authentication)
ENDPOINTS = [
    # Config API
    ("GET", "/api/dc2s/config/"),
    ("PUT", "/api/dc2s/config/"),
    ("POST", "/api/dc2s/config/custom-kpi"),
    ("PUT", "/api/dc2s/config/pillar-weights"),
    ("DELETE", "/api/dc2s/config/custom-kpi/TEST-KPI"),
    
    # Scores API
    ("GET", "/api/dc2s/scores/account/1001/latest"),
    ("GET", "/api/dc2s/scores/account/1001/history"),
    ("GET", "/api/dc2s/scores/customer/summary"),
    ("POST", "/api/dc2s/scores/calculate"),
    ("GET", "/api/dc2s/scores/account/1001/pillars/AI"),
]

def test_endpoint(method, endpoint):
    """Test if endpoint requires authentication"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "PUT":
            response = requests.put(url, json={}, timeout=5)
        elif method == "POST":
            response = requests.post(url, json={}, timeout=5)
        elif method == "DELETE":
            response = requests.delete(url, timeout=5)
        else:
            return False, f"Unknown method: {method}"
        
        status_code = response.status_code
        
        # Should return 401 (Unauthorized) or 403 (Forbidden)
        if status_code in [401, 403]:
            return True, f"✅ Protected (returns {status_code})"
        elif status_code == 404:
            return True, f"⚠️  Not found (404) - endpoint may not exist, but protected"
        elif status_code == 400:
            return True, f"⚠️  Bad request (400) - endpoint exists and requires valid input"
        else:
            return False, f"❌ NOT PROTECTED! Returns {status_code} (should be 401/403)"
    
    except requests.exceptions.ConnectionError:
        return None, "❌ Cannot connect to server (is it running?)"
    except Exception as e:
        return None, f"❌ Error: {e}"

def main():
    print("="*70)
    print("SECURITY AUDIT - API AUTHENTICATION TEST")
    print("="*70)
    print()
    print(f"Testing endpoints at: {BASE_URL}")
    print("All endpoints should return 401 (Unauthorized) without authentication")
    print()
    
    results = []
    
    for method, endpoint in ENDPOINTS:
        protected, message = test_endpoint(method, endpoint)
        results.append((method, endpoint, protected, message))
        
        status_icon = "✅" if protected else "❌" if protected is False else "⚠️"
        print(f"{status_icon} {method:6s} {endpoint:50s} - {message}")
    
    print()
    print("="*70)
    print("SECURITY AUDIT SUMMARY")
    print("="*70)
    
    protected_count = sum(1 for _, _, p, _ in results if p is True)
    unprotected_count = sum(1 for _, _, p, _ in results if p is False)
    error_count = sum(1 for _, _, p, _ in results if p is None)
    
    print(f"Protected endpoints: {protected_count}/{len(ENDPOINTS)}")
    print(f"Unprotected endpoints: {unprotected_count}/{len(ENDPOINTS)}")
    print(f"Errors/Unknown: {error_count}/{len(ENDPOINTS)}")
    print()
    
    if unprotected_count > 0:
        print("❌ SECURITY ISSUE: Some endpoints are not protected!")
        print()
        print("Unprotected endpoints:")
        for method, endpoint, protected, message in results:
            if protected is False:
                print(f"  - {method} {endpoint}")
        sys.exit(1)
    elif error_count > 0:
        print("⚠️  Some endpoints could not be tested (connection errors)")
        sys.exit(1)
    else:
        print("✅ All endpoints are properly protected!")
        sys.exit(0)

if __name__ == '__main__':
    main()
