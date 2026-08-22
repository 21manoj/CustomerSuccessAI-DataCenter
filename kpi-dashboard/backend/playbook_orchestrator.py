"""
Playbook Orchestrator — Phase 2 Enhanced
==========================================
Hand-off to n8n workflows, direct provider dispatch via Action Bindings,
retry policies, step-level audit logging, and status tracking.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import PlaybookExecution, CustomerWorkflowConfig
from security_utils import decrypt_credential, generate_webhook_signature

logger = logging.getLogger(__name__)


class HandoffError(Exception):
    """Raised when we fail to handoff execution to n8n after retries."""


class PlaybookOrchestrator:
    """Encapsulates the workflow for triggering and monitoring playbooks."""

    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)

    # ------------------------------------------------------------------ #
    # Public API — n8n handoff (existing)
    # ------------------------------------------------------------------ #
    def trigger_execution(
        self,
        execution: PlaybookExecution,
        payload: Dict[str, Any],
        *,
        retry_attempt: int = 0,
    ) -> Dict[str, Any]:
        """
        Hand-off a prepared execution payload to n8n and persist the state.
        """
        self.logger.info(
            "Triggering playbook execution %s (attempt=%s)",
            execution.execution_id,
            retry_attempt,
        )

        config = CustomerWorkflowConfig.query.filter_by(
            customer_id=execution.customer_id
        ).first()
        if not config or not config.n8n_webhook_url:
            raise HandoffError("Workflow configuration is incomplete for this customer")

        # Allow HTTP for localhost development, require HTTPS for production
        if not config.n8n_webhook_url.startswith("https://") and not config.n8n_webhook_url.startswith("http://localhost"):
            raise HandoffError("n8n webhook URL must use HTTPS in production (or use localhost for development)")

        api_key = (
            decrypt_credential(config.n8n_api_key_encrypted)
            if config.n8n_api_key_encrypted
            else None
        )
        if config.webhook_secret_encrypted:
            secret = decrypt_credential(config.webhook_secret_encrypted)
            signature = generate_webhook_signature(payload, secret)
        else:
            secret = None
            signature = None

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "GrowthPulse/PlaybookOrchestrator",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if signature:
            headers["X-GrowthPulse-Signature"] = signature

        response = requests.post(
            config.n8n_webhook_url,
            json=payload,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()

        data = response.json() if response.content else {}
        execution.external_workflow_id = data.get("workflow_execution_id")
        execution.status = "HANDED_OFF_TO_N8N"
        execution.handed_off_at = datetime.utcnow()
        execution.updated_at = datetime.utcnow()
        db.session.add(execution)
        db.session.commit()

        self._record_status_update(
            execution,
            status="HANDED_OFF_TO_N8N",
            message="Execution handed off to n8n",
            metadata={"response": data},
        )

        return data

    # ------------------------------------------------------------------ #
    # Phase 2 — Direct provider dispatch via Action Bindings
    # ------------------------------------------------------------------ #
    def execute_step(
        self,
        execution: PlaybookExecution,
        step_index: int,
        action_name: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a single playbook step by resolving the action binding
        and dispatching to the appropriate provider.

        Flow:
          1. Look up CustomerActionBinding for this customer + action_name
          2. Resolve credentials from IntegrationCredential
          3. Dispatch to the provider adapter
          4. Log the step result to PlaybookStepLog
          5. If provider fails and fallback is set, try fallback

        Returns the step result dict.
        """
        from models_action_interface import CustomerActionBinding, IntegrationCredential, PlaybookStepLog
        from providers.registry import get_provider

        start = time.monotonic()

        # 1. Resolve binding
        binding = CustomerActionBinding.query.filter_by(
            customer_id=execution.customer_id,
            action_name=action_name,
            enabled=True,
        ).first()

        if not binding:
            # No binding — use internal provider as default
            binding_provider = 'cs_pulse_internal'
            binding_config = {}
            credential_data = None
        else:
            binding_provider = binding.provider
            binding_config = binding.config or {}
            credential_data = self._resolve_credentials(binding)

        # 2. Get provider adapter
        provider = get_provider(binding_provider)
        if not provider:
            return self._log_step_failure(
                execution, step_index, action_name, binding_provider,
                params, f"Provider '{binding_provider}' not found", start,
            )

        # 3. Execute via provider
        try:
            result = provider.execute(
                action_name=action_name,
                params=params,
                credentials=credential_data,
                config=binding_config,
            )
        except Exception as e:
            result = None
            error_msg = str(e)
            self.logger.error(
                "Provider %s raised exception for step %s: %s",
                binding_provider, step_index, error_msg,
            )

        # 4. Handle result
        duration_ms = int((time.monotonic() - start) * 1000)

        if result and result.success:
            step_log = PlaybookStepLog(
                execution_id=execution.execution_id,
                step_index=step_index,
                action_name=action_name,
                provider=binding_provider,
                params_sent=params,
                response_received=result.to_dict(),
                status='success',
                executed_at=datetime.utcnow(),
                duration_ms=duration_ms,
            )
            db.session.add(step_log)
            db.session.commit()

            return {
                'step_index': step_index,
                'action_name': action_name,
                'provider': binding_provider,
                'status': 'success',
                'external_id': result.external_id,
                'external_url': result.external_url,
                'duration_ms': duration_ms,
            }

        # 5. Provider failed — try fallback
        error_msg = result.error_message if result else error_msg
        fallback = binding.fallback if binding else 'log_only'

        if fallback and fallback != binding_provider:
            self.logger.info(
                "Primary provider %s failed, trying fallback %s",
                binding_provider, fallback,
            )
            fallback_provider = get_provider(fallback)
            if fallback_provider:
                try:
                    fallback_result = fallback_provider.execute(
                        action_name=action_name,
                        params=params,
                    )
                    if fallback_result.success:
                        step_log = PlaybookStepLog(
                            execution_id=execution.execution_id,
                            step_index=step_index,
                            action_name=action_name,
                            provider=f"{binding_provider}→{fallback}",
                            params_sent=params,
                            response_received=fallback_result.to_dict(),
                            status='success',
                            executed_at=datetime.utcnow(),
                            duration_ms=int((time.monotonic() - start) * 1000),
                        )
                        db.session.add(step_log)
                        db.session.commit()

                        return {
                            'step_index': step_index,
                            'action_name': action_name,
                            'provider': f"{binding_provider}→{fallback}",
                            'status': 'success',
                            'fallback_used': True,
                            'duration_ms': step_log.duration_ms,
                        }
                except Exception:
                    pass

        return self._log_step_failure(
            execution, step_index, action_name, binding_provider,
            params, error_msg, start,
        )

    def execute_playbook_steps(
        self,
        execution: PlaybookExecution,
        steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute all steps in a playbook sequentially.

        Args:
            execution: The PlaybookExecution record
            steps: List of {'action_name': str, 'params': dict}

        Returns summary of all step results.
        """
        results = []
        failed = False

        for idx, step in enumerate(steps):
            if failed:
                results.append({
                    'step_index': idx,
                    'action_name': step['action_name'],
                    'status': 'skipped',
                    'reason': 'Prior step failed',
                })
                continue

            result = self.execute_step(
                execution=execution,
                step_index=idx,
                action_name=step['action_name'],
                params=step.get('params', {}),
            )
            results.append(result)

            if result.get('status') != 'success':
                failed = True

        # Update execution status
        success_count = sum(1 for r in results if r.get('status') == 'success')
        execution.status = 'COMPLETED' if not failed else 'PARTIALLY_COMPLETED'
        execution.completed_at = datetime.utcnow()
        execution.updated_at = datetime.utcnow()
        db.session.commit()

        return {
            'execution_id': execution.execution_id,
            'total_steps': len(steps),
            'succeeded': success_count,
            'failed': len(results) - success_count,
            'steps': results,
        }

    # ------------------------------------------------------------------ #
    # Callbacks
    # ------------------------------------------------------------------ #
    def process_callback(
        self,
        execution: PlaybookExecution,
        payload: Dict[str, Any],
    ) -> None:
        """
        Persist status updates coming back from n8n.
        """
        status = payload.get("status") or execution.status
        message = payload.get("progress_notes") or payload.get("message")

        execution.status = status
        execution.external_ticket_id = payload.get("external_ticket_id")
        execution.external_ticket_url = payload.get("external_ticket_url")
        execution.outcome = payload.get("outcome", execution.outcome)
        execution.outcome_details = payload.get("outcome_details", execution.outcome_details)
        execution.time_to_complete = payload.get("time_to_complete", execution.time_to_complete)

        if status in {"COMPLETED", "FAILED"}:
            execution.completed_at = datetime.utcnow()

        execution.updated_at = datetime.utcnow()
        db.session.add(execution)

        self._record_status_update(
            execution,
            status=status,
            message=message,
            metadata=payload,
        )

        # Store feedback for recalibration when execution completes
        if status == "COMPLETED":
            self._store_feedback(execution, payload)

        try:
            db.session.commit()
        except SQLAlchemyError as exc:  # pragma: no cover - defensive
            db.session.rollback()
            self.logger.error("Failed to persist playbook callback: %s", exc)
            raise

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _resolve_credentials(self, binding) -> Optional[Dict[str, Any]]:
        """Decrypt credentials from the vault for a binding."""
        if not binding.auth_credential_id:
            return None

        from models_action_interface import IntegrationCredential

        cred = db.session.get(IntegrationCredential, binding.auth_credential_id)
        if not cred or not cred.encrypted_data:
            return None

        try:
            decrypted = decrypt_credential(cred.encrypted_data)
            return json.loads(decrypted) if isinstance(decrypted, str) else decrypted
        except Exception as e:
            self.logger.error("Failed to decrypt credentials for binding %s: %s", binding.id, e)
            return None

    def _log_step_failure(
        self, execution, step_index, action_name, provider, params, error_msg, start,
    ) -> Dict[str, Any]:
        """Log a failed step to PlaybookStepLog and return the result dict."""
        from models_action_interface import PlaybookStepLog

        duration_ms = int((time.monotonic() - start) * 1000)
        step_log = PlaybookStepLog(
            execution_id=execution.execution_id,
            step_index=step_index,
            action_name=action_name,
            provider=provider,
            params_sent=params,
            response_received=None,
            status='failed',
            error_message=error_msg,
            executed_at=datetime.utcnow(),
            duration_ms=duration_ms,
        )
        db.session.add(step_log)
        db.session.commit()

        return {
            'step_index': step_index,
            'action_name': action_name,
            'provider': provider,
            'status': 'failed',
            'error': error_msg,
            'duration_ms': duration_ms,
        }

    def _store_feedback(self, execution: PlaybookExecution, payload: Dict) -> None:
        """Store execution feedback for Qdrant recalibration loop."""
        try:
            from qdrant_feedback_loop import store_execution_feedback, ExecutionFeedback

            feedback = ExecutionFeedback(
                execution_id=execution.execution_id,
                customer_id=execution.customer_id,
                account_id=str(getattr(execution, 'account_id', '')),
                playbook_type=execution.playbook_id or '',
                outcome=payload.get('outcome', execution.outcome or 'unknown'),
                kpi_improvements=payload.get('kpi_improvements'),
            )
            store_execution_feedback(feedback)
        except Exception as e:
            self.logger.warning("Failed to store feedback (non-fatal): %s", e)

    def _record_status_update(
        self,
        execution: PlaybookExecution,
        *,
        status: str,
        message: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        # This wrote to a StatusUpdate model that has never existed in
        # models.py (no status_updates table either) — the import crashed
        # this whole module, taking the live n8n-callback route down with
        # ImportError. Status history already lives on the execution row
        # itself (status/updated_at, committed by callers before this runs);
        # log the transition rather than fabricate a new table.
        logger.info(
            "playbook execution %s status update: %s — %s (metadata=%s)",
            execution.id, status, message, metadata,
        )
