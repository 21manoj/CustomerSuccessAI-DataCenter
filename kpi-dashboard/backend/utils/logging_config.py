"""
Logging Configuration for Signal Analyst
Provides structured JSON logging with rotation and multiple outputs
"""

import logging
import logging.handlers
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    import structlog  # Optional: structured logging
except ImportError:  # pragma: no cover - runtime fallback when structlog absent
    structlog = None


# =============================================================================
# CONFIGURATION
# =============================================================================

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "signal_analyst.log"
ERROR_LOG_FILE = LOG_DIR / "signal_analyst_errors.log"
COST_LOG_FILE = LOG_DIR / "api_costs.log"

LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# =============================================================================
# STRUCTURED LOGGING SETUP
# =============================================================================

def setup_structured_logging():
    """
    Configure structlog for JSON-formatted logging
    
    Benefits:
    - Machine-readable logs
    - Easy parsing/analysis
    - Contextual information
    If structlog is not installed, this becomes a no-op and the
    standard logging setup is still available.
    """
    if structlog is None:
        # Fallback: do nothing; callers can still use standard logging.
        return

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# =============================================================================
# STANDARD LOGGING SETUP
# =============================================================================

def setup_logging(log_level=LOG_LEVEL):
    """
    Setup standard Python logging with file rotation
    
    Features:
    - Console output (INFO and above)
    - File logging with rotation (all levels)
    - Separate error log (ERROR and above)
    - 30-day retention
    """
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation (all levels)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=30  # Keep 30 files (30 days if daily rotation)
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler (ERROR and above)
    error_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=30
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    return root_logger


# =============================================================================
# SPECIALIZED LOGGERS
# =============================================================================

class CostLogger:
    """
    Specialized logger for API cost tracking
    
    Logs to separate file for easy cost analysis
    """
    
    def __init__(self):
        self.logger = logging.getLogger('cost_tracker')
        self.logger.setLevel(logging.INFO)
        
        # Dedicated cost log file
        handler = logging.handlers.RotatingFileHandler(
            COST_LOG_FILE,
            maxBytes=10 * 1024 * 1024,
            backupCount=90  # Keep 90 days of cost data
        )
        
        # JSON format for easy parsing
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
    
    def log_api_call(self, provider, model, tokens_input, tokens_output, cost, 
                     customer_id=None, account_id=None, call_type=None, 
                     success=True, execution_time_ms=None):
        """
        Log an API call with cost information
        
        Args:
            provider: 'openai' or 'anthropic'
            model: Model name (e.g., 'text-embedding-3-large', 'claude-sonnet-4')
            tokens_input: Input tokens used
            tokens_output: Output tokens generated
            cost: Total cost in USD
            customer_id: Customer ID
            account_id: Account ID being analyzed
            call_type: 'embedding', 'claude_analysis', 'vector_search'
            success: Whether the call succeeded
            execution_time_ms: Time taken in milliseconds
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'provider': provider,
            'model': model,
            'tokens_input': tokens_input,
            'tokens_output': tokens_output,
            'tokens_total': tokens_input + tokens_output,
            'cost': round(cost, 6),
            'customer_id': customer_id,
            'account_id': account_id,
            'call_type': call_type,
            'success': success,
            'execution_time_ms': execution_time_ms
        }
        
        self.logger.info(json.dumps(log_entry))


class PerformanceLogger:
    """
    Logger for performance metrics
    
    Track execution times, throughput, resource usage
    """
    
    def __init__(self):
        self.logger = logging.getLogger('performance')
    
    def log_operation(self, operation, duration_ms, account_id=None, 
                     records_processed=None, success=True):
        """
        Log operation performance
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            account_id: Account being processed
            records_processed: Number of records processed
            success: Whether operation succeeded
        """
        self.logger.info(
            f"Performance: {operation}",
            extra={
                'operation': operation,
                'duration_ms': duration_ms,
                'account_id': account_id,
                'records_processed': records_processed,
                'success': success,
                'timestamp': datetime.utcnow().isoformat()
            }
        )


# =============================================================================
# CONTEXT LOGGERS
# =============================================================================

def get_logger(name):
    """
    Get a logger with the specified name.

    If structlog is available, returns a structlog logger; otherwise
    falls back to the standard library logger.
    """
    if structlog is None:
        return logging.getLogger(name)
    return structlog.get_logger(name)


def log_with_context(**context):
    """
    Add context to all subsequent log calls.

    When structlog is unavailable, this yields a standard logger
    without structured context binding (best-effort fallback).
    """
    from contextlib import contextmanager

    @contextmanager
    def _context_manager():
        if structlog is None:
            # Fallback: plain stdlib logger
            logger = logging.getLogger()
            yield logger
            return

        # Get logger and bind context (structlog path)
        logger = structlog.get_logger()
        bound_logger = logger.bind(**context)
        try:
            yield bound_logger
        finally:
            # Context is automatically cleared when exiting the context
            pass

    return _context_manager()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def log_exception(logger, message, exc_info=True):
    """
    Log an exception with full stack trace
    
    Usage:
        try:
            risky_operation()
        except Exception as e:
            log_exception(logger, "Operation failed", exc_info=True)
    """
    logger.error(message, exc_info=exc_info)


def log_api_metrics(logger, operation, start_time, success=True, **kwargs):
    """
    Log API call metrics
    
    Usage:
        start = time.time()
        result = api_call()
        log_api_metrics(logger, "Qdrant search", start, account_id=1007)
    """
    import time
    duration = (time.time() - start_time) * 1000  # Convert to ms
    
    logger.info(
        f"API call: {operation}",
        duration_ms=round(duration, 2),
        success=success,
        **kwargs
    )


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize_logging(use_structured=False, log_level=LOG_LEVEL):
    """
    Initialize logging system
    
    Args:
        use_structured: Use structured (JSON) logging
        log_level: Logging level (INFO, DEBUG, etc.)
    
    Returns:
        Root logger
    """
    if use_structured:
        setup_structured_logging()
    
    logger = setup_logging(log_level)
    
    logger.info("="*70)
    logger.info("Logging initialized")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info(f"Error log: {ERROR_LOG_FILE}")
    logger.info(f"Cost log: {COST_LOG_FILE}")
    logger.info("="*70)
    
    return logger


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Initialize logging
    logger = initialize_logging()
    
    # Get specialized loggers
    cost_logger = CostLogger()
    perf_logger = PerformanceLogger()
    
    # Example: Log API cost
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
    
    # Example: Log performance
    perf_logger.log_operation(
        operation='signal_analysis',
        duration_ms=3200,
        account_id=1007,
        records_processed=59,
        success=True
    )
    
    # Example: Structured logging
    app_logger = get_logger('signal_analyst')
    app_logger.info("Account analysis started", account_id=1007, customer_id=1)
    
    # Example: Error logging
    try:
        raise ValueError("Example error")
    except Exception as e:
        log_exception(logger, "An error occurred")
