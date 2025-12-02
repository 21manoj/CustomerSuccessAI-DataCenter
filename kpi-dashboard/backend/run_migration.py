#!/usr/bin/env python3
"""Run database migration"""
from app_v3_minimal import app
from flask_migrate import upgrade

with app.app_context():
    print("Running database migration...")
    upgrade()
    print("✅ Migration complete!")
