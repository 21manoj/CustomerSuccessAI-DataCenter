#!/usr/bin/env python3
"""Seed customer 291 (admin@loadtest.com / test123) for load driver. Run from /app/backend in platform container."""
from werkzeug.security import generate_password_hash
from sqlalchemy import text
from app_v3_minimal import app
from extensions import db
from models import Customer, CustomerConfig, User
import json

with app.app_context():
    cid, email, pw = 291, "admin@loadtest.com", "test123"
    cust = Customer.query.get(cid)
    if not cust:
        cust = Customer(customer_id=cid, customer_name="LoadTest-291", email=email, domain="loadtest.com")
        db.session.add(cust)
        db.session.flush()
        try:
            db.session.execute(text(
                "SELECT setval(pg_get_serial_sequence('customers', 'customer_id'), "
                "GREATEST(291, (SELECT COALESCE(MAX(customer_id), 1) FROM customers)))"
            ))
        except Exception:
            pass
        cfg = CustomerConfig(
            customer_id=cid,
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
    else:
        cust.email, cust.customer_name, cust.domain = email, "LoadTest-291", "loadtest.com"
    user = User.query.filter_by(customer_id=cid).filter(
        (User.email == email) | (User.user_name == "admin")
    ).first()
    if not user:
        user = User(
            customer_id=cid,
            user_name="admin",
            email=email,
            password_hash=generate_password_hash(pw),
            active=True,
        )
        db.session.add(user)
    else:
        user.email, user.password_hash, user.user_name, user.active = (
            email, generate_password_hash(pw), "admin", True
        )
    db.session.commit()
    print("Customer 291 and admin@loadtest.com ready")
