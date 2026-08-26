"""
Integration test: full pipeline on the three demo bidders (Section 12)
plus document ingestion + extraction.
"""
from pathlib import Path

from app.ai.extraction import extract_fields_deterministic
from app.db.audit import verify_chain
from app.db.session import SessionLocal, init_db
from app.models.bidder import Bidder
from app.models.bid_submission import BidSubmission
from app.models.compliance_assessment import ComplianceAssessment
from app.models.tender import Tender
from app.models.user import User
from app.models.verification_check import VerificationCheck
from app.seed import BIDDER_DOCS, seed
from app.services.pipeline import run_verification

REPO = Path(__file__).resolve().parent.parent.parent


def _seed_once():
    init_db()
    with SessionLocal() as db:
        if db.query(BidSubmission).count() == 0:
            seed(db)


def _by_name(db, name_fragment: str):
    for sub in db.query(BidSubmission).all():
        bidder = db.get(Bidder, sub.bidder_id)
        if name_fragment.lower() in bidder.legal_name.lower():
            return sub, bidder
    raise AssertionError(f"no submission for {name_fragment}")


def _checks(db, sub_id):
    return {
        c.check_type: c for c in
        db.query(VerificationCheck).filter_by(submission_id=sub_id).all()
    }


def test_clean_corp_qualifies():
    _seed_once()
    with SessionLocal() as db:
        sub, _ = _by_name(db, "CleanCorp")
        asc = db.query(ComplianceAssessment).filter_by(submission_id=sub.id) \
            .order_by(ComplianceAssessment.id.desc()).first()
        assert asc.score >= 90
        assert asc.risk_level == "low"
        assert asc.recommendation_action == "qualify"
        checks = _checks(db, sub.id)
        assert checks["digilocker"].result == "pass"
        assert checks["blacklist"].result == "pass"
        assert all(c.result != "fail" for c in checks.values())


def test_borderline_traders_flagged_for_review():
    _seed_once()
    with SessionLocal() as db:
        sub, _ = _by_name(db, "Borderline")
        asc = db.query(ComplianceAssessment).filter_by(submission_id=sub.id) \
            .order_by(ComplianceAssessment.id.desc()).first()
        assert asc.risk_level == "medium"
        assert asc.recommendation_action == "needs_review"
        checks = _checks(db, sub.id)
        assert checks["gst"].result == "flag"          # returns not filed
        assert "not filed" in (checks["gst"].evidence_json or {}).get("summary", "").lower()


def test_fraud_fillers_hard_fail():
    _seed_once()
    with SessionLocal() as db:
        sub, _ = _by_name(db, "FraudFillers")
        asc = db.query(ComplianceAssessment).filter_by(submission_id=sub.id) \
            .order_by(ComplianceAssessment.id.desc()).first()
        assert asc.risk_level == "high"
        assert asc.recommendation_action == "disqualify_candidate"
        checks = _checks(db, sub.id)
        assert checks["blacklist"].result == "fail"    # debarment hit
        assert checks["gst"].result == "fail"          # cancelled registration
        assert checks["digilocker"].result == "fail"   # forged cert caught


def test_document_extraction_fields():
    from app.ai.extraction import extract_document

    doc = extract_document(str(REPO / "data" / "docs" / "clean_udyam.pdf"), "udyam")
    fields = {k: v["value"] for k, v in doc["fields"].items()}
    assert fields["udyam_no"] == "UDYAM-MH-27-0001234"
    assert fields["legal_name"] == "CleanCorp Industrial Solutions Pvt. Ltd."
    assert fields["pan"] == "AABCC1234K"


def test_deterministic_extractor_no_model():
    text = (
        "Udyam Registration Certificate\n"
        "Udyam Registration Number UDYAM-MH-27-0001234\n"
        "Legal Name of Enterprise CleanCorp Industrial Solutions Pvt. Ltd.\n"
        "PAN AABCC1234K\nClassification Small\n"
        "Investment (Rs crore) 2.4\nTurnover (Rs crore) 18.5\n"
    )
    out = extract_fields_deterministic("udyam", text)
    assert out["udyam_no"]["value"] == "UDYAM-MH-27-0001234"
    assert out["legal_name"]["value"] == "CleanCorp Industrial Solutions Pvt. Ltd."
    assert out["classification"]["value"] == "Small"
    assert out["investment_crore"]["value"] == "2.4"


def test_pipeline_is_idempotent_and_audited():
    _seed_once()
    with SessionLocal() as db:
        sub, _ = _by_name(db, "Southern")
        n_before = db.query(VerificationCheck).filter_by(submission_id=sub.id).count()
        run_verification(db, sub, actor="test")
        n_after = db.query(VerificationCheck).filter_by(submission_id=sub.id).count()
        assert n_after == n_before  # stale rows cleared
        assert verify_chain(db)["valid"] is True