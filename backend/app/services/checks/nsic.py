"""NSIC check: single-point registration validity + monetary limit."""
from __future__ import annotations

from app.services.checks.base import CheckOutput, add_evidence


def check_nsic(context) -> CheckOutput:
    out = CheckOutput(check_type="nsic", result="na", rule_ref="RULES/nsic")
    bidder = context.bidder
    nsic_no = bidder.nsic_no
    if not nsic_no:
        out.summary = "No NSIC registration declared — not applicable."
        return out
    add_evidence(out, doc_type=None, field="nsic_no", value=nsic_no, source="submission")

    portal = context.adapter.nsic_status(nsic_no)
    out.portal_response = portal.to_dict()
    if not portal.found:
        add_evidence(out, source="portal", field="nsic.registration", value=nsic_no,
                     note=portal.error or "not found")
        out.result = "flag"
        out.summary = "NSIC registration not found."
        out.confidence = 0.9
        return out

    pd = portal.data
    add_evidence(out, source="portal", field="nsic.name", value=str(pd.get("unit_name", "")))
    add_evidence(out, source="portal", field="nsic.status", value=str(pd.get("status", "")))
    add_evidence(out, source="portal", field="nsic.monetary_limit", value=str(pd.get("monetary_limit", "")))

    if str(pd.get("status", "")).lower() != "active":
        out.result = "flag"
        out.summary = f"NSIC status is '{pd.get('status')}' — flag for review."
        out.confidence = 0.9
        return out

    out.result = "pass"
    out.confidence = 0.9
    out.summary = "NSIC registration active."
    return out