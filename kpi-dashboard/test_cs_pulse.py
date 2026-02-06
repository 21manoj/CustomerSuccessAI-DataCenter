#!/usr/bin/env python3
"""
CS Pulse Test Suite - Python Version
=====================================

Comprehensive testing for backend APIs and database validation.

Usage:
    python test_cs_pulse.py
    python test_cs_pulse.py --skip-analysis  # Skip slow Signal Analyst test
    python test_cs_pulse.py --verbose        # Show full responses

Ports:
    Backend:  5059
    Frontend: 8005
"""

import requests
import json
import time
import sys
import argparse
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

BACKEND_URL = "http://localhost:5059"
FRONTEND_URL = "http://localhost:8005"
TIMEOUT = 60  # seconds for Signal Analyst

# ============================================================================
# Test Results Tracking
# ============================================================================

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.details = []
    
    def add_pass(self, name, message=""):
        self.passed += 1
        self.details.append(("PASS", name, message))
        print(f"  ✅ PASS: {name}")
        if message:
            print(f"     {message}")
    
    def add_fail(self, name, message=""):
        self.failed += 1
        self.details.append(("FAIL", name, message))
        print(f"  ❌ FAIL: {name}")
        if message:
            print(f"     {message}")
    
    def add_skip(self, name, message=""):
        self.skipped += 1
        self.details.append(("SKIP", name, message))
        print(f"  ⏭️  SKIP: {name}")
        if message:
            print(f"     {message}")
    
    def summary(self):
        total = self.passed + self.failed + self.skipped
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Skipped: {self.skipped}")
        
        if self.failed == 0:
            print("\n🎉 All tests passed!")
            return True
        else:
            print("\n⚠️  Some tests failed!")
            return False

results = TestResults()

# ============================================================================
# Helper Functions
# ============================================================================

def print_header(title):
    print("\n" + "="*60)
    print(title)
    print("="*60)

# Session for maintaining cookies
session = requests.Session()

def safe_get(url, timeout=10):
    """Safe GET request with error handling"""
    try:
        response = session.get(url, timeout=timeout)
        return response
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        return None

def safe_post(url, data, timeout=60):
    """Safe POST request with error handling"""
    try:
        response = session.post(url, json=data, timeout=timeout)
        return response
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        return None

def login():
    """Login to get session cookie"""
    login_url = f"{BACKEND_URL}/api/login"
    login_data = {
        "email": "admin@syntara.com",
        "password": "syntara123"
    }
    try:
        response = session.post(login_url, json=login_data, timeout=10)
        if response and response.status_code == 200:
            return True
        return False
    except:
        return False

# ============================================================================
# Pre-flight Checks
# ============================================================================

def preflight_checks():
    print_header("PRE-FLIGHT CHECKS")
    
    # Check backend
    print("\n[1] Checking backend server...")
    response = safe_get(f"{BACKEND_URL}/api/journey/health")
    if response and response.status_code == 200:
        results.add_pass("Backend server", f"Running on port 5059")
    else:
        results.add_fail("Backend server", "Not responding - start with: python app_v3_minimal.py")
        return False
    
    # Login to get session cookie
    print("\n[2] Logging in...")
    if login():
        results.add_pass("Authentication", "Logged in successfully")
    else:
        results.add_fail("Authentication", "Failed to login - check credentials")
        return False
    
    # Check frontend
    print("\n[3] Checking frontend server...")
    response = safe_get(FRONTEND_URL)
    if response:
        results.add_pass("Frontend server", f"Running on port 8005")
    else:
        results.add_skip("Frontend server", "Not running - manual browser tests needed")
    
    # Check OpenAI API key (load from backend/.env)
    print("\n[4] Checking OPENAI_API_KEY...")
    import os
    from dotenv import load_dotenv
    # Try loading from backend/.env
    backend_env = os.path.join(os.path.dirname(__file__), 'backend', '.env')
    if os.path.exists(backend_env):
        load_dotenv(backend_env)
    api_key = os.environ.get('OPENAI_API_KEY', '')
    if api_key:
        results.add_pass("OPENAI_API_KEY", f"Set ({api_key[:7]}...)")
    else:
        results.add_skip("OPENAI_API_KEY", "Not set - Signal Analyst tests will fail")
    
    return True

# ============================================================================
# Test Suite 1: Journey API
# ============================================================================

def test_journey_api():
    print_header("TEST SUITE 1: JOURNEY API")
    
    # 1.1 Health Check
    print("\n[1.1] Journey API Health Check")
    response = safe_get(f"{BACKEND_URL}/api/journey/health")
    if response and response.status_code == 200:
        data = response.json()
        if data.get('status') == 'healthy':
            results.add_pass("Health endpoint", f"Tables: {data.get('tables', {})}")
        else:
            results.add_fail("Health endpoint", "Unhealthy status")
    else:
        results.add_fail("Health endpoint", "Request failed")
    
    # 1.2 List Accounts
    print("\n[1.2] List Journey Accounts")
    response = safe_get(f"{BACKEND_URL}/api/journey/accounts")
    if response and response.status_code == 200:
        data = response.json()
        accounts = data.get('accounts', [])
        if len(accounts) >= 1:
            account_ids = [a.get('journey_account_id') for a in accounts]
            results.add_pass("List accounts", f"Found {len(accounts)}: {account_ids}")
        else:
            results.add_fail("List accounts", "No accounts found")
    else:
        results.add_fail("List accounts", "Request failed")
    
    # 1.3-1.5 Get Individual Accounts
    for account_id in ['10001', '10003', '10007']:
        print(f"\n[1.x] Get Account {account_id}")
        response = safe_get(f"{BACKEND_URL}/api/journey/{account_id}")
        if response and response.status_code == 200:
            data = response.json()
            weeks = len(data.get('weekly_data', []))
            name = data.get('account_name', 'Unknown')
            pattern = data.get('pattern_type', 'Unknown')
            results.add_pass(f"Account {account_id}", f"{name} - {weeks} weeks - {pattern}")
        else:
            results.add_fail(f"Account {account_id}", "Not found or error")
    
    # 1.6 Week Detail - Find a valid week from account data
    print("\n[1.6] Get Week Detail")
    # First get account data to find a valid week
    acc_response = safe_get(f"{BACKEND_URL}/api/journey/10001")
    if acc_response and acc_response.status_code == 200:
        acc_data = acc_response.json()
        weeks = acc_data.get('weekly_data', [])
        if weeks:
            valid_week = weeks[0].get('week_number', 8)  # Use first available week
            response = safe_get(f"{BACKEND_URL}/api/journey/10001/week/{valid_week}")
            if response and response.status_code == 200:
                data = response.json()
                health = data.get('health_score', '?')
                kpi_count = len(data.get('normalized_kpis', {}))
                results.add_pass("Week detail", f"Week {valid_week}: Health={health}, KPIs={kpi_count}")
            else:
                error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
                results.add_fail("Week detail", f"Week {valid_week}: {error_msg}")
        else:
            results.add_fail("Week detail", "No weekly data available")
    else:
        results.add_fail("Week detail", "Could not fetch account data to find valid week")
    
    # 1.7 Account Summary
    print("\n[1.7] Get Account Summary")
    response = safe_get(f"{BACKEND_URL}/api/journey/10001/summary")
    if response and response.status_code == 200:
        data = response.json()
        total_weeks = data.get('total_weeks', '?')
        avg_health = data.get('avg_health', '?')
        results.add_pass("Account summary", f"Weeks={total_weeks}, AvgHealth={avg_health}")
    else:
        results.add_fail("Account summary", "Request failed")

# ============================================================================
# Test Suite 2: Signal Analyst API
# ============================================================================

def test_signal_analyst_api(skip_analysis=False):
    print_header("TEST SUITE 2: SIGNAL ANALYST API")
    
    # 2.1 Endpoint Check
    print("\n[2.1] Signal Analyst Endpoint")
    response = safe_get(f"{BACKEND_URL}/api/signal-analyst/health")
    if response:
        results.add_pass("Endpoint accessible", f"HTTP {response.status_code}")
    else:
        results.add_skip("Endpoint check", "Could not verify")
    
    # 2.2 Run Analysis
    if skip_analysis:
        print("\n[2.2] Run Signal Analyst (SKIPPED)")
        results.add_skip("Signal Analyst analysis", "--skip-analysis flag set")
        return
    
    print("\n[2.2] Run Signal Analyst on Account 10001")
    print("     (This takes 15-20 seconds for GPT-4o API call...)")
    
    start_time = time.time()
    response = safe_post(
        f"{BACKEND_URL}/api/signal-analyst/analyze",
        {"account_id": "10001"},
        timeout=TIMEOUT
    )
    duration = time.time() - start_time
    
    if response and response.status_code == 200:
        try:
            data = response.json()
            health = data.get('health_score', '?')
            churn = data.get('churn_probability', '?')
            expansion = data.get('expansion_probability', '?')
            confidence = data.get('confidence', '?')
            outcome = data.get('predicted_outcome', '?')
            
            results.add_pass(
                "Signal Analyst analysis",
                f"Completed in {duration:.1f}s\n"
                f"     Health: {health}, Churn: {churn}%, Expansion: {expansion}%\n"
                f"     Outcome: {outcome}, Confidence: {confidence}"
            )
            
            # Validate response structure
            print("\n[2.3] Validate Response Structure")
            has_drivers = 'risk_drivers' in data and 'growth_drivers' in data
            has_actions = 'recommended_actions' in data
            if has_drivers and has_actions:
                risk_count = len(data.get('risk_drivers', []))
                growth_count = len(data.get('growth_drivers', []))
                action_count = len(data.get('recommended_actions', []))
                results.add_pass(
                    "Response structure",
                    f"Risk drivers: {risk_count}, Growth drivers: {growth_count}, Actions: {action_count}"
                )
            else:
                results.add_fail("Response structure", "Missing drivers or actions")
                
        except json.JSONDecodeError:
            results.add_fail("Signal Analyst analysis", "Invalid JSON response")
    elif response:
        results.add_fail("Signal Analyst analysis", f"HTTP {response.status_code}: {response.text[:100]}")
    else:
        results.add_fail("Signal Analyst analysis", "Request failed (timeout or connection error)")

# ============================================================================
# Test Suite 3: Database Verification
# ============================================================================

def test_database():
    print_header("TEST SUITE 3: DATABASE VERIFICATION")
    
    # 3.1 Accounts Count
    print("\n[3.1] Journey Accounts")
    response = safe_get(f"{BACKEND_URL}/api/journey/accounts")
    if response and response.status_code == 200:
        data = response.json()
        count = len(data.get('accounts', []))
        if count >= 3:
            results.add_pass("Accounts table", f"{count} accounts (expected 3+)")
        else:
            results.add_fail("Accounts table", f"Only {count} accounts (expected 3+)")
    else:
        results.add_fail("Accounts table", "Could not query")
    
    # 3.2 KPIs Data
    print("\n[3.2] Journey KPIs Data")
    response = safe_get(f"{BACKEND_URL}/api/journey/10001")
    if response and response.status_code == 200:
        data = response.json()
        weekly_data = data.get('weekly_data', [])
        if weekly_data and weekly_data[0].get('kpis'):
            kpi_count = len(weekly_data[0].get('kpis', {}))
            results.add_pass("KPIs data", f"{kpi_count} KPIs per week")
        else:
            results.add_fail("KPIs data", "No KPI data in weekly records")
    else:
        results.add_fail("KPIs data", "Could not query")
    
    # 3.3 Health Scores
    print("\n[3.3] Health Score Data")
    response = safe_get(f"{BACKEND_URL}/api/journey/10001")
    if response and response.status_code == 200:
        data = response.json()
        weekly_data = data.get('weekly_data', [])
        health_scores = [w.get('health_score') for w in weekly_data if w.get('health_score')]
        if health_scores:
            results.add_pass(
                "Health scores",
                f"{len(health_scores)} weeks, range: {min(health_scores)}-{max(health_scores)}"
            )
        else:
            results.add_fail("Health scores", "No health score data")
    else:
        results.add_fail("Health scores", "Could not query")

# ============================================================================
# Frontend URLs
# ============================================================================

def print_frontend_urls():
    print_header("FRONTEND TEST URLS")
    print("""
Open these URLs in your browser:

1. Executive Dashboard:
   http://localhost:8005/dashboard

2. Journey V3 - Account 10001 (Expansion pattern):
   http://localhost:8005/journey-v3/10001

3. Journey V3 - Account 10003 (Churn pattern):
   http://localhost:8005/journey-v3/10003

4. Journey V3 - Account 10007 (Recovery pattern):
   http://localhost:8005/journey-v3/10007
""")

def print_manual_checklist():
    print_header("MANUAL TEST CHECKLIST")
    print("""
Perform these tests in the browser:

□ Executive Dashboard
  □ Portfolio cards show total/healthy/at-risk/critical
  □ Account cards display with health scores
  □ Click ▶️ (Play) → Progress modal appears
  □ Modal shows 5 steps progressing
  □ After ~16s → 'View Results' button
  □ Account card updates after analysis

□ Journey Dashboard V3
  □ Header shows account name and health badge
  □ 5 tabs visible and clickable
  
  □ Tab 1: Health Overview
    □ Health timeline chart renders
    □ Pillar radar chart renders
    □ Week navigation works
    
  □ Tab 2: Qualitative Signals
    □ Summary cards (Total/Positive/Negative/Critical)
    □ Sentiment pie chart
    □ Signal timeline with filters
    
  □ Tab 3: Signal Analyst
    □ Health/Churn/Expansion cards
    □ Risk drivers with evidence
    □ Growth drivers with evidence
    □ Recommended actions
    
  □ Tab 4: Correlation
    □ Health vs Sentiment overlay chart
    □ Weekly sentiment heatmap
    □ Leading indicators cards
    
  □ Tab 5: Root Cause Analysis
    □ Urgency badge
    □ Health change summary
    □ Hypotheses (expandable)
    □ Event timeline
    □ Recommended actions

□ Navigation
  □ 'View Journey' navigates to journey page
  □ Back arrow returns to dashboard
""")

# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='CS Pulse Test Suite')
    parser.add_argument('--skip-analysis', action='store_true',
                       help='Skip Signal Analyst API test (saves ~20s)')
    parser.add_argument('--verbose', action='store_true',
                       help='Show verbose output')
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("CS PULSE TEST SUITE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend: {BACKEND_URL}")
    print(f"Frontend: {FRONTEND_URL}")
    print("="*60)
    
    # Run tests
    if not preflight_checks():
        print("\n❌ Pre-flight checks failed. Fix issues and retry.")
        sys.exit(1)
    
    test_journey_api()
    test_signal_analyst_api(skip_analysis=args.skip_analysis)
    test_database()
    
    # Print frontend info
    print_frontend_urls()
    print_manual_checklist()
    
    # Summary
    success = results.summary()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
