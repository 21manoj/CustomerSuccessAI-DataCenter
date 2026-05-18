"""CFO dashboard context-graph revenue fields (Phase 1) — no live DB required."""

from pathlib import Path


def test_cfo_dashboard_api_exports_graph_fields():
    """cfo-dashboard must expose the same graph $ fields as CRO (+ expansion_pipeline)."""
    api_path = Path(__file__).resolve().parents[1] / 'executive_dashboard_api.py'
    source = api_path.read_text(encoding='utf-8')
    assert "'expansion_pipeline': revenue_data['expansion_pipeline']" in source
    assert "'context_graph_provenance': context_graph_provenance" in source
    assert "'revenue_risk_label': 'Confirmed Risk (Context Graph)'" in source
    # Comment/doc: graph totals distinct from proof_data
    assert 'Distinct from proof_data.revenue_protected' in source


def test_outcome_bucket_classifier():
    """Shared classifier used by aggregate + provenance."""
    from utils.context_graph import _outcome_revenue_bucket_and_amount

    class Node:
        revenue_impact = -50_000
        revenue_impact_type = None
        node_subtype = None

    bucket, amount = _outcome_revenue_bucket_and_amount(Node())
    assert bucket == 'at_risk'
    assert amount == 50_000


def test_provenance_empty_accounts_no_db_query():
    """Empty account list short-circuits without touching ContextNode.query."""
    from utils.context_graph import aggregate_revenue_with_provenance

    result = aggregate_revenue_with_provenance(334, [])
    assert result['revenue_at_risk'] == 0
    assert result['expansion_pipeline'] == 0
    assert result['provenance']['outcome_node_count'] == 0
