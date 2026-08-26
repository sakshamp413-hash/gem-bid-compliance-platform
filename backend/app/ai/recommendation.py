"""
Recommendation engine.

Turns assessment (score/risk/check results/findings) into a plain-language
recommendation: Qualify | Needs-Review | Disqualify-candidate.

Deterministic path is fully grounded in the check results; the LLM path
(optional) rewrites the same data in officer-friendly prose referencing
specific findings. The final call ALWAYS belongs to the officer.
"""
from __future__ import annotations

import json
from typing import Any

from app.ai.llm import GROUNDING_SYSTEM_PROMPT, get_llm_client
from app.core.logging import get_logger

logger = get_logger(__name__)


def deterministic_recommendation(payload: dict) -> dict[str, Any]:
    """
    payload: {score, risk_level, hard_fail: bool, checks: [{check_type,
              result, summary}], findings: [{severity, message}]}
    """
    score = float(payload.get("score", 0))
    risk = str(payload.get("risk_level", "unknown"))
    hard_fail = bool(payload.get("hard_fail", False))
    checks = payload.get("checks", [])
    findings = payload.get("findings", [])

    fails = [c for c in checks if c.get("result") == "fail"]
    flags = [c for c in checks if c.get("result") == "flag"]

    if hard_fail or risk == "high" or any(
        f.get("severity") in ("critical",) for f in findings
    ):
        action = "disqualify_candidate"
        confidence = 0.9
    elif fails or flags:
        action = "needs_review"
        confidence = 0.7
    else:
        action = "qualify"
        confidence = 0.85

    top_reasons = []
    for c in fails[:3]:
        top_reasons.append(f"[FAIL {c.get('check_type')}] {c.get('summary', '')}")
    for c in flags[:3]:
        top_reasons.append(f"[FLAG {c.get('check_type')}] {c.get('summary', '')}")
    for f in [x for x in findings if x.get("severity") in ("critical", "high")][:3]:
        top_reasons.append(f"[{f.get('severity','').upper()}] {f.get('message', '')}")

    action_label = {
        "qualify": "Qualify",
        "needs_review": "Needs Review",
        "disqualify_candidate": "Disqualify (candidate)",
    }[action]

    text = (
        f"Compliance score {score:.1f}/100, risk {risk.upper()}. "
        f"Recommended action: {action_label}. "
        + ("The submission meets the tender's applicable eligibility requirements "
           "with no material deviations." if action == "qualify" else
           "The submission has unresolved items that must be reviewed by an officer before "
           "a decision. " if action == "needs_review" else
           "This submission fails mandatory eligibility gates; proceeding would violate "
           "tender eligibility terms. ")
        + ("Reasons: " + "; ".join(top_reasons) if top_reasons else "")
    )

    return {
        "action": action,
        "action_label": action_label,
        "confidence": round(confidence, 3),
        "text": text,
        "top_reasons": top_reasons,
    }


def generate_recommendation(assessment_data: dict) -> dict[str, Any]:
    """
    assessment_data: {score, risk_level, hard_fail, checks, findings}
    Returns {action, action_label, confidence, text, top_reasons, model_meta}
    """
    llm = get_llm_client()
    deterministic = deterministic_recommendation(assessment_data)
    model_meta = {
        "provider": llm.provider,
        "model": llm.model,
        "prompt_hash": "",
        "deterministic": True,
    }

    if llm.provider != "offline_deterministic":
        try:
            user = (
                "Write a concise officer-facing recommendation (max 120 words) for a GeM bid "
                "compliance assessment. Reference specific checks and findings. Start with one "
                "word: QUALIFY / NEEDS-REVIEW / DISQUALIFY-CANDIDATE. Never exceed the evidence.\n\n"
                f"TASK: recommendation\nPAYLOAD: {json.dumps(assessment_data)}"
            )
            result = llm.complete_json(GROUNDING_SYSTEM_PROMPT, user, "object")
            action = str(result.get("action", deterministic["action"])).lower()
            if action not in ("qualify", "needs_review", "disqualify_candidate"):
                action = deterministic["action"]
            deterministic.update({
                "action": action,
                "text": str(result.get("text", deterministic["text"])),
                "confidence": float(result.get("confidence", deterministic["confidence"])),
            })
            model_meta.update({
                "deterministic": False,
                "prompt_hash": llm.prompt_hash(GROUNDING_SYSTEM_PROMPT, user),
            })
        except Exception as exc:
            logger.warning("LLM recommendation failed (%s) — deterministic used", exc)

    deterministic["model_meta"] = model_meta
    return deterministic