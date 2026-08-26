"""EPFO check: establishment code presence + active status (mock portal)."""
from __future__ import annotations

from app.services.checks.base import CheckOutput, add_evidence


def check_epfo(context) -> CheckOutput:
    out = CheckOutput(check_type="epfo", result="na", rule_ref="RULES/epfo")
    bidder = context.bidder
    epfo_no = bidder.epfo_no
    if not epfo_no:
        out.summary = "No EPFO establishment code declared — not applicable."
        return out
    add_evidence(out, doc_type=None, field="epfo_no", value=epfo_no, source="submission")

    portal = context.adapter.epfo_status(epfo_no)
    out.portal_response = portal.to_dict()
    if not portal.found:
        add_evidence(out, source="portal", field="epfo.establishment", value=epfo_no,
                     note=portal.error or "not found")
        out.result = "flag"
        out.summary = "EPFO establishment code not found."
        out.confidence = 0.9
        return out

    pd = portal.data
    add_evidence(out, source="portal", field="epfo.name", value=str(pd.get("establishment_name", "")))
    add_evidence(out, source="portal", field="epfo.status", value=str(pd.get("status", "")))

    if str(pd.get("status", "")).lower() != "active":
        out.result = "flag"
        out.summary = f"EPFO establishment status is '{pd.get('status')}' — flag for review."
        out.confidence = 0.9
        return out

    out.result = "pass"
    out.confidence = 0.9
    out.summary = "EPFO establishment active."
    return out