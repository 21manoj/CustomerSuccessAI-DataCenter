#!/usr/bin/env python3
"""
Agentic Loop — Plan → Act → Observe → Reflect
================================================
Wraps any agent in a multi-step reasoning loop that:
  1. ANALYZE  — Run the core agent (e.g., Signal Analyst)
  2. EVALUATE — Check confidence. If LOW → gather more data
  3. ENRICH   — Call tools (financial projection, memory recall, feedback history)
  4. QUANTIFY — Put $ on every recommendation via Power of 1
  5. DECIDE   — confidence > threshold → proceed. Else → flag for review
  6. ACT      — Auto-trigger playbook OR queue for human approval

Uses:
  - AgentState (agent_memory.py) for persistence between steps
  - AgentToolRegistry for tool invocation
  - EventPublisher for inter-agent events

This is NOT a generic agent framework — it's purpose-built for CS Pulse agents.
"""

import json
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================
# LOOP CONFIGURATION
# ============================================================

class LoopStep(str, Enum):
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    ENRICH = "enrich"
    QUANTIFY = "quantify"
    DECIDE = "decide"
    ACT = "act"
    COMPLETE = "complete"


# Confidence thresholds for decision-making
CONFIDENCE_AUTO_EXECUTE = 0.85   # Auto-execute playbook
CONFIDENCE_NEEDS_REVIEW = 0.60   # Needs human approval
# Below 0.60 → auto-reject (confidence too low)

# Max enrichment iterations (prevents infinite loops)
MAX_ENRICH_ITERATIONS = 2


# ============================================================
# LOOP STATE
# ============================================================

@dataclass
class EnrichedAction:
    """A recommended action enriched with $ impact."""
    action: str
    priority: str
    owner: str
    expected_impact: str
    dollar_impact: Optional[float] = None
    power_of_1_metric: Optional[str] = None
    playbook_id: Optional[str] = None
    confidence: float = 0.0
    deadline_days: Optional[int] = None


@dataclass
class LoopState:
    """State of the agentic loop — persisted between steps."""
    customer_id: int
    account_id: str
    current_step: LoopStep = LoopStep.ANALYZE
    iteration: int = 0

    # Analysis results (from Step 1)
    initial_analysis: Optional[Dict] = None
    predicted_outcome: Optional[str] = None
    churn_probability: float = 0.0
    expansion_probability: float = 0.0
    confidence: float = 0.0
    confidence_level: str = "low"

    # Enrichment results (from Step 3)
    enrichment_data: Dict = field(default_factory=dict)
    tools_called: List[str] = field(default_factory=list)

    # Quantified actions (from Step 4)
    enriched_actions: List[Dict] = field(default_factory=list)
    total_dollar_impact: float = 0.0

    # Decision (from Step 5)
    decision: str = "pending"  # auto_execute, needs_review, rejected
    decision_reason: str = ""

    # Outcome (from Step 6)
    actions_taken: List[Dict] = field(default_factory=list)

    # Timing
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    duration_ms: int = 0


# ============================================================
# AGENTIC LOOP
# ============================================================

class AgenticLoop:
    """
    Multi-step reasoning loop for CS Pulse agents.

    Usage:
        loop = AgenticLoop(
            analyze_fn=signal_analyst.analyze,
            tool_registry=get_tool_registry(),
            event_publisher=event_publisher,
        )
        result = loop.run(customer_id=1, account_id='acct-123', input_data=...)
    """

    def __init__(
        self,
        analyze_fn: Callable,
        tool_registry=None,
        event_publisher=None,
        auto_execute_threshold: float = CONFIDENCE_AUTO_EXECUTE,
        review_threshold: float = CONFIDENCE_NEEDS_REVIEW,
    ):
        self.analyze_fn = analyze_fn
        self.tool_registry = tool_registry
        self.event_publisher = event_publisher
        self.auto_execute_threshold = auto_execute_threshold
        self.review_threshold = review_threshold

    def run(
        self,
        customer_id: int,
        account_id: str,
        input_data: Any,
        account_arr: Optional[float] = None,
    ) -> LoopState:
        """
        Execute the full agentic loop.

        Returns LoopState with all intermediate and final results.
        """
        start_time = time.time()
        state = LoopState(customer_id=customer_id, account_id=account_id)

        try:
            # Step 1: ANALYZE — run the core agent
            state = self._step_analyze(state, input_data)

            # Step 2: EVALUATE — check confidence
            state = self._step_evaluate(state)

            # Step 3: ENRICH — gather more data if needed
            state = self._step_enrich(state, account_arr)

            # Step 4: QUANTIFY — put $ on every recommendation
            state = self._step_quantify(state, account_arr)

            # Step 5: DECIDE — auto-execute, review, or reject
            state = self._step_decide(state)

            # Step 6: ACT — trigger playbooks or queue for approval
            state = self._step_act(state)

            state.current_step = LoopStep.COMPLETE
            state.completed_at = datetime.utcnow().isoformat()

        except Exception as e:
            logger.error(f"Agentic loop failed at step {state.current_step}: {e}")
            state.decision = "error"
            state.decision_reason = str(e)

        state.duration_ms = int((time.time() - start_time) * 1000)

        # Publish completion event
        if self.event_publisher:
            try:
                from event_system import EventType
                self.event_publisher.publish(
                    EventType.AGENT_ANALYSIS_COMPLETE,
                    customer_id=customer_id,
                    data={
                        "account_id": account_id,
                        "predicted_outcome": state.predicted_outcome,
                        "confidence": state.confidence,
                        "decision": state.decision,
                        "total_dollar_impact": state.total_dollar_impact,
                        "actions_count": len(state.enriched_actions),
                        "duration_ms": state.duration_ms,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to publish completion event: {e}")

        # Store in shared memory
        self._store_in_shared_memory(state)

        return state

    # ─── Step 1: ANALYZE ─────────────────────────────────────

    def _step_analyze(self, state: LoopState, input_data: Any) -> LoopState:
        """Run the core analysis agent."""
        state.current_step = LoopStep.ANALYZE
        logger.info(f"[ANALYZE] Running core analysis for {state.account_id}")

        result = self.analyze_fn(input_data)

        # Extract key fields — works with both dict and Pydantic model
        if hasattr(result, 'model_dump'):
            result_dict = result.model_dump()
        elif isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {"raw": str(result)}

        state.initial_analysis = result_dict
        state.predicted_outcome = result_dict.get("predicted_outcome", "unknown")
        state.churn_probability = result_dict.get("churn_probability", 0)
        state.expansion_probability = result_dict.get("expansion_probability", 0)

        # Extract confidence
        confidence_data = result_dict.get("confidence", {})
        if isinstance(confidence_data, dict):
            state.confidence = confidence_data.get("overall_confidence", 0.5)
            state.confidence_level = confidence_data.get("confidence_level", "medium")
        elif isinstance(confidence_data, (int, float)):
            state.confidence = float(confidence_data)

        return state

    # ─── Step 2: EVALUATE ────────────────────────────────────

    def _step_evaluate(self, state: LoopState) -> LoopState:
        """Evaluate whether we have enough confidence to proceed."""
        state.current_step = LoopStep.EVALUATE
        logger.info(
            f"[EVALUATE] Confidence={state.confidence:.2f} "
            f"level={state.confidence_level} for {state.account_id}"
        )
        # Evaluation is implicit — enrichment step reads confidence
        return state

    # ─── Step 3: ENRICH ──────────────────────────────────────

    def _step_enrich(self, state: LoopState, account_arr: Optional[float]) -> LoopState:
        """Gather additional data via tools if confidence is low."""
        state.current_step = LoopStep.ENRICH

        if not self.tool_registry:
            logger.info("[ENRICH] No tool registry — skipping enrichment")
            return state

        # Always enrich with memory recall (fast, no LLM cost)
        memory_result = self.tool_registry.invoke(
            "memory_recall",
            customer_id=state.customer_id,
            account_id=state.account_id,
            namespace="customer_intelligence",
            limit=5,
        )
        if memory_result.success and memory_result.result:
            state.enrichment_data["shared_memory"] = memory_result.result
            state.tools_called.append("memory_recall")

        # If confidence is low, pull more data
        if state.confidence < self.review_threshold:
            logger.info(f"[ENRICH] Low confidence ({state.confidence:.2f}) — pulling feedback history")

            feedback_result = self.tool_registry.invoke(
                "feedback_history",
                customer_id=state.customer_id,
                limit=5,
            )
            if feedback_result.success:
                state.enrichment_data["feedback_history"] = feedback_result.result
                state.tools_called.append("feedback_history")

        # Always pull quarterly checkpoint for context
        try:
            from quarterly_checkpoints import get_current_quarter_from_date
            current_quarter = get_current_quarter_from_date()

            # Build actual values from initial analysis
            checkpoint_result = self.tool_registry.invoke(
                "quarterly_checkpoint",
                quarter=current_quarter,
                actual_values={},  # Will use defaults
                account_arr=account_arr,
            )
            if checkpoint_result.success:
                state.enrichment_data["quarterly_checkpoint"] = checkpoint_result.result
                state.tools_called.append("quarterly_checkpoint")
        except Exception as e:
            logger.warning(f"[ENRICH] Quarterly checkpoint failed: {e}")

        logger.info(f"[ENRICH] Called {len(state.tools_called)} tools")
        return state

    # ─── Step 4: QUANTIFY ────────────────────────────────────

    def _step_quantify(self, state: LoopState, account_arr: Optional[float]) -> LoopState:
        """Put $ impact on every recommended action via Power of 1."""
        state.current_step = LoopStep.QUANTIFY

        if not self.tool_registry:
            # Pass through raw actions without $ enrichment
            raw_actions = (state.initial_analysis or {}).get("recommended_actions", [])
            state.enriched_actions = [
                {**a, "dollar_impact": None, "power_of_1_metric": None}
                for a in raw_actions
            ]
            return state

        # Map recommended actions to Power of 1 metrics
        raw_actions = (state.initial_analysis or {}).get("recommended_actions", [])
        enriched = []
        total_dollar = 0.0

        # Keyword → metric mapping for action text
        ACTION_METRIC_MAP = {
            "onboard": "TTFV",
            "time to value": "TTFV",
            "activation": "TTFV",
            "retention": "GRR",
            "renew": "GRR",
            "churn": "GRR",
            "expand": "NRR",
            "upsell": "NRR",
            "cross-sell": "NRR",
            "nrr": "NRR",
            "support": "ticket_resolution_time",
            "ticket": "ticket_resolution_time",
            "resolution": "ticket_resolution_time",
            "adopt": "product_adoption",
            "usage": "product_adoption",
            "feature": "product_adoption",
            "expansion": "expansion_rate",
            "pipeline": "expansion_rate",
            "growth": "expansion_rate",
        }

        for action in raw_actions:
            action_text = action.get("action", "").lower() if isinstance(action, dict) else str(action).lower()
            matched_metric = None

            for keyword, metric_id in ACTION_METRIC_MAP.items():
                if keyword in action_text:
                    matched_metric = metric_id
                    break

            dollar_impact = None
            if matched_metric:
                # Calculate $ impact for a 1% improvement in this metric
                po1_result = self.tool_registry.invoke(
                    "power_of_1_calc",
                    metric_id=matched_metric,
                    improvement_pct=1.0,
                    account_arr=account_arr,
                )
                if po1_result.success and isinstance(po1_result.result, dict):
                    dollar_impact = po1_result.result.get("total_impact", 0)
                    total_dollar += dollar_impact
                    state.tools_called.append("power_of_1_calc")

            enriched_action = dict(action) if isinstance(action, dict) else {"action": str(action)}
            enriched_action["dollar_impact"] = dollar_impact
            enriched_action["power_of_1_metric"] = matched_metric
            enriched.append(enriched_action)

        state.enriched_actions = enriched
        state.total_dollar_impact = round(total_dollar, 2)
        logger.info(
            f"[QUANTIFY] {len(enriched)} actions enriched, "
            f"total impact: ${total_dollar:,.0f}"
        )
        return state

    # ─── Step 5: DECIDE ──────────────────────────────────────

    def _step_decide(self, state: LoopState) -> LoopState:
        """Decide whether to auto-execute, request review, or reject."""
        state.current_step = LoopStep.DECIDE

        if state.confidence >= self.auto_execute_threshold:
            state.decision = "auto_execute"
            state.decision_reason = (
                f"Confidence {state.confidence:.0%} >= {self.auto_execute_threshold:.0%} threshold. "
                f"Auto-executing {len(state.enriched_actions)} actions "
                f"(${state.total_dollar_impact:,.0f} total impact)."
            )
        elif state.confidence >= self.review_threshold:
            state.decision = "needs_review"
            state.decision_reason = (
                f"Confidence {state.confidence:.0%} is between "
                f"{self.review_threshold:.0%}-{self.auto_execute_threshold:.0%}. "
                f"Queuing {len(state.enriched_actions)} actions for human review."
            )
        else:
            state.decision = "rejected"
            state.decision_reason = (
                f"Confidence {state.confidence:.0%} < {self.review_threshold:.0%}. "
                f"Insufficient data for reliable action. Recommend gathering more signals."
            )

        logger.info(f"[DECIDE] {state.decision}: {state.decision_reason}")
        return state

    # ─── Step 6: ACT ─────────────────────────────────────────

    def _step_act(self, state: LoopState) -> LoopState:
        """Execute actions based on the decision."""
        state.current_step = LoopStep.ACT

        if state.decision == "rejected":
            logger.info("[ACT] Decision=rejected — no actions taken")
            return state

        if state.decision == "auto_execute":
            # Queue for auto-execution via approval system
            for action in state.enriched_actions:
                state.actions_taken.append({
                    "action": action.get("action", "unknown"),
                    "status": "queued_for_auto_execute",
                    "dollar_impact": action.get("dollar_impact"),
                    "playbook_id": action.get("playbook_id"),
                })

            # Publish auto-trigger event
            if self.event_publisher:
                try:
                    from event_system import EventType
                    self.event_publisher.publish(
                        EventType.PLAYBOOK_AUTO_TRIGGERED,
                        customer_id=state.customer_id,
                        data={
                            "account_id": state.account_id,
                            "actions": state.actions_taken,
                            "confidence": state.confidence,
                            "total_dollar_impact": state.total_dollar_impact,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish auto-trigger event: {e}")

        elif state.decision == "needs_review":
            for action in state.enriched_actions:
                state.actions_taken.append({
                    "action": action.get("action", "unknown"),
                    "status": "queued_for_review",
                    "dollar_impact": action.get("dollar_impact"),
                })

            # Publish approval request event
            if self.event_publisher:
                try:
                    from event_system import EventType
                    self.event_publisher.publish(
                        EventType.APPROVAL_REQUESTED,
                        customer_id=state.customer_id,
                        data={
                            "account_id": state.account_id,
                            "actions": state.actions_taken,
                            "confidence": state.confidence,
                            "predicted_outcome": state.predicted_outcome,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish approval event: {e}")

        logger.info(f"[ACT] {len(state.actions_taken)} actions queued as {state.decision}")
        return state

    # ─── Shared Memory Storage ───────────────────────────────

    def _store_in_shared_memory(self, state: LoopState) -> None:
        """Store loop results in shared memory for other agents to read."""
        if not self.tool_registry:
            return

        try:
            content = json.dumps({
                "predicted_outcome": state.predicted_outcome,
                "confidence": state.confidence,
                "decision": state.decision,
                "total_dollar_impact": state.total_dollar_impact,
                "actions_count": len(state.enriched_actions),
                "top_action": state.enriched_actions[0].get("action") if state.enriched_actions else None,
                "timestamp": datetime.utcnow().isoformat(),
            })

            self.tool_registry.invoke(
                "memory_remember",
                customer_id=state.customer_id,
                account_id=state.account_id,
                content=content,
                memory_type="episodic",
                namespace="customer_intelligence",
                key=f"analysis_{state.account_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                importance=0.8 if state.confidence >= self.review_threshold else 0.5,
                scope="shared",
            )
        except Exception as e:
            logger.warning(f"Failed to store loop results in shared memory: {e}")


# ============================================================
# SERIALIZATION
# ============================================================

def loop_state_to_dict(state: LoopState) -> Dict:
    """Serialize LoopState for API response."""
    return {
        "customer_id": state.customer_id,
        "account_id": state.account_id,
        "current_step": state.current_step.value,
        "iteration": state.iteration,
        "predicted_outcome": state.predicted_outcome,
        "churn_probability": state.churn_probability,
        "expansion_probability": state.expansion_probability,
        "confidence": state.confidence,
        "confidence_level": state.confidence_level,
        "tools_called": state.tools_called,
        "enriched_actions": state.enriched_actions,
        "total_dollar_impact": state.total_dollar_impact,
        "decision": state.decision,
        "decision_reason": state.decision_reason,
        "actions_taken": state.actions_taken,
        "started_at": state.started_at,
        "completed_at": state.completed_at,
        "duration_ms": state.duration_ms,
    }
