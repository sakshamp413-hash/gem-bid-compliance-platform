from pathlib import Path
import io

from app.security.signature_verify import verify_pdf_signature
from app.security.tamper_detect import analyze_pdf_tamper

DOCS = Path(__file__).resolve().parent.parent.parent / "data" / "docs"


def _make_object_stream_pdf() -> bytes:
    """
    Handcraft a minimal, VALID PDF 1.5 file that uses an object stream
    (as modern re-saved PDFs do) — a document-info dict is compressed
    inside a /ObjStm while the page tree stays directly accessible.
    """
    body1 = b"<< /Type /Catalog /Pages 2 0 R >>"
    body2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    body3 = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>"
    body6 = b"<< /Producer (ModernOffice 2026) /CreationDate (D:20260101120000Z) /ModDate (D:20260101120000Z) >>"
    header = b"6 0\n" + str(len(body6)).encode() + b"\n"
    # header pairs: "6 0 <offset>" — obj 6 at offset 0 within the decompressed data
    data = header + body6
    length = len(data)

    parts = [b"%PDF-1.5\n"]
    obj1 = b"1 0 obj\n" + body1 + b"\nendobj\n"
    obj2 = b"2 0 obj\n" + body2 + b"\nendobj\n"
    obj3 = b"3 0 obj\n" + body3 + b"\nendobj\n"
    obj4 = (
        b"4 0 obj\n<< /Length 46 >>\nstream\n"
        b"BT /F1 24 Tf 72 700 Td (Genuine) Tj ET\n"
        b"endstream\nendobj\n"
    )
    obj5 = (
        b"5 0 obj\n<< /Type /ObjStm /N 1 /First "
        + str(len(header)).encode()
        + b" /Length "
        + str(length).encode()
        + b" >>\nstream\n"
        + data
        + b"\nendstream\nendobj\n"
    )
    parts += [obj1, obj2, obj3, obj4, obj5]

    # xref: objects 1-4 regular, obj 5 regular, obj 6 compressed in stream 5
    n_entries = 7
    xref_offset = sum(len(p) for p in parts)
    entry_lines = [b"0000000000 65535 f \n"]
    entries_regular = []
    for _ in range(5):  # objects 1..5
        entries_regular.append(b"0000000000 00000 n \n")
    entries_compressed = [b"0000000005 00002 2 \n"]  # obj 6 -> stream 5
    xref = b"xref\n0 " + str(n_entries).encode() + b"\n" + b"".join(entry_lines + entries_regular + entries_compressed)
    # patch real offsets for objects 1..5
    base = xref_offset + len(b"xref\n0 " + str(n_entries).encode() + b"\n" + entry_lines[0])
    offset = base
    for i in range(5):
        xref = xref.replace(
            b"0000000000 00000 n \n",
            f"{offset:010d}".encode() + b" 00000 n \n",
            1,
        )
        offset += 0  # replaced in place — recompute below
    # simpler: rebuild the entries deterministically
    def obj_offset(i_obj):
        return xref_offset + sum(len(p) for p in parts[:i_obj])
    entries = [b"0000000000 65535 f \n"]
    for i_obj in range(1, 6):
        entries.append(f"{obj_offset(i_obj):010d}".encode() + b" 00000 n \n")
    entries.append(b"0000000005 00002 2 \n")
    xref = b"xref\n0 7\n" + b"".join(entries)
    trailer = (
        b"trailer\n<< /Size 7 /Root 1 0 R >>\n"
        b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF\n"
    )
    return b"".join(parts) + xref + trailer


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


def test_object_stream_pdf_is_not_flagged():
    """
    Object streams are normal in modern, perfectly valid PDFs. A clean
    PDF using them must NOT be marked tampered (informational only).
    """
    import pikepdf

    raw = _make_object_stream_pdf()
    tmp = DOCS.parent / "_objstream_test.pdf"
    tmp.write_bytes(raw)

    # sanity: the handcrafted file genuinely uses object streams
    with pikepdf.open(tmp) as pdf:
        n_streams = sum(
            1 for obj in pdf.objects
            if obj is not None and obj.get("/Type") == pikepdf.Name("/ObjStm")
        )
    assert n_streams > 0

    try:
        sig = verify_pdf_signature(str(tmp))
        tamper = analyze_pdf_tamper(tmp, sig)
        assert tamper["tampered"] is False
        assert tamper["soft_indicators"], "expected an informational structural note"
    finally:
        tmp.unlink(missing_ok=True)


def test_all_clean_docs_pass_integrity():
    for name in ("clean_udyam.pdf", "clean_pan_card.pdf", "clean_oem_auth.pdf",
                 "clean_local_content.pdf", "border_pan_card.pdf"):
        sig, tamper = _analyze(name)
        assert sig["valid"] is True, name
        assert tamper["tampered"] is False, name