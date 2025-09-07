#!/usr/bin/env python3
"""
Script to upload all company KPI data by default
"""
import os
import sys
import pandas as pd
from pathlib import Path
import io

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import KPI, KPIUpload, Account

def parse_excel_file(file_path):
    """Parse Excel file and extract KPI data"""
    try:
        # Parse Excel
        xls = pd.ExcelFile(file_path)
        kpi_data = []
        
        # Skip first sheet, process middle sheets (KPI tabs), skip last sheet (rollup)
        kpi_sheets = xls.sheet_names[1:-1]
        print(f"Processing sheets: {kpi_sheets}")
        
        for sheet_name in kpi_sheets:
            try:
                print(f"\n--- Processing sheet: {sheet_name} ---")
                df = pd.read_excel(xls, sheet_name, header=None)
                print(f"Sheet shape: {df.shape}")
                
                # Find header row
                header_row_idx = df[df.iloc[:,0] == 'Health Score Component'].index
                if len(header_row_idx) == 0:
                    print(f"No header row found in {sheet_name}")
                    continue
                header_row_idx = header_row_idx[0]
                
                # Get the actual header row
                header_row = df.iloc[header_row_idx]
                df.columns = df.iloc[header_row_idx]
                df = df.iloc[header_row_idx+1:]
                df = df.dropna(subset=['Health Score Component'])
                
                for idx, row in df.iterrows():
                    # Try different possible column names for each field
                    weight_value = (
                        row.get('Weight') or 
                        row.get('weight') or 
                        row.get('WEIGHT') or
                        None
                    )
                    
                    impact_value = (
                        row.get('Impact level') or 
                        row.get('Impact Level') or 
                        row.get('Impact') or
                        row.get('impact level') or
                        row.get('IMPACT LEVEL') or
                        None
                    )
                    
                    # Convert NaN values to None for JSON compatibility
                    kpi_row = {
                        'category': sheet_name,
                        'row_index': str(idx),
                        'health_score_component': row.get('Health Score Component'),
                        'weight': weight_value,
                        'data': row.get('Data'),
                        'source_review': row.get('Source Review'),
                        'kpi_parameter': row.get('KPI/Parameter'),
                        'impact_level': impact_value,
                        'measurement_frequency': row.get('Measurement Frequency'),
                    }
                    
                    # Convert any NaN values to None
                    for key, value in kpi_row.items():
                        if pd.isna(value):
                            kpi_row[key] = None
                    
                    kpi_data.append(kpi_row)
                    
            except Exception as e:
                print(f"Error processing sheet {sheet_name}: {str(e)}")
                continue

        print(f"Total KPIs parsed: {len(kpi_data)}")
        return kpi_data
        
    except Exception as e:
        print(f"Error parsing Excel file: {str(e)}")
        return []

def upload_all_company_data():
    """Upload all company KPI files to the database"""
    customer_id = 6  # Customer ID 6
    
    # Get the company_kpi_files directory
    kpi_files_dir = Path(__file__).parent / "company_kpi_files"
    
    if not kpi_files_dir.exists():
        print(f"Error: {kpi_files_dir} does not exist")
        return
    
    # Get all Excel files in the directory
    excel_files = list(kpi_files_dir.glob("*.xlsx"))
    excel_files = [f for f in excel_files if not f.name.startswith("~$")]  # Exclude temp files
    
    print(f"Found {len(excel_files)} KPI files to upload")
    
    uploaded_count = 0
    
    for excel_file in excel_files:
        try:
            print(f"Processing: {excel_file.name}")
            
            # Parse the Excel file
            kpis_data = parse_excel_file(str(excel_file))
            
            if not kpis_data:
                print(f"  No KPI data found in {excel_file.name}")
                continue
            
            # Create upload record
            upload = KPIUpload(
                customer_id=customer_id,
                original_filename=excel_file.name,
                uploaded_at=pd.Timestamp.now(),
                version=1,  # Set version to 1 for all uploads
                user_id=1   # Set default user ID
            )
            db.session.add(upload)
            db.session.flush()  # Get the upload_id
            
            # Add KPIs to database
            for kpi_data in kpis_data:
                kpi = KPI(
                    upload_id=upload.upload_id,
                    category=kpi_data['category'],
                    row_index=kpi_data['row_index'],
                    health_score_component=kpi_data['health_score_component'],
                    weight=kpi_data['weight'],
                    data=kpi_data['data'],
                    source_review=kpi_data['source_review'],
                    kpi_parameter=kpi_data['kpi_parameter'],
                    impact_level=kpi_data['impact_level'],
                    measurement_frequency=kpi_data['measurement_frequency']
                )
                db.session.add(kpi)
            
            db.session.commit()
            uploaded_count += 1
            print(f"  Successfully uploaded {len(kpis_data)} KPIs from {excel_file.name}")
            
        except Exception as e:
            print(f"  Error processing {excel_file.name}: {str(e)}")
            db.session.rollback()
            continue
    
    print(f"\nUpload complete! {uploaded_count} files uploaded successfully.")
    
    # Now assign KPIs to accounts
    print("\nAssigning KPIs to accounts...")
    assign_kpis_to_accounts()

def assign_kpis_to_accounts():
    """Assign uploaded KPIs to their corresponding accounts"""
    customer_id = 6
    
    # Get all accounts for this customer
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    
    # Create a mapping of company names to account IDs
    company_to_account = {}
    for account in accounts:
        # Normalize company name for matching
        normalized_name = account.account_name.lower().replace(' ', '_').replace('&', 'and')
        company_to_account[normalized_name] = account.account_id
    
    print(f"Found {len(accounts)} accounts")
    
    # Get all KPIs that don't have account_id assigned
    unassigned_kpis = KPI.query.join(KPIUpload).filter(
        KPIUpload.customer_id == customer_id,
        KPI.account_id.is_(None)
    ).all()
    
    print(f"Found {len(unassigned_kpis)} unassigned KPIs")
    
    assigned_count = 0
    
    for kpi in unassigned_kpis:
        # Try to find the account based on the upload filename
        upload = KPIUpload.query.get(kpi.upload_id)
        if upload:
            filename = upload.original_filename.lower()
            
            # Try to match filename to account
            for company_name, account_id in company_to_account.items():
                if company_name in filename:
                    kpi.account_id = account_id
                    assigned_count += 1
                    break
    
    db.session.commit()
    print(f"Assigned {assigned_count} KPIs to accounts")

if __name__ == "__main__":
    with app.app_context():
        upload_all_company_data() 