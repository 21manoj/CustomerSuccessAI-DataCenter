#!/usr/bin/env python3
"""
Ensure customer 291 exists with admin user admin@sacme.com / test123.
Used by the load driver (scenarios run against customer 291 with this login).

Run from repo root:
  PYTHONPATH=kpi-dashboard/backend python3 kpi-dashboard/backend/scripts/seed_customer291_sacme.py

Or inside the platform container:
  docker exec cspulse-platform python3 -c "
  from scripts.seed_customer291_sacme import ensure_customer291_sacme
  from app_v3_minimal import app
  with app.app_context(): ensure_customer291_sacme()
  "
"""
from werkzeug.security import generate_password_hash
from sqlalchemy import text

from app_v3_minimal import app
from extensions import db
from models import Customer, CustomerConfig, User
import json


def ensure_customer291_sacme():
    """Ensure customer_id 291 exists and has user admin@sacme.com / test123."""
    customer_id = 291
    customer_name = "Sacme"
    domain = "sacme.com"
    admin_email = "admin@sacme.com"
    admin_password = "test123"
    user_name = "admin"

    cust = Customer.query.get(customer_id)
    if not cust:
        cust = Customer(
            customer_id=customer_id,
            customer_name=customer_name,
            email=admin_email,
            domain=domain,
        )
        db.session.add(cust)
        db.session.flush()
        # Ensure next serial for customers is past 291
        try:
            db.session.execute(text(
                "SELECT setval(pg_get_serial_sequence('customers', 'customer_id'), "
                "GREATEST(291, (SELECT COALESCE(MAX(customer_id), 1) FROM customers)))"
            ))
        except Exception:
            pass
        # Default config for customer 291
        cfg = CustomerConfig(
            customer_id=customer_id,
            vertical="dc2_s",
            kpi_upload_mode="account_rollup",
            category_weights=json.dumps({
                "Relationship Strength": 0.20,
                "Adoption & Engagement": 0.25,
                "Support & Experience": 0.20,
                "Product Value": 0.20,
                "Business Outcomes": 0.15,
            }),
        )
        db.session.add(cfg)
        db.session.flush()
        print(f"Created customer {customer_id} ({customer_name})")
    else:
        print(f"Customer {customer_id} already exists")

    user = User.query.filter_by(customer_id=customer_id).filter(
        (User.email == admin_email) | (User.user_name == user_name)
    ).first()
    if not user:
        user = User(
            customer_id=customer_id,
            user_name=user_name,
            email=admin_email,
            password_hash=generate_password_hash(admin_password),
            active=True,
        )
        db.session.add(user)
        print(f"Created user {admin_email} for customer {customer_id}")
    else:
        user.email = admin_email
        user.password_hash = generate_password_hash(admin_password)
        user.user_name = user_name
        user.active = True
        print(f"Updated user {admin_email} for customer {customer_id}")

    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        ensure_customer291_sacme()
