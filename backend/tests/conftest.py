"""Pytest configuration: isolated temp SQLite DB + env overrides."""
import os
import sys
import tempfile
from pathlib import Path

# --- isolate the app BEFORE any app module is imported --------------------
_tmp = tempfile.mkdtemp(prefix="gem_test_")
REPO = Path(__file__).resolve().parent.parent.parent
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["PORTAL_ADAPTER"] = "mock"
os.environ["LLM_PROVIDER"] = "offline"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-32b+"
os.environ["DOCUMENT_STORAGE"] = str(Path(_tmp) / "docs")
# CERTS_DIR intentionally NOT overridden: demo documents are signed by the
# CA under backend/storage/certs — tests validate against that real trust root.
os.environ["MOCK_PORTAL_DATA"] = str(REPO / "data" / "mock_portal.json")
os.environ["RULES_FILE"] = str(
    Path(__file__).resolve().parent.parent / "app" / "rules" / "rules.yaml"
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(REPO))  # for `data` package

import pytest  # noqa: E402

from app.db.session import SessionLocal, init_db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    init_db()
    from app.models.bid_submission import BidSubmission
    from app.models.user import User
    from app.seed import DEMO_USERS, seed

    with SessionLocal() as db:
        for name, email, role, password in DEMO_USERS:
            if not db.query(User).filter(User.email == email).first():
                db.add(User.create(name, email, role, password))
        db.commit()
        if db.query(BidSubmission).count() == 0:
            seed(db)  # full demo dataset incl. pipeline assessments
    yield


@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def login(client, email: str = "officer@gem.gov.in", password: str = "GeM@2026!officer") -> dict:
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}