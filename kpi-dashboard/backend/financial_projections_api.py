#!/usr/bin/env python3
"""
Financial Projections API
Handles financial projections tied to KPI changes and trends
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from datetime import datetime, timedelta
from decimal import Decimal
import json

from extensions import db
from models import Account, KPI, KPITimeSeries, HealthTrend

financial_projections_api = Blueprint('financial_projections_api', __name__)

# Financial impact coefficients for different KPI categories
FINANCIAL_IMPACT_COEFFICIENTS = {
    'Product Usage KPI': {
        'revenue_impact': 0.15,  # 15% revenue impact per 10-point KPI improvement
        'cost_impact': -0.05,    # 5% cost reduction per 10-point improvement
        'retention_impact': 0.08  # 8% retention improvement per 10-point improvement
    },
    'Support KPI': {
        'revenue_impact': 0.08,
        'cost_impact': -0.12,    # Higher cost impact for support improvements
        'retention_impact': 0.12
    },
    'Customer Sentiment KPI': {
        'revenue_impact': 0.20,  # Highest revenue impact
        'cost_impact': -0.03,
        'retention_impact': 0.15
    },
    'Business Outcomes KPI': {
        'revenue_impact': 0.25,  # Direct business impact
        'cost_impact': -0.08,
        'retention_impact': 0.10
    },
    'Relationship Strength KPI': {
        'revenue_impact': 0.18,
        'cost_impact': -0.04,
        'retention_impact': 0.20  # Highest retention impact
    }
}

def calculate_financial_impact(kpi_category, current_score, projected_score, account_revenue):
    """
    Calculate financial impact based on KPI score changes
    
    Args:
        kpi_category: Category of the KPI
        current_score: Current KPI health score (0-100)
        projected_score: Projected KPI health score (0-100)
        account_revenue: Account's annual revenue
    
    Returns:
        dict: Financial impact projections
    """
    if kpi_category not in FINANCIAL_IMPACT_COEFFICIENTS:
        return {
            'revenue_impact': 0,
            'cost_savings': 0,
            'retention_improvement': 0,
            'total_impact': 0
        }
    
    # Calculate score improvement
    score_change = projected_score - current_score
    improvement_factor = score_change / 10  # Per 10-point improvement
    
    coefficients = FINANCIAL_IMPACT_COEFFICIENTS[kpi_category]
    
    # Calculate impacts
    revenue_impact = account_revenue * coefficients['revenue_impact'] * improvement_factor
    cost_savings = account_revenue * abs(coefficients['cost_impact']) * improvement_factor
    retention_improvement = coefficients['retention_impact'] * improvement_factor * 100
    
    total_impact = revenue_impact + cost_savings
    
    return {
        'revenue_impact': float(revenue_impact),
        'cost_savings': float(cost_savings),
        'retention_improvement': float(retention_improvement),
        'total_impact': float(total_impact),
        'score_change': float(score_change),
        'improvement_factor': float(improvement_factor)
    }

@financial_projections_api.route('/api/financial-projections/account/<int:account_id>', methods=['GET'])
def get_account_financial_projections(account_id):
    """Get financial projections for a specific account based on KPI trends"""
    customer_id = get_current_customer_id()
    
    if not customer_id:
        return jsonify({'error': 'Authentication required (handled by middleware)'}), 400
    
    customer_id = int(customer_id)
    months = request.args.get('months', 12, type=int)
    
    try:
        # Get account details
        account = Account.query.filter_by(
            account_id=account_id, 
            customer_id=customer_id
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Get recent health trends using the time series API data structure
        recent_trends = HealthTrend.query.filter_by(
            account_id=account_id
        ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).limit(months).all()
        
        if len(recent_trends) < 2:
            return jsonify({
                'account_id': account_id,
                'account_name': account.account_name,
                'revenue': float(account.revenue) if account.revenue else 0,
                'projections': [],
                'message': 'Insufficient trend data for projections'
            })
        
        # Calculate trend-based projections
        projections = []
        
        # Get the most recent trend as baseline
        latest_trend = recent_trends[0]
        print(f"DEBUG: Latest trend attributes: {dir(latest_trend)}")
        print(f"DEBUG: Latest trend overall_health_score: {latest_trend.overall_health_score}")
        
        baseline_scores = {
            'product_usage': float(latest_trend.product_usage_score) if latest_trend.product_usage_score else 0,
            'support': float(latest_trend.support_score) if latest_trend.support_score else 0,
            'customer_sentiment': float(latest_trend.customer_sentiment_score) if latest_trend.customer_sentiment_score else 0,
            'business_outcomes': float(latest_trend.business_outcomes_score) if latest_trend.business_outcomes_score else 0,
            'relationship_strength': float(latest_trend.relationship_strength_score) if latest_trend.relationship_strength_score else 0,
            'overall': float(latest_trend.overall_health_score) if latest_trend.overall_health_score else 0
        }
        
        # Calculate 3-month, 6-month, and 12-month projections
        for months_ahead in [3, 6, 12]:
            projected_month = datetime.now() + timedelta(days=months_ahead * 30)
            
            # Calculate projected scores based on trends
            projected_scores = {}
            total_financial_impact = 0
            
            categories = [
                ('Product Usage KPI', 'product_usage'),
                ('Support KPI', 'support'),
                ('Customer Sentiment KPI', 'customer_sentiment'),
                ('Business Outcomes KPI', 'business_outcomes'),
                ('Relationship Strength KPI', 'relationship_strength')
            ]
            
            for category_name, score_key in categories:
                current_score = baseline_scores[score_key]
                
                # Simple linear projection based on recent trend
                # In a real system, this would use more sophisticated forecasting
                try:
                    trend_data = [getattr(trend, f"{score_key}_score") for trend in recent_trends[:3]]
                except AttributeError as e:
                    print(f"Error accessing {score_key}_score: {e}")
                    trend_data = [0, 0, 0]
                if len(trend_data) >= 2:
                    trend_slope = (trend_data[0] - trend_data[-1]) / len(trend_data)
                    projected_score = max(0, min(100, current_score + (trend_slope * months_ahead)))
                else:
                    projected_score = current_score
                
                projected_scores[score_key] = projected_score
                
                # Calculate financial impact
                impact = calculate_financial_impact(
                    category_name, 
                    current_score, 
                    projected_score, 
                    float(account.revenue) if account.revenue else 1000000
                )
                
                total_financial_impact += impact['total_impact']
            
            # Calculate overall projected score
            category_weights = {
                'product_usage': 0.3,
                'support': 0.2,
                'customer_sentiment': 0.2,
                'business_outcomes': 0.15,
                'relationship_strength': 0.15
            }
            
            overall_projected = sum(
                projected_scores[key] * weight 
                for key, weight in category_weights.items()
            )
            
            projections.append({
                'months_ahead': months_ahead,
                'projection_date': projected_month.strftime('%Y-%m'),
                'projected_scores': projected_scores,
                'overall_projected_score': float(overall_projected),
                'financial_impact': {
                    'total_impact': float(total_financial_impact),
                    'revenue_impact': float(total_financial_impact * 0.6),  # 60% revenue, 40% cost savings
                    'cost_savings': float(total_financial_impact * 0.4),
                    'roi_percentage': float((total_financial_impact / float(account.revenue)) * 100) if account.revenue else 0
                },
                'confidence_level': 'medium' if months_ahead <= 6 else 'low'
            })
        
        return jsonify({
            'account_id': account_id,
            'account_name': account.account_name,
            'revenue': float(account.revenue) if account.revenue else 0,
            'baseline_scores': baseline_scores,
            'projections': projections,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        import traceback
        print(f"Error generating financial projections: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@financial_projections_api.route('/api/financial-projections/corporate', methods=['GET'])
def get_corporate_financial_projections():
    """Get corporate-level financial projections"""
    customer_id = get_current_customer_id()
    
    if not customer_id:
        return jsonify({'error': 'Authentication required (handled by middleware)'}), 400
    
    customer_id = int(customer_id)
    months = request.args.get('months', 12, type=int)
    
    try:
        # Get all accounts for customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        if not accounts:
            return jsonify({'error': 'No accounts found'}), 404
        
        total_revenue = sum(float(account.revenue) for account in accounts if account.revenue)
        corporate_projections = []
        
        for months_ahead in [3, 6, 12]:
            total_financial_impact = 0
            account_projections = []
            
            for account in accounts:
                # Get account-specific projection
                account_data = get_account_financial_projections().get_json()
                if 'projections' in account_data:
                    account_proj = next(
                        (p for p in account_data['projections'] if p['months_ahead'] == months_ahead),
                        None
                    )
                    if account_proj:
                        total_financial_impact += account_proj['financial_impact']['total_impact']
                        account_projections.append({
                            'account_id': account.account_id,
                            'account_name': account.account_name,
                            'financial_impact': account_proj['financial_impact']
                        })
            
            projected_month = datetime.now() + timedelta(days=months_ahead * 30)
            
            corporate_projections.append({
                'months_ahead': months_ahead,
                'projection_date': projected_month.strftime('%Y-%m'),
                'total_financial_impact': float(total_financial_impact),
                'revenue_impact': float(total_financial_impact * 0.6),
                'cost_savings': float(total_financial_impact * 0.4),
                'roi_percentage': float((total_financial_impact / total_revenue) * 100) if total_revenue > 0 else 0,
                'accounts_count': len(account_projections),
                'account_projections': account_projections,
                'confidence_level': 'medium' if months_ahead <= 6 else 'low'
            })
        
        return jsonify({
            'customer_id': customer_id,
            'total_revenue': float(total_revenue),
            'total_accounts': len(accounts),
            'corporate_projections': corporate_projections,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error generating corporate financial projections: {e}")
        return jsonify({'error': str(e)}), 500

@financial_projections_api.route('/api/financial-projections/kpi-impact/<kpi_name>', methods=['GET'])
def get_kpi_financial_impact(kpi_name):
    """Get financial impact analysis for a specific KPI across all accounts"""
    customer_id = get_current_customer_id()
    
    if not customer_id:
        return jsonify({'error': 'Authentication required (handled by middleware)'}), 400
    
    customer_id = int(customer_id)
    
    try:
        # Get KPI data across all accounts
        kpis = db.session.query(KPI).join(Account).filter(
            KPI.kpi_parameter == kpi_name,
            Account.customer_id == customer_id
        ).all()
        
        if not kpis:
            return jsonify({'error': f'KPI "{kpi_name}" not found'}), 404
        
        impact_analysis = []
        total_potential_impact = 0
        
        for kpi in kpis:
            account = Account.query.get(kpi.account_id)
            if not account:
                continue
            
            # Get current and historical scores
            current_score = 50  # Default, would be calculated from current data
            target_score = 80   # Target improvement
            
            impact = calculate_financial_impact(
                kpi.category,
                current_score,
                target_score,
                float(account.revenue) if account.revenue else 1000000
            )
            
            total_potential_impact += impact['total_impact']
            
            impact_analysis.append({
                'account_id': account.account_id,
                'account_name': account.account_name,
                'current_score': current_score,
                'target_score': target_score,
                'financial_impact': impact,
                'kpi_category': kpi.category
            })
        
        return jsonify({
            'kpi_name': kpi_name,
            'customer_id': customer_id,
            'total_accounts': len(impact_analysis),
            'total_potential_impact': float(total_potential_impact),
            'impact_analysis': impact_analysis,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error analyzing KPI financial impact: {e}")
        return jsonify({'error': str(e)}), 500
