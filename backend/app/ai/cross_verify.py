"""
Cross-verification engine.

Combines extracted document fields + portal responses and produces
findings: {severity, message, evidence[], rule_ref, confidence}.

Two passes:
  1. deterministic consistency rules (rapidfuzz names, PAN↔GST, dates,
     entity coherence) — always runs, fully grounded
  2. LLM reasoning pass (when a live model is available) constrained to
     the same evidence pack; offline mode reuses the deterministic pass.
"""
from __future__ import annotations

import datetime as dt
import json
from typing import Any

from app.core.name_match import name_match
from app.ai.llm import GROUNDING_SYSTEM_PROMPT, get_llm_client
from app.core.logging import get_logger

logger = get_logger(__name__)

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _finding(severity: str, message: str, evidence: list[dict], rule_ref: str, confidence: float) -> dict:
    return {
        "severity": severity,
        "message": message,
        "evidence": evidence,
        "rule_ref": rule_ref,
        "confidence": round(confidence, 3),
    }


def _ev(doc_id=None, doc_type=None, field="", value="", quote=None, source="document") -> dict:
    return {"doc_id": doc_id, "doc_type": doc_type, "field": field, "value": str(value),
            "quote": quote, "source": source}


def _doc_fields(ctx: dict, doc_type: str) -> dict:
    for d in ctx.get("documents", {}).get(doc_type, []):
        return d.get("fields", {})
    return {}


def _clean(d: dict) -> dict:
    return {k: (v.get("value") if isinstance(v, dict) else v) for k, v in d.items()}


def run_deterministic_cross_verify(payload: dict) -> dict[str, Any]:
    """
    Deterministic consistency analysis over the evidence pack.

    payload: {bidder:{...}, documents:{doc_type:[{fields}]}, portal:{...}}
    Returns: {findings: [...]}
    """
    findings: list[dict] = []
    bidder = payload.get("bidder", {})
    portal = payload.get("portal", {})
    docs = payload.get("documents", {})

    legal_name = str(bidder.get("legal_name", "") or "")

    def add(finding: dict):
        findings.append(finding)

    # 1) name consistency: submission vs udyam/gst docs
    names: list[tuple[str, str, dict]] = [
        ("udyam", _clean(_doc_fields(payload, "udyam")).get("legal_name"), None),
        ("gst_cert", _clean(_doc_fields(payload, "gst_cert")).get("legal_name"), None),
        ("cin", _clean(_doc_fields(payload, "cin")).get("company_name"), None),
        ("pan_card", _clean(_doc_fields(payload, "pan_card")).get("name"), None),
    ]
    if legal_name:
        for doc_type, name, _ in names:
            if not name:
                continue
            m = name_match(name, legal_name)
            ratio = m["score"]
            if ratio < 75:
                add(_finding(
                    "high",
                    f"Legal name on {doc_type} ('{name}') differs from submitted legal name "
                    f"'{legal_name}' (match {ratio:.0f}% after normalization: "
                    f"'{m['normalized_a']}' vs '{m['normalized_b']}').",
                    [_ev(doc_type=doc_type, field="legal_name", value=name,
                         quote=f"ratio {ratio:.0f}% · normalized '{m['normalized_a']}'")],
                    "XVERIFY/name-consistency", 0.9,
                ))
            else:
                add(_finding(
                    "info",
                    f"Name on {doc_type} consistent with submission "
                    f"({ratio:.0f}% after normalization).",
                    [_ev(doc_type=doc_type, field="legal_name", value=name,
                         quote=f"normalized '{m['normalized_a']}'")],
                    "XVERIFY/name-consistency", 0.95,
                ))

    # 2) PAN ↔ GST linkage + cross-doc PAN consistency
    bidder_pan = str(bidder.get("pan", "") or "")
    gstin = str(bidder.get("gstin", "") or "")
    if gstin and len(gstin) == 15:
        embedded = gstin[2:12]
        if bidder_pan and embedded.upper() != bidder_pan.upper():
            add(_finding(
                "critical",
                f"GSTIN embeds PAN '{embedded}' which does not match the declared PAN '{bidder_pan}'.",
                [_ev(field="gstin", value=gstin, quote=f"embedded PAN {embedded}"),
                 _ev(field="pan", value=bidder_pan, source="submission")],
                "XVERIFY/pan-gst-linkage", 0.99,
            ))
        else:
            add(_finding(
                "info", "PAN↔GST linkage consistent.",
                [_ev(field="gstin", value=gstin, quote=f"embedded PAN {embedded}")],
                "XVERIFY/pan-gst-linkage", 0.98,
            ))

    udyam_pan = _clean(_doc_fields(payload, "udyam")).get("pan")
    if bidder_pan and udyam_pan and udyam_pan.upper() != bidder_pan.upper():
        add(_finding(
            "critical",
            f"PAN on Udyam certificate ('{udyam_pan}') differs from declared PAN ('{bidder_pan}').",
            [_ev(doc_type="udyam", field="pan", value=udyam_pan),
             _ev(field="pan", value=bidder_pan, source="submission")],
            "XVERIFY/pan-doc-consistency", 0.98,
        ))

    pan_card_pan = _clean(_doc_fields(payload, "pan_card")).get("pan")
    if bidder_pan and pan_card_pan and pan_card_pan.upper() != bidder_pan.upper():
        add(_finding(
            "critical",
            f"PAN card shows '{pan_card_pan}' but declared PAN is '{bidder_pan}'.",
            [_ev(doc_type="pan_card", field="pan", value=pan_card_pan),
             _ev(field="pan", value=bidder_pan, source="submission")],
            "XVERIFY/pan-doc-consistency", 0.98,
        ))

    # 2b) PAN card name vs Udyam certificate name (direct doc-vs-doc)
    udyam_name = _clean(_doc_fields(payload, "udyam")).get("legal_name")
    pan_card_name = _clean(_doc_fields(payload, "pan_card")).get("name")
    if udyam_name and pan_card_name:
        m = name_match(udyam_name, pan_card_name)
        doc_ratio = m["score"]
        if doc_ratio < 85:
            add(_finding(
                "high",
                f"PAN card name '{pan_card_name}' differs from Udyam certificate name "
                f"'{udyam_name}' (match {doc_ratio:.0f}% after normalization: "
                f"'{m['normalized_a']}' vs '{m['normalized_b']}') — identity documents conflict.",
                [_ev(doc_type="pan_card", field="name", value=pan_card_name,
                     quote=f"normalized '{m['normalized_b']}'"),
                 _ev(doc_type="udyam", field="legal_name", value=udyam_name,
                     quote=f"normalized '{m['normalized_a']}'")],
                "XVERIFY/name-consistency", 0.92,
            ))

    # 3) document numbers must match declared numbers
    udyam_no_doc = _clean(_doc_fields(payload, "udyam")).get("udyam_no")
    if udyam_no_doc and str(udyam_no_doc).upper() != str(bidder.get("udyam_no", "") or "").upper():
        add(_finding(
            "high",
            f"Udyam number on certificate ('{udyam_no_doc}') differs from declared ('{bidder.get('udyam_no')}').",
            [_ev(doc_type="udyam", field="udyam_no", value=udyam_no_doc),
             _ev(field="udyam_no", value=bidder.get("udyam_no"), source="submission")],
            "XVERIFY/id-consistency", 0.97,
        ))
    gstin_doc = _clean(_doc_fields(payload, "gst_cert")).get("gstin")
    if gstin_doc and str(gstin_doc).upper() != gstin.upper():
        add(_finding(
            "critical",
            f"GSTIN on certificate ('{gstin_doc}') differs from declared GSTIN ('{gstin}').",
            [_ev(doc_type="gst_cert", field="gstin", value=gstin_doc),
             _ev(field="gstin", value=gstin, source="submission")],
            "XVERIFY/id-consistency", 0.97,
        ))

    # 4) expiry / date coherence
    today = dt.date.today()
    startup_valid = _clean(_doc_fields(payload, "startup")).get("valid_until")
    if startup_valid:
        try:
            if dt.date.fromisoformat(str(startup_valid)[:10]) < today:
                add(_finding(
                    "high", f"Startup recognition expired on {startup_valid}.",
                    [_ev(doc_type="startup", field="valid_until", value=startup_valid)],
                    "XVERIFY/expiry", 0.9,
                ))
        except ValueError:
            pass
    oem_to = _clean(_doc_fields(payload, "oem_auth")).get("valid_to")
    if oem_to:
        try:
            if dt.date.fromisoformat(str(oem_to)[:10]) < today:
                add(_finding(
                    "high", f"OEM authorization expired on {oem_to}.",
                    [_ev(doc_type="oem_auth", field="valid_to", value=oem_to)],
                    "XVERIFY/expiry", 0.9,
                ))
        except ValueError:
            pass

    # 5) entity-type coherence: PAN 4th char vs declared type vs CIN type
    from app.core.id_validators import pan_entity_type

    if bidder_pan and len(bidder_pan) == 10:
        entity = pan_entity_type(bidder_pan)
        declared = str(bidder.get("entity_type", "") or "")
        expect_map = {"private_limited": "company", "public_limited": "company",
                      "company": "company", "firm": "firm", "partnership": "firm",
                      "proprietorship": "individual", "individual": "individual",
                      "llp": "company", "trust": "trust"}
        if entity and expect_map.get(declared) and entity != expect_map[declared]:
            add(_finding(
                "high",
                f"PAN entity type '{entity}' conflicts with declared entity type '{declared}'.",
                [_ev(field="pan", value=bidder_pan, quote=f"4th char decodes to {entity}"),
                 _ev(field="entity_type", value=declared, source="submission")],
                "XVERIFY/entity-coherence", 0.88,
            ))

    # 6) portal cross-checks (from check results) get summarized as info
    for ctype, pres in (portal or {}).items():
        if isinstance(pres, dict) and pres.get("found") and pres.get("data"):
            nm = pres["data"].get("legal_name") or pres["data"].get("company_name") or pres["data"].get("name")
            if nm and legal_name and name_match(nm, legal_name)["score"] < 75:
                add(_finding(
                    "high",
                    f"Registry '{ctype}' name '{nm}' differs from submitted legal name.",
                    [_ev(source="portal", field=f"{ctype}.name", value=nm)],
                    "XVERIFY/portal-name", 0.85,
                ))

    # 7) escalate hard check failures into findings (forgery / debarment)
    for c in payload.get("checks", []) or []:
        if not isinstance(c, dict):
            continue
        ctype = c.get("check_type")
        if c.get("result") == "fail" and ctype == "digilocker":
            add(_finding(
                "critical",
                "Document integrity failure: a statutory document is forged or tampered with "
                "(signature invalid or modified after signing).",
                [_ev(source="document", field="signature/tamper", value="fail",
                     quote=str(c.get("summary", ""))[:200])],
                "RULES/digilocker", 0.97,
            ))
        if c.get("result") == "fail" and ctype == "blacklist":
            add(_finding(
                "critical",
                "Bidder appears on the debarment/blacklist registry.",
                [_ev(source="portal", field="blacklist", value="matched",
                     quote=str(c.get("summary", ""))[:200])],
                "RULES/blacklist", 0.99,
            ))
        if c.get("result") == "fail" and ctype == "gst":
            add(_finding(
                "critical" if "Cancel" in str(c.get("summary", "")) else "high",
                str(c.get("summary", "")),
                [_ev(source="portal", field="gst", value="fail")],
                "RULES/gst", 0.95,
            ))

    findings.sort(key=lambda f: SEVERITY_ORDER.get(f["severity"], 9))
    return {"findings": findings}


def run_cross_verify(context: dict) -> dict[str, Any]:
    """
    Full cross-verification for a submission.

    context: {bidder, documents, portal, checks} — serializable evidence pack.
    Returns {findings, model_meta}.
    """
    llm = get_llm_client()
    deterministic = run_deterministic_cross_verify(context)

    findings = deterministic["findings"]
    model_meta = {
        "provider": llm.provider,
        "model": llm.model,
        "prompt_hash": "",
        "deterministic_pass": True,
    }

    if llm.provider != "offline_deterministic":
        try:
            user = (
                "Analyze the bidder evidence pack and return JSON with three lists — "
                "\"missing\" (requirements with no supporting evidence), \"inconsistent\" "
                "(conflicting values) and \"contradictory\" (direct contradictions). "
                "Each item: {severity, message, evidence:[{field, value, source}]}. "
                "Only assert what the evidence supports. If a value is unknown say \"unknown\".\n\n"
                f"TASK: cross_verify\nPAYLOAD: {json.dumps(context)}"
            )
            result = llm.complete_json(GROUNDING_SYSTEM_PROMPT, user, "object")
            llm_findings = []
            for bucket in ("missing", "inconsistent", "contradictory"):
                for item in result.get(bucket, []) or []:
                    if not isinstance(item, dict):
                        continue
                    sev = {"missing": "medium", "inconsistent": "high",
                           "contradictory": "critical"}.get(bucket, "medium")
                    llm_findings.append(_finding(
                        sev, str(item.get("message", "")),
                        [{"field": e.get("field"), "value": e.get("value"),
                          "source": e.get("source", "llm")} for e in item.get("evidence", [])],
                        f"XVERIFY/llm-{bucket}", float(item.get("confidence", 0.7)),
                    ))
            findings.extend(llm_findings)
            findings.sort(key=lambda f: SEVERITY_ORDER.get(f["severity"], 9))
            model_meta.update({
                "llm_pass": True,
                "prompt_hash": llm.prompt_hash(GROUNDING_SYSTEM_PROMPT, user),
            })
        except Exception as exc:
            logger.warning("LLM cross-verify failed (%s) — deterministic results kept", exc)

    return {"findings": findings, "model_meta": model_meta}