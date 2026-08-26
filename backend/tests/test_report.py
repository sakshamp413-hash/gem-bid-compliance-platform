"""
Tests: officer explainability report (PDF export) + footer audit hash.
"""
import io

from pypdf import PdfReader

from app.db.audit import verify_chain
from app.db.session import SessionLocal
from app.models.audit import AuditLog
from app.models.bid_submission import BidSubmission
from app.models.compliance_assessment import ComplianceAssessment
from app.services.report_service import build_report_pdf


def _seed_demo():
    from app.db.session import init_db
    from app.seed import seed

    init_db()
    with SessionLocal() as db:
        if db.query(BidSubmission).count() == 0:
            seed(db)


def _sub_id(db) -> int:
    return db.query(BidSubmission).order_by(BidSubmission.id).first().id


def test_report_pdf_renders_for_assessed_submission():
    _seed_demo()
    with SessionLocal() as db:
        sid = _sub_id(db)
        asc = (
            db.query(ComplianceAssessment)
            .filter(ComplianceAssessment.submission_id == sid)
            .order_by(ComplianceAssessment.id.desc())
            .first()
        )
        pdf = build_report_pdf(db, sid)
        assert pdf[:5] == b"%PDF-"
        text = ""
        for page in PdfReader(io.BytesIO(pdf)).pages:
            text += page.extract_text() or ""
        assert "Compliance Verification Report" in text
        # the report's cited score/action must match the assessment
        assert f"{asc.score:.1f}" in text
        assert asc.recommendation_action.replace("_", " ").upper() in text
        assert "audit head" in text


def test_report_footer_hash_matches_audit_chain_head():
    _seed_demo()
    with SessionLocal() as db:
        sid = _sub_id(db)
        pdf = build_report_pdf(db, sid)
        text = ""
        for page in PdfReader(io.BytesIO(pdf)).pages:
            text += page.extract_text() or ""
        head = db.query(AuditLog).order_by(AuditLog.seq.desc()).first()
        assert head is not None
        assert head.this_hash in text
        assert verify_chain(db)["valid"] is True


def test_report_endpoint_via_api(client):
    _seed_demo()
    from tests.conftest import auth_headers, login

    tok = login(client)
    h = auth_headers(tok["access_token"])
    subs = client.get("/submissions", headers=h).json()
    assert len(subs) >= 7
    sid = subs[0]["id"]
    r = client.get(f"/submissions/{sid}/report.pdf", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:5] == b"%PDF-"