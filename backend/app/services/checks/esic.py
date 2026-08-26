"""ESIC check: code presence + active status (mock portal)."""
from __future__ import annotations

from app.services.checks.base import CheckOutput, add_evidence


def check_esic(context) -> CheckOutput:
    out = CheckOutput(check_type="esic", result="na", rule_ref="RULES/esic")
    bidder = context.bidder
    esic_no = bidder.esic_no
    if not esic_no:
        out.summary = "No ESIC code declared — not applicable."
        return out
    add_evidence(out, doc_type=None, field="esic_no", value=esic_no, source="submission")

    portal = context.adapter.esic_status(esic_no)
    out.portal_response = portal.to_dict()
    if not portal.found:
        add_evidence(out, source="portal", field="esic.establishment", value=esic_no,
                     note=portal.error or "not found")
        out.result = "flag"
        out.summary = "ESIC code not found."
        out.confidence = 0.9
        return out

    pd = portal.data
    add_evidence(out, source="portal", field="esic.name", value=str(pd.get("establishment_name", "")))
    add_evidence(out, source="portal", field="esic.status", value=str(pd.get("status", "")))
    if str(pd.get("status", "")).lower() != "active":
        out.result = "flag"
        out.summary = f"ESIC status is '{pd.get('status')}' — flag for review."
        out.confidence = 0.9
        return out

    out.result = "pass"
    out.confidence = 0.9
    out.summary = "ESIC registration active."
    return out