"""
Internal Provider — cs_pulse_internal
=======================================
Actions that are handled entirely within CS Pulse (no external API calls).
Used as the default/fallback provider and for logging-only actions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from providers.base import ProviderBase, ProviderResult

logger = logging.getLogger(__name__)


class InternalProvider(ProviderBase):
    """Provider for actions handled natively by CS Pulse."""

    PROVIDER_NAME = 'cs_pulse_internal'

    SUPPORTED_ACTIONS = {
        'log_event', 'create_task', 'send_alert', 'update_health_score',
        'flag_account', 'create_note', 'schedule_review', 'trigger_workflow',
    }

    def execute(
        self,
        action_name: str,
        params: Dict[str, Any],
        credentials: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> ProviderResult:
        logger.info(
            "InternalProvider executing %s with params=%s",
            action_name, list(params.keys()),
        )

        handler = getattr(self, f'_handle_{action_name}', None)
        if handler:
            return handler(params, config or {})

        # Default: log-only
        return ProviderResult(
            success=True,
            provider=self.PROVIDER_NAME,
            action_name=action_name,
            response_data={
                'message': f'Action {action_name} logged internally',
                'params': params,
                'timestamp': datetime.utcnow().isoformat(),
            },
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return True  # No external config needed

    def _handle_create_task(self, params: Dict, config: Dict) -> ProviderResult:
        return ProviderResult(
            success=True,
            provider=self.PROVIDER_NAME,
            action_name='create_task',
            response_data={
                'task_title': params.get('title', 'Untitled'),
                'assigned_to': params.get('assignee', 'unassigned'),
                'priority': params.get('priority', 'normal'),
                'created_at': datetime.utcnow().isoformat(),
            },
            external_id=f"internal-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        )

    def _handle_send_alert(self, params: Dict, config: Dict) -> ProviderResult:
        return ProviderResult(
            success=True,
            provider=self.PROVIDER_NAME,
            action_name='send_alert',
            response_data={
                'alert_type': params.get('type', 'info'),
                'message': params.get('message', ''),
                'recipients': params.get('recipients', []),
                'sent_at': datetime.utcnow().isoformat(),
            },
        )

    def _handle_flag_account(self, params: Dict, config: Dict) -> ProviderResult:
        return ProviderResult(
            success=True,
            provider=self.PROVIDER_NAME,
            action_name='flag_account',
            response_data={
                'account_id': params.get('account_id'),
                'flag_type': params.get('flag_type', 'at_risk'),
                'reason': params.get('reason', ''),
                'flagged_at': datetime.utcnow().isoformat(),
            },
        )
