from flask import Blueprint, request, jsonify, send_file
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import KPI, KPIUpload
import pandas as pd
import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

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