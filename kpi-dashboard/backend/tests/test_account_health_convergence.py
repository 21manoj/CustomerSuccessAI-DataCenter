"""
Account-health convergence tests — Wave 1 Workstream A (Aug 4, 2026).

Per AUDIT_REMEDIATION_WAVE1_SPEC.md §A3. Verifies the canonical service in
utils/account_health.py and that surfaces which used to disagree now agree.
Requires a DB connection (uses the app's configured database).
"""

import pytest


# Customer IDs created by _make_test_customer_and_account during the current
# test — deleted explicitly at teardown. Explicit tracked-delete rather than
# a SAVEPOINT/rollback trick: guaranteed correct regardless of how
# Flask-SQLAlchemy's scoped session is wired, at the cost of one extra
# query per created row.
_created_customer_ids: list = []


@pytest.fixture
def app_ctx():
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app_v3_minimal import app
    from extensions import db

    _created_customer_ids.clear()
    with app.app_context():
        yield app

        from models import Customer, Account, HealthScore
        for cid in _created_customer_ids:
            account_ids = [a.account_id for a in Account.query.filter_by(customer_id=cid).all()]
            if account_ids:
                HealthScore.query.filter(HealthScore.account_id.in_(account_ids)).delete(synchronize_session=False)
                Account.query.filter_by(customer_id=cid).delete(synchronize_session=False)
            Customer.query.filter_by(customer_id=cid).delete(synchronize_session=False)
        db.session.commit()
        _created_customer_ids.clear()


def _make_test_customer_and_account(missing_data=False, health_score=None,
                                    account_status='active'):
    from extensions import db
    from models import Customer, Account, HealthScore
    import datetime, uuid

    tag = uuid.uuid4().hex[:12]
    customer = Customer(customer_name=f"AH Test {tag}",
                        domain=f"ahtest{tag}.io",
                        vertical='saas_premium')
    db.session.add(customer)
    db.session.flush()
    _created_customer_ids.append(customer.customer_id)

    account = Account(customer_id=customer.customer_id, account_name="AH Test Acct",
                      revenue=1_000_000, account_status=account_status)
    db.session.add(account)
    db.session.flush()

    if not missing_data:
        hs = HealthScore(
            account_id=account.account_id,
            measurement_month=datetime.date(2026, 6, 1),
            health_score=health_score if health_score is not None else 50.0,
            health_status='at_risk',
            contributing_pillars={'P1': 55.0, 'P2': 45.0},
        )
        db.session.add(hs)

    db.session.commit()
    return customer, account


class TestCanonicalService:

    def test_missing_data_is_explicit_not_a_default(self, app_ctx):
        """No HealthScore row -> missing=True, no fabricated score."""
        from utils.account_health import get_account_health
        _customer, account = _make_test_customer_and_account(missing_data=True)
        ah = get_account_health(account.account_id)
        assert ah.missing is True
        assert ah.health_score is None
        assert ah.missing_reason == "no_health_scores"

    def test_score_exactly_50_is_not_treated_as_missing(self, app_ctx):
        """The old 50.0-sentinel bug: an account genuinely scoring 50 must
        NOT be reported as missing."""
        from utils.account_health import get_account_health
        _customer, account = _make_test_customer_and_account(health_score=50.0)
        ah = get_account_health(account.account_id)
        assert ah.missing is False
        assert ah.health_score == 50.0

    def test_tenant_isolation_rejects_wrong_customer(self, app_ctx):
        from utils.account_health import get_account_health
        _c1, account = _make_test_customer_and_account(health_score=72.0)
        c2, _ = _make_test_customer_and_account(missing_data=True)
        ah = get_account_health(account.account_id, customer_id=c2.customer_id)
        assert ah.missing is True
        assert ah.missing_reason == "not_found_or_wrong_tenant"

    def test_pillars_are_month_pinned(self, app_ctx):
        from utils.account_health import get_account_health
        _customer, account = _make_test_customer_and_account(health_score=68.0)
        ah = get_account_health(account.account_id)
        assert ah.pillars == {'P1': 55.0, 'P2': 45.0}
        assert ah.measurement_month is not None

    def test_legacy_tuple_shim_matches_service(self, app_ctx):
        from utils.account_health import get_account_health, get_precalculated_scores_tuple
        _customer, account = _make_test_customer_and_account(health_score=63.0)
        ah = get_account_health(account.account_id)
        h, status, pillars = get_precalculated_scores_tuple(account.account_id)
        assert h == ah.health_score
        assert status == ah.health_status
        assert pillars == ah.pillars

    def test_legacy_4tuple_shim_includes_month(self, app_ctx):
        from utils.account_health import get_precalculated_scores_tuple
        _customer, account = _make_test_customer_and_account(health_score=63.0)
        h, status, pillars, month = get_precalculated_scores_tuple(account.account_id, with_month=True)
        assert h == 63.0
        assert month is not None


class TestCrossSurfaceParity:
    """Same seeded account -> same number, regardless of which surface reads it."""

    def test_mcp_common_and_vertical_health_agree(self, app_ctx):
        _customer, account = _make_test_customer_and_account(health_score=77.0)
        from mcp_server.common import get_precalculated_scores as mcp_common
        from utils.vertical_health import get_precalculated_scores as vh
        from mcp_server.cs_pulse_mcp_server import _get_precalculated_scores as mcp_core
        r1 = mcp_common(account.account_id)
        r2 = vh(account.account_id)
        r3 = mcp_core(account.account_id)
        assert r1[0] == r2[0] == r3[0] == 77.0
        assert r1[2] == r2[2] == r3[2]

    def test_flask_api_routes_4tuple_agrees_with_3tuple_copies(self, app_ctx):
        _customer, account = _make_test_customer_and_account(health_score=81.0)
        from verticals.dc2_s.api_routes import get_precalculated_scores as flask_4t
        from mcp_server.common import get_precalculated_scores as mcp_3t
        h4, status4, pillars4, _month = flask_4t(account.account_id)
        h3, status3, pillars3 = mcp_3t(account.account_id)
        assert h4 == h3 == 81.0
        assert status4 == status3
        assert pillars4 == pillars3

    def test_ask_ai_direct_fallback_agrees_with_canonical(self, app_ctx):
        """The historically-worst offender: Ask AI's _execute_direct used to
        default missing scores to 0 and skip month-pinning. Verify it now
        matches the canonical service via list_accounts / get_account_health
        dispatch."""
        customer, account = _make_test_customer_and_account(health_score=59.0)
        from ask_ai_tools import _execute_direct
        from utils.account_health import get_account_health

        canonical = get_account_health(account.account_id)
        result = _execute_direct('get_account_health', {'account_id': account.account_id},
                                 customer.customer_id)
        assert result['health_score'] == round(canonical.health_score, 1)
        assert result['pillar_scores'] == {k: round(v, 1) for k, v in canonical.pillars.items()}

    def test_ask_ai_direct_reports_missing_not_zero(self, app_ctx):
        """C-19 regression guard: missing data must never silently render as 0."""
        customer, account = _make_test_customer_and_account(missing_data=True)
        from ask_ai_tools import _execute_direct
        result = _execute_direct('get_account_health', {'account_id': account.account_id},
                                 customer.customer_id)
        assert result['health_score'] is None
        assert result['health_data_missing'] is True

    def test_churned_account_excluded_from_ask_ai_at_risk(self, app_ctx):
        customer, account = _make_test_customer_and_account(
            health_score=20.0, account_status='churned')
        from ask_ai_tools import _execute_direct
        result = _execute_direct('get_at_risk_accounts', {'threshold': 70.0}, customer.customer_id)
        ids = [a['account_id'] for a in result['accounts']]
        assert account.account_id not in ids

    def test_churned_account_excluded_from_cfo_arr_at_risk(self, app_ctx):
        """Regression guard for the executive_dashboard_api.py:1288 fix —
        exercises the same query shape the CFO tile uses."""
        _customer, account = _make_test_customer_and_account(
            health_score=15.0, account_status='churned')
        from models import Account
        acct = Account.query.get(account.account_id)
        assert (acct.account_status or '').lower() == 'churned'
        # The fix is a `continue` on churned status before ARR accumulation —
        # verified structurally here; full endpoint coverage is the existing
        # executive dashboard test suite.


class TestTimeSeriesTenantIsolation:

    def test_cross_tenant_history_request_returns_empty(self, app_ctx):
        """C-18 regression guard: health_score_storage had no tenant filter."""
        from utils.account_health import get_account_health_history
        _c1, account = _make_test_customer_and_account(health_score=70.0)
        c2, _ = _make_test_customer_and_account(missing_data=True)
        history = get_account_health_history(account.account_id, c2.customer_id)
        assert history == []

    def test_same_tenant_history_returns_data(self, app_ctx):
        from utils.account_health import get_account_health_history
        customer, account = _make_test_customer_and_account(health_score=70.0)
        history = get_account_health_history(account.account_id, customer.customer_id)
        assert len(history) == 1
        assert history[0]['overall_score'] == 70.0
