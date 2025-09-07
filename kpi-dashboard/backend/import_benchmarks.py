#!/usr/bin/env python3
"""
Import Industry Benchmarks Data
Supports CSV, JSON, and Excel formats
"""

import os
import csv
import json
import pandas as pd
from datetime import datetime
from models import db, IndustryBenchmarks
from extensions import db

def import_benchmarks_csv(file_path):
    """Import benchmarks from CSV file"""
    print(f"📊 Importing benchmarks from CSV: {file_path}")
    
    imported_count = 0
    error_count = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                try:
                    # Validate required fields
                    if not row.get('kpi_name') or not row.get('industry') or not row.get('percentile_50'):
                        print(f"⚠️ Skipping row: Missing required fields")
                        error_count += 1
                        continue
                    
                    # Convert numeric fields
                    benchmark = IndustryBenchmarks(
                        kpi_name=row['kpi_name'].strip(),
                        industry=row['industry'].strip(),
                        company_size=row.get('company_size', '').strip() or None,
                        percentile_25=float(row['percentile_25']) if row.get('percentile_25') else None,
                        percentile_50=float(row['percentile_50']),
                        percentile_75=float(row['percentile_75']) if row.get('percentile_75') else None,
                        percentile_90=float(row['percentile_90']) if row.get('percentile_90') else None,
                        sample_size=int(row['sample_size']) if row.get('sample_size') else None,
                        data_source=row.get('data_source', '').strip() or None,
                        last_updated=datetime.strptime(row['last_updated'], '%Y-%m-%d') if row.get('last_updated') else None
                    )
                    
                    db.session.add(benchmark)
                    imported_count += 1
                    
                except Exception as e:
                    print(f"❌ Error importing row: {e}")
                    error_count += 1
                    continue
            
            db.session.commit()
            print(f"✅ Successfully imported {imported_count} benchmarks")
            if error_count > 0:
                print(f"⚠️ {error_count} rows had errors and were skipped")
                
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        db.session.rollback()

def import_benchmarks_json(file_path):
    """Import benchmarks from JSON file"""
    print(f"📊 Importing benchmarks from JSON: {file_path}")
    
    imported_count = 0
    error_count = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
            benchmarks = data.get('benchmarks', [])
            if not benchmarks:
                print("❌ No benchmarks found in JSON file")
                return
            
            for benchmark_data in benchmarks:
                try:
                    # Validate required fields
                    if not benchmark_data.get('kpi_name') or not benchmark_data.get('industry') or not benchmark_data.get('percentile_50'):
                        print(f"⚠️ Skipping benchmark: Missing required fields")
                        error_count += 1
                        continue
                    
                    benchmark = IndustryBenchmarks(
                        kpi_name=benchmark_data['kpi_name'].strip(),
                        industry=benchmark_data['industry'].strip(),
                        company_size=benchmark_data.get('company_size', '').strip() or None,
                        percentile_25=benchmark_data.get('percentile_25'),
                        percentile_50=benchmark_data['percentile_50'],
                        percentile_75=benchmark_data.get('percentile_75'),
                        percentile_90=benchmark_data.get('percentile_90'),
                        sample_size=benchmark_data.get('sample_size'),
                        data_source=benchmark_data.get('data_source', '').strip() or None,
                        last_updated=datetime.strptime(benchmark_data['last_updated'], '%Y-%m-%d') if benchmark_data.get('last_updated') else None
                    )
                    
                    db.session.add(benchmark)
                    imported_count += 1
                    
                except Exception as e:
                    print(f"❌ Error importing benchmark: {e}")
                    error_count += 1
                    continue
            
            db.session.commit()
            print(f"✅ Successfully imported {imported_count} benchmarks")
            if error_count > 0:
                print(f"⚠️ {error_count} benchmarks had errors and were skipped")
                
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        db.session.rollback()

def import_benchmarks_excel(file_path):
    """Import benchmarks from Excel file"""
    print(f"📊 Importing benchmarks from Excel: {file_path}")
    
    imported_count = 0
    error_count = 0
    
    try:
        df = pd.read_excel(file_path)
        
        for index, row in df.iterrows():
            try:
                # Validate required fields
                if pd.isna(row.get('kpi_name')) or pd.isna(row.get('industry')) or pd.isna(row.get('percentile_50')):
                    print(f"⚠️ Skipping row {index + 1}: Missing required fields")
                    error_count += 1
                    continue
                
                benchmark = IndustryBenchmarks(
                    kpi_name=str(row['kpi_name']).strip(),
                    industry=str(row['industry']).strip(),
                    company_size=str(row.get('company_size', '')).strip() if not pd.isna(row.get('company_size')) else None,
                    percentile_25=float(row['percentile_25']) if not pd.isna(row.get('percentile_25')) else None,
                    percentile_50=float(row['percentile_50']),
                    percentile_75=float(row['percentile_75']) if not pd.isna(row.get('percentile_75')) else None,
                    percentile_90=float(row['percentile_90']) if not pd.isna(row.get('percentile_90')) else None,
                    sample_size=int(row['sample_size']) if not pd.isna(row.get('sample_size')) else None,
                    data_source=str(row.get('data_source', '')).strip() if not pd.isna(row.get('data_source')) else None,
                    last_updated=row['last_updated'] if not pd.isna(row.get('last_updated')) else None
                )
                
                db.session.add(benchmark)
                imported_count += 1
                
            except Exception as e:
                print(f"❌ Error importing row {index + 1}: {e}")
                error_count += 1
                continue
        
        db.session.commit()
        print(f"✅ Successfully imported {imported_count} benchmarks")
        if error_count > 0:
            print(f"⚠️ {error_count} rows had errors and were skipped")
            
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        db.session.rollback()

def main():
    """Main import function"""
    print("🚀 Industry Benchmarks Import Tool")
    print("=" * 50)
    
    # Check if sample file exists
    sample_file = "sample_industry_benchmarks.csv"
    if os.path.exists(sample_file):
        print(f"📁 Found sample file: {sample_file}")
        choice = input("Import sample data? (y/n): ").lower().strip()
        
        if choice == 'y':
            import_benchmarks_csv(sample_file)
        else:
            print("Skipping sample data import")
    else:
        print(f"❌ Sample file not found: {sample_file}")
    
    # Interactive file selection
    while True:
        print("\n📂 Available import options:")
        print("1. CSV file")
        print("2. JSON file") 
        print("3. Excel file")
        print("4. Exit")
        
        choice = input("Select option (1-4): ").strip()
        
        if choice == '4':
            break
        elif choice in ['1', '2', '3']:
            file_path = input("Enter file path: ").strip()
            
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                continue
            
            if choice == '1':
                import_benchmarks_csv(file_path)
            elif choice == '2':
                import_benchmarks_json(file_path)
            elif choice == '3':
                import_benchmarks_excel(file_path)
        else:
            print("❌ Invalid option. Please select 1-4.")

if __name__ == "__main__":
    main()
