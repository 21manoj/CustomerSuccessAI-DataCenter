#!/usr/bin/env python3
"""
Migration: Add RBAC fields to users table
==========================================

Adds four new columns for contractor/tester access management:
  - allowed_account_ids  (JSON)    : restrict to specific accounts within a customer
  - allowed_customer_ids (JSON)    : restrict to specific customers (Test Runner)
  - expires_at           (TIMESTAMP): auto-expire contractor/tester access
  - is_contractor        (BOOLEAN)  : flag contractor vs regular user

Also migrates hardcoded Test Runner users to the database.

Usage:
    python -m migrations.add_user_rbac_fields
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Add RBAC columns to users table and migrate test runner users."""
    from extensions import db
    from app_v3_minimal import app

    with app.app_context():
        conn = db.engine.connect()

        # ── Step 1: Add columns (idempotent — skip if they exist) ──
        columns_to_add = [
            ("allowed_account_ids", "JSON"),
            ("allowed_customer_ids", "JSON"),
            ("expires_at", "TIMESTAMP"),
            ("is_contractor", "BOOLEAN DEFAULT FALSE"),
        ]

        for col_name, col_type in columns_to_add:
            try:
                conn.execute(db.text(
                    f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                ))
                conn.commit()
                print(f"  ✅ Added column: users.{col_name} ({col_type})")
            except Exception as e:
                conn.rollback()
                if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                    print(f"  ⏭️  Column users.{col_name} already exists, skipping")
                else:
                    print(f"  ⚠️  Error adding {col_name}: {e}")

        # ── Step 2: Migrate hardcoded Test Runner users to DB ──
        from werkzeug.security import generate_password_hash
        from models import User, Customer

        # Find the super admin's customer_id for tester user assignment
        super_admin = User.query.filter_by(role='super_admin').first()
        tester_customer_id = super_admin.customer_id if super_admin else 1

        test_runner_users = [
            {
                'email': 'tester@cspulse.com',
                'password': 'TestRunner2026!',
                'user_name': 'Test Runner',
                'role': 'tester',
            },
            {
                'email': 'qa@cspulse.com',
                'password': 'QATester2026!',
                'user_name': 'QA Tester',
                'role': 'tester',
            },
        ]

        for user_data in test_runner_users:
            existing = User.query.filter_by(email=user_data['email']).first()
            if existing:
                # Update role to 'tester' if not already
                if existing.role != 'tester':
                    existing.role = 'tester'
                    db.session.commit()
                    print(f"  ✅ Updated {user_data['email']} role to 'tester'")
                else:
                    print(f"  ⏭️  User {user_data['email']} already exists with role=tester")
            else:
                new_user = User(
                    customer_id=tester_customer_id,
                    user_name=user_data['user_name'],
                    email=user_data['email'],
                    password_hash=generate_password_hash(user_data['password']),
                    role=user_data['role'],
                    active=True,
                    vertical='dc2_s',
                    allowed_customer_ids=None,  # NULL = all customers (unrestricted)
                )
                db.session.add(new_user)
                db.session.commit()
                print(f"  ✅ Created tester user: {user_data['email']} (customer_id={tester_customer_id})")

        conn.close()
        print("\n✅ Migration complete: RBAC fields added + test runner users migrated")


if __name__ == '__main__':
    run_migration()
