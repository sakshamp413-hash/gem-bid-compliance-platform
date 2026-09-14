"""
Branch coverage for compliance check modules (SIH 80%+ coverage gate).

Unit-tests each check's decision branches with a fake context
(bidder namespace + stub adapter + real rule set) — no DB needed.
"""
from types import SimpleNamespace

from app.integration.adapter import PortalResponse
from app.rules.engine import get_rules

VALID_PAN = "AABCC1234K"          # company PAN, 5th char 'C' ~ CleanCorp
VALID_CIN = "U12345MH2023PLC123456"
VALID_UDYAM = "UDYAM-MH-27-0001234"
LEGAL_NAME = "CleanCorp Industrial Solutions Pvt. Ltd."


def _ctx(bidder_kwargs, adapter_kwargs, tender_kwargs=None, documents=None):
    def _resp(key):
        cfg = adapter_kwargs.get(key, {"found": False, "error": "not found"})
        return PortalResponse(
            found=cfg.get("found", False),
            data=cfg.get("data", {}),
            source="test",
            error=cfg.get("error"),
        )

    adapter = SimpleNamespace(
        mca_company=lambda cin: _resp("mca_company"),
        verify_pan=lambda pan: _resp("verify_pan"),
        verify_udyam=lambda no: _resp("verify_udyam"),
        check_blacklist=lambda *a: _resp("check_blacklist"),
    )
    bidder_fields = {
        "cin": None, "pan": None, "legal_name": LEGAL_NAME,
        "entity_type": "private_limited", "udyam_no": None,
    }
    bidder_fields.update(bidder_kwargs)
    bidder = SimpleNamespace(**bidder_fields)
    tender = SimpleNamespace(msme_only=False, **(tender_kwargs or {}))
    return SimpleNamespace(
        submission=None, tender=tender, bidder=bidder,
        documents=documents or {}, adapter=adapter, rules=get_rules(),
    )


# --- MCA ---------------------------------------------------------------

def test_mca_no_cin_is_na():
    from app.services.checks.mca import check_mca

    out = check_mca(_ctx({}, {}))
    assert out.result == "na"


def test_mca_invalid_cin_fails():
    from app.services.checks.mca import check_mca

    out = check_mca(_ctx({"cin": "BOGUS-1"}, {}))
    assert out.result == "fail"


def test_mca_portal_miss_flags():
    from app.services.checks.mca import check_mca

    out = check_mca(_ctx({"cin": VALID_CIN}, {}))
    assert out.result == "flag"


def test_mca_struck_off_flags():
    from app.services.checks.mca import check_mca

    adapter = {"mca_company": {"found": True, "data": {
        "company_name": LEGAL_NAME, "status": "Strike Off"}}}
    out = check_mca(_ctx({"cin": VALID_CIN}, adapter))
    assert out.result == "flag"


def test_mca_abnormal_status_flags():
    from app.services.checks.mca import check_mca

    adapter = {"mca_company": {"found": True, "data": {
        "company_name": LEGAL_NAME, "status": "Dormant"}}}
    out = check_mca(_ctx({"cin": VALID_CIN}, adapter))
    assert out.result == "flag"


def test_mca_name_mismatch_flags():
    from app.services.checks.mca import check_mca

    adapter = {"mca_company": {"found": True, "data": {
        "company_name": "Totally Different Enterprises Ltd.", "status": "Active"}}}
    out = check_mca(_ctx({"cin": VALID_CIN}, adapter))
    assert out.result == "flag"


def test_mca_pass():
    from app.services.checks.mca import check_mca

    adapter = {"mca_company": {"found": True, "data": {
        "company_name": LEGAL_NAME, "status": "Active"}}}
    out = check_mca(_ctx({"cin": VALID_CIN}, adapter))
    assert out.result == "pass"


# --- PAN ---------------------------------------------------------------

def test_pan_missing_fails():
    from app.services.checks.pan import check_pan

    out = check_pan(_ctx({"pan": None}, {}))
    assert out.result == "fail"


def test_pan_malformed_fails():
    from app.services.checks.pan import check_pan

    out = check_pan(_ctx({"pan": "NOTAPAN!!"}, {}))
    assert out.result == "fail"


def test_pan_entity_mismatch_flags():
    from app.services.checks.pan import check_pan

    adapter = {"verify_pan": {"found": True, "data": {
        "name": LEGAL_NAME, "status": "Active"}}}
    out = check_pan(_ctx(
        {"pan": VALID_PAN, "entity_type": "proprietorship"}, adapter))
    assert out.result == "flag"


def test_pan_registry_miss_flags():
    from app.services.checks.pan import check_pan

    out = check_pan(_ctx({"pan": VALID_PAN}, {}))
    assert out.result == "flag"


def test_pan_pass():
    from app.services.checks.pan import check_pan

    adapter = {"verify_pan": {"found": True, "data": {
        "name": LEGAL_NAME, "status": "Active"}}}
    out = check_pan(_ctx({"pan": VALID_PAN}, adapter))
    assert out.result == "pass"


# --- Blacklist ----------------------------------------------------------

def test_blacklist_clean_passes():
    from app.services.checks.blacklist import check_blacklist

    out = check_blacklist(_ctx({}, {}))
    assert out.result == "pass"


def test_blacklist_exact_pan_hit_fails():
    from app.services.checks.blacklist import check_blacklist

    adapter = {"check_blacklist": {"found": True, "data": {"matches": [{
        "name": "FraudFillers Traders", "pan": VALID_PAN,
        "cin": None, "period": "2024-2027"}]}}}
    out = check_blacklist(_ctx({"pan": VALID_PAN}, adapter))
    assert out.result == "fail"


def test_blacklist_fuzzy_name_hit_fails():
    from app.services.checks.blacklist import check_blacklist

    adapter = {"check_blacklist": {"found": True, "data": {"matches": [{
        "name": LEGAL_NAME, "pan": "ZZZZZ9999Z",
        "cin": None, "period": "2024-2027"}]}}}
    out = check_blacklist(
        _ctx({"pan": VALID_PAN, "legal_name": LEGAL_NAME}, adapter))
    assert out.result == "fail"


# --- Udyam ---------------------------------------------------------------

def test_udyam_missing_fails():
    from app.services.checks.udyam import check_udyam

    out = check_udyam(_ctx({"udyam_no": None}, {}))
    assert out.result == "fail"


def test_udyam_malformed_fails():
    from app.services.checks.udyam import check_udyam

    out = check_udyam(_ctx({"udyam_no": "UDYAM-XX"}, {}))
    assert out.result == "fail"


def test_udyam_registry_miss_fails():
    from app.services.checks.udyam import check_udyam

    out = check_udyam(_ctx({"udyam_no": VALID_UDYAM, "pan": VALID_PAN}, {}))
    assert out.result == "fail"


def test_udyam_pass():
    from app.services.checks.udyam import check_udyam

    adapter = {"verify_udyam": {"found": True, "data": {
        "legal_name": LEGAL_NAME, "status": "Active", "pan": VALID_PAN,
        "sector": "services", "investment_crore": 2.4, "turnover_crore": 18.5}}}
    out = check_udyam(_ctx({"udyam_no": VALID_UDYAM, "pan": VALID_PAN}, adapter))
    assert out.result == "pass"
