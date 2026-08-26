"""
Tests: DigiLocker-style signature verification + PDF tamper detection on
the generated demo corpus.
"""
from pathlib import Path

from app.security.signature_verify import verify_pdf_signature
from app.security.tamper_detect import analyze_pdf_tamper

DOCS = Path(__file__).resolve().parent.parent.parent / "data" / "docs"


def _analyze(name: str):
    sig = verify_pdf_signature(DOCS / name)
    tamper = analyze_pdf_tamper(DOCS / name, sig)
    return sig, tamper


def test_clean_doc_signature_valid_and_intact():
    sig, tamper = _analyze("clean_gst_cert.pdf")
    assert sig["signed"] is True
    assert sig["valid"] is True
    assert sig["intact"] is True
    assert sig["trusted"] is True
    assert sig["expected_issuer_ok"] is True
    assert tamper["tampered"] is False


def test_forged_gst_cert_caught():
    sig, tamper = _analyze("fraud_gst_cert.pdf")
    # forged: signature no longer intact (content modified after signing)
    # + metadata rewritten after signing + forge-tool producer fingerprint
    assert sig["signed"] is True
    assert sig["intact"] is False
    assert tamper["tampered"] is True
    reasons = " ".join(sig["reasons"] + tamper["reasons"]).lower()
    assert "modified after signing" in reasons
    assert "later than the signature timestamp" in reasons
    assert "forge" in reasons  # producer fingerprint


def test_rogue_issuer_detected():
    sig, _ = _analyze("fraud_udyam.pdf")
    assert sig["signed"] is True
    assert sig["trusted"] is False
    assert sig["expected_issuer_ok"] is False
    assert any("issuer" in r.lower() for r in sig["reasons"])


def test_unsigned_scan_not_tampered():
    sig, tamper = _analyze("kaveri_gst_cert.pdf")
    assert sig["signed"] is False
    assert tamper["tampered"] is False


def test_all_clean_docs_pass_integrity():
    for name in ("clean_udyam.pdf", "clean_pan_card.pdf", "clean_oem_auth.pdf",
                 "clean_local_content.pdf", "border_pan_card.pdf"):
        sig, tamper = _analyze(name)
        assert sig["valid"] is True, name
        assert tamper["tampered"] is False, name