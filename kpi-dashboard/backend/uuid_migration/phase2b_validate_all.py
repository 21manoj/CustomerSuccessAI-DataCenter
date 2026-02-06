#!/usr/bin/env python3
"""
Phase 2b: Validate UUID Migration for ALL Customers

Extends Phase 1c validation to check both:
  - customer_id=9 (DC) — should have 'dc_' prefixes
  - customer_id=1 (SaaS) — should have 'saas_' prefixes

Also checks cross-customer isolation (no UUID collisions between verticals).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text


class ValidationResult:
    def __init__(self):
        self.checks = []
        self.passed = 0
        self.failed = 0

    def check(self, name, passed, detail=''):
        status = 'PASS' if passed else 'FAIL'
        self.checks.append({'name': name, 'passed': passed, 'detail': detail})
        if passed:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed += 1
            print(f"  [FAIL] {name} -- {detail}")

    @property
    def all_passed(self):
        return self.failed == 0

    def summary(self):
        total = self.passed + self.failed
        return f"{self.passed}/{total} checks passed, {self.failed} failed"


def _validate_customer(conn, result, customer_id, vertical, prefix):
    """Validate UUID backfill for a single customer."""

    # Customer record
    row = conn.execute(text(
        "SELECT uuid, vertical FROM customers WHERE customer_id = :cid"
    ), {'cid': customer_id}).fetchone()

    result.check(
        f"[{vertical}] Customer {customer_id} has uuid",
        row is not None and row[0] is not None
    )
    result.check(
        f"[{vertical}] Customer {customer_id} vertical = '{vertical}'",
        row is not None and row[1] == vertical
    )
    result.check(
        f"[{vertical}] Customer {customer_id} uuid starts with '{prefix}_cust_'",
        row is not None and row[0] is not None and row[0].startswith(f'{prefix}_cust_')
    )

    # Tables with direct customer_id FK
    tables = [
        ('accounts', f'{prefix}_acct_'),
        ('products', f'{prefix}_prod_'),
        ('users', f'{prefix}_usr_'),
        ('customer_configs', f'{prefix}_ccfg_'),
        ('kpi_uploads', f'{prefix}_upl_'),
        ('health_trends', f'{prefix}_htrend_'),
        ('kpi_time_series', f'{prefix}_kts_'),
        ('kpi_reference_ranges', f'{prefix}_kref_'),
        ('playbook_triggers', f'{prefix}_ptrig_'),
        ('playbook_executions', f'{prefix}_pexec_'),
        ('playbook_reports', f'{prefix}_prep_'),
        ('feature_toggles', f'{prefix}_ftog_'),
        ('query_audits', f'{prefix}_qaud_'),
        ('activity_logs', f'{prefix}_alog_'),
        ('customer_workflow_configs', f'{prefix}_wfcfg_'),
        ('account_notes', f'{prefix}_anote_'),
        ('account_snapshots', f'{prefix}_asnap_'),
    ]

    for table, expected_prefix in tables:
        try:
            total = conn.execute(text(
                f"SELECT COUNT(*) FROM {table} WHERE customer_id = :cid"
            ), {'cid': customer_id}).scalar()

            if total == 0:
                continue  # Skip empty tables

            null_count = conn.execute(text(
                f"SELECT COUNT(*) FROM {table} WHERE customer_id = :cid AND uuid IS NULL"
            ), {'cid': customer_id}).scalar()

            bad_prefix = conn.execute(text(
                f"SELECT COUNT(*) FROM {table} "
                f"WHERE customer_id = :cid AND uuid IS NOT NULL AND uuid NOT LIKE :pfx"
            ), {'cid': customer_id, 'pfx': f'{expected_prefix}%'}).scalar()

            result.check(
                f"[{vertical}] {table}: {total} records, no NULL uuids",
                null_count == 0,
                f"{null_count}/{total} missing"
            )
            if total > 0:
                result.check(
                    f"[{vertical}] {table}: all uuids start with '{expected_prefix}'",
                    bad_prefix == 0,
                    f"{bad_prefix} wrong prefix"
                )
        except Exception as e:
            result.check(f"[{vertical}] {table}", False, f"Error: {e}")

    # KPIs (join through accounts)
    try:
        total = conn.execute(text(
            "SELECT COUNT(*) FROM kpis k JOIN accounts a ON k.account_id = a.account_id "
            "WHERE a.customer_id = :cid"
        ), {'cid': customer_id}).scalar()

        if total > 0:
            null_count = conn.execute(text(
                "SELECT COUNT(*) FROM kpis k JOIN accounts a ON k.account_id = a.account_id "
                "WHERE a.customer_id = :cid AND k.uuid IS NULL"
            ), {'cid': customer_id}).scalar()

            result.check(
                f"[{vertical}] kpis: {total} records, no NULL uuids",
                null_count == 0,
                f"{null_count}/{total} missing"
            )
    except Exception as e:
        result.check(f"[{vertical}] kpis", False, f"Error: {e}")


def run(db):
    """Validate both DC and SaaS customers."""
    result = ValidationResult()

    with db.engine.connect() as conn:
        # Validate DC (customer_id=9)
        print("\n[Validating DC customer (customer_id=9)]")
        _validate_customer(conn, result, 9, 'dc', 'dc')

        # Validate SaaS (customer_id=1)
        print("\n[Validating SaaS customer (customer_id=1)]")
        _validate_customer(conn, result, 1, 'saas', 'saas')

        # Cross-customer isolation
        print("\n[Cross-customer isolation checks]")

        # No UUID collisions across ALL tables
        all_tables = [
            'customers', 'accounts', 'products', 'users', 'customer_configs',
            'kpi_uploads', 'kpis', 'health_trends', 'kpi_time_series',
            'kpi_reference_ranges', 'playbook_triggers', 'playbook_executions',
            'playbook_reports', 'feature_toggles', 'query_audits',
            'activity_logs', 'customer_workflow_configs', 'account_notes',
            'account_snapshots',
        ]
        for table in all_tables:
            try:
                dup_count = conn.execute(text(
                    f"SELECT COUNT(*) FROM ("
                    f"  SELECT uuid FROM {table} WHERE uuid IS NOT NULL "
                    f"  GROUP BY uuid HAVING COUNT(*) > 1"
                    f") dups"
                )).scalar()
                result.check(
                    f"Global: no duplicate uuids in {table}",
                    dup_count == 0,
                    f"{dup_count} duplicates"
                )
            except Exception:
                pass  # Table may not exist

        # Verify DC and SaaS uuids don't mix
        try:
            dc_in_saas = conn.execute(text(
                "SELECT COUNT(*) FROM accounts "
                "WHERE customer_id = 1 AND uuid IS NOT NULL AND uuid LIKE 'dc_%'"
            )).scalar()
            result.check(
                "No DC uuids in SaaS accounts",
                dc_in_saas == 0,
                f"{dc_in_saas} found"
            )

            saas_in_dc = conn.execute(text(
                "SELECT COUNT(*) FROM accounts "
                "WHERE customer_id = 9 AND uuid IS NOT NULL AND uuid LIKE 'saas_%'"
            )).scalar()
            result.check(
                "No SaaS uuids in DC accounts",
                saas_in_dc == 0,
                f"{saas_in_dc} found"
            )
        except Exception as e:
            result.check("Cross-vertical isolation", False, f"Error: {e}")

    return result


if __name__ == '__main__':
    from app_v3_minimal import app, db as app_db
    print("=" * 60)
    print("Phase 2b: Validate UUID Migration (ALL customers)")
    print("=" * 60)
    with app.app_context():
        result = run(app_db)
    print("\n" + "=" * 60)
    print(f"RESULT: {result.summary()}")
    if result.all_passed:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")
        for c in result.checks:
            if not c['passed']:
                print(f"  FAIL: {c['name']} -- {c['detail']}")
    print("=" * 60)
    sys.exit(0 if result.all_passed else 1)
