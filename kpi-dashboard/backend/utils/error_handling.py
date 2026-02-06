"""
Error Handling Module for Signal Analyst
Provides retry logic, graceful degradation, and comprehensive error handling
"""

import time
import logging
from functools import wraps
from typing import Optional, Callable, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from qdrant_client.http.exceptions import UnexpectedResponse, ResponseHandlingException
from openai import OpenAIError, RateLimitError, APIError
import anthropic

# Setup logger
logger = logging.getLogger(__name__)


# =============================================================================
# RETRY DECORATORS
# =============================================================================

def retry_on_qdrant_error(max_attempts=3):
    """
    Retry decorator for Qdrant operations
    
    Usage:
        @retry_on_qdrant_error(max_attempts=3)
        def search_qdrant(...):
            return qdrant.search(...)
    """
    return retry(
        retry=retry_if_exception_type((UnexpectedResponse, ResponseHandlingException, ConnectionError)),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


def retry_on_openai_error(max_attempts=3):
    """
    Retry decorator for OpenAI API calls
    
    Usage:
        @retry_on_openai_error(max_attempts=3)
        def generate_embedding(...):
            return openai.embeddings.create(...)
    """
    return retry(
        retry=retry_if_exception_type((RateLimitError, APIError, ConnectionError)),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


def retry_on_claude_error(max_attempts=3):
    """
    Retry decorator for Claude API calls
    
    Usage:
        @retry_on_claude_error(max_attempts=3)
        def analyze_with_claude(...):
            return claude.messages.create(...)
    """
    return retry(
        retry=retry_if_exception_type((anthropic.APIError, anthropic.RateLimitError, ConnectionError)),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


# =============================================================================
# GRACEFUL DEGRADATION
# =============================================================================

class SignalAnalystFallback:
    """
    Provides fallback strategies when services fail
    """
    
    @staticmethod
    def qdrant_to_postgres_fallback(db_engine, account_id: int, limit: int = 10):
        """
        Fallback: When Qdrant fails, get signals from PostgreSQL
        
        Returns signals from qualitative_signals table ordered by date
        """
        from sqlalchemy import text
        
        logger.warning(f"Qdrant unavailable, falling back to PostgreSQL for account {account_id}")
        
        try:
            with db_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        signal_id,
                        subject,
                        summary,
                        sentiment,
                        priority,
                        date,
                        signal_type
                    FROM qualitative_signals
                    WHERE account_id = :account_id
                    ORDER BY date DESC
                    LIMIT :limit
                """), {"account_id": account_id, "limit": limit})
                
                signals = result.fetchall()
                
                logger.info(f"Fallback retrieved {len(signals)} signals from PostgreSQL")
                
                # Convert to format compatible with Qdrant search results
                fallback_results = []
                for sig in signals:
                    fallback_results.append({
                        'score': 1.0,  # No relevance score from SQL
                        'payload': {
                            'signal_id': sig.signal_id,
                            'subject': sig.subject,
                            'summary': sig.summary,
                            'sentiment': sig.sentiment,
                            'priority': sig.priority,
                            'date': str(sig.date),
                            'signal_type': sig.signal_type,
                            'source': 'postgres_fallback'
                        }
                    })
                
                return fallback_results
        
        except Exception as e:
            logger.error(f"PostgreSQL fallback also failed: {e}")
            return []
    
    @staticmethod
    def simple_analysis_fallback(account_name: str, kpis: list, signals: list):
        """
        Fallback: When Claude API fails, provide rule-based analysis
        
        Returns a simple analysis based on KPI thresholds
        """
        logger.warning(f"Claude API unavailable, using rule-based fallback for {account_name}")
        
        # Count critical KPIs
        critical_kpis = [kpi for kpi in kpis if hasattr(kpi, 'status') and kpi.status == 'critical']
        warning_kpis = [kpi for kpi in kpis if hasattr(kpi, 'status') and kpi.status == 'warning']
        
        # Count negative signals
        negative_signals = [s for s in signals if s.get('payload', {}).get('sentiment') == 'negative']
        
        # Determine health status
        if len(critical_kpis) >= 3 or len(negative_signals) >= 2:
            health_status = "Critical"
            churn_risk = "High (60-80%)"
        elif len(critical_kpis) >= 1 or len(warning_kpis) >= 3:
            health_status = "At-Risk"
            churn_risk = "Medium (30-60%)"
        else:
            health_status = "Healthy"
            churn_risk = "Low (<30%)"
        
        # Simple rule-based response
        response = f"""
[FALLBACK ANALYSIS - Rule-Based]

Account: {account_name}
Health Status: {health_status}

Key Findings:
- Critical KPIs: {len(critical_kpis)}
- Warning KPIs: {len(warning_kpis)}
- Negative Signals: {len(negative_signals)}

Risk Assessment:
- Churn Risk: {churn_risk}
- Recommendation: {"Immediate CSM intervention required" if health_status == "Critical" else "Monitor closely"}

Note: This is a simplified analysis. Claude API is currently unavailable.
Full AI-powered analysis will resume when service is restored.
"""
        
        return response


# =============================================================================
# ERROR CONTEXT MANAGER
# =============================================================================

class ErrorContext:
    """
    Context manager for handling errors with logging and fallback
    
    Usage:
        with ErrorContext("Searching Qdrant", fallback_func=fallback_to_postgres):
            results = qdrant.search(...)
    """
    
    def __init__(self, operation_name: str, fallback_func: Optional[Callable] = None, 
                 fallback_args: tuple = (), fallback_kwargs: dict = None):
        self.operation_name = operation_name
        self.fallback_func = fallback_func
        self.fallback_args = fallback_args
        self.fallback_kwargs = fallback_kwargs or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f"Starting: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        
        if exc_type is None:
            logger.debug(f"Completed: {self.operation_name} in {elapsed:.2f}s")
            return False
        
        # Error occurred
        logger.error(
            f"Error in {self.operation_name} after {elapsed:.2f}s: {exc_type.__name__}: {exc_val}",
            exc_info=True
        )
        
        # Try fallback if provided
        if self.fallback_func:
            try:
                logger.info(f"Attempting fallback for {self.operation_name}")
                result = self.fallback_func(*self.fallback_args, **self.fallback_kwargs)
                logger.info(f"Fallback succeeded for {self.operation_name}")
                # Store result for retrieval
                self.fallback_result = result
                return True  # Suppress the exception
            except Exception as fallback_error:
                logger.error(f"Fallback also failed for {self.operation_name}: {fallback_error}")
        
        return False  # Re-raise the original exception


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures
    
    Usage:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        
        if breaker.is_open():
            # Skip expensive operation
            return fallback_value
        
        try:
            result = expensive_operation()
            breaker.record_success()
        except Exception:
            breaker.record_failure()
            raise
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
    
    def is_open(self):
        """Check if circuit breaker is open (blocking calls)"""
        if self.state == 'closed':
            return False
        
        if self.state == 'open':
            # Check if timeout has passed
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = 'half-open'
                logger.info("Circuit breaker entering half-open state")
                return False
            return True
        
        # half-open state
        return False
    
    def record_success(self):
        """Record successful operation"""
        if self.state == 'half-open':
            logger.info("Circuit breaker closing after successful operation")
        self.failures = 0
        self.state = 'closed'
    
    def record_failure(self):
        """Record failed operation"""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = 'open'
            logger.warning(f"Circuit breaker opened after {self.failures} failures")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def safe_api_call(func: Callable, *args, fallback_value: Any = None, **kwargs):
    """
    Safely call an API function with fallback value on error
    
    Usage:
        result = safe_api_call(qdrant.search, collection="signals", fallback_value=[])
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"API call failed: {func.__name__}: {e}")
        return fallback_value


def log_performance(operation_name: str):
    """
    Decorator to log function performance
    
    Usage:
        @log_performance("Embedding generation")
        def generate_embeddings(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"{operation_name} completed in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"{operation_name} failed after {elapsed:.2f}s: {e}")
                raise
        return wrapper
    return decorator


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Retry on Qdrant error
    @retry_on_qdrant_error(max_attempts=3)
    def search_with_retry(qdrant_client, collection_name):
        return qdrant_client.search(collection_name, query_vector=[...], limit=10)
    
    # Example: Error context with fallback
    with ErrorContext("Vector search", fallback_func=lambda: []):
        results = search_with_retry(qdrant, "signals")
    
    # Example: Circuit breaker
    breaker = CircuitBreaker(failure_threshold=5, timeout=60)
    
    if not breaker.is_open():
        try:
            result = expensive_operation()
            breaker.record_success()
        except Exception:
            breaker.record_failure()
