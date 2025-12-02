#!/usr/bin/env python3
"""Create activity_logs table directly"""
from app_v3_minimal import app
from extensions import db

with app.app_context():
    # Check if table exists
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    
    if 'activity_logs' in existing_tables:
        print("✅ activity_logs table already exists")
    else:
        print("Creating activity_logs table...")
        from models import ActivityLog
        db.create_all()
        print("✅ activity_logs table created successfully!")

