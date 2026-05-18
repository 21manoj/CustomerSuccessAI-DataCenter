"""CFO dashboard Phase 2 — pre-proof / onboarding honesty (UI source checks)."""

from pathlib import Path


def test_cfo_phase2_pre_proof_banner_in_ui():
    tsx = (Path(__file__).resolve().parents[2] / 'src' / 'components' / 'dashboard' / 'CFODashboard.tsx')
    source = tsx.read_text(encoding='utf-8')
    assert 'CFOPreProofBanner' in source
    assert 'ROI tiles are Power-of-1 estimates until playbooks close' in source
    assert '!d.has_proof && <CFOPreProofBanner' in source


def test_cfo_phase2_playbook_proof_empty_state():
    tsx = (Path(__file__).resolve().parents[2] / 'src' / 'components' / 'dashboard' / 'CFODashboard.tsx')
    source = tsx.read_text(encoding='utf-8')
    assert 'PlaybookProofEmptyState' in source
    assert 'No closed playbook executions with attributed revenue yet' in source
    assert 'expectedProofHint' in source


def test_cfo_phase2_no_automation_tag_on_estimated_cards():
    """Phase 2: do not show fake automation % on pre-proof anchor row."""
    tsx = (Path(__file__).resolve().parents[2] / 'src' / 'components' / 'dashboard' / 'CFODashboard.tsx')
    source = tsx.read_text(encoding='utf-8')
    assert 'Illustrative · ~' not in source
    assert 'industry placeholder' not in source.lower() or 'industry-average' in source


def test_cfo_phase2_account_source_column():
    tsx = (Path(__file__).resolve().parents[2] / 'src' / 'components' / 'dashboard' / 'CFODashboard.tsx')
    source = tsx.read_text(encoding='utf-8')
    assert '<th className="text-center py-2 px-2">Source</th>' in source
    assert 'benchmark' in source and 'actual' in source


def test_cfo_phase2_coi_visible_with_predictor_v3():
    tsx = (Path(__file__).resolve().parents[2] / 'src' / 'components' / 'dashboard' / 'CFODashboard.tsx')
    source = tsx.read_text(encoding='utf-8')
    assert 'd.predictor_v3_portfolio_nrr && (' in source
    assert 'CostOfInactionPanel data={d.cost_of_inaction} compact' in source
