#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import KPI, Account, KPIUpload

def test_corporate_rollup():
    """Test the corporate rollup logic directly"""
    with app.app_context():
        customer_id = 6
        
        print("=== Testing Corporate Rollup Logic ===\n")
        
        # 1. Get all accounts for customer
        print("1. Getting accounts for customer 6...")
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        print(f"   Found {len(accounts)} accounts")
        
        # 2. Get KPIs for each account
        print("\n2. Getting KPIs for each account...")
        all_kpis_with_accounts = []
        total_revenue = 0
        
        for account in accounts:
            account_kpis = KPI.query.filter_by(account_id=account.account_id).all()
            print(f"   - {account.account_name} (ID: {account.account_id}): {len(account_kpis)} KPIs")
            
            if account_kpis:
                for kpi in account_kpis:
                    all_kpis_with_accounts.append((kpi, account))
                total_revenue += float(account.revenue) if account.revenue else 0
        
        print(f"\n   Total KPI-Account pairs: {len(all_kpis_with_accounts)}")
        print(f"   Total revenue: {total_revenue}")
        
        # 3. Group by KPI parameter
        print("\n3. Grouping by KPI parameter...")
        kpi_groups = {}
        for kpi, account in all_kpis_with_accounts:
            key = kpi.kpi_parameter
            if key not in kpi_groups:
                kpi_groups[key] = []
            kpi_groups[key].append((kpi, account))
        
        print(f"   Found {len(kpi_groups)} unique KPI parameters")
        
        # 4. Calculate rollup for first few KPIs
        print("\n4. Calculating rollup for first 3 KPIs...")
        count = 0
        for kpi_parameter, kpi_accounts in kpi_groups.items():
            if count >= 3:
                break
                
            first_kpi, first_account = kpi_accounts[0]
            print(f"   - {kpi_parameter}: {len(kpi_accounts)} companies")
            
            # Calculate weighted average
            weighted_sum = 0
            total_weight = 0
            
            for kpi, account in kpi_accounts:
                try:
                    data_str = str(kpi.data).replace('%', '').replace('$', '').replace('K', '000').replace('M', '000000')
                    data_value = float(data_str) if data_str.strip() else 0
                    revenue_weight = float(account.revenue) if account.revenue else 0
                    weighted_sum += data_value * revenue_weight
                    total_weight += revenue_weight
                except (ValueError, TypeError):
                    continue
            
            if total_weight > 0:
                weighted_avg = weighted_sum / total_weight
                print(f"     Weighted average: {weighted_avg:.2f}")
            else:
                print(f"     No valid data for calculation")
            
            count += 1
        
        # 5. Count unique companies
        companies_with_kpis = set(account.account_id for _, account in all_kpis_with_accounts)
        print(f"\n5. Summary:")
        print(f"   Companies with KPIs: {len(companies_with_kpis)}")
        print(f"   Total KPIs: {len(all_kpis_with_accounts)}")
        print(f"   Unique KPI parameters: {len(kpi_groups)}")

if __name__ == "__main__":
    test_corporate_rollup() 