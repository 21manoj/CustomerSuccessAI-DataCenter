"""
Playbook orchestration logic: hand-off to n8n workflows, retry policies, and status tracking.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import PlaybookExecution, CustomerWorkflowConfig, StatusUpdate
from security_utils import decrypt_credential, generate_webhook_signature

logger = logging.getLogger(__name__)


class HandoffError(Exception):
    """Raised when we fail to handoff execution to n8n after retries."""


class PlaybookOrchestrator:
    """Encapsulates the workflow for triggering and monitoring playbooks."""

    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)

    # ------------------------------------------------------------------ #
    # Public API
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
        try:
            db.session.commit()
        except SQLAlchemyError as exc:  # pragma: no cover - defensive
            db.session.rollback()
            self.logger.error("Failed to persist playbook callback: %s", exc)
            raise

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _record_status_update(
        self,
        execution: PlaybookExecution,
        *,
        status: str,
        message: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        update = StatusUpdate(
            execution_id=execution.id,
            status=status,
            message=message,
            metadata=metadata,
            external_ticket_url=execution.external_ticket_url,
            timestamp=datetime.utcnow(),
        )
        db.session.add(update)

