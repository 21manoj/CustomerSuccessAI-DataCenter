#!/usr/bin/env python3
"""
Regression tests for the 9 Account-column-access bugs drained from the
audit_account_column_access baseline (PR #32 follow-up).

Every entry that used to live in
``scripts/audit_account_column_access_baseline.txt`` would have raised
``AttributeError: 'Account' object has no attribute '<X>'`` the moment its
host route was exercised against a populated tenant.

Two test tiers:

  Tier A — Model-shape canaries (DB-free).
      Imports a couple of pure modules + the Account ORM model, asserts the
      assumptions the fix relies on (e.g. no `health_score` column). These run
      in CI alongside test_score_calculator.

  Tier B — Integration tests (Flask app + SQLite in-memory).
      Hit each formerly-broken entry point and assert it returns a 200-shaped
      response. These need to import app_v3_minimal, which requires
      DATABASE_URL — skipped automatically when not set (matches the local-dev
      pattern used by test_team_capacity_cold_start.py).

Drained entries (file : Account.<attr>):
  1. data_quality_api.py            acct.products       (no `products` relationship)
  2. mcp_tool_bridge.py             account.health_score (lives in HealthScore)
  3. mcp_tool_bridge.py             account.name         (column is account_name)
  4. mcp_tool_bridge.py             account.status       (column is account_status)
  5. playbook_triggers_api.py       account.health_score (lives in HealthScore)
  6. test_runner_api.py             a.id                 (column is account_id)
  7. test_runner_api.py             acct.arr             (column is revenue)
  8. test_runner_api.py             acct.id              (column is account_id)
  9. test_runner_api.py             acct.name            (column is account_name)
"""

import ast
import os
import sys
import uuid
from datetime import date
from pathlib import Path

import pytest

# Make backend importable when the test runner is launched from repo root.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


# ═══════════════════════════════════════════════════════════════════════════
# Tier A — Model-shape canaries (DB-free, CI-safe)
# ═══════════════════════════════════════════════════════════════════════════


def _account_columns_from_ast():
    """Parse models.py with the AST and return the set of declared columns.

    Avoids importing the ORM (which transitively pulls in config.py and
    requires DATABASE_URL). This is the same approach the audit script uses.
    """
    models_path = Path(_BACKEND_DIR) / 'models.py'
    tree = ast.parse(models_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'Account':
            cols = set()
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for t in stmt.targets:
                        if isinstance(t, ast.Name) and isinstance(stmt.value, ast.Call):
                            fn = stmt.value.func
                            is_col = (
                                (isinstance(fn, ast.Attribute) and fn.attr == 'Column')
                                or (isinstance(fn, ast.Name) and fn.id == 'Column')
                            )
                            if is_col:
                                cols.add(t.id)
            return cols
    raise RuntimeError('class Account not found in models.py')


def test_account_model_has_no_drained_columns():
    """If any of these become real columns, revisit the corresponding fix."""
    cols = _account_columns_from_ast()
    drained = {
        'health_score', 'name', 'status', 'id', 'arr',
        'products', 'is_active', 'assigned_csm', 'journey_data',
    }
    overlap = drained & cols
    assert not overlap, (
        f'Account model gained column(s) {overlap} — the audit baseline '
        f'drain (PR follow-up to #32) can be revisited.'
    )


def test_account_model_has_canonical_columns():
    """Pin the actual column names the fixes read from."""
    cols = _account_columns_from_ast()
    expected = {
        'account_id', 'account_name', 'account_status',
        'revenue', 'customer_id', 'profile_metadata',
    }
    missing = expected - cols
    assert not missing, (
        f'Account model lost canonical column(s) {missing}. '
        f'Many call sites depend on these — investigate the model change.'
    )


def _strip_comments_and_strings(src: str) -> str:
    """Drop Python comments and string literals so we only scan executable code.

    Pattern-matching against raw source would also flag the same identifier
    when it appears in a docstring or explanatory comment, which we use to
    document the historical bugs in the fix sites.
    """
    import io
    import tokenize
    out = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(src).readline)
        for tok in tokens:
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            out.append(tok.string)
    except tokenize.TokenizeError:
        return src
    return ' '.join(out)


def test_drained_files_have_no_bad_patterns():
    """Static check (code only — comments & strings stripped): the 4 fixed
    files no longer contain the historical bad patterns.

    This is a cheap regression backstop that runs in CI without DATABASE_URL;
    the full audit (scripts/audit_account_column_access.py) covers the
    repo-wide invariant.
    """
    bad_patterns_by_file = {
        'playbook_triggers_api.py': ['account.health_score'],
        'mcp_tool_bridge.py': ['account.name', 'account.status', 'account.health_score'],
        'data_quality_api.py': ['acct.products'],
        'test_runner_api.py': ['acct.id', 'acct.name', 'acct.arr', 'a.id for a in accounts',
                               'is_active=True'],
    }
    backend = Path(_BACKEND_DIR)
    failures = []
    for fname, patterns in bad_patterns_by_file.items():
        src = _strip_comments_and_strings((backend / fname).read_text())
        for p in patterns:
            if p in src:
                failures.append(f'{fname}: still contains {p!r}')
    assert not failures, '\n'.join(failures)


# ═══════════════════════════════════════════════════════════════════════════
# Tier B — Integration tests (require DATABASE_URL set; skipped otherwise)
# ═══════════════════════════════════════════════════════════════════════════


_requires_app = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL'),
    reason='DATABASE_URL not set — skip integration tests (Tier A canaries cover the static drain).',
)


@pytest.fixture
def tenant_with_accounts():
    """Populated tenant: 3 accounts, HealthScore rows for each.

    Uses SQLite in-memory (override SQLALCHEMY_DATABASE_URI post-import).
    Skip-guarded by _requires_app at the test level.
    """
    from app_v3_minimal import app, db
    from models import Customer, Account, HealthScore

    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()

        customer = Customer(
            customer_name='Drain Regression Tenant',
            email=f'drain_{uuid.uuid4().hex[:6]}@test.com',
        )
        db.session.add(customer)
        db.session.commit()

        accounts = []
        for i, score in enumerate([55, 82, 90]):
            acct = Account(
                customer_id=customer.customer_id,
                account_name=f'Account {i}',
                revenue=1_000_000 * (i + 1),
                account_status='active',
                external_account_id=f'DRAIN-{i}',
            )
            db.session.add(acct)
            db.session.commit()
            accounts.append(acct)

            db.session.add(HealthScore(
                account_id=acct.account_id,
                measurement_month=date(2026, 5, 1),
                health_score=score,
            ))
        db.session.commit()

        yield {
            'app': app,
            'db': db,
            'customer_id': customer.customer_id,
            'account_ids': [a.account_id for a in accounts],
            'first_account_id': accounts[0].account_id,
        }

        db.session.remove()
        db.drop_all()


# -- (B1) playbook_triggers_api.py: VoC + Activation evaluators ---------------


@_requires_app
def test_evaluate_voc_triggers_returns_200_with_health_scores(tenant_with_accounts):
    """evaluate_voc_triggers must not AttributeError on Account.health_score."""
    with tenant_with_accounts['app'].app_context():
        from playbook_triggers_api import evaluate_voc_triggers
        result = evaluate_voc_triggers(
            tenant_with_accounts['customer_id'],
            {'nps_threshold': 7, 'csat_threshold': 3.6,
             'churn_risk_threshold': 0.30, 'health_score_drop_threshold': 10},
        )
        assert isinstance(result, dict)
        assert 'triggered' in result
        assert 'affected_accounts' in result
        # health_score=55 trips the NPS proxy (55 < 70) ⇒ ≥1 account triggered.
        assert result['triggered'] is True
        assert len(result['affected_accounts']) >= 1
        for rec in result['affected_accounts']:
            assert rec['health_score'] is None or isinstance(rec['health_score'], (int, float))


@_requires_app
def test_evaluate_activation_triggers_returns_200(tenant_with_accounts):
    """evaluate_activation_triggers must not AttributeError on Account.health_score."""
    with tenant_with_accounts['app'].app_context():
        from playbook_triggers_api import evaluate_activation_triggers
        result = evaluate_activation_triggers(
            tenant_with_accounts['customer_id'],
            {'adoption_index_threshold': 60, 'active_users_threshold': 5000,
             'dau_mau_threshold': 0.25, 'unused_feature_check': False},
        )
        assert isinstance(result, dict)
        assert 'triggered' in result
        assert 'affected_accounts' in result


# -- (B2) data_quality_api.py: seed_missing_products --------------------------


@_requires_app
def test_seed_missing_products_creates_defaults(tenant_with_accounts):
    """Endpoint must seed one default Product per Product-less account."""
    app_ = tenant_with_accounts['app']
    db_ = tenant_with_accounts['db']
    with app_.app_context():
        from models import Product
        existing_acct_id = tenant_with_accounts['account_ids'][0]
        db_.session.add(Product(
            account_id=existing_acct_id,
            customer_id=tenant_with_accounts['customer_id'],
            product_name='Pre-existing Product',
        ))
        db_.session.commit()

        client = app_.test_client()
        resp = client.post(
            '/api/data-quality/fix/seed-missing-products',
            headers={'X-Customer-ID': str(tenant_with_accounts['customer_id'])},
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        body = resp.get_json()
        assert body['status'] == 'success'
        # 3 accounts; 1 pre-seeded ⇒ exactly 2 created.
        assert body['created_products'] == 2


# -- (B3) mcp_tool_bridge.py: CRM local-fallback path -------------------------


@_requires_app
def test_mcp_tool_bridge_crm_fallback_returns_local_data(tenant_with_accounts):
    """Local-DB fallback must return real account data, not unavailable."""
    with tenant_with_accounts['app'].app_context():
        from mcp_tool_bridge import MCPToolBridge
        from agent_tool_registry import AgentToolRegistry

        registry = AgentToolRegistry()
        bridge = MCPToolBridge(tool_registry=registry)
        bridge._mcp_available = False  # force fallback
        bridge.register_mcp_tools(mcp_integration=None)

        crm_tool = registry.get_tool('crm_account_data')
        assert crm_tool is not None

        result = crm_tool.callable(
            account_id=str(tenant_with_accounts['first_account_id']),
            customer_id=tenant_with_accounts['customer_id'],
        )
        assert result['source'] == 'local_fallback', (
            f"Expected local_fallback; got {result['source']!r}. "
            f"If 'unavailable', the fallback silently swallowed an exception — "
            f"likely a reintroduced Account.<attr> drift."
        )
        data = result['data']
        # The wire schema still uses 'name'/'status' (legacy MCP contract);
        # the fix is internal — read account_name/account_status, expose as
        # name/status to keep agent consumers stable.
        assert data['account_id'] == tenant_with_accounts['first_account_id']
        assert data['name'] == 'Account 0'
        assert data['status'] == 'active'
        assert data['revenue'] == 1_000_000
        assert data['health_score'] == 55.0  # joined from HealthScore


# -- (B4) test_runner_api.py: platform-state route ----------------------------


@_requires_app
def test_test_runner_platform_state_returns_200(tenant_with_accounts):
    """platform-state must not AttributeError on Account.id / .name / .arr."""
    app_ = tenant_with_accounts['app']
    with app_.app_context():
        from test_runner_api import test_runner_api as tr_bp

        # Mount the blueprint just for this test if not already mounted.
        registered_names = {bp.name for bp in app_.blueprints.values()}
        if tr_bp.name not in registered_names:
            app_.register_blueprint(tr_bp)

        client = app_.test_client()
        with client.session_transaction() as sess:
            sess['tr_role'] = 'super_admin'  # bypass RBAC for the test

        resp = client.get(
            '/api/test-runner/platform-state',
            query_string={'customer_id': tenant_with_accounts['customer_id']},
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        body = resp.get_json()
        assert len(body['accounts']) == 3
        for entry in body['accounts']:
            # Right keys → pre-fix code raised before this dict was built.
            assert 'account_id' in entry
            assert 'account_name' in entry
            assert 'arr' in entry
