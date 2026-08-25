"""Item 26 Model C — one canonical bucket policy, both revenue paths agree.

Signed off 2026-08-24: account-level at_risk becomes node-evidenced (matching
the CFO summary), the health heuristic moves to modeled_churn_exposure, and
lost holds realized losses only. The account-level get_revenue_at_risk and the
cross-account aggregate_revenue_across_accounts now bucket through the same
_outcome_revenue_bucket_and_amount, so a subtype can never land in different
buckets on the two surfaces.

Pure classifier tests — no DB.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from utils.context_graph import _outcome_revenue_bucket_and_amount  # noqa: E402


def _bucket(rtype, raw=-1_000_000, subtype=None):
    n = SimpleNamespace(revenue_impact=raw, revenue_impact_type=rtype, node_subtype=subtype)
    return _outcome_revenue_bucket_and_amount(n)[0]


def test_risk_trajectory_subtypes_are_at_risk():
    for t in ('revenue_at_risk', 'renewal_uncertainty', 'capacity_constraint',
              'engagement_decline', 'partner_friction', 'churn_risk'):
        assert _bucket(t) == 'at_risk', t


def test_partial_recovery_is_at_risk():
    # decision 2 (2026-08-24)
    assert _bucket('partial_recovery') == 'at_risk'


def test_realized_loss_subtypes_are_lost():
    for t in ('churn_lost', 'contraction', 'revenue_lost'):
        assert _bucket(t) == 'lost', t


def test_protected_and_expansion_unchanged():
    assert _bucket('revenue_protected', raw=1_000) == 'protected'
    assert _bucket('churn_averted', raw=1_000) == 'protected'
    assert _bucket('expansion_closed', raw=1_000) == 'expansion'
    assert _bucket('revenue_growth', raw=1_000) == 'expansion'


def test_unknown_negative_is_at_risk_not_lost():
    # conservative: an unknown negative is risk (not yet realized), not a
    # confirmed loss
    assert _bucket('some_new_subtype', raw=-500) == 'at_risk'


def test_at_risk_and_lost_sets_are_disjoint():
    from utils.context_graph import _OUTCOME_AT_RISK_TYPES, _OUTCOME_LOST_TYPES
    assert not (_OUTCOME_AT_RISK_TYPES & _OUTCOME_LOST_TYPES)


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
