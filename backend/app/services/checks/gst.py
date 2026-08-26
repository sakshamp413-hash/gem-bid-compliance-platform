"""
★ GST check.

Validate GSTIN (format + REAL public GSTN checksum), confirm the
GSTIN's embedded PAN equals the declared PAN (PAN↔GST linkage), pull
registration + return-filing status from the portal and flag
not-filed / cancelled registrations.
"""
from __future__ import annotations

import datetime as dt

from app.core.id_validators import gstin_pan, validate_gstin
from app.services.checks.base import CheckOutput, add_evidence


def check_gst(context) -> CheckOutput:
    out = CheckOutput(check_type="gst", result="fail", rule_ref="RULES/gst")
    bidder = context.bidder
    gstin = bidder.gstin
    add_evidence(out, doc_type=None, field="gstin", value=gstin or "", source="submission")

    if not gstin:
        out.summary = "No GSTIN declared by the bidder."
        return out

    valid, reason = validate_gstin(gstin)
    if not valid:
        add_evidence(out, field="gstin", value=gstin, quote=reason, note="format+checksum")
        out.summary = f"GSTIN failed validation: {reason}"
        out.confidence = 1.0
        return out
    add_evidence(out, field="gstin", value=gstin, note="format + GSTN checksum valid", source="submission")

    # PAN ↔ GST linkage
    embedded_pan = gstin_pan(gstin)
    if embedded_pan and bidder.pan:
        if embedded_pan.upper() == str(bidder.pan).upper():
            add_evidence(
                out, field="gstin", value=gstin,
                quote=f"embedded PAN {embedded_pan} matches declared PAN",
                note="PAN↔GST linkage",
            )
        else:
            add_evidence(
                out, field="gstin", value=gstin,
                quote=f"embedded PAN {embedded_pan} does NOT match declared PAN {bidder.pan}",
                note="PAN↔GST linkage",
            )
            out.result = "fail"
            out.summary = "GSTIN embeds a different PAN than declared — registration identity conflict."
            out.confidence = 0.98
            return out

    # portal: registration status
    portal = context.adapter.verify_gstin(gstin)
    out.portal_response = portal.to_dict()
    if not portal.found:
        add_evidence(
            out, source="portal", field="gstin.registration", value=gstin,
            note=portal.error or "record not found",
        )
        out.summary = "GSTIN not found in the GST registry."
        return out

    pd = portal.data
    add_evidence(out, source="portal", field="gstin.name", value=str(pd.get("legal_name", "")))
    add_evidence(out, source="portal", field="gstin.status", value=str(pd.get("status", "")))

    status = str(pd.get("status", ""))
    cancelled_statuses = context.rules.gst_cancelled_statuses()
    if status in cancelled_statuses or "cancel" in status.lower():
        add_evidence(
            out, source="portal", field="gstin.status", value=status,
            quote="registration cancelled — bidder not eligible to transact",
        )
        out.result = "fail"
        out.summary = f"GST registration is {status}."
        out.confidence = 0.97
        return out

    # name consistency
    import rapidfuzz.fuzz as fuzz

    portal_name = str(pd.get("legal_name", ""))
    ratio = fuzz.ratio(portal_name.upper(), str(bidder.legal_name or "").upper())
    if ratio < 80:
        add_evidence(
            out, source="portal", field="gstin.name", value=portal_name,
            quote=f"name match ratio {ratio:.0f}% vs submitted legal name", note="rapidfuzz",
        )
        out.result = "flag"
        out.summary = f"GST registry name '{portal_name}' mismatches submitted legal name ({ratio:.0f}%)."

    # return-filing status
    returns = context.adapter.gst_return_status(gstin)
    ret_status = str(returns.data.get("return_status", "unknown"))
    period = returns.data.get("period", "unknown")
    add_evidence(
        out, source="portal", field="gst.return_status", value=ret_status,
        quote=f"latest period: {period}",
    )
    grace = context.rules.gst_grace_months()

    if ret_status.lower() in ("not filed", "none", "not_filed", "missing"):
        add_evidence(
            out, source="portal", field="gst.return_status", value=ret_status,
            quote=f"GST returns not filed for period {period}",
        )
        out.result = "flag"
        out.summary = f"GST returns NOT filed (latest period {period})."
        out.confidence = 0.95
    elif ret_status.lower() in ("filed", "submitted", "active"):
        add_evidence(
            out, source="portal", field="gst.return_status", value=ret_status,
            quote="returns filed", note=f"grace {grace} months",
        )
    else:
        # unknown/other statuses → needs human look
        add_evidence(out, source="portal", field="gst.return_status", value=ret_status)
        out.result = "flag"
        out.summary = f"GST return status '{ret_status}' needs manual confirmation."

    if out.result != "flag":
        out.result = "pass"
    if out.result == "fail" and out.summary == "":
        out.summary = "GST registration check failed."
    if out.result == "pass" and out.summary == "":
        out.summary = "GST registration active; checksum valid; PAN linkage consistent; returns filed."
    if out.result == "pass":
        out.confidence = max(out.confidence, 0.95)
    return out