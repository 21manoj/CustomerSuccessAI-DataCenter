"""Item 23 / N1 — urgent-alert dedup reader and writer must share one source value.

The dedup query and the alert-node writer in urgent_signal_scanner filter/write
ContextNode.source. If they ever use different literals, dedup silently never
fires and duplicate critical `urgent_alert` notifications are emitted on every
scan (the 2026-08-24 bug: reader == 'system', writer == 'inferred', and nothing
writes 'system'). The fix routes both through the single constant
`_ALERT_NODE_SOURCE`; this test guards that they cannot drift apart again.

Static (source-level) guard — no DB/app-context needed.
"""
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

_SCANNER = BACKEND / 'utils' / 'urgent_signal_scanner.py'


def _source():
    return _SCANNER.read_text()


def test_constant_is_inferred_matching_the_writer():
    from utils.urgent_signal_scanner import _ALERT_NODE_SOURCE
    assert _ALERT_NODE_SOURCE == 'inferred'


def test_dedup_reader_uses_the_shared_constant():
    src = _source()
    assert 'ContextNode.source == _ALERT_NODE_SOURCE' in src
    # the old bug's literal must be gone
    assert "ContextNode.source == 'system'" not in src
    assert 'ContextNode.source == "system"' not in src


def test_writer_uses_the_shared_constant():
    src = _source()
    # the ContextNode(...) alert-node writer sets source=_ALERT_NODE_SOURCE
    assert re.search(r'source\s*=\s*_ALERT_NODE_SOURCE', src)
    # no raw-string 'system' source assignment survives (executable code, not
    # the explanatory comment): neither a filter compare nor a kwarg assign.
    assert not re.search(r"source\s*(==|=)\s*['\"]system['\"]", src)


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
