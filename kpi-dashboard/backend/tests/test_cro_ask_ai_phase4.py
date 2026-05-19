"""CRO Ask AI Phase 4 — prompt rules."""

from pathlib import Path


def test_cro_ask_ai_rules_in_endpoint():
    src = Path(__file__).resolve().parents[1] / "ask_ai_endpoint.py"
    text = src.read_text(encoding="utf-8")
    assert "if persona == 'cro':" in text
    assert "CRO REVENUE LENSES" in text
    assert "get_portfolio_revenue_breakdown" in text
    assert "no quarterly NRR target configured" in text


def test_cro_executive_suggested_questions():
    src = Path(__file__).resolve().parents[1] / "executive_dashboard_api.py"
    text = src.read_text(encoding="utf-8")
    assert "confirmed revenue is at risk (context graph)" in text
