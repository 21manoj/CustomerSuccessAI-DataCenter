"""
Slack Provider Adapter
=======================
Sends messages, alerts, and notifications to Slack channels.

Required config:
  - default_channel: Default Slack channel ID (e.g., "#cs-alerts")

Required credentials:
  - bot_token: Slack Bot Token (xoxb-...)
"""

import logging
import time
from typing import Any, Dict, Optional

import requests

from providers.base import ProviderBase, ProviderResult, ProviderError

logger = logging.getLogger(__name__)

SLACK_API_BASE = 'https://slack.com/api'


class SlackProvider(ProviderBase):
    """Provider adapter for Slack."""

    PROVIDER_NAME = 'slack'

    SUPPORTED_ACTIONS = {
        'send_alert', 'send_message', 'post_update', 'create_channel',
    }

    def execute(
        self,
        action_name: str,
        params: Dict[str, Any],
        credentials: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> ProviderResult:
        config = config or {}
        credentials = credentials or {}
        start = time.monotonic()

        if action_name in ('send_alert', 'send_message', 'post_update'):
            result = self._send_message(action_name, params, config, credentials)
        elif action_name == 'create_channel':
            result = self._create_channel(params, config, credentials)
        else:
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name=action_name,
                error_message=f'Unsupported Slack action: {action_name}',
            )

        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return bool(config.get('default_channel'))

    def health_check(self, credentials: Dict[str, Any]) -> bool:
        try:
            resp = requests.post(
                f'{SLACK_API_BASE}/auth.test',
                headers={'Authorization': f"Bearer {credentials['bot_token']}"},
                timeout=10,
            )
            data = resp.json()
            return data.get('ok', False)
        except Exception:
            return False

    def _send_message(
        self, action_name: str, params: Dict, config: Dict, creds: Dict,
    ) -> ProviderResult:
        channel = params.get('channel', config.get('default_channel', ''))
        text = params.get('message', params.get('text', ''))

        # Build blocks for richer formatting
        blocks = params.get('blocks')
        if not blocks and action_name == 'send_alert':
            alert_type = params.get('type', 'warning')
            emoji = {'critical': ':red_circle:', 'warning': ':warning:', 'info': ':information_source:'}.get(alert_type, ':bell:')
            blocks = [
                {
                    'type': 'section',
                    'text': {'type': 'mrkdwn', 'text': f'{emoji} *CS Alert*\n{text}'}
                },
            ]
            if params.get('account_name'):
                blocks.append({
                    'type': 'context',
                    'elements': [
                        {'type': 'mrkdwn', 'text': f"Account: *{params['account_name']}*"},
                    ]
                })

        payload = {
            'channel': channel,
            'text': text,
        }
        if blocks:
            payload['blocks'] = blocks

        try:
            resp = requests.post(
                f'{SLACK_API_BASE}/chat.postMessage',
                json=payload,
                headers={'Authorization': f"Bearer {creds['bot_token']}"},
                timeout=10,
            )
            data = resp.json()
            if data.get('ok'):
                return ProviderResult(
                    success=True,
                    provider=self.PROVIDER_NAME,
                    action_name=action_name,
                    response_data=data,
                    external_id=data.get('ts'),
                )
            else:
                return ProviderResult(
                    success=False,
                    provider=self.PROVIDER_NAME,
                    action_name=action_name,
                    error_message=data.get('error', 'Unknown Slack error'),
                )
        except requests.RequestException as e:
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name=action_name,
                error_message=str(e),
            )

    def _create_channel(self, params: Dict, config: Dict, creds: Dict) -> ProviderResult:
        channel_name = params.get('channel_name', '')
        try:
            resp = requests.post(
                f'{SLACK_API_BASE}/conversations.create',
                json={'name': channel_name, 'is_private': params.get('is_private', False)},
                headers={'Authorization': f"Bearer {creds['bot_token']}"},
                timeout=10,
            )
            data = resp.json()
            if data.get('ok'):
                ch = data.get('channel', {})
                return ProviderResult(
                    success=True,
                    provider=self.PROVIDER_NAME,
                    action_name='create_channel',
                    response_data=data,
                    external_id=ch.get('id'),
                )
            else:
                return ProviderResult(
                    success=False,
                    provider=self.PROVIDER_NAME,
                    action_name='create_channel',
                    error_message=data.get('error', 'Unknown Slack error'),
                )
        except requests.RequestException as e:
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name='create_channel',
                error_message=str(e),
            )
