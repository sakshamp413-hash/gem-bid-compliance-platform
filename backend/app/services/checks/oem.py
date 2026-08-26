"""OEM authorization check: letter links OEM → bidder, validity dates, signatory."""
from __future__ import annotations

import datetime as dt

from app.services.checks.base import CheckOutput, add_evidence


def check_oem(context) -> CheckOutput:
    out = CheckOutput(check_type="oem", result="fail", rule_ref="RULES/oem")
    docs = context.documents.get("oem_auth")
    if not docs:
        add_evidence(out, field="oem_auth.doc", value="missing",
                     quote="tender requires OEM authorization, document not submitted")
        out.summary = "OEM authorization letter not submitted though the tender requires it."
        out.confidence = 0.95
        return out

    doc = docs[0]
    oem_name = doc.get("oem_name")
    bidder_name = doc.get("authorized_bidder_name") or doc.get("distributor_name")
    from_date = doc.get("valid_from")
    to_date = doc.get("valid_to")
    signatory = doc.get("signatory")

    add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="oem_auth", field="oem_name", value=str(oem_name))
    add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="oem_auth",
                 field="authorized_bidder_name", value=str(bidder_name))
    add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="oem_auth", field="valid_to", value=str(to_date))
    add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="oem_auth", field="signatory", value=str(signatory))

    if not oem_name or not bidder_name:
        out.summary = "OEM authorization letter is missing the OEM or authorized-party name."
        return out

    # name consistency: authorized party must be the bidder
    from app.core.name_match import name_match

    m = name_match(str(bidder_name), context.bidder.legal_name)
    ratio = m["score"]
    if ratio < 80:
        add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="oem_auth",
                     field="authorized_bidder_name", value=str(bidder_name),
                     quote=f"authorized party does not match bidder legal name "
                           f"(ratio {ratio:.0f}% after normalization: "
                           f"'{m['normalized_a']}' vs '{m['normalized_b']}')",
                     note="rapidfuzz over normalized names")
        out.summary = "OEM letter authorizes a different entity than the bidder."
        return out

    # validity
    today = dt.date.today()
    try:
        if to_date:
            to = dt.date.fromisoformat(str(to_date)[:10])
            if to < today:
                add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="oem_auth",
                             field="valid_to", value=str(to_date), quote="authorization has EXPIRED")
                out.summary = "OEM authorization has expired."
                out.confidence = 0.95
                return out
            max_years = context.rules.oem_max_validity_years()
            if (to - today).days > max_years * 365:
                add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="oem_auth",
                             field="valid_to", value=str(to_date),
                             quote=f"validity longer than {max_years} years — suspicious")
                out.result = "flag"
                out.summary = f"OEM authorization validity exceeds {max_years} years — suspicious."
                out.confidence = 0.8
        if from_date:
            frm = dt.date.fromisoformat(str(from_date)[:10])
            if frm > today:
                add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="oem_auth",
                             field="valid_from", value=str(from_date), quote="validity starts in the future")
                out.result = "flag"
                out.summary = "OEM authorization validity starts in the future."
                out.confidence = 0.85
    except ValueError:
        add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="oem_auth",
                     field="valid_to", value=str(to_date), quote="dates unparseable")
        out.result = "flag"
        out.summary = "OEM authorization dates could not be parsed."
        out.confidence = 0.7
        return out

    if not signatory:
        add_evidence(out, doc_id=doc.get("_doc_id"), doc_type="oem_auth",
                     field="signatory", value="missing", quote="no signatory name found")
        out.result = "flag"
        out.summary = "OEM authorization has no identifiable signatory."

    if out.result != "flag":
        out.result = "pass"
        out.confidence = 0.9
        out.summary = "OEM authorization valid: bidder authorized, dates in range."
    return out