"""
Credential encryption for integration API keys/tokens.
Uses Fernet symmetric encryption with a master key from ENCRYPTION_KEY env var.

Usage:
    from utils.credential_manager import encrypt_credential, decrypt_credential

    encrypted = encrypt_credential("my-api-key-123")
    plaintext = decrypt_credential(encrypted)
"""
import os
import base64
import hashlib
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_fernet():
    """Build Fernet cipher from ENCRYPTION_KEY env var."""
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        raise ValueError(
            "ENCRYPTION_KEY environment variable not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    # Derive a proper 32-byte Fernet key from an arbitrary-length string
    derived = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_credential(plaintext: str) -> str:
    """Encrypt a credential string. Returns base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_credential(ciphertext: str) -> str:
    """Decrypt a credential string. Raises ValueError on bad key/data."""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError("Failed to decrypt credential — wrong ENCRYPTION_KEY or corrupted data")
