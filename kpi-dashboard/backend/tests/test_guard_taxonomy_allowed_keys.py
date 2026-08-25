"""Item 23 guard-fires — taxonomy _validate_structural EXCLUDES bad schema.

Invariant: a structurally clean taxonomy dict passes _validate_structural, while
(a) an unknown top-level key and (b) an unknown revenue-bucket name each raise
TaxonomyValidationError. Also proves the real base taxonomy on disk loads clean
through get_taxonomy().

The allow-set (_ALLOWED_TOP_KEYS) and bucket-set (_BUCKET_KEYS) are asserted
against their real constant values. Pure test — no DB.
"""
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from utils.taxonomy_loader import (  # noqa: E402
    _validate_structural,
    _ALLOWED_TOP_KEYS,
    _BUCKET_KEYS,
    TaxonomyValidationError,
    get_taxonomy,
)


def test_allowed_key_sets_are_as_expected():
    assert 'version' in _ALLOWED_TOP_KEYS
    assert 'revenue_buckets' in _ALLOWED_TOP_KEYS
    assert _BUCKET_KEYS == {'at_risk', 'lost', 'expansion', 'pipeline', 'protected'}


def test_clean_structural_passes():
    data = {'version': '0.1', 'description': 'ok',
            'revenue_buckets': {'at_risk': ['churn_risk']}}
    # returns None, raises nothing
    assert _validate_structural(data, 'taxonomy_base.json', is_overlay=False) is None


def test_unknown_top_key_raises():
    data = {'version': '0.1', 'bogus_key': 1}
    with pytest.raises(TaxonomyValidationError) as exc:
        _validate_structural(data, 'taxonomy_base.json', is_overlay=False)
    assert 'unknown keys' in str(exc.value)


def test_unknown_revenue_bucket_raises():
    data = {'version': '0.1', 'revenue_buckets': {'made_up_bucket': []}}
    with pytest.raises(TaxonomyValidationError) as exc:
        _validate_structural(data, 'taxonomy_base.json', is_overlay=False)
    assert 'unknown revenue buckets' in str(exc.value)


def test_real_base_taxonomy_loads_clean():
    # base only, no vertical overlay — exercises the real on-disk file end to end
    tax = get_taxonomy()
    assert tax.version
    assert 'at_risk' in tax.revenue_bucket_map


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
