"""
Tests for RBAC matrix capabilities:
- Tender ingestion: Officer ✅, Auditor 👁️ (403), Admin ✅
- Bid/evidence review: all 3 roles read-only / evaluate
- Rule visibility: Officer ✅, Auditor ✅, Admin ✅
- Procurement decision: Officer ✅, Auditor ❌ (403), Admin ⚠️ (audited as admin_decision_override)
- Rule drafting & publishing: Officer ❌ (403), Auditor ❌ (403), Admin ✅
- User & integration management: Admin ✅, Officer ❌ (403), Auditor ❌ (403)
- /users/me/permissions returns accurate capabilities
"""
import pytest
from app.core.security import create_access_token
from app.models.user import User
from app.models.audit import AuditLog
from app.models.bid_submission import BidSubmission
from tests.conftest import auth_headers


@pytest.fixture
def auth_tokens(db):
    officer = db.query(User).filter(User.role == "officer").first()
    auditor = db.query(User).filter(User.role == "auditor").first()
    admin = db.query(User).filter(User.role == "admin").first()
    return {
        "officer": auth_headers(create_access_token(officer.id)),
        "auditor": auth_headers(create_access_token(auditor.id)),
        "admin": auth_headers(create_access_token(admin.id)),
    }


def test_permissions_endpoint(client, auth_tokens):
    """Verify /users/me/permissions returns exact capabilities per role."""
    # Officer
    r_off = client.get("/users/me/permissions", headers=auth_tokens["officer"])
    assert r_off.status_code == 200
    caps_off = r_off.json()["capabilities"]
    assert caps_off["tender_ingestion"] is True
    assert caps_off["procurement_decision"] is True
    assert caps_off["rule_visibility"] is True
    assert caps_off["rule_drafting"] is False
    assert caps_off["rule_publishing"] is False
    assert caps_off["user_management"] is False
    assert caps_off["integration_management"] is False

    # Auditor
    r_aud = client.get("/users/me/permissions", headers=auth_tokens["auditor"])
    assert r_aud.status_code == 200
    caps_aud = r_aud.json()["capabilities"]
    assert caps_aud["tender_ingestion"] is False  # 👁️ view-only
    assert caps_aud["procurement_decision"] is False  # ❌
    assert caps_aud["rule_visibility"] is True  # ✅
    assert caps_aud["rule_drafting"] is False
    assert caps_aud["rule_publishing"] is False

    # Admin
    r_adm = client.get("/users/me/permissions", headers=auth_tokens["admin"])
    assert r_adm.status_code == 200
    caps_adm = r_adm.json()["capabilities"]
    assert caps_adm["tender_ingestion"] is True
    assert caps_adm["rule_drafting"] is True
    assert caps_adm["rule_publishing"] is True
    assert caps_adm["user_management"] is True
    assert caps_adm["integration_management"] is True


def test_tender_ingestion_rbac(client, auth_tokens):
    """Officer and Admin can ingest tenders; Auditor is blocked (403)."""
    payload_off = {
        "gem_ref": "GEM/2026/B/999111",
        "title": "Officer Test Tender Ingestion",
        "buyer_org": "CPCL",
    }
    r1 = client.post("/tenders", json=payload_off, headers=auth_tokens["officer"])
    assert r1.status_code in (200, 409)

    payload_aud = {
        "gem_ref": "GEM/2026/B/999222",
        "title": "Auditor Test Tender Ingestion",
        "buyer_org": "CPCL",
    }
    r2 = client.post("/tenders", json=payload_aud, headers=auth_tokens["auditor"])
    assert r2.status_code == 403

    payload_adm = {
        "gem_ref": "GEM/2026/B/999333",
        "title": "Admin Test Tender Ingestion",
        "buyer_org": "CPCL",
    }
    r3 = client.post("/tenders", json=payload_adm, headers=auth_tokens["admin"])
    assert r3.status_code in (200, 409)


def test_rule_visibility_and_authoring_rbac(client, auth_tokens):
    """All 3 roles can read rules (rule visibility); only Admin can modify/publish."""
    # Read rules (visibility for all)
    assert client.get("/admin/rules", headers=auth_tokens["officer"]).status_code == 200
    assert client.get("/admin/rules", headers=auth_tokens["auditor"]).status_code == 200
    assert client.get("/admin/rules", headers=auth_tokens["admin"]).status_code == 200

    # Modify rules (only admin allowed)
    assert client.put("/admin/rules", json={"weights": {}}, headers=auth_tokens["officer"]).status_code == 403
    assert client.put("/admin/rules", json={"weights": {}}, headers=auth_tokens["auditor"]).status_code == 403


def test_procurement_decision_rbac_and_audit(client, auth_tokens, db):
    """Auditor cannot make decisions (403); Admin decision is tagged as admin_decision_override."""
    sub = db.query(BidSubmission).first()
    assert sub is not None

    # Auditor decision is blocked
    r_aud = client.post(
        f"/submissions/{sub.id}/decisions",
        json={"decision": "qualify", "justification": "Auditor attempt should fail"},
        headers=auth_tokens["auditor"],
    )
    assert r_aud.status_code == 403

    # Officer decision succeeds
    r_off = client.post(
        f"/submissions/{sub.id}/decisions",
        json={"decision": "qualify", "justification": "Officer valid justification for evaluation"},
        headers=auth_tokens["officer"],
    )
    assert r_off.status_code == 200

    # Admin decision succeeds and is logged with admin_decision_override
    r_adm = client.post(
        f"/submissions/{sub.id}/decisions",
        json={"decision": "qualify", "justification": "Admin administrative override for testing"},
        headers=auth_tokens["admin"],
    )
    assert r_adm.status_code == 200

    db.expire_all()
    audit_entry = (
        db.query(AuditLog)
        .filter(AuditLog.entity == f"submission:{sub.id}", AuditLog.action == "admin_decision_override")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.action == "admin_decision_override"
    assert "user:" in audit_entry.actor


def test_integration_management_rbac(client, auth_tokens):
    """Only Admin can access integration management endpoints."""
    assert client.get("/admin/integrations", headers=auth_tokens["officer"]).status_code == 403
    assert client.get("/admin/integrations", headers=auth_tokens["auditor"]).status_code == 403

    r_adm = client.get("/admin/integrations", headers=auth_tokens["admin"])
    assert r_adm.status_code == 200
    data = r_adm.json()
    assert "integrations" in data
    assert len(data["integrations"]) > 0

    # Admin health test
    r_test = client.post("/admin/integrations/test", headers=auth_tokens["admin"])
    assert r_test.status_code == 200
    assert r_test.json()["status"] == "all_systems_operational"
