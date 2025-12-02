#!/usr/bin/env python3
"""
Validation script to check if OpenAI API key support is properly configured
Run this on startup to ensure the model and database are ready
"""

import os
import sys

def validate_openai_key_support():
    """Validate that OpenAI API key support is properly configured"""
    errors = []
    warnings = []
    
    # Check 1: Model has required attributes
    try:
        from models import CustomerConfig
        if not hasattr(CustomerConfig, 'openai_api_key_encrypted'):
            errors.append("CustomerConfig model missing 'openai_api_key_encrypted' attribute")
        if not hasattr(CustomerConfig, 'openai_api_key_updated_at'):
            errors.append("CustomerConfig model missing 'openai_api_key_updated_at' attribute")
    except Exception as e:
        errors.append(f"Failed to import CustomerConfig model: {e}")
    
    # Check 2: Database has required columns (if we can access it)
    try:
        from extensions import db
        from flask import Flask
        
        # Only check if we have a database connection
        app = Flask(__name__)
        db_path = os.path.join(os.path.dirname(__file__), 'instance', 'kpi_dashboard.db')
        if os.path.exists(db_path):
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            db.init_app(app)
            
            with app.app_context():
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                try:
                    columns = [col['name'] for col in inspector.get_columns('customer_configs')]
                    if 'openai_api_key_encrypted' not in columns:
                        warnings.append("Database table 'customer_configs' missing 'openai_api_key_encrypted' column - run migration")
                    if 'openai_api_key_updated_at' not in columns:
                        warnings.append("Database table 'customer_configs' missing 'openai_api_key_updated_at' column - run migration")
                except Exception as e:
                    # Table might not exist yet, that's okay
                    pass
    except Exception as e:
        # Database check is optional
        pass
    
    # Check 3: ENCRYPTION_KEY is available (for runtime)
    encryption_key = os.getenv('ENCRYPTION_KEY')
    if not encryption_key:
        warnings.append("ENCRYPTION_KEY environment variable not set - OpenAI key encryption will fail")
    
    # Check 4: Required utilities are available
    try:
        from openai_key_utils import get_openai_api_key, set_openai_api_key, has_openai_api_key
    except Exception as e:
        errors.append(f"Failed to import openai_key_utils: {e}")
    
    try:
        from security_utils import encrypt_credential, decrypt_credential
    except Exception as e:
        errors.append(f"Failed to import security_utils: {e}")
    
    return errors, warnings

def print_validation_results(errors, warnings):
    """Print validation results"""
    if errors:
        print("\n" + "="*70)
        print("❌ OPENAI API KEY SUPPORT VALIDATION FAILED")
        print("="*70)
        for error in errors:
            print(f"   ❌ {error}")
        print("\n💡 Fix these errors before deploying!")
        print("="*70 + "\n")
        return False
    
    if warnings:
        print("\n" + "="*70)
        print("⚠️  OPENAI API KEY SUPPORT VALIDATION WARNINGS")
        print("="*70)
        for warning in warnings:
            print(f"   ⚠️  {warning}")
        print("\n💡 These warnings should be addressed for full functionality")
        print("="*70 + "\n")
        return True
    
    print("\n✅ OpenAI API key support validation passed!")
    return True

if __name__ == "__main__":
    errors, warnings = validate_openai_key_support()
    success = print_validation_results(errors, warnings)
    sys.exit(0 if success else 1)

