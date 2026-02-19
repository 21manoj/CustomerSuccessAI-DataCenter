"""
Jira Provider Adapter
======================
Creates and updates Jira issues as part of playbook execution.

Required config:
  - base_url: Jira instance URL (e.g., "https://company.atlassian.net")
  - project_key: Jira project key (e.g., "CS")
  - issue_type: Default issue type (e.g., "Task")

Required credentials:
  - email: Jira user email
  - api_token: Jira API token
"""

import logging
import time
from typing import Any, Dict, Optional

import requests

from providers.base import ProviderBase, ProviderResult, ProviderError

logger = logging.getLogger(__name__)


class JiraProvider(ProviderBase):
    """Provider adapter for Atlassian Jira."""

    PROVIDER_NAME = 'jira'

    SUPPORTED_ACTIONS = {
        'create_task', 'create_issue', 'update_issue',
        'add_comment', 'transition_issue',
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

        if action_name in ('create_task', 'create_issue'):
            result = self._create_issue(params, config, credentials)
        elif action_name == 'add_comment':
            result = self._add_comment(params, config, credentials)
        elif action_name == 'update_issue':
            result = self._update_issue(params, config, credentials)
        elif action_name == 'transition_issue':
            result = self._transition_issue(params, config, credentials)
        else:
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name=action_name,
                error_message=f'Unsupported Jira action: {action_name}',
            )

        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    def validate_config(self, config: Dict[str, Any]) -> bool:
        required = ['base_url', 'project_key']
        return all(config.get(k) for k in required)

    def health_check(self, credentials: Dict[str, Any]) -> bool:
        try:
            base_url = credentials.get('base_url', '')
            resp = requests.get(
                f"{base_url}/rest/api/3/myself",
                auth=(credentials['email'], credentials['api_token']),
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _create_issue(self, params: Dict, config: Dict, creds: Dict) -> ProviderResult:
        base_url = config['base_url'].rstrip('/')
        payload = {
            'fields': {
                'project': {'key': config['project_key']},
                'summary': params.get('title', params.get('summary', 'CS Playbook Task')),
                'description': {
                    'type': 'doc', 'version': 1,
                    'content': [{
                        'type': 'paragraph',
                        'content': [{'type': 'text', 'text': params.get('description', '')}]
                    }]
                },
                'issuetype': {'name': params.get('issue_type', config.get('issue_type', 'Task'))},
            }
        }

        if params.get('assignee'):
            payload['fields']['assignee'] = {'accountId': params['assignee']}
        if params.get('priority'):
            payload['fields']['priority'] = {'name': params['priority']}
        if params.get('labels'):
            payload['fields']['labels'] = params['labels']

        try:
            resp = requests.post(
                f"{base_url}/rest/api/3/issue",
                json=payload,
                auth=(creds['email'], creds['api_token']),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            issue_key = data.get('key', '')
            return ProviderResult(
                success=True,
                provider=self.PROVIDER_NAME,
                action_name='create_issue',
                response_data=data,
                external_id=issue_key,
                external_url=f"{base_url}/browse/{issue_key}",
            )
        except requests.RequestException as e:
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name='create_issue',
                error_message=str(e),
            )

    def _add_comment(self, params: Dict, config: Dict, creds: Dict) -> ProviderResult:
        base_url = config['base_url'].rstrip('/')
        issue_key = params.get('issue_key', '')
        body = {
            'body': {
                'type': 'doc', 'version': 1,
                'content': [{
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': params.get('comment', '')}]
                }]
            }
        }
        try:
            resp = requests.post(
                f"{base_url}/rest/api/3/issue/{issue_key}/comment",
                json=body,
                auth=(creds['email'], creds['api_token']),
                timeout=15,
            )
            resp.raise_for_status()
            return ProviderResult(
                success=True,
                provider=self.PROVIDER_NAME,
                action_name='add_comment',
                response_data=resp.json(),
                external_id=issue_key,
            )
        except requests.RequestException as e:
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name='add_comment',
                error_message=str(e),
            )

    def _update_issue(self, params: Dict, config: Dict, creds: Dict) -> ProviderResult:
        base_url = config['base_url'].rstrip('/')
        issue_key = params.get('issue_key', '')
        fields = params.get('fields', {})
        try:
            resp = requests.put(
                f"{base_url}/rest/api/3/issue/{issue_key}",
                json={'fields': fields},
                auth=(creds['email'], creds['api_token']),
                timeout=15,
            )
            resp.raise_for_status()
            return ProviderResult(
                success=True,
                provider=self.PROVIDER_NAME,
                action_name='update_issue',
                external_id=issue_key,
            )
        except requests.RequestException as e:
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name='update_issue',
                error_message=str(e),
            )

    def _transition_issue(self, params: Dict, config: Dict, creds: Dict) -> ProviderResult:
        base_url = config['base_url'].rstrip('/')
        issue_key = params.get('issue_key', '')
        transition_id = params.get('transition_id', '')
        try:
            resp = requests.post(
                f"{base_url}/rest/api/3/issue/{issue_key}/transitions",
                json={'transition': {'id': str(transition_id)}},
                auth=(creds['email'], creds['api_token']),
                timeout=15,
            )
            resp.raise_for_status()
            return ProviderResult(
                success=True,
                provider=self.PROVIDER_NAME,
                action_name='transition_issue',
                external_id=issue_key,
            )
        except requests.RequestException as e:
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name='transition_issue',
                error_message=str(e),
            )
