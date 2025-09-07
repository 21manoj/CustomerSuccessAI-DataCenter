#!/usr/bin/env python3
"""
Create Excel file with companies list for corporate upload.
"""

import pandas as pd
import json

def create_corporate_excel():
    """Create Excel file with companies list"""
    
    # Load corporate metadata
    with open("corporate_metadata.json", "r") as f:
        metadata = json.load(f)
    
    # Create Excel file with companies list
    with pd.ExcelWriter("corporate_companies.xlsx", engine="openpyxl") as writer:
        # Create companies list sheet
        companies_data = []
        for company in metadata["companies"]:
            companies_data.append([
                company["company_id"],
                company["company_name"],
                company["revenue"],
                company["industry"],
                company["region"],
                company["employee_count"],
                company["contract_value"],
                company["status"]
            ])
        
        # Create companies dataframe
        companies_df = pd.DataFrame(companies_data, columns=[
            "Company ID",
            "Company Name", 
            "Revenue ($)",
            "Industry",
            "Region",
            "Employee Count",
            "Contract Value ($)",
            "Status"
        ])
        
        # Add companies sheet
        companies_df.to_excel(writer, sheet_name="Companies List", index=False)
        
        # Add summary sheet
        summary_data = [
            ["Corporate Companies Summary"],
            ["Total Companies", metadata["total_companies"]],
            ["Total Revenue", f"${metadata['summary']['total_revenue']:,}"],
            ["Total Employees", f"{metadata['summary']['total_employees']:,}"],
            ["Total Contract Value", f"${metadata['summary']['total_contract_value']:,}"],
            ["Industries", len(metadata['summary']['industries'])],
            ["Regions", len(metadata['summary']['regions'])]
        ]
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="Summary", index=False, header=False)
        
        # Add instructions sheet
        instructions_data = [
            ["Instructions"],
            ["1. This file contains metadata for 25 companies"],
            ["2. Each company can be loaded individually with their 59 KPIs"],
            ["3. Select companies from the list to load their KPI data"],
            ["4. Corporate rollup will be calculated from loaded companies"],
            [""],
            ["Company Selection Process:"],
            ["- Upload this file first to register companies"],
            ["- Then upload individual company KPI files"],
            ["- Corporate view will show aggregated data"]
        ]
        instructions_df = pd.DataFrame(instructions_data)
        instructions_df.to_excel(writer, sheet_name="Instructions", index=False, header=False)
    
    print("✅ Created corporate Excel file:")
    print(f"   - File: corporate_companies.xlsx")
    print(f"   - Companies: {metadata['total_companies']}")
    print(f"   - Sheets: Companies List, Summary, Instructions")
    print(f"   - Ready for upload to register companies")

if __name__ == "__main__":
    create_corporate_excel() 