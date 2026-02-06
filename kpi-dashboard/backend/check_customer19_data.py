#!/usr/bin/env python3
"""Check Customer 19 data in database"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import Customer, Account, KPIUpload
from sqlalchemy import text

with app.app_context():
    print("=" * 70)
    print("CUSTOMER 19 DATA CHECK")
    print("=" * 70)
    
    # Check all customers
    print("\n=== ALL CUSTOMERS ===")
    customers = Customer.query.all()
    for c in customers:
        print(f"ID: {c.customer_id:3d} | Name: {c.customer_name:30s} | Email: {c.email}")
    
    # Check customer 16 specifically
    print("\n=== CUSTOMER 16 (Synthetic Data Corp) ===")
    c16 = Customer.query.filter_by(customer_id=16).first()
    if c16:
        print(f"Found: {c16.customer_name}")
        accts_16 = Account.query.filter_by(customer_id=16).all()
        print(f"Accounts with customer_id=16: {len(accts_16)}")
        if accts_16:
            print("  Account IDs:", [a.account_id for a in accts_16[:5]])
    else:
        print("Not found")
    
    # Check customer 19 specifically
    print("\n=== CUSTOMER 19 ===")
    c19 = Customer.query.filter_by(customer_id=19).first()
    if c19:
        print(f"Found: {c19.customer_name}")
        accts_19 = Account.query.filter_by(customer_id=19).all()
        print(f"Accounts with customer_id=19: {len(accts_19)}")
        if accts_19:
            print("  Account IDs:", [a.account_id for a in accts_19[:5]])
    else:
        print("Customer 19 record not found in database")
    
    # Check accounts with customer_id=19 (from CSV)
    print("\n=== ACCOUNTS WITH customer_id=19 (from CSV) ===")
    accts_csv = db.session.execute(
        text("SELECT COUNT(*) FROM accounts WHERE customer_id = 19")
    ).scalar()
    print(f"Total accounts with customer_id=19: {accts_csv}")
    
    if accts_csv > 0:
        sample = db.session.execute(
            text("SELECT account_id, account_name FROM accounts WHERE customer_id = 19 LIMIT 5")
        ).fetchall()
        print("Sample accounts:")
        for row in sample:
            print(f"  {row[0]}: {row[1]}")
    
    # Check KPI uploads
    print("\n=== KPI UPLOADS ===")
    uploads_16 = KPIUpload.query.filter_by(customer_id=16).all()
    uploads_19 = KPIUpload.query.filter_by(customer_id=19).all()
    print(f"KPI uploads for customer_id=16: {len(uploads_16)}")
    print(f"KPI uploads for customer_id=19: {len(uploads_19)}")
    
    # Check account_id range 29001-29020
    print("\n=== ACCOUNTS IN RANGE 29001-29020 (Customer 19 expected) ===")
    accts_range = db.session.execute(
        text("SELECT customer_id, COUNT(*) FROM accounts WHERE account_id BETWEEN 29001 AND 29020 GROUP BY customer_id")
    ).fetchall()
    for row in accts_range:
        print(f"customer_id={row[0]}: {row[1]} accounts")
