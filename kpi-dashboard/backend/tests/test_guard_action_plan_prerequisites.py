"""Item 23 guard-fires — action_plan_generator._check_prerequisites EXCLUDES
LLM work when WITH_LLM is off or no API key is configured.

Invariant: _check_prerequisites(customer_id) returns a (ok, reason) tuple.
Clean (WITH_LLM enabled + API key present) -> (True, 'OK'). Dirty variants
reject with the real reason strings: 'WITH_LLM disabled' and 'No API key'.

The function reads three collaborators, each patched here:
  - models.FeatureToggle.query.filter_by(...).first()  (per-customer override)
  - feature_toggles.feature_toggles.is_enabled(...)      (global flag)
  - anthropic_key_utils.has_anthropic_api_key(customer_id)
"""
import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import models  # noqa: E402
import feature_toggles as ft_module  # noqa: E402
import anthropic_key_utils  # noqa: E402
from llm.action_plan_generator import _check_prerequisites  # noqa: E402


class _Query:
    """Minimal stand-in for FeatureToggle.query — filter_by(...).first()."""
    def __init__(self, first=None):
        self._first = first

    def filter_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._first


def _fake_toggle_model(first=None):
    return SimpleNamespace(query=_Query(first=first))


def test_clean_passes(monkeypatch):
    # no per-customer override row; global WITH_LLM on; key present
    monkeypatch.setattr(models, 'FeatureToggle', _fake_toggle_model(first=None))
    monkeypatch.setattr(ft_module.feature_toggles, 'is_enabled', lambda feature: True)
    monkeypatch.setattr(anthropic_key_utils, 'has_anthropic_api_key', lambda cid: True)
    ok, reason = _check_prerequisites(customer_id=390)
    assert ok is True
    assert reason == 'OK'


def test_llm_disabled_rejected(monkeypatch):
    # no override row AND global WITH_LLM off -> WITH_LLM disabled
    monkeypatch.setattr(models, 'FeatureToggle', _fake_toggle_model(first=None))
    monkeypatch.setattr(ft_module.feature_toggles, 'is_enabled', lambda feature: False)
    monkeypatch.setattr(anthropic_key_utils, 'has_anthropic_api_key', lambda cid: True)
    ok, reason = _check_prerequisites(customer_id=390)
    assert ok is False
    assert reason == 'WITH_LLM disabled'


def test_no_api_key_rejected(monkeypatch):
    # LLM enabled but no key -> 'No API key'
    monkeypatch.setattr(models, 'FeatureToggle', _fake_toggle_model(first=None))
    monkeypatch.setattr(ft_module.feature_toggles, 'is_enabled', lambda feature: True)
    monkeypatch.setattr(anthropic_key_utils, 'has_anthropic_api_key', lambda cid: False)
    ok, reason = _check_prerequisites(customer_id=390)
    assert ok is False
    assert reason == 'No API key'


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
