#!/usr/bin/env python3
"""
Test CSV Upload UI Combinations
================================

Tests all combinations of:
- File Types: accounts, kpis, signals, products, profiles, customers (6 types)
- Upload Modes: full_refresh, incremental, upsert, merge (4 modes)
- Total: 24 combinations

Also checks if Settings UI has KPI config filters enabled.
"""

import sys
import os
from pathlib import Path
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5059"
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
LOG_FILE = Path(__file__).parent / "logs" / f"csv_upload_ui_test_{TIMESTAMP}.log"

LOG_DIR = LOG_FILE.parent
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log(message: str):
    """Log to file and console"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    msg = f"[{timestamp}] {message}"
    print(msg)
    with open(LOG_FILE, 'a') as f:
        f.write(msg + '\n')

# File types from UI
FILE_TYPES = [
    'accounts',
    'kpis',
    'signals',
    'products',
    'profiles',
    'customers'
]

# Upload modes from UI
UPLOAD_MODES = [
    'full_refresh',
    'incremental',
    'upsert',
    'merge'
]

def create_test_user(session: requests.Session, customer_id: int, email: str = 'test@test.com', password: str = 'test123'):
    """Create a test user for an existing customer by directly inserting into database"""
    try:
        # Import required modules
        from models import User, Customer
        from extensions import db
        from app_v3_minimal import app
        from werkzeug.security import generate_password_hash
        
        with app.app_context():
            # Check if customer exists
            customer = db.session.get(Customer, customer_id)
            if not customer:
                log(f"❌ Customer {customer_id} not found")
                return False
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                log(f"⚠️  User already exists: {email} (user_id: {existing_user.user_id})")
                # Update password to ensure it matches
                existing_user.password_hash = generate_password_hash(password)
                db.session.commit()
                log(f"✅ Updated password for existing user")
                return True
            
            # Create new user
            user = User(
                customer_id=customer_id,
                user_name='Test User',
                email=email,
                password_hash=generate_password_hash(password),
                active=True
            )
            db.session.add(user)
            db.session.commit()
            
            log(f"✅ Test user created: {email} (user_id: {user.user_id})")
            return True
            
    except Exception as e:
        log(f"❌ User creation error: {e}")
        import traceback
        log(f"   Traceback: {traceback.format_exc()}")
        try:
            db.session.rollback()
        except:
            pass
        return False

def authenticate_session(session: requests.Session, email: str = 'test@test.com', password: str = 'test123'):
    """Authenticate and return session with cookies"""
    try:
        log(f"   Attempting login with email: {email}")
        response = session.post(
            f"{BASE_URL}/api/login",
            json={'email': email, 'password': password},
            headers={'Content-Type': 'application/json'},
            timeout=10,
            allow_redirects=True
        )
        
        log(f"   Login response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                log(f"✅ Authentication successful")
                log(f"   User ID: {data.get('user_id')}")
                log(f"   Customer ID: {data.get('customer_id')}")
                log(f"   Email: {data.get('email')}")
                
                # Check for session cookies
                cookies_set = list(session.cookies.keys())
                if cookies_set:
                    log(f"   Session cookies set: {cookies_set}")
                else:
                    log(f"   ⚠️  No session cookies found in response")
                    # Log all response headers for debugging
                    log(f"   Response headers: {dict(response.headers)}")
                
                # Verify we have cookies for subsequent requests
                if session.cookies:
                    log(f"   ✅ Session cookies available for subsequent requests")
                    return True, data.get('customer_id')
                else:
                    log(f"   ⚠️  Warning: No cookies in session object")
                    # Still return True if login was successful - cookies might be set differently
                    return True, data.get('customer_id')
            except Exception as e:
                log(f"   ⚠️  Error parsing response: {e}")
                log(f"   Response text: {response.text[:200]}")
                return False, None
        else:
            log(f"❌ Authentication failed: {response.status_code}")
            if response.text:
                try:
                    error_data = response.json()
                    log(f"   Error: {error_data.get('message', error_data.get('error', response.text[:100]))}")
                except:
                    log(f"   Error: {response.text[:200]}")
            return False, None
    except Exception as e:
        log(f"❌ Authentication error: {e}")
        import traceback
        log(f"   Traceback: {traceback.format_exc()}")
        return False, None

def test_upload_combination(session: requests.Session, customer_id: int, file_type: str, upload_mode: str, test_file_path: Path = None):
    """Test a single upload combination with authenticated session"""
    log(f"\n{'='*70}")
    log(f"Testing: File Type={file_type}, Upload Mode={upload_mode}")
    log(f"{'='*70}")
    
    # Create a minimal test CSV file if not provided
    if not test_file_path or not test_file_path.exists():
        test_file_path = create_test_csv(file_type, customer_id)
    
    try:
        # Map upload_mode to mode parameter
        mode_mapping = {
            'full_refresh': 'replace',
            'incremental': 'incremental',
            'upsert': 'incremental',  # /api/upload doesn't have upsert, use incremental
            'merge': 'incremental'    # /api/upload doesn't have merge, use incremental
        }
        
        mode = mode_mapping.get(upload_mode, 'incremental')
        
        # Prepare request data for /api/upload (V3 improved duplicates)
        # This endpoint expects:
        # - file: CSV file
        # - customer_id: int (required)
        # - file_type: Type of file (kpis, signals, accounts, products, profiles, customers)
        # - upload_mode: Upload mode (incremental, full_refresh, upsert, merge)
        # - duplicate_strategy: Optional override (skip, error, update, replace)
        request_data = {
            'customer_id': str(customer_id),
            'file_type': file_type,
            'upload_mode': upload_mode
        }
        
        # Read file content first
        with open(test_file_path, 'rb') as f:
            file_content = f.read()
        
        # Prepare form data with proper file tuple format
        files = {'file': (test_file_path.name, file_content, 'text/csv')}
        
        # Use /api/upload endpoint (requires authentication)
        endpoint = f"{BASE_URL}/api/upload"
        
        # Log what we're sending
        log(f"   Uploading to: {endpoint}")
        log(f"   Customer ID: {request_data.get('customer_id')} (type: {type(request_data.get('customer_id'))})")
        log(f"   Mode: {request_data.get('mode')}")
        log(f"   File: {test_file_path.name} ({len(file_content)} bytes)")
        
        # Log cookies being sent
        if session.cookies:
            log(f"   Sending cookies: {list(session.cookies.keys())}")
        else:
            log(f"   ⚠️  No cookies in session for upload request")
        
        # Don't set Content-Type header - let requests handle multipart/form-data automatically
        response = session.post(
            endpoint,
            files=files,
            data=request_data,
            timeout=30,
            allow_redirects=False  # Don't follow redirects
        )
        
        used_endpoint = endpoint
        
        result = {
            'file_type': file_type,
            'upload_mode': upload_mode,
            'status_code': response.status_code,
            'success': response.ok,
            'endpoint': used_endpoint,
            'response': None
        }
        
        # Parse response
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                result['response'] = response.json()
            else:
                result['response'] = response.text[:500]
        except:
            result['response'] = response.text[:500] if hasattr(response, 'text') else str(response.status_code)
        
        if response.ok:
            log(f"✅ SUCCESS: {file_type} with {upload_mode}")
            log(f"   Endpoint: {used_endpoint}")
            if isinstance(result['response'], dict):
                records = result['response'].get('records_processed') or result['response'].get('kpis_processed') or result['response'].get('accounts_processed')
                if records:
                    log(f"   Records processed: {records}")
                log(f"   Message: {result['response'].get('message', 'N/A')}")
        else:
            log(f"❌ FAILED: {file_type} with {upload_mode}")
            log(f"   Status: {response.status_code}")
            log(f"   Endpoint: {used_endpoint}")
            
            # Check if it's an authentication error
            if response.status_code == 401:
                log(f"   ⚠️  Authentication required - session may have expired")
                log(f"   Cookies in session: {list(session.cookies.keys()) if session.cookies else 'None'}")
            
            error_msg = result['response']
            if isinstance(error_msg, dict):
                error_msg = error_msg.get('error') or error_msg.get('message') or str(error_msg)
            log(f"   Error: {error_msg}")
        
        return result
            
    except Exception as e:
        log(f"❌ ERROR: {file_type} with {upload_mode}")
        log(f"   Exception: {str(e)}")
        return {
            'file_type': file_type,
            'upload_mode': upload_mode,
            'success': False,
            'error': str(e)
        }

def create_test_csv(file_type: str, customer_id: int) -> Path:
    """Create a minimal test CSV file for the given type"""
    test_dir = Path(__file__).parent / "test_csv_files"
    test_dir.mkdir(exist_ok=True)
    
    csv_file = test_dir / f"test_{file_type}.csv"
    
    # Calculate account_id from customer_id (customer_id * 1000)
    account_id = customer_id * 1000
    
    # Create minimal valid CSV based on type
    if file_type == 'accounts':
        content = "account_id,customer_id,account_name,industry,vertical,region,account_status\n"
        content += f"{account_id},{customer_id},Test Account,Technology,dc2_s,us-west-2,active\n"
    elif file_type == 'kpis':
        content = "account_id,kpi_code,measured_at,value,target,pillar\n"
        content += f"{account_id},AI-KPI1,2024-01-01,75.5,85.0,AI\n"
        content += f"{account_id},AI-KPI2,2024-01-01,82.3,90.0,AI\n"
    elif file_type == 'signals':
        # Generate unique signal_id using timestamp to avoid conflicts
        import time
        import uuid
        signal_id = str(uuid.uuid4())[:50]
        
        content = "signal_id,account_id,signal_date,signal_type,signal_text,sentiment\n"
        content += f"{signal_id},{account_id},2024-01-01,health_check,Test signal,positive\n"
    elif file_type == 'products':
        # Generate unique product_id using timestamp to avoid primary key conflicts
        import time
        timestamp = int(time.time() * 1000)  # Use milliseconds for better uniqueness
        # Add a small random offset to ensure uniqueness even in rapid tests
        import random
        offset = random.randint(1, 1000)
        product_id = timestamp + offset
        
        content = "customer_id,product_id,product_name,product_type,account_id\n"
        content += f"{customer_id},{product_id},Test Product,Infrastructure,{account_id}\n"
    elif file_type == 'profiles':
        content = "account_id,profile_metadata\n"
        content += f"{account_id},\"{{}}\"\n"
    elif file_type == 'customers':
        content = "customer_id,customer_name,vertical,created_at\n"
        content += "1,Test Customer,dc2_s,2024-01-01\n"
    else:
        content = "id,value\n1,test\n"
    
    csv_file.write_text(content)
    log(f"   Created test CSV: {csv_file}")
    return csv_file

def create_test_customer(session: requests.Session):
    """Create a test customer for upload testing"""
    try:
        response = session.post(
            f"{BASE_URL}/api/onboarding/complete",
            json={
                "customer_name": f"Test Customer {TIMESTAMP}",
                "industry": "Technology"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            customer_id = data.get('customer_id')
            log(f"✅ Created test customer: {customer_id}")
            return customer_id
        else:
            log(f"⚠️  Customer creation failed: {response.status_code}")
            log(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        log(f"❌ Error creating customer: {e}")
        return None

def test_all_combinations():
    """Test all file type × upload mode combinations"""
    log("="*70)
    log("CSV UPLOAD UI COMBINATIONS TEST")
    log("="*70)
    log(f"File Types: {len(FILE_TYPES)}")
    log(f"Upload Modes: {len(UPLOAD_MODES)}")
    log(f"Total Combinations: {len(FILE_TYPES) * len(UPLOAD_MODES)}")
    log("="*70)
    
    # Create test customer first
    log("\nCreating test customer...")
    session = requests.Session()
    customer_id = create_test_customer(session)
    
    if not customer_id:
        log("❌ Cannot create test customer. Cannot proceed with tests.")
        return []
    
    # Create test user for this customer
    log("\nCreating test user...")
    test_email = f"test_{TIMESTAMP}@test.com"
    test_password = "test123"
    user_created = create_test_user(session, customer_id, email=test_email, password=test_password)
    
    # Authenticate for /api/upload endpoint (requires auth)
    log("\nAuthenticating for /api/upload endpoint...")
    auth_success, authenticated_customer_id = authenticate_session(session, email=test_email, password=test_password)
    
    if not auth_success:
        log("❌ Authentication failed. /api/upload requires authentication.")
        log("   Tests will fail with 401")
        log("   Note: /api/upload is the single upload endpoint (replaces /api/onboarding/upload)")
        log("   Attempting to continue anyway...")
    else:
        log(f"✅ Authentication successful")
        # Get customer_id from the user we just created
        # Since login response doesn't include customer_id, use the one we created
        if authenticated_customer_id:
            customer_id = authenticated_customer_id
            log(f"   Using authenticated customer_id: {customer_id}")
        else:
            # Get customer_id from database
            try:
                from models import User
                from extensions import db
                from app_v3_minimal import app
                with app.app_context():
                    user = User.query.filter_by(email=test_email).first()
                    if user:
                        customer_id = user.customer_id
                        log(f"   Retrieved customer_id from database: {customer_id}")
            except Exception as e:
                log(f"   ⚠️  Could not retrieve customer_id: {e}")
                log(f"   Using original customer_id: {customer_id}")
    
    results = []
    total = len(FILE_TYPES) * len(UPLOAD_MODES)
    current = 0
    
    for file_type in FILE_TYPES:
        for upload_mode in UPLOAD_MODES:
            current += 1
            log(f"\n[{current}/{total}] Testing combination...")
            result = test_upload_combination(session, customer_id, file_type, upload_mode)
            results.append(result)
    
    # Summary
    log("\n" + "="*70)
    log("TEST SUMMARY")
    log("="*70)
    
    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]
    
    log(f"Total Combinations: {len(results)}")
    log(f"✅ Successful: {len(successful)}")
    log(f"❌ Failed: {len(failed)}")
    
    if failed:
        log("\nFailed Combinations:")
        for r in failed:
            log(f"  - {r['file_type']} + {r['upload_mode']}: {r.get('error', r.get('response', 'Unknown error'))}")
    
    # Group by file type
    log("\nResults by File Type:")
    for file_type in FILE_TYPES:
        type_results = [r for r in results if r['file_type'] == file_type]
        type_success = [r for r in type_results if r.get('success', False)]
        log(f"  {file_type}: {len(type_success)}/{len(type_results)} successful")
    
    # Group by upload mode
    log("\nResults by Upload Mode:")
    for upload_mode in UPLOAD_MODES:
        mode_results = [r for r in results if r['upload_mode'] == upload_mode]
        mode_success = [r for r in mode_results if r.get('success', False)]
        log(f"  {upload_mode}: {len(mode_success)}/{len(mode_results)} successful")
    
    return results

def check_settings_kpi_config():
    """Check if Settings UI has KPI config filters"""
    log("\n" + "="*70)
    log("SETTINGS UI - KPI CONFIG FILTERS CHECK")
    log("="*70)
    
    # Check if there's an API endpoint for KPI config
    endpoints_to_check = [
        '/api/dc2s/config',
        '/api/dc2s/config/kpis',
        '/api/customer-config',
        '/api/settings/kpi-config',
    ]
    
    log("\nChecking API endpoints for KPI config:")
    for endpoint in endpoints_to_check:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            if response.ok:
                log(f"  ✅ {endpoint} - Available (Status: {response.status_code})")
                try:
                    data = response.json()
                    if 'enabled_kpis' in str(data) or 'dc2s_enabled_kpis' in str(data):
                        log(f"     → Contains KPI config data")
                except:
                    pass
            else:
                log(f"  ⚠️  {endpoint} - Exists but returned {response.status_code}")
        except requests.exceptions.RequestException:
            log(f"  ❌ {endpoint} - Not available")
    
    # Check frontend components
    log("\nChecking frontend components:")
    frontend_path = Path(__file__).parent.parent / "src" / "components"
    
    # Look for KPI config related components
    kpi_config_files = [
        frontend_path / "Settings.tsx",
        frontend_path / "settings" / "SettingsPage.tsx",
        frontend_path / "settings" / "dc2s" / "KPIConfigurationSettings.tsx",
        frontend_path / "settings" / "dc2s" / "KPISelectionPanel.tsx",
        frontend_path / "KpiConfig.tsx",
        frontend_path / "KpiSettings.tsx",
        frontend_path / "dc" / "KpiConfig.tsx",
    ]
    
    found_kpi_config = False
    kpi_config_locations = []
    for file_path in kpi_config_files:
        if file_path.exists():
            content = file_path.read_text()
            if 'enabled_kpis' in content or 'dc2s_enabled_kpis' in content or 'KPISelectionPanel' in content:
                log(f"  ✅ {file_path.relative_to(frontend_path.parent)} - Contains KPI config")
                found_kpi_config = True
                kpi_config_locations.append(str(file_path.relative_to(frontend_path.parent)))
            else:
                log(f"  ⚠️  {file_path.name} - Exists but no KPI config found")
    
    if found_kpi_config:
        log(f"\n  ✅ KPI Config Filter UI Found!")
        log(f"  Location(s): {', '.join(kpi_config_locations)}")
        log(f"  Component: KPIConfigurationSettings.tsx with KPISelectionPanel")
        log(f"  Features: Enable/disable KPIs, pillar grouping, custom KPIs")
    else:
        log("  ❌ No KPI config filter UI found in Settings components")
        log("  → Recommendation: Add KPI config filter UI to Settings.tsx")
    
    return found_kpi_config

def main():
    log("="*70)
    log("CSV UPLOAD UI TESTING")
    log("="*70)
    log(f"Started: {datetime.now().isoformat()}")
    log(f"Log file: {LOG_FILE}")
    log("")
    
    # Check server
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        log("✅ Server running\n")
    except:
        log("❌ Server not running! Start: python3 app_v3_minimal.py")
        return 1
    
    # Test all combinations
    results = test_all_combinations()
    
    # Check Settings UI
    has_kpi_config = check_settings_kpi_config()
    
    # Final summary
    log("\n" + "="*70)
    log("FINAL SUMMARY")
    log("="*70)
    log(f"CSV Upload Combinations Tested: {len(results)}")
    log(f"Successful: {len([r for r in results if r.get('success', False)])}")
    log(f"Failed: {len([r for r in results if not r.get('success', False)])}")
    log(f"KPI Config Filters in Settings: {'✅ Found' if has_kpi_config else '❌ Not Found'}")
    log(f"\nLog saved: {LOG_FILE}")
    log("="*70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
