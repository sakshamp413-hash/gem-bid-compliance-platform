"""
DigiLocker / document integrity check.

Aggregates per-document signature + tamper analysis (Section 8) into a
check result. A broken signature or a tamper flag on a statutory
document is a HARD FAIL.
"""
from __future__ import annotations

from app.services.checks.base import CheckOutput, add_evidence


def check_digilocker(context) -> CheckOutput:
    out = CheckOutput(check_type="digilocker", result="na", rule_ref="RULES/digilocker")
    docs = context.documents
    if not docs:
        out.summary = "No documents to verify — not applicable."
        return out

    statutory = {"udyam", "gst_cert", "pan_card", "cin", "epfo", "esic", "startup", "nsic"}
    problems: list[str] = []      # hard failures (invalid/tampered/untrusted)
    flags: list[str] = []         # needs-review signals (unsigned scans etc.)
    total = 0
    signed_valid = 0
    tampered = 0

    for doc_type, extracted_list in docs.items():
        for doc in extracted_list:
            sig = doc.get("_signature_status") or "not_signed"
            tamper = doc.get("_tamper_flags") or {}
            total += 1
            add_evidence(out, doc_id=doc.get("_doc_id"), doc_type=doc_type,
                         field="signature_status", value=sig,
                         quote=f"signature: {sig}", source="document")
            if sig == "valid":
                signed_valid += 1
            elif doc_type in statutory and sig == "invalid":
                problems.append(f"{doc_type}: signature invalid (modified after signing)")
                add_evidence(out, doc_id=doc.get("_doc_id"), doc_type=doc_type,
                             field="signature_status", value=sig,
                             quote="statutory document signature INVALID — possible forgery")
                tampered += 1
            elif doc_type in statutory and sig == "untrusted":
                problems.append(f"{doc_type}: signer certificate untrusted")
                add_evidence(out, doc_id=doc.get("_doc_id"), doc_type=doc_type,
                             field="signature_status", value=sig,
                             quote="signer certificate not in trust chain")
            elif doc_type in statutory and sig == "not_signed":
                # scans / hand-signed uploads: flag for officer review, not a fail
                flags.append(f"{doc_type}: not digitally signed (scan)")
                add_evidence(out, doc_id=doc.get("_doc_id"), doc_type=doc_type,
                             field="signature_status", value="not_signed",
                             quote="statutory document carries no digital signature — "
                                   "manual verification recommended")

            if tamper.get("tampered"):
                problems.append(f"{doc_type}: {tamper.get('summary', 'tamper detected')}")
                add_evidence(out, doc_id=doc.get("_doc_id"), doc_type=doc_type,
                             field="tamper_flags", value=str(tamper.get("reasons", [])),
                             quote=tamper.get("summary", ""))
                tampered += 1

    if total == 0:
        out.summary = "No documents to verify — not applicable."
        return out

    if tampered > 0:
        out.result = "fail"
        out.confidence = 0.97
        out.summary = f"{tampered} document(s) failed integrity checks: " + "; ".join(problems[:3])
    elif problems:
        out.result = "fail"
        out.confidence = 0.9
        out.summary = "; ".join(problems[:4])
    elif flags:
        out.result = "flag"
        out.confidence = 0.8
        out.summary = "; ".join(flags[:4])
    else:
        out.result = "pass"
        out.confidence = 0.95
        out.summary = f"All {total} document(s) passed signature/integrity checks."
    return out