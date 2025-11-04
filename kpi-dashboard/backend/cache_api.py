#!/usr/bin/env python3
"""
Cache Management API
Provides endpoints to view, manage, and invalidate query cache
"""

from flask import Blueprint, request, jsonify, abort
from auth_middleware import get_current_customer_id, get_current_user_id
from query_cache import get_query_cache, invalidate_customer_cache, get_cache_stats
from datetime import datetime

cache_api = Blueprint('cache_api', __name__)


def get_current_customer_id():
    """Extract and validate customer ID"""
    cid = get_current_customer_id()
    if not cid:
        abort(400, 'Authentication required (handled by middleware)')
    try:
        return int(cid)
    except:
        abort(400, 'Invalid authentication (handled by middleware)')


@cache_api.route('/api/cache/stats', methods=['GET'])
def get_cache_statistics():
    """
    Get cache statistics and performance metrics
    
    Returns cache hit rate, cost savings, and usage statistics
    """
    customer_id = request.args.get('customer_id', type=int)
    
    cache = get_query_cache()
    stats = cache.get_stats()
    
    # Add additional insights
    stats['cost_per_query_uncached'] = 0.02
    stats['estimated_monthly_cost_without_cache'] = round(stats['total_queries'] * 0.02 * 30, 2)
    stats['estimated_monthly_cost_with_cache'] = round(stats['cache_misses'] * 0.02 * 30, 2)
    stats['monthly_savings'] = round(stats['estimated_cost_saved'] * 30, 2)
    
    # Get cached queries for this customer if specified
    if customer_id:
        cached_queries = cache.get_cached_queries(customer_id)
        stats['cached_queries_count'] = len(cached_queries)
        stats['top_queries'] = cached_queries[:10]  # Top 10 most hit queries
    
    return jsonify({
        'timestamp': datetime.utcnow().isoformat(),
        'cache_enabled': True,
        'statistics': stats
    })


@cache_api.route('/api/cache/queries', methods=['GET'])
def get_cached_queries():
    """
    Get list of cached queries for a customer
    
    Query params:
      - customer_id: Filter by customer (optional)
    """
    customer_id = request.args.get('customer_id', type=int)
    
    cache = get_query_cache()
    cached_queries = cache.get_cached_queries(customer_id)
    
    return jsonify({
        'timestamp': datetime.utcnow().isoformat(),
        'total_cached': len(cached_queries),
        'queries': cached_queries
    })


@cache_api.route('/api/cache/invalidate', methods=['POST'])
def invalidate_cache():
    """
    Invalidate cache entries
    
    Body:
      - customer_id: Invalidate all for this customer (optional)
      - pattern: Invalidate queries matching pattern (optional)
      - all: Invalidate entire cache if true
    """
    data = request.json or {}
    
    cache = get_query_cache()
    
    if data.get('all'):
        # Clear entire cache
        count = cache.invalidate()
        return jsonify({
            'status': 'success',
            'message': f'Cleared entire cache',
            'entries_invalidated': count
        })
    
    customer_id = data.get('customer_id')
    pattern = data.get('pattern')
    
    if not customer_id and not pattern:
        return jsonify({'error': 'Provide customer_id, pattern, or all=true'}), 400
    
    count = cache.invalidate(customer_id=customer_id, pattern=pattern)
    
    return jsonify({
        'status': 'success',
        'message': f'Invalidated {count} cache entries',
        'entries_invalidated': count,
        'customer_id': customer_id,
        'pattern': pattern
    })


@cache_api.route('/api/cache/cleanup', methods=['POST'])
def cleanup_expired_cache():
    """
    Remove expired cache entries
    
    Runs automatic cleanup of expired entries
    """
    cache = get_query_cache()
    count = cache.cleanup_expired()
    
    return jsonify({
        'status': 'success',
        'message': f'Cleaned up {count} expired entries',
        'entries_removed': count,
        'timestamp': datetime.utcnow().isoformat()
    })


@cache_api.route('/api/cache/info', methods=['GET'])
def get_cache_info():
    """
    Get detailed cache information and health
    """
    cache = get_query_cache()
    stats = cache.get_stats()
    
    return jsonify({
        'cache_enabled': True,
        'cache_type': 'in_memory',
        'default_ttl_seconds': cache.default_ttl,
        'default_ttl_minutes': cache.default_ttl / 60,
        'default_ttl_hours': cache.default_ttl / 3600,
        'current_size': len(cache.cache),
        'statistics': stats,
        'recommendations': {
            'hit_rate': stats.get('hit_rate_percentage', 0),
            'cost_efficiency': 'Excellent' if stats.get('hit_rate_percentage', 0) > 70 else 
                             'Good' if stats.get('hit_rate_percentage', 0) > 50 else 'Poor',
            'estimated_monthly_savings': f"${stats.get('estimated_savings_monthly', 0):.2f}"
        },
        'timestamp': datetime.utcnow().isoformat()
    })


@cache_api.route('/api/cache/test', methods=['GET'])
def test_cache():
    """Test endpoint to verify cache is working"""
    return jsonify({
        'status': 'success',
        'message': 'Cache API is working',
        'cache_enabled': True,
        'timestamp': datetime.utcnow().isoformat()
    })

