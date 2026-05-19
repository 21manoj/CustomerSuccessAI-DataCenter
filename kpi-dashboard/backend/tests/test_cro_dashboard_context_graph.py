"""CRO dashboard context-graph fields (Phase 1)."""


def test_cro_dashboard_api_exports_graph_fields():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "executive_dashboard_api.py"
    ).read_text(encoding="utf-8")
    assert "def cro_dashboard" in source
    assert "'period_meta': period_meta" in source
    assert "'context_graph_provenance': context_graph_provenance" in source
    assert "'arr_exposure':" in source
