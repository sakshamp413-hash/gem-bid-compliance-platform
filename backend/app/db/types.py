"""
Encrypted column TypeDecorator: transparently encrypts sensitive string
fields at rest using Fernet (see app.core.crypto).
"""
from __future__ import annotations

from sqlalchemy.types import String, TypeDecorator

from app.core.crypto import decrypt_value, encrypt_value


class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True

    def __init__(self, length: int = 500, **kwargs):
        super().__init__(length=length, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_value(str(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_value(str(value))

    def copy(self, **kw):
        return EncryptedString(self.impl.length, **kw)