"""Item 23 guard-fires — provenance allowlist EXCLUDES synthetic + NULL.

Invariant: the correlation/forecast reader trusts only 'observed' and 'inferred'.
This pins four things:
  1. synthetic is NOT trustworthy and is NOT a member of TRUSTWORTHY_SOURCES.
  2. observed / inferred are trustworthy.
  3. a NULL source fails closed (normalize(None) stays None; not trustworthy).
  4. the legacy 'customer' value is trustworthy via normalize() (-> 'observed')
     EVEN THOUGH it is NOT a literal member of TRUSTWORTHY_SOURCES — the trap
     for any reader that filters on a raw `.in_(TRUSTWORTHY_SOURCES)` without
     normalizing first.

Pure test — no DB.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from utils.provenance import (  # noqa: E402
    is_trustworthy,
    normalize,
    TRUSTWORTHY_SOURCES,
    OBSERVED,
    INFERRED,
    SYNTHETIC,
)


def test_synthetic_is_excluded():
    assert SYNTHETIC == 'synthetic'
    assert SYNTHETIC not in TRUSTWORTHY_SOURCES
    assert is_trustworthy(SYNTHETIC) is False


def test_observed_and_inferred_are_trusted():
    assert OBSERVED in TRUSTWORTHY_SOURCES
    assert INFERRED in TRUSTWORTHY_SOURCES
    assert is_trustworthy(OBSERVED) is True
    assert is_trustworthy(INFERRED) is True


def test_null_source_fails_closed():
    # a missing value must never become the most-trusted value
    assert normalize(None) is None
    assert is_trustworthy(None) is False


def test_legacy_customer_trusted_via_normalize_but_not_a_literal_member():
    # normalize maps the legacy value onto the canonical trusted one ...
    assert normalize('customer') == OBSERVED
    assert is_trustworthy('customer') is True
    # ... but the raw string is NOT itself in the allowlist — a `.in_()` filter
    # that skips normalize() would wrongly drop these rows.
    assert 'customer' not in TRUSTWORTHY_SOURCES


def test_legacy_system_normalizes_to_inferred():
    assert normalize('system') == INFERRED
    assert is_trustworthy('system') is True
    assert 'system' not in TRUSTWORTHY_SOURCES


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
