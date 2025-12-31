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
import logging

logger = logging.getLogger(__name__)


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
        max_tokens: int = 3000
    ):
        """
        Initialize Signal Analyst Agent
        
        Args:
            openai_api_key: OpenAI API key
            model: Model to use (gpt-4o, gpt-4-turbo, etc.)
            temperature: Temperature for generation (0.0-1.0, lower = more deterministic)
            max_tokens: Maximum tokens in response
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        logger.info(f"Initialized SignalAnalystAgent with model={model}")
    
    def analyze(
        self,
        input_data: SignalAnalystInput
    ) -> SignalAnalystOutput:
        """
        Main analysis method - orchestrates the prediction
        
        Args:
            input_data: Validated input containing account info and signals
            
        Returns:
            SignalAnalystOutput: Structured prediction with reasoning and actions
        """
        start_time = time.time()
        
        try:
            logger.info(
                f"Starting analysis for account_id={input_data.account_id}, "
                f"vertical={input_data.vertical_type}, "
                f"analysis_type={input_data.analysis_type}"
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
                quantitative_context=quantitative_context,
                qualitative_context=qualitative_context,
                historical_context=historical_context,
                analysis_type=input_data.analysis_type,
                time_horizon_days=input_data.time_horizon_days
            )
            
            # Step 3: Call OpenAI
            logger.debug(f"Calling OpenAI with {len(user_prompt)} char prompt")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}  # Force JSON output
            )
            
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
                f"Analysis completed for account_id={input_data.account_id} in {duration_ms}ms. "
                f"Predicted outcome: {output.predicted_outcome}, "
                f"Churn prob: {output.churn_probability}%, "
                f"Health: {output.health_score}"
            )
            
            return output
            
        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}", exc_info=True)
            raise AnalysisError(f"Signal analysis failed: {str(e)}") from e
    
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
                
                # Metadata
                model_used=model_used
            )
            
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

