#!/usr/bin/env python3
"""Voyage AI API Key Management Utilities.

Mirrors openai_key_utils.py. Voyage AI (voyage-3-large) replaced OpenAI
text-embedding-3-large as the embeddings provider for the Qdrant RAG
retrieval layer (June 2026) so the stack runs entirely on Anthropic +
Anthropic's recommended embeddings partner.

Keys resolve in priority order:
  1. Customer-specific key from the database (encrypted), if the
     `voyage_api_key_encrypted` column exists on CustomerConfig.
  2. Global VOYAGE_API_KEY environment variable (fallback).
"""

import os

from models import CustomerConfig

try:
    from security_utils import decrypt_credential
except Exception:  # pragma: no cover - security_utils always present in app
    decrypt_credential = None


def get_voyage_api_key(customer_id: int) -> str:
    """Return the Voyage AI API key for a customer, or None if unconfigured."""
    try:
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        # Per-customer encrypted key (only if the column has been added).
        if (
            config
            and decrypt_credential is not None
            and getattr(config, "voyage_api_key_encrypted", None)
        ):
            try:
                api_key = decrypt_credential(config.voyage_api_key_encrypted)
                if api_key:
                    return api_key
            except Exception as e:
                print(f"Warning: Failed to decrypt Voyage API key for customer {customer_id}: {e}")

        # Fallback to env var only when no encrypted key is stored.
        if not (config and getattr(config, "voyage_api_key_encrypted", None)):
            global_key = os.getenv("VOYAGE_API_KEY")
            if global_key:
                return global_key

        return None
    except Exception as e:
        print(f"Error getting Voyage API key for customer {customer_id}: {e}")
        return os.getenv("VOYAGE_API_KEY")


def has_voyage_api_key(customer_id: int) -> bool:
    """True if a Voyage key is resolvable for the customer."""
    try:
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if config and getattr(config, "voyage_api_key_encrypted", None):
            return True
        return bool(os.getenv("VOYAGE_API_KEY"))
    except Exception:
        return bool(os.getenv("VOYAGE_API_KEY"))
