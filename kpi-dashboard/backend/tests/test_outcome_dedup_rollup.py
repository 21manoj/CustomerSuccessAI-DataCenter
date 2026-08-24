"""Cross-account revenue rollup must not double-count duplicate OUTCOME nodes.

Customer 391 had 63 excess byte-identical OUTCOME rows (outcomes.csv
re-ingested 4×; the write path was a raw INSERT with a degenerate
source_event_id). The account-level get_revenue_at_risk masked it via its
amount-dedup, but aggregate_revenue_across_accounts (the CFO rollup) summed
raw — producing revenue_at_risk = $39.84M = 111% of the tenant's $35.9M
ARR, an impossible number. Fix: _dedupe_exact_outcome_nodes, applied in
both rollups.

Pure-function test on the dedup helper — no DB.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from utils.context_graph import _dedupe_exact_outcome_nodes  # noqa: E402


def _node(node_id, account_id=1, title="Revenue at Risk", impact=-2_550_000,
          rtype="revenue_at_risk", occurred_at="2026-01-01"):
    return SimpleNamespace(node_id=node_id, account_id=account_id, title=title,
                           revenue_impact=impact, revenue_impact_type=rtype,
                           occurred_at=occurred_at)


def test_four_identical_nodes_collapse_to_one():
    nodes = [_node(124768), _node(124789), _node(124810), _node(124831)]  # 391's actual quad
    out = _dedupe_exact_outcome_nodes(nodes)
    assert len(out) == 1
    assert out[0].node_id == 124768  # keeps the lowest node_id


def test_distinct_nodes_survive():
    nodes = [
        _node(1, title="Titan risk", impact=-4_100_000),
        _node(2, title="Pacific expansion", impact=2_500_000, rtype="expansion_closed"),
        _node(3, account_id=99, title="Titan risk", impact=-4_100_000),  # diff account
    ]
    out = _dedupe_exact_outcome_nodes(nodes)
    assert len(out) == 3  # none are byte-identical


def test_same_amount_different_occurred_at_survive():
    # Two genuinely-distinct risk events of equal size on the same account
    # must NOT be collapsed — only byte-identical rows are duplicates.
    nodes = [_node(1, occurred_at="2026-01-01"), _node(2, occurred_at="2026-03-15")]
    out = _dedupe_exact_outcome_nodes(nodes)
    assert len(out) == 2


def test_partial_duplication_collapses_only_the_dupes():
    nodes = [_node(1), _node(2), _node(3),  # 3 identical
             _node(9, title="Other", impact=-500_000)]  # 1 distinct
    out = _dedupe_exact_outcome_nodes(nodes)
    assert len(out) == 2
    assert {n.node_id for n in out} == {1, 9}


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
