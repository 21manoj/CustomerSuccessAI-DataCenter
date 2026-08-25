"""Item 23 guard-fires — _check_mcp_enabled EXCLUDES calls when MCP is off.

Invariant: when the MCP_SERVER feature toggle is ON the guard is a no-op; when
it is OFF the guard raises fastmcp's ToolError with the real "MCP Server is
disabled" message. The toggle state is controlled by monkeypatching the
feature_toggles singleton's is_enabled (the only external dependency).
"""
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import feature_toggles as ft_module  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402
from mcp_server.cs_pulse_mcp_server import _check_mcp_enabled  # noqa: E402


def test_enabled_is_a_noop(monkeypatch):
    monkeypatch.setattr(ft_module.feature_toggles, 'is_enabled', lambda feature: True)
    # returns None, raises nothing
    assert _check_mcp_enabled() is None


def test_disabled_raises_tool_error(monkeypatch):
    monkeypatch.setattr(ft_module.feature_toggles, 'is_enabled', lambda feature: False)
    with pytest.raises(ToolError) as exc:
        _check_mcp_enabled()
    assert 'MCP Server is disabled' in str(exc.value)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
