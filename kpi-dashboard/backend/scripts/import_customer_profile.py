#!/usr/bin/env python3
"""
Import Customer Profile Data from Excel file.

This script imports customer profile data from CS_GrowthPulse_Input_SEEDED.xlsx
for a specific tenant (Test Company).
"""

import os
import sys
from datetime import datetime

import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app_v3_minimal import app
from extensions import db
from models import Account, Customer

def _extract_reference_values(ref_df):
    """
    Extract allowed values from Reference Data sheet.
    Expected structure: columns with category names, rows with allowed values.
    """
    ref_vals = {}
    if ref_df is None or ref_df.empty:
        return ref_vals
    
    # Reference Data typically has category names as headers and values below
    for col in ref_df.columns:
        col_name = str(col).strip()
        if not col_name or col_name == 'nan':
            continue
        
        # Get non-null values from this column
        values = ref_df[col].dropna().astype(str).str.strip()
        values = {v for v in values if v and v.lower() != 'nan'}
        if values:
            # Normalize key names
            key = col_name
            if 'status' in col_name.lower() and 'option' in col_name.lower():
                key = 'Status Options'
            elif 'tier' in col_name.lower() and 'option' in col_name.lower():
                key = 'Account Tier Options'
            elif 'region' in col_name.lower() and 'option' in col_name.lower():
                key = 'Region Options'
            elif 'champion' in col_name.lower() and 'status' in col_name.lower():
                key = 'Champion Status'
            elif 'lifecycle' in col_name.lower() and 'stage' in col_name.lower():
                key = 'Lifecycle Stage'
            elif 'onboarding' in col_name.lower() and 'status' in col_name.lower():
                key = 'Onboarding Status'
            
            ref_vals[key] = values
    
    return ref_vals


def _load_profile_workbook(file_path: str):
    """Load all sheets from Excel workbook."""
    xl = pd.ExcelFile(file_path)
    sheets = {}
    for name in xl.sheet_names:
        df = xl.parse(name)
        sheets[name] = df
    return sheets


def _extract_rows(df, header_marker: str):
    """Find the row containing header_marker and return a DataFrame with proper columns."""
    if df is None or df.empty:
        return pd.DataFrame()
    
    header_idx = None
    for i, row in enumerate(df.values[:10]):
        if any(str(x).strip() == header_marker for x in row):
            header_idx = i
            break
    if header_idx is None:
        return pd.DataFrame()
    df = df.copy()
    df.columns = df.iloc[header_idx]
    df = df.iloc[header_idx + 1:]
    df = df.rename(columns=lambda c: str(c).strip())
    return df


def _safe_date(val):
    """Safely convert value to ISO date string."""
    if pd.isna(val) or val is None or str(val).strip() == '':
        return None
    if isinstance(val, (datetime, )):
        return val.isoformat()
    try:
        return pd.to_datetime(val).isoformat()
    except Exception:
        return str(val)


def _safe_number(val):
    """Safely convert value to number."""
    if val is None or (isinstance(val, str) and not val.strip()):
        return None
    try:
        return float(val)
    except Exception:
        return None


def import_customer_profile(customer_name: str, file_path: str):
    """Import customer profile data from Excel file."""
    with app.app_context():
        # Find customer
        customer = Customer.query.filter_by(customer_name=customer_name).first()
        if not customer:
            print(f"❌ Customer '{customer_name}' not found")
            return
        
        customer_id = customer.customer_id
        print(f"✅ Found customer: {customer_name} (ID: {customer_id})")
        
        # Load workbook
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return
        
        print(f"📖 Reading Excel file: {file_path}")
        sheets = _load_profile_workbook(file_path)
        print(f"   Sheets found: {list(sheets.keys())}")
        
        # Extract dataframes
        prof_df = _extract_rows(sheets.get('Customer Profile Input'), 'Account ID*')
        champ_df = _extract_rows(sheets.get('Champion & Stakeholder Input'), 'Account ID*')
        engage_df = _extract_rows(sheets.get('Engagement Tracking Input'), 'Account ID*')
        ref_df = sheets.get('Reference Data')
        
        print(f"   Profile rows: {len(prof_df)}")
        print(f"   Champion rows: {len(champ_df)}")
        print(f"   Engagement rows: {len(engage_df)}")
        
        # Extract reference values
        ref_vals = _extract_reference_values(ref_df)
        print(f"   Reference values extracted: {list(ref_vals.keys())}")
        
        # Validate (skip for now, but check structure)
        allowed_status = ref_vals.get('Status Options', set())
        allowed_tiers = ref_vals.get('Account Tier Options', set())
        allowed_regions = ref_vals.get('Region Options', set())
        allowed_champion_status = ref_vals.get('Champion Status', set())
        allowed_lifecycle = ref_vals.get('Lifecycle Stage', set())
        allowed_onboarding = ref_vals.get('Onboarding Status', set())
        
        # Index champions and engagement by Account ID or Name
        champ_by_id = {}
        if not champ_df.empty:
            for _, row in champ_df.iterrows():
                acc_id = str(row.get('Account ID*', '')).strip()
                acc_name = str(row.get('Account Name', '')).strip()
                key = acc_id or acc_name
                if not key:
                    continue
                champ_by_id.setdefault(key, []).append({
                    'primary_champion_name': str(row.get('Primary Champion Name*', '')).strip(),
                    'champion_title': str(row.get('Champion Title', '')).strip(),
                    'champion_email': str(row.get('Champion Email', '')).strip(),
                    'champion_status': str(row.get('Champion Status', '')).strip(),
                    'champion_tenure_months': row.get('Champion Tenure (months)'),
                    'champion_influence_level': str(row.get('Champion Influence Level', '')).strip(),
                    'economic_buyer_name': str(row.get('Economic Buyer Name', '')).strip(),
                    'economic_buyer_title': str(row.get('Economic Buyer Title', '')).strip(),
                    'executive_sponsor_name': str(row.get('Executive Sponsor Name', '')).strip(),
                    'executive_sponsor_title': str(row.get('Executive Sponsor Title', '')).strip(),
                    'technical_champion_name': str(row.get('Technical Champion Name', '')).strip(),
                    'active_champions': row.get('Number of Active Champions'),
                })
        
        engage_by_id = {}
        if not engage_df.empty:
            for _, row in engage_df.iterrows():
                acc_id = str(row.get('Account ID*', '')).strip()
                acc_name = str(row.get('Account Name', '')).strip()
                key = acc_id or acc_name
                if not key:
                    continue
                engage_by_id[key] = {
                    'last_touchpoint_date': _safe_date(row.get('Last Touchpoint Date')),
                    'next_scheduled_touchpoint': _safe_date(row.get('Next Scheduled Touchpoint')),
                    'last_business_review_date': _safe_date(row.get('Last Business Review Date')),
                    'next_business_review_date': _safe_date(row.get('Next Business Review Date')),
                    'active_users': _safe_number(row.get('Number of Active Users')),
                    'total_licenses': _safe_number(row.get('Total Licenses')),
                    'license_utilization_pct': _safe_number(row.get('License Utilization %')),
                    'days_since_last_login': _safe_number(row.get('Days Since Last Login')),
                    'lifecycle_stage': str(row.get('Lifecycle Stage', '')).strip(),
                    'onboarding_status': str(row.get('Onboarding Status', '')).strip(),
                    'open_support_tickets': _safe_number(row.get('Open Support Tickets')),
                }
        
        # Get all accounts for this customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        accounts_by_name = {a.account_name.strip(): a for a in accounts if a.account_name}
        print(f"   Found {len(accounts)} accounts in database")
        
        # Process profile rows
        updated = 0
        not_found = []
        
        for _, row in prof_df.iterrows():
            acc_id = str(row.get('Account ID*', '')).strip()
            acc_name = str(row.get('Account Name*', '')).strip()
            key = acc_id or acc_name
            if not key:
                continue
            
            acct = None
            # Prefer external id match
            if acc_id:
                acct = Account.query.filter_by(customer_id=customer_id, external_account_id=acc_id).first()
            if not acct:
                acct = accounts_by_name.get(acc_name)
            
            if not acct:
                not_found.append(key)
                continue
            
            # Build profile metadata
            profile = acct.profile_metadata or {}
            profile.update({
                'account_id_external': acc_id or profile.get('account_id_external'),
                'account_name': acc_name or acct.account_name,
                'industry': str(row.get('Industry*', '')).strip() or acct.industry,
                'region': str(row.get('Region*', '')).strip() or acct.region,
                'status': str(row.get('Status*', '')).strip() or acct.account_status,
                'account_tier': str(row.get('Account Tier*', '')).strip(),
                'assigned_csm': str(row.get('Assigned CSM*', '')).strip(),
                'csm_manager': str(row.get('CSM Manager', '')).strip(),
                'executive_sponsor': str(row.get('Executive Sponsor', '')).strip(),
                'strategic_account': str(row.get('Strategic Account', '')).strip(),
                'products_used': str(row.get('Products Used*', '')).strip(),
                'contract_start_date': _safe_date(row.get('Contract Start Date*')),
                'contract_end_date': _safe_date(row.get('Contract End Date*')),
                'renewal_date': _safe_date(row.get('Renewal Date')),
                'arr': _safe_number(row.get('ARR')),
                'mrr': _safe_number(row.get('MRR')),
            })
            
            # Merge champions and engagement
            champions = champ_by_id.get(key) or champ_by_id.get(acc_name) or []
            if champions:
                profile['champions'] = champions
            if key in engage_by_id or acc_name in engage_by_id:
                profile['engagement'] = engage_by_id.get(key) or engage_by_id.get(acc_name)
            
            # Update account
            acct.external_account_id = acc_id or acct.external_account_id
            acct.industry = profile.get('industry') or acct.industry
            acct.region = profile.get('region') or acct.region
            acct.account_status = profile.get('status') or acct.account_status
            acct.profile_metadata = profile
            updated += 1
        
        # Commit changes
        db.session.commit()
        
        print(f"\n✅ Successfully updated {updated} accounts")
        if not_found:
            print(f"⚠️  Accounts not found in database: {', '.join(not_found[:10])}")
            if len(not_found) > 10:
                print(f"   ... and {len(not_found) - 10} more")


if __name__ == '__main__':
    file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'CS_GrowthPulse_CustomerProfile_TestCompany.xlsx')
    import_customer_profile('Test Company', file_path)









