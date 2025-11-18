"""
Rehydration API - Import/Restore account, product, and KPI data from exported Excel file
This allows customers to backup and restore their complete data.
"""
from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import Account, Product, KPI, KPIUpload
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
    
    Expected Excel format (from export):
    - Sheet "Accounts Summary": Account data with profile_metadata
    - Sheet "All KPIs": KPI data with product_id and aggregation_type
    - Sheet "Products": Product data
    - Sheet "Export Metadata": Metadata about the export
    
    This will:
    1. Create/update accounts (matching by external_account_id or account_name)
    2. Create/update products (matching by account_id + product_name)
    3. Create/update KPIs (matching by account_id + kpi_parameter + product_id)
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
        
        results = {
            'accounts_created': 0,
            'accounts_updated': 0,
            'products_created': 0,
            'products_updated': 0,
            'kpis_created': 0,
            'kpis_updated': 0,
            'errors': []
        }
        
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
                        
                        if existing_account:
                            # Update existing account
                            existing_account.account_name = account_name
                            existing_account.revenue = float(row.get('Revenue', 0)) if pd.notna(row.get('Revenue')) else 0
                            existing_account.industry = str(row.get('Industry', '')) if pd.notna(row.get('Industry')) else ''
                            existing_account.region = str(row.get('Region', '')) if pd.notna(row.get('Region')) else ''
                            existing_account.account_status = str(row.get('Status', 'active')) if pd.notna(row.get('Status')) else 'active'
                            if external_account_id:
                                existing_account.external_account_id = external_account_id
                            if profile_metadata:
                                existing_account.profile_metadata = profile_metadata
                            results['accounts_updated'] += 1
                        else:
                            # Create new account
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
                        
                        # Find existing product
                        existing_product = Product.query.filter_by(
                            account_id=account.account_id,
                            product_name=product_name
                        ).first()
                        
                        if existing_product:
                            # Update existing product
                            existing_product.product_sku = str(row.get('Product SKU', '')) if pd.notna(row.get('Product SKU')) else None
                            existing_product.product_type = str(row.get('Product Type', '')) if pd.notna(row.get('Product Type')) else None
                            existing_product.revenue = float(row.get('Revenue', 0)) if pd.notna(row.get('Revenue')) else None
                            existing_product.status = str(row.get('Status', 'active')) if pd.notna(row.get('Status')) else 'active'
                            results['products_updated'] += 1
                        else:
                            # Create new product
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
                        
                        # Find existing KPI
                        existing_kpi = None
                        if product:
                            existing_kpi = KPI.query.filter_by(
                                account_id=account.account_id,
                                kpi_parameter=kpi_parameter,
                                product_id=product.product_id
                            ).first()
                        else:
                            existing_kpi = KPI.query.filter_by(
                                account_id=account.account_id,
                                kpi_parameter=kpi_parameter,
                                product_id=None
                            ).first()
                        
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
                        
                        if existing_kpi:
                            # Update existing KPI
                            for key, value in kpi_data.items():
                                if key != 'upload_id' and value:
                                    setattr(existing_kpi, key, value)
                            results['kpis_updated'] += 1
                        else:
                            # Create new KPI
                            new_kpi = KPI(**kpi_data)
                            db.session.add(new_kpi)
                            results['kpis_created'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error processing KPI {row.get('KPI Parameter', 'unknown')}: {str(e)}")
        
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

