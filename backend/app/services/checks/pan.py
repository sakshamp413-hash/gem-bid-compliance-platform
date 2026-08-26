"""
★ PAN / Income-Tax check.

Validate PAN structure, decode the 4th char (entity type) and confirm it
matches the bidder's declared entity type, sanity-check the 5th char
against the legal name, and cross-check with the ITD registry (mock).
"""
from __future__ import annotations

from app.core.id_validators import (
    pan_entity_type,
    pan_matches_entity_type,
    pan_name_sanity,
    validate_pan,
)
from app.services.checks.base import CheckOutput, add_evidence


def check_pan(context) -> CheckOutput:
    out = CheckOutput(check_type="pan", result="fail", rule_ref="RULES/pan")
    bidder = context.bidder
    pan = bidder.pan
    add_evidence(out, doc_type=None, field="pan", value=pan or "", source="submission")

    if not pan:
        out.summary = "No PAN declared by the bidder."
        return out

    valid, reason = validate_pan(pan)
    if not valid:
        add_evidence(out, field="pan", value=pan, quote=reason, note="format check")
        out.summary = f"PAN failed validation: {reason}"
        return out
    add_evidence(out, field="pan", value=pan, note="format valid", source="submission")

    # 4th char entity-type decode
    entity_name = pan_entity_type(pan)
    add_evidence(
        out, field="pan.entity_type", value=entity_name or "",
        quote=f"4th char '{pan[3]}' decodes to {entity_name}",
    )
    ok, reason = pan_matches_entity_type(pan, bidder.entity_type)
    if not ok:
        add_evidence(out, field="pan.entity_type", value=entity_name or "", quote=reason)
        out.result = "flag"
        out.summary = f"PAN entity-type ({entity_name}) does not match declared entity type ({bidder.entity_type})."
        out.confidence = 0.9

    # 5th char name sanity
    ok5, reason5 = pan_name_sanity(pan, bidder.legal_name)
    if not ok5:
        add_evidence(out, field="pan.name_sanity", value=pan[4], quote=reason5, note="5th char")
        out.result = "flag"
        out.confidence = min(out.confidence, 0.8)
        if not out.summary:
            out.summary = reason5

    # portal cross-check
    portal = context.adapter.verify_pan(pan)
    out.portal_response = portal.to_dict()
    if not portal.found:
        add_evidence(out, source="portal", field="pan.registration", value=pan, note=portal.error or "not found")
        out.result = "flag"
        out.summary = "PAN not found in the ITD registry — possible mismatch or typo."
        return out

    pd = portal.data
    add_evidence(out, source="portal", field="pan.name", value=str(pd.get("name", "")))
    add_evidence(out, source="portal", field="pan.status", value=str(pd.get("status", "")))

    from app.core.name_match import name_match

    m = name_match(str(pd.get("name", "")), bidder.legal_name)
    ratio = m["score"]
    if ratio < 80:
        add_evidence(
            out, source="portal", field="pan.name", value=str(pd.get("name", "")),
            quote=f"name match ratio {ratio:.0f}% vs submitted legal name "
                  f"(normalized: '{m['normalized_a']}' vs '{m['normalized_b']}')",
            note="rapidfuzz over normalized names",
        )
        out.result = "flag"
        out.summary = f"ITD name '{pd.get('name')}' mismatches submitted legal name ({ratio:.0f}%)."

    if pd.get("status") and str(pd.get("status")).lower() not in ("active", "valid", "pan valid"):
        add_evidence(out, source="portal", field="pan.status", value=str(pd.get("status", "")))
        out.result = "flag"
        out.summary = f"PAN status is '{pd.get('status')}'."

    if out.result == "flag" and not out.summary:
        out.summary = "PAN checks raised flags requiring officer review."
    if out.result != "flag":
        out.result = "pass"
        out.summary = "PAN valid; entity type matches; name sanity consistent; registry active."
        out.confidence = max(out.confidence, 0.95)
    return out