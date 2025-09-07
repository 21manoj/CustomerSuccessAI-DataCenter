#!/usr/bin/env python3
"""
Corporate API for handling corporate metadata uploads.
"""

print("DEBUG: corporate_api.py module loaded/reloaded")

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
from extensions import db
from models import KPIUpload, KPI, CustomerConfig, Account
import io
from datetime import datetime
from health_score_engine import HealthScoreEngine
from health_score_storage import HealthScoreStorageService

corporate_api = Blueprint('corporate_api', __name__)

@corporate_api.route('/api/corporate/upload', methods=['POST'])
def upload_corporate_metadata():
    """Upload corporate metadata with companies list."""
    file = request.files.get('file')
    customer_id = request.headers.get('X-Customer-ID')
    user_id = request.headers.get('X-User-ID')
    
    if not file:
        return jsonify({'error': 'Missing file'}), 400
    if not customer_id:
        return jsonify({'error': 'Missing X-Customer-ID header'}), 400
    if not user_id:
        return jsonify({'error': 'Missing X-User-ID header'}), 400
    
    customer_id = int(customer_id)
    user_id = int(user_id)
    
    filename = secure_filename(file.filename)
    raw_excel = file.read()
    file.seek(0)

    try:
        # Parse Excel
        xls = pd.ExcelFile(io.BytesIO(raw_excel))
        
        # Look for "Companies List" sheet
        if "Companies List" not in xls.sheet_names:
            return jsonify({'error': 'No "Companies List" sheet found in Excel file'}), 400
        
        # Read companies list
        companies_df = pd.read_excel(xls, sheet_name="Companies List")
        
        # Validate required columns
        required_columns = ["Company ID", "Company Name", "Revenue ($)", "Industry", "Region"]
        missing_columns = [col for col in required_columns if col not in companies_df.columns]
        if missing_columns:
            return jsonify({'error': f'Missing required columns: {missing_columns}'}), 400
        
        # Create accounts from companies data
        accounts_created = []
        for _, row in companies_df.iterrows():
            account = Account(
                customer_id=customer_id,
                account_name=row["Company Name"],
                revenue=row["Revenue ($)"],
                industry=row["Industry"],
                region=row["Region"]
            )
            db.session.add(account)
            accounts_created.append({
                "company_name": row["Company Name"],
                "revenue": row["Revenue ($)"],
                "industry": row["Industry"],
                "region": row["Region"]
            })
        
        # Create upload record
        upload = KPIUpload(
            customer_id=customer_id,
            user_id=user_id,
            original_filename=filename,
            version=1,
            upload_type='corporate_metadata'
        )
        db.session.add(upload)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Corporate metadata uploaded successfully',
            'upload_id': upload.upload_id,
            'accounts_created': len(accounts_created),
            'companies': accounts_created
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to process corporate metadata: {str(e)}'}), 500

@corporate_api.route('/api/corporate/companies', methods=['GET'])
def get_corporate_companies():
    """Get list of companies for corporate view."""
    customer_id = request.headers.get('X-Customer-ID')
    
    if not customer_id:
        return jsonify({'error': 'Missing X-Customer-ID header'}), 400
    
    customer_id = int(customer_id)
    
    # Get all accounts for this customer
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    
    companies = []
    for account in accounts:
        companies.append({
            'account_id': account.account_id,
            'company_name': account.account_name,
            'revenue': account.revenue,
            'industry': account.industry,
            'region': account.region,
            'has_kpis': KPI.query.filter_by(account_id=account.account_id).count() > 0
        })
    
    return jsonify({
        'companies': companies,
        'total_companies': len(companies),
        'companies_with_kpis': len([c for c in companies if c['has_kpis']])
    })

def calculate_enhanced_health_scores(kpis_with_accounts, customer_id=None):
    """Calculate enhanced health scores using the new engine"""
    print(f"DEBUG: calculate_enhanced_health_scores called with customer_id={customer_id}")
    # Group KPIs by category (using the actual category names from database)
    components = {}
    
    for kpi, _ in kpis_with_accounts:
        category = kpi.category  # Use the actual category name from database
        if category not in components:
            components[category] = []
        
        # Convert KPI object to dict for processing
        kpi_dict = {
            'kpi_parameter': kpi.kpi_parameter,
            'data': kpi.data,
            'impact_level': kpi.impact_level,
            'health_score_component': kpi.health_score_component,
            'category': kpi.category,
            'weight': kpi.weight,
            'source_review': kpi.source_review,
            'measurement_frequency': kpi.measurement_frequency
        }
        components[category].append(kpi_dict)
    
    # Calculate health scores for each category
    category_scores = []
    for category, kpis in components.items():
        if kpis:
            print(f"DEBUG: Processing category '{category}' with {len(kpis)} KPIs, customer_id={customer_id}")
            category_score = HealthScoreEngine.calculate_category_health_score(kpis, category, customer_id)
            category_scores.append(category_score)
    
    # Calculate overall health score
    overall_score = HealthScoreEngine.calculate_overall_health_score(category_scores)
    
    return {
        'category_scores': category_scores,
        'overall_score': overall_score
    }

@corporate_api.route('/api/corporate/test', methods=['GET'])
def test_corporate():
    """Test endpoint to verify corporate_api is working"""
    return jsonify({'message': 'Corporate API is working', 'timestamp': '2025-08-05', 'version': 'UPDATED'})

@corporate_api.route('/api/corporate/rollup', methods=['GET'])
def get_corporate_rollup():
    """Get corporate rollup data from loaded companies with revenue-weighted averaging."""
    print("DEBUG: get_corporate_rollup function called")
    customer_id = request.headers.get('X-Customer-ID')
    
    if not customer_id:
        return jsonify({'error': 'Missing X-Customer-ID header'}), 400
    
    customer_id = int(customer_id)
    
    print(f"DEBUG: Processing corporate rollup for customer {customer_id}")
    
    # Get all accounts for this customer
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    print(f"DEBUG: Found {len(accounts)} accounts for customer {customer_id}")
    
    # Get KPIs for each account
    all_kpis_with_accounts = []
    total_revenue = 0
    
    for account in accounts:
        account_kpis = KPI.query.filter_by(account_id=account.account_id).all()
        print(f"DEBUG: Account {account.account_name} (ID: {account.account_id}) has {len(account_kpis)} KPIs")
        
        if account_kpis:
            for kpi in account_kpis:
                all_kpis_with_accounts.append((kpi, account))
            total_revenue += float(account.revenue) if account.revenue else 0
    
    print(f"DEBUG: Total KPI-Account pairs: {len(all_kpis_with_accounts)}")
    print(f"DEBUG: Total revenue: {total_revenue}")
    
    if not all_kpis_with_accounts:
        return jsonify({
            'companies_loaded': 0,
            'rollup_kpis': [],
            'total_kpis': 0,
            'total_revenue': 0,
            'calculation_method': 'Revenue-weighted averaging'
        })
    
    # Group by KPI parameter and calculate revenue-weighted rollup
    kpi_groups = {}
    for kpi, account in all_kpis_with_accounts:
        key = kpi.kpi_parameter
        if key not in kpi_groups:
            kpi_groups[key] = []
        kpi_groups[key].append((kpi, account))
    
    rollup_data = []
    
    for kpi_parameter, kpi_accounts in kpi_groups.items():
        if not kpi_accounts:
            continue
            
        # Get the first KPI for metadata
        first_kpi, first_account = kpi_accounts[0]
        
        # Calculate revenue-weighted average for data values
        weighted_sum = 0
        total_weight = 0
        
        for kpi, account in kpi_accounts:
            try:
                # Parse the data value, handling different formats
                data_str = str(kpi.data).replace('%', '').replace('$', '').replace('K', '000').replace('M', '000000')
                data_value = float(data_str) if data_str.strip() else 0
                
                # Weight by revenue
                revenue_weight = float(account.revenue) if account.revenue else 0
                weighted_sum += data_value * revenue_weight
                total_weight += revenue_weight
            except (ValueError, TypeError):
                # Skip invalid data values
                continue
        
        # Calculate weighted average
        if total_weight > 0:
            weighted_avg = weighted_sum / total_weight
        else:
            weighted_avg = 0
        
        # Format the result based on the original data format
        original_data = first_kpi.data
        if '%' in original_data:
            formatted_data = f"{weighted_avg:.1f}%"
        elif '$' in original_data:
            formatted_data = f"${weighted_avg:,.0f}"
        elif 'K' in original_data or 'M' in original_data:
            if weighted_avg >= 1000000:
                formatted_data = f"{weighted_avg/1000000:.1f}M"
            else:
                formatted_data = f"{weighted_avg/1000:.1f}K"
        else:
            formatted_data = f"{weighted_avg:.1f}"
        
        rollup_kpi = {
            'category': first_kpi.category,
            'health_score_component': first_kpi.health_score_component,
            'kpi_parameter': kpi_parameter,
            'impact_level': first_kpi.impact_level,
            'measurement_frequency': first_kpi.measurement_frequency,
            'weight': first_kpi.weight,
            'data': formatted_data,
            'source_review': 'Corporate Rollup (Revenue-Weighted)',
            'companies_count': len(set(kpi.account_id for kpi, _ in kpi_accounts)),
            'weighted_average': weighted_avg
        }
        rollup_data.append(rollup_kpi)
    
    # Count unique companies that have KPIs
    companies_with_kpis = set(account.account_id for _, account in all_kpis_with_accounts)
    
    # Calculate enhanced corporate health scores
    print("DEBUG: Starting enhanced health score calculation...")
    print(f"DEBUG: Number of KPI-account pairs: {len(all_kpis_with_accounts)}")
    try:
        print("DEBUG: Calling calculate_enhanced_health_scores...")
        print(f"DEBUG: customer_id being passed: {customer_id}")
        health_analysis = calculate_enhanced_health_scores(all_kpis_with_accounts, customer_id)
        print(f"DEBUG: Enhanced health analysis completed")
        print(f"DEBUG: Health analysis keys: {list(health_analysis.keys())}")
        
        # Extract category scores
        category_scores = health_analysis['category_scores']
        overall_score = health_analysis['overall_score']
        
        # Create health scores dict for backward compatibility
        health_scores = {
            'product_usage': next((cat['average_score'] for cat in category_scores if cat['category'] == 'Product Usage KPI'), 0),
            'support': next((cat['average_score'] for cat in category_scores if cat['category'] == 'Support KPI'), 0),
            'customer_sentiment': next((cat['average_score'] for cat in category_scores if cat['category'] == 'Customer Sentiment KPI'), 0),
            'business_outcomes': next((cat['average_score'] for cat in category_scores if cat['category'] == 'Business Outcomes KPI'), 0),
            'relationship_strength': next((cat['average_score'] for cat in category_scores if cat['category'] == 'Relationship Strength KPI'), 0),
            'overall': overall_score['overall_score']
        }
        
        # Add enhanced health data (without the large KPI details)
        health_scores['enhanced_analysis'] = {
            'category_scores': [
                {
                    'category': cat['category'],
                    'average_score': cat['average_score'],
                    'health_status': cat['health_status'],
                    'color': cat['color'],
                    'kpi_count': cat['kpi_count'],
                    'valid_kpi_count': cat['valid_kpi_count'],
                    'category_weight': cat['category_weight']
                }
                for cat in category_scores
            ],
            'overall_score': {
                'overall_score': overall_score['overall_score'],
                'health_status': overall_score['health_status'],
                'color': overall_score['color']
            }
        }
        
    except Exception as e:
        print(f"DEBUG: Error calculating enhanced health scores: {str(e)}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        health_scores = {
            'product_usage': 0,
            'support': 0,
            'customer_sentiment': 0,
            'business_outcomes': 0,
            'relationship_strength': 0,
            'overall': 0
        }
    
    print(f"DEBUG: Generated {len(rollup_data)} rollup KPIs from {len(companies_with_kpis)} companies")
    print(f"DEBUG: Corporate health scores: {health_scores}")
    print(f"DEBUG: Health scores keys: {list(health_scores.keys())}")
    
    response_data = {
        'rollup_kpis': rollup_data,
        'total_kpis': len(rollup_data),
        'companies_loaded': len(companies_with_kpis),
        'total_revenue': total_revenue,
        'calculation_method': 'Revenue-weighted averaging',
        'health_scores': health_scores
    }
    
    print(f"DEBUG: Response data keys: {list(response_data.keys())}")
    
    # Store health scores and KPI time series data
    try:
        storage_service = HealthScoreStorageService()
        
        # Store health scores for all accounts
        print("DEBUG: Storing health scores...")
        health_stored_count = storage_service.store_health_scores_after_rollup(
            health_analysis, customer_id
        )
        print(f"DEBUG: Stored health scores for {health_stored_count} accounts")
        
        # Store monthly KPI data
        print("DEBUG: Storing monthly KPI data...")
        kpi_stored_count = storage_service.store_monthly_kpi_data(customer_id)
        print(f"DEBUG: Stored monthly KPI data for {kpi_stored_count} KPIs")
        
        # Add storage info to response
        response_data['storage_info'] = {
            'health_scores_stored': health_stored_count,
            'kpi_time_series_stored': kpi_stored_count,
            'storage_timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error storing health scores and KPI data: {e}")
        # Don't fail the API call if storage fails
        response_data['storage_info'] = {
            'error': f"Failed to store data: {str(e)}",
            'storage_timestamp': datetime.now().isoformat()
        }
    
    return jsonify(response_data) 