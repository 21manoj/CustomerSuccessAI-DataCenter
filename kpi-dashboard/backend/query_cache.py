#!/usr/bin/env python3
"""
Simple In-Memory Query Cache for RAG Systems
Reduces OpenAI API costs by caching query results
"""

import hashlib
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class QueryCache:
    """
    Simple in-memory cache for RAG query results
    - Thread-safe for single-process applications
    - TTL-based expiration
    - Automatic cleanup of expired entries
    """
    
    def __init__(self, default_ttl: int = 3600):
        """
        Initialize query cache
        
        Args:
            default_ttl: Time-to-live in seconds (default: 1 hour)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.stats = {
            'hits': 0,
            'misses': 0,
            'total_queries': 0,
            'cache_size': 0,
            'cost_saved': 0.0  # Estimated cost saved
        }
    
    def _generate_cache_key(self, customer_id: int, query: str, query_type: str = 'general') -> str:
        """
        Generate unique cache key from query parameters
        
        Args:
            customer_id: Customer ID
            query: Query text
            query_type: Type of query
            
        Returns:
            Unique cache key (MD5 hash)
        """
        # Normalize query (lowercase, strip whitespace)
        normalized_query = query.lower().strip()
        
        # Create unique string
        cache_string = f"{customer_id}:{normalized_query}:{query_type}"
        
        # Generate hash
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def get(self, customer_id: int, query: str, query_type: str = 'general') -> Optional[Dict[str, Any]]:
        """
        Get cached query result if available and not expired
        
        Args:
            customer_id: Customer ID
            query: Query text
            query_type: Type of query
            
        Returns:
            Cached result or None if not found/expired
        """
        cache_key = self._generate_cache_key(customer_id, query, query_type)
        
        self.stats['total_queries'] += 1
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            # Check if expired
            if time.time() < entry['expires_at']:
                self.stats['hits'] += 1
                self.stats['cost_saved'] += 0.02  # Estimate $0.02 saved per cache hit
                entry['hit_count'] += 1
                entry['last_accessed'] = datetime.utcnow()
                
                print(f"✅ CACHE HIT: {query[:50]}... (saved $0.02)")
                return entry['result']
            else:
                # Expired - remove from cache
                del self.cache[cache_key]
                print(f"⏰ CACHE EXPIRED: {query[:50]}...")
        
        self.stats['misses'] += 1
        print(f"❌ CACHE MISS: {query[:50]}... (cost: $0.02)")
        return None
    
    def set(self, customer_id: int, query: str, result: Dict[str, Any], 
            query_type: str = 'general', ttl: Optional[int] = None) -> None:
        """
        Cache a query result
        
        Args:
            customer_id: Customer ID
            query: Query text
            result: Query result to cache
            query_type: Type of query
            ttl: Time-to-live in seconds (optional, uses default if not provided)
        """
        cache_key = self._generate_cache_key(customer_id, query, query_type)
        ttl = ttl or self.default_ttl
        
        self.cache[cache_key] = {
            'result': result,
            'created_at': datetime.utcnow(),
            'last_accessed': datetime.utcnow(),
            'expires_at': time.time() + ttl,
            'ttl': ttl,
            'customer_id': customer_id,
            'query': query,
            'query_type': query_type,
            'hit_count': 0
        }
        
        self.stats['cache_size'] = len(self.cache)
        print(f"💾 CACHED: {query[:50]}... (TTL: {ttl}s)")
    
    def invalidate(self, customer_id: Optional[int] = None, 
                   pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries
        
        Args:
            customer_id: Invalidate all entries for this customer (optional)
            pattern: Invalidate entries matching this pattern in query text (optional)
            
        Returns:
            Number of entries invalidated
        """
        if customer_id is None and pattern is None:
            # Clear all cache
            count = len(self.cache)
            self.cache.clear()
            self.stats['cache_size'] = 0
            print(f"🗑️  Cleared entire cache ({count} entries)")
            return count
        
        # Selective invalidation
        keys_to_delete = []
        
        for key, entry in self.cache.items():
            should_delete = False
            
            if customer_id and entry['customer_id'] == customer_id:
                should_delete = True
            
            if pattern and pattern.lower() in entry['query'].lower():
                should_delete = True
            
            if should_delete:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.cache[key]
        
        self.stats['cache_size'] = len(self.cache)
        print(f"🗑️  Invalidated {len(keys_to_delete)} cache entries")
        return len(keys_to_delete)
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache
        
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        keys_to_delete = [
            key for key, entry in self.cache.items()
            if current_time >= entry['expires_at']
        ]
        
        for key in keys_to_delete:
            del self.cache[key]
        
        self.stats['cache_size'] = len(self.cache)
        
        if keys_to_delete:
            print(f"🧹 Cleaned up {len(keys_to_delete)} expired cache entries")
        
        return len(keys_to_delete)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
        
        return {
            'cache_size': len(self.cache),
            'total_queries': self.stats['total_queries'],
            'cache_hits': self.stats['hits'],
            'cache_misses': self.stats['misses'],
            'hit_rate_percentage': round(hit_rate, 2),
            'estimated_cost_saved': round(self.stats['cost_saved'], 2),
            'estimated_savings_monthly': round(self.stats['cost_saved'] * 30, 2),
            'default_ttl_seconds': self.default_ttl,
            'default_ttl_minutes': self.default_ttl / 60
        }
    
    def get_cached_queries(self, customer_id: Optional[int] = None) -> list:
        """
        Get list of cached queries
        
        Args:
            customer_id: Filter by customer ID (optional)
            
        Returns:
            List of cached query information
        """
        results = []
        
        for entry in self.cache.values():
            if customer_id is None or entry['customer_id'] == customer_id:
                results.append({
                    'query': entry['query'],
                    'query_type': entry['query_type'],
                    'customer_id': entry['customer_id'],
                    'created_at': entry['created_at'].isoformat(),
                    'last_accessed': entry['last_accessed'].isoformat(),
                    'hit_count': entry['hit_count'],
                    'ttl_seconds': entry['ttl'],
                    'expires_in_seconds': max(0, int(entry['expires_at'] - time.time()))
                })
        
        return sorted(results, key=lambda x: x['hit_count'], reverse=True)


# Global cache instance
_global_query_cache = None


def get_query_cache() -> QueryCache:
    """Get or create global query cache instance"""
    global _global_query_cache
    if _global_query_cache is None:
        _global_query_cache = QueryCache(default_ttl=3600)  # 1 hour default
        print("🚀 Query cache initialized (TTL: 1 hour)")
    return _global_query_cache


# Convenience functions
def cache_query_result(customer_id: int, query: str, result: Dict, query_type: str = 'general'):
    """Cache a query result"""
    cache = get_query_cache()
    cache.set(customer_id, query, result, query_type)


def get_cached_query_result(customer_id: int, query: str, query_type: str = 'general') -> Optional[Dict]:
    """Get cached query result"""
    cache = get_query_cache()
    return cache.get(customer_id, query, query_type)


def invalidate_customer_cache(customer_id: int) -> int:
    """Invalidate all cache entries for a customer"""
    cache = get_query_cache()
    return cache.invalidate(customer_id=customer_id)


def get_cache_stats() -> Dict:
    """Get cache statistics"""
    cache = get_query_cache()
    return cache.get_stats()


if __name__ == '__main__':
    # Test the cache
    cache = QueryCache(default_ttl=60)  # 1 minute for testing
    
    print("=" * 70)
    print("QUERY CACHE TEST")
    print("=" * 70)
    
    # Test 1: Cache miss
    result1 = cache.get(1, "What is the total revenue?", "revenue_analysis")
    print(f"Test 1 - First query: {result1}")
    
    # Test 2: Cache set
    cache.set(1, "What is the total revenue?", {"answer": "Total revenue is $100M"}, "revenue_analysis")
    
    # Test 3: Cache hit
    result2 = cache.get(1, "What is the total revenue?", "revenue_analysis")
    print(f"Test 2 - Cached query: {result2}")
    
    # Test 4: Different query type (miss)
    result3 = cache.get(1, "What is the total revenue?", "general")
    print(f"Test 3 - Different query type: {result3}")
    
    # Test 5: Stats
    print("\n" + "=" * 70)
    print("CACHE STATISTICS")
    print("=" * 70)
    stats = cache.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print("\n" + "=" * 70)
    print("CACHED QUERIES")
    print("=" * 70)
    for query_info in cache.get_cached_queries():
        print(f"- {query_info['query']} (hits: {query_info['hit_count']}, expires in {query_info['expires_in_seconds']}s)")

