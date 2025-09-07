#!/usr/bin/env python3
"""
Import Best Practices Content Library
Supports JSON and CSV formats
"""

import os
import csv
import json
import pandas as pd
from datetime import datetime
from models import db, KPIBestPractices
from extensions import db

def import_best_practices_json(file_path):
    """Import best practices from JSON file"""
    print(f"📚 Importing best practices from JSON: {file_path}")
    
    imported_count = 0
    error_count = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
            best_practices = data.get('best_practices', [])
            if not best_practices:
                print("❌ No best practices found in JSON file")
                return
            
            for practice_data in best_practices:
                try:
                    # Validate required fields
                    required_fields = ['kpi_name', 'category', 'title', 'description', 'implementation_steps']
                    missing_fields = [field for field in required_fields if not practice_data.get(field)]
                    
                    if missing_fields:
                        print(f"⚠️ Skipping best practice: Missing required fields: {missing_fields}")
                        error_count += 1
                        continue
                    
                    # Convert implementation_steps to JSON if it's a list
                    implementation_steps = practice_data.get('implementation_steps', [])
                    if isinstance(implementation_steps, list):
                        implementation_steps = json.dumps(implementation_steps)
                    
                    # Convert industry_applicability to JSON if it's a list
                    industry_applicability = practice_data.get('industry_applicability', [])
                    if isinstance(industry_applicability, list):
                        industry_applicability = json.dumps(industry_applicability)
                    
                    # Convert company_size_applicability to JSON if it's a list
                    company_size_applicability = practice_data.get('company_size_applicability', [])
                    if isinstance(company_size_applicability, list):
                        company_size_applicability = json.dumps(company_size_applicability)
                    
                    best_practice = KPIBestPractices(
                        kpi_name=practice_data['kpi_name'].strip(),
                        category=practice_data['category'].strip(),
                        title=practice_data['title'].strip(),
                        description=practice_data['description'].strip(),
                        implementation_steps=implementation_steps,
                        expected_impact=practice_data.get('expected_impact', '').strip() or None,
                        typical_improvement_percentage=float(practice_data['typical_improvement_percentage']) if practice_data.get('typical_improvement_percentage') else None,
                        implementation_timeframe=practice_data.get('implementation_timeframe', '').strip() or None,
                        difficulty_level=practice_data.get('difficulty_level', '').strip() or None,
                        cost_estimate=practice_data.get('cost_estimate', '').strip() or None,
                        industry_applicability=industry_applicability,
                        company_size_applicability=company_size_applicability
                    )
                    
                    db.session.add(best_practice)
                    imported_count += 1
                    
                except Exception as e:
                    print(f"❌ Error importing best practice: {e}")
                    error_count += 1
                    continue
            
            db.session.commit()
            print(f"✅ Successfully imported {imported_count} best practices")
            if error_count > 0:
                print(f"⚠️ {error_count} best practices had errors and were skipped")
                
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        db.session.rollback()

def import_best_practices_csv(file_path):
    """Import best practices from CSV file"""
    print(f"📚 Importing best practices from CSV: {file_path}")
    
    imported_count = 0
    error_count = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                try:
                    # Validate required fields
                    required_fields = ['kpi_name', 'category', 'title', 'description', 'implementation_steps']
                    missing_fields = [field for field in required_fields if not row.get(field)]
                    
                    if missing_fields:
                        print(f"⚠️ Skipping row: Missing required fields: {missing_fields}")
                        error_count += 1
                        continue
                    
                    # Parse JSON fields
                    implementation_steps = row.get('implementation_steps', '[]')
                    if implementation_steps.startswith('[') and implementation_steps.endswith(']'):
                        # Already in JSON format
                        pass
                    else:
                        # Convert from string representation
                        implementation_steps = json.dumps(implementation_steps.split('|'))
                    
                    industry_applicability = row.get('industry_applicability', '[]')
                    if industry_applicability.startswith('[') and industry_applicability.endswith(']'):
                        # Already in JSON format
                        pass
                    else:
                        # Convert from string representation
                        industry_applicability = json.dumps(industry_applicability.split('|'))
                    
                    company_size_applicability = row.get('company_size_applicability', '[]')
                    if company_size_applicability.startswith('[') and company_size_applicability.endswith(']'):
                        # Already in JSON format
                        pass
                    else:
                        # Convert from string representation
                        company_size_applicability = json.dumps(company_size_applicability.split('|'))
                    
                    best_practice = KPIBestPractices(
                        kpi_name=row['kpi_name'].strip(),
                        category=row['category'].strip(),
                        title=row['title'].strip(),
                        description=row['description'].strip(),
                        implementation_steps=implementation_steps,
                        expected_impact=row.get('expected_impact', '').strip() or None,
                        typical_improvement_percentage=float(row['typical_improvement_percentage']) if row.get('typical_improvement_percentage') else None,
                        implementation_timeframe=row.get('implementation_timeframe', '').strip() or None,
                        difficulty_level=row.get('difficulty_level', '').strip() or None,
                        cost_estimate=row.get('cost_estimate', '').strip() or None,
                        industry_applicability=industry_applicability,
                        company_size_applicability=company_size_applicability
                    )
                    
                    db.session.add(best_practice)
                    imported_count += 1
                    
                except Exception as e:
                    print(f"❌ Error importing row: {e}")
                    error_count += 1
                    continue
            
            db.session.commit()
            print(f"✅ Successfully imported {imported_count} best practices")
            if error_count > 0:
                print(f"⚠️ {error_count} rows had errors and were skipped")
                
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        db.session.rollback()

def main():
    """Main import function"""
    print("🚀 Best Practices Content Library Import Tool")
    print("=" * 50)
    
    # Check if sample file exists
    sample_file = "sample_best_practices.json"
    if os.path.exists(sample_file):
        print(f"📁 Found sample file: {sample_file}")
        choice = input("Import sample data? (y/n): ").lower().strip()
        
        if choice == 'y':
            import_best_practices_json(sample_file)
        else:
            print("Skipping sample data import")
    else:
        print(f"❌ Sample file not found: {sample_file}")
    
    # Interactive file selection
    while True:
        print("\n📂 Available import options:")
        print("1. JSON file")
        print("2. CSV file")
        print("3. Exit")
        
        choice = input("Select option (1-3): ").strip()
        
        if choice == '3':
            break
        elif choice in ['1', '2']:
            file_path = input("Enter file path: ").strip()
            
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                continue
            
            if choice == '1':
                import_best_practices_json(file_path)
            elif choice == '2':
                import_best_practices_csv(file_path)
        else:
            print("❌ Invalid option. Please select 1-3.")

if __name__ == "__main__":
    main()
