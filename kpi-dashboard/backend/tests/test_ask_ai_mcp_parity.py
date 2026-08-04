#!/usr/bin/env python3
"""
P1 gap closure: Ask AI tools must route through MCP implementations when available.

Source-level contract tests — no fastmcp required.
"""

import os
import re
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

_ASK_AI = os.path.join(_BACKEND, 'ask_ai_tools.py')
_INTELLIGENCE = os.path.join(_BACKEND, 'mcp_server', 'cs_pulse_intelligence.py')
_ADMIN = os.path.join(_BACKEND, 'mcp_server', 'cs_pulse_admin.py')


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _mcp_tools_in(path):
    return set(re.findall(r'^@mcp\.tool(?:\(\))?\ndef ([a-z_0-9]+)\(', _read(path), re.MULTILINE))


def test_ask_ai_enables_mcp_when_fastmcp_available():
    text = _read(_ASK_AI)
    assert '_mcp_stack_available' in text
    assert '_MCP_AVAILABLE = _mcp_stack_available()' in text
    assert '_call_mcp(' in text


def test_ask_ai_tools_route_through_mcp_modules():
    via_mcp = _read(_ASK_AI).split('def _execute_via_mcp')[1].split('def _execute_direct')[0]
    expected_routes = {
        'list_accounts': 'cs_pulse_mcp_server',
        'get_account_health': 'cs_pulse_mcp_server',
        'get_playbook_recommendations': 'cs_pulse_revenue',
        'get_portfolio_revenue_breakdown': 'cs_pulse_intelligence',
        'analyze_root_cause': 'cs_pulse_intelligence',
        'explain_kpi_anomaly': 'cs_pulse_intelligence',
        'generate_action_plan': 'cs_pulse_intelligence',
        'get_calibration_history': 'cs_pulse_admin',
        'get_account_nrr_forecast': 'cs_pulse_predictor',
    }
    for tool, module in expected_routes.items():
        assert f"tool_name == '{tool}'" in via_mcp, f"{tool} missing from _execute_via_mcp"
        assert module in via_mcp.split(tool)[1].split('if tool_name')[0], (
            f"{tool} should route to {module}"
        )


def test_p1_mcp_tools_exist():
    intel = _mcp_tools_in(_INTELLIGENCE)
    admin = _mcp_tools_in(_ADMIN)
    for name in (
        'get_portfolio_revenue_breakdown',
        'analyze_root_cause',
        'explain_kpi_anomaly',
        'generate_action_plan',
    ):
        assert name in intel, f"Missing MCP tool {name} in cs_pulse_intelligence.py"
    assert 'get_calibration_history' in admin


def test_portfolio_breakdown_shared_util():
    assert os.path.isfile(os.path.join(_BACKEND, 'utils', 'portfolio_revenue_breakdown.py'))
    intel = _read(_INTELLIGENCE)
    assert 'build_portfolio_revenue_breakdown' in intel
    ask = _read(_ASK_AI)
    assert 'build_portfolio_revenue_breakdown' in ask
