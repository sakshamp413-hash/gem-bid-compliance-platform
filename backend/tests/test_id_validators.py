"""
Unit tests for Indian statutory identifier validators
(GSTIN checksum, PAN, Udyam, CIN).
"""
from app.core.id_validators import (
    gstin_checksum_char,
    gstin_pan,
    pan_entity_type,
    pan_matches_entity_type,
    pan_name_sanity,
    validate_cin,
    validate_gstin,
    validate_pan,
    validate_udyam,
)


# ---------------------------------------------------------------------------
# GSTIN
# ---------------------------------------------------------------------------

def test_gstin_valid_structure_and_checksum():
    # construct a mathematically valid GSTIN via the algorithm itself
    first14 = "27AABCC1234C1Z"
    checksum = gstin_checksum_char(first14)
    gstin = first14 + checksum
    valid, reason = validate_gstin(gstin)
    assert valid, reason
    assert len(gstin) == 15


def test_gstin_bad_checksum_rejected():
    first14 = "27AABCC1234C1Z"
    good = gstin_checksum_char(first14)
    bad_char = "A" if good != "A" else "B"
    valid, reason = validate_gstin(first14 + bad_char)
    assert not valid
    assert "checksum" in reason


def test_gstin_format_errors():
    assert not validate_gstin("27AABCC1234C1")[0]          # too short
    assert not validate_gstin("27AABCC1234C1ZZ")[0]        # too long
    assert not validate_gstin("27AABCC1234C1XA")[0]        # 14th char not Z
    assert not validate_gstin("27AABCC1234C!ZX")[0]        # invalid char
    assert not validate_gstin("")[0]


def test_gstin_extracts_embedded_pan():
    first14 = "27AABCC1234C1Z"
    gstin = first14 + gstin_checksum_char(first14)
    assert gstin_pan(gstin) == "AABCC1234C"


# ---------------------------------------------------------------------------
# PAN
# ---------------------------------------------------------------------------

def test_pan_valid():
    assert validate_pan("AABCC1234K")[0]
    assert validate_pan("AAVFB1234K")[0]


def test_pan_invalid():
    assert not validate_pan("AABCC1234")[0]      # short
    assert not validate_pan("AABCC12345K")[0]    # long
    assert not validate_pan("AAB1C1234K")[0]     # digit in letter block
    assert not validate_pan("AABCC1234")[0]
    assert not validate_pan("")[0]


def test_pan_entity_type_decode():
    assert pan_entity_type("AABCC1234K") == "company"      # 4th char C
    assert pan_entity_type("AAVFB1234K") == "firm"         # 4th char F
    assert pan_entity_type("AABPP1234K") == "individual"   # 4th char P


def test_pan_matches_entity_type():
    ok, _ = pan_matches_entity_type("AABCC1234K", "private_limited")
    assert ok
    ok, _ = pan_matches_entity_type("AAVFB1234K", "partnership")
    assert ok
    ok, reason = pan_matches_entity_type("AABCC1234K", "partnership")
    assert not ok
    assert "does not match" in reason


def test_pan_name_sanity():
    ok, _ = pan_name_sanity("AABCC1234K", "CleanCorp Industrial Solutions")
    assert ok  # 5th char C == first letter
    ok, _ = pan_name_sanity("AAVFB1234K", "Zebra Traders")
    assert not ok


# ---------------------------------------------------------------------------
# Udyam
# ---------------------------------------------------------------------------

def test_udyam_valid():
    assert validate_udyam("UDYAM-MH-27-0001234")[0]
    assert validate_udyam("udyam-tn-02-0005678")[0]  # case-insensitive


def test_udyam_invalid():
    assert not validate_udyam("UDYAM-MH-27-1234")[0]      # 3 digits
    assert not validate_udyam("UDYAM-MH-27-00012345")[0]  # 8 digits
    assert not validate_udyam("UDYAM-M-27-0001234")[0]    # 1-letter state
    assert not validate_udyam("")[0]


# ---------------------------------------------------------------------------
# CIN
# ---------------------------------------------------------------------------

def test_cin_valid():
    assert validate_cin("U12345MH2023PLC123456")[0]
    assert validate_cin("U11223TN2021NPL987654")[0]
    assert validate_cin("L28910MH1956PLC001146")[0]  # Tata Steel style


def test_cin_invalid():
    assert not validate_cin("U12345MH2023XXX123456")[0]   # bad type code
    assert not validate_cin("U12345MH1823PLC123456")[0]   # year 1823
    assert not validate_cin("U12345MH2023PLC12345")[0]    # short
    assert not validate_cin("")[0]