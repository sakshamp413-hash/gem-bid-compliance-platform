"""
Tests: Make-in-India local-content verification — computed domestic
value addition from the BoM, class classification and inflated-claim
detection (thresholds from the YAML rule set).
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from app.core.config import settings  # noqa: E402
from app.rules.engine import RuleSet  # noqa: E402
from app.services.checks.local_content import _classify, check_local_content  # noqa: E402

import yaml  # noqa: E402

_RULES = RuleSet(yaml.safe_load(Path(settings.rules_file).read_text(encoding="utf-8")))


class _Tender:
    local_content_class_required = "I"


class _Bidder:
    pass


class _Adapter:
    pass


class _Ctx:
    def __init__(self, doc: dict | None):
        self.tender = _Tender()
        self.bidder = _Bidder()
        self.adapter = _Adapter()
        self.rules = _RULES
        self.documents = {"local_content": [doc]} if doc else {}


def test_classify_from_thresholds():
    assert _classify(70.0, _RULES) == "I"
    assert _classify(50.0, _RULES) == "I"
    assert _classify(49.9, _RULES) == "II"
    assert _classify(25.0, _RULES) == "II"
    assert _classify(19.9, _RULES) == "Non-local"


def test_computed_local_content_arithmetic_and_pass():
    out = check_local_content(_Ctx({"total_value_lakh": 100.0, "imported_value_lakh": 30.0,
                                    "declared_class": "I"}))
    assert out.result == "pass"
    text = out.summary
    assert "70.0%" in text                      # (1 − 30/100) × 100
    assert "Class I" in text
    assert any("local content % = (1" in (e.quote or "") for e in out.evidence), "arithmetic in evidence"


def test_inflated_declared_class_is_caught():
    # declared Class I but the BoM only supports Class II (25%)
    out = check_local_content(_Ctx({"total_value_lakh": 40.0, "imported_value_lakh": 30.0,
                                    "declared_class": "I"}))
    assert out.result == "fail"
    assert "Inflated Make-in-India claim" in out.summary
    quotes = " ".join(e.quote or "" for e in out.evidence)
    assert "declared Class I but computed Class II" in quotes
    assert "25.0%" in out.summary


def test_missing_bom_not_computable():
    out = check_local_content(_Ctx({"declared_class": "I"}))
    assert out.result == "flag"
    assert "BoM" in out.summary


def test_claimed_vs_computed_inconsistency_flagged():
    out = check_local_content(_Ctx({"total_value_lakh": 100.0, "imported_value_lakh": 30.0,
                                    "declared_class": "I", "claimed_local_content_percent": 55.0}))
    assert out.result == "flag"
    assert "differs from the" in out.summary


def test_thresholds_are_yaml_driven():
    assert float(_RULES.get("local_content", "class_i_min_percent", default=50.0)) == 50.0
    assert float(_RULES.get("local_content", "class_ii_min_percent", default=20.0)) == 20.0