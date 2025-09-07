#!/usr/bin/env python3
"""
Script to create the kpi_reference_ranges table
"""

from extensions import db
from models import KPIReferenceRange
from app import app

def create_reference_ranges_table():
    """Create the kpi_reference_ranges table"""
    
    with app.app_context():
        # Create the table
        db.create_all()
        print("Created kpi_reference_ranges table")

if __name__ == "__main__":
    create_reference_ranges_table()
