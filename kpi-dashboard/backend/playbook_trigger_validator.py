"""
Playbook Trigger Validator — Phase 2: LLM Validation Gate

Sits between KPI threshold detection and playbook execution.
Uses the existing SignalAnalystAgent to validate that a playbook
should actually fire, preventing false-positive triggering.

Cost controls:
 - 24-hour cache per (account_id, playbook_id) to avoid repeat LLM calls.
 - Respects `requires_llm_validation` flag on PlaybookTrigger.
 - Falls back to rule-based approval when the LLM is unavailable.
 - Uses the existing CostTracker + CircuitBreaker infrastructure.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

# Lazy imports: agents.signal_analyst_agent pulls in qdrant_client, openai, etc.
# These are only needed when the LLM path is actually used, not at import time.
SignalAnalystAgent = None
AnalysisError = None


def _ensure_agent_imports():
    global SignalAnalystAgent, AnalysisError
    if SignalAnalystAgent is None:
        from agents.signal_analyst_agent import (
            SignalAnalystAgent as _Agent,
            AnalysisError as _Err,
        )
        SignalAnalystAgent = _Agent
        AnalysisError = _Err


# Import lightweight models directly from the module (NOT through agents/__init__
# which eagerly imports SignalAnalystAgent → qdrant_client → heavy dependencies).
import importlib as _il
_agent_models = _il.import_module('agents.models')
_vertical_mapper = _il.import_module('agents.vertical_mapper')

SignalAnalystInput = _agent_models.SignalAnalystInput
SignalData = _agent_models.SignalData
TriggerValidationResult = _agent_models.TriggerValidationResult
TriggerValidationDecision = _agent_models.TriggerValidationDecision
map_vertical_to_agent_type = _vertical_mapper.map_vertical_to_agent_type

logger = logging.getLogger(__name__)

# ---- In-memory 24-hour validation cache ----
_validation_cache: Dict[str, TriggerValidationResult] = {}
_CACHE_TTL_SECONDS = 24 * 3600


def _cache_key(account_id: str, playbook_id: str) -> str:
    return f"{account_id}::{playbook_id}"


def _get_cached(account_id: str, playbook_id: str) -> Optional[TriggerValidationResult]:
    key = _cache_key(account_id, playbook_id)
    entry = _validation_cache.get(key)
    if entry is None:
        return None
    age = (datetime.now() - entry.validated_at).total_seconds()
    if age > _CACHE_TTL_SECONDS:
        del _validation_cache[key]
        return None
    return entry


def _set_cached(account_id: str, playbook_id: str, result: TriggerValidationResult):
    _validation_cache[_cache_key(account_id, playbook_id)] = result


class PlaybookTriggerValidator:
    """
    Validates whether a triggered playbook should actually execute
    by running a lightweight SignalAnalyst analysis.

    Decision thresholds (from the implementation plan):
      confidence > 0.8  → auto-approve
      confidence < 0.4  → auto-reject (log for CSM review)
      0.4 ≤ confidence ≤ 0.8 → pending manual approval
    """

    AUTO_APPROVE_THRESHOLD = 0.8
    AUTO_REJECT_THRESHOLD = 0.4

    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self._agent: Optional[SignalAnalystAgent] = None

    @property
    def agent(self):
        if self._agent is None:
            _ensure_agent_imports()
            self._agent = SignalAnalystAgent(
                openai_api_key=self.openai_api_key,
                model="gpt-4o",
                temperature=0.2,
                max_tokens=2000,
            )
        return self._agent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_trigger(
        self,
        account_id: str,
        customer_id: int,
        playbook_id: str,
        trigger_context: dict,
        *,
        account_name: Optional[str] = None,
        account_arr: Optional[float] = None,
        health_score: Optional[float] = None,
        vertical: str = "dc2_s",
        use_cache: bool = True,
    ) -> TriggerValidationResult:
        """
        Main entry point.  Returns a TriggerValidationResult indicating
        whether the playbook should proceed.

        Args:
            account_id: Account that triggered the playbook.
            customer_id: Tenant / customer owning the account.
            playbook_id: Which playbook was triggered (e.g. 'PB-02').
            trigger_context: Dict of KPIs that breached thresholds.
            account_name: Optional human-readable name.
            account_arr: Optional ARR for context.
            health_score: Optional pre-computed health score (0-100).
            vertical: 'dc2_s' or 'saas'.
            use_cache: If True, return cached result when available.
        """
        # Check cache first
        if use_cache:
            cached = _get_cached(account_id, playbook_id)
            if cached is not None:
                logger.info(
                    "Returning cached validation for %s / %s (decision=%s)",
                    account_id, playbook_id, cached.decision,
                )
                return cached

        try:
            result = self._validate_with_llm(
                account_id=account_id,
                customer_id=customer_id,
                playbook_id=playbook_id,
                trigger_context=trigger_context,
                account_name=account_name,
                account_arr=account_arr,
                health_score=health_score,
                vertical=vertical,
            )
        except Exception as exc:
            logger.warning(
                "LLM validation failed for %s / %s, falling back to rule-based: %s",
                account_id, playbook_id, exc,
            )
            result = self._fallback_rule_based(
                playbook_id=playbook_id,
                trigger_context=trigger_context,
                health_score=health_score,
            )

        # Cache the result
        if use_cache:
            _set_cached(account_id, playbook_id, result)

        return result

    # ------------------------------------------------------------------
    # LLM-based validation
    # ------------------------------------------------------------------

    def _validate_with_llm(
        self,
        account_id: str,
        customer_id: int,
        playbook_id: str,
        trigger_context: dict,
        account_name: Optional[str],
        account_arr: Optional[float],
        health_score: Optional[float],
        vertical: str,
    ) -> TriggerValidationResult:
        """Call SignalAnalystAgent, read output, apply thresholds."""
        agent_vertical = map_vertical_to_agent_type(vertical)

        # Build quantitative signals from the trigger context KPIs
        quant_signals = []
        for kpi_code, detail in trigger_context.items():
            value = detail if isinstance(detail, (int, float)) else detail.get("value", 0)
            threshold = detail.get("threshold") if isinstance(detail, dict) else None
            quant_signals.append(
                SignalData(
                    similarity=0.95,
                    payload={
                        "pillar": kpi_code.split("-")[0] if "-" in kpi_code else "unknown",
                        "metric_type": kpi_code,
                        "current_value": value,
                        "threshold": threshold,
                        "text": f"{kpi_code} = {value} (triggered playbook {playbook_id})",
                    },
                )
            )

        agent_input = SignalAnalystInput(
            account_id=account_id,
            customer_id=customer_id,
            vertical_type=agent_vertical,
            account_name=account_name or f"Account {account_id}",
            account_arr=account_arr,
            health_score=health_score,
            quantitative_signals=quant_signals,
            qualitative_signals=[],
            historical_patterns=[],
            analysis_type="comprehensive",
            time_horizon_days=60,
        )

        output = self.agent.analyze(agent_input)

        # Extract confidence from SignalAnalystOutput
        confidence = output.confidence.overall_confidence if output.confidence else 0.5

        # Alignment check: if decision matrix says DISAGREEMENT, lower confidence
        alignment = output.data_alignment or {}
        if alignment.get("alignment") == "disagreement":
            confidence *= 0.7  # Penalize disagreement

        # Outcome coherence check:
        # If playbook is a *churn* playbook but LLM predicts EXPANSION → reject
        churn_playbooks = {"PB-02", "PB-05"}
        expansion_playbooks = {"PB-04"}
        predicted = output.predicted_outcome
        if playbook_id in churn_playbooks and predicted == "expansion":
            logger.info(
                "Coherence check: %s triggered but LLM predicts expansion — rejecting.",
                playbook_id,
            )
            confidence = min(confidence, 0.3)
        elif playbook_id in expansion_playbooks and predicted == "churn":
            logger.info(
                "Coherence check: %s triggered but LLM predicts churn — rejecting.",
                playbook_id,
            )
            confidence = min(confidence, 0.3)

        # Apply thresholds
        decision, approved = self._apply_thresholds(confidence)

        # Check if LLM suggests a different priority or playbook
        modified_priority = None
        recommended_playbook = None
        if output.recommended_actions:
            top_action = output.recommended_actions[0]
            if hasattr(top_action, 'priority') and top_action.priority:
                modified_priority = top_action.priority

        return TriggerValidationResult(
            approved=approved,
            confidence=round(confidence, 3),
            reasoning=output.reasoning or "LLM validation completed.",
            decision=decision,
            signal_analyst_output=output.model_dump(),
            modified_priority=modified_priority,
            recommended_playbook=recommended_playbook,
            validated_at=datetime.now(),
        )

    # ------------------------------------------------------------------
    # Rule-based fallback
    # ------------------------------------------------------------------

    def _fallback_rule_based(
        self,
        playbook_id: str,
        trigger_context: dict,
        health_score: Optional[float],
    ) -> TriggerValidationResult:
        """
        Simple rule-based approval when LLM is unavailable.
        Uses health score + number of breached KPIs as a proxy for confidence.
        """
        breach_count = len(trigger_context)
        hs = health_score if health_score is not None else 50.0

        # Heuristic confidence: more breaches + lower health → higher confidence
        # that the playbook should fire
        if hs < 50 and breach_count >= 2:
            confidence = 0.85
        elif hs < 70 and breach_count >= 1:
            confidence = 0.65
        else:
            confidence = 0.45

        decision, approved = self._apply_thresholds(confidence)

        return TriggerValidationResult(
            approved=approved,
            confidence=round(confidence, 3),
            reasoning=(
                f"Rule-based fallback: health_score={hs:.1f}, "
                f"breached_kpis={breach_count}. LLM unavailable."
            ),
            decision=decision,
            signal_analyst_output=None,
            modified_priority=None,
            recommended_playbook=None,
            validated_at=datetime.now(),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @classmethod
    def _apply_thresholds(cls, confidence: float):
        """Map confidence to (TriggerValidationDecision, approved_bool)."""
        if confidence > cls.AUTO_APPROVE_THRESHOLD:
            return TriggerValidationDecision.AUTO_APPROVED, True
        elif confidence < cls.AUTO_REJECT_THRESHOLD:
            return TriggerValidationDecision.AUTO_REJECTED, False
        else:
            return TriggerValidationDecision.PENDING_MANUAL_APPROVAL, False


# ============================================================
# Trigger evaluation loop — Phase 2.3 integration point
# ============================================================

def evaluate_triggers(account_id: int, customer_id: int, current_kpis: dict, openai_api_key: str):
    """
    Evaluate all playbook triggers for an account and dispatch or log results.

    This is the *integration point* described in Phase 2.3 of the plan.
    It is called after health score recalculation (e.g., after KPI upload or
    scheduled refresh).

    Args:
        account_id: Account whose KPIs just changed.
        customer_id: Tenant ID.
        current_kpis: Dict of latest KPI values (catalog codes → floats).
        openai_api_key: API key for the LLM validation gate.
    """
    from models import PlaybookTrigger, PlaybookExecution, Account
    from extensions import db
    import uuid

    account = db.session.get(Account, account_id)
    if not account:
        logger.warning("evaluate_triggers: account %s not found", account_id)
        return []

    triggers = PlaybookTrigger.query.filter_by(customer_id=customer_id).all()
    if not triggers:
        logger.debug("No triggers configured for customer %s", customer_id)
        return []

    validator = PlaybookTriggerValidator(openai_api_key=openai_api_key)
    results = []

    for trigger in triggers:
        # Check KPI thresholds from trigger_conditions (JSON column)
        conditions = trigger.trigger_conditions or {}
        breached = {}
        for kpi_code, condition in conditions.items():
            if kpi_code not in current_kpis:
                continue
            val = current_kpis[kpi_code]
            op = condition.get("operator", ">")
            thresh = condition.get("value", 0)
            if op == ">" and val > thresh:
                breached[kpi_code] = {"value": val, "threshold": thresh, "operator": op}
            elif op == "<" and val < thresh:
                breached[kpi_code] = {"value": val, "threshold": thresh, "operator": op}
            elif op == "==" and val == thresh:
                breached[kpi_code] = {"value": val, "threshold": thresh, "operator": op}

        if not breached:
            continue

        # Update last_evaluated timestamp
        trigger.last_evaluated = datetime.utcnow()

        # Run through LLM validation gate (or skip if not required)
        if trigger.requires_llm_validation:
            result = validator.validate_trigger(
                account_id=str(account_id),
                customer_id=customer_id,
                playbook_id=trigger.playbook_id or trigger.playbook_type,
                trigger_context=breached,
                account_name=account.account_name,
                account_arr=float(account.revenue) if account.revenue else None,
                health_score=None,  # Caller can pre-compute if needed
            )
        else:
            # Auto-approve playbooks that skip LLM validation (e.g., QBR cadence)
            result = TriggerValidationResult(
                approved=True,
                confidence=1.0,
                reasoning="LLM validation not required for this playbook.",
                decision=TriggerValidationDecision.AUTO_APPROVED,
                signal_analyst_output=None,
                modified_priority=None,
                recommended_playbook=None,
                validated_at=datetime.now(),
            )

        results.append({
            "trigger_id": trigger.trigger_id,
            "playbook_id": trigger.playbook_id or trigger.playbook_type,
            "breached_kpis": breached,
            "validation": result.model_dump(),
        })

        # Dispatch or log based on decision
        if result.decision == TriggerValidationDecision.AUTO_APPROVED:
            trigger.last_triggered = datetime.utcnow()
            trigger.trigger_count = (trigger.trigger_count or 0) + 1

            # Create a PlaybookExecution record
            execution = PlaybookExecution(
                execution_id=str(uuid.uuid4()),
                customer_id=customer_id,
                account_id=account_id,
                playbook_id=trigger.playbook_id or trigger.playbook_type,
                status="in-progress",
                current_step="initialized",
                execution_data={"trigger_context": breached, "validation": result.model_dump()},
                started_at=datetime.utcnow(),
                execution_mode=trigger.execution_mode or "workflow",
                trigger_context=breached,
                llm_validation_result=result.model_dump(),
            )
            db.session.add(execution)
            logger.info(
                "AUTO-APPROVED: Dispatching %s for account %s (confidence=%.2f)",
                trigger.playbook_id, account_id, result.confidence,
            )
        elif result.decision == TriggerValidationDecision.PENDING_MANUAL_APPROVAL:
            logger.info(
                "PENDING APPROVAL: %s for account %s (confidence=%.2f). CSM review required.",
                trigger.playbook_id, account_id, result.confidence,
            )
        else:
            logger.info(
                "AUTO-REJECTED: %s for account %s (confidence=%.2f). Reason: %s",
                trigger.playbook_id, account_id, result.confidence, result.reasoning[:120],
            )

    try:
        db.session.commit()
    except Exception as exc:
        logger.error("Failed to commit trigger evaluation results: %s", exc)
        db.session.rollback()

    return results
