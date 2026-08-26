"""
Tamper-evident, hash-chained audit log.

Every state-changing action appends a record whose hash binds:
    this_hash = H(seq | actor | action | entity | payload_hash | prev_hash)

`verify_chain` recomputes the entire chain and reports the first broken link.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import text

from app.db.session import SessionLocal


def payload_hash(payload: dict[str, Any] | None) -> str:
    """Stable hash of a JSON payload (sorted keys)."""
    if not payload:
        payload = {}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_hash(
    seq: int, actor: str, action: str, entity: str, payload_hash_: str, prev_hash: str
) -> str:
    raw = f"{seq}|{actor}|{action}|{entity}|{payload_hash_}|{prev_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def append_audit(
    db,
    *,
    actor: str,
    action: str,
    entity: str,
    payload: dict[str, Any] | None = None,
    commit: bool = True,
) -> int:
    """Insert an audit record, chained to the previous one. Returns its seq."""
    from app.models.audit import AuditLog

    last = (
        db.query(AuditLog)
        .order_by(AuditLog.seq.desc())
        .limit(1)
        .first()
    )
    prev_hash = last.this_hash if last else "GENESIS"
    seq = (last.seq + 1) if last else 1
    ph = payload_hash(payload)
    this_hash = compute_hash(seq, actor, action, entity, ph, prev_hash)

    row = AuditLog(
        seq=seq,
        actor=actor,
        action=action,
        entity=entity,
        payload_hash=ph,
        prev_hash=prev_hash,
        this_hash=this_hash,
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    return seq


def verify_chain(db) -> dict[str, Any]:
    """Recompute the chain; return integrity status + first broken link."""
    from app.models.audit import AuditLog

    rows = db.query(AuditLog).order_by(AuditLog.seq.asc()).all()
    result = {
        "valid": True,
        "records": len(rows),
        "first_broken_seq": None,
        "broken_reason": None,
    }
    prev_hash = "GENESIS"
    for row in rows:
        expected = compute_hash(
            row.seq, row.actor, row.action, row.entity, row.payload_hash, prev_hash
        )
        if expected != row.this_hash:
            result["valid"] = False
            result["first_broken_seq"] = row.seq
            result["broken_reason"] = (
                f"record {row.seq} hash mismatch: expected {expected[:16]}…, "
                f"found {row.this_hash[:16]}…"
            )
            return result
        prev_hash = row.this_hash
    return result