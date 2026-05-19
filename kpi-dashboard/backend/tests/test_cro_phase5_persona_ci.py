"""CRO Phase 5 — fixtures + verify script smoke."""

from pathlib import Path


def test_cro_persona_fixtures_complete():
    from tests.persona_grading.fixtures.cro import CRO_QUESTIONS

    assert len(CRO_QUESTIONS) >= 6
    assert any(q.id == "cro-q03-expansion-upside" for q in CRO_QUESTIONS)


def test_verify_cro_phases_script_exists():
    script = Path(__file__).resolve().parents[3] / "scripts" / "verify_cro_phases_ec2.py"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "period_meta" in text
    assert "How to read CRO metrics" in text
