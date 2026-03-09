#!/usr/bin/env python3
"""
n8n Webhook Simulator for CS Pulse Load Testing (Ring 3)

Simulates n8n pushing data to CS Pulse via webhook endpoints.
In production, n8n workflows pull data from Google Sheets and push
to the CS Pulse data-ingestion API. This simulator replaces both
n8n and Google Sheets for fully offline testing.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class N8NWebhookSimulator:
    """
    Simulates n8n webhook interactions with CS Pulse.

    Covers two main patterns:
      1. Data push — n8n forwards KPI/signal data to data-ingestion endpoints
      2. Playbook callback — n8n reports back after executing a playbook step
    """

    def __init__(self):
        logger.debug("N8NWebhookSimulator initialized")

    # ------------------------------------------------------------------
    # Data push simulation (n8n → CS Pulse data-ingestion)
    # ------------------------------------------------------------------

    def simulate_data_push(
        self,
        client,
        kpi_data: List[Dict[str, Any]],
        batch_size: int = 50,
    ) -> Dict[str, Any]:
        """
        POST KPI data to /api/data-ingestion/kpis as if n8n is pushing
        a batch of Google Sheets rows.

        Sends data in batches (matching real n8n behavior where large
        sheets are chunked).

        Args:
            client: CSPulseClient instance (authenticated).
            kpi_data: List of KPI measurement dicts (from GoogleSheetsSimulator).
            batch_size: Records per batch (default 50).

        Returns:
            Dict with push_results, total_sent, total_accepted, errors.
        """
        results = {
            'total_sent': 0,
            'total_accepted': 0,
            'batches': 0,
            'errors': [],
        }

        # Chunk into batches
        for i in range(0, len(kpi_data), batch_size):
            batch = kpi_data[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            payload = {
                'records': batch,
                'source': 'n8n_webhook_simulator',
                'batch_id': str(uuid.uuid4()),
                'batch_number': batch_num,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
            }

            logger.debug(
                f"  Pushing KPI batch {batch_num} ({len(batch)} records)"
            )

            response = client.post('/api/data-ingestion/kpis', payload)
            results['total_sent'] += len(batch)
            results['batches'] += 1

            if response and response.get('status') != 'error':
                accepted = response.get('accepted', len(batch))
                results['total_accepted'] += accepted
                logger.debug(f"    Batch {batch_num}: {accepted} accepted")
            else:
                error_msg = (
                    response.get('error', 'Unknown error')
                    if response else 'No response'
                )
                results['errors'].append(
                    f"Batch {batch_num} failed: {error_msg}"
                )
                logger.warning(f"    Batch {batch_num} failed: {error_msg}")

        logger.info(
            f"Data push complete: {results['total_accepted']}/{results['total_sent']} "
            f"accepted in {results['batches']} batches"
        )
        return results

    def simulate_signal_push(
        self,
        client,
        signal_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        POST signal data to /api/data-ingestion/signals as if n8n
        is forwarding qualitative signals from a Google Sheet or
        alerting system.

        Args:
            client: CSPulseClient instance (authenticated).
            signal_data: List of signal dicts (from GoogleSheetsSimulator).

        Returns:
            Dict with total_sent, total_accepted, errors.
        """
        payload = {
            'records': signal_data,
            'source': 'n8n_webhook_simulator',
            'batch_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }

        logger.debug(f"  Pushing {len(signal_data)} signals")
        response = client.post('/api/data-ingestion/signals', payload)

        result = {
            'total_sent': len(signal_data),
            'total_accepted': 0,
            'errors': [],
        }

        if response and response.get('status') != 'error':
            result['total_accepted'] = response.get('accepted', len(signal_data))
            logger.info(f"Signal push: {result['total_accepted']}/{result['total_sent']} accepted")
        else:
            error_msg = (
                response.get('error', 'Unknown error')
                if response else 'No response'
            )
            result['errors'].append(f"Signal push failed: {error_msg}")
            logger.warning(f"Signal push failed: {error_msg}")

        return result

    # ------------------------------------------------------------------
    # Playbook callback simulation (n8n → CS Pulse webhook)
    # ------------------------------------------------------------------

    def simulate_playbook_callback(
        self,
        client,
        execution_id: str,
        status: str = 'COMPLETED',
        outputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        POST to /api/webhooks/playbook-callback with a realistic payload,
        simulating n8n reporting back after executing a playbook workflow.

        Args:
            client: CSPulseClient instance (authenticated).
            execution_id: The playbook execution ID to report on.
            status: Execution status ('COMPLETED', 'FAILED', 'PARTIAL').
            outputs: Workflow output details (auto-generated if None).

        Returns:
            Dict with callback_accepted (bool), response, error.
        """
        if outputs is None:
            outputs = self._generate_default_outputs(status)

        payload = {
            'execution_id': execution_id,
            'status': status,
            'external_ticket_id': f'EXT-{uuid.uuid4().hex[:8].upper()}',
            'outputs': outputs,
            'completed_at': datetime.utcnow().isoformat() + 'Z',
            'source': 'n8n_webhook_simulator',
            'workflow_run_id': f'n8n-run-{uuid.uuid4().hex[:12]}',
        }

        logger.debug(
            f"  Playbook callback: execution={execution_id}, status={status}"
        )

        response = client.post('/api/webhooks/playbook-callback', payload)

        result = {
            'callback_accepted': response is not None and response.get('status') != 'error',
            'response': response,
            'error': None,
        }

        if not result['callback_accepted']:
            result['error'] = (
                response.get('error', 'Callback rejected')
                if response else 'No response from callback endpoint'
            )
            logger.warning(f"Playbook callback not accepted: {result['error']}")
        else:
            logger.info(f"Playbook callback accepted for execution {execution_id}")

        return result

    def _generate_default_outputs(self, status: str) -> Dict[str, Any]:
        """Generate realistic default outputs based on execution status."""
        if status == 'COMPLETED':
            return {
                'actions_taken': [
                    'Created Jira ticket for follow-up',
                    'Sent Slack notification to #cs-alerts',
                    'Updated CRM record with latest notes',
                ],
                'jira_ticket_id': f'CS-{uuid.uuid4().hex[:5].upper()}',
                'jira_ticket_url': f'https://company.atlassian.net/browse/CS-{uuid.uuid4().hex[:5].upper()}',
                'slack_channel': '#cs-alerts',
                'slack_message_ts': f'{int(datetime.utcnow().timestamp())}.000001',
                'duration_seconds': 12.5,
            }
        elif status == 'FAILED':
            return {
                'error_message': 'Jira API returned 503 — service temporarily unavailable',
                'error_code': 'EXTERNAL_SERVICE_ERROR',
                'retry_eligible': True,
                'partial_actions': [
                    'Slack notification sent successfully',
                ],
            }
        else:  # PARTIAL
            return {
                'actions_taken': [
                    'Sent Slack notification to #cs-alerts',
                ],
                'actions_failed': [
                    'Jira ticket creation timed out',
                ],
                'partial_reason': 'One or more external actions failed',
            }
