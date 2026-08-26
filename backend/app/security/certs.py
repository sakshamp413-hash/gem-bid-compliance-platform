"""
Demo PKI trust infrastructure.

Generates (once) a self-signed demo "DigiLocker-style" CA + issuer and
persists them under backend/storage/certs. Documents in the demo dataset
are genuinely signed by this issuer, and verification validates them
against this trust root.

PRODUCTION SWAP (documented in docs/production.md):
  * Replace `demo_ca.pem` with the real DigiLocker / GSTN / MCA signing
    CA certificates (trust roots).
  * Set EXPECTED_ISSUER_CN to the real signing CA's common name.
  * No application code changes are required.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

CA_CN = "Demo DigiLocker Issuing CA"


def _write_pem(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    logger.info("wrote %s", path)


def ensure_demo_ca() -> tuple[Path, Path]:
    """Create the demo CA + key if absent. Returns (ca_path, key_path)."""
    certs = settings.certs_path
    ca_path = certs / "demo_ca.pem"
    key_path = certs / "demo_ca_key.pem"
    if ca_path.exists() and key_path.exists():
        return ca_path, key_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, CA_CN)])
    now = dt.datetime.now(dt.timezone.utc)
    ca = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_cert_sign=True, crl_sign=True,
                content_commitment=True, key_encipherment=False,
                data_encipherment=False, key_agreement=False,
                encipher_only=False, decipher_only=False,
            ),
            True,
        )
        .sign(key, hashes.SHA256())
    )
    _write_pem(
        key_path,
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )
    _write_pem(ca_path, ca.public_bytes(serialization.Encoding.PEM))
    return ca_path, key_path


def trust_root_path() -> Path:
    """Path to the PEM trust root used for signature validation."""
    return ensure_demo_ca()[0]


def signer_key_path() -> Path:
    return ensure_demo_ca()[1]


def expected_issuer_cn() -> str:
    return settings.expected_issuer_cn or CA_CN