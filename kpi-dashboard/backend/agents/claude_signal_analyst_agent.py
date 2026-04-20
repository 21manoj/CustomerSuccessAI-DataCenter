"""
Claude Signal Analyst Agent — Anthropic-powered churn/expansion prediction
==========================================================================
Drop-in replacement for SignalAnalystAgent using Claude (Opus/Sonnet/Haiku)
instead of OpenAI GPT-4o.  Same SignalAnalystInput → SignalAnalystOutput
contract so the API layer can switch providers with a single parameter.
"""

import json
import time
import os
import sys
from typing import Optional

import anthropic

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from .models import (
    SignalAnalystInput,
    SignalAnalystOutput,
    OutcomeType,
    RiskDriver,
    GrowthDriver,
    RecommendedAction,
    PredictionConfidence,
)
from .prompts import SignalAnalystPrompts
from .decision_matrix import calculate_decision_matrix

from utils.error_handling import CircuitBreaker, log_performance
from utils.logging_config import initialize_logging, log_with_context, log_exception
from utils.llm_budget_controller import record_usage as _llm_record_usage

logger = initialize_logging()

# ============================================================
# CLAUDE PRICING  (as of Feb 2025)
# ============================================================
CLAUDE_PRICING = {
    "claude-opus-4-6":               {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-5-20250929":    {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5-20251001":     {"input":  0.80, "output":  4.00},
    # fallback for unknown models
    "default":                       {"input":  3.00, "output": 15.00},
}


class ClaudeSignalAnalystAgent:
    """
    Anthropic Claude agent with the same analyse() contract as the
    OpenAI SignalAnalystAgent.  Supports Opus 4.6 / Sonnet 4.5 / Haiku 4.5.
    """

    def __init__(
        self,
        anthropic_api_key: str,
        model: str = "claude-sonnet-4-5-20250929",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        customer_id: Optional[int] = None,
        account_id: Optional[str] = None,
    ):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.anthropic_api_key = anthropic_api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.customer_id = customer_id
        self.account_id = account_id

        # Cost tracking centralized via utils.llm_budget_controller.record_usage
        # (writes to llm_usage_log). No per-agent tracker instance needed.

        # Circuit breaker
        self.breaker = CircuitBreaker(failure_threshold=3, timeout=120)

        logger.info(
            "ClaudeSignalAnalystAgent initialized",
            extra={
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "customer_id": customer_id,
            },
        )

    # ────────────────────────────────────────────────────────
    #  Main entry point — same signature as OpenAI agent
    # ────────────────────────────────────────────────────────
    def analyze(self, input_data: SignalAnalystInput) -> SignalAnalystOutput:
        start_time = time.time()

        with log_with_context(
            account_id=input_data.account_id,
            customer_id=input_data.customer_id,
            analysis_type=input_data.analysis_type,
        ):
            try:
                logger.info(
                    "Starting Claude analysis",
                    extra={
                        "account_id": input_data.account_id,
                        "vertical": input_data.vertical_type,
                        "quantitative_signals": len(input_data.quantitative_signals),
                        "qualitative_signals": len(input_data.qualitative_signals),
                        "historical_patterns": len(input_data.historical_patterns),
                    },
                )

                # 1. Format signals
                quant_ctx = SignalAnalystPrompts.format_quantitative_signals(
                    [s.model_dump() for s in input_data.quantitative_signals]
                )
                qual_ctx = SignalAnalystPrompts.format_qualitative_signals(
                    [s.model_dump() for s in input_data.qualitative_signals]
                )
                hist_ctx = SignalAnalystPrompts.format_historical_patterns(
                    [s.model_dump() for s in input_data.historical_patterns]
                )

                # 2. Build prompts
                system_prompt = SignalAnalystPrompts.get_system_prompt(
                    input_data.vertical_type
                )
                # Append JSON-only instruction (Claude doesn't have response_format)
                system_prompt += (
                    "\n\nIMPORTANT: You MUST respond with a single valid JSON object "
                    "and nothing else. Do not include markdown code fences."
                )
                user_prompt = SignalAnalystPrompts.get_analysis_prompt(
                    account_id=input_data.account_id,
                    account_name=input_data.account_name or "Unknown",
                    account_arr=input_data.account_arr or 0,
                    health_score=input_data.health_score,
                    quantitative_context=quant_ctx,
                    qualitative_context=qual_ctx,
                    historical_context=hist_ctx,
                    analysis_type=input_data.analysis_type,
                    time_horizon_days=input_data.time_horizon_days,
                )

                # 3. Call Claude
                if self.breaker.is_open():
                    raise AnalysisError(
                        "Claude circuit breaker is open — service temporarily unavailable."
                    )

                try:
                    response = self._call_claude_with_tracking(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        customer_id=input_data.customer_id,
                        account_id=input_data.account_id,
                    )
                    self.breaker.record_success()
                except Exception:
                    self.breaker.record_failure()
                    raise

                # 4. Extract text content
                raw_response = response.content[0].text

                # 5. Parse into structured output
                output = self._parse_response(
                    raw_response=raw_response,
                    input_data=input_data,
                    model_used=self.model,
                )

                # 6. Timing
                duration_ms = int((time.time() - start_time) * 1000)
                output.analysis_duration_ms = duration_ms

                logger.info(
                    "Claude analysis completed",
                    extra={
                        "duration_ms": duration_ms,
                        "predicted_outcome": output.predicted_outcome,
                        "churn_probability": output.churn_probability,
                        "health_score": output.health_score,
                    },
                )
                return output

            except Exception as e:
                log_exception(
                    logger,
                    f"Claude analysis failed for account {input_data.account_id}",
                )
                raise AnalysisError(f"Claude analysis failed: {e}") from e

    # ────────────────────────────────────────────────────────
    #  Anthropic API call with retry + cost tracking
    # ────────────────────────────────────────────────────────
    def _call_claude_with_tracking(
        self,
        system_prompt: str,
        user_prompt: str,
        customer_id: int,
        account_id: str,
        _attempt: int = 0,
    ):
        max_attempts = 3
        start = time.time()

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            exec_ms = int((time.time() - start) * 1000)

            # Token usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            pricing = CLAUDE_PRICING.get(self.model, CLAUDE_PRICING["default"])
            input_cost = (input_tokens / 1_000_000) * pricing["input"]
            output_cost = (output_tokens / 1_000_000) * pricing["output"]
            total_cost = input_cost + output_cost

            logger.info(
                "Claude call completed",
                extra={
                    "model": self.model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": round(total_cost, 6),
                    "execution_time_ms": exec_ms,
                },
            )

            _llm_record_usage(
                customer_id=customer_id,
                module='claude_signal_analyst',
                tokens_in=input_tokens,
                tokens_out=output_tokens,
                model=self.model,
                cost_estimate=total_cost,
                success=True,
            )

            return response

        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError) as e:
            _llm_record_usage(
                customer_id=customer_id,
                module='claude_signal_analyst',
                tokens_in=0,
                tokens_out=0,
                model=self.model,
                cost_estimate=0.0,
                success=False,
                error_message=str(e)[:500],
            )

            if _attempt < max_attempts - 1:
                wait = 2 ** (_attempt + 1)
                logger.warning(f"Retrying Claude call in {wait}s (attempt {_attempt + 1})")
                time.sleep(wait)
                return self._call_claude_with_tracking(
                    system_prompt, user_prompt, customer_id, account_id, _attempt + 1
                )
            raise

    # ────────────────────────────────────────────────────────
    #  Response parsing (shared logic with OpenAI agent)
    # ────────────────────────────────────────────────────────
    def _parse_response(
        self,
        raw_response: str,
        input_data: SignalAnalystInput,
        model_used: str,
    ) -> SignalAnalystOutput:
        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)

            # Auto-set confidence level
            confidence_data = data["confidence"].copy()
            overall = confidence_data["overall_confidence"]
            if "confidence_level" not in confidence_data:
                if overall >= 0.90:
                    confidence_data["confidence_level"] = "very_high"
                elif overall >= 0.75:
                    confidence_data["confidence_level"] = "high"
                elif overall >= 0.60:
                    confidence_data["confidence_level"] = "medium"
                elif overall >= 0.40:
                    confidence_data["confidence_level"] = "low"
                else:
                    confidence_data["confidence_level"] = "very_low"

            output = SignalAnalystOutput(
                account_id=input_data.account_id,
                customer_id=input_data.customer_id,
                vertical_type=input_data.vertical_type,
                predicted_outcome=OutcomeType(data["predicted_outcome"]),
                churn_probability=float(data["churn_probability"]),
                expansion_probability=data.get("expansion_probability"),
                health_score=float(data["health_score"]),
                time_to_event=data.get("time_to_event"),
                risk_drivers=[RiskDriver(**rd) for rd in data.get("risk_drivers", [])],
                growth_drivers=[GrowthDriver(**gd) for gd in data.get("growth_drivers", [])],
                confidence=PredictionConfidence(**confidence_data),
                reasoning=data["reasoning"],
                key_insights=data.get("key_insights", []),
                recommended_actions=[
                    RecommendedAction(**ra) for ra in data.get("recommended_actions", [])
                ],
                signals_analyzed={
                    "quantitative": len(input_data.quantitative_signals),
                    "qualitative": len(input_data.qualitative_signals),
                    "historical": len(input_data.historical_patterns),
                },
                data_alignment=None,
                model_used=model_used,
            )

            # Decision matrix (reuse OpenAI key if available for gpt-4o-mini fallback)
            try:
                openai_key = os.getenv("OPENAI_API_KEY")
                decision_result = calculate_decision_matrix(
                    input_data=input_data,
                    openai_api_key=openai_key,
                    use_llm=bool(openai_key),
                )
                output.data_alignment = decision_result.to_dict()
            except Exception:
                try:
                    decision_result = calculate_decision_matrix(
                        input_data=input_data, openai_api_key=None, use_llm=False
                    )
                    output.data_alignment = decision_result.to_dict()
                except Exception:
                    output.data_alignment = None

            return output

        except json.JSONDecodeError as e:
            raise ResponseParseError(f"Invalid JSON from Claude: {e}") from e
        except Exception as e:
            raise ResponseParseError(f"Failed to parse Claude response: {e}") from e


# ============================================================
# MULTI-PROVIDER FACTORY
# ============================================================

def create_signal_analyst_agent(
    provider: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    customer_id: Optional[int] = None,
    account_id: Optional[str] = None,
):
    """
    Factory function — returns the right agent based on provider.

    Args:
        provider: 'openai' | 'anthropic' | 'claude'
        api_key:  Provider API key (falls back to env var)
        model:    Model override (defaults per provider)
    """
    provider = provider.lower()

    if provider in ("anthropic", "claude"):
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY required for Claude provider")
        return ClaudeSignalAnalystAgent(
            anthropic_api_key=key,
            model=model or "claude-sonnet-4-5-20250929",
            customer_id=customer_id,
            account_id=account_id,
        )
    else:
        # Default to OpenAI
        from .signal_analyst_agent import SignalAnalystAgent

        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY required for OpenAI provider")
        return SignalAnalystAgent(
            openai_api_key=key,
            model=model or "gpt-4o",
            customer_id=customer_id,
            account_id=account_id,
        )


# Reuse exceptions from the OpenAI agent
class AnalysisError(Exception):
    pass


class ResponseParseError(Exception):
    pass
