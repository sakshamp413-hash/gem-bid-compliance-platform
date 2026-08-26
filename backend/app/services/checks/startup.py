"""Startup India check: DPIIT recognition number + validity + relaxation applicability."""
from __future__ import annotations

from app.services.checks.base import CheckOutput, add_evidence


def check_startup(context) -> CheckOutput:
    out = CheckOutput(check_type="startup", result="na", rule_ref="RULES/startup")
    bidder = context.bidder
    startup_no = bidder.startup_no
    if not startup_no:
        out.summary = "No DPIIT recognition number declared — not applicable."
        return out
    add_evidence(out, doc_type=None, field="startup_no", value=startup_no, source="submission")

    portal = context.adapter.startup_status(startup_no)
    out.portal_response = portal.to_dict()
    if not portal.found:
        add_evidence(out, source="portal", field="startup.recognition", value=startup_no,
                     note=portal.error or "not found")
        out.result = "flag"
        out.summary = "DPIIT startup recognition not found."
        out.confidence = 0.9
        return out

    pd = portal.data
    add_evidence(out, source="portal", field="startup.name", value=str(pd.get("startup_name", "")))
    add_evidence(out, source="portal", field="startup.status", value=str(pd.get("status", "")))

    if str(pd.get("status", "")).lower() != "active":
        out.result = "flag"
        out.summary = f"DPIIT recognition status is '{pd.get('status')}' — flag for review."
        out.confidence = 0.9
        return out

    out.result = "pass"
    out.confidence = 0.9
    out.summary = "DPIIT startup recognition active."
    return out