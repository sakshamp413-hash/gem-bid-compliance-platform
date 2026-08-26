#!/usr/bin/env python3
"""
Synthetic dataset generator for the GeM bid-compliance demo.

Produces:
  * data/mock_portal.json          — the seeded "government registry" dataset
  * data/docs/*.pdf                — bidder documents, GENUINELY signed with
                                     pyHanko against the demo issuing CA
  * forged variants:               — GST cert signed THEN modified after
                                     signing (incremental update), and a cert
                                     signed by a rogue CA (issuer mismatch)

Usage:  python data/generate.py   (run from repo root)

Re-runnable: deterministic (fixed seeds), overwrites its own outputs.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

from app.core.id_validators import gstin_checksum_char  # noqa: E402
from app.security.certs import ensure_demo_ca, signer_key_path, trust_root_path  # noqa: E402

OUT_DOCS = REPO_ROOT / "data" / "docs"
OUT_PORTAL = REPO_ROOT / "data" / "mock_portal.json"

# --------------------------------------------------------------------------
# ID construction (all REAL-format, checksummed)
# --------------------------------------------------------------------------


def make_gstin(state: str, pan: str, entity_code: str = "1") -> str:
    """GSTIN = state(2) + PAN(10) + entity(1) + Z + checksum(1)."""
    first14 = f"{state}{pan}{entity_code}Z"
    return first14 + gstin_checksum_char(first14)


def make_pan(first3: str, entity_char: str, name_first: str, digits: str = "1234") -> str:
    return f"{first3}{entity_char}{name_first}{digits}K"


# --------------------------------------------------------------------------
# Registry dataset
# --------------------------------------------------------------------------

def build_portal_data() -> dict:
    # --- identifiers -------------------------------------------------------
    clean_pan = make_pan("AAB", "C", "C")          # CleanCorp - company
    clean_gstin = make_gstin("27", clean_pan)      # Maharashtra
    border_pan = make_pan("AAV", "F", "B")         # BorderlineTraders - firm
    border_gstin = make_gstin("33", border_pan)    # Tamil Nadu
    fraud_pan = make_pan("AAB", "F", "F")          # FraudFillers - firm
    fraud_gstin = make_gstin("27", fraud_pan)      # Maharashtra
    kaveri_pan = make_pan("AAK", "F", "K")         # Kaveri - firm
    kaveri_gstin = make_gstin("29", kaveri_pan)    # Karnataka
    southern_pan = make_pan("AAP", "C", "S")       # Southern Pumps LLP - company-type
    southern_gstin = make_gstin("33", southern_pan)
    front_pan = make_pan("AAF", "C", "F")          # FrontRunner - company
    front_gstin = make_gstin("27", front_pan)
    quick_pan = make_pan("AAQ", "F", "Q")          # QuickSpares - firm
    quick_gstin = make_gstin("29", quick_pan)

    today = date.today()

    def d(y, m, day):
        return date(y, m, day).isoformat()

    data: dict = {
        "udyam": {
            "UDYAM-MH-27-0001234": {
                "legal_name": "CleanCorp Industrial Solutions Pvt. Ltd.",
                "trade_name": "CleanCorp",
                "pan": clean_pan,
                "classification": "Small",
                "sector": "manufacturing",
                "investment_crore": 2.4,
                "turnover_crore": 18.5,
                "status": "Active",
                "issued_on": d(2023, 4, 12),
            },
            "UDYAM-TN-02-0005678": {
                "legal_name": "Borderline Traders",
                "trade_name": "BorderlineTraders",
                "pan": border_pan,
                "classification": "Micro",
                "sector": "services",
                "investment_crore": 0.4,
                "turnover_crore": 1.2,
                "status": "Active",
                "issued_on": d(2022, 11, 2),
            },
            "UDYAM-MH-27-0009876": {
                "legal_name": "FraudFillers Traders",
                "trade_name": "FraudFillers",
                "pan": fraud_pan,
                "classification": "Small",
                "sector": "services",
                "investment_crore": 1.1,
                "turnover_crore": 9.0,
                "status": "Active",
                "issued_on": d(2023, 1, 20),
            },
            "UDYAM-KA-01-0002468": {
                "legal_name": "Kaveri Engineering Works",
                "trade_name": "Kaveri Engg",
                "pan": kaveri_pan,
                "classification": "Micro",
                "sector": "manufacturing",
                "investment_crore": 0.3,
                "turnover_crore": 0.9,
                "status": "Active",
                "issued_on": d(2021, 6, 15),
            },
            "UDYAM-TN-04-0001357": {
                "legal_name": "Southern Pumps LLP",
                "trade_name": "Southern Pumps",
                "pan": southern_pan,
                "classification": "Small",
                "sector": "manufacturing",
                "investment_crore": 3.0,
                "turnover_crore": 22.0,
                "status": "Active",
                "issued_on": d(2022, 9, 30),
            },
            "UDYAM-MH-27-0003141": {
                "legal_name": "FrontRunner Pumps Pvt. Ltd.",
                "trade_name": "FrontRunner",
                "pan": front_pan,
                "classification": "Small",
                "sector": "services",
                "investment_crore": 2.0,
                "turnover_crore": 12.0,
                "status": "Active",
                "issued_on": d(2023, 8, 10),
            },
            "UDYAM-KA-01-0007159": {
                "legal_name": "QuickSpares Trading Co.",
                "trade_name": "QuickSpares",
                "pan": quick_pan,
                "classification": "Micro",
                "sector": "services",
                "investment_crore": 0.6,
                "turnover_crore": 1.8,
                "status": "Active",
                "issued_on": d(2022, 12, 5),
            },
        },
        "gstin": {
            clean_gstin: {
                "legal_name": "CleanCorp Industrial Solutions Pvt. Ltd.",
                "trade_name": "CleanCorp",
                "status": "Active",
                "returns": {"latest": {"status": "filed", "period": "Q2 FY 2025-26", "filed_on": d(2025, 8, 15)}},
            },
            border_gstin: {
                "legal_name": "Borderline Traders",
                "trade_name": "BorderlineTraders",
                "status": "Active",
                "returns": {"latest": {"status": "not filed", "period": "Q3 FY 2025-26", "filed_on": None}},
            },
            fraud_gstin: {
                "legal_name": "FraudFillers Traders",
                "trade_name": "FraudFillers",
                "status": "Cancelled",
                "returns": {"latest": {"status": "not filed", "period": "Q1 FY 2024-25", "filed_on": None}},
            },
            kaveri_gstin: {
                "legal_name": "Kaveri Engineering Works",
                "trade_name": "Kaveri Engg",
                "status": "Active",
                "returns": {"latest": {"status": "filed", "period": "Q2 FY 2025-26", "filed_on": d(2025, 7, 20)}},
            },
            southern_gstin: {
                "legal_name": "Southern Pumps LLP",
                "trade_name": "Southern Pumps",
                "status": "Active",
                "returns": {"latest": {"status": "filed", "period": "Q2 FY 2025-26", "filed_on": d(2025, 8, 2)}},
            },
            front_gstin: {
                "legal_name": "FrontRunner Pumps Pvt. Ltd.",
                "trade_name": "FrontRunner",
                "status": "Active",
                "returns": {"latest": {"status": "filed", "period": "Q2 FY 2025-26", "filed_on": d(2025, 8, 10)}},
            },
            quick_gstin: {
                "legal_name": "QuickSpares Trading Co.",
                "trade_name": "QuickSpares",
                "status": "Active",
                "returns": {"latest": {"status": "filed", "period": "Q2 FY 2025-26", "filed_on": d(2025, 7, 28)}},
            },
        },
        "pan": {
            clean_pan: {"name": "CleanCorp Industrial Solutions Pvt. Ltd.", "status": "PAN valid"},
            border_pan: {"name": "Borderline Traders", "status": "PAN valid"},
            fraud_pan: {"name": "FraudFillers Traders", "status": "PAN valid"},
            kaveri_pan: {"name": "Kaveri Engineering Works", "status": "PAN valid"},
            southern_pan: {"name": "Southern Pumps LLP", "status": "PAN valid"},
            front_pan: {"name": "FrontRunner Pumps Pvt. Ltd.", "status": "PAN valid"},
            quick_pan: {"name": "QuickSpares Trading Co.", "status": "PAN valid"},
        },
        "mca": {
            "U12345MH2023PLC123456": {
                "company_name": "CleanCorp Industrial Solutions Pvt. Ltd.",
                "status": "Active",
                "date_of_incorporation": d(2023, 3, 10),
            },
            "U54321TN2019PTC654321": {
                "company_name": "FraudFillers Traders Pvt. Ltd.",
                "status": "Active",
                "date_of_incorporation": d(2019, 7, 25),
            },
            "U11223TN2021NPL987654": {
                "company_name": "Southern Pumps LLP",
                "status": "Active",
                "date_of_incorporation": d(2021, 5, 5),
            },
        },
        "epfo": {
            "MH/12345/00678": {"establishment_name": "CleanCorp Industrial Solutions Pvt. Ltd.", "status": "Active"},
            "TN/45678/00321": {"establishment_name": "Borderline Traders", "status": "Active"},
        },
        "esic": {
            "2712345678": {"establishment_name": "CleanCorp Industrial Solutions Pvt. Ltd.", "status": "Active"},
        },
        "startup": {
            "DIPP12345678": {"startup_name": "CleanCorp Industrial Solutions Pvt. Ltd.", "status": "Active",
                             "valid_until": d(2030, 3, 10)},
            "DIPP87654321": {"startup_name": "Kaveri Engineering Works", "status": "Active",
                             "valid_until": d(2025, 1, 1)},  # EXPIRED
        },
        "nsic": {
            "NSIC12345678": {"unit_name": "CleanCorp Industrial Solutions Pvt. Ltd.", "status": "Active",
                             "monetary_limit": "Rs. 5,00,00,000"},
        },
        "digilocker": {
            "clean://gst/cert/1": {"issued_to": clean_pan, "doc": "gst_cert", "valid": True},
        },
        "blacklist": [
            {
                "name": "FraudFillers Traders",
                "pan": fraud_pan,
                "period": "2025-03-15 to 2027-03-14",
                "source": "GeM banned vendor list / CPPP debarment",
                "reason": "Submission of forged statutory documents in prior tenders",
            },
            {
                "name": "Sharma & Sons Traders",
                "pan": "AABSS1234K",
                "period": "2024-06-01 to 2026-05-31",
                "source": "CPPP debarment",
                "reason": "Collusive bidding",
            },
        ],
    }
    return data


STYLES = {
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=13, leading=17,
                            alignment=1, textColor=colors.HexColor("#1a3a6b")),
    "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=8, leading=11,
                          alignment=1, textColor=colors.HexColor("#666666")),
    "label": ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=9.5, leading=14),
    "value": ParagraphStyle("value", fontName="Helvetica", fontSize=9.5, leading=14),
    "note": ParagraphStyle("note", fontName="Helvetica", fontSize=8, leading=11,
                           textColor=colors.HexColor("#888888")),
}


def render_cert(title: str, header_note: str, rows: list[tuple[str, str]],
                footer: str = "") -> bytes:
    """Government-style certificate PDF with label: value rows."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    story = [
        Paragraph(title, STYLES["title"]),
        Spacer(1, 2),
        Paragraph(header_note, STYLES["sub"]),
        Spacer(1, 8),
    ]
    data_rows = [[Paragraph(k, STYLES["label"]), Paragraph(v, STYLES["value"])] for k, v in rows]
    tbl = Table(data_rows, colWidths=[62 * mm, 116 * mm])
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)
    if footer:
        story.append(Spacer(1, 10))
        story.append(Paragraph(footer, STYLES["note"]))
    doc.build(story)
    return buf.getvalue()


def render_letter(title: str, paragraphs: list[str], signature: str) -> bytes:
    """Authorization-letter style document."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    story = [Paragraph(title, STYLES["title"]), Spacer(1, 10)]
    for p in paragraphs:
        story.append(Paragraph(p, ParagraphStyle("p", fontName="Helvetica", fontSize=9.5,
                                                 leading=14, spaceAfter=8)))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Authorized Signatory: {signature}", STYLES["label"]))
    doc.build(story)
    return buf.getvalue()


# --------------------------------------------------------------------------
# Signing (pyHanko) + tampering (pikepdf)
# --------------------------------------------------------------------------

def sign_pdf_bytes(pdf_bytes: bytes, cert_file: Path, key_file: Path,
                   reason: str = "Issued by statutory authority") -> bytes:
    from pyhanko.sign import fields, signers
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.keys import load_cert_from_pemder, load_private_key_from_pemder
    from pyhanko_certvalidator.registry import SimpleCertificateStore

    store = SimpleCertificateStore.from_certs([load_cert_from_pemder(str(cert_file))])
    signer = signers.SimpleSigner(
        load_cert_from_pemder(str(cert_file)),
        load_private_key_from_pemder(str(key_file), None),
        cert_registry=store,
    )
    w = IncrementalPdfFileWriter(BytesIO(pdf_bytes))
    meta = signers.PdfSignatureMetadata(field_name="Sig1", reason=reason,
                                        location="GeM Demo")
    ps = signers.PdfSigner(meta, signer,
                           new_field_spec=fields.SigFieldSpec("Sig1", box=(12, 12, 200, 48)))
    out = BytesIO()
    ps.sign_pdf(w, output=out)
    return out.getvalue()


def tamper_after_signing(pdf_bytes: bytes) -> bytes:
    """
    Append a NEW revision after signing that rewrites the document info
    (/ModDate, /Producer). This is a genuine, spec-compliant incremental
    update — exactly what a forger produces — so signature verification
    reports "modified after signing" and tamper signals fire.
    """
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(pdf_bytes))
    trailer = reader.trailer
    size = int(trailer["/Size"])
    root_ref = trailer["/Root"]
    root_id = (
        root_ref.indirect_reference.idnum
        if hasattr(root_ref, "indirect_reference") and root_ref.indirect_reference
        else root_ref.idnum
    )
    info_id = trailer.get("/Info")
    orig_creation = ""
    if info_id is not None:
        info = info_id.get_object() if hasattr(info_id, "get_object") else info_id
        orig_creation = str(info.get("/CreationDate", ""))
    new_info_id = size + 1

    new_date = (datetime.now() + timedelta(days=1)).strftime("D:%Y%m%d%H%M%S") + "Z"
    info_dict = (
        f"<< /Producer (GSTN-ForgeTool 2.1 (re-signed)) "
        f"/ModDate ({new_date}) /CreationDate ({orig_creation}) >>"
    )
    old_startxref = int(reader._startxref)
    obj_offset = len(pdf_bytes)
    obj_str = f"{new_info_id} 0 obj\n{info_dict}\nendobj\n"
    xref_offset = obj_offset + len(obj_str)
    xref = (
        f"xref\n{new_info_id} 1\n{obj_offset:010d} 00000 n \n"
        f"trailer\n<< /Size {new_info_id + 1} /Root {root_id} 0 R "
        f"/Info {new_info_id} 0 R /Prev {old_startxref} >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    )
    tampered_bytes = pdf_bytes + obj_str.encode("latin-1") + xref.encode("latin-1")

    # A forger's editor also re-saves the file wholesale — this breaks the
    # signature digest outright (byte-range content no longer matches).
    import pikepdf

    with pikepdf.open(BytesIO(tampered_bytes)) as pdf:
        out = BytesIO()
        pdf.save(out)
        return out.getvalue()


# --------------------------------------------------------------------------
# Document builders
# --------------------------------------------------------------------------

def build_docs(bidder_key: str) -> dict[str, bytes]:
    """Returns {doc_type: pdf_bytes} for one demo bidder."""
    today = date.today()
    P = build_portal_data()

    if bidder_key == "clean":
        pan = make_pan("AAB", "C", "C")
        gstin = make_gstin("27", pan)
        udyam = "UDYAM-MH-27-0001234"
        return {
            "udyam": render_cert(
                "Udyam Registration Certificate",
                "Government of India — Ministry of Micro, Small & Medium Enterprises",
                [
                    ("Udyam Registration Number", udyam),
                    ("Legal Name of Enterprise", "CleanCorp Industrial Solutions Pvt. Ltd."),
                    ("Trade Name", "CleanCorp"),
                    ("PAN", pan),
                    ("Type of Enterprise", "Private Limited Company"),
                    ("Sector", "Manufacturing"),
                    ("Classification", "Small"),
                    ("Investment (₹ crore)", "2.4"),
                    ("Turnover (₹ crore)", "18.5"),
                    ("Date of Issue", "2023-04-12"),
                    ("Address", "Plot 17, MIDC Andheri East, Mumbai 400093"),
                ],
                "This certificate is digitally signed by the issuing authority."),
            "gst_cert": render_cert(
                "Goods and Services Tax Registration Certificate",
                "Government of India — GSTN (Provisional)",
                [
                    ("GSTIN", gstin),
                    ("Legal Name", "CleanCorp Industrial Solutions Pvt. Ltd."),
                    ("Trade Name", "CleanCorp"),
                    ("Registration Status", "Active"),
                    ("Date of Registration", "2023-05-02"),
                    ("Address", "Plot 17, MIDC Andheri East, Mumbai 400093"),
                    ("Principal Place of Business", "Maharashtra (27)"),
                ],
                "Digitally signed — verify at https://www.gst.gov.in"),
            "pan_card": render_cert(
                "Permanent Account Number (PAN) Card",
                "Income Tax Department, Government of India",
                [
                    ("PAN", pan),
                    ("Name", "CleanCorp Industrial Solutions Pvt. Ltd."),
                    ("Father/Spouse Name", "N/A"),
                    ("Date of Issue", "2023-03-18"),
                    ("Status", "Valid"),
                ],
                "Digitally signed."),
            "cin": render_cert(
                "Certificate of Incorporation",
                "Ministry of Corporate Affairs — ROC Mumbai",
                [
                    ("CIN", "U12345MH2023PLC123456"),
                    ("Company Name", "CleanCorp Industrial Solutions Pvt. Ltd."),
                    ("Date of Incorporation", "2023-03-10"),
                    ("Registered Office", "Plot 17, MIDC Andheri East, Mumbai 400093"),
                    ("Company Status", "Active"),
                ],
                "Digitally signed by ROC."),
            "oem_auth": render_letter(
                "OEM Authorisation Letter",
                [
                    "To Whom It May Concern,",
                    "We, <b>PumpTech Industries Ltd.</b> (OEM), manufacturer of centrifugal "
                    "pumps, hereby authorise <b>CleanCorp Industrial Solutions Pvt. Ltd.</b> "
                    "as our authorised distributor for the supply of industrial pumps "
                    "(CP-100 series) to GeM buyers.",
                    "Item Description: Industrial centrifugal pumps, 5HP-50HP, ISI marked.",
                    "This authorisation is valid from 2024-01-01 to 2026-12-31.",
                ],
                "R. Mehta, Director, PumpTech Industries Ltd."),
            "local_content": render_cert(
                "Make in India — Local Content Self-Certification",
                "As per DPIIT Public Procurement (Preference to Make in India) Order",
                [
                    ("Item", "Industrial centrifugal pumps (CP-100)"),
                    ("Declared Class", "I"),
                    ("Total Value (Rs. Lakh)", "100.0"),
                    ("Imported Content Value (Rs. Lakh)", "30.0"),
                    ("Claimed Local Content (%)", "70%"),
                    ("Date of Certification", today.isoformat()),
                    ("Declared By", "CleanCorp Industrial Solutions Pvt. Ltd."),
                ],
                "Self-certification — subject to verification."),
            "epfo": render_cert(
                "EPFO Establishment Registration",
                "Employees' Provident Fund Organisation",
                [
                    ("Establishment Code", "MH/12345/00678"),
                    ("Name of Establishment", "CleanCorp Industrial Solutions Pvt. Ltd."),
                    ("Status", "Active"),
                ],
                ""),
            "esic": render_cert(
                "ESIC Registration",
                "Employees' State Insurance Corporation",
                [
                    ("ESIC Code", "2712345678"),
                    ("Name of Establishment", "CleanCorp Industrial Solutions Pvt. Ltd."),
                    ("Status", "Active"),
                ],
                ""),
            "startup": render_cert(
                "Startup Recognition Certificate",
                "DPIIT, Ministry of Commerce & Industry",
                [
                    ("Recognition Number", "DIPP12345678"),
                    ("Startup Name", "CleanCorp Industrial Solutions Pvt. Ltd."),
                    ("Status", "Active"),
                    ("Valid Until", "2030-03-10"),
                ],
                ""),
            "nsic": render_cert(
                "NSIC Single Point Registration",
                "National Small Industries Corporation Ltd.",
                [
                    ("Registration Number", "NSIC12345678"),
                    ("Unit Name", "CleanCorp Industrial Solutions Pvt. Ltd."),
                    ("Status", "Active"),
                    ("Monetary Limit", "Rs. 5,00,00,000"),
                ],
                ""),
        }

    if bidder_key == "border":
        pan = make_pan("AAV", "F", "B")
        gstin = make_gstin("33", pan)
        return {
            "udyam": render_cert(
                "Udyam Registration Certificate",
                "Government of India — Ministry of Micro, Small & Medium Enterprises",
                [
                    ("Udyam Registration Number", "UDYAM-TN-02-0005678"),
                    ("Legal Name of Enterprise", "Borderline Traders"),
                    ("Trade Name", "BorderlineTraders"),
                    ("PAN", pan),
                    ("Type of Enterprise", "Partnership Firm"),
                    ("Sector", "Services"),
                    ("Classification", "Micro"),
                    ("Investment (₹ crore)", "0.4"),
                    ("Turnover (₹ crore)", "1.2"),
                    ("Date of Issue", "2022-11-02"),
                    ("Address", "12 Anna Salai, Chennai 600002"),
                ],
                "Digitally signed."),
            "gst_cert": render_cert(
                "Goods and Services Tax Registration Certificate",
                "Government of India — GSTN (Provisional)",
                [
                    ("GSTIN", gstin),
                    ("Legal Name", "Borderline Traders"),
                    ("Trade Name", "BorderlineTraders"),
                    ("Registration Status", "Active"),
                    ("Date of Registration", "2022-11-20"),
                    ("Address", "12 Anna Salai, Chennai 600002"),
                    ("Principal Place of Business", "Tamil Nadu (33)"),
                ],
                "Digitally signed."),
            "pan_card": render_cert(
                "Permanent Account Number (PAN) Card",
                "Income Tax Department, Government of India",
                [
                    ("PAN", pan),
                    ("Name", "Borderline Trading House"),   # ← differs from Udyam cert name
                    ("Father/Spouse Name", "N/A"),
                    ("Date of Issue", "2022-10-05"),
                    ("Status", "Valid"),
                ],
                "Digitally signed."),
            "oem_auth": render_letter(
                "OEM Authorisation Letter",
                [
                    "To Whom It May Concern,",
                    "We, <b>HydroFlow Pumps Pvt. Ltd.</b> (OEM), hereby authorise "
                    "<b>Borderline Traders</b> as our authorised dealer for supply of "
                    "industrial pumps to GeM buyers.",
                    "Item Description: Industrial submersible pumps, 3HP-30HP.",
                    "This authorisation is valid from 2024-06-01 to 2027-05-31.",
                ],
                "S. Kumar, Managing Director, HydroFlow Pumps Pvt. Ltd."),
            "local_content": render_cert(
                "Make in India — Local Content Self-Certification",
                "As per DPIIT Public Procurement (Preference to Make in India) Order",
                [
                    ("Item", "Industrial submersible pumps"),
                    ("Declared Class", "I"),
                    ("Total Value (Rs. Lakh)", "50.0"),
                    ("Imported Content Value (Rs. Lakh)", "20.0"),
                    ("Claimed Local Content (%)", "60%"),
                    ("Date of Certification", today.isoformat()),
                    ("Declared By", "Borderline Traders"),
                ],
                "Self-certification — subject to verification."),
        }

    if bidder_key == "fraud":
        pan = make_pan("AAB", "F", "F")
        gstin = make_gstin("27", pan)
        return {
            "udyam": render_cert(
                "Udyam Registration Certificate",
                "Government of India — Ministry of Micro, Small & Medium Enterprises",
                [
                    ("Udyam Registration Number", "UDYAM-MH-27-0009876"),
                    ("Legal Name of Enterprise", "FraudFillers Traders"),
                    ("Trade Name", "FraudFillers"),
                    ("PAN", pan),
                    ("Type of Enterprise", "Partnership Firm"),
                    ("Sector", "Services"),
                    ("Classification", "Small"),
                    ("Investment (₹ crore)", "1.1"),
                    ("Turnover (₹ crore)", "9.0"),
                    ("Date of Issue", "2023-01-20"),
                    ("Address", "77 BKC, Bandra East, Mumbai 400051"),
                ],
                "Digitally signed."),
            # ← FORGED: signed, then modified after signing (incremental update)
            "gst_cert": tamper_after_signing(sign_pdf_bytes(
                render_cert(
                    "Goods and Services Tax Registration Certificate",
                    "Government of India — GSTN (Provisional)",
                    [
                        ("GSTIN", gstin),
                        ("Legal Name", "FraudFillers Traders"),
                        ("Trade Name", "FraudFillers"),
                        ("Registration Status", "Active"),
                        ("Date of Registration", "2023-02-14"),
                        ("Address", "77 BKC, Bandra East, Mumbai 400051"),
                        ("Principal Place of Business", "Maharashtra (27)"),
                    ],
                    "Digitally signed."),
                trust_root_path(), signer_key_path(),
                reason="GST Registration Certificate",
            )),
            "pan_card": render_cert(
                "Permanent Account Number (PAN) Card",
                "Income Tax Department, Government of India",
                [
                    ("PAN", pan),
                    ("Name", "FraudFillers Traders"),
                    ("Father/Spouse Name", "N/A"),
                    ("Date of Issue", "2023-01-05"),
                    ("Status", "Valid"),
                ],
                "Digitally signed."),
            "oem_auth": render_letter(
                "OEM Authorisation Letter",
                [
                    "To Whom It May Concern,",
                    "We, <b>PrimePumps Ltd.</b> (OEM), hereby authorise "
                    "<b>FraudFillers Traders</b> as our authorised reseller for supply of "
                    "industrial pumps to GeM buyers.",
                    "Item Description: Industrial high-pressure pumps.",
                    "This authorisation is valid from 2023-01-01 to 2025-12-31.",  # ← expired
                ],
                "A. Shah, Director, PrimePumps Ltd."),
            "local_content": render_cert(
                "Make in India — Local Content Self-Certification",
                "As per DPIIT Public Procurement (Preference to Make in India) Order",
                [
                    ("Item", "Industrial high-pressure pumps"),
                    ("Declared Class", "I"),
                    ("Total Value (Rs. Lakh)", "40.0"),
                    ("Imported Content Value (Rs. Lakh)", "30.0"),
                    ("Claimed Local Content (%)", "25%"),   # ← below Class I threshold
                    ("Date of Certification", today.isoformat()),
                    ("Declared By", "FraudFillers Traders"),
                ],
                "Self-certification — subject to verification."),
        }

    if bidder_key == "kaveri":
        pan = make_pan("AAK", "F", "K")
        gstin = make_gstin("29", pan)
        return {
            "udyam": render_cert(
                "Udyam Registration Certificate",
                "Government of India — Ministry of Micro, Small & Medium Enterprises",
                [
                    ("Udyam Registration Number", "UDYAM-KA-01-0002468"),
                    ("Legal Name of Enterprise", "Kaveri Engineering Works"),
                    ("Trade Name", "Kaveri Engg"),
                    ("PAN", pan),
                    ("Type of Enterprise", "Partnership Firm"),
                    ("Sector", "Manufacturing"),
                    ("Classification", "Micro"),
                    ("Investment (₹ crore)", "0.3"),
                    ("Turnover (₹ crore)", "0.9"),
                    ("Date of Issue", "2021-06-15"),
                    ("Address", "8 JC Road, Bengaluru 560002"),
                ],
                ""),   # ← scan only: NOT digitally signed
            "gst_cert": render_cert(
                "Goods and Services Tax Registration Certificate",
                "Government of India — GSTN (Provisional)",
                [
                    ("GSTIN", gstin),
                    ("Legal Name", "Kaveri Engineering Works"),
                    ("Trade Name", "Kaveri Engg"),
                    ("Registration Status", "Active"),
                    ("Date of Registration", "2021-07-01"),
                    ("Address", "8 JC Road, Bengaluru 560002"),
                    ("Principal Place of Business", "Karnataka (29)"),
                ],
                ""),   # ← scan only
            "pan_card": render_cert(
                "Permanent Account Number (PAN) Card",
                "Income Tax Department, Government of India",
                [
                    ("PAN", pan),
                    ("Name", "Kaveri Engineering Works"),
                    ("Father/Spouse Name", "N/A"),
                    ("Date of Issue", "2021-05-30"),
                    ("Status", "Valid"),
                ],
                "Digitally signed."),
            "startup": render_cert(
                "Startup Recognition Certificate",
                "DPIIT, Ministry of Commerce & Industry",
                [
                    ("Recognition Number", "DIPP87654321"),
                    ("Startup Name", "Kaveri Engineering Works"),
                    ("Status", "Active"),
                    ("Valid Until", "2025-01-01"),   # ← EXPIRED
                ],
                ""),
            "local_content": render_cert(
                "Make in India — Local Content Self-Certification",
                "As per DPIIT Public Procurement (Preference to Make in India) Order",
                [
                    ("Item", "Industrial pump spares"),
                    ("Declared Class", "I"),
                    ("Total Value (Rs. Lakh)", "100.0"),
                    ("Imported Content Value (Rs. Lakh)", "30.0"),
                    ("Claimed Local Content (%)", "70%"),
                    ("Date of Certification", today.isoformat()),
                    ("Declared By", "Kaveri Engineering Works"),
                ],
                "Self-certification — subject to verification."),
        }

    if bidder_key == "southern":
        pan = make_pan("AAP", "C", "S")
        gstin = make_gstin("33", pan)
        return {
            "udyam": render_cert(
                "Udyam Registration Certificate",
                "Government of India — Ministry of Micro, Small & Medium Enterprises",
                [
                    ("Udyam Registration Number", "UDYAM-TN-04-0001357"),
                    ("Legal Name of Enterprise", "Southern Pumps LLP"),
                    ("Trade Name", "Southern Pumps"),
                    ("PAN", pan),
                    ("Type of Enterprise", "LLP"),
                    ("Sector", "Manufacturing"),
                    ("Classification", "Small"),
                    ("Investment (₹ crore)", "3.0"),
                    ("Turnover (₹ crore)", "22.0"),
                    ("Date of Issue", "2022-09-30"),
                    ("Address", "45 Mount Road, Chennai 600006"),
                ],
                "Digitally signed."),
            "gst_cert": render_cert(
                "Goods and Services Tax Registration Certificate",
                "Government of India — GSTN (Provisional)",
                [
                    ("GSTIN", gstin),
                    ("Legal Name", "Southern Pumps LLP"),
                    ("Trade Name", "Southern Pumps"),
                    ("Registration Status", "Active"),
                    ("Date of Registration", "2022-10-10"),
                    ("Address", "45 Mount Road, Chennai 600006"),
                    ("Principal Place of Business", "Tamil Nadu (33)"),
                ],
                "Digitally signed."),
            "pan_card": render_cert(
                "Permanent Account Number (PAN) Card",
                "Income Tax Department, Government of India",
                [
                    ("PAN", pan),
                    ("Name", "Southern Pumps LLP"),
                    ("Father/Spouse Name", "N/A"),
                    ("Date of Issue", "2022-09-12"),
                    ("Status", "Valid"),
                ],
                "Digitally signed."),
            "cin": render_cert(
                "Certificate of Incorporation (LLP)",
                "Ministry of Corporate Affairs — ROC Chennai",
                [
                    ("LLPIN", "U11223TN2021NPL987654"),
                    ("LLP Name", "Southern Pumps LLP"),
                    ("Date of Incorporation", "2021-05-05"),
                    ("Registered Office", "45 Mount Road, Chennai 600006"),
                    ("Status", "Active"),
                ],
                "Digitally signed by ROC."),
            "local_content": render_cert(
                "Make in India — Local Content Self-Certification",
                "As per DPIIT Public Procurement (Preference to Make in India) Order",
                [
                    ("Item", "Industrial pumps — complete range"),
                    ("Declared Class", "I"),
                    ("Total Value (Rs. Lakh)", "120.0"),
                    ("Imported Content Value (Rs. Lakh)", "40.0"),
                    ("Claimed Local Content (%)", "67%"),
                    ("Date of Certification", today.isoformat()),
                    ("Declared By", "Southern Pumps LLP"),
                ],
                "Self-certification — subject to verification."),
        }


    if bidder_key == "frontrunner":
        pan = make_pan("AAF", "C", "F")
        gstin = make_gstin("27", pan)
        return {
            "udyam": render_cert(
                "Udyam Registration Certificate",
                "Government of India - Ministry of Micro, Small & Medium Enterprises",
                [
                    ("Udyam Registration Number", "UDYAM-MH-27-0003141"),
                    ("Legal Name of Enterprise", "FrontRunner Pumps Pvt. Ltd."),
                    ("Trade Name", "FrontRunner"),
                    ("PAN", pan),
                    ("Type of Enterprise", "Private Limited Company"),
                    ("Sector", "Services"),
                    ("Classification", "Small"),
                    ("Investment (Rs crore)", "2.0"),
                    ("Turnover (Rs crore)", "12.0"),
                    ("Date of Issue", "2023-08-10"),
                    ("Address", "91 Powai Plaza, Mumbai 400076"),
                ],
                "Digitally signed."),
            "gst_cert": render_cert(
                "Goods and Services Tax Registration Certificate",
                "Government of India - GSTN (Provisional)",
                [
                    ("GSTIN", gstin),
                    ("Legal Name", "FrontRunner Pumps Pvt. Ltd."),
                    ("Trade Name", "FrontRunner"),
                    ("Registration Status", "Active"),
                    ("Date of Registration", "2023-08-25"),
                    ("Address", "91 Powai Plaza, Mumbai 400076"),
                    ("Principal Place of Business", "Maharashtra (27)"),
                ],
                "Digitally signed."),
            "pan_card": render_cert(
                "Permanent Account Number (PAN) Card",
                "Income Tax Department, Government of India",
                [
                    ("PAN", pan),
                    ("Name", "FrontRunner Pumps Pvt. Ltd."),
                    ("Father/Spouse Name", "N/A"),
                    ("Date of Issue", "2023-08-02"),
                    ("Status", "Valid"),
                ],
                "Digitally signed."),
            "oem_auth": render_letter(
                "OEM Authorisation Letter",
                [
                    "To Whom It May Concern,",
                    "We, <b>TurbineFlow Systems Ltd.</b> (OEM), hereby authorise "
                    "<b>FrontRunner Pumps Pvt. Ltd.</b> as our authorised distributor for "
                    "supply of industrial pumps to GeM buyers.",
                    "Item Description: Industrial turbine pumps, 10HP-100HP.",
                    "This authorisation is valid from 2025-01-01 to 2028-12-31.",
                ],
                "K. Verma, Regional Manager, TurbineFlow Systems Ltd."),
            "local_content": render_cert(
                "Make in India - Local Content Self-Certification",
                "As per DPIIT Public Procurement (Preference to Make in India) Order",
                [
                    ("Item", "Industrial turbine pumps"),
                    ("Declared Class", "I"),
                    ("Total Value (Rs. Lakh)", "80.0"),
                    ("Imported Content Value (Rs. Lakh)", "25.0"),
                    ("Claimed Local Content (%)", "69%"),
                    ("Date of Certification", today.isoformat()),
                    ("Declared By", "FrontRunner Pumps Pvt. Ltd."),
                ],
                "Self-certification - subject to verification."),
        }

    if bidder_key == "quickspares":
        pan = make_pan("AAQ", "F", "Q")
        gstin = make_gstin("29", pan)
        return {
            "udyam": render_cert(
                "Udyam Registration Certificate",
                "Government of India - Ministry of Micro, Small & Medium Enterprises",
                [
                    ("Udyam Registration Number", "UDYAM-KA-01-0007159"),
                    ("Legal Name of Enterprise", "QuickSpares Trading Co."),
                    ("Trade Name", "QuickSpares"),
                    ("PAN", pan),
                    ("Type of Enterprise", "Partnership Firm"),
                    ("Sector", "Services"),
                    ("Classification", "Micro"),
                    ("Investment (Rs crore)", "0.6"),
                    ("Turnover (Rs crore)", "1.8"),
                    ("Date of Issue", "2022-12-05"),
                    ("Address", "33 MG Road, Bengaluru 560001"),
                ],
                "Digitally signed."),
            "gst_cert": render_cert(
                "Goods and Services Tax Registration Certificate",
                "Government of India - GSTN (Provisional)",
                [
                    ("GSTIN", gstin),
                    ("Legal Name", "QuickSpares Trading Co."),
                    ("Trade Name", "QuickSpares"),
                    ("Registration Status", "Active"),
                    ("Date of Registration", "2022-12-20"),
                    ("Address", "33 MG Road, Bengaluru 560001"),
                    ("Principal Place of Business", "Karnataka (29)"),
                ],
                "Digitally signed."),
            "pan_card": render_cert(
                "Permanent Account Number (PAN) Card",
                "Income Tax Department, Government of India",
                [
                    ("PAN", pan),
                    ("Name", "QuickSpares Trading Co."),
                    ("Father/Spouse Name", "N/A"),
                    ("Date of Issue", "2022-11-25"),
                    ("Status", "Valid"),
                ],
                "Digitally signed."),
            "oem_auth": render_letter(
                "OEM Authorisation Letter",
                [
                    "To Whom It May Concern,",
                    "We, <b>PrimeFlow Systems Ltd.</b> (OEM), hereby authorise "
                    "<b>QuickSpares Trading Co.</b> as our authorised dealer for supply of "
                    "industrial pumps to GeM buyers.",
                    "Item Description: Industrial turbine pumps, 10HP-100HP.",
                    "This authorisation is valid from 2025-02-01 to 2028-01-31.",
                ],
                "K. Verma, Regional Manager, PrimeFlow Systems Ltd."),
            "local_content": render_cert(
                "Make in India - Local Content Self-Certification",
                "As per DPIIT Public Procurement (Preference to Make in India) Order",
                [
                    ("Item", "Industrial turbine pumps"),
                    ("Declared Class", "I"),
                    ("Total Value (Rs. Lakh)", "90.0"),
                    ("Imported Content Value (Rs. Lakh)", "40.0"),
                    ("Claimed Local Content (%)", "56%"),
                    ("Date of Certification", today.isoformat()),
                    ("Declared By", "QuickSpares Trading Co."),
                ],
                "Self-certification - subject to verification."),
        }

    raise KeyError(bidder_key)


BIDDERS = {
    "clean": {
        "legal_name": "CleanCorp Industrial Solutions Pvt. Ltd.",
        "entity_type": "private_limited",
        "is_reseller": True,
        "bank_account": "HDFC00123456789",
        "phone": "+91 98200 10001",
        "pan": make_pan("AAB", "C", "C"),
        "gstin": make_gstin("27", make_pan("AAB", "C", "C")),
        "udyam_no": "UDYAM-MH-27-0001234",
        "cin": "U12345MH2023PLC123456",
        "epfo_no": "MH/12345/00678",
        "esic_no": "2712345678",
        "startup_no": "DIPP12345678",
        "nsic_no": "NSIC12345678",
    },
    "border": {
        "legal_name": "Borderline Traders",
        "entity_type": "partnership",
        "is_reseller": True,
        "bank_account": "ICICI00234567890",
        "phone": "+91 98410 20002",
        "pan": make_pan("AAV", "F", "B"),
        "gstin": make_gstin("33", make_pan("AAV", "F", "B")),
        "udyam_no": "UDYAM-TN-02-0005678",
        "cin": None,
        "epfo_no": "TN/45678/00321",
        "esic_no": None,
        "startup_no": None,
        "nsic_no": None,
    },
    "fraud": {
        "legal_name": "FraudFillers Traders",
        "entity_type": "partnership",
        "is_reseller": True,
        "bank_account": "SBI00345678901",
        "phone": "+91 98200 30003",
        "pan": make_pan("AAB", "F", "F"),
        "gstin": make_gstin("27", make_pan("AAB", "F", "F")),
        "udyam_no": "UDYAM-MH-27-0009876",
        "cin": "U54321TN2019PTC654321",
        "epfo_no": None,
        "esic_no": None,
        "startup_no": None,
        "nsic_no": None,
    },
    "kaveri": {
        "legal_name": "Kaveri Engineering Works",
        "entity_type": "partnership",
        "is_reseller": False,
        "bank_account": "CANARA00456789012",
        "phone": "+91 98860 40004",
        "pan": make_pan("AAK", "F", "K"),
        "gstin": make_gstin("29", make_pan("AAK", "F", "K")),
        "udyam_no": "UDYAM-KA-01-0002468",
        "cin": None,
        "epfo_no": None,
        "esic_no": None,
        "startup_no": "DIPP87654321",
        "nsic_no": None,
    },
    "southern": {
        "legal_name": "Southern Pumps LLP",
        "entity_type": "llp",
        "is_reseller": False,
        "bank_account": "AXIS00567890123",
        "phone": "+91 98410 50005",
        "pan": make_pan("AAP", "C", "S"),
        "gstin": make_gstin("33", make_pan("AAP", "C", "S")),
        "udyam_no": "UDYAM-TN-04-0001357",
        "cin": "U11223TN2021NPL987654",
        "epfo_no": None,
        "esic_no": None,
        "startup_no": None,
        "nsic_no": None,
    },
    "frontrunner": {
        "legal_name": "FrontRunner Pumps Pvt. Ltd.",
        "entity_type": "private_limited",
        "is_reseller": True,
        "pan": make_pan("AAF", "C", "F"),
        "gstin": make_gstin("27", make_pan("AAF", "C", "F")),
        "udyam_no": "UDYAM-MH-27-0003141",
        "cin": None,
        "epfo_no": None,
        "esic_no": None,
        "startup_no": None,
        "nsic_no": None,
        "bank_account": "HDFC50200012345678",
        "phone": "+91 98220 61001",
    },
    "quickspares": {
        "legal_name": "QuickSpares Trading Co.",
        "entity_type": "partnership",
        "is_reseller": True,
        "pan": make_pan("AAQ", "F", "Q"),
        "gstin": make_gstin("29", make_pan("AAQ", "F", "Q")),
        "udyam_no": "UDYAM-KA-01-0007159",
        "cin": None,
        "epfo_no": None,
        "esic_no": None,
        "startup_no": None,
        "nsic_no": None,
        "bank_account": "HDFC50200012345678",
        "phone": "+91 98450 72002",
    },
}
TENDER = {
    "gem_ref": "GEM/2026/B/1234567",
    "title": "Supply of Industrial Pumps",
    "buyer_org": "Chennai Petroleum Corporation Limited",
    "eligibility_json": {
        "clause": "Bidders must hold valid Udyam registration, GST registration with "
                  "filed returns, PAN, and be compliant with Make-in-India local content "
                  "class requirements. OEM authorisation required for reseller bids.",
    },
    "local_content_class_required": "I",
    "msme_only": False,
    "min_turnover_crore": 50.0,
    "required_docs_json": ["udyam", "gst_cert", "pan_card", "oem_auth", "local_content"],
}


def _make_rogue_ca() -> tuple[Path, Path]:
    """Self-signed CA with a different CN — used to demo issuer-mismatch forgeries."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    from app.core.config import settings

    certs = Path(settings.certs_dir)
    ca_path = certs / "rogue_ca.pem"
    key_path = certs / "rogue_ca_key.pem"
    if ca_path.exists() and key_path.exists():
        return ca_path, key_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "FraudCorp Digital Signing Services")])
    now = datetime.now()
    ca = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
        .add_extension(
            x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True,
                          content_commitment=True, key_encipherment=False,
                          data_encipherment=False, key_agreement=False,
                          encipher_only=False, decipher_only=False),
            True,
        )
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                           serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    return ca_path, key_path


def generate(force: bool = False) -> None:
    OUT_DOCS.mkdir(parents=True, exist_ok=True)
    OUT_PORTAL.parent.mkdir(parents=True, exist_ok=True)

    # portal dataset
    portal = build_portal_data()
    OUT_PORTAL.write_text(json.dumps(portal, indent=2, default=str), encoding="utf-8")

    # CA (demo) + rogue CA for issuer-mismatch demo
    ca_path, ca_key = ensure_demo_ca()
    rogue_ca, rogue_key = _make_rogue_ca()
    print(f"[generate] trust root: {ca_path}")
    print(f"[generate] rogue CA (issuer-mismatch demo): {rogue_ca}")

    manifest: dict[str, list[str]] = {}
    for key in BIDDERS:
        docs = build_docs(key)
        manifest[key] = []
        for doc_type, pdf_bytes in docs.items():
            if key == "kaveri":
                pass  # unsigned scans (uploaded by hand, not signed)
            elif key == "fraud" and doc_type == "gst_cert":
                pass  # already signed (demo CA) then tampered in build_docs
            elif key == "fraud" and doc_type == "udyam":
                pdf_bytes = sign_pdf_bytes(pdf_bytes, rogue_ca, rogue_key,
                                           reason="Udyam Registration Certificate")
            else:
                pdf_bytes = sign_pdf_bytes(pdf_bytes, ca_path, ca_key)
            name = f"{key}_{doc_type}.pdf"
            (OUT_DOCS / name).write_bytes(pdf_bytes)
            manifest[key].append(name)
        print(f"[generate] {key}: {', '.join(manifest[key])}")

    print(f"[generate] portal dataset -> {OUT_PORTAL}")
    print(f"[generate] documents    -> {OUT_DOCS}")


if __name__ == "__main__":
    generate()