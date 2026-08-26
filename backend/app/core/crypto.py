"""
Field-level encryption at rest (Fernet).

Sensitive identifier fields (PAN, GSTIN, CIN, EPFO No, etc.) are stored
encrypted in the database. The key comes from settings (env: ENCRYPTION_KEY);
in production use a KMS-derived key (see docs/production.md).
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.fernet_key)
    return _fernet


def encrypt_value(plaintext: str | None) -> str | None:
    if plaintext is None or plaintext == "":
        return plaintext
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str | None) -> str | None:
    if ciphertext is None or ciphertext == "":
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ciphertext  # not encrypted (or bad key) — return as-is


def encrypt_json(obj) -> str | None:
    """Encrypt a JSON-serializable object to an encrypted JSON string column."""
    import json

    if obj is None:
        return None
    return encrypt_value(json.dumps(obj, default=str))


def decrypt_json(ciphertext: str | None):
    import json

    if not ciphertext:
        return None
    try:
        return json.loads(decrypt_value(ciphertext) or "")
    except (ValueError, TypeError):
        return None


class EncryptedString:
    """SQLAlchemy TypeDecorator storing a field encrypted at rest."""

    # used via sqlalchemy TypeDecorator in models
    pass