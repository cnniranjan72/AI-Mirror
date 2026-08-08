"""
Symmetric encryption for data that must be stored but never logged or
displayed in plaintext — currently just per-user LLM provider API keys
(users.llm_api_key_encrypted, see migration_v15.sql).

Same pattern as auth.py's AUTH_SECRET: a dev-default env var that must be
overridden in production. Fernet requires a 32-byte urlsafe-base64 key, so
an arbitrary secret string is hashed down to the right shape rather than
requiring the operator to generate a Fernet key directly.
"""
import base64
import hashlib
import os

from cryptography.fernet import Fernet

API_KEY_ENCRYPTION_SECRET = os.getenv("API_KEY_ENCRYPTION_SECRET", "aimirror-dev-key-encryption-secret-change-me")


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(API_KEY_ENCRYPTION_SECRET.encode()).digest())
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
