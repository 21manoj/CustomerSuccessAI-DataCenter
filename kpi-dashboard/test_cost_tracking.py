#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, 'backend')

from dotenv import load_dotenv
from sqlalchemy import create_engine
from utils.cost_tracker import CostTracker, CostReporter

load_dotenv()

print("="*70)
print("COST TRACKING TEST")
print("="*70)

# Initialize
engine = create_engine(os.getenv("DATABASE_URL"))
tracker = CostTracker(engine)

# Test: Log API call
print("\n1. Testing API call logging...")
tracker.log_api_call(
    provider='openai',
    model='text-embedding-3-large',
    call_type='embedding',
    tokens_input=150,
    tokens_output=0,
    cost=0.0000195,
    customer_id=1,
    account_id=1007,
    success=True,
    execution_time_ms=250
)
print("   ✅ API call logged to database")

# Test: Get reports
print("\n2. Testing cost reports...")
reporter = CostReporter(engine)
daily_report = reporter.get_daily_costs()
print(f"   ✅ Today's total cost: ${daily_report['total_cost']:.6f}")

print("\n" + "="*70)
print(" TRACKING TESTS PASSED!")
print("="*70)
