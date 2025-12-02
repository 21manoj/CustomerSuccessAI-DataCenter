#!/usr/bin/env python3
"""
Migration script to add OpenAI API key columns to customer_configs table.
Run this once to update the database schema.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db
from models import CustomerConfig

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def migrate():
    """Add OpenAI API key columns to customer_configs table"""
    print("\n" + "="*70)
    print("MIGRATING: Adding OpenAI API Key Support")
    print("="*70)
    
    with app.app_context():
        try:
            # Check if columns already exist
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('customer_configs')]
            
            if 'openai_api_key_encrypted' in columns:
                print("\n✅ Columns already exist. Migration not needed.")
                return True
            
            # Add new columns
            print("\n📝 Adding columns to customer_configs table...")
            db.session.execute(text("""
                ALTER TABLE customer_configs 
                ADD COLUMN openai_api_key_encrypted TEXT
            """))
            db.session.execute(text("""
                ALTER TABLE customer_configs 
                ADD COLUMN openai_api_key_updated_at DATETIME
            """))
            db.session.commit()
            
            print("✅ Migration completed successfully!")
            print("\n📋 New columns added:")
            print("   - openai_api_key_encrypted (TEXT)")
            print("   - openai_api_key_updated_at (DATETIME)")
            print("\n💡 Customers can now set their OpenAI API keys in Settings")
            print("   without requiring a server restart!")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)

