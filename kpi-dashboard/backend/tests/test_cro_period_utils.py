"""Sanity checks for CRO period tab wiring (frontend croPeriod.ts)."""

from pathlib import Path


def test_cro_period_utils_exist_in_frontend():
    ts = Path(__file__).resolve().parents[2] / 'src' / 'utils' / 'croPeriod.ts'
    source = ts.read_text(encoding='utf-8')
    assert 'periodToAnchorBucket' in source
    assert "export type CroPeriod = 'Q3' | 'Q4' | 'TTM'" in source


def test_cro_dashboard_wires_period_tabs():
    tsx = Path(__file__).resolve().parents[2] / 'src' / 'components' / 'dashboard' / 'CRODashboard.tsx'
    source = tsx.read_text(encoding='utf-8')
    assert 'applyPeriodToCroData' in source
    assert 'period={activePeriod}' in source
    login = (Path(__file__).resolve().parents[2] / 'src' / 'components' / 'LoginComponent.tsx').read_text(encoding='utf-8')
    assert 'customer_name: data.user?.customer_name' in login


def test_login_stores_customer_name_not_as_user_name():
    login = Path(__file__).resolve().parents[2] / 'src' / 'components' / 'LoginComponent.tsx'
    source = login.read_text(encoding='utf-8')
    assert 'customer_name: data.user?.customer_name' in source
    assert 'user_name: data.user?.user_name' in source
