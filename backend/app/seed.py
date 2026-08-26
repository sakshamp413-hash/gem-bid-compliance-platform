"""
Seed script: loads demo users, tender, 5 bidders + documents, and runs the
full verification pipeline — so `docker compose up` → dashboard works
immediately, fully offline.

Usage:  python -m app.seed   (from backend/)
"""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.logging import configure_logging, get_logger
from app.db.audit import append_audit
from app.db.session import SessionLocal, init_db
from app.models.bid_submission import BidSubmission
from app.models.bidder import Bidder
from app.models.tender import Tender
from app.models.user import User
from app.services.document_service import process_uploaded_document
from app.services.pipeline import run_verification

configure_logging()
logger = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "data" / "docs"

DEMO_USERS = [
    ("Aarav Officer", "officer@gem.gov.in", "officer", "GeM@2026!officer"),
    ("Priya Admin", "admin@gem.gov.in", "admin", "GeM@2026!admin"),
    ("Vikram Auditor", "auditor@gem.gov.in", "auditor", "GeM@2026!auditor"),
]

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

# bidder key -> (document types to upload)
BIDDER_DOCS = {
    "clean": ["udyam", "gst_cert", "pan_card", "cin", "oem_auth", "local_content",
              "epfo", "esic", "startup", "nsic"],
    "border": ["udyam", "gst_cert", "pan_card", "oem_auth", "local_content"],
    "fraud": ["udyam", "gst_cert", "pan_card", "oem_auth", "local_content"],
    "kaveri": ["udyam", "gst_cert", "pan_card", "startup", "local_content"],
    "southern": ["udyam", "gst_cert", "pan_card", "cin", "local_content"],
    "frontrunner": ["udyam", "gst_cert", "pan_card", "oem_auth", "local_content"],
    "quickspares": ["udyam", "gst_cert", "pan_card", "oem_auth", "local_content"],
}


def _make_bidder(seed_key: str) -> dict:
    """Mirrors data/generate.py BIDDERS (kept here so seeding is standalone)."""
    from data.generate import BIDDERS  # backend/ is on sys.path in this env

    return dict(BIDDERS[seed_key])


def seed(db: Session) -> None:
    # --- users -----------------------------------------------------------
    for name, email, role, password in DEMO_USERS:
        if not db.query(User).filter(User.email == email).first():
            db.add(User.create(name, email, role, password))
    db.commit()
    logger.info("users seeded")

    # --- tender ----------------------------------------------------------
    tender = db.query(Tender).filter(Tender.gem_ref == TENDER["gem_ref"]).first()
    if tender is None:
        tender = Tender(**TENDER)
        db.add(tender)
        db.commit()
        db.refresh(tender)
    logger.info("tender ready: %s", tender.gem_ref)

    # --- bidders + submissions + documents + pipeline --------------------
    for seed_key, doc_types in BIDDER_DOCS.items():
        bidder_data = _make_bidder(seed_key)
        bidder = Bidder(**bidder_data)
        db.add(bidder)
        db.flush()
        sub = BidSubmission(tender_id=tender.id, bidder_id=bidder.id, status="submitted")
        db.add(sub)
        db.commit()
        db.refresh(sub)

        for doc_type in doc_types:
            path = DOCS_DIR / f"{seed_key}_{doc_type}.pdf"
            if not path.exists():
                logger.warning("missing doc %s — skipping", path.name)
                continue
            process_uploaded_document(
                db, sub.id, doc_type, path.name, path.read_bytes(),
                actor=f"seed:{seed_key}",
            )
        run_verification(db, sub, actor=f"seed:{seed_key}")
        from app.models.compliance_assessment import ComplianceAssessment

        assessment = (
            db.query(ComplianceAssessment)
            .filter(ComplianceAssessment.submission_id == sub.id)
            .order_by(ComplianceAssessment.id.desc())
            .first()
        )
        logger.info(
            "seeded %-10s score=%.1f risk=%s action=%s",
            seed_key, assessment.score, assessment.risk_level,
            assessment.recommendation_action,
        )

    append_audit(db, actor="seed", action="seed_demo", entity="system",
                 payload={"tender": TENDER["gem_ref"]})


def _ensure_dataset() -> None:
    """Regenerate the synthetic dataset if missing or stale (fresh clones)."""
    portal = REPO_ROOT / "data" / "mock_portal.json"
    docs = list((REPO_ROOT / "data" / "docs").glob("*.pdf"))
    certs = list((REPO_ROOT / "backend" / "storage" / "certs").glob("demo_ca.pem"))
    if not portal.exists() or len(docs) < 25 or not certs:
        logger.info("dataset incomplete — regenerating via data/generate.py")
        sys.path.insert(0, str(REPO_ROOT))
        from data.generate import generate

        generate()
        logger.info("dataset regenerated")


def main() -> None:
    _ensure_dataset()
    init_db()
    with SessionLocal() as db:
        seed(db)
    print("seed complete — login: officer@gem.gov.in / GeM@2026!officer")


if __name__ == "__main__":
    sys.path.insert(0, str(REPO_ROOT))
    main()