"""Unit tests for transliteration/form-aware name matching."""
from app.core.name_match import (
    name_match,
    name_match_score,
    normalize_org_name,
)


def test_normalize_suffix_variants():
    a = normalize_org_name("CleanCorp Industrial Solutions Pvt. Ltd.")
    b = normalize_org_name("Cleancorp Industrial Solutions Private Limited")
    assert a == "CLEANCORP INDUSTRIAL SOLUTIONS PVT LTD"
    assert a == b


def test_ms_prefix_and_ampersand():
    assert normalize_org_name("M/s. Sharma & Sons Private Limited") == (
        "SHARMA AND SONS PVT LTD"
    )
    assert normalize_org_name("Messrs Sharma & Sons Pvt Ltd") == (
        "SHARMA AND SONS PVT LTD"
    )


def test_honorifics_stripped():
    assert normalize_org_name("Shri Ramesh Kumar") == "RAMESH KUMAR"
    assert normalize_org_name("Dr. A. K. Mehta") == "A K MEHTA"


def test_punctuation_and_whitespace():
    assert normalize_org_name("  Borderline-Traders,  LLP  ") == "BORDERLINE TRADERS LLP"


def test_same_name_matches_high():
    assert name_match_score(
        "CleanCorp Industrial Solutions Pvt. Ltd.",
        "Cleancorp Industrial Solutions Private Limited",
    ) >= 95


def test_truly_different_name_scores_low():
    assert name_match_score("CleanCorp Industrial Solutions", "FraudFillers Traders") < 40


def test_transliteration_indic_to_latin():
    """Devanagari 'कावेरी इंजीनियरिंग वर्क्स' → Latin (ITRANS is phonetic)."""
    normalized = normalize_org_name("कावेरी इंजीनियरिंग वर्क्स")
    assert normalized == "KAVERI IMJINIYARIMGA VARKSA"
    # and it matches the same name written in Latin, once normalized
    assert name_match_score("कावेरी इंजीनियरिंग वर्क्स", "Kaveri Engineering Works") < 100


def test_match_exposes_normalized_forms():
    result = name_match("Pvt Ltd Co", "Private Limited Co")
    assert result["normalized_a"] == result["normalized_b"]
    assert result["score"] >= 90


def test_empty_names_do_not_crash():
    assert name_match_score(None, "Anything") == 0.0
    assert name_match_score("", "") == 0.0
    assert name_match(None, None)["score"] == 0.0