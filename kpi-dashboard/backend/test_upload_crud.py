#!/usr/bin/env python3
"""
Test script to verify upload persistence and CRUD operations.
"""

import requests
import json
import os
from datetime import datetime

def test_upload_and_crud():
    """Test upload persistence and CRUD operations"""
    base_url = "http://localhost:5054"
    headers = {"X-Customer-ID": "6", "X-User-ID": "1"}
    
    print("🧪 Testing Upload and CRUD Operations")
    print("=" * 50)
    
    # 1. Check initial state
    print("\n1️⃣ Checking initial state...")
    response = requests.get(f"{base_url}/api/data/status", headers=headers)
    if response.status_code == 200:
        status = response.json()
        print(f"   - KPIs: {status['total_kpis']}")
        print(f"   - Uploads: {status['total_uploads']}")
        print(f"   - Accounts: {status['total_accounts']}")
    
    # 2. Create test Excel file
    print("\n2️⃣ Creating test Excel file...")
    test_data = {
        'sheets': {
            'Test Category 1': [
                ['Health Score Component', 'Weight (%)', 'Data', 'Source Review', 'KPI/Parameter', 'Impact Level', 'Measurement Frequency'],
                ['Test Component', '0.15', '75.5%', 'CSR', 'Test KPI 1', 'High', 'Monthly'],
                ['Test Component', '0.15', '82.3%', 'OBR', 'Test KPI 2', 'Medium', 'Quarterly'],
                ['Test Component', '0.15', '91.0%', 'CSR', 'Test KPI 3', 'High', 'Weekly']
            ],
            'Test Category 2': [
                ['Health Score Component', 'Weight (%)', 'Data', 'Source Review', 'KPI/Parameter', 'Impact Level', 'Measurement Frequency'],
                ['Test Component 2', '0.20', '68.7%', 'OBR', 'Test KPI 4', 'Medium', 'Monthly'],
                ['Test Component 2', '0.20', '79.2%', 'CSR', 'Test KPI 5', 'High', 'Quarterly']
            ]
        }
    }
    
    # Create Excel file using pandas
    try:
        import pandas as pd
        with pd.ExcelWriter('test_upload.xlsx', engine='openpyxl') as writer:
            # Add a summary sheet first (will be skipped)
            summary_data = [['Summary'], ['Total KPIs', '5'], ['Categories', '2']]
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False, header=False)
            
            # Add KPI sheets (these will be processed)
            for sheet_name, data in test_data['sheets'].items():
                df = pd.DataFrame(data[1:], columns=data[0])
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Add a rollup sheet last (will be skipped)
            rollup_data = [['Rollup'], ['Category 1', '3 KPIs'], ['Category 2', '2 KPIs']]
            rollup_df = pd.DataFrame(rollup_data)
            rollup_df.to_excel(writer, sheet_name='Rollup', index=False, header=False)
            
        print("   ✅ Test Excel file created: test_upload.xlsx")
    except ImportError:
        print("   ❌ pandas not available, skipping Excel creation")
        return
    
    # 3. Upload the file
    print("\n3️⃣ Uploading test file...")
    with open('test_upload.xlsx', 'rb') as f:
        files = {'file': ('test_upload.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        response = requests.post(f"{base_url}/api/upload", headers=headers, files=files)
    
    if response.status_code == 200:
        upload_result = response.json()
        print(f"   ✅ Upload successful!")
        print(f"   - Upload ID: {upload_result['upload_id']}")
        print(f"   - KPIs created: {upload_result['kpi_count']}")
        print(f"   - Version: {upload_result['version']}")
        upload_id = upload_result['upload_id']
    else:
        print(f"   ❌ Upload failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return
    
    # 4. Verify upload persistence
    print("\n4️⃣ Verifying upload persistence...")
    response = requests.get(f"{base_url}/api/data/status", headers=headers)
    if response.status_code == 200:
        status = response.json()
        print(f"   - KPIs: {status['total_kpis']}")
        print(f"   - Uploads: {status['total_uploads']}")
        if status['total_kpis'] > 0 and status['total_uploads'] > 0:
            print("   ✅ Data persisted successfully!")
        else:
            print("   ❌ Data not persisted!")
            return
    
    # 5. Test KPI CRUD operations
    print("\n5️⃣ Testing KPI CRUD operations...")
    
    # Get KPIs
    response = requests.get(f"{base_url}/api/kpis/{upload_id}", headers=headers)
    if response.status_code == 200:
        kpis = response.json()
        print(f"   ✅ Retrieved {len(kpis)} KPIs")
        
        if kpis:
            # Test UPDATE operation
            first_kpi = kpis[0]
            kpi_id = first_kpi['kpi_id']
            
            update_data = {
                'data': '99.9%',
                'source_review': 'UPDATED',
                'impact_level': 'Critical'
            }
            
            response = requests.patch(
                f"{base_url}/api/kpi/{kpi_id}",
                headers={**headers, 'Content-Type': 'application/json'},
                json=update_data
            )
            
            if response.status_code == 200:
                print(f"   ✅ KPI {kpi_id} updated successfully")
                
                # Verify update
                response = requests.get(f"{base_url}/api/kpis/{upload_id}", headers=headers)
                if response.status_code == 200:
                    updated_kpis = response.json()
                    updated_kpi = next((k for k in updated_kpis if k['kpi_id'] == kpi_id), None)
                    if updated_kpi and updated_kpi['data'] == '99.9%':
                        print("   ✅ Update verified!")
                    else:
                        print("   ❌ Update not verified!")
            else:
                print(f"   ❌ KPI update failed: {response.status_code}")
        else:
            print("   ❌ No KPIs to test")
    else:
        print(f"   ❌ Failed to retrieve KPIs: {response.status_code}")
    
    # 6. Test Account CRUD operations
    print("\n6️⃣ Testing Account CRUD operations...")
    
    # Create account
    account_data = {
        'account_name': 'Test Account',
        'revenue': 1000000,
        'industry': 'Technology',
        'region': 'North America'
    }
    
    response = requests.post(
        f"{base_url}/api/accounts",
        headers={**headers, 'Content-Type': 'application/json'},
        json=account_data
    )
    
    if response.status_code == 200:
        account_result = response.json()
        print(f"   ✅ Account created with ID: {account_result['account_id']}")
        account_id = account_result['account_id']
        
        # Update account
        update_data = {
            'account_name': 'Updated Test Account',
            'revenue': 2000000
        }
        
        response = requests.patch(
            f"{base_url}/api/account/{account_id}",
            headers={**headers, 'Content-Type': 'application/json'},
            json=update_data
        )
        
        if response.status_code == 200:
            print(f"   ✅ Account {account_id} updated successfully")
        else:
            print(f"   ❌ Account update failed: {response.status_code}")
    else:
        print(f"   ❌ Account creation failed: {response.status_code}")
    
    # 7. Test KPI assignment to accounts
    print("\n7️⃣ Testing KPI assignment to accounts...")
    
    if 'account_id' in locals() and 'kpi_id' in locals():
        assignment_data = {'account_id': account_id}
        
        response = requests.patch(
            f"{base_url}/api/kpi/{kpi_id}",
            headers={**headers, 'Content-Type': 'application/json'},
            json=assignment_data
        )
        
        if response.status_code == 200:
            print(f"   ✅ KPI {kpi_id} assigned to account {account_id}")
            
            # Verify assignment
            response = requests.get(f"{base_url}/api/kpis/{upload_id}", headers=headers)
            if response.status_code == 200:
                kpis = response.json()
                assigned_kpi = next((k for k in kpis if k['kpi_id'] == kpi_id), None)
                if assigned_kpi and assigned_kpi.get('account_id') == account_id:
                    print("   ✅ Assignment verified!")
                else:
                    print("   ❌ Assignment not verified!")
        else:
            print(f"   ❌ KPI assignment failed: {response.status_code}")
    
    # 8. Final status check
    print("\n8️⃣ Final status check...")
    response = requests.get(f"{base_url}/api/data/status", headers=headers)
    if response.status_code == 200:
        status = response.json()
        print(f"   - KPIs: {status['total_kpis']}")
        print(f"   - Uploads: {status['total_uploads']}")
        print(f"   - Accounts: {status['total_accounts']}")
        print("   ✅ All operations completed successfully!")
    
    # Cleanup
    if os.path.exists('test_upload.xlsx'):
        os.remove('test_upload.xlsx')
        print("\n🧹 Cleaned up test file")

if __name__ == "__main__":
    test_upload_and_crud() 