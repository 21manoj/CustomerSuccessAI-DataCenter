"""Item 23 guard-fires — ConfigValidator EXCLUDES malformed customer config.

Invariant: a well-formed pillar-weight map / KPI code / custom-KPI definition
passes, and every dirty variant (missing pillar, weights that don't sum to 1.0,
an unrecognized KPI-code format, a custom KPI missing a required field, a bad
pillar/operator, an inverted or target-out-of-range span) is rejected with the
real error substring the validator emits.

Pure tests — ConfigValidator has no DB dependency.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from utils.config_validator import ConfigValidator  # noqa: E402


def _v():
    return ConfigValidator()


# ---- pillar weights -------------------------------------------------------

def test_pillar_weights_clean_passes():
    weights = {'P1': 0.2, 'P2': 0.2, 'P3': 0.2, 'P4': 0.2, 'P5': 0.2}
    ok, errors = _v().validate_pillar_weights(weights)
    assert ok is True
    assert errors == []


def test_pillar_weights_missing_pillar_rejected():
    weights = {'P1': 0.25, 'P2': 0.25, 'P3': 0.25, 'P4': 0.25}  # no P5
    ok, errors = _v().validate_pillar_weights(weights)
    assert ok is False
    assert any("Missing weight for pillar 'P5'" in e for e in errors)


def test_pillar_weights_not_summing_to_one_rejected():
    weights = {'P1': 0.5, 'P2': 0.5, 'P3': 0.5, 'P4': 0.5, 'P5': 0.5}
    ok, errors = _v().validate_pillar_weights(weights)
    assert ok is False
    assert any('must sum to 1.0' in e for e in errors)


# ---- KPI code format ------------------------------------------------------

def test_kpi_code_catalog_and_custom_pass():
    ok1, e1 = _v().validate_kpi_code('P1-KPI1')
    ok2, e2 = _v().validate_kpi_code('CUSTOM-CHURN-RISK')
    assert ok1 is True and e1 == []
    assert ok2 is True and e2 == []


def test_kpi_code_bad_format_rejected():
    ok, errors = _v().validate_kpi_code('BOGUS_CODE')
    assert ok is False
    assert any("Invalid KPI code 'BOGUS_CODE'" in e for e in errors)


# ---- custom KPI definition ------------------------------------------------

def _clean_custom_def():
    return {'pillar': 'P1', 'name': 'Rack Utilization', 'unit': '%',
            'target': 50, 'operator': '>', 'range': [0, 100]}


def test_custom_kpi_clean_passes():
    ok, errors = _v().validate_custom_kpi('CUSTOM-RACK-UTIL', _clean_custom_def())
    assert ok is True
    assert errors == []


def test_custom_kpi_missing_required_field_rejected():
    d = _clean_custom_def()
    del d['unit']
    ok, errors = _v().validate_custom_kpi('CUSTOM-RACK-UTIL', d)
    assert ok is False
    assert any("missing required field 'unit'" in e for e in errors)


def test_custom_kpi_bad_pillar_rejected():
    d = _clean_custom_def()
    d['pillar'] = 'P9'
    ok, errors = _v().validate_custom_kpi('CUSTOM-RACK-UTIL', d)
    assert ok is False
    assert any("Invalid pillar 'P9'" in e for e in errors)


def test_custom_kpi_bad_operator_rejected():
    d = _clean_custom_def()
    d['operator'] = '!!'
    ok, errors = _v().validate_custom_kpi('CUSTOM-RACK-UTIL', d)
    assert ok is False
    assert any("Invalid operator '!!'" in e for e in errors)


def test_custom_kpi_inverted_range_rejected():
    d = _clean_custom_def()
    d['range'] = [100, 0]
    ok, errors = _v().validate_custom_kpi('CUSTOM-RACK-UTIL', d)
    assert ok is False
    assert any('Range min must be less than max' in e for e in errors)


def test_custom_kpi_target_out_of_range_rejected():
    d = _clean_custom_def()
    d['target'] = 200  # outside [0, 100]
    ok, errors = _v().validate_custom_kpi('CUSTOM-RACK-UTIL', d)
    assert ok is False
    assert any('must be within range' in e for e in errors)


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
