"""
Make-in-India local content check — real domestic value addition.

Parses the bidder's cost break-up / BoM from the self-certification
document and COMPUTES the local-content percentage:

    local_content_% = (1 - imported_value / total_value) × 100

Classifies Class I / Class II / Non-local from the YAML thresholds and
compares the COMPUTED class against both the declared class and the
tender's required class. A declared class better than the computed class
is an inflated MII claim — flagged with the arithmetic in evidence.
"""
from __future__ import annotations

from app.services.checks.base import CheckOutput, add_evidence


def _classify(pct: float, rules) -> str:
    i_min = float(rules.get("local_content", "class_i_min_percent", default=50.0))
    ii_min = float(rules.get("local_content", "class_ii_min_percent", default=20.0))
    if pct >= i_min:
        return "I"
    if pct >= ii_min:
        return "II"
    return "Non-local"


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
    doc_id = doc.get("_doc_id")

    def num(field: str):
        try:
            return float(doc.get(field))
        except (TypeError, ValueError):
            return None

    total = num("total_value_lakh")
    imported = num("imported_value_lakh")
    declared_class = str(doc.get("declared_class") or "").strip()
    claimed = num("claimed_local_content_percent")

    add_evidence(out, doc_id=doc_id, doc_type="local_content",
                 field="total_value_lakh", value=str(total),
                 quote="total contract value (₹ lakh) from cost break-up / BoM")
    add_evidence(out, doc_id=doc_id, doc_type="local_content",
                 field="imported_value_lakh", value=str(imported),
                 quote="imported-content value (₹ lakh) from cost break-up / BoM")
    add_evidence(out, doc_id=doc_id, doc_type="local_content",
                 field="declared_class", value=declared_class,
                 quote="class declared by the bidder")

    if total is None or imported is None or total <= 0:
        add_evidence(out, doc_id=doc_id, doc_type="local_content",
                     field="cost_breakup", value="incomplete",
                     quote="BoM values missing or invalid — cannot compute local content")
        out.summary = "Cost break-up / BoM incomplete — local content cannot be computed."
        out.confidence = 0.7
        return out

    # --- compute domestic value addition ---
    local_pct = (1.0 - imported / total) * 100.0
    computed_class = _classify(local_pct, context.rules)
    arithmetic = f"local content % = (1 − {imported:g}/{total:g}) × 100 = {local_pct:.1f}% → Class {computed_class}"
    add_evidence(out, doc_id=doc_id, doc_type="local_content",
                 field="computed_local_content_percent", value=f"{local_pct:.1f}",
                 quote=arithmetic, note="computed from BoM")

    # declared-class vs computed-class mismatch → inflated MII claim
    if declared_class and declared_class != computed_class:
        add_evidence(
            out, doc_id=doc_id, doc_type="local_content",
            field="declared_class", value=declared_class,
            quote=f"declared Class {declared_class} but computed Class {computed_class} "
                  f"({local_pct:.1f}%) — declared class is better than the arithmetic supports",
            note="inflated Make-in-India claim",
        )
        out.result = "fail"
        out.summary = (
            f"Inflated Make-in-India claim: declared Class {declared_class} but the cost "
            f"break-up computes {local_pct:.1f}% → Class {computed_class} ({arithmetic})."
        )
        out.confidence = 0.92
        return out

    # tender-required class vs computed class
    if computed_class in ("II", "Non-local"):
        add_evidence(out, doc_id=doc_id, doc_type="local_content",
                     field="computed_local_content_percent", value=f"{local_pct:.1f}",
                     quote=f"does not meet required Class {class_label} (≥{required_percent}%)",
                     note="RULES/local_content")
        out.result = "fail"
        out.summary = (
            f"Computed local content {local_pct:.1f}% ({arithmetic}) is below the "
            f"{required_percent}% required for Class {class_label}."
        )
        out.confidence = 0.9
        return out

    # consistency: computed % vs claimed %
    if claimed is not None and abs(claimed - local_pct) > 2.0:
        add_evidence(out, doc_id=doc_id, doc_type="local_content",
                     field="claimed_local_content_percent", value=f"{claimed:g}",
                     quote=f"claimed {claimed:g}% differs from computed {local_pct:.1f}% — arithmetic attached")
        out.result = "flag"
        out.summary = (
            f"Claimed local content {claimed:g}% differs from the {local_pct:.1f}% computed "
            f"from the cost break-up ({arithmetic})."
        )
        out.confidence = 0.85
        return out

    out.result = "pass"
    out.confidence = 0.92
    out.summary = (
        f"Computed local content {local_pct:.1f}% ({arithmetic}) meets Class {class_label} "
        f"requirement (≥{required_percent}%)."
    )
    return out