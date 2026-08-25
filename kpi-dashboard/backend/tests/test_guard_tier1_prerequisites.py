"""Item 23 guard-fires — tier1_inference._check_prerequisites EXCLUDES the
11-CSV path (and the global kill switch) from auto-running LLM inference.

Invariant: _check_prerequisites(customer_id, mode) returns a
(should_run, reason, resolved_mode) triple. The default-ON path is 4-CSV
onboarding (0 customer-sourced DECISION nodes); the default-OFF path is 11-CSV
(customer uploaded decisions.csv -> >0 DECISION nodes). This pins:
  - clean 4-CSV -> (True, 'Ready', 'full')
  - 11-CSV default-off reject -> real reason string
  - explicit per-customer toggle disabled -> real reason string
  - global FEATURE_WITH_LLM=false kill switch -> real reason string

The function issues SQLAlchemy queries against several models; each is replaced
with a deterministic fake whose .count()/.first()/.all() return fixed values,
so no DB is required. ContextNode is queried in a fixed order
(DECISION count, then csv-signal count, then llm-signal count) so its fake
counts are supplied as an ordered sequence.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import models  # noqa: E402
import anthropic_key_utils  # noqa: E402
from llm.tier1_inference import _check_prerequisites  # noqa: E402


class _Col:
    """Stand-in for a SQLAlchemy column: == / != / .in_ are all no-ops."""
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return True

    def in_(self, *args, **kwargs):
        return True

    __hash__ = None


class _Query:
    def __init__(self, counts=(), first=None, all_=()):
        self._counts = list(counts)
        self._first = first
        self._all = list(all_)

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self

    def count(self):
        return self._counts.pop(0) if self._counts else 0

    def first(self):
        return self._first

    def all(self):
        return self._all


def _model(query):
    return SimpleNamespace(
        query=query,
        customer_id=_Col(), node_type=_Col(), source=_Col(),
        source_platform=_Col(), account_id=_Col(),
    )


def _patch_common(monkeypatch, *, ctx_node_counts, toggle_first,
                  accounts=1, kpi_count=10, edge_count=0, has_key=True):
    monkeypatch.setattr(models, 'ContextNode', _model(_Query(counts=ctx_node_counts)))
    monkeypatch.setattr(models, 'FeatureToggle', _model(_Query(first=toggle_first)))
    acct_rows = [SimpleNamespace(account_id=i + 1) for i in range(accounts)]
    monkeypatch.setattr(models, 'Account', _model(_Query(all_=acct_rows)))
    monkeypatch.setattr(models, 'DC2SKPI', _model(_Query(counts=[kpi_count])))
    monkeypatch.setattr(models, 'ContextEdge', _model(_Query(counts=[edge_count])))
    monkeypatch.setattr(anthropic_key_utils, 'has_anthropic_api_key', lambda cid: has_key)


def test_clean_four_csv_passes(monkeypatch):
    # 0 DECISION nodes (4-CSV), 0 csv signals, 0 llm signals -> full inference
    monkeypatch.delenv('FEATURE_WITH_LLM', raising=False)
    _patch_common(monkeypatch, ctx_node_counts=[0, 0, 0], toggle_first=None)
    should_run, reason, resolved_mode = _check_prerequisites(390, mode='auto')
    assert should_run is True
    assert reason == 'Ready'
    assert resolved_mode == 'full'


def test_eleven_csv_default_off_rejected(monkeypatch):
    # >0 customer DECISION nodes and no explicit toggle -> 11-CSV default-off
    monkeypatch.delenv('FEATURE_WITH_LLM', raising=False)
    _patch_common(monkeypatch, ctx_node_counts=[5], toggle_first=None)
    should_run, reason, resolved_mode = _check_prerequisites(390, mode='auto')
    assert should_run is False
    assert reason == '11-CSV mode (customer decisions uploaded); LLM default-off'
    assert resolved_mode == ''


def test_explicit_toggle_disabled_rejected(monkeypatch):
    monkeypatch.delenv('FEATURE_WITH_LLM', raising=False)
    disabled_toggle = SimpleNamespace(enabled=False)
    _patch_common(monkeypatch, ctx_node_counts=[0], toggle_first=disabled_toggle)
    should_run, reason, resolved_mode = _check_prerequisites(390, mode='auto')
    assert should_run is False
    assert reason == 'with_llm toggle explicitly disabled for this customer'
    assert resolved_mode == ''


def test_global_kill_switch_rejected(monkeypatch):
    # 4-CSV default-on path, but the emergency kill switch is set
    monkeypatch.setenv('FEATURE_WITH_LLM', 'false')
    _patch_common(monkeypatch, ctx_node_counts=[0], toggle_first=None)
    should_run, reason, resolved_mode = _check_prerequisites(390, mode='auto')
    assert should_run is False
    assert reason == 'Global FEATURE_WITH_LLM=false kill switch active'
    assert resolved_mode == ''


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
