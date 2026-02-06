"""
Signal Analyst Agent - Core AI agent for churn/expansion prediction

This agent analyzes account signals to predict outcomes and recommend actions.
"""

import json
import time
from typing import Dict, Any, Optional
from openai import OpenAI

from .models import (
    SignalAnalystInput,
    SignalAnalystOutput,
    SignalData,
    OutcomeType,
    RiskDriver,
    GrowthDriver,
    RecommendedAction,
    PredictionConfidence
)
from .prompts import SignalAnalystPrompts
from .decision_matrix import calculate_decision_matrix
import logging

# ============================================================================
# PRODUCTION HARDENING IMPORTS
# ============================================================================
import sys
import os

# Add parent directory to path to import from utils/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.error_handling import (
    retry_on_openai_error,
    CircuitBreaker,
    log_performance
)
from utils.logging_config import (
    initialize_logging,
    log_with_context,
    log_exception
)
from utils.cost_tracker import CostTracker
from sqlalchemy import create_engine

# Replace basic logger with structured logger
structured_logger = initialize_logging()
logger = structured_logger  # Keep same variable name for compatibility


class SignalAnalystAgent:
    """
    AI Agent for analyzing customer signals and predicting outcomes
    
    Capabilities:
    - Churn risk prediction
    - Expansion opportunity identification
    - Health score calculation
    - Actionable recommendations
    """
    
    def __init__(
        self,
        openai_api_key: str,
        model: str = "gpt-4o",
        temperature: float = 0.3,
        max_tokens: int = 3000,
        customer_id: Optional[int] = None,
        account_id: Optional[str] = None
    ):
        """
        Initialize Signal Analyst Agent with production hardening
        
        Args:
            openai_api_key: OpenAI API key
            model: Model to use (gpt-4o, gpt-4-turbo, etc.)
            temperature: Temperature for generation (0.0-1.0)
            max_tokens: Maximum tokens in response
            customer_id: Customer ID for cost tracking (REQUIRED for tracking)
            account_id: Account ID for cost tracking (optional)
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.openai_api_key = openai_api_key  # Store for decision matrix
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.customer_id = customer_id
        self.account_id = account_id
        
        # Initialize cost tracker
        try:
            db_url = os.getenv("DATABASE_URL")
            if db_url:
                engine = create_engine(db_url)
                self.cost_tracker = CostTracker(engine)
                logger.info("Cost tracker initialized successfully")
            else:
                logger.warning("DATABASE_URL not set, cost tracking disabled")
                self.cost_tracker = None
        except Exception as e:
            logger.warning(f"Failed to initialize cost tracker: {e}", exc_info=True)
            self.cost_tracker = None
        
        # Initialize circuit breaker for OpenAI
        self.openai_breaker = CircuitBreaker(
            failure_threshold=3,  # Open after 3 failures
            timeout=120  # Wait 2 minutes before retry
        )
        
        logger.info(
            f"SignalAnalystAgent initialized with model={model}",
            extra={
                'model': model,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'cost_tracking_enabled': self.cost_tracker is not None,
                'customer_id': customer_id
            }
        )
    
    def analyze(
        self,
        input_data: SignalAnalystInput
    ) -> SignalAnalystOutput:
        """
        Main analysis method with production hardening
        
        Includes:
        - Structured logging with context
        - Retry logic for API calls
        - Cost tracking to database
        - Circuit breaker protection
        
        Args:
            input_data: Validated input containing account info and signals
            
        Returns:
            SignalAnalystOutput: Structured prediction with reasoning and actions
        """
        start_time = time.time()
        
        # Add context to all logs in this analysis
        with log_with_context(
            account_id=input_data.account_id,
            customer_id=input_data.customer_id,
            analysis_type=input_data.analysis_type
        ):
            try:
                logger.info(
                    "Starting Signal Analyst analysis",
                    extra={
                        'account_id': input_data.account_id,
                        'account_name': input_data.account_name,
                        'vertical': input_data.vertical_type,
                        'analysis_type': input_data.analysis_type,
                        'time_horizon_days': input_data.time_horizon_days,
                        'quantitative_signals': len(input_data.quantitative_signals),
                        'qualitative_signals': len(input_data.qualitative_signals),
                        'historical_patterns': len(input_data.historical_patterns)
                    }
                )
                
                # Step 1: Format signals for prompt
                quantitative_context = SignalAnalystPrompts.format_quantitative_signals(
                    [s.model_dump() for s in input_data.quantitative_signals]
                )
                
                qualitative_context = SignalAnalystPrompts.format_qualitative_signals(
                    [s.model_dump() for s in input_data.qualitative_signals]
                )
                
                historical_context = SignalAnalystPrompts.format_historical_patterns(
                    [s.model_dump() for s in input_data.historical_patterns]
                )
                
                # Step 2: Build prompts
                system_prompt = SignalAnalystPrompts.get_system_prompt(
                    input_data.vertical_type
                )
                
                user_prompt = SignalAnalystPrompts.get_analysis_prompt(
                    account_id=input_data.account_id,
                    account_name=input_data.account_name or "Unknown",
                    account_arr=input_data.account_arr or 0,
                    health_score=input_data.health_score,
                    quantitative_context=quantitative_context,
                    qualitative_context=qualitative_context,
                    historical_context=historical_context,
                    analysis_type=input_data.analysis_type,
                    time_horizon_days=input_data.time_horizon_days
                )
                
                # Step 3: Call OpenAI with retry and cost tracking
                logger.info(
                    "Calling OpenAI for analysis",
                    extra={
                        'prompt_length': len(user_prompt),
                        'model': self.model,
                        'account_id': input_data.account_id
                    }
                )
                
                # Check circuit breaker
                if self.openai_breaker.is_open():
                    logger.error(
                        "OpenAI circuit breaker is open",
                        extra={'failure_count': self.openai_breaker.failures}
                    )
                    raise AnalysisError(
                        "OpenAI service temporarily unavailable due to repeated failures. "
                        "Please try again in a few minutes."
                    )
                
                try:
                    # Call OpenAI with retry and cost tracking
                    response = self._call_openai_with_tracking(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        customer_id=input_data.customer_id,
                        account_id=input_data.account_id
                    )
                    
                    # Record success in circuit breaker
                    self.openai_breaker.record_success()
                    
                    logger.debug("OpenAI call successful")
                    
                except Exception as e:
                    # Record failure in circuit breaker
                    self.openai_breaker.record_failure()
                    
                    logger.error(
                        f"OpenAI call failed: {e}",
                        extra={'error_type': type(e).__name__},
                        exc_info=True
                    )
                    raise
                
                # Step 4: Parse response
                raw_response = response.choices[0].message.content
                
                logger.debug(f"Received OpenAI response: {len(raw_response)} chars")
                
                # Step 5: Build structured output
                output = self._parse_response(
                    raw_response=raw_response,
                    input_data=input_data,
                    model_used=self.model
                )
                
                # Step 6: Add timing
                duration_ms = int((time.time() - start_time) * 1000)
                output.analysis_duration_ms = duration_ms
                
                logger.info(
                    "Analysis completed successfully",
                    extra={
                        'account_id': input_data.account_id,
                        'duration_ms': duration_ms,
                        'predicted_outcome': output.predicted_outcome,
                        'churn_probability': output.churn_probability,
                        'health_score': output.health_score,
                        'confidence_level': output.confidence.confidence_level,
                        'actions_count': len(output.recommended_actions)
                    }
                )
                
                return output
                
            except Exception as e:
                log_exception(logger, f"Signal analysis failed for account {input_data.account_id}")
                raise AnalysisError(f"Signal analysis failed: {str(e)}") from e
    
    @retry_on_openai_error(max_attempts=3)
    def _call_openai_with_tracking(
        self,
        system_prompt: str,
        user_prompt: str,
        customer_id: int,
        account_id: str
    ):
        """
        Call OpenAI GPT-4o with retry logic and cost tracking
        
        This method:
        - Retries up to 3 times on transient failures
        - Tracks token usage and costs to database
        - Logs execution metrics
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            customer_id: Customer ID for cost tracking
            account_id: Account ID for cost tracking
            
        Returns:
            OpenAI ChatCompletion response
            
        Raises:
            Exception: If all retries fail
        """
        start_time = time.time()
        
        try:
            # Make OpenAI API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Get token usage
            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            
            # Calculate cost for GPT-4o
            # Pricing as of Jan 2025: $2.50 per 1M input, $10.00 per 1M output
            input_cost = (input_tokens / 1_000_000) * 2.50
            output_cost = (output_tokens / 1_000_000) * 10.00
            total_cost = input_cost + output_cost
            
            # Log metrics
            logger.info(
                "OpenAI call completed",
                extra={
                    'model': self.model,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': total_tokens,
                    'cost_usd': round(total_cost, 6),
                    'execution_time_ms': execution_time_ms,
                    'customer_id': customer_id,
                    'account_id': account_id
                }
            )
            
            # Track cost to database
            if self.cost_tracker:
                try:
                    self.cost_tracker.log_api_call(
                        provider='openai',
                        model=self.model,
                        call_type='chat_completion',
                        tokens_input=input_tokens,
                        tokens_output=output_tokens,
                        cost=total_cost,
                        customer_id=customer_id,
                        account_id=int(account_id) if account_id else None,
                        success=True,
                        error_message=None,
                        execution_time_ms=execution_time_ms
                    )
                except Exception as e:
                    logger.warning(f"Failed to log cost to database: {e}")
            
            return response
            
        except Exception as e:
            # Calculate execution time even on failure
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Log failure to database
            if self.cost_tracker:
                try:
                    self.cost_tracker.log_api_call(
                        provider='openai',
                        model=self.model,
                        call_type='chat_completion',
                        tokens_input=0,
                        tokens_output=0,
                        cost=0.0,
                        customer_id=customer_id,
                        account_id=int(account_id) if account_id else None,
                        success=False,
                        error_message=str(e)[:500],  # Truncate error message
                        execution_time_ms=execution_time_ms
                    )
                except Exception as log_error:
                    logger.warning(f"Failed to log error to database: {log_error}")
            
            # Re-raise to trigger retry
            raise
    
    def _parse_response(
        self,
        raw_response: str,
        input_data: SignalAnalystInput,
        model_used: str
    ) -> SignalAnalystOutput:
        """
        Parse OpenAI JSON response into structured output
        
        Handles cases where JSON might be wrapped in markdown code blocks
        """
        try:
            # Clean response (remove markdown code blocks if present)
            cleaned = raw_response.strip()
            
            # Remove ```json and ``` if present
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            cleaned = cleaned.strip()
            
            # Parse JSON
            data = json.loads(cleaned)
            
            # Build Pydantic model with validation
            # Handle confidence_level separately since it needs to be set from overall_confidence
            confidence_data = data['confidence'].copy()
            overall_confidence = confidence_data['overall_confidence']
            
            # Auto-set confidence level based on overall_confidence if not provided
            if 'confidence_level' not in confidence_data:
                if overall_confidence >= 0.90:
                    confidence_level = "very_high"
                elif overall_confidence >= 0.75:
                    confidence_level = "high"
                elif overall_confidence >= 0.60:
                    confidence_level = "medium"
                elif overall_confidence >= 0.40:
                    confidence_level = "low"
                else:
                    confidence_level = "very_low"
                confidence_data['confidence_level'] = confidence_level
            
            output = SignalAnalystOutput(
                account_id=input_data.account_id,
                customer_id=input_data.customer_id,
                vertical_type=input_data.vertical_type,
                
                # Predictions
                predicted_outcome=OutcomeType(data['predicted_outcome']),
                churn_probability=float(data['churn_probability']),
                expansion_probability=data.get('expansion_probability'),
                health_score=float(data['health_score']),
                time_to_event=data.get('time_to_event'),
                
                # Risk drivers
                risk_drivers=[
                    RiskDriver(**rd) for rd in data.get('risk_drivers', [])
                ],
                
                # Growth drivers
                growth_drivers=[
                    GrowthDriver(**gd) for gd in data.get('growth_drivers', [])
                ],
                
                # Confidence
                confidence=PredictionConfidence(**confidence_data),
                
                # Reasoning
                reasoning=data['reasoning'],
                key_insights=data.get('key_insights', []),
                
                # Actions
                recommended_actions=[
                    RecommendedAction(**ra) for ra in data.get('recommended_actions', [])
                ],
                
                # Signal breakdown
                signals_analyzed={
                    "quantitative": len(input_data.quantitative_signals),
                    "qualitative": len(input_data.qualitative_signals),
                    "historical": len(input_data.historical_patterns)
                },
                
                # Decision matrix (quantitative vs qualitative alignment)
                data_alignment=None,  # Will be set after decision matrix calculation
                
                # Metadata
                model_used=model_used
            )
            
            # Calculate decision matrix (quantitative vs qualitative alignment) - using LLM
            try:
                # Use LLM for decision matrix (better context, handles complex signals, future-ready)
                decision_matrix_result = calculate_decision_matrix(
                    input_data=input_data,
                    openai_api_key=self.openai_api_key,  # Use same API key as main analysis
                    use_llm=True  # Use LLM for nuanced correlation and better context
                )
                output.data_alignment = decision_matrix_result.to_dict()
                logger.info(f"✅ Decision matrix (LLM): {decision_matrix_result.alignment.value} (confidence: {decision_matrix_result.confidence:.2f})")
            except Exception as e:
                logger.warning(f"LLM decision matrix failed, using rule-based fallback: {e}", exc_info=True)
                # Fallback to rule-based if LLM fails
                try:
                    decision_matrix_result = calculate_decision_matrix(
                        input_data=input_data,
                        openai_api_key=None,
                        use_llm=False  # Fallback to rule-based
                    )
                    output.data_alignment = decision_matrix_result.to_dict()
                    logger.info(f"✅ Decision matrix (rule-based fallback): {decision_matrix_result.alignment.value}")
                except Exception as e2:
                    logger.error(f"Failed to calculate decision matrix even with fallback: {e2}", exc_info=True)
                    output.data_alignment = None
            
            return output
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {raw_response[:500]}...")
            raise ResponseParseError(f"Invalid JSON from AI: {str(e)}") from e
        
        except Exception as e:
            logger.error(f"Failed to build output model: {e}")
            raise ResponseParseError(f"Failed to parse AI response: {str(e)}") from e


class AnalysisError(Exception):
    """Raised when analysis fails"""
    pass


class ResponseParseError(Exception):
    """Raised when AI response cannot be parsed"""
    pass

