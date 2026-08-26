"""MCA21 check: CIN format validation + company status + name consistency."""
from __future__ import annotations

from app.core.id_validators import validate_cin
from app.services.checks.base import CheckOutput, add_evidence


def check_mca(context) -> CheckOutput:
    out = CheckOutput(check_type="mca", result="fail", rule_ref="RULES/mca")
    bidder = context.bidder
    cin = bidder.cin
    add_evidence(out, doc_type=None, field="cin", value=cin or "", source="submission")

    if not cin:
        out.result = "na"
        out.summary = "No CIN declared — MCA check not applicable."
        return out

    valid, reason = validate_cin(cin)
    if not valid:
        add_evidence(out, field="cin", value=cin, quote=reason, note="format check")
        out.summary = f"CIN failed validation: {reason}"
        return out
    add_evidence(out, field="cin", value=cin, note="format valid", source="submission")

    portal = context.adapter.mca_company(cin)
    out.portal_response = portal.to_dict()
    if not portal.found:
        add_evidence(out, source="portal", field="mca.company", value=cin, note=portal.error or "not found")
        out.summary = "Company not found on the MCA registry for this CIN."
        out.result = "flag"
        out.confidence = 0.9
        return out

    pd = portal.data
    add_evidence(out, source="portal", field="mca.name", value=str(pd.get("company_name", "")))
    add_evidence(out, source="portal", field="mca.status", value=str(pd.get("status", "")))

    status = str(pd.get("status", "")).lower()
    if status in ("active", "strike off", "struck off"):
        if status != "active":
            add_evidence(out, source="portal", field="mca.status", value=status,
                         quote="company not in Active status — flag for review")
            out.result = "flag"
            out.summary = f"MCA status is '{status}' — needs review."
            out.confidence = 0.9
            return out
    else:
        add_evidence(out, source="portal", field="mca.status", value=status,
                     quote="unrecognised/abnormal MCA status")
        out.result = "flag"
        out.summary = f"MCA status '{status}' needs manual confirmation."
        return out

    from app.core.name_match import name_match

    m = name_match(str(pd.get("company_name", "")), bidder.legal_name)
    ratio = m["score"]
    if ratio < 80:
        add_evidence(out, source="portal", field="mca.name", value=str(pd.get("company_name", "")),
                     quote=f"name match ratio {ratio:.0f}% vs submitted legal name "
                           f"(normalized: '{m['normalized_a']}' vs '{m['normalized_b']}')",
                     note="rapidfuzz over normalized names")
        out.result = "flag"
        out.summary = f"MCA company name '{pd.get('company_name')}' mismatches submitted name ({ratio:.0f}%)."
        return out

    out.result = "pass"
    out.confidence = 0.95
    out.summary = "CIN valid; company Active on MCA registry; name consistent."
    return out