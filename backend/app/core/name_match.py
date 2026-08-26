"""
Transliteration- & form-aware organization-name matching.

Real registries disagree on the form of a legal name:
  * "Pvt. Ltd." vs "Private Limited" vs "Pvt Ltd"
  * "M/s" / "Messrs" prefixes, honorifics
  * "&" vs "and", punctuation/whitespace noise
  * Devanagari / other Indic scripts vs Latin (transliteration)

`normalize_org_name()` canonicalizes all of that so fuzzy scoring compares
like-for-like. `name_match_score()` returns 0-100 like rapidfuzz, and
`name_match()` surfaces the normalized forms so evidence can show *why*
two names matched or did not.
"""
from __future__ import annotations

import re
import unicodedata

import rapidfuzz.fuzz as fuzz

# ---------------------------------------------------------------------------
# Transliteration (optional, graceful no-op if the library is absent)
# ---------------------------------------------------------------------------

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate

    _HAS_INDIC = True
except Exception:  # pragma: no cover - graceful degradation
    _HAS_INDIC = False


def _transliterate_to_latin(text: str) -> str:
    """Convert Devanagari segments to Latin ITRANS (other scripts: no-op)."""
    if not _HAS_INDIC:
        return text
    try:
        return transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except Exception:
        return text


# ---------------------------------------------------------------------------
# Canonicalization
# ---------------------------------------------------------------------------

# String-level replacements, longest-first. Applied AFTER punctuation removal
# so "PVT LTD", "PRIVATE LIMITED", "LIMITED" collapse to one form.
_SUFFIX_REPLACEMENTS = [
    ("PRIVATE LIMITED", "PVT LTD"),
    ("PRIVATE LTD", "PVT LTD"),
    ("LIMITED", "LTD"),
    ("PRIVATE", "PVT"),
]

_HONORIFICS = {"MR", "MRS", "MS", "DR", "SMT", "SHRI", "SHRIMATI", "KUMARI", "SIR", "LATE"}

# M/s, M/S., Messrs, MESSRS., M/s.  — applied to the RAW text before punctuation
# removal (so "M/S." matches as a prefix, not as tokens "M S").
_PREFIX_RE = re.compile(r"^(?:M\s*/\s*S|MESSRS|M/S)\.?\s*", re.IGNORECASE)

_PUNCT_RE = re.compile(r"[^\w\s]")
_SPACE_RE = re.compile(r"\s+")
_QUOTE_RE = re.compile(r"\.|'|\u2019")


def normalize_org_name(name: str | None) -> str:
    """
    Canonicalize an organization/person name for comparison:

      CleanCorp Industrial Solutions Pvt. Ltd.
      → CLEANCORP INDUSTRIAL SOLUTIONS PVT LTD

      M/s. Sharma & Sons Private Limited
      → SHARMA AND SONS PVT LTD

      कावेरी इंजीनियरिंग वर्क्स  →  KAVERI ENGINEERING WORKS
    """
    if not name:
        return ""
    text = unicodedata.normalize("NFKC", str(name)).strip()
    # transliterate Indic script BEFORE case conversion (ITRANS is case-sensitive)
    text = _transliterate_to_latin(text)
    text = text.upper()
    text = _PREFIX_RE.sub("", text)
    text = _QUOTE_RE.sub("", text)
    # "&" and "AND" are interchangeable in Indian entity names — replace
    # BEFORE punctuation removal so the ampersand survives
    text = text.replace("&", " AND ")
    text = _PUNCT_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text)

    for old, new in _SUFFIX_REPLACEMENTS:
        text = text.replace(old, new)

    tokens = [tok for tok in text.split(" ") if tok and tok not in _HONORIFICS]
    return " ".join(tokens).strip()


def name_match_score(name_a: str | None, name_b: str | None) -> float:
    """0-100 similarity between two names after canonicalization."""
    na, nb = normalize_org_name(name_a), normalize_org_name(name_b)
    if not na or not nb:
        return 0.0
    return float(fuzz.ratio(na, nb))


def name_match(name_a: str | None, name_b: str | None) -> dict:
    """Full match result incl. normalized forms (for evidence display)."""
    na, nb = normalize_org_name(name_a), normalize_org_name(name_b)
    return {
        "score": name_match_score(name_a, name_b),
        "normalized_a": na,
        "normalized_b": nb,
    }