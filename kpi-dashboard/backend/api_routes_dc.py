"""
Data Center API Routes
DC-specific API endpoints for Data Center vertical
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id
from extensions import db
from models import Account, KPI
from kpi_definitions_dc import DC_KPIS, get_kpi, get_kpis_by_pillar
from health_calculator_dc import calculate_dc_health_score
from alert_engine_dc import DCAlertEngine
from recommendation_engine_dc import DCRecommendationEngine

api_routes_dc = Blueprint('api_routes_dc', __name__)

@api_routes_dc.route('/api/dc/kpis', methods=['GET'])
def get_dc_kpis():
    """Get all DC KPI definitions"""
    try:
        return jsonify({
            "kpis": DC_KPIS,
            "count": len(DC_KPIS),
            "pillars": list(set(kpi.get("pillar") for kpi in DC_KPIS.values()))
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_routes_dc.route('/api/dc/kpis/<pillar>', methods=['GET'])
def get_dc_kpis_by_pillar(pillar):
    """Get DC KPIs by pillar"""
    try:
        pillar_kpis = get_kpis_by_pillar(pillar)
        return jsonify({
            "pillar": pillar,
            "kpis": pillar_kpis,
            "count": len(pillar_kpis)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_routes_dc.route('/api/dc/health-score/<int:account_id>', methods=['GET'])
def get_dc_health_score(account_id):
    """Calculate DC health score for an account
    
    Query parameters:
    - month: Integer (1-7) to filter by specific month, or 'aggregate' for average across all months
    """
    import re
    from models import KPIUpload
    
    customer_id = get_current_customer_id()
    
    if not customer_id:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        # Get month parameter
        month_param = request.args.get('month', 'aggregate')
        is_aggregate = month_param.lower() == 'aggregate'
        selected_month = None if is_aggregate else int(month_param)
        
        # Get account KPIs
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).first()
        
        if not account:
            return jsonify({"error": "Account not found"}), 404
        
        # Get all KPIs with upload information
        kpis_query = db.session.query(KPI, KPIUpload).join(
            KPIUpload, KPI.upload_id == KPIUpload.upload_id
        ).filter(
            KPI.account_id == account_id,
            KPIUpload.customer_id == customer_id
        )
        
        kpis_with_uploads = kpis_query.all()
        
        if not kpis_with_uploads:
            return jsonify({
                "account_id": account_id,
                "account_name": account.account_name,
                "overall_score": 0,
                "health_status": "unknown",
                "category_scores": {},
                "kpi_count": 0,
                "month": month_param
            }), 200
        
        # Helper function to extract month from filename
        def get_month_from_filename(filename):
            if not filename:
                return None
            match = re.search(r'Month[_\s](\d+)', filename, re.IGNORECASE)
            return int(match.group(1)) if match else None
        
        # Filter by month if not aggregate
        if not is_aggregate:
            filtered_kpis = [
                (kpi, upload) for kpi, upload in kpis_with_uploads
                if get_month_from_filename(upload.original_filename) == selected_month
            ]
        else:
            filtered_kpis = kpis_with_uploads
        
        if not filtered_kpis:
            return jsonify({
                "account_id": account_id,
                "account_name": account.account_name,
                "overall_score": 0,
                "health_status": "unknown",
                "category_scores": {},
                "kpi_count": 0,
                "month": month_param,
                "message": f"No KPIs found for month {selected_month}" if not is_aggregate else "No KPIs found"
            }), 200
        
        # Group KPIs by parameter for aggregate calculation
        if is_aggregate:
            # Group by kpi_parameter and calculate average
            kpi_groups = {}
            for kpi, upload in filtered_kpis:
                param = kpi.kpi_parameter
                if param not in kpi_groups:
                    kpi_groups[param] = []
                
                # Extract numeric value
                value_str = str(kpi.data or '0').replace("%", "").replace("$", "").replace(",", "").strip()
                try:
                    numeric_value = float(value_str)
                    kpi_groups[param].append(numeric_value)
                except (ValueError, TypeError):
                    continue
            
            # Create aggregated KPI data (average values)
            kpi_data = []
            for param, values in kpi_groups.items():
                if values:
                    avg_value = sum(values) / len(values)
                    # Format based on original data format
                    original_data = filtered_kpis[0][0].data if filtered_kpis else '0'
                    if '%' in str(original_data):
                        formatted_value = f"{avg_value:.2f}%"
                    elif '$' in str(original_data):
                        formatted_value = f"${avg_value:.2f}"
                    else:
                        formatted_value = f"{avg_value:.2f}"
                    
                    kpi_data.append({
                        "kpi_id": param,
                        "kpi_parameter": param,
                        "data": formatted_value,
                        "value": avg_value
                    })
        else:
            # Use KPIs from selected month
            kpi_data = [{
                "kpi_id": kpi.kpi_parameter,
                "kpi_parameter": kpi.kpi_parameter,
                "data": kpi.data,
                "value": kpi.data
            } for kpi, upload in filtered_kpis]
        
        # Calculate health score
        health_data = calculate_dc_health_score(kpi_data)
        
        return jsonify({
            "account_id": account_id,
            "account_name": account.account_name,
            "month": month_param,
            "is_aggregate": is_aggregate,
            "kpi_count": len(kpi_data),
            **health_data
        }), 200
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@api_routes_dc.route('/api/dc/alerts/<int:account_id>', methods=['GET'])
def get_dc_alerts(account_id):
    """Get alerts for a DC account"""
    customer_id = get_current_customer_id()
    
    if not customer_id:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).first()
        
        if not account:
            return jsonify({"error": "Account not found"}), 404
        
        kpis = KPI.query.filter_by(account_id=account_id).all()
        alerts = []
        
        for kpi in kpis:
            try:
                value = float(str(kpi.data).replace("%", "").replace("$", "").replace(",", ""))
            except (ValueError, TypeError):
                continue
            
            kpi_alerts = DCAlertEngine.check_kpi_alerts(
                kpi.kpi_parameter,
                value,
                account_id,
                account.account_name
            )
            alerts.extend(kpi_alerts)
        
        aggregated = DCAlertEngine.aggregate_alerts(alerts)
        
        return jsonify({
            "account_id": account_id,
            "alerts": alerts,
            "aggregated": aggregated
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_routes_dc.route('/api/dc/recommendations/<int:account_id>', methods=['GET'])
def get_dc_recommendations(account_id):
    """Get recommendations for a DC account"""
    customer_id = get_current_customer_id()
    
    if not customer_id:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).first()
        
        if not account:
            return jsonify({"error": "Account not found"}), 404
        
        kpis = KPI.query.filter_by(account_id=account_id).all()
        kpi_data = [{
            "kpi_id": kpi.kpi_parameter,
            "kpi_parameter": kpi.kpi_parameter,
            "data": kpi.data,
            "value": kpi.data
        } for kpi in kpis]
        
        # Get health score
        health_data = calculate_dc_health_score(kpi_data)
        
        # Generate recommendations
        recommendations = DCRecommendationEngine.generate_recommendations(
            kpi_data,
            health_data.get("overall_score", 0)
        )
        
        prioritized = DCRecommendationEngine.prioritize_recommendations(recommendations)
        
        return jsonify({
            "account_id": account_id,
            "recommendations": prioritized,
            "count": len(prioritized)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

