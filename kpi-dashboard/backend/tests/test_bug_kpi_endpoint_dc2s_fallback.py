"""
GET /api/accounts/<id>/kpis returned [] for every real tenant (tracer finding,
Aug 2026, live EC2 customer 393 / datacenter_v1, 12 accounts).

kpi_api.py's get_account_kpis() only ever queried the legacy `kpis` table
(KPI model — per-CSV-upload shape: category/row_index/weight/aggregation_type).
Every tenant onboarded through the current generic-scorer pipeline (dc2_s,
saas_premium, datacenter_v1 alike) lands its KPI measurements in DC2SKPI
(`dc2s_kpis` table — kpi_code/value/target/pillar/measured_at) instead. The
endpoint never checked that table, so it silently returned an empty list even
when the account had hundreds of dc2s_kpis rows.

Fix: DC2SKPI first (current path for every real tenant), fall back to the
legacy KPI table only when DC2SKPI has no rows for that account — additive,
read-time only. No tenant's data is migrated or backfilled; a tenant that
genuinely still has legacy `kpis` rows and no dc2s_kpis rows keeps getting
served from `kpis`, unchanged.

Uses an in-memory SQLite DB via app_v3_minimal/extensions.db, same pattern as
tests/test_kpi_filtering.py.

*** DANGER — CONFIRMED LIVE, Aug 21 2026 *** app_v3_minimal.py runs
`db.create_all()` at MODULE IMPORT time (see its lines ~113-114), bound to
whatever DATABASE_URL is in the environment/.env at that moment — BEFORE
this test's setUp ever runs. Flask-SQLAlchemy then caches that engine on the
app; overriding `app.config['SQLALCHEMY_DATABASE_URI']` afterwards does NOT
rebind it (verified: `db.engine.url` still reports the real Postgres URL
after the override). That means `db.create_all()`/`db.drop_all()` in this
test's setUp/tearDown run against whatever REAL database was configured at
import time, not the in-memory URI set above — and drop_all() really does
drop every table's data there. This is exactly what happened here: it wiped
every row in the local `cs_pulse_datacenter` Postgres DB (a shared dev DB
with real seeded tenant data, matching this repo's prior "destructive test
fixture caused 2 prod data-loss incidents" pattern — this makes 3).
`tests/test_kpi_filtering.py` uses the identical pattern and carries the
same live risk in this environment.

The guard below refuses to run (skips) unless `db.engine` is provably
sqlite, so this can never repeat that wipe. In practice that means it will
SKIP in this environment: config.py's Config class hard-requires DATABASE_URL
to be a PostgreSQL DSN (raises ValueError otherwise), so there is no sqlite
DATABASE_URL that satisfies both "safe" and "importable" here — the only way
to run this file for real is to point DATABASE_URL at a disposable/throwaway
Postgres database (never a real seeded one) before any import in the process:
    DATABASE_URL='postgresql://user:pass@localhost/some_throwaway_db' \\
        python3.11 -m pytest tests/test_bug_kpi_endpoint_dc2s_fallback.py
The skip-by-default behavior is intentional and safe; treat the stash-based
FAIL/PASS proof already on record for this bug (see the fix commit/session
notes) as the verification evidence rather than re-running this file against
whatever DATABASE_URL happens to be ambient.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from extensions import db
from models import KPI, Account, Customer, DC2SKPI


class TestAccountKPIsDC2SFallback(unittest.TestCase):
    """GET /api/accounts/<id>/kpis must prefer dc2s_kpis, and only fall back
    to the legacy kpis table when dc2s_kpis is empty for that account."""

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()

        with self.app.app_context():
            # Safety guard (see module docstring): db.engine may already be
            # bound to a real, populated database from module-import time,
            # regardless of the app.config override just above. Refuse to
            # touch anything unless it's provably sqlite.
            engine_url = str(db.engine.url)
            if not engine_url.startswith('sqlite'):
                self.skipTest(
                    f"Refusing to run: db.engine is bound to a non-sqlite URL "
                    f"({engine_url}) — create_all()/drop_all() here would hit "
                    f"a real database, not the in-memory URI just set on "
                    f"app.config. Re-run with DATABASE_URL pointed at a "
                    f"throwaway sqlite file/':memory:' set BEFORE any import "
                    f"of app_v3_minimal in this process."
                )
            db.create_all()

            customer = Customer(customer_name='Test Customer', email='dc2s-fallback@test.com')
            db.session.add(customer)
            db.session.flush()
            self.customer_id = customer.customer_id

            # Account A: current generic-scorer tenant — has dc2s_kpis rows,
            # and (deliberately, to prove ordering) also some stray legacy
            # kpis rows that must NOT be returned once dc2s_kpis has data.
            account_a = Account(
                customer_id=self.customer_id, account_name='DC2S Account',
                revenue=1_000_000, industry='Tech', region='US',
            )
            db.session.add(account_a)
            db.session.flush()
            self.account_a_id = account_a.account_id

            db.session.add(DC2SKPI(
                account_id=self.account_a_id, kpi_code='P1-KPI1',
                value=85.0, target=90.0, pillar='P1',
            ))
            db.session.add(DC2SKPI(
                account_id=self.account_a_id, kpi_code='P2-KPI1',
                value=70.0, target=80.0, pillar='P2',
            ))
            db.session.add(KPI(
                account_id=self.account_a_id, category='stale_legacy_row',
                kpi_parameter='should_not_appear',
            ))

            # Account B: genuine legacy tenant — no dc2s_kpis rows at all,
            # only legacy kpis rows. Must still be served (no data left behind).
            account_b = Account(
                customer_id=self.customer_id, account_name='Legacy Account',
                revenue=500_000, industry='Tech', region='US',
            )
            db.session.add(account_b)
            db.session.flush()
            self.account_b_id = account_b.account_id

            db.session.add(KPI(
                account_id=self.account_b_id, category='legacy_upload',
                kpi_parameter='DAU', weight='0.5',
            ))

            # Account C: no KPI data anywhere — must return [], not error.
            account_c = Account(
                customer_id=self.customer_id, account_name='Empty Account',
                revenue=100_000, industry='Tech', region='US',
            )
            db.session.add(account_c)
            db.session.flush()
            self.account_c_id = account_c.account_id

            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _get(self, account_id):
        # get_current_customer_id() falls back to X-Customer-ID when the
        # request isn't authenticated (auth_middleware.py) — used here rather
        # than a session cookie to keep this a plain unittest.TestCase.
        return self.client.get(
            f'/api/accounts/{account_id}/kpis',
            headers={'X-Customer-ID': str(self.customer_id)},
        )

    def test_prefers_dc2s_kpis_over_legacy_when_both_exist(self):
        """This is the exact tracer-found bug: an account with real
        dc2s_kpis rows must not get an empty (or legacy-only) response."""
        resp = self._get(self.account_a_id)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)  # the 2 dc2s_kpis rows, not the 1 legacy row
        codes = {row['kpi_code'] for row in data}
        self.assertEqual(codes, {'P1-KPI1', 'P2-KPI1'})
        # dc2s_kpis shape, not the legacy kpis shape
        for row in data:
            self.assertIn('value', row)
            self.assertIn('pillar', row)
            self.assertNotIn('category', row)

    def test_falls_back_to_legacy_kpis_when_no_dc2s_rows(self):
        """A genuinely legacy tenant (no dc2s_kpis rows for this account) must
        still be served from the kpis table — additive fallback, not a swap."""
        resp = self._get(self.account_b_id)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['kpi_parameter'], 'DAU')
        self.assertIn('category', data[0])

    def test_empty_account_returns_empty_list_not_error(self):
        resp = self._get(self.account_c_id)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])


if __name__ == '__main__':
    unittest.main()
