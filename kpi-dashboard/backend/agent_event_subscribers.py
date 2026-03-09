#!/usr/bin/env python3
"""
Agent Event Subscribers — Wires the autonomous agent pipeline
==============================================================
Subscribes to events from the event system and routes them to the
correct agent/service.  This is the CRITICAL missing piece that
connects the existing production-ready components:

  Signal Analyst  →  Approval Queue  →  Playbook Orchestrator

Subscriber chain:
  1. OnboardingCompleteSubscriber  — onboarding done → run Signal Analyst
  2. AgentAnalysisSubscriber       — analysis done → route to approval queue
  3. PlaybookAutoTriggerSubscriber  — approved action → trigger playbook
  4. ApprovalDecisionSubscriber     — human decision → follow-up events
  5. PlaybookFeedbackSubscriber     — playbook done → store in agent memory

Each subscriber follows the same pattern as existing subscribers
(RAGRebuildSubscriber, DataIngestionSubscriber) in event_system.py.
"""

import threading
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


# ============================================================
# 1. ONBOARDING COMPLETE → SIGNAL ANALYST
# ============================================================

class OnboardingCompleteSubscriber:
    """
    When onboarding completes (or KPI data is uploaded), trigger the
    Signal Analyst agentic loop for the affected accounts.

    Uses a per-account cooldown to prevent analysis storms during
    bulk data uploads.
    """

    def __init__(self, cooldown_seconds: int = 300):
        self.cooldown = {}           # account_id → last_run_timestamp
        self.cooldown_seconds = cooldown_seconds
        self._lock = threading.Lock()

    def handle_event(self, event):
        """Handle ONBOARDING_COMPLETE or KPI_DATA_UPLOADED events."""
        try:
            customer_id = event.customer_id
            data = event.data or {}

            # Entitlement check — auto-trigger pipeline requires 'auto_trigger_pipeline'
            try:
                from entitlements import check_entitlement
                if not check_entitlement(customer_id, 'auto_trigger_pipeline'):
                    logger.info(
                        f"[OnboardingCompleteSubscriber] Customer {customer_id} not entitled "
                        f"to 'auto_trigger_pipeline' — skipping auto-analysis"
                    )
                    return
            except ImportError:
                pass  # Entitlements not available — allow by default

            # Get account IDs from event
            account_ids = data.get('account_ids', [])
            if not account_ids:
                # Try to load from DB
                account_ids = self._get_customer_accounts(customer_id)

            if not account_ids:
                logger.info(
                    f"[OnboardingCompleteSubscriber] No accounts found for customer {customer_id}"
                )
                return

            trigger = data.get('trigger', 'data_upload')
            logger.info(
                f"[OnboardingCompleteSubscriber] Trigger={trigger}, "
                f"customer={customer_id}, accounts={len(account_ids)}"
            )

            # Queue analysis for each account (with cooldown)
            for account_id in account_ids:
                if self._check_cooldown(str(account_id)):
                    threading.Thread(
                        target=self._run_analysis,
                        args=(customer_id, str(account_id)),
                        daemon=True,
                    ).start()

        except Exception as e:
            logger.error(f"[OnboardingCompleteSubscriber] Error: {e}", exc_info=True)

    def _check_cooldown(self, account_id: str) -> bool:
        """Check if enough time has passed since last analysis for this account."""
        with self._lock:
            now = time.time()
            last_run = self.cooldown.get(account_id, 0)
            if now - last_run < self.cooldown_seconds:
                logger.debug(
                    f"[OnboardingCompleteSubscriber] Cooldown active for {account_id}"
                )
                return False
            self.cooldown[account_id] = now
            return True

    def _run_analysis(self, customer_id: int, account_id: str):
        """Run the agentic loop for a single account (background thread)."""
        try:
            from agents.signal_analyst_api import _run_analysis_with_loop
            logger.info(
                f"[OnboardingCompleteSubscriber] Auto-triggering Signal Analyst "
                f"for customer={customer_id}, account={account_id}"
            )
            # _run_analysis_with_loop is the internal function used by the API
            # If it doesn't exist, fall back to a simpler approach
            result = _run_analysis_with_loop(customer_id, account_id)
            logger.info(
                f"[OnboardingCompleteSubscriber] Analysis complete for {account_id}: "
                f"decision={result.get('decision', 'unknown') if isinstance(result, dict) else 'done'}"
            )
        except ImportError:
            logger.warning(
                "[OnboardingCompleteSubscriber] _run_analysis_with_loop not available, "
                "using direct agent call"
            )
            self._run_analysis_direct(customer_id, account_id)
        except Exception as e:
            logger.error(
                f"[OnboardingCompleteSubscriber] Analysis failed for {account_id}: {e}"
            )

    def _run_analysis_direct(self, customer_id: int, account_id: str):
        """Fallback: run Signal Analyst without the full API layer."""
        try:
            import os
            from agents.claude_signal_analyst_agent import create_signal_analyst_agent
            from agents.models import SignalAnalystInput

            provider = 'anthropic' if os.getenv('ANTHROPIC_API_KEY') else 'openai'
            agent = create_signal_analyst_agent(
                provider=provider,
                customer_id=customer_id,
                account_id=account_id,
            )
            # Minimal input — the agent will work with what's available
            input_data = SignalAnalystInput(
                account_id=account_id,
                account_name=f"Account {account_id}",
                customer_id=customer_id,
                analysis_type="comprehensive",
            )
            agent.analyze(input_data)
        except Exception as e:
            logger.error(f"[OnboardingCompleteSubscriber] Direct analysis failed: {e}")

    def _get_customer_accounts(self, customer_id: int) -> list:
        """Load account IDs from the database."""
        try:
            import os
            from sqlalchemy import create_engine, text
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                return []
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT account_id FROM accounts WHERE customer_id = :cid"),
                    {"cid": customer_id},
                )
                return [row[0] for row in result.fetchall()]
        except Exception:
            return []


# ============================================================
# 2. AGENT ANALYSIS COMPLETE → APPROVAL QUEUE
# ============================================================

class AgentAnalysisSubscriber:
    """
    When Signal Analyst completes, route recommended actions to the
    Approval Queue based on confidence thresholds:
      - >= 0.85 → auto_execute tier
      - >= 0.60 → needs_review tier (human approval required)
      - <  0.60 → rejected (logged but no action)
    """

    AUTO_EXECUTE_THRESHOLD = 0.85
    NEEDS_REVIEW_THRESHOLD = 0.60

    def handle_event(self, event):
        """Handle AGENT_ANALYSIS_COMPLETE events."""
        try:
            customer_id = event.customer_id
            data = event.data or {}

            account_id = data.get('account_id')
            actions = data.get('actions', [])
            confidence = data.get('confidence', 0.0)
            predicted_outcome = data.get('predicted_outcome', 'unknown')
            total_dollar_impact = data.get('total_dollar_impact', 0.0)

            if not actions:
                logger.info(
                    f"[AgentAnalysisSubscriber] No actions from analysis for {account_id}"
                )
                return

            # Determine tier
            if confidence >= self.AUTO_EXECUTE_THRESHOLD:
                tier = "auto_execute"
            elif confidence >= self.NEEDS_REVIEW_THRESHOLD:
                tier = "needs_review"
            else:
                logger.info(
                    f"[AgentAnalysisSubscriber] Confidence {confidence:.2f} too low for "
                    f"{account_id} — actions rejected"
                )
                return

            logger.info(
                f"[AgentAnalysisSubscriber] Routing {len(actions)} actions to approval queue "
                f"(tier={tier}, confidence={confidence:.2f}, account={account_id})"
            )

            # Submit to approval queue
            self._submit_to_approval_queue(
                customer_id=customer_id,
                account_id=account_id,
                actions=actions,
                confidence=confidence,
                tier=tier,
                predicted_outcome=predicted_outcome,
                total_dollar_impact=total_dollar_impact,
            )

        except Exception as e:
            logger.error(f"[AgentAnalysisSubscriber] Error: {e}", exc_info=True)

    def _submit_to_approval_queue(
        self,
        customer_id: int,
        account_id: str,
        actions: list,
        confidence: float,
        tier: str,
        predicted_outcome: str,
        total_dollar_impact: float,
    ):
        """Submit actions to the ApprovalQueueService."""
        try:
            from approval_queue import ApprovalQueueService

            svc = ApprovalQueueService()
            for action in actions:
                action_text = action.get('action', 'unknown') if isinstance(action, dict) else str(action)
                playbook_id = action.get('playbook_id') if isinstance(action, dict) else None

                svc.submit(
                    customer_id=customer_id,
                    account_id=account_id,
                    action_type='playbook_trigger',
                    action_description=action_text,
                    playbook_id=playbook_id,
                    confidence=confidence,
                    tier=tier,
                    context={
                        'predicted_outcome': predicted_outcome,
                        'total_dollar_impact': total_dollar_impact,
                        'dollar_impact': action.get('dollar_impact') if isinstance(action, dict) else None,
                    },
                )

            logger.info(
                f"[AgentAnalysisSubscriber] Submitted {len(actions)} actions to approval queue"
            )
        except ImportError:
            logger.warning(
                "[AgentAnalysisSubscriber] ApprovalQueueService not available — "
                "actions not queued"
            )
        except Exception as e:
            logger.error(f"[AgentAnalysisSubscriber] Failed to submit to queue: {e}")


# ============================================================
# 3. PLAYBOOK AUTO-TRIGGERED → PLAYBOOK ORCHESTRATOR
# ============================================================

class PlaybookAutoTriggerSubscriber:
    """
    When an action is approved (auto or human), trigger the
    Playbook Orchestrator to execute it via n8n.
    """

    def handle_event(self, event):
        """Handle PLAYBOOK_AUTO_TRIGGERED events."""
        try:
            customer_id = event.customer_id
            data = event.data or {}

            account_id = data.get('account_id')
            actions = data.get('actions', [])
            confidence = data.get('confidence', 0.0)

            logger.info(
                f"[PlaybookAutoTriggerSubscriber] Triggering {len(actions)} playbooks "
                f"for account={account_id} (confidence={confidence:.2f})"
            )

            for action in actions:
                playbook_id = action.get('playbook_id') if isinstance(action, dict) else None
                if playbook_id:
                    self._trigger_playbook(
                        customer_id=customer_id,
                        account_id=account_id,
                        playbook_id=playbook_id,
                        action=action,
                    )

        except Exception as e:
            logger.error(f"[PlaybookAutoTriggerSubscriber] Error: {e}", exc_info=True)

    def _trigger_playbook(
        self, customer_id: int, account_id: str, playbook_id: str, action: dict
    ):
        """Create a PlaybookExecution and trigger the orchestrator."""
        try:
            from playbook_orchestrator import PlaybookOrchestrator

            orchestrator = PlaybookOrchestrator()

            # Build execution context
            context = {
                'customer_id': customer_id,
                'account_id': account_id,
                'playbook_id': playbook_id,
                'trigger': 'agent_auto',
                'action_description': action.get('action', '') if isinstance(action, dict) else str(action),
                'dollar_impact': action.get('dollar_impact') if isinstance(action, dict) else None,
                'timestamp': datetime.utcnow().isoformat(),
            }

            orchestrator.trigger_execution(playbook_id, context)
            logger.info(
                f"[PlaybookAutoTriggerSubscriber] Triggered playbook {playbook_id} "
                f"for account {account_id}"
            )
        except ImportError:
            logger.warning(
                "[PlaybookAutoTriggerSubscriber] PlaybookOrchestrator not available"
            )
        except Exception as e:
            logger.error(
                f"[PlaybookAutoTriggerSubscriber] Failed to trigger {playbook_id}: {e}"
            )


# ============================================================
# 4. APPROVAL DECIDED → FOLLOW-UP EVENTS
# ============================================================

class ApprovalDecisionSubscriber:
    """
    When a human approves or rejects an action:
      - Approved → publish PLAYBOOK_AUTO_TRIGGERED to execute
      - Rejected → store rejection in agent memory for learning
    """

    def handle_event(self, event):
        """Handle APPROVAL_DECIDED events."""
        try:
            customer_id = event.customer_id
            data = event.data or {}

            decision = data.get('decision', 'unknown')
            account_id = data.get('account_id')
            actions = data.get('actions', [])

            logger.info(
                f"[ApprovalDecisionSubscriber] Decision={decision} for "
                f"account={account_id}, {len(actions)} actions"
            )

            if decision == 'approved':
                # Publish PLAYBOOK_AUTO_TRIGGERED so the orchestrator picks it up
                try:
                    from event_system import EventType
                    event.event_type = EventType.PLAYBOOK_AUTO_TRIGGERED
                    # Re-publish as auto-trigger (the event publisher in the
                    # parent EventManager will route to PlaybookAutoTriggerSubscriber)
                    from event_system import get_event_manager
                    mgr = get_event_manager()
                    if mgr:
                        mgr.publisher.publish(
                            EventType.PLAYBOOK_AUTO_TRIGGERED,
                            customer_id=customer_id,
                            data={
                                'account_id': account_id,
                                'actions': actions,
                                'confidence': data.get('confidence', 0.0),
                                'approval_source': 'human',
                            },
                        )
                except Exception as e:
                    logger.error(f"[ApprovalDecisionSubscriber] Failed to re-publish: {e}")

            elif decision == 'rejected':
                # Store rejection in agent memory for future learning
                self._store_rejection(customer_id, account_id, data)

        except Exception as e:
            logger.error(f"[ApprovalDecisionSubscriber] Error: {e}", exc_info=True)

    def _store_rejection(self, customer_id: int, account_id: str, data: dict):
        """Store rejection in agent memory so future analyses can learn."""
        try:
            from agent_memory import (
                get_memory_store, MemoryEntry, MemoryType, MemoryScope
            )
            store = get_memory_store()

            rejection_content = json.dumps({
                'event': 'action_rejected',
                'account_id': account_id,
                'rejected_actions': data.get('actions', []),
                'rejection_reason': data.get('reason', ''),
                'confidence_at_time': data.get('confidence', 0.0),
                'timestamp': datetime.utcnow().isoformat(),
            })

            store.remember(MemoryEntry(
                memory_type=MemoryType.EPISODIC,
                scope=MemoryScope.SHARED,
                content=rejection_content,
                customer_id=customer_id,
                account_id=account_id,
                namespace="playbook_outcome",
                key=f"rejection_{account_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                importance=0.7,
            ))

            logger.info(
                f"[ApprovalDecisionSubscriber] Stored rejection in agent memory "
                f"for account {account_id}"
            )
        except Exception as e:
            logger.warning(f"[ApprovalDecisionSubscriber] Failed to store rejection: {e}")


# ============================================================
# 5. PLAYBOOK EXECUTION COMPLETED → FEEDBACK LOOP
# ============================================================

class PlaybookFeedbackSubscriber:
    """
    When a playbook execution completes, store the outcome in:
      1. qdrant_feedback_loop — for signal weight recalibration
      2. agent_memory — for cross-agent intelligence (future analyses)

    This closes the feedback loop: Playbook outcome → Agent memory → Better predictions.
    """

    def handle_event(self, event):
        """Handle PLAYBOOK_EXECUTION_COMPLETED events."""
        try:
            customer_id = event.customer_id
            data = event.data or {}

            account_id = data.get('account_id')
            playbook_id = data.get('playbook_id', 'unknown')
            outcome = data.get('outcome', 'completed')
            kpi_improvements = data.get('kpi_improvements')

            logger.info(
                f"[PlaybookFeedbackSubscriber] Playbook {playbook_id} completed "
                f"for account {account_id}: {outcome}"
            )

            # 1. Store in qdrant_feedback_loop (for weight recalibration)
            try:
                from qdrant_feedback_loop import store_execution_feedback
                store_execution_feedback({
                    'customer_id': customer_id,
                    'account_id': account_id,
                    'playbook_id': playbook_id,
                    'outcome': outcome,
                    'kpi_improvements': kpi_improvements,
                })
            except ImportError:
                logger.debug("[PlaybookFeedbackSubscriber] qdrant_feedback_loop not available")
            except Exception as e:
                logger.warning(f"[PlaybookFeedbackSubscriber] Feedback store failed: {e}")

            # 2. Store in agent_memory (for cross-agent intelligence)
            try:
                from agent_memory import remember_playbook_outcome
                remember_playbook_outcome(
                    customer_id=customer_id,
                    account_id=account_id,
                    playbook_id=playbook_id,
                    outcome=outcome,
                    kpi_improvements=kpi_improvements,
                )
                logger.info(
                    f"[PlaybookFeedbackSubscriber] Stored outcome in agent memory "
                    f"for future analysis enrichment"
                )
            except ImportError:
                logger.debug("[PlaybookFeedbackSubscriber] agent_memory not available")
            except Exception as e:
                logger.warning(f"[PlaybookFeedbackSubscriber] Memory store failed: {e}")

        except Exception as e:
            logger.error(f"[PlaybookFeedbackSubscriber] Error: {e}", exc_info=True)
