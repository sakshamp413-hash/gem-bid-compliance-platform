"""Make-in-India local content check (self-certification + claimed % vs class)."""
from __future__ import annotations

from app.services.checks.base import CheckOutput, add_evidence


def check_local_content(context) -> CheckOutput:
    out = CheckOutput(check_type="local_content", result="flag", rule_ref="RULES/local_content")
    tender = context.tender
    class_label = tender.local_content_class_required
    required_percent = context.rules.local_content_required_percent(class_label)

    add_evidence(out, source="rule", field="tender.local_content_class", value=str(class_label),
                 quote=f"required class '{class_label}' → min {required_percent}% local content",
                 note="RULES/local_content")

    if required_percent is None:
        out.result = "na"
        out.summary = "Tender does not require local content — not applicable."
        return out

    docs = context.documents.get("local_content")
    if not docs:
        add_evidence(out, field="local_content.doc", value="missing",
                     quote="no local-content self-certification document uploaded")
        out.summary = "Local-content self-certification document not submitted."
        out.confidence = 0.9
        return out

    doc = docs[0]
    claimed = doc.get("claimed_local_content_percent")
    add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="local_content",
                 field="claimed_local_content_percent", value=str(claimed),
                 quote=f"claimed {claimed}% vs required {required_percent}%")

    try:
        claimed_f = float(claimed)
    except (TypeError, ValueError):
        add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="local_content",
                     field="claimed_local_content_percent", value=str(claimed),
                     quote="claim not numeric — needs human confirmation")
        out.summary = "Claimed local-content percentage is not numeric."
        return out

    if class_label == "I":
        ok = claimed_f >= required_percent
    elif class_label == "II":
        ok = claimed_f >= required_percent
    else:
        ok = True

    if ok:
        out.result = "pass"
        out.confidence = 0.9
        out.summary = f"Claimed local content {claimed_f}% meets Class {class_label} requirement (≥{required_percent}%)."
        add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="local_content",
                     field="claimed_local_content_percent", value=str(claimed_f),
                     quote="meets class threshold", note="RULES/local_content")
    else:
        out.summary = f"Claimed local content {claimed_f}% is BELOW the {required_percent}% required for Class {class_label}."
        add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="local_content",
                     field="claimed_local_content_percent", value=str(claimed_f),
                     quote="below class threshold")
        out.confidence = 0.92
    return out