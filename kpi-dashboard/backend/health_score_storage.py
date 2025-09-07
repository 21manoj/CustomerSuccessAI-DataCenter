#!/usr/bin/env python3
"""
Health Score Storage Service for persisting calculated health scores and KPI time series data.
"""

from datetime import datetime
from extensions import db
from models import HealthTrend, KPITimeSeries, Account, KPI
from health_score_engine import HealthScoreEngine

class HealthScoreStorageService:
    """Service for storing health scores and KPI time series data."""
    
    def __init__(self):
        self.health_engine = HealthScoreEngine()
    
    def store_health_scores_after_rollup(self, health_analysis, customer_id, month=None, year=None):
        """
        Store calculated health scores in health_trends table after rollup.
        
        Args:
            health_analysis: Dictionary containing health analysis results
            customer_id: Customer ID
            month: Month (1-12), defaults to current month
            year: Year, defaults to current year
        """
        if month is None:
            month = datetime.now().month
        if year is None:
            year = datetime.now().year
        
        try:
            # Get all accounts for this customer
            accounts = Account.query.filter_by(customer_id=customer_id).all()
            
            stored_count = 0
            for account in accounts:
                # Calculate health scores for this account
                account_health = self._calculate_account_health_scores(account, customer_id)
                
                # Check if trend already exists for this month
                existing_trend = HealthTrend.query.filter_by(
                    account_id=account.account_id,
                    month=month,
                    year=year
                ).first()
                
                if existing_trend:
                    # Update existing trend
                    existing_trend.overall_health_score = account_health['overall']
                    existing_trend.product_usage_score = account_health['product_usage']
                    existing_trend.support_score = account_health['support']
                    existing_trend.customer_sentiment_score = account_health['customer_sentiment']
                    existing_trend.business_outcomes_score = account_health['business_outcomes']
                    existing_trend.relationship_strength_score = account_health['relationship_strength']
                    existing_trend.updated_at = datetime.utcnow()
                    trend = existing_trend
                else:
                    # Create new trend
                    trend = HealthTrend(
                        account_id=account.account_id,
                        customer_id=customer_id,
                        month=month,
                        year=year,
                        overall_health_score=account_health['overall'],
                        product_usage_score=account_health['product_usage'],
                        support_score=account_health['support'],
                        customer_sentiment_score=account_health['customer_sentiment'],
                        business_outcomes_score=account_health['business_outcomes'],
                        relationship_strength_score=account_health['relationship_strength'],
                        total_kpis=account_health['total_kpis'],
                        valid_kpis=account_health['valid_kpis']
                    )
                    db.session.add(trend)
                
                stored_count += 1
            
            db.session.commit()
            print(f"✅ Stored health scores for {stored_count} accounts")
            return stored_count
            
        except Exception as e:
            print(f"❌ Error storing health scores: {e}")
            db.session.rollback()
            raise e
    
    def store_monthly_kpi_data(self, customer_id, month=None, year=None):
        """
        Store monthly KPI data for all KPIs of a customer.
        
        Args:
            customer_id: Customer ID
            month: Month (1-12), defaults to current month
            year: Year, defaults to current year
        """
        if month is None:
            month = datetime.now().month
        if year is None:
            year = datetime.now().year
        
        try:
            # Get all KPIs for this customer
            kpis = db.session.query(KPI).join(Account).filter(
                Account.customer_id == customer_id
            ).all()
            
            stored_count = 0
            for kpi in kpis:
                # Parse KPI value
                parsed_value = self.health_engine.parse_kpi_value(kpi.data, kpi.kpi_parameter)
                
                if parsed_value is not None:
                    # Calculate health status and score
                    health_info = self.health_engine.calculate_health_status(parsed_value, kpi.kpi_parameter)
                    
                    # Check if time series record already exists
                    existing_record = KPITimeSeries.query.filter_by(
                        kpi_id=kpi.kpi_id,
                        month=month,
                        year=year
                    ).first()
                    
                    if existing_record:
                        # Update existing record
                        existing_record.value = parsed_value
                        existing_record.health_status = health_info['status']
                        existing_record.health_score = health_info['score']
                        existing_record.updated_at = datetime.utcnow()
                    else:
                        # Create new record
                        kpi_trend = KPITimeSeries(
                            kpi_id=kpi.kpi_id,
                            account_id=kpi.account_id,
                            customer_id=customer_id,
                            month=month,
                            year=year,
                            value=parsed_value,
                            health_status=health_info['status'],
                            health_score=health_info['score']
                        )
                        db.session.add(kpi_trend)
                    
                    stored_count += 1
            
            db.session.commit()
            print(f"✅ Stored monthly KPI data for {stored_count} KPIs")
            return stored_count
            
        except Exception as e:
            print(f"❌ Error storing monthly KPI data: {e}")
            db.session.rollback()
            raise e
    
    def _calculate_account_health_scores(self, account, customer_id):
        """Calculate health scores for a specific account using the same rollup methodology."""
        # Get KPIs for this account
        account_kpis = KPI.query.filter_by(account_id=account.account_id).all()
        
        if not account_kpis:
            return {
                'overall': 0,
                'product_usage': 0,
                'support': 0,
                'customer_sentiment': 0,
                'business_outcomes': 0,
                'relationship_strength': 0,
                'total_kpis': 0,
                'valid_kpis': 0
            }
        
        # Group KPIs by category with weighted scores
        category_data = {}
        total_kpis = len(account_kpis)
        valid_kpis = 0
        
        # Category weights from the rollup methodology
        category_weights = {
            'Product Usage KPI': 0.3,
            'Support KPI': 0.2,
            'Customer Sentiment KPI': 0.2,
            'Business Outcomes KPI': 0.15,
            'Relationship Strength KPI': 0.15
        }
        
        for kpi in account_kpis:
            parsed_value = self.health_engine.parse_kpi_value(kpi.data, kpi.kpi_parameter)
            
            if parsed_value is not None:
                health_info = self.health_engine.calculate_health_status(parsed_value, kpi.kpi_parameter)
                
                category = kpi.category
                if category not in category_data:
                    category_data[category] = {
                        'scores': [],
                        'weights': [],
                        'impact_multipliers': []
                    }
                
                # Get impact level multiplier
                impact_multiplier = 1
                if kpi.impact_level == 'High':
                    impact_multiplier = 3
                elif kpi.impact_level == 'Medium':
                    impact_multiplier = 2
                elif kpi.impact_level == 'Low':
                    impact_multiplier = 1
                
                category_data[category]['scores'].append(health_info['score'])
                category_data[category]['weights'].append(impact_multiplier)
                category_data[category]['impact_multipliers'].append(impact_multiplier)
                valid_kpis += 1
        
        # Calculate weighted category scores using the same methodology as rollup
        health_scores = {}
        weighted_category_sum = 0
        total_weight = 0
        
        for category, weight in category_weights.items():
            if category in category_data:
                scores = category_data[category]['scores']
                impact_multipliers = category_data[category]['impact_multipliers']
                
                # Calculate weighted average for this category
                weighted_scores = [score * impact for score, impact in zip(scores, impact_multipliers)]
                total_impact = sum(impact_multipliers)
                category_average = sum(weighted_scores) / total_impact if total_impact > 0 else 0
                
                health_scores[category.lower().replace(' kpi', '').replace(' ', '_')] = category_average
                
                # Add to overall calculation
                weighted_category_sum += category_average * weight
                total_weight += weight
        
        # Calculate overall score using weighted methodology
        health_scores['overall'] = weighted_category_sum / total_weight if total_weight > 0 else 0
        health_scores['total_kpis'] = total_kpis
        health_scores['valid_kpis'] = valid_kpis
        
        return health_scores
    
    def _calculate_category_average(self, scores):
        """Calculate average score for a category."""
        if not scores:
            return 0
        return sum(scores) / len(scores)
    
    def get_kpi_trends(self, kpi_name, account_id, months=12):
        """Get historical trends for a specific KPI."""
        trends = db.session.query(KPITimeSeries).join(KPI).filter(
            KPI.kpi_parameter == kpi_name,
            KPITimeSeries.account_id == account_id
        ).order_by(KPITimeSeries.year, KPITimeSeries.month).limit(months).all()
        
        return [{
            'month': f"{trend.year}-{trend.month:02d}",
            'value': float(trend.value) if trend.value else 0,
            'health_status': trend.health_status,
            'health_score': float(trend.health_score) if trend.health_score else 0
        } for trend in trends]
    
    def get_account_health_trends(self, account_id, months=12):
        """Get historical health score trends for an account."""
        trends = HealthTrend.query.filter_by(account_id=account_id).order_by(
            HealthTrend.year, HealthTrend.month
        ).limit(months).all()
        
        return [{
            'month': f"{trend.year}-{trend.month:02d}",
            'overall_score': float(trend.overall_health_score),
            'product_usage_score': float(trend.product_usage_score) if trend.product_usage_score else 0,
            'support_score': float(trend.support_score) if trend.support_score else 0,
            'customer_sentiment_score': float(trend.customer_sentiment_score) if trend.customer_sentiment_score else 0,
            'business_outcomes_score': float(trend.business_outcomes_score) if trend.business_outcomes_score else 0,
            'relationship_strength_score': float(trend.relationship_strength_score) if trend.relationship_strength_score else 0
        } for trend in trends]
