#!/usr/bin/env python3
"""
Test Suite 5 — MCP Interfaces
===============================
Tests: MCP integration module, mock MCP servers, provider adapters
that bridge MCP → Action Interface.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


# ============================================================
# MCP INTEGRATION LAYER TESTS
# ============================================================

class TestMCPIntegration:
    def test_mcp_integration_import(self):
        from mcp_integration import MCPIntegration
        assert MCPIntegration is not None

    def test_mcp_integration_init(self):
        from mcp_integration import MCPIntegration
        mcp = MCPIntegration(customer_id=1)
        assert mcp.customer_id == 1
        assert mcp.sessions == {}
        assert mcp.connected is False

    def test_is_mcp_enabled(self):
        from mcp_integration import is_mcp_enabled
        result = is_mcp_enabled(1)
        assert isinstance(result, bool)

    def test_get_mcp_config(self):
        from mcp_integration import get_mcp_config
        config = get_mcp_config(1)
        assert isinstance(config, dict)


# ============================================================
# MOCK MCP SERVER TESTS
# ============================================================

class TestMockServers:
    def test_salesforce_server_import(self):
        try:
            from mcp_servers.mock_salesforce_server import MockSalesforceMCPServer
            server = MockSalesforceMCPServer()
            assert server is not None
        except ImportError:
            pytest.skip("Salesforce mock server not available")

    def test_servicenow_server_import(self):
        try:
            from mcp_servers.mock_servicenow_server import MockServiceNowMCPServer
            server = MockServiceNowMCPServer()
            assert server is not None
        except ImportError:
            pytest.skip("ServiceNow mock server not available")

    def test_survey_server_import(self):
        try:
            from mcp_servers.mock_survey_server import MockSurveyMCPServer
            server = MockSurveyMCPServer()
            assert server is not None
        except ImportError:
            pytest.skip("Survey mock server not available")


# ============================================================
# PROVIDER ADAPTER TESTS (MCP → Action Interface bridge)
# ============================================================

class TestProviderAdapters:
    def test_provider_registry_loads(self):
        from providers.registry import get_provider, PROVIDER_REGISTRY
        registry = PROVIDER_REGISTRY()
        assert len(registry) >= 4  # internal, jira, slack, salesforce, email

    def test_internal_provider_execute(self):
        from providers.internal_provider import InternalProvider
        provider = InternalProvider()
        result = provider.execute(
            action_name='log_event',
            params={'message': 'Test event'},
        )
        assert result.success is True
        assert result.provider == 'cs_pulse_internal'

    def test_internal_provider_create_task(self):
        from providers.internal_provider import InternalProvider
        provider = InternalProvider()
        result = provider.execute(
            action_name='create_task',
            params={'title': 'Test Task', 'assignee': 'csm@test.com'},
        )
        assert result.success is True
        assert result.external_id is not None

    def test_internal_provider_send_alert(self):
        from providers.internal_provider import InternalProvider
        provider = InternalProvider()
        result = provider.execute(
            action_name='send_alert',
            params={'type': 'warning', 'message': 'Test alert'},
        )
        assert result.success is True

    def test_internal_provider_flag_account(self):
        from providers.internal_provider import InternalProvider
        provider = InternalProvider()
        result = provider.execute(
            action_name='flag_account',
            params={'account_id': '123', 'flag_type': 'at_risk'},
        )
        assert result.success is True

    def test_jira_provider_validate_config(self):
        from providers.jira_provider import JiraProvider
        provider = JiraProvider()
        assert provider.validate_config({'base_url': 'https://x.atlassian.net', 'project_key': 'CS'}) is True
        assert provider.validate_config({}) is False

    def test_slack_provider_validate_config(self):
        from providers.slack_provider import SlackProvider
        provider = SlackProvider()
        assert provider.validate_config({'default_channel': '#cs-alerts'}) is True
        assert provider.validate_config({}) is False

    def test_salesforce_provider_validate_config(self):
        from providers.salesforce_provider import SalesforceProvider
        provider = SalesforceProvider()
        assert provider.validate_config({'instance_url': 'https://x.salesforce.com'}) is True
        assert provider.validate_config({}) is False

    def test_email_provider_validate_config(self):
        from providers.email_provider import EmailProvider
        provider = EmailProvider()
        assert provider.validate_config({'from_email': 'cs@test.com'}) is True
        assert provider.validate_config({}) is False


# ============================================================
# PROVIDER BASE CLASS TESTS
# ============================================================

class TestProviderBase:
    def test_provider_result_to_dict(self):
        from providers.base import ProviderResult
        result = ProviderResult(
            success=True,
            provider='test',
            action_name='test_action',
            external_id='EXT-123',
            external_url='https://example.com/EXT-123',
            duration_ms=150,
        )
        d = result.to_dict()
        assert d['success'] is True
        assert d['provider'] == 'test'
        assert d['external_id'] == 'EXT-123'
        assert d['duration_ms'] == 150

    def test_provider_error(self):
        from providers.base import ProviderError
        err = ProviderError('Test error', provider='jira', retriable=True)
        assert str(err) == 'Test error'
        assert err.provider == 'jira'
        assert err.retriable is True

    def test_provider_result_failure(self):
        from providers.base import ProviderResult
        result = ProviderResult(
            success=False,
            provider='slack',
            action_name='send_message',
            error_message='Channel not found',
        )
        assert result.success is False
        assert result.error_message == 'Channel not found'


# ============================================================
# ENHANCED RAG WITH MCP TESTS
# ============================================================

class TestEnhancedRAG:
    def test_enhanced_rag_import(self):
        try:
            from enhanced_rag_with_mcp import EnhancedRAGWithMCP
            assert EnhancedRAGWithMCP is not None
        except ImportError:
            pytest.skip("Enhanced RAG with MCP not available")


# ============================================================
# PROVIDER UNSUPPORTED ACTION TESTS
# ============================================================

class TestUnsupportedActions:
    def test_jira_unsupported_action(self):
        from providers.jira_provider import JiraProvider
        provider = JiraProvider()
        result = provider.execute(
            action_name='nonexistent_action',
            params={},
            config={'base_url': 'https://x.atlassian.net', 'project_key': 'CS'},
        )
        assert result.success is False

    def test_slack_unsupported_action(self):
        from providers.slack_provider import SlackProvider
        provider = SlackProvider()
        result = provider.execute(
            action_name='nonexistent_action',
            params={},
        )
        assert result.success is False

    def test_salesforce_unsupported_action(self):
        from providers.salesforce_provider import SalesforceProvider
        provider = SalesforceProvider()
        result = provider.execute(
            action_name='nonexistent_action',
            params={},
        )
        assert result.success is False


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
