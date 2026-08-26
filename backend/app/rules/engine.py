"""
Tender-aware rule engine.

Loads `rules.yaml` (editable in Admin UI), computes the applicable check
checklist for a (tender, submission) pair, and exposes typed accessors so
check modules never hardcode thresholds.
"""
from __future__ import annotations

import copy
import threading
from pathlib import Path
from typing import Any

import yaml

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RuleSet:
    def __init__(self, data: dict[str, Any]):
        self.data = data

    # -- accessors ------------------------------------------------------
    def get(self, *path: str, default: Any = None) -> Any:
        node: Any = self.data
        for key in path:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    @property
    def weights(self) -> dict[str, float]:
        return {k: float(v) for k, v in self.get("weights", default={}).items()}

    @property
    def hard_fail_checks(self) -> list[str]:
        return list(self.get("hard_fail_checks", default=[]))

    def classification_band(self, sector: str, investment_crore: float, turnover_crore: float) -> str:
        """Classify micro/small/medium from thresholds (configurable)."""
        bands = self.get("msme", "classification", sector, default={})
        for band in ("micro", "small", "medium"):
            caps = bands.get(band, {})
            inv_ok = investment_crore <= float(caps.get("investment_crore", 0))
            turn_ok = turnover_crore <= float(caps.get("turnover_crore", 0))
            if inv_ok and turn_ok:
                return band
        return "large"

    def local_content_required_percent(self, class_label: str) -> float | None:
        if class_label == "I":
            return float(self.get("local_content", "class_i_min_percent", default=50.0))
        if class_label == "II":
            return float(self.get("local_content", "class_ii_min_percent", default=20.0))
        return None

    def gst_grace_months(self) -> int:
        return int(self.get("gst", "return_grace_period_months", default=2))

    def gst_cancelled_statuses(self) -> list[str]:
        return [str(s) for s in self.get("gst", "cancelled_status", default=["Cancelled"])]

    def oem_max_validity_years(self) -> int:
        return int(self.get("oem", "max_validity_years", default=2))

    def blacklist_fuzzy_threshold(self) -> float:
        return float(self.get("blacklist", "fuzzy_threshold", default=85.0))

    def flag_ratio(self) -> float:
        return float(self.get("scoring", "flag_ratio", default=0.5))

    def hard_fail_score_cap(self) -> float:
        return float(self.get("scoring", "hard_fail_score_cap", default=25.0))

    def recommendation_confidence_threshold(self) -> float:
        return float(self.get("scoring", "recommendation_confidence_threshold", default=0.6))

    # -- checklist generation -------------------------------------------
    def applicable_checks(self, tender: Any, bidder: Any, doc_types: set[str]) -> list[str]:
        """Return the ordered list of check_type names applicable to this submission."""
        checks: list[str] = ["udyam", "gst", "pan", "blacklist"]
        # MCA — only when the bidder holds a CIN (companies)
        if getattr(bidder, "cin", None):
            checks.append("mca")
        # Local content — tender requires a class AND bidder claims it
        if tender.local_content_class_required and "local_content" in doc_types:
            checks.append("local_content")
        # EPFO / ESIC — when the bidder declares establishment codes
        if getattr(bidder, "epfo_no", None):
            checks.append("epfo")
        if getattr(bidder, "esic_no", None):
            checks.append("esic")
        # Startup India — when the bidder declares a DPIIT number
        if getattr(bidder, "startup_no", None):
            checks.append("startup")
        # NSIC — when declared
        if getattr(bidder, "nsic_no", None):
            checks.append("nsic")
        # OEM authorization — tender requires it AND bidder is a reseller
        required = list(tender.required_docs_json or [])
        if "oem_auth" in required and getattr(bidder, "is_reseller", True):
            checks.append("oem")
        # DigiLocker-style document integrity — when signed/tamper analysis exists
        if doc_types:
            checks.append("digilocker")
        # Keep declared order stable
        order = [
            "udyam", "gst", "pan", "mca", "local_content", "epfo", "esic",
            "startup", "nsic", "oem", "digilocker", "blacklist",
        ]
        return [c for c in order if c in checks]


class RuleStore:
    """Loads/saves the rule set; thread-safe; supports hot reload."""

    def __init__(self, path: str | None = None):
        self.path = Path(path or settings.rules_file)
        self._lock = threading.Lock()
        self._ruleset = self._load()

    def _load(self) -> RuleSet:
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                return RuleSet(yaml.safe_load(f) or {})
        logger.warning("rules file missing at %s — using empty rule set", self.path)
        return RuleSet({})

    @property
    def current(self) -> RuleSet:
        return self._ruleset

    def save(self, data: dict[str, Any]) -> RuleSet:
        with self._lock:
            with open(self.path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
            self._ruleset = RuleSet(copy.deepcopy(data))
        return self._ruleset

    def reload(self) -> RuleSet:
        with self._lock:
            self._ruleset = self._load()
        return self._ruleset


_rule_store: RuleStore | None = None


def get_rule_store() -> RuleStore:
    global _rule_store
    if _rule_store is None:
        _rule_store = RuleStore()
    return _rule_store


def get_rules() -> RuleSet:
    return get_rule_store().current