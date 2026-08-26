"""
Cross-submission collusion / duplicate-bidder detector.

Real bid-rigging shows up ACROSS bidders on the same tender: the same PAN,
GSTIN, bank account, phone, address or authorized signatory reused by
ostensibly independent bidders (front companies).

Given all submissions on a tender, builds a similarity graph over
{pan, gstin, bank_account, phone, address, signatory_name} — exact match
for identifiers, transliteration/form-aware fuzzy match for address and
signatory names — and emits clusters with shared-attribute evidence
(rule_ref = "XVERIFY/collusion"). Deterministic and fully offline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.name_match import name_match_score

# exact-match identifiers (normalized for comparison)
_EXACT_ATTRS = ("pan", "gstin", "cin", "bank_account", "phone")
# fuzzy-matched attributes
_FUZZY_ATTRS = ("address", "signatory_name")

# fuzzy threshold for a link on address/signatory (after normalization)
_FUZZY_THRESHOLD = 85.0

DOC_ADDRESS_TYPES = ("udyam", "gst_cert", "cin")
DOC_SIGNATORY_TYPES = ("oem_auth",)


@dataclass
class SubmissionAttrs:
    submission_id: int
    bidder_name: str
    attrs: dict[str, str] = field(default_factory=dict)


def _collect_attrs(db, tender_id: int) -> list[SubmissionAttrs]:
    from app.models.bid_submission import BidSubmission
    from app.models.bidder import Bidder
    from app.models.document import Document

    items: list[SubmissionAttrs] = []
    subs = db.query(BidSubmission).filter(BidSubmission.tender_id == tender_id).all()
    for sub in subs:
        bidder = db.get(Bidder, sub.bidder_id)
        if bidder is None:
            continue
        attrs: dict[str, str] = {}
        for key in _EXACT_ATTRS:
            val = getattr(bidder, key, None)
            if val:
                attrs[key] = str(val).strip().upper()
        # document-derived attributes (best-effort from extracted fields)
        docs = db.query(Document).filter(Document.submission_id == sub.id).all()
        for doc in docs:
            fields = (doc.extracted_json or {}).get("fields", {}) or {}
            if doc.doc_type in DOC_ADDRESS_TYPES and "address" not in attrs:
                v = fields.get("address")
                if isinstance(v, dict):
                    v = v.get("value")
                if v:
                    attrs["address"] = str(v).strip()
            if doc.doc_type in DOC_SIGNATORY_TYPES and "signatory_name" not in attrs:
                v = fields.get("signatory")
                if isinstance(v, dict):
                    v = v.get("value")
                if v:
                    attrs["signatory_name"] = str(v).strip()
        items.append(SubmissionAttrs(sub.id, bidder.legal_name, attrs))
    return items


def _attr_link(a: str, b: str, attr: str) -> tuple[bool, float, str]:
    """Return (linked, confidence, match_kind)."""
    if attr in _EXACT_ATTRS:
        return (a == b, 0.99, "exact")
    score = name_match_score(a, b)
    if score >= _FUZZY_THRESHOLD:
        return (True, score / 100.0, "fuzzy")
    return (False, 0.0, "none")


def detect_collusion(db, tender_id: int) -> dict[str, Any]:
    """
    Detect clusters of submissions sharing identifiers or near-identical
    address/signatory attributes.

    Returns:
      {clusters: [{members: [{submission_id, bidder_name}],
                   links: [{attribute, value, match, confidence,
                            submissions: [ids]}]}], notes: [str]}
    """
    items = _collect_attrs(db, tender_id)

    # union-find over submissions connected by a shared attribute
    parent = {s.submission_id: s.submission_id for s in items}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    links: dict[tuple[int, int], list[dict]] = {}

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            shared = []
            for attr in _EXACT_ATTRS + _FUZZY_ATTRS:
                av, bv = a.attrs.get(attr), b.attrs.get(attr)
                if not av or not bv:
                    continue
                linked, conf, kind = _attr_link(av, bv, attr)
                if linked:
                    shared.append({"attribute": attr, "value": av, "match": kind,
                                   "confidence": round(conf, 3)})
            if shared:
                union(a.submission_id, b.submission_id)
                links[(a.submission_id, b.submission_id)] = shared

    # group by root
    groups: dict[int, list[SubmissionAttrs]] = {}
    for s in items:
        groups.setdefault(find(s.submission_id), []).append(s)

    clusters = []
    for root, members in groups.items():
        if len(members) < 2:
            continue
        ids = {m.submission_id for m in members}
        cluster_links = []
        for (x, y), shared in links.items():
            if x in ids and y in ids:
                cluster_links.append({
                    "between": [x, y],
                    "attributes": shared,
                    "submissions": [x, y],
                })
        clusters.append({
            "members": [{"submission_id": m.submission_id, "bidder_name": m.bidder_name}
                        for m in sorted(members, key=lambda m: m.submission_id)],
            "links": cluster_links,
        })

    return {"clusters": clusters, "notes": ["offline deterministic analysis — rule XVERIFY/collusion"]}