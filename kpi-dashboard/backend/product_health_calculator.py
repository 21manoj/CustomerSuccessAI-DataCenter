#!/usr/bin/env python3
"""
Product Health Score Calculator
Calculates product health scores from KPIs and stores in product_trends and product_aggregate_trends
"""

from models import db, Account, KPI, ProductCatalog, ProductTrend, ProductAggregateTrend
from product_normalization import sync_account_products_to_catalog, normalize_product_name
from health_score_engine import HealthScoreEngine
from datetime import datetime
from collections import defaultdict


def calculate_product_health_score(product_id: int, account_id: int, customer_id: int) -> dict:
    """
    Calculate health scores for a specific product-account combination
    
    Returns:
        dict with health scores and KPI statistics
    """
    product = ProductCatalog.query.get(product_id)
    if not product:
        return None
    
    account = Account.query.get(account_id)
    if not account:
        return None
    
    # Get product-level KPIs (KPIs with product_id matching)
    product_level_kpis = KPI.query.filter_by(
        account_id=account_id,
        product_id=product_id
    ).all()
    
    # Get account-level KPIs from Product Usage and Support pillars
    # These are treated as product-level for health calculation
    account_level_kpis = KPI.query.filter(
        KPI.account_id == account_id,
        KPI.product_id.is_(None),  # Account-level only
        KPI.category.in_(['Product Usage KPI', 'Support KPI'])
    ).all()
    
    all_kpis = list(product_level_kpis) + list(account_level_kpis)
    
    if not all_kpis:
        return {
            'overall_health_score': 0,
            'product_usage_score': 0,
            'support_score': 0,
            'customer_sentiment_score': 0,
            'business_outcomes_score': 0,
            'relationship_strength_score': 0,
            'total_kpis': 0,
            'valid_kpis': 0,
            'product_level_kpis': len(product_level_kpis),
            'account_level_kpis': len(account_level_kpis)
        }
    
    # Group KPIs by category
    category_kpis = defaultdict(list)
    for kpi in all_kpis:
        category = kpi.category
        if category:
            category_kpis[category].append({
                'kpi_parameter': kpi.kpi_parameter,
                'data': kpi.data,
                'impact_level': kpi.impact_level,
                'health_score_component': kpi.health_score_component,
                'category': kpi.category,
                'weight': kpi.weight,
                'source_review': kpi.source_review,
                'measurement_frequency': kpi.measurement_frequency
            })
    
    # Calculate category scores
    category_scores = {}
    for category, kpis in category_kpis.items():
        if kpis:
            category_score = HealthScoreEngine.calculate_category_health_score(kpis, category, customer_id)
            category_scores[category] = category_score.get('average_score', 0)
    
    # Map categories to health score components
    product_usage_score = category_scores.get('Product Usage KPI', 0)
    support_score = category_scores.get('Support KPI', 0)
    customer_sentiment_score = category_scores.get('Customer Sentiment KPI', 0)
    business_outcomes_score = category_scores.get('Business Outcomes KPI', 0)
    relationship_strength_score = category_scores.get('Relationship Strength KPI', 0)
    
    # Calculate overall score (weighted average)
    category_weights = {
        'Product Usage KPI': 0.3,
        'Support KPI': 0.2,
        'Customer Sentiment KPI': 0.2,
        'Business Outcomes KPI': 0.15,
        'Relationship Strength KPI': 0.15
    }
    
    weighted_sum = 0
    total_weight = 0
    for category, score in category_scores.items():
        weight = category_weights.get(category, 0.1)
        weighted_sum += score * weight
        total_weight += weight
    
    overall_health_score = weighted_sum / total_weight if total_weight > 0 else 0
    
    # Count valid KPIs (KPIs with valid data)
    valid_kpis = sum(1 for kpi in all_kpis if kpi.data and str(kpi.data).strip())
    
    return {
        'overall_health_score': round(overall_health_score, 2),
        'product_usage_score': round(product_usage_score, 2),
        'support_score': round(support_score, 2),
        'customer_sentiment_score': round(customer_sentiment_score, 2),
        'business_outcomes_score': round(business_outcomes_score, 2),
        'relationship_strength_score': round(relationship_strength_score, 2),
        'total_kpis': len(all_kpis),
        'valid_kpis': valid_kpis,
        'product_level_kpis': len(product_level_kpis),
        'account_level_kpis': len(account_level_kpis)
    }


def store_product_trend(product_id: int, account_id: int, customer_id: int, 
                        health_data: dict, revenue: float = None) -> ProductTrend:
    """
    Store or update product trend for current month/year
    """
    now = datetime.now()
    month = now.month
    year = now.year
    
    # Get or create trend
    trend = ProductTrend.query.filter_by(
        product_id=product_id,
        account_id=account_id,
        month=month,
        year=year
    ).first()
    
    if not trend:
        trend = ProductTrend(
            product_id=product_id,
            account_id=account_id,
            customer_id=customer_id,
            month=month,
            year=year
        )
        db.session.add(trend)
    
    # Update health scores
    trend.overall_health_score = health_data['overall_health_score']
    trend.product_usage_score = health_data.get('product_usage_score')
    trend.support_score = health_data.get('support_score')
    trend.customer_sentiment_score = health_data.get('customer_sentiment_score')
    trend.business_outcomes_score = health_data.get('business_outcomes_score')
    trend.relationship_strength_score = health_data.get('relationship_strength_score')
    
    # Update KPI statistics
    trend.total_kpis = health_data.get('total_kpis', 0)
    trend.valid_kpis = health_data.get('valid_kpis', 0)
    trend.product_level_kpis = health_data.get('product_level_kpis', 0)
    trend.account_level_kpis = health_data.get('account_level_kpis', 0)
    
    # Update revenue
    if revenue is not None:
        trend.revenue = revenue
    
    db.session.flush()
    return trend


def calculate_and_store_product_health(account_id: int, customer_id: int = None):
    """
    Calculate and store product health scores for an account
    Called on KPI upload or data change
    """
    account = Account.query.get(account_id)
    if not account:
        return
    
    if customer_id is None:
        customer_id = account.customer_id
    
    # Sync account products to catalog (normalize and link to catalog)
    linked_products = sync_account_products_to_catalog(account)
    
    if not linked_products:
        print(f"⚠️ No products found for account {account_id}")
        return
    
    # Calculate health for each product
    for product in linked_products:
        health_data = calculate_product_health_score(
            product_id=product.product_id,
            account_id=account_id,
            customer_id=customer_id
        )
        
        if health_data:
            store_product_trend(
                product_id=product.product_id,
                account_id=account_id,
                customer_id=customer_id,
                health_data=health_data,
                revenue=float(account.revenue) if account.revenue else None
            )
            print(f"✅ Calculated health for product '{product.product_name}' @ account {account_id}: {health_data['overall_health_score']}")
    
    # Calculate aggregate trends for all products
    calculate_product_aggregate_trends(customer_id)
    
    db.session.commit()


def calculate_product_aggregate_trends(customer_id: int):
    """
    Calculate aggregate product trends across all accounts
    """
    now = datetime.now()
    month = now.month
    year = now.year
    
    # Get all products for this customer
    products = ProductCatalog.query.filter_by(customer_id=customer_id, status='active').all()
    
    for product in products:
        # Get all trends for this product in current month
        trends = ProductTrend.query.filter_by(
            product_id=product.product_id,
            month=month,
            year=year
        ).all()
        
        if not trends:
            continue
        
        # Calculate weighted averages (by revenue)
        total_revenue = sum(float(t.revenue or 0) for t in trends)
        total_accounts = len(trends)
        
        if total_accounts == 0:
            continue
        
        # Weighted average health scores
        weighted_overall = 0
        weighted_product_usage = 0
        weighted_support = 0
        weighted_sentiment = 0
        weighted_outcomes = 0
        weighted_relationship = 0
        
        total_kpis = 0
        valid_kpis = 0
        
        for trend in trends:
            weight = float(trend.revenue or 0) / total_revenue if total_revenue > 0 else 1.0 / total_accounts
            
            weighted_overall += float(trend.overall_health_score or 0) * weight
            weighted_product_usage += float(trend.product_usage_score or 0) * weight
            weighted_support += float(trend.support_score or 0) * weight
            weighted_sentiment += float(trend.customer_sentiment_score or 0) * weight
            weighted_outcomes += float(trend.business_outcomes_score or 0) * weight
            weighted_relationship += float(trend.relationship_strength_score or 0) * weight
            
            total_kpis += trend.total_kpis or 0
            valid_kpis += trend.valid_kpis or 0
        
        # Get or create aggregate trend
        aggregate = ProductAggregateTrend.query.filter_by(
            product_id=product.product_id,
            month=month,
            year=year
        ).first()
        
        if not aggregate:
            aggregate = ProductAggregateTrend(
                product_id=product.product_id,
                customer_id=customer_id,
                month=month,
                year=year
            )
            db.session.add(aggregate)
        
        # Update aggregate scores
        aggregate.overall_health_score = round(weighted_overall, 2)
        aggregate.product_usage_score = round(weighted_product_usage, 2)
        aggregate.support_score = round(weighted_support, 2)
        aggregate.customer_sentiment_score = round(weighted_sentiment, 2)
        aggregate.business_outcomes_score = round(weighted_outcomes, 2)
        aggregate.relationship_strength_score = round(weighted_relationship, 2)
        
        aggregate.total_accounts = total_accounts
        aggregate.total_revenue = total_revenue
        aggregate.average_revenue_per_account = total_revenue / total_accounts if total_accounts > 0 else 0
        aggregate.total_kpis = total_kpis
        aggregate.valid_kpis = valid_kpis
        
        db.session.flush()
    
    db.session.commit()
