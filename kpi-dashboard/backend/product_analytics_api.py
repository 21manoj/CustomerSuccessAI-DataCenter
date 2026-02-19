#!/usr/bin/env python3
"""
Product Analytics API
Endpoints for querying product health scores, trends, and analytics
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id
from models import db, Account
from product_analytics_models import ProductCatalog, ProductTrend, ProductAggregateTrend
from product_health_calculator import calculate_and_store_product_health
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

product_analytics_api = Blueprint('product_analytics_api', __name__)


@product_analytics_api.route('/api/products/health', methods=['GET'])
def get_product_health():
    """
    Get product health scores for a customer
    Query params:
        - account_id: Optional, filter by account
        - product_id: Optional, filter by product
        - aggregate: Optional, if true return aggregate trends
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'X-Customer-ID header is required'}), 400
    
    try:
        customer_id = int(customer_id)
    except ValueError:
        return jsonify({'error': 'Invalid X-Customer-ID'}), 400
    
    account_id = request.args.get('account_id', type=int)
    product_id = request.args.get('product_id', type=int)
    aggregate = request.args.get('aggregate', 'false').lower() == 'true'
    
    now = datetime.now()
    month = now.month
    year = now.year
    
    if aggregate:
        # Return aggregate trends
        query = ProductAggregateTrend.query.filter_by(
            customer_id=customer_id,
            month=month,
            year=year
        )
        
        if product_id:
            query = query.filter_by(product_id=product_id)
        
        trends = query.all()
        
        results = []
        for trend in trends:
            product = db.session.get(ProductCatalog, trend.product_id)
            results.append({
                'product_id': trend.product_id,
                'product_name': product.product_name if product else 'Unknown',
                'month': trend.month,
                'year': trend.year,
                'overall_health_score': float(trend.overall_health_score),
                'product_usage_score': float(trend.product_usage_score) if trend.product_usage_score else None,
                'support_score': float(trend.support_score) if trend.support_score else None,
                'customer_sentiment_score': float(trend.customer_sentiment_score) if trend.customer_sentiment_score else None,
                'business_outcomes_score': float(trend.business_outcomes_score) if trend.business_outcomes_score else None,
                'relationship_strength_score': float(trend.relationship_strength_score) if trend.relationship_strength_score else None,
                'total_accounts': trend.total_accounts,
                'total_revenue': float(trend.total_revenue) if trend.total_revenue else 0,
                'average_revenue_per_account': float(trend.average_revenue_per_account) if trend.average_revenue_per_account else 0,
                'total_kpis': trend.total_kpis,
                'valid_kpis': trend.valid_kpis
            })
        
        return jsonify({'products': results}), 200
    
    else:
        # Return per-account product trends
        query = ProductTrend.query.filter_by(
            customer_id=customer_id,
            month=month,
            year=year
        )
        
        if account_id:
            query = query.filter_by(account_id=account_id)
        if product_id:
            query = query.filter_by(product_id=product_id)
        
        trends = query.all()
        
        results = []
        for trend in trends:
            product = db.session.get(ProductCatalog, trend.product_id)
            account = db.session.get(Account, trend.account_id)
            results.append({
                'product_id': trend.product_id,
                'product_name': product.product_name if product else 'Unknown',
                'account_id': trend.account_id,
                'account_name': account.account_name if account else 'Unknown',
                'month': trend.month,
                'year': trend.year,
                'overall_health_score': float(trend.overall_health_score),
                'product_usage_score': float(trend.product_usage_score) if trend.product_usage_score else None,
                'support_score': float(trend.support_score) if trend.support_score else None,
                'customer_sentiment_score': float(trend.customer_sentiment_score) if trend.customer_sentiment_score else None,
                'business_outcomes_score': float(trend.business_outcomes_score) if trend.business_outcomes_score else None,
                'relationship_strength_score': float(trend.relationship_strength_score) if trend.relationship_strength_score else None,
                'total_kpis': trend.total_kpis,
                'valid_kpis': trend.valid_kpis,
                'product_level_kpis': trend.product_level_kpis,
                'account_level_kpis': trend.account_level_kpis,
                'revenue': float(trend.revenue) if trend.revenue else 0
            })
        
        return jsonify({'product_trends': results}), 200


@product_analytics_api.route('/api/products/catalog', methods=['GET'])
def get_product_catalog():
    """Get product catalog for a customer"""
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'X-Customer-ID header is required'}), 400
    
    try:
        customer_id = int(customer_id)
    except ValueError:
        return jsonify({'error': 'Invalid X-Customer-ID'}), 400
    
    products = ProductCatalog.query.filter_by(customer_id=customer_id, status='active').all()
    
    results = []
    for product in products:
        # Count accounts using this product
        account_count = ProductTrend.query.filter_by(
            product_id=product.product_id
        ).distinct(ProductTrend.account_id).count()
        
        results.append({
            'product_id': product.product_id,
            'product_name': product.product_name,
            'product_sku': product.product_sku,
            'product_type': product.product_type,
            'status': product.status,
            'account_count': account_count,
            'created_at': product.created_at.isoformat() if product.created_at else None
        })
    
    return jsonify({'products': results}), 200


@product_analytics_api.route('/api/products/recalculate', methods=['POST'])
def recalculate_product_health():
    """
    Recalculate product health scores
    Body: { "account_id": <id>, "customer_id": <id> } or empty for all accounts
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'X-Customer-ID header is required'}), 400
    
    try:
        customer_id = int(customer_id)
    except ValueError:
        return jsonify({'error': 'Invalid X-Customer-ID'}), 400
    
    data = request.get_json() or {}
    account_id = data.get('account_id')
    
    try:
        if account_id:
            # ✅ SECURITY: Validate account belongs to customer before processing
            account = Account.query.filter_by(
                account_id=account_id,
                customer_id=customer_id
            ).first()
            
            if not account:
                return jsonify({
                    'status': 'error',
                    'error': 'Account not found or access denied'
                }), 404
            
            # Recalculate for specific account
            calculate_and_store_product_health(account_id, customer_id)
            return jsonify({
                'status': 'success',
                'message': f'Product health recalculated for account {account_id}'
            }), 200
        else:
            # Recalculate for all accounts
            accounts = Account.query.filter_by(customer_id=customer_id).all()
            count = 0
            for account in accounts:
                try:
                    calculate_and_store_product_health(account.account_id, customer_id)
                    count += 1
                except Exception as e:
                    print(f"⚠️ Error recalculating for account {account.account_id}: {str(e)}")
            
            return jsonify({
                'status': 'success',
                'message': f'Product health recalculated for {count} accounts'
            }), 200
            
    except Exception as e:
        # Log full error for debugging, but return sanitized message to client
        logger.error(f"Product health recalculation failed for customer {customer_id}: {str(e)}", exc_info=True)
        
        return jsonify({
            'status': 'error',
            'error': 'Recalculation failed. Please try again or contact support.'
        }), 500
