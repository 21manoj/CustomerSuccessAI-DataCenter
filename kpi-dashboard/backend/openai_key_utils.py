#!/usr/bin/env python3
"""
OpenAI API Key Management Utilities

Provides functions to get and set OpenAI API keys per customer.
Keys are stored encrypted in the database and can be updated without server restart.
"""

from models import db, CustomerConfig
from security_utils import encrypt_credential, decrypt_credential
from datetime import datetime
import os


def get_openai_api_key(customer_id: int) -> str:
    """
    Get OpenAI API key for a customer.
    
    Priority:
    1. Customer-specific key from database (encrypted)
    2. Global environment variable (fallback for backward compatibility)
    
    Args:
        customer_id: Customer ID
        
    Returns:
        OpenAI API key string, or None if not configured
    """
    try:
        # Try to get customer-specific key from database
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if config and config.openai_api_key_encrypted:
            try:
                api_key = decrypt_credential(config.openai_api_key_encrypted)
                if api_key:
                    return api_key
            except Exception as e:
                print(f"Warning: Failed to decrypt OpenAI API key for customer {customer_id}: {e}")
        
        # Fallback to global environment variable (for backward compatibility)
        # BUT: Only if no encrypted key exists (to avoid using invalid env keys)
        # If we got here, it means decryption failed or no key in DB
        # Don't fallback to env var if we had an encrypted key that failed to decrypt
        if not (config and config.openai_api_key_encrypted):
            global_key = os.getenv('OPENAI_API_KEY')
            if global_key:
                return global_key
        
        return None
    except Exception as e:
        print(f"Error getting OpenAI API key for customer {customer_id}: {e}")
        # Fallback to environment variable
        return os.getenv('OPENAI_API_KEY')


def set_openai_api_key(customer_id: int, api_key: str) -> bool:
    """
    Set OpenAI API key for a customer (encrypted in database).
    
    Args:
        customer_id: Customer ID
        api_key: OpenAI API key to store
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Validate model has required attributes
        if not hasattr(CustomerConfig, 'openai_api_key_encrypted'):
            error_msg = "CustomerConfig model missing 'openai_api_key_encrypted' attribute. Please update models.py and rebuild Docker image."
            print(f"❌ {error_msg}")
            raise AttributeError(error_msg)
        
        if not hasattr(CustomerConfig, 'openai_api_key_updated_at'):
            error_msg = "CustomerConfig model missing 'openai_api_key_updated_at' attribute. Please update models.py and rebuild Docker image."
            print(f"❌ {error_msg}")
            raise AttributeError(error_msg)
        
        # Check ENCRYPTION_KEY is available
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            error_msg = "ENCRYPTION_KEY environment variable not set. Cannot encrypt API key."
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        # Get or create customer config
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            config = CustomerConfig(customer_id=customer_id)
            db.session.add(config)
        
        # Encrypt and store the API key
        config.openai_api_key_encrypted = encrypt_credential(api_key)
        config.openai_api_key_updated_at = datetime.utcnow()
        db.session.commit()
        
        return True
    except AttributeError as e:
        # Model issue - provide helpful error
        print(f"❌ Model configuration error: {e}")
        print("💡 This usually means the Docker image needs to be rebuilt with updated models.py")
        db.session.rollback()
        return False
    except ValueError as e:
        # Configuration issue
        print(f"❌ Configuration error: {e}")
        print("💡 Set ENCRYPTION_KEY in docker.env or environment variables")
        db.session.rollback()
        return False
    except Exception as e:
        print(f"❌ Error setting OpenAI API key for customer {customer_id}: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return False


def has_openai_api_key(customer_id: int) -> bool:
    """
    Check if customer has an OpenAI API key configured.
    
    Args:
        customer_id: Customer ID
        
    Returns:
        True if key is configured, False otherwise
    """
    try:
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if config and config.openai_api_key_encrypted:
            return True
        
        # Check global environment variable
        return bool(os.getenv('OPENAI_API_KEY'))
    except Exception as e:
        print(f"Error checking OpenAI API key for customer {customer_id}: {e}")
        return bool(os.getenv('OPENAI_API_KEY'))

