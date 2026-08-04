#!/usr/bin/env python3
"""
P0 gap closure: documented MCP onboarding tools must exist and stay registered.

Guards against auth / onboarding ONBOARDING_TOOLS drift and missing @mcp.tool
implementations (get_onboarding_status, validate_csv, etc.).
"""

import os
import re
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_MCP = os.path.join(_BACKEND, 'mcp_server')
for _p in (_BACKEND, _MCP):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ONBOARDING_SRC = os.path.join(_MCP, 'cs_pulse_onboarding.py')


def _onboarding_tool_names_from_source() -> set:
    """Parse @mcp.tool def name blocks from cs_pulse_onboarding.py."""
    text = open(_ONBOARDING_SRC, encoding='utf-8').read()
    return set(re.findall(r'^@mcp\.tool(?:\(\))?\ndef ([a-z_0-9]+)\(', text, re.MULTILINE))


def test_auth_and_registry_tool_sets_match():
    from onboarding_tool_registry import ONBOARDING_TOOLS as registry_set
    from mcp_server.auth import ONBOARDING_TOOLS as auth_set

    assert registry_set == auth_set
    assert len(registry_set) == 15


def test_p0_onboarding_tools_exist_in_source():
    """Documented ghost tools must have @mcp.tool implementations."""
    names = _onboarding_tool_names_from_source()
    for required in (
        'get_reference_customer',
        'get_vertical_config',
        'validate_csv',
        'get_onboarding_status',
    ):
        assert required in names, f"Missing @mcp.tool def {required} in cs_pulse_onboarding.py"

    from onboarding_tool_registry import ONBOARDING_TOOLS
    missing_impl = ONBOARDING_TOOLS - names
    assert not missing_impl, f"ONBOARDING_TOOLS without @mcp.tool impl: {sorted(missing_impl)}"


def test_validate_csv_delegates_to_dry_run_upload():
    text = open(_ONBOARDING_SRC, encoding='utf-8').read()
    assert 'def validate_csv(' in text
    assert 'dry_run=True' in text.split('def validate_csv(')[1].split('def get_onboarding_status')[0]
    assert '_upload_csv_impl' in text


def test_get_onboarding_status_wires_checklist_and_progress():
    text = open(_ONBOARDING_SRC, encoding='utf-8').read()
    block = text.split('def get_onboarding_status(')[1].split('@mcp.tool')[0]
    assert 'complete_onboarding' in block
    assert 'check_only=True' in block
    assert 'read_progress' in block
