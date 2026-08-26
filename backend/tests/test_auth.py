"""
Tests: auth flow + RBAC + rate limiting + officer decision flow.
"""
from tests.conftest import auth_headers, login


def test_login_and_me(client):
    tok = login(client)
    assert tok["token_type"] == "bearer"
    me = client.get("/auth/me", headers=auth_headers(tok["access_token"]))
    assert me.status_code == 200
    assert me.json()["role"] == "officer"


def test_wrong_password_rejected(client):
    r = client.post("/auth/login", json={"email": "officer@gem.gov.in", "password": "wrong"})
    assert r.status_code == 401


def test_missing_token_rejected(client):
    assert client.get("/tenders").status_code == 401


def test_rbac_auditor_cannot_create_tender(client):
    tok = login(client, "auditor@gem.gov.in", "GeM@2026!auditor")
    r = client.post("/tenders", json={
        "gem_ref": "GEM/X", "title": "x", "buyer_org": "y",
    }, headers=auth_headers(tok["access_token"]))
    assert r.status_code == 403


def test_rbac_admin_can_manage_users(client):
    tok = login(client, "admin@gem.gov.in", "GeM@2026!admin")
    r = client.get("/users", headers=auth_headers(tok["access_token"]))
    assert r.status_code == 200
    assert len(r.json()) >= 3


def test_officer_decision_flow(client):
    tok = login(client)
    h = auth_headers(tok["access_token"])
    # decision on a seeded submission
    subs = client.get("/submissions", headers=h).json()
    assert len(subs) >= 5
    sub_id = subs[0]["id"]
    r = client.post(f"/submissions/{sub_id}/decisions", headers=h, json={
        "decision": "qualify",
        "justification": "All statutory checks passed and registry data verified.",
    })
    assert r.status_code == 200, r.text
    # override without justification is rejected by validation
    r = client.post(f"/submissions/{sub_id}/decisions", headers=h, json={
        "decision": "disqualify",
        "justification": "short",
    })
    assert r.status_code == 422


def test_audit_verify_endpoint(client):
    tok = login(client)
    r = client.get("/audit/verify", headers=auth_headers(tok["access_token"]))
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_rate_limit_auth(client):
    import time

    time.sleep(1)
    code = None
    for _ in range(30):
        r = client.post("/auth/login", json={"email": "officer@gem.gov.in",
                                             "password": "wrong-password"})
        code = r.status_code
        if code == 429:
            break
    assert code == 429