#!/usr/bin/env python3
"""
Analyze the original Excel file structure to understand the exact 59 KPIs.
"""

import pandas as pd
import sys
import os

def analyze_excel_structure():
    """Analyze the original Excel file to understand the KPI structure"""
    
    # Path to the original Excel file
    excel_file = "../Maturity-Framework-KPI-loveable.xlsx"
    
    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        return
    
    print("📊 Analyzing Excel Structure")
    print("=" * 50)
    
    try:
        # Read all sheets
        xls = pd.ExcelFile(excel_file)
        print(f"📋 Sheets found: {xls.sheet_names}")
        
        total_kpis = 0
        kpi_details = []
        
        for sheet_name in xls.sheet_names:
            print(f"\n📄 Processing sheet: {sheet_name}")
            
            try:
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                print(f"   Shape: {df.shape}")
                
                # Find header row
                header_row_idx = df[df.iloc[:,0] == 'Health Score Component'].index
                if len(header_row_idx) > 0:
                    header_row_idx = header_row_idx[0]
                    print(f"   Header row found at index: {header_row_idx}")
                    
                    # Get header row
                    header_row = df.iloc[header_row_idx]
                    print(f"   Headers: {list(header_row)}")
                    
                    # Process data rows
                    df.columns = df.iloc[header_row_idx]
                    df = df.iloc[header_row_idx+1:]
                    df = df.dropna(subset=['Health Score Component'])
                    
                    print(f"   Data rows: {len(df)}")
                    
                    for idx, row in df.iterrows():
                        kpi_info = {
                            'sheet': sheet_name,
                            'row_index': idx,
                            'health_score_component': row.get('Health Score Component'),
                            'weight': row.get('Weight (%)'),
                            'data': row.get('Data'),
                            'source_review': row.get('Source Review'),
                            'kpi_parameter': row.get('KPI/Parameter'),
                            'impact_level': row.get('Impact Level'),
                            'measurement_frequency': row.get('Measurement Frequency')
                        }
                        
                        # Clean NaN values
                        for key, value in kpi_info.items():
                            if pd.isna(value):
                                kpi_info[key] = None
                        
                        kpi_details.append(kpi_info)
                        total_kpis += 1
                        
                        print(f"     KPI: {kpi_info['kpi_parameter']} ({kpi_info['impact_level']})")
                else:
                    print(f"   ⚠️ No header row found in {sheet_name}")
                    
            except Exception as e:
                print(f"   ❌ Error processing {sheet_name}: {str(e)}")
        
        print(f"\n📈 Summary:")
        print(f"   Total KPIs found: {total_kpis}")
        print(f"   Sheets processed: {len(xls.sheet_names)}")
        
        # Group by sheet
        sheets_summary = {}
        for kpi in kpi_details:
            sheet = kpi['sheet']
            if sheet not in sheets_summary:
                sheets_summary[sheet] = []
            sheets_summary[sheet].append(kpi)
        
        print(f"\n📋 KPIs by Sheet:")
        for sheet, kpis in sheets_summary.items():
            print(f"   {sheet}: {len(kpis)} KPIs")
            for kpi in kpis:
                print(f"     - {kpi['kpi_parameter']}")
        
        return kpi_details
        
    except Exception as e:
        print(f"❌ Error analyzing Excel file: {str(e)}")
        return None

if __name__ == "__main__":
    analyze_excel_structure() 