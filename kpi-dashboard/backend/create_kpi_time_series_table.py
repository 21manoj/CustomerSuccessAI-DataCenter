#!/usr/bin/env python3
"""
Create KPI time series table for storing monthly KPI data.
"""

from extensions import db
from models import KPITimeSeries

def create_kpi_time_series_table():
    """Create the kpi_time_series table in the database."""
    try:
        db.create_all()
        print("✅ Created kpi_time_series table successfully")
    except Exception as e:
        print(f"❌ Error creating kpi_time_series table: {e}")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        create_kpi_time_series_table()
