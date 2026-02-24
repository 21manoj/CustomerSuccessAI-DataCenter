#!/usr/bin/env python3
"""
Fix dc2s_super@test.com login (create user or reset password so login works).

Login uses email + password_hash (pbkdf2:sha256). If the user was created
without that method or active=0, you get "Invalid email or password".
Run this from the backend directory (or with backend on PYTHONPATH).

  cd kpi-dashboard/backend && python scripts/fix_dc2s_super_login.py

Optional env: DC2S_SUPER_PASSWORD (default: DC2_Super_2024!)
"""

import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from dotenv import load_dotenv
load_dotenv()

EMAIL = "dc2s_super@test.com"
USERNAME = "dc2s_super"
CUSTOMER_ID = 5
# Must match app login check (pbkdf2:sha256)
HASH_METHOD = "pbkdf2:sha256"


def main():
    from werkzeug.security import generate_password_hash, check_password_hash
    from sqlalchemy import create_engine, text

    password = os.getenv("DC2S_SUPER_PASSWORD", "DC2_Super_2024!")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in .env")
        sys.exit(1)

    engine = create_engine(db_url)
    pw_hash = generate_password_hash(password, method=HASH_METHOD)

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT user_id, user_name, email, customer_id, active, password_hash FROM users WHERE email = :email"),
            {"email": EMAIL}
        ).fetchone()

        if row:
            # Verify current hash works
            if row.password_hash and check_password_hash(row.password_hash, password):
                if row.active in (True, 1):
                    print(f"OK: {EMAIL} already has correct password and active=1. No change.")
                    return
            print(f"Updating existing user {EMAIL} (user_id={row.user_id}): set password and active=1")
            conn.execute(
                text("""
                    UPDATE users SET password_hash = :pw, active = TRUE WHERE user_id = :uid
                """),
                {"pw": pw_hash, "uid": row.user_id}
            )
            conn.commit()
            print("Done. You can log in with:")
            print(f"  Email:    {EMAIL}")
            print(f"  Password: {password}")
            return

        # Create user
        print(f"Creating user {EMAIL} (customer_id={CUSTOMER_ID})")
        conn.execute(
            text("""
                INSERT INTO users (user_name, email, customer_id, password_hash, active)
                VALUES (:uname, :email, :cid, :pw, TRUE)
            """),
            {"uname": USERNAME, "email": EMAIL, "cid": CUSTOMER_ID, "pw": pw_hash}
        )
        conn.commit()
        print("Done. You can log in with:")
        print(f"  Email:    {EMAIL}")
        print(f"  Password: {password}")
        print("Note: Customer 5 will show data only if that customer has accounts in the DB (e.g. from onboarding/upload).")


if __name__ == "__main__":
    main()
