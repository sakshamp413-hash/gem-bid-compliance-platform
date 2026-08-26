"""
★ Blacklisting / debarment check.

Matches the bidder's name (exact + fuzzy) and exact PAN/CIN against the
seeded debarment list (GeM banned + CPPP-style). Any hit is a HARD FAIL
and caps the assessment at high risk.
"""
from __future__ import annotations

import rapidfuzz.fuzz as fuzz

from app.services.checks.base import CheckOutput, add_evidence


def check_blacklist(context) -> CheckOutput:
    out = CheckOutput(check_type="blacklist", result="pass", rule_ref="RULES/blacklist")
    bidder = context.bidder
    threshold = context.rules.blacklist_fuzzy_threshold()

    portal = context.adapter.check_blacklist(
        bidder.legal_name, bidder.pan, bidder.cin
    )
    out.portal_response = portal.to_dict()
    if not portal.found:
        add_evidence(out, source="portal", field="blacklist", value="no match",
                     quote="no exact PAN/CIN/name match in debarment list")
        out.summary = "No exact debarment match on PAN/CIN."
        out.confidence = 0.95
        return out

    matches = portal.data.get("matches", [])
    exact_hit = False
    fuzzy_hits = []

    for m in matches:
        hit_by = []
        if m.get("pan") and bidder.pan and m["pan"].upper() == str(bidder.pan).upper():
            hit_by.append("PAN exact")
        if m.get("cin") and bidder.cin and m["cin"].upper() == str(bidder.cin).upper():
            hit_by.append("CIN exact")
        if not hit_by and m.get("name") and bidder.legal_name:
            ratio = fuzz.ratio(m["name"].upper(), str(bidder.legal_name).upper())
            if ratio >= threshold:
                hit_by.append(f"name fuzzy {ratio:.0f}%")
                fuzzy_hits.append((m, ratio))
            elif ratio >= 60:  # near-miss → flag for human review
                fuzzy_hits.append((m, ratio))

        if hit_by:
            add_evidence(out, source="portal", field="blacklist.match", value=str(m.get("name", "")),
                         quote=f"debarred {m.get('period', '')} — matched by {', '.join(hit_by)}")
            if any("exact" in h for h in hit_by):
                exact_hit = True

    if exact_hit:
        out.result = "fail"
        out.confidence = 0.99
        out.summary = f"HARD FAIL: bidder is on the debarment/blacklist ({', '.join(str(m.get('name')) for m in matches)})."
        return out

    if fuzzy_hits:
        worst = max(ratio for _, ratio in fuzzy_hits)
        if worst >= threshold:
            out.result = "fail"
            out.confidence = 0.9
            out.summary = f"HARD FAIL: name closely matches a debarred entity (fuzzy {worst:.0f}%)."
        else:
            out.result = "flag"
            out.confidence = 0.75
            out.summary = f"Name partially matches a debarred entity ({worst:.0f}%) — confirm identity."
        return out

    out.result = "pass"
    out.confidence = 0.9
    out.summary = "No debarment match found."
    return out