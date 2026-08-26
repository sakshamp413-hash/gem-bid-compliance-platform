"""
★ Udyam / MSME check.

Validate URN format, cross-check with the mock portal, classify
micro/small/medium against the configurable rule thresholds, verify
name/PAN consistency across documents, and enforce the MSME-only
tender gate.
"""
from __future__ import annotations

from app.core.id_validators import validate_udyam, validate_state_code
from app.services.checks.base import CheckOutput, add_evidence


def _doc(context, doc_type: str) -> dict | None:
    docs = context.documents.get(doc_type)
    if not docs:
        return None
    return docs[0]


def check_udyam(context) -> CheckOutput:
    out = CheckOutput(check_type="udyam", result="fail", rule_ref="RULES/msme/classification")
    bidder = context.bidder
    udyam_no = bidder.udyam_no
    add_evidence(out, doc_type=None, field="udyam_no", value=udyam_no or "", source="submission")

    if not udyam_no:
        out.summary = "No Udyam number declared by the bidder."
        return out

    valid, reason = validate_udyam(udyam_no)
    if not valid:
        add_evidence(out, field="udyam_no", value=udyam_no, quote=reason, note="format check")
        out.summary = f"Udyam number invalid: {reason}"
        return out

    add_evidence(out, field="udyam_no", value=udyam_no, note="format valid", source="submission")
    state_code = udyam_no.split("-")[1]
    if not validate_state_code(state_code):
        add_evidence(out, field="udyam_no", value=udyam_no, quote=f"unrecognised state code {state_code}")
        out.result = "flag"
        out.summary = f"Udyam state code '{state_code}' unrecognised."

    # portal cross-check
    portal = context.adapter.verify_udyam(udyam_no)
    out.portal_response = portal.to_dict()
    if not portal.found:
        add_evidence(
            out, source="portal", field="udyam.registration", value=udyam_no,
            note=portal.error or "record not found",
        )
        out.summary = "Udyam registration not found on the MSME registry."
        out.confidence = 0.9
        return out

    pd = portal.data
    add_evidence(out, source="portal", field="udyam.name", value=str(pd.get("legal_name", "")))
    add_evidence(out, source="portal", field="udyam.status", value=str(pd.get("status", "")))
    add_evidence(out, source="portal", field="udyam.pan", value=str(pd.get("pan", "")))

    # cross-document consistency: portal name vs submission legal name
    from app.core.name_match import name_match

    portal_name = str(pd.get("legal_name", ""))
    legal_name = str(bidder.legal_name or "")
    m = name_match(portal_name, legal_name)
    ratio = m["score"]
    if ratio < 80:
        add_evidence(
            out, source="portal", field="udyam.name", value=portal_name,
            quote=f"name match ratio {ratio:.0f}% vs submitted legal name "
                  f"(normalized: '{m['normalized_a']}' vs '{m['normalized_b']}')",
            note="rapidfuzz over normalized names",
        )
        out.result = "flag"
        out.summary = f"Udyam portal name '{portal_name}' does not match submitted legal name (ratio {ratio:.0f}%)."
        out.confidence = 0.85
    else:
        add_evidence(
            out, source="portal", field="udyam.name", value=portal_name,
            quote=f"matches legal name (ratio {ratio:.0f}% after normalization)", note="rapidfuzz over normalized names",
        )

    # PAN linkage: Udyam PAN vs bidder PAN (and vs GST's embedded PAN where relevant)
    portal_pan = str(pd.get("pan", "") or "")
    if portal_pan and bidder.pan and portal_pan.upper() != str(bidder.pan).upper():
        add_evidence(
            out, source="portal", field="udyam.pan", value=portal_pan,
            quote=f"does not match declared PAN {bidder.pan}",
            note="PAN↔Udyam linkage",
        )
        out.result = "flag"
        out.summary = "PAN recorded against this Udyam number differs from the declared PAN."

    # MSME-only tender gate
    if context.tender.msme_only and pd.get("status", "").lower() not in ("active", "valid", "registered"):
        add_evidence(
            out, source="portal", field="udyam.status", value=str(pd.get("status", "")),
            quote="MSME-only tender requires an active Udyam registration",
        )
        out.result = "fail"
        out.summary = "MSME-only tender: Udyam registration is not active."
        return out

    # classification against configurable thresholds
    sector = pd.get("sector", "services")
    investment = float(pd.get("investment_crore", 0) or 0)
    turnover = float(pd.get("turnover_crore", 0) or 0)
    band = context.rules.classification_band(sector, investment, turnover)
    add_evidence(
        out, source="portal", field="udyam.classification", value=band,
        quote=f"investment ₹{investment} Cr, turnover ₹{turnover} Cr → {band}",
        note="RULES/msme/classification",
    )

    if out.result != "flag":
        out.result = "pass"
    if out.summary == "":
        out.summary = f"Udyam registration valid and active; classified {band}."
    out.confidence = max(out.confidence, 0.95)
    return out