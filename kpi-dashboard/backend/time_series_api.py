#!/usr/bin/env python3
"""
Time Series API for retrieving KPI trends and health score history.
"""

from flask import Blueprint, request, jsonify
from health_score_storage import HealthScoreStorageService
from datetime import datetime

time_series_api = Blueprint('time_series_api', __name__)

@time_series_api.route('/api/time-series/kpi-trends', methods=['GET'])
def get_kpi_trends():
    """Get historical trends for a specific KPI."""
    try:
        customer_id = request.headers.get('X-Customer-ID')
        kpi_name = request.args.get('kpi_name')
        account_id = request.args.get('account_id', type=int)
        months = request.args.get('months', 12, type=int)
        
        if not customer_id:
            return jsonify({'error': 'Missing X-Customer-ID header'}), 400
        if not kpi_name:
            return jsonify({'error': 'Missing kpi_name parameter'}), 400
        if not account_id:
            return jsonify({'error': 'Missing account_id parameter'}), 400
        
        storage_service = HealthScoreStorageService()
        trends = storage_service.get_kpi_trends(kpi_name, account_id, months)
        
        return jsonify({
            'kpi_name': kpi_name,
            'account_id': account_id,
            'trends': trends,
            'total_months': len(trends)
        })
        
    except Exception as e:
        print(f"Error fetching KPI trends: {e}")
        return jsonify({'error': 'Failed to fetch KPI trends'}), 500

@time_series_api.route('/api/time-series/account-health', methods=['GET'])
def get_account_health_trends():
    """Get historical health score trends for an account."""
    try:
        customer_id = request.headers.get('X-Customer-ID')
        account_id = request.args.get('account_id', type=int)
        months = request.args.get('months', 12, type=int)
        
        if not customer_id:
            return jsonify({'error': 'Missing X-Customer-ID header'}), 400
        if not account_id:
            return jsonify({'error': 'Missing account_id parameter'}), 400
        
        storage_service = HealthScoreStorageService()
        trends = storage_service.get_account_health_trends(account_id, months)
        
        return jsonify({
            'account_id': account_id,
            'health_trends': trends,
            'total_months': len(trends)
        })
        
    except Exception as e:
        print(f"Error fetching account health trends: {e}")
        return jsonify({'error': 'Failed to fetch account health trends'}), 500

@time_series_api.route('/api/time-series/generate-historical', methods=['POST'])
def generate_historical_data():
    """Generate historical KPI and health score data for testing."""
    try:
        customer_id = request.headers.get('X-Customer-ID')
        months_back = request.json.get('months_back', 12) if request.json else 12
        
        if not customer_id:
            return jsonify({'error': 'Missing X-Customer-ID header'}), 400
        
        storage_service = HealthScoreStorageService()
        
        # Generate historical data for the last N months
        current_date = datetime.now()
        generated_data = {
            'health_scores': 0,
            'kpi_time_series': 0,
            'months_generated': []
        }
        
        for month_offset in range(months_back, 0, -1):
            target_date = current_date.replace(day=1) - datetime.timedelta(days=30 * month_offset)
            month = target_date.month
            year = target_date.year
            
            # Store health scores for this month
            health_count = storage_service.store_health_scores_after_rollup(
                {}, customer_id, month, year
            )
            
            # Store KPI time series for this month
            kpi_count = storage_service.store_monthly_kpi_data(customer_id, month, year)
            
            generated_data['health_scores'] += health_count
            generated_data['kpi_time_series'] += kpi_count
            generated_data['months_generated'].append(f"{year}-{month:02d}")
        
        return jsonify({
            'message': 'Historical data generated successfully',
            'generated_data': generated_data
        })
        
    except Exception as e:
        print(f"Error generating historical data: {e}")
        return jsonify({'error': 'Failed to generate historical data'}), 500

@time_series_api.route('/api/time-series/stats', methods=['GET'])
def get_time_series_stats():
    """Get statistics about stored time series data."""
    try:
        customer_id = request.headers.get('X-Customer-ID')
        
        if not customer_id:
            return jsonify({'error': 'Missing X-Customer-ID header'}), 400
        
        from models import HealthTrend, KPITimeSeries, Account
        
        # Get account count
        account_count = Account.query.filter_by(customer_id=customer_id).count()
        
        # Get health trend stats
        health_trend_count = HealthTrend.query.join(Account).filter(
            Account.customer_id == customer_id
        ).count()
        
        # Get KPI time series stats
        kpi_time_series_count = KPITimeSeries.query.join(Account).filter(
            Account.customer_id == customer_id
        ).count()
        
        # Get date range
        oldest_health = HealthTrend.query.join(Account).filter(
            Account.customer_id == customer_id
        ).order_by(HealthTrend.year, HealthTrend.month).first()
        
        newest_health = HealthTrend.query.join(Account).filter(
            Account.customer_id == customer_id
        ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).first()
        
        date_range = None
        if oldest_health and newest_health:
            date_range = {
                'oldest': f"{oldest_health.year}-{oldest_health.month:02d}",
                'newest': f"{newest_health.year}-{newest_health.month:02d}"
            }
        
        return jsonify({
            'customer_id': customer_id,
            'account_count': account_count,
            'health_trend_records': health_trend_count,
            'kpi_time_series_records': kpi_time_series_count,
            'date_range': date_range,
            'total_data_points': health_trend_count + kpi_time_series_count
        })
        
    except Exception as e:
        print(f"Error fetching time series stats: {e}")
        return jsonify({'error': 'Failed to fetch time series stats'}), 500
