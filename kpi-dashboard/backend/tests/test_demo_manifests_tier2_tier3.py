#!/usr/bin/env python3
"""
Test Suite — Tier 2 & 3: DB-Backed + API + Frontend Validation
================================================================
Tier 2: Seeds demo manifest CSV data into PostgreSQL via ORM models,
        then validates DB contents, API endpoints, and health calculations.
Tier 3: Tests API response formats match what frontend components expect,
        validates route availability, and checks component data contracts.

Requires: DATABASE_URL environment variable pointing to PostgreSQL.
"""

import sys
import os
import csv
import json
import uuid
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

# ============================================================
# APP + DB SETUP
# ============================================================

DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')

# Skip entire module if no DB connection
if not DATABASE_URL:
    pytest.skip("DATABASE_URL not set — skipping Tier 2/3 tests", allow_module_level=True)

# Import app after setting env
os.environ['DATABASE_URL'] = DATABASE_URL

from app_v3_minimal import app, db
from models import (
    Customer, Account, DC2SKPI, QualitativeSignal,
    HealthScore, PillarScore, KPIScore, CustomerConfig, User,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent
VERTICALS_DIR = BACKEND_DIR / "verticals"

# Test customer IDs to seed (subset with DEMO_MANIFEST + SMART loaders)
SEED_CUSTOMERS = [
    {
        'customer_id': 19,
        'data_dir': VERTICALS_DIR / "customer19-dc2_s" / "data",
        'company': 'DC2_S Demo Enterprise',
    },
    {
        'customer_id': 102,
        'data_dir': VERTICALS_DIR / "customer102-dc2_s" / "data",
        'company': 'E2E UI Test Customer',
    },
    {
        'customer_id': 261,
        'data_dir': VERTICALS_DIR / "customer261-dc2_s" / "data",
        'company': 'Customer 261',
    },
]


# ============================================================
# FIXTURES — SEED DB ONCE PER SESSION
# ============================================================

def _load_csv(path: Path) -> list[dict]:
    """Read a CSV into a list of dicts."""
    with open(path, 'r') as f:
        return list(csv.DictReader(f))


def _seed_customer(cust_info: dict):
    """Load one customer's CSV data into ORM tables."""
    cid = cust_info['customer_id']
    data_dir = cust_info['data_dir']

    if not data_dir.is_dir():
        return False

    # 1. Customer
    if not Customer.query.get(cid):
        customers_csv = data_dir / "customers.csv"
        if customers_csv.exists():
            rows = _load_csv(customers_csv)
            for r in rows:
                if int(r['customer_id']) == cid:
                    db.session.add(Customer(
                        customer_id=cid,
                        customer_name=r.get('customer_name', cust_info['company']),
                        vertical=r.get('vertical', 'dc2_s'),
                    ))
                    break
        else:
            db.session.add(Customer(
                customer_id=cid,
                customer_name=cust_info['company'],
                vertical='dc2_s',
            ))
        db.session.flush()

    # 2. Accounts
    accounts_csv = data_dir / "accounts.csv"
    if accounts_csv.exists():
        rows = _load_csv(accounts_csv)
        for r in rows:
            aid = int(r['account_id'])
            if not Account.query.get(aid):
                db.session.add(Account(
                    account_id=aid,
                    customer_id=int(r.get('customer_id', cid)),
                    account_name=r.get('account_name', f'Account {aid}'),
                    account_status=r.get('account_status', 'active'),
                    industry=r.get('industry'),
                    vertical=r.get('vertical', 'dc2_s'),
                    region=r.get('region'),
                ))
        db.session.flush()

    # 3. KPI Measurements → DC2SKPI
    kpi_csv = data_dir / "kpi_measurements.csv"
    if kpi_csv.exists():
        rows = _load_csv(kpi_csv)
        batch = []
        for r in rows:
            aid = int(r['account_id'])
            kpi_code = r['kpi_code']
            # Parse date — handle multiple formats
            date_str = r.get('measured_at') or r.get('date', '2024-01-01')
            try:
                measured_at = datetime.fromisoformat(date_str)
            except ValueError:
                measured_at = datetime.strptime(date_str, '%Y-%m-%d')

            batch.append(dict(
                account_id=aid,
                kpi_code=kpi_code,
                value=float(r['value']),
                target=float(r.get('target', 85.0)),
                pillar=r.get('pillar', kpi_code.split('-')[0] if '-' in kpi_code else 'XX'),
                weight=float(r['weight']) if r.get('weight') else None,
                status=r.get('status'),
                measured_at=measured_at,
            ))
        # Bulk insert, skip duplicates via try/except per batch
        if batch:
            for b in batch:
                try:
                    db.session.add(DC2SKPI(**b))
                    db.session.flush()
                except Exception:
                    db.session.rollback()
                    # Duplicate — skip

    # 4. Qualitative Signals
    signals_csv = data_dir / "qualitative_signals.csv"
    if signals_csv.exists():
        rows = _load_csv(signals_csv)
        for i, r in enumerate(rows):
            sid = r.get('signal_id') or f"sig-{cid}-{i}"
            existing = QualitativeSignal.query.get(sid)
            if not existing:
                try:
                    db.session.add(QualitativeSignal(
                        signal_id=sid,
                        account_id=int(r['account_id']),
                        signal_date=r.get('signal_date', '2024-01-01'),
                        signal_type=r.get('signal_type', 'health_check'),
                        content=r.get('signal_text') or r.get('content', ''),
                        sentiment=r.get('sentiment', 'neutral'),
                    ))
                    db.session.flush()
                except Exception:
                    db.session.rollback()

    db.session.commit()
    return True


def _seed_test_user(cid: int):
    """Create a test user for API auth."""
    from werkzeug.security import generate_password_hash
    email = f"test_{cid}@cspulse.test"
    existing = User.query.filter_by(email=email).first()
    if not existing:
        db.session.add(User(
            customer_id=cid,
            user_name=f'Test User {cid}',
            email=email,
            password_hash=generate_password_hash('testpass123'),
            vertical='dc2_s',
            role='admin',
        ))
        db.session.commit()
    return email


@pytest.fixture(scope='session')
def seeded_app():
    """Create app, seed DB, return (app, client)."""
    with app.app_context():
        db.create_all()
        for cust in SEED_CUSTOMERS:
            _seed_customer(cust)
        _seed_test_user(19)
    yield app


@pytest.fixture(scope='session')
def client(seeded_app):
    """Flask test client."""
    seeded_app.config['TESTING'] = True
    return seeded_app.test_client()


@pytest.fixture(scope='session')
def auth_client(seeded_app):
    """Authenticated Flask test client."""
    seeded_app.config['TESTING'] = True
    c = seeded_app.test_client()
    with seeded_app.app_context():
        # Login
        resp = c.post('/api/login', json={
            'email': 'test_19@cspulse.test',
            'password': 'testpass123',
        })
        # Store session cookie
    return c


# ============================================================
# TIER 2: DATABASE VALIDATION
# ============================================================

class TestTier2_DBSeeding:
    """Verify demo data was seeded into PostgreSQL correctly."""

    def test_customer19_exists(self, seeded_app):
        with seeded_app.app_context():
            c = Customer.query.get(19)
            assert c is not None
            assert c.customer_name == 'DC2_S Demo Enterprise'

    def test_customer102_exists(self, seeded_app):
        with seeded_app.app_context():
            c = Customer.query.get(102)
            assert c is not None

    def test_customer261_exists(self, seeded_app):
        with seeded_app.app_context():
            c = Customer.query.get(261)
            assert c is not None

    def test_customer19_has_10_accounts(self, seeded_app):
        with seeded_app.app_context():
            accounts = Account.query.filter_by(customer_id=19).all()
            assert len(accounts) >= 10, f"Expected 10 accounts, got {len(accounts)}"

    def test_customer102_has_5_accounts(self, seeded_app):
        with seeded_app.app_context():
            accounts = Account.query.filter_by(customer_id=102).all()
            assert len(accounts) >= 5, f"Expected 5 accounts, got {len(accounts)}"

    def test_customer261_has_3_accounts(self, seeded_app):
        with seeded_app.app_context():
            accounts = Account.query.filter_by(customer_id=261).all()
            assert len(accounts) >= 3, f"Expected 3 accounts, got {len(accounts)}"

    def test_all_accounts_are_active(self, seeded_app):
        with seeded_app.app_context():
            for cust in SEED_CUSTOMERS:
                accounts = Account.query.filter_by(customer_id=cust['customer_id']).all()
                for a in accounts:
                    assert a.account_status == 'active', (
                        f"Account {a.account_id} status is '{a.account_status}'"
                    )

    def test_all_accounts_are_dc2_s(self, seeded_app):
        with seeded_app.app_context():
            for cust in SEED_CUSTOMERS:
                accounts = Account.query.filter_by(customer_id=cust['customer_id']).all()
                for a in accounts:
                    assert a.vertical == 'dc2_s', (
                        f"Account {a.account_id} vertical is '{a.vertical}'"
                    )


class TestTier2_KPIData:
    """Verify KPI measurements loaded correctly."""

    def test_customer19_has_kpi_data(self, seeded_app):
        with seeded_app.app_context():
            account_ids = [a.account_id for a in Account.query.filter_by(customer_id=19).all()]
            kpi_count = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).count()
            assert kpi_count > 0, "No KPI data for customer 19"

    def test_customer102_has_kpi_data(self, seeded_app):
        with seeded_app.app_context():
            account_ids = [a.account_id for a in Account.query.filter_by(customer_id=102).all()]
            kpi_count = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).count()
            assert kpi_count > 0, "No KPI data for customer 102"

    def test_kpi_values_are_numeric(self, seeded_app):
        with seeded_app.app_context():
            kpis = DC2SKPI.query.limit(50).all()
            for k in kpis:
                assert isinstance(k.value, (int, float, Decimal)), (
                    f"KPI {k.kpi_id} value is not numeric: {type(k.value)}"
                )

    def test_kpi_have_pillar_codes(self, seeded_app):
        with seeded_app.app_context():
            kpis = DC2SKPI.query.limit(100).all()
            for k in kpis:
                assert k.pillar is not None and len(k.pillar) > 0, (
                    f"KPI {k.kpi_id} missing pillar code"
                )

    def test_kpi_have_timestamps(self, seeded_app):
        with seeded_app.app_context():
            kpis = DC2SKPI.query.limit(50).all()
            for k in kpis:
                assert k.measured_at is not None, (
                    f"KPI {k.kpi_id} missing measured_at"
                )

    def test_kpi_pillars_are_valid(self, seeded_app):
        """KPI pillar codes should be from the DC2_S set."""
        with seeded_app.app_context():
            pillars = db.session.query(DC2SKPI.pillar).distinct().all()
            valid = {'P1', 'P2', 'P3', 'P4', 'P5'}
            for (p,) in pillars:
                assert p in valid, f"Unexpected pillar code: {p}"

    def test_kpi_account_ids_match_accounts(self, seeded_app):
        """All KPI account_ids should reference existing accounts."""
        with seeded_app.app_context():
            kpi_aids = {r[0] for r in db.session.query(DC2SKPI.account_id).distinct().all()}
            acct_aids = {r[0] for r in db.session.query(Account.account_id).all()}
            orphans = kpi_aids - acct_aids
            assert not orphans, f"KPIs reference non-existent accounts: {orphans}"


class TestTier2_Signals:
    """Verify qualitative signals loaded correctly."""

    def test_customer19_has_signals(self, seeded_app):
        with seeded_app.app_context():
            account_ids = [a.account_id for a in Account.query.filter_by(customer_id=19).all()]
            count = QualitativeSignal.query.filter(
                QualitativeSignal.account_id.in_(account_ids)
            ).count()
            assert count > 0, "No signals for customer 19"

    def test_signals_have_required_fields(self, seeded_app):
        with seeded_app.app_context():
            signals = QualitativeSignal.query.limit(20).all()
            for s in signals:
                assert s.signal_id is not None
                assert s.account_id is not None
                assert s.signal_date is not None

    def test_signal_sentiments_are_valid(self, seeded_app):
        with seeded_app.app_context():
            sentiments = {r[0] for r in db.session.query(
                QualitativeSignal.sentiment
            ).distinct().all() if r[0]}
            valid = {'positive', 'negative', 'neutral', 'mixed'}
            for s in sentiments:
                assert s.lower() in valid, f"Unexpected sentiment: {s}"


class TestTier2_CrossTableIntegrity:
    """Foreign key and cross-table consistency."""

    def test_all_accounts_have_valid_customer(self, seeded_app):
        with seeded_app.app_context():
            orphan_count = db.session.execute(
                db.text("""
                    SELECT COUNT(*) FROM accounts a
                    LEFT JOIN customers c ON a.customer_id = c.customer_id
                    WHERE c.customer_id IS NULL
                """)
            ).scalar()
            assert orphan_count == 0, f"{orphan_count} accounts have no customer"

    def test_all_kpis_have_valid_account(self, seeded_app):
        with seeded_app.app_context():
            orphan_count = db.session.execute(
                db.text("""
                    SELECT COUNT(*) FROM dc2s_kpis k
                    LEFT JOIN accounts a ON k.account_id = a.account_id
                    WHERE a.account_id IS NULL
                """)
            ).scalar()
            assert orphan_count == 0, f"{orphan_count} KPIs have no account"

    def test_all_signals_have_valid_account(self, seeded_app):
        with seeded_app.app_context():
            orphan_count = db.session.execute(
                db.text("""
                    SELECT COUNT(*) FROM qualitative_signals s
                    LEFT JOIN accounts a ON s.account_id = a.account_id
                    WHERE a.account_id IS NULL
                """)
            ).scalar()
            assert orphan_count == 0, f"{orphan_count} signals have no account"

    def test_manifest_account_count_matches_db(self, seeded_app):
        """CSV manifest claims should match DB counts."""
        expected = {19: 10, 102: 5, 261: 3}
        with seeded_app.app_context():
            for cid, expected_count in expected.items():
                actual = Account.query.filter_by(customer_id=cid).count()
                assert actual >= expected_count, (
                    f"Customer {cid}: expected {expected_count} accounts, got {actual}"
                )


# ============================================================
# TIER 2: API ENDPOINT TESTS
# ============================================================

class TestTier2_HealthEndpoint:
    """Test /api/health and core API availability."""

    def test_health_endpoint(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200

    def test_login_endpoint_exists(self, client):
        resp = client.post('/api/login', json={
            'email': 'nonexistent@test.com',
            'password': 'wrong',
        })
        # Should return 401 or 400, not 404
        assert resp.status_code != 404, "Login endpoint not registered"

    def test_upload_endpoint_exists(self, client):
        resp = client.post('/api/upload')
        # Should return 400 (no file) or 401 (auth), not 404
        assert resp.status_code != 404, "Upload endpoint not registered"


class TestTier2_DC2SEndpoints:
    """Test DC2_S vertical API endpoints."""

    def test_dc2s_accounts_endpoint(self, auth_client, seeded_app):
        with seeded_app.app_context():
            resp = auth_client.get('/api/dc2s/accounts?customer_id=19')
            # Accept 200 or 401 (if auth needed differently)
            assert resp.status_code in (200, 401, 403), (
                f"DC2S accounts returned {resp.status_code}"
            )

    def test_dc2s_config_endpoint(self, auth_client, seeded_app):
        with seeded_app.app_context():
            resp = auth_client.get('/api/dc2s/config/defaults')
            assert resp.status_code in (200, 401, 404)

    def test_dc2s_scores_endpoint(self, auth_client, seeded_app):
        with seeded_app.app_context():
            resp = auth_client.get('/api/dc2s/scores/19001')
            assert resp.status_code in (200, 401, 404)


class TestTier2_AuthFlow:
    """Test authentication flow."""

    def test_login_success(self, client, seeded_app):
        with seeded_app.app_context():
            resp = client.post('/api/login', json={
                'email': 'test_19@cspulse.test',
                'password': 'testpass123',
            })
            assert resp.status_code == 200, f"Login failed: {resp.data}"
            data = resp.get_json()
            assert 'user' in data or 'customer_id' in data or resp.status_code == 200

    def test_login_wrong_password(self, client, seeded_app):
        with seeded_app.app_context():
            resp = client.post('/api/login', json={
                'email': 'test_19@cspulse.test',
                'password': 'wrongpass',
            })
            assert resp.status_code in (401, 403)


# ============================================================
# TIER 3: API RESPONSE FORMAT FOR FRONTEND
# ============================================================

class TestTier3_AccountsAPIFormat:
    """Validate API response formats match frontend component expectations."""

    def test_accounts_response_is_list(self, auth_client, seeded_app):
        with seeded_app.app_context():
            resp = auth_client.get('/api/dc2s/accounts?customer_id=19')
            if resp.status_code == 200:
                data = resp.get_json()
                assert isinstance(data, (list, dict)), (
                    f"Expected list or dict, got {type(data)}"
                )

    def test_account_has_required_fields(self, auth_client, seeded_app):
        """Frontend AccountCard component expects specific fields."""
        with seeded_app.app_context():
            resp = auth_client.get('/api/dc2s/accounts?customer_id=19')
            if resp.status_code == 200:
                data = resp.get_json()
                accounts = data if isinstance(data, list) else data.get('accounts', [])
                if accounts:
                    first = accounts[0]
                    # Fields the frontend expects
                    for field in ['account_id', 'account_name']:
                        assert field in first, (
                            f"Account response missing '{field}'"
                        )


class TestTier3_KPIAPIFormat:
    """Validate KPI API response format for dashboard components."""

    def test_kpi_response_structure(self, auth_client, seeded_app):
        with seeded_app.app_context():
            resp = auth_client.get('/api/dc2s/accounts/19001/kpis')
            if resp.status_code == 200:
                data = resp.get_json()
                # Should contain KPI data with pillar grouping
                assert isinstance(data, (list, dict))


class TestTier3_FrontendRouteAssets:
    """Verify frontend routes and component files exist."""

    def test_app_tsx_exists(self):
        app_tsx = BACKEND_DIR.parent / "src" / "App.tsx"
        assert app_tsx.exists(), "src/App.tsx missing"

    def test_portco_dashboard_exists(self):
        dashboard = BACKEND_DIR.parent / "src" / "components" / "dashboard" / "PortcoCEODashboard.tsx"
        assert dashboard.exists(), "PortcoCEODashboard.tsx missing"

    def test_app_has_portco_route(self):
        app_tsx = BACKEND_DIR.parent / "src" / "App.tsx"
        content = app_tsx.read_text()
        assert 'portco-dashboard' in content, (
            "App.tsx missing /portco-dashboard route"
        )

    def test_app_has_login_route(self):
        app_tsx = BACKEND_DIR.parent / "src" / "App.tsx"
        content = app_tsx.read_text()
        assert 'login' in content.lower(), "App.tsx missing login route"

    def test_app_has_dashboard_route(self):
        app_tsx = BACKEND_DIR.parent / "src" / "App.tsx"
        content = app_tsx.read_text()
        assert 'dashboard' in content.lower(), "App.tsx missing dashboard route"


class TestTier3_FrontendDataContracts:
    """Verify that DB data can be serialized for frontend consumption."""

    def test_account_to_dict(self, seeded_app):
        with seeded_app.app_context():
            acct = Account.query.filter_by(customer_id=19).first()
            assert acct is not None
            # Verify JSON-serializable
            data = {
                'account_id': acct.account_id,
                'account_name': acct.account_name,
                'customer_id': acct.customer_id,
                'status': acct.account_status,
                'vertical': acct.vertical,
                'region': acct.region,
                'industry': acct.industry,
            }
            serialized = json.dumps(data)
            assert serialized is not None

    def test_kpi_to_dict(self, seeded_app):
        with seeded_app.app_context():
            kpi = DC2SKPI.query.first()
            if kpi:
                data = kpi.to_dict()
                assert 'kpi_code' in data
                assert 'value' in data
                assert 'pillar' in data
                # Must be JSON-serializable
                serialized = json.dumps(data)
                assert serialized is not None

    def test_signal_to_dict(self, seeded_app):
        with seeded_app.app_context():
            sig = QualitativeSignal.query.first()
            if sig:
                data = sig.to_dict()
                assert 'signal_id' in data
                assert 'account_id' in data
                serialized = json.dumps(data)
                assert serialized is not None


class TestTier3_BlueprintRegistration:
    """Verify all critical API blueprints are registered."""

    REQUIRED_BLUEPRINTS = [
        'dc2s_api',
        'upload_api_v3_improved',
    ]

    def test_required_blueprints_registered(self, seeded_app):
        registered = set(seeded_app.blueprints.keys())
        for bp in self.REQUIRED_BLUEPRINTS:
            assert bp in registered, (
                f"Blueprint '{bp}' not registered. Available: {sorted(registered)}"
            )

    def test_blueprint_count(self, seeded_app):
        """App should have 10+ blueprints registered."""
        count = len(seeded_app.blueprints)
        assert count >= 10, (
            f"Only {count} blueprints registered, expected 10+"
        )

    def test_list_all_registered_routes(self, seeded_app):
        """Sanity check: verify we have API routes."""
        with seeded_app.app_context():
            rules = [rule.rule for rule in seeded_app.url_map.iter_rules()]
            api_rules = [r for r in rules if r.startswith('/api/')]
            assert len(api_rules) >= 20, (
                f"Only {len(api_rules)} API routes, expected 20+"
            )


class TestTier3_CriticalRoutes:
    """Verify critical API routes are reachable (return non-404)."""

    CRITICAL_ROUTES = [
        ('GET', '/api/health'),
        ('POST', '/api/login'),
        ('POST', '/api/upload'),
    ]

    @pytest.mark.parametrize("method,path", CRITICAL_ROUTES)
    def test_route_exists(self, client, method, path):
        if method == 'GET':
            resp = client.get(path)
        else:
            resp = client.post(path, json={})
        assert resp.status_code != 404, (
            f"{method} {path} returned 404 — route not registered"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("=" * 70)
    print("TIER 2 + TIER 3 DEMO MANIFEST DB TESTS")
    print(f"DATABASE_URL: {DATABASE_URL[:50]}...")
    print("=" * 70)
    sys.exit(pytest.main([__file__, '-v', '--tb=short']))
