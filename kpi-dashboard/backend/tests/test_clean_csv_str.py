"""Guard for _clean_csv_str (mcp_server/cs_pulse_onboarding.py).

Reviewer finding, live on eval-profile customer_id=405/406/407 (2026-08-27):
stakeholder_name/stakeholder_title showed the literal string "nan" for
blank CSV cells. Root cause: `str(row.get(col, '') or '').strip()` doesn't
guard against pandas NaN — NaN is a float, and float('nan') is TRUTHY in
Python, so `nan or ''` evaluates to `nan`, not `''`. Pure function test —
no DB, no Flask app context.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
MCP_SERVER_DIR = BACKEND / 'mcp_server'
if str(MCP_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_SERVER_DIR))  # cs_pulse_onboarding.py bare-imports cs_pulse_mcp_server as a sibling

from mcp_server.cs_pulse_onboarding import _clean_csv_str  # noqa: E402


def test_nan_float_becomes_empty_not_the_string_nan():
    assert _clean_csv_str(float('nan')) == ''


def test_none_becomes_empty():
    assert _clean_csv_str(None) == ''


def test_literal_nan_string_also_cleaned():
    # In case some upstream layer already stringified it before this call.
    assert _clean_csv_str('nan') == ''
    assert _clean_csv_str('NaN') == ''


def test_real_value_passes_through_stripped():
    assert _clean_csv_str('  Jane Doe  ') == 'Jane Doe'


def test_custom_default_respected():
    assert _clean_csv_str(float('nan'), default='engagement') == 'engagement'


def test_the_bug_this_replaces_would_have_failed():
    # The old pattern this function replaces: str(x or '').strip()
    old_buggy = str(float('nan') or '').strip()
    assert old_buggy == 'nan'  # proves the bug was real
    assert _clean_csv_str(float('nan')) != 'nan'  # proves the fix


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
