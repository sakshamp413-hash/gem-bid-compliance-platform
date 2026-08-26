"""
Officer-facing "Explainability Report" (PDF) — a signed-off artifact for
the procurement file.

Renders: bidder + tender header, compliance score/risk/recommendation,
the applicable-check table (result, confidence, summary, rule ref),
cross-verification findings, document signature/tamper status, and the
current audit-chain head hash in the footer so the PDF is verifiable
against `/audit/verify`.
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from sqlalchemy.orm import Session

from app.ai.cross_verify import run_cross_verify
from app.models.audit import AuditLog
from app.models.bid_submission import BidSubmission
from app.models.bidder import Bidder
from app.models.compliance_assessment import ComplianceAssessment
from app.models.document import Document
from app.models.tender import Tender
from app.models.verification_check import VerificationCheck

CHECK_LABELS = {
    "udyam": "Udyam / MSME", "gst": "GST (incl. return filing)", "pan": "PAN / Income-Tax",
    "mca": "MCA21 (CIN)", "local_content": "Make-in-India local content",
    "epfo": "EPFO", "esic": "ESIC", "startup": "Startup India (DPIIT)",
    "nsic": "NSIC", "oem": "OEM authorization",
    "digilocker": "DigiLocker / document integrity", "blacklist": "Blacklisting / debarment",
}


def _findings_for(db: Session, submission: BidSubmission) -> list[dict]:
    docs = db.query(Document).filter(Document.submission_id == submission.id).all()
    bidder = db.get(Bidder, submission.bidder_id)
    checks = (
        db.query(VerificationCheck)
        .filter(VerificationCheck.submission_id == submission.id)
        .order_by(VerificationCheck.id)
        .all()
    )
    pack: dict[str, list[dict]] = {}
    for doc in docs:
        entry = dict(doc.extracted_json or {})
        entry["_doc_id"] = doc.id
        pack.setdefault(doc.doc_type, []).append(entry)
    evidence = {
        "bidder": {"legal_name": bidder.legal_name, "entity_type": bidder.entity_type,
                   "pan": bidder.pan, "gstin": bidder.gstin,
                   "udyam_no": bidder.udyam_no, "cin": bidder.cin},
        "documents": pack,
        "portal": {},
        "checks": [{"check_type": c.check_type, "result": c.result,
                    "summary": (c.evidence_json or {}).get("summary", "")}
                   for c in checks],
    }
    return run_cross_verify(evidence)["findings"]


def build_report_pdf(db: Session, submission_id: int) -> bytes:
    """Render the compliance report PDF. Returns raw bytes."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    sub = db.get(BidSubmission, submission_id)
    if sub is None:
        raise ValueError("submission not found")
    tender = db.get(Tender, sub.tender_id)
    bidder = db.get(Bidder, sub.bidder_id)
    assessment = (
        db.query(ComplianceAssessment)
        .filter(ComplianceAssessment.submission_id == sub.id)
        .order_by(ComplianceAssessment.id.desc())
        .first()
    )
    checks = (
        db.query(VerificationCheck)
        .filter(VerificationCheck.submission_id == sub.id)
        .order_by(VerificationCheck.id)
        .all()
    )
    docs = db.query(Document).filter(Document.submission_id == sub.id).all()
    findings = _findings_for(db, sub)

    audit_head = db.query(AuditLog).order_by(AuditLog.seq.desc()).first()
    audit_hash = audit_head.this_hash if audit_head else "no audit records"

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=15, leading=19,
                        textColor=colors.HexColor("#0f2a4a"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11.5, leading=15,
                        textColor=colors.HexColor("#1a4a8a"), spaceBefore=10, spaceAfter=4)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8, leading=11)
    mono = ParagraphStyle("mono", fontName="Courier", fontSize=7.5, leading=10,
                          textColor=colors.HexColor("#555555"))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm,
                            title="Bid Compliance Verification Report",
                            author="GeM Bid Compliance Verification Platform")

    story = [
        Paragraph("Bid Compliance Verification Report", h1),
        Paragraph(
            f"GeM Bid Compliance Verification Platform &nbsp;·&nbsp; generated "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;·&nbsp; "
            f"submission #{sub.id}",
            small,
        ),
        Spacer(1, 8),
        Paragraph("Tender & bidder", h2),
    ]

    def kv_table(rows: list[tuple[str, str]]) -> Table:
        t = Table([[Paragraph(f"<b>{k}</b>", small), Paragraph(v, small)] for k, v in rows],
                  colWidths=[52 * mm, 118 * mm])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f8")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    story.append(kv_table([
        ("Tender", f"{tender.title} · {tender.gem_ref}"),
        ("Buyer", tender.buyer_org),
        ("Bidder", bidder.legal_name),
        ("Entity type", bidder.entity_type),
        ("PAN", bidder.pan or "—"),
        ("GSTIN", bidder.gstin or "—"),
        ("Udyam", bidder.udyam_no or "—"),
        ("CIN", bidder.cin or "—"),
        ("Local content class required", tender.local_content_class_required or "none"),
    ]))

    story.append(Paragraph("Assessment summary", h2))
    if assessment:
        story.append(kv_table([
            ("Compliance score", f"{assessment.score:.1f} / 100"),
            ("Risk level", assessment.risk_level.upper()),
            ("Recommendation", (assessment.recommendation_action or "—").replace("_", " ").upper()),
            ("Recommendation confidence", f"{round((assessment.recommendation_confidence or 0) * 100)}%"),
            ("AI provider (model_meta)", str((assessment.model_meta_json or {}).get("llm"))),
        ]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Recommendation text:</b> {assessment.recommendation_text or '—'}", small))
    else:
        story.append(Paragraph("No assessment available for this submission.", small))

    story.append(Paragraph(f"Compliance checks ({len(checks)})", h2))
    if checks:
        rows = [[Paragraph("<b>#</b>", small), Paragraph("<b>Check</b>", small),
                 Paragraph("<b>Result</b>", small), Paragraph("<b>Conf</b>", small),
                 Paragraph("<b>Summary / evidence</b>", small),
                 Paragraph("<b>Rule</b>", small)]]
        for i, c in enumerate(checks, 1):
            ev = (c.evidence_json or {})
            summary = ev.get("summary", "")
            rows.append([
                Paragraph(str(i), small),
                Paragraph(CHECK_LABELS.get(c.check_type, c.check_type), small),
                Paragraph(c.result.upper(), small),
                Paragraph(f"{round(c.confidence * 100)}%", small),
                Paragraph(summary[:220], small),
                Paragraph(c.rule_ref or "—", small),
            ])
        t = Table(rows, colWidths=[7 * mm, 30 * mm, 15 * mm, 13 * mm, 90 * mm, 15 * mm],
                  repeatRows=1)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f8")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)

    story.append(Paragraph(f"Cross-verification findings ({len(findings)})", h2))
    if findings:
        for f in findings:
            sev = str(f.get("severity", "")).upper()
            story.append(Paragraph(
                f"<b>[{sev}]</b> {f.get('message', '')} "
                f"<font size='7' color='#666666'>({f.get('rule_ref', '')}, "
                f"conf {round(float(f.get('confidence', 0)) * 100)}%)</font>",
                small,
            ))
    else:
        story.append(Paragraph("No findings.", small))

    story.append(Paragraph(f"Documents ({len(docs)})", h2))
    if docs:
        rows = [[Paragraph("<b>Document</b>", small), Paragraph("<b>Signature</b>", small),
                 Paragraph("<b>Tampered</b>", small), Paragraph("<b>OCR</b>", small)]]
        for d in docs:
            tampered = (d.tamper_flags_json or {}).get("tampered", False)
            rows.append([
                Paragraph(f"{d.doc_type} ({d.file_name})", small),
                Paragraph(d.signature_status.upper(), small),
                Paragraph("YES" if tampered else "no", small),
                Paragraph(f"{d.ocr_source} · {round((d.ocr_confidence or 0) * 100)}%", small),
            ])
        t = Table(rows, colWidths=[80 * mm, 35 * mm, 22 * mm, 33 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f8")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)

    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "This report is AI-assisted decision support. The final decision is recorded by the "
        "procurement officer and chained into the audit log. Verify report integrity against "
        "the audit-chain head hash below via /audit/verify.", small))
    story.append(Paragraph(f"audit head (seq {audit_head.seq if audit_head else 0}): {audit_hash}", mono))

    doc.build(story)
    return buf.getvalue()