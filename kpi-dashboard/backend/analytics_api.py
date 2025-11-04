#!/usr/bin/env python3
"""
Analytics API: Deterministic endpoints for exact numerical queries
Provides fast, accurate, cost-effective responses for quantitative questions
"""

from flask import Blueprint, request, jsonify, abort
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import Account, KPI, KPIUpload
from sqlalchemy import func, and_, or_, cast, Float
from typing import Dict, List, Any
from datetime import datetime

analytics_api = Blueprint('analytics_api', __name__)


def get_current_customer_id():
    """Extract and validate customer ID from headers"""
    cid = get_current_customer_id()
    if not cid:
        abort(400, 'Authentication required (handled by middleware)')
    try:
        return int(cid)
    except:
        abort(400, 'Invalid authentication (handled by middleware)')


# ==================== REVENUE ANALYTICS ====================

@analytics_api.route('/api/analytics/revenue/total', methods=['GET'])
def get_total_revenue():
    """Get total revenue across all accounts"""
    customer_id = get_current_customer_id()
    
    # Optional filters
    industry = request.args.get('industry')
    region = request.args.get('region')
    status = request.args.get('status', 'active')
    
    query = db.session.query(func.sum(Account.revenue)).filter(
        Account.customer_id == customer_id
    )
    
    if industry:
        query = query.filter(Account.industry == industry)
    if region:
        query = query.filter(Account.region == region)
    if status:
        query = query.filter(Account.account_status == status)
    
    total = query.scalar() or 0
    
    return jsonify({
        'query_type': 'revenue_total',
        'customer_id': customer_id,
        'result': {
            'total_revenue': float(total),
            'formatted': f"${total:,.2f}"
        },
        'filters': {
            'industry': industry,
            'region': region,
            'status': status
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'calculation': 'SUM(revenue)',
            'precision': 'exact',
            'timestamp': datetime.utcnow().isoformat()
        }
    })


@analytics_api.route('/api/analytics/revenue/average', methods=['GET'])
def get_average_revenue():
    """Get average revenue per account"""
    customer_id = get_current_customer_id()
    
    # Optional filters
    industry = request.args.get('industry')
    region = request.args.get('region')
    
    query = db.session.query(
        func.avg(Account.revenue).label('average'),
        func.count(Account.account_id).label('count'),
        func.min(Account.revenue).label('min'),
        func.max(Account.revenue).label('max')
    ).filter(Account.customer_id == customer_id)
    
    if industry:
        query = query.filter(Account.industry == industry)
    if region:
        query = query.filter(Account.region == region)
    
    result = query.first()
    
    return jsonify({
        'query_type': 'revenue_average',
        'customer_id': customer_id,
        'result': {
            'average_revenue': float(result.average or 0),
            'account_count': result.count,
            'min_revenue': float(result.min or 0),
            'max_revenue': float(result.max or 0),
            'formatted_average': f"${result.average or 0:,.2f}"
        },
        'filters': {
            'industry': industry,
            'region': region
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'calculation': 'AVG(revenue)',
            'precision': 'exact',
            'timestamp': datetime.utcnow().isoformat()
        }
    })


@analytics_api.route('/api/analytics/revenue/by-industry', methods=['GET'])
def get_revenue_by_industry():
    """Get revenue breakdown by industry"""
    customer_id = get_current_customer_id()
    
    results = db.session.query(
        Account.industry,
        func.sum(Account.revenue).label('total_revenue'),
        func.count(Account.account_id).label('account_count'),
        func.avg(Account.revenue).label('avg_revenue'),
        func.min(Account.revenue).label('min_revenue'),
        func.max(Account.revenue).label('max_revenue')
    ).filter(
        Account.customer_id == customer_id
    ).group_by(
        Account.industry
    ).order_by(
        func.sum(Account.revenue).desc()
    ).all()
    
    return jsonify({
        'query_type': 'revenue_by_industry',
        'customer_id': customer_id,
        'result': [{
            'industry': r.industry,
            'total_revenue': float(r.total_revenue or 0),
            'account_count': r.account_count,
            'average_revenue': float(r.avg_revenue or 0),
            'min_revenue': float(r.min_revenue or 0),
            'max_revenue': float(r.max_revenue or 0),
            'formatted_total': f"${r.total_revenue or 0:,.2f}"
        } for r in results],
        'metadata': {
            'source': 'deterministic_analytics',
            'calculation': 'SUM(revenue) GROUP BY industry',
            'precision': 'exact',
            'timestamp': datetime.utcnow().isoformat()
        }
    })


@analytics_api.route('/api/analytics/revenue/by-region', methods=['GET'])
def get_revenue_by_region():
    """Get revenue breakdown by region"""
    customer_id = get_current_customer_id()
    
    results = db.session.query(
        Account.region,
        func.sum(Account.revenue).label('total_revenue'),
        func.count(Account.account_id).label('account_count'),
        func.avg(Account.revenue).label('avg_revenue')
    ).filter(
        Account.customer_id == customer_id
    ).group_by(
        Account.region
    ).order_by(
        func.sum(Account.revenue).desc()
    ).all()
    
    return jsonify({
        'query_type': 'revenue_by_region',
        'customer_id': customer_id,
        'result': [{
            'region': r.region,
            'total_revenue': float(r.total_revenue or 0),
            'account_count': r.account_count,
            'average_revenue': float(r.avg_revenue or 0),
            'formatted_total': f"${r.total_revenue or 0:,.2f}"
        } for r in results],
        'metadata': {
            'source': 'deterministic_analytics',
            'precision': 'exact',
            'timestamp': datetime.utcnow().isoformat()
        }
    })


@analytics_api.route('/api/analytics/revenue/top-accounts', methods=['GET'])
def get_top_revenue_accounts():
    """Get top accounts by revenue"""
    customer_id = get_current_customer_id()
    limit = request.args.get('limit', 10, type=int)
    
    accounts = Account.query.filter_by(
        customer_id=customer_id
    ).order_by(
        Account.revenue.desc()
    ).limit(limit).all()
    
    total_revenue = sum(a.revenue or 0 for a in accounts)
    
    return jsonify({
        'query_type': 'top_revenue_accounts',
        'customer_id': customer_id,
        'result': {
            'accounts': [{
                'rank': idx + 1,
                'account_id': a.account_id,
                'account_name': a.account_name,
                'revenue': float(a.revenue or 0),
                'industry': a.industry,
                'region': a.region,
                'status': a.account_status,
                'formatted_revenue': f"${a.revenue or 0:,.2f}"
            } for idx, a in enumerate(accounts)],
            'summary': {
                'total_revenue_top_accounts': float(total_revenue),
                'account_count': len(accounts),
                'average_revenue': float(total_revenue / len(accounts)) if accounts else 0
            }
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'limit': limit,
            'precision': 'exact',
            'timestamp': datetime.utcnow().isoformat()
        }
    })


# ==================== ACCOUNT ANALYTICS ====================

@analytics_api.route('/api/analytics/accounts/count', methods=['GET'])
def get_account_count():
    """Get total account count with optional filters"""
    customer_id = get_current_customer_id()
    
    # Get optional filters
    industry = request.args.get('industry')
    region = request.args.get('region')
    status = request.args.get('status')
    min_revenue = request.args.get('min_revenue', type=float)
    max_revenue = request.args.get('max_revenue', type=float)
    
    query = Account.query.filter_by(customer_id=customer_id)
    
    if industry:
        query = query.filter(Account.industry == industry)
    if region:
        query = query.filter(Account.region == region)
    if status:
        query = query.filter(Account.account_status == status)
    if min_revenue is not None:
        query = query.filter(Account.revenue >= min_revenue)
    if max_revenue is not None:
        query = query.filter(Account.revenue <= max_revenue)
    
    count = query.count()
    
    return jsonify({
        'query_type': 'account_count',
        'customer_id': customer_id,
        'result': {
            'count': count
        },
        'filters': {
            'industry': industry,
            'region': region,
            'status': status,
            'min_revenue': min_revenue,
            'max_revenue': max_revenue
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'calculation': 'COUNT(*)',
            'precision': 'exact',
            'timestamp': datetime.utcnow().isoformat()
        }
    })


@analytics_api.route('/api/analytics/accounts/by-industry', methods=['GET'])
def get_accounts_by_industry():
    """Get account distribution by industry"""
    customer_id = get_current_customer_id()
    
    results = db.session.query(
        Account.industry,
        func.count(Account.account_id).label('count'),
        func.sum(Account.revenue).label('total_revenue'),
        func.avg(Account.revenue).label('avg_revenue')
    ).filter(
        Account.customer_id == customer_id
    ).group_by(
        Account.industry
    ).order_by(
        func.count(Account.account_id).desc()
    ).all()
    
    total_accounts = sum(r.count for r in results)
    
    return jsonify({
        'query_type': 'accounts_by_industry',
        'customer_id': customer_id,
        'result': [{
            'industry': r.industry,
            'account_count': r.count,
            'total_revenue': float(r.total_revenue or 0),
            'average_revenue': float(r.avg_revenue or 0),
            'percentage_of_total': round(r.count / total_accounts * 100, 2) if total_accounts > 0 else 0
        } for r in results],
        'summary': {
            'total_accounts': total_accounts,
            'industry_count': len(results)
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'precision': 'exact',
            'timestamp': datetime.utcnow().isoformat()
        }
    })


@analytics_api.route('/api/analytics/accounts/by-region', methods=['GET'])
def get_accounts_by_region():
    """Get account distribution by region"""
    customer_id = get_current_customer_id()
    
    results = db.session.query(
        Account.region,
        func.count(Account.account_id).label('count'),
        func.sum(Account.revenue).label('total_revenue'),
        func.avg(Account.revenue).label('avg_revenue')
    ).filter(
        Account.customer_id == customer_id
    ).group_by(
        Account.region
    ).order_by(
        func.count(Account.account_id).desc()
    ).all()
    
    return jsonify({
        'query_type': 'accounts_by_region',
        'customer_id': customer_id,
        'result': [{
            'region': r.region,
            'account_count': r.count,
            'total_revenue': float(r.total_revenue or 0),
            'average_revenue': float(r.avg_revenue or 0)
        } for r in results],
        'metadata': {
            'source': 'deterministic_analytics',
            'precision': 'exact',
            'timestamp': datetime.utcnow().isoformat()
        }
    })


@analytics_api.route('/api/analytics/accounts/<int:account_id>', methods=['GET'])
def get_account_details(account_id):
    """Get detailed information for a specific account"""
    customer_id = get_current_customer_id()
    
    account = Account.query.filter_by(
        account_id=account_id,
        customer_id=customer_id
    ).first()
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Get KPI count for this account
    kpi_count = KPI.query.filter_by(account_id=account_id).count()
    
    return jsonify({
        'query_type': 'account_details',
        'customer_id': customer_id,
        'result': {
            'account_id': account.account_id,
            'account_name': account.account_name,
            'revenue': float(account.revenue or 0),
            'industry': account.industry,
            'region': account.region,
            'status': account.account_status,
            'kpi_count': kpi_count,
            'created_at': account.created_at.isoformat() if account.created_at else None,
            'formatted_revenue': f"${account.revenue or 0:,.2f}"
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'precision': 'exact',
            'timestamp': datetime.utcnow().isoformat()
        }
    })


# ==================== KPI ANALYTICS ====================

@analytics_api.route('/api/analytics/kpis/count', methods=['GET'])
def get_kpi_count():
    """Get total KPI count"""
    customer_id = get_current_customer_id()
    
    count = db.session.query(func.count(KPI.kpi_id)).join(
        Account, KPI.account_id == Account.account_id
    ).filter(
        Account.customer_id == customer_id
    ).scalar()
    
    # Get count by category
    category_counts = db.session.query(
        KPI.category,
        func.count(KPI.kpi_id).label('count')
    ).join(
        Account, KPI.account_id == Account.account_id
    ).filter(
        Account.customer_id == customer_id
    ).group_by(
        KPI.category
    ).all()
    
    return jsonify({
        'query_type': 'kpi_count',
        'customer_id': customer_id,
        'result': {
            'total_count': count,
            'by_category': [{
                'category': c.category,
                'count': c.count
            } for c in category_counts]
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'precision': 'exact',
            'timestamp': datetime.utcnow().isoformat()
        }
    })


@analytics_api.route('/api/analytics/kpis/summary', methods=['GET'])
def get_kpi_summary():
    """Get comprehensive KPI summary statistics"""
    customer_id = get_current_customer_id()
    
    # Get KPI count by category
    category_stats = db.session.query(
        KPI.category,
        func.count(KPI.kpi_id).label('count')
    ).join(
        Account, KPI.account_id == Account.account_id
    ).filter(
        Account.customer_id == customer_id
    ).group_by(
        KPI.category
    ).all()
    
    # Get total count
    total_count = sum(c.count for c in category_stats)
    
    # Get account count with KPIs
    accounts_with_kpis = db.session.query(
        func.count(func.distinct(KPI.account_id))
    ).join(
        Account, KPI.account_id == Account.account_id
    ).filter(
        Account.customer_id == customer_id
    ).scalar()
    
    return jsonify({
        'query_type': 'kpi_summary',
        'customer_id': customer_id,
        'result': {
            'total_kpis': total_count,
            'accounts_with_kpis': accounts_with_kpis,
            'by_category': [{
                'category': c.category,
                'count': c.count,
                'percentage': round(c.count / total_count * 100, 2) if total_count > 0 else 0
            } for c in category_stats]
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'precision': 'exact',
            'timestamp': datetime.utcnow().isoformat()
        }
    })


# ==================== GENERIC AGGREGATION ====================

@analytics_api.route('/api/analytics/aggregate', methods=['POST'])
def aggregate_data():
    """Generic aggregation endpoint for flexible queries"""
    customer_id = get_current_customer_id()
    data = request.json
    
    metric = data.get('metric', 'revenue')
    operation = data.get('operation', 'sum')
    filters = data.get('filters', {})
    group_by = data.get('group_by', [])
    
    try:
        # Build base query
        if operation == 'count':
            agg_func = func.count(Account.account_id)
        else:
            column = getattr(Account, metric, Account.revenue)
            if operation == 'sum':
                agg_func = func.sum(column)
            elif operation == 'avg':
                agg_func = func.avg(column)
            elif operation == 'min':
                agg_func = func.min(column)
            elif operation == 'max':
                agg_func = func.max(column)
            else:
                return jsonify({'error': f'Invalid operation: {operation}'}), 400
        
        # Build grouped query if needed
        if group_by:
            group_cols = [getattr(Account, col) for col in group_by if hasattr(Account, col)]
            query = db.session.query(*group_cols, agg_func.label('value')).filter(
                Account.customer_id == customer_id
            )
            
            # Apply filters
            if filters.get('industry'):
                query = query.filter(Account.industry == filters['industry'])
            if filters.get('region'):
                query = query.filter(Account.region == filters['region'])
            if filters.get('status'):
                query = query.filter(Account.account_status == filters['status'])
            if filters.get('min_revenue'):
                query = query.filter(Account.revenue >= filters['min_revenue'])
            if filters.get('max_revenue'):
                query = query.filter(Account.revenue <= filters['max_revenue'])
            
            query = query.group_by(*group_cols)
            results = query.all()
            
            return jsonify({
                'query_type': 'aggregate_grouped',
                'customer_id': customer_id,
                'result': [{
                    **{col: getattr(r, col) for col in group_by if hasattr(r, col)},
                    'value': float(r.value or 0)
                } for r in results],
                'metadata': {
                    'metric': metric,
                    'operation': operation,
                    'group_by': group_by,
                    'filters': filters,
                    'source': 'deterministic_analytics',
                    'precision': 'exact',
                    'timestamp': datetime.utcnow().isoformat()
                }
            })
        else:
            # Single aggregation
            query = db.session.query(agg_func).filter(
                Account.customer_id == customer_id
            )
            
            # Apply filters
            if filters.get('industry'):
                query = query.filter(Account.industry == filters['industry'])
            if filters.get('region'):
                query = query.filter(Account.region == filters['region'])
            if filters.get('status'):
                query = query.filter(Account.account_status == filters['status'])
            if filters.get('min_revenue'):
                query = query.filter(Account.revenue >= filters['min_revenue'])
            if filters.get('max_revenue'):
                query = query.filter(Account.revenue <= filters['max_revenue'])
            
            result = query.scalar() or 0
            
            return jsonify({
                'query_type': 'aggregate_single',
                'customer_id': customer_id,
                'result': {
                    'value': float(result),
                    'operation': operation,
                    'metric': metric
                },
                'metadata': {
                    'filters': filters,
                    'source': 'deterministic_analytics',
                    'precision': 'exact',
                    'timestamp': datetime.utcnow().isoformat()
                }
            })
    
    except Exception as e:
        return jsonify({'error': f'Aggregation failed: {str(e)}'}), 500


# ==================== STATISTICS ====================

@analytics_api.route('/api/analytics/statistics', methods=['GET'])
def get_statistics():
    """Get comprehensive statistics for customer data"""
    customer_id = get_current_customer_id()
    
    # Revenue statistics
    revenue_stats = db.session.query(
        func.sum(Account.revenue).label('total'),
        func.avg(Account.revenue).label('average'),
        func.min(Account.revenue).label('minimum'),
        func.max(Account.revenue).label('maximum'),
        func.count(Account.account_id).label('count')
    ).filter(
        Account.customer_id == customer_id
    ).first()
    
    # Account statistics
    account_count_by_status = db.session.query(
        Account.account_status,
        func.count(Account.account_id).label('count')
    ).filter(
        Account.customer_id == customer_id
    ).group_by(
        Account.account_status
    ).all()
    
    # KPI statistics
    kpi_count = db.session.query(func.count(KPI.kpi_id)).join(
        Account, KPI.account_id == Account.account_id
    ).filter(
        Account.customer_id == customer_id
    ).scalar()
    
    return jsonify({
        'query_type': 'comprehensive_statistics',
        'customer_id': customer_id,
        'result': {
            'revenue': {
                'total': float(revenue_stats.total or 0),
                'average': float(revenue_stats.average or 0),
                'minimum': float(revenue_stats.minimum or 0),
                'maximum': float(revenue_stats.maximum or 0),
                'formatted_total': f"${revenue_stats.total or 0:,.2f}"
            },
            'accounts': {
                'total': revenue_stats.count,
                'by_status': [{
                    'status': s.account_status,
                    'count': s.count
                } for s in account_count_by_status]
            },
            'kpis': {
                'total': kpi_count
            }
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'precision': 'exact',
            'timestamp': datetime.utcnow().isoformat()
        }
    })

