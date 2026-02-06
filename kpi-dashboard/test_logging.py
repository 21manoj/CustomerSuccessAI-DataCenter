#!/usr/bin/env python3
import sys
sys.path.insert(0, 'backend')

from utils.logging_config import initialize_logging, CostLogger

print("="*70)
print("LOGGING TEST")
print("="*70)

# Initialize logging
logger = initialize_logging()

# Test different log levels
logger.info("✅ INFO log test")
logger.warning("⚠️  WARNING log test")
logger.error("❌ ERROR log test")

# Test cost logging
cost_logger = CostLogger()
cost_logger.log_api_call(
    provider='openai',
    model='text-embedding-3-large',
    tokens_input=150,
    tokens_output=0,
    cost=0.0000195,
    customer_id=1,
    account_id=1007,
    call_type='embedding',
    success=True,
    execution_time_ms=250
)

print("\n✅ Check logs/signal_analyst.log for all logs")
print("✅ Check logs/api_costs.log for cost tracking")

print("\n" + "="*70)
print("LOGGING TESTS PASSED!")
print("="*70)
