"""
Indian statutory identifier validators.

Implements real, public, offline-verifiable algorithms:
  * GSTIN format + the public GSTN checksum algorithm
  * PAN format + 4th-char entity-type decode
  * Udyam Registration Number (URN) format
  * CIN format

Thresholds (MSME caps, etc.) intentionally live in the editable rule set
(app/rules/rules.yaml) — never hardcoded here.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# GSTIN
# ---------------------------------------------------------------------------

GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z][Z][0-9A-Z]$")
_GSTIN_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _gstin_char_value(ch: str) -> int:
    """Map a GSTIN character to its numeric value (0-9=0-9, A-Z=10-35)."""
    return _GSTIN_CHARSET.index(ch.upper())


def gstin_checksum_char(first14: str) -> str:
    """
    GSTN check digit — the algorithm GSTN actually uses.

    Luhn mod 36 over the charset 0-9A-Z: iterate the first 14 characters from
    right to left, double every second character (factor alternates 2,1,2,1…),
    split the doubled value into digit-sum parts (value//36 + value%36),
    accumulate, then the check digit is the character whose numeric value makes
    the total divisible by 36.

    Reference: GSTN 'GSTIN generation logic' (check digit as Luhn mod 36);
    this is the scheme used by real GSTINs (e.g. 27AAPFU0939F1ZV).
    """
    if len(first14) != 14:
        raise ValueError("GSTIN checksum requires exactly 14 characters")
    factor, total = 2, 0
    for ch in reversed(first14.upper()):
        cp = _gstin_char_value(ch)  # raises on invalid char — validate upstream
        addend = factor * cp
        factor = 1 if factor == 2 else 2
        addend = (addend // 36) + (addend % 36)
        total += addend
    return _GSTIN_CHARSET[(36 - (total % 36)) % 36]


def validate_gstin(gstin: str) -> tuple[bool, str]:
    """
    Validate a GSTIN: format + real checksum.

    Returns (valid, reason). reason describes the failure if invalid.
    """
    gstin = (gstin or "").strip().upper()
    if len(gstin) != 15:
        return False, "GSTIN must be exactly 15 characters"
    if not GSTIN_RE.match(gstin):
        return False, "GSTIN format invalid (expected 2-digit state + PAN + entity + Z + checksum)"
    if gstin[13] != "Z":
        return False, "GSTIN position 14 must be 'Z'"
    expected = gstin_checksum_char(gstin[:14])
    if gstin[14] != expected:
        return False, f"GSTIN checksum mismatch (expected '{expected}')"
    return True, "GSTIN format and checksum valid"


def gstin_pan(gstin: str) -> str | None:
    """Extract the embedded PAN (chars 2..12) from a GSTIN."""
    g = (gstin or "").strip().upper()
    if len(g) == 15:
        return g[2:12]
    return None


# ---------------------------------------------------------------------------
# PAN
# ---------------------------------------------------------------------------

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

# 4th character = entity type code (standard Income-Tax codes).
PAN_ENTITY_CODES: dict[str, str] = {
    "A": "association_of_persons",
    "B": "body_of_individuals",
    "C": "company",
    "F": "firm",
    "G": "government",
    "H": "hindu_undivided_family",
    "J": "artificial_juridical_person",
    "L": "local_authority",
    "P": "individual",
    "T": "trust",
}

# Map our internal entity_type values to the expected PAN 4th char.
ENTITY_TYPE_TO_PAN_CODE: dict[str, str] = {
    "private_limited": "C",
    "public_limited": "C",
    "company": "C",
    "firm": "F",
    "partnership": "F",
    "proprietorship": "P",
    "individual": "P",
    "llp": "C",  # LLPs are issued PAN with 'C' (company-type) in practice
    "trust": "T",
    "society": "A",
    "government": "G",
    "huf": "H",
}


def validate_pan(pan: str) -> tuple[bool, str]:
    pan = (pan or "").strip().upper()
    if len(pan) != 10:
        return False, "PAN must be exactly 10 characters"
    if not PAN_RE.match(pan):
        return False, "PAN format invalid (expected 5 letters + 4 digits + 1 letter)"
    return True, "PAN format valid"


def pan_entity_type(pan: str) -> str | None:
    """Decode the 4th character of a PAN into an entity-type name."""
    p = (pan or "").strip().upper()
    if len(p) != 10:
        return None
    return PAN_ENTITY_CODES.get(p[3])


def pan_matches_entity_type(pan: str, entity_type: str) -> tuple[bool, str]:
    """Check PAN 4th char against the bidder's declared entity type."""
    code = ENTITY_TYPE_TO_PAN_CODE.get(entity_type, "")
    actual = (pan or "").strip().upper()[3] if pan and len(pan.strip()) == 10 else None
    if not actual:
        return False, "PAN unavailable to check entity type"
    if code and actual == code:
        return True, f"PAN entity-type char '{actual}' matches declared entity type '{entity_type}'"
    return (
        False,
        f"PAN entity-type char '{actual}' does not match declared entity type '{entity_type}'",
    )


def pan_name_sanity(pan: str, legal_name: str) -> tuple[bool, str]:
    """
    The 5th PAN character is the first letter of the surname (individuals)
    or the first letter of the entity name. Compare against the legal name.
    """
    p = (pan or "").strip().upper()
    name = (legal_name or "").strip().upper()
    if len(p) != 10 or not name:
        return False, "PAN or legal name unavailable for name sanity check"
    if p[4] == name[0]:
        return True, f"PAN 5th char '{p[4]}' matches first letter of legal name '{name[0]}'"
    return False, f"PAN 5th char '{p[4]}' does not match first letter of legal name '{name[0]}'"


# ---------------------------------------------------------------------------
# Udyam Registration Number
# ---------------------------------------------------------------------------

# UDYAM-<state 2 letters>-<district 2 digits>-<7 digits>
UDYAM_RE = re.compile(r"^UDYAM-[A-Z]{2}-\d{2}-\d{7}$", re.IGNORECASE)


def validate_udyam(udyam: str) -> tuple[bool, str]:
    u = (udyam or "").strip().upper()
    if not UDYAM_RE.match(u):
        return False, "Udyam number format invalid (expected UDYAM-XX-XX-XXXXXXX)"
    return True, "Udyam number format valid"


# ---------------------------------------------------------------------------
# CIN
# ---------------------------------------------------------------------------

# CIN is 21 chars: [L|U] + 5 digits + 2-letter state + 4-digit year +
# 3-letter type + 6-digit ROC/serial.
# NOTE (public sources differ on the meaning of the 5-digit block; MCA FAQ
# documents the layout as ListingStatus/Year/State/Number/Type/ROC — we
# validate the *structural* pattern that every real CIN satisfies:
#   U74900MH2012PTC229448  (Tata Steel: U28910MH1956PLC001146)
# Isolated here for unit testing.
CIN_RE = re.compile(r"^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$")
CIN_TYPES = {"PLC", "PTC", "LLP", "OPC", "FII", "NPL", "SGC", "UGC", "GAP", "NLC", "INI", "PSC", "BCH"}


def validate_cin(cin: str) -> tuple[bool, str]:
    c = (cin or "").strip().upper()
    if len(c) != 21:
        return False, "CIN must be exactly 21 characters"
    if not CIN_RE.match(c):
        return False, "CIN format invalid (expected L/U + 5 digits + state + 4-digit year + type + 6 digits)"
    year = int(c[8:12])
    if not (1900 <= year <= 2099):
        return False, f"CIN registration year '{c[8:12]}' out of plausible range"
    if c[12:15] not in CIN_TYPES:
        return False, f"CIN company type code '{c[12:15]}' not recognised"
    return True, "CIN format valid"


def validate_state_code(code2: str) -> bool:
    """2-letter state/UT abbreviation sanity (used by Udyam state component)."""
    return code2.upper() in {
        "AP", "AR", "AS", "BR", "CG", "GA", "GJ", "HR", "HP", "JH",
        "KA", "KL", "MP", "MH", "MN", "ML", "MZ", "NL", "OD", "PB",
        "RJ", "SK", "TN", "TG", "TR", "UP", "UK", "WB", "AN", "CH",
        "DN", "DD", "DL", "JK", "LA", "LD", "PY",
    }