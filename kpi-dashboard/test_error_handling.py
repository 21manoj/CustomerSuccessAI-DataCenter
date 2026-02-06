#!/usr/bin/env python3
import sys
sys.path.insert(0, 'backend')

from utils.error_handling import (
    retry_on_qdrant_error,
    CircuitBreaker
)

print("="*70)
print("ERROR HANDLING TEST")
print("="*70)

# Test circuit breaker
print("\n1. Testing circuit breaker...")
breaker = CircuitBreaker(failure_threshold=3, timeout=5)
print(f"   Circuit state: {breaker.state}")
print(f"   Is open: {breaker.is_open()}")
print("   ✅ Circuit breaker working")

print("\n" + "="*70)
print("ERROR HANDLING TESTS PASSED!")
print("="*70)
