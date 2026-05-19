"""VPCS capacity planning helper tests."""

from unittest.mock import MagicMock, patch

from utils.vpcs_dashboard_helpers import build_capacity_planning


def test_build_capacity_planning_recommends_headcount():
    accounts = []
    for i in range(12):
        acct = MagicMock()
        acct.account_id = 440000 + i
        acct.revenue = 100_000
        acct.profile_metadata = {'assigned_csm': f'CSM {i % 2 + 1}'}
        accounts.append(acct)

    with patch('utils.vpcs_dashboard_helpers._latest_health', return_value=60.0):
        with patch('models.PlaybookExecutionV2') as pb:
            pb.customer_id = MagicMock()
            pb.customer_id.__eq__ = MagicMock(return_value=MagicMock())
            pb.triggered_at = MagicMock()
            pb.triggered_at.__ge__ = MagicMock(return_value=MagicMock())
            pb.query.filter.return_value.all.return_value = []
            out = build_capacity_planning(334, accounts)

    assert out['csm_count_current'] == 2
    assert out['recommended_csm_count'] >= 2
    assert 'allocation_rationale' in out
    assert isinstance(out['top_performers'], list)
