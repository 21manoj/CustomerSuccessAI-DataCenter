#!/usr/bin/env python3
"""
Migration: Admin UI + SaaS Premium Vertical
============================================
Adds:
  - customers.is_reference, customers.reference_for columns
  - users.role column (if not exists)
  - vertical_templates table
  - customer_vertical_configs table
  - account_config_overrides table
  - customer_licenses table
  - customer_api_keys table

Safe to re-run (checks for existence before creating).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from extensions import db
from sqlalchemy import inspect, text


def migrate():
    """Run the Admin UI + SaaS Premium migration."""
    with app.app_context():
        print("=" * 70)
        print("MIGRATION: Admin UI + SaaS Premium Vertical")
        print("=" * 70)
        print()

        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        # ------------------------------------------------------------------
        # Step 1: Add columns to 'customers' table
        # ------------------------------------------------------------------
        print("Step 1: Adding columns to 'customers' table...")
        if 'customers' in existing_tables:
            existing_cols = {c['name'] for c in inspector.get_columns('customers')}

            new_cols = {
                'is_reference': "BOOLEAN DEFAULT FALSE",
                'reference_for': "VARCHAR(30)",
            }
            for col_name, col_def in new_cols.items():
                if col_name not in existing_cols:
                    db.session.execute(text(
                        f"ALTER TABLE customers ADD COLUMN {col_name} {col_def}"
                    ))
                    print(f"  + Added customers.{col_name}")
                else:
                    print(f"  ✓ customers.{col_name} already exists")
            db.session.commit()
        else:
            print("  ⚠ 'customers' table not found")

        # ------------------------------------------------------------------
        # Step 2: Add 'role' column to 'users' table
        # ------------------------------------------------------------------
        print("\nStep 2: Adding 'role' column to 'users' table...")
        if 'users' in existing_tables:
            existing_cols = {c['name'] for c in inspector.get_columns('users')}
            if 'role' not in existing_cols:
                db.session.execute(text(
                    "ALTER TABLE users ADD COLUMN role VARCHAR(30) DEFAULT 'user'"
                ))
                print("  + Added users.role")
                db.session.commit()
            else:
                print("  ✓ users.role already exists")
        else:
            print("  ⚠ 'users' table not found")

        # ------------------------------------------------------------------
        # Step 3: Create 'vertical_templates' table
        # ------------------------------------------------------------------
        print("\nStep 3: Creating 'vertical_templates' table...")
        if 'vertical_templates' not in existing_tables:
            db.session.execute(text("""
                CREATE TABLE vertical_templates (
                    template_id SERIAL PRIMARY KEY,
                    vertical VARCHAR(50) NOT NULL,
                    config_type VARCHAR(50) NOT NULL,
                    config JSON NOT NULL DEFAULT '{}',
                    version VARCHAR(20) DEFAULT '1.0.0',
                    is_locked BOOLEAN DEFAULT FALSE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.execute(text("""
                CREATE INDEX idx_vt_vertical ON vertical_templates(vertical)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_vt_vertical_config ON vertical_templates(vertical, config_type)
            """))
            print("  + Created vertical_templates table")
            db.session.commit()
        else:
            print("  ✓ vertical_templates already exists")

        # ------------------------------------------------------------------
        # Step 4: Create 'customer_vertical_configs' table
        # ------------------------------------------------------------------
        print("\nStep 4: Creating 'customer_vertical_configs' table...")
        if 'customer_vertical_configs' not in existing_tables:
            db.session.execute(text("""
                CREATE TABLE customer_vertical_configs (
                    id SERIAL PRIMARY KEY,
                    customer_id INTEGER NOT NULL,
                    vertical VARCHAR(50) NOT NULL,
                    config_type VARCHAR(50) NOT NULL,
                    config JSON NOT NULL DEFAULT '{}',
                    merge_strategy VARCHAR(20) DEFAULT 'deep_merge',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            """))
            db.session.execute(text("""
                CREATE INDEX idx_cvc_customer ON customer_vertical_configs(customer_id)
            """))
            db.session.execute(text("""
                CREATE UNIQUE INDEX idx_cvc_unique
                ON customer_vertical_configs(customer_id, vertical, config_type)
            """))
            print("  + Created customer_vertical_configs table")
            db.session.commit()
        else:
            print("  ✓ customer_vertical_configs already exists")

        # ------------------------------------------------------------------
        # Step 5: Create 'account_config_overrides' table
        # ------------------------------------------------------------------
        print("\nStep 5: Creating 'account_config_overrides' table...")
        if 'account_config_overrides' not in existing_tables:
            db.session.execute(text("""
                CREATE TABLE account_config_overrides (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    customer_id INTEGER NOT NULL,
                    config_type VARCHAR(50) NOT NULL,
                    config JSON NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            """))
            db.session.execute(text("""
                CREATE INDEX idx_aco_account ON account_config_overrides(account_id)
            """))
            db.session.execute(text("""
                CREATE UNIQUE INDEX idx_aco_unique
                ON account_config_overrides(account_id, config_type)
            """))
            print("  + Created account_config_overrides table")
            db.session.commit()
        else:
            print("  ✓ account_config_overrides already exists")

        # ------------------------------------------------------------------
        # Step 6: Create 'customer_licenses' table
        # ------------------------------------------------------------------
        print("\nStep 6: Creating 'customer_licenses' table...")
        if 'customer_licenses' not in existing_tables:
            db.session.execute(text("""
                CREATE TABLE customer_licenses (
                    id SERIAL PRIMARY KEY,
                    customer_id INTEGER NOT NULL UNIQUE,
                    license_type VARCHAR(30) DEFAULT 'standard',
                    max_seats INTEGER DEFAULT 10,
                    max_accounts INTEGER,
                    license_start DATE,
                    license_end DATE,
                    auto_renew BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            """))
            print("  + Created customer_licenses table")
            db.session.commit()
        else:
            print("  ✓ customer_licenses already exists")

        # ------------------------------------------------------------------
        # Step 7: Create 'customer_api_keys' table
        # ------------------------------------------------------------------
        print("\nStep 7: Creating 'customer_api_keys' table...")
        if 'customer_api_keys' not in existing_tables:
            db.session.execute(text("""
                CREATE TABLE customer_api_keys (
                    id SERIAL PRIMARY KEY,
                    customer_id INTEGER NOT NULL,
                    created_by INTEGER,
                    key_prefix VARCHAR(20) NOT NULL,
                    key_hash VARCHAR(64) NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    scopes JSON DEFAULT '["read"]',
                    is_active BOOLEAN DEFAULT TRUE,
                    expires_at TIMESTAMP,
                    last_used_at TIMESTAMP,
                    last_used_ip VARCHAR(45),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            """))
            db.session.execute(text("""
                CREATE INDEX idx_cak_prefix ON customer_api_keys(key_prefix)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_cak_customer ON customer_api_keys(customer_id)
            """))
            print("  + Created customer_api_keys table")
            db.session.commit()
        else:
            print("  ✓ customer_api_keys already exists")

        # ------------------------------------------------------------------
        # Step 8: Seed SaaS Premium vertical templates
        # ------------------------------------------------------------------
        print("\nStep 8: Seeding SaaS Premium vertical templates...")
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM vertical_templates WHERE vertical = 'saas_premium'"
        ))
        count = result.scalar()
        if count == 0:
            from verticals.saas_premium.kpi_definitions import SAAS_PILLARS, SAAS_KPIS
            from verticals.saas_premium.pillar_weights import BOOTSTRAP_L2_WEIGHTS
            import json

            templates = [
                ('saas_premium', 'kpi_definitions', json.dumps({
                    'pillars': {pid: {'name': p['name'], 'weight_l2': p['weight_l2']}
                                for pid, p in SAAS_PILLARS.items()},
                    'kpi_count': len(SAAS_KPIS)
                }), '1.0.0', 'SaaS Premium KPI definitions with 35 KPIs across 5 pillars'),
                ('saas_premium', 'health_thresholds', json.dumps({
                    'healthy': {'min': 70},
                    'at_risk': {'min': 50},
                    'critical': {'min': 0}
                }), '1.0.0', 'Default health score thresholds for SaaS Premium'),
                ('saas_premium', 'default_weights', json.dumps(
                    BOOTSTRAP_L2_WEIGHTS
                ), '1.0.0', 'Default pillar weights for SaaS Premium'),
                ('saas_premium', 'playbooks', json.dumps({
                    'count': 8,
                    'includes_partner': True
                }), '1.0.0', 'SaaS Premium playbook definitions'),
            ]

            for vertical, config_type, config, version, desc in templates:
                db.session.execute(text("""
                    INSERT INTO vertical_templates (vertical, config_type, config, version, description)
                    VALUES (:v, :ct, CAST(:c AS json), :ver, :desc)
                """), {'v': vertical, 'ct': config_type, 'c': config, 'ver': version, 'desc': desc})

            db.session.commit()
            print(f"  + Seeded {len(templates)} SaaS Premium templates")
        else:
            print(f"  ✓ SaaS Premium templates already exist ({count} found)")

        # ------------------------------------------------------------------
        # Step 9: Seed DC2_S vertical templates (if missing)
        # ------------------------------------------------------------------
        print("\nStep 9: Seeding DC2_S vertical templates...")
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM vertical_templates WHERE vertical = 'dc2_s'"
        ))
        count = result.scalar()
        if count == 0:
            import json
            templates = [
                ('dc2_s', 'kpi_definitions', json.dumps({
                    'pillars': {'P1': 'AI & Analytics', 'P2': 'Cloud & Hybrid',
                                'P3': 'DevOps', 'P4': 'Experience', 'P5': 'Ops & Security'},
                    'kpi_count': 38
                }), '1.0.0', 'DC2_S KPI definitions with 38 KPIs across 5 pillars'),
                ('dc2_s', 'health_thresholds', json.dumps({
                    'healthy': {'min': 70},
                    'at_risk': {'min': 50},
                    'critical': {'min': 0}
                }), '1.0.0', 'Default health score thresholds for DC2_S'),
                ('dc2_s', 'default_weights', json.dumps({
                    'P1': 0.20, 'P2': 0.20, 'P3': 0.20, 'P4': 0.20, 'P5': 0.20
                }), '1.0.0', 'Default pillar weights for DC2_S'),
            ]

            for vertical, config_type, config, version, desc in templates:
                db.session.execute(text("""
                    INSERT INTO vertical_templates (vertical, config_type, config, version, description)
                    VALUES (:v, :ct, CAST(:c AS json), :ver, :desc)
                """), {'v': vertical, 'ct': config_type, 'c': config, 'ver': version, 'desc': desc})

            db.session.commit()
            print(f"  + Seeded {len(templates)} DC2_S templates")
        else:
            print(f"  ✓ DC2_S templates already exist ({count} found)")

        # ------------------------------------------------------------------
        # Step 10: Create super_admin user (if none exists)
        # ------------------------------------------------------------------
        print("\nStep 10: Ensuring super_admin user exists...")
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM users WHERE role = 'super_admin'"
        ))
        admin_count = result.scalar()
        if admin_count == 0:
            from werkzeug.security import generate_password_hash
            # Get the first customer
            result = db.session.execute(text(
                "SELECT customer_id FROM customers ORDER BY customer_id LIMIT 1"
            ))
            row = result.fetchone()
            if row:
                cust_id = row[0]
                pw_hash = generate_password_hash('Admin123!')
                db.session.execute(text("""
                    INSERT INTO users (customer_id, user_name, email, password_hash, role, active)
                    VALUES (:cid, 'Platform Admin', 'superadmin@cspulse.com', :pw, 'super_admin', TRUE)
                """), {'cid': cust_id, 'pw': pw_hash})
                db.session.commit()
                print(f"  + Created super_admin: superadmin@cspulse.com (customer_id={cust_id})")
                print(f"    Password: Admin123!")
            else:
                print("  ⚠ No customers found — cannot create super_admin")
        else:
            print(f"  ✓ {admin_count} super_admin user(s) already exist")

        # ------------------------------------------------------------------
        # Done
        # ------------------------------------------------------------------
        print()
        print("=" * 70)
        print("MIGRATION COMPLETE")
        print("=" * 70)
        print()
        print("New tables: vertical_templates, customer_vertical_configs,")
        print("            account_config_overrides, customer_licenses, customer_api_keys")
        print("New columns: customers.is_reference, customers.reference_for, users.role")
        print()


if __name__ == '__main__':
    migrate()
