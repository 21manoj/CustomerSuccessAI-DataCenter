"""Item 23 guard-fires — validate_arc EXCLUDES malformed story-arc manifests.

Invariant: a manifest carrying every required top-level field validates with an
empty error list, while (a) a manifest missing required fields trips the
required-field gate, and (b) a target_audience outside the VALID_AUDIENCES
allow-set {CRO, CFO, CEO} is rejected.

validate_arc RETURNS a list of error strings (it does not raise); an empty list
means valid. Pure test — no DB, no disk.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from utils.story_arc_loader import validate_arc, VALID_AUDIENCES  # noqa: E402


def _minimal_valid_arc():
    """Smallest manifest that satisfies validate_arc with zero errors.

    Empty phases => total_weeks 0 which matches time_horizon_weeks 0, so the
    phase-duration reconciliation passes; empty cast/chains/decisions/outcomes
    skip their per-item validators.
    """
    return {
        'arc_id': 'arc_test',
        'arc_name': 'Test Arc',
        'version': '1.0',
        'revenue_narrative': {
            'arr_start': 100_000,
            'arr_end': 100_000,
            'arr_at_risk_peak': 10_000,
            'roi_of_intervention': 1.0,
            'cost_of_inaction': 1_000,
            'time_horizon_weeks': 0,
        },
        'cast': [],
        'phases': [],
        'causal_chains': [],
        'kpi_trajectories': {},
        'decisions': [],
        'outcomes': [],
        'edges_template': [],
    }


def test_allow_set_is_the_expected_three():
    assert VALID_AUDIENCES == {'CRO', 'CFO', 'CEO'}


def test_minimal_valid_arc_passes():
    errors = validate_arc(_minimal_valid_arc())
    assert errors == [], errors


def test_missing_required_fields_rejected():
    errors = validate_arc({})
    # required-field gate fires and short-circuits before deeper checks
    assert any('Missing required field: arc_id' in e for e in errors)
    assert any('Missing required field: revenue_narrative' in e for e in errors)


def test_bad_target_audience_rejected():
    arc = _minimal_valid_arc()
    arc['target_audience'] = 'INVESTOR'  # not in VALID_AUDIENCES
    errors = validate_arc(arc)
    assert any('Invalid target_audience: INVESTOR' in e for e in errors)


def test_valid_target_audience_accepted():
    arc = _minimal_valid_arc()
    arc['target_audience'] = 'CFO'
    errors = validate_arc(arc)
    assert errors == [], errors


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
