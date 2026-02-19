"""
Salesforce Provider Adapter
=============================
Creates and updates Salesforce records (Cases, Tasks, Notes) as part
of playbook execution.

Required config:
  - instance_url: Salesforce instance (e.g., "https://company.my.salesforce.com")
  - api_version: API version (default: "v59.0")

Required credentials:
  - access_token: OAuth2 access token
  - (or) client_id, client_secret, refresh_token for auto-refresh
"""

import logging
import time
from typing import Any, Dict, Optional

import requests

from providers.base import ProviderBase, ProviderResult, ProviderError

logger = logging.getLogger(__name__)


class SalesforceProvider(ProviderBase):
    """Provider adapter for Salesforce."""

    PROVIDER_NAME = 'salesforce'

    SUPPORTED_ACTIONS = {
        'create_task', 'create_case', 'update_record',
        'add_note', 'update_field', 'create_opportunity',
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

        if action_name == 'create_task':
            result = self._create_task(params, config, credentials)
        elif action_name == 'create_case':
            result = self._create_case(params, config, credentials)
        elif action_name in ('update_record', 'update_field'):
            result = self._update_record(params, config, credentials)
        elif action_name == 'add_note':
            result = self._add_note(params, config, credentials)
        elif action_name == 'create_opportunity':
            result = self._create_opportunity(params, config, credentials)
        else:
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name=action_name,
                error_message=f'Unsupported Salesforce action: {action_name}',
            )

        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return bool(config.get('instance_url'))

    def health_check(self, credentials: Dict[str, Any]) -> bool:
        try:
            instance_url = credentials.get('instance_url', '')
            resp = requests.get(
                f"{instance_url}/services/data/",
                headers=self._auth_headers(credentials),
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _auth_headers(self, creds: Dict) -> Dict:
        return {
            'Authorization': f"Bearer {creds.get('access_token', '')}",
            'Content-Type': 'application/json',
        }

    def _api_url(self, config: Dict, sobject: str) -> str:
        instance = config['instance_url'].rstrip('/')
        version = config.get('api_version', 'v59.0')
        return f"{instance}/services/data/{version}/sobjects/{sobject}"

    def _create_task(self, params: Dict, config: Dict, creds: Dict) -> ProviderResult:
        payload = {
            'Subject': params.get('title', params.get('subject', 'CS Playbook Task')),
            'Description': params.get('description', ''),
            'Status': params.get('status', 'Not Started'),
            'Priority': params.get('priority', 'Normal'),
            'WhatId': params.get('account_id', params.get('what_id')),
            'OwnerId': params.get('assignee', params.get('owner_id')),
            'ActivityDate': params.get('due_date'),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._create_record('Task', payload, config, creds, 'create_task')

    def _create_case(self, params: Dict, config: Dict, creds: Dict) -> ProviderResult:
        payload = {
            'Subject': params.get('subject', 'CS Playbook Case'),
            'Description': params.get('description', ''),
            'Status': params.get('status', 'New'),
            'Priority': params.get('priority', 'Medium'),
            'AccountId': params.get('account_id'),
            'Origin': params.get('origin', 'CS Platform'),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._create_record('Case', payload, config, creds, 'create_case')

    def _create_opportunity(self, params: Dict, config: Dict, creds: Dict) -> ProviderResult:
        payload = {
            'Name': params.get('name', 'CS Expansion Opportunity'),
            'AccountId': params.get('account_id'),
            'StageName': params.get('stage', 'Prospecting'),
            'Amount': params.get('amount'),
            'CloseDate': params.get('close_date'),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._create_record('Opportunity', payload, config, creds, 'create_opportunity')

    def _add_note(self, params: Dict, config: Dict, creds: Dict) -> ProviderResult:
        payload = {
            'Title': params.get('title', 'CS Note'),
            'Body': params.get('body', params.get('note', '')),
            'ParentId': params.get('parent_id', params.get('account_id')),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._create_record('Note', payload, config, creds, 'add_note')

    def _update_record(self, params: Dict, config: Dict, creds: Dict) -> ProviderResult:
        sobject = params.get('sobject', 'Account')
        record_id = params.get('record_id', '')
        fields = params.get('fields', {})
        instance = config['instance_url'].rstrip('/')
        version = config.get('api_version', 'v59.0')
        url = f"{instance}/services/data/{version}/sobjects/{sobject}/{record_id}"
        try:
            resp = requests.patch(
                url, json=fields,
                headers=self._auth_headers(creds),
                timeout=15,
            )
            resp.raise_for_status()
            return ProviderResult(
                success=True,
                provider=self.PROVIDER_NAME,
                action_name='update_record',
                external_id=record_id,
                response_data={'sobject': sobject, 'fields_updated': list(fields.keys())},
            )
        except requests.RequestException as e:
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name='update_record',
                error_message=str(e),
            )

    def _create_record(
        self, sobject: str, payload: Dict, config: Dict, creds: Dict, action_name: str,
    ) -> ProviderResult:
        try:
            resp = requests.post(
                self._api_url(config, sobject),
                json=payload,
                headers=self._auth_headers(creds),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            record_id = data.get('id', '')
            instance = config['instance_url'].rstrip('/')
            return ProviderResult(
                success=True,
                provider=self.PROVIDER_NAME,
                action_name=action_name,
                response_data=data,
                external_id=record_id,
                external_url=f"{instance}/{record_id}" if record_id else None,
            )
        except requests.RequestException as e:
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name=action_name,
                error_message=str(e),
            )
