#!/usr/bin/env python3
"""
Tier System Migration Script
==============================
Adds tier support to vertical_templates and partner_tier to customer_api_keys.

Changes:
  1. vertical_templates: add 'tier' column (VARCHAR(20), nullable, indexed)
  2. vertical_templates: replace unique constraint to include tier
  3. vertical_templates: backfill existing rows with tier='enterprise'
  4. customer_api_keys: add 'partner_tier' column (VARCHAR(30), nullable)

Usage:
  python scripts/migrate_tier_system.py
  python scripts/migrate_tier_system.py --dry-run

Safe: idempotent — checks for column existence before altering.
"""
import argparse
import sys

sys.path.insert(0, '.')
from app_v3_minimal import app
from models import db
from sqlalchemy import text, inspect


def column_exists(inspector, table_name, column_name):
    """Check if a column exists in a table."""
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def constraint_exists(inspector, table_name, constraint_name):
    """Check if a unique constraint exists."""
    constraints = inspector.get_unique_constraints(table_name)
    return any(c['name'] == constraint_name for c in constraints)


def run_migration(dry_run=False):
    with app.app_context():
        inspector = inspect(db.engine)

        changes = []

        # ================================================================
        # 1. Add 'tier' column to vertical_templates
        # ================================================================
        if not column_exists(inspector, 'vertical_templates', 'tier'):
            changes.append("ADD vertical_templates.tier VARCHAR(20)")
            if not dry_run:
                db.session.execute(text(
                    "ALTER TABLE vertical_templates ADD COLUMN tier VARCHAR(20)"
                ))
                db.session.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_vt_tier ON vertical_templates (tier)"
                ))
                print("  ✅ Added column vertical_templates.tier")
        else:
            print("  ⏭️  Column vertical_templates.tier already exists")

        # ================================================================
        # 2. Replace unique constraint to include tier
        # ================================================================
        old_constraint = 'uq_vt_vertical_type_ver'
        new_constraint = 'uq_vt_vertical_tier_type_ver'

        if constraint_exists(inspector, 'vertical_templates', old_constraint):
            changes.append(f"DROP CONSTRAINT {old_constraint}")
            if not dry_run:
                db.session.execute(text(
                    f"ALTER TABLE vertical_templates DROP CONSTRAINT {old_constraint}"
                ))
                print(f"  ✅ Dropped old constraint {old_constraint}")

        if not constraint_exists(inspector, 'vertical_templates', new_constraint):
            changes.append(f"ADD CONSTRAINT {new_constraint}")
            if not dry_run:
                db.session.execute(text(
                    f"ALTER TABLE vertical_templates ADD CONSTRAINT {new_constraint} "
                    f"UNIQUE (vertical, tier, config_type, version)"
                ))
                print(f"  ✅ Added new constraint {new_constraint}")
        else:
            print(f"  ⏭️  Constraint {new_constraint} already exists")

        # ================================================================
        # 3. Backfill existing rows: set tier='enterprise' where NULL
        # ================================================================
        # Refresh inspector after schema changes
        if not dry_run:
            result = db.session.execute(text(
                "UPDATE vertical_templates SET tier = 'enterprise' WHERE tier IS NULL"
            ))
            if result.rowcount > 0:
                print(f"  ✅ Backfilled {result.rowcount} rows with tier='enterprise'")
                changes.append(f"BACKFILL {result.rowcount} rows → tier='enterprise'")
            else:
                print("  ⏭️  No rows need backfilling")
        else:
            # In dry-run the tier column may not exist yet — estimate from total row count
            try:
                count = db.session.execute(text(
                    "SELECT COUNT(*) FROM vertical_templates WHERE tier IS NULL"
                )).scalar()
            except Exception:
                db.session.rollback()
                count = db.session.execute(text(
                    "SELECT COUNT(*) FROM vertical_templates"
                )).scalar()
            if count > 0:
                changes.append(f"Would backfill {count} rows → tier='enterprise'")

        # ================================================================
        # 4. Add 'partner_tier' column to customer_api_keys
        # ================================================================
        if column_exists(inspector, 'customer_api_keys', 'id'):
            # Table exists
            if not column_exists(inspector, 'customer_api_keys', 'partner_tier'):
                changes.append("ADD customer_api_keys.partner_tier VARCHAR(30)")
                if not dry_run:
                    db.session.execute(text(
                        "ALTER TABLE customer_api_keys ADD COLUMN partner_tier VARCHAR(30)"
                    ))
                    print("  ✅ Added column customer_api_keys.partner_tier")
            else:
                print("  ⏭️  Column customer_api_keys.partner_tier already exists")
        else:
            print("  ⚠️  Table customer_api_keys does not exist — skipping partner_tier")

        # ================================================================
        # 5. Add composite index for tier-aware template lookups
        # ================================================================
        if not dry_run:
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_vt_vertical_tier ON vertical_templates (vertical, tier)"
            ))
            print("  ✅ Ensured index idx_vt_vertical_tier exists")

        # Commit
        if not dry_run:
            db.session.commit()
            print(f"\n✅ Migration complete. {len(changes)} changes applied.")
        else:
            print(f"\n🔍 DRY RUN — {len(changes)} changes would be applied:")
            for c in changes:
                print(f"    • {c}")

        # Verify
        if not dry_run:
            inspector = inspect(db.engine)
            assert column_exists(inspector, 'vertical_templates', 'tier'), "tier column missing!"
            print("\n✅ Verification passed: tier column exists in vertical_templates")

            # Show current state
            rows = db.session.execute(text(
                "SELECT template_id, vertical, tier, config_type, is_active FROM vertical_templates ORDER BY template_id"
            )).fetchall()
            print(f"\nCurrent vertical_templates ({len(rows)} rows):")
            for r in rows:
                print(f"  id={r[0]} vertical={r[1]:<15} tier={r[2] or 'NULL':<15} config_type={r[3]:<25} active={r[4]}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Tier System Migration')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)
