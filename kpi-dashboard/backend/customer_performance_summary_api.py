#!/usr/bin/env python3
"""
Customer Performance Summary API
Provides summary of accounts needing attention with focus areas
"""

from flask import Blueprint, jsonify
from auth_middleware import get_current_customer_id
from models import db, Account, HealthTrend, PlaybookExecution, KPI
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

customer_perf_summary_api = Blueprint('customer_perf_summary_api', __name__)

@customer_perf_summary_api.route('/api/customer-performance/summary', methods=['GET'])
def get_performance_summary():
    """
    Get summary of top 3 accounts needing attention
    - Last 3 months data
    - Category health scores
    - Focus areas (worst performing categories)
    - Active playbooks count
    """
    try:
        customer_id = get_current_customer_id()
        
        if not customer_id:
            return jsonify({
                'status': 'error',
                'error': 'Authentication required',
                'message': 'Please log in to access this resource'
            }), 401
        
        # Get date 3 months ago
        three_months_ago = datetime.utcnow() - timedelta(days=90)
        
        # Get all accounts with their latest health trends
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        if not accounts:
            # Return empty summary if no accounts
            return jsonify({
                'status': 'success',
                'summary': {
                    'total_accounts': 0,
                    'critical_accounts': 0,
                    'at_risk_accounts': 0,
                    'healthy_accounts': 0,
                    'average_health_score': 0,
                    'company_avg_revenue_growth': 0
                },
                'accounts_needing_attention': [],
                'healthy_declining_revenue': [],
                'timeframe': 'Last 6 months'
            })
        
        account_summaries = []
        
        for account in accounts:
            # Get category-level scores from KPIs
            category_scores = calculate_category_scores(account.account_id, customer_id)
            
            if not category_scores:
                continue  # Skip accounts with no KPIs
            
            # Calculate overall health score from category scores
            overall_health_score = sum(category_scores.values()) / len(category_scores)
            
            # Calculate revenue growth trend (last 6 months)
            revenue_growth_pct = calculate_revenue_growth(account.account_id)
            
            # Find worst performing categories (focus areas)
            focus_areas = sorted(
                [(cat, score) for cat, score in category_scores.items()],
                key=lambda x: x[1]
            )[:2]  # Top 2 worst categories
            
            # Count active playbooks (started in last 3 months)
            # Use try/except to handle missing columns gracefully
            try:
                active_playbooks = PlaybookExecution.query.filter_by(
                    account_id=account.account_id,
                    customer_id=customer_id
                ).filter(
                    PlaybookExecution.started_at >= three_months_ago
                ).count()
            except Exception as e:
                # If column doesn't exist, just count all playbooks for this account
                print(f"Warning: Could not query playbook_executions with started_at filter: {e}")
                active_playbooks = PlaybookExecution.query.filter_by(
                    account_id=account.account_id,
                    customer_id=customer_id
                ).count()
            
            account_summaries.append({
                'account_id': account.account_id,
                'account_name': account.account_name,
                'revenue': float(account.revenue) if account.revenue else 0,
                'industry': account.industry,
                'region': account.region,
                'overall_health_score': overall_health_score,
                'category_scores': category_scores,
                'focus_areas': [{'category': cat, 'score': score} for cat, score in focus_areas],
                'active_playbooks_count': active_playbooks,
                'revenue_growth_pct': revenue_growth_pct
            })
        
        # Calculate overall summary stats with better thresholds
        total_accounts = len(accounts)
        
        # Use stricter thresholds for enterprise customers
        critical_accounts = len([a for a in account_summaries if a['overall_health_score'] < 70])
        at_risk_accounts = len([a for a in account_summaries if 70 <= a['overall_health_score'] < 80])
        healthy_accounts = len([a for a in account_summaries if a['overall_health_score'] >= 80])
        
        # Sort by overall health score (ascending) to get accounts needing most attention
        account_summaries.sort(key=lambda x: x['overall_health_score'])
        
        # Get accounts that actually need attention (score < 80) OR bottom 3 if all are healthy
        accounts_needing_attention = [a for a in account_summaries if a['overall_health_score'] < 80]
        
        if len(accounts_needing_attention) < 3:
            # If less than 3 need attention, show bottom 3 performers anyway
            accounts_needing_attention = account_summaries[:3]
        else:
            # Show worst performers (up to 5)
            accounts_needing_attention = accounts_needing_attention[:5]
        
        # Find healthy accounts (≥80) with declining revenue (negative growth)
        healthy_declining_revenue = [
            a for a in account_summaries 
            if a['overall_health_score'] >= 80 and a['revenue_growth_pct'] < 0
        ]
        
        # Sort by revenue decline (most negative first)
        healthy_declining_revenue.sort(key=lambda x: x['revenue_growth_pct'])
        
        # Limit to 5 accounts
        healthy_declining_revenue = healthy_declining_revenue[:5]
        
        # Calculate company average revenue growth
        all_revenue_growth = [a['revenue_growth_pct'] for a in account_summaries if a['revenue_growth_pct'] is not None]
        company_avg_revenue_growth = sum(all_revenue_growth) / len(all_revenue_growth) if all_revenue_growth else 0
        
        return jsonify({
            'status': 'success',
            'summary': {
                'total_accounts': total_accounts,
                'critical_accounts': critical_accounts,
                'at_risk_accounts': at_risk_accounts,
                'healthy_accounts': healthy_accounts,
                'average_health_score': sum(a['overall_health_score'] for a in account_summaries) / max(len(account_summaries), 1),
                'company_avg_revenue_growth': round(company_avg_revenue_growth, 1)
            },
            'accounts_needing_attention': accounts_needing_attention,
            'healthy_declining_revenue': healthy_declining_revenue,
            'timeframe': 'Last 6 months'
        })
    except Exception as e:
        import traceback
        print(f"Error in get_performance_summary: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Failed to fetch performance summary'
        }), 500

def calculate_revenue_growth(account_id, customer_id=None):
    """
    Calculate revenue growth % for an account based on Revenue Growth KPI trend
    Compares recent 3 months vs previous 3 months
    """
    # Get Revenue Growth KPI data for this account (account-level only)
    from kpi_queries import get_account_level_kpis
    if customer_id is None:
        from auth_middleware import get_current_customer_id
        customer_id = get_current_customer_id()
    account_kpis = get_account_level_kpis(account_id, customer_id)
    revenue_kpis = [kpi for kpi in account_kpis if kpi.kpi_parameter == 'Revenue Growth']
    
    if not revenue_kpis or len(revenue_kpis) < 2:
        return 0.0  # Not enough data
    
    # Parse and sort by month (stored in source_review as "month/year")
    revenue_data = []
    for kpi in revenue_kpis:
        try:
            # Extract numeric value from "25.7%" format
            val_str = str(kpi.data).replace('%', '').strip()
            value = float(val_str)
            revenue_data.append(value)
        except:
            continue
    
    if len(revenue_data) < 2:
        return 0.0
    
    # Calculate trend: compare recent half vs earlier half
    mid_point = len(revenue_data) // 2
    recent_avg = statistics.mean(revenue_data[mid_point:])
    earlier_avg = statistics.mean(revenue_data[:mid_point])
    
    if earlier_avg == 0:
        return 0.0
    
    # Calculate % change
    growth_pct = ((recent_avg - earlier_avg) / earlier_avg) * 100
    
    return round(growth_pct, 1)

def calculate_category_scores(account_id, customer_id):
    """Calculate category-level health scores for an account"""
    
    # Get latest KPIs for this account (account-level only, excludes product KPIs)
    from kpi_queries import get_account_level_kpis
    kpis = get_account_level_kpis(account_id, customer_id)
    
    if not kpis:
        return {}
    
    # Group KPIs by category
    category_groups = defaultdict(list)
    for kpi in kpis:
        category_groups[kpi.category].append(kpi)
    
    # Calculate average score per category (simple approach)
    category_scores = {}
    for category, kpi_list in category_groups.items():
        # For simplicity, assume scores between 50-90 based on data quality
        # In production, this would use actual health scoring logic
        scores = []
        for kpi in kpi_list:
            try:
                # Try to extract numeric value
                val_str = str(kpi.data).replace('%', '').replace('$', '').replace(',', '').strip()
                # Handle units like "10 days", "25.7%", "$50,000"
                parts = val_str.split()
                if parts:
                    val = float(parts[0])  # Get first number
                    # Normalize to 0-100 scale (simplified - in production use reference ranges)
                    # For now, just use the value as-is if it's already in 0-100 range
                    if 0 <= val <= 100:
                        normalized = val
                    else:
                        # Scale down large values
                        normalized = min(100, max(0, val / 10))
                    scores.append(normalized)
                else:
                    scores.append(65)  # Default if empty
            except Exception as e:
                scores.append(65)  # Default mid-range score
        
        category_scores[category] = sum(scores) / len(scores) if scores else 65
    
    return category_scores

