from flask import Blueprint, request, jsonify, send_file
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import KPI, KPIUpload, Account, Product
import pandas as pd
import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
import json

export_api = Blueprint('export_api', __name__)

@export_api.route('/api/export/<int:upload_id>', methods=['GET'])
def export_excel(upload_id):
    """Export KPI data back to Excel format"""
    try:
        # Get the upload record
        upload = KPIUpload.query.get_or_404(upload_id)
        
        # Get all KPIs for this upload
        kpis = KPI.query.filter_by(upload_id=upload_id).all()
        
        if not kpis:
            return jsonify({'error': 'No KPIs found for this upload'}), 404
        
        # Group KPIs by category
        kpis_by_category = {}
        for kpi in kpis:
            if kpi.category not in kpis_by_category:
                kpis_by_category[kpi.category] = []
            kpis_by_category[kpi.category].append(kpi)
        
        # Create Excel workbook
        wb = openpyxl.Workbook()
        
        # Remove default sheet
        wb.remove(wb.active)
        
        # Add metadata sheet (first sheet)
        metadata_sheet = wb.create_sheet("Metadata")
        metadata_sheet['A1'] = "KPI Dashboard Export"
        metadata_sheet['A2'] = f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        metadata_sheet['A3'] = f"Original File: {upload.original_filename}"
        metadata_sheet['A4'] = f"Version: {upload.version}"
        metadata_sheet['A5'] = f"Upload Date: {upload.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}"
        metadata_sheet['A6'] = f"Total KPIs: {len(kpis)}"
        
        # Style metadata
        for row in range(1, 7):
            metadata_sheet[f'A{row}'].font = Font(bold=True)
        
        # Add KPI sheets
        for category, category_kpis in kpis_by_category.items():
            sheet = wb.create_sheet(category)
            
            # Add header row
            headers = [
                'Health Score Component',
                'Weight',
                'Data',
                'Source Review',
                'KPI/Parameter',
                'Impact level',
                'Measurement Frequency'
            ]
            
            for col, header in enumerate(headers, 1):
                cell = sheet.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")
            
            # Add KPI data
            for row, kpi in enumerate(category_kpis, 2):
                sheet.cell(row=row, column=1, value=kpi.health_score_component)
                sheet.cell(row=row, column=2, value=kpi.weight)
                sheet.cell(row=row, column=3, value=kpi.data)
                sheet.cell(row=row, column=4, value=kpi.source_review)
                sheet.cell(row=row, column=5, value=kpi.kpi_parameter)
                sheet.cell(row=row, column=6, value=kpi.impact_level)
                sheet.cell(row=row, column=7, value=kpi.measurement_frequency)
            
            # Auto-adjust column widths
            for column in sheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                sheet.column_dimensions[column_letter].width = adjusted_width
        
        # Add summary sheet (last sheet)
        summary_sheet = wb.create_sheet("Summary")
        summary_sheet['A1'] = "KPI Summary"
        summary_sheet['A1'].font = Font(bold=True, size=14)
        
        summary_sheet['A3'] = "Category Distribution:"
        summary_sheet['A3'].font = Font(bold=True)
        
        row = 4
        for category, category_kpis in kpis_by_category.items():
            summary_sheet[f'A{row}'] = f"{category}: {len(category_kpis)} KPIs"
            row += 1
        
        # Save to bytes
        excel_bytes = io.BytesIO()
        wb.save(excel_bytes)
        excel_bytes.seek(0)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"KPI_Export_v{upload.version}_{timestamp}.xlsx"
        
        return send_file(
            excel_bytes,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@export_api.route('/api/export/<int:upload_id>/preview', methods=['GET'])
def export_preview(upload_id):
    """Get preview of export data"""
    try:
        upload = KPIUpload.query.get_or_404(upload_id)
        kpis = KPI.query.filter_by(upload_id=upload_id).all()
        
        # Group KPIs by category
        kpis_by_category = {}
        for kpi in kpis:
            if kpi.category not in kpis_by_category:
                kpis_by_category[kpi.category] = []
            kpis_by_category[kpi.category].append({
                'health_score_component': kpi.health_score_component,
                'weight': kpi.weight,
                'data': kpi.data,
                'source_review': kpi.source_review,
                'kpi_parameter': kpi.kpi_parameter,
                'impact_level': kpi.impact_level,
                'measurement_frequency': kpi.measurement_frequency
            })
        
        return jsonify({
            'upload_id': upload_id,
            'version': upload.version,
            'uploaded_at': upload.uploaded_at.isoformat(),
            'original_filename': upload.original_filename,
            'total_kpis': len(kpis),
            'categories': kpis_by_category
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@export_api.route('/api/export/all-account-data', methods=['GET'])
def export_all_account_data():
    """Export all account data including KPIs, products, and configuration in Excel format"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        customer_id = get_current_customer_id()
        logger.info(f"Export request received for customer_id: {customer_id}")
        
        # Get all accounts for this customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        logger.info(f"Found {len(accounts)} accounts for customer {customer_id}")
        
        if not accounts:
            logger.warning(f"No accounts found for customer {customer_id}")
            return jsonify({'error': 'No accounts found'}), 404
        
        # Create Excel workbook
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default sheet
        
        # Sheet 1: Accounts Summary (for rehydration)
        accounts_sheet = wb.create_sheet("Accounts Summary")
        accounts_headers = [
            'Account ID', 'Account Name', 'Revenue', 'Industry', 'Region', 
            'Status', 'Health Score', 'Products Used', 'External Account ID', 'Profile Metadata (JSON)'
        ]
        for col, header in enumerate(accounts_headers, 1):
            cell = accounts_sheet.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
        
        # Add account data
        for row, account in enumerate(accounts, 2):
            # Get products for this account
            products = Product.query.filter_by(account_id=account.account_id).all()
            products_list = ', '.join([p.product_name for p in products]) if products else ''
            
            # Get health score
            from models import HealthTrend
            from playbook_recommendations_api import calculate_health_score_proxy
            latest_trend = HealthTrend.query.filter_by(
                account_id=account.account_id,
                customer_id=customer_id
            ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).first()
            
            health_score = None
            if latest_trend and latest_trend.overall_health_score:
                health_score = float(latest_trend.overall_health_score)
            else:
                health_score = calculate_health_score_proxy(account.account_id)
            
            accounts_sheet.cell(row=row, column=1, value=account.account_id)
            accounts_sheet.cell(row=row, column=2, value=account.account_name)
            accounts_sheet.cell(row=row, column=3, value=float(account.revenue) if account.revenue else 0)
            accounts_sheet.cell(row=row, column=4, value=account.industry or '')
            accounts_sheet.cell(row=row, column=5, value=account.region or '')
            accounts_sheet.cell(row=row, column=6, value=account.account_status or '')
            accounts_sheet.cell(row=row, column=7, value=health_score if health_score else '')
            accounts_sheet.cell(row=row, column=8, value=products_list)
            accounts_sheet.cell(row=row, column=9, value=account.external_account_id or '')
            # Export profile_metadata as JSON string for rehydration
            profile_metadata_json = ''
            if account.profile_metadata:
                try:
                    profile_metadata_json = json.dumps(account.profile_metadata) if isinstance(account.profile_metadata, dict) else str(account.profile_metadata)
                except:
                    profile_metadata_json = str(account.profile_metadata)
            accounts_sheet.cell(row=row, column=10, value=profile_metadata_json)
        
        # Auto-adjust column widths for accounts sheet
        for column in accounts_sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            accounts_sheet.column_dimensions[column_letter].width = adjusted_width
        
        # Sheet 2: All KPIs (for rehydration)
        kpis_sheet = wb.create_sheet("All KPIs")
        kpi_headers = [
            'KPI ID', 'Account ID', 'Account Name', 'Product ID', 'Product Name',
            'Category', 'KPI Parameter', 'Data', 'Impact Level', 
            'Measurement Frequency', 'Health Score Component', 'Weight', 'Aggregation Type'
        ]
        for col, header in enumerate(kpi_headers, 1):
            cell = kpis_sheet.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
        
        # Get all KPIs for this customer
        kpis = db.session.query(KPI, Account, Product).join(
            KPIUpload, KPI.upload_id == KPIUpload.upload_id
        ).join(
            Account, KPI.account_id == Account.account_id, isouter=True
        ).outerjoin(
            Product, KPI.product_id == Product.product_id
        ).filter(KPIUpload.customer_id == customer_id).all()
        
        # Add KPI data
        for row, (kpi, account, product) in enumerate(kpis, 2):
            kpis_sheet.cell(row=row, column=1, value=kpi.kpi_id)
            kpis_sheet.cell(row=row, column=2, value=kpi.account_id)
            kpis_sheet.cell(row=row, column=3, value=account.account_name if account else '')
            kpis_sheet.cell(row=row, column=4, value=kpi.product_id if kpi.product_id else '')
            kpis_sheet.cell(row=row, column=5, value=product.product_name if product else '')
            kpis_sheet.cell(row=row, column=6, value=kpi.category or '')
            kpis_sheet.cell(row=row, column=7, value=kpi.kpi_parameter or '')
            kpis_sheet.cell(row=row, column=8, value=kpi.data or '')
            kpis_sheet.cell(row=row, column=9, value=kpi.impact_level or '')
            kpis_sheet.cell(row=row, column=10, value=kpi.measurement_frequency or '')
            kpis_sheet.cell(row=row, column=11, value=kpi.health_score_component or '')
            kpis_sheet.cell(row=row, column=12, value=kpi.weight or '')
            kpis_sheet.cell(row=row, column=13, value=kpi.aggregation_type or '')
        
        # Auto-adjust column widths for KPIs sheet
        for column in kpis_sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            kpis_sheet.column_dimensions[column_letter].width = adjusted_width
        
        # Sheet 3: Products
        products_sheet = wb.create_sheet("Products")
        product_headers = [
            'Product ID', 'Account ID', 'Account Name', 'Product Name', 
            'Product SKU', 'Product Type', 'Revenue', 'Status'
        ]
        for col, header in enumerate(product_headers, 1):
            cell = products_sheet.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
        
        # Get all products for this customer
        all_products = db.session.query(Product, Account).join(
            Account, Product.account_id == Account.account_id
        ).filter(Product.customer_id == customer_id).all()
        
        for row, (product, account) in enumerate(all_products, 2):
            products_sheet.cell(row=row, column=1, value=product.product_id)
            products_sheet.cell(row=row, column=2, value=product.account_id)
            products_sheet.cell(row=row, column=3, value=account.account_name if account else '')
            products_sheet.cell(row=row, column=4, value=product.product_name)
            products_sheet.cell(row=row, column=5, value=product.product_sku or '')
            products_sheet.cell(row=row, column=6, value=product.product_type or '')
            products_sheet.cell(row=row, column=7, value=float(product.revenue) if product.revenue else 0)
            products_sheet.cell(row=row, column=8, value=product.status or '')
        
        # Auto-adjust column widths for products sheet
        for column in products_sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            products_sheet.column_dimensions[column_letter].width = adjusted_width
        
        # Sheet 4: Export Metadata
        metadata_sheet = wb.create_sheet("Export Metadata")
        metadata_sheet['A1'] = "KPI Dashboard - All Account Data Export"
        metadata_sheet['A1'].font = Font(bold=True, size=14)
        metadata_sheet['A2'] = f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        metadata_sheet['A3'] = f"Customer ID: {customer_id}"
        metadata_sheet['A4'] = f"Total Accounts: {len(accounts)}"
        metadata_sheet['A5'] = f"Total KPIs: {len(kpis)}"
        metadata_sheet['A6'] = f"Total Products: {len(all_products)}"
        
        for row in range(1, 7):
            metadata_sheet[f'A{row}'].font = Font(bold=True)
        
        # Save to bytes
        excel_bytes = io.BytesIO()
        wb.save(excel_bytes)
        excel_bytes.seek(0)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Account_Data_Export_{timestamp}.xlsx"
        
        # Return file with proper headers for download
        logger.info(f"Excel file generated successfully: {filename}, size: {excel_bytes.tell()} bytes")
        
        response = send_file(
            excel_bytes,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Add CORS headers if needed
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"Sending Excel file response for customer {customer_id}")
        return response
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Export failed for customer {customer_id}: {str(e)}\n{error_trace}")
        traceback.print_exc()
        return jsonify({'error': f'Export failed: {str(e)}'}), 500 