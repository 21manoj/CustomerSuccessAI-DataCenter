"""CFO dashboard context-graph revenue fields (Phase 1) — no live DB required."""

from pathlib import Path


def test_cfo_dashboard_api_exports_graph_fields():
    """cfo-dashboard must expose the same graph $ fields as CRO (+ expansion_pipeline)."""
    api = (
        Path(__file__).resolve().parents[1]
        / 'executive_dashboard_api.py'
    )
    source = api.read_text(encoding='utf-8')
    for field in (
        'revenue_at_risk',
        'revenue_protected',
        'expansion_pipeline',
        'context_graph_provenance',
        'roi_scaling',
        'efficiency',
    ):
        assert field in source, f'missing {field} in cfo_dashboard response'
