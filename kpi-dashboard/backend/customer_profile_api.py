#!/usr/bin/env python3
"""
Customer Profile API

Uploads and applies CS GrowthPulse-style customer profile templates on a per-tenant basis.
Populates:
- Account.external_account_id (from \"Account ID*\")
- Account.profile_metadata (JSON with profile, champion, engagement data)
"""

import os
from datetime import datetime

import pandas as pd
from flask import Blueprint, request, jsonify, current_app

from auth_middleware import get_current_customer_id
from extensions import db
from models import Account
from activity_logging import activity_logger

customer_profile_api = Blueprint('customer_profile_api', __name__)


def _load_profile_workbook(file_path: str):
    xl = pd.ExcelFile(file_path)
    sheets = {}
    for name in xl.sheet_names:
        df = xl.parse(name)
        sheets[name] = df
    return sheets


def _extract_rows(df, header_marker: str):
    """
    Find the row containing header_marker and return a DataFrame with proper columns.
    """
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


@customer_profile_api.route('/api/customer-profile/upload', methods=['POST'])
def upload_customer_profile():
    """
    Upload and apply CS_GrowthPulse_Input_Template.xlsx-style file for the current tenant.

    Behavior:
    - Reads three sheets:
        * Customer Profile Input
        * Champion & Stakeholder Input
        * Engagement Tracking Input
    - Matches rows to Accounts by external_account_id (Account ID*); if empty, falls back to Account Name.
    - Updates Account.external_account_id and Account.profile_metadata JSON.
    """
    customer_id = get_current_customer_id()

    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'Empty filename'}), 400

    try:
        # Save to temp path for pandas
        upload_dir = current_app.config.get('UPLOAD_FOLDER', '/tmp')
        os.makedirs(upload_dir, exist_ok=True)
        path = os.path.join(upload_dir, file.filename)
        file.save(path)

        sheets = _load_profile_workbook(path)

        prof_df = _extract_rows(sheets.get('Customer Profile Input'), 'Account ID*')
        champ_df = _extract_rows(sheets.get('Champion & Stakeholder Input'), 'Account ID*')
        engage_df = _extract_rows(sheets.get('Engagement Tracking Input'), 'Account ID*')
        ref_df = sheets.get('Reference Data')
        ref_vals = _extract_reference_values(ref_df)

        # Allowed values from Reference Data
        allowed_status = ref_vals.get('Status Options', set())
        allowed_tiers = ref_vals.get('Account Tier Options', set())
        allowed_regions = ref_vals.get('Region Options', set())
        allowed_champion_status = ref_vals.get('Champion Status', set())
        allowed_lifecycle = ref_vals.get('Lifecycle Stage', set())
        allowed_onboarding = ref_vals.get('Onboarding Status', set())

        validation_errors = []

        # Validate Customer Profile Input sheet
        if not prof_df.empty:
            for _, row in prof_df.iterrows():
                acc_id = str(row.get('Account ID*', '')).strip()
                acc_name = str(row.get('Account Name*', '')).strip()
                row_key = acc_id or acc_name or '(missing)'
                status = str(row.get('Status*', '')).strip()
                tier = str(row.get('Account Tier*', '')).strip()
                region = str(row.get('Region*', '')).strip()
                if status and allowed_status and status not in allowed_status:
                    validation_errors.append({
                        'sheet': 'Customer Profile Input',
                        'account': row_key,
                        'field': 'Status*',
                        'value': status,
                        'allowed': sorted(allowed_status)
                    })
                if tier and allowed_tiers and tier not in allowed_tiers:
                    validation_errors.append({
                        'sheet': 'Customer Profile Input',
                        'account': row_key,
                        'field': 'Account Tier*',
                        'value': tier,
                        'allowed': sorted(allowed_tiers)
                    })
                if region and allowed_regions and region not in allowed_regions:
                    validation_errors.append({
                        'sheet': 'Customer Profile Input',
                        'account': row_key,
                        'field': 'Region*',
                        'value': region,
                        'allowed': sorted(allowed_regions)
                    })

        # Validate Champion & Stakeholder Input sheet
        if not champ_df.empty:
            for _, row in champ_df.iterrows():
                acc_id = str(row.get('Account ID*', '')).strip()
                acc_name = str(row.get('Account Name', '')).strip()
                row_key = acc_id or acc_name or '(missing)'
                c_status = str(row.get('Champion Status', '')).strip()
                if c_status and allowed_champion_status and c_status not in allowed_champion_status:
                    validation_errors.append({
                        'sheet': 'Champion & Stakeholder Input',
                        'account': row_key,
                        'field': 'Champion Status',
                        'value': c_status,
                        'allowed': sorted(allowed_champion_status)
                    })

        # Validate Engagement Tracking Input sheet
        if not engage_df.empty:
            for _, row in engage_df.iterrows():
                acc_id = str(row.get('Account ID*', '')).strip()
                acc_name = str(row.get('Account Name', '')).strip()
                row_key = acc_id or acc_name or '(missing)'
                lifecycle = str(row.get('Lifecycle Stage', '')).strip()
                onboarding = str(row.get('Onboarding Status', '')).strip()
                if lifecycle and allowed_lifecycle and lifecycle not in allowed_lifecycle:
                    validation_errors.append({
                        'sheet': 'Engagement Tracking Input',
                        'account': row_key,
                        'field': 'Lifecycle Stage',
                        'value': lifecycle,
                        'allowed': sorted(allowed_lifecycle)
                    })
                if onboarding and allowed_onboarding and onboarding not in allowed_onboarding:
                    validation_errors.append({
                        'sheet': 'Engagement Tracking Input',
                        'account': row_key,
                        'field': 'Onboarding Status',
                        'value': onboarding,
                        'allowed': sorted(allowed_onboarding)
                    })

        if validation_errors:
            return jsonify({
                'status': 'error',
                'message': 'Customer profile validation failed',
                'errors': validation_errors
            }), 400

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

        updated = 0
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        accounts_by_name = {a.account_name.strip(): a for a in accounts if a.account_name}

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
                current_app.logger.warning(f"CustomerProfile: No account match for key={key}")
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

            # Merge champions and engagement by key
            champions = champ_by_id.get(key) or champ_by_id.get(acc_name) or []
            if champions:
                profile['champions'] = champions
            if key in engage_by_id or acc_name in engage_by_id:
                profile['engagement'] = engage_by_id.get(key) or engage_by_id.get(acc_name)

            acct.external_account_id = acc_id or acct.external_account_id
            acct.industry = profile.get('industry') or acct.industry
            acct.region = profile.get('region') or acct.region
            acct.account_status = profile.get('status') or acct.account_status
            acct.profile_metadata = profile
            updated += 1

        db.session.commit()

        # Publish account change events for automatic snapshot creation
        try:
            from event_system import event_manager, EventType
            for account_id in [acct.account_id for acct in accounts if acct.account_id]:
                event_manager.publish_account_change(
                    customer_id,
                    account_id,
                    {'action': 'profile_metadata_updated', 'source': 'customer_profile_upload'}
                )
        except Exception as e:
            current_app.logger.warning(f"Could not publish account change event: {e}")

        # Activity log
        try:
            activity_logger.log_settings_change(
                customer_id=customer_id,
                user_id=None,
                setting_type='customer_profile_upload',
                changed_fields=['external_account_id', 'profile_metadata'],
                before_values={},
                after_values={'updated_accounts': updated, 'file': file.filename},
                status='success'
            )
        except Exception:
            pass

        return jsonify({
            'status': 'success',
            'updated_accounts': updated
        })
    except Exception as e:
        current_app.logger.exception('Error processing customer profile upload')
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


def _safe_date(val):
    if pd.isna(val) or val is None or str(val).strip() == '':
        return None
    if isinstance(val, (datetime, )):
        return val.iso8601() if hasattr(val, 'iso8601') else val.isoformat()
    try:
        # pandas may give Timestamp
        return pd.to_datetime(val).isoformat()
    except Exception:
        return str(val)


def _safe_number(val):
    if val is None or (isinstance(val, str) and not val.strip()):
        return None
    try:
        return float(val)
    except Exception:
        return None


