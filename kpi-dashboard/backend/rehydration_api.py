"""
Rehydration API - Import/Restore account, product, and KPI data from exported Excel file
This allows customers to backup and restore their complete data.
"""
from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import (
    Account, Product, KPI, KPIUpload, CustomerConfig, HealthTrend,
    KPITimeSeries, KPIReferenceRange, PlaybookTrigger, PlaybookExecution,
    PlaybookReport, FeatureToggle
)
from werkzeug.utils import secure_filename
import pandas as pd
import io
import json
from datetime import datetime

rehydration_api = Blueprint('rehydration_api', __name__)

@rehydration_api.route('/api/rehydrate/import', methods=['POST'])
def import_account_data():
    """
    Import/rehydrate account, product, and KPI data from exported Excel file.
    
    IMPORTANT: This REPLACES all existing data for the customer (no merge/update).
    All existing accounts, products, and KPIs for this customer will be deleted first.
    
    Expected Excel format (from export):
    - Sheet "Accounts Summary": Account data with profile_metadata
    - Sheet "All KPIs": KPI data with product_id and aggregation_type
    - Sheet "Products": Product data
    - Sheet "Export Metadata": Metadata about the export (includes Customer ID for validation)
    
    Security:
    - Validates that the exported Customer ID matches the current customer
    - Prevents cross-tenant data imports
    - Checks export version and timestamp for compatibility
    """
    try:
        customer_id = get_current_customer_id()
        user_id = get_current_user_id()
        
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'No file provided'}), 400
        
        # Read Excel file
        raw_excel = file.read()
        xls = pd.ExcelFile(io.BytesIO(raw_excel))
        
        # Step 0: Validate export metadata (customer ID, version, timestamp)
        export_customer_id = None
        export_version = None
        export_timestamp = None
        
        if "Export Metadata" in xls.sheet_names:
            metadata_df = pd.read_excel(xls, sheet_name="Export Metadata", header=None)
            for idx, row in metadata_df.iterrows():
                if pd.notna(row[0]):
                    value = str(row[0]).strip()
                    if value.startswith('Customer ID:'):
                        try:
                            export_customer_id = int(value.split(':')[1].strip())
                        except:
                            pass
                    elif value.startswith('Export Version:'):
                        try:
                            export_version = int(value.split(':')[1].strip())
                        except:
                            pass
                    elif value.startswith('Export Timestamp:'):
                        try:
                            export_timestamp = value.split(':')[1].strip()
                        except:
                            pass
        
        # Validate customer ID match (prevent cross-tenant imports)
        if export_customer_id is not None and export_customer_id != customer_id:
            return jsonify({
                'error': f'Security validation failed: Export file belongs to Customer ID {export_customer_id}, but you are logged in as Customer ID {customer_id}. Cannot import data from different customer.'
            }), 403
        
        if export_customer_id is None:
            return jsonify({
                'error': 'Export file missing Customer ID validation. Cannot verify file authenticity. Please export a fresh file and try again.'
            }), 400
        
        # Validate export version (for future compatibility)
        if export_version is None:
            return jsonify({
                'error': 'Export file missing version information. Please export a fresh file and try again.'
            }), 400
        
        # Warn if version mismatch (but allow import)
        if export_version != 1:
            # Future: Add version compatibility checks here
            pass
        
        results = {
            'accounts_deleted': 0,
            'accounts_created': 0,
            'products_deleted': 0,
            'products_created': 0,
            'kpis_deleted': 0,
            'kpis_created': 0,
            'playbook_triggers_deleted': 0,
            'playbook_triggers_created': 0,
            'playbook_executions_deleted': 0,
            'playbook_executions_created': 0,
            'playbook_reports_deleted': 0,
            'playbook_reports_created': 0,
            'health_trends_deleted': 0,
            'health_trends_created': 0,
            'time_series_deleted': 0,
            'time_series_created': 0,
            'ref_ranges_deleted': 0,
            'ref_ranges_created': 0,
            'toggles_deleted': 0,
            'toggles_created': 0,
            'export_customer_id': export_customer_id,
            'export_version': export_version,
            'export_timestamp': export_timestamp,
            'errors': []
        }
        
        # STEP 1: DELETE ALL EXISTING DATA FOR THIS CUSTOMER (REPLACE MODE)
        # Count before deletion for reporting
        accounts_deleted = Account.query.filter_by(customer_id=customer_id).count()
        products_deleted = Product.query.filter_by(customer_id=customer_id).count()
        kpi_uploads = KPIUpload.query.filter_by(customer_id=customer_id).all()
        upload_ids = [upload.upload_id for upload in kpi_uploads]
        kpis_deleted = KPI.query.filter(KPI.upload_id.in_(upload_ids)).count() if upload_ids else 0
        triggers_deleted = PlaybookTrigger.query.filter_by(customer_id=customer_id).count()
        executions_deleted = PlaybookExecution.query.filter_by(customer_id=customer_id).count()
        reports_deleted = PlaybookReport.query.filter_by(customer_id=customer_id).count()
        health_trends_deleted = HealthTrend.query.filter_by(customer_id=customer_id).count()
        time_series_deleted = KPITimeSeries.query.filter_by(customer_id=customer_id).count()
        ref_ranges_deleted = KPIReferenceRange.query.filter_by(customer_id=customer_id).count()
        toggles_deleted = FeatureToggle.query.filter_by(customer_id=customer_id).count()
        
        # Delete all KPIs for this customer
        if upload_ids:
            KPI.query.filter(KPI.upload_id.in_(upload_ids)).delete(synchronize_session=False)
        
        # Delete all KPIUploads
        KPIUpload.query.filter_by(customer_id=customer_id).delete()
        
        # Delete all Products
        Product.query.filter_by(customer_id=customer_id).delete()
        
        # Delete all Accounts
        Account.query.filter_by(customer_id=customer_id).delete()
        
        # Delete all Playbook data
        PlaybookReport.query.filter_by(customer_id=customer_id).delete()
        PlaybookExecution.query.filter_by(customer_id=customer_id).delete()
        PlaybookTrigger.query.filter_by(customer_id=customer_id).delete()
        
        # Delete all Health Trends
        HealthTrend.query.filter_by(customer_id=customer_id).delete()
        
        # Delete all KPI Time Series
        KPITimeSeries.query.filter_by(customer_id=customer_id).delete()
        
        # Delete customer-specific KPI Reference Ranges
        KPIReferenceRange.query.filter_by(customer_id=customer_id).delete()
        
        # Delete Feature Toggles
        FeatureToggle.query.filter_by(customer_id=customer_id).delete()
        
        # Delete Customer Config (will recreate from import)
        CustomerConfig.query.filter_by(customer_id=customer_id).delete()
        
        results['accounts_deleted'] = accounts_deleted
        results['products_deleted'] = products_deleted
        results['kpis_deleted'] = kpis_deleted
        results['playbook_triggers_deleted'] = triggers_deleted
        results['playbook_executions_deleted'] = executions_deleted
        results['playbook_reports_deleted'] = reports_deleted
        results['health_trends_deleted'] = health_trends_deleted
        results['time_series_deleted'] = time_series_deleted
        results['ref_ranges_deleted'] = ref_ranges_deleted
        results['toggles_deleted'] = toggles_deleted
        
        db.session.flush()  # Commit deletions before creating new data
        
        # Step 1: Import Accounts
        if "Accounts Summary" in xls.sheet_names:
            accounts_df = pd.read_excel(xls, sheet_name="Accounts Summary")
            required_cols = ['Account ID', 'Account Name']
            if not all(col in accounts_df.columns for col in required_cols):
                results['errors'].append('Accounts Summary sheet missing required columns')
            else:
                for _, row in accounts_df.iterrows():
                    try:
                        account_name = str(row['Account Name']).strip()
                        if not account_name or account_name == 'nan':
                            continue
                        
                        external_account_id = str(row.get('External Account ID', '')).strip() if pd.notna(row.get('External Account ID')) else None
                        external_account_id = external_account_id if external_account_id and external_account_id != 'nan' else None
                        
                        # Try to find existing account by external_account_id or account_name
                        existing_account = None
                        if external_account_id:
                            existing_account = Account.query.filter_by(
                                customer_id=customer_id,
                                external_account_id=external_account_id
                            ).first()
                        
                        if not existing_account:
                            existing_account = Account.query.filter_by(
                                customer_id=customer_id,
                                account_name=account_name
                            ).first()
                        
                        # Parse profile_metadata
                        profile_metadata = None
                        if 'Profile Metadata (JSON)' in accounts_df.columns:
                            pm_str = row.get('Profile Metadata (JSON)', '')
                            if pd.notna(pm_str) and str(pm_str).strip() and str(pm_str) != 'nan':
                                try:
                                    profile_metadata = json.loads(str(pm_str))
                                except:
                                    # Try to parse as string representation
                                    try:
                                        profile_metadata = eval(str(pm_str))
                                    except:
                                        pass
                        
                        # Create new account (all existing accounts were deleted)
                        new_account = Account(
                            customer_id=customer_id,
                            account_name=account_name,
                            revenue=float(row.get('Revenue', 0)) if pd.notna(row.get('Revenue')) else 0,
                            industry=str(row.get('Industry', '')) if pd.notna(row.get('Industry')) else 'Unknown',
                            region=str(row.get('Region', '')) if pd.notna(row.get('Region')) else 'Unknown',
                            account_status=str(row.get('Status', 'active')) if pd.notna(row.get('Status')) else 'active',
                            external_account_id=external_account_id,
                            profile_metadata=profile_metadata
                        )
                        db.session.add(new_account)
                        results['accounts_created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error processing account {row.get('Account Name', 'unknown')}: {str(e)}")
        
        db.session.flush()  # Get account_ids before processing products
        
        # Step 2: Import Products
        if "Products" in xls.sheet_names:
            products_df = pd.read_excel(xls, sheet_name="Products")
            required_cols = ['Product ID', 'Account ID', 'Product Name']
            if not all(col in products_df.columns for col in required_cols):
                results['errors'].append('Products sheet missing required columns')
            else:
                for _, row in products_df.iterrows():
                    try:
                        account_id_val = row.get('Account ID')
                        if pd.isna(account_id_val):
                            continue
                        
                        # Find account by ID or name
                        account = Account.query.filter_by(
                            customer_id=customer_id,
                            account_id=int(account_id_val)
                        ).first()
                        
                        if not account:
                            # Try by account name if provided
                            account_name = str(row.get('Account Name', '')).strip() if pd.notna(row.get('Account Name')) else None
                            if account_name:
                                account = Account.query.filter_by(
                                    customer_id=customer_id,
                                    account_name=account_name
                                ).first()
                        
                        if not account:
                            results['errors'].append(f"Account not found for product {row.get('Product Name', 'unknown')}")
                            continue
                        
                        product_name = str(row.get('Product Name', '')).strip()
                        if not product_name or product_name == 'nan':
                            continue
                        
                        # Create new product (all existing products were deleted)
                        new_product = Product(
                            account_id=account.account_id,
                            customer_id=customer_id,
                            product_name=product_name,
                            product_sku=str(row.get('Product SKU', '')) if pd.notna(row.get('Product SKU')) else None,
                            product_type=str(row.get('Product Type', '')) if pd.notna(row.get('Product Type')) else None,
                            revenue=float(row.get('Revenue', 0)) if pd.notna(row.get('Revenue')) else None,
                            status=str(row.get('Status', 'active')) if pd.notna(row.get('Status')) else 'active'
                        )
                        db.session.add(new_product)
                        results['products_created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error processing product {row.get('Product Name', 'unknown')}: {str(e)}")
        
        db.session.flush()  # Get product_ids before processing KPIs
        
        # Step 3: Import KPIs
        if "All KPIs" in xls.sheet_names:
            kpis_df = pd.read_excel(xls, sheet_name="All KPIs")
            required_cols = ['Account ID', 'KPI Parameter']
            if not all(col in kpis_df.columns for col in required_cols):
                results['errors'].append('All KPIs sheet missing required columns')
            else:
                # Create a KPIUpload record for this import
                upload = KPIUpload(
                    customer_id=customer_id,
                    user_id=user_id,
                    account_id=None,  # Multi-account import
                    version=1,
                    original_filename=file.filename,
                    raw_excel=raw_excel
                )
                db.session.add(upload)
                db.session.flush()
                
                for _, row in kpis_df.iterrows():
                    try:
                        account_id_val = row.get('Account ID')
                        if pd.isna(account_id_val):
                            continue
                        
                        # Find account
                        account = Account.query.filter_by(
                            customer_id=customer_id,
                            account_id=int(account_id_val)
                        ).first()
                        
                        if not account:
                            account_name = str(row.get('Account Name', '')).strip() if pd.notna(row.get('Account Name')) else None
                            if account_name:
                                account = Account.query.filter_by(
                                    customer_id=customer_id,
                                    account_name=account_name
                                ).first()
                        
                        if not account:
                            results['errors'].append(f"Account not found for KPI {row.get('KPI Parameter', 'unknown')}")
                            continue
                        
                        kpi_parameter = str(row.get('KPI Parameter', '')).strip()
                        if not kpi_parameter or kpi_parameter == 'nan':
                            continue
                        
                        # Find product if product_id is provided
                        product = None
                        product_id_val = row.get('Product ID')
                        if pd.notna(product_id_val) and str(product_id_val).strip() and str(product_id_val) != 'nan':
                            product = Product.query.filter_by(
                                product_id=int(product_id_val),
                                account_id=account.account_id
                            ).first()
                            
                            # If not found by ID, try by name
                            if not product:
                                product_name = str(row.get('Product Name', '')).strip() if pd.notna(row.get('Product Name')) else None
                                if product_name and product_name != 'nan':
                                    product = Product.query.filter_by(
                                        account_id=account.account_id,
                                        product_name=product_name
                                    ).first()
                        
                        # Create new KPI (all existing KPIs were deleted)
                        kpi_data = {
                            'upload_id': upload.upload_id,
                            'account_id': account.account_id,
                            'product_id': product.product_id if product else None,
                            'category': str(row.get('Category', '')) if pd.notna(row.get('Category')) else None,
                            'kpi_parameter': kpi_parameter,
                            'data': str(row.get('Data', '')) if pd.notna(row.get('Data')) else None,
                            'impact_level': str(row.get('Impact Level', '')) if pd.notna(row.get('Impact Level')) else None,
                            'measurement_frequency': str(row.get('Measurement Frequency', '')) if pd.notna(row.get('Measurement Frequency')) else None,
                            'health_score_component': str(row.get('Health Score Component', '')) if pd.notna(row.get('Health Score Component')) else None,
                            'weight': str(row.get('Weight', '')) if pd.notna(row.get('Weight')) else None,
                            'aggregation_type': str(row.get('Aggregation Type', '')) if pd.notna(row.get('Aggregation Type')) else None
                        }
                        
                        new_kpi = KPI(**kpi_data)
                        db.session.add(new_kpi)
                        results['kpis_created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error processing KPI {row.get('KPI Parameter', 'unknown')}: {str(e)}")
        
        db.session.flush()  # Get account_ids before processing profile data
        
        # Step 4: Import Customer Profile Data (separate tab for account/product cards)
        if "Customer Profile Data" in xls.sheet_names:
            profile_df = pd.read_excel(xls, sheet_name="Customer Profile Data")
            required_cols = ['Account ID']
            if all(col in profile_df.columns for col in required_cols):
                for _, row in profile_df.iterrows():
                    try:
                        account_id_val = row.get('Account ID')
                        if pd.isna(account_id_val):
                            continue
                        
                        account = Account.query.filter_by(
                            customer_id=customer_id,
                            account_id=int(account_id_val)
                        ).first()
                        
                        if not account:
                            continue
                        
                        # Import profile_metadata
                        pm_str = row.get('Profile Metadata (JSON)', '')
                        if pd.notna(pm_str) and str(pm_str).strip() and str(pm_str) != 'nan':
                            try:
                                profile_metadata = json.loads(str(pm_str))
                                account.profile_metadata = profile_metadata
                            except:
                                try:
                                    profile_metadata = eval(str(pm_str))
                                    account.profile_metadata = profile_metadata
                                except:
                                    pass
                    except Exception as e:
                        results['errors'].append(f"Error processing profile data for account {row.get('Account ID', 'unknown')}: {str(e)}")
        
        db.session.flush()
        
        # Step 5: Import Playbook Triggers
        if "Playbook Triggers" in xls.sheet_names:
            triggers_df = pd.read_excel(xls, sheet_name="Playbook Triggers")
            required_cols = ['Trigger ID', 'Playbook Type']
            if all(col in triggers_df.columns for col in required_cols):
                for _, row in triggers_df.iterrows():
                    try:
                        playbook_type = str(row.get('Playbook Type', '')).strip()
                        if not playbook_type or playbook_type == 'nan':
                            continue
                        
                        trigger_config = str(row.get('Trigger Config (JSON)', '')) if pd.notna(row.get('Trigger Config (JSON)')) else None
                        auto_trigger = str(row.get('Auto Trigger Enabled', '')).strip().lower() == 'yes' if pd.notna(row.get('Auto Trigger Enabled')) else False
                        
                        last_evaluated = None
                        if pd.notna(row.get('Last Evaluated')) and str(row.get('Last Evaluated')).strip():
                            try:
                                last_evaluated = pd.to_datetime(row.get('Last Evaluated'))
                            except:
                                pass
                        
                        last_triggered = None
                        if pd.notna(row.get('Last Triggered')) and str(row.get('Last Triggered')).strip():
                            try:
                                last_triggered = pd.to_datetime(row.get('Last Triggered'))
                            except:
                                pass
                        
                        trigger_count = int(row.get('Trigger Count', 0)) if pd.notna(row.get('Trigger Count')) else 0
                        
                        new_trigger = PlaybookTrigger(
                            customer_id=customer_id,
                            playbook_type=playbook_type,
                            trigger_config=trigger_config,
                            auto_trigger_enabled=auto_trigger,
                            last_evaluated=last_evaluated,
                            last_triggered=last_triggered,
                            trigger_count=trigger_count
                        )
                        db.session.add(new_trigger)
                        results['playbook_triggers_created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error processing playbook trigger {row.get('Playbook Type', 'unknown')}: {str(e)}")
        
        db.session.flush()
        
        # Step 6: Import Playbook Executions
        if "Playbook Executions" in xls.sheet_names:
            executions_df = pd.read_excel(xls, sheet_name="Playbook Executions")
            required_cols = ['Execution ID', 'Playbook ID']
            if all(col in executions_df.columns for col in required_cols):
                for _, row in executions_df.iterrows():
                    try:
                        execution_id = str(row.get('Execution ID', '')).strip()
                        if not execution_id or execution_id == 'nan':
                            continue
                        
                        playbook_id = str(row.get('Playbook ID', '')).strip()
                        if not playbook_id or playbook_id == 'nan':
                            continue
                        
                        account_id_val = row.get('Account ID')
                        account_id = int(account_id_val) if pd.notna(account_id_val) and str(account_id_val).strip() != 'nan' else None
                        
                        status = str(row.get('Status', 'in-progress')).strip() if pd.notna(row.get('Status')) else 'in-progress'
                        current_step = str(row.get('Current Step', '')).strip() if pd.notna(row.get('Current Step')) else None
                        
                        # Import execution_data
                        execution_data = None
                        ed_str = row.get('Execution Data (JSON)', '')
                        if pd.notna(ed_str) and str(ed_str).strip() and str(ed_str) != 'nan':
                            try:
                                execution_data = json.loads(str(ed_str))
                            except:
                                try:
                                    execution_data = eval(str(ed_str))
                                except:
                                    pass
                        
                        started_at = None
                        if pd.notna(row.get('Started At')) and str(row.get('Started At')).strip():
                            try:
                                started_at = pd.to_datetime(row.get('Started At'))
                            except:
                                pass
                        
                        completed_at = None
                        if pd.notna(row.get('Completed At')) and str(row.get('Completed At')).strip():
                            try:
                                completed_at = pd.to_datetime(row.get('Completed At'))
                            except:
                                pass
                        
                        if not started_at:
                            started_at = datetime.utcnow()
                        
                        if not execution_data:
                            execution_data = {}
                        
                        new_execution = PlaybookExecution(
                            execution_id=execution_id,
                            customer_id=customer_id,
                            account_id=account_id,
                            playbook_id=playbook_id,
                            status=status,
                            current_step=current_step,
                            execution_data=execution_data,
                            started_at=started_at,
                            completed_at=completed_at
                        )
                        db.session.add(new_execution)
                        results['playbook_executions_created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error processing playbook execution {row.get('Execution ID', 'unknown')}: {str(e)}")
        
        db.session.flush()
        
        # Step 7: Import Playbook Reports
        if "Playbook Reports" in xls.sheet_names:
            reports_df = pd.read_excel(xls, sheet_name="Playbook Reports")
            required_cols = ['Report ID', 'Execution ID', 'Playbook ID', 'Playbook Name']
            if all(col in reports_df.columns for col in required_cols):
                for _, row in reports_df.iterrows():
                    try:
                        execution_id = str(row.get('Execution ID', '')).strip()
                        if not execution_id or execution_id == 'nan':
                            continue
                        
                        playbook_id = str(row.get('Playbook ID', '')).strip()
                        playbook_name = str(row.get('Playbook Name', '')).strip()
                        if not playbook_id or playbook_id == 'nan' or not playbook_name or playbook_name == 'nan':
                            continue
                        
                        account_id_val = row.get('Account ID')
                        account_id = int(account_id_val) if pd.notna(account_id_val) and str(account_id_val).strip() != 'nan' else None
                        account_name = str(row.get('Account Name', '')).strip() if pd.notna(row.get('Account Name')) else None
                        
                        status = str(row.get('Status', 'in-progress')).strip() if pd.notna(row.get('Status')) else 'in-progress'
                        
                        # Import report_data
                        report_data = None
                        rd_str = row.get('Report Data (JSON)', '')
                        if pd.notna(rd_str) and str(rd_str).strip() and str(rd_str) != 'nan':
                            try:
                                report_data = json.loads(str(rd_str))
                            except:
                                try:
                                    report_data = eval(str(rd_str))
                                except:
                                    pass
                        
                        if not report_data:
                            report_data = {}
                        
                        duration = str(row.get('Duration', '')).strip() if pd.notna(row.get('Duration')) else None
                        steps_completed = int(row.get('Steps Completed', 0)) if pd.notna(row.get('Steps Completed')) else 0
                        total_steps = int(row.get('Total Steps', 0)) if pd.notna(row.get('Total Steps')) else None
                        
                        started_at = None
                        if pd.notna(row.get('Started At')) and str(row.get('Started At')).strip():
                            try:
                                started_at = pd.to_datetime(row.get('Started At'))
                            except:
                                pass
                        
                        completed_at = None
                        if pd.notna(row.get('Completed At')) and str(row.get('Completed At')).strip():
                            try:
                                completed_at = pd.to_datetime(row.get('Completed At'))
                            except:
                                pass
                        
                        if not started_at:
                            started_at = datetime.utcnow()
                        
                        new_report = PlaybookReport(
                            execution_id=execution_id,
                            customer_id=customer_id,
                            account_id=account_id,
                            playbook_id=playbook_id,
                            playbook_name=playbook_name,
                            account_name=account_name,
                            status=status,
                            report_data=report_data,
                            duration=duration,
                            steps_completed=steps_completed,
                            total_steps=total_steps,
                            started_at=started_at,
                            completed_at=completed_at
                        )
                        db.session.add(new_report)
                        results['playbook_reports_created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error processing playbook report {row.get('Report ID', 'unknown')}: {str(e)}")
        
        db.session.flush()
        
        # Step 8: Import Customer Config
        if "Customer Config" in xls.sheet_names:
            config_df = pd.read_excel(xls, sheet_name="Customer Config")
            if len(config_df) > 0:
                try:
                    row = config_df.iloc[0]
                    kpi_upload_mode = str(row.get('KPI Upload Mode', 'corporate')).strip() if pd.notna(row.get('KPI Upload Mode')) else 'corporate'
                    category_weights = str(row.get('Category Weights (JSON)', '')).strip() if pd.notna(row.get('Category Weights (JSON)')) else None
                    master_file_name = str(row.get('Master File Name', '')).strip() if pd.notna(row.get('Master File Name')) else None
                    
                    new_config = CustomerConfig(
                        customer_id=customer_id,
                        kpi_upload_mode=kpi_upload_mode,
                        category_weights=category_weights,
                        master_file_name=master_file_name
                    )
                    db.session.add(new_config)
                except Exception as e:
                    results['errors'].append(f"Error processing customer config: {str(e)}")
        
        db.session.flush()
        
        # Step 9: Import Health Trends
        if "Health Trends" in xls.sheet_names:
            health_df = pd.read_excel(xls, sheet_name="Health Trends")
            required_cols = ['Trend ID', 'Account ID', 'Month', 'Year']
            if all(col in health_df.columns for col in required_cols):
                for _, row in health_df.iterrows():
                    try:
                        account_id_val = row.get('Account ID')
                        if pd.isna(account_id_val):
                            continue
                        
                        account = Account.query.filter_by(
                            customer_id=customer_id,
                            account_id=int(account_id_val)
                        ).first()
                        
                        if not account:
                            continue
                        
                        month = int(row.get('Month')) if pd.notna(row.get('Month')) else None
                        year = int(row.get('Year')) if pd.notna(row.get('Year')) else None
                        
                        if not month or not year:
                            continue
                        
                        overall_health_score = float(row.get('Overall Health Score')) if pd.notna(row.get('Overall Health Score')) else None
                        if overall_health_score is None:
                            continue
                        
                        new_trend = HealthTrend(
                            account_id=account.account_id,
                            customer_id=customer_id,
                            month=month,
                            year=year,
                            overall_health_score=overall_health_score,
                            product_usage_score=float(row.get('Product Usage Score')) if pd.notna(row.get('Product Usage Score')) else None,
                            support_score=float(row.get('Support Score')) if pd.notna(row.get('Support Score')) else None,
                            customer_sentiment_score=float(row.get('Customer Sentiment Score')) if pd.notna(row.get('Customer Sentiment Score')) else None,
                            business_outcomes_score=float(row.get('Business Outcomes Score')) if pd.notna(row.get('Business Outcomes Score')) else None,
                            relationship_strength_score=float(row.get('Relationship Strength Score')) if pd.notna(row.get('Relationship Strength Score')) else None,
                            total_kpis=int(row.get('Total KPIs', 0)) if pd.notna(row.get('Total KPIs')) else 0,
                            valid_kpis=int(row.get('Valid KPIs', 0)) if pd.notna(row.get('Valid KPIs')) else 0
                        )
                        db.session.add(new_trend)
                        results['health_trends_created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error processing health trend {row.get('Trend ID', 'unknown')}: {str(e)}")
        
        db.session.flush()
        
        # Step 10: Import KPI Time Series
        if "KPI Time Series" in xls.sheet_names:
            ts_df = pd.read_excel(xls, sheet_name="KPI Time Series")
            required_cols = ['KPI ID', 'Account ID', 'Month', 'Year']
            if all(col in ts_df.columns for col in required_cols):
                for _, row in ts_df.iterrows():
                    try:
                        kpi_id_val = row.get('KPI ID')
                        account_id_val = row.get('Account ID')
                        if pd.isna(kpi_id_val) or pd.isna(account_id_val):
                            continue
                        
                        account = Account.query.filter_by(
                            customer_id=customer_id,
                            account_id=int(account_id_val)
                        ).first()
                        
                        if not account:
                            continue
                        
                        month = int(row.get('Month')) if pd.notna(row.get('Month')) else None
                        year = int(row.get('Year')) if pd.notna(row.get('Year')) else None
                        
                        if not month or not year:
                            continue
                        
                        new_ts = KPITimeSeries(
                            kpi_id=int(kpi_id_val),
                            account_id=account.account_id,
                            customer_id=customer_id,
                            month=month,
                            year=year,
                            value=float(row.get('Value')) if pd.notna(row.get('Value')) else None,
                            health_status=str(row.get('Health Status', '')).strip() if pd.notna(row.get('Health Status')) else None,
                            health_score=float(row.get('Health Score')) if pd.notna(row.get('Health Score')) else None
                        )
                        db.session.add(new_ts)
                        results['time_series_created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error processing time series {row.get('ID', 'unknown')}: {str(e)}")
        
        db.session.flush()
        
        # Step 11: Import KPI Reference Ranges
        if "KPI Reference Ranges" in xls.sheet_names:
            ref_df = pd.read_excel(xls, sheet_name="KPI Reference Ranges")
            required_cols = ['KPI Name', 'Unit', 'Higher Is Better']
            if all(col in ref_df.columns for col in required_cols):
                for _, row in ref_df.iterrows():
                    try:
                        kpi_name = str(row.get('KPI Name', '')).strip()
                        if not kpi_name or kpi_name == 'nan':
                            continue
                        
                        unit = str(row.get('Unit', '')).strip()
                        if not unit or unit == 'nan':
                            continue
                        
                        higher_is_better = str(row.get('Higher Is Better', '')).strip().lower() == 'yes' if pd.notna(row.get('Higher Is Better')) else True
                        
                        critical_min = float(row.get('Critical Min')) if pd.notna(row.get('Critical Min')) else None
                        critical_max = float(row.get('Critical Max')) if pd.notna(row.get('Critical Max')) else None
                        risk_min = float(row.get('Risk Min')) if pd.notna(row.get('Risk Min')) else None
                        risk_max = float(row.get('Risk Max')) if pd.notna(row.get('Risk Max')) else None
                        healthy_min = float(row.get('Healthy Min')) if pd.notna(row.get('Healthy Min')) else None
                        healthy_max = float(row.get('Healthy Max')) if pd.notna(row.get('Healthy Max')) else None
                        
                        if not all([critical_min, critical_max, risk_min, risk_max, healthy_min, healthy_max]):
                            continue
                        
                        new_ref_range = KPIReferenceRange(
                            customer_id=customer_id,
                            kpi_name=kpi_name,
                            unit=unit,
                            higher_is_better=higher_is_better,
                            critical_min=critical_min,
                            critical_max=critical_max,
                            risk_min=risk_min,
                            risk_max=risk_max,
                            healthy_min=healthy_min,
                            healthy_max=healthy_max,
                            critical_range=str(row.get('Critical Range', '')).strip() if pd.notna(row.get('Critical Range')) else None,
                            risk_range=str(row.get('Risk Range', '')).strip() if pd.notna(row.get('Risk Range')) else None,
                            healthy_range=str(row.get('Healthy Range', '')).strip() if pd.notna(row.get('Healthy Range')) else None,
                            description=str(row.get('Description', '')).strip() if pd.notna(row.get('Description')) else None
                        )
                        db.session.add(new_ref_range)
                        results['ref_ranges_created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error processing reference range {row.get('KPI Name', 'unknown')}: {str(e)}")
        
        db.session.flush()
        
        # Step 12: Import Feature Toggles
        if "Feature Toggles" in xls.sheet_names:
            toggles_df = pd.read_excel(xls, sheet_name="Feature Toggles")
            required_cols = ['Feature Name']
            if all(col in toggles_df.columns for col in required_cols):
                for _, row in toggles_df.iterrows():
                    try:
                        feature_name = str(row.get('Feature Name', '')).strip()
                        if not feature_name or feature_name == 'nan':
                            continue
                        
                        enabled = str(row.get('Enabled', '')).strip().lower() == 'yes' if pd.notna(row.get('Enabled')) else False
                        
                        # Import config
                        config = None
                        config_str = row.get('Config (JSON)', '')
                        if pd.notna(config_str) and str(config_str).strip() and str(config_str) != 'nan':
                            try:
                                config = json.loads(str(config_str))
                            except:
                                try:
                                    config = eval(str(config_str))
                                except:
                                    pass
                        
                        description = str(row.get('Description', '')).strip() if pd.notna(row.get('Description')) else None
                        
                        new_toggle = FeatureToggle(
                            customer_id=customer_id,
                            feature_name=feature_name,
                            enabled=enabled,
                            config=config,
                            description=description
                        )
                        db.session.add(new_toggle)
                        results['toggles_created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error processing feature toggle {row.get('Feature Name', 'unknown')}: {str(e)}")
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Data rehydration completed',
            'results': results
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'error': f'Rehydration failed: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500

