#!/usr/bin/env python3
"""
List Users and Customer Data Counts
====================================
Shows which login emails are tied to which customer_id and whether that
customer has accounts/KPIs in the database. Use this to see why a login
(e.g. demo@cspulse.ai) returns zero records.

Usage (from backend directory):
  python scripts/list_users_and_customer_data.py
  python scripts/list_users_and_customer_data.py --csv   # one-line summary

Requires: DATABASE_URL in .env
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from dotenv import load_dotenv
load_dotenv()

def main():
    from sqlalchemy import create_engine, text
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in .env")
        sys.exit(1)
    engine = create_engine(db_url)
    csv_mode = "--csv" in sys.argv

    with engine.connect() as conn:
        # All users with customer info
        users = conn.execute(text("""
            SELECT u.user_id, u.user_name, u.email, u.customer_id, u.vertical,
                   c.customer_name
            FROM users u
            LEFT JOIN customers c ON c.customer_id = u.customer_id
            ORDER BY u.customer_id, u.email
        """)).fetchall()

        if not users:
            print("No users found in database.")
            return

        # Account counts per customer
        acct = conn.execute(text("""
            SELECT customer_id, COUNT(*) AS cnt
            FROM accounts
            GROUP BY customer_id
        """)).fetchall()
        acct_by_cust = {r.customer_id: r.cnt for r in acct}

        # DC2S KPI counts per customer (via accounts) - table may not exist in all DBs
        dc2s_by_cust = {}
        try:
            dc2s = conn.execute(text("""
                SELECT a.customer_id, COUNT(k.id) AS cnt
                FROM dc2s_kpis k
                JOIN accounts a ON a.account_id = k.account_id
                GROUP BY a.customer_id
            """)).fetchall()
            dc2s_by_cust = {r.customer_id: r.cnt for r in dc2s}
        except Exception:
            pass

        if csv_mode:
            print("email,customer_id,customer_name,accounts,dc2s_kpis,has_data")
            for u in users:
                cid = u.customer_id
                ac = acct_by_cust.get(cid) or 0
                dk = dc2s_by_cust.get(cid) or 0
                has = "yes" if (ac or dk) else "no"
                print(f"{u.email},{cid},{u.customer_name or ''},{ac},{dk},{has}")
            return

        print("=" * 72)
        print("USERS AND CUSTOMER DATA")
        print("=" * 72)
        print()
        for u in users:
            cid = u.customer_id
            ac = acct_by_cust.get(cid) or 0
            dk = dc2s_by_cust.get(cid) or 0
            has_data = ac > 0 or dk > 0
            status = "HAS DATA" if has_data else "ZERO RECORDS"
            print(f"  Email:       {u.email}")
            print(f"  User name:   {u.user_name}")
            print(f"  Customer ID: {cid}  ({u.customer_name or 'no customer name'})")
            print(f"  Vertical:    {u.vertical or '(not set)'}")
            print(f"  Accounts:   {ac}  |  DC2S KPIs: {dk}  ->  {status}")
            print()
        print("=" * 72)
        print("CUSTOMERS WITH DATA (no user listed above = no login for that customer)")
        print("=" * 72)
        all_cust_with_accts = set(acct_by_cust.keys()) | set(dc2s_by_cust.keys())
        for cid in sorted(all_cust_with_accts):
            ac = acct_by_cust.get(cid) or 0
            dk = dc2s_by_cust.get(cid) or 0
            names = [u.email for u in users if u.customer_id == cid]
            logins = ", ".join(names) if names else "(no user)"
            print(f"  Customer {cid}: accounts={ac}, dc2s_kpis={dk}  Logins: {logins}")
        print()
        print("To get data for a login: run the load script for that customer_id, e.g.")
        print("  cd verticals/customer19-dc2_s/scripts && python 02_load_customer19_data_SMART.py")
        print("Then either use a user already tied to that customer_id or update the user's customer_id.")
        print("See README_DEMO_LOGINS.md for which logins are pre-configured.")
        print()

if __name__ == "__main__":
    main()
