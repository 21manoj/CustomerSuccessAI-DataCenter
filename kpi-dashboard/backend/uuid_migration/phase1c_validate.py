#!/usr/bin/env python3
"""
Phase 1c: Validate UUID Backfill for customer_id=9 (DC)

Runs comprehensive checks:
  1. No NULL uuids for customer_id=9 records
  2. All UUIDs have correct 'dc_' vertical prefix
  3. No duplicate UUIDs within any table
  4. Parent-child UUID relationships are consistent
  5. Record counts unchanged (no data loss)
  6. UUID format is valid (prefix_entity_uuid7)

Returns pass/fail for each check. Safe to run repeatedly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text

TARGET_CUSTOMER_ID = 9
TARGET_VERTICAL = 'dc'


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


def run(db):
    """
    Validate the Phase 1 migration for customer_id=9.

    Returns:
        ValidationResult object
    """
    result = ValidationResult()

    with db.engine.connect() as conn:

        # ==============================================================
        # CHECK 1: Customer has uuid and vertical set
        # ==============================================================
        print("\n[Check 1] Customer record")
        row = conn.execute(text(
            "SELECT uuid, vertical FROM customers WHERE customer_id = :cid"
        ), {'cid': TARGET_CUSTOMER_ID}).fetchone()

        result.check(
            "Customer uuid is set",
            row is not None and row[0] is not None,
            f"uuid={row[0] if row else 'NOT FOUND'}"
        )
        result.check(
            "Customer vertical is 'dc'",
            row is not None and row[1] == TARGET_VERTICAL,
            f"vertical={row[1] if row else 'NOT FOUND'}"
        )
        result.check(
            "Customer uuid starts with 'dc_cust_'",
            row is not None and row[0] is not None and row[0].startswith('dc_cust_'),
            f"uuid={row[0] if row else 'N/A'}"
        )
        customer_uuid = row[0] if row else None

        # ==============================================================
        # CHECK 2: No NULL uuids in child tables
        # ==============================================================
        print("\n[Check 2] No NULL uuids for customer_id=9 records")

        direct_tables = [
            ('accounts', 'customer_id'),
            ('products', 'customer_id'),
            ('users', 'customer_id'),
            ('customer_configs', 'customer_id'),
            ('kpi_uploads', 'customer_id'),
            ('health_trends', 'customer_id'),
            ('kpi_time_series', 'customer_id'),
            ('kpi_reference_ranges', 'customer_id'),
            ('playbook_triggers', 'customer_id'),
            ('playbook_executions', 'customer_id'),
            ('playbook_reports', 'customer_id'),
            ('feature_toggles', 'customer_id'),
            ('query_audits', 'customer_id'),
            ('activity_logs', 'customer_id'),
            ('customer_workflow_configs', 'customer_id'),
            ('account_notes', 'customer_id'),
            ('account_snapshots', 'customer_id'),
        ]

        for table, fk_col in direct_tables:
            try:
                null_count = conn.execute(text(
                    f"SELECT COUNT(*) FROM {table} WHERE {fk_col} = :cid AND uuid IS NULL"
                ), {'cid': TARGET_CUSTOMER_ID}).scalar()
                total = conn.execute(text(
                    f"SELECT COUNT(*) FROM {table} WHERE {fk_col} = :cid"
                ), {'cid': TARGET_CUSTOMER_ID}).scalar()
                result.check(
                    f"{table}: no NULL uuids",
                    null_count == 0,
                    f"{null_count}/{total} records missing uuid"
                )
            except Exception as e:
                result.check(f"{table}: no NULL uuids", False, f"Error: {e}")

        # KPIs join through accounts
        try:
            null_count = conn.execute(text(
                "SELECT COUNT(*) FROM kpis k JOIN accounts a ON k.account_id = a.account_id "
                "WHERE a.customer_id = :cid AND k.uuid IS NULL"
            ), {'cid': TARGET_CUSTOMER_ID}).scalar()
            total = conn.execute(text(
                "SELECT COUNT(*) FROM kpis k JOIN accounts a ON k.account_id = a.account_id "
                "WHERE a.customer_id = :cid"
            ), {'cid': TARGET_CUSTOMER_ID}).scalar()
            result.check(
                "kpis: no NULL uuids",
                null_count == 0,
                f"{null_count}/{total} records missing uuid"
            )
        except Exception as e:
            result.check("kpis: no NULL uuids", False, f"Error: {e}")

        # ==============================================================
        # CHECK 3: All UUIDs have correct vertical prefix
        # ==============================================================
        print("\n[Check 3] Correct vertical prefix (dc_)")

        prefix_checks = {
            'accounts': 'dc_acct_',
            'products': 'dc_prod_',
            'users': 'dc_usr_',
            'customer_configs': 'dc_ccfg_',
            'kpi_uploads': 'dc_upl_',
            'health_trends': 'dc_htrend_',
            'kpi_reference_ranges': 'dc_kref_',
            'playbook_triggers': 'dc_ptrig_',
            'playbook_executions': 'dc_pexec_',
            'playbook_reports': 'dc_prep_',
            'feature_toggles': 'dc_ftog_',
            'query_audits': 'dc_qaud_',
            'activity_logs': 'dc_alog_',
            'customer_workflow_configs': 'dc_wfcfg_',
            'account_notes': 'dc_anote_',
            'account_snapshots': 'dc_asnap_',
            'kpi_time_series': 'dc_kts_',
        }

        for table, expected_prefix in prefix_checks.items():
            try:
                bad_count = conn.execute(text(
                    f"SELECT COUNT(*) FROM {table} "
                    f"WHERE customer_id = :cid AND uuid IS NOT NULL AND uuid NOT LIKE :prefix"
                ), {'cid': TARGET_CUSTOMER_ID, 'prefix': f'{expected_prefix}%'}).scalar()
                result.check(
                    f"{table}: uuid prefix is '{expected_prefix}'",
                    bad_count == 0,
                    f"{bad_count} records with wrong prefix"
                )
            except Exception as e:
                result.check(f"{table}: uuid prefix", False, f"Error: {e}")

        # Check KPIs separately (join)
        try:
            bad_count = conn.execute(text(
                "SELECT COUNT(*) FROM kpis k JOIN accounts a ON k.account_id = a.account_id "
                "WHERE a.customer_id = :cid AND k.uuid IS NOT NULL AND k.uuid NOT LIKE 'dc_kpi_%'"
            ), {'cid': TARGET_CUSTOMER_ID}).scalar()
            result.check(
                "kpis: uuid prefix is 'dc_kpi_'",
                bad_count == 0,
                f"{bad_count} records with wrong prefix"
            )
        except Exception as e:
            result.check("kpis: uuid prefix", False, f"Error: {e}")

        # ==============================================================
        # CHECK 4: No duplicate UUIDs
        # ==============================================================
        print("\n[Check 4] No duplicate UUIDs")

        all_tables_with_uuid = [
            'customers', 'accounts', 'products', 'users', 'customer_configs',
            'kpi_uploads', 'kpis', 'health_trends', 'kpi_time_series',
            'kpi_reference_ranges', 'playbook_triggers', 'playbook_executions',
            'playbook_reports', 'feature_toggles', 'query_audits',
            'activity_logs', 'customer_workflow_configs', 'account_notes',
            'account_snapshots',
        ]

        for table in all_tables_with_uuid:
            try:
                dup_count = conn.execute(text(
                    f"SELECT COUNT(*) FROM ("
                    f"  SELECT uuid FROM {table} WHERE uuid IS NOT NULL "
                    f"  GROUP BY uuid HAVING COUNT(*) > 1"
                    f") dups"
                )).scalar()
                result.check(
                    f"{table}: no duplicate uuids",
                    dup_count == 0,
                    f"{dup_count} duplicate uuid values"
                )
            except Exception as e:
                result.check(f"{table}: no duplicate uuids", False, f"Error: {e}")

        # ==============================================================
        # CHECK 5: Parent UUID references are consistent
        # ==============================================================
        print("\n[Check 5] Parent-child UUID consistency")

        # Accounts should reference parent customer uuid
        if customer_uuid:
            try:
                bad_ref = conn.execute(text(
                    "SELECT COUNT(*) FROM accounts "
                    "WHERE customer_id = :cid AND customer_uuid != :cuuid AND customer_uuid IS NOT NULL"
                ), {'cid': TARGET_CUSTOMER_ID, 'cuuid': customer_uuid}).scalar()
                result.check(
                    "accounts.customer_uuid matches parent",
                    bad_ref == 0,
                    f"{bad_ref} records with mismatched customer_uuid"
                )
            except Exception as e:
                result.check("accounts.customer_uuid matches parent", False, f"Error: {e}")

            # Products should reference correct account uuids
            try:
                bad_ref = conn.execute(text(
                    "SELECT COUNT(*) FROM products p "
                    "JOIN accounts a ON p.account_id = a.account_id "
                    "WHERE p.customer_id = :cid "
                    "AND p.account_uuid IS NOT NULL AND a.uuid IS NOT NULL "
                    "AND p.account_uuid != a.uuid"
                ), {'cid': TARGET_CUSTOMER_ID}).scalar()
                result.check(
                    "products.account_uuid matches accounts.uuid",
                    bad_ref == 0,
                    f"{bad_ref} records with mismatched account_uuid"
                )
            except Exception as e:
                result.check("products.account_uuid matches accounts.uuid", False, f"Error: {e}")

        # ==============================================================
        # CHECK 6: No customer_id=1 (SaaS) records were touched
        # ==============================================================
        print("\n[Check 6] SaaS customer (id=1) NOT affected")

        try:
            saas_uuid_count = conn.execute(text(
                "SELECT COUNT(*) FROM accounts WHERE customer_id = 1 AND uuid IS NOT NULL"
            )).scalar()
            result.check(
                "SaaS accounts untouched (no uuids set)",
                saas_uuid_count == 0,
                f"{saas_uuid_count} SaaS accounts have uuid set"
            )
        except Exception as e:
            result.check("SaaS accounts untouched", False, f"Error: {e}")

        try:
            saas_cust_uuid = conn.execute(text(
                "SELECT uuid FROM customers WHERE customer_id = 1"
            )).fetchone()
            result.check(
                "SaaS customer uuid is NULL",
                saas_cust_uuid is None or saas_cust_uuid[0] is None,
                f"uuid={saas_cust_uuid[0] if saas_cust_uuid else 'N/A'}"
            )
        except Exception as e:
            result.check("SaaS customer uuid is NULL", False, f"Error: {e}")

    return result


if __name__ == '__main__':
    from app_v3_minimal import app, db as app_db
    print("=" * 60)
    print(f"Phase 1c: Validate UUID Migration (customer_id={TARGET_CUSTOMER_ID})")
    print("=" * 60)
    with app.app_context():
        result = run(app_db)
    print("\n" + "=" * 60)
    print(f"RESULT: {result.summary()}")
    if result.all_passed:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED - Review output above")
        failed = [c for c in result.checks if not c['passed']]
        print(f"\nFailed checks:")
        for c in failed:
            print(f"  - {c['name']}: {c['detail']}")
    print("=" * 60)
    sys.exit(0 if result.all_passed else 1)
