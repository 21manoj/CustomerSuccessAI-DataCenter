#!/usr/bin/env python3
"""
Utility to create a SaaS customer and an initial user.

Usage example:
  PYTHONPATH=. python3 backend/scripts/create_customer_and_user.py \\
      --customer "DCMarketPlace" --domain "dcmarketplace.com" \\
      --username "DCMP1" --email "dcmp1@dcmarketplace.com" --password "DCMP123"
"""
import argparse
from werkzeug.security import generate_password_hash

from app_v3_minimal import app
from models import db, Customer, CustomerConfig, User
import json


def ensure_customer_and_user(customer_name: str, domain: str, username: str, email: str, password: str):
    with app.app_context():
        cust = Customer.query.filter_by(customer_name=customer_name).first()
        if not cust:
            cust = Customer(customer_name=customer_name, email=email, domain=domain)
            db.session.add(cust)
            db.session.flush()
            # default config
            cfg = CustomerConfig(
                customer_id=cust.customer_id,
                kpi_upload_mode='account_rollup',
                category_weights=json.dumps({
                    'Relationship Strength': 0.20,
                    'Adoption & Engagement': 0.25,
                    'Support & Experience': 0.20,
                    'Product Value': 0.20,
                    'Business Outcomes': 0.15
                })
            )
            db.session.add(cfg)
            db.session.flush()
            print(f"✅ Created customer '{customer_name}' (id={cust.customer_id})")
        else:
            print(f"ℹ️  Customer '{customer_name}' already exists (id={cust.customer_id})")

        user = User.query.filter_by(customer_id=cust.customer_id, user_name=username).first()
        if not user:
            # ensure email unique
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                # tweak email if collision
                local, _, dom = email.partition('@')
                email = f"{local}+{cust.customer_id}@{dom or 'example.com'}"
            user = User(
                customer_id=cust.customer_id,
                user_name=username,
                email=email,
                password_hash=generate_password_hash(password),
                active=True
            )
            db.session.add(user)
            db.session.commit()
            print(f"✅ Created user '{username}' (id={user.user_id}) for customer '{customer_name}' with email {email}")
        else:
            print(f"ℹ️  User '{username}' already exists for customer '{customer_name}' (id={user.user_id})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--customer", required=True, help="Customer name")
    parser.add_argument("--domain", required=True, help="Customer email domain")
    parser.add_argument("--username", required=True, help="Username (unique within customer)")
    parser.add_argument("--email", required=True, help="User email (globally unique)")
    parser.add_argument("--password", required=True, help="User password (will be hashed)")
    args = parser.parse_args()
    ensure_customer_and_user(args.customer, args.domain, args.username, args.email, args.password)


if __name__ == "__main__":
    main()


