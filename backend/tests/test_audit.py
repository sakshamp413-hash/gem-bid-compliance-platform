"""
Tests: hash-chained audit log integrity + PII redaction.
"""
from app.core.logging import redact
from app.db.audit import append_audit, compute_hash, verify_chain
from app.db.session import SessionLocal


def test_audit_chain_appends_and_verifies(db):
    append_audit(db, actor="tester", action="test_action", entity="x", payload={"a": 1})
    append_audit(db, actor="tester", action="test_action2", entity="y", payload={"b": [1, 2]})
    result = verify_chain(db)
    assert result["valid"] is True
    assert result["records"] >= 2


def test_audit_chain_detects_tampering(db):
    from app.models.audit import AuditLog

    append_audit(db, actor="tester", action="a", entity="e1", payload={"k": "v"})
    append_audit(db, actor="tester", action="b", entity="e2", payload={"k": "w"})
    row = db.query(AuditLog).order_by(AuditLog.seq).first()
    assert verify_chain(db)["valid"] is True
    # tamper with the first record's hash
    original_hash = row.this_hash
    row.this_hash = "0" * 64
    db.commit()
    result = verify_chain(db)
    assert result["valid"] is False
    assert result["first_broken_seq"] == row.seq
    assert result["broken_reason"]
    # restore so the shared DB stays intact for later tests
    row.this_hash = original_hash
    db.commit()
    assert verify_chain(db)["valid"] is True


def test_audit_chain_detects_actor_edit(db):
    from app.models.audit import AuditLog

    append_audit(db, actor="tester", action="c", entity="e3")
    row = db.query(AuditLog).order_by(AuditLog.seq.desc()).first()
    assert verify_chain(db)["valid"] is True
    original_actor = row.actor
    row.actor = "attacker"
    db.commit()
    assert verify_chain(db)["valid"] is False
    # restore for tests that share the DB
    row.actor = original_actor
    db.commit()
    assert verify_chain(db)["valid"] is True


def test_compute_hash_is_deterministic():
    h1 = compute_hash(1, "a", "b", "c", "ph", "GENESIS")
    h2 = compute_hash(1, "a", "b", "c", "ph", "GENESIS")
    assert h1 == h2
    h3 = compute_hash(1, "a", "b", "c", "ph", "DIFFERENT")
    assert h1 != h3


def test_pii_redaction():
    msg = "PAN AABCC1234K GSTIN 27AABCC1234C1ZX UDYAM-MH-27-0001234 email x@y.com 9820098200"
    out = redact(msg)
    assert "AABCC1234K" not in out
    assert "27AABCC1234C1ZX" not in out
    assert "UDYAM-MH-27-0001234" not in out
    assert "x@y.com" not in out
    assert "9820098200" not in out