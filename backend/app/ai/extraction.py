"""
Structured document extraction.

Per-doc-type schemas with per-field confidence. Two paths produce the
SAME output contract:
  * LLM path    — grounded JSON extraction via LLMClient (schema-hinted)
  * deterministic path — regex/pattern extractors (offline, no model)

Fields optionally carry a page + bounding box (pdf points) so the UI can
highlight the exact location on the rendered page.
"""
from __future__ import annotations

import re
from typing import Any

from app.ai.llm import GROUNDING_SYSTEM_PROMPT, LLMClient, get_llm_client
from app.core.logging import get_logger

logger = get_logger(__name__)

DOC_SCHEMAS: dict[str, list[str]] = {
    "udyam": ["udyam_no", "legal_name", "trade_name", "pan", "classification", "sector",
              "investment_crore", "turnover_crore", "issue_date", "address"],
    "gst_cert": ["gstin", "legal_name", "trade_name", "address", "status", "registration_date"],
    "pan_card": ["pan", "name", "date_of_birth", "father_name"],
    "cin": ["cin", "company_name", "date_of_incorporation", "registered_office"],
    "oem_auth": ["oem_name", "authorized_bidder_name", "item_description", "valid_from", "valid_to", "signatory"],
    "local_content": ["claimed_local_content_percent", "item", "declared_class", "certification_date"],
    "epfo": ["epfo_no", "establishment_name", "status"],
    "esic": ["esic_no", "establishment_name", "status"],
    "startup": ["startup_no", "startup_name", "status", "valid_until"],
    "nsic": ["nsic_no", "unit_name", "status", "monetary_limit"],
}

# --- deterministic extractors ---------------------------------------------

_UDYAM_RE = re.compile(r"UDYAM-[A-Z]{2}-\d{2}-\d{7}", re.IGNORECASE)
_GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]\b")
_PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_CIN_RE = re.compile(r"\b[LU]\d{5}[A-Z]{2}\d{6}[A-Z]{3}\d{6}\b")
_EPFO_RE = re.compile(r"\b[A-Z]{2}/\d{5,7}/\d{3,5}\b")
_ESIC_RE = re.compile(r"\b\d{5,10}\b")
_STARTUP_RE = re.compile(r"\b(?:S?\d{10,12}|DIPP\d{6,10})\b", re.IGNORECASE)
_NSIC_RE = re.compile(r"\b(?:NSIC[- ]?\d{6,10}|[A-Z]{2}\d{5,8})\b", re.IGNORECASE)
_PERCENT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _find_label(lines: list[str], *labels: str) -> str | None:
    """
    Match "Label value" or "Label: value" lines. Labels are matched
    longest-first with a word boundary so "legal name of enterprise"
    wins over "legal name".
    """
    ordered = sorted((lbl for lbl in labels if lbl), key=len, reverse=True)
    for line in lines:
        low = line.lower()
        for label in ordered:
            if low.startswith(label.lower()):
                rest = line[len(label):].lstrip()
                if rest.startswith(":"):
                    rest = rest[1:]
                rest = rest.strip()
                if rest:
                    return rest
    return None


def extract_fields_deterministic(doc_type: str, text: str) -> dict[str, Any]:
    """Regex/pattern extraction. Returns {field: {value, confidence}}."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    full = text.upper()
    out: dict[str, Any] = {}

    def put(field: str, value: Any, conf: float = 0.98):
        if value is not None and str(value).strip():
            out[field] = {"value": str(value).strip(), "confidence": conf}

    if doc_type == "udyam":
        m = _UDYAM_RE.search(text)
        put("udyam_no", m.group(0) if m else _find_label(lines, "udyam registration number"))
        put("legal_name", _find_label(lines, "legal name of enterprise", "legal name", "name of enterprise"))
        put("trade_name", _find_label(lines, "trade name"))
        pan = _PAN_RE.search(text)
        put("pan", pan.group(0) if pan else None)
        put("classification", _find_label(lines, "classification", "category"))
        put("sector", _find_label(lines, "sector"))
        m_inv = re.search(r"[Ii]nvestment[^0-9]*([\d.]+)", text)
        put("investment_crore", m_inv.group(1) if m_inv else _find_label(lines, "investment"))
        m_turn = re.search(r"[Tt]urnover[^0-9]*([\d.]+)", text)
        put("turnover_crore", m_turn.group(1) if m_turn else _find_label(lines, "turnover"))
        put("issue_date", _find_label(lines, "date of issue", "issue date") or (_DATE_RE.search(text).group(0) if _DATE_RE.search(text) else None))
        put("address", _find_label(lines, "address"))

    elif doc_type == "gst_cert":
        m = _GSTIN_RE.search(text)
        put("gstin", m.group(0) if m else None)
        put("legal_name", _find_label(lines, "legal name"))
        put("trade_name", _find_label(lines, "trade name"))
        put("address", _find_label(lines, "address"))
        put("status", _find_label(lines, "registration status", "status"))
        put("registration_date", _find_label(lines, "date of registration", "registration date"))

    elif doc_type == "pan_card":
        m = _PAN_RE.search(text)
        put("pan", m.group(0) if m else None)
        put("name", _find_label(lines, "name"))
        put("father_name", _find_label(lines, "father"))
        put("date_of_birth", _find_label(lines, "date of birth", "dob") or (_DATE_RE.search(text).group(0) if _DATE_RE.search(text) else None))

    elif doc_type == "cin":
        m = _CIN_RE.search(text)
        put("cin", m.group(0) if m else None)
        put("company_name", _find_label(lines, "company name", "name of company", "llp name"))
        put("date_of_incorporation", _find_label(lines, "date of incorporation", "incorporation date"))
        put("registered_office", _find_label(lines, "registered office", "registered address"))

    elif doc_type == "oem_auth":
        put("oem_name", _find_label(lines, "manufacturer", "principal"))
        # NB: "authorised distributor" etc. are NOT label anchors here — prose
        # letters wrap onto lines that start with those words (label lookups
        # would capture the rest of the sentence). Handled by prose regex below.
        put("authorized_bidder_name",
            _find_label(lines, "authorised dealer", "authorized dealer"))
        put("item_description", _find_label(lines, "item description", "item", "product", "goods"))
        put("valid_from", _find_label(lines, "valid from", "effective from"))
        put("valid_to", _find_label(lines, "valid to", "valid until", "expiry"))
        put("signatory", _find_label(lines, "signatory", "authorized signatory", "signed by"))
        # Prose fallbacks (authorization letters are prose, not label:value)
        if not out.get("oem_name"):
            m = re.search(r"(?:we|m/s)[,.]?\s+([A-Za-z0-9&][A-Za-z0-9 &.,'-]*?)\s*\(OEM\)", text, re.IGNORECASE)
            if m:
                put("oem_name", m.group(1).strip(), 0.8)
        if not out.get("authorized_bidder_name"):
            m = re.search(
                r"authoris[ez][a-z]*\s+([A-Za-z0-9&][A-Za-z0-9 &.,'-]*?)"
                r"(?:\s+as our|\s+for supply|\s+to supply|\s+for\b|\s*\.\s*$)",
                text, re.IGNORECASE | re.MULTILINE,
            )
            if m:
                put("authorized_bidder_name", m.group(1).strip(), 0.8)
        if not out.get("valid_from") or not out.get("valid_to"):
            m = re.search(
                r"valid\s+(?:from\s+)?(\d{4}-\d{2}-\d{2})(?:\s+to\s+(\d{4}-\d{2}-\d{2}))",
                text, re.IGNORECASE,
            )
            if m:
                put("valid_from", m.group(1), 0.85)
                put("valid_to", m.group(2), 0.85)

    elif doc_type == "local_content":
        pm = _PERCENT_RE.search(text)
        put("claimed_local_content_percent", pm.group(1) if pm else None)
        put("item", _find_label(lines, "item", "product"))
        put("declared_class", _find_label(lines, "declared class", "class", "category"))
        # cost break-up / BoM (Make-in-India domestic value addition)
        m_tot = re.search(r"[Tt]otal [Vv]alue[^0-9]*([\d.]+)", text)
        put("total_value_lakh", m_tot.group(1) if m_tot else None)
        m_imp = re.search(r"[Ii]mported [Cc]ontent [Vv]alue[^0-9]*([\d.]+)", text)
        put("imported_value_lakh", m_imp.group(1) if m_imp else None)
        put("certification_date",
            _find_label(lines, "date of certification", "certification date")
            or (_DATE_RE.search(text).group(0) if _DATE_RE.search(text) else None))

    elif doc_type == "epfo":
        m = _EPFO_RE.search(text)
        put("epfo_no", m.group(0) if m else _find_label(lines, "establishment code"))
        put("establishment_name", _find_label(lines, "name of establishment", "establishment name"))
        put("status", _find_label(lines, "status"))

    elif doc_type == "esic":
        m = _ESIC_RE.search(text)
        put("esic_no", m.group(0) if m else _find_label(lines, "esic code"))
        put("establishment_name", _find_label(lines, "name of establishment", "establishment name"))
        put("status", _find_label(lines, "status"))

    elif doc_type == "startup":
        m = _STARTUP_RE.search(text)
        put("startup_no", m.group(0) if m else _find_label(lines, "recognition number"))
        put("startup_name", _find_label(lines, "startup name", "name of startup"))
        put("status", _find_label(lines, "status"))
        put("valid_until", _find_label(lines, "valid until", "validity") or (_DATE_RE.search(text).group(0) if _DATE_RE.search(text) else None))

    elif doc_type == "nsic":
        m = _NSIC_RE.search(text)
        put("nsic_no", m.group(0) if m else _find_label(lines, "registration number"))
        put("unit_name", _find_label(lines, "unit name", "unit", "name"))
        put("status", _find_label(lines, "status"))
        put("monetary_limit", _find_label(lines, "monetary limit", "limit"))

    return out


# --- bbox location (for UI highlight boxes) -------------------------------

def locate_field_bbox(path: str, field_value: str) -> list[float] | None:
    """Find the first page + word position of a value (pdf points)."""
    try:
        import pdfplumber

        target = str(field_value).strip()
        with pdfplumber.open(path) as pdf:
            for pno, page in enumerate(pdf.pages):
                words = page.extract_words()
                for w in words:
                    if target.upper() in str(w.get("text", "")).upper():
                        return [pno + 1, w["x0"], w["top"], w["x1"], w["bottom"]]
    except Exception:
        pass
    return None


# --- unified extraction API ------------------------------------------------

def extract_document(
    path: str,
    doc_type: str,
    text: str | None = None,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    """
    Full extraction: text → fields (+bbox) with per-field confidence.
    Returns {doc_type, fields, source, confidence}.
    """
    llm = llm or get_llm_client()

    if text is None:
        from app.ai.ocr import extract_text_from_pdf

        text_result = extract_text_from_pdf(path)
        text = "\n".join(p["text"] for p in text_result["pages"])
        source = text_result["source"]
    else:
        source = "provided"

    fields: dict[str, Any] = {}
    if llm.provider != "offline_deterministic" and text.strip():
        try:
            schema = DOC_SCHEMAS.get(doc_type, [])
            user = (
                f"Extract the following fields from this {doc_type} document text "
                f"into JSON with keys exactly: {schema}. Unknown values → \"unknown\".\n\n"
                f"TASK: extract_document\nPAYLOAD: {json.dumps({'doc_type': doc_type, 'text': text})}"
            )
            result = llm.complete_json(GROUNDING_SYSTEM_PROMPT, user, "object")
            for key, val in (result.get("fields") or result).items():
                if isinstance(val, dict):
                    fields[key] = val
                elif val not in (None, "", "unknown"):
                    fields[key] = {"value": str(val), "confidence": 0.9}
        except Exception as exc:
            logger.warning("LLM extraction failed (%s) — falling back to deterministic", exc)

    if not fields:
        raw = extract_fields_deterministic(doc_type, text)
        for key, val in raw.items():
            v = val.get("value")
            if v not in (None, "", "unknown"):
                fields[key] = val

    # attach bbox for key fields (best-effort, offline)
    for key in list(fields.keys()):
        val = fields[key].get("value")
        if val and val.lower() not in ("unknown", "n/a"):
            bbox = locate_field_bbox(path, str(val))
            if bbox:
                fields[key]["page"] = bbox[0]
                fields[key]["bbox"] = bbox[1:]

    conf_values = [f.get("confidence", 1.0) for f in fields.values()]
    overall = sum(conf_values) / len(conf_values) if conf_values else 0.0
    return {
        "doc_type": doc_type,
        "fields": fields,
        "source": source,
        "confidence": round(overall, 3),
    }