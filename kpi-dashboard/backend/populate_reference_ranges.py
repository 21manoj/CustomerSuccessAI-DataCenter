#!/usr/bin/env python3
"""
Script to populate KPI reference ranges from health_score_config.py into the database
"""

from extensions import db
from models import KPIReferenceRange
from health_score_config import KPI_REFERENCE_RANGES
from app import app

def populate_reference_ranges():
    """Populate the database with KPI reference ranges from config"""
    
    with app.app_context():
        # Clear existing ranges
        KPIReferenceRange.query.delete()
        print("Cleared existing reference ranges")
        
        # Populate with current ranges
        for kpi_name, config in KPI_REFERENCE_RANGES.items():
            ranges = config['ranges']
            
            # Create new reference range record
            ref_range = KPIReferenceRange(
                kpi_name=kpi_name,
                unit=config['unit'],
                higher_is_better=config['higher_is_better'],
                
                # Critical range (low performance)
                critical_min=ranges['low']['min'],
                critical_max=ranges['low']['max'],
                
                # Risk range (medium performance)
                risk_min=ranges['medium']['min'],
                risk_max=ranges['medium']['max'],
                
                # Healthy range (high performance)
                healthy_min=ranges['high']['min'],
                healthy_max=ranges['high']['max']
            )
            
            db.session.add(ref_range)
        
        # Commit all changes
        db.session.commit()
        print(f"Successfully populated {len(KPI_REFERENCE_RANGES)} KPI reference ranges")
        
        # Verify the data
        count = KPIReferenceRange.query.count()
        print(f"Database now contains {count} reference ranges")

if __name__ == "__main__":
    populate_reference_ranges()
