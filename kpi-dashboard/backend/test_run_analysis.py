#!/usr/bin/env python3
"""
Test Run Analysis functionality on Executive Dashboard
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = 'http://localhost:5059'

def log(message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")

def authenticate(email, password):
    """Authenticate and get session cookie"""
    session = requests.Session()
    
    log(f"Authenticating as {email}...")
    response = session.post(
        f"{BASE_URL}/api/login",
        json={'email': email, 'password': password},
        timeout=30
    )
    
    if response.status_code == 200:
        log("✅ Authentication successful")
        return session
    else:
        log(f"❌ Authentication failed: {response.status_code}")
        log(f"   Response: {response.text[:200]}")
        return None

def get_accounts(session, customer_id):
    """Get accounts for the customer"""
    log(f"Fetching accounts for customer {customer_id}...")
    response = session.get(
        f"{BASE_URL}/api/accounts",
        headers={'X-Customer-ID': str(customer_id)},
        timeout=30
    )
    
    if response.status_code == 200:
        accounts = response.json()
        log(f"✅ Found {len(accounts)} account(s)")
        return accounts
    else:
        log(f"❌ Failed to fetch accounts: {response.status_code}")
        return []

def test_run_analysis(session, account_id):
    """Test the run analysis endpoint"""
    log(f"Testing Run Analysis for account {account_id}...")
    
    response = session.post(
        f"{BASE_URL}/api/signal-analyst/analyze",
        json={
            'account_id': account_id,
            'analysis_type': 'comprehensive'
        },
        timeout=120  # Analysis may take time
    )
    
    if response.status_code == 200:
        result = response.json()
        log("✅ Analysis completed successfully!")
        log(f"   Health Score: {result.get('health_score', 'N/A')}")
        log(f"   Churn Probability: {result.get('churn_probability', 'N/A')}%")
        log(f"   Expansion Probability: {result.get('expansion_probability', 'N/A')}%")
        
        if result.get('recommended_actions'):
            log(f"   Recommended Actions: {len(result['recommended_actions'])}")
            for i, action in enumerate(result['recommended_actions'][:3], 1):
                action_text = action if isinstance(action, str) else action.get('action', str(action))
                log(f"      {i}. {action_text[:80]}...")
        
        if result.get('reasoning'):
            reasoning = result['reasoning'][:200]
            log(f"   Reasoning: {reasoning}...")
        
        return True
    else:
        log(f"❌ Analysis failed: {response.status_code}")
        try:
            error_data = response.json()
            log(f"   Error: {error_data.get('error', 'Unknown error')}")
        except:
            log(f"   Response: {response.text[:200]}")
        return False

def main():
    log("=" * 70)
    log("RUN ANALYSIS TEST - Executive Dashboard")
    log("=" * 70)
    
    # Get test credentials from database
    try:
        from app_v3_minimal import app
        from extensions import db
        from models import Customer, Account, User
        
        with app.app_context():
            latest_customer = Customer.query.order_by(Customer.customer_id.desc()).first()
            if not latest_customer:
                log("❌ No customers found in database")
                return 1
            
            customer_id = latest_customer.customer_id
            account = Account.query.filter_by(customer_id=customer_id).first()
            user = User.query.filter_by(customer_id=customer_id).first()
            
            if not account:
                log("❌ No accounts found for customer")
                return 1
            
            if not user:
                log("❌ No user found for customer")
                return 1
            
            email = user.email
            # Try common test passwords
            password = "test123"  # Default from test_csv_upload_ui_combinations.py
            account_id = account.account_id
            
            log(f"Customer ID: {customer_id}")
            log(f"Account ID: {account_id}")
            log(f"Email: {email}")
    except Exception as e:
        log(f"❌ Error getting test data: {e}")
        return 1
    
    # Authenticate
    session = authenticate(email, password)
    if not session:
        return 1
    
    # Use account_id from database query (already have it)
    test_account_id = account_id
    test_account_name = account.account_name
    
    log("")
    log("=" * 70)
    log(f"Testing Run Analysis on Account: {test_account_id}")
    log(f"Account Name: {test_account_name}")
    log("=" * 70)
    
    success = test_run_analysis(session, test_account_id)
    
    log("")
    log("=" * 70)
    if success:
        log("✅ RUN ANALYSIS TEST PASSED")
    else:
        log("❌ RUN ANALYSIS TEST FAILED")
    log("=" * 70)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
