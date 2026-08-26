"""
Offline deterministic task handlers for the OfflineFallback LLM.

Each handler parses a task JSON payload embedded in the user prompt
("PAYLOAD: <json>") and returns grounded results. No model required.
"""
from __future__ import annotations

import json
import re
from typing import Any


def _payload(user: str) -> dict[str, Any]:
    m = re.search(r"PAYLOAD:\s*(\{.*\})\s*$", user, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


def _to_contract(fields: dict[str, Any]) -> dict[str, Any]:
    """Normalize {field: {value, confidence, page, bbox}} from simple values."""
    out = {}
    for key, val in fields.items():
        if isinstance(val, dict) and "value" in val:
            out[key] = val
        else:
            out[key] = {"value": val, "confidence": 1.0}
    return out


def task_extract_document(user: str) -> dict[str, Any]:
    """Deterministic field extraction per document type."""
    from app.ai.extraction import extract_fields_deterministic

    payload = _payload(user)
    text = payload.get("text", "")
    doc_type = payload.get("doc_type", "")
    fields = extract_fields_deterministic(doc_type, text)
    return {"doc_type": doc_type, "fields": _to_contract(fields)}


def task_cross_verify(user: str) -> dict[str, Any]:
    """Deterministic cross-document consistency analysis."""
    from app.ai.cross_verify import run_deterministic_cross_verify

    payload = _payload(user)
    return run_deterministic_cross_verify(payload)


def task_recommendation(user: str) -> dict[str, Any]:
    """Deterministic recommendation from assessment data."""
    from app.ai.recommendation import deterministic_recommendation

    payload = _payload(user)
    return deterministic_recommendation(payload)


def task_generic(user: str) -> dict[str, Any]:
    return {"note": "offline deterministic responder: no specialized handler for this task"}