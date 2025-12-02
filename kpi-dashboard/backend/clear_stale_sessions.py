#!/usr/bin/env python3
"""
Clear Stale Sessions

This script clears all sessions from the database to force fresh logins.
Useful when customer_id or user data has changed.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from extensions import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def clear_sessions():
    """Clear all sessions from the database"""
    print("\n" + "="*70)
    print("CLEARING STALE SESSIONS")
    print("="*70)
    
    with app.app_context():
        try:
            # Check if sessions table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'sessions' not in tables:
                print("\n⚠️  Sessions table does not exist (using in-memory sessions)")
                print("   Sessions will be cleared on server restart")
                return True
            
            # Clear all sessions
            result = db.session.execute(db.text("DELETE FROM sessions"))
            db.session.commit()
            
            deleted_count = result.rowcount
            print(f"\n✅ Cleared {deleted_count} stale sessions")
            print(f"   Users will need to log in again")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error clearing sessions: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = clear_sessions()
    sys.exit(0 if success else 1)

