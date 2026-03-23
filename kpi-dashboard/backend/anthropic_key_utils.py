#!/usr/bin/env python3
"""
Anthropic API Key Management Utilities

Mirrors openai_key_utils.py pattern. Keys are stored encrypted in the database
and can fall back to ANTHROPIC_API_KEY env var.
"""

from models import db, CustomerConfig
from security_utils import encrypt_credential, decrypt_credential
from datetime import datetime
import os


def get_anthropic_api_key(customer_id: int) -> str:
    """
    Get Anthropic API key for a customer.

    Priority:
    1. Customer-specific key from database (encrypted)
    2. Global ANTHROPIC_API_KEY environment variable (fallback)

    Returns:
        Anthropic API key string, or None if not configured
    """
    try:
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if config and hasattr(config, 'anthropic_api_key_encrypted') and config.anthropic_api_key_encrypted:
            try:
                api_key = decrypt_credential(config.anthropic_api_key_encrypted)
                if api_key:
                    return api_key
            except Exception as e:
                print(f"Warning: Failed to decrypt Anthropic API key for customer {customer_id}: {e}")

        # Fallback to global environment variable
        if not (config and hasattr(config, 'anthropic_api_key_encrypted') and config.anthropic_api_key_encrypted):
            global_key = os.getenv('ANTHROPIC_API_KEY')
            if global_key:
                return global_key

        return None
    except Exception as e:
        print(f"Error getting Anthropic API key for customer {customer_id}: {e}")
        return os.getenv('ANTHROPIC_API_KEY')


def has_anthropic_api_key(customer_id: int) -> bool:
    """Check if customer has an Anthropic API key configured."""
    try:
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if config and hasattr(config, 'anthropic_api_key_encrypted') and config.anthropic_api_key_encrypted:
            return True
        return bool(os.getenv('ANTHROPIC_API_KEY'))
    except Exception:
        return bool(os.getenv('ANTHROPIC_API_KEY'))
