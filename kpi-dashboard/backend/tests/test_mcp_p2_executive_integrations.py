#!/usr/bin/env python3
"""P2: executive dashboard MCP tools + integration connector MCP registration."""

import os
import re
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_MCP = os.path.join(_BACKEND, 'mcp_server')
for _p in (_BACKEND, _MCP):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _tools_in(path):
    return set(re.findall(r'^@mcp\.tool(?:\(\))?\ndef ([a-z_0-9]+)\(', open(path, encoding='utf-8').read(), re.MULTILINE))


def test_executive_mcp_tools_exist():
    tools = _tools_in(os.path.join(_MCP, 'cs_pulse_executive.py'))
    for name in (
        'get_cro_dashboard_summary',
        'get_cfo_dashboard_summary',
        'get_ceo_dashboard_summary',
    ):
        assert name in tools


def test_executive_mcp_delegates_to_flask_handlers():
    util = open(os.path.join(_BACKEND, 'utils', 'executive_dashboard_mcp.py'), encoding='utf-8').read()
    assert 'fetch_executive_dashboard' in util
    assert 'cro_dashboard' in util
    assert 'cfo_dashboard' in util
    assert 'ceo_dashboard' in util
    assert 'X-Customer-ID' in util

    exec_src = open(os.path.join(_MCP, 'cs_pulse_executive.py'), encoding='utf-8').read()
    assert 'fetch_executive_dashboard' in exec_src


def test_integration_mcp_tools_registered():
    tools = _tools_in(os.path.join(_MCP, 'cs_pulse_integrations.py'))
    for name in (
        'list_integration_connectors',
        'get_integration_health',
        'get_sync_logs',
        'list_playbook_webhook_triggers',
    ):
        assert name in tools, f"Missing @mcp.tool {name}"


def test_mcp_server_loads_executive_and_integrations_modules():
    src = open(os.path.join(_MCP, 'cs_pulse_mcp_server.py'), encoding='utf-8').read()
    assert "'executive'" in src
    assert "'integrations'" in src
