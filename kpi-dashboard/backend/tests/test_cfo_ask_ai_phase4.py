"""CFO Ask AI Phase 4 — prompt rules and suggested questions."""

from pathlib import Path


def test_cfo_ask_ai_phase4_rules_in_endpoint():
    src = (
        Path(__file__).resolve().parents[1] / 'ask_ai_endpoint.py'
    ).read_text(encoding='utf-8')
    assert "if persona == 'cfo':" in src
    assert 'CFO NRR LENS' in src
    assert 'CFO VARIANCE' in src
    assert 'do NOT invent' in src
    assert 'get_portfolio_roi_summary' in src


def test_cfo_executive_ask_suggested_questions():
    src = (
        Path(__file__).resolve().parents[1] / 'executive_dashboard_api.py'
    ).read_text(encoding='utf-8')
    assert 'confirmed revenue is at risk (context graph)' in src


def test_cfo_persona_fixtures_have_variance_guard():
    from tests.persona_grading.fixtures.cfo import CFO_QUESTIONS

    q03 = next(q for q in CFO_QUESTIONS if q.id == 'cfo-q03-actual-vs-projected')
    assert any('fabricated' in a.lower() for a in q03.anti_hallucination)
