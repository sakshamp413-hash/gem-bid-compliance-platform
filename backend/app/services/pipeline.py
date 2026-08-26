"""
Verification pipeline — orchestrates the full compliance assessment:

  documents (extracted + signed/tamper analyzed)
    → applicable checklist (rule engine)
    → run each check module (evidence-linked)
    → AI cross-verification (findings)
    → weighted score + risk + pending
    → recommendation (AI, decision-support only)
    → persist + hash-chained audit trail
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.cross_verify import run_cross_verify
from app.ai.recommendation import generate_recommendation
from app.db.audit import append_audit
from app.integration.adapter import get_adapter
from app.models.bid_submission import BidSubmission
from app.models.compliance_assessment import ComplianceAssessment
from app.models.document import Document
from app.models.verification_check import VerificationCheck
from app.rules.engine import get_rule_store
from app.rules.scoring import compute_score
from app.services.checks.base import check_registry
from app.core.logging import get_logger

logger = get_logger(__name__)


def _document_pack(docs: list[Document]) -> dict[str, list[dict]]:
    """
    doc_type -> [extracted dict] for check modules.
    Extracted fields are flattened to the top level (checks read
    doc["field"]), while the structured "fields" map is kept for the
    cross-verification engine and evidence drill-down.
    """
    pack: dict[str, list[dict]] = {}
    for doc in docs:
        entry = dict(doc.extracted_json or {})
        fields = entry.pop("fields", None) or {}
        for key, val in fields.items():
            if isinstance(val, dict):
                entry[key] = val.get("value")
            else:
                entry[key] = val
        entry["fields"] = fields
        entry["_doc_id"] = doc.id
        entry["_signature_status"] = doc.signature_status
        entry["_tamper_flags"] = doc.tamper_flags_json
        pack.setdefault(doc.doc_type, []).append(entry)
    return pack


def _evidence_pack(submission, tender, bidder, docs, checks, portal_summary) -> dict:
    """Serializable evidence pack for cross-verification + LLM passes."""
    return {
        "bidder": {
            "legal_name": bidder.legal_name,
            "entity_type": bidder.entity_type,
            "pan": bidder.pan,
            "gstin": bidder.gstin,
            "udyam_no": bidder.udyam_no,
            "cin": bidder.cin,
        },
        "documents": _document_pack(docs),
        "portal": portal_summary,
        "checks": [c.to_dict() for c in checks] if checks else [],
    }


def _portal_summary(submission, bidder, adapter) -> dict[str, dict]:
    """Re-query portal for key registries (dedup: reuse stored portal responses)."""
    summary: dict[str, dict] = {}
    pairs = [
        ("udyam", ("verify_udyam", getattr(bidder, "udyam_no", None))),
        ("gstin", ("verify_gstin", getattr(bidder, "gstin", None))),
        ("pan", ("verify_pan", getattr(bidder, "pan", None))),
        ("mca", ("mca_company", getattr(bidder, "cin", None))),
    ]
    for key, (method, value) in pairs:
        if not value:
            continue
        try:
            resp = getattr(adapter, method)(value)
            summary[key] = resp.to_dict()
        except Exception as exc:
            logger.warning("portal %s lookup failed: %s", method, exc)
    return summary


def run_verification(db: Session, submission: BidSubmission, actor: str = "system") -> ComplianceAssessment:
    """
    Execute the full pipeline for a submission. Idempotent: re-running
    replaces previous checks/assessments with fresh records.
    """
    from app.models.tender import Tender
    from app.models.bidder import Bidder

    tender = db.get(Tender, submission.tender_id)
    bidder = db.get(Bidder, submission.bidder_id)
    docs = (
        db.query(Document).filter(Document.submission_id == submission.id).all()
    )

    adapter = get_adapter()
    rules = get_rule_store().current
    doc_pack = _document_pack(docs)
    doc_types = set(doc_pack.keys())

    # idempotent re-run: clear previous pipeline output for this submission
    db.query(VerificationCheck).filter(
        VerificationCheck.submission_id == submission.id
    ).delete()
    db.query(ComplianceAssessment).filter(
        ComplianceAssessment.submission_id == submission.id
    ).delete()
    db.commit()

    # 1) applicable checklist
    applicable = rules.applicable_checks(tender, bidder, doc_types)
    logger.info(
        "pipeline submission=%s applicable=%s", submission.id, applicable
    )

    # 2) run check modules
    registry = check_registry()
    context = type(
        "CheckContext",
        (),
        {
            "submission": submission,
            "tender": tender,
            "bidder": bidder,
            "documents": doc_pack,
            "adapter": adapter,
            "rules": rules,
        },
    )()

    check_outputs: list[Any] = []
    for ctype in applicable:
        fn = registry.get(ctype)
        if fn is None:
            continue
        try:
            out = fn(context)
            out.check_type = ctype
        except Exception as exc:
            logger.exception("check %s failed: %s", ctype, exc)
            from app.services.checks.base import CheckOutput

            out = CheckOutput(check_type=ctype, result="flag",
                              confidence=0.5,
                              summary=f"check module error: {exc}",
                              rule_ref="SYSTEM/error")
        check_outputs.append(out)
        db.add(VerificationCheck(
            submission_id=submission.id,
            check_type=out.check_type,
            result=out.result,
            confidence=out.confidence,
            evidence_json={"evidence": [e.to_dict() for e in out.evidence],
                           "summary": out.summary},
            rule_ref=out.rule_ref,
            portal_response_json=out.portal_response,
        ))

    # 3) AI cross-verification
    portal_summary = _portal_summary(submission, bidder, adapter)
    evidence_pack = _evidence_pack(submission, tender, bidder, docs, check_outputs, portal_summary)
    cross = run_cross_verify(evidence_pack)

    # 4) score + risk + pending
    weights = rules.weights
    scoring = compute_score([c.to_dict() for c in check_outputs], weights, rules)

    # 5) recommendation
    assessment_data = {
        "score": scoring["score"],
        "risk_level": scoring["risk_level"],
        "hard_fail": scoring["hard_fail"],
        "checks": [c.to_dict() for c in check_outputs],
        "findings": cross["findings"],
    }
    rec = generate_recommendation(assessment_data)

    assessment = ComplianceAssessment(
        submission_id=submission.id,
        score=scoring["score"],
        risk_level=scoring["risk_level"],
        pending_json=scoring["pending"],
        recommendation_text=rec["text"],
        recommendation_action=rec["action"],
        recommendation_confidence=rec["confidence"],
        model_meta_json={
            "llm": rec["model_meta"],
            "cross_verify": cross["model_meta"],
            "scoring_detail": scoring["detail"],
        },
    )
    db.add(assessment)
    submission.status = "assessed"
    db.commit()
    db.refresh(assessment)

    append_audit(
        db,
        actor=actor,
        action="assess_submission",
        entity=f"submission:{submission.id}",
        payload={"score": assessment.score, "risk": assessment.risk_level,
                 "action": assessment.recommendation_action,
                 "checks": [c.check_type for c in check_outputs]},
    )
    return assessment