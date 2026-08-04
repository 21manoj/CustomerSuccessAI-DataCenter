#!/usr/bin/env python3
"""P3: read-only onboarding agent MCP tools + module registry counts."""

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


def test_onboarding_agent_mcp_tools_exist():
    tools = _tools_in(os.path.join(_MCP, 'cs_pulse_onboarding_agent.py'))
    assert 'get_onboarding_activation_plan' in tools
    assert 'get_onboarding_ttfv_status' in tools


def test_onboarding_agent_mcp_is_read_only():
    src = open(os.path.join(_MCP, 'cs_pulse_onboarding_agent.py'), encoding='utf-8').read()
    assert 'analyze_new_customer' not in src
    assert 'OnboardingAgent' in src
    assert 'get_activation_plan' in src
    assert 'evaluate_activation_readiness' in src
    assert 'check_entitlement' in src


def test_mcp_server_registry_includes_onboarding_agent():
    src = open(os.path.join(_MCP, 'cs_pulse_mcp_server.py'), encoding='utf-8').read()
    assert "'onboarding_agent': 2" in src
    assert 'cs_pulse_onboarding_agent.py' in src


def test_module_tool_counts_match_source():
    """Registry counts in cs_pulse_mcp_server should match @mcp.tool defs (+6 core)."""
    modules = {
        'cs_pulse_intelligence.py': 13,
        'cs_pulse_revenue.py': 13,
        'cs_pulse_onboarding.py': 15,
        'cs_pulse_admin.py': 9,
        'cs_pulse_predictor.py': 4,
        'cs_pulse_executive.py': 3,
        'cs_pulse_integrations.py': 4,
        'cs_pulse_onboarding_agent.py': 2,
    }
    for fname, expected in modules.items():
        actual = len(_tools_in(os.path.join(_MCP, fname)))
        assert actual == expected, f"{fname}: expected {expected} tools, found {actual}"
