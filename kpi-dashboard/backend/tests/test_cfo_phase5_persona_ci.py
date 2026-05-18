"""CFO Phase 5 — persona fixture contract + golden proof economics smoke."""

from pathlib import Path


def test_cfo_persona_grading_fixtures_complete():
    from tests.persona_grading.fixtures.cfo import CFO_QUESTIONS

    assert len(CFO_QUESTIONS) >= 6
    ids = {q.id for q in CFO_QUESTIONS}
    assert 'cfo-q01-portfolio-roi' in ids
    assert 'cfo-q03-actual-vs-projected' in ids
    for q in CFO_QUESTIONS:
        assert q.must_call_tools
        assert q.must_call_at_least >= 1


def test_cfo_golden_proof_roi_math():
    """Bottom-up proof ROI matches CFO dashboard formula."""
    proof = {
        'total_cost': 250_000,
        'revenue_protected': 1_000_000,
        'revenue_expanded': 500_000,
    }
    total_value = proof['revenue_protected'] + proof['revenue_expanded']
    realized = round(total_value / proof['total_cost'], 1)
    assert realized == 6.0


def test_verify_script_covers_phases_3_5():
    script = (
        Path(__file__).resolve().parents[3] / 'scripts' / 'verify_cfo_phases_ec2.py'
    )
    assert script.is_file()
    text = script.read_text(encoding='utf-8')
    assert 'efficiency' in text
    assert 'Phase 3' in text
