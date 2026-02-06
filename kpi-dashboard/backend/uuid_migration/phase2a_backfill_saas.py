#!/usr/bin/env python3
"""
Phase 2a: Backfill UUIDs for SaaS Customer (customer_id=1)

Same pattern as Phase 1b (DC backfill), but targets customer_id=1 (SaaS).

Prerequisites:
  - Phase 1a columns must exist (run phase1a_add_uuid_columns.py first)
  - Phase 1b (DC backfill) should be validated and working

Safety:
  - Only touches records where customer_id=1
  - Skips records that already have a uuid (idempotent)
  - Single transaction (all-or-nothing)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text

TARGET_CUSTOMER_ID = 1
TARGET_VERTICAL = 'saas'


def run(db):
    """
    Backfill UUIDs for customer_id=1 and all its children.
    Reuses the same logic as phase1b_backfill_dc.py but with different target.

    Returns:
        dict with per-table counts
    """
    # Reuse the same backfill helpers from phase1b
    from uuid_migration.phase1b_backfill_dc import (
        _backfill_simple_child, _backfill_account_child
    )
    from id_generator import generate_id

    stats = {}

    with db.engine.connect() as conn:
        trans = conn.begin()
        try:
            # ============================================================
            # Step 1: Customer itself
            # ============================================================
            print(f"\n[Step 1] Backfill customer (customer_id={TARGET_CUSTOMER_ID})")
            row = conn.execute(text(
                "SELECT customer_id, uuid FROM customers WHERE customer_id = :cid"
            ), {'cid': TARGET_CUSTOMER_ID}).fetchone()

            if not row:
                print(f"  ERROR: customer_id={TARGET_CUSTOMER_ID} not found!")
                trans.rollback()
                return {'error': f'customer_id={TARGET_CUSTOMER_ID} not found'}

            if row[1]:
                customer_uuid = row[1]
                print(f"  SKIP customer (already has uuid: {customer_uuid})")
            else:
                customer_uuid = generate_id(TARGET_VERTICAL, 'customer')
                conn.execute(text(
                    "UPDATE customers SET uuid = :uuid, vertical = :vert WHERE customer_id = :cid"
                ), {'uuid': customer_uuid, 'vert': TARGET_VERTICAL, 'cid': TARGET_CUSTOMER_ID})
                print(f"  SET  customer uuid={customer_uuid}, vertical={TARGET_VERTICAL}")
            stats['customers'] = 1

            # ============================================================
            # Step 2: Accounts
            # ============================================================
            print(f"\n[Step 2] Backfill accounts (customer_id={TARGET_CUSTOMER_ID})")
            accounts = conn.execute(text(
                "SELECT account_id, uuid FROM accounts WHERE customer_id = :cid"
            ), {'cid': TARGET_CUSTOMER_ID}).fetchall()

            account_uuid_map = {}
            count = 0
            for acct in accounts:
                acct_id, existing_uuid = acct[0], acct[1]
                if existing_uuid:
                    account_uuid_map[acct_id] = existing_uuid
                    continue
                new_uuid = generate_id(TARGET_VERTICAL, 'account')
                account_uuid_map[acct_id] = new_uuid
                conn.execute(text(
                    "UPDATE accounts SET uuid = :uuid, customer_uuid = :cuuid "
                    "WHERE account_id = :aid"
                ), {'uuid': new_uuid, 'cuuid': customer_uuid, 'aid': acct_id})
                count += 1

            conn.execute(text(
                "UPDATE accounts SET customer_uuid = :cuuid "
                "WHERE customer_id = :cid AND customer_uuid IS NULL"
            ), {'cuuid': customer_uuid, 'cid': TARGET_CUSTOMER_ID})

            print(f"  Backfilled {count} accounts ({len(accounts)} total)")
            stats['accounts'] = count

            # ============================================================
            # Step 3: Products
            # ============================================================
            print(f"\n[Step 3] Backfill products")
            products = conn.execute(text(
                "SELECT product_id, account_id, uuid FROM products WHERE customer_id = :cid"
            ), {'cid': TARGET_CUSTOMER_ID}).fetchall()

            count = 0
            for prod in products:
                prod_id, acct_id, existing_uuid = prod[0], prod[1], prod[2]
                if existing_uuid:
                    continue
                new_uuid = generate_id(TARGET_VERTICAL, 'product')
                acct_uuid = account_uuid_map.get(acct_id)
                conn.execute(text(
                    "UPDATE products SET uuid = :uuid, customer_uuid = :cuuid, account_uuid = :auuid "
                    "WHERE product_id = :pid"
                ), {'uuid': new_uuid, 'cuuid': customer_uuid, 'auuid': acct_uuid, 'pid': prod_id})
                count += 1
            print(f"  Backfilled {count} products ({len(products)} total)")
            stats['products'] = count

            # ============================================================
            # Step 4: Users
            # ============================================================
            print(f"\n[Step 4] Backfill users")
            users = conn.execute(text(
                "SELECT user_id, uuid FROM users WHERE customer_id = :cid"
            ), {'cid': TARGET_CUSTOMER_ID}).fetchall()

            user_uuid_map = {}
            count = 0
            for usr in users:
                uid, existing_uuid = usr[0], usr[1]
                if existing_uuid:
                    user_uuid_map[uid] = existing_uuid
                    continue
                new_uuid = generate_id(TARGET_VERTICAL, 'user')
                user_uuid_map[uid] = new_uuid
                conn.execute(text(
                    "UPDATE users SET uuid = :uuid, customer_uuid = :cuuid WHERE user_id = :uid"
                ), {'uuid': new_uuid, 'cuuid': customer_uuid, 'uid': uid})
                count += 1
            print(f"  Backfilled {count} users ({len(users)} total)")
            stats['users'] = count

            # ============================================================
            # Step 5: Customer Configs
            # ============================================================
            print(f"\n[Step 5] Backfill customer_configs")
            count = _backfill_simple_child(
                conn, 'customer_configs', 'config_id',
                TARGET_CUSTOMER_ID, customer_uuid, TARGET_VERTICAL, 'customer_config',
                generate_id
            )
            stats['customer_configs'] = count

            # ============================================================
            # Step 6: KPI Uploads
            # ============================================================
            print(f"\n[Step 6] Backfill kpi_uploads")
            uploads = conn.execute(text(
                "SELECT upload_id, account_id, uuid FROM kpi_uploads WHERE customer_id = :cid"
            ), {'cid': TARGET_CUSTOMER_ID}).fetchall()

            upload_uuid_map = {}
            count = 0
            for upl in uploads:
                upl_id, acct_id, existing_uuid = upl[0], upl[1], upl[2]
                if existing_uuid:
                    upload_uuid_map[upl_id] = existing_uuid
                    continue
                new_uuid = generate_id(TARGET_VERTICAL, 'upload')
                upload_uuid_map[upl_id] = new_uuid
                acct_uuid = account_uuid_map.get(acct_id)
                conn.execute(text(
                    "UPDATE kpi_uploads SET uuid = :uuid, customer_uuid = :cuuid, account_uuid = :auuid "
                    "WHERE upload_id = :uid"
                ), {'uuid': new_uuid, 'cuuid': customer_uuid, 'auuid': acct_uuid, 'uid': upl_id})
                count += 1
            print(f"  Backfilled {count} uploads ({len(uploads)} total)")
            stats['kpi_uploads'] = count

            # ============================================================
            # Step 7: KPIs
            # ============================================================
            print(f"\n[Step 7] Backfill kpis")
            kpis = conn.execute(text(
                "SELECT k.kpi_id, k.account_id, k.upload_id, k.product_id, k.uuid "
                "FROM kpis k JOIN accounts a ON k.account_id = a.account_id "
                "WHERE a.customer_id = :cid"
            ), {'cid': TARGET_CUSTOMER_ID}).fetchall()

            count = 0
            for kpi in kpis:
                kpi_id, acct_id, upl_id, prod_id, existing_uuid = kpi[0], kpi[1], kpi[2], kpi[3], kpi[4]
                if existing_uuid:
                    continue
                new_uuid = generate_id(TARGET_VERTICAL, 'kpi')
                acct_uuid = account_uuid_map.get(acct_id)
                upl_uuid = upload_uuid_map.get(upl_id)
                prod_uuid = None
                if prod_id:
                    prod_row = conn.execute(text(
                        "SELECT uuid FROM products WHERE product_id = :pid"
                    ), {'pid': prod_id}).fetchone()
                    prod_uuid = prod_row[0] if prod_row else None
                conn.execute(text(
                    "UPDATE kpis SET uuid = :uuid, account_uuid = :auuid, "
                    "upload_uuid = :uuuid, product_uuid = :puuid "
                    "WHERE kpi_id = :kid"
                ), {
                    'uuid': new_uuid, 'auuid': acct_uuid,
                    'uuuid': upl_uuid, 'puuid': prod_uuid, 'kid': kpi_id
                })
                count += 1
            print(f"  Backfilled {count} KPIs ({len(kpis)} total)")
            stats['kpis'] = count

            # ============================================================
            # Step 8: Health Trends
            # ============================================================
            print(f"\n[Step 8] Backfill health_trends")
            count = _backfill_account_child(
                conn, 'health_trends', 'trend_id',
                TARGET_CUSTOMER_ID, customer_uuid, account_uuid_map, TARGET_VERTICAL, 'health_trend',
                generate_id
            )
            stats['health_trends'] = count

            # ============================================================
            # Step 9: KPI Time Series
            # ============================================================
            print(f"\n[Step 9] Backfill kpi_time_series")
            ts_rows = conn.execute(text(
                "SELECT id, kpi_id, account_id, uuid FROM kpi_time_series WHERE customer_id = :cid"
            ), {'cid': TARGET_CUSTOMER_ID}).fetchall()

            count = 0
            for row in ts_rows:
                row_id, kpi_id, acct_id, existing_uuid = row[0], row[1], row[2], row[3]
                if existing_uuid:
                    continue
                new_uuid = generate_id(TARGET_VERTICAL, 'kpi_time_series')
                acct_uuid = account_uuid_map.get(acct_id)
                kpi_row = conn.execute(text(
                    "SELECT uuid FROM kpis WHERE kpi_id = :kid"
                ), {'kid': kpi_id}).fetchone()
                kpi_uuid = kpi_row[0] if kpi_row else None
                conn.execute(text(
                    "UPDATE kpi_time_series SET uuid = :uuid, kpi_uuid = :kuuid, "
                    "account_uuid = :auuid, customer_uuid = :cuuid WHERE id = :rid"
                ), {
                    'uuid': new_uuid, 'kuuid': kpi_uuid,
                    'auuid': acct_uuid, 'cuuid': customer_uuid, 'rid': row_id
                })
                count += 1
            print(f"  Backfilled {count} time series rows ({len(ts_rows)} total)")
            stats['kpi_time_series'] = count

            # ============================================================
            # Steps 10-18: Remaining tables
            # ============================================================
            simple_tables = [
                ('kpi_reference_ranges', 'range_id', 'kpi_reference_range'),
                ('playbook_triggers', 'trigger_id', 'playbook_trigger'),
                ('feature_toggles', 'id', 'feature_toggle'),
                ('query_audits', 'id', 'query_audit'),
                ('activity_logs', 'id', 'activity_log'),
                ('customer_workflow_configs', 'id', 'workflow_config'),
            ]
            for table, pk, entity in simple_tables:
                print(f"\n[Backfill {table}]")
                count = _backfill_simple_child(
                    conn, table, pk,
                    TARGET_CUSTOMER_ID, customer_uuid, TARGET_VERTICAL, entity,
                    generate_id
                )
                stats[table] = count

            account_tables = [
                ('playbook_executions', 'id', 'playbook_execution'),
                ('playbook_reports', 'report_id', 'playbook_report'),
                ('account_notes', 'note_id', 'account_note'),
                ('account_snapshots', 'snapshot_id', 'account_snapshot'),
            ]
            for table, pk, entity in account_tables:
                print(f"\n[Backfill {table}]")
                count = _backfill_account_child(
                    conn, table, pk,
                    TARGET_CUSTOMER_ID, customer_uuid, account_uuid_map, TARGET_VERTICAL, entity,
                    generate_id
                )
                stats[table] = count

            # ============================================================
            # Commit
            # ============================================================
            trans.commit()
            print("\n" + "=" * 60)
            print("COMMITTED - SaaS backfill applied successfully")
            print("=" * 60)

        except Exception as e:
            trans.rollback()
            print(f"\nROLLBACK - Error during SaaS backfill: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e), 'stats': stats}

    return stats


if __name__ == '__main__':
    from app_v3_minimal import app, db as app_db
    print("=" * 60)
    print(f"Phase 2a: Backfill UUIDs for customer_id={TARGET_CUSTOMER_ID} (SaaS)")
    print("=" * 60)
    with app.app_context():
        result = run(app_db)
    print(f"\nResult: {result}")
