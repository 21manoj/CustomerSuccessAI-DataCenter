#!/usr/bin/env python3
"""
n8n Callback Simulator for CS Pulse Load Testing (Ring 3)

Simulates n8n returning playbook execution results for specific
external tools: Jira ticket creation, Slack message delivery, and
failure scenarios. Each callback type includes tool-specific payload
details that match what the real n8n workflows would produce.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class N8NCallbackSimulator:
    """
    Simulates n8n returning playbook execution results to CS Pulse
    via the /api/webhooks/playbook-callback endpoint.

    Provides specialized callbacks for each external tool integration:
      - Jira — ticket creation with issue key, URL, and metadata
      - Slack — message delivery with channel, timestamp, and thread
      - Failure — error reporting with retry eligibility
    """

    CALLBACK_ENDPOINT = '/api/webhooks/playbook-callback'

    def __init__(self):
        logger.debug("N8NCallbackSimulator initialized")

    # ------------------------------------------------------------------
    # Jira callback
    # ------------------------------------------------------------------

    def simulate_jira_callback(
        self,
        client,
        execution_id: str,
        project_key: str = 'CS',
        issue_type: str = 'Task',
    ) -> Dict[str, Any]:
        """
        Simulate n8n callback reporting successful Jira ticket creation.

        The payload matches what the n8n Jira node would return after
        creating a ticket via the Jira REST API.

        Args:
            client: CSPulseClient instance (authenticated).
            execution_id: Playbook execution ID to report on.
            project_key: Jira project key (default 'CS').
            issue_type: Jira issue type (default 'Task').

        Returns:
            Dict with callback_accepted, jira_ticket_id, response, error.
        """
        ticket_num = uuid.uuid4().hex[:5].upper()
        jira_ticket_id = f'{project_key}-{ticket_num}'
        jira_base_url = 'https://company.atlassian.net'

        payload = {
            'execution_id': execution_id,
            'status': 'COMPLETED',
            'tool': 'jira',
            'external_ticket_id': jira_ticket_id,
            'completed_at': datetime.utcnow().isoformat() + 'Z',
            'source': 'n8n_callback_simulator',
            'workflow_run_id': f'n8n-jira-{uuid.uuid4().hex[:12]}',
            'outputs': {
                'jira_ticket_id': jira_ticket_id,
                'jira_ticket_url': f'{jira_base_url}/browse/{jira_ticket_id}',
                'jira_project': project_key,
                'jira_issue_type': issue_type,
                'jira_status': 'Open',
                'jira_priority': 'High',
                'jira_assignee': 'csm-team@company.com',
                'jira_summary': f'[CS Pulse] Automated follow-up for execution {execution_id}',
                'jira_created_at': datetime.utcnow().isoformat() + 'Z',
                'actions_taken': [
                    f'Created Jira ticket {jira_ticket_id}',
                    'Set priority to High',
                    'Assigned to CSM team queue',
                    'Added CS Pulse context as ticket description',
                ],
            },
        }

        logger.debug(f"  Jira callback: execution={execution_id}, ticket={jira_ticket_id}")
        response = client.post(self.CALLBACK_ENDPOINT, payload)

        result = {
            'callback_accepted': response is not None and response.get('status') != 'error',
            'jira_ticket_id': jira_ticket_id,
            'response': response,
            'error': None,
        }

        if not result['callback_accepted']:
            result['error'] = (
                response.get('error', 'Jira callback rejected')
                if response else 'No response from callback endpoint'
            )
            logger.warning(f"Jira callback not accepted: {result['error']}")
        else:
            logger.info(f"Jira callback accepted: {jira_ticket_id} for execution {execution_id}")

        return result

    # ------------------------------------------------------------------
    # Slack callback
    # ------------------------------------------------------------------

    def simulate_slack_callback(
        self,
        client,
        execution_id: str,
        channel: str = '#cs-alerts',
    ) -> Dict[str, Any]:
        """
        Simulate n8n callback reporting successful Slack message delivery.

        The payload matches what the n8n Slack node would return after
        posting a message via the Slack Web API.

        Args:
            client: CSPulseClient instance (authenticated).
            execution_id: Playbook execution ID to report on.
            channel: Slack channel the message was posted to.

        Returns:
            Dict with callback_accepted, slack_message_ts, response, error.
        """
        ts = f'{int(datetime.utcnow().timestamp())}.{uuid.uuid4().hex[:6]}'
        thread_ts = f'{int(datetime.utcnow().timestamp())}.{uuid.uuid4().hex[:6]}'

        payload = {
            'execution_id': execution_id,
            'status': 'COMPLETED',
            'tool': 'slack',
            'completed_at': datetime.utcnow().isoformat() + 'Z',
            'source': 'n8n_callback_simulator',
            'workflow_run_id': f'n8n-slack-{uuid.uuid4().hex[:12]}',
            'outputs': {
                'slack_channel': channel,
                'slack_channel_id': f'C{uuid.uuid4().hex[:9].upper()}',
                'slack_message_ts': ts,
                'slack_thread_ts': thread_ts,
                'slack_permalink': f'https://company.slack.com/archives/{channel}/p{ts.replace(".", "")}',
                'message_preview': f'[CS Pulse Alert] Playbook execution {execution_id} completed',
                'mentions': ['@csm-team', '@cs-lead'],
                'actions_taken': [
                    f'Posted alert to {channel}',
                    'Mentioned @csm-team and @cs-lead',
                    'Included health score summary in thread',
                ],
            },
        }

        logger.debug(f"  Slack callback: execution={execution_id}, channel={channel}")
        response = client.post(self.CALLBACK_ENDPOINT, payload)

        result = {
            'callback_accepted': response is not None and response.get('status') != 'error',
            'slack_message_ts': ts,
            'response': response,
            'error': None,
        }

        if not result['callback_accepted']:
            result['error'] = (
                response.get('error', 'Slack callback rejected')
                if response else 'No response from callback endpoint'
            )
            logger.warning(f"Slack callback not accepted: {result['error']}")
        else:
            logger.info(f"Slack callback accepted: {channel} ts={ts} for execution {execution_id}")

        return result

    # ------------------------------------------------------------------
    # Failure callback
    # ------------------------------------------------------------------

    def simulate_failure_callback(
        self,
        client,
        execution_id: str,
        error_msg: str = 'External service unavailable (simulated)',
        error_code: str = 'EXTERNAL_SERVICE_ERROR',
        retry_eligible: bool = True,
    ) -> Dict[str, Any]:
        """
        Simulate n8n callback reporting a workflow failure.

        This represents the case where n8n tried to execute a playbook
        step (e.g., create a Jira ticket) but the external service
        returned an error.

        Args:
            client: CSPulseClient instance (authenticated).
            execution_id: Playbook execution ID to report on.
            error_msg: Human-readable error message.
            error_code: Machine-readable error code.
            retry_eligible: Whether the operation can be retried.

        Returns:
            Dict with callback_accepted, response, error.
        """
        payload = {
            'execution_id': execution_id,
            'status': 'FAILED',
            'tool': 'unknown',
            'completed_at': datetime.utcnow().isoformat() + 'Z',
            'source': 'n8n_callback_simulator',
            'workflow_run_id': f'n8n-fail-{uuid.uuid4().hex[:12]}',
            'outputs': {
                'error_message': error_msg,
                'error_code': error_code,
                'retry_eligible': retry_eligible,
                'attempt_number': 1,
                'max_attempts': 3,
                'partial_actions': [],
                'actions_taken': [],
            },
        }

        logger.debug(
            f"  Failure callback: execution={execution_id}, error={error_msg}"
        )
        response = client.post(self.CALLBACK_ENDPOINT, payload)

        result = {
            'callback_accepted': response is not None and response.get('status') != 'error',
            'response': response,
            'error': None,
        }

        if not result['callback_accepted']:
            result['error'] = (
                response.get('error', 'Failure callback rejected')
                if response else 'No response from callback endpoint'
            )
            logger.warning(f"Failure callback not accepted: {result['error']}")
        else:
            logger.info(f"Failure callback accepted for execution {execution_id}")

        return result
