"""Item: auto-close outcome must not claim 'resolved' with no evidence.

Reviewer finding, live on eval-profile customer_id=405/406 (2026-08-27):
signal_analyst's auto-close reported "7/7 resolved" for playbook executions
where health_at_trigger == health_at_close EXACTLY (same underlying
HealthScore row — an account with only one snapshot ever, not unique to
eval-profile tenants), revenue_protected/expanded=0, csm_hours=0. Two
branches used to fall through to 'resolved' with zero supporting evidence:
missing health data, and "stabilized" when trigger/close were actually the
same single data point.

Pure function test — no DB, no Flask app context.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from datetime import date

from utils.signal_analyst import _classify_auto_close_outcome  # noqa: E402

JAN = date(2026, 1, 1)
FEB = date(2026, 2, 1)


def test_same_snapshot_is_insufficient_data_not_resolved():
    # trigger and close resolve to the SAME HealthScore row (same month) —
    # exactly the eval-profile bug: no real second data point.
    assert _classify_auto_close_outcome(35.6, 35.6, JAN, JAN) == 'insufficient_data'


def test_missing_health_data_is_insufficient_data_not_resolved():
    assert _classify_auto_close_outcome(None, 40.0, JAN, FEB) == 'insufficient_data'
    assert _classify_auto_close_outcome(40.0, None, JAN, FEB) == 'insufficient_data'
    assert _classify_auto_close_outcome(None, None, None, None) == 'insufficient_data'


def test_genuine_improvement_across_two_real_points_is_resolved():
    assert _classify_auto_close_outcome(40.0, 50.0, JAN, FEB) == 'resolved'


def test_genuine_decline_across_two_real_points_is_timeout():
    assert _classify_auto_close_outcome(50.0, 35.0, JAN, FEB) == 'timeout'


def test_genuine_stability_across_two_real_points_is_still_resolved():
    # Two DIFFERENT real measurements that happen to be close — this is a
    # real "we held the line" signal, unlike the same-snapshot case above.
    assert _classify_auto_close_outcome(40.0, 42.0, JAN, FEB) == 'resolved'


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
