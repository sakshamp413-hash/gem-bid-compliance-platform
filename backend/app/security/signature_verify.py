"""
DigiLocker-style PDF signature verification (pyHanko).

Validates: cryptographic signature, certificate chain against the
configured trust root, content integrity (nothing modified after
signing), and that the signer's issuer matches the expected issuing CA
(the "issuer-hash mismatch" forgery signal).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.security.certs import expected_issuer_cn, trust_root_path

logger = get_logger(__name__)


def _load_trust_roots():
    from pyhanko.keys import load_cert_from_pemder

    return [load_cert_from_pemder(str(trust_root_path()))]


def verify_pdf_signature(path: str | Path) -> dict[str, Any]:
    """
    Returns a SignatureReport dict:
      {signed, valid, intact, trusted, coverage, signer_name, issuer_cn,
       expected_issuer_ok, sig_timestamp, reasons[]}
    """
    report: dict[str, Any] = {
        "signed": False,
        "valid": False,
        "intact": False,
        "trusted": False,
        "coverage": None,
        "signer_name": None,
        "issuer_cn": None,
        "expected_issuer_ok": False,
        "sig_timestamp": None,
        "reasons": [],
    }
    try:
        from pyhanko_certvalidator import ValidationContext
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.sign.validation import validate_pdf_signature

        # NOTE: the reader must stay open while validating (lazy IO).
        with open(path, "rb") as f:
            reader = PdfFileReader(f)
            sigs = list(reader.embedded_signatures)

            if not sigs:
                report["reasons"].append("document carries no digital signature")
                return report

            report["signed"] = True
            sig = sigs[0]
            if sig.self_reported_timestamp is not None:
                report["sig_timestamp"] = sig.self_reported_timestamp.isoformat()
            vc = ValidationContext(trust_roots=_load_trust_roots())
            status = validate_pdf_signature(sig, vc)

            report["valid"] = bool(status.valid)
            report["intact"] = bool(status.intact)
            report["trusted"] = bool(status.trusted)
            report["coverage"] = str(status.coverage)

            if status.signing_cert is not None:
                cert = status.signing_cert
                report["signer_name"] = cert.subject.human_friendly
                report["issuer_cn"] = cert.issuer.human_friendly
                report["expected_issuer_ok"] = (
                    expected_issuer_cn().lower() in cert.issuer.human_friendly.lower()
                )

            if not status.intact:
                report["reasons"].append("content was modified after signing (integrity broken)")
            if not status.valid:
                report["reasons"].append("signature digest/certificate validation failed")
            if not status.trusted:
                report["reasons"].append("signer certificate not trusted by configured trust root")
            if not report["expected_issuer_ok"] and report["issuer_cn"]:
                report["reasons"].append(
                    f"signer issuer '{report['issuer_cn']}' does not match expected "
                    f"issuing CA '{expected_issuer_cn()}' (issuer mismatch — forged chain?)"
                )
            if not report["reasons"]:
                report["reasons"].append("signature valid, intact and trusted")

    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("signature verification error on %s: %s", path, exc)
        report["reasons"].append(f"verification error: {exc}")
        report["valid"] = False
        report["intact"] = False
    return report