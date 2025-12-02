#!/usr/bin/env python3
"""Check what data is in the seeded Excel file."""

import os
import sys
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def check_seeded_file():
    """Examine the seeded Excel file structure."""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'CS_GrowthPulse_CustomerProfile_TestCompany.xlsx')
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"📖 Reading: {file_path}\n")
    
    xl = pd.ExcelFile(file_path)
    print(f"Sheets: {xl.sheet_names}\n")
    
    for sheet_name in xl.sheet_names:
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"Sheet: {sheet_name}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        df = xl.parse(sheet_name)
        print(f"Rows: {len(df)}, Columns: {len(df.columns)}\n")
        
        # Show first few rows
        print("First 10 rows:")
        print(df.head(10).to_string())
        print("\n")
        
        # Show column names
        print("Columns:")
        for i, col in enumerate(df.columns):
            print(f"  {i+1}. {col}")
        print("\n")
        
        # Check for KPI-related columns
        kpi_keywords = ['kpi', 'parameter', 'metric', 'value', 'data', 'health', 'score']
        kpi_cols = [col for col in df.columns if any(kw in str(col).lower() for kw in kpi_keywords)]
        if kpi_cols:
            print(f"⚠️  Potential KPI columns found: {kpi_cols}\n")


if __name__ == '__main__':
    check_seeded_file()


