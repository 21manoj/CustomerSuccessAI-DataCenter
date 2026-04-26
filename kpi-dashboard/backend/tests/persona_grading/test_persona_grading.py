"""Pytest entry for persona-grading. Default-OFF in CI.

Set PERSONA_GRADING_ENABLED=1 to run. Requires:
  - DATABASE_URL pointing at a DB with the customer + accounts to grade
  - ANTHROPIC_API_KEY set (each fixture costs ~$0.05 for tool-use + grading)
  - Customer has been ingested with health/signals/outcomes (otherwise tools return empty)
"""
import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)

ENABLED = os.environ.get('PERSONA_GRADING_ENABLED') == '1'
CUSTOMER_ID = int(os.environ.get('PERSONA_GRADING_CUSTOMER_ID', '0') or 0)


@pytest.mark.skipif(not ENABLED, reason="set PERSONA_GRADING_ENABLED=1 to run (incurs LLM cost)")
def test_persona_grading_run():
    """Single test that runs all 5 personas and writes results JSON."""
    if not CUSTOMER_ID:
        pytest.skip("PERSONA_GRADING_CUSTOMER_ID env var not set")
    if not os.environ.get('ANTHROPIC_API_KEY'):
        pytest.skip("ANTHROPIC_API_KEY env var not set")

    from .runner import run_all_personas

    out = Path(os.environ.get(
        'PERSONA_GRADING_OUTPUT',
        f'/tmp/persona_grades_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.json'
    ))
    payload = run_all_personas(CUSTOMER_ID, output_path=out)

    # Sanity assertions on the produced report
    assert 'personas' in payload
    assert len(payload['personas']) >= 1
    summary = payload.get('summary', {})
    for persona, info in summary.items():
        if isinstance(info, dict) and info.get('avg_grade'):
            assert info['avg_grade'] in {
                'A', 'A-', 'B+', 'B', 'B-',
                'C+', 'C', 'C-', 'D+', 'D', 'F'
            }, f"Unexpected grade for {persona}: {info['avg_grade']}"


@pytest.mark.skipif(not ENABLED, reason="set PERSONA_GRADING_ENABLED=1 to run")
def test_fixtures_loadable():
    """Cheap smoke: ensure all 5 fixture files import + have non-empty questions."""
    from .fixtures import BY_PERSONA, ALL_FIXTURES
    assert set(BY_PERSONA.keys()) == {'cro', 'cfo', 'ceo', 'vpcs', 'csm'}
    assert len(ALL_FIXTURES) >= 25, f"Expected ≥25 questions across all personas, got {len(ALL_FIXTURES)}"
    for persona, qs in BY_PERSONA.items():
        assert len(qs) >= 5, f"Persona {persona} has only {len(qs)} questions"
        for q in qs:
            assert q.question, f"Empty question in {persona}: {q.id}"
            assert q.must_cite or q.must_call_tools, f"No rubric for {q.id}"
