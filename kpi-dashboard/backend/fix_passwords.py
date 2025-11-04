#!/usr/bin/env python3
"""
Script to fix password hashing compatibility issues.
Converts scrypt hashes to pbkdf2:sha256 hashes.
"""

import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

def fix_passwords():
    """Convert scrypt passwords to pbkdf2:sha256"""
    
    # Database path
    if os.path.exists('/app/instance'):
        db_path = '/app/instance/kpi_dashboard.db'
    else:
        basedir = os.path.abspath(os.path.dirname(__file__))
        instance_path = os.path.join(os.path.dirname(basedir), 'instance')
        db_path = os.path.join(instance_path, 'kpi_dashboard.db')
    
    print(f"Using database: {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all users with scrypt passwords
    cursor.execute("SELECT user_id, email, password_hash FROM users WHERE password_hash LIKE 'scrypt:%'")
    users = cursor.fetchall()
    
    print(f"Found {len(users)} users with scrypt passwords")
    
    # Known passwords (for demo purposes)
    known_passwords = {
        'test@test.com': 'test123',
        'acme@acme.com': 'acme123'
    }
    
    for user_id, email, old_hash in users:
        if email in known_passwords:
            password = known_passwords[email]
            # Generate new pbkdf2:sha256 hash
            new_hash = generate_password_hash(password, method='pbkdf2:sha256')
            
            # Update the database
            cursor.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (new_hash, user_id))
            print(f"Updated password for {email}")
        else:
            print(f"Skipping {email} - no known password")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print("Password fix completed!")

if __name__ == '__main__':
    fix_passwords()
