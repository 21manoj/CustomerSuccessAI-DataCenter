import requests
import json

def assign_kpis_to_accounts():
    """Assign KPIs to their respective accounts based on upload filename"""
    base_url = "http://localhost:5054"
    headers = {"X-Customer-ID": "6", "X-User-ID": "1"}
    
    # Get all uploads
    response = requests.get(f"{base_url}/api/uploads", headers=headers)
    if response.status_code != 200:
        print(f"Failed to get uploads: {response.status_code}")
        return
    
    uploads = response.json()
    print(f"Found {len(uploads)} uploads")
    
    # Get all accounts
    response = requests.get(f"{base_url}/api/accounts", headers=headers)
    if response.status_code != 200:
        print(f"Failed to get accounts: {response.status_code}")
        return
    
    accounts = response.json()
    print(f"Found {len(accounts)} accounts")
    
    # Create a mapping of company names to account IDs
    company_to_account = {}
    for account in accounts:
        company_name = account['account_name'].lower().replace(' ', '_').replace('&', 'and')
        company_to_account[company_name] = account['account_id']
    
    print("Company to account mapping:")
    for company, account_id in company_to_account.items():
        print(f"  {company} -> {account_id}")
    
    # Process each upload
    for upload in uploads:
        filename = upload['original_filename']
        upload_id = upload['upload_id']
        
        # Extract company name from filename
        if '_kpis.xlsx' in filename:
            company_name = filename.replace('_kpis.xlsx', '')
            print(f"\nProcessing upload {upload_id}: {filename}")
            print(f"Extracted company name: {company_name}")
            
            if company_name in company_to_account:
                account_id = company_to_account[company_name]
                print(f"Assigning to account {account_id}")
                
                # Get KPIs for this upload
                response = requests.get(f"{base_url}/api/kpis/{upload_id}", headers=headers)
                if response.status_code != 200:
                    print(f"Failed to get KPIs for upload {upload_id}")
                    continue
                
                kpis = response.json()
                print(f"Found {len(kpis)} KPIs to assign")
                
                # Assign each KPI to the account
                assigned_count = 0
                for kpi in kpis:
                    kpi_id = kpi['kpi_id']
                    
                    # Update KPI with account_id
                    update_data = {"account_id": account_id}
                    response = requests.patch(
                        f"{base_url}/api/kpi/{kpi_id}",
                        headers={**headers, "Content-Type": "application/json"},
                        json=update_data
                    )
                    
                    if response.status_code == 200:
                        assigned_count += 1
                    else:
                        print(f"Failed to assign KPI {kpi_id}: {response.status_code}")
                
                print(f"Successfully assigned {assigned_count} KPIs to account {account_id}")
            else:
                print(f"Company {company_name} not found in accounts")
        else:
            print(f"Skipping upload {upload_id}: {filename} (not a company KPI file)")

if __name__ == "__main__":
    assign_kpis_to_accounts() 