"""
Weighted compliance scoring + risk bands + pending requirements.

Score (0–100) = Σ(weight × credit × confidence) / Σ(weight) over applicable
checks, where credit = 1.0 (pass), flag_ratio (flag), 0.0 (fail).

Hard-fail gates (configurable list) cap the score and force High risk.
"""
from __future__ import annotations

from typing import Any


def compute_score(check_results: list[dict], weights: dict[str, float], rules: Any) -> dict[str, Any]:
    total_w = 0.0
    acc = 0.0
    hard_fail = False
    detail: list[dict] = []

    for c in check_results:
        ctype = c["check_type"]
        result = c["result"]
        if result == "na":
            continue
        w = float(weights.get(ctype, 5.0))
        total_w += w
        if result == "pass":
            credit = 1.0
        elif result == "flag":
            credit = rules.flag_ratio()
        else:  # fail
            credit = 0.0
            if ctype in rules.hard_fail_checks:
                hard_fail = True
        acc += w * credit * float(c.get("confidence", 1.0))
        detail.append({"check_type": ctype, "result": result,
                       "weight": w, "credit": credit,
                       "confidence": float(c.get("confidence", 1.0))})

    score = (acc / total_w * 100.0) if total_w else 0.0
    if hard_fail:
        score = min(score, rules.hard_fail_score_cap())

    # risk bands
    has_fail = any(c["result"] == "fail" for c in check_results)
    has_flag = any(c["result"] == "flag" for c in check_results)
    if hard_fail or has_fail:
        risk = "high"
    elif has_flag or score < 80.0:
        risk = "medium"
    else:
        risk = "low"

    # pending requirements
    pending: list[dict] = []
    for c in check_results:
        if c["result"] in ("fail", "flag"):
            pending.append({
                "check_type": c["check_type"],
                "result": c["result"],
                "requirement": c.get("summary", f"{c['check_type']} requires officer review"),
                "rule_ref": c.get("rule_ref", ""),
            })

    return {
        "score": round(score, 2),
        "risk_level": risk,
        "hard_fail": hard_fail,
        "detail": detail,
        "pending": pending,
        "applicable_count": len(detail),
    }