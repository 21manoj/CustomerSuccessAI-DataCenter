#!/usr/bin/env python3
"""
Set or rotate a user's password by email (werkzeug hash, same as /api/register).

Run inside the platform container (from /app/backend):
  python3 scripts/set_user_password.py --email admin@example.com --password 'YourSecret!'

Or locally with DB URL:
  cd kpi-dashboard/backend && python3 scripts/set_user_password.py ...
"""
from __future__ import annotations

import argparse

from werkzeug.security import generate_password_hash

from app_v3_minimal import app
from extensions import db
from models import User


def main() -> int:
    p = argparse.ArgumentParser(description="Set user password_hash by email")
    p.add_argument("--email", required=True, help="User email (unique)")
    p.add_argument("--password", required=True, help="New plain-text password")
    args = p.parse_args()

    email = args.email.strip().lower()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            # Case-insensitive match for odd casing in DB
            user = User.query.filter(
                db.func.lower(User.email) == email
            ).first()
        if not user:
            print(f"No user found for email: {args.email}")
            return 1
        user.password_hash = generate_password_hash(args.password)
        db.session.commit()
        print(f"Updated password for user_id={user.user_id} email={user.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
