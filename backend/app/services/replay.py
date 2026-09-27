"""
Decision Replay Engine (F06) — step-by-step verification playback for auditors.

Reconstructs the complete decision trail for a submission in a
chronological, explainable sequence of steps that an auditor can follow.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)


def _check_result_icon(result: str) -> str:
    return {"pass": "✅", "fail": "❌", "flag": "⚠️", "na": "⬜"}.get(result, "❓")


def reconstruct_decision_replay(db: Session, submission_id: int) -> dict[str, Any]:
    """
    Build a deterministic, step-by-step replay of the compliance decision
    for the given submission.

    Returns:
      {
        submission_id, bidder_name, tender_ref,
        steps: [
          {seq, timestamp, actor, event_type, title, detail, result, rule_ref}
        ],
        summary: {total_steps, pass_count, fail_count, flag_count,
                  final_score, final_recommendation, final_decision}
      }
    """
    from app.models.bid_submission import BidSubmission
    from app.models.bidder import Bidder
    from app.models.compliance_assessment import ComplianceAssessment
    from app.models.document import Document
    from app.models.officer_decision import OfficerDecision
    from app.models.tender import Tender
    from app.models.verification_check import VerificationCheck

    sub = db.get(BidSubmission, submission_id)
    if sub is None:
        raise ValueError(f"Submission {submission_id} not found")

    bidder = db.get(Bidder, sub.bidder_id)
    tender = db.get(Tender, sub.tender_id)
    docs = db.query(Document).filter(Document.submission_id == submission_id).all()
    checks = (
        db.query(VerificationCheck)
        .filter(VerificationCheck.submission_id == submission_id)
        .order_by(VerificationCheck.id)
        .all()
    )
    assessment = (
        db.query(ComplianceAssessment)
        .filter(ComplianceAssessment.submission_id == submission_id)
        .order_by(ComplianceAssessment.id.desc())
        .first()
    )
    decisions = (
        db.query(OfficerDecision)
        .filter(OfficerDecision.submission_id == submission_id)
        .order_by(OfficerDecision.id)
        .all()
    )

    steps: list[dict[str, Any]] = []
    seq = 0

    # Step 0: Submission received
    seq += 1
    steps.append({
        "seq": seq,
        "timestamp": sub.submitted_at.isoformat() if sub.submitted_at else None,
        "actor": "system",
        "event_type": "submission_received",
        "title": "Bid Submission Received",
        "detail": (
            f"Bidder '{bidder.legal_name if bidder else '?'}' submitted for "
            f"tender '{tender.gem_ref if tender else '?'}' — "
            f"{tender.title[:80] if tender else ''}."
        ),
        "result": "info",
        "rule_ref": None,
    })

    # Step 1+: Document uploads
    for doc in sorted(docs, key=lambda d: d.uploaded_at):
        seq += 1
        sig = doc.signature_status or "unknown"
        tamper = doc.tamper_flags_json or {}
        steps.append({
            "seq": seq,
            "timestamp": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "actor": "system",
            "event_type": "document_processed",
            "title": f"Document: {doc.doc_type.upper()} — {doc.file_name}",
            "detail": (
                f"OCR source: {doc.ocr_source} | confidence: {doc.ocr_confidence:.0%} | "
                f"signature: {sig} | tamper flags: {len(tamper)} detected."
            ),
            "result": "pass" if sig == "valid" and not tamper else ("flag" if tamper else "pass"),
            "rule_ref": "DOC/PKI/TAMPER",
        })

    # Step N+: Verification checks
    pass_count = fail_count = flag_count = 0
    for check in checks:
        seq += 1
        icon = _check_result_icon(check.result)
        evidence_summary = ""
        if check.evidence_json:
            evlist = check.evidence_json.get("evidence", [])
            if evlist:
                evidence_summary = "; ".join(
                    str(e.get("summary", e.get("field", "")))[:80]
                    for e in evlist[:3]
                )

        steps.append({
            "seq": seq,
            "timestamp": check.created_at.isoformat() if check.created_at else None,
            "actor": "pipeline",
            "event_type": "verification_check",
            "title": f"{icon} Check: {check.check_type.upper()} → {check.result.upper()}",
            "detail": (
                f"Confidence: {check.confidence:.0%} | Rule: {check.rule_ref or 'N/A'}"
                + (f" | Evidence: {evidence_summary}" if evidence_summary else "")
            ),
            "result": check.result,
            "rule_ref": check.rule_ref,
        })
        if check.result == "pass":
            pass_count += 1
        elif check.result == "fail":
            fail_count += 1
        elif check.result == "flag":
            flag_count += 1

    # AI Assessment step
    if assessment:
        seq += 1
        cross_verify = (assessment.model_meta_json or {}).get("cross_verify", {})
        findings = cross_verify.get("findings", []) if isinstance(cross_verify, dict) else []
        steps.append({
            "seq": seq,
            "timestamp": assessment.created_at.isoformat() if assessment.created_at else None,
            "actor": "ai_engine",
            "event_type": "assessment_generated",
            "title": (
                f"AI Assessment: Score {assessment.score:.1f} | "
                f"Risk: {assessment.risk_level.upper()} | "
                f"Recommendation: {assessment.recommendation_action or 'N/A'}"
            ),
            "detail": (
                f"{assessment.recommendation_text or ''}  "
                f"[Confidence: {assessment.recommendation_confidence:.0%}]  "
                f"[AI findings: {len(findings)}]"
            ),
            "result": (
                "pass" if assessment.recommendation_action == "qualify"
                else "flag" if assessment.recommendation_action == "needs_review"
                else "fail"
            ),
            "rule_ref": "PIPELINE/SCORE",
        })

    # Officer decisions
    for decision in decisions:
        seq += 1
        steps.append({
            "seq": seq,
            "timestamp": decision.created_at.isoformat() if decision.created_at else None,
            "actor": f"officer:{decision.officer_id}",
            "event_type": "officer_decision",
            "title": (
                f"Officer Decision: {decision.decision.upper()}"
                + (" [OVERRIDES AI]" if decision.overrides_recommendation else "")
            ),
            "detail": decision.justification[:500],
            "result": (
                "pass" if decision.decision == "qualify"
                else "fail" if decision.decision == "disqualify"
                else "flag"
            ),
            "rule_ref": "HUMAN_OVERRIDE" if decision.overrides_recommendation else "HUMAN_CONFIRM",
        })

    # Build summary
    final_decision = None
    if decisions:
        last = decisions[-1]
        final_decision = {
            "decision": last.decision,
            "officer_id": last.officer_id,
            "overrides_recommendation": last.overrides_recommendation,
            "timestamp": last.created_at.isoformat() if last.created_at else None,
        }

    return {
        "submission_id": submission_id,
        "bidder_name": bidder.legal_name if bidder else None,
        "tender_ref": tender.gem_ref if tender else None,
        "tender_title": tender.title[:120] if tender else None,
        "steps": steps,
        "summary": {
            "total_steps": len(steps),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "flag_count": flag_count,
            "final_score": assessment.score if assessment else None,
            "final_risk": assessment.risk_level if assessment else None,
            "final_recommendation": assessment.recommendation_action if assessment else None,
            "final_decision": final_decision,
        },
    }
